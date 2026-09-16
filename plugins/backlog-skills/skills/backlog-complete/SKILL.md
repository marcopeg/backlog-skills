---
name: backlog-complete
description: Marks a WIP backlog task completed in place and regenerates the full backlog index.
---

# Complete Task

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

1. Resolve the canonical task under `docs/backlog/tasks/` and require `wip`.
2. Run `python3 "<skills-root>/backlog-complete/scripts/complete_task.py" <taskid>`.
3. Verify `status: completed` and `completedAt`; verify the folder did not move
   and `BACKLOG.md` contains exactly one task link.

Preserve custom frontmatter and sidecars. Do not modify `CHANGELOG.md` unless the user or project workflow requests it.
