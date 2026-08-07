#!/usr/bin/env python3
"""
Script to build standalone backend executable using PyInstaller
"""

import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("Building NUA POS Backend Executable...")
    
    # Get paths
    backend_dir = Path(__file__).parent
    dist_dir = backend_dir / "dist"
    build_dir = backend_dir / "build"
    
    # Clean previous builds
    if dist_dir.exists():
        print("Cleaning previous build...")
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # PyInstaller command
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=server",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--console",
        "--add-data", ".env:.",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "motor",
        "--hidden-import", "pydantic",
        "--hidden-import", "pymongo",
        "--hidden-import", "bcrypt",
        "--hidden-import", "pyserial",
        "--hidden-import", "dotenv",
        "--collect-all", "fastapi",
        "--collect-all", "uvicorn",
        "--collect-all", "pydantic",
        "server.py"
    ]
    
    print(f"Running: {' '.join(pyinstaller_cmd)}")
    
    try:
        result = subprocess.run(
            pyinstaller_cmd,
            cwd=backend_dir,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
        # Move the executable to a cleaner location
        exe_path = dist_dir / "server.exe"
        if exe_path.exists():
            print(f"\n✅ Backend executable built successfully!")
            print(f"Location: {exe_path}")
            print(f"Size: {exe_path.stat().st_size / (1024*1024):.2f} MB")
            
            # Copy .env file to dist
            env_file = backend_dir / ".env"
            if env_file.exists():
                shutil.copy(env_file, dist_dir / ".env")
                print("✅ .env file copied to dist folder")
            
            return True
        else:
            print("❌ Executable not found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
