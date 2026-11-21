#!/usr/bin/env bash
set -e

# Determine if the script is being sourced or executed
# If sourced: $0 is bash/zsh; if executed: $0 is the script path
IS_SOURCED=0
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    IS_SOURCED=1
fi

echo "=================================================="
echo " Setting up Job Application Mailer Environment"
echo "=================================================="

# Check Python 3 availability
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "❌ Error: Python 3 is not installed or not in your PATH."
    exit 1
fi

echo "Using Python: $($PYTHON_BIN --version)"

# Ensure we are in the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create virtual environment if missing or broken
if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment in ./venv..."
    $PYTHON_BIN -m venv venv
else
    echo "Virtual environment ready in ./venv."
fi

# Install dependencies
echo "Checking and installing dependencies from requirements.txt..."
./venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt

echo ""
echo "=================================================="
echo "✅ Environment ready!"
echo "=================================================="

if [ "$IS_SOURCED" -eq 1 ]; then
    # Script was sourced: activate venv in current shell
    source venv/bin/activate
    echo "Virtual environment activated in current shell."
    echo "Run 'python main.py' to start the application."
else
    # Script was executed directly: activate and launch main.py so it keeps running
    echo "🚀 Starting Mail Campaigner (keeping server running)..."
    echo "👉 Press Ctrl+C anytime to stop."
    echo "=================================================="
    source venv/bin/activate
    exec python main.py
fi
