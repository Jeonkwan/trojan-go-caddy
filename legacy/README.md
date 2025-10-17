# Legacy Manual Deployment Scripts

The files in this directory predate the modern Docker Compose and Ansible
workflows that now live under `docker/` and `ansible/`. They implement the
original manual setup process for Trojan-Go and Caddy on a single host. The
scripts remain available for historical reference or for operators who need to
reproduce the legacy environment exactly, but they are no longer maintained.

## Contents

| File | Purpose |
| ---- | ------- |
| `configure_namecheap_dns.sh` | Automates DNS record management for Namecheap-hosted domains using the legacy approach. |
| `configure_trojan-go.sh` | Walks through interactive prompts to generate Trojan-Go and Caddy configuration files without templates. |
| `trojan_go_funcs.sh` | Library of helper functions consumed by `configure_trojan-go.sh`. |
| `docker-compose_trojan-go.yml` | The original Compose v1 file that launched the stack before the GitOps-friendly refactor. |

## When to Use These Scripts

Prefer the new Ansible playbook (`ansible/playbook.yml`) combined with the
configuration renderer (`docker/scripts/render.py`) for fresh deployments. The
legacy scripts can help with:

* Auditing the previous bootstrap flow for troubleshooting.
* Migrating configurations from older hosts that still rely on the shell-based
  tooling.
* Learning how the pre-refactor stack was assembled step by step.

Because the scripts are no longer part of the primary deployment path, they may
not receive updates when new features land. Run them at your own discretion and
validate any generated configuration before deploying to production systems.
