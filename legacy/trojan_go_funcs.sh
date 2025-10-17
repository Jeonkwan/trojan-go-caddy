#!/usr/bin/env bash
TROJAN_GO_CONFIG_SCRIPT_FILE="./configure_trojan-go.sh"
TROJAN_GO_DOCKER_COMPOSE_FILE="./docker-compose_trojan-go.yml"

function configure_trojan_go {
    local trojan_passwd=$1
    local full_domain_name=$2
   [[ ! -f "$TROJAN_GO_CONFIG_SCRIPT_FILE" ]] && { echo "EXIT. configuration script missing." && return 1; }
    printf "${trojan_passwd}\n${full_domain_name}" | $TROJAN_GO_CONFIG_SCRIPT_FILE
}

function run_trojan_go {
    [[ ! -f "$TROJAN_GO_DOCKER_COMPOSE_FILE" ]] && { echo "EXIT. docker-compose file missing." && return 1; }
    docker-compose -f $TROJAN_GO_DOCKER_COMPOSE_FILE up &
}

function clean_up_trojan_go {
    [[ ! -f "$TROJAN_GO_DOCKER_COMPOSE_FILE" ]] && { echo "EXIT. docker-compose file missing." && return 1; }
    docker-compose -f docker-compose_trojan-go.yml down
    rm -rf {./caddy,./trojan-go,./wwwroot,./ssl}
}

function get_nc_dns_update_args {
    SAMPLE_DOMAIN="example.com"
    SAMPLE_SUBDOMAIN="sub1"
    read -r -p "Domain name(e.g.: ${SAMPLE_DOMAIN}): " DOMAIN
    read -r -p "Subdomain name(e.g.: ${SAMPLE_SUBDOMAIN}): " SUBDOMAIN
    read -r -p "Instance public IP address: " INSTANCE_PUBLIC_IP
    read -s -r -p "Namecheap Dynamice DNS Password: " NAMECHEAP_DDNS_PASS
    echo ""
}

function update_nc_dns_curl {
    get_nc_dns_update_args
    curl "https://dynamicdns.park-your-domain.com/update?host=${SUBDOMAIN}&domain=${DOMAIN}&password=${NAMECHEAP_DDNS_PASS}&ip=${INSTANCE_PUBLIC_IP}"
}

function update_nc_dns_docker {
    get_nc_dns_update_args
    docker run \
    --name namecheap-ddns-update \
    --rm \
    -e "DOMAIN=${DOMAIN}" \
    -e "SUBDOMAINS=${SUBDOMAIN}" \
    -e "IP=${INSTANCE_PUBLIC_IP}" \
    -e "NC_DDNS_PASS=${NAMECHEAP_DDNS_PASS}" \
    joshuamorris3/namecheap-ddns-update
}