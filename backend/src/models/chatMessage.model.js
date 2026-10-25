/**
 * ChatMessage Mongoose Model.
 * Stores user and assistant messages with source citations and RAG metadata.
 */

const mongoose = require('mongoose');

const sourceReferenceSchema = new mongoose.Schema(
  {
    sourceNumber: {
      type: Number,
    },
    sourceLabel: {
      type: String,
      trim: true,
    },
    documentName: {
      type: String,
      trim: true,
    },
    chunkId: {
      type: String,
      trim: true,
    },
    pageNumbers: {
      type: [Number],
      default: [],
    },
    relevanceScore: {
      type: Number,
      default: null,
    },
    snippet: {
      type: String,
      default: '',
    },
    evidenceType: {
      type: String,
      default: 'STATUTE',
    },
    caseName: {
      type: String,
      default: null,
    },
    court: {
      type: String,
      default: null,
    },
    citation: {
      type: String,
      default: null,
    },
    paragraphNumber: {
      type: String,
      default: null,
    },
    isHoldingOrRatio: {
      type: Boolean,
      default: false,
    },
  },
  { _id: false, strict: false },
);

const ragMetadataSchema = new mongoose.Schema(
  {
    model: {
      type: String,
      default: null,
    },
    provider: {
      type: String,
      default: null,
    },
    retrievalDuration: {
      type: Number,
      default: null,
    },
    totalDuration: {
      type: Number,
      default: null,
    },
    warnings: {
      type: [String],
      default: [],
    },
    status: {
      type: String,
      default: null,
    },
    requestedFacets: {
      type: [String],
      default: [],
    },
    facetCoverage: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },
    facetValidation: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },
    claimValidation: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },
    qualityStatus: {
      type: String,
      default: 'UNVERIFIED',
    },
    generationStatus: {
      type: String,
      default: 'NOT_RUN',
    },
    retrievalStatus: {
      type: String,
      default: 'NOT_RUN',
    },
    validationStatus: {
      type: String,
      default: 'NOT_RUN',
    },
    failedStage: {
      type: String,
      default: null,
    },
    errorCategory: {
      type: String,
      default: null,
    },
    retryable: {
      type: Boolean,
      default: false,
    },
    safeUserMessage: {
      type: String,
      default: null,
    },
    requestId: {
      type: String,
      default: null,
    },
  },
  { _id: false, strict: false },
);

const chatMessageSchema = new mongoose.Schema(
  {
    sessionId: {
      type: String,
      required: [true, 'sessionId is required'],
      index: true,
      trim: true,
    },
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: [true, 'userId is required'],
      index: true,
    },
    role: {
      type: String,
      enum: ['user', 'assistant'],
      required: [true, 'Role must be either user or assistant'],
    },
    content: {
      type: String,
      required: [true, 'Message content cannot be empty'],
    },
    sources: {
      type: [sourceReferenceSchema],
      default: [],
    },
    ragMetadata: {
      type: ragMetadataSchema,
      default: () => ({}),
    },
    createdAt: {
      type: Date,
      default: Date.now,
      index: true,
    },
  },
  {
    versionKey: false,
  },
);

// Compound index for querying chronological messages within a chat session
chatMessageSchema.index({ userId: 1, sessionId: 1, createdAt: 1 });

module.exports = mongoose.model('ChatMessage', chatMessageSchema);
