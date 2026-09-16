---
name: backlog-epic-refine-refinement
description: Refine a backlog epic and its full child-task set through iterative question rounds. Use when an epic needs its scope, dependency order, child-task boundaries, shared contracts, acceptance criteria, or delivery readiness clarified before planning; this workflow may add, split, merge, or retire child tasks.
---

# Refine Backlog Epic

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

Use the single-task `backlog-refine` workflow as the base, but apply its ambiguity-reduction loop to the epic and every child task as one delivery system. The outcome is an epic and a best-fit task set that are each ready for independent planning and execution.

## Storage and Lifecycle

- Keep the epic canonical record at `<backlog-root>/tasks/<epic-folder>/<epic-id>.task.md`; `docs/backlog` is the default root.
- Use epic question rounds named `<epic-id>.question.v1.md`, `<epic-id>.question.v2.md`, and so on. They have no frontmatter.
- Keep the epic in `refining` until both the epic and every retained child are plan-ready.
- Keep task-level facts in the child task that owns them. Put cross-cutting decisions in the epic and propagate them to every affected child contract.
- Use `backlog-core` transitions and regenerate `<backlog-root>/BACKLOG.md` after each backlog action. Do not modify `CHANGELOG.md` unless the user or project workflow requests it.

## Workflow

1. Resolve and read the epic, every question round, plan, note, sidecar, `BACKLOG.md`, and concretely relevant predecessor work.
2. Identify all child tasks from the epic's dependency order and related links. Read each canonical task before asking the next question.
3. Build and maintain a private coverage check across the epic and children: business gain, current state, desired state, definition of success, constraints, acceptance criteria, ownership boundaries, dependencies, shared contracts, and verification.
4. Fold answered questions into the epic and every affected child. Preserve the original decision in the applicable question round.
5. Write the next epic question round before asking it, and keep the epic `refining`. Ask a focused set of independent material questions that fits the current interaction; use one question when the channel or user preference is unclear.
6. Re-read affected children after every answer. Propagate a cross-cutting decision to all owners rather than leaving it only in the epic.
7. Propose a task-set change when it improves execution boundaries:
   - Add a child when a required capability lacks a clear owner.
   - Split a task when it contains independently plannable work, conflicting dependencies, distinct risk, or acceptance criteria that cannot be verified together.
   - Merge or retire work only when ownership and acceptance criteria are genuinely redundant or out of scope.
   - Explain the boundary and dependency impact, obtain the user's decision when the change is material, then use the appropriate backlog workflow to create or revise canonical tasks and update the epic's order.
8. Mark the epic `refined` only after every retained child is individually plan-ready, the dependency order is explicit, cross-cutting contracts agree, and the epic readiness gate is met. Then invite the user to plan the epic.

## Question-Round Discipline

Use this format:

```markdown
# Refinement Questions vN — <Epic title>

Answer inline or in the active conversation before requesting the next round.

## Questions

### 1. <Material ambiguity>

Answer:
```

Ask only material questions whose answer is not already established in the epic, child tasks, prior rounds, or relevant completed work. Order the round by dependency and keep only questions that can be answered independently; use a later round when an answer changes the next question. Do not advance to planning while any child has a material unresolved ambiguity.

## Epic Readiness Gate

Treat an epic as plan-ready only when:

- The epic's business gain, current and desired state, definition of success, constraints, and acceptance criteria are concrete or explicitly `n/a`.
- Every retained child is individually plan-ready by the same gate.
- Every cross-cutting decision appears in the epic and in each child task that implements or verifies it.
- Each deliverable has one clear owner, dependency order, and verification boundary.
- The task set is neither missing a necessary delivery capability nor mixing work that should be independently planned.
