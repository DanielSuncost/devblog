# DevBlog cross-agent architecture

DevBlog is a development telemetry + narrative layer, not a generic blogging assistant.

The core distinction:
- it runs during active project development;
- it records a background ledger of evidence;
- scheduled entries are compiled from that ledger plus git history;
- every host agent uses the same on-disk contract.

## Layers

1. Shared data contract
   - `.devblog/config.json` or `.devblog/config.yaml`
   - `.devblog/state.json`
   - `.devblog/ledger.jsonl`
   - `.devblog/entries/*.md`

2. Shared CLI
   - `devblog init`
   - `devblog track --once` or `devblog track --daemon`
   - `devblog entry`
   - `devblog status`

3. Host adapters
   - Hermes: cron + terminal tool calls the shared CLI.
   - Claude Code: slash command / skill / cron shell calls the shared CLI.
   - Codex: AGENTS.md-compatible instructions + `codex exec` calls the shared CLI.
   - Charon: native daemon/scheduler task calls the shared CLI.

## Compatibility rule

Adapters may differ, but the file contract must not. If Hermes generates a ledger event,
Claude Code, Codex, and Charon must be able to read it. If Charon generates an entry,
Hermes should not duplicate the same window.

## Idempotency rule

The entry window is `last_entry.until_ref -> current HEAD` by default. The entry command
computes a window hash from:
- since_ref
- until_ref
- commit list
- diff stat

If the same window hash already exists in state history, the run must become
`skipped_duplicate` unless explicitly forced.

## Background tracking rule

The tracker is allowed to poll cheaply. It should capture observations, not produce prose.
The prose step happens only in `devblog entry` so adapters can use their own model if desired.

Ledger event classes:
- `git_status`: status hash, changed files, branch, HEAD
- `commit`: sha, author, timestamp, subject
- `diff_stat`: files, insertions, deletions
- `test_event`: command, status, duration, optional summary
- `agent_event`: host agent, session id, prompt/task summary
- `entry`: path, since_ref, until_ref, window_hash

## Multi-agent notes

Agents add tagged observations with `devblog note`. Notes include `host`, `agent`, `area`, `visibility`, `message`, and a stable display tag of `host/agent/area`. Entries include recent notes in an `Agent notes` section, and `--entry latest` can append a note into an existing post.

## Generation model routing

`.devblog/config.json` may define `generation.default` and `generation.hosts`. Provider-flexible hosts (Hermes, Charon, Pi Agent) can use provider+model pairs; Claude Code primarily maps to `--model`; Codex and OpenCode use provider/model config or model flags supported by their CLIs.
