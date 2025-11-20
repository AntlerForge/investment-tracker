#!/usr/bin/env bash
# Daily risk evaluation runner script
# This script runs the evaluate_risk.py script with proper environment setup

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the evaluation script
python scripts/evaluate_risk.py \
    --config config/portfolio.yaml \
    --signals config/signals.yaml

