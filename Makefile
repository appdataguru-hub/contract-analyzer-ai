.PHONY: help install install-dev lint format test coverage docker-up docker-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: install ## Install development dependencies
	pip install -r requirements-dev.txt

lint: ## Run linters
	flake8 app/ tests/ --max-line-length=100 --extend-ignore=E203,W503

format: ## Format code with black and isort
	black .
	isort --profile black .

check-format: ## Check formatting without changes
	black --check --diff app/ tests/
	isort --profile black --check-only --diff app/ tests/

test: ## Run tests
	pytest tests/ -v

coverage: ## Run tests with coverage
	coverage run -m pytest tests/ -v
	coverage report
	coverage html

docker-up: ## Start all services
	docker-compose up --build -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## View service logs
	docker-compose logs -f

clean: ## Clean cache and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
	rm -rf htmlcov .coverage
