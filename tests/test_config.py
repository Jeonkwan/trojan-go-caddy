from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from trojan_go_caddy.config import build_config


def test_build_config_generates_password(tmp_path: Path) -> None:
    config = build_config(
        overrides={
            "domain": "example.com",
            "directories": {"base_dir": tmp_path},
        },
    )
    assert config.domain == "example.com"
    assert config.trojan_password
    assert config.directories.base_dir == tmp_path


def test_build_config_from_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        dedent(
            f"""
            domain: demo.example
            trojan_password: secret
            directories:
              base_dir: {tmp_path}
            """
        ).strip(),
        encoding="utf-8",
    )
    config = build_config(file_path=config_file)
    assert config.domain == "demo.example"
    assert config.trojan_password == "secret"
    assert config.directories.base_dir == tmp_path


def test_render_context_contains_ssl_paths(tmp_path: Path) -> None:
    config = build_config(
        overrides={
            "domain": "site.example",
            "directories": {"base_dir": tmp_path},
        },
    )
    context = config.render_context()
    assert context["ssl_cert_path"].endswith("site.example.crt")
    assert context["ssl_key_path"].endswith("site.example.key")
