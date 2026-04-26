# Adapter/plugin architecture

DevBlog adapters are intentionally thin. They install host-specific prompts, task definitions, or instruction snippets, but all hosts share the same CLI and `.devblog/*` state.

## Shared contract

Every adapter must call the shared CLI:

```bash
devblog track --repo /abs/repo --once
devblog entry --repo /abs/repo --host HOST
devblog publish --repo /abs/repo --format public-md -o /abs/repo/.devblog/public/latest.md
```

Every adapter must preserve these files:

```text
.devblog/config.json
.devblog/state.json
.devblog/ledger.jsonl
.devblog/entries/*.md
```

Host-specific plugin files live under `.devblog/adapters/<host>/`.

## Installing adapters

```bash
devblog init --repo /abs/repo
devblog install-adapter --repo /abs/repo --host all
```

Supported hosts:

- `hermes`
- `charon`
- `pi-agent`
- `claude-code`
- `codex`
- `opencode`

Use `--force` to overwrite previously generated adapter files.

## Hermes

Hermes uses a cron job and terminal/file tools. The installed plugin files are:

```text
.devblog/adapters/hermes/README.md
.devblog/adapters/hermes/cron-prompt.txt
.devblog/adapters/hermes/cronjob.example.json
```

Schedule `cron-prompt.txt` every 12 hours. Recommended toolsets: `terminal,file`.

## Charon

Charon maps DevBlog onto native persistent project tasks:

```text
.devblog/adapters/charon/README.md
.devblog/adapters/charon/charon-devblog.tasks.yaml
```

Charon should run the tracker as a daemon and the entry/public export as scheduled tasks. Charon dashboards can read `.devblog/ledger.jsonl` and `.devblog/entries/*.md` directly.

## Pi Agent

Pi Agent uses a recurring prompt and optional conversation context capture:

```text
.devblog/adapters/pi-agent/README.md
.devblog/adapters/pi-agent/pi-devblog.prompt.md
```

The Pi prompt should save available context to a temp file and pass it to `devblog note --host pi-agent --context-file TEMPFILE` before entry generation.

## Claude Code

Claude Code uses project instructions and a reusable command prompt:

```text
.devblog/adapters/claude-code/README.md
.devblog/adapters/claude-code/CLAUDE.devblog.md
.devblog/adapters/claude-code/command-devblog.md
```

Include `CLAUDE.devblog.md` from the project `CLAUDE.md` or paste it into the Claude Code project instructions. Use `command-devblog.md` as a `/devblog` command body.

## Codex

Codex uses AGENTS instructions and a one-shot command prompt:

```text
.devblog/adapters/codex/README.md
.devblog/adapters/codex/AGENTS.devblog.md
.devblog/adapters/codex/codex-command.txt
```

Include `AGENTS.devblog.md` from the project `AGENTS.md`.

## OpenCode

OpenCode uses a reusable run prompt:

```text
.devblog/adapters/opencode/README.md
.devblog/adapters/opencode/opencode-command.txt
```

## Compatibility rule

If adapters disagree, the file contract wins. Adapters may evolve independently, but they must not fork the ledger, state, config, or entry formats.
