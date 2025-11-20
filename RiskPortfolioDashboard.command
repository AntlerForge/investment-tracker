#!/usr/bin/env bash

# Risk Portfolio Dashboard Launcher
# This script can be placed in Applications folder and double-clicked to launch

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
PORT=5001
URL="http://localhost:${PORT}"

# Function to check if server is running
check_server() {
    lsof -ti:${PORT} > /dev/null 2>&1
}

# Function to start the server
start_server() {
    echo "Starting Risk Portfolio Dashboard..."
    echo ""
    
    # Activate virtual environment if it exists
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "⚠️  Warning: Virtual environment not found!"
        echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check if Flask is installed
    if ! python -c "import flask" 2>/dev/null; then
        echo "Installing Flask..."
        pip install -q flask
    fi
    
    # Start Flask server in background
    echo "Starting server on port ${PORT}..."
    python app.py > /tmp/risk-portfolio-dashboard.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to start (max 10 seconds)
    for i in {1..10}; do
        sleep 1
        if check_server; then
            echo "✅ Server started successfully!"
            return 0
        fi
    done
    
    echo "❌ Server failed to start. Check /tmp/risk-portfolio-dashboard.log for errors."
    return 1
}

# Function to open browser
open_browser() {
    echo "Opening dashboard in browser..."
    sleep 1
    open "${URL}"
}

# Main execution
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Risk Portfolio Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if server is already running
if check_server; then
    echo "✅ Dashboard server is already running on port ${PORT}"
    echo ""
    open_browser
else
    echo "🔄 Starting dashboard server..."
    echo ""
    
    if start_server; then
        echo ""
        open_browser
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Dashboard is running at: ${URL}"
        echo ""
        echo "To stop the server, run:"
        echo "  lsof -ti:${PORT} | xargs kill"
        echo ""
        echo "Or close this window and the server will continue running."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        # Keep the window open
        read -p "Press Enter to close this window (server will keep running)..."
    else
        echo ""
        echo "Failed to start dashboard. Please check the logs."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

