# DevBlog instructions for Codex

This repo uses DevBlog for scheduled, evidence-based development posts.

Use these commands:
- `devblog track --repo . --once`
- `devblog note --repo . --host codex --agent codex --area AREA --message "..."`
- `devblog entry --repo . --host codex`
- `devblog publish --repo . --format public-md -o .devblog/public/latest.md`
- `devblog status --repo .`

Rules:
- Preserve `.devblog/state.json` idempotency.
- Use git history, tests, and `.devblog/ledger.jsonl`; do not invent progress.
- Keep compatibility with Hermes, Charon, Pi Agent, and Claude Code.
