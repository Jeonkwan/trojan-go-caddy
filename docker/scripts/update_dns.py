#!/usr/bin/env python3
"""Update Namecheap dynamic DNS records using repository configuration."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

NAMECHEAP_ENDPOINT = "https://dynamicdns.park-your-domain.com/update"
REQUIRED_KEYS = ("DNS_HOST", "DNS_DOMAIN", "NAMECHEAP_DDNS_PASSWORD")


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a dotenv-style file into a dictionary."""
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid line in {path}: {raw_line!r}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]
        values[key] = value
    return values


def load_dns_config(env_file: Path) -> Dict[str, str]:
    """Load DNS-related values from a dotenv file and environment overrides."""
    file_values = parse_env_file(env_file)
    config: Dict[str, str] = {}

    for key in REQUIRED_KEYS:
        value = os.environ.get(key, file_values.get(key, "")).strip()
        if value:
            config[key] = value

    missing = [key for key in REQUIRED_KEYS if key not in config]
    if missing:
        formatted = ", ".join(missing)
        raise SystemExit(f"Missing required DNS configuration values: {formatted}")

    return config


def build_update_params(host: str, domain: str, password: str, ip: Optional[str]) -> Dict[str, str]:
    params = {"host": host, "domain": domain, "password": password}
    if ip:
        params["ip"] = ip
    return params


def perform_update(host: str, domain: str, password: str, *, ip: Optional[str], timeout: float = 10.0) -> str:
    params = build_update_params(host, domain, password, ip)
    url = f"{NAMECHEAP_ENDPOINT}?{urlencode(params)}"
    with urlopen(url, timeout=timeout) as response:  # nosec: B310 Namecheap DDNS uses HTTPS
        payload = response.read().decode("utf-8", errors="replace")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=".env",
        type=Path,
        help="Path to the dotenv file that stores DNS credentials.",
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=None,
        help="Optional IP address to set for the record. Defaults to the caller's public IP.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the request that would be sent without making any network calls.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_dns_config(args.env_file)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1

    host = config["DNS_HOST"]
    domain = config["DNS_DOMAIN"]
    password = config["NAMECHEAP_DDNS_PASSWORD"]

    if args.dry_run:
        params = build_update_params(host, domain, password, args.ip)
        safe_params = {**params, "password": "***redacted***"}
        print("[dns] Dry run - would request:")
        print(f"        {NAMECHEAP_ENDPOINT}?{urlencode(safe_params)}")
        return 0

    try:
        payload = perform_update(host, domain, password, ip=args.ip)
    except URLError as exc:  # pragma: no cover - exercised via error handling
        print(f"[dns] Failed to update DNS: {exc}", file=sys.stderr)
        return 2

    print(f"[dns] Updated Namecheap record for {host}.{domain}")
    print(payload.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
