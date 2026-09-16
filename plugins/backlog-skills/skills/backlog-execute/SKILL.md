---
name: backlog-execute
description: Executes an accepted docs/backlog plan, transitions the canonical task to wip, updates progress checkboxes, and maintains notes.
---

# Execute Task

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

Use `backlog-execute` only after the operator explicitly accepts a plan.

## Storage Model

- Backlog root: `docs/backlog`
- Stable task storage: `docs/backlog/tasks/`
- Canonical task file: `<taskid>.task.md`
- Plan file: `<taskid>.plan.md`
- Notes file: `<taskid>.notes.md`
- Plan and notes files are content-only artifacts and must not own frontmatter.

## Execution Gate

- Do not execute without an accepted plan.
- If no plan exists, stop and direct the workflow back to `backlog-plan`.
- `accept and execute`, `yes and execute`, and `execute` after a pending acceptance prompt mean accepted plan plus execution.

## Lifecycle Rules

- Transition the task to `wip` before implementation.
- Update canonical task metadata to `status: wip` without moving the folder.
- Deterministically rebuild the full root `BACKLOG.md`.
- Create `<taskid>.notes.md` if it does not exist.
- Never move the task to completed or archived in this skill.

Use:

```bash
python3 "<skills-root>/backlog-execute/scripts/transition_task.py" <taskid> --to-state wip
```

## Plan Tracking

- Execute milestone by milestone.
- Mark completed steps in the plan immediately.
- Record deviations in both the plan notes and execution notes.

## Notes Structure

Notes files use no YAML frontmatter:

```markdown
# Execution Notes — <Task title>
**Task**: ./<taskid>.task.md
**Plan**: ./<taskid>.plan.md

## Decisions

## Problems Encountered

## Deviations From Plan

## Additional Requests

## Known Limitations
```

Do not modify `CHANGELOG.md` unless the user or project workflow requests it.
