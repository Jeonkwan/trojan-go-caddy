"""Unit tests for the configuration rendering utilities."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "docker" / "scripts" / "render.py"


_spec = importlib.util.spec_from_file_location("render", SCRIPT_PATH)
render = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader  # Narrow type checking complaints.
_spec.loader.exec_module(render)  # type: ignore[attr-defined]


def test_parse_env_file_handles_comments_and_quotes(tmp_path: Path) -> None:
    env_file = tmp_path / "sample.env"
    env_file.write_text(
        """
        # Comment to ignore
        DOMAIN = example.com
        EMAIL='admin@example.com'
        TROJAN_PASSWORD="super-secret"
        EXTRA = value with spaces
        """
    )

    values = render.parse_env_file(env_file)

    assert values == {
        "DOMAIN": "example.com",
        "EMAIL": "admin@example.com",
        "TROJAN_PASSWORD": "super-secret",
        "EXTRA": "value with spaces",
    }


def test_load_context_requires_mandatory_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "empty.env"
    env_file.write_text("")

    for key in render.REQUIRED_KEYS:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(SystemExit) as exc:
        render.load_context(env_file)

    assert "Missing required configuration values" in str(exc.value)


def test_load_context_normalises_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "config.env"
    env_file.write_text(
        "\n".join(
            [
                "DOMAIN=example.com",
                "EMAIL=admin@example.com",
                "TROJAN_PASSWORD=password",
                "WEBSOCKET_PATH=custom/path",
                "TROJAN_PORT=8000",
            ]
        )
    )

    monkeypatch.setenv("TROJAN_PORT", "443")
    monkeypatch.delenv("WEBSOCKET_PATH", raising=False)

    context = render.load_context(env_file)

    assert context["WEBSOCKET_PATH"] == "/custom/path"
    assert context["TROJAN_PORT"] == "443"


def test_render_templates_and_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "stack.env"
    env_file.write_text(
        "\n".join(
            [
                "DOMAIN=example.com",
                "EMAIL=admin@example.com",
                "TROJAN_PASSWORD=password",
            ]
        )
    )

    for key in ("DOMAIN", "EMAIL", "TROJAN_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    context = render.load_context(env_file)

    output_dir = tmp_path / "rendered"
    render.render_templates(context, output_dir)
    render.copy_assets(output_dir)

    caddyfile = output_dir / "caddy" / "Caddyfile"
    trojan_config = output_dir / "trojan-go" / "config.json"
    index_html = output_dir / "wwwroot" / "index.html"

    assert "example.com {" in caddyfile.read_text()
    trojan_contents = trojan_config.read_text()
    assert '"local_port": 8443' in trojan_contents
    assert '"path": "/trojan"' in trojan_contents
    assert index_html.exists()

    # The render step should be idempotent; running it again overwrites files cleanly.
    render.render_templates(context, output_dir)
    render.copy_assets(output_dir)

    assert caddyfile.read_text().startswith("example.com {")
    assert index_html.exists()
