# Architecture

React renders the chat and citations. Express authenticates requests, verifies conversation ownership, persists messages in MongoDB and proxies to FastAPI using a shared service token. FastAPI admits one query at a time and lazily initializes local retrieval resources.

The active Python pipeline is `issue-evidence-v4.0`:

1. Validate a small issue/search plan; retain the original question and only relevant conversation history.
2. Search each issue using BM25, dense vectors and reciprocal-rank fusion. Match document titles/aliases, inspect explicit provision starts and optionally rerank.
3. Balance direct passages across searches, preserving provenance and useful continuation text.
4. Assess each issue using quoted evidence. Invalid quotes/IDs cannot establish coverage. Perform at most one follow-up search round for gaps.
5. Generate a draft and require a structured support review. Keep supported blocks, append source markers in application code, and report unresolved issues.
6. Return readable prose, source passages, issue coverage, pipeline version and request diagnostics. Store these with the authenticated conversation.

See UPGRADE_V4.md for settings, limits and failure behavior. A quote check proves that text was supplied, not that the model's interpretation is correct. No calibrated confidence or expert legal verification is claimed.

## Storage and boundaries

- MongoDB stores accounts and chat history. Existing password hashing, hashed session tokens, ownership controls and rate limits remain.
- Chroma stores the original 6,545 passage embeddings; runtime queries do not create missing collections.
- Canonical JSONL supplies the passage text. Three supplementary notification passages enter lexical search without pretending to have dense vectors.
- Source metadata guesses are not presented as verified sections. Explicit section windows preserve original chunk IDs and PDF pages.
- Source labels are unique within a response, and UI anchors are unique across messages. Raw HTML and model-supplied remote images are not rendered.
- Full search-text diagnostics are opt-in and request-scoped. No legal question or API key is logged by the new pipeline.

This local prototype uses process-local concurrency guards, not a distributed queue. It is not configured for multi-worker deployment. A failed RAG request may leave its user message saved without an assistant answer. Provider retries, model downloads and CPU inference still affect latency.

## Main files

- `rag-service/rag/conversation_pipeline.py`: orchestration and response assembly.
- `rag-service/rag/evidence.py`: validated model structures, prompts and provenance checks.
- `rag-service/retrieval/hybrid.py`: lexical/dense retrieval and section context.
- `scripts/configure_local.py`, `scripts/check-setup.js`: consistent local wiring and port checks.
- `scripts/check_index.py`, `scripts/diagnose_query.py`: explicit runtime diagnostics.
- `frontend/src/components/chat/`: answer, source and processing-detail rendering.
