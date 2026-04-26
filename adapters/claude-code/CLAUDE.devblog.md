# DevBlog project instructions

This repo uses DevBlog for evidence-based development posts.

When asked to update DevBlog:
- run `devblog track --repo . --once`;
- add relevant context with `devblog note --repo . --host claude-code --agent claude --area AREA --message "..."`;
- run `devblog entry --repo . --host claude-code`;
- run `devblog publish --repo . --format public-md -o .devblog/public/latest.md` if a public export is needed.

Rules:
- Source of truth is `.devblog/config.json`, `.devblog/state.json`, `.devblog/ledger.jsonl`, and `.devblog/entries/`.
- Do not force duplicate entries unless explicitly asked.
- Do not invent changes beyond git/test/ledger evidence.
