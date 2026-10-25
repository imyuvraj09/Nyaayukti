/**
 * Opaque authentication sessions.
 * The browser receives a random token; only its SHA-256 hash is stored.
 */

const mongoose = require('mongoose');

const authSessionSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
      index: true,
    },
    tokenHash: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    expiresAt: {
      type: Date,
      required: true,
      index: { expires: 0 },
    },
    lastUsedAt: {
      type: Date,
      default: Date.now,
    },
    userAgent: {
      type: String,
      default: '',
      maxlength: 500,
    },
  },
  {
    timestamps: true,
    versionKey: false,
  },
);

authSessionSchema.index({ userId: 1, expiresAt: 1 });

module.exports = mongoose.model('AuthSession', authSessionSchema);
