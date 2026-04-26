Run the DevBlog workflow for this repository:

1. `devblog track --repo . --once`
2. `devblog entry --repo . --host claude-code`
3. `devblog publish --repo . --format public-md -o .devblog/public/latest.md`
4. `devblog status --repo .`

Summarize the generated entry path, public export path, or duplicate/no-change status.
