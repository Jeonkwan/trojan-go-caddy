#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 || "$1" == -* ]]; then
  set -- trojan-go-caddy bootstrap "$@"
elif [[ "$1" == "bootstrap" || "$1" == "configure" || "$1" == "dns-update" || "$1" == "validate" || "$1" == "docker" ]]; then
  set -- trojan-go-caddy "$@"
elif [[ "$1" == "trojan-go-caddy" ]]; then
  :
fi

if [[ "$1" == "trojan-go-caddy" && "${2:-}" == "bootstrap" ]]; then
  export TROJAN_GO_CADDY_DIR_BASE_DIR="${TROJAN_GO_CADDY_DIR_BASE_DIR:-/data}"
fi

exec "$@"
