const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = require('electron-is-dev');
const fs = require('fs');

let mainWindow;
let backendProcess = null;
let mongoProcess = null;

const BACKEND_PORT = 8001;
const FRONTEND_PORT = 3000;

// Get resource paths
function getResourcePath(relativePath) {
  if (isDev) {
    return path.join(__dirname, '..', '..', relativePath);
  }
  return path.join(process.resourcesPath, relativePath);
}

// Start MongoDB
function startMongoDB() {
  return new Promise((resolve, reject) => {
    console.log('Starting MongoDB...');
    
    const mongoPath = getResourcePath('mongodb');
    const dbPath = path.join(app.getPath('userData'), 'mongodb-data');
    const logPath = path.join(app.getPath('userData'), 'mongodb.log');
    
    // Create data directory if it doesn't exist
    if (!fs.existsSync(dbPath)) {
      fs.mkdirSync(dbPath, { recursive: true });
    }
    
    const mongodExe = path.join(mongoPath, 'bin', 'mongod.exe');
    
    if (!fs.existsSync(mongodExe)) {
      console.log('MongoDB not found in packaged resources, using system MongoDB');
      resolve();
      return;
    }
    
    mongoProcess = spawn(mongodExe, [
      '--dbpath', dbPath,
      '--port', '27017',
      '--logpath', logPath,
      '--bind_ip', '127.0.0.1'
    ]);
    
    mongoProcess.stdout.on('data', (data) => {
      console.log(`MongoDB: ${data}`);
    });
    
    mongoProcess.stderr.on('data', (data) => {
      console.error(`MongoDB Error: ${data}`);
    });
    
    // Wait for MongoDB to start
    setTimeout(() => {
      console.log('MongoDB started');
      resolve();
    }, 3000);
  });
}

// Start Backend Server
function startBackend() {
  return new Promise((resolve, reject) => {
    console.log('Starting backend server...');
    
    const backendPath = getResourcePath('backend');
    const backendExe = path.join(backendPath, 'server.exe');
    
    if (!fs.existsSync(backendExe)) {
      console.error('Backend executable not found at:', backendExe);
      reject(new Error('Backend not found'));
      return;
    }
    
    // Set environment variables for backend
    const env = Object.assign({}, process.env, {
      MONGO_URL: 'mongodb://127.0.0.1:27017/nuva_pos',
      PORT: BACKEND_PORT.toString(),
      ENVIRONMENT: 'production'
    });
    
    backendProcess = spawn(backendExe, [], {
      cwd: backendPath,
      env: env
    });
    
    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data}`);
    });
    
    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data}`);
    });
    
    backendProcess.on('error', (error) => {
      console.error('Failed to start backend:', error);
      reject(error);
    });
    
    // Wait for backend to start
    setTimeout(() => {
      console.log('Backend server started');
      resolve();
    }, 2000);
  });
}

// Create main window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    minWidth: 1024,
    minHeight: 768,
    title: 'NUVA POS',
    icon: path.join(__dirname, '..', 'assets', 'icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    frame: true,
    backgroundColor: '#ffffff',
    show: false
  });

  // Load the app
  const startUrl = isDev
    ? `http://localhost:${FRONTEND_PORT}`
    : `file://${path.join(__dirname, '..', 'build', 'index.html')}`;

  mainWindow.loadURL(startUrl);

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.maximize();
  });

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Initialize app
async function initializeApp() {
  try {
    // Start MongoDB first
    await startMongoDB();
    
    // Then start backend
    await startBackend();
    
    // Finally create window
    createWindow();
  } catch (error) {
    console.error('Failed to initialize app:', error);
    app.quit();
  }
}

// App event handlers
app.on('ready', () => {
  setTimeout(initializeApp, 500);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  // Kill backend process
  if (backendProcess) {
    console.log('Stopping backend server...');
    backendProcess.kill();
  }
  
  // Kill MongoDB process
  if (mongoProcess) {
    console.log('Stopping MongoDB...');
    mongoProcess.kill();
  }
});

// Handle IPC messages
ipcMain.handle('get-backend-url', () => {
  return `http://localhost:${BACKEND_PORT}`;
});

ipcMain.handle('app-version', () => {
  return app.getVersion();
});
