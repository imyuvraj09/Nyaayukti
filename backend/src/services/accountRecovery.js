const crypto = require('crypto');
const mongoose = require('mongoose');
const { User, AuthSession } = require('../models');
const { ValidationError, AppError } = require('../utils/errors');
const schema = new mongoose.Schema(
  {
    userId: mongoose.Schema.Types.ObjectId,
    tokenHash: { type: String, unique: true },
    purpose: String,
    expiresAt: Date,
  },
  { versionKey: false },
);
schema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
const Action = mongoose.models.AccountAction || mongoose.model('AccountAction', schema);
const hash = (value) => crypto.createHash('sha256').update(value).digest('hex');
function mailConfigured() {
  return (
    /^https:\/\//.test(process.env.MAIL_DELIVERY_URL || '') && !!process.env.MAIL_DELIVERY_TOKEN
  );
}
async function requestAction(email, purpose) {
  if (!mailConfigured())
    throw new AppError(
      'Email delivery is not configured. Contact the service administrator.',
      503,
      'MAIL_UNAVAILABLE',
    );
  const normalized = typeof email === 'string' ? email.trim().toLowerCase() : '';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized))
    throw new ValidationError('Enter a valid email address.');
  const user = await User.findOne({ email: normalized });
  if (!user || (purpose === 'verify' && user.emailVerified)) return;
  const token = crypto.randomBytes(32).toString('base64url');
  const action = await Action.create({
    userId: user._id,
    tokenHash: hash(token),
    purpose,
    expiresAt: new Date(Date.now() + 1800000),
  });
  // This endpoint must deliver the supplied message via an administrator-configured mail adapter.
  const url = new URL(process.env.FRONTEND_URL || 'http://localhost:5173');
  url.hash = `/account/${purpose}?token=${encodeURIComponent(token)}`;
  try {
    const response = await fetch(process.env.MAIL_DELIVERY_URL, {
      method: 'POST',
      redirect: 'error',
      signal: AbortSignal.timeout(10000),
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.MAIL_DELIVERY_TOKEN}`,
      },
      body: JSON.stringify({
        to: user.email,
        subject:
          purpose === 'reset' ? 'Reset your Nyaayukti password' : 'Verify your Nyaayukti email',
        text: `Open this link within 30 minutes: ${url.toString()}\nIgnore this email if you did not request it.`,
      }),
    });
    if (!response.ok) throw new Error('delivery failed');
  } catch {
    await Action.deleteOne({ _id: action._id });
    // Do not expose account existence through a different HTTP response.
    console.error('[Account mail] Delivery failed. Check the configured mail adapter.');
  }
}
async function completeAction(token, purpose, password) {
  if (typeof token !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(token))
    throw new ValidationError('Invalid or expired link.');
  let passwordData;
  if (purpose === 'reset') {
    const { hashPassword, validatePassword } = require('./authService');
    passwordData = await hashPassword(validatePassword(password));
  }
  const action = await Action.findOneAndDelete({
    tokenHash: hash(token),
    purpose,
    expiresAt: { $gt: new Date() },
  });
  if (!action) throw new ValidationError('Invalid or expired link.');
  if (purpose === 'reset') {
    await User.updateOne(
      { _id: action.userId },
      { $set: { passwordHash: passwordData.hash, passwordSalt: passwordData.salt } },
    );
    await AuthSession.deleteMany({ userId: action.userId });
  } else {
    await User.updateOne({ _id: action.userId }, { $set: { emailVerified: true } });
  }
  await Action.deleteMany({ userId: action.userId, purpose });
}
module.exports = { requestAction, completeAction, mailConfigured };
