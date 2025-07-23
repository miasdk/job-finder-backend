#!/bin/bash
set -e

echo "Starting deployment..."
echo "Current directory: $(pwd)"
echo "Contents: $(ls -la)"

# Change to backend directory
cd backend
echo "Changed to backend directory: $(pwd)"
echo "Backend contents: $(ls -la)"

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
echo "Python path: $PYTHONPATH"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Start gunicorn
echo "Starting gunicorn..."
gunicorn job_finder.wsgi:application --bind 0.0.0.0:$PORT