---
name: backlog-archive
description: Archives a backlog task in place with required reason/prior-status metadata and regenerates the full backlog index.
---

# Archive Task

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

Use when the operator deliberately abandons a task from any lifecycle status.

1. Resolve the canonical task under `docs/backlog/tasks/`.
2. Obtain a clear archival reason.
3. Run `python3 "<skills-root>/backlog-archive/scripts/archive_task.py" <taskid> --reason "<reason>"`.
4. Verify `status: archived`, `archivedAt`, `archivedFrom`, and `archiveReason`;
   verify the folder did not move and `BACKLOG.md` has exactly one task link.

Preserve custom frontmatter and sidecars. Never add frontmatter to sidecars or
modify `CHANGELOG.md` unless the user or project workflow requests it.
