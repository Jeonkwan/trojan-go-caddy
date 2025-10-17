# Trojan-Go + Caddy Ansible Role

This repository now provides an Ansible role that provisions the Trojan-Go + Caddy reverse proxy stack used by the [`lightsail-proxy`](https://github.com/Jeonkwan/lightsail-proxy) project.  The role replaces the previous ad-hoc shell scripts so that Terraform or ad-hoc playbooks can deploy and maintain the service declaratively.

## 🚀 What the role configures
- Installs Docker Engine and supporting packages.
- Creates the directory layout under `/opt/trojan-go-caddy` for Caddy, Trojan-Go, TLS assets, and static web content.
- Templates configuration for Caddy (`Caddyfile`), Trojan-Go (`config.json`), a placeholder landing page, and the Docker Compose definition.
- Starts (and reconfigures on changes) the Docker Compose stack using the `community.docker.docker_compose_v2` module.

## 📦 Repository layout
```
ansible.cfg                     # Local Ansible configuration
collections/requirements.yml    # Galaxy dependencies (community.docker)
playbooks/provision.yml         # Example playbook wiring in the role
roles/
  trojan_go_caddy/
    defaults/main.yml           # Role defaults and variable descriptions
    handlers/main.yml           # Handler to recreate the Docker stack
    tasks/main.yml              # Main task list
    templates/                  # Jinja2 templates for generated files
molecule/default/               # Molecule scenario for local testing
archive/                        # Deprecated shell scripts kept for reference
```

The legacy shell helpers (`configure_trojan-go.sh`, `configure_namecheap_dns.sh`, `trojan_go_funcs.sh`, `docker-compose_trojan-go.yml`) now live in the `archive/` directory for historical reference.

## 🔧 Requirements
- Python 3.9+
- [Ansible 8+](https://docs.ansible.com/ansible/latest/installation_guide/index.html)
- Docker Engine available on the managed host (the role installs it on Debian/Ubuntu)
- The [`community.docker`](https://galaxy.ansible.com/community/docker) collection (installed automatically via `ansible-galaxy install -r collections/requirements.yml`)

For local development of the role install the testing toolchain:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r collections/requirements.yml
```

## ⚙️ Variables
Override these defaults from inventory variables or extra vars:

| Variable | Description | Default |
| --- | --- | --- |
| `trojan_go_caddy_domain_name` | Apex domain used for certificates | `example.com` |
| `trojan_go_caddy_subdomain` | Subdomain that fronts Trojan-Go | `trojan` |
| `trojan_go_caddy_password` | Shared secret for clients | `change-me` |
| `trojan_go_caddy_project_root` | Base directory for generated files | `/opt/trojan-go-caddy` |
| `trojan_go_caddy_trojan_port` | External TLS port exposed by Trojan-Go | `443` |
| `trojan_go_caddy_http_port` | Port exposed by Caddy for HTTP traffic | `80` |
| `trojan_go_caddy_https_port` | Port served by Caddy inside the container | `443` |
| `trojan_go_caddy_caddy_image` | Container image for Caddy | `abiosoft/caddy` |
| `trojan_go_caddy_trojan_image` | Container image for Trojan-Go | `p4gefau1t/trojan-go` |
| `trojan_go_caddy_docker_users` | Additional OS users to add to the `docker` group | `[]` |

See `roles/trojan_go_caddy/defaults/main.yml` for the full set of tunables, including filesystem layout and placeholder HTML content.

## ▶️ Example usage
The included playbook demonstrates how to map existing variable names from `lightsail-proxy` to the role:

```bash
ansible-playbook -i inventory.ini playbooks/provision.yml \
  -e domain_name=example.com \
  -e subdomain_name=demo \
  -e trojan_go_password=$(uuidgen) \
  -e "trojan_go_caddy_docker_users=['ubuntu']"
```

The play targets the `trojan_hosts` inventory group by default—adjust the inventory or pass `-l hostname` to scope execution.

## 🧪 Testing with Molecule
Run the Molecule scenario to lint and converge the role inside a Docker-based Ubuntu 22.04 container:

```bash
molecule test
```

The scenario installs the role, asserts that the generated configuration files exist, and keeps the stack idempotent across reruns.

> **Note:** Docker-in-Docker is required for the converge step; run Molecule on a host where Docker is available.

## 🤝 Integrating with `lightsail-proxy`
The role can be consumed directly from this repository—`lightsail-proxy` does not need to maintain its own playbook unless it has extra host-specific tasks. A bootstrap script (e.g., Terraform user data) can clone the repo, install the dependencies, and invoke the provided playbook with the existing Terraform outputs:

```bash
sudo apt-get update && sudo apt-get install -y python3-pip git
git clone https://github.com/Jeonkwan/trojan-go-caddy.git /opt/trojan-go-caddy-role
cd /opt/trojan-go-caddy-role
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
ansible-galaxy collection install -r collections/requirements.yml
ANSIBLE_CONFIG=ansible.cfg ansible-playbook -i "${TARGET_HOST}," \
  -u "${SSH_USER}" --private-key /path/to/key \
  playbooks/provision.yml \
  -e "domain_name=${DOMAIN}" \
  -e "subdomain_name=${SUBDOMAIN}" \
  -e "trojan_go_password=${TROJAN_PASSWORD}" \
  -e "trojan_go_caddy_docker_users=['${SSH_USER}']"
```

Adjust the inventory string (`${TARGET_HOST}`) and SSH parameters to match how the instance is accessed during provisioning. When Terraform already manages the connection (for example via `remote-exec`), it can substitute the variables directly. The bundled playbook simply maps the historical variable names to the role’s defaults, so additional overrides can be passed via `-e` as needed.

If `lightsail-proxy` later grows host-specific logic, it can still include the role from its own playbook—see the follow-up plan in `plan/lightsail-proxy-integration.md` for the migration steps and alternatives (vendoring the role vs. pulling it dynamically).

## 🗃️ Migrating existing deployments
Because the role manages the same directory structure as the legacy scripts, you can safely point it at hosts that previously used `configure_trojan-go.sh`. The role will render the configuration templates and recreate the Docker Compose stack to apply changes automatically.

## 📄 License
This project retains the original license—consult the repository history for details or open an issue if clarification is needed.
