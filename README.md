# Trojan-Go + Caddy (Modernized Stack)

This repository packages a repeatable Docker Compose deployment for running
[Trojan-Go](https://p4gefau1t.github.io/trojan-go/) behind
[Caddy](https://caddyserver.com/) with automatic HTTPS. Instead of manually
editing configuration files, you describe your environment in a simple `.env`
file, render the templates, and bring the stack online with a single `make`
command.

> **New to this project?** Start with the
> [deployment guide](docs/deployment-guide.md) for a friendly walkthrough of
> the entire workflow.

## ✨ What's inside

- **Declarative Compose file** – `docker/compose.yml` defines the Caddy and
  Trojan-Go services using the modern Compose v2 syntax, complete with named
  volumes and optional Watchtower updates.
- **Templated configuration** – `docker/config/` holds Jinja2 templates for the
  Caddyfile and Trojan-Go config. They are rendered into the `rendered/`
  directory with values from your `.env` file.
- **Idempotent tooling** – The `Makefile` provides ergonomic commands such as
  `make render`, `make deploy`, and `make logs` so day-to-day operations remain
  consistent.
- **GitOps ready** – Everything required to configure and launch the stack is
  committed to version control. Clone the repo, commit your environment file,
  and reapply changes using Git.

## 🚀 Quick start

1. **Install prerequisites**
   - Docker Engine 20.10+
   - Docker Compose Plugin v2 (bundled with recent Docker releases)
   - Python 3.9+ with `pip`

2. **Clone the repository and enter it**

   ```bash
   git clone https://github.com/Jeonkwan/trojan-go-caddy.git
   cd trojan-go-caddy
   ```

3. **Create your `.env` configuration**

   ```bash
   cp docker/config/env.example .env
   # Edit .env with your domain, email address, and Trojan-Go password
   ```

4. **Install template dependencies** (only required once per machine)

   ```bash
   python3 -m pip install --user -r docker/scripts/requirements.txt
   ```

5. **Render configs and start the stack**

   ```bash
   make deploy
   ```

   This renders the templates into `rendered/` and runs `docker compose up -d`
   against `docker/compose.yml`.

6. **Verify the services**

   ```bash
   make status
   make logs SERVICE=caddy
   ```

   Caddy will request certificates from Let's Encrypt and proxy WebSocket
   traffic on the path configured via `WEBSOCKET_PATH`.

For a comprehensive explanation of each step, environment variable, and
operational task, see the [deployment guide](docs/deployment-guide.md).

## 🗂️ Repository layout

```
├── docker/
│   ├── assets/               # Static website served by Caddy
│   ├── compose.yml           # Compose v2 stack definition
│   ├── config/               # Jinja2 templates and env example
│   └── scripts/              # Rendering helper script and requirements
├── docs/
│   ├── deployment-guide.md   # Friendly, step-by-step instructions
│   └── lightsail-integration-plan.md
├── rendered/                 # Generated configs (ignored by Git)
├── legacy/                   # Archived manual setup scripts (see below)
├── Makefile                  # Convenience targets for lifecycle commands
└── README.md
```

Legacy helper scripts now live under [`legacy/`](legacy/README.md) so they stay
available without cluttering the modern workflow. Consult that README for a
full overview and guidance on when (or if) you should still use them.

## 🧪 Continuous validation

A GitHub Actions workflow (see `.github/workflows/compose.yml`) renders the
example environment and runs `docker compose config` to catch syntax errors
before changes are merged. To reproduce the same check locally after installing
Docker and the Compose plugin:

```bash
cp docker/config/env.example .env
make render
make config
```

Running `make config` invokes `docker compose --env-file .env -f docker/compose.yml config`,
so you will get identical validation to the automated pipeline before committing changes.

A companion workflow (`.github/workflows/tests.yml`) runs unit tests against the
rendering utilities to ensure template changes remain safe. You can execute the
same suite locally once `pytest` is available:

```bash
python3 -m pip install --user -r docker/scripts/requirements.txt pytest
make test
```

## 🛠️ Automated provisioning with Ansible

Prefer an end-to-end automation flow? The repository now ships with an
[Ansible](https://docs.ansible.com/) playbook that handles host preparation,
configuration rendering, and Compose deployment on Debian/Ubuntu systems.

1. **Install Ansible on your control machine.** Refer to the
   [upstream docs](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
   for platform-specific steps.
2. **Describe your target hosts.** Copy `ansible/inventory.example` to
   `ansible/inventory` and update the hostname, SSH user, and connection
   details.
3. **Provide stack variables.** Edit `ansible/group_vars/all.yml` with your
   domain, email address, and Trojan-Go password. Optional values such as the
   WebSocket path or Watchtower interval can be tuned here as well.
4. **Run the playbook.** Execute the following from the repository root:

   ```bash
   ansible-playbook -i ansible/inventory ansible/playbook.yml
   ```

The playbook ensures Docker Engine, the Compose plugin, Python dependencies,
and the project files are present before running `make render` and `docker
compose` remotely. Set `trojan_enable_watchtower: true` in
`ansible/group_vars/all.yml` if you want the Watchtower service to launch along
with Caddy and Trojan-Go.

## 🔄 Automating other environments

The templated approach makes it straightforward to integrate with tools such as
Terraform, Ansible, or GitHub Actions. If you rely on the
[`lightsail-proxy`](https://github.com/Jeonkwan/lightsail-proxy) project, check
out the dedicated integration plan in
[`docs/lightsail-integration-plan.md`](docs/lightsail-integration-plan.md) for a
step-by-step update strategy.

## 📄 License

This repository inherits its license from the upstream project history. Contact
the maintainer if you need clarification on usage rights.
