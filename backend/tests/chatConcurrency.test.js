const test = require('node:test');
const assert = require('node:assert/strict');
const { ChatService } = require('../src/services/chatService');

test('concurrent send and delete are rejected; lock released after failure', async () => {
  const service = new ChatService();
  let reject;
  service.generateReply = () =>
    new Promise((resolve, fail) => {
      reject = fail;
    });
  const first = service.sendMessage('u', 's', 'question');
  await assert.rejects(service.sendMessage('u', 's', 'other'), /already being generated/);
  await assert.rejects(service.deleteSession('u', 's'), /Wait for the reply/);
  reject(new Error('provider failed'));
  await assert.rejects(first, /provider failed/);
  service.generateReply = async () => 'recovered';
  assert.equal(await service.sendMessage('u', 's', 'retry'), 'recovered');
});
