# Hermes adapter

Hermes should not own a separate format. It invokes the shared CLI and uses Hermes cron only as the scheduler.

## One-shot setup

```bash
cd /home/dopppo/Projects/charon
python tools/devblog/devblog.py init --repo . --default-branch main
python tools/devblog/devblog.py track --repo . --once
```

## Long-running background tracker from Hermes

Use terminal background process:

```python
terminal(command="python tools/devblog/devblog.py track --repo /home/dopppo/Projects/charon", background=True)
```

## 12h entry cron prompt

Create a Hermes cron job with this self-contained prompt:

```text
In /home/dopppo/Projects/charon, run:
python tools/devblog/devblog.py track --repo /home/dopppo/Projects/charon --once
python tools/devblog/devblog.py entry --repo /home/dopppo/Projects/charon
Then report the generated entry path or duplicate/no-change status.
Do not invent changes outside the evidence in .devblog/ledger.jsonl and git history.
```

Recommended enabled toolsets: `terminal,file`.

## Multi-agent notes and model routing

```bash
devblog model --repo . --host hermes
devblog note --repo . --host hermes --agent AGENT --area AREA --message "What changed."
devblog entry --repo . --host hermes
```

Use `.devblog/config.json` generation settings for cheap model routing where the host supports provider/model selection.
