#!/usr/bin/env bash

SAMPLE_DOMAIN="example.com"
SAMPLE_SUBDOMAIN="sub1"
[[ -z "${DOMAIN}" ]] && { read -r -p "Domain name(e.g.: ${SAMPLE_DOMAIN}): " DOMAIN; }
[[ -z "${SUBDOMAIN}" ]] && { read -r -p "Subdomain name(e.g.: ${SAMPLE_SUBDOMAIN}): " SUBDOMAIN; }
[[ -z "${INSTANCE_PUBLIC_IP}" ]] && { read -r -p "Instance public IP address: " INSTANCE_PUBLIC_IP; }
[[ -z "${NAMECHEAP_DDNS_PASS}" ]] && { read -s -r -p "Namecheap Dynamice DNS Password: " NAMECHEAP_DDNS_PASS; }
echo ""

curl "https://dynamicdns.park-your-domain.com/update?host=${SUBDOMAIN}&domain=${DOMAIN}&password=${NAMECHEAP_DDNS_PASS}&ip=${INSTANCE_PUBLIC_IP}"
