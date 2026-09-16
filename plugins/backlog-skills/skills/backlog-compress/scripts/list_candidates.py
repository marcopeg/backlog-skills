#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path


ELIGIBLE_STATUSES = {"completed", "archived"}
CUTOFF_FIELDS = ("updatedAt", "archivedAt", "completedAt")
TASK_ID_RE = re.compile(r"^[A-Z0-9]{2,8}$")


@dataclass
class TaskCandidate:
    task_id: str
    status: str
    last_update: str
    age_days: int | None
    eligible: bool
    reason: str
    task_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List backlog tasks eligible for historical compression.",
    )
    parser.add_argument("task_id", nargs="?", help="Inspect one task ID")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include ineligible tasks (automatic for a specific task ID)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a confirmation table",
    )
    parser.add_argument(
        "--as-of",
        help="Override the current time with an ISO-8601 timestamp",
    )
    parser.add_argument(
        "--min-age-days",
        type=int,
        default=14,
        help="Required age in full days (default: 14)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--backlog-root",
        type=Path,
        default=Path("docs/backlog"),
        help="Backlog directory, relative to --repo-root when not absolute (default: docs/backlog)",
    )
    return parser.parse_args()


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}

    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key.strip()] = value
    return result


def parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def normalize_task_id(value: str) -> str:
    normalized = re.sub(r"[-_\s]+", "", value.strip().upper())
    if not TASK_ID_RE.fullmatch(normalized):
        raise ValueError(f"Invalid task ID: {value}")
    return normalized


def find_task_files(tasks_root: Path) -> list[Path]:
    return sorted(
        path
        for path in tasks_root.glob("*/*.task.md")
        if ".history." not in path.name
    )


def select_task_file(task_files: list[Path], task_id: str) -> Path:
    normalized = normalize_task_id(task_id)

    matches = []
    for path in task_files:
        meta = parse_frontmatter(path)
        file_id = meta.get("taskId", path.name.removesuffix(".task.md")).upper()
        if file_id == normalized:
            matches.append(path)

    if not matches:
        raise ValueError(f"Task not found: {normalized}")
    if len(matches) > 1:
        raise ValueError(f"Multiple canonical task files found for: {normalized}")
    return matches[0]


def inspect_task(path: Path, now: datetime, min_age_days: int) -> TaskCandidate:
    meta = parse_frontmatter(path)
    task_id = meta.get("taskId", path.name.removesuffix(".task.md")).upper()
    status = meta.get("status", "unknown").lower()

    parsed_dates: list[tuple[datetime, str]] = []
    invalid_dates: list[str] = []
    for field in CUTOFF_FIELDS:
        value = meta.get(field)
        if not value:
            continue
        try:
            parsed_dates.append((parse_datetime(value), value))
        except ValueError:
            invalid_dates.append(field)

    last_update = ""
    age_days: int | None = None
    if parsed_dates:
        cutoff, last_update = max(parsed_dates, key=lambda item: item[0])
        age_days = (now - cutoff.astimezone(now.tzinfo)) // timedelta(days=1)

    reasons = []
    if status not in ELIGIBLE_STATUSES:
        reasons.append(f"status is {status}, not completed or archived")
    if meta.get("compressedAt"):
        reasons.append("already compressed")
    if not parsed_dates:
        detail = f" ({', '.join(invalid_dates)} malformed)" if invalid_dates else ""
        reasons.append(f"no parseable update/archive/completion date{detail}")
    elif age_days is not None and age_days < min_age_days:
        reasons.append(f"only {age_days} full days old")

    eligible = not reasons
    return TaskCandidate(
        task_id=task_id,
        status=status,
        last_update=last_update or "unknown",
        age_days=age_days,
        eligible=eligible,
        reason="eligible" if eligible else "; ".join(reasons),
        task_file=str(path),
    )


def render_table(candidates: list[TaskCandidate], include_reason: bool) -> str:
    headers = ["ID", "Status", "Last update"]
    if include_reason:
        headers.append("Assessment")

    rows = []
    for candidate in candidates:
        row = [candidate.task_id, candidate.status, candidate.last_update]
        if include_reason:
            row.append(candidate.reason)
        rows.append(row)

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    separator = "  ".join("-" * width for width in widths)
    lines = [
        "  ".join(
            header.ljust(widths[index]) for index, header in enumerate(headers)
        ),
        separator,
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.min_age_days < 0:
        print("--min-age-days must be non-negative", file=sys.stderr)
        return 2

    try:
        now = parse_datetime(args.as_of) if args.as_of else datetime.now().astimezone()
    except ValueError as error:
        print(f"Invalid --as-of timestamp: {error}", file=sys.stderr)
        return 2

    repo_root = args.repo_root.resolve()
    backlog_root = args.backlog_root
    if not backlog_root.is_absolute():
        backlog_root = repo_root / backlog_root
    tasks_root = backlog_root.resolve() / "tasks"
    if not tasks_root.is_dir():
        print(f"Backlog task directory not found: {tasks_root}", file=sys.stderr)
        return 2

    task_files = find_task_files(tasks_root)
    try:
        if args.task_id:
            task_files = [select_task_file(task_files, args.task_id)]
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    inspected = [
        inspect_task(path, now, args.min_age_days)
        for path in task_files
    ]
    include_ineligible = args.all or bool(args.task_id)
    candidates = (
        inspected
        if include_ineligible
        else [candidate for candidate in inspected if candidate.eligible]
    )

    if args.json:
        print(json.dumps([asdict(candidate) for candidate in candidates], indent=2))
    elif not candidates:
        print("No eligible backlog tasks.")
    else:
        print(render_table(candidates, include_reason=include_ineligible))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
