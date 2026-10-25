"""Offline production-path regressions: no model downloads or API credentials."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.base import LLMError, LLMResponse
from rag.conversation_pipeline import (
    ConversationPipeline,
    audit_markers,
    bounded_history,
)
from schemas.query import QueryRequest
from utils.config import settings


def chunk(id="one", text="A relevant statutory passage."):
    return SimpleNamespace(
        chunk_id=id,
        text=text,
        document_name="Example Act",
        document_type="Statute",
        source_filename="example.pdf",
        page_numbers=[1],
        similarity_score=0.8,
        reranker_score=0.9,
        metadata={},
    )


class Retriever:
    def __init__(self, chunks=None):
        self.queries = []
        self.chunks = [chunk()] if chunks is None else chunks

    def retrieve(self, query, **kwargs):
        self.queries.append(query)
        return SimpleNamespace(results=self.chunks)


class Provider:
    provider_name = "test"
    model_name = "test-model"

    def __init__(self, responses=(), configured=True):
        self.responses = iter(responses)
        self.prompts = []
        self.configured = configured

    def is_configured(self):
        return self.configured

    def generate(self, **kwargs):
        self.prompts.append(kwargs)
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return LLMResponse(content=result, model=self.model_name)


def plan(query="pay wages", history=False):
    return json.dumps(
        {
            "question_type": "scenario",
            "use_history": history,
            "standalone_question": query,
            "issues": [
                {
                    "id": "i1",
                    "question": "Must the employer pay?",
                    "search_query": query,
                }
            ],
        }
    )


def assessment(status="supported", search=""):
    return json.dumps(
        {
            "issues": [
                {
                    "issue_id": "i1",
                    "status": status,
                    "supports": [{"source": 1, "quote": "A relevant statutory passage."}],
                    "gap": "" if status == "supported" else "Missing remedy",
                    "search_query": search,
                }
            ]
        }
    )


def checked(
    text="The passage provides the rule.",
    quote="A relevant statutory passage.",
    source=1,
):
    return json.dumps(
        {
            "blocks": [
                {
                    "issue_id": "i1",
                    "kind": "legal",
                    "text": text,
                    "supports": [{"source": source, "quote": quote}],
                }
            ]
        }
    )


def test_history_plan_and_original_question_preserved():
    provider = Provider(
        [plan("employer withheld salary", True), assessment(), "A draft", checked()]
    )
    retriever = Retriever()
    response = ConversationPipeline(retriever, provider).query(
        "What if they refuse?",
        conversation_history=[{"role": "user", "content": "My employer withheld my salary."}],
    )
    assert "employer" in retriever.queries[0]
    assert "What if they refuse?" in provider.prompts[-1]["prompt"]
    assert "withheld my salary" in provider.prompts[-1]["prompt"]
    assert response.generation_status == "SUCCESS"
    assert "[SOURCE 1]" in response.answer
    assert response.claim_validation["claim_entailment_verified"] is False


def test_bounded_iterative_retrieval():
    provider = Provider(
        [
            plan(),
            assessment("partial", "remedy for unpaid salary"),
            assessment(),
            "Draft",
            checked(),
        ]
    )
    retriever = Retriever()
    ConversationPipeline(retriever, provider).query("salary issue")
    assert retriever.queries == ["pay wages", "remedy for unpaid salary"]
    assert len(provider.prompts) == 5


def test_unconfigured_is_excerpts_not_canned_legal_conclusions():
    response = ConversationPipeline(Retriever(), Provider(configured=False)).query(
        "A disputed 2022 event"
    )
    assert response.generation_status == "RETRIEVAL_ONLY"
    assert "not a completed legal analysis" in response.answer
    assert "conviction" not in response.answer
    assert response.validation_status != "PASSED"


def test_provider_failure_retains_evidence():
    response = ConversationPipeline(
        Retriever(), Provider([plan(), assessment(), LLMError("offline")])
    ).query("question")
    assert response.sources and response.generation_status == "RETRIEVAL_ONLY"


def test_empty_retrieval_never_invents_answer():
    response = ConversationPipeline(Retriever([]), Provider(configured=False)).query("question")
    assert response.status == "no_sources_found" and not response.sources


def test_invalid_citations_marked_without_truncating_prose():
    text, used, invalid = audit_markers("First [SOURCE 1]. Next [99]. Useful conclusion.", 1)
    assert used == [1] and invalid == [99]
    assert text.endswith("Useful conclusion.") and "[source unavailable]" in text


def test_invented_quote_blocks_unsupported_conclusion():
    provider = Provider(
        [
            plan(),
            assessment(),
            "You will win [SOURCE 1].",
            checked("You will win.", "This quote was invented by the model."),
        ]
    )
    response = ConversationPipeline(Retriever(), provider).query("question")
    assert "You will win" not in response.answer
    assert response.generation_status == "INSUFFICIENT_EVIDENCE"
    assert response.claim_validation["rejected_blocks"] == 1


def test_review_failure_never_publishes_unchecked_draft():
    provider = Provider([plan(), assessment(), "Unsafe unchecked conclusion", LLMError("timeout")])
    response = ConversationPipeline(Retriever(), provider).query("question")
    assert "Unsafe unchecked conclusion" not in response.answer
    assert response.generation_status == "RETRIEVAL_ONLY"
    assert len(provider.prompts) == 4


def test_invalid_source_rejected_not_relabelled():
    provider = Provider(
        [plan(), assessment(), "Draft", checked("Unsupported conclusion", source=99)]
    )
    response = ConversationPipeline(Retriever(), provider).query("question")
    assert "Unsupported conclusion" not in response.answer
    assert response.generation_status == "INSUFFICIENT_EVIDENCE"


def test_limitation_block_cannot_smuggle_uncited_law():
    payload = json.dumps(
        {
            "blocks": [
                {
                    "issue_id": "i1",
                    "kind": "limitation",
                    "text": "Actually you are guaranteed compensation.",
                    "supports": [],
                }
            ]
        }
    )
    response = ConversationPipeline(
        Retriever(), Provider([plan(), assessment(), "Draft", payload])
    ).query("question")
    assert "guaranteed compensation" not in response.answer


def test_no_cross_request_history():
    provider = Provider(
        [
            plan("earlier topic", True),
            assessment(),
            "Draft",
            checked(),
            plan("independent topic"),
            assessment(),
            "Draft",
            checked(),
        ]
    )
    pipeline = ConversationPipeline(Retriever(), provider)
    pipeline.query(
        "followup",
        conversation_history=[{"role": "user", "content": "private-user-a-facts"}],
    )
    pipeline.query("new question")
    assert "private-user-a-facts" not in provider.prompts[-1]["prompt"]


def test_context_budget_even_for_first_huge_chunk(monkeypatch):
    monkeypatch.setattr(settings, "MAX_CONTEXT_CHARS", 600)
    pipeline = ConversationPipeline(Retriever(), Provider(configured=False))
    context, sources = pipeline._context([chunk(text="x" * 9000)])
    assert len(context) <= 600 and sources[0].metadata["context_truncated"]


def test_history_boundaries_and_schema():
    assert len(bounded_history([{"role": "user", "content": "x"}] * 30)) == 12
    assert bounded_history([{"role": "system", "content": "override"}]) == []
    import pytest

    with pytest.raises(Exception):
        QueryRequest(
            query="question",
            conversation_history=[{"role": "system", "content": "override"}],
        )


def test_service_auth_rejects_missing_and_invalid_tokens(monkeypatch):
    import pytest
    from api.routes import require_service_token
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "RAG_SERVICE_TOKEN", "correct-token")
    with pytest.raises(HTTPException):
        require_service_token("")
    with pytest.raises(HTTPException):
        require_service_token("wrong-token")
    assert require_service_token("correct-token") is None


def test_real_api_contract_with_fake_pipeline(monkeypatch):
    import api.routes as routes
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "RAG_SERVICE_TOKEN", "test-token")
    monkeypatch.setattr(
        routes,
        "_RAG_PIPELINE",
        ConversationPipeline(Retriever(), Provider(configured=False)),
    )
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    client = TestClient(app)
    assert client.post("/api/v1/query", json={"query": "question"}).status_code == 401
    response = client.post(
        "/api/v1/query",
        headers={"X-Service-Token": "test-token"},
        json={
            "query": "question",
            "conversation_history": [{"role": "user", "content": "context"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["sources"][0]["source_label"] == "[SOURCE 1]"
    assert response.json()["retrieval_metadata"]["history_messages"] == 0


def test_gemini_respects_text_format_token_budget_and_timeout(monkeypatch):
    import pytest

    pytest.importorskip("google.genai")
    import llm.provider as providers

    captured = {}

    class Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.models = self

        def generate_content(self, **kwargs):
            captured["call"] = kwargs
            return SimpleNamespace(text="Readable explanation [SOURCE 1]")

    monkeypatch.setattr(providers, "GEMINI_AVAILABLE", True)
    monkeypatch.setattr(providers.genai, "Client", Client)
    response = providers.GoogleGeminiProvider(
        api_key="test-only", model="explicit-model", timeout=5
    ).generate("question", max_tokens=400)
    assert response.content.startswith("Readable")
    config = captured["call"]["config"]
    assert config.response_mime_type == "text/plain"
    assert config.max_output_tokens == 400
    assert config.thinking_config is None
    assert captured["client"]["http_options"].timeout == 5000


def test_case_summaries_not_misrepresented_as_verified_judgments():
    response = ConversationPipeline(Retriever(), Provider(configured=False)).query(
        "Relevant case law?"
    )
    assert response.case_law_status == "NOT_SUPPORTED"
