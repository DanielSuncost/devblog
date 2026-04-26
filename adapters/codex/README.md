# DevBlog for Codex

Codex can use DevBlog through AGENTS instructions plus a reusable command prompt.
The CLI and `.devblog/*` files remain shared with every other host.

Install into a project with:

```bash
devblog init --repo /abs/repo
devblog install-adapter --repo /abs/repo --host codex
```

Copy or include `AGENTS.devblog.md` from this directory in the repo's `AGENTS.md`.
Use `codex-command.txt` for one-shot execution.
