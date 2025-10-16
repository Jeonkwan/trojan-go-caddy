# Deployment Guide

Welcome! This document walks you through deploying the modernized Trojan-Go +
Caddy stack from scratch. No prior experience with Docker Compose or GitOps is
required—we will explain each step along the way.

---

## 1. Understand the moving pieces

- **Trojan-Go** provides the proxy server that your clients connect to. It uses a
  password (or UUID) for authentication.
- **Caddy** terminates HTTPS, obtains certificates from Let's Encrypt, and serves
  a decoy static site.
- **Docker Compose** orchestrates both containers so they share a network and
  exchange data securely.
- **Templates** in `docker/config/` let you declare your desired configuration in
  a `.env` file. The `render.py` script converts those templates into real config
  files under `rendered/`.

The result is a repeatable, declarative deployment. If you ever need to rebuild
on another server, simply copy the repository and rerun `make deploy`.

## 2. Prerequisites

| Tool | Minimum version | Purpose |
| ---- | ---------------- | ------- |
| Docker Engine | 20.10 | Runs the containers |
| Docker Compose | v2 | Coordinates the multi-container stack |
| Python | 3.9 | Renders the templates via Jinja2 |

### Install Docker and Compose (Ubuntu example)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Verify the installation:

```bash
docker info
docker compose version
```

### Optional: let Ansible prepare the host for you

If you would rather automate the dependency setup and deployment, run the
included Ansible playbook from your control machine:

1. Install Ansible locally.
2. Copy `ansible/inventory.example` to `ansible/inventory` and update the host
   entry with your server's address and SSH user.
3. Replace the placeholder values in `ansible/group_vars/all.yml` with your
   domain, email address, and Trojan-Go password. Set
   `trojan_enable_watchtower: true` if you want Watchtower to manage image
   updates automatically.
4. Execute the playbook:

   ```bash
   ansible-playbook -i ansible/inventory ansible/playbook.yml
   ```

The playbook targets Debian/Ubuntu hosts. It installs Docker Engine, the
Compose plugin, Python requirements, renders the templates, and finally runs the
Compose stack. You can rerun it any time to pick up configuration changes—tasks
remain idempotent.

## 3. Clone the repository and prepare Python

```bash
git clone https://github.com/Jeonkwan/trojan-go-caddy.git
cd trojan-go-caddy
python3 -m pip install --user -r docker/scripts/requirements.txt
```

The only Python dependency is `jinja2`, a lightweight templating engine.

## 4. Configure environment values

Copy the example environment file and edit it with your details:

```bash
cp docker/config/env.example .env
nano .env  # or use your favorite editor
```

| Variable | Description |
| -------- | ----------- |
| `DOMAIN` | The fully qualified domain name (e.g. `vpn.example.com`). Must point to your server's public IP before you request certificates. |
| `EMAIL` | Email used for Let's Encrypt registration and expiry notices. |
| `TROJAN_PASSWORD` | Strong shared secret clients will use to authenticate. |
| `WEBSOCKET_PATH` | (Optional) WebSocket path that Caddy proxies to Trojan-Go. Default is `/trojan`. |
| `TROJAN_PORT` | (Optional) Internal container port for Trojan-Go. Default is `8443`. |
| `TZ` | (Optional) Time zone applied to containers that read the `TZ` variable. |
| `WATCHTOWER_INTERVAL` | (Optional) Interval in seconds between Watchtower update checks when that profile is enabled. |

Keep the `.env` file private. You can commit it to a private repository if you
are using GitOps, but avoid publishing secrets in a public fork.

## 5. Render configuration files

Run the rendering step whenever you change `.env`:

```bash
make render
```

What happens:

1. `docker/scripts/render.py` reads `.env` (and any overrides exported as real
   environment variables).
2. The script fills in the Jinja2 templates:
   - `rendered/caddy/Caddyfile`
   - `rendered/trojan-go/config.json`
3. Static site assets are copied to `rendered/wwwroot/`.

You can inspect the generated files before bringing up the containers.

## 6. Launch the stack

```bash
make deploy
```

This command runs `docker compose -f docker/compose.yml up -d` using your `.env`
file. Two named volumes—`caddy_data` and `caddy_config`—store HTTPS certificates
and Caddy settings so they persist across restarts. `trojan_data` stores
Trojan-Go state (such as session tickets, if enabled later).

To confirm everything is healthy:

```bash
make status          # Shows container state
make logs SERVICE=caddy
make logs SERVICE=trojan-go
```

The first start may take a minute while Caddy completes domain validation.
Ensure port 80/443 are accessible and DNS resolves correctly.

## 7. Connect a client

Configure your Trojan-Go client with the following details (update values to
match your `.env` file):

- **Server:** `DOMAIN`
- **Port:** `443`
- **Password:** `TROJAN_PASSWORD`
- **WebSocket path:** `WEBSOCKET_PATH`
- **SSL SNI/Host:** `DOMAIN`

Because Caddy terminates TLS, the client connects over HTTPS and then upgrades
to WebSocket. This disguises the traffic as regular web requests.

## 8. Operational tasks

| Task | Command |
| ---- | ------- |
| Restart containers | `make restart` |
| Follow logs | `make logs SERVICE=caddy` or `SERVICE=trojan-go` |
| Stop everything | `make down` |
| Remove generated configs | `make clean` |
| Preview combined Compose file | `make config` |

### Enabling automatic updates

To allow Watchtower to auto-update the images periodically, supply the profile:

```bash
docker compose --env-file .env -f docker/compose.yml --profile watchtower up -d
```

Or set `COMPOSE='docker compose --profile watchtower'` before running `make
deploy`.

## 9. GitOps workflow

1. Commit your `.env` (or `.env.enc` if using a secret manager) to your Git
   repository.
2. Use a CI pipeline or cron job on the server to run:

   ```bash
   git pull
   make deploy
   ```

3. The included GitHub Actions workflow (`.github/workflows/compose.yml`) runs
   `make render` with the sample environment and validates the Compose file. Use
   it as a template for your own CI checks.

## 10. Troubleshooting

| Symptom | Possible fix |
| ------- | ------------ |
| `Missing required configuration values` | Ensure `.env` defines `DOMAIN`, `EMAIL`, and `TROJAN_PASSWORD`. |
| Caddy fails to obtain a certificate | Confirm DNS records are in place, ports 80/443 are open, and no other process is listening on those ports. |
| Trojan-Go clients cannot connect | Double-check the WebSocket path and password. Review `make logs SERVICE=trojan-go`. |
| Template rendering fails with `jinja2` import error | Run `python3 -m pip install --user -r docker/scripts/requirements.txt`. |
| Want to rotate the Trojan password | Update `.env`, rerun `make render`, then `make deploy`. Distribute the new password to clients. |

## 11. Cleaning up

To remove containers but keep volumes:

```bash
make down
```

To start fresh (removes volumes and TLS certificates):

```bash
docker compose -f docker/compose.yml down --volumes
rm -rf rendered/
```

## 12. Next steps

- Review the [Lightsail integration plan](lightsail-integration-plan.md) if you
  deploy via AWS Lightsail automation.
- Consider storing secrets in a password manager or Vault product and injecting
  them during CI/CD runs.
- Experiment with additional Caddy directives (rate limiting, log retention) by
  editing `docker/config/Caddyfile.j2` and rerunning `make render`.

Happy deploying!
