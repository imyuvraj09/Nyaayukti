from types import SimpleNamespace

from rag.conversation_pipeline import ConversationPipeline, audit_markers
from retrieval.hybrid import HybridRetriever, reciprocal_rank_fusion
from test_conversation_pipeline import Provider, Retriever, chunk
from utils.config import settings


def records():
    return [
        dict(
            chunk_id=f"a{i}",
            document_id="a",
            chunk_index=i,
            document_name="Employment Act",
            text=text,
            page_numbers=[i + 1],
        )
        for i, text in enumerate(
            [
                "Definitions of wages.",
                "Employer must pay wages.",
                "Except when the following condition applies.",
            ]
        )
    ]


def test_fusion_rewards_agreement_without_duplicate_votes():
    assert reciprocal_rank_fusion([["a", "a", "b"], ["b", "c"]])[0] == "b"


def test_neighbours_preserve_provenance(monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", False)
    monkeypatch.setattr(settings, "FINAL_RETRIEVAL_K", 1)
    found = HybridRetriever(records()).retrieve("employer pay").results
    assert found[0].chunk_id == "a1"
    assert {c.chunk_id for c in found} == {"a0", "a1", "a2"}
    assert found[1].metadata["adjacent_to"] == "a1"
    assert all(not c.section_number for c in found)


def test_low_reranker_scores_do_not_erase_retrieved_evidence(monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", True)
    reranker = SimpleNamespace(rerank=lambda q, candidates: [(c, 0) for c in candidates])
    result = HybridRetriever(records(), reranker=reranker).retrieve("wages")
    assert result.results
    assert all(c.reranker_score == 0 for c in result.results)


def test_hybrid_uses_both_rankings(monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "hybrid")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", False)
    dense = SimpleNamespace(
        search=lambda *a, **kw: SimpleNamespace(
            results=[SimpleNamespace(chunk_id="a2", relevance_score=0.8)]
        )
    )
    result = HybridRetriever(records(), dense=dense).retrieve("employer")
    assert {"a1", "a2"}.issubset({c.chunk_id for c in result.results})


def test_grouped_citations_are_not_lost():
    cleaned, used, invalid = audit_markers("Rule [SOURCE 1, SOURCE 3, 9].", 3)
    assert used == [1, 3] and invalid == [9]
    assert "[SOURCE 3]" in cleaned


def test_new_scenario_discards_prior_location():
    from test_conversation_pipeline import assessment, checked, plan

    provider = Provider([plan(), assessment(), "Draft", checked()])
    ConversationPipeline(Retriever(), provider).query(
        "A new independent problem",
        conversation_history=[{"role": "user", "content": "Earlier private facts in Kolkata"}],
    )
    assert "Kolkata" not in provider.prompts[-1]["prompt"]


def test_context_does_not_publish_unverified_metadata():
    c = chunk()
    c.metadata = {"section_number": "214", "section_title": "Wrong heading"}
    _, sources = ConversationPipeline(Retriever(), Provider(configured=False))._context([c])
    assert not sources[0].section_number and not sources[0].section_title


def test_health_does_not_construct_retriever(monkeypatch):
    import api.routes as routes

    monkeypatch.setattr(
        routes,
        "get_pipeline",
        lambda: (_ for _ in ()).throw(AssertionError("heavy health check")),
    )
    assert routes.health_check()["llm_available"] is None


def test_actual_corpus_lexical_search(monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", False)
    retriever = HybridRetriever()
    result = retriever.retrieve("dishonestly movable property without consent theft")
    assert result.results
    assert any("Bharatiya Nyaya Sanhita" in c.document_name for c in result.results)


def test_unknown_lexical_terms_still_return_no_evidence(monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", False)
    assert HybridRetriever(records()).retrieve("xyzzyplugh").results == []


def test_reported_question_retains_candidates_with_low_scores(monkeypatch):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", True)
    reranker = SimpleNamespace(rerank=lambda q, candidates: [(c, 0.001) for c in candidates])
    result = HybridRetriever(reranker=reranker).retrieve(
        "What constitutes theft under Bharatiya Nyaya Sanhita?"
    )
    assert result.results
    assert any("Bharatiya Nyaya Sanhita" in c.document_name for c in result.results)
