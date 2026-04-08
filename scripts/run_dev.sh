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

# Do NOT source .env here; let the app load it via python-dotenv.
# The app will automatically read .env using pydantic-settings or similar.
# If you must source, quote values in .env like: APP_NAME="Garuda Local"

# Start the development server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000