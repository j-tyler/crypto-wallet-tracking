.PHONY: install test lint format check clean

# Install dependencies
install:
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	pytest tests/ -v --cov=scripts --cov-report=term-missing --cov-report=html

# Run linting
lint:
	flake8 scripts/ tests/
	mypy scripts/

# Format code
format:
	black scripts/ tests/

# Check formatting without modifying
format-check:
	black --check scripts/ tests/

# Run all checks (lint + test)
check: lint test

# Clean up build artifacts
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
