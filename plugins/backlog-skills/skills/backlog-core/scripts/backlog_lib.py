#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TASK_ID_RE = re.compile(r"\b([a-z]{2})(\d{1,2})\b", re.IGNORECASE)
LEGACY_TASK_ID_RE = re.compile(r"^(?:[A-Za-z]{2,4}\d{0,4}|\d{1,6}[A-Za-z]?)$")
PLAIN_YAML_RE = re.compile(r"^[A-Za-z0-9_.:+/@-]+$")
INLINE_TASK_ID_RE = re.compile(r"^\*\*TaskID\*\*:\s*(.+?)\s*$", re.IGNORECASE)
INLINE_STATUS_RE = re.compile(r"^\*\*Status\*\*:\s*(.+?)\s*$", re.IGNORECASE)

STATUS_ORDER = [
    "draft",
    "todo",
    "someday",
    "refining",
    "refined",
    "planned",
    "wip",
    "blocked",
    "archived",
    "completed",
]
STATE_DIRS = OrderedDict((status, "tasks") for status in STATUS_ORDER)
ACTIVE_STATES = set(STATUS_ORDER) - {"archived", "completed"}
HISTORY_STATES = {"archived", "completed"}
MANUAL_STATES = ("draft", "todo", "someday", "planned")
TIMESTAMP_FIELDS = {
    "refining": "updatedAt",
    "refined": "updatedAt",
    "wip": "updatedAt",
    "blocked": "blockedAt",
    "archived": "archivedAt",
    "completed": "completedAt",
}
ORDER_FILE_NAME = "order.json"

TASK_FRONTMATTER_ORDER = [
    "taskId",
    "status",
    "createdAt",
    "updatedAt",
    "group",
    "reviewedAt",
    "plannedAt",
    "startedAt",
    "blockedAt",
    "blockedFrom",
    "blockReason",
    "archivedAt",
    "archivedFrom",
    "archiveReason",
    "completedAt",
    "reviewAfter",
]
ARTIFACT_FRONTMATTER_ORDER = ["taskId", "createdAt", "updatedAt"]
QUESTION_FRONTMATTER_ORDER = ["taskId", "round", "createdAt", "updatedAt", "answeredAt"]
TASK_ARTIFACT_SUFFIXES = (".task.refined.md", ".task.draft.md", ".task.md")


@dataclass
class TaskRecord:
    state: str
    folder_state: str
    folder: Path
    task_file: Path
    draft_task_file: Path | None
    refined_task_file: Path | None
    legacy_task_file: Path | None
    plan_file: Path | None
    notes_file: Path | None
    extra_files: list[Path]
    task_id: str
    title: str
    meta: dict[str, str]


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def normalize_task_id(raw: str) -> str:
    token = raw.strip()
    match = TASK_ID_RE.search(token)
    if match:
        return f"{match.group(1).upper()}{int(match.group(2)):02d}"
    if LEGACY_TASK_ID_RE.fullmatch(token):
        return token.upper()
    bracket = re.search(r"\[([A-Za-z0-9]{2,8})\]", token)
    if bracket and LEGACY_TASK_ID_RE.fullmatch(bracket.group(1)):
        return bracket.group(1).upper()
    raise ValueError(f"Could not parse task ID from: {raw}")


def looks_like_task_id(raw: str) -> bool:
    try:
        normalize_task_id(raw)
        return True
    except ValueError:
        return False


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "task"


def render_yaml_value(value: str) -> str:
    if value == "":
        return '""'
    return value if PLAIN_YAML_RE.fullmatch(value) else json.dumps(value)


def parse_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return json.loads(value) if value[0] == '"' else value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end_marker = text.find("\n---\n", 4)
    if end_marker == -1:
        return {}, text
    data: dict[str, str] = {}
    for line in text[4:end_marker].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip():
            data[key.strip()] = parse_yaml_scalar(value)
    return data, text[end_marker + 5 :]


def dump_frontmatter(meta: dict[str, str], order: list[str]) -> str:
    lines = ["---"]
    seen: set[str] = set()
    for key in order:
        value = meta.get(key)
        if value in (None, ""):
            continue
        lines.append(f"{key}: {render_yaml_value(str(value))}")
        seen.add(key)
    for key in sorted(meta):
        if key in seen or meta[key] in (None, ""):
            continue
        lines.append(f"{key}: {render_yaml_value(str(meta[key]))}")
    return "\n".join([*lines, "---", ""])


def read_markdown(path: Path) -> tuple[dict[str, str], str]:
    return parse_frontmatter(path.read_text())


def write_markdown(path: Path, meta: dict[str, str], body: str, kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "task":
        atomic_write(path, dump_frontmatter(meta, TASK_FRONTMATTER_ORDER) + body.lstrip("\n"))
    else:
        atomic_write(path, body.lstrip("\n"))


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def detect_task_kind(path: Path) -> str:
    if path.name.endswith(".task.md"):
        return "task"
    if ".question.v" in path.name:
        return "question"
    if path.name.endswith(".plan.md"):
        return "plan"
    if path.name.endswith(".notes.md"):
        return "notes"
    return "artifact"


def task_filename(task_id: str) -> str:
    return f"{task_id}.task.md"


def draft_task_filename(task_id: str) -> str:
    return f"{task_id}.task.draft.md"


def refined_task_filename(task_id: str) -> str:
    return f"{task_id}.task.refined.md"


def plan_filename(task_id: str) -> str:
    return f"{task_id}.plan.md"


def notes_filename(task_id: str) -> str:
    return f"{task_id}.notes.md"


def tasks_dir(backlog_root: Path) -> Path:
    return backlog_root / "tasks"


def state_dir(backlog_root: Path, state: str) -> Path:
    if state not in STATUS_ORDER:
        raise ValueError(f"Unsupported state: {state}")
    return tasks_dir(backlog_root)


def active_backlog_path(backlog_root: Path) -> Path:
    return backlog_root / "BACKLOG.md"


def order_file_path(backlog_root: Path) -> Path:
    return backlog_root / ORDER_FILE_NAME


def completed_log_path(backlog_root: Path) -> Path:
    return backlog_root / "COMPLETED.md"


def archived_log_path(backlog_root: Path) -> Path:
    return backlog_root / "ARCHIVED.md"


def status_index_filename(state: str) -> str:
    return f"BACKLOG_{state.upper()}.md"


def status_index_path(backlog_root: Path, state: str) -> Path:
    return backlog_root / status_index_filename(state)


def strip_task_artifact_suffix(name: str) -> str:
    for suffix in TASK_ARTIFACT_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def extract_title(body: str, fallback: str) -> str:
    return next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), fallback)


def relative_link(from_dir: Path, target: Path) -> str:
    value = os.path.relpath(target, from_dir)
    return (value if value.startswith(".") else f"./{value}").replace(os.sep, "/")


def ensure_task_indexes(backlog_root: Path) -> None:
    tasks_dir(backlog_root).mkdir(parents=True, exist_ok=True)


def _canonical_candidates(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.task.md"))


def discover_tasks(backlog_root: Path) -> list[TaskRecord]:
    root = tasks_dir(backlog_root)
    if not root.is_dir():
        return []
    records: list[TaskRecord] = []
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        candidates = _canonical_candidates(folder)
        if len(candidates) != 1:
            if candidates:
                raise RuntimeError(f"Expected one canonical task file in {folder}, found {len(candidates)}")
            continue
        task_file = candidates[0]
        meta, body = read_markdown(task_file)
        task_id = str(meta.get("taskId") or strip_task_artifact_suffix(task_file.name)).strip()
        status = str(meta.get("status") or "").strip().lower()
        if status not in STATUS_ORDER:
            raise ValueError(f"Invalid or missing status in {task_file}: {status or '<missing>'}")
        plan_path = folder / plan_filename(task_id)
        notes_path = folder / notes_filename(task_id)
        records.append(
            TaskRecord(
                state=status,
                folder_state=status,
                folder=folder,
                task_file=task_file,
                draft_task_file=None,
                refined_task_file=None,
                legacy_task_file=task_file,
                plan_file=plan_path if plan_path.exists() else None,
                notes_file=notes_path if notes_path.exists() else None,
                extra_files=sorted(
                    path
                    for path in folder.glob("*.md")
                    if path not in {task_file, plan_path, notes_path}
                ),
                task_id=task_id,
                title=extract_title(body, folder.name),
                meta=meta,
            )
        )
    ids: dict[str, list[Path]] = {}
    for record in records:
        ids.setdefault(normalize_task_id(record.task_id), []).append(record.task_file)
    duplicates = {key: paths for key, paths in ids.items() if len(paths) > 1}
    if duplicates:
        summary = "; ".join(f"{key}: {', '.join(map(str, paths))}" for key, paths in duplicates.items())
        raise RuntimeError(f"Duplicate task IDs: {summary}")
    return records


def resolve_task(backlog_root: Path, task_ref: str, states: set[str] | None = None) -> TaskRecord:
    normalized = normalize_task_id(task_ref)
    matches = [
        record
        for record in discover_tasks(backlog_root)
        if normalize_task_id(record.task_id) == normalized and (not states or record.state in states)
    ]
    if not matches:
        raise FileNotFoundError(f"Task {task_ref} not found in {backlog_root}")
    if len(matches) != 1:
        raise RuntimeError(f"Task {task_ref} resolved to {len(matches)} tasks")
    return matches[0]


def _empty_order() -> dict[str, object]:
    return {"version": 1, "manualOrder": {state: [] for state in MANUAL_STATES}}


def read_manual_order(backlog_root: Path) -> dict[str, list[str]]:
    path = order_file_path(backlog_root)
    if not path.exists():
        return {state: [] for state in MANUAL_STATES}
    data = json.loads(path.read_text())
    raw = data.get("manualOrder", {}) if isinstance(data, dict) else {}
    return {
        state: [normalize_task_id(str(value)) for value in raw.get(state, [])]
        for state in MANUAL_STATES
    }


def repair_manual_order(backlog_root: Path, records: list[TaskRecord] | None = None) -> dict[str, list[str]]:
    records = records if records is not None else discover_tasks(backlog_root)
    current = read_manual_order(backlog_root)
    repaired: dict[str, list[str]] = {}
    for state in MANUAL_STATES:
        valid = [normalize_task_id(record.task_id) for record in records if record.state == state]
        valid_set = set(valid)
        seen: set[str] = set()
        ordered = []
        for task_id in current.get(state, []):
            if task_id in valid_set and task_id not in seen:
                ordered.append(task_id)
                seen.add(task_id)
        ordered.extend(sorted(task_id for task_id in valid if task_id not in seen))
        repaired[state] = ordered
    payload = {"version": 1, "manualOrder": repaired}
    atomic_write(order_file_path(backlog_root), json.dumps(payload, indent=2) + "\n")
    return repaired


def append_manual_order(backlog_root: Path, task_id: str, status: str) -> None:
    if status not in MANUAL_STATES:
        return
    order = read_manual_order(backlog_root)
    normalized = normalize_task_id(task_id)
    if normalized not in order[status]:
        order[status].append(normalized)
    atomic_write(order_file_path(backlog_root),
        json.dumps({"version": 1, "manualOrder": order}, indent=2) + "\n"
    )


def set_manual_order(backlog_root: Path, status: str, task_ids: list[str]) -> dict[str, list[str]]:
    if status not in MANUAL_STATES:
        raise ValueError(f"Status is not manually ordered: {status}")
    order = read_manual_order(backlog_root)
    order[status] = [normalize_task_id(value) for value in task_ids]
    atomic_write(order_file_path(backlog_root),
        json.dumps({"version": 1, "manualOrder": order}, indent=2) + "\n"
    )
    return repair_manual_order(backlog_root)


def _timestamp_key(record: TaskRecord) -> tuple[float, str]:
    field = TIMESTAMP_FIELDS.get(record.state, "updatedAt")
    raw = record.meta.get(field) or record.meta.get("updatedAt") or ""
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        stamp = float("-inf")
    return (-stamp, normalize_task_id(record.task_id))


def ordered_records(
    backlog_root: Path,
    records: list[TaskRecord],
    status: str,
    manual_order: dict[str, list[str]] | None = None,
) -> list[TaskRecord]:
    if status in MANUAL_STATES:
        order = manual_order or repair_manual_order(backlog_root, discover_tasks(backlog_root))
        positions = {task_id: index for index, task_id in enumerate(order[status])}
        return sorted(
            records,
            key=lambda record: (positions.get(normalize_task_id(record.task_id), 10**9), normalize_task_id(record.task_id)),
        )
    return sorted(records, key=_timestamp_key)


def task_label(record: TaskRecord) -> str:
    return f"{record.task_id}: {record.title}"


def rebuild_active_index(backlog_root: Path) -> None:
    ensure_task_indexes(backlog_root)
    records = discover_tasks(backlog_root)
    manual_order = repair_manual_order(backlog_root, records)
    lines = ["# Backlog", ""]
    for status in STATUS_ORDER:
        lines.extend([f"## {'WIP' if status == 'wip' else status.capitalize()}", ""])
        items = [record for record in records if record.state == status]
        for record in ordered_records(backlog_root, items, status, manual_order):
            lines.append(f"- [{task_label(record)}]({relative_link(backlog_root, record.task_file)})")
        lines.append("")
    atomic_write(active_backlog_path(backlog_root), "\n".join(lines))


def rebuild_indexes(backlog_root: Path) -> None:
    rebuild_active_index(backlog_root)


def append_history_entry(backlog_root: Path, state: str, record: TaskRecord) -> None:
    rebuild_active_index(backlog_root)


def apply_task_meta_defaults(meta: dict[str, str], task_id: str, status: str, timestamp: str) -> dict[str, str]:
    result = dict(meta)
    result["taskId"] = result.get("taskId") or task_id
    result["status"] = status
    result["createdAt"] = result.get("createdAt") or timestamp
    result["updatedAt"] = timestamp
    return result


def transition_task(
    backlog_root: Path,
    task_ref: str,
    to_state: str,
    *,
    review_after: str | None = None,
    reason: str | None = None,
    timestamp: str | None = None,
) -> TaskRecord:
    if to_state not in STATUS_ORDER:
        raise ValueError(f"Unsupported state: {to_state}")
    timestamp = timestamp or now_iso()
    record = resolve_task(backlog_root, task_ref)
    prior_state = record.state
    meta, body = read_markdown(record.task_file)
    meta = apply_task_meta_defaults(meta, record.task_id, to_state, timestamp)
    if to_state == "refined":
        meta["reviewedAt"] = meta.get("reviewedAt") or timestamp
    elif to_state == "planned":
        meta["plannedAt"] = meta.get("plannedAt") or timestamp
    elif to_state == "wip":
        meta["startedAt"] = meta.get("startedAt") or timestamp
    elif to_state == "blocked":
        if not reason:
            raise ValueError("Blocking a task requires a reason")
        meta.update({"blockedAt": timestamp, "blockedFrom": prior_state, "blockReason": reason})
        if review_after:
            meta["reviewAfter"] = review_after
    elif to_state == "archived":
        if not reason:
            raise ValueError("Archiving a task requires a reason")
        meta.update({"archivedAt": timestamp, "archivedFrom": prior_state, "archiveReason": reason})
    elif to_state == "completed":
        meta["completedAt"] = timestamp
    if to_state != "blocked":
        meta.pop("reviewAfter", None)
    write_markdown(record.task_file, meta, body, "task")
    if to_state in MANUAL_STATES:
        append_manual_order(backlog_root, record.task_id, to_state)
    rebuild_active_index(backlog_root)
    return resolve_task(backlog_root, record.task_id, {to_state})


def update_frontmatter(
    path: Path,
    *,
    kind: str | None = None,
    set_values: dict[str, str] | None = None,
    clear_keys: list[str] | None = None,
    refresh_updated_at: bool = False,
    timestamp: str | None = None,
) -> dict[str, str]:
    timestamp = timestamp or now_iso()
    meta, body = read_markdown(path)
    result = dict(meta)
    result.update(set_values or {})
    for key in clear_keys or []:
        result.pop(key, None)
    if refresh_updated_at and "updatedAt" in result:
        result["updatedAt"] = timestamp
    write_markdown(path, result, body, kind or detect_task_kind(path))
    return result


def extract_filename_task_id(path: Path) -> str | None:
    token = re.split(r"[.\-_ ]", strip_task_artifact_suffix(path.name), 1)[0]
    return token if LEGACY_TASK_ID_RE.fullmatch(token) else None


def strip_inline_metadata(body: str) -> tuple[str, str | None, str | None]:
    task_id = status = None
    kept = []
    for line in body.splitlines():
        match = INLINE_TASK_ID_RE.match(line.strip())
        if match:
            task_id = match.group(1).strip()
            continue
        match = INLINE_STATUS_RE.match(line.strip())
        if match:
            status = match.group(1).strip()
            continue
        kept.append(line)
    return "\n".join(kept).lstrip("\n") + ("\n" if body.endswith("\n") else ""), task_id, status


def derive_task_id(path: Path, meta: dict[str, str], body: str) -> str:
    if meta.get("taskId"):
        return str(meta["taskId"]).strip()
    _, inline, _ = strip_inline_metadata(body)
    if inline:
        return inline
    token = extract_filename_task_id(path)
    if not token:
        raise ValueError(f"Could not derive task ID for {path}")
    return token


def repo_root(cwd: Path | None = None) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd or Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def infer_oldest_timestamp(*paths: Path) -> str | None:
    return None


def infer_semantic_completion_timestamp(*paths: Path) -> str | None:
    return None
