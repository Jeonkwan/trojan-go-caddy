from __future__ import annotations

from trojan_go_caddy import dns


class DummyResponse:
    def __init__(self) -> None:
        self.status_code = 200
        self.text = "<ok />"

    def raise_for_status(self) -> None:
        return None


class DummySession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def get(self, url: str, params: dict[str, str], timeout: float):
        self.calls.append((url, params, timeout))
        return DummyResponse()


def test_build_update_params() -> None:
    params = dns.build_update_params(
        domain="example.com",
        subdomain="test",
        password="abc",
        ip="1.2.3.4",
    )
    assert params == {
        "host": "test",
        "domain": "example.com",
        "password": "abc",
        "ip": "1.2.3.4",
    }


def test_update_dns_dry_run() -> None:
    result = dns.update_dns(
        domain="example.com",
        subdomain="test",
        password="abc",
        ip="1.2.3.4",
        dry_run=True,
    )
    assert result.dry_run
    assert "example.com" in result.url


def test_update_dns_success() -> None:
    session = DummySession()
    result = dns.update_dns(
        domain="example.com",
        subdomain="test",
        password="abc",
        ip="1.2.3.4",
        session=session,
        retries=1,
    )
    assert not result.dry_run
    assert session.calls
    assert result.status_code == 200
