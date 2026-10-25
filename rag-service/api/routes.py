"""
Nyaayukti RAG Service — API route handlers.

All routes are mounted under the /api/v1 prefix (configured in main.py).
Wires the legal RAG pipeline into POST /api/v1/query.
"""

import secrets
import threading
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from rag.conversation_pipeline import (
    PIPELINE_VERSION,
)
from rag.conversation_pipeline import (
    ConversationPipeline as LegalRAGPipeline,
)
from schemas.query import QueryRequest
from schemas.response import QueryResponse, SourceDocument
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def require_service_token(x_service_token: str = Header(default="")):
    expected = settings.RAG_SERVICE_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="Service authentication is not configured")
    if not secrets.compare_digest(x_service_token.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid service credentials")


router = APIRouter(dependencies=[Depends(require_service_token)])

# Lazy singleton: initialize only when a query needs it
_RAG_PIPELINE: LegalRAGPipeline | None = None
_PIPELINE_LOCK = threading.Lock()
_QUERY_SLOT = threading.BoundedSemaphore(settings.MAX_CONCURRENT_QUERIES)


def get_pipeline() -> LegalRAGPipeline:
    """Lazy loader for the LegalRAGPipeline singleton."""
    global _RAG_PIPELINE
    with _PIPELINE_LOCK:
        if _RAG_PIPELINE is None:
            _RAG_PIPELINE = LegalRAGPipeline()
    return _RAG_PIPELINE


@router.get("/health")
def health_check():
    """Return the service health and configuration status."""
    from llm.provider import get_llm_provider

    provider = get_llm_provider()
    llm_health = {
        "provider": provider.provider_name,
        "model": provider.model_name,
        "configured": provider.is_configured(),
        "available": None,
    }
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "pipeline": PIPELINE_VERSION,
        "llm_provider": llm_health.get("provider", settings.LLM_PROVIDER),
        "llm_model": llm_health.get("model", settings.LLM_MODEL),
        "llm_configured": llm_health.get("configured", False),
        "llm_available": llm_health.get("available", False),
        "vector_db_collection": settings.VECTOR_COLLECTION_NAME,
    }


@router.get("/health/llm")
def llm_health_check():
    """Expose safe health information for LLM provider without revealing secrets."""
    from llm.provider import get_llm_provider

    return get_llm_provider().check_health()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """Accept a legal question and return a grounded, cited RAG-generated response.

    Executes:
    1. Query preprocessing
    2. Hybrid lexical/dense retrieval and optional cross-encoder reranking
    3. Structured legal context construction with [SOURCE N] labels
    4. Grounded answer generation via LLM provider
    5. Deterministic citation validation and safety checks
    """
    session_id = request.session_id or str(uuid.uuid4())
    request_id = getattr(request, "request_id", None) or str(uuid.uuid4())

    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty or whitespace only.",
        )

    logger.info(
        "API Query received | session=%s | request_id=%s | length=%d",
        session_id,
        request_id,
        len(request.query),
    )

    if not _QUERY_SLOT.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="The answer service is busy; retry shortly.",
            headers={"Retry-After": "5"},
        )
    try:
        pipeline = get_pipeline()
        rag_result = pipeline.query(
            request.query,
            request_id=request_id,
            use_query_answer_grounding=request.use_query_answer_grounding,
            conversation_history=request.conversation_history,
        )

        # Convert SourceReference list to SourceDocument list for response
        mapped_sources = [
            SourceDocument(
                source_label=src.source_label,
                chunk_id=src.chunk_id,
                document_name=src.document_name,
                document_type=src.document_type,
                source_filename=src.source_filename,
                section=(
                    f"Article {src.section_number}"
                    if "constitution" in src.document_name.lower()
                    else f"Section {src.section_number}"
                )
                if src.section_number
                else None,
                section_number=src.section_number or None,
                section_title=src.section_title or None,
                act_short_name=src.act_short_name or None,
                page=src.page_numbers[0] if src.page_numbers else None,
                page_numbers=src.page_numbers,
                content_snippet=src.text_snippet,
                relevance_score=float(src.similarity_score) if src.similarity_score is not None else None,
                reranker_score=float(src.reranker_score) if src.reranker_score is not None else None,
                evidence_type=getattr(src, "evidence_type", "STATUTE"),
                case_name=getattr(src, "case_name", None),
                court=getattr(src, "court", None),
                citation=getattr(src, "citation", None),
                paragraph_number=getattr(src, "paragraph_number", None),
                is_holding_or_ratio=getattr(src, "is_holding_or_ratio", False),
                metadata=src.metadata,
            )
            for src in rag_result.sources
        ]

        return QueryResponse(
            answer=rag_result.answer,
            sources=mapped_sources,
            session_id=session_id,
            query=request.query,
            retrieval_metadata=rag_result.retrieval_metadata,
            model_metadata=rag_result.model_metadata,
            warnings=rag_result.warnings,
            status=rag_result.status,
            requested_facets=getattr(rag_result, "requested_facets", []),
            facet_coverage=getattr(rag_result, "facet_coverage", {}),
            facet_validation=getattr(rag_result, "facet_validation", {}),
            claim_validation=getattr(rag_result, "claim_validation", {}),
            quality_status=getattr(rag_result, "quality_status", "COMPLETE"),
            case_law_status=getattr(rag_result, "case_law_status", None),
            evidence_graph=getattr(rag_result, "evidence_graph", None),
            generation_status=getattr(rag_result, "generation_status", "SUCCESS"),
            retrieval_status=getattr(rag_result, "retrieval_status", "SUCCESS"),
            validation_status=getattr(rag_result, "validation_status", "PASSED"),
            request_id=request_id,
            failed_stage=getattr(rag_result, "failed_stage", None),
            error_category=getattr(rag_result, "error_category", None),
            retryable=getattr(rag_result, "retryable", False),
            safe_user_message=getattr(rag_result, "safe_user_message", None),
            intent_coverage=getattr(rag_result, "intent_coverage", None),
        )

    except HTTPException:
        raise
    except Exception as err:
        logger.error("Query failed | request_id=%s | type=%s", request_id, type(err).__name__)
        raise HTTPException(
            status_code=503,
            detail="Legal query processing is unavailable; please retry.",
        ) from err

    finally:
        _QUERY_SLOT.release()
