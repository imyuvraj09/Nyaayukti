const { randomUUID } = require('node:crypto');
const { ValidationError } = require('../utils/errors');

function requestId(req, res, next) {
  const supplied = req.body?.requestId ?? req.headers['x-request-id'];
  if (
    supplied != null &&
    (typeof supplied !== 'string' || !/^[A-Za-z0-9_-]{1,80}$/.test(supplied))
  ) {
    return next(
      new ValidationError('Request ID must contain 1–80 letters, numbers, hyphens or underscores.'),
    );
  }
  req.requestId = supplied || randomUUID();
  res.set('X-Request-Id', req.requestId);
  next();
}

module.exports = requestId;
