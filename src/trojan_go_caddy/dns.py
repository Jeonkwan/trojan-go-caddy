"""Namecheap Dynamic DNS helper utilities."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass

import requests

LOGGER = logging.getLogger(__name__)
NAMECHEAP_ENDPOINT = "https://dynamicdns.park-your-domain.com/update"


@dataclass(frozen=True)
class DNSUpdateResult:
    """Represents the outcome of a Namecheap dynamic DNS request."""

    params: Mapping[str, str]
    status_code: int | None
    content: str | None
    dry_run: bool = False

    @property
    def url(self) -> str:
        """Return the URL that would be requested."""

        from urllib.parse import urlencode

        return f"{NAMECHEAP_ENDPOINT}?{urlencode(self.params)}"


def build_update_params(*, domain: str, subdomain: str, password: str, ip: str) -> dict[str, str]:
    """Return the parameters used for the dynamic DNS request."""

    return {
        "host": subdomain,
        "domain": domain,
        "password": password,
        "ip": ip,
    }


def update_dns(
    *,
    domain: str,
    subdomain: str,
    password: str,
    ip: str,
    dry_run: bool = False,
    retries: int = 3,
    backoff_factor: float = 1.0,
    session: requests.Session | None = None,
    timeout: float = 10.0,
) -> DNSUpdateResult:
    """Invoke the Namecheap dynamic DNS endpoint."""

    params = build_update_params(domain=domain, subdomain=subdomain, password=password, ip=ip)
    if dry_run:
        LOGGER.info("Skipping DNS update (dry run). Params=%s", params)
        return DNSUpdateResult(params=params, status_code=None, content=None, dry_run=True)

    sess = session or requests.Session()
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = sess.get(NAMECHEAP_ENDPOINT, params=params, timeout=timeout)
            response.raise_for_status()
            LOGGER.info("Updated Namecheap DNS for %s.%s", subdomain, domain)
            return DNSUpdateResult(
                params=params,
                status_code=response.status_code,
                content=response.text,
                dry_run=False,
            )
        except requests.RequestException as exc:
            last_exc = exc
            LOGGER.warning(
                "DNS update attempt %s/%s failed: %s", attempt, retries, exc, exc_info=True
            )
            if attempt == retries:
                raise
            time.sleep(backoff_factor * attempt)
    # This line is never reached because of the raise above, but satisfies the type checker.
    raise RuntimeError("DNS update failed") from last_exc
