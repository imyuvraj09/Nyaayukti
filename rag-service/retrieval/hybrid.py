"""BM25 + dense retrieval, reciprocal-rank fusion, and optional reranking.

Scores rank passages; they are not calibrated probabilities of legal correctness.
The JSONL corpus is the canonical passage source. We do not guess section titles.
"""

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from schemas.retrieval import AdvancedRetrievalResult, RerankedChunk, RetrievedChunk
from utils.config import settings

STOPWORDS = set(
    "a an the is are was were of to in on for and or with this that i my me it have has had do does can would could should what which how explain under please".split()
)


def tokens(text):
    return [t for t in re.findall(r"\w+", text.lower()) if t not in STOPWORDS]


def reciprocal_rank_fusion(rankings, k=60):
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] += 1 / (k + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))


class HybridRetriever:
    def __init__(self, records=None, dense=None, reranker=None):
        self.corpus_fingerprint = None
        if records is None:
            path = Path(__file__).resolve().parents[1] / "data/processed/legal_chunks.jsonl"
            self.corpus_fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            with path.open(encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle if line.strip()]
            supplement = path.with_name("supplemental_chunks.jsonl")
            if supplement.exists():
                self.corpus_fingerprint += (
                    ":" + hashlib.sha256(supplement.read_bytes()).hexdigest()[:16]
                )
                with supplement.open(encoding="utf-8") as handle:
                    records.extend(json.loads(line) for line in handle if line.strip())
        self.records = {r["chunk_id"]: r for r in records}
        if not self.records:
            raise ValueError("The legal corpus is empty. Run ingestion and chunking first.")
        self.catalog = sorted({r["document_name"] for r in self.records.values()})
        self.aliases = {}
        for title in self.catalog:
            words = [w for w in re.findall(r"[a-z]+", title.lower()) if w != "the"]
            base = " ".join(words)
            self.aliases[base] = title
            if "constitution" in words:
                self.aliases["constitution"] = title
            acronym = "".join(w[0] for w in words if w not in {"the", "of", "and"})
            if len(acronym) >= 3:
                self.aliases[acronym] = title
        alias_path = Path(__file__).resolve().parents[1] / "data/act_aliases.json"
        if alias_path.exists():
            for alias, title in json.loads(alias_path.read_text(encoding="utf-8")).items():
                if title in self.catalog:
                    self.aliases[alias] = title
        self.dense, self.reranker = dense, reranker
        self.postings = defaultdict(dict)
        self.lengths = {}
        self.passage_terms = {}
        self.definition_terms = {}
        self.order = defaultdict(list)
        for key, record in self.records.items():
            terms = tokens(record.get("document_type", "") + " " + record["text"])
            self.lengths[key] = len(terms)
            self.passage_terms[key] = " ".join(tokens(record["text"]))
            self.definition_terms[key] = [
                set(tokens(term))
                for term in re.findall(
                    r'["“]([^"”]{3,100})["”]\s+(?:means|includes)', record["text"], re.I
                )
            ]
            for term, count in Counter(terms).items():
                self.postings[term][key] = count
            self.order[record["document_id"]].append(key)
        for keys in self.order.values():
            keys.sort(key=lambda key: self.records[key]["chunk_index"])
        self.neighbours = {}
        for keys in self.order.values():
            for i, key in enumerate(keys):
                self.neighbours[key] = keys[max(0, i - 1) : i] + keys[i + 1 : i + 2]
        self.average_length = max(1, sum(self.lengths.values()) / len(self.lengths))

    def detected_authorities(self, query):
        normal = " ".join(re.findall(r"[a-z]+", query.lower()))
        return {
            title
            for alias, title in self.aliases.items()
            if re.search(r"\b" + re.escape(alias) + r"\b", normal)
        }

    def strict_document_scope(self, query):
        detected = self.detected_authorities(query)
        if not detected:
            return set()
        if re.search(r"\b(?:only|strictly|exclusively)\b", query, re.I):
            return detected
        if re.search(r"\bunder\s+(?:the\s+)?([a-z\s]+)\s+only\b", query, re.I):
            return detected
        return set()

    def document_scope(self, query):
        return self.detected_authorities(query)

    def exact_provisions(self, query):
        # Only use anchored provision starts in source text, never historical
        # inferred metadata or incidental cross-references to another Act.
        scope = self.detected_authorities(query)
        numbers = re.findall(r"\b(?:sections?|articles?|sec\.?|s\.)\s*(\d+[A-Za-z]?)", query, re.I)
        if len(scope) != 1 or not numbers:
            return []
        # Constitution schedules enumerate entries using the same numbering as
        # Articles. Without structural metadata, text search is safer than claiming
        # a schedule entry is an exact Article hit.
        if re.search(r"\barticles?\b", query, re.I):
            return []
        matches = []
        lengths = {}
        for key, record in self.records.items():
            if record["document_name"] not in scope:
                continue
            for number in numbers:
                pattern = r"(?:^|\n)\s*" + re.escape(number) + r"\s*[.．]\s*(?:\(|[A-Z])"
                match = re.search(pattern, record["text"])
                if match:
                    tail = record["text"][match.start() :]
                    body = re.sub(r"^\s*" + re.escape(number) + r"\s*[.．]\s*", "", tail)
                    if re.match(
                        r"(?:Subs?\.|Ins\.|Omitted|Clause .*omitted|Sub-sections .*omitted)",
                        body,
                        re.I,
                    ):
                        continue
                    # Contents lists and schedules often reuse provision numbers.
                    # Prefer a subclause or operative text before the next numbered entry.
                    first_entry = re.split(r"\n\s*\d+[A-Z]?\s*\.", body, maxsplit=1)[0]
                    if not (
                        body.startswith("(")
                        or re.search(r"\b(?:shall|Whoever|means)\b", first_entry[:1600])
                    ):
                        continue
                    lengths[key] = len(record["text"]) - match.start()
                    matches.append(key)
                    break
        return sorted(matches, key=lambda key: -lengths[key])

    def lexical(self, query, limit):
        strict_scope = self.strict_document_scope(query)
        signals = self.detected_authorities(query)
        # Titles select documents, not every paragraph inside those documents.
        term_query = query.lower()
        for alias in sorted(self.aliases, key=len, reverse=True):
            term_query = re.sub(r"\b" + re.escape(alias) + r"\b", " ", term_query)
        terms = tokens(term_query)
        scores = defaultdict(float)
        for term in set(terms):
            posting = self.postings.get(term, {})
            idf = math.log(1 + (len(self.records) - len(posting) + 0.5) / (len(posting) + 0.5))
            for key, frequency in posting.items():
                doc_name = self.records[key]["document_name"]
                if strict_scope and doc_name not in strict_scope:
                    continue
                length = self.lengths[key] / self.average_length
                score = idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * length))
                if signals and doc_name in signals:
                    score *= 1.35
                scores[key] += score
        # Phrase continuity helps distinguish a definition from incidental mentions.
        phrases = {" ".join(terms[i : i + 2]) for i in range(len(terms) - 1)}
        for key in scores:
            text = self.passage_terms[key]
            scores[key] += sum(1.5 for phrase in phrases if phrase in text)
            for definition_terms in self.definition_terms[key]:
                if definition_terms and definition_terms.issubset(terms):
                    scores[key] += 12
            if signals and self.records[key]["document_name"] in signals:
                scores[key] += 3.0
        return sorted(scores, key=lambda key: (-scores[key], key))[:limit]

    def passage(self, key, score=0):
        record = self.records[key]
        return RetrievedChunk(
            chunk_id=key,
            document_name=record["document_name"],
            document_type=record.get("document_type", "Statute"),
            source_filename=record.get("source_filename", ""),
            page_numbers=record.get("page_numbers", []),
            text=record["text"],
            relevance_score=score,
            metadata={
                "source_url": record.get("source_url"),
                "source_sha256": record.get("source_sha256"),
                "retrieved_at": record.get("retrieved_at"),
                "document_id": record["document_id"],
                "chunk_index": record["chunk_index"],
                "provision_metadata_verified": False,
            },
        )

    def with_continuation(self, chunk):
        """Expose forward context across extraction noise, preserving constituent IDs."""
        record = self.records[chunk.chunk_id]
        order = self.order[record["document_id"]]
        index = order.index(chunk.chunk_id)
        keys = order[index : index + 4]
        text = chunk.text
        pages = list(chunk.page_numbers)
        for key in keys[1:]:
            following = self.records[key]
            addition = following["text"]
            # Remove only exact character overlap; never drop a supposed exception.
            overlap = next(
                (
                    n
                    for n in range(min(len(text), len(addition), 400), 19, -1)
                    if text.endswith(addition[:n])
                ),
                0,
            )
            text += "\n" + addition[overlap:]
            pages.extend(following.get("page_numbers", []))
        return chunk.model_copy(
            update={
                "text": text,
                "page_numbers": sorted(set(pages)),
                "metadata": {**chunk.metadata, "constituent_chunk_ids": keys},
            }
        )

    def retrieve(self, query, request_id=None):
        limit = settings.INITIAL_RETRIEVAL_K
        lexical = self.lexical(query, limit)
        exact = self.exact_provisions(query)
        strict_scope = self.strict_document_scope(query)
        signals = self.detected_authorities(query)
        dense_count = 0
        dense_scores = {}
        rankings = [lexical]
        if settings.RETRIEVAL_MODE == "hybrid":
            if self.dense is None:
                from retrieval.similarity_search import SimilaritySearchService

                self.dense = SimilaritySearchService()
            found = self.dense.search(query, top_k=limit).results
            if not found:
                raise ValueError(
                    "Dense collection is empty. Check VECTOR_COLLECTION_NAME or rebuild the index."
                )
            dense_count = len(found)
            dense_scores = {
                r.chunk_id: r.relevance_score for r in found if r.chunk_id in self.records
            }
            if not dense_scores:
                raise ValueError("Dense index and passage corpus do not match; rebuild the index.")
            if strict_scope:
                dense_scores = {
                    key: score
                    for key, score in dense_scores.items()
                    if self.records[key]["document_name"] in strict_scope
                }
            elif signals:
                dense_scores = {
                    key: (score * 1.25 if self.records[key]["document_name"] in signals else score)
                    for key, score in dense_scores.items()
                }
            rankings.append(list(dense_scores))
        elif settings.RETRIEVAL_MODE != "lexical":
            raise ValueError("RETRIEVAL_MODE must be hybrid or lexical")
        keys = list(dict.fromkeys(exact + lexical[:3] + reciprocal_rank_fusion(rankings)))[:limit]
        candidates = [self.passage(key, dense_scores.get(key, 0)) for key in keys]
        if settings.ENABLE_RERANKER:
            if self.reranker is None:
                from retrieval.reranker import LegalReranker

                self.reranker = LegalReranker()
            try:
                ranked = self.reranker.rerank(query, candidates)
            except Exception as rerank_err:
                ranked = [(c, float(c.relevance_score or 0.0)) for c in candidates]
        else:
            ranked = [(c, 0.0) for c in candidates]
        # A requested provision is a retrieval lead, not a verified conclusion.
        # Keep its literal text even when semantic scores prefer generic passages.
        exact_set = set(exact)
        positions = {key: i for i, key in enumerate(exact)}
        ranked.sort(key=lambda item: positions.get(item[0].chunk_id, len(exact)))
        selected = ranked[: settings.FINAL_RETRIEVAL_K]
        if exact:
            selected = [
                (self.with_continuation(c) if c.chunk_id in exact_set else c, score)
                for c, score in selected
            ]

        # Keep direct matches first. Adjacent chunks retain provenance and may carry
        # the continuation/exception; never label them as independently relevant.
        expanded = list(selected)
        used = {c.chunk_id for c, _ in selected}
        for chunk, _ in selected[:3]:
            for key in self.neighbours.get(chunk.chunk_id, []):
                if key not in used:
                    neighbour = self.passage(key)
                    neighbour.metadata["adjacent_to"] = chunk.chunk_id
                    clean_start = neighbour.text.lstrip()
                    if re.match(
                        r"^(?:Provided|Exception|Explanation|Saving|Notwithstanding|\(\d+\))",
                        clean_start,
                        re.I,
                    ):
                        neighbour.metadata["is_exception_or_continuation"] = True
                    expanded.append((neighbour, 0.0))
                    used.add(key)
        results = [
            RerankedChunk(
                rank=i + 1,
                chunk_id=c.chunk_id,
                document_name=c.document_name,
                document_type=c.document_type,
                source_filename=c.source_filename,
                page_numbers=c.page_numbers,
                text=c.text,
                similarity_score=c.relevance_score,
                reranker_score=score,
                metadata=c.metadata,
            )
            for i, (c, score) in enumerate(expanded)
        ]
        return AdvancedRetrievalResult(
            original_query=query,
            normalized_query=query,
            initial_k=limit,
            final_k=settings.FINAL_RETRIEVAL_K,
            initial_candidates_count=len(candidates),
            filtered_candidates_count=len(ranked),
            final_results_count=len(results),
            results=results,
            debug_telemetry={
                "mode": settings.RETRIEVAL_MODE,
                "corpus_count": len(self.records),
                "lexical_candidates": len(lexical),
                "dense_candidates": dense_count,
                "exact_provision_candidates": len(exact),
                "fused_candidates": len(candidates),
                "reranked_candidates": len(ranked),
                "direct_selected": len(selected),
                "adjacent_selected": len(expanded) - len(selected),
                "reranker": settings.ENABLE_RERANKER,
            },
        )
