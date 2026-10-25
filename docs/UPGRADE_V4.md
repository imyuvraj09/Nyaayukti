> Historical notes from the supplied project. See [FINAL_REVIEW.md](FINAL_REVIEW.md) for this revision.

# Version 4: issue-based evidence retrieval

This release is based on the uploaded Nyaayukti-Retrieval-Fix ZIP (Library version 2). Later changes made in a separate Antigravity workspace were not uploaded and are not included. Extract into a new folder and retain your existing working folder for comparison.

## What changed

The previous pipeline searched a whole scenario, optionally tried one additional query, then asked the model to rewrite its draft. It could retrieve broadly related procedure while missing controlling rules, lose secondary evidence during context selection, and publish unsupported draft claims if review failed.

The active pipeline now performs:

1. **Planning:** one validated JSON plan with one to four legal issues and complementary queries. The original question remains in every generation/review request; history is included only for a dependent follow-up.
2. **Retrieval:** lexical and dense candidates, rank fusion, optional cross-encoder ordering, title/abbreviation matching, and explicit provision-text lookup. No uncalibrated score cutoff discards every passage. Numbered contents and amendment footnotes are excluded from exact provision promotion where detectable. Constitution Article lookups use text retrieval because schedule numbering is ambiguous.
3. **Context selection:** round-robin direct evidence across all searches, then neighboring context. Explicit section hits can retain up to three following chunks, with constituent IDs and original pages preserved. This carries continuations across noisy extracted headers without rebuilding the base embeddings.
4. **Evidence coverage:** a model assesses each planned issue and supplies exact supporting quotations. Invalid source IDs or quotes absent from the supplied passage downgrade the assessment. Missing/partial/conflicting evidence can trigger one targeted follow-up round. Context numbering is rebuilt and evidence is assessed again after a new search.
5. **Draft and review:** the original question, current passages and issue coverage inform the draft. A mandatory structured review returns individual legal/application blocks with supporting quotes. The application rejects invalid references, invented quotes, unknown issue IDs and unsupported blocks; it appends source markers itself. Missing issues receive a specific limitation rather than unrelated procedural filler.
6. **Failure behavior:** generation/review errors show labeled excerpts rather than an unchecked draft. Retrieval/configuration errors remain service failures; they are not disguised as absence of law.

A matching quotation establishes provenance only. Whether it entails the legal conclusion remains a fallible model judgment. This system does not certify current law, factual truth or legal advice. A model can still select a real but insufficient quote. Expert review is still needed for legal accuracy claims.

## Bounds and settings

- Up to four planned issues and eight total search queries.
- At most one follow-up retrieval round (`MAX_RETRIEVAL_ATTEMPTS=1` disables that round; values above 2 do not add rounds).
- Usually four model calls, five if follow-up evidence review runs: plan, assessment, draft, final review, plus reassessment when applicable.
- Context defaults: 12 sources, 28,000 characters total, at most 5,000 characters per source window. Truncation is marked in provenance.
- Final review is mandatory; the old `ENABLE_ANSWER_REVIEW` toggle is removed.
- Full per-query search text and chunk IDs are opt-in using `DEBUG_RETRIEVAL=true`. They remain in the owning response/history, not server logs. Do not publish private diagnostic exports.
- `RETRIEVAL_MODE=lexical` and `ENABLE_RERANKER=false` are an explicit diagnostic configuration, not equivalent to the default hybrid pipeline.

## Data additions

Three commencement-notification passages were transcribed via OCR and checked against rendered English pages 3, 5 and 7 of the official government-hosted combined PDF:

https://hajcommittee.gov.in/uploads/assets/3-new-criminal-laws.pdf

The original PDF is retained in `rag-service/data/raw/notifications/`. The passages retain URL, retrieval date (2026-10-15), source hash and PDF pages in `supplemental_chunks.jsonl`. They are searchable through the lexical branch and reranked alongside other candidates; the original 6,545-vector collection remains unchanged. The runtime has 6,548 text passages in total.

These historical commencement notices do not establish the current amendment status of every provision. The original 14-document corpus has not been comprehensively updated or legally verified. IPC, CrPC, the General Clauses Act, Contract Act, state legislation, and verified judgment coverage remain incomplete or absent; the system must identify gaps rather than fill them from memory.

## Fresh-folder setup

Use Python 3.12 and Node 22.12 or newer. Create/activate the root `.venv`, install `requirements.txt`, and run `npm run install:all`.

To run alongside your existing application:

```sh
python scripts/configure_local.py --frontend-port 5175 --backend-port 3002 --rag-port 8002
```

This creates three matching `.env` files and a shared service token. Set your provider/model/key in `rag-service/.env` and your persistent MongoDB URI in `backend/.env`. Transfer only needed values from your old configuration, not entire files; this avoids restoring inconsistent ports or collection names. Do not reuse an exposed credential.

```sh
npm run check:setup
python scripts/check_index.py
npm run dev
```

Open http://localhost:5175 for the example above. The development launcher refuses occupied ports and mismatched frontend/backend/RAG addresses. It never kills unrelated processes. Vite uses a strict port instead of silently selecting a new one. Configuration checks do not prove that MongoDB or the LLM is ready.

Create a new chat. Under **Answer processing details**, verify `issue-evidence-v4.0`, generation/review status and request ID. Saved older answers retain their original content and metadata.

## Diagnostics

No model download or LLM call is needed for the index identity check:

```sh
python scripts/check_index.py
```

Offline lexical diagnostic (no LLM calls):

```sh
python scripts/diagnose_query.py "Consumer Protection Act consumer rights" --lexical --show-evidence
```

Live local pipeline test (uses your provider quota; may download models on first use):

```sh
python scripts/diagnose_query.py "Your legal question" --live-generation --show-evidence
```

The CLI calls the actual Python pipeline but does not test browser cookies, Node proxying or MongoDB persistence. For those, run a fresh question through the UI and inspect its processing details. Do not treat HTTP 200 as proof of evidence quality.

## Evaluation and limits

See VALIDATION.md and retrieval-comparison.json. The ten comparison examples are development regression tests, not held-out evidence of legal accuracy. Two improvements also depend on adding previously absent notification material. No live generated-answer comparison is claimed for this build because no provider credentials were available here.

Remaining work: run live questions across topics, have legal claims and citations reviewed by a qualified person, measure cost/latency on your laptop, and complete full MongoDB and real-browser tests. Mixed Hindi/English input is not a measured capability; the unchanged query normalization and pretrained models may handle some inputs, but no multilingual accuracy claim is made. Prompt-injection protections are layered constraints and validation, not a proven defense against every attack.
