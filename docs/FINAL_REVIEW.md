# Nyaayukti: current engineering review

Reviewed 22 October 2026. Start here; older review/upgrade files are retained as historical notes.

## What this revision means

This is a maintainability, security and reliability revision of the supplied B.Tech project. It is not a claim that the software is wholly human-authored, immune to attack, legally authoritative or production-certified. Existing implementations were retained where sound. Formatting and type annotation improvements do not establish authorship. Present assistance honestly and be prepared to explain the decisions below.

The review covered the archive inventory, source boundaries, application routes, authentication, persistence, retrieval, generation, ingestion utilities, dependency manifests and tests. Static tools traversed the source tree. The active request path received focused manual review. Binary assets and source PDFs were preserved, not independently verified for legal accuracy. A file-level change inventory is included; this is not a claim of manual verification of every line or every PDF page.

## Features retained

- Home, About, contributor imagery, navigation, chat modal and responsive styles.
- Registration, login, logout, cookie sessions, verification and password recovery through the configured mail adapter.
- Private chat sessions, history, deletion, retry, source cards and citation navigation.
- Gemini and OpenAI-compatible provider adapters; explicit excerpt fallback when generation is unavailable.
- Noisy-input preprocessing, lexical/dense hybrid retrieval, cross-encoder reranking, issue planning, evidence review, follow-up searches and final support checking.
- Original PDFs, processed passages, supplemental excerpts and vector store. The existing internal collection name remains unchanged.

These are implementation-preservation statements, not a browser/device parity certification. No visual redesign was introduced.

## Changes and reasons

| Area | Change | Reason |
| --- | --- | --- |
| Repository | Consistent JS/JSX formatting, LF text, explicit editor settings, Python 3.12 type syntax and lint configuration | Make maintenance and code review predictable |
| Secrets | Removed the three packaged `.env` files; retained examples and the local setup generator | Shared archives must not carry operational credentials |
| Dependencies | Updated compatible npm lockfile versions; replaced nodemon with Node's native `--watch` | Remove reported vulnerable dependency chains without changing development hot reload |
| API | Bounded scalar request IDs; validated direct-chat IDs; bounded pagination; 413 for oversized bodies | Reject malformed input before logs, database operations or provider calls |
| RAG API | 128 KiB body cap including chunked bodies; bounded IDs; production docs disabled; production token-length check | Bound request allocation and reduce unintended service exposure |
| Deployment | Validate proxy-hop count, HTTPS frontend and service-token length in production | Fail early on unsafe deployment configuration |
| Privacy | `Cache-Control: no-store`, request IDs in responses, reduced URL/database-error logging | Avoid shared-cache persistence and unnecessary sensitive logs |
| Authentication | Perform a password hash for nonexistent users too | Reduce one account-enumeration timing difference; this is not a complete constant-time guarantee |
| Gateway | Reject redirects when forwarding the service credential; correct relevance-score field mapping | Avoid credential forwarding and retain citation metadata accurately |
| Retrieval | Precompute passage tokens and definition terms once | Avoid repeating immutable corpus preprocessing on every question |
| Concurrency | Two bounded requests by default; local retrieval protected by a lock | Overlap provider waits without racing lazy model initialization or overloading inference |
| Providers | Thread-local SDK clients reused across stages; close clients at shutdown; one provider attempt by default | Reduce connection setup and timeout multiplication; optional second attempt remains configurable |
| Answer display | App-owned rule/application/next-step headings and citations; plain-language prompt; explicit evidence limits | Improve readability without inventing missing legal procedures or remedies |
| Retry | Return created conversation ID even on generation failure; reuse the latest identical unanswered user turn | Keep retry in the same chat and avoid storing that question twice |
| Frontend | Ignore stale conversation-load failures, reset pending message loading for a new chat, bound question length | Reduce stale state and confusing UI transitions |
| Model loading | Explicitly disable remote model code and Chroma embedding-function selection | Keep embeddings controlled by this application |
| Diagnostics | Repair the live smoke test to authenticate and fail on excerpt-only output; use portable temporary MongoDB setup | Avoid a misleading success result |

## Measured validation

| Check | Result |
| --- | --- |
| Python offline suites | 56 passed, including real-corpus lexical retrieval and fake-provider generation tests |
| Backend security/concurrency suite | 17 passed |
| Backend API suite with temporary MongoDB | 23 passed |
| Frontend citation tests | 2 passed |
| Frontend build and oxlint | Passed |
| Python lint and formatting | Passed |
| SQLite integrity / base index IDs | Integrity OK; 6,545 passages and 6,545 matching IDs |
| npm audit | Backend 0, frontend 0 reported findings after updates |
| Python dependency audit | Unresolved ChromaDB advisories; see below |
| Python static security scan | One low-severity exception-fallback finding; reviewed below |

The tests use synthetic credentials, isolated temporary MongoDB and provider doubles. No original credential was used. The MongoDB test initially failed with exit 100; `--nounixsocket` made it runnable in this environment. This change is in test setup, not production database configuration.

Warm BM25 median latency fell from 39.813 ms to 2.617 ms across five queries repeated five times (25 observations per implementation), with identical top-20 rankings. See `RETRIEVAL_BENCHMARK.json`; reproduce with `python scripts/benchmark_retrieval.py`. This is a local microbenchmark, not an end-to-end chatbot speed claim. Initial model downloads, CPU reranking, network time and model generation still dominate many requests. The evidence pipeline still makes four calls normally, or five with follow-up evidence review; no safety review was removed to obtain this timing.

Live Gemini/OpenAI quality, dense-model inference, the email adapter, browser interaction/accessibility across devices, production load, multi-host deployment and legal-answer accuracy were not validated here. The Python lock file is a resolved dependency/audit snapshot, not proof that all ML packages were installed and exercised in this environment.

## Security findings that remain relevant

1. **Rotate shared credentials.** The original ZIP contained runtime environment files. Treat any real API key or shared service token in it as exposed. Revoke it at its provider and generate fresh local configuration. Removing it from the new ZIP does not revoke the original.
2. **ChromaDB advisories remain unresolved.** `pip-audit` reported five records representing four unique advisory IDs for resolved `chromadb==1.5.9`; no fix versions were listed: `PYSEC-2026-311`, `PYSEC-2026-3813`, `PYSEC-2026-3814`, `PYSEC-2026-3815`. These describe server code-injection and authorization weaknesses. This project uses an embedded `PersistentClient` and does not launch Chroma's HTTP server or expose collection-management routes. Keep that boundary: do not run `chroma run` publicly, accept user-supplied model repositories, or accept untrusted replacement indexes. Explicit `embedding_function=None` and `trust_remote_code=False` are hardening, not an upstream patch. Recheck the advisories before deployment.
3. **Single gateway process.** The per-conversation generation/deletion lock is process-local. Multiple backend workers need a database-backed lease or queue before use. Two RAG slots are per process; adding workers also duplicates model memory.
4. **Operational deployment still matters.** Keep MongoDB and RAG on private interfaces, require authenticated persistent MongoDB in production, terminate TLS, set correct proxy trust, restrict filesystem access, configure backups and retention, and impose reverse-proxy body/read/connection limits. Rate limiting does not stop every denial-of-service attack.
5. **Recovery writes are not a transaction.** Password reset updates, token consumption and session revocation can partially fail during a database outage. Production recovery needs transaction/retry design. Registration intentionally retains its existing account-exists message.
6. **Cancellation/idempotency limits.** A browser disconnect does not cancel Python inference. The unanswered-turn retry fix is not general exactly-once delivery: a completed response lost in transit can still be submitted again. Long conversation history responses are not paginated.
7. **Prompt injection and privacy.** Prompts treat evidence/history as data, structured supports are checked against passages, raw HTML/images/external model links are blocked in answer rendering, and the model has no execution tools. These controls reduce risk but do not prove factual correctness or prevent every injection. Query/history/evidence are sent to the chosen LLM provider; decide consent, retention and access policies before real case use.
8. **Corpus and legal limits.** Retrieval can miss an exception or amendment. Matching a quote proves provenance, not that the conclusion follows. State laws, current amendments and verified judgment retrieval are incomplete. No lawyer reviewed generated answers in this revision. Do not label them “perfect legal advice.”
9. **Static scan finding.** Bandit reports B110 at hardware detection: exceptions fall back to CPU if CUDA detection is unavailable. This was retained deliberately. Passing scans is not a penetration test or a guarantee of safety.

## Local setup

Use Node 22.12+ and Python 3.12. From the `Nyaayukti` directory:

```sh
python -m venv .venv
# Activate: Windows PowerShell .venv\Scripts\Activate.ps1
# Activate: macOS/Linux source .venv/bin/activate
python -m pip install -r requirements.txt
npm run install:all
python scripts/configure_local.py
```

Start a persistent MongoDB instance. Edit `backend/.env` for its URI. Edit `rag-service/.env` for a freshly rotated provider key and a model available to your account. The setup script supplies matching random service tokens and refuses to overwrite existing files. Keep the historical vector collection name. Configure the mail adapter only if using email recovery/verification.

```sh
npm run check:setup
python scripts/check_index.py
npm run dev
```

Open `http://localhost:5173`. Internet is required for package/model downloads and hosted LLM calls. Model files and node_modules are not bundled; source data and the vector database are. CPU-only users should install the CPU PyTorch build before the remaining ML dependencies. `requirements.lock.txt` records the audit resolution; platform-specific CPU installations may need a separate lock and audit.

Tune `MAX_CONCURRENT_QUERIES=1` on low-memory hardware; default is 2. `LLM_MAX_ATTEMPTS=1` avoids retries multiplying across stages; set 2 if transient retry behavior matters more than latency. Keep hybrid retrieval and reranking enabled for the existing feature set. Lexical-only mode remains a diagnostic option, not a quality-equivalent optimization.

## Reproduce checks

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check rag-service evaluation scripts tests
npm test --prefix backend
npm run test:security --prefix backend
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
npm audit --prefix backend
npm audit --prefix frontend
```

With your RAG service running and credentials configured, `node backend/tests/live_rag_integration.js` performs a billable live smoke test against a temporary database. It now requires successful generation, source retrieval and persisted history. It cannot establish legal correctness.

## Explain this project in your viva

Trace one request: authenticated cookie → user-scoped MongoDB session → gateway with service token → issue planning → BM25/dense fusion → reranking → evidence assessment → supported draft/review → checked citations → persisted answer → Markdown/source cards.

Be able to explain why BM25 helps exact legal terminology, why dense retrieval helps paraphrases, why reranker scores are not confidence percentages, why missing evidence must not be filled from memory, why histories cannot be globally cached, and why a matching quotation still needs legal interpretation. Demonstrate both a supported answer and a safe insufficient-evidence response. Discuss the measured retrieval improvement separately from model latency.

## References consulted

- OWASP prompt injection prevention: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- OWASP RAG security: https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html
- FastAPI deployment/process memory: https://fastapi.tiangolo.com/deployment/concepts/
- Google Gen AI client lifecycle: https://googleapis.github.io/python-genai/
- Chroma advisory: https://github.com/advisories/GHSA-f4j7-r4q5-qw2c

Dependency results are dated observations. Rerun audits on the actual deployment environment.
