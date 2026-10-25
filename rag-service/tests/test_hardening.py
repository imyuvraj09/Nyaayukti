"""Boundaries that must hold without calling a paid provider."""

import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from api.body_limit import BodyLimitMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient
from llm.clients import ThreadClients
from rag.conversation_pipeline import ConversationPipeline
from schemas.query import QueryRequest
from test_conversation_pipeline import Provider, Retriever, assessment, checked, plan


def test_request_identifiers_cannot_inject_logs():
    for value in ["line\nbreak", "x" * 81, {"operator": "value"}]:
        with pytest.raises(ValueError):
            QueryRequest(query="Question", request_id=value)


def test_body_limit_counts_bytes_without_trusting_content_length():
    app = FastAPI()
    app.add_middleware(BodyLimitMiddleware, max_bytes=32)

    @app.post("/")
    def accept(data: dict):
        return data

    client = TestClient(app)
    assert client.post("/", json={"ok": True}).status_code == 200
    assert client.post("/", content=b"x" * 33).status_code == 413


def test_client_pool_reuses_connections_with_thread_isolation():
    pool = ThreadClients()
    closed = []
    barrier = threading.Barrier(2)

    def run():
        client = pool.get(lambda: SimpleNamespace(close=lambda: closed.append(True)))
        barrier.wait(timeout=5)
        assert pool.get(lambda: pytest.fail("client recreated")) is client
        return client

    with ThreadPoolExecutor(2) as executor:
        a = executor.submit(run)
        b = executor.submit(run)
        assert a.result() is not b.result()
    pool.close()
    assert len(closed) == 2


def test_answer_has_readable_sections_and_cited_next_steps():
    import json

    result = json.loads(checked())
    result["blocks"][0]["kind"] = "next_step"
    provider = Provider([plan(), assessment(), "Draft", json.dumps(result)])
    response = ConversationPipeline(Retriever(), provider).query("Question")
    assert "### Possible next steps" in response.answer
    assert "[SOURCE 1]" in response.answer
    assert "general legal information" in response.answer
