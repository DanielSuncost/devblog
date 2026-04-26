# DevBlog for Claude Code

Claude Code can participate through a project instruction file and slash-command
style prompt. DevBlog remains a CLI/file-contract tool; Claude is just one host.

Install into a project with:

```bash
devblog init --repo /abs/repo
devblog install-adapter --repo /abs/repo --host claude-code
```

Copy or include `CLAUDE.devblog.md` from this directory in your project-level
`CLAUDE.md`, and use `command-devblog.md` as the body of a `/devblog` command or
manual prompt.
