# Pi Agent adapter

Pi Agent should call the shared CLI and use `.devblog/config.json` for provider/model routing.

```bash
devblog model --repo . --host pi-agent
devblog track --repo . --once
devblog note --repo . --host pi-agent --context-file conversation.txt
devblog entry --repo . --host pi-agent
```

Pi/Hermes/Charon-style hosts can use provider+model pairs such as OpenRouter cheap models for scheduled DevBlog work.
