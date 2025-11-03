@echo off
REM ====================================================================
REM Ananta POS - Windows Executable Build Script
REM ====================================================================
REM This script automates the build process for creating a Windows .exe
REM Run this script on your Windows machine after downloading the code
REM ====================================================================

echo ========================================
echo Ananta POS - Windows Build Script
echo ========================================
echo.

REM Check if Node.js is installed
echo [1/6] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed!
    echo Please download and install from: https://nodejs.org/
    pause
    exit /b 1
)
echo OK: Node.js found
echo.

REM Check if Python is installed
echo [2/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please download and install from: https://www.python.org/
    pause
    exit /b 1
)
echo OK: Python found
echo.

REM Build Backend
echo [3/6] Building backend executable...
echo This may take 5-10 minutes...
cd backend
pip install pyinstaller --quiet
pip install -r requirements.txt --quiet
python build_backend.py
if errorlevel 1 (
    echo ERROR: Backend build failed!
    pause
    exit /b 1
)
echo OK: Backend built successfully
cd ..
echo.

REM Setup Frontend
echo [4/6] Setting up frontend...
cd frontend

REM Install Yarn if not present
echo Checking for Yarn...
yarn --version >nul 2>&1
if errorlevel 1 (
    echo Installing Yarn...
    npm install -g yarn
)

REM Copy Electron package config
echo Preparing Electron configuration...
copy /Y electron-package.json package.json >nul

REM Install dependencies
echo Installing dependencies (this may take 5-10 minutes)...
call yarn install
call yarn add electron-is-dev

echo OK: Frontend setup complete
echo.

REM Build React App
echo [5/6] Building React application...
echo This may take 2-5 minutes...
call yarn build
if errorlevel 1 (
    echo ERROR: React build failed!
    pause
    exit /b 1
)
echo OK: React app built successfully
echo.

REM Build Electron Installer
echo [6/6] Building Electron installer...
echo This may take 10-15 minutes...
echo Please be patient, electron-builder downloads additional tools...
call yarn electron:build
if errorlevel 1 (
    echo ERROR: Electron build failed!
    echo Try running: yarn build:portable
    pause
    exit /b 1
)
echo.

echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo.
echo Your installer files are located at:
echo   %cd%\dist\Ananta POS-Setup-2.0.1.exe
echo   %cd%\dist\Ananta POS-Portable-2.0.1.exe
echo.
echo You can now distribute these files!
echo.
pause
