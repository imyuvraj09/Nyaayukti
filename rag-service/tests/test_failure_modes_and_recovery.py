"""Comprehensive regression tests covering all failure modes, recovery, boundary cleaning,
and operational metadata preservation across the RAG pipeline.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock

from llm.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMUnconfiguredError,
    LLMAuthenticationError,
    LLMInvalidModelError,
    LLMRateLimitError,
    LLMQuotaExceededError,
    LLMTimeoutError,
    LLMEmptyResponseError,
    LLMOutputTruncatedError,
    LLMJsonParseError,
    LLMSchemaValidationError,
    LLMReviewFailedError,
)
from rag.evidence import (
    clean_passage_excerpt,
    attempt_json_repair,
    parse_model_json,
    QueryPlan,
    EvidenceReview,
    CheckedAnswer,
)
from ingestion.text_cleaner import clean_text
from rag.conversation_pipeline import ConversationPipeline, SAFE_USER_MESSAGES


# Stub provider for testing
class MockLLMProvider(BaseLLMProvider):
    def __init__(self, responses=None, side_effects=None, exception=None, configured=True):
        self.responses = list(responses or [])
        self.side_effects = list(side_effects or [])
        self.exception = exception
        self.call_count = 0
        self._configured = configured

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    def is_configured(self) -> bool:
        return self._configured

    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        self.call_count += 1
        if self.exception:
            raise self.exception
        if self.side_effects:
            effect = self.side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            if callable(effect):
                return effect(prompt)
        if self.responses:
            resp = self.responses.pop(0)
            if isinstance(resp, str):
                return LLMResponse(content=resp, model=self.model_name)
            return resp
        return LLMResponse(content="{}", model=self.model_name)


def create_sample_chunk(num=1, text="Section 34. (1) Subject to the other provisions of this Act, the District Commission shall have jurisdiction to entertain complaints."):
    return SimpleNamespace(
        chunk_id=f"chunk-{num}",
        doc_id="cpa-2019",
        document_name="Consumer Protection Act, 2019",
        page_numbers=[22],
        text=text,
        clean_text=text,
        section_number="34",
        section_title="Jurisdiction of District Commission",
        act_short_name="CPA 2019",
        document_type="Statute",
        similarity_score=0.85,
        reranker_score=0.95,
        source_filename="cpa_2019.pdf",
        metadata={},
    )


class MockRetriever:
    def __init__(self, chunks=None):
        self.chunks = [create_sample_chunk()] if chunks is None else chunks

    def retrieve(self, query, **kwargs):
        return SimpleNamespace(results=self.chunks)


# 1. Clean excerpt boundaries and omission markers
def test_clean_passage_excerpt_boundary_snapping():
    # Incomplete sentence cutting off mid-word
    text = "The District Commission shall have jurisdiction. The complaint may be filed where the opposite party suffered b"
    excerpt = clean_passage_excerpt(text, max_chars=110)
    # Must snap to sentence or clean boundary with omission marker and not end with "suffered b"
    assert "suffered b" not in excerpt
    assert excerpt.endswith(" [...]") or excerpt.endswith(".")
    assert "The District Commission shall have jurisdiction." in excerpt


def test_gazette_header_and_ocr_artifact_removal():
    messy_text = (
        "SEC. 1] THE GAZETTE OF INDIA EXTRAORDINARY 15\n"
        "Separate paging is given to this Part in order that it may be filed as a separate compilation.\n"
        "34. (1) Subject to the other provisions of this Act, the District Commission shall have jurisdiction."
    )
    cleaned = clean_text(messy_text)
    assert "THE GAZETTE OF INDIA EXTRAORDINARY" not in cleaned
    assert "Separate paging is given" not in cleaned
    assert "District Commission shall have jurisdiction" in cleaned


# 2. JSON Repair and Truncation handling
def test_attempt_json_repair_success():
    # Incomplete JSON with missing closing brackets
    broken_json = '{"question_type": "scenario", "standalone_question": "Where to file?", "issues": []'
    repaired = attempt_json_repair(broken_json)
    assert repaired is not None
    assert repaired["question_type"] == "scenario"
    assert repaired["standalone_question"] == "Where to file?"


def test_attempt_json_repair_failure_on_hopeless_input():
    broken = "Not JSON at all, completely scrambled <<<<<"
    assert attempt_json_repair(broken) is None


def test_parse_model_json_detects_truncation_finish_reason():
    response = LLMResponse(
        content='{"main_answer": "Incomplete',
        model="mock",
        finish_reason="MAX_TOKENS",
    )
    with pytest.raises(LLMOutputTruncatedError) as exc_info:
        parse_model_json(response.content, QueryPlan, finish_reason=response.finish_reason)
    assert exc_info.value.category == "OUTPUT_TRUNCATED"


# 3. Unconfigured Provider
def test_pipeline_unconfigured_provider():
    mock_llm = MockLLMProvider(configured=False)
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "CONFIGURATION"
    assert res.error_category == "UNCONFIGURED"
    assert res.retryable is False
    assert "API key" in res.safe_user_message or "configured" in res.safe_user_message
    assert "Sources cited" not in res.answer
    assert "not a completed legal analysis" in res.answer


# 4. Authentication Error
def test_pipeline_auth_error():
    mock_llm = MockLLMProvider(exception=LLMAuthenticationError("Invalid API Key: 401"))
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "PLANNING"
    assert res.error_category == "AUTH_ERROR"
    assert res.retryable is False
    assert "authentication failed" in res.safe_user_message.lower()


# 5. Invalid Model Error
def test_pipeline_invalid_model_error():
    mock_llm = MockLLMProvider(exception=LLMInvalidModelError("Model gemini-fake not found: 404"))
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "PLANNING"
    assert res.error_category == "INVALID_MODEL"
    assert res.retryable is False


# 6. Rate Limit and Quota Exceeded
def test_pipeline_rate_limited():
    mock_llm = MockLLMProvider(exception=LLMRateLimitError("Resource exhausted: rate limit"))
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "PLANNING"
    assert res.error_category == "RATE_LIMITED"
    assert res.retryable is True


def test_pipeline_quota_exceeded():
    mock_llm = MockLLMProvider(exception=LLMQuotaExceededError("Daily quota exceeded"))
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "PLANNING"
    assert res.error_category == "QUOTA_EXCEEDED"
    assert res.retryable is False


# 7. Timeout and Empty Response
def test_pipeline_timeout():
    mock_llm = MockLLMProvider(exception=LLMTimeoutError("Operation timed out after 10s"))
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "PLANNING"
    assert res.error_category == "TIMEOUT"
    assert res.retryable is True


def test_pipeline_empty_response():
    mock_llm = MockLLMProvider(exception=LLMEmptyResponseError("Empty generation from model"))
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "PLANNING"
    assert res.error_category == "EMPTY_RESPONSE"
    assert res.retryable is True


# 8. Malformed JSON and Schema Validation Failure
def test_pipeline_schema_validation_failure():
    # Returns JSON that doesn't conform to QueryPlan schema
    invalid_schema_json = '{"unknown_field": 123}'
    mock_llm = MockLLMProvider(responses=[invalid_schema_json])
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "PLANNING"
    assert res.error_category in ("SCHEMA_VALIDATION_FAILED", "JSON_PARSE_FAILED")


# 9. Review failure after successful draft (Unchecked draft must NEVER be published)
def test_pipeline_review_failure_never_publishes_unchecked_draft():
    # 1. Plan response
    plan_json = json.dumps({
        "question_type": "scenario",
        "use_history": False,
        "standalone_question": "Where do I file a consumer complaint?",
        "issues": [{"id": "i1", "question": "Where to file?", "search_query": "consumer court jurisdiction"}],
        "truncated_issues_count": 0,
    })
    # 2. Assessment response
    assessment_json = json.dumps({
        "issues": [{
            "issue_id": "i1",
            "status": "supported",
            "supports": [{"source": 1, "quote": "District Commission shall have jurisdiction to entertain complaints."}],
            "gap": "",
            "search_query": ""
        }]
    })
    # 3. Draft response
    draft_answer = "You must file the complaint in the District Commission having jurisdiction."
    # 4. Review response fails with exception or invalid JSON
    mock_llm = MockLLMProvider(
        responses=[plan_json, assessment_json, draft_answer],
        side_effects=[None, None, None, LLMReviewFailedError("Structured review failed to validate draft")]
    )
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=mock_llm,
    )

    res = pipeline.query("Where do I file a consumer complaint?")
    # Must NOT publish unchecked draft
    assert res.generation_status == "RETRIEVAL_ONLY"
    assert res.failed_stage == "STRUCTURED_REVIEW"
    assert res.error_category == "REVIEW_FAILED"
    assert res.validation_status in ("FAILED", "REVIEW_FAILED", "FAIL")
    assert "Sources cited" not in res.answer


# 10. No retrieved evidence
def test_pipeline_no_retrieved_evidence():
    pipeline = ConversationPipeline(
        retriever=MockRetriever(chunks=[]),
        llm_provider=MockLLMProvider(),
    )

    res = pipeline.query("Some question with no matching documents")
    assert res.status == "no_sources_found"
    assert res.generation_status == "NO_SOURCES_FOUND"
    assert res.retrieval_status == "NO_SOURCES_FOUND"
    assert len(res.sources) == 0


# 11. No secret or credential leakage in diagnostics or safe messages
def test_diagnostics_sanitize_secrets():
    secret_key = "AIzaSyFakeSecretKey1234567890abcdef"
    err = LLMAuthenticationError(f"API key {secret_key} invalid")
    # safe user message must never leak the secret key
    pipeline = ConversationPipeline(
        retriever=MockRetriever(),
        llm_provider=MockLLMProvider(exception=err),
    )
    res = pipeline.query("Test query")
    assert secret_key not in res.safe_user_message
    assert secret_key not in res.answer
    assert secret_key not in (res.model_metadata.get("generation_error") or "")
