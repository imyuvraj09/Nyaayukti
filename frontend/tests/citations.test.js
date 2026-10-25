import test from 'node:test';
import assert from 'node:assert/strict';
import { normaliseCitations, citedNumbers, sourceAnchor } from '../src/utils/citations.js';

test('grouped citations retain every source identity', () => {
  assert.equal(normaliseCitations('Rule [SOURCE 2, SOURCE 7, 9].'), 'Rule [SOURCE 2] [SOURCE 7] [SOURCE 9].');
  assert.deepEqual([...citedNumbers('A [SOURCE 2, 7] B [SOURCE 2]')], [2, 7]);
});
test('citations in separate messages have different anchors', () => {
  assert.notEqual(sourceAnchor('message-a', 1), sourceAnchor('message-b', 1));
});

test('retrieval-only fallback text does not falsely extract cited sources', () => {
  const fallbackNotice =
    'We found potentially relevant sources, but could not complete the answer. AI generation was unavailable. You can inspect the retrieved passages below.';
  assert.equal(citedNumbers(fallbackNotice).size, 0);
});

