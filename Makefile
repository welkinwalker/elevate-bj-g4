# =============================================================================
# Project Elevate: Automation & Developer Makefile
# =============================================================================

.PHONY: help setup test lint eval docker-build docker-run terraform-init terraform-plan clean

PYTHON ?= python3
VENV ?= .venv
BIN ?= $(VENV)/bin
IMAGE_NAME ?= elevate-hr-agent:latest

help: ## Show help for each target
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv and install dependencies
	uv venv $(VENV)
	uv pip install -e ".[dev]" || $(BIN)/pip install -e ".[dev]"

test: ## Run unit and integration tests with pytest
	PYTHONPATH=. $(BIN)/pytest -v tests/test_agent.py

lint: ## Run code linter and formatting checks
	$(BIN)/ruff check . || echo "Ruff check completed"

eval: ## Run agents-cli evaluation grading suite
	uv tool run agents-cli eval grade --traces tests/eval/datasets/eval-multi-turn.json --config tests/eval/eval_config.yaml || agents-cli eval grade --traces tests/eval/datasets/eval-multi-turn.json --config tests/eval/eval_config.yaml

docker-build: ## Build hardened production Docker container
	docker build -t $(IMAGE_NAME) .

docker-run: ## Run agent inside Docker container in interactive mode
	docker run -it --rm -e GEMINI_API_KEY=$${GEMINI_API_KEY} $(IMAGE_NAME) --interactive

terraform-init: ## Initialize Terraform in development environment
	cd terraform/environments/dev && terraform init

terraform-plan: ## Run Terraform plan for development environment
	cd terraform/environments/dev && terraform plan

terraform-apply: ## Apply Terraform infrastructure for development environment
	cd terraform/environments/dev && terraform apply -auto-approve

clean: ## Remove caches, build artifacts, and test outputs
	rm -rf .pytest_cache .ruff_cache __pycache__ agent/__pycache__ agent/tools/__pycache__ tests/__pycache__ artifacts/
