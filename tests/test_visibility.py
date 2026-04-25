import json
import subprocess
import sys
from pathlib import Path

import pytest

from devblog import visibility as vis

CLI = Path(__file__).resolve().parents[1] / "src" / "devblog" / "cli.py"


def run(cmd, cwd, check=True):
    result = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(map(str, cmd))}\nSTDOUT={result.stdout}\nSTDERR={result.stderr}")
    return result


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    run(["git", "config", "user.email", "t@example.com"], repo)
    run(["git", "config", "user.name", "T"], repo)
    (repo / "README.md").write_text("# r\n")
    run(["git", "add", "README.md"], repo)
    run(["git", "commit", "-m", "init"], repo)
    run([sys.executable, str(CLI), "init", "--repo", str(repo)], repo)
    (repo / ".devblog" / "entries").mkdir(parents=True, exist_ok=True)
    return repo


# ----- pure parsing/transform unit tests -------------------------------------

def test_parse_pure_public_has_no_private_blocks():
    md = "# t\n\nA paragraph.\n\nAnother one.\n"
    doc = vis.parse(md)
    assert doc.visibility == "public"
    assert all(b.visibility == "public" for b in doc.blocks)
    assert len(doc.blocks) >= 1


def test_parse_with_private_block_marks_mixed():
    md = (
        "# t\n\n"
        "Public para.\n\n"
        "<!-- vis:private -->\n"
        "Secret para.\n"
        "<!-- /vis -->\n\n"
        "Another public para.\n"
    )
    doc = vis.parse(md)
    assert doc.visibility == "mixed"
    pub = [b for b in doc.blocks if b.visibility == "public"]
    priv = [b for b in doc.blocks if b.visibility == "private"]
    # Unmarked regions are split into paragraph-level blocks: heading,
    # "Public para.", "Another public para." → 3 public; 1 private.
    assert len(pub) == 3 and len(priv) == 1
    assert "Secret para" in priv[0].text
    assert any("Public para." == b.text for b in pub)
    assert any("Another public para." == b.text for b in pub)


def test_header_bullet_overrides_inferred_visibility():
    md = "# t\n\n- Visibility: private\n\nUnmarked content here.\n"
    assert vis.parse(md).visibility == "private"


def test_strip_private_removes_block_and_inline():
    md = (
        "# t\n\n"
        "Stay <span class=\"vis-priv\">go away</span> stay.\n\n"
        "<!-- vis:private -->\nGone.\n<!-- /vis -->\n\n"
        "Tail.\n"
    )
    out = vis.strip_private(md)
    assert "Gone." not in out
    assert "go away" not in out
    assert "Stay  stay." in out or "Stay stay." in out
    assert "Tail." in out


def test_strip_private_rewrites_visibility_bullet_to_public():
    md = "# t\n- Visibility: mixed\n\n<!-- vis:private -->\nx\n<!-- /vis -->\n\nbody\n"
    out = vis.strip_private(md)
    assert "- Visibility: public" in out
    assert "- Visibility: mixed" not in out


def test_set_block_visibility_round_trips():
    md = "# t\n\nFirst para.\n\nSecond para.\n"
    doc = vis.parse(md)
    target = next(b for b in doc.blocks if "Second" in b.text)
    md2, changed = vis.set_block_visibility(md, target.para_id, "private")
    assert changed
    assert "<!-- vis:private -->" in md2
    assert "Second para." in md2
    # Re-parse and flip back to public.
    doc2 = vis.parse(md2)
    same = next(b for b in doc2.blocks if "Second" in b.text)
    assert same.visibility == "private"
    md3, changed2 = vis.set_block_visibility(md2, same.para_id, "public")
    assert changed2
    assert "<!-- vis:private -->" not in md3
    assert "Second para." in md3


def test_lint_flags_moat_outside_private_block():
    md = (
        "# t\n\n"
        "This is the moat we are building.\n\n"
        "<!-- vis:private -->\nThe moat is here too but private.\n<!-- /vis -->\n"
    )
    findings = vis.lint(md)
    assert any("moat" in f.snippet.lower() and f.block_visibility == "public" for f in findings)
    # The private occurrence should NOT be reported.
    assert not any(f.block_visibility == "private" for f in findings)


def test_set_header_visibility_inserts_when_missing():
    md = "# Title\n\nbody\n"
    out = vis.set_header_visibility(md, "mixed")
    assert "- Visibility: mixed" in out


def test_set_header_visibility_replaces_existing():
    md = "# t\n\n- Generated: 2026\n- Visibility: public\n\nbody\n"
    out = vis.set_header_visibility(md, "private")
    assert "- Visibility: private" in out
    assert out.count("Visibility:") == 1


# ----- CLI integration tests -------------------------------------------------

def write_entry(repo: Path, name: str, body: str) -> Path:
    p = repo / ".devblog" / "entries" / name
    p.write_text(body)
    return p


def test_cli_visibility_command_sets_header(tmp_path):
    repo = make_repo(tmp_path)
    entry = write_entry(
        repo, "20260425T120000Z-devlog.md",
        "# t\n\n- Generated: now\n- Visibility: public\n\nA paragraph.\n",
    )
    run([sys.executable, str(CLI), "visibility", "--repo", str(repo), "--value", "mixed"], repo)
    md = entry.read_text()
    assert "- Visibility: mixed" in md


def test_cli_publish_public_md_strips_private(tmp_path):
    repo = make_repo(tmp_path)
    entry = write_entry(
        repo, "20260425T120000Z-devlog.md",
        "# t\n\n- Visibility: mixed\n\nVisible.\n\n<!-- vis:private -->\nHidden.\n<!-- /vis -->\n",
    )
    result = run(
        [sys.executable, str(CLI), "publish", "--repo", str(repo), "--entry", str(entry), "--format", "public-md"],
        repo,
    )
    assert "Visible." in result.stdout
    assert "Hidden." not in result.stdout
    assert "<!-- vis:private -->" not in result.stdout


def test_cli_publish_substack_html_drops_metadata(tmp_path):
    repo = make_repo(tmp_path)
    entry = write_entry(
        repo, "20260425T120000Z-devlog.md",
        "# Title\n\n- Generated: 2026-04-25T12:00:00Z\n- Window: a → b\n- Visibility: mixed\n\nBody.\n",
    )
    result = run(
        [sys.executable, str(CLI), "publish", "--repo", str(repo), "--entry", str(entry), "--format", "substack-html"],
        repo,
    )
    assert "<h1>Title</h1>" in result.stdout
    assert "Body." in result.stdout
    assert "Generated" not in result.stdout
    assert "Visibility" not in result.stdout


def test_cli_lint_strict_returns_nonzero_on_findings(tmp_path):
    repo = make_repo(tmp_path)
    write_entry(
        repo, "20260425T120000Z-devlog.md",
        "# t\n\nHere is our moat.\n",
    )
    res = run(
        [sys.executable, str(CLI), "lint", "--repo", str(repo), "--strict"],
        repo, check=False,
    )
    assert res.returncode != 0


def test_cli_visibility_flips_block_by_para_id(tmp_path):
    repo = make_repo(tmp_path)
    entry = write_entry(
        repo, "20260425T120000Z-devlog.md",
        "# t\n\n- Visibility: public\n\nFirst para we will hide.\n\nSecond para we keep.\n",
    )
    md = entry.read_text()
    target = next(b for b in vis.parse(md).blocks if "First" in b.text)
    run(
        [sys.executable, str(CLI), "visibility", "--repo", str(repo),
         "--para-id", target.para_id, "--value", "private"],
        repo,
    )
    md2 = entry.read_text()
    assert "<!-- vis:private -->" in md2
    assert "Second para we keep." in md2
    # Header should now read mixed.
    assert "- Visibility: mixed" in md2
