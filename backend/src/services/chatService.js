/**
 * Chat Service handling user-scoped database operations and legal query orchestration.
 */

const crypto = require('crypto');
const { ChatSession, ChatMessage } = require('../models');
const { ragService } = require('./ragService');
const { NotFoundError, ConflictError } = require('../utils/errors');

function stripOwnership(value) {
  const obj = value && typeof value.toObject === 'function' ? value.toObject() : { ...value };
  delete obj.userId;
  return obj;
}

class ChatService {
  constructor() {
    this.activeSessions = new Set();
  }

  async sendMessage(userId, sessionId, query, requestId = null) {
    const key = `${userId}:${sessionId}`;
    if (this.activeSessions.has(key))
      throw new ConflictError('A reply is already being generated in this conversation.');
    this.activeSessions.add(key);
    try {
      return await this.generateReply(userId, sessionId, query, requestId);
    } finally {
      this.activeSessions.delete(key);
    }
  }

  async createSession(userId, title) {
    const sessionId = crypto.randomUUID();
    const session = await ChatSession.create({
      sessionId,
      userId,
      title:
        title && typeof title === 'string' ? title.trim().slice(0, 100) : 'New Legal Conversation',
      lastActivityAt: new Date(),
    });
    return stripOwnership(session);
  }

  async getSessionWithMessages(userId, sessionId) {
    const session = await ChatSession.findOne({ sessionId, userId });
    if (!session) {
      throw new NotFoundError(`Chat session '${sessionId}' was not found.`);
    }

    const messages = await ChatMessage.find({ sessionId, userId }).sort({ createdAt: 1 }).lean();
    return {
      session: stripOwnership(session),
      messages: messages.map(stripOwnership),
    };
  }

  async listSessions(userId, skip = 0, limit = 20, page = 1) {
    const filter = { userId };
    const [sessions, total] = await Promise.all([
      ChatSession.find(filter).sort({ lastActivityAt: -1 }).skip(skip).limit(limit).lean(),
      ChatSession.countDocuments(filter),
    ]);

    return {
      sessions: sessions.map(stripOwnership),
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit) || 1,
    };
  }

  async deleteSession(userId, sessionId) {
    if (this.activeSessions.has(`${userId}:${sessionId}`))
      throw new ConflictError('Wait for the reply before deleting this conversation.');
    const session = await ChatSession.findOne({ sessionId, userId });
    if (!session) {
      throw new NotFoundError(`Chat session '${sessionId}' was not found.`);
    }

    const [deleteMsgResult] = await Promise.all([
      ChatMessage.deleteMany({ sessionId, userId }),
      ChatSession.deleteOne({ sessionId, userId }),
    ]);

    return {
      sessionId,
      deletedMessagesCount: deleteMsgResult.deletedCount || 0,
    };
  }

  async generateReply(userId, sessionId, query, requestId = null) {
    const activeRequestId =
      requestId || `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    const session = await ChatSession.findOne({ sessionId, userId });
    if (!session) {
      throw new NotFoundError(`Chat session '${sessionId}' was not found.`);
    }

    const recent = await ChatMessage.find({ sessionId, userId })
      .sort({ createdAt: -1, _id: -1 })
      .limit(12)
      .lean();
    const lastMessage = recent[0];
    const unansweredRetry = lastMessage?.role === 'user' && lastMessage.content === query;
    const historyMessages = unansweredRetry ? recent.slice(1) : recent;
    const conversationHistory = historyMessages
      .reverse()
      .filter((m) => ['user', 'assistant'].includes(m.role))
      .map((m) => ({ role: m.role, content: String(m.content || '').slice(0, 4000) }))
      .filter((m) => m.content);
    const userMessage = unansweredRetry
      ? lastMessage
      : await ChatMessage.create({
          sessionId,
          userId,
          role: 'user',
          content: query,
          sources: [],
          ragMetadata: { requestId: activeRequestId },
          createdAt: new Date(),
        });

    if (session.title === 'New Legal Conversation') {
      session.title = query.length > 60 ? `${query.slice(0, 57)}...` : query;
    }
    session.lastActivityAt = new Date();
    await session.save();

    const ragResponse = await ragService.queryLegalRAG(
      query,
      sessionId,
      activeRequestId,
      conversationHistory,
    );

    const assistantMessage = await ChatMessage.create({
      sessionId,
      userId,
      role: 'assistant',
      content: ragResponse.content,
      sources: ragResponse.sources,
      ragMetadata: ragResponse.ragMetadata,
      createdAt: new Date(),
    });

    await ChatSession.updateOne({ sessionId, userId }, { lastActivityAt: new Date() });

    return {
      sessionId,
      userMessage: stripOwnership(userMessage),
      assistantMessage: stripOwnership(assistantMessage),
    };
  }
}

const chatService = new ChatService();

module.exports = {
  ChatService,
  chatService,
};
