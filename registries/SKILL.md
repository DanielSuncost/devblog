---
name: devblog
description: Cross-agent background development blog tracker/generator. Use when a project should continuously track coding activity and periodically create clear devlog posts from git + ledger evidence. Compatible with Hermes, Claude Code, Codex, OpenCode, Pi Agent, and Charon.
version: 0.1.0
author: DevBlog contributors
license: MIT
metadata:
  hermes:
    tags: [devblog, development-log, background-tracking, cron, documentation, cross-agent]
    homepage: https://github.com/REPLACE_ME/devblog
    related_skills: [hermes-agent, claude-code, codex, opencode]
---

# DevBlog

Use this skill when the user wants an automatic project development blog/devlog that runs during coding and periodically summarizes actual changes.

## Core distinction

DevBlog is not generic blog writing. It is:
- background tracking while development happens;
- an evidence ledger in `.devblog/ledger.jsonl`;
- idempotent state in `.devblog/state.json`;
- scheduled markdown entries in `.devblog/entries/`;
- portable across Hermes, Claude Code, Codex, OpenCode, Pi Agent, Charon, and any shell-capable agent.

## Commands

From a project using DevBlog:

```bash
# tracking & generation
devblog init --repo .
devblog track --repo . --once
devblog entry --repo . --host hermes
devblog note --repo . --host opencode --agent frontend --area frontend --message "Built UI shell."
devblog model --repo . --host hermes
devblog status --repo .

# review, tag, publish
devblog review --repo .                          # local web UI on :8780
devblog visibility --repo . --value mixed        # entry-level header
devblog visibility --repo . --para-id p-XXX --value private
devblog lint --repo .                            # flag risky words
devblog publish --repo . --format public-md
devblog publish --repo . --format substack-html -o out.html
devblog publish --repo . --format clipboard | xclip -selection clipboard
```

If running from source instead of an installed package, prefix the commands
with `python /path/to/devblog/src/devblog/cli.py`.

## Workflow

1. Ensure the project has `.devblog/config.json` or initialize it.
2. Run `devblog track --once` before entry generation to capture latest state.
3. Run `devblog entry` on schedule, typically every 12 hours.
4. Do not force duplicate windows unless the user explicitly asks.
5. Use `templates/entry-prompt.md` if asking a model to polish the markdown.

## Multi-agent notes

Use `devblog note` to let multiple agents contribute tagged notes to the shared ledger or an existing entry. Supported hosts: `pi-agent`, `hermes`, `claude-code`, `codex`, `opencode`, `charon`. Use `--context-file` to infer agent/area/message from conversation context. Use `--entry latest` to append into an existing post.

## Model/provider selection

Use `generation.default` and `generation.hosts` in `.devblog/config.json` to select cheap models per host. `devblog model --host HOST` prints the resolved provider/model and adapter hint. Hermes, Charon, and Pi Agent can use provider+model; Claude Code generally uses `--model`; Codex/OpenCode use their provider/model configuration or CLI model flags where supported.

## Cross-agent rule

Do not create host-specific state. Hermes, Claude Code, Codex, OpenCode, Pi Agent, and Charon must all share:
- `.devblog/config.json`
- `.devblog/state.json`
- `.devblog/ledger.jsonl`
- `.devblog/entries/*.md`

## Public / private tagging

Entries can mix public and private content with HTML-comment markers in the
markdown source. See `spec/visibility.md`. Block markers:

```
<!-- vis:private -->
sensitive paragraphs here
<!-- /vis -->
```

`devblog review` opens a local web UI for clicking paragraphs to flip
visibility, hiding private blocks with a toggle, and exporting/copying
public-safe markdown or substack-ready HTML.

## Safety

For public posts, redact secrets and internal-only details. Do not invent
changes beyond git history and ledger evidence. Run `devblog lint` (or
`devblog publish --lint`) before any external publish to catch terms like
"moat", "proprietary", or "secret sauce" that escaped a private wrap.
