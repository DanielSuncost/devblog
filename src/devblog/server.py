"""Local HTTP server for reviewing/tagging DevBlog entries.

Stdlib-only. Runs at http://127.0.0.1:<port>.

Routes:
    GET  /                              entry list
    GET  /entry?path=<rel>              render entry with toggleable blocks
    POST /api/visibility                {"path":..., "para_id":..., "target":"public|private"}
    POST /api/header-visibility         {"path":..., "value":"public|private|mixed"}
    GET  /export?path=<rel>&format=...  exports (public-md|public-html|substack-html|raw-md)
    GET  /api/lint?path=<rel>           returns lint findings as JSON
    GET  /static/<file>                 css/js
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import visibility as vis


# ----- styling and scripts ---------------------------------------------------

_CSS = r"""
:root{
  --bg:#0d0d14;--bg2:#13131e;--bg3:#1a1a28;--border:#2a2a40;--border2:#3a3a55;
  --accent:#7c6af7;--accent2:#5ee8c0;--accent3:#f7c44a;
  --text:#e0e0f0;--text-soft:#b8b8d0;--muted:#6a6a9a;
  --priv:#f74a6a;--pub:#5ee8c0;--warn:#f7a24a;--success:#4af78a;
  --priv-bg:rgba(247,74,106,0.08);--priv-border:#5a2a3a;
  --pub-bg:rgba(94,232,192,0.04);--pub-border:rgba(94,232,192,0.18);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font:14px/1.65 'SF Mono','Fira Code','JetBrains Mono','Consolas',monospace}
body{min-height:100vh;display:flex;flex-direction:column}
a{color:var(--accent2);text-decoration:none;border-bottom:1px dashed transparent}
a:hover{border-bottom-color:var(--accent2)}
.shell{max-width:920px;margin:0 auto;padding:0 24px;width:100%}
header.site{padding:14px 0;border-bottom:1px solid var(--border);background:var(--bg2);position:sticky;top:0;z-index:10;backdrop-filter:blur(8px)}
header.site .shell{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
.brand{display:flex;align-items:baseline;gap:10px}
.brand .logo{font-size:16px;font-weight:700;color:var(--accent2)}
.brand .logo::before{content:"●";color:var(--accent);margin-right:6px;font-size:10px}
.brand .tag{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em}
nav.site{display:flex;gap:14px;align-items:center;font-size:12px}
nav.site a{color:var(--muted);border:none}
nav.site a:hover{color:var(--text)}
.btn{padding:6px 12px;background:var(--bg3);border:1px solid var(--border);color:var(--text-soft);
     border-radius:5px;font-family:inherit;font-size:12px;cursor:pointer;transition:all .12s}
.btn:hover{border-color:var(--accent);color:var(--text)}
.btn.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.btn.primary:hover{background:#9484ff;border-color:#9484ff}
.btn.priv{border-color:var(--priv);color:var(--priv)}
.btn.priv:hover{background:var(--priv-bg)}
.btn.pub{border-color:var(--pub);color:var(--pub)}
.btn.pub:hover{background:var(--pub-bg)}
.toggle-mode{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;background:var(--bg3);
             border:1px solid var(--border);border-radius:6px;font-size:11px;color:var(--muted);cursor:pointer}
.toggle-mode .dot{width:8px;height:8px;border-radius:50%;background:var(--priv);box-shadow:0 0 8px var(--priv)}
body[data-mode="public"] .toggle-mode .dot{background:var(--pub);box-shadow:0 0 8px var(--pub)}
body[data-mode="public"] [data-visibility="private"]{display:none !important}
main{flex:1;padding:32px 0 64px}
h1{font-size:22px;margin-bottom:14px;letter-spacing:-.005em}
h2{font-size:18px;color:var(--accent2);margin:24px 0 10px}
h3{font-size:14px;margin:16px 0 6px}
p{margin:0 0 12px;color:var(--text-soft);line-height:1.7}
ul,ol{margin:0 0 14px 22px;color:var(--text-soft)}
li{margin-bottom:4px}
li::marker{color:var(--accent)}
code{background:var(--bg3);border:1px solid var(--border);padding:1px 5px;border-radius:3px;font-size:12.5px;color:var(--accent2)}
pre{background:var(--bg2);border:1px solid var(--border);padding:12px 14px;border-radius:6px;overflow-x:auto;margin:14px 0}
pre code{background:none;border:none;padding:0;font-size:12.5px;color:var(--text-soft)}
blockquote{border-left:3px solid var(--accent);padding:10px 14px;background:var(--bg2);
           margin:14px 0;color:var(--text-soft);font-style:italic;border-radius:0 6px 6px 0}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:12.5px;border:1px solid var(--border);
      background:var(--bg2);border-radius:6px;overflow:hidden}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--border)}
th{background:var(--bg3);color:var(--accent);font-weight:600;font-size:11px;letter-spacing:.04em;text-transform:uppercase}
hr{border:none;border-top:1px dashed var(--border);margin:24px 0}
.entry-list{display:flex;flex-direction:column;gap:0;border-top:1px solid var(--border)}
.entry-card{display:block;padding:18px 0;border-bottom:1px solid var(--border);color:inherit}
.entry-card:hover{background:var(--bg2);border-radius:0}
.entry-card h3{color:var(--text);font-size:15px;font-weight:600;margin-bottom:4px}
.entry-card:hover h3{color:var(--accent2)}
.entry-card .meta{color:var(--muted);font-size:11px;letter-spacing:.04em}
.entry-card .pills{margin-top:8px;display:flex;gap:6px}
.pill{font-size:10px;padding:2px 8px;border-radius:10px;border:1px solid currentColor;letter-spacing:.05em}
.pill.pub{color:var(--pub)} .pill.priv{color:var(--priv)} .pill.mixed{color:var(--accent3)}
[data-visibility="private"]{position:relative;background:var(--priv-bg);border:1px solid var(--priv-border);
  border-left:3px solid var(--priv);padding:14px 16px 14px 20px;margin:16px 0;border-radius:0 6px 6px 0}
[data-visibility="private"]::before{content:"🔒 PRIVATE — internal only";display:block;
  font-size:9.5px;letter-spacing:.14em;color:var(--priv);font-weight:700;margin-bottom:8px}
[data-visibility="public"]{padding:0;margin:0;border:none;background:transparent}
[data-visibility="public"]:hover{background:rgba(124,106,247,0.04)}
section[data-visibility]{position:relative}
.block-controls{position:absolute;top:6px;right:6px;display:none;gap:4px;z-index:5}
section[data-visibility]:hover .block-controls{display:flex}
.block-controls .btn{padding:3px 8px;font-size:10px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;padding:14px;background:var(--bg2);
         border:1px solid var(--border);border-radius:8px;margin-bottom:24px}
.toolbar .group{display:flex;gap:6px;align-items:center}
.toolbar .group .label{font-size:10px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-right:4px}
.toolbar select{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 8px;
                border-radius:4px;font-family:inherit;font-size:12px;outline:none;cursor:pointer}
.toolbar select:focus{border-color:var(--accent)}
.toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:var(--bg3);
       border:1px solid var(--border);padding:10px 18px;border-radius:6px;font-size:12px;z-index:99;
       opacity:0;transition:opacity .25s;pointer-events:none}
.toast.show{opacity:1}
.toast.ok{border-color:var(--success);color:var(--success)}
.toast.err{border-color:var(--priv);color:var(--priv)}
.lint-row{padding:8px 12px;background:var(--bg2);border:1px solid var(--warn);border-left:3px solid var(--warn);
          border-radius:0 6px 6px 0;margin:6px 0;font-size:12px;color:var(--text-soft)}
.lint-row .pat{color:var(--warn);font-weight:600}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,0.7);display:none;align-items:center;justify-content:center;z-index:200}
.modal-bg.show{display:flex}
.modal{background:var(--bg);border:1px solid var(--border2);padding:20px;border-radius:8px;width:min(720px,92vw);max-height:80vh;display:flex;flex-direction:column;gap:12px}
.modal h2{margin:0;color:var(--accent2)}
.modal textarea{flex:1;min-height:320px;background:var(--bg2);border:1px solid var(--border);color:var(--text);
                font-family:inherit;font-size:12px;padding:12px;border-radius:5px;outline:none;resize:vertical;line-height:1.55}
.modal textarea:focus{border-color:var(--accent)}
.modal .row{display:flex;gap:8px;justify-content:flex-end}
"""

_TOGGLE_JS = r"""
(function(){
  const KEY="devblog-mode";
  const btn=document.querySelector(".toggle-mode");
  if(!btn) return;
  function apply(m){
    document.body.dataset.mode=m;
    const lab=btn.querySelector(".label");
    if(lab) lab.textContent=m==="public"?"Public preview":"Internal view";
    try{localStorage.setItem(KEY,m)}catch(e){}
  }
  let saved="internal";
  try{saved=localStorage.getItem(KEY)||"internal"}catch(e){}
  apply(saved);
  btn.addEventListener("click",()=>apply(document.body.dataset.mode==="public"?"internal":"public"));
})();
"""

_ENTRY_JS = r"""
(function(){
  const path = document.body.dataset.path;
  function toast(msg, kind){
    const t=document.createElement("div");
    t.className="toast "+(kind||"ok");
    t.textContent=msg; document.body.appendChild(t);
    requestAnimationFrame(()=>t.classList.add("show"));
    setTimeout(()=>{t.classList.remove("show");setTimeout(()=>t.remove(),300)},1800);
  }
  async function setVisibility(paraId, target){
    const r = await fetch("/api/visibility", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({path, para_id:paraId, target})
    });
    if(!r.ok){ toast("save failed","err"); return; }
    const data = await r.json();
    if(!data.changed){ toast("no change"); return; }
    toast("saved · reloading");
    setTimeout(()=>location.reload(),300);
  }
  document.addEventListener("click", e=>{
    const b = e.target.closest("[data-action]");
    if(!b) return;
    const action = b.dataset.action;
    if(action==="set-private" || action==="set-public"){
      const sec = b.closest("section[data-visibility]");
      const paraId = sec.dataset.paraId;
      setVisibility(paraId, action==="set-private"?"private":"public");
    }
  });
  // header visibility selector
  const hsel = document.querySelector("#header-visibility");
  if(hsel){
    hsel.addEventListener("change", async ()=>{
      const r = await fetch("/api/header-visibility", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({path, value:hsel.value})
      });
      if(r.ok){ toast("header updated · reloading"); setTimeout(()=>location.reload(),300); }
      else toast("save failed","err");
    });
  }
  // export buttons
  async function showExport(format){
    const url = "/export?format="+encodeURIComponent(format)+"&path="+encodeURIComponent(path);
    const r = await fetch(url);
    if(!r.ok){ toast("export failed","err"); return; }
    const text = await r.text();
    document.querySelector("#export-text").value = text;
    document.querySelector("#export-title").textContent = "export · "+format;
    document.querySelector("#export-modal").classList.add("show");
  }
  document.querySelectorAll("[data-export]").forEach(b=>{
    b.addEventListener("click", ()=>showExport(b.dataset.export));
  });
  document.querySelector("#export-close")?.addEventListener("click", ()=>{
    document.querySelector("#export-modal").classList.remove("show");
  });
  document.querySelector("#export-copy")?.addEventListener("click", async ()=>{
    const ta = document.querySelector("#export-text");
    ta.select();
    try{ await navigator.clipboard.writeText(ta.value); toast("copied to clipboard"); }
    catch(e){ document.execCommand("copy"); toast("copied to clipboard"); }
  });
})();
"""


# ----- HTML rendering --------------------------------------------------------

def _layout(title: str, body: str, *, body_data: dict[str, str] | None = None) -> str:
    extra_attrs = ""
    if body_data:
        for k, v in body_data.items():
            extra_attrs += f' data-{k}="{html.escape(v)}"'
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html.escape(title)} — DevBlog</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body data-mode="internal"{extra_attrs}>
<header class="site"><div class="shell">
  <div class="brand"><span class="logo">devblog</span><span class="tag">review</span></div>
  <nav class="site">
    <a href="/">entries</a>
    <button class="toggle-mode" type="button" title="Toggle public preview">
      <span class="dot"></span><span class="label">Internal view</span>
    </button>
  </nav>
</div></header>
<main><div class="shell">
{body}
</div></main>
<script src="/static/toggle.js"></script>
<script src="/static/entry.js"></script>
</body></html>"""


def _render_index(entries: list[dict[str, Any]]) -> str:
    cards = []
    for e in entries:
        pill_cls = {"public": "pub", "private": "priv", "mixed": "mixed"}.get(e["visibility"], "mixed")
        stats = e["stats"]
        cards.append(f"""
        <a class="entry-card" href="/entry?path={urllib.parse.quote(e['path'])}">
          <h3>{html.escape(e['title'])}</h3>
          <div class="meta">{html.escape(e['path'])} · modified {e['mtime']}</div>
          <div class="pills">
            <span class="pill {pill_cls}">{e['visibility']}</span>
            <span class="pill" style="color:var(--muted)">{stats['public_blocks']} public · {stats['private_blocks']} private</span>
          </div>
        </a>""")
    body = f"""
    <h1>DevBlog entries</h1>
    <p style="color:var(--muted);margin-bottom:24px">
      Click an entry to review, tag paragraphs, or export.
      Toggle <strong>Public preview</strong> in the header to hide private blocks.
    </p>
    <div class="entry-list">
      {''.join(cards) if cards else '<p style="color:var(--muted);padding:18px 0">No entries yet. Run <code>devblog entry</code>.</p>'}
    </div>
    """
    return _layout("entries", body)


def _render_entry(*, path: str, md: str, doc: vis.Document, lint: list[vis.LintFinding]) -> str:
    # Build per-block HTML with hover controls.
    block_html_parts: list[str] = []
    for b in doc.blocks:
        inner = vis._md_to_html_simple(b.text)
        if b.visibility == "private":
            controls = '<div class="block-controls"><button class="btn pub" data-action="set-public">→ public</button></div>'
        else:
            controls = '<div class="block-controls"><button class="btn priv" data-action="set-private">→ private</button></div>'
        block_html_parts.append(
            f'<section data-visibility="{b.visibility}" data-para-id="{b.para_id}">{controls}{inner}</section>'
        )
    blocks_html = "\n".join(block_html_parts)

    title = _extract_title(md) or path

    lint_html = ""
    if lint:
        rows = "\n".join(
            f'<div class="lint-row">line {f.line}: <span class="pat">{html.escape(f.pattern)}</span> — {html.escape(f.snippet[:140])}</div>'
            for f in lint[:30]
        )
        lint_html = f"""
        <h2>Lint warnings</h2>
        <p style="color:var(--muted);font-size:12px">
          Risky terms found in non-private blocks. Either rephrase, or wrap the block as private.
        </p>
        {rows}
        """

    vis_options = "".join(
        f'<option value="{v}"{" selected" if v == doc.visibility else ""}>{v}</option>'
        for v in ("public", "private", "mixed")
    )

    toolbar = f"""
    <div class="toolbar">
      <div class="group">
        <span class="label">entry</span>
        <select id="header-visibility">{vis_options}</select>
      </div>
      <div class="group">
        <span class="label">stats</span>
        <span style="color:var(--text-soft);font-size:12px">
          {doc.stats()['public_blocks']} public · {doc.stats()['private_blocks']} private
        </span>
      </div>
      <div style="flex:1"></div>
      <div class="group">
        <span class="label">export</span>
        <button class="btn" data-export="public-md">public md</button>
        <button class="btn" data-export="public-html">public html</button>
        <button class="btn" data-export="substack-html">substack</button>
        <button class="btn" data-export="raw-md">raw md</button>
      </div>
    </div>
    """

    body = f"""
    <p style="margin-bottom:16px"><a href="/">← all entries</a></p>
    <h1>{html.escape(title)}</h1>
    <p style="color:var(--muted);font-size:12px;margin-bottom:18px">{html.escape(path)}</p>
    {toolbar}
    {blocks_html}
    {lint_html}

    <div class="modal-bg" id="export-modal">
      <div class="modal">
        <h2 id="export-title">export</h2>
        <p style="color:var(--muted);font-size:12px;margin:0">
          Private blocks are stripped. Copy the text or paste it into your destination.
        </p>
        <textarea id="export-text" readonly></textarea>
        <div class="row">
          <button class="btn" id="export-close">close</button>
          <button class="btn primary" id="export-copy">copy to clipboard</button>
        </div>
      </div>
    </div>
    """
    return _layout(title, body, body_data={"path": path})


def _extract_title(md: str) -> str | None:
    m = re.search(r"^#\s+(.+?)\s*$", md, re.MULTILINE)
    return m.group(1).strip() if m else None


# ----- substack-flavored HTML ------------------------------------------------

def render_substack_html(md: str) -> str:
    """Substack accepts pasted rich text. We strip private blocks and emit a
    paste-friendly HTML fragment without our visibility chrome.
    """
    public_md = vis.strip_private(md)
    # Strip the operational/provenance bits Substack readers don't want.
    public_md = re.sub(r"^---\s*$.*\Z", "", public_md, flags=re.DOTALL | re.MULTILINE)
    public_md = re.sub(r"^##\s+Provenance\s*$.*?(?=^##\s|\Z)", "", public_md, flags=re.DOTALL | re.MULTILINE)
    # Drop the metadata bullets (Generated, Window, Repo, Visibility, Tracker mode).
    public_md = re.sub(
        r"^- (?:Generated|Window|Repo|Visibility|Tracker mode):[^\n]*\n",
        "",
        public_md,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    # Render and strip the visibility data attributes.
    body_html = vis._md_to_html_simple(public_md)
    body_html = re.sub(r' data-visibility="[^"]*"', "", body_html)
    body_html = re.sub(r' data-para-id="[^"]*"', "", body_html)
    body_html = re.sub(r"<section[^>]*>|</section>", "", body_html)
    return body_html.strip()


# ----- request handler -------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    server_version = "DevBlogReview/0.1"
    repo_root: Path = Path(".")
    entry_root: Path = Path(".devblog/entries")

    # Reduce log noise.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    # ---- helpers ----
    def _send(self, code: int, body: bytes, *, content_type: str = "text/html; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, text: str, *, content_type: str = "text/html; charset=utf-8") -> None:
        self._send(code, text.encode("utf-8"), content_type=content_type)

    def _send_json(self, code: int, obj: Any) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), content_type="application/json")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def _resolve(self, rel: str) -> Path | None:
        rel = rel.lstrip("/")
        candidate = (self.repo_root / rel).resolve()
        try:
            candidate.relative_to(self.repo_root.resolve())
        except ValueError:
            return None
        return candidate

    def _list_entries(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not self.entry_root.exists():
            return out
        for p in sorted(self.entry_root.glob("**/*.md")):
            try:
                md = p.read_text(encoding="utf-8")
            except OSError:
                continue
            doc = vis.parse(md)
            out.append({
                "path": str(p.relative_to(self.repo_root)),
                "title": _extract_title(md) or p.name,
                "visibility": doc.visibility,
                "stats": doc.stats(),
                "mtime": _fmt_mtime(p),
            })
        out.sort(key=lambda e: e["mtime"], reverse=True)
        return out

    # ---- GET ----
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/" or parsed.path == "/index.html":
            self._send_text(200, _render_index(self._list_entries()))
            return

        if parsed.path == "/static/style.css":
            self._send_text(200, _CSS, content_type="text/css; charset=utf-8")
            return
        if parsed.path == "/static/toggle.js":
            self._send_text(200, _TOGGLE_JS, content_type="application/javascript; charset=utf-8")
            return
        if parsed.path == "/static/entry.js":
            self._send_text(200, _ENTRY_JS, content_type="application/javascript; charset=utf-8")
            return

        if parsed.path == "/entry":
            rel = (params.get("path") or [""])[0]
            target = self._resolve(rel)
            if not target or not target.exists():
                self._send_text(404, "<p>entry not found</p>")
                return
            md = target.read_text(encoding="utf-8")
            doc = vis.parse(md)
            findings = vis.lint(md)
            self._send_text(200, _render_entry(path=rel, md=md, doc=doc, lint=findings))
            return

        if parsed.path == "/api/lint":
            rel = (params.get("path") or [""])[0]
            target = self._resolve(rel)
            if not target or not target.exists():
                self._send_json(404, {"error": "not_found"})
                return
            md = target.read_text(encoding="utf-8")
            findings = vis.lint(md)
            self._send_json(200, {"findings": [
                {"line": f.line, "pattern": f.pattern, "snippet": f.snippet, "block": f.block_visibility}
                for f in findings
            ]})
            return

        if parsed.path == "/export":
            rel = (params.get("path") or [""])[0]
            fmt = (params.get("format") or ["public-md"])[0]
            target = self._resolve(rel)
            if not target or not target.exists():
                self._send_text(404, "not found", content_type="text/plain")
                return
            md = target.read_text(encoding="utf-8")
            if fmt == "raw-md":
                out = md
                ct = "text/markdown; charset=utf-8"
            elif fmt == "public-md":
                out = vis.strip_private(md)
                ct = "text/markdown; charset=utf-8"
            elif fmt == "public-html":
                public_md = vis.strip_private(md)
                out = vis._md_to_html_simple(public_md)
                ct = "text/html; charset=utf-8"
            elif fmt == "substack-html":
                out = render_substack_html(md)
                ct = "text/html; charset=utf-8"
            else:
                self._send_text(400, "unknown format", content_type="text/plain")
                return
            self._send_text(200, out, content_type=ct)
            return

        self._send_text(404, "<p>not found</p>")

    # ---- POST ----
    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/visibility":
            data = self._read_json()
            rel = data.get("path", "")
            para_id = data.get("para_id", "")
            target = data.get("target", "")
            if target not in ("public", "private"):
                self._send_json(400, {"error": "bad_target"})
                return
            f = self._resolve(rel)
            if not f or not f.exists():
                self._send_json(404, {"error": "not_found"})
                return
            md = f.read_text(encoding="utf-8")
            new_md, changed = vis.set_block_visibility(md, para_id, target)
            if changed:
                f.write_text(new_md, encoding="utf-8")
                # Auto-update header visibility based on new content state.
                doc = vis.parse(new_md)
                priv_count = sum(1 for b in doc.blocks if b.visibility == "private")
                pub_count = sum(1 for b in doc.blocks if b.visibility == "public")
                if priv_count == 0:
                    new_md = vis.set_header_visibility(new_md, "public")
                elif pub_count == 0:
                    new_md = vis.set_header_visibility(new_md, "private")
                else:
                    new_md = vis.set_header_visibility(new_md, "mixed")
                f.write_text(new_md, encoding="utf-8")
            self._send_json(200, {"changed": changed})
            return

        if parsed.path == "/api/header-visibility":
            data = self._read_json()
            rel = data.get("path", "")
            value = data.get("value", "")
            f = self._resolve(rel)
            if not f or not f.exists():
                self._send_json(404, {"error": "not_found"})
                return
            md = f.read_text(encoding="utf-8")
            new_md = vis.set_header_visibility(md, value)
            f.write_text(new_md, encoding="utf-8")
            self._send_json(200, {"ok": True})
            return

        self._send_json(404, {"error": "not_found"})


def _fmt_mtime(p: Path) -> str:
    import datetime as dt
    ts = p.stat().st_mtime
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def serve(repo_root: Path, entry_root: Path, host: str = "127.0.0.1", port: int = 8780) -> None:
    """Start the local review server. Blocks until Ctrl-C."""
    handler = type("HandlerBound", (_Handler,), {"repo_root": repo_root, "entry_root": entry_root})
    srv = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"devblog review server: {url}", flush=True)
    print(f"  repo:    {repo_root}", flush=True)
    print(f"  entries: {entry_root}", flush=True)
    print("  Ctrl-C to stop.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
