---
name: backlog-compress
description: Compress stable backlog task folders into one durable canonical task record while preserving reconstructable Git history. Use when the user invokes backlog compression, asks which completed or archived tasks are old enough to compress, requests compression of one task ID, or wants redundant task plans, notes, questions, tests, migrations, and assets consolidated after completion.
---

# Backlog Compress

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

Consolidate a task folder under the configured backlog root (by default,
`docs/backlog/tasks/<task-folder>/`) into its canonical
`<TASKID>.task.md`. Optimize for agentic search, drill-down investigation, and
historical reconstruction. Preserve exact retrieval anchors in the compressed
record and use Git for forensic detail.

## Eligibility

Use `scripts/list_candidates.py` from this skill.

A task is automatically eligible when all conditions hold:

- status is `completed` or `archived`;
- it has not already been compressed;
- the newest parseable value among `updatedAt`, `archivedAt`, and `completedAt`
  is at least 14 full days old.

Do not use `createdAt` as the age cutoff. Treat a missing or malformed cutoff
date as ineligible.

## Invocation

### Specific task ID

1. Inspect the task with:

   ```bash
   python3 "<skills-root>/backlog-compress/scripts/list_candidates.py" <TASKID> --all \
     --backlog-root <backlog-root>
   ```

2. If eligible, compress it without asking for confirmation.
3. If ineligible, explain the exact reason and ask whether to override.
4. Continue after explicit confirmation. An override authorizes compression,
   not a lifecycle transition; retain the existing status.

### No task ID

1. Run:

   ```bash
   python3 "<skills-root>/backlog-compress/scripts/list_candidates.py" \
     --backlog-root <backlog-root>
   ```

2. Present the resulting `ID`, `Status`, and `Last update` table.
3. Ask for confirmation before changing any task.
4. On confirmation, compress exactly the listed IDs. Recheck each task before
   editing and report any that became ineligible or dirty.
5. If no task is eligible, report that and stop.

Never ask a second confirmation for tasks already approved through the table.

## Compression Workflow

For every approved task:

1. Resolve the canonical task and list every file recursively.
2. Require the task directory to be clean before editing:

   ```bash
   git status --short -- <task-directory>
   ```

   Stop on any output. The source commit must contain the exact artifacts being
   compressed.

3. Capture the full pre-compression revision:

   ```bash
   git rev-parse HEAD
   ```

4. Read every textual artifact completely. Inspect images and other meaningful
   assets. Do not infer their contents from filenames.
5. Build a small research inventory before drafting:
   - task IDs named by the artifacts;
   - legacy and final paths;
   - component, script, API, database, and configuration names;
   - assets moved or replaced;
   - implementation commits explicitly tied to the task.
6. Search the whole backlog for every concrete inventory anchor, not only the
   task ID or title. This must catch task-specific consumers of a replaced path
   or mechanism. Run the deterministic candidate scan:

   ```bash
   python3 "<skills-root>/backlog-compress/scripts/find_anchor_references.py" \
     <TASKID> --source-commit <compressedFromCommit> \
     --backlog-root <backlog-root>
   ```

   Review every reported task and classify it as superseded, superseding,
   related, or irrelevant before drafting. Inspect current source and Git
   history only to confirm the delivered state, reconcile contradictions, or
   establish relationships.
   For claims about delivered code, compare narrative artifacts with the
   implementation commit and its parent. When they disagree, Git determines
   what shipped; preserve the contradiction only when it helps historical
   interpretation.
7. Separate actual supersession from precedent, dependency, extension, and
   ordinary related work. Require evidence before declaring supersession.
8. Apply a relevance pass before writing:
   - retain task-specific decisions, outcomes, evidence, and limitations;
   - omit generic backlog migrations and lifecycle archaeology;
   - omit unrelated warnings even when they appeared during QA;
   - mention a later code change only when it explains why current source
     differs materially from the task's delivered state.
9. Create `<TASKID>.task.compressed.md` first. Do not delete anything yet.
10. Run:

   ```bash
   python3 "<skills-root>/backlog-compress/scripts/validate_compressed.py" \
     <TASKID> <path-to-compressed-file> \
     --source-dir <task-directory> \
     --require-source-head
   ```

11. Perform two explicit audits:
    - coverage: restore any missing durable decision, migration consequence,
      limitation, or supported relationship;
    - compression: remove lifecycle narration, unrelated diagnostics,
      duplicated facts, and details recoverable from Git that do not explain
      the durable outcome.
    - retrieval: test whether the record can be found and understood through
      exact legacy terms, replacement terms, symbols, task IDs, and commits.
12. Replace `<TASKID>.task.md` with the validated content. Delete every other
    file and empty subdirectory inside that task folder, including the temporary
    compressed draft. Use `apply_patch` for text-file changes and explicit,
    validated paths for other removals.
13. Validate the canonical file again with the same validator command. Verify
    the folder contains only `<TASKID>.task.md`, run `git diff --check`,
    and confirm the configured backlog index still links the canonical path exactly
    once. Regenerate the index only if compression changed index-visible data.

Do not commit unless the user separately asks.
Do not modify `CHANGELOG.md` unless the user or project workflow requests it.

## Canonical Record

Keep the original `taskId`, `status`, `createdAt`, relevant `completedAt` or
`archivedAt`, `group`, and historically meaningful archive reason. Remove
workflow-only transition metadata.

Keep lifecycle prose short. The normal historical record needs creation,
completion or archival, and the implementation commit when identifiable. Do
not reconstruct moves between backlog states, bulk archive operations, or
later migration reconciliation unless a task-specific reason changes how the
outcome should be interpreted.

Add:

```yaml
compressedAt: <current timezone-aware ISO-8601 datetime>
compressedFromCommit: <full HEAD before compression>
```

The body must stand alone and normally contain:

```markdown
# <Title>

## Historical Summary
## Retrieval Anchors
## Durable Outcome and Decisions
## Validation and Limitations
## Task Relationships
### Supersedes
### Superseded by
### Related Tasks
## Compression Provenance
```

Use `None identified` when a relationship section has no supported entries.
State partial supersession precisely. Do not classify a task as superseding
merely because it touched the same files later.

Write `Retrieval Anchors` as compact atomic bullets containing exact strings:

- task ID and full title;
- legacy aliases, paths, endpoints, schema names, and symbols;
- final paths, endpoints, schema names, and symbols;
- implementation commits;
- related task IDs with full titles.

Preserve both sides of important migrations as `old` → `new`. Exact obsolete
strings are valuable because they let an agent find the task from historical
code, logs, documentation, or operator language. Prefer backticks around
searchable identifiers.

Make every relationship entry a Markdown link to its canonical task file. Use
full relationship labels such as `AAF: Support Accent Color`, not bare labels
such as `AAF`. The title supplies semantic retrieval terms and the link enables
direct drill-down.

In provenance, list the artifacts consolidated and state that their exact
versions are recoverable from `compressedFromCommit`.

Report the compression ratio, but treat it as a secondary diagnostic. Retrieval
coverage outranks a fixed reduction target. Deliberate repetition of exact
identifiers is acceptable when it improves search recall.

Before deletion, run these retrieval checks against the draft:

1. Find it using an obsolete term or path.
2. Find the replacement contract and exact implementation symbols.
3. Answer why the change happened without opening Git.
4. Follow superseded, superseding, and related task links.
5. Recover one deleted artifact from `compressedFromCommit`.

If any check fails, improve the record before finalization.

## Keep

- original problem and business reason;
- exact legacy and replacement identifiers needed for search;
- compact old-to-new mappings;
- final outcome and durable contracts;
- important alternatives, constraints, and negative decisions;
- migrations and compatibility consequences;
- meaningful implementation deviations;
- task-relevant validation evidence, unresolved limitations, and known failures;
- supported supersession and related-task links;
- facts needed to explain why current code or documentation has its shape.

## Discard

- milestone narration and lifecycle transitions;
- repeated acceptance criteria already proven by the outcome;
- checkbox mechanics, empty sections, and operator chatter;
- temporary debugging output;
- generic lifecycle archaeology and repository-wide migration narration;
- warnings unrelated to the task's behavior or acceptance;
- detailed test recipes when their result is enough;
- duplicated content already expressed more clearly elsewhere in the record.

Do not copy current documentation wholesale. Preserve the historical decision
and link canonical documentation when it materially improves future discovery.
Optimize for precise agent retrieval, not literary flow.
