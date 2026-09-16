---
name: backlog-block
description: Temporarily blocks a backlog task in place while recording required prior-status, reason, and optional review timing metadata.
---

# Block Task

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

Use when execution or another active lifecycle stage is temporarily interrupted.

1. Resolve the canonical task under `docs/backlog/tasks/`.
2. Obtain a required, specific blocking reason and optional review-after date.
3. Run `python3 "<skills-root>/backlog-block/scripts/block_task.py" <taskid> --reason "<reason>" [--review-after YYYY-MM-DD]`.
4. Verify `status: blocked`, `blockedAt`, `blockedFrom`, and `blockReason`; verify
   the task folder did not move and `BACKLOG.md` contains exactly one link.

Preserve custom frontmatter and sidecars. Do not modify `CHANGELOG.md` unless the user or project workflow requests it.
