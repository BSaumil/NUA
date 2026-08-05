#!/usr/bin/env python3
"""
Verify build prerequisites for NUA POS Windows executable
Run this script to check if your system is ready to build
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🔍 NUA POS - Build Prerequisites Checker")
    print("=" * 60)
    print()

def check_command(command, name, install_url):
    """Check if a command exists and return version"""
    print(f"Checking {name}...", end=" ")
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ FOUND: {version}")
            return True
        else:
            print(f"❌ NOT FOUND")
            print(f"   Install from: {install_url}")
            return False
    except FileNotFoundError:
        print(f"❌ NOT FOUND")
        print(f"   Install from: {install_url}")
        return False
    except Exception as e:
        print(f"⚠️  ERROR: {e}")
        return False

def check_python_path():
    """Check if Python is in PATH"""
    print("Checking Python PATH...", end=" ")
    python_path = sys.executable
    path_env = os.environ.get('PATH', '')
    python_dir = str(Path(python_path).parent)
    
    if python_dir in path_env:
        print(f"✅ OK: {python_path}")
        return True
    else:
        print(f"⚠️  WARNING: Python may not be in PATH")
        print(f"   Python location: {python_path}")
        return False

def check_pip_packages():
    """Check if required pip packages can be installed"""
    print("Checking pip...", end=" ")
    try:
        result = subprocess.run(
            ["pip", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ FOUND: {result.stdout.strip()}")
            return True
        else:
            print("❌ NOT FOUND")
            return False
    except:
        print("❌ NOT FOUND")
        return False

def check_mongodb_folder():
    """Check if MongoDB is prepared"""
    print("Checking MongoDB setup...", end=" ")
    
    # Try different possible locations
    possible_paths = [
        Path(__file__).parent / "mongodb" / "bin" / "mongod.exe",
        Path("/app/mongodb/bin/mongod.exe"),
        Path("mongodb/bin/mongod.exe"),
    ]
    
    for mongo_path in possible_paths:
        if mongo_path.exists():
            size_mb = mongo_path.stat().st_size / (1024 * 1024)
            print(f"✅ FOUND: {mongo_path} ({size_mb:.1f} MB)")
            return True
    
    print("❌ NOT FOUND")
    print("   Download MongoDB ZIP from: https://www.mongodb.com/try/download/community")
    print("   Extract and copy bin folder to: /app/mongodb/bin/")
    return False

def check_disk_space():
    """Check available disk space"""
    print("Checking disk space...", end=" ")
    try:
        if platform.system() == "Windows":
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (1024 ** 3)
            if free_gb >= 5:
                print(f"✅ OK: {free_gb} GB free")
                return True
            else:
                print(f"⚠️  LOW: Only {free_gb} GB free (need 5+ GB)")
                return False
        else:
            print("⚠️  SKIPPED: Not on Windows")
            return True
    except Exception as e:
        print(f"⚠️  ERROR: {e}")
        return True

def check_backend_structure():
    """Check if backend structure is correct"""
    print("Checking backend structure...", end=" ")
    
    backend_files = [
        Path(__file__).parent / "backend" / "server.py",
        Path(__file__).parent / "backend" / "requirements.txt",
        Path(__file__).parent / "backend" / "build_backend.py",
    ]
    
    missing = []
    for file in backend_files:
        if not file.exists():
            missing.append(file.name)
    
    if not missing:
        print("✅ OK: All files present")
        return True
    else:
        print(f"❌ MISSING: {', '.join(missing)}")
        return False

def check_frontend_structure():
    """Check if frontend structure is correct"""
    print("Checking frontend structure...", end=" ")
    
    frontend_files = [
        Path(__file__).parent / "frontend" / "package.json",
        Path(__file__).parent / "frontend" / "electron-package.json",
        Path(__file__).parent / "frontend" / "electron" / "main.js",
    ]
    
    missing = []
    for file in frontend_files:
        if not file.exists():
            missing.append(str(file.relative_to(Path(__file__).parent)))
    
    if not missing:
        print("✅ OK: All files present")
        return True
    else:
        print(f"❌ MISSING: {', '.join(missing)}")
        return False

def main():
    print_header()
    
    checks = []
    
    print("1️⃣  System Requirements")
    print("-" * 60)
    checks.append(check_command("node", "Node.js", "https://nodejs.org/"))
    checks.append(check_command("npm", "npm", "https://nodejs.org/"))
    checks.append(check_command("python", "Python", "https://www.python.org/"))
    checks.append(check_python_path())
    checks.append(check_pip_packages())
    checks.append(check_command("git", "Git", "https://git-scm.com/"))
    print()
    
    print("2️⃣  Build Dependencies")
    print("-" * 60)
    checks.append(check_mongodb_folder())
    checks.append(check_disk_space())
    print()
    
    print("3️⃣  Project Structure")
    print("-" * 60)
    checks.append(check_backend_structure())
    checks.append(check_frontend_structure())
    print()
    
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(checks)
    total = len(checks)
    
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED!")
        print("✅ Your system is ready to build NUA POS!")
        print("\nNext step: Run build_windows_exe.bat")
        return 0
    else:
        print(f"\n⚠️  {total - passed} issues found")
        print("❌ Please fix the issues above before building")
        print("\nSee QUICK_BUILD_GUIDE.md for detailed instructions")
        return 1

if __name__ == "__main__":
    sys.exit(main())
