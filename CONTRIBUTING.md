# Contributing to Contract Analyzer AI

Thank you for considering contributing! This document outlines the process.

## Development Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Code Style

- Format: `black`
- Imports: `isort --profile black`
- Lint: `flake8 --max-line-length=100 --extend-ignore=E203,W503`

Run all checks before committing:

```bash
black .
isort --profile black .
flake8 --max-line-length=100 --extend-ignore=E203,W503 .
pytest tests/ -v --cov=app
```

## Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

## Pull Request Process

1. Create a feature branch from `main`
2. Add tests for any new functionality
3. Ensure all tests pass
4. Update documentation if needed
5. Open a PR with a clear description

## Reporting Issues

Include:
- Python version
- Full error traceback
- Steps to reproduce
- Expected vs actual behavior
