#!/usr/bin/env python
"""
Django management script wrapper that delegates to backend/manage.py
This allows Render to find manage.py in the expected location.
"""
import os
import sys
import subprocess

if __name__ == '__main__':
    # Change to backend directory and run the real manage.py
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
    manage_py = os.path.join(backend_dir, 'manage.py')
    
    # Change working directory to backend
    os.chdir(backend_dir)
    
    # Execute the real manage.py with all arguments
    sys.exit(subprocess.call([sys.executable, manage_py] + sys.argv[1:]))