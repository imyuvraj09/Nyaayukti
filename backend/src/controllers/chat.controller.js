/**
 * Authenticated Chat Controller for Nyaayukti API Gateway.
 */

const { chatService } = require('../services/chatService');
const { sendSuccess } = require('../utils/apiResponse');

async function createChat(req, res, next) {
  try {
    const { title } = req.body || {};
    const session = await chatService.createSession(req.user._id, title);
    return sendSuccess(res, session, 201, 'Chat session created successfully');
  } catch (err) {
    return next(err);
  }
}

async function getChat(req, res, next) {
  try {
    const chatData = await chatService.getSessionWithMessages(req.user._id, req.params.sessionId);
    return sendSuccess(res, chatData, 200);
  } catch (err) {
    return next(err);
  }
}

async function listChats(req, res, next) {
  try {
    const { skip, limit, page } = req.pagination;
    const result = await chatService.listSessions(req.user._id, skip, limit, page);
    return sendSuccess(res, result, 200);
  } catch (err) {
    return next(err);
  }
}

async function deleteChat(req, res, next) {
  try {
    const result = await chatService.deleteSession(req.user._id, req.params.sessionId);
    return sendSuccess(res, result, 200, 'Chat session and messages deleted successfully');
  } catch (err) {
    return next(err);
  }
}

async function postMessage(req, res, next) {
  try {
    const { sessionId } = req.params;
    const { query, requestId: bodyRequestId } = req.body;
    const requestId = req.requestId;
    const result = await chatService.sendMessage(req.user._id, sessionId, query, requestId);

    return sendSuccess(
      res,
      {
        sessionId: result.sessionId,
        message: result.assistantMessage,
        userMessage: result.userMessage,
        requestId: result.assistantMessage.ragMetadata?.requestId || requestId,
      },
      200,
    );
  } catch (err) {
    return next(err);
  }
}

async function handleDirectChat(req, res, next) {
  try {
    const {
      sessionId: rawSessionId,
      message: rawMessage,
      query: rawQuery,
      title,
      requestId: bodyRequestId,
    } = req.body || {};
    const requestId = req.requestId;
    const value = rawMessage ?? rawQuery;
    if (typeof value !== 'string') {
      const { ValidationError } = require('../utils/errors');
      throw new ValidationError('Message must be a string.');
    }
    const text = value.trim();

    if (!text) {
      const { ValidationError } = require('../utils/errors');
      throw new ValidationError('Message content is required and cannot be empty.');
    }
    if (text.length > 2000) {
      const { ValidationError } = require('../utils/errors');
      throw new ValidationError('Message exceeds maximum allowed length of 2000 characters.');
    }

    let effectiveSessionId =
      rawSessionId && typeof rawSessionId === 'string' ? rawSessionId.trim() : null;

    if (
      rawSessionId != null &&
      (typeof rawSessionId !== 'string' || !/^[A-Za-z0-9_-]{4,64}$/.test(rawSessionId))
    ) {
      const { ValidationError } = require('../utils/errors');
      throw new ValidationError('Invalid conversation ID.');
    }

    if (effectiveSessionId) {
      const { ChatSession } = require('../models');
      const existing = await ChatSession.findOne({
        sessionId: effectiveSessionId,
        userId: req.user._id,
      });
      if (!existing) {
        const { NotFoundError } = require('../utils/errors');
        throw new NotFoundError('Conversation not found.');
      }
    } else {
      const newSession = await chatService.createSession(req.user._id, title || text.slice(0, 60));
      effectiveSessionId = newSession.sessionId;
    }

    // Return the created conversation even if generation fails, so retry stays in it.
    res.set('X-Conversation-Id', effectiveSessionId);
    const result = await chatService.sendMessage(req.user._id, effectiveSessionId, text, requestId);

    return res.status(200).json({
      success: true,
      sessionId: result.sessionId,
      message: {
        role: result.assistantMessage.role,
        content: result.assistantMessage.content,
        sources: result.assistantMessage.sources || [],
        metadata: result.assistantMessage.ragMetadata || result.assistantMessage.metadata || {},
        ragMetadata: result.assistantMessage.ragMetadata || {},
        generationStatus:
          result.assistantMessage.ragMetadata?.generationStatus ||
          result.assistantMessage.generationStatus ||
          'SUCCESS',
        retrievalStatus:
          result.assistantMessage.ragMetadata?.retrievalStatus ||
          result.assistantMessage.retrievalStatus ||
          'SUCCESS',
        validationStatus:
          result.assistantMessage.ragMetadata?.validationStatus ||
          result.assistantMessage.validationStatus ||
          'PASSED',
        createdAt: result.assistantMessage.createdAt,
      },
      userMessage: result.userMessage,
      data: {
        sessionId: result.sessionId,
        message: result.assistantMessage,
        userMessage: result.userMessage,
      },
    });
  } catch (err) {
    return next(err);
  }
}

module.exports = {
  createChat,
  getChat,
  listChats,
  deleteChat,
  postMessage,
  handleDirectChat,
};
