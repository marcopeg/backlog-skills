# Installation and updates

Choose one route per agent. The native plugins install the entire bundle in one
operation. Standalone skill installers must include all 13 skills: they do not
resolve the sibling `backlog-core` dependency automatically.

## Codex native plugin

In a terminal:

```bash
codex plugin marketplace add marcopeg/backlog-skills
codex plugin add backlog-skills@backlog-skills
```

Use a Codex CLI with the `plugin` command (packaging was checked against 0.139.0).
Start a new session after installation, then select Backlog Skills or ask to use
its backlog-draft skill. Use the name displayed by your client for explicit
plugin-scoped invocation.

For a fixed release, use this instead of the first command:

```bash
codex plugin marketplace add marcopeg/backlog-skills --ref v1.2.0
```

For a marketplace following the default branch, refresh and reinstall:

```bash
codex plugin marketplace upgrade backlog-skills
codex plugin add backlog-skills@backlog-skills
```

Remove the plugin:

```bash
codex plugin remove backlog-skills@backlog-skills
```

The repository supplies `.agents/plugins/marketplace.json` and a native
`.codex-plugin/plugin.json`. This is a self-hosted GitHub marketplace, not a
listing in OpenAI's curated directory.

## Codex built-in skill installer

For local skill installation without plugins, paste into Codex:

```text
Use $skill-installer to install every skill under
plugins/backlog-skills/skills in https://github.com/marcopeg/backlog-skills
at ref v1.2.0. Include all 13 folders, especially backlog-core, and preserve
their sibling layout.
```

The built-in installer supports multiple repository paths in one invocation.
Its default destination is your Codex skills directory. It refuses existing
destination folders; review and move old copies aside before replacing them.
The skills live under `plugins/backlog-skills/skills/`; installed skill names are unchanged.

OpenAI documents the [built-in skill installer](https://learn.chatgpt.com/docs/build-skills#install-curated-skills-for-local-use), including installation from other repositories.

## Claude Code native plugin

Inside Claude Code:

```text
/plugin marketplace add marcopeg/backlog-skills
/plugin install backlog-skills@backlog-skills
```

Restart Claude Code (or `/reload-plugins` on versions supporting it), then use:

```text
/backlog-skills:backlog-draft Capture an idea for CSV export.
/backlog-skills:backlog-clarify AB12
/backlog-skills:backlog-plan AB12
```

Replace `AB12` with the ID produced by drafting. Plugin skills are namespaced;
standalone installations use `/backlog-draft` instead.

Update:

```text
/plugin marketplace update backlog-skills
/plugin update backlog-skills@backlog-skills
```

Remove:

```text
/plugin uninstall backlog-skills@backlog-skills
```

This follows Anthropic's [marketplace installation pattern](https://code.claude.com/docs/en/discover-plugins).
It is your own marketplace, not an Anthropic-curated listing.

## Cross-agent Skills CLI

The community-maintained [Vercel Skills CLI](https://github.com/vercel-labs/skills)
supports both Codex and Claude Code:

```bash
npx skills add marcopeg/backlog-skills --skill '*' --agent codex claude-code
```

Run in the target project. Keep `'*'` quoted so your shell does not expand it.
To install just for one agent, pass `--agent codex` or `--agent claude-code`.
Add `--global` for user-wide installation. Add `--copy` if you cannot use symlinks.
The CLI discovers skills through the Claude marketplace; there is one canonical
source tree, not separate agent-specific copies in this repository.

For a fixed source version:

```bash
npx skills add https://github.com/marcopeg/backlog-skills/tree/v1.2.0/plugins/backlog-skills/skills --skill '*' --agent codex claude-code
```

Check for updates with `npx skills check`; `npx skills update` updates all tracked
skills, so review the scope if you have other bundles. Use `npx skills remove`
interactively and select this bundle's skills when uninstalling. Do not remove
`backlog-core` while keeping workflows that depend on it.

This route requires Node.js/npm and installs skills, not the native plugin.

## Offline Python fallback

Download the release ZIP or clone the tag:

```bash
git clone --branch v1.2.0 https://github.com/marcopeg/backlog-skills.git
python3 backlog-skills/scripts/install.py --project /path/to/your-project
```

This installs into `.agents/skills/` for Codex. For Claude Code alone:

```bash
python3 backlog-skills/scripts/install.py --destination /path/to/your-project/.claude/skills
```

Use `--destination` with an absolute global skills directory for a user-wide
install. Add `--dry-run` to preview. Existing folders are never overwritten.
On Windows, use `python` if `python3` is unavailable.

## Runtime and first use

Python 3.10+ in UTF-8 mode is required; on non-UTF-8 systems set `PYTHONUTF8=1`.
The runtime helpers use only the Python standard library. Git is required for
backup/history operations. A first draft initializes `docs/backlog/`.

Run helpers from the **target project**, using the installed helper's absolute
path. Each skill explains how to resolve `<skills-root>` from its own location.
This matters because plugin managers copy the package into a cache. Creating
backlog data in that cache would lose the connection to your project.

## Verification

The release test suite verifies the shared helper behavior and executes helpers
from a copied plugin directory. Distribution checks cover both native manifest
formats and installation using the Vercel Skills CLI. The CI installation job
uses a disposable project and invokes a real installed helper.

Sources: [Codex plugin packaging](https://learn.chatgpt.com/docs/build-plugins),
[Codex marketplace layout](https://learn.chatgpt.com/docs/enterprise/plugin-management#supported-formats),
[Claude marketplace format](https://code.claude.com/docs/en/plugin-marketplaces),
[Claude plugin reference](https://code.claude.com/docs/en/plugins-reference), and
[Skills CLI](https://github.com/vercel-labs/skills). Researched September 15, 2026.
