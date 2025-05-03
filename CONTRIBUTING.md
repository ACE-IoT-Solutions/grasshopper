# Contributing to Grasshopper

Thank you for your interest in contributing to Grasshopper! This document provides guidelines and instructions for contributing.

## Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/grasshopper.git
    cd grasshopper
    ```

2.  **Create and activate a virtual environment:**
    We recommend using `uv`:
    ```bash
    uv venv
    source .venv/bin/activate # Or equivalent for your shell
    ```

3.  **Install dependencies:**
    Install main and development dependencies using `uv`:
    ```bash
    uv pip sync pyproject.toml --extras dev
    ```

4.  **Running Tests:**
    ```bash
    pytest
    ```

5.  **Running Linters/Formatters:**
    ```bash
    # Example for mypy
    mypy grasshopper
    ```

6.  **Adding Dependencies:**
    *   Install the package into your environment: `uv pip install <package-name>`
    *   Manually add the package and version specifier to the appropriate list (`dependencies` or `optional-dependencies.dev`) in `pyproject.toml`.
    *   Re-sync the environment: `uv pip sync pyproject.toml --extras dev`

## Running Tests

We use pytest for testing. Here are several ways to run tests:

### Using the Script

We provide a script to run tests with different options:

```bash
# Run all tests
./scripts/run_tests.sh

# Run only API tests
./scripts/run_tests.sh --api-only

# Run tests with coverage
./scripts/run_tests.sh --coverage

# Run tests in verbose mode
./scripts/run_tests.sh --verbose
```

### Using pytest Directly

```bash
# Run all tests
pytest

# Run API tests
pytest tests/api/

# Run with coverage
pytest --cov=Grasshopper/grasshopper

# Generate HTML coverage report
pytest --cov=Grasshopper/grasshopper --cov-report=html
```

## Code Linting and Formatting

We use several tools to maintain code quality:

```bash
# Check code style with Black
black --check Grasshopper/grasshopper

# Format code with Black
black Grasshopper/grasshopper

# Check imports with isort
isort --check-only --profile black Grasshopper/grasshopper

# Sort imports with isort
isort --profile black Grasshopper/grasshopper

# Run static type checking
mypy --ignore-missing-imports Grasshopper/grasshopper

# Run linting
flake8 Grasshopper/grasshopper
```

## Pull Request Process

1. Fork the repository and create a new branch from `main`.
2. Make your changes, add tests, and ensure all tests pass.
3. Update the documentation to reflect any changes.
4. Submit a pull request to the `main` branch.
5. The PR must pass all CI checks and receive approvals from maintainers.

## API Changes

When making changes to the API:

1. Update the Pydantic models in `serializers.py`.
2. Add appropriate tests in the `tests/api/` directory.
3. Update any documentation related to the API.
4. Ensure all tests pass before submitting your PR.

## Project Structure

- `Grasshopper/grasshopper/` - Main application code
  - `api.py` - FastAPI endpoints
  - `web_app.py` - FastAPI application setup
  - `serializers.py` - Pydantic models
  - `agent.py` - Volttron agent code
- `tests/` - Test files
  - `api/` - API-specific tests
- `scripts/` - Utility scripts
- `.github/workflows/` - CI/CD configuration

## Code of Conduct

Please be respectful and constructive in your interactions with other contributors. We aim to foster an inclusive and welcoming community.