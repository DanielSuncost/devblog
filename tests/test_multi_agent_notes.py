
import json
import subprocess
import sys
from pathlib import Path

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
    run(["git", "config", "user.email", "test@example.com"], repo)
    run(["git", "config", "user.name", "Tester"], repo)
    (repo / "README.md").write_text("# repo\n")
    run(["git", "add", "README.md"], repo)
    run(["git", "commit", "-m", "initial"], repo)
    run([sys.executable, str(CLI), "init", "--repo", str(repo)], repo)
    return repo


def test_agent_note_records_supported_host_area_and_message(tmp_path):
    repo = make_repo(tmp_path)

    run([
        sys.executable, str(CLI), "note", "--repo", str(repo),
        "--host", "claude-code", "--agent", "frontend-agent",
        "--area", "frontend", "--message", "Implemented dashboard shell."
    ], repo)

    ledger = (repo / ".devblog" / "ledger.jsonl").read_text().splitlines()
    note = [json.loads(line) for line in ledger if json.loads(line).get("type") == "agent_note"][-1]
    assert note["host"] == "claude-code"
    assert note["agent"] == "frontend-agent"
    assert note["area"] == "frontend"
    assert note["message"] == "Implemented dashboard shell."
    assert note["tag"] == "claude-code/frontend-agent/frontend"


def test_agent_note_can_infer_agent_area_and_task_from_context_file(tmp_path):
    repo = make_repo(tmp_path)
    context = repo / "conversation.txt"
    context.write_text("I am the backend shade working on API auth routes and database migrations.")

    run([
        sys.executable, str(CLI), "note", "--repo", str(repo),
        "--host", "pi-agent", "--context-file", str(context)
    ], repo)

    ledger = (repo / ".devblog" / "ledger.jsonl").read_text().splitlines()
    note = [json.loads(line) for line in ledger if json.loads(line).get("type") == "agent_note"][-1]
    assert note["host"] == "pi-agent"
    assert note["agent"] == "backend-shade"
    assert note["area"] == "backend"
    assert "API auth routes" in note["message"]


def test_entry_includes_multi_agent_notes_from_window(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "frontend.py").write_text("print('ui')\n")
    run(["git", "add", "frontend.py"], repo)
    run(["git", "commit", "-m", "add frontend"], repo)
    run([sys.executable, str(CLI), "track", "--repo", str(repo), "--once"], repo)
    run([sys.executable, str(CLI), "note", "--repo", str(repo), "--host", "opencode", "--agent", "frontend", "--area", "frontend", "--message", "Built the UI shell."], repo)
    run([sys.executable, str(CLI), "note", "--repo", str(repo), "--host", "codex", "--agent", "backend", "--area", "backend", "--message", "Prepared API contract."], repo)

    result = run([sys.executable, str(CLI), "entry", "--repo", str(repo)], repo)
    entry_path = Path(result.stdout.strip())
    md = entry_path.read_text()

    assert "## Agent notes" in md
    assert "`opencode/frontend/frontend`" in md
    assert "Built the UI shell." in md
    assert "`codex/backend/backend`" in md
    assert "Prepared API contract." in md


def test_note_rejects_unknown_host_and_lists_supported_hosts(tmp_path):
    repo = make_repo(tmp_path)
    result = run([sys.executable, str(CLI), "note", "--repo", str(repo), "--host", "unknown", "--message", "x"], repo, check=False)
    assert result.returncode != 0
    assert "pi-agent" in result.stderr
    assert "hermes" in result.stderr
    assert "claude-code" in result.stderr
    assert "codex" in result.stderr
    assert "opencode" in result.stderr
    assert "charon" in result.stderr



def test_note_can_append_to_existing_entry(tmp_path):
    repo = make_repo(tmp_path)
    entry_dir = repo / ".devblog" / "entries"
    entry_dir.mkdir(parents=True, exist_ok=True)
    entry = entry_dir / "entry.md"
    entry.write_text("# Existing\n\nBody.\n")

    run([
        sys.executable, str(CLI), "note", "--repo", str(repo),
        "--host", "charon", "--agent", "research", "--area", "research",
        "--message", "Added paper notes.", "--entry", "latest"
    ], repo)

    md = entry.read_text()
    assert "## Agent notes" in md
    assert "`charon/research/research`" in md
    assert "Added paper notes." in md
