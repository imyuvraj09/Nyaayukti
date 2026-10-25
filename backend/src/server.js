/**
 * Nyaayukti Backend Server Entrypoint.
 * Connects to MongoDB, starts HTTP listener, and handles graceful shutdown.
 */

require('dotenv').config();
const app = require('./app');
const { connectDB, disconnectDB } = require('./config/database');
const { PORT } = require('./config/env');

async function startServer() {
  if (!process.env.RAG_SERVICE_TOKEN)
    throw new Error('Set RAG_SERVICE_TOKEN before starting the backend');
  // Resilient database connection attempt
  await connectDB();

  const server = app.listen(PORT, () => {
    console.log(`[Nyaayukti Backend] Server running on http://localhost:${PORT}`);
  });

  // Graceful shutdown handling
  const shutdown = async (signal) => {
    console.log(`\n[Nyaayukti Backend] Received ${signal}. Initiating graceful shutdown...`);
    server.close(async () => {
      try {
        await disconnectDB();
      } catch (err) {
        console.error('[Nyaayukti Backend] Error closing database connection:', err.message);
      }
      console.log('[Nyaayukti Backend] Server closed. Exiting process.');
      process.exit(0);
    });

    // Force close after 10 seconds if graceful shutdown hangs
    setTimeout(() => {
      console.error('[Nyaayukti Backend] Forced shutdown due to timeout.');
      process.exit(1);
    }, 10000);
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

startServer().catch(() => {
  console.error('Backend startup failed. Check database and service-token configuration.');
  process.exit(1);
});
