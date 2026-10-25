> Historical notes from the supplied project. See [FINAL_REVIEW.md](FINAL_REVIEW.md) for this revision.

# Code review and changes

## Resolved findings

- The configured vector collection name differed from the collection bundled on disk. Configuration now uses the existing populated collection.
- Several overlapping retrieval/answer pipelines and scenario-specific deterministic logic made behavior difficult to explain. The active path now uses generic BM25, dense retrieval, rank fusion, optional reranking, bounded generation and review.
- Historical section guesses and UI badges could imply verified legal support. Source cards now show document, passage and PDF page; answer quality is not represented as guaranteed.
- Grouped citations and repeated source IDs across messages could link incorrectly. Citation normalization and message-scoped anchors fix this.
- A custom Markdown renderer and multiple answer renderers duplicated logic. A maintained Markdown parser with raw HTML disabled now serves one response path.
- Account-recovery JSX was returned from a React effect rather than the rendered component. Routing now renders recovery content normally.
- Stale chat responses could populate another session. Active-session checks and send-time guards protect the selected conversation.
- Simultaneous requests could race over chat history or load duplicate Python model instances. Local concurrency guards and locked lazy initialization bound those cases.
- The backend timeout was cleared before body consumption completed. It now covers response parsing too. Busy-service errors retain their meaning.
- An actual credential was present in the supplied environment example. It was removed. **Revoke that exposed credential before sharing or using the project.** Removing it from this ZIP does not revoke it or erase prior copies.
- Root Docker/deployment configuration, duplicate research pipelines, stale experiments and unsupported reports were removed. See REMOVALS.md.

## Deliberately retained

Original account ownership controls, password/session handling, useful service boundaries, source PDFs, canonical passage data, the matching vector index, and focused tests. The original contributor attribution remains.

## Remaining work before a public release

Run MongoDB integration tests on a compatible host and exercise signup, login, recovery, persistence and deletion in a real browser. Test a configured provider against a human-labeled set of varied questions, including missing evidence and adversarial prompts. Review dependency advisories and pin/test a reproducible Python environment for your target machine. Audit legal data provenance, licensing, amendments and jurisdiction coverage. Add distributed coordination only if multiple workers are actually needed.

This review simplifies the project and fixes identified defects; it is not a claim that every possible issue has been eliminated. No model-generated answer or code review guarantees a prize, employment, or legal correctness.

## Follow-up: false empty-evidence response

Removed the uncalibrated minimum reranker score introduced in the initial refactor. Scores now order candidates rather than delete all evidence. Unsupported claims still require qualification or abstention during generation/review. Added tests for low scores on generic data, the reported theft question against the bundled corpus, and genuinely absent lexical matches. This change does not establish live-model answer accuracy.

## Current version

Version 4 replaces the earlier retrieval orchestration and mandatory answer review. Read UPGRADE_V4.md and VALIDATION.md for current behavior and actual test results.
