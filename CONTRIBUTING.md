# Contributing to Contract Analyzer AI

Thank you for considering contributing! We welcome contributions of all kinds: bug reports, feature requests, documentation, and code.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/contract-analyzer-ai.git
cd contract-analyzer-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install all dependencies
make install-dev

# Install pre-commit hooks
pre-commit install
```

## Code Style

This project uses automated code quality tools:

- **Formatting:** [Black](https://github.com/psf/black) (line-length=100)
- **Imports:** [isort](https://github.com/PyCQA/isort) (profile=black)
- **Linting:** [flake8](https://github.com/PyCQA/flake8) (E203, W503 ignored)

Run all checks before committing:

```bash
make lint
make check-format
make test
```

Or use pre-commit (installed automatically):

```bash
pre-commit run --all-files
```

## Testing

We aim for 80%+ coverage with tests across all modules.

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
pytest tests/test_api.py -v
```

## Pull Request Process

1. Create a feature branch from `main` (`git checkout -b feature/amazing-feature`)
2. Add tests for any new functionality
3. Ensure all tests pass (`make test`)
4. Ensure code style is clean (`make lint && make check-format`)
5. Update documentation if needed (README, CHANGELOG)
6. Open a PR with a clear description of changes
7. Wait for review and address feedback

### PR Checklist

- [ ] Code follows project style (black, isort, flake8)
- [ ] Tests added for new functionality
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)

## Reporting Issues

Please use the GitHub issue tracker. Include:

- Python version and OS
- Full error traceback (if applicable)
- Steps to reproduce
- Expected vs actual behavior

For security vulnerabilities, see [SECURITY.md](SECURITY.md) — **do not** publicly report security issues.

## Project Structure

```
app/          — FastAPI backend (main, config, models, ingestion, retrieval, generation, evaluation)
tests/        — 160+ tests across 8 module
frontend/     — Streamlit web interface
docs/         — Documentation (CHANGELOG, QA audit)
data/         — Sample data and evaluation datasets
```

## Questions?

Open a [GitHub Discussion](https://github.com/your-username/contract-analyzer-ai/discussions) for questions and ideas.
