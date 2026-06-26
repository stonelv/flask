# One-click developer entrypoints. Thin wrappers over scripts/ and tox so a
# newcomer can go from clone to release without memorising commands.
#
#   make bootstrap   set up the dev environment from a fresh clone (uv)
#   make dev         format, lint, type-check, test with coverage
#   make test        run the test suite on the current interpreter
#   make perf        run benchmarks and compare against the baseline
#   make perf-update  refresh the committed performance baseline
#   make docs        build the documentation
#   make release     dry-run the release wizard (validate + suggest)
#   make clean       remove build/test/cache artifacts
#
# On Windows (no make), call the equivalents directly, e.g.
#   uv run --group tests pytest    /    bash scripts/dev.sh

.DEFAULT_GOAL := help
.PHONY: help bootstrap dev test perf perf-update docs release clean

help:
	@grep -E '^#   make ' $(MAKEFILE_LIST) | sed 's/^#   /  /'

bootstrap:
	@bash scripts/bootstrap.sh

dev:
	@bash scripts/dev.sh

test:
	@uv run --group tests pytest -q

perf:
	@bash scripts/perf.sh

perf-update:
	@bash scripts/perf.sh --update

docs:
	@uv run --no-default-groups --group dev tox run -e docs

release:
	@bash scripts/release.sh

clean:
	@rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov \
		dist build .perf-current.json
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
