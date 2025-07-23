#!/bin/bash

# Personal Job Finder - Full Automation Startup Script
# This script starts all services needed for automated job finding

echo "🚀 Starting Personal Job Finder Automation..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated"

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "🔴 Redis server not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

echo "✅ Redis server is running"

# Run Django migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Set up periodic tasks
echo "⏰ Setting up scheduled tasks..."
python manage.py setup_celery_beat

# Start Celery worker in background
echo "👷 Starting Celery worker..."
celery -A job_finder worker --loglevel=info --detach --pidfile=celery_worker.pid

# Start Celery beat scheduler in background  
echo "📅 Starting Celery beat scheduler..."
celery -A job_finder beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler --detach --pidfile=celery_beat.pid

# Start Django development server
echo "🌐 Starting Django web server..."
echo ""
echo "🎉 Personal Job Finder is now running!"
echo ""
echo "📊 Dashboard: http://localhost:8000"
echo "💼 Browse Jobs: http://localhost:8000/jobs/"
echo ""
echo "🤖 Automated Schedule:"
echo "• Job Scraping: Daily at 9 AM EST"
echo "• Email Digest: Daily at 7 PM EST" 
echo "• Weekly Cleanup: Sundays at 2 AM EST"
echo ""
echo "📧 Email will be sent to: miariccidev@gmail.com"
echo "   (Make sure to set EMAIL_HOST_PASSWORD in .env file)"
echo ""
echo "To stop automation, run: ./stop_automation.sh"
echo ""

python manage.py runserver 0.0.0.0:8000