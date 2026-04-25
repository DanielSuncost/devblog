# DevBlog instructions for Codex

This repository uses a cross-agent DevBlog framework. Use the shared CLI instead of inventing a Codex-specific workflow.

Commands:
- Initialize: `python tools/devblog/devblog.py init --repo .`
- Capture one observation: `python tools/devblog/devblog.py track --repo . --once`
- Generate entry: `python tools/devblog/devblog.py entry --repo .`
- Status: `python tools/devblog/devblog.py status --repo .`

Rules:
- The source of truth is `.devblog/config.json`, `.devblog/state.json`, `.devblog/ledger.jsonl`, and `.devblog/entries/`.
- Do not duplicate an entry for the same window hash.
- This is a development-log tracker running during coding, not a generic blog skill.
- Preserve compatibility with Hermes, Claude Code, and Charon.

## Multi-agent notes and model routing

```bash
devblog model --repo . --host codex
devblog note --repo . --host codex --agent AGENT --area AREA --message "What changed."
devblog entry --repo . --host codex
```

Use `.devblog/config.json` generation settings for cheap model routing where the host supports provider/model selection.
