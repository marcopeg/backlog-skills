---
name: backlog-migrate
description: Migrates legacy backlogs to stable tasks storage with canonical metadata, deterministic ordering/indexing, preservation, and audited reconciliation.
---

# Migrate Backlog

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

Target: all task folders live under `docs/backlog/tasks/`; one
`<taskid>.task.md` owns metadata; `order.json` owns manual order for draft,
todo, someday, and planned; `BACKLOG.md` is the only generated index.

1. Verify a restorable backup and pause backlog writers.
2. Run `python3 "<skills-root>/backlog-migrate/scripts/migrate_backlog.py" --dry-run`.
3. Inspect every reconciliation, confidence level, warning, and unresolved item.
4. If safe, run the same command without `--dry-run`.
5. Run backlog-doctor and verify task counts, hashes, links, ordering, and a
   byte-identical second rebuild before resuming writers.

Valid canonical frontmatter status wins over legacy folder status with a
warning. Reconciliation is automation-first: conflicts older than three weeks
receive the best safe automatic reconciliation; newer conflicts reconcile
automatically when evidence is high-confidence; lower-confidence newer cases
use conservative preservation and audit notes. Preserve every source variant as
a frontmatter-free sidecar/history file where feasible. Skip only genuinely
irreconcilable ambiguity or material data-loss risk. Remove legacy layout only
after successful validation; never maintain dual-read or dual-write support.

## Supported legacy input

The helper migrates flat task folders inside recognized status directories.
Nested attachments, symlinks, and loose files in legacy status directories are
reported as unresolved; a real run stops before task writes or legacy deletion.
Resolve those layouts manually with a backup before retrying. The script does
not migrate arbitrary issue trackers or infer arbitrary directory structures.
