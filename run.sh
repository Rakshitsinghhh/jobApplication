#!/usr/bin/env bash
# Quick launcher for Mail Campaigner
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup.sh..."
    exec ./setup.sh
fi

echo "🚀 Starting Mail Campaigner..."
source venv/bin/activate
exec python main.py
