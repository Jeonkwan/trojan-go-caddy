# Plan: Convert `trojan-go-caddy` into an Ansible Role

## Overview
The `lightsail-proxy` project provisions Ubuntu instances and expects to bootstrap Trojan-Go and Caddy through user-data. Currently, `trojan-go-caddy` relies on ad-hoc shell scripts (`configure_trojan-go.sh`, `configure_namecheap_dns.sh`, `trojan_go_funcs.sh`) and manual steps. This plan turns the repository into a reusable Ansible role so the Terraform stack can install and maintain Trojan-Go/Caddy declaratively.

## Objectives
- Replace interactive shell scripts with idempotent Ansible tasks.
- Expose configuration via variables matching `setup_env.yaml` expectations in `lightsail-proxy`.
- Standardize file layout (`roles/trojan_go_caddy/{tasks,templates,files,defaults}`) for maintainability.
- Provide local testing via Molecule to validate playbook behavior before Terraform integration.

## Deliverables
1. An Ansible role `roles/trojan_go_caddy` containing:
   - `defaults/main.yml`: variables for domain, trojan password, Namecheap DDNS, ports, web root, etc.
   - `tasks/main.yml`: orchestrates setup (package installation, directory creation, template rendering, service enablement).
   - `templates/`: Jinja2 templates for `Caddyfile`, `trojan-go.json`, and placeholder HTML content.
   - `handlers/main.yml`: reloads Caddy and restarts Trojan-Go when configurations change.
2. Top-level playbook `playbooks/provision.yml` that invokes the role using variables provided by `setup_env.yaml`.
3. `molecule/default/` scenario with converge/verify steps using Docker or Vagrant to ensure idempotence.
4. Documentation updates explaining how `lightsail-proxy` should call the role.

## Implementation Steps
1. **Repository Restructure**
   - Create `ansible.cfg`, `collections/requirements.yml` (pin `community.docker`), and `requirements.txt` for Molecule.
   - Move shell helper scripts into an `archive/` folder for reference and note their deprecated status.
2. **Role Authoring**
   - Write tasks to install required packages (`docker`, `docker-compose`, `uuid-runtime`, etc.).
   - Manage directories `/opt/trojan-go`, `/opt/caddy`, `/var/www/trojan`, and log files with correct permissions.
   - Render configuration templates using Ansible variables. Leverage `template` module for `Caddyfile` and `trojan-go` config aligning with current script output.
   - Use `community.docker.docker_compose` module to deploy the stack from a managed compose file instead of manually running `docker-compose`.
3. **Service Management**
   - Introduce a systemd unit or rely on Docker Compose managed via `docker stack`. Ensure idempotent start/enable.
   - Register handlers for configuration changes to trigger container recreation or reload commands.
4. **Testing Setup**
   - Configure Molecule with Docker driver (e.g., Ubuntu 22.04 image).
   - Implement `molecule.yml`, `converge.yml` calling the role, and `verify.yml` (Ansible or Testinfra) to assert files/ports exist.
   - Add GitHub Actions workflow `ci.yml` running Molecule tests.
5. **Documentation & Integration**
   - Update `README.md` with instructions for running the playbook locally and from `lightsail-proxy`.
   - Modify `lightsail-proxy/setup_env.yaml` (in its repository) to consume the new role (future work). Document required variable mappings and example inventory snippet.

## Risks & Mitigations
- **Terraform user-data size**: Large playbooks may slow boot. Mitigate by packaging role as tarball fetched via `ansible-pull` or using prebuilt release archive.
- **Molecule resource usage**: Keep scenario lean (disable heavy dependencies) and provide skip instructions for constrained environments.

## Next Steps
- Approve role-based direction.
- Begin restructuring repository and authoring tasks/templates.
- Coordinate with `lightsail-proxy` maintainers to align variable names and integration timeline.
