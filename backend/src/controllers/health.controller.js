/**
 * Health check controller.
 * Reports gateway health, database connectivity, and RAG service reachability safely.
 */

const { getConnectionStatus } = require('../config/database');
const { NODE_ENV } = require('../config/env');
const { ragService } = require('../services/ragService');

const getHealth = async (_req, res) => {
  const dbStatus = getConnectionStatus();
  const ragStatus = await ragService.checkHealth();

  res.status(200).json({
    success: true,
    service: 'nyaayukti-backend',
    status: dbStatus.connected && ragStatus.available ? 'healthy' : 'degraded',
    environment: NODE_ENV,
    timestamp: new Date().toISOString(),
    database: {
      connected: dbStatus.connected,
      status: dbStatus.state,
      name: dbStatus.dbName,
    },
    ragService: {
      url: ragService.baseUrl,
      available: ragStatus.available,
      details: ragStatus.details,
    },
  });
};

module.exports = { getHealth };
