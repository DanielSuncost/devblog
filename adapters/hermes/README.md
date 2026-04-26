# DevBlog for Hermes

Hermes should use DevBlog as a shared project tool, not as Hermes-only state.

Install the package somewhere on PATH, then initialize the target repo:

```bash
devblog init --repo /abs/repo
devblog install-adapter --repo /abs/repo --host hermes
```

Create a Hermes cron job using `cron-prompt.txt`, usually on `every 12h`, with
`terminal,file` toolsets enabled. The prompt runs `track --once`, `entry`,
`publish`, and `status` against the same `.devblog/*` files used by every host.
