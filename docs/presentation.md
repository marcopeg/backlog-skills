# From idea to durable project memory

## One-slide summary

**Backlog Skills: a Markdown workflow for coding agents.**

- Capture the idea and clarify the outcome.
- Accept an explicit plan before implementation.
- Track decisions and verification beside the task.
- Keep stable task paths and a generated index.
- Preserve useful history after the work is done.

**Get the skills:** https://github.com/marcopeg/backlog-skills

![Scan to get Backlog Skills](repository-qr.png)

[Download the QR code](repository-qr.png) for your slide.

## Install for your agent

Codex (terminal):

```bash
codex plugin marketplace add marcopeg/backlog-skills
codex plugin add backlog-skills@backlog-skills
```

Claude Code (inside the app):

```text
/plugin marketplace add marcopeg/backlog-skills
/plugin install backlog-skills@backlog-skills
```

Both agents (terminal, in your project):

```bash
npx skills add marcopeg/backlog-skills --skill '*' --agent codex claude-code
```

Choose one route. [Full installation guide](installation.md).

## A short live demo

Use a disposable project. Install the skills and open the project in your agent.

1. Ask: “Use $backlog-draft to capture a CSV export for a reading list.”
2. Open the generated task and show the business goal, uncertainty, and criteria.
3. Ask: “Use $backlog-clarify to clarify this task.” Answer one round.
4. Ask: “Use $backlog-plan to plan this task.” Show the milestone checkboxes.
5. Show that the task path stays fixed while its status changes in `BACKLOG.md`.

Stop at the plan for a short talk. Implementation and historical compression are
separate workflows that can be demonstrated with more time.

## Speaker notes

The skills are the instructions. The helper scripts maintain the filesystem facts.
The agent still needs judgment to clarify intent, implement the plan, and verify
results. Markdown keeps those decisions readable in an editor and reviewable in Git.

Audience members can browse the skills immediately or download the versioned
release and install them in a project. The release contains synthetic tests only;
no original project backlog is included.
