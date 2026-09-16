---
name: backlog-clarify
description: Chat-based refinement for docs/backlog tasks; logs clarify rounds without frontmatter, updates the canonical TASKID.task.md, and transitions status through refining/refined.
---

# Clarify Task

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

Use `backlog-clarify` when the operator wants chat-based clarification instead of file-edited question rounds.

## Storage Model

- Backlog root: `docs/backlog`
- Canonical task file: `<taskid>.task.md`
- Clarify round files: `<taskid>.clarify.v1.md`, `<taskid>.clarify.v2.md`, and so on.
- Clarify files are content-only artifacts and must not own frontmatter.
- All task-level frontmatter belongs only in `<taskid>.task.md`.

## Status Rules

- Transition to `refining` when clarification begins.
- Keep `refining` while chat rounds are pending.
- Transition to `refined` when clarification is enough and planning is proposed.
- Keep the task folder permanently under `docs/backlog/tasks/`; status changes update canonical metadata only.

## Workflow

1. Resolve and read the task folder.
2. Read prior clarify rounds, question rounds, plan, notes, and relevant sidecars.
3. Ask 1 to 3 targeted questions in chat.
4. Record each round in the next `<taskid>.clarify.vN.md` file without frontmatter.
5. Fold usable answers into `<taskid>.task.md`.
6. If ambiguity remains, ask another chat round and keep status `refining`.
7. If plan-ready, transition to `refined` and ask exactly: `Clarification is enough. Do you want to plan this task now?`

## Clarify File Structure

```markdown
# Clarify Round v1 — <Task title>

## Questions

### 1. <question>

## Answers

### 1.

<answer or pending>

## Resolution Summary

- <resolved ambiguity or pending>
```

Do not modify `CHANGELOG.md` unless the user or project workflow requests it.
