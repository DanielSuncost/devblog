# Adapter command examples (Hermes, Claude Code, Charon)

Goal: keep one shared format (`.devblog/*`) and use thin runtime adapters.

## Shared contract
All adapters should call:

`devblog track`   -> background tracker loop
`devblog entry`   -> generate a periodic devlog from tracked ledger + git window

Both commands read `.devblog/config.yaml` and update `.devblog/state.json` + `.devblog/ledger.jsonl`.

## Hermes adapter
1) Start tracker (long-running background process):

terminal(command="devblog track --repo /abs/repo", background=true, notify_on_complete=false)

2) Schedule entry generation every 12h (cronjob tool):

cronjob(action="create", name="devblog-12h", schedule="every 12h", prompt="In /abs/repo, run devblog entry and write/update .devblog/entries using .devblog/config.yaml. If no changes since last entry, record no_changes in .devblog/state.json.", enabled_toolsets=["terminal","file"])

## Claude Code adapter
Use system cron (or CI scheduler) for portability:

- Tracker:
  `@reboot cd /abs/repo && devblog track --repo /abs/repo >> .devblog/tracker.log 2>&1`

- 12h entry:
  `0 */12 * * * cd /abs/repo && claude -p "Run devblog entry for this repo using .devblog/config.yaml and update .devblog/state.json" --max-turns 8 >> .devblog/entry.log 2>&1`

## Charon adapter
Charon scheduler should treat tracker + entry as two tasks:

- Persistent task:
  `name: devblog-tracker`
  `kind: daemon`
  `command: devblog track --repo /abs/repo`

- Periodic task:
  `name: devblog-entry-12h`
  `kind: schedule`
  `schedule: every 12h`
  `command: devblog entry --repo /abs/repo`

## Compatibility rule
If adapters differ, file formats win:
- `.devblog/config.yaml`
- `.devblog/state.json`
- `.devblog/ledger.jsonl`
- `.devblog/entries/*.md`

As long as these stay stable, Hermes/Claude/Charon can interoperate.
