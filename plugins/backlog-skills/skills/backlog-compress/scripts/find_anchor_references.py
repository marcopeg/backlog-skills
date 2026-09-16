#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


TASK_ID_RE = re.compile(r"^[A-Z0-9]{2,8}$")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
PATH_RE = re.compile(
    r"(?:@?/)?[A-Za-z0-9_.{}\[\]<>-]+(?:/[A-Za-z0-9_.{}\[\]<>*-]+)+"
)
FILE_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_.-]*\.[A-Za-z0-9]{1,12}\b")
MAX_TASK_FREQUENCY = 12
TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".md",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find backlog tasks sharing concrete anchors with a task.",
    )
    parser.add_argument("task_id")
    parser.add_argument(
        "--source-commit",
        help="Read the source task artifacts from this commit",
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


def normalize_task_id(value: str) -> str:
    normalized = re.sub(r"[-_\s]+", "", value.strip().upper())
    if not TASK_ID_RE.fullmatch(normalized):
        raise ValueError(f"Invalid task ID: {value}")
    return normalized


def run_git(repo_root: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )


def parse_task_id(path: Path) -> str:
    return path.name.split(".", 1)[0].upper()


def find_task_dir(tasks_root: Path, task_id: str) -> Path:
    matches = [
        path.parent
        for path in tasks_root.glob("*/*.task.md")
        if parse_task_id(path) == task_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one canonical task for {task_id}, found {len(matches)}"
        )
    return matches[0]


def read_source_texts(
    repo_root: Path,
    task_dir: Path,
    source_commit: str | None,
) -> list[str]:
    if not source_commit:
        return [
            path.read_text(encoding="utf-8", errors="replace")
            for path in task_dir.rglob("*")
            if path.is_file()
        ]

    relative_dir = task_dir.relative_to(repo_root).as_posix()
    listing = run_git(
        repo_root,
        ["ls-tree", "-r", "--name-only", source_commit, "--", relative_dir],
    )
    if listing.returncode != 0:
        raise ValueError("Could not list source task artifacts from Git")

    texts = []
    for source_path in listing.stdout.splitlines():
        if Path(source_path).suffix.lower() not in TEXT_SUFFIXES:
            continue
        content = run_git(repo_root, ["show", f"{source_commit}:{source_path}"])
        if content.returncode == 0:
            texts.append(content.stdout)
    return texts


def normalize_anchor(value: str) -> str:
    value = value.strip().strip("\"'")
    value = value.removeprefix("@/")
    return value.lstrip("/")


def extract_anchors(texts: list[str]) -> set[str]:
    anchors: set[str] = set()
    for text in texts:
        candidates = [
            *INLINE_CODE_RE.findall(text),
            *PATH_RE.findall(text),
            *FILE_RE.findall(text),
        ]
        for candidate in candidates:
            normalized = normalize_anchor(candidate)
            if len(normalized) < 5 or any(character.isspace() for character in normalized):
                continue
            if "/" not in normalized:
                continue
            if Path(normalized).suffix.lower() not in TEXT_SUFFIXES:
                continue
            anchors.add(normalized)
    return anchors


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    backlog_root = args.backlog_root
    if not backlog_root.is_absolute():
        backlog_root = repo_root / backlog_root
    tasks_root = backlog_root.resolve() / "tasks"
    try:
        task_id = normalize_task_id(args.task_id)
        task_dir = find_task_dir(tasks_root, task_id)
        source_texts = read_source_texts(
            repo_root,
            task_dir,
            args.source_commit,
        )
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    anchors = extract_anchors(source_texts)
    anchor_tasks: dict[str, set[str]] = defaultdict(set)
    for path in tasks_root.glob("*/*.md"):
        candidate_id = parse_task_id(path)
        if candidate_id == task_id:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for anchor in anchors:
            if anchor in text:
                anchor_tasks[anchor].add(candidate_id)

    matches: dict[str, set[str]] = defaultdict(set)
    for anchor, candidate_ids in anchor_tasks.items():
        if len(candidate_ids) > MAX_TASK_FREQUENCY:
            continue
        for candidate_id in candidate_ids:
            matches[candidate_id].add(anchor)

    if not matches:
        print("No anchor-sharing backlog tasks found.")
        return 0

    print("Task  Matching anchors")
    print("----  ----------------")
    for candidate_id in sorted(matches):
        displayed = sorted(matches[candidate_id], key=lambda value: (len(value), value))
        print(f"{candidate_id:<4}  {', '.join(displayed[:8])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
