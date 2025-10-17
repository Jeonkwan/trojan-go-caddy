# Trojan-go + Caddy

This repository provides helper scripts and configuration to deploy a [Trojan-Go](https://p4gefau1t.github.io/trojan-go/) server with [Caddy](https://caddyserver.com/) as the TLS termination proxy.  The included scripts walk you through provisioning secrets, generating the configuration directories expected by the containers, and starting the docker-compose stack so that you can quickly expose a Trojan-Go service behind Caddy with automatic HTTPS.

## ✨ Features
- **Guided bootstrap script** – `configure_trojan-go.sh` prepares all required directories and configuration files based on your answers to a few prompts.
- **Automated container lifecycle** – `run_trojan_go` (sourced from `trojan_go_funcs.sh`) builds and starts the docker-compose stack with sensible defaults.
- **Reverse proxy + TLS** – Caddy handles certificate management and forwards WebSocket traffic to Trojan-Go, providing seamless TLS encryption.
- **Convenient cleanup** – a single command tears down the containers and removes generated assets when you are finished testing.

## 🧰 Requirements
You will need the following tools on the host running the scripts:

| Tool | Purpose | Installation hint |
| ---- | ------- | ----------------- |
| `docker` | Runs the Caddy and Trojan-Go containers | [Docker Engine installation guide](https://docs.docker.com/engine/install/) |
| `docker-compose` | Orchestrates the multi-container stack | Usually bundled with recent Docker releases |
| `uuid` | Generates the Trojan-Go user ID during configuration | `sudo apt-get install uuid` |
| `curl` | Retrieves the public IP address during setup | `sudo apt-get install curl` |

On Debian/Ubuntu hosts you can install the missing packages with:

```bash
sudo apt-get update
sudo apt-get install -y uuid curl
```

> **Tip:** Verify Docker is ready before proceeding:
>
> ```bash
> docker info
> docker compose version  # or docker-compose --version
> ```

## 🗂️ Repository layout
The helper scripts live at the root of the repository:

- `configure_trojan-go.sh` – interactive script that scaffolds configuration directories and files.
- `configure_namecheap_dns.sh` – optional helper to configure Namecheap DNS records via their API.
- `trojan_go_funcs.sh` – shell functions that include the `run_trojan_go` helper.
- `docker-compose_trojan-go.yml` – compose file that starts the Trojan-Go and Caddy containers.
- `example/` – example configuration snippets referenced by the setup script.

## 🛠️ Script reference
Each script is designed to be run from the repository root. The sections below explain how and when to use them.

### 🚀 `configure_trojan-go.sh`
This is the main bootstrap script you will run first:

- **How to execute:** `source ./configure_trojan-go.sh`
- **What it does:**
  - Prompts for your domain, Trojan-Go password, and UUID (with an option to auto-generate one).
  - Creates the `./caddy`, `./trojan-go`, and `./wwwroot` directories with populated configuration files.
  - Loads helper functions (including `run_trojan_go`) into your current shell session for later use.
- **Pro tip:** Because the script is sourced, any environment variables it exports remain available after it finishes. Open a new shell if you want to start over with fresh prompts.

### 🌐 `configure_namecheap_dns.sh`
Use this optional helper when Namecheap manages your DNS records:

- **How to execute:** `bash ./configure_namecheap_dns.sh`
- **What it does:**
  - Interacts with the Namecheap API to set or update A/AAAA records for your domain.
  - Fetches your public IP automatically (via `curl`) to minimize manual copying.
  - Validates the response from Namecheap so you know the change succeeded.
- **Before you run it:**
  - Export the environment variables `NAMECHEAP_API_USER`, `NAMECHEAP_API_KEY`, `NAMECHEAP_USERNAME`, and `NAMECHEAP_CLIENT_IP`.
  - Ensure your Namecheap account has API access enabled and whitelists the IP you are calling from.

### ⚙️ `trojan_go_funcs.sh`
This file collects reusable shell functions that power the scripts:

- **How to use it:** You normally do not run this file directly; it is sourced by `configure_trojan-go.sh`.
- **Key helpers inside:**
  - `run_trojan_go` – launches `docker-compose -f docker-compose_trojan-go.yml up -d` and waits for healthy containers.
  - `cleanup_trojan_go` – stops the stack and removes generated directories when you are finished.
- **Why it matters:** Keeping the functions in one place makes it easier to reuse them in your own automation or to customize behaviors without editing multiple scripts.

## 🚧 Bootstrap the environment
1. Clone the repository and change into the directory.
2. Source the configuration script so it can prompt for the values it needs and create the directory structure.

```bash
source ./configure_trojan-go.sh
```

The script performs the following tasks:
- Collects your domain, Trojan-Go password, and UUID (it can generate one if you prefer).
- Writes the answers into template files in `./trojan-go` and `./caddy`.
- Creates a simple landing page under `./wwwroot/trojan/index.html` for traffic probing.

When the script finishes you can run the helper function that it loads into your shell session:

```bash
run_trojan_go
```

This function wraps `docker-compose -f docker-compose_trojan-go.yml up -d` and waits for the containers to become healthy before returning.

## 📂 Generated directories and files
After the bootstrap script completes you should see the following tree:

```bash
├── caddy
│   └── Caddyfile            # generated from example_caddyfile
├── trojan-go
│   └── config.json          # generated from example_config.json
└── wwwroot
    ├── caddy.log
    └── trojan
        └── index.html
```

The `./ssl` directory will be created automatically by the Caddy container when certificates are obtained.

## 📝 Configuration notes
- **Multiple users:** Edit `./trojan-go/config.json` to add more users to the `password` or `users` list after the initial run.
- **Custom web root:** Replace the files under `./wwwroot` with your own static site. Caddy serves this directory on port 80/443 to provide legitimate-looking traffic.
- **DNS setup:** Ensure your domain's A/AAAA records point to the host running this stack. You can adapt `configure_namecheap_dns.sh` or create the records manually via your DNS provider.
- **Trojan-Go over WebSocket:** Clients should connect with `wss://<your-domain>/trojan` (override the path by exporting `WEBSOCKET_PATH` before running `configure_trojan-go.sh`). Set the Trojan-Go client `websocket` hostname to your domain so that CDN or proxy layers keep the correct `Host` header.
- **Firewall rules:** Only expose ports 80 and 443 on the host. Caddy terminates TLS/HTTP traffic and forwards `/trojan` WebSocket requests to the internal Trojan-Go container, so no additional ports need to be reachable from the internet.

## 🕹️ Operating the stack
- **Start / restart:** `run_trojan_go`
- **View logs:**
  - `docker-compose -f docker-compose_trojan-go.yml logs -f caddy`
  - `docker-compose -f docker-compose_trojan-go.yml logs -f trojan-go`
- **Inspect status:** `docker ps --filter name=trojan-go`
- **Update configuration:** Modify files in `./caddy` or `./trojan-go` and run `docker-compose -f docker-compose_trojan-go.yml restart <service>`.

## 🧹 Cleanup
To stop the services and remove the generated assets run:

```bash
docker-compose -f docker-compose_trojan-go.yml down
sudo rm -rf ./caddy ./trojan-go ./wwwroot ./ssl
```

You can re-run `configure_trojan-go.sh` at any time to regenerate clean configuration files.

## 🩺 Troubleshooting
| Symptom | Suggested fix |
| ------- | -------------- |
| Containers exit immediately | Run `docker-compose -f docker-compose_trojan-go.yml logs` to identify syntax errors in the generated files. |
| Certificates are not issued | Confirm DNS records resolve to your host and that ports 80/443 are reachable from the internet. |
| Clients cannot connect | Ensure the UUID/password matches the values in `config.json` and that any upstream firewall allows the Trojan-Go port. |

## 📚 Further reading
- [Trojan-Go documentation](https://p4gefau1t.github.io/trojan-go/config/) explains advanced configuration options, including transport modes and routing policies.
- [Caddy documentation](https://caddyserver.com/docs/) covers reverse proxy directives, TLS automation, and logging customization.

## License
This repository follows the upstream license terms found in the original project. Check the project history or contact the maintainer if you require clarification.
