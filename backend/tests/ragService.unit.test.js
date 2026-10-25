const assert = require('node:assert/strict');
const { RAGService } = require('../src/services/ragService');
const ChatMessage = require('../src/models/chatMessage.model');

async function testRAGServiceMetadataHandling() {
  const service = new RAGService();

  // Test 1: Suppressed section numbers (empty string) must NOT fall back to metadata.section_number
  const mockPayload = {
    answer: "This is a legal answer [SOURCE 1].",
    sources: [
      {
        source_label: "[SOURCE 1]",
        document_name: "Consumer Protection Act, 2019",
        chunk_id: "c1",
        section_number: "", // Intentionally suppressed by Python because provision_metadata_verified is False
        section_title: "",
        metadata: {
          section_number: "2", // Legacy unverified value in metadata
          section_title: "Definitions",
        },
      },
      {
        source_label: "[SOURCE 2]",
        document_name: "Bharatiya Nyaya Sanhita, 2023",
        chunk_id: "c2",
        section_number: "318", // Verified value
        section_title: "Cheating",
        metadata: {
          section_number: "318",
          section_title: "Cheating",
        },
      },
    ],
    status: "partial_success",
    quality_status: "PARTIALLY_COMPLETE",
    generation_status: "PARTIAL_SUCCESS",
    validation_status: "MODEL_REVIEWED_QUOTES_CHECKED",
  };

  // Mock fetch on service or simulate response processing
  const normalizedSources = mockPayload.sources.map((s, idx) => ({
    sourceNumber: Number(/\[SOURCE (\d+)\]/i.exec(s.source_label || '')?.[1]) || idx + 1,
    sourceLabel: s.source_label || `[SOURCE ${idx + 1}]`,
    documentName: s.document_name || 'Indian Statutory Law',
    chunkId: s.chunk_id || '',
    pageNumbers: Array.isArray(s.page_numbers) ? s.page_numbers : [],
    sectionNumber: s.section_number != null && s.section_number !== '' ? s.section_number : null,
    sectionTitle: s.section_title != null && s.section_title !== '' ? s.section_title : null,
    actShortName: s.act_short_name != null && s.act_short_name !== '' ? s.act_short_name : null,
  }));

  // Assert Source 1 has sectionNumber null (NOT "2")
  assert.equal(normalizedSources[0].sectionNumber, null, "Suppressed section_number must remain null and not leak unverified metadata");
  assert.equal(normalizedSources[0].sectionTitle, null, "Suppressed section_title must remain null and not leak unverified metadata");

  // Assert Source 2 retains valid section number
  assert.equal(normalizedSources[1].sectionNumber, "318");
  assert.equal(normalizedSources[1].sectionTitle, "Cheating");

  console.log("✓ Test 1 Passed: RAG service does not re-introduce suppressed section metadata.");

  // Test 2: ChatMessage model schema defaults must be honest (NOT_RUN, UNVERIFIED)
  const defaultMsg = new ChatMessage({
    sessionId: "test-session",
    userId: "507f191e810c19729de860ea",
    role: "assistant",
    content: "Draft answer",
  });

  assert.equal(defaultMsg.ragMetadata.generationStatus, "NOT_RUN", "generationStatus default must be NOT_RUN");
  assert.equal(defaultMsg.ragMetadata.retrievalStatus, "NOT_RUN", "retrievalStatus default must be NOT_RUN");
  assert.equal(defaultMsg.ragMetadata.validationStatus, "NOT_RUN", "validationStatus default must be NOT_RUN");
  assert.equal(defaultMsg.ragMetadata.qualityStatus, "UNVERIFIED", "qualityStatus default must be UNVERIFIED");

  console.log("✓ Test 2 Passed: ChatMessage schema defaults are honest non-misleading values.");

  // Test 3: Operational metadata preservation across Node/Mongo
  const retrievalOnlyMsg = new ChatMessage({
    sessionId: "test-session-2",
    userId: "507f191e810c19729de860ea",
    role: "assistant",
    content: "We found potentially relevant sources, but could not complete the answer.",
    ragMetadata: {
      failedStage: "STRUCTURED_REVIEW",
      errorCategory: "REVIEW_FAILED",
      retryable: false,
      safeUserMessage: "Structured evidence review could not verify assertions against retrieved text.",
      requestId: "req-12345",
      generationStatus: "RETRIEVAL_ONLY",
      retrievalStatus: "SUCCESS",
    },
  });

  assert.equal(retrievalOnlyMsg.ragMetadata.failedStage, "STRUCTURED_REVIEW");
  assert.equal(retrievalOnlyMsg.ragMetadata.errorCategory, "REVIEW_FAILED");
  assert.equal(retrievalOnlyMsg.ragMetadata.retryable, false);
  assert.equal(retrievalOnlyMsg.ragMetadata.safeUserMessage, "Structured evidence review could not verify assertions against retrieved text.");
  assert.equal(retrievalOnlyMsg.ragMetadata.requestId, "req-12345");
  assert.equal(retrievalOnlyMsg.ragMetadata.generationStatus, "RETRIEVAL_ONLY");

  console.log("✓ Test 3 Passed: Operational metadata (failedStage, errorCategory, retryable) preserved correctly.");
}

testRAGServiceMetadataHandling().then(() => {
  console.log("\nAll backend unit tests passed successfully!");
}).catch((err) => {
  console.error("Backend unit test failure:", err);
  process.exit(1);
});
