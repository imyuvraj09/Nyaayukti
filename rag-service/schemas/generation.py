"""
Pydantic schemas for LLM answer generation in Nyaayukti RAG Service.

Defines the structure for source references, generation responses, and metadata.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Source provenance record associated with a generated legal answer."""

    source_label: str = Field(
        ...,
        description="Assigned label used in prompt context and citation (e.g. [SOURCE 1])",
        examples=["[SOURCE 1]"],
    )
    chunk_id: str = Field(
        ...,
        description="Unique chunk identifier from legal_chunks.jsonl",
        examples=["bns_2023_c0384"],
    )
    document_name: str = Field(
        ...,
        description="Canonical Indian statutory enactment name",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    document_type: str = Field(
        default="Unknown",
        description="Legal domain classification",
        examples=["Criminal Law"],
    )
    source_filename: str = Field(
        default="",
        description="Original source PDF file name",
        examples=["bns_2023.pdf"],
    )
    page_numbers: list[int] = Field(
        default_factory=list,
        description="Source PDF page numbers containing this passage",
        examples=[[82]],
    )
    similarity_score: float = Field(
        ...,
        description="Initial dense retrieval cosine score",
        examples=[0.8252],
    )
    reranker_score: float = Field(
        ...,
        description="Cross-encoder relevance score",
        examples=[0.9996],
    )
    text_snippet: str = Field(
        ...,
        description="Excerpt or full text of the statutory passage",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata",
    )
    section_number: str = Field(
        default="",
        description="Statutory section number (e.g. '101', '103')",
    )
    section_title: str = Field(
        default="",
        description="Official title of the statutory section",
    )
    act_short_name: str = Field(
        default="",
        description="Abbreviated statutory enactment name (e.g. 'BNS')",
    )
    evidence_type: str = Field(
        default="STATUTE",
        description="Evidence type: STATUTE, CASE_LAW, etc.",
    )
    case_name: str = Field(
        default="",
        description="Official case name if evidence_type is CASE_LAW",
    )
    court: str = Field(
        default="",
        description="Court name (e.g. Supreme Court of India)",
    )
    citation: str = Field(
        default="",
        description="Official case citation",
    )
    judgment_date: str = Field(
        default="",
        description="Judgment date (YYYY-MM-DD)",
    )
    paragraph_number: str = Field(
        default="",
        description="Numbered paragraph or passage in judgment",
    )
    topic_compatibility: str = Field(
        default="DIRECT",
        description="Topic compatibility: DIRECT, RELATED, BACKGROUND, IRRELEVANT",
    )


class RAGResponse(BaseModel):
    """Grounded legal response returned to the user or API client."""

    query: str = Field(
        ...,
        description="Original or normalized user query string",
    )
    answer: str = Field(
        ...,
        description="Grounded natural language answer synthesized from retrieved sources",
    )
    sources: list[SourceReference] = Field(
        default_factory=list,
        description="List of verified legal source chunks included in the context",
    )
    retrieval_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata on candidate discovery, filtering, and cross-encoder scoring",
    )
    model_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata regarding the LLM provider, model version, and tokens",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Safety, validation, or evidence limitation notices",
    )
    status: str = Field(
        default="pending",
        description="Execution status ('success', 'partial_success', 'unconfigured_llm', 'no_sources_found', 'retrieval_only', 'insufficient_evidence', 'error')",
    )
    requested_facets: list[str] = Field(
        default_factory=list,
        description="Requested legal facets identified from the query",
    )
    facet_coverage: dict[str, Any] = Field(
        default_factory=dict,
        description="Coverage status for each required facet in the retrieved evidence",
    )
    facet_validation: dict[str, Any] = Field(
        default_factory=dict,
        description="Facet completeness validation results on generated answer",
    )
    claim_validation: dict[str, Any] = Field(
        default_factory=dict,
        description="Substantive claim-to-evidence validation metrics",
    )
    quality_status: str = Field(
        default="UNVERIFIED",
        description="Overall legal answer quality gate status ('COMPLETE', 'PARTIALLY_COMPLETE', 'UNSUPPORTED_CLAIM', 'INSUFFICIENT_EVIDENCE', 'UNVERIFIED')",
    )
    case_law_status: str = Field(
        default="NOT_REQUESTED",
        description="Case law availability status: 'NOT_REQUESTED', 'FOUND', 'NOT_FOUND', 'CORPUS_UNAVAILABLE'",
    )
    evidence_graph: dict[str, Any] = Field(
        default_factory=dict,
        description="Structural summary of the multi-authority evidence graph",
    )
    generation_status: str = Field(
        default="SUCCESS",
        description="LLM generation outcome: 'SUCCESS', 'RETRIEVAL_ONLY', 'RATE_LIMITED', 'QUOTA_EXCEEDED', 'TIMEOUT', 'PROVIDER_ERROR', 'VALIDATION_FAILED', 'AUTHENTICATION_ERROR', 'INVALID_MODEL', 'UNCONFIGURED'",
    )
    retrieval_status: str = Field(
        default="SUCCESS",
        description="Retrieval pipeline outcome: 'SUCCESS', 'NO_SOURCES_FOUND', 'ERROR'",
    )
    validation_status: str = Field(
        default="NOT_RUN",
        description="Answer validation outcome: 'MODEL_REVIEWED_QUOTES_CHECKED', 'FAILED', 'NOT_RUN'",
    )
    request_id: str | None = Field(
        default=None,
        description="Unique request correlation ID matching the client's request",
    )
    failed_stage: str | None = Field(
        default=None,
        description="Pipeline stage where processing halted, if any ('CONFIGURATION', 'PLANNING', 'RETRIEVAL', 'EVIDENCE_ASSESSMENT', 'DRAFT_GENERATION', 'STRUCTURED_REVIEW', 'OUTPUT_PARSING', 'SCHEMA_VALIDATION', 'EVIDENCE_VALIDATION', 'RENDERING')",
    )
    error_category: str | None = Field(
        default=None,
        description="Explicit failure category ('UNCONFIGURED', 'AUTH_ERROR', 'INVALID_MODEL', 'RATE_LIMITED', 'QUOTA_EXCEEDED', 'TIMEOUT', 'EMPTY_RESPONSE', 'OUTPUT_TRUNCATED', 'JSON_PARSE_FAILED', 'SCHEMA_VALIDATION_FAILED', 'REVIEW_FAILED', 'INSUFFICIENT_EVIDENCE')",
    )
    retryable: bool = Field(
        default=False,
        description="Whether the operational failure is safe to retry",
    )
    safe_user_message: str | None = Field(
        default=None,
        description="Sanitized, user-friendly operational notice",
    )
    intent_coverage: dict[str, Any] | None = Field(
        default=None,
        description="Multi-intent query coverage report",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of generation",
    )
