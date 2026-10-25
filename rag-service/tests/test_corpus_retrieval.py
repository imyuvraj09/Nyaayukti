"""Real text corpus checks. These do not establish live-model legal accuracy."""

import pytest
from retrieval.hybrid import HybridRetriever
from utils.config import settings


@pytest.fixture(scope="module")
def corpus():
    return HybridRetriever()


@pytest.mark.parametrize(
    "query,expected",
    [
        ("BNS section 358 repeal savings", "bns_2023_c0482"),
        ("BNSS section 531 repeal savings", "bnss_2023_c0724"),
        ("Consumer Protection Act consumer rights", "consumer_c0006"),
        (
            "Constitution article 20 conviction offence penalty",
            "constitution_of_india_c0163",
        ),
        (
            "Right to Information Act section 7 disposal request",
            "right_to_information_act_2005_c0019",
        ),
        ("Information Technology Act section 43 damage computer", "it_act_c0048"),
        ("Motor Vehicles Act section 3 driving licence", "motor_vehicle_act_c0028"),
        ("Companies Act section 166 duties directors", "companies_act_2013_c0430"),
        (
            "BNS commencement notification date come into force",
            "bns_commencement_2024_c0000",
        ),
        (
            "BNSS commencement notification date come into force",
            "bnss_commencement_2024_c0000",
        ),
    ],
)
def test_controlling_passage_in_top_three(monkeypatch, corpus, query, expected):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", False)
    found = corpus.retrieve(query)
    assert expected in [c.chunk_id for c in found.results[:3]]


def test_savings_continuation_survives_header_noise(monkeypatch, corpus):
    monkeypatch.setattr(settings, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(settings, "ENABLE_RERANKER", False)
    result = corpus.retrieve("BNSS section 531 repeal savings")
    passage = next(c for c in result.results if c.chunk_id == "bnss_2023_c0724")
    assert "as if this Sanhita had not come into force" in passage.text
    assert len(passage.metadata["constituent_chunk_ids"]) > 1


def test_article_lookup_does_not_promote_schedule_entry(corpus):
    assert corpus.exact_provisions("Constitution article 20") == []


def test_data_scope_is_not_confused_between_bns_and_bnss(corpus):
    assert corpus.document_scope("BNS section 358") == {"Bharatiya Nyaya Sanhita, 2023"}
    assert corpus.document_scope("BNSS section 531") == {"Bharatiya Nagarik Suraksha Sanhita, 2023"}
