"""Unit tests for the Namecheap DNS update helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.error import URLError

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "docker" / "scripts" / "update_dns.py"

_spec = importlib.util.spec_from_file_location("update_dns", SCRIPT_PATH)
update_dns = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(update_dns)  # type: ignore[attr-defined]


def test_load_dns_config_requires_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "dns.env"
    env_file.write_text("")

    for key in update_dns.REQUIRED_KEYS:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(SystemExit) as exc:
        update_dns.load_dns_config(env_file)

    assert "Missing required DNS configuration values" in str(exc.value)


def test_build_update_params_includes_optional_ip() -> None:
    params = update_dns.build_update_params("@", "example.com", "secret", "1.2.3.4")
    assert params == {
        "host": "@",
        "domain": "example.com",
        "password": "secret",
        "ip": "1.2.3.4",
    }


def test_perform_update_invokes_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    responses: list[str] = []

    class FakeHandle:
        def __init__(self, body: str) -> None:
            self.body = body.encode()

        def __enter__(self) -> "FakeHandle":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - nothing to do
            return None

        def read(self) -> bytes:
            return self.body

    def fake_urlopen(url: str, timeout: float) -> FakeHandle:
        responses.append(url)
        return FakeHandle("<interface-response>OK</interface-response>")

    monkeypatch.setattr(update_dns, "urlopen", fake_urlopen)

    payload = update_dns.perform_update("@", "example.com", "secret", ip=None)

    assert payload == "<interface-response>OK</interface-response>"
    assert responses
    assert "dynamicdns.park-your-domain.com/update" in responses[0]


def test_main_handles_url_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env_file = tmp_path / "dns.env"
    env_file.write_text(
        "\n".join(
            [
                "DNS_HOST=@",
                "DNS_DOMAIN=example.com",
                "NAMECHEAP_DDNS_PASSWORD=secret",
            ]
        )
    )

    def failing_update(*args, **kwargs):
        raise URLError("boom")

    monkeypatch.setattr(update_dns, "perform_update", failing_update)
    monkeypatch.setattr(update_dns.sys, "argv", ["prog", "--env-file", str(env_file)])

    exit_code = update_dns.main()

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "Failed to update DNS" in captured.err
