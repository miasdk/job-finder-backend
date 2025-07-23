"""
WSGI config for job_finder project at root level.
This ensures Render can find the Django app regardless of directory structure.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir / 'backend'
sys.path.insert(0, str(backend_dir))

# Change working directory to backend
os.chdir(str(backend_dir))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_finder.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()