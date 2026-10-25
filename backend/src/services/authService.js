/**
 * Authentication service for Nyaayukti.
 * Uses Node's built-in scrypt password hashing and opaque bearer sessions.
 */

const crypto = require('crypto');
const { promisify } = require('util');
const { User, AuthSession } = require('../models');
const { ValidationError, AuthenticationError, ConflictError } = require('../utils/errors');
const { AUTH_SESSION_DAYS } = require('../config/env');

const scryptAsync = promisify(crypto.scrypt);
const PASSWORD_KEY_LENGTH = 64;

function normalizeEmail(email) {
  return String(email || '')
    .trim()
    .toLowerCase();
}

function validateEmail(email) {
  const normalized = normalizeEmail(email);
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(normalized) || normalized.length > 254) {
    throw new ValidationError('Enter a valid email address.');
  }
  return normalized;
}

function validatePassword(password) {
  if (typeof password !== 'string' || password.length < 8) {
    throw new ValidationError('Password must contain at least 8 characters.');
  }
  if (password.length > 128) {
    throw new ValidationError('Password cannot exceed 128 characters.');
  }
  return password;
}

function validateDisplayName(name) {
  const clean = String(name || '')
    .trim()
    .replace(/\s+/g, ' ');
  if (clean.length < 2 || clean.length > 80) {
    throw new ValidationError('Name must be between 2 and 80 characters.');
  }
  return clean;
}

async function hashPassword(password, saltHex = null) {
  const salt = saltHex ? Buffer.from(saltHex, 'hex') : crypto.randomBytes(16);
  const derived = await scryptAsync(password, salt, PASSWORD_KEY_LENGTH);
  return {
    hash: Buffer.from(derived).toString('hex'),
    salt: salt.toString('hex'),
  };
}

async function verifyPassword(password, saltHex, expectedHashHex) {
  const { hash } = await hashPassword(password, saltHex);
  const actual = Buffer.from(hash, 'hex');
  const expected = Buffer.from(expectedHashHex, 'hex');
  if (actual.length !== expected.length) return false;
  return crypto.timingSafeEqual(actual, expected);
}

function hashSessionToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

function publicUser(user) {
  return {
    id: String(user._id),
    displayName: user.displayName,
    email: user.email,
    role: user.role,
    emailVerified: Boolean(user.emailVerified),
    createdAt: user.createdAt,
    lastLoginAt: user.lastLoginAt,
  };
}

async function createSession(user, userAgent = '') {
  const token = crypto.randomBytes(48).toString('base64url');
  const tokenHash = hashSessionToken(token);
  const expiresAt = new Date(Date.now() + AUTH_SESSION_DAYS * 24 * 60 * 60 * 1000);

  await AuthSession.create({
    userId: user._id,
    tokenHash,
    expiresAt,
    lastUsedAt: new Date(),
    userAgent: String(userAgent || '').slice(0, 500),
  });

  return { token, expiresAt };
}

async function register({ displayName, email, password, userAgent }) {
  const cleanName = validateDisplayName(displayName);
  const cleanEmail = validateEmail(email);
  const cleanPassword = validatePassword(password);

  const existing = await User.findOne({ email: cleanEmail }).lean();
  if (existing) {
    throw new ConflictError('An account with this email already exists. Please sign in instead.');
  }

  const passwordData = await hashPassword(cleanPassword);

  let user;
  try {
    user = await User.create({
      displayName: cleanName,
      email: cleanEmail,
      passwordHash: passwordData.hash,
      passwordSalt: passwordData.salt,
      lastLoginAt: new Date(),
    });
  } catch (err) {
    if (err?.code === 11000) {
      throw new ConflictError('An account with this email already exists. Please sign in instead.');
    }
    throw err;
  }

  const session = await createSession(user, userAgent);
  return { ...session, user: publicUser(user) };
}

async function login({ email, password, userAgent }) {
  const cleanEmail = validateEmail(email);
  const cleanPassword = validatePassword(password);

  const user = await User.findOne({ email: cleanEmail }).select('+passwordHash +passwordSalt');
  if (!user) {
    // Keep the expensive password check on both paths to reduce account timing leaks.
    await hashPassword(cleanPassword, '00000000000000000000000000000000');
    throw new AuthenticationError('Incorrect email or password.');
  }

  const valid = await verifyPassword(cleanPassword, user.passwordSalt, user.passwordHash);
  if (!valid) {
    throw new AuthenticationError('Incorrect email or password.');
  }

  user.lastLoginAt = new Date();
  await user.save();

  const session = await createSession(user, userAgent);
  return { ...session, user: publicUser(user) };
}

async function getSessionFromToken(token) {
  if (!token || typeof token !== 'string') return null;
  const tokenHash = hashSessionToken(token);
  const session = await AuthSession.findOne({
    tokenHash,
    expiresAt: { $gt: new Date() },
  });
  if (!session) return null;

  const user = await User.findById(session.userId);
  if (!user) {
    await AuthSession.deleteOne({ _id: session._id });
    return null;
  }

  const now = new Date();
  if (!session.lastUsedAt || now - session.lastUsedAt > 5 * 60 * 1000) {
    session.lastUsedAt = now;
    await session.save();
  }

  return { session, user };
}

async function logout(token) {
  if (!token) return;
  await AuthSession.deleteOne({ tokenHash: hashSessionToken(token) });
}

const authService = {
  register,
  login,
  logout,
  getSessionFromToken,
  publicUser,
  hashSessionToken,
};

module.exports = { authService };

module.exports.hashPassword = hashPassword;
module.exports.validatePassword = validatePassword;
