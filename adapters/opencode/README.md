# OpenCode adapter

OpenCode should use the shared DevBlog CLI and file contract.

```bash
devblog model --repo . --host opencode
opencode run "Use DevBlog to track once and write an entry" --model openrouter/google/gemini-2.0-flash-lite
devblog note --repo . --host opencode --agent frontend --area frontend --message "Built UI shell."
```

Do not create OpenCode-specific state. Use `.devblog/state.json`, `.devblog/ledger.jsonl`, and `.devblog/entries/*.md`.
