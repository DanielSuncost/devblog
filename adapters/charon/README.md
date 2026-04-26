# DevBlog for Charon

Charon should treat DevBlog as a project-level capability:

- tracker daemon: captures project evidence;
- scheduled task: writes a development entry;
- dashboard surface: reads `.devblog/entries/*.md` and `.devblog/ledger.jsonl`.

Install into a project with:

```bash
devblog init --repo /abs/repo
devblog install-adapter --repo /abs/repo --host charon
```

Import or translate `charon-devblog.tasks.yaml` into Charon's scheduler/task
registry. Charon-specific UI can be added on top, but the source of truth stays
in `.devblog/*`.
