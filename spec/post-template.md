# {{title}}

- Generated: {{generated_at_utc}}
- Window: `{{since_ref}}` → `{{until_ref}}`
- Repo: `{{repo_name}}`
- Tracker mode: background_daemon
- Visibility: {{visibility|public}}

## TL;DR
{{summary_3_bullets}}

## Development activity pulse (tracked in background)
- Active files touched: {{active_files_count}}
- Commit events observed: {{commit_events_count}}
- Test/build events observed: {{test_events_count}}
- Largest churn area: {{largest_churn_area}}

## What changed
{{what_changed_narrative}}

### Key files
| File | Change type | Why it matters |
|---|---|---|
{{key_files_table}}

### Commits in window
| SHA | Author | Message |
|---|---|---|
{{commit_table}}

## Agent notes
{{agent_notes}}

## Why it matters
{{impact_section}}

## Risks and follow-ups
- Risks:
{{risk_bullets}}
- Follow-ups:
{{followup_bullets}}

## Metrics snapshot
- Files changed: {{files_changed}}
- Insertions: {{insertions}}
- Deletions: {{deletions}}
- Tests touched: {{tests_touched}}
- Docs touched: {{docs_touched}}

## Next window plan
{{next_window_plan}}

---

## Provenance
- Dedupe key: {{dedupe_key}}
- Window hash: {{window_hash}}
- Redaction applied: {{redaction_applied}}
- Generation host: {{generation_host}}
- Generation provider: {{generation_provider}}
- Generation model: {{generation_model}}
