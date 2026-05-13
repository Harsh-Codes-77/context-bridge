.PHONY: test test-coverage test-fast clean install-dev help

help:
	@echo "Available targets:"
	@echo "  make test            - Run all tests with verbose output"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo "  make test-fast       - Run tests and stop at first failure"
	@echo "  make install-dev     - Install dev dependencies"
	@echo "  make clean           - Clean cache and temp files"

test:
	pytest tests/

test-coverage:
	pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

test-fast:
	pytest tests/ -x

install-dev:
	pip install -r requirements.txt

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
