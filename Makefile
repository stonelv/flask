.DEFAULT_GOAL := help
UV_RUN = uv run --locked --no-default-groups

.PHONY: help
help: ## Show available commands
	@echo "Flask Development Commands"
	@echo "=========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: lint
lint: ## Run linting (ruff check + format)
	$(UV_RUN) --group dev tox run -e style

.PHONY: type
type: ## Run type checking (mypy + pyright)
	$(UV_RUN) --group dev tox run -e typing

.PHONY: test
test: ## Run tests on default Python version
	$(UV_RUN) --group dev tox run -e py

.PHONY: test-all
test-all: ## Run tests on all Python versions
	$(UV_RUN) --group dev tox run

.PHONY: bench
bench: ## Run benchmarks
	$(UV_RUN) --group dev tox run -e bench

.PHONY: docs
docs: ## Build documentation
	$(UV_RUN) --group dev tox run -e docs

.PHONY: docs-auto
docs-auto: ## Start auto-rebuilding docs server
	$(UV_RUN) --group dev tox run -e docs-auto

.PHONY: clean
clean: ## Remove build artifacts
	rm -rf dist/ build/ docs/_build/ .tox/ .mypy_cache/ .pyright/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

.PHONY: changelog-preview
changelog-preview: ## Preview upcoming changelog
	$(UV_RUN) --group dev towncrier build --draft --version=Unreleased

.PHONY: release-check
release-check: lint type test ## Verify release readiness
	@echo "✓ All checks passed. Ready for release."
