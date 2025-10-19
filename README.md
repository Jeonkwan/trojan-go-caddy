# Trojan-Go + Caddy Python CLI

This repository provides a Python based command line interface (CLI) that scaffolds the
configuration, DNS automation, and Docker helpers required to run
[Trojan-Go](https://p4gefau1t.github.io/trojan-go/) behind a
[Caddy](https://caddyserver.com/) reverse proxy. The CLI replaces the previous interactive
shell scripts with a repeatable, non-interactive workflow that can be executed locally or
from provisioning tools such as Terraform or Ansible.

## ✨ Features
- **Single entrypoint** – `trojan-go-caddy configure` renders all configuration files,
  creates the directory structure, and prepares placeholder SSL paths.
- **Structured configuration** – a Pydantic model loads settings from CLI options,
  environment variables (`TROJAN_GO_CADDY_*`), or YAML files.
- **Templated assets** – Jinja2 templates generate the Caddyfile, Trojan-Go `config.json`,
  Docker Compose definition, and landing page.
- **DNS automation** – the `dns-update` subcommand performs Namecheap Dynamic DNS updates
  with optional dry-run support.
- **Docker helpers** – wrap `docker compose` to start or stop the stack with validated
  configuration paths.

Legacy shell scripts (`configure_trojan-go.sh`, `configure_namecheap_dns.sh`) remain in the
repository for historical reference but are superseded by the Python CLI.

## 🧰 Requirements
- Python 3.10 or newer
- Docker Engine with the `docker compose` plugin (required for the docker helpers)

## 🚀 Installation
Install the package in a virtual environment or with [pipx](https://pipx.pypa.io/):

```bash
python -m pip install .
# or
pipx install .
```

You can also execute the CLI in-place without installation:

```bash
python -m trojan_go_caddy.cli --help
```

## ⚙️ Usage

### Generate configuration

```bash
trojan-go-caddy configure \
  --domain demo.example \
  --base-dir ./deployment
```

The command creates the following structure (paths are configurable):

```
./deployment
├── caddy/Caddyfile
├── docker-compose.yml
├── trojan-go/config.json
└── wwwroot/
    ├── caddy.log
    └── trojan/index.html
```

Use `--overwrite` to refresh existing files, or provide a YAML file via `--config` with the
same schema as the CLI options. Configuration values can also be supplied through
environment variables prefixed with `TROJAN_GO_CADDY_` (for example,
`TROJAN_GO_CADDY_DOMAIN`).

To download a remote landing page instead of the bundled template, pass
`--pingpong-html-url https://example.com/page.html`.

### Update Namecheap Dynamic DNS

```bash
trojan-go-caddy dns-update \
  --domain example.com \
  --subdomain trojan \
  --password <namecheap_ddns_password> \
  --ip 203.0.113.10
```

Add `--dry-run` to preview the request URL without making changes.

### Manage Docker Compose

```bash
trojan-go-caddy docker up --compose-path ./deployment/docker-compose.yml
# ... later ...
trojan-go-caddy docker down --compose-path ./deployment/docker-compose.yml
```

## 🐳 Container image

Build the container locally:

```bash
docker build -t trojan-go-caddy .
```

Run it with a single command to render the configuration and start the stack on the host
Docker daemon:

```bash
docker run --rm \
  -e TROJAN_GO_CADDY_DOMAIN=demo.example \
  -e TROJAN_GO_CADDY_TROJAN_PASSWORD=supersecret \
  -v "$PWD/deployment:/data" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  trojan-go-caddy
```

The container entrypoint executes `trojan-go-caddy bootstrap`, which loads settings from
environment variables, renders all assets into `/data`, and runs `docker compose up -d` using
the generated `docker-compose.yml`. Mount a host directory at `/data` to persist the files, and
pass additional environment variables with the `TROJAN_GO_CADDY_` prefix to customise other
settings (for example, `TROJAN_GO_CADDY_REMOTE_PORT=80`). The container ships with the Docker CLI
and Compose plugin; mounting `/var/run/docker.sock` allows that CLI to talk to the host daemon so
the compose services start on the server rather than inside the helper container.

To skip starting Docker Compose, set `--no-run-compose` in the container command:

```bash
docker run --rm \
  -e TROJAN_GO_CADDY_DOMAIN=demo.example \
  -v "$PWD/deployment:/data" \
  trojan-go-caddy --no-run-compose
```

When using `--no-run-compose` you can still bring the stack online with
`docker compose -f deployment/docker-compose.yml up -d` on the host.

## 🧪 Development
Install the development dependencies and run the checks:

```bash
python -m pip install --upgrade pip
pip install -e .[dev]
ruff check .
pyright
pytest
```

The repository includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs the
same lint, type-check, and test steps on each push and pull request, and a second job that builds
the container image with Docker Buildx before smoke-testing it via `docker run --no-run-compose`
and validating the generated Compose file with `docker compose config`.

## 📄 License
This project is released under the MIT License. Refer to `LICENSE` (or the repository
history) for details.
