---
name: backlog-doctor
description: Verifies and repairs stable backlog task storage, canonical metadata sidecars, manual ordering, and the generated full index.
---

# Backlog Doctor

## Running the helpers

Run commands from the target project's root. Before running a helper, resolve
`<skills-root>` to the absolute parent directory of this loaded skill folder
(the directory containing all 13 `backlog-*` folders). Substitute that actual
path in the quoted command examples; `<skills-root>` is a documentation
placeholder, not an environment variable. This works for project/global skills,
symlink installs, and plugin caches. Never assume a repository-relative install.

Keep the full bundle together: helpers import their sibling `backlog-core`.
Backlog data belongs to the target project, never the skill/plugin cache.
When a workflow names another skill, resolve it within this same bundle; plugin
installations may prefix its name with `backlog-skills:`.

Follow existing user authorization when chaining workflows. Ask for missing
decisions; do not repeat approvals the user already gave.

Use after migration or whenever `docs/backlog/tasks/`, `order.json`, or
`BACKLOG.md` may have drifted.

1. Run `python3 "<skills-root>/backlog-doctor/scripts/doctor_backlog.py" --dry-run`.
2. Inspect all issues. A nonzero dry-run result means repair or investigation is
   still needed.
3. Run without `--dry-run` only when repair is authorized.
4. Run dry-run again and verify a deterministic second index rebuild.

Every task folder must live directly under `docs/backlog/tasks/` and contain one
canonical `<taskid>.task.md`. Supported statuses are draft, todo, someday,
refining, refined, planned, wip, blocked, archived, and completed. The doctor
never moves folders for status changes. It strips frontmatter from noncanonical
Markdown sidecars, repairs manual-order membership, and regenerates the single
full `BACKLOG.md`.
