# Corpus and evidence limits

The delivered statute corpus contains 6,545 passages from 14 documents. It includes the Constitution, BNS, BNSS, BSA, Companies Act, GST material, Insolvency and Bankruptcy Code, Motor Vehicles Act, Consumer Protection Act, IT Act, RTI Act, POCSO, Right to Education Act and workplace sexual-harassment legislation.

The documents and passage text were retained from the uploaded project; this review does not independently certify their current legal status or extraction accuracy. PDF page numbers are file pages, not necessarily printed Gazette page labels. OCR, headers, tables and section boundaries can affect retrieval.

The Indian Contract Act is not in this bundled set. Questions about repairers' liens, for example, require additional sources and must not receive an invented conclusion. State law, amendments, specialist rules and case-law coverage are incomplete. The removed curated case-law summaries are not used as authoritative judgments.

Canonical passages: `rag-service/data/processed/legal_chunks.jsonl`. Raw source PDFs: `rag-service/data/raw`. Chroma's statute collection has matching passage IDs. Treat the JSONL and index as a versioned pair.

Before adding documents, record their official source, retrieval date, version/effective date and applicable jurisdiction. Inspect extraction and chunk boundaries, rebuild embeddings, then measure retrieval on held-out questions. Do not label all extracted section metadata as verified without checking it against the original source.

## Version 4 additions

Three government-hosted commencement-notification passages are now loaded from supplemental_chunks.jsonl through the lexical branch. Total text passages: 6,548. Base vectors: 6,545. See UPGRADE_V4.md for provenance and limitations. The supplemental text does not require modifying the base vector index.
