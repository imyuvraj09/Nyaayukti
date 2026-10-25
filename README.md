# Nyaayukti

Start with [the current review and validation report](docs/FINAL_REVIEW.md). This revision preserves the uploaded interface, legal corpus and application features while tightening request boundaries and improving retrieval and connection handling.

An Indian legal-information assistant built with React, Express, FastAPI, MongoDB and retrieval-augmented generation (RAG). This is a local-first BTech project, not a substitute for legal advice or a claim of production readiness.

The system retrieves passages from 14 bundled legal documents plus three commencement-notification excerpts, combines keyword and vector search, optionally reranks passages, plans issue-specific searches, checks evidence coverage, and asks a configured language model to draft and review a cited response. Users can inspect source excerpts and PDF page numbers. Missing model access is reported as retrieved excerpts, never disguised as a completed analysis.

## Run locally

Requirements: Node.js 22.12 or newer, Python 3.12, and a running local MongoDB server. Docker is not required or included. Internet access is needed to install dependencies, download embedding/reranking models on first use, and call the configured LLM.

From the project directory:

```sh
python -m venv .venv
```

Activate it: Windows PowerShell `.venv\Scripts\Activate.ps1`; macOS/Linux `source .venv/bin/activate`.

```sh
python -m pip install -r requirements.txt
npm run install:all
python scripts/configure_local.py
```

For a CPU-only PyTorch installation, install torch from its CPU wheel index before installing requirements. The ML dependencies and model weights are considerably larger than the web application.

Edit `rag-service/.env`: set `GEMINI_API_KEY` and `LLM_MODEL` to a model available to your account; keep `LLM_PROVIDER=gemini`. Do not put keys in frontend code. Alternatively configure the OpenAI-compatible provider using the settings in `utils/config.py`. Credentials and local `.env` files are intentionally excluded from this archive.

Check `backend/.env`: `MONGODB_URI` must point to your running database. The configuration script creates matching backend/RAG tokens and consistent ports across all three service configuration files and refuses to overwrite existing configuration.

```sh
npm run check:setup
python scripts/check_index.py
npm run dev
```

Open http://localhost:5173. Express listens on port 3000 and FastAPI on port 8000. If troubleshooting, start each service in a separate terminal with `npm run dev:rag`, `npm run dev:backend`, and `npm run dev:frontend`.

The bundled vector collection retains its historical internal name `nyayasetu_legal_documents`. Do not rename this setting without rebuilding the collection. This is a storage identifier, not the displayed product name.

For a lightweight retrieval diagnostic, set `RETRIEVAL_MODE=lexical` and `ENABLE_RERANKER=false`. This explicitly disables vector search and the cross-encoder; it is not equivalent to the full retrieval configuration. The first full query can take longer while models load. Restart the RAG service after changing its settings.

## Check the project

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
npm run test:security --prefix backend
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

`npm test --prefix backend` additionally starts a temporary MongoDB instance; its binary must be supported by the host. See [current validation](docs/FINAL_REVIEW.md) for what ran and what remains unverified.

## Project map

- `frontend/`: React interface, authentication screens, chat and source display.
- `backend/`: Express API, MongoDB persistence, authentication, chat ownership and RAG proxy.
- `rag-service/`: ingestion, local retrieval, model adapters and answer orchestration.
- `evaluation/`: metrics and a human-review export for the current pipeline.
- `tests/`: evaluation tests; each service also owns its focused tests.
- `scripts/`: local configuration and development launchers.

Read [architecture](docs/ARCHITECTURE.md), [review](docs/REVIEW.md), [data coverage](docs/DATA.md), and [demo/viva preparation](docs/DEMO_AND_VIVA.md).

## Limits and responsible presentation

A valid citation label only proves that a referenced source exists. It does not prove that the source supports every claim. Automated answer review can still miss errors. No measured legal-answer accuracy, calibrated confidence, or current-law completeness is claimed. Case-law search is not implemented in the simplified application. The corpus does not cover all statutes, amendments, state laws or jurisdictions.

Authentication recovery requires your own configured mail delivery service. Query coordination is designed for one backend and one RAG process, with two bounded RAG requests and serialized local inference. It is not a distributed lock. Read the review before deploying publicly.

Keep the original author and license attribution. Explain your own implementation decisions and disclose assistance honestly in your submission. The code license does not independently establish redistribution rights for bundled source documents.
