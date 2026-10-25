"""Compare warm BM25 with the original ranking algorithm; no model/API calls."""

import json
import math
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag-service"))
from retrieval.hybrid import HybridRetriever, tokens


def reference_lexical(self, query, limit):
    scope = self.document_scope(query)
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
            if scope and self.records[key]["document_name"] not in scope:
                continue
            length = self.lengths[key] / self.average_length
            scores[key] += idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * length))
    # Phrase continuity helps distinguish a definition from incidental mentions.
    phrases = {" ".join(terms[i : i + 2]) for i in range(len(terms) - 1)}
    for key in scores:
        text = " ".join(tokens(self.records[key]["text"]))
        scores[key] += sum(1.5 for phrase in phrases if phrase in text)
        definitions = re.findall(
            r'["“]([^"”]{3,100})["”]\s+(?:means|includes)',
            self.records[key]["text"],
            re.I,
        )
        for term in definitions:
            definition_terms = tokens(term)
            if len(definition_terms) >= 1 and set(definition_terms).issubset(terms):
                scores[key] += 12
    return sorted(scores, key=lambda key: (-scores[key], key))[:limit]


QUERIES = [
    "BNS section 358 repeal savings",
    "consumer rights defective goods refund",
    "Information Technology Act section 43 damage computer",
    "Constitution article 20 conviction offence penalty",
    "Companies Act section 166 duties directors",
]


def main():
    retriever = HybridRetriever()
    measurements, rankings = {}, {}
    for name, search in [
        ("reference", lambda q: reference_lexical(retriever, q, 20)),
        ("current", lambda q: retriever.lexical(q, 20)),
    ]:
        elapsed, results = [], []
        for _ in range(5):
            for query in QUERIES:
                started = time.perf_counter()
                results.append(search(query))
                elapsed.append((time.perf_counter() - started) * 1000)
        measurements[name] = {"median_ms": statistics.median(elapsed), "samples": len(elapsed)}
        rankings[name] = results
    measurements["identical_rankings"] = rankings["reference"] == rankings["current"]
    print(json.dumps(measurements, indent=2))
    if not measurements["identical_rankings"]:
        raise SystemExit("Ranking regression")


if __name__ == "__main__":
    main()
