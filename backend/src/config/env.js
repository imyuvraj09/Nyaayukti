/**
 * Environment configuration for Nyaayukti Node.js Backend.
 * Safely parses and validates environment variables with production-ready defaults.
 */

const PORT = parseInt(process.env.PORT, 10) || 3000;
const NODE_ENV = process.env.NODE_ENV || 'development';

// RAG Service Configuration
const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://127.0.0.1:8000';
const RAG_SERVICE_TIMEOUT_MS = parseInt(process.env.RAG_SERVICE_TIMEOUT_MS, 10) || 240000;

// MongoDB Configuration
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/nyaayukti';
const DATABASE_NAME = process.env.DATABASE_NAME || 'nyaayukti';

// Frontend Integration / CORS
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

// Authentication
const AUTH_SESSION_DAYS = Math.min(
  30,
  Math.max(1, parseInt(process.env.AUTH_SESSION_DAYS, 10) || 7),
);
const TRUST_PROXY_HOPS = Number(process.env.TRUST_PROXY_HOPS || 0);
if (!Number.isInteger(TRUST_PROXY_HOPS) || TRUST_PROXY_HOPS < 0 || TRUST_PROXY_HOPS > 5) {
  throw new Error('TRUST_PROXY_HOPS must be an integer between 0 and 5.');
}
if (NODE_ENV === 'production') {
  if ((process.env.RAG_SERVICE_TOKEN || '').length < 32)
    throw new Error('Use a service token of at least 32 characters.');
  if (new URL(FRONTEND_URL).protocol !== 'https:')
    throw new Error('Production FRONTEND_URL must use HTTPS.');
}

module.exports = {
  PORT,
  NODE_ENV,
  RAG_SERVICE_URL,
  RAG_SERVICE_TIMEOUT_MS,
  MONGODB_URI,
  DATABASE_NAME,
  FRONTEND_URL,
  AUTH_SESSION_DAYS,
  TRUST_PROXY_HOPS,
  RAG_SERVICE_TOKEN: process.env.RAG_SERVICE_TOKEN || '',
};
