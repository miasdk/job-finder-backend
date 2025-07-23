#!/bin/bash
set -e

echo "Starting deployment..."
echo "Current directory: $(pwd)"
echo "Contents: $(ls -la)"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Start gunicorn with root WSGI
echo "Starting gunicorn..."
gunicorn wsgi:application --bind 0.0.0.0:$PORT