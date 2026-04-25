# Charon adapter

Charon is the best long-term host for DevBlog because it already wants persistent project agents.
The integration should map directly onto Charon concepts:

- tracker daemon = persistent Charon project watcher
- entry generator = scheduled project task
- ledger = auditable project memory stream
- entry markdown = human-facing project progress artifact

Do not make Charon-specific state that Hermes/Claude/Codex cannot read. Add richer Charon UI on top of the same `.devblog/*` files.

## Multi-agent notes and model routing

```bash
devblog model --repo . --host charon
devblog note --repo . --host charon --agent AGENT --area AREA --message "What changed."
devblog entry --repo . --host charon
```

Use `.devblog/config.json` generation settings for cheap model routing where the host supports provider/model selection.
