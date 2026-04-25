#!/usr/bin/env python3
"""Shared DevBlog CLI.

Portable across Pi Agent, Hermes, Claude Code, Codex, OpenCode, and Charon.
Uses only Python stdlib so every host agent can invoke it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "version": "1",
    "repo": {"path": ".", "default_branch": "main"},
    "tracking": {"mode": "background_daemon", "poll_interval_seconds": 60, "retention_days": 30, "capture": {"git_status": True, "commits": True, "diff_stats": True}},
    "schedule": {"cadence": "every 12h", "timezone": "UTC", "window_strategy": "from_last_successful_entry"},
    "content": {"audience": "internal", "style": "engineering-update", "max_words": 1000, "redaction": {"enabled": True, "patterns": [], "replacement": "[REDACTED]"}},
    "output": {"entry_dir": ".devblog/entries", "state_file": ".devblog/state.json", "ledger_file": ".devblog/ledger.jsonl", "index_file": ".devblog/INDEX.md"},
    "generation": {
        "default": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"},
        "hosts": {
            "hermes": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"},
            "charon": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"},
            "pi-agent": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"},
            "claude-code": {"model": "haiku"},
            "codex": {"provider": "openrouter", "model": "openai/gpt-4.1-mini"},
            "opencode": {"model": "openrouter/google/gemini-2.0-flash-lite"},
        },
    },
}


def utc() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(cmd: list[str], cwd: Path, check: bool = False) -> str:
    p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{p.stderr}")
    return p.stdout.strip()


def git(cwd: Path, *args: str) -> str:
    return run(["git", *args], cwd=cwd)


def load_config(repo: Path) -> dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    cfg_path = repo / ".devblog" / "config.json"
    example = repo / ".devblog" / "config.example.json"
    if cfg_path.exists():
        data = json.loads(cfg_path.read_text())
    elif example.exists():
        data = json.loads(example.read_text())
    else:
        data = {}
    return deep_merge(cfg, data)


def deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def path_from(repo: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else repo / p


def load_state(repo: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    p = path_from(repo, cfg["output"]["state_file"])
    if not p.exists():
        head = git(repo, "rev-parse", "HEAD") or ""
        return {"version":"1", "repo_path": str(repo), "tracker":{"status":"stopped", "last_poll_at":"", "cursor":{"head_sha":head, "last_seen_commit_sha":head}}, "last_entry": None, "history": []}
    return json.loads(p.read_text())


def save_state(repo: Path, cfg: dict[str, Any], state: dict[str, Any]) -> None:
    p = path_from(repo, cfg["output"]["state_file"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n")


def append_ledger(repo: Path, cfg: dict[str, Any], event: dict[str, Any]) -> None:
    p = path_from(repo, cfg["output"]["ledger_file"])
    p.parent.mkdir(parents=True, exist_ok=True)
    event.setdefault("at", utc())
    with p.open("a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def diff_stat(repo: Path, since: str, until: str) -> dict[str, Any]:
    raw = git(repo, "diff", "--numstat", f"{since}..{until}") if since and until and since != until else git(repo, "diff", "--numstat")
    files=[]; ins=0; dele=0
    for line in raw.splitlines():
        parts=line.split("\t")
        if len(parts)>=3:
            a,b,path=parts[0],parts[1],parts[2]
            ia=0 if a == '-' else int(a or 0); db=0 if b == '-' else int(b or 0)
            ins += ia; dele += db; files.append({"path":path,"insertions":ia,"deletions":db})
    return {"files": files, "files_changed": len(files), "insertions": ins, "deletions": dele}


def current_snapshot(repo: Path) -> dict[str, Any]:
    branch = git(repo, "branch", "--show-current")
    head = git(repo, "rev-parse", "HEAD")
    status = git(repo, "status", "--porcelain=v1")
    status_hash = hashlib.sha256(status.encode()).hexdigest()[:16]
    return {"branch": branch, "head": head, "status_hash": status_hash, "status": status.splitlines()[:200]}


def commits_between(repo: Path, since: str, until: str) -> list[dict[str, str]]:
    if not since or since == until:
        return []
    fmt = "%H%x1f%h%x1f%an%x1f%aI%x1f%s"
    raw = git(repo, "log", f"{since}..{until}", f"--pretty=format:{fmt}")
    out=[]
    for line in raw.splitlines():
        p=line.split("\x1f")
        if len(p)==5: out.append({"sha":p[0],"short":p[1],"author":p[2],"at":p[3],"subject":p[4]})
    return list(reversed(out))


SUPPORTED_HOSTS = ("pi-agent", "hermes", "claude-code", "codex", "opencode", "charon")
AREA_KEYWORDS = {
    "frontend": ("frontend", "ui", "ux", "dashboard", "react", "css", "tui", "textual"),
    "backend": ("backend", "api", "server", "database", "db", "auth", "migration", "daemon"),
    "research": ("research", "paper", "experiment", "benchmark", "analysis", "study"),
    "tests": ("test", "pytest", "spec", "regression", "coverage"),
    "docs": ("doc", "readme", "documentation", "blog", "devlog", "guide"),
    "devops": ("ci", "deploy", "docker", "infra", "workflow", "release"),
}


def validate_host(host: str) -> str:
    host = (host or "hermes").strip().lower()
    aliases = {"pi": "pi-agent", "claude": "claude-code", "claude_code": "claude-code", "open-code": "opencode"}
    host = aliases.get(host, host)
    if host not in SUPPORTED_HOSTS:
        raise ValueError(f"unsupported host: {host}. supported hosts: {', '.join(SUPPORTED_HOSTS)}")
    return host


def infer_area(text: str) -> str:
    low = text.lower()
    scores = {area: sum(1 for kw in kws if kw in low) for area, kws in AREA_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"


def infer_agent(text: str, area: str) -> str:
    low = text.lower()
    if "shade" in low:
        return f"{area}-shade" if area != "general" else "shade"
    for pat in (r"agent\s+([a-zA-Z0-9_-]+)", r"i am\s+(?:the\s+)?([a-zA-Z0-9_-]+)[\s-]+agent"):
        m = re.search(pat, low)
        if m:
            return m.group(1)
    return area if area != "general" else "agent"


def summarize_context(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return "No context supplied."
    # Prefer the phrase after "working on" if present, but keep original capitalization.
    m = re.search(r"working on\s+(.+?)(?:[.!?]\s|$)", compact, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()[:240]
    return compact[:240]


def infer_note_fields(args: argparse.Namespace) -> tuple[str, str, str]:
    context = ""
    if getattr(args, "context_file", None):
        context = Path(args.context_file).read_text(encoding="utf-8", errors="ignore")
    seed = " ".join(x for x in [getattr(args, "message", "") or "", context] if x)
    area = args.area or infer_area(seed)
    agent = args.agent or infer_agent(seed, area)
    message = args.message or summarize_context(context)
    return agent, area, message


def generation_for_host(cfg: dict[str, Any], host: str | None) -> dict[str, Any]:
    host = validate_host(host or "hermes")
    gen = cfg.get("generation", {})
    default = gen.get("default", {}) if isinstance(gen, dict) else {}
    hosts = gen.get("hosts", {}) if isinstance(gen, dict) else {}
    host_cfg = hosts.get(host, {}) if isinstance(hosts, dict) else {}
    # load_config deep-merges DEFAULT_CONFIG, so default host mappings are present
    # even when a project only configured generation.default. In that case, let
    # the project default win instead of silently re-applying built-in host defaults.
    builtin_default = DEFAULT_CONFIG.get("generation", {}).get("default", {})
    builtin_host = DEFAULT_CONFIG.get("generation", {}).get("hosts", {}).get(host, {})
    if default != builtin_default and host_cfg == builtin_host:
        host_cfg = {}
    merged = deep_merge(default, host_cfg)
    merged.setdefault("provider", None)
    merged.setdefault("model", None)
    merged["host"] = host
    merged["adapter_hint"] = adapter_hint(host, merged)
    return merged


def adapter_hint(host: str, gen: dict[str, Any]) -> str:
    provider = gen.get("provider")
    model = gen.get("model")
    if host == "hermes":
        return f"Hermes: use cron/model config or hermes chat --provider {provider} --model {model}."
    if host == "charon":
        return f"Charon: schedule the task with provider={provider} model={model}."
    if host == "pi-agent":
        return f"Pi Agent: configure provider={provider} and model={model} for the devblog task."
    if host == "claude-code":
        return f"Claude Code: run claude -p ... --model {model}."
    if host == "codex":
        return f"Codex: configure provider={provider} and run codex exec --model {model} where supported."
    if host == "opencode":
        return f"OpenCode: run opencode run ... --model {model}."
    return "Use the shared DevBlog CLI and pass the model through the host adapter."


def agent_notes_markdown(notes: list[dict[str, Any]]) -> str:
    if not notes:
        return "No agent notes were recorded for this window."
    rows = []
    for n in notes:
        vis = n.get("visibility", "public")
        msg = str(n.get("message", "")).replace("\n", " ").strip()
        row = f"- `{n.get('tag','')}` ({vis}): {msg}"
        if vis == "private":
            row = f"<!-- vis:private -->\n{row}\n<!-- /vis -->"
        rows.append(row)
    return "\n".join(rows)


def append_note_to_entry(entry: Path, event: dict[str, Any]) -> None:
    md = entry.read_text(encoding="utf-8")
    note_line = agent_notes_markdown([event])
    if "## Agent notes" not in md:
        insert = f"\n## Agent notes\n{note_line}\n"
        marker = "\n---\n\n## Provenance"
        if marker in md:
            md = md.replace(marker, insert + marker, 1)
        else:
            md = md.rstrip() + insert + "\n"
    else:
        # Append before the next section after Agent notes when possible.
        m = re.search(r"(## Agent notes\n)(.*?)(\n## |\n---\n|\Z)", md, flags=re.DOTALL)
        if m:
            body = m.group(2).rstrip()
            replacement = m.group(1) + body + "\n" + note_line + "\n" + m.group(3)
            md = md[:m.start()] + replacement + md[m.end():]
        else:
            md = md.rstrip() + "\n" + note_line + "\n"
    entry.write_text(md, encoding="utf-8")


def cmd_note(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve(); cfg = load_config(repo)
    try:
        host = validate_host(args.host)
    except ValueError as e:
        print(str(e), file=sys.stderr); return 2
    agent, area, message = infer_note_fields(args)
    visibility = args.visibility
    event = {
        "type": "agent_note",
        "host": host,
        "agent": agent,
        "area": area,
        "message": message,
        "visibility": visibility,
        "tag": f"{host}/{agent}/{area}",
    }
    if args.context_file:
        event["context_file"] = str(Path(args.context_file).resolve())
    append_ledger(repo, cfg, event)
    if args.entry:
        entry = _resolve_entry(repo, cfg, args.entry)
        append_note_to_entry(entry, event)
        event["entry_path"] = str(entry.relative_to(repo)) if str(entry).startswith(str(repo)) else str(entry)
    print(json.dumps(event, indent=2))
    return 0


def cmd_model(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve(); cfg = load_config(repo)
    try:
        gen = generation_for_host(cfg, args.host)
    except ValueError as e:
        print(str(e), file=sys.stderr); return 2
    print(json.dumps(gen, indent=2))
    return 0

def cmd_init(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    (repo/".devblog"/"entries").mkdir(parents=True, exist_ok=True)
    src = repo/".devblog"/"config.example.json"
    dst = repo/".devblog"/"config.json"
    if not dst.exists():
        cfg = DEFAULT_CONFIG.copy(); cfg["repo"] = {"path": str(repo), "default_branch": args.default_branch}
        dst.write_text(json.dumps(cfg, indent=2)+"\n")
    cfg=load_config(repo); state=load_state(repo,cfg); save_state(repo,cfg,state)
    print(f"initialized {repo}/.devblog")
    return 0


def track_once(repo: Path, cfg: dict[str, Any], state: dict[str, Any]) -> None:
    snap = current_snapshot(repo)
    cursor = state.setdefault("tracker", {}).setdefault("cursor", {})
    prev_head = cursor.get("head_sha") or snap["head"]
    prev_status = cursor.get("last_seen_status_hash")
    if snap["status_hash"] != prev_status:
        append_ledger(repo, cfg, {"type":"git_status", **snap})
    if snap["head"] != prev_head:
        for c in commits_between(repo, prev_head, snap["head"]):
            append_ledger(repo, cfg, {"type":"commit", **c})
        append_ledger(repo, cfg, {"type":"diff_stat", "since_ref": prev_head, "until_ref": snap["head"], **diff_stat(repo, prev_head, snap["head"])})
    state["tracker"] = {"status":"running", "last_poll_at": utc(), "cursor":{"head_sha":snap["head"], "last_seen_commit_sha":snap["head"], "last_seen_status_hash":snap["status_hash"]}}
    save_state(repo,cfg,state)


def cmd_track(args: argparse.Namespace) -> int:
    repo=Path(args.repo).resolve(); cfg=load_config(repo); state=load_state(repo,cfg)
    if args.once:
        track_once(repo,cfg,state); print("tracked once"); return 0
    interval=int(cfg.get("tracking",{}).get("poll_interval_seconds",60))
    print(f"devblog tracker running for {repo} every {interval}s", flush=True)
    while True:
        try: track_once(repo,cfg,load_state(repo,cfg))
        except Exception as e: append_ledger(repo,cfg,{"type":"tracker_error","error":str(e)})
        time.sleep(interval)


def recent_ledger(repo: Path, cfg: dict[str, Any], limit: int = 80) -> list[dict[str, Any]]:
    p=path_from(repo,cfg["output"]["ledger_file"])
    if not p.exists(): return []
    lines=p.read_text(errors="ignore").splitlines()[-limit:]
    out=[]
    for l in lines:
        try: out.append(json.loads(l))
        except Exception: pass
    return out


def render_entry(repo: Path, cfg: dict[str, Any], state: dict[str, Any], since: str, until: str, force: bool=False, host: str="hermes") -> tuple[str,str]:
    commits=commits_between(repo,since,until)
    stat=diff_stat(repo,since,until)
    payload={"since":since,"until":until,"commits":commits,"stat":stat}
    whash=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
    if not force:
        for h in state.get("history",[]):
            if h.get("window_hash")==whash and h.get("status")=="success":
                return "", whash
    generated=utc(); until_utc=generated.replace(":", "").replace("-", "")
    title=f"Devlog {since[:8]} → {until[:8]}"
    ledger=recent_ledger(repo,cfg)
    gen = generation_for_host(cfg, host)
    notes = [e for e in ledger if e.get("type") == "agent_note"]
    notes_md = agent_notes_markdown(notes)
    key_files=sorted(stat["files"], key=lambda x:x["insertions"]+x["deletions"], reverse=True)[:12]
    commit_table="\n".join(f"| `{c['short']}` | {c['author']} | {c['subject']} |" for c in commits) or "| — | — | No new commits in this window. |"
    file_table="\n".join(f"| `{f['path']}` | {f['insertions']}+/ {f['deletions']}- | High-churn file in this window. |" for f in key_files) or "| — | — | No tracked file changes. |"
    tldr=[
        f"- {len(commits)} commits observed between `{since[:8]}` and `{until[:8]}`.",
        f"- {stat['files_changed']} files changed with +{stat['insertions']} / -{stat['deletions']} lines.",
        f"- Background tracker recorded {len(ledger)} recent evidence events."
    ]
    changed = "This window primarily changed " + (", ".join(f"`{f['path']}`" for f in key_files[:5]) if key_files else "no committed files") + "."
    risks = "- Review high-churn files for accidental regressions.\n- Confirm tests cover the modified paths."
    tests_touched=sum(1 for f in stat['files'] if 'test' in f['path'].lower() or 'spec' in f['path'].lower())
    docs_touched=sum(1 for f in stat['files'] if f['path'].lower().endswith(('.md','.rst')) or '/docs/' in f['path'].lower())
    md=f"""# {title}

- Generated: {generated}
- Window: `{since}` → `{until}`
- Repo: `{repo.name}`
- Tracker mode: background_daemon
- Visibility: public

## TL;DR
{chr(10).join(tldr)}

## Development activity pulse (tracked in background)
- Active files touched: {stat['files_changed']}
- Commit events observed: {len(commits)}
- Test/build events observed: {sum(1 for e in ledger if e.get('type')=='test_event')}
- Largest churn area: `{key_files[0]['path'] if key_files else 'n/a'}`

## What changed
{changed}

### Key files
| File | Change type | Why it matters |
|---|---|---|
{file_table}

### Commits in window
| SHA | Author | Message |
|---|---|---|
{commit_table}

## Agent notes
{notes_md}

## Why it matters
These changes represent the concrete development activity captured in git, agent notes, and the background ledger for this window. The entry is intentionally evidence-first so another agent or developer can audit it later.

## Risks and follow-ups
- Risks:
{risks}
- Follow-ups:
- Run the project verification suite before publishing this as an external update.
- Add human narrative context if this entry is intended for a public audience.

## Metrics snapshot
- Files changed: {stat['files_changed']}
- Insertions: {stat['insertions']}
- Deletions: {stat['deletions']}
- Tests touched: {tests_touched}
- Docs touched: {docs_touched}

## Next window plan
Continue from the changed paths above; prioritize tests, documentation updates, and closing any TODOs surfaced by the active work.

---

## Provenance
- Dedupe key: commit_range
- Window hash: {whash}
- Redaction applied: false
- Generation host: {gen.get('host')}
- Generation provider: {gen.get('provider')}
- Generation model: {gen.get('model')}
"""
    return md, whash


def cmd_entry(args: argparse.Namespace) -> int:
    repo=Path(args.repo).resolve(); cfg=load_config(repo); state=load_state(repo,cfg)
    until=git(repo,"rev-parse","HEAD")
    since=args.since or ((state.get("last_entry") or {}).get("until_ref")) or git(repo,"rev-list","--max-parents=0","HEAD").splitlines()[0]
    md, whash=render_entry(repo,cfg,state,since,until,args.force,args.host)
    if not md:
        state.setdefault("history",[]).append({"at":utc(),"since_ref":since,"until_ref":until,"status":"skipped_duplicate","window_hash":whash})
        save_state(repo,cfg,state); print("skipped duplicate window"); return 0
    outdir=path_from(repo,cfg["output"]["entry_dir"]); outdir.mkdir(parents=True,exist_ok=True)
    filename=utc().replace(":","").replace("-","").replace("Z","Z")+"-devlog.md"
    path=outdir/filename; path.write_text(md)
    rec={"generated_at":utc(),"since_ref":since,"until_ref":until,"entry_path":str(path.relative_to(repo)),"window_hash":whash,"status":"success"}
    state["last_entry"]=rec; state.setdefault("history",[]).append({"at":rec["generated_at"],**rec})
    save_state(repo,cfg,state); append_ledger(repo,cfg,{"type":"entry",**rec})
    print(str(path))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    repo=Path(args.repo).resolve(); cfg=load_config(repo); state=load_state(repo,cfg)
    print(json.dumps({"repo":str(repo),"tracker":state.get("tracker"),"last_entry":state.get("last_entry"),"history_count":len(state.get("history",[]))}, indent=2))
    return 0


# --- visibility / publish / lint / review --------------------------------

def _entry_dir(repo: Path, cfg: dict[str, Any]) -> Path:
    return path_from(repo, cfg["output"]["entry_dir"])


def _resolve_entry(repo: Path, cfg: dict[str, Any], entry: str | None) -> Path:
    """Resolve an entry path. Accepts:
      - absolute path
      - path relative to repo
      - bare filename inside the entries dir
      - "latest" / None → most recently modified entry
    """
    edir = _entry_dir(repo, cfg)
    if not entry or entry == "latest":
        candidates = sorted(edir.glob("**/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError(f"no entries in {edir}")
        return candidates[0]
    p = Path(entry)
    if not p.is_absolute():
        if (repo / p).exists():
            p = repo / p
        elif (edir / p).exists():
            p = edir / p
        elif (edir / (p.name + ".md")).exists():
            p = edir / (p.name + ".md")
        else:
            p = (repo / p)
    if not p.exists():
        raise FileNotFoundError(f"entry not found: {entry}")
    return p.resolve()


def _import_local(name: str):
    """Import a sibling module in either package or script mode."""
    if __package__:
        from importlib import import_module
        return import_module(f"{__package__}.{name}")
    # Running as a plain script: ensure src/ is on the path then import.
    here = Path(__file__).resolve().parent
    parent = str(here.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    from importlib import import_module
    return import_module(f"devblog.{name}")


def cmd_visibility(args: argparse.Namespace) -> int:
    """Set entry header or per-block visibility."""
    vis_mod = _import_local("visibility")
    repo = Path(args.repo).resolve()
    cfg = load_config(repo)
    entry = _resolve_entry(repo, cfg, args.entry)
    md = entry.read_text(encoding="utf-8")

    if args.para_id:
        new_md, changed = vis_mod.set_block_visibility(md, args.para_id, args.value)
        if not changed:
            print(f"no change (para_id={args.para_id} already {args.value} or not found)")
            return 0
        # Refresh header automatically.
        doc = vis_mod.parse(new_md)
        priv = sum(1 for b in doc.blocks if b.visibility == "private")
        pub = sum(1 for b in doc.blocks if b.visibility == "public")
        header_value = "public" if priv == 0 else ("private" if pub == 0 else "mixed")
        new_md = vis_mod.set_header_visibility(new_md, header_value)
    else:
        if args.value not in ("public", "private", "mixed"):
            print("--value must be one of public|private|mixed when no --para-id is given", file=sys.stderr)
            return 2
        new_md = vis_mod.set_header_visibility(md, args.value)

    entry.write_text(new_md, encoding="utf-8")
    print(str(entry))
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    """Flag risky terms in non-private blocks of an entry (or all entries)."""
    vis_mod = _import_local("visibility")
    repo = Path(args.repo).resolve()
    cfg = load_config(repo)
    edir = _entry_dir(repo, cfg)
    targets: list[Path]
    if args.entry:
        targets = [_resolve_entry(repo, cfg, args.entry)]
    else:
        targets = sorted(edir.glob("**/*.md"))
    patterns = None
    if args.patterns:
        patterns = [p.strip() for p in args.patterns.split(",") if p.strip()]
    total = 0
    for t in targets:
        md = t.read_text(encoding="utf-8")
        findings = vis_mod.lint(md, patterns)
        if not findings:
            continue
        rel = t.relative_to(repo) if str(t).startswith(str(repo)) else t
        print(f"\n{rel}:")
        for f in findings:
            print(f"  line {f.line}: {f.pattern!r} in {f.block_visibility} block — {f.snippet[:100].strip()}")
        total += len(findings)
    if total == 0:
        print("no findings")
    elif args.strict:
        return 1
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Strip private content and emit the entry in the requested format."""
    vis_mod = _import_local("visibility")
    srv = _import_local("server")
    repo = Path(args.repo).resolve()
    cfg = load_config(repo)
    entry = _resolve_entry(repo, cfg, args.entry)
    md = entry.read_text(encoding="utf-8")

    # Optional pre-publish lint gate.
    if args.lint:
        findings = vis_mod.lint(md)
        if findings:
            for f in findings:
                print(f"lint: line {f.line}: {f.pattern!r} — {f.snippet[:100].strip()}", file=sys.stderr)
            print(f"refusing to publish due to {len(findings)} lint findings (drop --lint to override)", file=sys.stderr)
            return 1

    fmt = args.format
    if fmt == "raw-md":
        rendered = md
    elif fmt == "public-md":
        rendered = vis_mod.strip_private(md)
    elif fmt == "public-html":
        rendered = vis_mod._md_to_html_simple(vis_mod.strip_private(md))
    elif fmt == "substack-html":
        rendered = srv.render_substack_html(md)
    elif fmt == "clipboard":
        # Emit a self-contained HTML page suitable for paste into a rich-text editor.
        rendered = vis_mod._md_to_html_simple(vis_mod.strip_private(md))
        rendered = (
            "<!doctype html><meta charset='utf-8'>\n"
            + rendered
        )
    else:
        print(f"unknown format: {fmt}", file=sys.stderr)
        return 2

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = repo / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        print(str(out_path))
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Start the local review server."""
    srv = _import_local("server")
    repo = Path(args.repo).resolve()
    cfg = load_config(repo)
    edir = _entry_dir(repo, cfg)
    edir.mkdir(parents=True, exist_ok=True)
    srv.serve(repo_root=repo, entry_root=edir, host=args.host, port=args.port)
    return 0


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(prog="devblog", description="Cross-agent development blog tracker/generator")
    sub=ap.add_subparsers(dest="cmd", required=True)
    p=sub.add_parser("init"); p.add_argument("--repo", default="."); p.add_argument("--default-branch", default="main"); p.set_defaults(fn=cmd_init)
    p=sub.add_parser("track"); p.add_argument("--repo", default="."); p.add_argument("--once", action="store_true"); p.set_defaults(fn=cmd_track)
    p=sub.add_parser("entry"); p.add_argument("--repo", default="."); p.add_argument("--since"); p.add_argument("--force", action="store_true"); p.add_argument("--host", default="hermes", choices=SUPPORTED_HOSTS); p.set_defaults(fn=cmd_entry)
    p=sub.add_parser("status"); p.add_argument("--repo", default="."); p.set_defaults(fn=cmd_status)

    p = sub.add_parser("review", help="Open a local web UI to tag, toggle, and export entries")
    p.add_argument("--repo", default=".")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8780)
    p.set_defaults(fn=cmd_review)

    p = sub.add_parser("visibility", help="Set entry header or per-block visibility")
    p.add_argument("--repo", default=".")
    p.add_argument("--entry", help="Entry path or 'latest' (default)")
    p.add_argument("--para-id", dest="para_id", help="Block id to flip (omit to set the header bullet only)")
    p.add_argument("--value", required=True, choices=["public", "private", "mixed"])
    p.set_defaults(fn=cmd_visibility)

    p = sub.add_parser("lint", help="Flag risky terms in non-private blocks")
    p.add_argument("--repo", default=".")
    p.add_argument("--entry", help="Entry path; if omitted, lints every entry")
    p.add_argument("--patterns", help="Comma-separated regex overrides")
    p.add_argument("--strict", action="store_true", help="Exit non-zero if any findings")
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("publish", help="Strip private content and export an entry")
    p.add_argument("--repo", default=".")
    p.add_argument("--entry", help="Entry path or 'latest' (default)")
    p.add_argument(
        "--format",
        default="public-md",
        choices=["public-md", "public-html", "substack-html", "raw-md", "clipboard"],
        help="Output format",
    )
    p.add_argument("--output", "-o", help="Write to file (default: stdout)")
    p.add_argument("--lint", action="store_true", help="Refuse to publish if lint warnings remain")
    p.set_defaults(fn=cmd_publish)

    p = sub.add_parser("note", help="Append a tagged multi-agent note to the DevBlog ledger")
    p.add_argument("--repo", default=".")
    p.add_argument("--host", required=True, help="Host agent framework: " + ", ".join(SUPPORTED_HOSTS))
    p.add_argument("--agent", help="Agent identity/name; inferred from context when omitted")
    p.add_argument("--area", help="Work area such as frontend/backend/research; inferred when omitted")
    p.add_argument("--message", help="Note text; inferred from --context-file when omitted")
    p.add_argument("--context-file", help="Conversation/context file used to infer agent, area, and note")
    p.add_argument("--entry", help="Optional entry path/'latest' to append this note into an existing post")
    p.add_argument("--visibility", default="public", choices=["public", "private"])
    p.set_defaults(fn=cmd_note)

    p = sub.add_parser("model", help="Show host-specific generation model/provider mapping")
    p.add_argument("--repo", default=".")
    p.add_argument("--host", required=True, help="Host agent framework: " + ", ".join(SUPPORTED_HOSTS))
    p.set_defaults(fn=cmd_model)

    args=ap.parse_args(argv); return args.fn(args)

if __name__ == "__main__":
    raise SystemExit(main())
