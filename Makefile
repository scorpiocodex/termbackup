# TermBackup — Developer Makefile
# Run `make help` to see all available targets.

.DEFAULT_GOAL := help
PYTHON        := python3
POETRY        := poetry
VENV          := .venv
SRC           := termbackup
TESTS         := tests

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────
.PHONY: install
install:  ## Install all dependencies (incl. dev)
	$(POETRY) install

.PHONY: install-hooks
install-hooks:  ## Install pre-commit hooks
	$(POETRY) run pre-commit install

.PHONY: setup
setup: install install-hooks  ## Full dev environment bootstrap

# ── Code Quality ──────────────────────────────────────────────────────────────
.PHONY: lint
lint:  ## Run Ruff linter
	$(POETRY) run ruff check $(SRC) $(TESTS)

.PHONY: format
format:  ## Auto-format code with Ruff
	$(POETRY) run ruff format $(SRC) $(TESTS)

.PHONY: format-check
format-check:  ## Check formatting without modifying files
	$(POETRY) run ruff format --check $(SRC) $(TESTS)

.PHONY: typecheck
typecheck:  ## Run MyPy strict type checker
	$(POETRY) run mypy $(SRC)

.PHONY: check
check: lint format-check typecheck  ## Run all code quality checks

# ── Security ──────────────────────────────────────────────────────────────────
.PHONY: security
security:  ## Run Bandit security linter
	$(POETRY) run bandit -r $(SRC) -ll

.PHONY: audit
audit:  ## Audit dependencies for known CVEs (pip-audit)
	$(POETRY) run pip-audit

# ── Tests ─────────────────────────────────────────────────────────────────────
.PHONY: test
test:  ## Run the full test suite
	$(POETRY) run pytest $(TESTS) -v

.PHONY: test-fast
test-fast:  ## Run tests, stop on first failure
	$(POETRY) run pytest $(TESTS) -x -q

.PHONY: coverage
coverage:  ## Run tests with coverage report
	$(POETRY) run pytest $(TESTS) --cov=$(SRC) --cov-report=term-missing --cov-report=html

.PHONY: coverage-open
coverage-open: coverage  ## Open HTML coverage report
	$(PYTHON) -m webbrowser htmlcov/index.html

# ── Build ─────────────────────────────────────────────────────────────────────
.PHONY: build
build:  ## Build sdist + wheel via Poetry
	$(POETRY) build

.PHONY: clean-build
clean-build:  ## Remove build artefacts
	rm -rf dist/ build/ *.egg-info

# ── Pre-commit ────────────────────────────────────────────────────────────────
.PHONY: pre-commit
pre-commit:  ## Run all pre-commit hooks against staged files
	$(POETRY) run pre-commit run

.PHONY: pre-commit-all
pre-commit-all:  ## Run all pre-commit hooks against all files
	$(POETRY) run pre-commit run --all-files

# ── Combined CI target ────────────────────────────────────────────────────────
.PHONY: ci
ci: check security test  ## Run the full CI pipeline locally

# ── Misc ──────────────────────────────────────────────────────────────────────
.PHONY: clean
clean:  ## Remove caches and temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov       -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true

.PHONY: version
version:  ## Show current project version
	@$(POETRY) version
