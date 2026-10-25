const { cookieToken } = require('./browserSession');
/**
 * Authentication middleware. Chat endpoints require a valid bearer token.
 */

const { authService } = require('../services/authService');
const { AuthenticationError } = require('../utils/errors');

function extractBearerToken(req) {
  const header = req.headers.authorization || '';
  const match = /^Bearer\s+(.+)$/i.exec(header);
  return match ? match[1].trim() : null;
}

async function requireAuth(req, _res, next) {
  try {
    const token = cookieToken(req) || extractBearerToken(req);
    if (!token) {
      throw new AuthenticationError('Please sign in to use the Nyaayukti legal assistant.');
    }

    const auth = await authService.getSessionFromToken(token);
    if (!auth) {
      throw new AuthenticationError('Your sign-in session has expired. Please sign in again.');
    }

    req.authToken = token;
    req.authSession = auth.session;
    req.user = auth.user;
    return next();
  } catch (err) {
    return next(err);
  }
}

module.exports = {
  requireAuth,
  extractBearerToken,
};
