#!/bin/bash
cd backend
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn job_finder.wsgi:application --bind 0.0.0.0:$PORT