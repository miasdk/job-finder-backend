#!/usr/bin/env python3
"""
Build script for Render deployment
This ensures proper Django setup regardless of directory structure
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Starting Render build process...")
    
    # Get project root
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    print(f"📁 Project root: {project_root}")
    print(f"📁 Backend dir: {backend_dir}")
    
    # Change to backend directory
    os.chdir(backend_dir)
    print(f"📍 Changed to: {os.getcwd()}")
    
    # Install requirements
    print("📦 Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Run migrations
    print("🗃️ Running migrations...")
    subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
    
    # Collect static files
    print("📁 Collecting static files...")
    subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=True)
    
    print("✅ Build complete!")

if __name__ == "__main__":
    main()