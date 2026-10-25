"""Measured production evaluation. Source retrieval and legal accuracy are distinct.

Use --allow-llm-spend to explicitly enable live generation. Without it, only
retrieval is evaluated and generation-dependent fields are null.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "rag-service")]


def retrieval_metrics(retrieved, expected, k=5, out_of_scope=False):
    top = list(dict.fromkeys(retrieved))[:k]
    gold = set(expected)
    if out_of_scope:
        return {
            "recall_at_k": None,
            "precision_at_k": None,
            "mrr": None,
            "rejection_correct": len(top) == 0,
        }
    if not gold:
        return {
            "recall_at_k": None,
            "precision_at_k": None,
            "mrr": None,
            "rejection_correct": None,
        }
    hits = [x in gold for x in top]
    return {
        "recall_at_k": len(set(top) & gold) / len(gold),
        "precision_at_k": sum(hits) / len(top) if top else 0.0,
        "mrr": next((1.0 / (i + 1) for i, hit in enumerate(hits) if hit), 0.0),
        "rejection_correct": None,
    }


def evaluate(cases, pipeline):
    rows = []
    for item in cases:
        start = time.perf_counter()
        query = item.get("question") or item.get("query")
        if not query:
            raise ValueError("Every benchmark item needs question or query")
        try:
            result = pipeline.query(
                query, conversation_history=item.get("conversation_history", [])
            )
            # Prefer exact evidence labels; fall back to explicitly identified document-level evaluation.
            if item.get("expected_chunk_ids"):
                retrieved = [s.chunk_id for s in result.sources]
                expected = item["expected_chunk_ids"]
                level = "chunk"
            else:
                retrieved = [s.document_name for s in result.sources]
                expected = item.get("expected_statutes", [])
                level = "document_exact_name"
            metrics = retrieval_metrics(
                retrieved, expected, out_of_scope=item.get("category") == "out_of_scope"
            )
            rows.append(
                {
                    "id": item.get("id"),
                    "question": query,
                    "answer": result.answer,
                    "metrics": metrics,
                    "retrieval_label_level": level,
                    "sources": [s.model_dump() for s in result.sources],
                    "latency_seconds": time.perf_counter() - start,
                    "generation_status": result.generation_status,
                    "claim_accuracy": None,
                    "human_review_required": True,
                    "model": result.model_metadata,
                    "error": None,
                }
            )
        except Exception as err:
            rows.append(
                {
                    "id": item.get("id"),
                    "question": query,
                    "answer": "",
                    "sources": [],
                    "metrics": {},
                    "latency_seconds": time.perf_counter() - start,
                    "error": type(err).__name__,
                    "human_review_required": True,
                }
            )

    def mean(key):
        values = [r["metrics"].get(key) for r in rows if r["metrics"].get(key) is not None]
        return {"mean": sum(values) / len(values) if values else None, "n": len(values)}

    return {
        "scope": "Current production pipeline; source retrieval is not legal-answer accuracy.",
        "n": len(rows),
        "failures": sum(bool(r["error"]) for r in rows),
        "aggregate": {
            k: mean(k) for k in ("recall_at_k", "precision_at_k", "mrr", "rejection_correct")
        },
        "claim_accuracy": None,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output", default="results/current_production.json")
    parser.add_argument("--allow-llm-spend", action="store_true")
    args = parser.parse_args()
    from rag.conversation_pipeline import ConversationPipeline

    pipeline = ConversationPipeline()
    if not args.allow_llm_spend:
        pipeline.llm_provider.is_configured = lambda: False
    elif not pipeline.llm_provider.is_configured():
        parser.error(
            "Live evaluation requires configured provider credentials and an explicit model"
        )
    payload = json.loads(Path(args.benchmark).read_text())
    cases = payload if isinstance(payload, list) else payload.get("queries", [])
    if not cases:
        parser.error("Benchmark contains no queries")
    report = evaluate(cases, pipeline)
    report["live_generation_requested"] = args.allow_llm_spend
    report["latency_scope"] = "Full production call, including generation when enabled"
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    with path.with_suffix(".review.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "id",
                "question",
                "answer",
                "correctness_0_2",
                "citation_support_0_2",
                "completeness_0_2",
                "reviewer",
                "notes",
            ]
        )
        for row in report["rows"]:
            writer.writerow([row["id"], row["question"], row["answer"], "", "", "", "", ""])
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
