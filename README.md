# Backlog Skills

**Turn a rough idea into an explicit plan, tracked work, and durable project memory.**

A collection of 13 portable agent skills maintained by the Backlog Skills contributors.
The backlog lives in Markdown and JSON inside your project. No hosted task service,
API key, or Python package installation is required.

[Download v1.2.0](https://github.com/marcopeg/backlog-skills/releases/tag/v1.2.0) ·
[Browse the skills](plugins/backlog-skills/skills) · [Presentation handout](docs/presentation.md)

## The idea in one minute

```mermaid
flowchart LR
    A[Draft an idea] --> B[Clarify the outcome]
    B --> C[Accept a plan]
    C --> D[Execute and track]
    D --> E[Complete]
    E --> F[Compress durable history]
```

Each task keeps the same folder throughout its life. Its canonical Markdown file
owns status and metadata. Plans, questions, and notes stay beside it. The tools
rebuild one index, so people and agents can find the same facts.

**Example conversation** — replace `AB12` with the ID returned by drafting:

```text
Use $backlog-draft to capture an idea: export my reading list as CSV.
Use $backlog-clarify to clarify task AB12.
Use $backlog-plan to plan AB12.
Accept the plan and use $backlog-execute to implement AB12.
Use $backlog-complete to complete AB12 after verification.
```

An agent writes the reasoning and implementation. Python helpers handle task IDs,
metadata, ordering, and indexes. Completion is explicit; compression is a separate
historical cleanup operation.

## Install

Choose **one** method to avoid duplicate skill entries. All methods install the
same complete bundle, including `backlog-core`.

### Codex: native plugin

Run in your terminal with a Codex CLI that includes `codex plugin`:

```bash
codex plugin marketplace add marcopeg/backlog-skills
codex plugin add backlog-skills@backlog-skills
```

Open a new Codex session after installation. For versions without plugin support,
use the built-in `$skill-installer` route in the [installation guide](docs/installation.md#codex-built-in-skill-installer).

### Claude Code: native plugin

Run inside Claude Code:

```text
/plugin marketplace add marcopeg/backlog-skills
/plugin install backlog-skills@backlog-skills
```

Restart Claude Code, or use `/reload-plugins` when your version offers it. Invoke
`/backlog-skills:backlog-draft` to start drafting a task.

### Codex and Claude Code: one command

Run in your target project's root (requires Node.js/npm):

```bash
npx skills add marcopeg/backlog-skills --skill '*' --agent codex claude-code
```

This uses the community-maintained [Vercel Skills CLI](https://github.com/vercel-labs/skills).
Add `--global` for a user-wide install, or choose just one agent. Install all 13
skills: selecting a single workflow does not automatically install its siblings.

See the [installation guide](docs/installation.md) for updates, removal, pinned
versions, the native Codex skill installer, and the offline Python fallback.

**Runtime:** Python 3.10+ in UTF-8 mode; Git for backup/history operations.
No third-party Python packages or service credentials are required by the skills.
The plugin contains no hooks, MCP servers, or external integrations.

## Privacy and portability

The published bundle contains only general-purpose workflow instructions and
standard-library helpers. It does not require a particular application, account,
machine path, service, or project name. `docs/backlog` is the default data root;
projects can provide another backlog root where a helper supports that option.

Before every release, run `python3 scripts/privacy_audit.py`. The check rejects
committed email addresses, user-home paths, common private-key blocks, and likely
access tokens. It is a safeguard, so maintainers must still review examples and
new documentation for context that should remain private.

## Skills

| Skill | Purpose |
| --- | --- |
| [backlog-draft](plugins/backlog-skills/skills/backlog-draft/SKILL.md) | Capture an idea as a structured task. |
| [backlog-clarify](plugins/backlog-skills/skills/backlog-clarify/SKILL.md) | Refine a task through chat questions. |
| [backlog-refine](plugins/backlog-skills/skills/backlog-refine/SKILL.md) | Refine through recorded question rounds. |
| [backlog-epic-refine-refinement](plugins/backlog-skills/skills/backlog-epic-refine-refinement/SKILL.md) | Align an epic, its children, and dependencies. |
| [backlog-plan](plugins/backlog-skills/skills/backlog-plan/SKILL.md) | Turn a refined task into an accepted milestone plan. |
| [backlog-execute](plugins/backlog-skills/skills/backlog-execute/SKILL.md) | Implement an accepted plan and record progress. |
| [backlog-complete](plugins/backlog-skills/skills/backlog-complete/SKILL.md) | Mark verified work complete. |
| [backlog-block](plugins/backlog-skills/skills/backlog-block/SKILL.md) | Record a temporary blocker and prior state. |
| [backlog-archive](plugins/backlog-skills/skills/backlog-archive/SKILL.md) | Retire work with a recorded reason. |
| [backlog-doctor](plugins/backlog-skills/skills/backlog-doctor/SKILL.md) | Diagnose and repair metadata and index drift. |
| [backlog-migrate](plugins/backlog-skills/skills/backlog-migrate/SKILL.md) | Convert supported legacy backlog layouts. |
| [backlog-compress](plugins/backlog-skills/skills/backlog-compress/SKILL.md) | Consolidate old history with Git retrieval anchors. |
| [backlog-core](plugins/backlog-skills/skills/backlog-core/SKILL.md) | Shared storage, lifecycle, ordering, and indexing helpers. |

The longer epic skill name is preserved so existing invocations remain compatible.

## Storage contract

```text
your-project/
├── .agents/skills/backlog-*/
└── docs/backlog/
    ├── BACKLOG.md
    ├── order.json
    └── tasks/
        └── AB12-export-reading-list/
            ├── AB12.task.md
            ├── AB12.plan.md
            └── AB12.notes.md
```

- `TASKID.task.md` is the only owner of task metadata. Use flat scalar frontmatter;
  the helpers do not implement arbitrary nested YAML.
- Status changes update metadata and keep task paths stable.
- `order.json` owns manual ordering for `draft`, `todo`, `someday`, and `planned`.
- `BACKLOG.md` is generated across all ten statuses. Edit task records, then rebuild.
- Additional statuses are `refining`, `refined`, `wip`, `blocked`, `archived`, and `completed`.
- Helpers perform mechanics; the agent follows acceptance and authorization rules
  in the skills. The low-level transition command is not a policy enforcement engine.
- Run one backlog writer at a time. Atomic file writes do not provide a transaction
  across the task, ordering file, and index.

## Migration and compression

Migration is for the legacy status-folder layouts described by its skill. Preview
with `--dry-run` and keep a restorable backup. Nested attachments, symlinks, and loose
legacy files stop migration for manual handling before source directories are removed.

Compression normally considers completed or archived tasks at least 14 full days
past their latest parseable update/completion/archive timestamp. It requires clean,
committed task content, records the source revision, and preserves retrieval anchors.
Keep that Git history available when sharing a compressed backlog.

## Verify or contribute

```bash
python3 -m unittest discover -s tests -v
```

Tests use disposable sample projects. They exercise installation, lifecycle
invariants, completion gates, index repair, migration preservation, compression
eligibility, and every helper's command-line entrypoint. CI runs on Linux, macOS,
and Windows with Python 3.10 and 3.13 in UTF-8 mode.

To contribute, keep instructions focused, preserve stable paths, and add a
regression test for changes to file-handling behavior. This repository contains
only skill source and distribution support; it includes no private backlog tasks
or application code.

## License

[MIT](LICENSE). Copyright © 2026 Backlog Skills contributors.
