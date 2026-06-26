# Thin task runner over uv + tox + the bootstrap script.
# Mirrors the tox env names; no logic of its own. See scripts/bootstrap.sh for
# the clone-to-release flow.

.PHONY: help smoke test typing docs perf style check release-dry-run

help:
	@echo "make smoke       # fast smoke subset gate"
	@echo "make test        # full tox test matrix"
	@echo "make typing      # mypy + pyright"
	@echo "make docs        # sphinx build (-W)"
	@echo "make perf        # perf benchmarks vs baseline (advisory)"
	@echo "make style       # pre-commit on all files"
	@echo "make check       # bootstrap check (env + smoke + style + build)"
	@echo "make release-dry-run  # dry-run the semver release pipeline"

smoke:
	uv run --locked --no-default-groups --group dev tox run -e smoke

test:
	uv run --locked --no-default-groups --group dev tox run

typing:
	uv run --locked --no-default-groups --group dev tox run -e typing

docs:
	uv run --locked --no-default-groups --group dev tox run -e docs

perf:
	uv run --locked --no-default-groups --group dev tox run -e perf

style:
	uv run --locked --no-default-groups --group dev tox run -e style

check:
	./scripts/bootstrap.sh check

release-dry-run:
	./scripts/bootstrap.sh release
