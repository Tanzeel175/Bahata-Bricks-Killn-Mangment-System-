#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment .venv..."
    python3 -m venv .venv --without-pip
    curl -sSL https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
    .venv/bin/pip install -r requirements.txt
fi

echo "Starting Bahata Bricks Kiln Management System..."
.venv/bin/python -m app.main
