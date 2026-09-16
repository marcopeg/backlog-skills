#!/usr/bin/env python3
"""Install the complete sibling skill bundle without overwriting existing files."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--project', type=Path, help='Target project; installs in .agents/skills')
    target.add_argument('--destination', type=Path, help='Explicit skills directory, including global installs')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    destination = (args.project.expanduser() / '.agents/skills' if args.project else args.destination.expanduser()).resolve()
    source = Path(__file__).resolve().parents[1] / 'plugins/backlog-skills/skills'
    skills = sorted(source.glob('backlog-*'))
    conflicts = [destination / skill.name for skill in skills if (destination / skill.name).exists() or (destination / skill.name).is_symlink()]
    if conflicts:
        parser.exit(1, 'No files copied. Existing skill folders:\n' + '\n'.join(map(str, conflicts)) + '\nChoose a fresh destination or move your existing copies aside.\n')
    for skill in skills:
        print(f'{skill.name} -> {destination / skill.name}')
    if not args.dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            shutil.copytree(skill, destination / skill.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    print(f'{"Would install" if args.dry_run else "Installed"} {len(skills)} skills.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
