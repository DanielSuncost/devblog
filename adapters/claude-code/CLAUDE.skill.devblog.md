# DevBlog skill for Claude Code

When asked to create, maintain, or run a DevBlog for this repo, use the shared CLI:

- `python tools/devblog/devblog.py init --repo .`
- `python tools/devblog/devblog.py track --repo . --once`
- `python tools/devblog/devblog.py entry --repo .`
- `python tools/devblog/devblog.py status --repo .`

Important: DevBlog is development telemetry + scheduled narrative. Do not treat it as a generic blog-writing task.
Always read `.devblog/spec/architecture.md` before changing behavior.

For scheduled use outside Claude Code, prefer system cron or the host orchestrator. Claude Code should only be the model/runtime adapter, not the source of truth.

## Multi-agent notes and model routing

```bash
devblog model --repo . --host claude-code
devblog note --repo . --host claude-code --agent AGENT --area AREA --message "What changed."
devblog entry --repo . --host claude-code
```

Use `.devblog/config.json` generation settings for cheap model routing where the host supports provider/model selection.
