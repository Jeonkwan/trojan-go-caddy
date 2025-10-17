# Plan: Update `lightsail-proxy` for the Ansible role

## Goals
- Replace inline shell script execution in `setup_env.yaml` with a direct call to the `trojan_go_caddy` Ansible role.
- Keep variable names (`domain_name`, `subdomain_name`, `trojan_go_password`, etc.) consistent to minimize Terraform changes.
- Ensure the Terraform user-data/bootstrap flow installs role dependencies (`ansible-galaxy` collections, Python requirements) before running the playbook.

## Proposed Steps
1. **Decide how to consume the role**
   - Option A: Reuse the bundled playbook directly from this repository. Terraform user data can `git clone` the repo, install dependencies, and invoke `playbooks/provision.yml` with the existing variables (`domain_name`, `subdomain_name`, `trojan_go_password`, etc.). This requires no changes to `lightsail-proxy`'s Ansible files today.
   - Option B: Vendor the role (e.g., Git submodule under `ansible/roles/trojan_go_caddy`) and call it from `setup_env.yaml`.
   - Option C: Pull the role dynamically via `ansible-galaxy install git+https://github.com/Jeonkwan/trojan-go-caddy.git` and include it in a local playbook.
   - Document the chosen approach to keep Terraform state reproducible.

2. **(If adopting Options B/C) Update `setup_env.yaml` playbook**
   - Remove tasks that clone this repository and run shell scripts.
   - Add a role inclusion:
     ```yaml
     - hosts: all
       become: yes
       roles:
         - role: trojan_go_caddy
           vars:
             trojan_go_caddy_domain_name: "{{ domain_name }}"
             trojan_go_caddy_subdomain: "{{ subdomain_name }}"
             trojan_go_caddy_password: "{{ trojan_go_password }}"
             trojan_go_caddy_docker_users:
               - "{{ username }}"
     ```
   - Retain auxiliary tasks (e.g., reboot cronjob) as separate plays or convert them into role variables/handlers.

3. **Ensure dependency installation**
   - Extend bootstrap scripts to run:
     ```bash
     pip install -r /opt/trojan-go-caddy/requirements.txt
     ansible-galaxy collection install -r /opt/trojan-go-caddy/collections/requirements.yml
     ```
   - Alternatively, pre-build a lightweight Ansible execution environment container.

4. **CI/CD alignment**
   - Mirror Molecule testing inside `lightsail-proxy`'s CI (GitHub Actions) to catch regressions when Terraform or playbooks change.

5. **Documentation**
   - Update `README` or operational runbooks to describe the new role-based deployment and variables required from Terraform outputs.

## Risks & Considerations
- **Execution environment**: AWS Lightsail user-data has limited runtime. Consider packaging dependencies or using an Ansible Execution Environment image.
- **Docker availability**: Ensure the base AMI supports Docker installation—keep fallback instructions if package names differ (e.g., Debian vs. Ubuntu).
- **State drift**: Because the role manages Docker Compose, Terraform should treat the host as mutable; document how to reconcile manual changes (e.g., rerun playbook).
