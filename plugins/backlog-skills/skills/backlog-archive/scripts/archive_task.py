#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "backlog-core" / "scripts"
sys.path.insert(0, str(SHARED))

from backlog_lib import transition_task  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive a backlog task.")
    parser.add_argument("task_id")
    parser.add_argument("--backlog-root", default="docs/backlog")
    parser.add_argument("--reason", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    record = transition_task(Path(args.backlog_root), args.task_id, "archived", reason=args.reason)
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
