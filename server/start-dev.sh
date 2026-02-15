#!/bin/bash

# Development startup script for local development (non-Docker)

echo "🚀 Starting Media Downloader Backend (Local Mode)"
echo "=================================================="

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running!"
    echo "Please start Redis first:"
    echo "  - Windows: redis-server"
    echo "  - Docker: docker run -d -p 6379:6379 redis:7-alpine"
    exit 1
fi

echo "✅ Redis is running"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded .env file"
fi

# Activate virtual environment if it exists
if [ -d "venv/Scripts" ]; then
    source venv/Scripts/activate
    echo "✅ Activated virtual environment"
elif [ -d "venv/bin" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment"
else
    echo "⚠️  Virtual environment not found"
fi

echo ""
echo "Starting services..."
echo "  - API: http://localhost:${PORT:-8000}"
echo "  - Flower: http://localhost:5555"
echo ""

# Start services in background using tmux or screen if available
if command -v tmux &> /dev/null; then
    echo "Using tmux to manage services..."

    # Create new tmux session
    tmux new-session -d -s mediadownloader

    # Window 0: API
    tmux send-keys -t mediadownloader:0 "uvicorn app.main:app --reload --host ${HOST:-0.0.0.0} --port ${PORT:-8000}" C-m

    # Window 1: Celery Worker
    tmux new-window -t mediadownloader:1
    tmux send-keys -t mediadownloader:1 "celery -A app.celery_app worker --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-4}" C-m

    # Window 2: Flower
    tmux new-window -t mediadownloader:2
    tmux send-keys -t mediadownloader:2 "celery -A app.celery_app flower --port=5555" C-m

    echo "✅ Services started in tmux session 'mediadownloader'"
    echo ""
    echo "To attach: tmux attach -t mediadownloader"
    echo "To stop: tmux kill-session -t mediadownloader"

else
    echo "⚠️  tmux not found. Starting services in foreground..."
    echo "Press Ctrl+C to stop"
    echo ""

    # Start Celery worker in background
    celery -A app.celery_app worker --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-4} &
    WORKER_PID=$!

    # Start Flower in background
    celery -A app.celery_app flower --port=5555 &
    FLOWER_PID=$!

    # Start API in foreground
    uvicorn app.main:app --reload --host ${HOST:-0.0.0.0} --port ${PORT:-8000}

    # Cleanup on exit
    kill $WORKER_PID $FLOWER_PID 2>/dev/null
fi
