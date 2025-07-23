#!/usr/bin/env python
"""
Django management script wrapper that delegates to backend/manage.py
This allows Render to find manage.py in the expected location.
"""
import os
import sys

if __name__ == '__main__':
    # Get the directory containing this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(current_dir, 'backend')
    
    # Add backend directory to Python path
    sys.path.insert(0, backend_dir)
    
    # Change working directory to backend
    os.chdir(backend_dir)
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_finder.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)