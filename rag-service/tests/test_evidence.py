from types import SimpleNamespace

import pytest
from rag.evidence import (
    EvidenceReview,
    QueryPlan,
    Support,
    assess,
    balanced_chunks,
    checked_supports,
    parse_model_json,
)
from test_conversation_pipeline import chunk


def test_balanced_context_reserves_space_for_each_search_before_neighbours():
    groups = [
        [chunk(f"a{i}") for i in range(8)],
        [chunk("new-controlling-rule")],
        [chunk("exception")],
    ]
    groups[0][1].metadata["adjacent_to"] = "a0"
    first = list(balanced_chunks(groups))[:3]
    assert [c.chunk_id for c in first] == ["a0", "new-controlling-rule", "exception"]


def test_context_deduplicates_and_preserves_preferred_support():
    a, b, c = chunk("a"), chunk("b"), chunk("c")
    assert [x.chunk_id for x in balanced_chunks([[a, b], [a, c]], ["c"])] == [
        "c",
        "a",
        "b",
    ]


def test_unknown_source_and_invented_quote_fail_provenance():
    sources = [SimpleNamespace(text_snippet="A real passage that limits the rule.")]
    assert not checked_supports([Support(source=2, quote="A real passage")], sources)
    assert not checked_supports([Support(source=1, quote="The rule always applies.")], sources)
    assert checked_supports([Support(source=1, quote="A real passage")], sources)


def test_missing_issue_cannot_be_marked_supported():
    plan = QueryPlan(
        question_type="comparison",
        standalone_question="compare rules",
        issues=[
            dict(id="a", question="First rule?", search_query="first rule"),
            dict(id="b", question="Second rule?", search_query="second rule"),
        ],
    )
    review = EvidenceReview(issues=[dict(issue_id="a", status="supported", supports=[])])
    result = assess(review, plan, [])
    assert [x.status for x in result] == ["missing", "missing"]


def test_duplicate_assessment_rejected():
    plan = QueryPlan(
        question_type="definition",
        standalone_question="define rule",
        issues=[dict(id="a", question="Rule?", search_query="rule")],
    )
    review = EvidenceReview(
        issues=[
            dict(issue_id="a", status="missing"),
            dict(issue_id="a", status="supported"),
        ]
    )
    with pytest.raises(ValueError):
        assess(review, plan, [])


def test_untrusted_instructions_cannot_change_json_schema():
    with pytest.raises(Exception):
        parse_model_json('{"issues":[],"ignore_evidence":true}', EvidenceReview)


def test_whitespace_only_quote_cannot_pass_provenance():
    sources = [SimpleNamespace(text_snippet="A real statutory passage.")]
    assert not checked_supports([Support(source=1, quote=" " * 20)], sources)
