/**
 * Cross-platform script to start the Nyaayukti FastAPI RAG Service.
 * Automatically detects virtual environment (Windows/Linux/macOS)
 * and starts uvicorn with hot-reload enabled.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const ragDir = path.join(rootDir, 'rag-service');

const venvPythonWin = path.join(rootDir, '.venv', 'Scripts', 'python.exe');
const venvPythonUnix = path.join(rootDir, '.venv', 'bin', 'python');

let pythonBin = 'python';

if (fs.existsSync(venvPythonWin)) {
  pythonBin = venvPythonWin;
} else if (fs.existsSync(venvPythonUnix)) {
  pythonBin = venvPythonUnix;
} else {
  console.warn('[rag-service] Virtualenv not found in root .venv. Using system python.');
}

const config = require('./check-setup').readEnv('rag-service');
const args = [
  '-m',
  'uvicorn',
  'main:app',
  '--reload',
  '--reload-dir',
  'api',
  '--reload-dir',
  'rag',
  '--reload-dir',
  'retrieval',
  '--reload-dir',
  'schemas',
  '--reload-dir',
  'utils',
  '--reload-dir',
  'llm',
  '--host',
  '127.0.0.1',
  '--port',
  config.PORT || '8000',
];
console.log('[rag-service] Project: ' + rootDir + '; pipeline: issue-evidence-v4.0');

const child = spawn(pythonBin, args, {
  cwd: ragDir,
  stdio: 'inherit',
  shell: false,
});

child.on('error', (err) => {
  console.error('[rag-service] Failed to start RAG service:', err.message);
  process.exit(1);
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.exit(0);
  }
  process.exit(code || 0);
});

const handleTermination = () => {
  if (process.platform === 'win32' && child.pid) {
    try {
      const { execSync } = require('child_process');
      execSync(`taskkill /pid ${child.pid} /t /f`, { stdio: 'ignore' });
    } catch (_e) {
      child.kill('SIGTERM');
    }
  } else {
    child.kill('SIGTERM');
  }
};

process.on('SIGINT', handleTermination);
process.on('SIGTERM', handleTermination);
