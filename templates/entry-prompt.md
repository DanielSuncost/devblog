# DevBlog entry generation prompt

You are generating a development log from tracked project evidence. This is not a generic blog post.
Do not invent product claims or unstated motivations. Prefer concrete, auditable statements.

Inputs available:
- git window: {{since_ref}} -> {{until_ref}}
- commit list
- diff stat
- changed files
- recent `.devblog/ledger.jsonl` observations
- project-specific context from repository files if needed

Output:
- Write one markdown entry using `.devblog/spec/post-template.md`.
- Keep it clear for a technical reader who wants to understand development progress.
- Mention uncertainty explicitly when the evidence is ambiguous.
- Preserve the provenance footer.

Visibility tagging (always emit, even if everything looks public):

- Add the metadata bullet `- Visibility: public` (default), `private`, or `mixed`.
- Wrap any block that should not be in the public version using these markers
  on their own lines:

      <!-- vis:private -->
      ...sensitive paragraphs, lists, or tables...
      <!-- /vis -->

- For a short fragment inside an otherwise-public sentence, use:
  `<span class="vis-priv">fragment</span>`.
- Default any block to public unless it falls into one of these categories:
  business strategy, monetization tactics, proprietary methodology,
  competitor comparisons that name companies pejoratively, anything pairing
  the words "moat" / "differentiator" / "proprietary" with concrete technical
  detail, voice/face/identity privacy specifics, secrets/credentials.
- The user can edit visibility later via the `devblog review` UI; aim for a
  reasonable first pass rather than worrying about being perfect.

Required emphasis:
1. What changed during this development window.
2. Why the change matters to the project direction.
3. What risks, TODOs, or next steps remain.
4. Which evidence supports the narrative.
