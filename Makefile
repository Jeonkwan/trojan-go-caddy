SHELL := /bin/bash

COMPOSE ?= docker compose
COMPOSE_FILE := docker/compose.yml
ENV_FILE ?= .env
RENDERED_DIR := rendered

.PHONY: render up down restart logs ps status deploy config clean test dns-update

render:
	@echo "[render] Using $(ENV_FILE) -> $(RENDERED_DIR)"
	python3 docker/scripts/render.py --env-file "$(ENV_FILE)" --output-dir "$(RENDERED_DIR)"

up: render
	$(COMPOSE) --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" up -d

deploy: up
	@echo "[deploy] Stack is running"

down:
	$(COMPOSE) --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" down

restart:
	$(COMPOSE) --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" restart

logs:
	$(COMPOSE) --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" logs -f $(SERVICE)

ps status:
	$(COMPOSE) --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" ps

config:
	$(COMPOSE) --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" config

dns-update:
	python3 docker/scripts/update_dns.py --env-file "$(ENV_FILE)" $(if $(IP),--ip "$(IP)")

clean:
	rm -rf "$(RENDERED_DIR)"
	mkdir -p "$(RENDERED_DIR)"
	printf '# Ignore rendered configuration and assets\n*\n!/.gitignore\n' > "$(RENDERED_DIR)/.gitignore"

test:
	python -m pytest
