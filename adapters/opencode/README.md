# DevBlog for OpenCode

OpenCode can use DevBlog through a reusable project prompt and the shared CLI.
Install into a project with:

```bash
devblog init --repo /abs/repo
devblog install-adapter --repo /abs/repo --host opencode
```

Use `opencode-command.txt` for one-shot execution and keep all state in `.devblog/*`.
