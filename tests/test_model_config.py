
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


def test_model_command_reports_host_specific_model_mapping(tmp_path):
    repo = make_repo(tmp_path)
    cfg = json.loads((repo / ".devblog" / "config.json").read_text())
    cfg["generation"] = {
        "default": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"},
        "hosts": {
            "hermes": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"},
            "claude-code": {"model": "haiku"},
            "codex": {"provider": "openrouter", "model": "openai/gpt-4.1-mini"},
            "opencode": {"model": "openrouter/google/gemini-2.0-flash-lite"},
            "pi-agent": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"},
            "charon": {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite"}
        }
    }
    (repo / ".devblog" / "config.json").write_text(json.dumps(cfg))

    out = run([sys.executable, str(CLI), "model", "--repo", str(repo), "--host", "hermes"], repo).stdout
    data = json.loads(out)
    assert data["host"] == "hermes"
    assert data["provider"] == "openrouter"
    assert data["model"] == "google/gemini-2.0-flash-lite"
    assert "Hermes" in data["adapter_hint"]

    out = run([sys.executable, str(CLI), "model", "--repo", str(repo), "--host", "claude-code"], repo).stdout
    data = json.loads(out)
    assert data["model"] == "haiku"
    assert "--model haiku" in data["adapter_hint"]


def test_entry_records_generation_model_in_provenance(tmp_path):
    repo = make_repo(tmp_path)
    cfg = json.loads((repo / ".devblog" / "config.json").read_text())
    cfg["generation"] = {"default": {"provider": "openrouter", "model": "cheap/model"}}
    (repo / ".devblog" / "config.json").write_text(json.dumps(cfg))

    (repo / "x.py").write_text("print('x')\n")
    run(["git", "add", "x.py"], repo)
    run(["git", "commit", "-m", "add x"], repo)
    result = run([sys.executable, str(CLI), "entry", "--repo", str(repo), "--host", "hermes"], repo)
    md = Path(result.stdout.strip()).read_text()
    assert "Generation host: hermes" in md
    assert "Generation provider: openrouter" in md
    assert "Generation model: cheap/model" in md
