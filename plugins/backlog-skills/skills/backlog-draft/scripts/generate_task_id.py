#!/usr/bin/env python3

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path

TASK_ID_RE = re.compile(r"\b([a-z]{2}\d{2})\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate free AA11-style task IDs.")
    parser.add_argument(
        "--backlog-root",
        default="docs/backlog",
        help="Backlog root to scan for already used task IDs.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="How many unique free IDs to generate.",
    )
    return parser.parse_args()


def collect_used_ids(backlog_root: Path) -> set[str]:
    used: set[str] = set()
    if not backlog_root.exists():
        return used

    for path in backlog_root.rglob("*"):
        if not path.is_file():
            continue
        for match in TASK_ID_RE.findall(path.name):
            used.add(match.upper())
    return used


def build_pool(used: set[str]) -> list[str]:
    pool = [
        f"{first}{second}{number:02d}"
        for first in "abcdefghijklmnopqrstuvwxyz"
        for second in "abcdefghijklmnopqrstuvwxyz"
        for number in range(100)
        if f"{first}{second}{number:02d}".upper() not in used
    ]
    random.shuffle(pool)
    return [value.upper() for value in pool]


def main() -> int:
    args = parse_args()
    used = collect_used_ids(Path(args.backlog_root))
    pool = build_pool(used)

    if args.count < 1:
        raise SystemExit("--count must be >= 1")
    if len(pool) < args.count:
        raise SystemExit("Not enough free task IDs available.")

    for value in pool[: args.count]:
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
