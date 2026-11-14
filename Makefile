# AI-Native SDLC Engine — Developer Makefile
# ─────────────────────────────────────────────────────────────────────────────
# Usage:
#   make install    — full dev setup (deps + git hooks)
#   make test       — run test suite
#   make lint       — run ruff linter
#   make fmt        — auto-format with black + isort
#   make coverage   — coverage report with 50% threshold
#   make clean      — remove build/cache artifacts

.PHONY: install test lint fmt coverage clean

# ─── Setup ───────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt
	pre-commit install
	@echo "Dev environment ready. Git hooks installed."

# ─── Testing ─────────────────────────────────────────────────────────────────

test:
	pytest tests/ -x --tb=short -q

coverage:
	pytest tests/ --tb=short -q \
		--cov=sdlc_engine \
		--cov-report=term-missing \
		--cov-fail-under=50

# ─── Code Quality ─────────────────────────────────────────────────────────────

lint:
	ruff check sdlc_engine/ scripts/ --select E,W,F --ignore E501

fmt:
	black sdlc_engine/ scripts/ --line-length=120
	isort sdlc_engine/ scripts/ --profile=black --line-length=120

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
