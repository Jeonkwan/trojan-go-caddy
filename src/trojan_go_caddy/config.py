"""Configuration models and loaders for the Trojan-Go + Caddy CLI."""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

ENV_PREFIX = "TROJAN_GO_CADDY_"


@dataclass(frozen=True)
class DirectoryPaths:
    base_dir: Path
    caddy_dir: Path
    trojan_go_dir: Path
    wwwroot_dir: Path
    ssl_dir: Path
    compose_path: Path


class DirectorySettings(BaseModel):
    """Filesystem locations used by the CLI."""

    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    caddy_dir: Path | None = None
    trojan_go_dir: Path | None = None
    wwwroot_dir: Path | None = None
    ssl_dir: Path | None = None
    compose_path: Path | None = None

    @model_validator(mode="after")
    def _apply_defaults(self) -> DirectorySettings:
        base = self.base_dir
        if self.caddy_dir is None:
            self.caddy_dir = base / "caddy"
        if self.trojan_go_dir is None:
            self.trojan_go_dir = base / "trojan-go"
        if self.wwwroot_dir is None:
            self.wwwroot_dir = base / "wwwroot"
        if self.ssl_dir is None:
            self.ssl_dir = base / "ssl"
        if self.compose_path is None:
            self.compose_path = base / "docker-compose.yml"
        return self

    def resolved(self) -> DirectoryPaths:
        return DirectoryPaths(
            base_dir=self.base_dir,
            caddy_dir=self.caddy_dir or self.base_dir / "caddy",
            trojan_go_dir=self.trojan_go_dir or self.base_dir / "trojan-go",
            wwwroot_dir=self.wwwroot_dir or self.base_dir / "wwwroot",
            ssl_dir=self.ssl_dir or self.base_dir / "ssl",
            compose_path=self.compose_path or self.base_dir / "docker-compose.yml",
        )

    def to_dict(self) -> dict[str, str]:
        """Return a JSON serialisable representation."""

        resolved = self.resolved()
        return {
            "base_dir": str(resolved.base_dir),
            "caddy_dir": str(resolved.caddy_dir),
            "trojan_go_dir": str(resolved.trojan_go_dir),
            "wwwroot_dir": str(resolved.wwwroot_dir),
            "ssl_dir": str(resolved.ssl_dir),
            "compose_path": str(resolved.compose_path),
        }


class AppConfig(BaseModel):
    """Application configuration built from CLI args, files, or the environment."""

    domain: str
    trojan_password: str | None = None
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    pingpong_html_url: str | None = None

    local_addr: str = "0.0.0.0"
    local_port: int = 443
    remote_addr: str = "caddy"
    remote_port: int = 80
    caddy_root: str = "/usr/src/trojan"
    caddy_log: str = "/usr/src/caddy.log"
    mux_enabled: bool = True

    @model_validator(mode="after")
    def _ensure_password(self) -> AppConfig:
        if not self.trojan_password:
            self.trojan_password = str(uuid.uuid4())
        return self

    @property
    def ssl_domain_dir(self) -> Path:
        return self.directories.resolved().ssl_dir / self.domain

    @property
    def ssl_cert_path(self) -> Path:
        return self.ssl_domain_dir / f"{self.domain}.crt"

    @property
    def ssl_key_path(self) -> Path:
        return self.ssl_domain_dir / f"{self.domain}.key"

    def render_context(self) -> dict[str, Any]:
        """Context dictionary consumed by the Jinja templates."""

        resolved_dirs = self.directories.resolved()
        return {
            "domain": self.domain,
            "trojan_password": self.trojan_password,
            "local_addr": self.local_addr,
            "local_port": self.local_port,
            "remote_addr": self.remote_addr,
            "remote_port": self.remote_port,
            "ssl_cert_path": str(self.ssl_cert_path),
            "ssl_key_path": str(self.ssl_key_path),
            "ssl_sni": self.domain,
            "caddy_root": self.caddy_root,
            "caddy_log": self.caddy_log,
            "mux_enabled": self.mux_enabled,
            "directories": self.directories.to_dict(),
            "resolved_directories": {
                "base_dir": str(resolved_dirs.base_dir),
                "caddy_dir": str(resolved_dirs.caddy_dir),
                "trojan_go_dir": str(resolved_dirs.trojan_go_dir),
                "wwwroot_dir": str(resolved_dirs.wwwroot_dir),
                "ssl_dir": str(resolved_dirs.ssl_dir),
                "compose_path": str(resolved_dirs.compose_path),
            },
        }

    def merge(self, **overrides: Any) -> AppConfig:
        """Return a copy of the configuration updated with overrides."""

        return self.model_copy(update=overrides)


def _normalise_key(key: str) -> str:
    return key.lower().replace("-", "_")


def load_from_env(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Load configuration values from environment variables."""

    env = env or os.environ
    data: dict[str, Any] = {}
    for key, value in env.items():
        if not key.startswith(ENV_PREFIX):
            continue
        trimmed = key.removeprefix(ENV_PREFIX).lower()
        if trimmed.startswith("dir_"):
            directories = data.setdefault("directories", {})
            directories[_normalise_key(trimmed.removeprefix("dir_"))] = value
        else:
            data[_normalise_key(trimmed)] = value
    return data


def load_from_file(path: Path) -> dict[str, Any]:
    """Load configuration values from a YAML file."""

    if not path.exists():
        raise FileNotFoundError(f"Configuration file '{path}' does not exist")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return {}
    loaded = yaml.safe_load(content)
    if loaded is None:
        return {}
    if not isinstance(loaded, MutableMapping):
        raise ValueError("Configuration file must contain a mapping")
    return dict(loaded)


def _merge_dict(base: dict[str, Any], updates: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), Mapping):
            base[key] = _merge_dict(dict(base[key]), value)
        else:
            base[key] = value
    return base


def build_config(
    *,
    file_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> AppConfig:
    """Create an :class:`AppConfig` using layered sources."""

    data: dict[str, Any] = {}
    if file_path is not None:
        _merge_dict(data, load_from_file(file_path))
    env_data = load_from_env(env)
    _merge_dict(data, env_data)
    if overrides:
        _merge_dict(data, overrides)
    return AppConfig.model_validate(data)
