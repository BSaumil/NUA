# 💻 Ananta POS - Windows Desktop Application Guide

**Build standalone Windows .exe installer for Ananta POS**

---

## 🎯 What You Get

**Single .exe installer that includes:**
- ✅ Complete Ananta POS application
- ✅ Built-in database (MongoDB embedded)
- ✅ No internet required for operation
- ✅ Auto-start on Windows boot
- ✅ System tray icon
- ✅ Desktop shortcuts
- ✅ Start menu entry
- ✅ One-click installation

---

## 🏗️ Build Methods

### Method 1: Electron + PyInstaller (Recommended)
**Best for:** Full-featured desktop app with native look

### Method 2: Tauri (Lightweight)
**Best for:** Smaller file size, faster performance

### Method 3: PyWebView (Simplest)
**Best for:** Quick deployment, minimal setup

---

## 📦 Method 1: Electron Package (Recommended)

### Step 1: Install Build Tools

```bash
# On your Windows development machine

# Install Node.js (if not installed)
# Download from: https://nodejs.org/

# Install Python (if not installed)
# Download from: https://www.python.org/

# Install build dependencies
npm install -g electron-builder
pip install pyinstaller
```

### Step 2: Build Backend Executable

```bash
cd /app/backend

# Create spec file for PyInstaller
pyinstaller --name AnantaPOS-Backend ^
  --onefile ^
  --add-data "models;models" ^
  --add-data "services;services" ^
  --hidden-import motor ^
  --hidden-import pymongo ^
  --hidden-import fastapi ^
  server.py

# Output: dist/AnantaPOS-Backend.exe
```

### Step 3: Build Frontend with Electron

```bash
cd /app/frontend

# Install Electron
npm install --save-dev electron electron-builder

# Build React app
npm run build

# Build Electron app
npm run electron:build

# Output: dist/Ananta-POS-Setup-2.0.1.exe
```

### Step 4: Create Unified Installer

```bash
# Use Inno Setup to combine both
# Download: https://jrsoftware.org/isinfo.php

# Run the installer script
iscc ananta-installer.iss

# Output: AnantaPOS-Setup-v2.0.1.exe
```

---

## 🚀 Quick Build Script (Automated)

### For Windows PowerShell:

```powershell
# build-windows.ps1

Write-Host "Building Ananta POS for Windows..." -ForegroundColor Green

# Build Backend
Write-Host "Building Backend..." -ForegroundColor Yellow
cd backend
pyinstaller ananta-backend.spec
cd ..

# Build Frontend
Write-Host "Building Frontend..." -ForegroundColor Yellow
cd frontend
npm run build
npm run electron:build
cd ..

# Create Installer
Write-Host "Creating Installer..." -ForegroundColor Yellow
iscc installer/ananta-installer.iss

Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "Installer: output/AnantaPOS-Setup-v2.0.1.exe"
```

**Run:**
```powershell
.\build-windows.ps1
```

---

## 📋 Installation Process

### What Happens When User Runs .exe:

1. **Welcome Screen**
   - Ananta POS logo
   - Version information
   - License agreement

2. **Installation Location**
   - Default: `C:\Program Files\AnantaPOS`
   - User can customize

3. **Components Selection**
   - [x] Ananta POS Application (Required)
   - [x] Desktop Shortcut
   - [x] Start Menu Entry
   - [ ] Start with Windows
   - [ ] Sample Data

4. **Installing Files**
   - Backend executable
   - Frontend files
   - MongoDB embedded
   - Configuration files
   - Drivers (printer, EFTPOS)

5. **First Run Setup**
   - Database initialization
   - Admin account creation
   - Business configuration
   - Hardware detection

6. **Completion**
   - Launch Ananta POS
   - Desktop shortcut created
   - System tray icon

---

## 🗂️ Installed Directory Structure

```
C:\Program Files\AnantaPOS\
├── AnantaPOS.exe              (Main launcher)
├── backend\
│   ├── AnantaPOS-Backend.exe  (FastAPI server)
│   └── config\
│       ├── settings.json
│       └── database.conf
├── frontend\
│   ├── index.html
│   ├── static\
│   └── assets\
├── mongodb\
│   ├── mongod.exe            (Embedded MongoDB)
│   └── data\
├── logs\
├── receipts\
└── backups\
```

---

## 🎨 Desktop Application Features

### 1. System Tray Integration
- ✅ Minimize to system tray
- ✅ Quick access menu
- ✅ Notifications
- ✅ Quick actions

### 2. Auto-Start Service
- ✅ Start backend on Windows boot
- ✅ Auto-login option
- ✅ Silent start mode

### 3. Native Features
- ✅ Windows notifications
- ✅ File associations (.receipt files)
- ✅ Context menu integration
- ✅ Keyboard shortcuts

### 4. Offline Database
- ✅ Embedded MongoDB
- ✅ Local data storage
- ✅ Automatic backups
- ✅ Data export/import

---

## 🔧 Build Configuration Files

### 1. PyInstaller Spec (backend/ananta-backend.spec)

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('models', 'models'),
        ('services', 'services'),
    ],
    hiddenimports=[
        'motor',
        'pymongo',
        'fastapi',
        'uvicorn',
        'pydantic',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pdb = PDB(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pdb,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AnantaPOS-Backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icon.ico'
)
```

### 2. Electron Main.js (frontend/electron/main.js)

```javascript
const { app, BrowserWindow, Tray, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let tray;
let backendProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    icon: path.join(__dirname, '../assets/icon.ico'),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    title: 'Ananta POS',
    autoHideMenuBar: true
  });

  // Load app
  mainWindow.loadFile('build/index.html');

  // System tray
  createTray();

  // Start backend
  startBackend();
}

function createTray() {
  tray = new Tray(path.join(__dirname, '../assets/tray-icon.ico'));
  
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Ananta POS', click: () => mainWindow.show() },
    { label: 'Settings', click: () => {} },
    { type: 'separator' },
    { label: 'Exit', click: () => app.quit() }
  ]);
  
  tray.setContextMenu(contextMenu);
  tray.setToolTip('Ananta POS');
}

function startBackend() {
  const backendPath = path.join(process.resourcesPath, 'backend', 'AnantaPOS-Backend.exe');
  backendProcess = spawn(backendPath);
  
  backendProcess.on('error', (err) => {
    console.error('Backend failed to start:', err);
  });
}

app.whenReady().then(createWindow);

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
```

### 3. Electron Builder Config (frontend/package.json)

```json
{
  "build": {
    "appId": "com.anantapos.app",
    "productName": "Ananta POS",
    "copyright": "Copyright © 2025 Ananta POS",
    "win": {
      "target": ["nsis"],
      "icon": "assets/icon.ico",
      "extraResources": [
        {
          "from": "../backend/dist",
          "to": "backend",
          "filter": ["**/*"]
        }
      ]
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "installerIcon": "assets/installer-icon.ico",
      "uninstallerIcon": "assets/uninstaller-icon.ico"
    }
  }
}
```

---

## 🎯 Alternative: Single-File Portable

### Create Portable Version (No Installation)

```bash
# Build portable package
npm run build:portable

# Output: AnantaPOS-Portable-v2.0.1.zip
# Extract anywhere and run AnantaPOS.exe
```

**Portable Features:**
- ✅ No installation needed
- ✅ Run from USB drive
- ✅ All data in same folder
- ✅ Easy backup (copy folder)
- ✅ Multiple instances

---

## 📦 Installer Distribution

### File Sizes (Approximate):
- **Full Installer:** ~250-300 MB
- **Portable ZIP:** ~300-350 MB
- **After Installation:** ~500-600 MB

### Distribution Options:

1. **Direct Download**
   - Host on your website
   - Google Drive/Dropbox
   - GitHub Releases

2. **Microsoft Store**
   - Submit as MSIX package
   - Automatic updates
   - Trust certification

3. **USB Distribution**
   - Portable version on USB
   - Auto-run setup
   - Offline installation

---

## 🔄 Auto-Updates

### Electron Auto-Updater:

```javascript
const { autoUpdater } = require('electron-updater');

autoUpdater.checkForUpdatesAndNotify();

autoUpdater.on('update-available', () => {
  dialog.showMessageBox({
    type: 'info',
    title: 'Update Available',
    message: 'A new version of Ananta POS is available. Download now?',
    buttons: ['Yes', 'Later']
  });
});
```

---

## 🛠️ Developer Tools

### Debug Mode:
```bash
# Run in development mode
AnantaPOS.exe --debug

# Features:
- DevTools enabled
- Console logging
- Hot reload
- Backend logs visible
```

---

## ✅ Pre-Built Download (Coming Soon)

**We'll provide ready-to-use installers:**
- AnantaPOS-Setup-v2.0.1.exe (Full installer)
- AnantaPOS-Portable-v2.0.1.zip (Portable)
- AnantaPOS-Update-v2.0.1.exe (Update only)

**System Requirements:**
- Windows 10/11 (64-bit)
- 4GB RAM minimum (8GB recommended)
- 1GB free disk space
- Admin rights for installation

---

## 🎁 Bonus Features

### 1. Silent Installation (for IT departments)
```cmd
AnantaPOS-Setup.exe /S /D=C:\AnantaPOS
```

### 2. Command Line Interface
```cmd
AnantaPOS.exe --backup
AnantaPOS.exe --restore backup.zip
AnantaPOS.exe --export-data
```

### 3. Network Installation
- Install on server
- Client PCs connect via network
- Shared database
- Centralized management

---

## 📞 Support

**Need Help Building?**
- Email: support@anantapos.com
- Video tutorial: Coming soon
- Build service: Available on request

**Want Pre-Built .exe?**
- Contact us for enterprise license
- Includes: Signed installer, auto-updates, support

---

<div align="center">

**Ananta POS - Desktop Edition**

Professional Windows Application

One-Click Installation • Offline Operation • Auto-Updates

</div>
