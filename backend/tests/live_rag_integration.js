/** Live smoke test. Start the configured RAG service first; this can incur API charges. */
const assert = require('node:assert/strict');
const path = require('node:path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });
process.env.NODE_ENV = 'test';

const { MongoMemoryServer } = require('mongodb-memory-server');
const mongoose = require('mongoose');
const request = require('supertest');
const app = require('../src/app');
const { ragService } = require('../src/services/ragService');

async function run() {
  assert.ok(process.env.RAG_SERVICE_TOKEN, 'Configure the shared service token first.');
  const health = await ragService.checkHealth();
  assert.ok(health.available, 'Start the RAG service and verify its service token.');
  const database = await MongoMemoryServer.create({ instance: { args: ['--nounixsocket'] } });
  try {
    await mongoose.connect(database.getUri());
    const client = request.agent(app);
    await client
      .post('/api/auth/register')
      .send({
        displayName: 'Smoke Test',
        email: 'smoke@example.test',
        password: 'LocalTestPassword123!',
      })
      .expect(201);
    const created = await client
      .post('/api/chats')
      .set('X-Nyaayukti-Request', '1')
      .send({ title: 'Live retrieval check' })
      .expect(201);
    const id = created.body.data.sessionId;
    const answer = await client
      .post(`/api/chats/${id}/messages`)
      .set('X-Nyaayukti-Request', '1')
      .send({ query: 'What does the Consumer Protection Act say about consumer rights?' })
      .expect(200);
    const message = answer.body.data.message;
    assert.equal(message.role, 'assistant');
    assert.ok(message.sources.length > 0, 'Expected retrieved passages.');
    assert.equal(
      message.ragMetadata.generationStatus,
      'SUCCESS',
      'Excerpts alone do not pass generation testing.',
    );
    const history = await client.get(`/api/chats/${id}`).expect(200);
    assert.deepEqual(
      history.body.data.messages.map((item) => item.role),
      ['user', 'assistant'],
    );
    console.log(
      'Live retrieval, generation and persistence smoke test passed. Legal accuracy still needs expert review.',
    );
  } finally {
    await mongoose.disconnect();
    await database.stop();
  }
}

run().catch((error) => {
  console.error('Live smoke test failed:', error.name);
  process.exitCode = 1;
});
