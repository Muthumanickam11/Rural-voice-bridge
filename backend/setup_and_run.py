#!/usr/bin/env python3
"""
Rural Voice Bridge - Backend Setup and Dev Runner Script
Run this script to install deps and start the backend server.
"""
import subprocess, sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))

def run(cmd, **kw):
    print(f">>> {' '.join(cmd)}")
    subprocess.check_call(cmd, **kw)

def main():
    # Ensure .env exists
    env_src = os.path.join(ROOT, ".env.example")
    env_dst = os.path.join(ROOT, ".env")
    if not os.path.exists(env_dst):
        import shutil
        shutil.copy(env_src, env_dst)
        print("✅ Created .env from .env.example — fill in your API keys!")

    # Install Python dependencies
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=ROOT)

    # Create necessary directories
    for d in ["logs", "temp"]:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

    print("\n✅ Setup complete! Starting backend...\n")
    # Run the server
    run([sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"], cwd=ROOT)

if __name__ == "__main__":
    main()
