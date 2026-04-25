# DevBlog

Cross-agent development blog framework for active coding projects.

DevBlog is not a generic blog-writing prompt. It runs during development, tracks project activity in the background, and periodically turns evidence into clear devlog entries.

It is designed to be shared across:
- Hermes
- Claude Code
- Codex
- Charon
- Pi Agent
- OpenCode
- any agent that can run a shell command and read files

## Core idea

All hosts share one file contract:

```text
.devblog/config.json        project config
.devblog/state.json         idempotency and cursor state
.devblog/ledger.jsonl       background evidence events
.devblog/entries/*.md       generated devlog posts
```

All hosts call one CLI:

```bash
python -m devblog init --repo /path/to/repo
python -m devblog track --repo /path/to/repo --once
python -m devblog track --repo /path/to/repo
python -m devblog entry --repo /path/to/repo --host hermes
python -m devblog note --repo /path/to/repo --host claude-code --agent frontend --area frontend --message "Built the UI shell."
python -m devblog model --repo /path/to/repo --host hermes
python -m devblog status --repo /path/to/repo

# review, tag, and publish
python -m devblog review     --repo /path/to/repo            # local web UI on :8780
python -m devblog visibility --repo /path/to/repo --value mixed
python -m devblog lint       --repo /path/to/repo
python -m devblog publish    --repo /path/to/repo --format substack-html -o out.html
```

## Multi-agent notes

Multiple agents can contribute to the same DevBlog ledger. Each note is tagged with host, agent, and work area:

```bash
devblog note --repo . --host opencode --agent frontend --area frontend --message "Built the dashboard shell."
devblog note --repo . --host codex --agent backend --area backend --message "Prepared API contract."
devblog note --repo . --host pi-agent --context-file conversation.txt
devblog note --repo . --host charon --agent research --area research --message "Added paper notes." --entry latest
```

Supported hosts: `pi-agent`, `hermes`, `claude-code`, `codex`, `opencode`, `charon`.

Omit `--agent`, `--area`, or `--message` with `--context-file` to let DevBlog infer them from conversation context. Use `--entry latest` to append a tagged note to an existing entry.

## Model/provider selection

DevBlog keeps generation model configuration in `.devblog/config.json` so all host frameworks can share one policy. Hermes, Charon, and Pi Agent can use provider+model pairs; Claude Code generally maps to `--model`; Codex/OpenCode use provider/model config or model flags where supported.

```bash
devblog model --repo . --host hermes
devblog entry --repo . --host hermes
```

## Public / private tagging

Each entry can mix public and private content. Mark blocks with HTML comments
in the markdown source — they survive every markdown renderer:

```markdown
<!-- vis:private -->
Strategy/secrets/proprietary detail goes here.
<!-- /vis -->
```

Inline fragments use `<span class="vis-priv">…</span>`. A
`- Visibility: public|private|mixed` bullet on the entry header tracks the
overall classification.

The `devblog review` command starts a small local web UI where you can:

- Browse all entries with their public/private/mixed classification
- Click any block to flip its visibility (saves immediately to the markdown source)
- Toggle a "Public preview" mode that hides private blocks
- Export the entry as public markdown, public HTML, paste-ready
  Substack HTML, or copy to clipboard
- See lint warnings for risky words (`moat`, `proprietary`, etc.) outside
  private blocks

See `spec/visibility.md` for the full tagging spec.

## Quick start from source

```bash
git clone <this repo>
cd devblog
python -m pip install -e .
devblog init --repo /path/to/project
devblog track --repo /path/to/project --once
devblog entry --repo /path/to/project
devblog status --repo /path/to/project
```

## Why this is plugin-worthy

The wedge is background development tracking:
- watches git/project activity during coding
- records a ledger of evidence
- generates scheduled entries from tracked evidence
- prevents duplicate posts with state/window hashes
- lets different agents interoperate through the same files

## Repository layout

```text
src/devblog/                 stdlib-only CLI implementation
spec/                        shared schemas and architecture
adapters/                    Hermes, Claude Code, Codex, OpenCode, Pi Agent, Charon adapters
registries/                  reusable skill registry manifests
examples/                    example config files
templates/                   generation prompt/template files
```

## Status

MVP scaffold. The CLI currently provides a portable baseline tracker and entry generator. Host agents can improve narrative quality by using `templates/entry-prompt.md` while preserving `.devblog/*` state compatibility.
