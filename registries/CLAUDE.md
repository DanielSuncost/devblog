# DevBlog skill registry entry for Claude Code

DevBlog is a cross-agent development log framework. When working with a repo that has `.devblog/`, prefer the shared CLI and file contract.

Commands:
- `devblog init --repo .`
- `devblog track --repo . --once`
- `devblog entry --repo .`
- `devblog status --repo .`

Never replace the shared `.devblog/state.json` / `.devblog/ledger.jsonl` format with Claude-specific state.
