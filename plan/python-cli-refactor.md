# Plan: Replace Shell Scripts with a Python CLI & Configuration Templates

## Overview
Current automation lives in multiple interactive bash scripts that generate configs and rely on `source` side-effects. This plan consolidates the logic into a Python CLI package with declarative templates. The CLI can be consumed locally or by Terraform/Ansible user-data, reducing shell complexity while remaining lightweight.

## Objectives
- Provide a single entrypoint (`python -m trojan_go_caddy configure`) to scaffold all required assets.
- Use type-safe configuration (`pydantic` or `dataclasses`) that can ingest environment variables, `.env` files, or YAML.
- Offer subcommands for DNS updates, Docker Compose management, and validation.
- Preserve compatibility with existing directories (`caddy/`, `trojan-go/`, `wwwroot/`) but make paths configurable.

## Deliverables
1. Python package `trojan_go_caddy/` with modules:
   - `config.py`: configuration models & loaders (env vars, CLI flags, YAML input).
   - `templates/`: Jinja2 templates for Caddyfile, Trojan-Go config, and sample HTML.
   - `dns.py`: Namecheap Dynamic DNS updater using `requests` with retry/backoff.
   - `cli.py`: Click/Typer CLI exposing commands (`configure`, `dns-update`, `docker up/down`, `validate`).
2. `pyproject.toml` using Poetry or Hatch for dependency management and packaging.
3. Unit tests validating template rendering, CLI parsing, and DNS client behavior.
4. GitHub Actions workflow for linting (`ruff`), type-checking (`pyright`), and tests (`pytest`).

## Implementation Steps
1. **Bootstrap Package**
   - Initialize `pyproject.toml` with dependencies (`typer`, `pydantic`, `jinja2`, `requests`, `pyyaml`).
   - Set up `src/` layout and enable `ruff` + `pyright` config files.
2. **Implement Configuration Loader**
   - Create data models for domain settings, TLS paths, Docker Compose options.
   - Add `from_env`, `from_file`, and CLI argument parsing to build configuration.
   - Support automatic UUID generation when password not provided.
3. **Template Rendering**
   - Translate existing shell `cat <<EOF` templates into `.j2` files.
   - Provide CLI `configure` command that writes rendered files to target directories, ensuring directories exist.
4. **DNS Update Command**
   - Implement HTTP call to Namecheap endpoint with structured response handling and logging.
   - Add `--dry-run` support to preview requests without executing.
5. **Docker Helpers**
   - Provide wrappers around `subprocess` or Docker SDK to run `docker compose` commands with sanitized environment.
   - Optionally generate Compose file from template to keep configuration centralized.
6. **Testing & CI**
   - Write pytest suites for config parsing, template output snapshots, and DNS URL composition.
   - Add GitHub Actions pipeline to run lint/type/test on push and PR.
7. **Documentation**
   - Update README with installation instructions (`pipx install .`, `poetry run trojan-go-caddy configure --config settings.yaml`).
   - Provide example YAML/ENV files for integration with `lightsail-proxy`.

## Integration with `lightsail-proxy`
- Package CLI as wheel/zip published to GitHub Releases or PyPI; Terraform user-data installs via `pipx`.
- `setup_ubuntu.sh.tftpl` downloads release artifact and runs `trojan-go-caddy configure --from-env` using environment variables set by Terraform template variables.
- DNS updates triggered through CLI invocation rather than direct `curl` commands.

## Risks & Mitigations
- **Python dependency bloat**: Keep dependency set minimal, consider optional extras for features.
- **Runtime availability**: Ensure Python 3.10+ is available on target hosts (Ubuntu 22.04 includes it). Provide pre-flight check in CLI.

## Next Steps
- Approve Python CLI direction.
- Scaffold package and migrate templates.
- Coordinate release and update Terraform scripts to consume CLI.
