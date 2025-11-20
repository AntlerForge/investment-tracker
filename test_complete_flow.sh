#!/bin/bash
# Complete test of the evaluation flow
cd "$(dirname "$0")"
source .venv/bin/activate

echo "="
echo "COMPLETE FLOW TEST"
echo "="
echo ""
echo "1. Testing refresh flow (should work)..."
python3 test_evaluation_flow.py | grep -A 10 "TEST 1"
echo ""
echo "2. Testing evaluation flow (this breaks)..."
python3 test_evaluation_flow.py | grep -A 15 "TEST 2"
echo ""
echo "3. Testing Flask simulation (should work)..."
python3 test_flask_simulation.py | tail -15
echo ""
echo "="
echo "If Flask simulation shows correct values but dashboard shows wrong,"
echo "the issue is likely browser caching or JavaScript reload behavior."
echo "="
