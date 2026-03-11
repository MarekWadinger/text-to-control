# Task runner for python-project-template
# Requires `just` (https://github.com/casey/just) and `uv`

# Use bash for interactive prompts and bashisms
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default:
    @just --list

help:
    @just --list

install:
    @echo "📦 Installing project dependencies..."
    uv sync
    plotly_get_chrome

dev-install:
    @echo "🛠️  Installing development dependencies..."
    uv sync --all-groups
    plotly_get_chrome

install-hooks:
    @echo "🪝 Installing pre-commit hooks..."
    uv run pre-commit install

env-encrypt:
    @echo "Encrypting .env file using openssl..."
    if [ -z "${ENV_PASSWORD-}" ]; then \
        openssl aes-256-cbc -a -salt -pbkdf2 -in .env -out .env.enc; \
    else \
        openssl aes-256-cbc -a -salt -pbkdf2 -in .env -out .env.enc -pass pass:\""$ENV_PASSWORD"\"; \
    fi
    @echo "✓ .env encrypted to .env.enc"

env-decrypt:
    @echo "Decrypting .env file using openssl..."
    if [ -z "${ENV_PASSWORD-}" ]; then \
        openssl aes-256-cbc -d -a -pbkdf2 -in .env.enc -out .env; \
    else \
        openssl aes-256-cbc -d -a -pbkdf2 -in .env.enc -out .env -pass pass:\""$ENV_PASSWORD"\"; \
    fi
    @echo "✓ .env decrypted from .env.enc"

test:
    @echo "🧪 Running tests..."
    uv run pytest

test-cov:
    @echo "🧪 Running tests with coverage..."
    uv run pytest --cov=src --cov-report=term --cov-report=html --cov-report=xml

lint:
    @echo "🔍 Running linting..."
    uv run ty check .

format:
    @echo "🎨 Formatting code..."
    uv run ruff format .

pre-commit-run:
    @echo "🔍 Running pre-commit hooks..."
    uv run pre-commit run --all-files

pre-commit-update:
    @echo "🔍 Updating pre-commit hooks..."
    uv run pre-commit autoupdate

security:
    @echo "🔒 Running security checks..."
    uv run bandit -r src/ -f json -o bandit-report.json

clean:
    @echo "🧹 Cleaning build artifacts..."
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info/
    rm -rf .coverage
    rm -rf htmlcov/
    rm -rf .pytest_cache/
    rm -rf .mypy_cache/
    find . -type d -name __pycache__ -delete
    find . -type f -name "*.pyc" -delete

build:
    @echo "🏗️  Building package..."
    uv build

validator-build:
    @echo "🐳 Building validator Docker sandbox..."
    docker build -t text-to-control-validator docker/validator/

check:
    just lint
    just test
    just security
