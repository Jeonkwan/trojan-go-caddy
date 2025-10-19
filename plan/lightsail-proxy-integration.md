# Plan: Integrate the Python CLI with `lightsail-proxy`

The Terraform module in [`Jeonkwan/lightsail-proxy`](https://github.com/Jeonkwan/lightsail-proxy)
currently downloads shell scripts from this repository and executes them during instance
provisioning. After introducing the Python CLI we should update that module to consume the
new tooling. The high-level steps below outline the required changes.

## Objectives
1. Ship the CLI as an installable artifact (wheel or zip) that the Terraform user data can
download reliably.
2. Replace shell script invocations in Terraform templates with CLI commands.
3. Provide configuration hand-off between Terraform variables and the CLI options / YAML.
4. Maintain backwards compatibility for existing module consumers by versioning the changes.

## Implementation Steps

### 1. Package distribution
- Publish a GitHub Release for this repository that includes a built wheel (`pip install build && python -m build`).
- Alternatively, push the package to PyPI and reference the version in Terraform. Document the
  expected version pin.
- Update this repository's README with installation instructions for remote hosts (e.g. using
  `pipx install trojan-go-caddy==<version>`).

### 2. Terraform template updates
- In `lightsail-proxy`, identify templates such as `setup_ubuntu.sh.tftpl` that reference
  `configure_trojan-go.sh` and `configure_namecheap_dns.sh`.
- Replace the `curl | bash` blocks with steps to:
  1. Install Python 3.10+ (use `apt-get install -y python3 python3-venv`).
  2. Install the CLI (via `pipx` or `pip install` inside a virtual environment).
  3. Execute `trojan-go-caddy configure --from-env` style command (see step 3 below).

### 3. Configuration hand-off
- Map existing Terraform variables to environment variables expected by the CLI
  (e.g. `TROJAN_GO_CADDY_DOMAIN`, `TROJAN_GO_CADDY_TROJAN_PASSWORD`).
- Optionally render a YAML file within the template and call
  `trojan-go-caddy configure --config /var/tmp/trojan.yml` for clarity.
- Use Terraform's `templatefile` function to populate the YAML with module inputs.
- Update Namecheap DNS provisioning blocks to call `trojan-go-caddy dns-update` with the
  relevant variables and `--dry-run` when running planning validations.

### 4. Docker lifecycle hooks
- Replace references to the shell `run_trojan_go` helper with `trojan-go-caddy docker up`.
- Expose optional outputs/variables allowing operators to choose whether Terraform should start
  the Docker stack automatically or leave it for manual execution.

### 5. Validation & documentation
- Add Terratest or simple integration tests within `lightsail-proxy` to ensure the user data
  script completes successfully on a fresh Ubuntu image.
- Update the module README to describe the new Python CLI dependency, installation steps, and
  any version constraints.
- Provide migration notes for users upgrading from the shell script workflow (e.g. emphasise
  that Python 3.10 is now required on target instances).

### 6. Release management
- Tag a new module release (e.g. `v0.2.0`) that switches to the Python CLI.
- Deprecate the older workflow but keep the previous release available for consumers who cannot
  install Python 3.10 yet.

Following this plan keeps Terraform templates clean, reduces bash logic duplication, and ensures
that infrastructure automation benefits from the new declarative CLI.
