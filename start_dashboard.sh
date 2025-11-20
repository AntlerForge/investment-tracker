#!/usr/bin/env bash
# Start the Risk Portfolio Dashboard web server

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing Flask..."
    pip install flask
fi

# Start the Flask app
echo "Starting Risk Portfolio Dashboard..."
echo "Dashboard will be available at: http://localhost:5001"
echo "Press Ctrl+C to stop"
echo ""

# Clear Python cache before starting
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Start with no bytecode and no reloader
export PYTHONDONTWRITEBYTECODE=1
export FLASK_ENV=production
export FLASK_DEBUG=0
python3 -B app.py

