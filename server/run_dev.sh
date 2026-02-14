#!/bin/bash

# Load environment variables
source .env 2>/dev/null || true

# Default values if not set
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

# Activate virtual environment
if [ -d "venv/Scripts" ]; then
    # Windows (Git Bash)
    source venv/Scripts/activate
elif [ -d "venv/bin" ]; then
    # Unix/Linux/Mac
    source venv/bin/activate
else
    echo "Virtual environment not found. Please create it first:"
    echo "  python -m venv venv"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "Starting FastAPI server on ${HOST}:${PORT}..."
uvicorn app.main:app --reload --host ${HOST} --port ${PORT}
