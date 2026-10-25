// HTTP and service contract regressions using database doubles; no MongoDB process.
process.env.NODE_ENV = 'test';
process.env.RAG_SERVICE_TOKEN = 'test-service-secret';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const request = require('supertest');
const mongoose = require('mongoose');
const app = require('../src/app');
const { authService, hashPassword } = require('../src/services/authService');
const { chatService } = require('../src/services/chatService');
const { ChatSession, ChatMessage } = require('../src/models');
const { ragService, RAGService } = require('../src/services/ragService');
const { cookieToken } = require('../src/middleware/browserSession');
const { rateLimit } = require('../src/middleware/rateLimit');
const bucket = mongoose.models.RateBucket;
bucket.findOneAndUpdate = async () => ({ count: 1 });

const user = { _id: 'user-a', email: 'a@example.test', displayName: 'User A' };
const auth = { user, session: { userId: user._id } };
authService.register = async () => ({
  token: 'secret-token',
  user,
  expiresAt: new Date(Date.now() + 60000).toISOString(),
});
authService.getSessionFromToken = async (token) => (token === 'secret-token' ? auth : null);
authService.logout = async () => {};

// Tests execute sequentially to keep model doubles isolated.
test('registration sets HttpOnly cookie and omits raw session token', async () => {
  const response = await request(app).post('/api/auth/register').send({ email: user.email });
  assert.equal(response.status, 201);
  assert.equal(response.body.data.token, undefined);
  assert.match(response.headers['set-cookie'][0], /HttpOnly/);
  assert.match(response.headers['set-cookie'][0], /SameSite=Strict/);
});
test('cookie session survives authenticated read', async () => {
  const response = await request(app)
    .get('/api/auth/me')
    .set('Cookie', 'nyaayukti_session=secret-token');
  assert.equal(response.status, 200);
});
test('missing or invalid credentials rejected', async () => {
  assert.equal((await request(app).get('/api/auth/me')).status, 401);
  assert.equal(
    (await request(app).get('/api/auth/me').set('Cookie', 'nyaayukti_session=invalid')).status,
    401,
  );
});
test('cookie mutation requires custom anti-CSRF header', async () => {
  assert.equal(
    (await request(app).post('/api/auth/logout').set('Cookie', 'nyaayukti_session=secret-token'))
      .status,
    403,
  );
  const response = await request(app)
    .post('/api/auth/logout')
    .set('Cookie', 'nyaayukti_session=secret-token')
    .set('X-Nyaayukti-Request', '1');
  assert.equal(response.status, 200);
  assert.match(response.headers['set-cookie'][0], /Expires=Thu, 01 Jan 1970/);
});
test('untrusted browser origin rejected', async () => {
  const response = await request(app)
    .post('/api/auth/login')
    .set('Origin', 'https://untrusted.example')
    .send({});
  assert.notEqual(response.status, 200);
});
test('cookie parsing rejects malformed escapes', () => {
  assert.equal(cookieToken({ headers: { cookie: 'nyaayukti_session=%ZZ' } }), null);
});
test('password hashes are salted and do not contain plaintext', async () => {
  const a = await hashPassword('StrongPassword123!'),
    b = await hashPassword('StrongPassword123!');
  assert.notEqual(a.hash, b.hash);
  assert.notEqual(a.salt, b.salt);
  assert.equal(a.hash.includes('StrongPassword'), false);
});
test('rate limit rejects over-limit requests', async () => {
  const saved = bucket.findOneAndUpdate;
  bucket.findOneAndUpdate = async () => ({ count: 21 });
  let status;
  await rateLimit({ name: 'test', limit: 20 })(
    { ip: 'test' },
    {
      set() {},
      status(code) {
        status = code;
        return this;
      },
      json() {},
    },
    () => assert.fail('must reject'),
  );
  bucket.findOneAndUpdate = saved;
  assert.equal(status, 429);
});
test('history query is account scoped and current message is not duplicated', async () => {
  let captured;
  ChatSession.findOne = async (filter) => {
    assert.deepEqual(filter, { userId: 'user-a', sessionId: 'session-a' });
    return { title: 'Existing', save: async () => {} };
  };
  ChatSession.updateOne = async () => {};
  ChatMessage.find = (filter) => {
    assert.deepEqual(filter, { userId: 'user-a', sessionId: 'session-a' });
    return {
      sort() {
        return this;
      },
      limit(n) {
        assert.equal(n, 12);
        return this;
      },
      lean: async () => [
        { role: 'assistant', content: 'Prior answer' },
        { role: 'user', content: 'Prior question' },
      ],
    };
  };
  ChatMessage.create = async (value) => value;
  const old = ragService.queryLegalRAG;
  ragService.queryLegalRAG = async (...args) => {
    captured = args;
    return { content: 'answer', sources: [], ragMetadata: {} };
  };
  await chatService.sendMessage('user-a', 'session-a', 'followup', 'request-id');
  ragService.queryLegalRAG = old;
  assert.deepEqual(
    captured[3].map((m) => m.content),
    ['Prior question', 'Prior answer'],
  );
  assert.equal(captured[0], 'followup');
});
test('unknown or other-account chat rejected before retrieval', async () => {
  ChatSession.findOne = async () => null;
  await assert.rejects(
    chatService.sendMessage('user-b', 'session-a', 'question'),
    (err) => err.statusCode === 404,
  );
});
test('gateway forwards service secret and history, rejects error-shaped responses', async () => {
  const original = global.fetch;
  let captured;
  global.fetch = async (_url, options) => {
    captured = options;
    return { ok: true, json: async () => ({ status: 'error', answer: 'failed' }) };
  };
  try {
    await assert.rejects(
      new RAGService().queryLegalRAG('question', 'session', 'request', [
        { role: 'user', content: 'prior' },
      ]),
    );
    assert.equal(captured.headers['X-Service-Token'], 'test-service-secret');
    assert.equal(JSON.parse(captured.body).conversation_history[0].content, 'prior');
  } finally {
    global.fetch = original;
  }
});
test('reset link consumption revokes sessions and cannot be reused', async () => {
  const recovery = require('../src/services/accountRecovery');
  const { User, AuthSession } = require('../src/models');
  const actionModel = mongoose.models.AccountAction;
  let consumed = false,
    revoked = false,
    updated = false;
  actionModel.findOneAndDelete = async (filter) => {
    assert.equal(filter.purpose, 'reset');
    assert.ok(filter.expiresAt.$gt instanceof Date);
    if (consumed) return null;
    consumed = true;
    return { userId: 'reset-user' };
  };
  actionModel.deleteMany = async () => {};
  User.updateOne = async (filter, change) => {
    updated = !!change.$set.passwordHash;
  };
  AuthSession.deleteMany = async (filter) => {
    revoked = filter.userId === 'reset-user';
  };
  const token = require('crypto').randomBytes(32).toString('base64url');
  await recovery.completeAction(token, 'reset', 'NewStrongPassword123!');
  assert.ok(updated && revoked);
  await assert.rejects(
    recovery.completeAction(token, 'reset', 'OtherPassword123!'),
    /Invalid or expired/,
  );
});

test('request IDs reject objects and control characters before database access', async () => {
  for (const requestId of [{ injected: true }, 'a\nb', 'x'.repeat(81)]) {
    const response = await request(app).post('/api/chat').send({ message: 'question', requestId });
    assert.equal(response.status, 400);
  }
});
test('API responses are not stored by shared caches', async () => {
  const response = await request(app).get('/api/health');
  assert.equal(response.headers['cache-control'], 'no-store');
  assert.match(response.headers['x-request-id'], /^[A-Za-z0-9_-]+$/);
});
test('oversized payload returns 413 rather than an internal error', async () => {
  const response = await request(app)
    .post('/api/chat')
    .send({ message: 'x'.repeat(1100000) });
  assert.equal(response.status, 413);
});
test('an unanswered retry reuses the stored user message', async () => {
  const previous = { role: 'user', content: 'Retry question', _id: 'stored-user-message' };
  ChatSession.findOne = async () => ({ title: 'Existing', save: async () => {} });
  ChatSession.updateOne = async () => {};
  ChatMessage.find = () => ({
    sort() {
      return this;
    },
    limit() {
      return this;
    },
    lean: async () => [previous],
  });
  const inserted = [];
  ChatMessage.create = async (value) => {
    inserted.push(value);
    return value;
  };
  const original = ragService.queryLegalRAG;
  ragService.queryLegalRAG = async (_q, _s, _r, history) => {
    assert.deepEqual(history, []);
    return { content: 'answer', sources: [], ragMetadata: {} };
  };
  try {
    const result = await chatService.sendMessage('user-a', 'session-a', 'Retry question');
    assert.equal(result.userMessage._id, previous._id);
    assert.deepEqual(
      inserted.map((m) => m.role),
      ['assistant'],
    );
  } finally {
    ragService.queryLegalRAG = original;
  }
});
