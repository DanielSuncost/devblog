# DevBlog agent integrations

DevBlog integrates with agents through a shared CLI and a small installable adapter pack. The important rule is that every host reads and writes the same `.devblog/*` files; host plugins are thin scheduling and instruction layers, not separate implementations.

## Universal install

Install DevBlog once where the agent can run it:

```bash
git clone git@github.com:DanielSuncost/devblog.git
cd devblog
python -m pip install -e .
```

Then initialize any target project:

```bash
devblog init --repo /abs/project
devblog install-adapter --repo /abs/project --host all
```

This creates host-specific plugin files under:

```text
/abs/project/.devblog/adapters/<host>/
```

Use `--host hermes`, `--host charon`, `--host pi-agent`, `--host claude-code`, `--host codex`, or `--host opencode` to install one host at a time. Use `--force` to overwrite generated adapter files.

## Hermes

Hermes should use DevBlog through Hermes cron jobs and terminal/file tools.

```bash
devblog install-adapter --repo /abs/project --host hermes
```

Use `.devblog/adapters/hermes/cron-prompt.txt` as the cron prompt. Recommended cron settings:

```text
schedule: every 12h
enabled_toolsets: terminal,file
```

The prompt runs:

```bash
devblog track --repo /abs/project --once
devblog entry --repo /abs/project --host hermes
devblog publish --repo /abs/project --format public-md -o /abs/project/.devblog/public/latest.md
devblog status --repo /abs/project
```

## Charon

Charon should treat DevBlog as a native project capability: a tracker daemon, a scheduled entry task, and a dashboard-readable artifact stream.

```bash
devblog install-adapter --repo /abs/project --host charon
```

Import or translate `.devblog/adapters/charon/charon-devblog.tasks.yaml` into Charon's task registry. Charon can build richer UI on top of `.devblog/ledger.jsonl` and `.devblog/entries/*.md`, but should not create a separate DevBlog state format.

## Pi Agent

Pi Agent should call the shared CLI and pass conversation context into `devblog note` when available.

```bash
devblog install-adapter --repo /abs/project --host pi-agent
```

Use `.devblog/adapters/pi-agent/pi-devblog.prompt.md` as the recurring task prompt. The prompt captures context, generates an entry, publishes a public-safe markdown export, and reports the output path.

## Claude Code

Claude Code integration is instruction-based.

```bash
devblog install-adapter --repo /abs/project --host claude-code
```

Copy or include `.devblog/adapters/claude-code/CLAUDE.devblog.md` in the project's `CLAUDE.md`. Use `.devblog/adapters/claude-code/command-devblog.md` as a reusable `/devblog` command body or manual prompt.

## Codex

Codex integration is AGENTS-instruction based.

```bash
devblog install-adapter --repo /abs/project --host codex
```

Copy or include `.devblog/adapters/codex/AGENTS.devblog.md` in the project's `AGENTS.md`. Use `.devblog/adapters/codex/codex-command.txt` for one-shot command execution.

## OpenCode

OpenCode integration uses a reusable run prompt and shared `.devblog/*` state.

```bash
devblog install-adapter --repo /abs/project --host opencode
```

Use `.devblog/adapters/opencode/opencode-command.txt` as a one-shot OpenCode run command.

## Compatibility checklist

Every adapter must preserve:

- `.devblog/config.json`
- `.devblog/state.json`
- `.devblog/ledger.jsonl`
- `.devblog/entries/*.md`

Adapters may add host-specific files under `.devblog/adapters/<host>/`, but generated evidence and posts must stay in the shared file contract.
