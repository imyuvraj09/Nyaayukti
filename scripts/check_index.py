"""Check corpus/index identity without loading an embedding model or contacting an LLM."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rag-service"))
from utils.config import settings
from vectorstore.chroma_store import ChromaStore

base = ROOT / "rag-service/data/processed/legal_chunks.jsonl"
ids = {
    json.loads(line)["chunk_id"]
    for line in base.read_text(encoding="utf-8").splitlines()
    if line.strip()
}
try:
    store = ChromaStore()
    stored = store.get_existing_ids()
    print(
        json.dumps(
            {
                "collection": settings.VECTOR_COLLECTION_NAME,
                "base_passages": len(ids),
                "vectors": len(stored),
                "missing_ids": len(ids - stored),
                "unexpected_ids": len(stored - ids),
            },
            indent=2,
        )
    )
    if ids != stored:
        raise SystemExit(
            "Corpus and vectors differ. Rebuild the matched pair before using hybrid retrieval."
        )
except Exception as err:
    raise SystemExit(
        f"Index check failed ({type(err).__name__}). Check vector path and collection name."
    ) from None
