# DevBlog skill for Claude Code

This is the Claude Code skill/instruction variant of the DevBlog adapter.

Use the shared CLI and file contract; do not create Claude-specific DevBlog state.

```bash
devblog track --repo . --once
devblog note --repo . --host claude-code --agent claude --area AREA --message "What changed."
devblog entry --repo . --host claude-code
devblog publish --repo . --format public-md -o .devblog/public/latest.md
devblog status --repo .
```

Rules:
- Source of truth: `.devblog/config.json`, `.devblog/state.json`, `.devblog/ledger.jsonl`, `.devblog/entries/`.
- Do not force duplicate entries unless explicitly asked.
- Do not invent project progress beyond git/test/ledger evidence.
- For new installs, run `devblog install-adapter --repo . --host claude-code` and include `.devblog/adapters/claude-code/CLAUDE.devblog.md` from the project `CLAUDE.md`.
