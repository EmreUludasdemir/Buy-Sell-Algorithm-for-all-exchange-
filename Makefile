# ═══════════════════════════════════════════════════════════════════════════
# EPA Trading Bot - Makefile
# ═══════════════════════════════════════════════════════════════════════════
# Author: Emre Uludaşdemir
# Usage: make <target>
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: help install lint format test test-unit test-integration backtest hyperopt \
        docker-up docker-down docker-logs clean

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# ═══════════════════════════════════════════════════════════════════════════
# HELP
# ═══════════════════════════════════════════════════════════════════════════

help: ## Show this help message
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)    EPA Trading Bot - Available Commands$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ═══════════════════════════════════════════════════════════════════════════
# DEVELOPMENT
# ═══════════════════════════════════════════════════════════════════════════

install: ## Install dependencies
	@echo "$(BLUE)[1/2] Installing Python dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(BLUE)[2/2] Installing dev dependencies...$(NC)"
	pip install ruff pytest pytest-asyncio pytest-cov mypy
	@echo "$(GREEN)✓ Installation complete$(NC)"

lint: ## Run linter (ruff)
	@echo "$(BLUE)Running ruff linter...$(NC)"
	ruff check .
	@echo "$(GREEN)✓ Linting complete$(NC)"

lint-fix: ## Run linter and fix issues
	@echo "$(BLUE)Running ruff linter with auto-fix...$(NC)"
	ruff check . --fix
	@echo "$(GREEN)✓ Linting and fixing complete$(NC)"

format: ## Format code (ruff)
	@echo "$(BLUE)Formatting code with ruff...$(NC)"
	ruff format .
	@echo "$(GREEN)✓ Formatting complete$(NC)"

format-check: ## Check code formatting without changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	ruff format . --check
	@echo "$(GREEN)✓ Format check complete$(NC)"

typecheck: ## Run type checker (mypy)
	@echo "$(BLUE)Running mypy type checker...$(NC)"
	mypy src/ freqtrade/user_data/strategies/ --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking complete$(NC)"

# ═══════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	pytest tests/ -v
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/ -v -m "unit"
	@echo "$(GREEN)✓ Unit tests complete$(NC)"

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/ -v -m "integration"
	@echo "$(GREEN)✓ Integration tests complete$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest tests/ -v --cov=src --cov=freqtrade/user_data/strategies --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

# ═══════════════════════════════════════════════════════════════════════════
# FREQTRADE - DOCKER
# ═══════════════════════════════════════════════════════════════════════════

docker-up: ## Start Freqtrade bot (paper trading)
	@echo "$(BLUE)Starting Freqtrade bot...$(NC)"
	cd freqtrade && docker compose up -d
	@echo "$(GREEN)✓ Bot started. Web UI: http://127.0.0.1:8080$(NC)"

docker-down: ## Stop Freqtrade bot
	@echo "$(BLUE)Stopping Freqtrade bot...$(NC)"
	cd freqtrade && docker compose down
	@echo "$(GREEN)✓ Bot stopped$(NC)"

docker-logs: ## Show Freqtrade logs
	cd freqtrade && docker compose logs -f

docker-shell: ## Open shell in Freqtrade container
	cd freqtrade && docker compose exec freqtrade /bin/bash

# ═══════════════════════════════════════════════════════════════════════════
# FREQTRADE - BACKTESTING
# ═══════════════════════════════════════════════════════════════════════════

STRATEGY ?= EPAUltimateV3
TIMERANGE ?= 20240101-20241231
TIMEFRAME ?= 4h
PAIRS ?= BTC/USDT ETH/USDT

download-data: ## Download historical data
	@echo "$(BLUE)Downloading data for $(PAIRS)...$(NC)"
	cd freqtrade && docker compose run --rm freqtrade download-data \
		--config user_data/config.json \
		--timeframe $(TIMEFRAME) \
		--timerange $(TIMERANGE)
	@echo "$(GREEN)✓ Data download complete$(NC)"

backtest: ## Run backtest (use STRATEGY=name TIMERANGE=YYYYMMDD-YYYYMMDD)
	@echo "$(BLUE)Running backtest for $(STRATEGY)...$(NC)"
	@echo "$(YELLOW)Timerange: $(TIMERANGE) | Timeframe: $(TIMEFRAME)$(NC)"
	cd freqtrade && docker compose run --rm freqtrade backtesting \
		--strategy $(STRATEGY) \
		--config user_data/config.json \
		--timeframe $(TIMEFRAME) \
		--timerange $(TIMERANGE) \
		--enable-protections
	@echo "$(GREEN)✓ Backtest complete$(NC)"

backtest-futures: ## Run futures backtest
	@echo "$(BLUE)Running futures backtest...$(NC)"
	cd freqtrade && ./scripts/backtest_futures.sh $(TIMERANGE)

hyperopt: ## Run hyperopt optimization (use STRATEGY=name EPOCHS=n)
	@echo "$(BLUE)Running hyperopt for $(STRATEGY)...$(NC)"
	cd freqtrade && docker compose run --rm freqtrade hyperopt \
		--strategy $(STRATEGY) \
		--config user_data/config.json \
		--timeframe $(TIMEFRAME) \
		--timerange $(TIMERANGE) \
		--hyperopt-loss SharpeHyperOptLoss \
		--epochs $(or $(EPOCHS),100)
	@echo "$(GREEN)✓ Hyperopt complete$(NC)"

hyperopt-futures: ## Run futures hyperopt
	@echo "$(BLUE)Running futures hyperopt...$(NC)"
	cd freqtrade && ./scripts/hyperopt_futures.sh $(or $(EPOCHS),300) $(TIMERANGE)

# ═══════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

clean: ## Clean temporary files and caches
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

verify: ## Verify project setup
	@echo "$(BLUE)Verifying project setup...$(NC)"
	@echo ""
	@echo "$(YELLOW)Python version:$(NC)"
	@python --version
	@echo ""
	@echo "$(YELLOW)Required tools:$(NC)"
	@which ruff && echo "  ✓ ruff installed" || echo "  ✗ ruff not found"
	@which pytest && echo "  ✓ pytest installed" || echo "  ✗ pytest not found"
	@which docker && echo "  ✓ docker installed" || echo "  ✗ docker not found"
	@echo ""
	@echo "$(YELLOW)Freqtrade strategies:$(NC)"
	@ls -1 freqtrade/user_data/strategies/*.py 2>/dev/null | wc -l | xargs -I {} echo "  {} strategy files found"
	@echo ""
	@echo "$(GREEN)✓ Verification complete$(NC)"

# ═══════════════════════════════════════════════════════════════════════════
# CI/CD TARGETS
# ═══════════════════════════════════════════════════════════════════════════

ci: lint format-check test ## Run CI checks (lint + format check + tests)
	@echo "$(GREEN)✓ All CI checks passed$(NC)"

pre-commit: lint-fix format ## Run pre-commit checks (lint fix + format)
	@echo "$(GREEN)✓ Pre-commit checks complete$(NC)"
