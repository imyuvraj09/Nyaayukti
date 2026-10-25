"""
Cross-encoder reranker module for Nyaayukti Legal Assistant.

Provides lazy-loaded cross-encoder reranking using BAAI/bge-reranker-base.
Scores (query, chunk_text) pairs with full cross-attention for deep semantic alignment.
"""

import math
from typing import TYPE_CHECKING, Any, Optional

from embeddings.embedding_model import get_device
from schemas.retrieval import RetrievedChunk
from utils.config import settings
from utils.logger import get_logger

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = get_logger(__name__)

# Global singleton cache for the loaded CrossEncoder model
_RERANKER_INSTANCE: Optional["CrossEncoder"] = None


def sigmoid(x: float) -> float:
    """Map raw logit scores smoothly to [0.0, 1.0] ranking-score range (not a calibrated probability)."""
    try:
        return 1.0 / (1.0 + math.exp(-float(x)))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class LegalReranker:
    """Cross-encoder reranking service for candidate legal chunks."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.model_name = model_name or settings.RERANKER_MODEL
        self.device = device or get_device()
        self.batch_size = batch_size or settings.RERANKER_BATCH_SIZE

    def _load_model(self):
        """Lazily load and cache the CrossEncoder model instance."""
        global _RERANKER_INSTANCE
        if _RERANKER_INSTANCE is None:
            logger.info(
                "Loading CrossEncoder reranker '%s' on device '%s'...",
                self.model_name,
                self.device,
            )
            from sentence_transformers import CrossEncoder

            _RERANKER_INSTANCE = CrossEncoder(
                self.model_name,
                device=self.device,
                trust_remote_code=False,
            )
            logger.info("CrossEncoder reranker '%s' loaded successfully.", self.model_name)

        return _RERANKER_INSTANCE

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[tuple[RetrievedChunk, float]]:
        """Score and sort candidate chunks by cross-encoder relevance to query.

        Args:
            query: Normalized natural language query.
            candidates: List of RetrievedChunk objects to score.
            top_k: Optional limit on the number of returned chunks.

        Returns:
            List of (chunk, reranker_score) tuples sorted by reranker_score descending.
        """
        if not candidates:
            return []

        model = self._load_model()

        # Construct (query, passage) pairs for joint cross-attention
        pairs = [[query, chunk.text] for chunk in candidates]

        logger.info(
            "Reranking %d candidate pairs with batch size %d...",
            len(pairs),
            self.batch_size,
        )

        from torch.nn import Identity

        raw_scores = model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            activation_fn=Identity(),
        )

        # Normalize raw logit scores using sigmoid to [0.0, 1.0]
        scored_candidates: list[tuple[RetrievedChunk, float]] = []
        for chunk, raw_score in zip(candidates, raw_scores):
            normalized_score = sigmoid(float(raw_score))
            scored_candidates.append((chunk, normalized_score))

        # Sort descending by reranker score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if top_k is not None:
            scored_candidates = scored_candidates[:top_k]

        return scored_candidates

    def compute_scores(self, pairs: list[Any]) -> list[float]:
        """Compute cross-encoder scores directly on (query, text) pairs.

        Args:
            pairs: List of [query, text] pairs or tuples.

        Returns:
            List of float scores mapped to [0.0, 1.0] via sigmoid.
        """
        if not pairs:
            return []

        model = self._load_model()
        formatted_pairs = [[p[0], p[1]] for p in pairs]
        from torch.nn import Identity

        raw_scores = model.predict(
            formatted_pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            activation_fn=Identity(),
        )
        return [sigmoid(float(s)) for s in raw_scores]


# Factory helper
def get_legal_reranker(
    model_name: str | None = None,
    device: str | None = None,
) -> LegalReranker:
    """Factory helper returning a LegalReranker instance."""
    return LegalReranker(model_name=model_name, device=device)
