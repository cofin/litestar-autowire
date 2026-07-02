SHELL := /bin/bash

# =============================================================================
# Configuration and Environment Variables
# =============================================================================

.DEFAULT_GOAL := help
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

PYTHON_VERSION ?= 3.10
UV_RUN ?= uv run --python $(PYTHON_VERSION)
PACKAGE_DIR := litestar_autowire
TEST_DIR := tests
DOCS_DIR := docs
RUFF_DIRS := $(PACKAGE_DIR) $(TEST_DIR) $(DOCS_DIR)

# -----------------------------------------------------------------------------
# Display Formatting and Colors
# -----------------------------------------------------------------------------
BLUE := $(shell printf "\033[1;34m")
GREEN := $(shell printf "\033[1;32m")
RED := $(shell printf "\033[1;31m")
YELLOW := $(shell printf "\033[1;33m")
NC := $(shell printf "\033[0m")
INFO := $(shell printf "$(BLUE)ℹ$(NC)")
OK := $(shell printf "$(GREEN)✓$(NC)")
WARN := $(shell printf "$(YELLOW)⚠$(NC)")
ERROR := $(shell printf "$(RED)✖$(NC)")

# =============================================================================
# Help and Documentation
# =============================================================================

.PHONY: help
help:                                               ## Display this help text for Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# =============================================================================
# Installation and Environment Setup
# =============================================================================

.PHONY: install-uv
install-uv:                                         ## Install latest version of uv
	@echo "$(INFO) Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
	@echo "$(OK) uv installed successfully"

.PHONY: install
install: clean                                      ## Install development dependencies
	@echo "$(INFO) Installing project dependencies..."
	@uv sync --all-extras --dev
	@echo "$(OK) Installation complete"

.PHONY: destroy
destroy:                                            ## Destroy the virtual environment
	@echo "$(INFO) Destroying virtual environment..."
	@$(UV_RUN) pre-commit clean >/dev/null 2>&1 || true
	@rm -rf .venv
	@echo "$(OK) Virtual environment destroyed"

# =============================================================================
# Dependency Management
# =============================================================================

.PHONY: upgrade
upgrade:                                            ## Upgrade dependencies and pre-commit hooks
	@echo "$(INFO) Updating dependencies..."
	@uv lock --upgrade
	@echo "$(OK) Dependencies updated"
	@$(UV_RUN) pre-commit autoupdate
	@echo "$(OK) Pre-commit hooks updated"
	@uv lock >/dev/null 2>&1

.PHONY: lock
lock:                                               ## Refresh uv.lock
	@echo "$(INFO) Refreshing uv.lock..."
	@uv lock
	@echo "$(OK) Lockfile refreshed"

# =============================================================================
# Build and Release
# =============================================================================

.PHONY: build
build:                                              ## Build package distributions
	@echo "$(INFO) Building package..."
	@uv build
	@echo "$(OK) Package build complete"

.PHONY: release
release:                                            ## Bump version for a release (bump=major|minor|patch|pre)
	@if [ -z "$(bump)" ]; then \
		echo "$(ERROR) Usage: make release bump=major|minor|patch|pre"; \
		exit 1; \
	fi
	@echo "$(INFO) Preparing release bump ($(bump))..."
	@$(MAKE) clean
	@$(UV_RUN) bump-my-version bump $(bump)
	@uv lock
	@$(MAKE) build
	@echo "$(OK) Release version bumped successfully"

.PHONY: pre-release
pre-release:                                        ## Start a pre-release: make pre-release version=0.1.0-alpha.1
	@if [ -z "$(version)" ]; then \
		echo "$(ERROR) Usage: make pre-release version=X.Y.Z-alpha.N"; \
		echo ""; \
		echo "Pre-release workflow:"; \
		echo "  1. Start alpha:     make pre-release version=0.1.0-alpha.1"; \
		echo "  2. Next alpha:      make pre-release version=0.1.0-alpha.2"; \
		echo "  3. Move to beta:    make pre-release version=0.1.0-beta.1"; \
		echo "  4. Move to rc:      make pre-release version=0.1.0-rc.1"; \
		echo "  5. Final release:   make release bump=pre (from rc) OR bump=patch/minor (from stable)"; \
		exit 1; \
	fi
	@echo "$(INFO) Preparing pre-release $(version)..."
	@$(MAKE) clean
	@$(UV_RUN) bump-my-version bump --new-version $(version) pre
	@uv lock
	@$(MAKE) build
	@echo "$(OK) Pre-release version bumped successfully"

# =============================================================================
# Cleaning and Maintenance
# =============================================================================

.PHONY: clean
clean:                                              ## Cleanup temporary build artifacts
	@echo "$(INFO) Cleaning working directory..."
	@rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache .pyright .hypothesis build dist htmlcov coverage.xml coverage.json
	@find . \( -path ./.venv -o -path ./.git \) -prune -o -name '*.egg-info' -exec rm -rf {} +
	@find . \( -path ./.venv -o -path ./.git \) -prune -o -type f -name '*.egg' -exec rm -f {} +
	@find . \( -path ./.venv -o -path ./.git \) -prune -o -type f -name '*.pyc' -exec rm -f {} +
	@find . \( -path ./.venv -o -path ./.git \) -prune -o -type f -name '*.pyo' -exec rm -f {} +
	@find . \( -path ./.venv -o -path ./.git \) -prune -o -type f -name '*~' -exec rm -f {} +
	@find . \( -path ./.venv -o -path ./.git \) -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	@find . \( -path ./.venv -o -path ./.git \) -prune -o -type d -name '.ipynb_checkpoints' -exec rm -rf {} +
	@echo "$(OK) Working directory cleaned"
	@$(MAKE) docs-clean

# =============================================================================
# Testing and Quality Checks
# =============================================================================

.PHONY: test
test:                                               ## Run tests
	@echo "$(INFO) Running tests..."
	@$(UV_RUN) pytest $(TEST_DIR)
	@echo "$(OK) Tests complete"

.PHONY: test-all
test-all: test                                      ## Run all tests

.PHONY: quick-test
quick-test:                                         ## Run tests with fail-fast and failed-first behavior
	@echo "$(INFO) Running quick tests..."
	@$(UV_RUN) pytest $(TEST_DIR) -x --ff
	@echo "$(OK) Quick tests complete"

.PHONY: coverage
coverage:                                           ## Run tests with coverage
	@echo "$(INFO) Running tests with coverage..."
	@$(UV_RUN) pytest $(TEST_DIR) --cov=$(PACKAGE_DIR) --cov-report=term-missing --cov-report=xml --cov-report=html
	@echo "$(OK) Coverage report generated"

# -----------------------------------------------------------------------------
# Type Checking
# -----------------------------------------------------------------------------

.PHONY: mypy
mypy:                                               ## Run mypy
	@echo "$(INFO) Running mypy..."
	@$(UV_RUN) mypy $(PACKAGE_DIR) $(TEST_DIR)
	@echo "$(OK) Mypy checks passed"

.PHONY: pyright
pyright:                                            ## Run pyright
	@echo "$(INFO) Running pyright..."
	@$(UV_RUN) pyright $(PACKAGE_DIR) $(TEST_DIR)
	@echo "$(OK) Pyright checks passed"

.PHONY: type-check
type-check: mypy pyright                            ## Run all type checking

# -----------------------------------------------------------------------------
# Linting and Formatting
# -----------------------------------------------------------------------------

.PHONY: pre-commit
pre-commit:                                         ## Run pre-commit hooks
	@echo "$(INFO) Running pre-commit checks..."
	@$(UV_RUN) pre-commit run --color=always --all-files
	@echo "$(OK) Pre-commit checks passed"

.PHONY: ruff-check
ruff-check:                                         ## Run Ruff lint checks
	@echo "$(INFO) Running Ruff checks..."
	@$(UV_RUN) ruff check $(RUFF_DIRS)
	@echo "$(OK) Ruff checks passed"

.PHONY: ruff-format
ruff-format:                                        ## Format code and docs Python files
	@echo "$(INFO) Running Ruff format..."
	@$(UV_RUN) ruff format $(RUFF_DIRS)
	@echo "$(OK) Ruff formatting complete"

.PHONY: format-check
format-check:                                       ## Check formatting
	@echo "$(INFO) Checking formatting..."
	@$(UV_RUN) ruff format --check $(RUFF_DIRS)
	@echo "$(OK) Formatting check complete"

.PHONY: fix
fix:                                                ## Fix linting and formatting issues
	@echo "$(INFO) Fixing linting issues..."
	@$(UV_RUN) ruff check --fix --unsafe-fixes $(RUFF_DIRS)
	@$(UV_RUN) ruff format $(RUFF_DIRS)
	@echo "$(OK) Linting issues fixed"

.PHONY: slotscheck
slotscheck:                                         ## Run slotscheck
	@echo "$(INFO) Running slotscheck..."
	@$(UV_RUN) slotscheck $(PACKAGE_DIR)
	@echo "$(OK) Slotscheck complete"

.PHONY: lint
lint: ruff-check format-check type-check slotscheck ## Run all lint and type checks

.PHONY: check-all
check-all: lint test-all coverage                   ## Run all checks (lint, test, coverage)
	@echo "$(OK) All checks passed"

# =============================================================================
# Documentation
# =============================================================================

.PHONY: docs-clean
docs-clean:                                         ## Clean documentation build output
	@echo "$(INFO) Cleaning documentation build assets..."
	@rm -rf $(DOCS_DIR)/_build
	@echo "$(OK) Documentation assets cleaned"

.PHONY: docs
docs: docs-clean                                    ## Build documentation
	@echo "$(INFO) Building documentation..."
	@$(UV_RUN) sphinx-build -M html $(DOCS_DIR) $(DOCS_DIR)/_build -E -a -W --keep-going
	@echo "$(OK) Documentation built successfully"

.PHONY: docs-serve
docs-serve: docs-clean                              ## Serve documentation locally
	@echo "$(INFO) Starting documentation server..."
	@$(UV_RUN) sphinx-autobuild $(DOCS_DIR) $(DOCS_DIR)/_build/html --watch $(PACKAGE_DIR) --watch $(DOCS_DIR) --watch tools --port 8002

.PHONY: docs-linkcheck
docs-linkcheck:                                     ## Check documentation links
	@echo "$(INFO) Checking documentation links..."
	@$(UV_RUN) sphinx-build -b linkcheck $(DOCS_DIR) $(DOCS_DIR)/_build/linkcheck -D linkcheck_ignore='http://.*','https://.*'
	@echo "$(OK) Link check complete"

.PHONY: docs-linkcheck-full
docs-linkcheck-full:                                ## Run full documentation link check
	@echo "$(INFO) Running full link check..."
	@$(UV_RUN) sphinx-build -b linkcheck $(DOCS_DIR) $(DOCS_DIR)/_build/linkcheck -D linkcheck_anchors=0
	@echo "$(OK) Full link check complete"

# =============================================================================
# Development Targets
# =============================================================================

.PHONY: dev-setup
dev-setup: install lint test                        ## Complete development setup
	@echo "$(OK) Development environment ready"

# =============================================================================
# End of Makefile
# =============================================================================
