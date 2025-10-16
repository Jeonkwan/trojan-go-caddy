#!/usr/bin/env python3
"""Render configuration templates for the Trojan-Go + Caddy stack.

This script loads variables from a dotenv-style file and the environment,
then renders the templates under ``docker/config`` into the ``rendered``
directory. It also copies the static site assets that Caddy will serve.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "config"
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"

REQUIRED_KEYS = ("DOMAIN", "EMAIL", "TROJAN_PASSWORD")
OPTIONAL_DEFAULTS = {
    "WEBSOCKET_PATH": "/trojan",
    "TROJAN_PORT": "8443",
}


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


def load_context(env_file: Path) -> Dict[str, str]:
    """Combine values from the env file and current environment."""
    context = {**OPTIONAL_DEFAULTS, **parse_env_file(env_file)}

    # Allow environment variables to override values from the file.
    for key, value in os.environ.items():
        if key in context or key in REQUIRED_KEYS:
            context[key] = value

    missing = [key for key in REQUIRED_KEYS if not context.get(key)]
    if missing:
        formatted = ", ".join(missing)
        raise SystemExit(f"Missing required configuration values: {formatted}")

    websocket_path = context.get("WEBSOCKET_PATH", "/trojan")
    if not websocket_path.startswith("/"):
        websocket_path = "/" + websocket_path
    context["WEBSOCKET_PATH"] = websocket_path

    trojan_port = context.get("TROJAN_PORT", "8443")
    try:
        context["TROJAN_PORT"] = str(int(trojan_port))
    except ValueError as exc:
        raise SystemExit("TROJAN_PORT must be an integer") from exc

    return context


def render_templates(context: Dict[str, str], output_dir: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )

    mappings = {
        "Caddyfile.j2": output_dir / "caddy" / "Caddyfile",
        "trojan-go.json.j2": output_dir / "trojan-go" / "config.json",
    }

    for template_name, target_path in mappings.items():
        template = env.get_template(template_name)
        rendered = template.render(
            domain=context["DOMAIN"],
            email=context["EMAIL"],
            trojan_password=context["TROJAN_PASSWORD"],
            websocket_path=context["WEBSOCKET_PATH"],
            trojan_port=context["TROJAN_PORT"],
        )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(rendered)
        print(f"[render] Wrote {target_path.relative_to(output_dir)}")


def copy_assets(output_dir: Path) -> None:
    destination = output_dir / "wwwroot"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(ASSET_DIR, destination)
    print(f"[render] Copied static assets to {destination.relative_to(output_dir)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=".env",
        type=Path,
        help="Path to the dotenv file containing configuration values.",
    )
    parser.add_argument(
        "--output-dir",
        default="rendered",
        type=Path,
        help="Directory where rendered templates will be stored.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        context = load_context(args.env_file)
    except (ValueError, SystemExit) as exc:
        print(exc, file=sys.stderr)
        return 1

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    render_templates(context, output_dir)
    copy_assets(output_dir)

    print("[render] Complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
