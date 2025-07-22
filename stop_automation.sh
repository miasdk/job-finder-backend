#!/bin/bash

# Stop Personal Job Finder Automation

echo "🛑 Stopping Personal Job Finder Automation..."

# Stop Celery worker
if [ -f "celery_worker.pid" ]; then
    echo "👷 Stopping Celery worker..."
    celery multi stop worker --pidfile=celery_worker.pid
    rm -f celery_worker.pid
fi

# Stop Celery beat
if [ -f "celery_beat.pid" ]; then
    echo "📅 Stopping Celery beat scheduler..."
    celery multi stop beat --pidfile=celery_beat.pid
    rm -f celery_beat.pid
fi

# Kill any remaining Celery processes
pkill -f "celery worker"
pkill -f "celery beat"

echo "✅ All automation services stopped"
echo ""
echo "Note: Redis server and Django development server may still be running"
echo "Use Ctrl+C to stop Django if it's running in terminal"