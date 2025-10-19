"""Trojan-Go + Caddy deployment helper CLI."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("trojan-go-caddy")
except PackageNotFoundError:  # pragma: no cover - handled during installation only
    __version__ = "0.0.0"

__all__ = ["__version__"]
