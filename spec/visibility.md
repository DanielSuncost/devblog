# DevBlog visibility tagging

Markdown source is the source of truth. We mark public/private chunks with
HTML comments at the block level and a tiny `<span>` at the inline level. Both
survive arbitrary markdown renderers and round-trip through git losslessly.

## Block markers

Open and close on their own lines. Anything between is treated as belonging
to that block, including blank lines and nested markdown structures.

```markdown
<!-- vis:private -->
Sensitive paragraph(s).

Multiple paragraphs are fine.
<!-- /vis -->
```

`<!-- vis:public -->` exists symmetrically but is rarely needed — unwrapped
content already defaults to public.

## Inline markers

For a fragment inside an otherwise-public sentence:

```markdown
We are using the Foo dataset (<span class="vis-priv">internal-only license tier</span>) for tier-S training.
```

Public inline marker `<span class="vis-pub">…</span>` exists but is mostly
informational; in public exports its body is preserved, the span tag is
stripped.

## Header metadata bullet

Every entry should declare overall visibility on the metadata bullet list:

```markdown
- Visibility: public
- Visibility: private
- Visibility: mixed
```

If the bullet is missing, DevBlog infers from block content — `mixed` if any
private block or inline span is present, `public` otherwise. The header is
auto-updated by the review UI / CLI when you flip blocks.

## What gets stripped on public export

- Every `<!-- vis:private --> … <!-- /vis -->` region — content and markers.
- Every `<span class="vis-priv">…</span>` — span and body.
- The opening/closing markers of `<!-- vis:public --> … <!-- /vis -->` —
  body retained.
- The `Visibility:` bullet is rewritten to `public`.
- Any consecutive blank lines collapsed to one.

The `substack-html` export additionally drops the metadata bullets
(`Generated`, `Window`, `Repo`, `Tracker mode`, `Visibility`) and the
`Provenance` section so the result is paste-ready into a Substack post.

## CLI surface

```bash
devblog review                       # local web UI (default :8780)
devblog visibility --value mixed     # set header bullet on the latest entry
devblog visibility --para-id p-1234abcd --value private
                                     # flip a single block
devblog lint                         # scan for risky words outside private blocks
devblog lint --strict                # exit non-zero if findings
devblog publish                      # stdout, public-md (default)
devblog publish --format substack-html -o out.html
devblog publish --format clipboard | xclip -selection clipboard
                                     # paste-ready HTML to clipboard
devblog publish --lint --format public-html -o public.html
                                     # refuse to publish if lint warnings remain
```

## Defaults: what should be private

Default to **public** unless a block contains one of:

- Specific monetization or pricing tactics.
- Proprietary methodology paired with concrete numbers.
- Competitor comparisons that name companies pejoratively.
- The words *moat*, *differentiator*, *proprietary*, *secret sauce* paired
  with implementation detail.
- Legal posture statements that you wouldn't want a competitor to copy.
- Credentials, internal hostnames, customer names, unreleased product names.

These are the patterns the default lint rules flag. Override with
`devblog lint --patterns 'foo,bar,baz'` if a project's vocabulary differs.

## Implementation notes

- Stable per-block IDs (`para_id`) are SHA1-derived from block content. Edit
  the content and the ID changes — this is intentional, since flipping
  visibility on a block whose content has materially changed shouldn't
  silently re-flip after an edit.
- The review server saves immediately on every flip; there is no draft state
  to lose.
- The HTML comment markers are invisible in every standard markdown renderer
  (GitHub, GitLab, Substack, Notion via paste, Pandoc). They show up only
  when reading raw source.
