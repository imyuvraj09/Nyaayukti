"""Inspect the actual pipeline locally. Live model calls require an explicit flag."""

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rag-service"))
parser = argparse.ArgumentParser()
parser.add_argument("question")
parser.add_argument(
    "--live-generation",
    action="store_true",
    help="Allow configured provider calls and charges",
)
parser.add_argument(
    "--lexical",
    action="store_true",
    help="Explicitly disable dense retrieval and reranking for a diagnostic",
)
parser.add_argument(
    "--show-evidence",
    action="store_true",
    help="Print question/plan/source text locally; may contain private information",
)
args = parser.parse_args()
from utils.config import settings

if args.lexical:
    settings.RETRIEVAL_MODE = "lexical"
    settings.ENABLE_RERANKER = False
settings.DEBUG_RETRIEVAL = args.show_evidence
from rag.conversation_pipeline import ConversationPipeline

pipeline = ConversationPipeline()
if not args.live_generation:
    pipeline.llm_provider.is_configured = lambda: False
result = pipeline.query(args.question, request_id=str(uuid4()))
meta = dict(result.retrieval_metadata)
if not args.show_evidence:
    meta.pop("issue_plan", None)
report = dict(
    request_id=result.request_id,
    generation_status=result.generation_status,
    validation_status=result.validation_status,
    retrieval=meta,
    model=result.model_metadata,
)
if args.show_evidence:
    report["answer"] = result.answer
    report["sources"] = [s.model_dump() for s in result.sources]
print(json.dumps(report, indent=2, ensure_ascii=False))
