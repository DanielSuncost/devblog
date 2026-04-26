import json
from pathlib import Path

from devblog.cli import SUPPORTED_HOSTS, cmd_install_adapter
import argparse


def test_install_single_adapter_writes_hermes_files(tmp_path: Path):
    args = argparse.Namespace(repo=str(tmp_path), host="hermes", default_branch="main", force=False)

    assert cmd_install_adapter(args) == 0

    base = tmp_path / ".devblog" / "adapters" / "hermes"
    assert (base / "README.md").exists()
    prompt = (base / "cron-prompt.txt").read_text()
    assert f"Repository: {tmp_path.resolve()}" in prompt
    assert "devblog entry" in prompt

    cron = json.loads((base / "cronjob.example.json").read_text())
    assert cron["schedule"] == "every 12h"
    assert cron["enabled_toolsets"] == ["terminal", "file"]


def test_install_all_adapters_writes_each_supported_host(tmp_path: Path):
    args = argparse.Namespace(repo=str(tmp_path), host="all", default_branch="main", force=False)

    assert cmd_install_adapter(args) == 0

    for host in SUPPORTED_HOSTS:
        base = tmp_path / ".devblog" / "adapters" / host
        assert base.exists(), host
        assert (base / "README.md").exists(), host

    assert (tmp_path / ".devblog" / "adapters" / "charon" / "charon-devblog.tasks.yaml").exists()
    assert (tmp_path / ".devblog" / "adapters" / "pi-agent" / "pi-devblog.prompt.md").exists()
    assert (tmp_path / ".devblog" / "adapters" / "claude-code" / "CLAUDE.devblog.md").exists()
    assert (tmp_path / ".devblog" / "adapters" / "codex" / "AGENTS.devblog.md").exists()
