/**
 * Protected chat and messaging routes.
 */

const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chat.controller');
const { requireAuth } = require('../middleware/auth');
const {
  validateSessionIdParam,
  validateMessageQuery,
  validatePagination,
} = require('../middleware/validate');

router.use(requireAuth);
const { rateLimit } = require('../middleware/rateLimit');
router.use((req, res, next) =>
  req.method === 'POST'
    ? rateLimit({ name: 'chat', limit: 30, windowMs: 60000 })(req, res, next)
    : next(),
);

router.post('/', (req, res, next) => {
  if (req.body && (req.body.message !== undefined || req.body.query !== undefined)) {
    return chatController.handleDirectChat(req, res, next);
  }
  return chatController.createChat(req, res, next);
});
router.get('/', validatePagination, chatController.listChats);
router.get('/:sessionId', validateSessionIdParam, chatController.getChat);
router.delete('/:sessionId', validateSessionIdParam, chatController.deleteChat);
router.post(
  '/:sessionId/messages',
  validateSessionIdParam,
  validateMessageQuery,
  chatController.postMessage,
);

module.exports = router;
