#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "backlog-core" / "scripts"
sys.path.insert(0, str(SHARED))

from backlog_lib import transition_task  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Block a backlog task with required context.")
    parser.add_argument("task_id")
    parser.add_argument("--backlog-root", default="docs/backlog")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--review-after")
    args = parser.parse_args()
    record = transition_task(
        Path(args.backlog_root),
        args.task_id,
        "blocked",
        reason=args.reason,
        review_after=args.review_after,
    )
    print(json.dumps({
        "taskId": record.task_id,
        "state": record.state,
        "folder": str(record.folder),
        "taskFile": str(record.task_file),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
