#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run setup_local.sh first."
    exit 1
fi

source venv/bin/activate

# Install test dependencies if not already installed
pip install -q pytest pytest-asyncio httpx pytest-cov

# Run the tests (optionally with coverage)
pytest src/tests/ -v
