# Lightsail Integration Plan

The [`lightsail-proxy`](https://github.com/Jeonkwan/lightsail-proxy) project
currently clones this repository and runs the interactive
`configure_trojan-go.sh` script. The modernization refactors the workflow to use
a declarative `.env` file, the `render.py` templating script, and `make` targets.
This guide outlines the updates required so Lightsail automation can take
advantage of the new flow.

## 1. Inventory the current automation

From the Lightsail project:

- `setup_env.yaml` (Ansible playbook) clones `trojan-go-caddy`, executes the
  interactive configuration script, and calls `docker-compose` directly.
- Terraform user data (`setup_ubuntu.sh.tftpl`) triggers the Ansible playbook
  with extra-vars such as `trojan_go_password`.
- The playbook distributes the generated directories (`caddy/`, `trojan-go/`,
  `wwwroot/`) as Ansible templates.

These steps assume interactive prompts and the legacy directory structure.

## 2. Target architecture

- Provide a non-interactive `.env` file using Terraform variables.
- Use the new `Makefile` targets (`make render`, `make deploy`) instead of
  bespoke shell scripts.
- Render configuration templates on the Lightsail instance so secrets do not need
  to be committed to Git.

## 3. Implementation steps

1. **Update Terraform variables**
   - Add variables for `domain_name`, `trojan_websocket_path`, and
     `lets_encrypt_email` if they are not already present.
   - Generate an `.env` file within the user-data script using these variables.

2. **Revise user-data bootstrap (`setup_ubuntu.sh.tftpl`)**
   - After cloning `trojan-go-caddy`, create `/opt/trojan-go-caddy/.env` with the
     required keys (`DOMAIN`, `EMAIL`, `TROJAN_PASSWORD`, optional
     `WEBSOCKET_PATH`).
   - Install Python 3 and `pip`, then run `python3 -m pip install --user -r
     docker/scripts/requirements.txt`.
   - Execute `make deploy` from the repository root.
   - Optionally enable the Watchtower profile by exporting
     `COMPOSE='docker compose --profile watchtower'` before running `make`.

3. **Simplify Ansible playbook (`setup_env.yaml`)**
   - Remove tasks that call `configure_trojan-go.sh` and copy the legacy
     directories.
   - Replace them with a task that ensures the `.env` file contains the desired
     variables (Ansible's `copy` or `template` module).
   - Use the `community.docker.docker_compose_v2` module (if available) or a
     command task to run `make deploy` idempotently.
   - Add handlers for `make down` or `docker compose down` during cleanup.

4. **Validate with Terraform apply**
   - Run `terraform apply` in a staging environment.
   - Confirm that the instance provisions Docker, renders the templates, and the
     containers are running.
   - Ensure the Let's Encrypt challenge succeeds by verifying DNS and firewall
     settings.

5. **Document the new flow**
   - Update the Lightsail project's README to explain the `.env`-driven process
     and reference this repository's deployment guide.
   - Provide troubleshooting tips for failed template rendering or Compose runs.

## 4. Rollout strategy

- **Phase 1:** Implement changes on a feature branch and test with a disposable
  Lightsail instance.
- **Phase 2:** Update CI/CD (if any) to run `make config` or `make render` as a
  lint step.
- **Phase 3:** Merge into the main branch and tag a release that depends on the
  new version of `trojan-go-caddy`.

## 5. Optional enhancements

- Integrate secrets management (e.g., AWS Secrets Manager) to source the Trojan
  password securely instead of storing it in Terraform variables.
- Configure systemd to run `make deploy` on boot, ensuring the stack recovers
  automatically after reboots.
- Emit structured logs to CloudWatch by mounting a log volume or using the
  `awslogs` logging driver in `docker/compose.yml`.

With these adjustments, the Lightsail automation will align with the modernized
Docker Compose workflow, eliminating manual steps and reducing configuration
drift.
