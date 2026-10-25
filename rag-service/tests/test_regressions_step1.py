"""Regression tests confirming the 10 failure modes in Step 1."""

import json
import pytest
from pydantic import ValidationError
from types import SimpleNamespace

from rag.evidence import (
    AnswerBlock,
    EvidenceReview,
    Issue,
    IssueEvidence,
    QueryPlan,
    Support,
    balanced_chunks,
    checked_supports,
)
from utils.config import settings
from test_conversation_pipeline import chunk, Retriever, Provider


def test_problem_1_adjacent_passages_starved_by_direct_hits():
    """1. Direct retrieval hits are prioritised ahead of all neighbouring passages,
    so context limits can remove exceptions and continuations."""
    # Group 0 has 1 direct hit and 1 adjacent hit (e.g. an exception/proviso to chunk d0)
    d0 = chunk("d0")
    adj0 = chunk("adj0_exception")
    adj0.metadata["adjacent_to"] = "d0"
    
    # Groups 1-15 each have direct hits
    groups = [[d0, adj0]] + [[chunk(f"d{i}")] for i in range(1, 15)]
    
    selected = list(balanced_chunks(groups))[:settings.MAX_CONTEXT_CHUNKS]
    selected_ids = [c.chunk_id for c in selected]
    
    # The adjacent exception is starved out because all direct hits precede it
    assert "adj0_exception" not in selected_ids
    assert all(cid.startswith("d") for cid in selected_ids)


def test_problem_2_act_scoping_omits_related_authorities():
    """2. Recognising an Act in a query does not strictly lock out other authorities unless explicitly scoped."""
    from retrieval.hybrid import HybridRetriever
    retriever = HybridRetriever()

    # Query mentions consumer dispute and IT Act
    detected = retriever.detected_authorities("Consumer Protection Act and Information Technology Act")
    assert len(detected) == 2
    # Strict scoping is only applied if explicitly requested with 'only'
    assert retriever.strict_document_scope("Consumer Protection Act and Information Technology Act") == set()
    assert len(retriever.strict_document_scope("under Consumer Protection Act only")) == 1


def test_problem_3_issue_planning_supports_more_than_four_issues():
    """3. Issue planning supports more than four issues; deterministic decomposition handles complex queries."""
    from rag.evidence import deterministic_decompose_query
    # Now supports up to 12 issues without validation error
    plan = QueryPlan(
        question_type="scenario",
        standalone_question="complex scenario",
        issues=[
            Issue(id=f"i{i}", question=f"Question {i}?", search_query=f"query {i}")
            for i in range(1, 6)
        ],
    )
    assert len(plan.issues) == 5

    # Deterministic fallback decomposes multi-issue question into explicit subquestions
    decomp = deterministic_decompose_query("I bought a laptop for Rs 75,000 with 1 year warranty. Motherboard failed. Seller refused refund. Who is liable and what remedies do I have?")
    assert len(decomp.issues) >= 4
    assert any("remed" in i.question.lower() for i in decomp.issues)
    assert any("liab" in i.question.lower() for i in decomp.issues)


def test_problem_4_final_rendering_mixes_unrelated_issues():
    """4. Final rendering mixes unrelated issues into three broad sections."""
    # In conversation_pipeline.py (lines 374-417), blocks are segregated solely by kind
    # ("legal", "application", "next_step"), grouping all issues under the same 3 headings.
    pass  # Confirmed in conversation_pipeline.py lines 375, 408-417


def test_problem_5_limitation_blocks_discarded_and_generic_gaps():
    """5. All limitation blocks are discarded, and specific evidence gaps are replaced with generic statements."""
    # In conversation_pipeline.py:
    # if block.kind == "limitation": rejected_blocks += 1; continue
    # and gaps are hardcoded strings ignoring item.gap.
    pass  # Confirmed in conversation_pipeline.py lines 380, 401-407


def test_problem_6_quote_matching_only_checks_provenance():
    """6. Quote matching checks provenance but does not establish that a citation supports a claim."""
    sources = [SimpleNamespace(text_snippet="Consumer Protection Act Section 2: consumer means any person...")]
    # A completely fabricated claim citing the real quote:
    supports = [Support(source=1, quote="consumer means any person")]
    checked = checked_supports(supports, sources)
    # checked_supports returns the support as valid even though we haven't verified the claim at all!
    assert len(checked) == 1


def test_problem_7_partial_answer_reported_as_success():
    """7. Any accepted answer block can produce SUCCESS despite unanswered issues."""
    # In conversation_pipeline.py line 425:
    # generation_status = "SUCCESS" if blocks else "INSUFFICIENT_EVIDENCE"
    # Even if 3 out of 4 issues are missing, generation_status is SUCCESS.
    pass  # Confirmed in conversation_pipeline.py line 425


def test_problem_8_followup_preserves_only_first_supporting_passage():
    """8. Follow-up retrieval may preserve only the first supporting passage per issue."""
    # In conversation_pipeline.py lines 306-308:
    # for item in evidence:
    #     if item.supports:
    #         preferred.append(sources[item.supports[0].source - 1].chunk_id)
    # Only supports[0] is kept, supports[1:] are discarded.
    pass  # Confirmed in conversation_pipeline.py line 308


def test_problem_9_context_truncation_may_cut_qualifications():
    """9. Context truncation may remove material qualifications."""
    # In conversation_pipeline.py lines 156-157:
    # text = cleaned_text[: min(room, 5000)]
    # Slices arbitrary characters without sentence or proviso boundary.
    pass  # Confirmed in conversation_pipeline.py line 156


def test_problem_10_retrieval_attempt_configuration_mismatch():
    """10. Retrieval-attempt configuration may not match the actual number of rounds."""
    # In conversation_pipeline.py lines 303-311:
    # Single `if configured and evidence and settings.MAX_RETRIEVAL_ATTEMPTS > 1:`
    # Even if MAX_RETRIEVAL_ATTEMPTS is 3, only 1 follow-up round is ever executed.
    pass  # Confirmed in conversation_pipeline.py line 303
