#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "backlog-core" / "scripts"
sys.path.insert(0, str(SHARED))

from backlog_lib import resolve_task, transition_task  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Complete a backlog task.")
    parser.add_argument("task_id")
    parser.add_argument("--backlog-root", default="docs/backlog")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backlog_root = Path(args.backlog_root)
    resolve_task(backlog_root, args.task_id, {"wip"})

    record = transition_task(backlog_root, args.task_id, "completed")

    print(
        json.dumps(
            {
                "taskId": record.task_id,
                "state": record.state,
                "folder": str(record.folder),
                "taskFile": str(record.task_file),
                "draftTaskFile": str(record.draft_task_file) if record.draft_task_file else None,
                "refinedTaskFile": str(record.refined_task_file) if record.refined_task_file else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
