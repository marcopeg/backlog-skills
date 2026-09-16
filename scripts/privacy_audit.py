#!/usr/bin/env python3
"""Reject common private details before publishing this source tree."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


EXCLUDED_DIRECTORIES = {".git", "__pycache__", ".venv", "node_modules"}
TEXT_EXTENSIONS = {
    ".json", ".md", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml",
}
PATTERNS = {
    "email address": re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"),
    "user-specific path": re.compile(r"(?:^|[\s\"'])/(?:Users|home)/[^/\s\"']+|[A-Za-z]:\\Users\\[^\\\s\"']+"),
    "private key block": re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "likely access token": re.compile(
        r"(?:gh[pousr]_|github" + r"_pat_|sk-)[A-Za-z0-9_-]{16,}"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Directory to inspect (default: repository root)",
    )
    return parser.parse_args()


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def main() -> int:
    root = parse_args().root.resolve()
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if any(part in EXCLUDED_DIRECTORIES for part in path.parts):
            continue
        if not path.is_file() or not is_text_file(path):
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path.relative_to(root)}: {label}")

    if findings:
        print("Privacy audit failed:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Privacy audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
