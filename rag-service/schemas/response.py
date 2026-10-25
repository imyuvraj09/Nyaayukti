"""
Response schemas for the Nyaayukti RAG pipeline.

Supports grounded legal answer delivery, complete source provenance tracking,
reranker scores, retrieval metadata, and backward compatibility.
"""

from typing import Any

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """A single retrieved legal source used to ground the answer."""

    source_label: str | None = Field(
        default=None,
        description="Assigned label used in citations (e.g., [SOURCE 1]).",
        examples=["[SOURCE 1]"],
    )
    chunk_id: str | None = Field(
        default=None,
        description="Unique chunk identifier from legal_chunks.jsonl.",
        examples=["bns_2023_c0384"],
    )
    document_name: str | None = Field(
        default=None,
        description="Name or title of the source document.",
        examples=["Bharatiya Nyaya Sanhita, 2023"],
    )
    document_type: str | None = Field(
        default=None,
        description="Legal domain classification.",
        examples=["Criminal Law"],
    )
    source_filename: str | None = Field(
        default=None,
        description="Name of the source PDF.",
        examples=["bns_2023.pdf"],
    )
    section: str | None = Field(
        default=None,
        description="Section or clause number if detected.",
        examples=["Section 303"],
    )
    section_number: str | None = Field(
        default=None,
        description="Statutory section number (e.g. 303).",
    )
    section_title: str | None = Field(
        default=None,
        description="Official title or marginal heading of the section.",
    )
    act_short_name: str | None = Field(
        default=None,
        description="Short enactment code (e.g. BNS).",
    )
    article: str | None = Field(
        default=None,
        description="Article number (for constitutional documents).",
        examples=["Article 14"],
    )
    page: int | None = Field(
        default=None,
        description="Primary page number in the source PDF.",
        examples=[82],
    )
    page_numbers: list[int] = Field(
        default_factory=list,
        description="All source PDF page numbers containing this chunk.",
        examples=[[82]],
    )
    content_snippet: str | None = Field(
        default=None,
        description="Relevant text excerpt from the source.",
    )
    relevance_score: float | None = Field(
        default=None,
        description="Initial dense semantic similarity score (0-1).",
        examples=[0.8252],
    )
    reranker_score: float | None = Field(
        default=None,
        description="Cross-encoder relevance score (can be boosted by court level and holding).",
        examples=[0.9996],
    )
    evidence_type: str = Field(
        default="STATUTE",
        description="Evidence type: STATUTE or CASE_LAW.",
    )
    case_name: str | None = Field(
        default=None,
        description="Judicial case name for case law sources.",
    )
    court: str | None = Field(
        default=None,
        description="Court name (e.g. Supreme Court of India).",
    )
    citation: str | None = Field(
        default=None,
        description="Law report citation (e.g. (2019) 9 SCC 608).",
    )
    paragraph_number: str | None = Field(
        default=None,
        description="Paragraph number of the judgment.",
    )
    is_holding_or_ratio: bool = Field(
        default=False,
        description="Whether this excerpt contains the judicial ratio or holding.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible metadata.",
    )


class QueryResponse(BaseModel):
    """Schema for the response returned by the /api/v1/query endpoint."""

    answer: str = Field(
        ...,
        description="The generated answer to the user's legal question.",
    )
    sources: list[SourceDocument] = Field(
        default_factory=list,
        description="List of legal sources used to generate the answer.",
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID echoed back for conversation tracking.",
    )
    query: str | None = Field(
        default=None,
        description="Original user inquiry string.",
    )
    retrieval_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Candidate counts and document distribution statistics.",
    )
    model_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata on the LLM provider, model version, and tokens.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Operational warnings or fallback notices.",
    )
    status: str = Field(
        default="success",
        description="Execution status of the query pipeline.",
    )
    requested_facets: list[str] = Field(
        default_factory=list,
        description="Legal information facets identified in the query.",
    )
    facet_coverage: dict[str, Any] = Field(
        default_factory=dict,
        description="Coverage mapping for requested facets.",
    )
    facet_validation: dict[str, Any] = Field(
        default_factory=dict,
        description="Facet completeness validation report.",
    )
    claim_validation: dict[str, Any] = Field(
        default_factory=dict,
        description="Claim-evidence validation report.",
    )
    quality_status: str = Field(
        default="UNVERIFIED",
        description="Quality status (COMPLETE, PARTIALLY_COMPLETE, UNSUPPORTED_CLAIM, UNVERIFIED).",
    )
    case_law_status: str | None = Field(
        default=None,
        description="Status of case law retrieval: NOT_REQUESTED, FOUND, NOT_FOUND, CORPUS_UNAVAILABLE.",
    )
    evidence_graph: dict[str, Any] | None = Field(
        default=None,
        description="In-memory structural legal evidence graph.",
    )
    generation_status: str = Field(
        default="SUCCESS",
        description="Generation status: SUCCESS, RETRIEVAL_ONLY, RATE_LIMITED, QUOTA_EXCEEDED, TIMEOUT, PROVIDER_ERROR, VALIDATION_FAILED, AUTHENTICATION_ERROR, INVALID_MODEL",
    )
    retrieval_status: str = Field(
        default="SUCCESS",
        description="Retrieval status: SUCCESS, NO_SOURCES_FOUND, ERROR",
    )
    validation_status: str = Field(
        default="NOT_RUN",
        description="Validation status: MODEL_REVIEWED_QUOTES_CHECKED, FAILED, NOT_RUN",
    )
    request_id: str | None = Field(
        default=None,
        description="Unique request correlation ID matching the client's request.",
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
        description="Multi-intent query coverage report.",
    )
