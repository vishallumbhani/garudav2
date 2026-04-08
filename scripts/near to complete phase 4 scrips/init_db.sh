#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

source venv/bin/activate

# Run async database initialization
python -c "import asyncio; from src.db.init_db import init_db; asyncio.run(init_db())"
