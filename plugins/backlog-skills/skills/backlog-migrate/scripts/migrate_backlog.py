#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "backlog-core" / "scripts"
sys.path.insert(0, str(SHARED))

from backlog_lib import (  # noqa: E402
    STATUS_ORDER,
    derive_task_id,
    dump_frontmatter,
    extract_title,
    normalize_task_id,
    now_iso,
    parse_frontmatter,
    rebuild_active_index,
    repair_manual_order,
    slugify,
    task_filename,
    tasks_dir,
)

LEGACY_STATUS_MAP = {
    "draft": "draft",
    "todo": "todo",
    "future": "someday",
    "someday": "someday",
    "refining": "refining",
    "refined": "refined",
    "ready": "planned",
    "planned": "planned",
    "wip": "wip",
    "working": "wip",
    "blocked": "blocked",
    "archive": "archived",
    "archived": "archived",
    "complete": "completed",
    "completed": "completed",
}
LIFECYCLE_FIELDS = {
    "draft": "updatedAt",
    "todo": "updatedAt",
    "someday": "updatedAt",
    "refining": "updatedAt",
    "refined": "reviewedAt",
    "planned": "plannedAt",
    "wip": "startedAt",
    "blocked": "blockedAt",
    "archived": "archivedAt",
    "completed": "completedAt",
}
THREE_WEEKS = timedelta(days=21)


@dataclass
class Candidate:
    path: Path
    folder: Path
    folder_status: str | None
    task_id: str
    meta: dict[str, str]
    body: str
    canonical: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate a backlog to stable metadata-driven storage.")
    parser.add_argument("--backlog-root", default="docs/backlog")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-prefix", default="migration-audit")
    parser.add_argument("--now", help="ISO timestamp used for deterministic tests.")
    return parser.parse_args()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hash_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    } if root.exists() else {}


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def candidate_time(candidate: Candidate) -> datetime:
    values = [
        parse_time(candidate.meta.get(key))
        for key in ("completedAt", "archivedAt", "blockedAt", "startedAt", "plannedAt", "reviewedAt", "updatedAt", "createdAt")
    ]
    valid = [value for value in values if value is not None]
    if valid:
        return max(valid)
    return datetime.fromtimestamp(candidate.path.stat().st_mtime, tz=timezone.utc)


def effective_status(candidate: Candidate) -> tuple[str, list[str]]:
    warnings: list[str] = []
    raw = str(candidate.meta.get("status") or "").strip().lower()
    status = LEGACY_STATUS_MAP.get(raw)
    if status:
        if candidate.folder_status and status != candidate.folder_status:
            warnings.append(
                f"canonical frontmatter status {status} overrides legacy folder status {candidate.folder_status}"
            )
        return status, warnings
    if candidate.folder_status:
        warnings.append("missing/invalid frontmatter status; inferred from legacy folder")
        return candidate.folder_status, warnings
    warnings.append("missing/invalid status; defaulted conservatively to draft")
    return "draft", warnings


def score(candidate: Candidate) -> tuple[int, float, int, str]:
    status, _ = effective_status(candidate)
    stamp = candidate_time(candidate).timestamp()
    return (STATUS_ORDER.index(status), stamp, 1 if candidate.canonical else 0, str(candidate.path))


def title_similarity(candidates: list[Candidate]) -> bool:
    titles = {
        re.sub(r"[^a-z0-9]+", "", extract_title(candidate.body, "").lower())
        for candidate in candidates
        if extract_title(candidate.body, "")
    }
    return len(titles) <= 1


def confidence(candidates: list[Candidate], now: datetime) -> tuple[str, str]:
    oldest = min(candidate_time(candidate) for candidate in candidates)
    if now - oldest > THREE_WEEKS:
        return "automatic-aged", "conflict is older than three weeks"
    if title_similarity(candidates):
        return "high", "candidate titles agree"
    if len(candidates) == 1:
        return "high", "single task candidate"
    return "conservative", "newer candidates have differing semantic titles; all variants preserved"


def discover_candidates(root: Path) -> tuple[dict[str, list[Candidate]], list[dict[str, str]]]:
    groups: dict[str, list[Candidate]] = {}
    unresolved: list[dict[str, str]] = []
    task_root = tasks_dir(root).resolve()
    legacy_roots = [
        path for path in root.iterdir()
        if path.is_dir() and path.name.lower() in LEGACY_STATUS_MAP and path.resolve() != task_root
    ] if root.exists() else []
    folders: list[tuple[Path, str | None]] = []
    if task_root.is_dir():
        folders.extend((folder, None) for folder in task_root.iterdir() if folder.is_dir())
    for status_root in legacy_roots:
        for loose in sorted(status_root.iterdir()):
            if not loose.is_dir():
                unresolved.append({"path": str(loose), "reason": "loose legacy file; move into a task folder before migration"})
        status = LEGACY_STATUS_MAP[status_root.name.lower()]
        folders.extend((folder, status) for folder in status_root.iterdir() if folder.is_dir())

    for folder, folder_status in sorted(folders, key=lambda item: str(item[0])):
        for nested in sorted(folder.iterdir()):
            if nested.is_dir() or nested.is_symlink():
                unresolved.append({"path": str(nested), "reason": "nested directory or symlink requires manual migration; source preserved"})
        markdown = sorted(path for path in folder.glob("*.md") if path.is_file())
        task_like = [path for path in markdown if ".task" in path.name]
        candidates = task_like or markdown[:1]
        if not candidates:
            unresolved.append({"path": str(folder), "reason": "folder contains no Markdown task candidate"})
            continue
        for path in candidates:
            text = path.read_text()
            meta, body = parse_frontmatter(text)
            try:
                task_id = normalize_task_id(derive_task_id(path, meta, body))
            except ValueError as error:
                unresolved.append({"path": str(path), "reason": str(error)})
                continue
            groups.setdefault(task_id, []).append(
                Candidate(
                    path=path,
                    folder=folder,
                    folder_status=folder_status,
                    task_id=task_id,
                    meta=meta,
                    body=body,
                    canonical=path.name == task_filename(task_id),
                )
            )
    return groups, unresolved


def unique_history_name(destination: Path, candidate: Candidate, used: set[str]) -> str:
    source = candidate.folder.parent.name if candidate.folder_status else "stable"
    stem = re.sub(r"[^a-z0-9.-]+", "-", candidate.path.stem.lower()).strip("-")
    stem = stem.replace(".task", "-task")
    base = f"{candidate.task_id}.history.{source}.{stem}.md"
    name = base
    counter = 2
    while name in used or (destination / name).exists():
        name = f"{base[:-3]}.{counter}.md"
        counter += 1
    used.add(name)
    return name


def copy_all_content(
    candidates: list[Candidate],
    chosen: Candidate,
    destination: Path,
    dry_run: bool,
) -> list[dict[str, str]]:
    preserved: list[dict[str, str]] = []
    used: set[str] = {task_filename(chosen.task_id)}
    seen_sources: set[Path] = set()
    for candidate in candidates:
        for source in sorted(candidate.folder.iterdir()):
            if not source.is_file() or source in seen_sources:
                continue
            seen_sources.add(source)
            if source == chosen.path:
                continue
            desired = source.name
            if desired == task_filename(chosen.task_id) or desired in used or (destination / desired).exists():
                desired = unique_history_name(destination, candidate, used)
            else:
                used.add(desired)
            target = destination / desired
            preserved.append({"source": str(source), "target": str(target)})
            if dry_run:
                continue
            if source.suffix.lower() == ".md":
                _, body = parse_frontmatter(source.read_text())
                target.write_text(body.lstrip("\n"))
            else:
                shutil.copy2(source, target)
    return preserved


def migrate_group(
    root: Path,
    task_id: str,
    candidates: list[Candidate],
    now: datetime,
    dry_run: bool,
) -> dict[str, object]:
    chosen = max(candidates, key=score)
    status, warnings = effective_status(chosen)
    confidence_name, confidence_reason = confidence(candidates, now)
    title = extract_title(chosen.body, chosen.folder.name)
    stable_candidates = [
        candidate
        for candidate in candidates
        if candidate.folder.parent.resolve() == tasks_dir(root).resolve()
    ]
    destination = (
        max(stable_candidates, key=score).folder
        if stable_candidates
        else tasks_dir(root) / f"{task_id}-{slugify(title)}"
    )
    meta = dict(chosen.meta)
    timestamp = now.isoformat()
    meta.update(
        {
            "taskId": task_id,
            "status": status,
            "createdAt": meta.get("createdAt") or candidate_time(chosen).isoformat(),
            "updatedAt": meta.get("updatedAt") or timestamp,
        }
    )
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
    preserved = copy_all_content(candidates, chosen, destination, dry_run)
    if not dry_run:
        (destination / task_filename(task_id)).write_text(
            dump_frontmatter(meta, [
                "taskId", "status", "createdAt", "updatedAt", "group", "reviewedAt",
                "plannedAt", "startedAt", "blockedAt", "blockedFrom", "blockReason",
                "archivedAt", "archivedFrom", "archiveReason", "completedAt", "reviewAfter",
            ]) + chosen.body.lstrip("\n")
        )
    return {
        "taskId": task_id,
        "status": status,
        "destination": str(destination),
        "chosen": str(chosen.path),
        "candidateCount": len(candidates),
        "confidence": confidence_name,
        "confidenceReason": confidence_reason,
        "warnings": sorted(
            set(
                warnings
                + [
                    warning
                    for candidate in candidates
                    for warning in effective_status(candidate)[1]
                ]
            )
        ),
        "preserved": preserved,
    }


def write_audit(root: Path, prefix: str, report: dict[str, object]) -> None:
    (root / f"{prefix}.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# Backlog migration audit", "",
        f"- Dry run: `{str(report['dryRun']).lower()}`",
        f"- Reconciled tasks: {len(report['tasks'])}",
        f"- Unresolved items: {len(report['unresolved'])}", "",
        "## Reconciliations", "",
    ]
    for item in report["tasks"]:
        lines.append(
            f"- **{item['taskId']}** → `{item['status']}` "
            f"({item['confidence']}: {item['confidenceReason']}); "
            f"{item['candidateCount']} candidate(s), {len(item['preserved'])} preserved file(s)."
        )
    lines.extend(["", "## Unresolved", ""])
    for item in report["unresolved"]:
        lines.append(f"- `{item['path']}`: {item['reason']}")
    (root / f"{prefix}.md").write_text("\n".join(lines) + "\n")


def remove_legacy_layout(root: Path) -> list[str]:
    removed: list[str] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.lower() not in LEGACY_STATUS_MAP:
            continue
        if path.resolve() == tasks_dir(root).resolve():
            continue
        shutil.rmtree(path)
        removed.append(str(path))
    for name in ("COMPLETED.md", "ARCHIVED.md"):
        path = root / name
        if path.exists():
            path.unlink()
            removed.append(str(path))
    for path in root.glob("BACKLOG_*.md"):
        path.unlink()
        removed.append(str(path))
    return removed


def main() -> int:
    args = parse_args()
    root = Path(args.backlog_root)
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        raise SystemExit("--now must be a valid ISO timestamp")
    before = manifest(root)
    groups, unresolved = discover_candidates(root)
    if unresolved and not args.dry_run:
        report: dict[str, object] = {
            "version": 2,
            "policy": "automation-first-age-confidence",
            "backlogRoot": str(root),
            "dryRun": False,
            "generatedAt": now.isoformat(),
            "beforeManifest": before,
            "afterManifest": before,
            "tasks": [],
            "unresolved": unresolved,
            "removedLegacy": [],
            "abortedBeforeWrite": True,
        }
        write_audit(root, args.audit_prefix, report)
        print(json.dumps(report, indent=2))
        return 2
    reconciled = [
        migrate_group(root, task_id, candidates, now, args.dry_run)
        for task_id, candidates in sorted(groups.items())
    ]
    removed: list[str] = []
    if not args.dry_run:
        repair_manual_order(root)
        rebuild_active_index(root)
        removed = remove_legacy_layout(root)
        rebuild_active_index(root)
    after = manifest(root)
    report: dict[str, object] = {
        "version": 2,
        "policy": "automation-first-age-confidence",
        "backlogRoot": str(root),
        "dryRun": args.dry_run,
        "generatedAt": now.isoformat(),
        "beforeManifest": before,
        "afterManifest": after,
        "tasks": reconciled,
        "unresolved": unresolved,
        "removedLegacy": removed,
    }
    if not args.dry_run:
        write_audit(root, args.audit_prefix, report)
    print(json.dumps(report, indent=2))
    return 2 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
