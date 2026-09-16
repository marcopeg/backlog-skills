---
name: backlog-plan
description: Builds or revises a milestone-based implementation plan for a canonical docs/backlog task and transitions accepted plans to planned.
---

# Plan Task

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

Use `backlog-plan` to create or revise a milestone plan for a refined task.

## Storage Model

- Backlog root: `docs/backlog`
- Canonical task file: `<taskid>.task.md`
- Plan file: `<taskid>.plan.md`
- Plan files are content-only artifacts and must not own frontmatter.
- All task-level frontmatter belongs only in `<taskid>.task.md`.

## Workflow

1. Resolve the task from `docs/backlog/tasks/` using canonical task frontmatter.
2. Read `<taskid>.task.md` first.
3. Read question, clarify, notes, and existing plan artifacts when useful.
4. Apply the review gate before planning.
5. Create or update `<taskid>.plan.md`.
6. Deterministically rebuild the full root `BACKLOG.md`.
7. Ask exactly: `Do you accept the plan?`

## Review Gate

Treat the task as reviewed when the canonical task file has planning-ready content for:

- `Business Gain`
- `Current State`
- `Desired State`
- `Definition of Success`
- `Constraints`
- `Acceptance Criteria`

If the task does not appear reviewed, ask exactly:

`This task does not appear to have been reviewed yet. Do you want to review it first, or should I proceed with the planning anyway?`

## Plan Structure

Plan files use checkbox progress and no YAML frontmatter:

```markdown
# Plan — <Task title>

## Goal

<short outcome>

## Milestones

### Milestone 1 — <name>

- [ ] Step 1 — <short label>
  - Achieve:
  - Create:
  - Modify:
  - Delete:
  - Touch points:
  - Validation:
  - Notes:
```

## Acceptance Semantics

- `accept` only: transition the task to `planned`.
- `accept and execute`: transition to `planned`, then to `wip`, then continue with `backlog-execute`.
- Planning must not set `startedAt` or `completedAt`.
- The task folder remains under `docs/backlog/tasks/`; plan acceptance changes only canonical metadata and appends the task to manual `planned` order.

Use the shared transition helper where practical:

```bash
python3 "<skills-root>/backlog-core/scripts/backlog_tool.py" transition <taskid> --to-state planned
```

Do not modify `CHANGELOG.md` unless the user or project workflow requests it.
