/**
 * AI Exam Guardian — Electron Main Process
 *
 * NOTE: This is a placeholder for Phase 1.
 * Full desktop implementation is a future/advanced component.
 * Unsigned builds are NOT production-ready.
 * Platform-specific signing requirements apply.
 */

const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false, // Security: never enable nodeIntegration
    },
  });

  // In production, load the built React app
  // In development, connect to the dev server
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    win.loadURL('http://localhost:3000');
  } else {
    win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  }
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
