---
name: backlog-refine
description: File-based refinement for docs/backlog tasks; writes question rounds without frontmatter, updates the canonical TASKID.task.md, and transitions status through refining/refined.
---

# Refine Task

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

Use `backlog-refine` to make a task explicit enough for planning through file-edited question rounds.

## Storage Model

- Backlog root: `docs/backlog` by default; use the project's configured backlog root when it differs.
- Resolve tasks from `<backlog-root>/tasks/` using canonical task frontmatter.
- Canonical task file: `<taskid>.task.md`
- Question round files: `<taskid>.question.v1.md`, `<taskid>.question.v2.md`, and so on.
- Question files are content-only artifacts and must not own frontmatter.
- All task-level frontmatter belongs only in `<taskid>.task.md`.

## Status Rules

- When refinement begins, transition the task to `refining`.
- Keep the task in `refining` while question rounds are pending.
- When the task is plan-ready and planning is proposed, transition the task to `refined`.
- Never move or rename a task folder for a status change; update canonical metadata and regenerate `BACKLOG.md`.

Use the shared transition helper where practical:

```bash
python3 "<skills-root>/backlog-core/scripts/backlog_tool.py" transition <taskid> --to-state refining
python3 "<skills-root>/backlog-core/scripts/backlog_tool.py" transition <taskid> --to-state refined
```

## Workflow

1. Resolve the task:

```bash
python3 "<skills-root>/backlog-refine/scripts/resolve_task.py" <taskid>
```

2. Read the task folder, including task, question rounds, plan, notes, and relevant sidecars.
3. Read `<backlog-root>/BACKLOG.md` if it exists; the first draft initializes a new backlog.
4. Inspect concretely relevant prior tasks and notes.
5. If no question round exists, transition to `refining`, write `<taskid>.question.v1.md`, and stop.
6. If the latest question round has no usable answers, stop and tell the operator which file needs answers.
7. If answers exist, fold them into `<taskid>.task.md`.
8. If ambiguity remains, write the next question round and keep status `refining`. Ask a focused set of independent material questions that fits the current interaction; use one question when the channel or user preference is unclear.
9. If plan-ready, transition to `refined` and invite the user to plan the task.

## Question Files

Question files use this structure without YAML frontmatter:

```markdown
# Refinement Questions v1 — <Task title>

Answer inline or in the active conversation before requesting the next round.

## Questions

### 1. <material ambiguity>

Answer:
```

## Readiness Gate

Treat the task as plan-ready only when these task sections are concrete enough for implementation sequencing or explicitly `n/a`:

- `Business Gain`
- `Current State`
- `Desired State`
- `Definition of Success`
- `Constraints`
- `Acceptance Criteria`

Do not modify `CHANGELOG.md` unless the user or project workflow requests it.

## Question-Round Discipline

Ask only questions whose answers are not already established in the task, prior rounds, or relevant predecessor work. Order questions by dependency and defer dependent questions to a later round.
