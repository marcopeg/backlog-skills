#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import shutil
import tempfile
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "backlog-core" / "scripts"
sys.path.insert(0, str(SHARED))

from backlog_lib import (  # noqa: E402
    STATUS_ORDER,
    discover_tasks,
    read_markdown,
    rebuild_active_index,
    repair_manual_order,
    tasks_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify and repair a stable-layout backlog.")
    parser.add_argument("--backlog-root", default="docs/backlog")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.backlog_root)
    issues: list[dict[str, object]] = []
    task_root = tasks_dir(root)

    if not task_root.is_dir():
        issues.append({"action": "missing-tasks-directory", "path": str(task_root)})

    if task_root.is_dir():
        for folder in sorted(task_root.iterdir()):
            if folder.is_dir() and not list(folder.glob("*.task.md")):
                issues.append({"action": "missing-canonical-task", "path": str(folder)})
    records = discover_tasks(root) if task_root.is_dir() else []
    with tempfile.TemporaryDirectory(prefix="backlog-doctor-") as temporary:
        expected = Path(temporary) / "backlog"
        if root.exists():
            shutil.copytree(root, expected)
        rebuild_active_index(expected)
        for name in ("BACKLOG.md", "order.json"):
            current = root / name
            if not current.exists() or current.read_bytes() != (expected / name).read_bytes():
                issues.append({"action": "stale-generated-file", "path": str(current)})
    for record in records:
        if record.state not in STATUS_ORDER:
            issues.append(
                {"taskId": record.task_id, "action": "invalid-status", "value": record.state}
            )
        for path in sorted(record.folder.glob("*.md")):
            if path == record.task_file:
                continue
            meta, body = read_markdown(path)
            if not meta:
                continue
            issues.append(
                {"taskId": record.task_id, "action": "strip-sidecar-frontmatter", "path": str(path)}
            )
            if not args.dry_run:
                path.write_text(body.lstrip("\n"))

    if not args.dry_run:
        repair_manual_order(root, records)
        rebuild_active_index(root)

    print(
        json.dumps(
            {
                "backlogRoot": str(root),
                "layout": "stable-tasks",
                "dryRun": args.dry_run,
                "taskCount": len(records),
                "issueCount": len(issues),
                "issues": issues,
                "indexes": "not-changed" if args.dry_run else "rebuilt",
            },
            indent=2,
        )
    )
    unresolved = any(issue["action"] == "missing-canonical-task" for issue in issues)
    return 1 if unresolved or (args.dry_run and issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
