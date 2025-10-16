# Plan: Standardize Docker Deployment with Compose v2 and GitOps Workflow

## Overview
The repository currently stores Docker Compose and helper scripts without lifecycle management. Configuration drift occurs because files are generated manually. This plan restructures the project into a declarative Docker Compose stack with versioned configuration, automated TLS provisioning, and GitOps-style deployment pipeline.

## Objectives
- Maintain canonical Compose manifests committed to the repo instead of generated via shell scripts.
- Parameterize environment via `.env` and templated overrides for domain-specific values.
- Integrate automated provisioning (Let's Encrypt via Caddy, cron jobs for renewal) with minimal manual input.
- Enable remote updates by syncing the repository and running a single make/compose command.

## Deliverables
1. `docker/` directory containing:
   - `compose.yml` (Compose v2 syntax) defining services: `caddy`, `trojan-go`, optional `watchtower` for updates.
   - `config/` with templated `Caddyfile.j2`, `trojan-go.json.j2`, `env.example`.
   - `scripts/` directory with non-interactive helpers (e.g., `render-config.py` or `gomplate` templates).
2. `Makefile` exposing targets (`make render`, `make up`, `make down`, `make logs`).
3. GitHub Actions workflow to lint Compose (`docker compose config`), run Hadolint on Dockerfiles if added, and validate templates.
4. Documentation describing GitOps deployment: clone repo onto host, populate `.env`, run `make deploy`.

## Implementation Steps
1. **Compose Refactor**
   - Rewrite `docker-compose_trojan-go.yml` using Compose specification v3.9 features (profiles, secrets, healthchecks).
   - Use named volumes for `caddy_data`, `caddy_config`, and `trojan_data` to keep TLS certificates persistent.
   - Define networks for isolation between Caddy and Trojan-Go containers.
2. **Configuration Management**
   - Replace shell-based template generation with Jinja2/Envsubst pipeline (`scripts/render.py`).
   - Accept inputs from `.env` (DOMAIN, TROJAN_PASSWORD, EMAIL) and produce configs under `rendered/` tracked via `.gitignore`.
   - Provide default HTML assets under `assets/` copied during render.
3. **Automation & Idempotence**
   - Introduce `make` targets that call `docker compose` with environment variable file and ensure correct exit codes.
   - Optionally add a systemd unit template to run `docker compose up` as a service (commit to `systemd/`).
4. **Secrets Handling**
   - Use `.env` for non-sensitive defaults and reference Docker secrets or external files for passwords.
   - Document process for injecting secrets via Terraform/Ansible.
5. **GitOps Deployment Flow**
   - Document steps for host provisioning: install Docker, clone repo, copy `.env`, run `make deploy`.
   - Add guidance for hooking into `lightsail-proxy` user-data: git clone repo on boot, run render/deploy commands automatically.
6. **Testing**
   - Add local test harness script or `act` workflow verifying Compose syntax and config rendering.
   - Provide integration test instructions (e.g., `docker compose up -d` on GitHub Codespaces using ephemeral domain + TLS skip).

## Integration Considerations
- Terraform user-data can clone a specific tag/release and run `make render deploy` using exported environment variables.
- Ansible role (from other plan) can include this stack as a dependency by invoking Make targets or Compose modules.

## Risks & Mitigations
- **Template complexity**: Keep templates simple, rely on environment substitution and defaults to reduce branching.
- **Secrets in `.env`**: Provide `.env.template` and recommend secret managers or Terraform locals for sensitive values.

## Next Steps
- Approve Compose-first direction.
- Begin restructure by committing canonical Compose + templates.
- Align with Terraform/Ansible integration strategies for automated deployment.
