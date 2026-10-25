/**
 * ChatSession Mongoose Model.
 * Each legal conversation belongs to exactly one authenticated Nyaayukti user.
 */

const mongoose = require('mongoose');

const chatSessionSchema = new mongoose.Schema(
  {
    sessionId: {
      type: String,
      required: [true, 'sessionId is required'],
      unique: true,
      index: true,
      trim: true,
    },
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'userId is required'],
      index: true,
    },
    title: {
      type: String,
      default: 'New Legal Conversation',
      trim: true,
      maxlength: [120, 'Title cannot exceed 120 characters'],
    },
    lastActivityAt: {
      type: Date,
      default: Date.now,
      index: true,
    },
  },
  {
    timestamps: true,
    versionKey: false,
  },
);

chatSessionSchema.index({ userId: 1, lastActivityAt: -1 });

module.exports = mongoose.model('ChatSession', chatSessionSchema);
