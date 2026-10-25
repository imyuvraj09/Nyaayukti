> Historical notes from the supplied project. See [FINAL_REVIEW.md](FINAL_REVIEW.md) for this revision.

# Version 4 validation

Checks performed on the delivered source in the available Linux environment. No user API credentials were used.

| Check | Result |
|---|---|
| Python suite | 52 passed, including real-corpus retrieval, issue coverage, quote provenance, unsupported-block rejection, provider failures, privacy and API contract checks |
| Python Ruff F checks | Passed |
| Backend security/concurrency suite | 13 passed |
| Frontend citation tests | 2 passed |
| Frontend lint and production build | Passed |
| Server-rendered answer UI | Processing details, source type, citation anchors and blocked HTML/images passed |
| Startup script syntax and credential-pattern scan | Passed |
| Base corpus / vector IDs | All 6,545 base chunk IDs match the populated Chroma collection |
| Supplementary data | 3 notification passages; original government PDF retained; OCR checked against rendered pages |
| Isolated setup checks | Matching service tokens and custom ports; existing files not overwritten; incorrect frontend/backend wiring rejected |
| Lexical development regression comparison | Expected passage in top 3: baseline 5/10, revised 10/10 |

The comparison is provided as `retrieval-comparison.json`, with exact query, expected passage, before/after IDs and a retrieved excerpt. It compares lexical-only retrieval and includes two newly added sources. It is NOT a held-out benchmark, a hybrid-model accuracy score, or a legal correctness measurement.

## Blocked or unverified

- Full backend MongoDB integration was attempted. MongoMemoryServer exited with code 100 before application assertions. The focused security/concurrency suite uses test doubles and does not replace database integration testing.
- No live LLM generation/review was run. Provider configuration, JSON compliance on real outputs, answer correctness, semantic entailment, actual latency and API cost must be checked locally.
- Fresh embedding/cross-encoder inference was not run. Tests exercise the real text corpus, storage identity, algorithm behavior and injected retrieval/provider adapters. They do not establish the effectiveness of the pretrained models or prompt-injection resistance.
- Real-browser authentication and UI end-to-end testing were not completed. Frontend build tests are not browser behavior tests.
- No expert legal review, current-law audit, full dependency-security audit or production load test was performed.

The corpus includes imperfect extraction and incomplete law coverage. Exact quote matching checks provenance, not whether a legal claim follows from the quote. Model judgments can still be wrong; the UI intentionally does not label answers as verified.

Python requirements use version ranges, not a reproducible lock for every supported platform. Use the Node lockfiles with npm ci, and freeze your validated Python environment after local testing. Rebuilding or changing embedding models requires a matched corpus/index and updated evaluation.
