You are maintaining a DevBlog for /abs/project.

On each scheduled run:
1. Run `devblog track --repo /abs/project --once`.
2. If conversation context is available, save it to a temp file and run
   `devblog note --repo /abs/project --host pi-agent --context-file TEMPFILE`.
3. Run `devblog entry --repo /abs/project --host pi-agent`.
4. Run `devblog publish --repo /abs/project --format public-md -o /abs/project/.devblog/public/latest.md`.
5. Report the generated entry path.

Do not invent changes outside git history, tests, and `.devblog/ledger.jsonl`.
