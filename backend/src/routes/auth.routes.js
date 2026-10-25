const express = require('express');
const authController = require('../controllers/auth.controller');
const { requireAuth } = require('../middleware/auth');

const router = express.Router();
const { rateLimit } = require('../middleware/rateLimit');
const recovery = require('../services/accountRecovery');
const authLimit = rateLimit({ name: 'auth', limit: 20, account: true });
const mailLimit = rateLimit({ name: 'account-mail', limit: 5, account: true });

router.post('/register', authLimit, authController.register);
router.post('/login', authLimit, authController.login);
router.get('/me', requireAuth, authController.me);
router.post('/logout', requireAuth, authController.logout);

router.get('/capabilities', (_req, res) => res.json({ emailDelivery: recovery.mailConfigured() }));
router.post('/forgot-password', mailLimit, async (req, res, next) => {
  try {
    await recovery.requestAction(req.body?.email, 'reset');
    res.json({ success: true, message: 'If the account exists, a reset link will be sent.' });
  } catch (err) {
    next(err);
  }
});
router.post('/send-verification', requireAuth, mailLimit, async (req, res, next) => {
  try {
    await recovery.requestAction(req.user.email, 'verify');
    res.json({ success: true, message: 'A verification link has been requested.' });
  } catch (err) {
    next(err);
  }
});
router.post('/reset-password', authLimit, async (req, res, next) => {
  try {
    await recovery.completeAction(req.body?.token, 'reset', req.body?.password);
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
});
router.post('/verify-email', authLimit, async (req, res, next) => {
  try {
    await recovery.completeAction(req.body?.token, 'verify');
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
});
module.exports = router;
