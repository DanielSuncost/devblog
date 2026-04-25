# DevBlog spec bundle

This spec defines a development-native devblog system:
- background tracking while coding
- periodic entry generation (e.g. every 12h)
- idempotent state + ledger for retries and dedupe
- adapter portability across Hermes, Claude Code, and Charon

Files:
- `config.schema.yaml`
- `state.schema.json`
- `post-template.md`
- `adapters.md`
