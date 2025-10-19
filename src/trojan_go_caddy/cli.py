"""Command line interface for managing Trojan-Go + Caddy assets."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import requests
import typer
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import ValidationError

from .config import AppConfig, build_config
from .dns import update_dns

app = typer.Typer(help="Generate configuration and manage Trojan-Go + Caddy assets.")
docker_app = typer.Typer(help="Wrapper commands around docker compose.")
app.add_typer(docker_app, name="docker")


def _jinja_env() -> Environment:
    env = Environment(
        loader=PackageLoader("trojan_go_caddy", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters.setdefault("tojson", json.dumps)
    return env


def _collect_overrides(**kwargs: Any) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    directories: dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        if key in {
            "base_dir",
            "caddy_dir",
            "trojan_go_dir",
            "wwwroot_dir",
            "ssl_dir",
            "compose_path",
        }:
            directories[key] = str(value)
        else:
            overrides[key] = value
    if directories:
        overrides["directories"] = directories
    return overrides


def _write_file(path: Path, content: str, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise typer.BadParameter(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _render_assets(config_obj: AppConfig, *, overwrite: bool) -> None:
    env = _jinja_env()
    context = config_obj.render_context()
    dirs = config_obj.directories.resolved()

    template_targets = {
        "caddy/Caddyfile.j2": dirs.caddy_dir / "Caddyfile",
        "trojan_go/config.json.j2": dirs.trojan_go_dir / "config.json",
        "wwwroot/index.html.j2": dirs.wwwroot_dir / "trojan" / "index.html",
        "docker-compose.yml.j2": dirs.compose_path,
    }

    for template_name, output_path in template_targets.items():
        template = env.get_template(template_name)
        rendered = template.render(context)
        _write_file(output_path, rendered, overwrite=overwrite)
        typer.echo(f"Wrote {output_path}")

    log_path = dirs.wwwroot_dir / "caddy.log"
    if not log_path.exists() or overwrite:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
        typer.echo(f"Initialised log file {log_path}")

    if config_obj.pingpong_html_url:
        html_path = dirs.wwwroot_dir / "trojan" / "index.html"
        response = requests.get(config_obj.pingpong_html_url, timeout=10)
        response.raise_for_status()
        html_path.write_text(response.text, encoding="utf-8")
        typer.echo(f"Downloaded HTML asset from {config_obj.pingpong_html_url}")

    config_obj.ssl_domain_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Prepared SSL directory {config_obj.ssl_domain_dir}")


def _has_docker_access() -> bool:
    """Return ``True`` when the docker socket or host endpoint is reachable."""

    if os.environ.get("DOCKER_HOST"):
        return True
    socket_path = "/var/run/docker.sock"
    if not os.path.exists(socket_path):
        return False
    try:
        socket_stat = os.stat(socket_path)
    except FileNotFoundError:
        return False
    return stat.S_ISSOCK(socket_stat.st_mode)


def _run_docker_compose(compose_path: Path, *, detach: bool) -> None:
    if not _has_docker_access():
        typer.secho(
            "Docker socket not available. Mount /var/run/docker.sock or use --no-run-compose.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    command = ["docker", "compose", "-f", str(compose_path), "up"]
    if detach:
        command.append("-d")
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:  # pragma: no cover - surfaced to CLI
        typer.secho("docker CLI not found inside the container.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover - surfaced to CLI
        raise typer.Exit(code=exc.returncode) from exc


@app.command()
def configure(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a YAML configuration file.",
    ),
    domain: str | None = typer.Option(
        None,
        "--domain",
        help="Fully qualified domain name.",
    ),
    trojan_password: str | None = typer.Option(
        None,
        "--trojan-password",
        help="Pre-shared key used by Trojan-Go clients.",
    ),
    base_dir: Path = typer.Option(
        Path.cwd(),
        "--base-dir",
        help="Base directory for generated files.",
    ),
    caddy_dir: Path | None = typer.Option(
        None,
        "--caddy-dir",
        help="Override Caddy configuration directory.",
    ),
    trojan_go_dir: Path | None = typer.Option(
        None,
        "--trojan-go-dir",
        help="Override Trojan-Go configuration directory.",
    ),
    wwwroot_dir: Path | None = typer.Option(
        None,
        "--wwwroot-dir",
        help="Override wwwroot directory.",
    ),
    ssl_dir: Path | None = typer.Option(
        None,
        "--ssl-dir",
        help="Override SSL certificate directory.",
    ),
    compose_path: Path | None = typer.Option(
        None,
        "--compose-path",
        help="Location to write docker-compose.yml.",
    ),
    local_addr: str = typer.Option(
        "0.0.0.0",
        "--local-addr",
        help="Bind address for Trojan-Go.",
    ),
    local_port: int = typer.Option(
        443,
        "--local-port",
        help="Local port for Trojan-Go.",
    ),
    remote_addr: str = typer.Option(
        "caddy",
        "--remote-addr",
        help="Caddy upstream hostname.",
    ),
    remote_port: int = typer.Option(
        80,
        "--remote-port",
        help="Caddy upstream port.",
    ),
    caddy_root: str = typer.Option(
        "/usr/src/trojan",
        "--caddy-root",
        help="Caddy site root inside container.",
    ),
    caddy_log: str = typer.Option(
        "/usr/src/caddy.log",
        "--caddy-log",
        help="Caddy log path inside container.",
    ),
    mux_enabled: bool = typer.Option(
        True,
        "--mux/--no-mux",
        help="Toggle Trojan-Go MUX.",
    ),
    pingpong_html_url: str | None = typer.Option(
        None,
        "--pingpong-html-url",
        help="Download external HTML instead of bundled template.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing files.",
    ),
) -> None:
    """Render configuration files from templates."""

    if domain is None and config is None and "TROJAN_GO_CADDY_DOMAIN" not in os.environ:
        domain = typer.prompt("Domain name (e.g. example.com)")

    overrides = _collect_overrides(
        domain=domain,
        trojan_password=trojan_password,
        base_dir=base_dir,
        caddy_dir=caddy_dir,
        trojan_go_dir=trojan_go_dir,
        wwwroot_dir=wwwroot_dir,
        ssl_dir=ssl_dir,
        compose_path=compose_path,
        local_addr=local_addr,
        local_port=local_port,
        remote_addr=remote_addr,
        remote_port=remote_port,
        caddy_root=caddy_root,
        caddy_log=caddy_log,
        mux_enabled=mux_enabled,
        pingpong_html_url=pingpong_html_url,
    )

    try:
        config_obj = build_config(file_path=config, overrides=overrides)
    except ValidationError as exc:  # pragma: no cover - defensive, surfaced to CLI
        raise typer.BadParameter(str(exc)) from exc

    _render_assets(config_obj, overwrite=overwrite)


@app.command()
def bootstrap(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Optional path to a YAML configuration file.",
    ),
    base_dir: Path = typer.Option(
        Path("/data"),
        "--base-dir",
        help="Base directory to render files inside the container.",
    ),
    overwrite: bool = typer.Option(
        True,
        "--overwrite/--no-overwrite",
        help="Allow replacing previously generated files.",
    ),
    run_compose: bool = typer.Option(
        True,
        "--run-compose/--no-run-compose",
        help="Run `docker compose up` after rendering assets.",
    ),
    detach: bool = typer.Option(
        True,
        "--detach/--no-detach",
        help="Run docker compose in detached mode when `--run-compose` is enabled.",
    ),
) -> None:
    """Render assets using environment defaults and optionally start the stack."""

    overrides = _collect_overrides(base_dir=base_dir)

    try:
        config_obj = build_config(file_path=config, overrides=overrides)
    except ValidationError as exc:  # pragma: no cover - defensive, surfaced to CLI
        raise typer.BadParameter(str(exc)) from exc

    _render_assets(config_obj, overwrite=overwrite)

    if run_compose:
        _run_docker_compose(config_obj.directories.resolved().compose_path, detach=detach)


@app.command("dns-update")
def dns_update(
    domain: str = typer.Option(
        ...,
        "--domain",
        help="Registered domain, e.g. example.com.",
    ),
    subdomain: str = typer.Option(
        ...,
        "--subdomain",
        help="Host record to update.",
    ),
    password: str = typer.Option(
        ...,
        "--password",
        help="Namecheap dynamic DNS password.",
    ),
    ip: str = typer.Option(
        ...,
        "--ip",
        help="IP address to assign.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Only print the request without sending it.",
    ),
) -> None:
    """Update Namecheap Dynamic DNS records."""

    result = update_dns(
        domain=domain,
        subdomain=subdomain,
        password=password,
        ip=ip,
        dry_run=dry_run,
    )
    if dry_run:
        typer.echo(f"Dry run: {result.url}")
    else:
        typer.echo(f"Updated DNS ({result.status_code}): {result.url}")


@app.command()
def validate(
    config: Path = typer.Option(
        None,
        "--config",
        help="Validate a configuration file.",
    ),
) -> None:
    """Validate configuration from file and environment."""

    build_config(file_path=config)
    typer.echo("Configuration is valid.")


@docker_app.command("up")
def docker_up(
    compose_path: Path = typer.Option(
        Path("docker-compose.yml"),
        "--compose-path",
        help="Compose file path.",
    ),
    detach: bool = typer.Option(
        True,
        "--detach/--no-detach",
        help="Run docker compose in detached mode.",
    ),
) -> None:
    """Execute `docker compose up`."""

    _run_docker_compose(compose_path, detach=detach)


@docker_app.command("down")
def docker_down(
    compose_path: Path = typer.Option(
        Path("docker-compose.yml"),
        "--compose-path",
        help="Compose file path.",
    ),
) -> None:
    """Execute `docker compose down`."""

    command = ["docker", "compose", "-f", str(compose_path), "down"]
    subprocess.run(command, check=True)


def main() -> None:  # pragma: no cover - convenience wrapper
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
