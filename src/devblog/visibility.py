"""Visibility tagging primitives for DevBlog entries.

Markdown source is the source of truth. We mark public/private chunks with
HTML comments at the block level and a small <span> at the inline level. Both
survive arbitrary markdown renderers, and we can parse them ourselves with a
few regexes.

Block markers:
    <!-- vis:private -->
    ...content...
    <!-- /vis -->

Inline markers:
    <span class="vis-priv">fragment</span>
    <span class="vis-pub">fragment</span>

Header metadata (optional bullet on the entry header):
    - Visibility: public | private | mixed

Defaults:
    - Unmarked content is public.
    - An entry without a Visibility bullet is treated as `public` for export,
      `mixed` (everything visible) for review.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Iterator

# ----- regexes ---------------------------------------------------------------

# Block open/close markers must each occupy their own line. Anything between
# is treated as belonging to that block, including blank lines.
_BLOCK_OPEN = re.compile(r"^[ \t]*<!--\s*vis:(?P<v>private|public)\s*-->[ \t]*$", re.MULTILINE)
_BLOCK_CLOSE = re.compile(r"^[ \t]*<!--\s*/vis\s*-->[ \t]*$", re.MULTILINE)

_INLINE = re.compile(
    r'<span\s+class="vis-(?P<v>priv|pub)"\s*>(?P<body>.*?)</span>',
    re.DOTALL,
)

_VISIBILITY_BULLET = re.compile(
    r"^[ \t]*[-*][ \t]+visibility[ \t]*:[ \t]*(?P<v>public|private|mixed)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


# ----- data model ------------------------------------------------------------

@dataclass
class Block:
    """A contiguous chunk of the markdown source plus its visibility."""

    visibility: str  # "public" | "private"
    text: str
    start: int       # byte offset in source
    end: int         # byte offset in source (exclusive)
    para_id: str = "" # stable id derived from text


@dataclass
class Document:
    visibility: str          # "public" | "private" | "mixed"
    blocks: list[Block] = field(default_factory=list)
    raw: str = ""

    def stats(self) -> dict[str, int]:
        priv = sum(1 for b in self.blocks if b.visibility == "private")
        pub = sum(1 for b in self.blocks if b.visibility == "public")
        return {"public_blocks": pub, "private_blocks": priv, "total_blocks": pub + priv}


# ----- parsing ---------------------------------------------------------------

def header_visibility(md: str) -> str | None:
    """Return the value of the `- Visibility:` bullet at top of file, if any."""
    m = _VISIBILITY_BULLET.search(md)
    return m.group("v").lower() if m else None


def _para_id(text: str) -> str:
    """Stable id derived from first ~80 chars + a tiny hash. Idempotent across runs."""
    import hashlib
    head = re.sub(r"\s+", " ", text.strip())[:80]
    h = hashlib.sha1(text.encode()).hexdigest()[:8]
    return f"p-{h}"


def _split_paragraphs(text: str, base_offset: int) -> list[Block]:
    """Split an unmarked region of markdown into paragraph-level Blocks.

    A paragraph is a contiguous run of non-blank lines, EXCEPT that fenced
    code blocks (```...```) are kept together even when they contain blank
    lines internally. Each emitted Block is tagged public.
    """
    lines = text.splitlines(keepends=True)
    blocks: list[Block] = []
    buf: list[str] = []
    buf_start_off = base_offset
    cur_off = base_offset
    in_fence = False

    def flush():
        nonlocal buf, buf_start_off
        if not buf:
            return
        joined = "".join(buf)
        if joined.strip():
            content = joined.rstrip("\n")
            blocks.append(Block("public", content, buf_start_off, buf_start_off + len(joined), _para_id(content)))
        buf = []

    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("```"):
            if not in_fence:
                # opening fence — start a fresh para if buffer was not empty
                if buf and "".join(buf).strip():
                    flush()
                    buf_start_off = cur_off
                else:
                    buf = []
                    buf_start_off = cur_off
                in_fence = True
                buf.append(ln)
            else:
                # closing fence
                buf.append(ln)
                in_fence = False
                flush()
                buf_start_off = cur_off + len(ln)
            cur_off += len(ln)
            continue
        if in_fence:
            buf.append(ln)
            cur_off += len(ln)
            continue
        if stripped == "":
            if buf:
                flush()
                buf_start_off = cur_off + len(ln)
            else:
                buf_start_off = cur_off + len(ln)
            cur_off += len(ln)
            continue
        if not buf:
            buf_start_off = cur_off
        buf.append(ln)
        cur_off += len(ln)

    flush()
    return blocks


def parse(md: str) -> Document:
    """Split markdown into Blocks tagged by visibility.

    Marked regions (<!-- vis:* --> ... <!-- /vis -->) become a single Block
    each. Unmarked regions are split into paragraph-level public Blocks so
    individual paragraphs can be flipped via the review UI.
    """
    blocks: list[Block] = []
    cursor = 0
    n = len(md)

    while cursor < n:
        open_match = _BLOCK_OPEN.search(md, cursor)
        if not open_match:
            tail = md[cursor:]
            if tail.strip():
                blocks.extend(_split_paragraphs(tail, cursor))
            break

        if open_match.start() > cursor:
            chunk = md[cursor:open_match.start()]
            if chunk.strip():
                blocks.extend(_split_paragraphs(chunk, cursor))

        marker_vis = open_match.group("v")
        body_start = open_match.end()
        close_match = _BLOCK_CLOSE.search(md, body_start)
        if not close_match:
            chunk = md[body_start:]
            stripped = chunk.strip("\n")
            blocks.append(Block(marker_vis, stripped, body_start, n, _para_id(stripped)))
            cursor = n
            break

        body = md[body_start:close_match.start()]
        body_stripped = body.strip("\n")
        blocks.append(Block(marker_vis, body_stripped, body_start, close_match.start(), _para_id(body_stripped)))
        cursor = close_match.end()
        if cursor < n and md[cursor] == "\n":
            cursor += 1

    declared = header_visibility(md)
    if declared:
        visibility = declared
    else:
        priv = any(b.visibility == "private" for b in blocks)
        has_inline_priv = bool(_INLINE.search(md)) and "vis-priv" in md
        visibility = "mixed" if (priv or has_inline_priv) else "public"

    return Document(visibility=visibility, blocks=blocks, raw=md)


# ----- transformations -------------------------------------------------------

def strip_private(md: str) -> str:
    """Return the markdown with all private blocks and inline fragments removed.

    Suitable for public export.
    """
    # Remove block-level private regions, including their markers and the
    # newline that follows the close marker (so we don't leave double blank lines).
    def block_repl(match: re.Match[str]) -> str:
        return ""

    out = re.sub(
        r"^[ \t]*<!--\s*vis:private\s*-->[ \t]*\n.*?^[ \t]*<!--\s*/vis\s*-->[ \t]*\n?",
        "",
        md,
        flags=re.DOTALL | re.MULTILINE,
    )

    # Remove public block markers (the markers themselves; keep the content).
    out = re.sub(r"^[ \t]*<!--\s*vis:public\s*-->[ \t]*\n", "", out, flags=re.MULTILINE)
    out = re.sub(r"^[ \t]*<!--\s*/vis\s*-->[ \t]*\n?", "", out, flags=re.MULTILINE)

    # Remove inline private spans entirely. Preserve inline public spans
    # by keeping their body text only.
    out = _INLINE.sub(lambda m: "" if m.group("v") == "priv" else m.group("body"), out)

    # Update the Visibility bullet, if present, to "public".
    out = _VISIBILITY_BULLET.sub("- Visibility: public", out)

    # Collapse runs of >2 blank lines that the strip might have produced.
    out = re.sub(r"\n{3,}", "\n\n", out)

    return out


def set_block_visibility(md: str, para_id: str, target: str) -> tuple[str, bool]:
    """Find the block whose para_id matches and toggle its visibility.

    Returns (new_md, changed). target is "public" or "private".
    """
    if target not in ("public", "private"):
        raise ValueError(f"target must be public|private, got {target!r}")

    doc = parse(md)
    for b in doc.blocks:
        if b.para_id != para_id:
            continue
        if b.visibility == target:
            return md, False
        if target == "private":
            # Wrap the block with markers.
            block_text = b.text
            replacement = f"<!-- vis:private -->\n{block_text}\n<!-- /vis -->"
            new_md = md[:b.start] + replacement + md[b.end:]
            return new_md, True
        else:  # target == "public"
            # The block is currently inside <!-- vis:private --> ... <!-- /vis -->.
            # We need to also remove those wrapping markers, which sit just
            # outside b.start / b.end. Find the open marker that immediately
            # precedes b.start.
            preceding = md[:b.start]
            open_match = None
            for m in _BLOCK_OPEN.finditer(preceding):
                open_match = m
            close_match = _BLOCK_CLOSE.search(md, b.end)
            if not open_match or not close_match:
                return md, False
            # Replace [open_marker..close_marker] with just the body.
            new_md = (
                md[:open_match.start()]
                + b.text
                + md[close_match.end():]
            )
            return new_md, True
    return md, False


# ----- HTML rendering --------------------------------------------------------

def _md_to_html_simple(md: str) -> str:
    """Tiny markdown → HTML renderer covering what our entries actually use.

    Supports: # h1-h6, paragraphs, **bold**, *italic*, `code`, fenced code blocks,
    bullet lists (- and *), numbered lists, [links], > blockquotes, --- hr,
    pipe tables, and raw HTML pass-through.

    This is deliberately simple. If a project needs a real renderer they can
    pipe the markdown through one externally; we only need enough to make the
    review UI legible.
    """
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    in_table = False
    table_buf: list[str] = []

    def flush_table():
        nonlocal in_table, table_buf
        if not table_buf:
            in_table = False
            return
        rows = []
        sep_idx = None
        for idx, ln in enumerate(table_buf):
            if re.match(r"^\s*\|?[\s|:-]+\|?\s*$", ln) and "-" in ln:
                sep_idx = idx
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows.append(cells)
        if sep_idx is None or not rows:
            for ln in table_buf:
                out.append(_inline(ln))
            table_buf.clear()
            in_table = False
            return
        head = rows[0]
        body = rows[1:]
        out.append("<table>")
        out.append("<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead>")
        out.append("<tbody>")
        for r in body:
            out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
        out.append("</tbody></table>")
        table_buf.clear()
        in_table = False

    while i < len(lines):
        ln = lines[i]
        # fenced code
        if ln.startswith("```"):
            if in_code:
                out.append(f'<pre><code class="lang-{html.escape(code_lang)}">' + html.escape("\n".join(code_buf)) + "</code></pre>")
                in_code = False
                code_lang = ""
                code_buf = []
            else:
                in_code = True
                code_lang = ln[3:].strip()
            i += 1
            continue
        if in_code:
            code_buf.append(ln)
            i += 1
            continue

        # table
        if "|" in ln and ln.strip().startswith("|"):
            in_table = True
            table_buf.append(ln)
            i += 1
            continue
        elif in_table:
            flush_table()

        # raw HTML comment passthrough (vis markers etc.)
        if ln.lstrip().startswith("<!--"):
            out.append(ln)
            i += 1
            continue

        # raw HTML blocks (e.g. <div data-...>) passthrough
        if re.match(r"^\s*<(?:div|section|span|details|summary|aside|figure)\b", ln):
            out.append(ln)
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # hr
        if re.match(r"^\s*-{3,}\s*$", ln) or re.match(r"^\s*\*{3,}\s*$", ln):
            out.append("<hr/>")
            i += 1
            continue

        # blockquote
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> "))
                i += 1
            out.append("<blockquote>" + _inline("\n".join(buf)) + "</blockquote>")
            continue

        # bullet / numbered lists
        if re.match(r"^\s*[-*]\s+", ln):
            buf = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                buf.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(b)}</li>" for b in buf) + "</ul>")
            continue
        if re.match(r"^\s*\d+\.\s+", ln):
            buf = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(b)}</li>" for b in buf) + "</ol>")
            continue

        # blank line
        if not ln.strip():
            i += 1
            continue

        # paragraph
        para = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i]):
            para.append(lines[i])
            i += 1
        out.append("<p>" + _inline(" ".join(para)) + "</p>")

    if in_code:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>")
    if in_table:
        flush_table()

    return "\n".join(out)


def _is_block_start(ln: str) -> bool:
    if not ln:
        return False
    if ln.startswith(("#", ">", "```", "---", "***")):
        return True
    if ln.lstrip().startswith("<!--"):
        return True
    if re.match(r"^\s*[-*]\s+", ln) or re.match(r"^\s*\d+\.\s+", ln):
        return True
    if "|" in ln and ln.strip().startswith("|"):
        return True
    if re.match(r"^\s*<(?:div|section|span|details|summary|aside|figure)\b", ln):
        return True
    return False


def _inline(s: str) -> str:
    """Inline markdown: code, bold, italic, links. Leaves raw HTML alone."""
    # protect inline code first
    placeholders: dict[str, str] = {}
    def stash(text: str) -> str:
        key = f"\x00{len(placeholders)}\x00"
        placeholders[key] = text
        return key

    s = re.sub(r"`([^`]+)`", lambda m: stash(f"<code>{html.escape(m.group(1))}</code>"), s)

    # preserve already-rendered <span class="vis-..."> spans
    s = re.sub(
        r'<span\s+class="vis-(priv|pub)"\s*>(.*?)</span>',
        lambda m: stash(f'<span class="vis-{m.group(1)}">{_inline_inner(m.group(2))}</span>'),
        s,
        flags=re.DOTALL,
    )

    # links [text](url)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: stash(f'<a href="{html.escape(m.group(2))}">{html.escape(m.group(1))}</a>'), s)

    # bold then italic
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)

    # escape any remaining angle brackets that aren't part of placeholders
    # (raw HTML blocks were handled at the block level)
    s = re.sub(r"&", "&amp;", s)
    s = re.sub(r"<(?!/?(?:strong|em|code|a|span)\b)", "&lt;", s)

    # restore placeholders
    for key, val in placeholders.items():
        s = s.replace(key, val)
    return s


def _inline_inner(s: str) -> str:
    return _inline(s)


def render_html(md: str, mode: str = "internal", *, paragraph_anchors: bool = False) -> str:
    """Render markdown to HTML, marking visibility blocks with data attributes.

    mode="internal": private blocks are rendered, wrapped in <section data-visibility="private">.
    mode="public":   private blocks are stripped before rendering.
    """
    if mode == "public":
        md = strip_private(md)

    doc = parse(md)
    parts: list[str] = []
    for b in doc.blocks:
        inner_html = _md_to_html_simple(b.text)
        # Inline spans become <span class="vis-priv|pub">.
        if b.visibility == "private":
            attr = f'data-visibility="private" data-para-id="{b.para_id}"'
        else:
            attr = f'data-visibility="public" data-para-id="{b.para_id}"' if paragraph_anchors else f'data-visibility="public"'
        parts.append(f'<section {attr}>\n{inner_html}\n</section>')
    return "\n".join(parts)


# ----- linting ---------------------------------------------------------------

DEFAULT_RED_FLAGS = [
    r"\bmoat\b",
    r"\bdifferentiator\b",
    r"\bproprietary\b",
    r"\bsecret sauce\b",
    r"\bcompetitive advantage\b",
    r"\bunpublished\b",
    r"\bdo not share\b",
    r"\binternal only\b",
]


@dataclass
class LintFinding:
    line: int
    block_visibility: str
    pattern: str
    snippet: str

    def __str__(self) -> str:
        return f"line {self.line}: '{self.pattern}' in {self.block_visibility} block — {self.snippet}"


def lint(md: str, patterns: list[str] | None = None) -> list[LintFinding]:
    """Flag occurrences of red-flag terms in non-private blocks.

    Private blocks are exempt — the whole point is to host sensitive content
    safely. Public blocks (and the implicit-public surrounding text) get
    scanned and reported.
    """
    pats = [re.compile(p, re.IGNORECASE) for p in (patterns or DEFAULT_RED_FLAGS)]
    findings: list[LintFinding] = []
    doc = parse(md)
    for b in doc.blocks:
        if b.visibility == "private":
            continue
        for p in pats:
            for m in p.finditer(b.text):
                line_no = md[:b.start + m.start()].count("\n") + 1
                snippet = b.text[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
                findings.append(LintFinding(line=line_no, block_visibility=b.visibility, pattern=p.pattern, snippet=snippet))
    return findings


# ----- header visibility helpers --------------------------------------------

def set_header_visibility(md: str, value: str) -> str:
    """Update or insert the `- Visibility:` bullet on the entry header."""
    if value not in ("public", "private", "mixed"):
        raise ValueError(f"value must be public|private|mixed, got {value!r}")
    if _VISIBILITY_BULLET.search(md):
        return _VISIBILITY_BULLET.sub(f"- Visibility: {value}", md)
    # Insert after the first run of "- Foo: bar" header bullets if any.
    m = re.search(r"^(- [A-Z][^\n]*\n)+", md, re.MULTILINE)
    if m:
        insert_at = m.end()
        return md[:insert_at] + f"- Visibility: {value}\n" + md[insert_at:]
    # Otherwise, insert just after the first H1.
    h1 = re.search(r"^# .*\n", md, re.MULTILINE)
    if h1:
        insert_at = h1.end()
        return md[:insert_at] + f"\n- Visibility: {value}\n" + md[insert_at:]
    return f"- Visibility: {value}\n\n" + md
