/**
 * AI Exam Guardian — Electron Preload Script
 *
 * Exposes a controlled, limited API to the renderer process.
 * contextIsolation: true ensures renderer cannot access Node.js APIs directly.
 */

const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('examGuardian', {
  version: () => process.env.npm_package_version || '0.1.0',
  platform: () => process.platform,
});
