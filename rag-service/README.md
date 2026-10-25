# Nyaayukti RAG service

See the root README for installation and local configuration, and `../docs/ARCHITECTURE.md` for the active request path.

Run from the project root with `npm run dev:rag`. The launcher selects the root `.venv` interpreter. Configure `rag-service/.env`, never browser-side variables. The default provider requires an explicit model ID and key.

The active retriever is `retrieval/hybrid.py`. The canonical corpus and matching Chroma index are bundled. Ingestion/chunking/vector-store command modules remain for corpus maintenance; inspect their `--help` and back up the existing pair before rebuilding.

Health status does not prove legal-answer quality. `/health` does not trigger model downloads; the explicit LLM health route checks provider access. Automated review and source-ID checks do not replace human verification of legal claims.
