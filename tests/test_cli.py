from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from trojan_go_caddy import cli


def test_configure_generates_files(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "configure",
            "--domain",
            "demo.example",
            "--base-dir",
            str(tmp_path),
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.stdout

    caddy_file = tmp_path / "caddy" / "Caddyfile"
    assert caddy_file.exists()
    assert "demo.example" in caddy_file.read_text(encoding="utf-8")

    trojan_config = tmp_path / "trojan-go" / "config.json"
    assert trojan_config.exists()

    docker_compose = tmp_path / "docker-compose.yml"
    assert docker_compose.exists()

    index_html = tmp_path / "wwwroot" / "trojan" / "index.html"
    assert index_html.exists()

    ssl_dir = tmp_path / "ssl" / "demo.example"
    assert ssl_dir.exists()

    log_file = tmp_path / "wwwroot" / "caddy.log"
    assert log_file.exists()
    assert log_file.read_text(encoding="utf-8") == ""


def test_bootstrap_generates_files_and_runs_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded: dict[str, object] = {}

    def fake_run(compose_path: Path, *, detach: bool) -> None:
        recorded["compose_path"] = compose_path
        recorded["detach"] = detach

    monkeypatch.setattr(cli, "_run_docker_compose", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "bootstrap",
            "--base-dir",
            str(tmp_path),
            "--run-compose",
        ],
        env={"TROJAN_GO_CADDY_DOMAIN": "bootstrap.example"},
    )

    assert result.exit_code == 0, result.stdout
    assert recorded == {
        "compose_path": tmp_path / "docker-compose.yml",
        "detach": True,
    }
    assert (tmp_path / "caddy" / "Caddyfile").exists()


def test_bootstrap_requires_docker_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TROJAN_GO_CADDY_DOMAIN", "no-socket.example")
    monkeypatch.setattr(cli, "_has_docker_access", lambda: False)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["bootstrap", "--base-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "Docker socket not available" in result.stderr


def test_has_docker_access_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCKER_HOST", "tcp://docker.example:2375")
    assert cli._has_docker_access()


def test_has_docker_access_detects_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCKER_HOST", raising=False)

    def fake_exists(path: str) -> bool:
        assert path == "/var/run/docker.sock"
        return True

    def fake_stat(path: str) -> os.stat_result | SimpleNamespace:
        assert path == "/var/run/docker.sock"
        return SimpleNamespace(st_mode=stat.S_IFSOCK)

    monkeypatch.setattr(os.path, "exists", fake_exists)
    monkeypatch.setattr(os, "stat", fake_stat)

    assert cli._has_docker_access()
