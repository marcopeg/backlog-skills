#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SHARED = Path(__file__).resolve().parents[2] / "backlog-core" / "scripts"
sys.path.insert(0, str(SHARED))

from backlog_lib import (  # noqa: E402
    normalize_task_id,
    now_iso,
    append_manual_order,
    rebuild_active_index,
    relative_link,
    slugify,
    state_dir,
    task_filename,
    write_markdown,
)
from generate_task_id import build_pool, collect_used_ids  # noqa: E402

MISSING = "information is missing"

SECTION_NAMES = [
    "Elevator's Pitch",
    "Business Gain",
    "Current State",
    "Desired State",
    "Definition of Success",
    "Additional Context",
    "Assumptions",
    "Constraints",
    "Acceptance Criteria",
    "Dos",
    "Don'ts",
    "Open Questions",
    "Related to",
]

SECTION_ALIASES = {
    "title": "title",
    "group": "group",
    "pitch": "Elevator's Pitch",
    "elevatorpitch": "Elevator's Pitch",
    "elevatorspitch": "Elevator's Pitch",
    "businessgain": "Business Gain",
    "businessvalue": "Business Gain",
    "currentstate": "Current State",
    "desiredstate": "Desired State",
    "definitionofsuccess": "Definition of Success",
    "success": "Definition of Success",
    "additionalcontext": "Additional Context",
    "context": "Additional Context",
    "assumptions": "Assumptions",
    "constraints": "Constraints",
    "acceptancecriteria": "Acceptance Criteria",
    "criteria": "Acceptance Criteria",
    "dos": "Dos",
    "do": "Dos",
    "donts": "Don'ts",
    "dont": "Don'ts",
    "donots": "Don'ts",
    "openquestions": "Open Questions",
    "questions": "Open Questions",
    "relatedto": "Related to",
    "related": "Related to",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a draft backlog task.")
    parser.add_argument(
        "--backlog-root",
        default="docs/backlog",
        help="Backlog root where the draft task should be created.",
    )
    parser.add_argument(
        "--input",
        help="JSON input file. Use '-' to read JSON from stdin.",
    )
    parser.add_argument("--title", help="Task title. Overrides JSON title.")
    parser.add_argument("--group", help="Optional task group. Overrides JSON group.")
    parser.add_argument("--task-id", help="Optional AA11-style task ID, mainly for tests.")
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Create the draft file without rebuilding BACKLOG.md.",
    )
    return parser.parse_args()


def normalize_key(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def read_input(args: argparse.Namespace) -> dict[str, Any]:
    raw = ""
    if args.input == "-":
        raw = sys.stdin.read()
    elif args.input:
        raw = Path(args.input).read_text()
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()

    raw = raw.strip()
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON input: {error}") from error

    if not isinstance(data, dict):
        raise SystemExit("JSON input must be an object.")
    return data


def markdown_value(value: Any) -> str:
    if value is None:
        return MISSING
    if isinstance(value, str):
        content = value.strip()
        return content or MISSING
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            rendered = markdown_value(item)
            if rendered == MISSING:
                continue
            if "\n" in rendered:
                lines.append(rendered)
            elif rendered.startswith(("- ", "- [ ] ", "- [x] ")):
                lines.append(rendered)
            else:
                lines.append(f"- {rendered}")
        return "\n".join(lines) if lines else MISSING
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            rendered = markdown_value(item)
            if rendered == MISSING:
                continue
            lines.append(f"- {key}: {rendered}")
        return "\n".join(lines) if lines else MISSING
    return str(value).strip() or MISSING


def section_from_payload(data: dict[str, Any], section_name: str) -> str:
    sections = data.get("sections")
    if isinstance(sections, dict):
        for key, value in sections.items():
            if SECTION_ALIASES.get(normalize_key(str(key))) == section_name:
                return markdown_value(value)
            if str(key).strip().lower() == section_name.lower():
                return markdown_value(value)

    for key, value in data.items():
        if SECTION_ALIASES.get(normalize_key(str(key))) == section_name:
            return markdown_value(value)
        if str(key).strip().lower() == section_name.lower():
            return markdown_value(value)

    return MISSING


def resolve_task_id(backlog_root: Path, requested_task_id: str | None) -> str:
    used_ids = collect_used_ids(backlog_root)
    if requested_task_id:
        task_id = normalize_task_id(requested_task_id)
        if task_id in used_ids:
            raise SystemExit(f"Task ID already exists: {task_id}")
        return task_id

    pool = build_pool(used_ids)
    if not pool:
        raise SystemExit("Not enough free task IDs available.")
    return pool[0]


def render_body(title: str, data: dict[str, Any]) -> str:
    parts = [f"# {title.strip()}", ""]
    for section_name in SECTION_NAMES:
        parts.extend(
            [
                f"## {section_name}",
                "",
                section_from_payload(data, section_name),
                "",
            ]
        )
    return "\n".join(parts).rstrip() + "\n"


def count_active_links(backlog_path: Path, draft_file: Path) -> int:
    if not backlog_path.exists():
        return 0
    target = relative_link(backlog_path.parent, draft_file)
    return backlog_path.read_text().count(f"]({target})")


def main() -> int:
    args = parse_args()
    data = read_input(args)

    title = (args.title or data.get("title") or "").strip()
    if not title:
        raise SystemExit("A task title is required.")

    group = (args.group or data.get("group") or "").strip()
    backlog_root = Path(args.backlog_root)
    task_id = resolve_task_id(backlog_root, args.task_id)
    timestamp = now_iso()

    task_folder = state_dir(backlog_root, "draft") / f"{task_id}-{slugify(title)}"
    task_path = task_folder / task_filename(task_id)
    if task_folder.exists():
        raise SystemExit(f"Task folder already exists: {task_folder}")

    task_folder.mkdir(parents=True, exist_ok=False)
    meta = {
        "taskId": task_id,
        "status": "draft",
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }
    if group:
        meta["group"] = group

    write_markdown(task_path, meta, render_body(title, data), "task")

    if not args.skip_index:
        append_manual_order(backlog_root, task_id, "draft")
        rebuild_active_index(backlog_root)

    backlog_path = backlog_root / "BACKLOG.md"
    link_count = count_active_links(backlog_path, task_path)
    if not args.skip_index and link_count != 1:
        raise SystemExit(
            f"Expected exactly one active backlog link for {task_id}, found {link_count}."
        )

    output = {
        "taskId": task_id,
        "title": title,
        "status": "draft",
        "taskFolder": str(task_folder),
        "taskPath": str(task_path),
        "absoluteTaskPath": str(task_path.resolve()),
        "draftPath": str(task_path),
        "absoluteDraftPath": str(task_path.resolve()),
        "backlogPath": str(backlog_path),
        "backlogEntry": relative_link(backlog_path.parent, task_path),
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
