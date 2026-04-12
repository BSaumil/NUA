@echo off
REM ============================================================
REM NUVA POS — Windows .exe Build Script
REM ============================================================
REM Prerequisites:
REM   1. Node.js >= 18 installed
REM   2. yarn installed globally (npm install -g yarn)
REM
REM Usage:
REM   Double-click this file or run from command prompt:
REM   build-windows.bat
REM ============================================================

echo ========================================
echo   NUVA POS — Windows EXE Builder
echo ========================================

echo [1/4] Installing dependencies...
call yarn install
if errorlevel 1 goto :error

echo [2/4] Building React app...
set REACT_APP_BACKEND_URL=https://your-production-api.com
call npx craco build
if errorlevel 1 goto :error

echo [3/4] Packaging with Electron Builder...
call npx electron-builder --win --publish never
if errorlevel 1 goto :error

echo [4/4] Done!
echo ========================================
echo   EXE Ready: dist\NUVA POS Setup *.exe
echo ========================================
pause
goto :end

:error
echo Build failed! Check the error above.
pause

:end
