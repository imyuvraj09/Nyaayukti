/**
 * Express Application initialization for Nyaayukti Backend.
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const { FRONTEND_URL, NODE_ENV, TRUST_PROXY_HOPS } = require('./config/env');
const healthRoutes = require('./routes/health.routes');
const chatRoutes = require('./routes/chat.routes');
const authRoutes = require('./routes/auth.routes');
const errorHandler = require('./middleware/errorHandler');
const { sendError } = require('./utils/apiResponse');

const app = express();
const { browserGuard } = require('./middleware/browserSession');
// Trust only a configured, known proxy hop count; never blindly trust forwarded headers.
app.set('trust proxy', TRUST_PROXY_HOPS);

// --------------- Security & Parsing Middleware ---------------
app.use(helmet());

// CORS configuration (configured for React frontend)
const allowedOrigins = [
  FRONTEND_URL,
  ...(NODE_ENV !== 'production' ? ['http://localhost:5173', 'http://127.0.0.1:5173'] : []),
];

app.use(
  cors({
    origin: (origin, callback) => {
      // Allow requests with no origin (like mobile apps, curl, server-to-server)
      if (!origin || allowedOrigins.includes(origin)) {
        return callback(null, true);
      }
      const err = new (require('./utils/errors').AuthorizationError)('Untrusted request origin.');
      return callback(err);
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: [
      'Content-Type',
      'Authorization',
      'Accept',
      'X-Request-Id',
      'x-request-id',
      'X-Nyaayukti-Request',
      'x-nyaayukti-request',
      'X-NyayaSetu-Request',
      'x-nyayasetu-request',
    ],
    credentials: true,
    exposedHeaders: ['X-Request-Id', 'X-Conversation-Id', 'Retry-After'],
  }),
);

// Logging
if (NODE_ENV !== 'test') {
  app.use(morgan(':method :status :res[content-length] - :response-time ms'));
}

// Body parsers
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true, limit: '1mb' }));

app.use(browserGuard);
app.use(require('./middleware/requestId'));
app.use('/api', (_req, res, next) => {
  res.set('Cache-Control', 'no-store');
  next();
});

// --------------- Routes ---------------
app.get(['/', '/api'], (_req, res) => {
  return res.status(200).json({
    success: true,
    service: 'nyaayukti-backend',
    message: 'Nyaayukti Backend API Gateway is running.',
    version: '1.0.0',
    frontend: FRONTEND_URL,
    endpoints: {
      health: '/api/health',
      auth: '/api/auth',
      chat: '/api/chat (sign-in required)',
      chats: '/api/chats (sign-in required)',
    },
  });
});

app.use('/api/health', healthRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/chats', chatRoutes);

// --------------- 404 Handler ---------------
app.use((req, res) => {
  return sendError(
    res,
    'ROUTE_NOT_FOUND',
    `The requested endpoint '${req.method} ${req.originalUrl}' does not exist on this server.`,
    404,
  );
});

// --------------- Centralized Error Handler ---------------
app.use(errorHandler);

module.exports = app;
