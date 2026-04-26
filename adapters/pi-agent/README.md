# DevBlog for Pi Agent

Pi Agent can use DevBlog by invoking the shared CLI and passing conversation
context through `devblog note --context-file`.

Install into a project with:

```bash
devblog init --repo /abs/repo
devblog install-adapter --repo /abs/repo --host pi-agent
```

Use `pi-devblog.prompt.md` as the recurring task prompt. Pi/Hermes/Charon-style
hosts can share provider/model routing through `.devblog/config.json`.
