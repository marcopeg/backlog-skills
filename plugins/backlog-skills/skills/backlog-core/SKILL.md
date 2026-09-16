---
name: backlog-core
description: Shared deterministic tooling for stable backlog task storage, metadata transitions, manual ordering, indexing, validation, and migration support.
---

# Backlog Core

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

Use this internal skill through the user-facing backlog workflows. The permanent
contract is `docs/backlog/tasks/<task-folder>/<taskid>.task.md`: canonical task
frontmatter owns lifecycle status and transitions never move folders.

`docs/backlog/order.json` owns manual order for `draft`, `todo`, `someday`, and
`planned`; do not add per-task position metadata. The Python tooling regenerates
the single full `docs/backlog/BACKLOG.md` after every backlog action.
