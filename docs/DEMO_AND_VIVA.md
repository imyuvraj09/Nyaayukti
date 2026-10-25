# Demonstration and interview preparation

## Five-minute demonstration

1. Explain the problem and scope: legal-information retrieval with inspectable evidence, not an autonomous lawyer.
2. Ask a definition question supported by the corpus. Open a citation and compare the answer with the passage.
3. Ask a factual scenario and show how the answer distinguishes alleged facts, conditions and missing information.
4. Ask a follow-up to demonstrate conversation context, then start a new chat to show separation.
5. Ask about a missing statute or case-law requirement. Show that limitations are visible rather than claiming complete coverage.

Prepare the model cache, MongoDB and your provider quota before presenting. Keep a clearly labeled recorded demo as a backup; never present recorded or cached output as a live result.

## Be ready to explain

Why combine BM25 and embeddings? What does reciprocal-rank fusion do? Why is a reranker score not confidence? What happens when a model invents a citation? Why does citation existence differ from citation support? How do you prevent another user reading a chat? What happens when two requests arrive together? Why were Docker and experimental pipelines removed? What would require a database transaction or distributed queue at larger scale?

Use concrete code and test examples in your answers. Do not claim you trained the pretrained embedding model or developed a foundation model. Distinguish your engineering work from third-party libraries and AI assistance.

## Evidence for your report

Build a human-reviewed benchmark across statutes and question types. Record retrieval recall/MRR separately from answer correctness, citation support and completeness. Measure warm and cold latency separately, with model/provider/settings and hardware recorded. Keep a held-out test set and report failures. The evaluation utility exports a review sheet, but a qualified reviewer must supply the legal judgments.

Describe this as an implemented, evaluated prototype. A credible account of tradeoffs and limitations is more useful in an interview than unsupported accuracy claims.
