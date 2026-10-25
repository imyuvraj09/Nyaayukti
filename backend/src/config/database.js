/**
 * Database connection manager using Mongoose.
 * Provides resilient connection handling, structured logging, status queries,
 * and graceful shutdown.
 */

const mongoose = require('mongoose');
const { MONGODB_URI, DATABASE_NAME } = require('./env');

let isConnected = false;
let memoryServerInstance = null;

/**
 * Connect to MongoDB with resilient timeout and retry settings.
 * @param {string} [customUri] - Optional override URI (e.g. for in-memory testing)
 * @returns {Promise<typeof mongoose>}
 */
async function connectDB(customUri) {
  const targetUri = customUri || MONGODB_URI;

  try {
    mongoose.set('strictQuery', true);

    const connection = await mongoose.connect(targetUri, {
      dbName: DATABASE_NAME,
      serverSelectionTimeoutMS: 2500,
      connectTimeoutMS: 5000,
    });

    isConnected = true;
    console.log('[MongoDB] Connected.');

    mongoose.connection.on('error', (err) => {
      console.error('[MongoDB] Connection error:', err.name);
      isConnected = false;
    });

    mongoose.connection.on('disconnected', () => {
      console.warn('[MongoDB] Connection lost / disconnected');
      isConnected = false;
    });

    return connection;
  } catch (err) {
    isConnected = false;
    console.warn(
      `[MongoDB] Connection failed (${err.name || 'Error'}). Check database configuration.`,
    );

    // In development or test environments, fallback seamlessly to in-memory MongoDB
    if (
      !customUri &&
      process.env.NODE_ENV !== 'production' &&
      process.env.ALLOW_EPHEMERAL_DATABASE === 'true'
    ) {
      try {
        console.log(
          '[MongoDB] Starting fallback in-memory MongoDB instance for local development...',
        );
        const { MongoMemoryServer } = require('mongodb-memory-server');
        memoryServerInstance = await MongoMemoryServer.create();
        const memUri = memoryServerInstance.getUri();

        const connection = await mongoose.connect(memUri, {
          dbName: DATABASE_NAME,
        });

        isConnected = true;
        console.log(`[MongoDB] Fallback in-memory database connected at: ${memUri}`);
        return connection;
      } catch (memErr) {
        console.error('[MongoDB] Failed to start fallback in-memory database:', memErr.message);
      }
    }

    throw new Error('MongoDB is unavailable; refusing to start with nonpersistent storage.');
  }
}

/**
 * Disconnect from MongoDB gracefully.
 */
async function disconnectDB() {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
    isConnected = false;
    console.log('[MongoDB] Disconnected successfully.');
  }

  if (memoryServerInstance) {
    await memoryServerInstance.stop();
    memoryServerInstance = null;
    console.log('[MongoDB] In-memory database instance stopped.');
  }
}

/**
 * Query the live status of the database connection.
 * @returns {{ connected: boolean, state: string, dbName: string }}
 */
function getConnectionStatus() {
  const states = ['disconnected', 'connected', 'connecting', 'disconnecting'];
  const currentState = states[mongoose.connection.readyState] || 'unknown';

  return {
    connected: mongoose.connection.readyState === 1,
    state: currentState,
    dbName: DATABASE_NAME,
  };
}

module.exports = {
  connectDB,
  disconnectDB,
  getConnectionStatus,
};
