"""
Nyaayukti RAG Service — Application configuration.

Uses Pydantic Settings for type-safe environment variable management.
Local configuration. Secrets are loaded from rag-service/.env.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "Nyaayukti RAG Service"
    APP_VERSION: str = "4.0.0"
    ENVIRONMENT: str = "development"

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Chunking ───────────────────────────────────────
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200

    # ── Embeddings & Vector Store ──────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_BATCH_SIZE: int = 32
    VECTOR_DB_PATH: str = "vector_store/chroma_db"
    VECTOR_COLLECTION_NAME: str = "nyayasetu_legal_documents"

    # ── Advanced Retrieval & Reranking ─────────────────
    INITIAL_RETRIEVAL_K: int = 20
    FINAL_RETRIEVAL_K: int = 5
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANKER_BATCH_SIZE: int = 16

    # ── Centralized RAG Architecture Thresholds & Guardrails ────
    MAX_RETRIEVAL_ATTEMPTS: int = Field(default=2, ge=1, le=3)
    MAX_CONTEXT_CHUNKS: int = Field(default=12, ge=4, le=16)
    # ── Context bounds ──────────

    RAG_SERVICE_TOKEN: str = ""
    MAX_CONCURRENT_QUERIES: int = Field(default=2, ge=1, le=8)
    LLM_MAX_ATTEMPTS: int = Field(default=1, ge=1, le=2)
    RETRIEVAL_MODE: str = "hybrid"
    ENABLE_RERANKER: bool = True
    DEBUG_RETRIEVAL: bool = False
    MAX_SEARCH_QUERIES: int = Field(default=12, ge=4, le=16)
    MAX_PLANNED_ISSUES: int = Field(default=8, ge=1, le=12)

    # ── LLM & Answer Generation (Google Gemini Primary) ─────────
    LLM_PROVIDER: str = "gemini"  # gemini or openai
    LLM_MODEL: str = ""
    GEMINI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = None
    LLM_TEMPERATURE: float = 0.1
    LLM_SEND_TEMPERATURE: bool = False
    LLM_MAX_TOKENS: int = 3500
    LLM_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0, le=30)
    MAX_CONTEXT_CHARS: int = Field(default=28000, ge=1000, le=50000)

    # ── Provider key resolution ────────────────

    @property
    def effective_gemini_api_key(self) -> str | None:
        """Resolve Gemini API key from GEMINI_API_KEY, GOOGLE_API_KEY, or LLM_API_KEY."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or self.LLM_API_KEY

    @property
    def effective_openai_api_key(self) -> str | None:
        """Resolve OpenAI API key from OPENAI_API_KEY or LLM_API_KEY."""
        return self.OPENAI_API_KEY or self.LLM_API_KEY


# Singleton instance — import this everywhere
settings = Settings()
