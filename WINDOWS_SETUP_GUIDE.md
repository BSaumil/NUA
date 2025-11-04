# 🛠️ Windows PC Setup Guide - Ananta POS

## Overview

This guide will help you install everything needed on your Windows PC to build the Ananta POS .exe file.

**Time Required:** 15-25 minutes (one-time setup)

**What You'll Install:**
- Node.js (JavaScript runtime)
- Python (Backend runtime)
- Git (Version control)
- MongoDB (Database)

---

## 📋 Before You Start

**Prerequisites:**
- [ ] Windows 7, 8, 10, or 11 (64-bit)
- [ ] Administrator access
- [ ] 5+ GB free disk space
- [ ] Stable internet connection
- [ ] Code already downloaded to PC (see previous guides)

---

## 🎯 Installation Steps

### STEP 1: Install Node.js ⚡

**What is Node.js?**
JavaScript runtime needed for React frontend and Electron.

#### Download Node.js

1. **Go to:** https://nodejs.org/
2. **Choose:** LTS version (Long Term Support)
   - Should show something like "20.x.x LTS (Recommended for most users)"
3. **Click:** Download button
4. **Save:** `node-v20.x.x-x64.msi` file

**Download size:** ~30 MB
**Download time:** 1-2 minutes

---

#### Install Node.js

1. **Double-click** the downloaded `.msi` file
2. **UAC Prompt:** Click "Yes" (needs admin rights)
3. **Welcome Screen:** Click "Next"
4. **License:** Check "I accept" → Click "Next"
5. **Destination:** Leave default → Click "Next"
   - Default: `C:\Program Files\nodejs\`
6. **Custom Setup:** Keep all default options
   - ✅ Node.js runtime
   - ✅ npm package manager
   - ✅ Add to PATH
   - Click "Next"
7. **Tools for Native Modules:**
   - ✅ Check "Automatically install the necessary tools"
   - This installs build tools automatically
   - Click "Next"
8. **Ready to Install:** Click "Install"
9. **Progress:** Wait 2-3 minutes
10. **Completion:** Click "Finish"

**Post-Installation (Automated):**
- A PowerShell window may open
- It installs Python and build tools automatically
- Wait for it to complete (5-10 minutes)
- Press any key when prompted

---

#### Verify Node.js Installation

1. **Open Command Prompt:**
   - Press `Windows Key + R`
   - Type: `cmd`
   - Press Enter

2. **Check Node.js version:**
   ```bash
   node --version
   ```
   **Expected output:** `v20.x.x` (or similar)

3. **Check npm version:**
   ```bash
   npm --version
   ```
   **Expected output:** `10.x.x` (or similar)

**✅ If you see version numbers, Node.js is installed correctly!**

**❌ If you see "not recognized":**
- Restart Command Prompt
- If still fails, reinstall Node.js
- Make sure "Add to PATH" was checked

---

### STEP 2: Install Python 🐍

**What is Python?**
Programming language used for FastAPI backend.

#### Check if Python Already Installed

**If Node.js installed build tools, Python might already be installed!**

```bash
python --version
```

**If you see:** `Python 3.x.x` → Skip to Step 3 (Git)
**If you see:** "not recognized" → Continue below

---

#### Download Python

1. **Go to:** https://www.python.org/downloads/
2. **Click:** Big yellow "Download Python 3.x.x" button
3. **Save:** `python-3.x.x-amd64.exe` file

**Recommended version:** Python 3.9, 3.10, or 3.11
**Download size:** ~25 MB
**Download time:** 1-2 minutes

---

#### Install Python

**⚠️ CRITICAL:** The first step is the most important!

1. **Double-click** the downloaded `.exe` file
2. **UAC Prompt:** Click "Yes"

3. **⚠️ IMPORTANT - First Screen:**
   - **✅ CHECK:** "Add Python to PATH" (at bottom)
   - **✅ CHECK:** "Install launcher for all users"
   - **THEN CLICK:** "Install Now" (recommended)
   
   **THIS IS CRITICAL! Without checking "Add Python to PATH", nothing will work!**

4. **Progress:** Wait 2-3 minutes
5. **Setup was successful:** Click "Close"

**Optional but Recommended:**
- If you see "Disable path length limit" → Click it
- This prevents issues with long file paths

---

#### Verify Python Installation

1. **Close and reopen Command Prompt** (important!)

2. **Check Python version:**
   ```bash
   python --version
   ```
   **Expected output:** `Python 3.x.x`

3. **Check pip version:**
   ```bash
   pip --version
   ```
   **Expected output:** `pip 23.x.x from C:\...`

**✅ If you see version numbers, Python is installed correctly!**

**❌ If you see "not recognized":**

**FIX:**
1. Uninstall Python (Control Panel → Programs)
2. Reinstall Python
3. **MAKE SURE** to check "Add Python to PATH"!
4. Restart Command Prompt

---

### STEP 3: Install Git 📚

**What is Git?**
Version control system (needed if you skipped it earlier).

#### Check if Git Already Installed

```bash
git --version
```

**If you see:** `git version 2.x.x` → Skip to Step 4 (MongoDB)
**If you see:** "not recognized" → Continue below

---

#### Download Git

1. **Go to:** https://git-scm.com/
2. **Click:** "Download for Windows"
3. **Save:** `Git-2.x.x-64-bit.exe` file

**Download size:** ~50 MB
**Download time:** 2-3 minutes

---

#### Install Git

**Just use default settings for everything:**

1. **Double-click** the downloaded `.exe` file
2. **UAC Prompt:** Click "Yes"
3. **License:** Click "Next"
4. **Destination:** Leave default → Click "Next"
5. **Components:** Leave all checked → Click "Next"
6. **Start Menu:** Leave default → Click "Next"
7. **Default Editor:** Leave as "Vim" or choose "Nano" → Click "Next"
8. **Adjusting PATH:** Leave "Git from command line" → Click "Next"
9. **HTTPS:** Leave default → Click "Next"
10. **Line Endings:** Leave default → Click "Next"
11. **Terminal:** Leave "MinTTY" → Click "Next"
12. **Pull behavior:** Leave default → Click "Next"
13. **Credential Manager:** Leave default → Click "Next"
14. **Extra Options:** Leave defaults → Click "Next"
15. **Experimental:** Uncheck all → Click "Install"
16. **Progress:** Wait 1-2 minutes
17. **Completion:** Uncheck "View Release Notes" → Click "Finish"

**Don't worry about all those options - defaults work perfectly!**

---

#### Verify Git Installation

1. **Close and reopen Command Prompt**

2. **Check Git version:**
   ```bash
   git --version
   ```
   **Expected output:** `git version 2.x.x`

**✅ If you see version number, Git is installed correctly!**

---

### STEP 4: Download MongoDB Portable 🗄️

**What is MongoDB?**
Database that will be embedded in your .exe file.

#### Download MongoDB

1. **Go to:** https://www.mongodb.com/try/download/community

2. **Select:**
   - Version: `6.0.x` or higher (current stable)
   - Platform: `Windows`
   - Package: **`ZIP`** (not MSI!)
   
3. **Click:** "Download"

4. **Save:** `mongodb-windows-x86_64-6.0.x.zip` file

**Download size:** ~250-300 MB
**Download time:** 5-10 minutes

**💡 Important:** Make sure you select **ZIP**, not MSI!

---

#### Extract and Prepare MongoDB

1. **Navigate to Downloads folder**

2. **Right-click** `mongodb-windows-x86_64-6.0.x.zip`

3. **Select:** "Extract All..."

4. **Extract to:** Downloads folder → Click "Extract"

5. **Open the extracted folder**
   - You'll see a folder like `mongodb-win32-x86_64-windows-6.0.x`
   - Inside that, find the `bin` folder

6. **Copy the entire `bin` folder**

7. **Navigate to your Ananta POS project:**
   - Example: `C:\Users\YourName\Documents\AnantaPOS\`

8. **Create folder structure:**
   - Create folder: `mongodb`
   - Inside mongodb, paste the `bin` folder

**Final structure should be:**
```
AnantaPOS\
├── backend\
├── frontend\
├── mongodb\              ← Create this
│   └── bin\              ← Paste this
│       ├── mongod.exe    ← Should contain these
│       ├── mongo.exe
│       └── (many other files)
└── (other files...)
```

---

#### Verify MongoDB Setup

**Check files exist:**

1. Navigate to: `YourProject\mongodb\bin\`

2. **Verify these files exist:**
   - `mongod.exe` (50-60 MB)
   - `mongo.exe` (30-40 MB)
   - Many `.dll` files

**✅ If you see these files, MongoDB is ready!**

---

## 🧪 Final Verification

### Run Complete System Check

**Navigate to your project folder in Command Prompt:**

```bash
cd C:\Users\YourName\Documents\AnantaPOS
```

**Run the checker script:**

```bash
python check_prerequisites.py
```

**Expected output:**

```
=============================================================
🔍 Ananta POS - Build Prerequisites Checker
=============================================================

1️⃣  System Requirements
------------------------------------------------------------
Checking Node.js... ✅ FOUND: v20.x.x
Checking npm... ✅ FOUND: 10.x.x
Checking Python... ✅ FOUND: Python 3.x.x
Checking Python PATH... ✅ OK
Checking pip... ✅ FOUND: pip 23.x.x
Checking Git... ✅ FOUND: git version 2.x.x

2️⃣  Build Dependencies
------------------------------------------------------------
Checking MongoDB setup... ✅ FOUND: C:\...\mongodb\bin\mongod.exe
Checking disk space... ✅ OK: XX GB free

3️⃣  Project Structure
------------------------------------------------------------
Checking backend structure... ✅ OK: All files present
Checking frontend structure... ✅ OK: All files present

=============================================================
📊 SUMMARY
=============================================================
Checks passed: 11/11

🎉 ALL CHECKS PASSED!
✅ Your system is ready to build Ananta POS!

Next step: Run build_windows_exe.bat
```

**✅ If all checks pass, you're ready to build!**

**❌ If any checks fail, see Troubleshooting below.**

---

## ✅ Success Checklist

After completing this guide:

- [ ] Node.js installed and verified (`node --version` works)
- [ ] npm installed and verified (`npm --version` works)
- [ ] Python installed and verified (`python --version` works)
- [ ] pip installed and verified (`pip --version` works)
- [ ] Git installed and verified (`git --version` works)
- [ ] MongoDB extracted to `mongodb/bin/` folder
- [ ] `mongod.exe` exists in project folder
- [ ] All checks pass in `check_prerequisites.py`
- [ ] Command Prompt open in project directory

---

## 🎯 What's Next?

### ➡️ Next Step: Build the .exe File!
**Read:** `WINDOWS_BUILD_GUIDE.md`

Now that your Windows PC is set up, you're ready to build the .exe file!

**Time:** 20-35 minutes (mostly automated)

---

## 🚨 Troubleshooting

### Node.js Issues

**"node is not recognized"**
1. Restart Command Prompt
2. If still fails, reinstall Node.js
3. During install, ensure "Add to PATH" is checked
4. After reinstall, restart PC

---

### Python Issues

**"python is not recognized" - MOST COMMON ISSUE**

**Solution:**
1. **Uninstall Python:**
   - Windows Key → Settings → Apps
   - Find "Python 3.x"
   - Click → Uninstall

2. **Reinstall Python:**
   - Download again from python.org
   - **CRITICAL:** Check "Add Python to PATH"
   - Install

3. **Verify:**
   - Close all Command Prompts
   - Open new Command Prompt
   - Run: `python --version`

4. **Still fails? Manual PATH fix:**
   - Windows Key → "Environment Variables"
   - Edit "Path" variable
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3x\`
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3x\Scripts\`
   - Click OK
   - Restart Command Prompt

---

### Git Issues

**"git is not recognized"**
1. Restart Command Prompt
2. If still fails, reinstall Git
3. After reinstall, restart PC

---

### MongoDB Issues

**"MongoDB not found"**
1. Verify you downloaded ZIP (not MSI)
2. Check folder structure:
   ```
   YourProject\mongodb\bin\mongod.exe
   ```
3. The path must be exactly: `mongodb\bin\` (not `mongodb\mongodb\bin\`)
4. Re-extract if structure is wrong

**"mongod.exe missing"**
1. Re-download MongoDB ZIP
2. Extract completely
3. Copy entire `bin` folder
4. Don't copy individual files

---

### Disk Space Issues

**"Not enough disk space"**

**You need at least 5 GB free:**
- Node.js: ~500 MB
- Python: ~200 MB
- MongoDB: ~300 MB
- Build files: ~2 GB
- Final .exe: ~300 MB
- Temporary files: ~1-2 GB

**Solutions:**
1. Free up disk space
2. Use different drive with more space
3. Clean temporary files:
   - Windows Key + R → `cleanmgr` → Run Disk Cleanup

---

### Permission Issues

**"Access denied" during installation**

**Solution:**
1. Right-click installer
2. Select "Run as administrator"
3. Click "Yes" on UAC prompt

---

### Internet Connection Issues

**Downloads fail or timeout**

**Solutions:**
1. Check internet connection
2. Try different browser
3. Disable VPN temporarily
4. Disable antivirus temporarily
5. Try downloading on different network
6. Use download manager for large files

---

## 💡 Pro Tips

### Keep Installers
Don't delete the downloaded installers until build succeeds. You might need to reinstall.

### Restart After Everything
After installing everything, restart your computer. This ensures all PATH changes take effect.

### Windows Defender
If Windows Defender blocks any installers, click "More info" → "Run anyway". These are safe, official downloads.

### Updates
After successful build, you can update installed software:
- Node.js: Check nodejs.org periodically
- Python: Check python.org periodically
- Git: Git auto-updates

### Documentation
Keep the installation guides until you successfully build the .exe.

---

## ✨ Summary

**What you accomplished:**
1. ✅ Installed Node.js and npm
2. ✅ Installed Python and pip
3. ✅ Installed Git
4. ✅ Downloaded and prepared MongoDB
5. ✅ Verified all installations
6. ✅ System ready for building!

**What's next:**
1. ➡️ Build the .exe file (WINDOWS_BUILD_GUIDE.md)

---

**🎉 Excellent! Your Windows PC is now fully prepared!**

**Next:** Open `WINDOWS_BUILD_GUIDE.md` to build your .exe file!
