#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


REQUIRED_HEADINGS = (
    "## Historical Summary",
    "## Retrieval Anchors",
    "## Durable Outcome and Decisions",
    "## Validation and Limitations",
    "## Task Relationships",
    "### Supersedes",
    "### Superseded by",
    "### Related Tasks",
    "## Compression Provenance",
)
FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TASK_ID_RE = re.compile(r"^[A-Z0-9]{2,8}$")
TEXT_SUFFIXES = {
    ".csv",
    ".json",
    ".md",
    ".sql",
    ".txt",
    ".yaml",
    ".yml",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a proposed compressed backlog task.",
    )
    parser.add_argument("task_id")
    parser.add_argument("compressed_file", type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Original task directory used to verify provenance and reduction",
    )
    parser.add_argument(
        "--require-source-head",
        action="store_true",
        help="Require compressedFromCommit to equal the current HEAD",
    )
    return parser.parse_args()


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result, text[end + 5 :]


def parse_datetime(value: str) -> None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")


def commit_exists(repo_root: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.returncode == 0


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


def list_source_files(
    repo_root: Path,
    source_commit: str,
    source_dir: Path,
) -> tuple[list[str], str | None]:
    try:
        relative_dir = source_dir.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return [], "source directory is outside the repository"

    result = run_git(
        repo_root,
        ["ls-tree", "-r", "--name-only", source_commit, "--", relative_dir],
    )
    if result.returncode != 0:
        return [], "could not inspect source artifacts at compressedFromCommit"
    files = [line for line in result.stdout.splitlines() if line]
    if not files:
        return [], "compressedFromCommit contains no files for the source directory"
    return files, None


def count_git_words(repo_root: Path, source_commit: str, paths: list[str]) -> int:
    total = 0
    for source_path in paths:
        if Path(source_path).suffix.lower() not in TEXT_SUFFIXES:
            continue
        result = run_git(repo_root, ["show", f"{source_commit}:{source_path}"])
        if result.returncode == 0:
            total += len(result.stdout.split())
    return total


def validate_local_links(
    body: str,
    compressed_path: Path,
    repo_root: Path,
) -> list[str]:
    errors: list[str] = []
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", body)
    for raw_target in links:
        target = raw_target.strip().strip("<>")
        if (
            not target
            or target.startswith(("#", "http://", "https://", "mailto:"))
        ):
            continue
        target = unquote(target.split("#", 1)[0])
        if not target:
            continue
        resolved = (
            repo_root / target.lstrip("/")
            if target.startswith("/")
            else compressed_path.parent / target
        ).resolve()
        try:
            resolved.relative_to(repo_root)
        except ValueError:
            errors.append(f"local link escapes repository: {raw_target}")
            continue
        if not resolved.exists():
            errors.append(f"broken local link: {raw_target}")
    return errors


def main() -> int:
    args = parse_args()
    try:
        task_id = normalize_task_id(args.task_id)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    path = args.compressed_file.resolve()
    repo_root = args.repo_root.resolve()
    errors: list[str] = []

    if not path.is_file():
        print(f"Compressed file not found: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    if not meta:
        errors.append("missing or malformed YAML frontmatter")

    if meta.get("taskId", "").upper() != task_id:
        errors.append(f"taskId must be {task_id}")
    if not meta.get("status"):
        errors.append("missing status")
    if not meta.get("createdAt"):
        errors.append("missing createdAt")

    for field in ("createdAt", "compressedAt"):
        value = meta.get(field)
        if not value:
            errors.append(f"missing {field}")
            continue
        try:
            parse_datetime(value)
        except ValueError as error:
            errors.append(f"invalid {field}: {error}")

    source_commit = meta.get("compressedFromCommit", "")
    if not FULL_COMMIT_RE.fullmatch(source_commit):
        errors.append("compressedFromCommit must be a full 40-character commit ID")
    elif not commit_exists(repo_root, source_commit):
        errors.append("compressedFromCommit does not resolve to a commit")
    elif args.require_source_head:
        head = run_git(repo_root, ["rev-parse", "HEAD"])
        if head.returncode != 0 or head.stdout.strip() != source_commit:
            errors.append("compressedFromCommit must equal the current HEAD")

    if not re.search(r"^#\s+\S", body, flags=re.MULTILINE):
        errors.append("missing task title")
    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            errors.append(f"missing heading: {heading}")

    retrieval_start = body.find("## Retrieval Anchors")
    durable_start = body.find("## Durable Outcome and Decisions")
    retrieval = (
        body[retrieval_start:durable_start]
        if retrieval_start != -1 and durable_start > retrieval_start
        else ""
    )
    if task_id not in retrieval:
        errors.append("Retrieval Anchors must contain the task ID")
    retrieval_identifiers = re.findall(r"`([^`\n]+)`", retrieval)
    if len(set(retrieval_identifiers)) < 3:
        errors.append("Retrieval Anchors must contain at least three exact identifiers")

    sibling_link = re.compile(
        rf"\]\(\.?/?{re.escape(task_id)}\.(?:plan|notes|test|migration|"
        r"question|clarify|task\.(?:draft|refined))[^)]*\)",
        flags=re.IGNORECASE,
    )
    if sibling_link.search(body):
        errors.append("contains a link to a sibling artifact that compression will delete")
    errors.extend(validate_local_links(body, path, repo_root))

    relationships_start = body.find("## Task Relationships")
    provenance_boundary = body.find("## Compression Provenance")
    relationships = (
        body[relationships_start:provenance_boundary]
        if relationships_start != -1 and provenance_boundary > relationships_start
        else ""
    )
    relationship_bullets = [
        line.strip()
        for line in relationships.splitlines()
        if line.lstrip().startswith("- ")
    ]
    for bullet in relationship_bullets:
        if "](" not in bullet:
            errors.append("every relationship bullet must link a canonical task file")

    for label, target in re.findall(
        r"\[([^\]]+)\]\(([^)]+\.task\.md)\)",
        relationships,
    ):
        normalized_label = label.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{2,8}", normalized_label):
            errors.append(
                f"relationship link must include the full task title: {normalized_label}"
            )
        resolved_target = (path.parent / target).resolve()
        if resolved_target.is_file():
            target_text = resolved_target.read_text(encoding="utf-8")
            target_meta, target_body = parse_frontmatter(target_text)
            target_id = target_meta.get("taskId", "").upper()
            title_match = re.search(r"^#\s+(.+?)\s*$", target_body, flags=re.MULTILINE)
            if target_id and title_match:
                title = re.sub(
                    rf"\s*\[{re.escape(target_id)}\]\s*$",
                    "",
                    title_match.group(1),
                    flags=re.IGNORECASE,
                )
                expected_label = f"{target_id}: {title}"
                if normalized_label != expected_label:
                    errors.append(
                        "relationship label must match canonical ID and title: "
                        f"expected {expected_label!r}"
                    )

    provenance_start = body.find("## Compression Provenance")
    if provenance_start != -1:
        provenance = body[provenance_start:]
        if "compressedFromCommit" not in provenance:
            errors.append(
                "compression provenance must explain recovery from compressedFromCommit"
            )

    original_word_count = 0
    compressed_word_count = len(text.split())
    if args.source_dir and FULL_COMMIT_RE.fullmatch(source_commit):
        source_files, source_error = list_source_files(
            repo_root,
            source_commit,
            args.source_dir,
        )
        if source_error:
            errors.append(source_error)
        else:
            canonical_name = f"{task_id}.task.md"
            if not any(Path(source).name == canonical_name for source in source_files):
                errors.append(
                    f"compressedFromCommit does not contain canonical {canonical_name}"
                )
            provenance = body[provenance_start:] if provenance_start != -1 else ""
            for source in source_files:
                if Path(source).name not in provenance:
                    errors.append(
                        f"compression provenance omits source artifact: {Path(source).name}"
                    )
            original_word_count = count_git_words(
                repo_root,
                source_commit,
                source_files,
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if original_word_count:
        reduction = 100 * (1 - compressed_word_count / original_word_count)
        print(
            "Compression ratio: "
            f"{original_word_count} -> {compressed_word_count} words "
            f"({reduction:.1f}% reduction)"
        )
        if reduction < 40 or reduction > 95:
            print(
                "WARNING: reduction warrants manual retrieval review",
                file=sys.stderr,
            )

    print(f"Validated compressed backlog task {task_id}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
