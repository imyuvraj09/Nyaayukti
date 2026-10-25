"""
Nyaayukti RAG Service — FastAPI application entry point.

Start with:
    uvicorn main:app --reload --port 8000
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.body_limit import BodyLimitMiddleware
from api.routes import router as api_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.config import settings
from utils.logger import get_logger, setup_logging

# ── Logging ──────────────────────────────────────────────────────
setup_logging(level="INFO")
logger = get_logger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — runs on startup and shutdown."""
    if not settings.RAG_SERVICE_TOKEN:
        raise RuntimeError("Set RAG_SERVICE_TOKEN before starting the service")
    if settings.ENVIRONMENT == "production" and len(settings.RAG_SERVICE_TOKEN) < 32:
        raise RuntimeError("Production service tokens must contain at least 32 characters")
    logger.info("=" * 60)
    logger.info("  %s  v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("  Environment : %s", settings.ENVIRONMENT)
    logger.info("  Server      : http://%s:%s", settings.HOST, settings.PORT)
    logger.info("  Docs        : http://%s:%s/docs", settings.HOST, settings.PORT)
    logger.info("=" * 60)
    yield
    from api import routes

    if routes._RAG_PIPELINE is not None:
        clients = getattr(routes._RAG_PIPELINE.llm_provider, "_clients", None)
        if clients is not None:
            clients.close()
    logger.info("%s shutting down.", settings.APP_NAME)


# ── FastAPI application ─────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=("AI-powered Retrieval-Augmented Generation service for Indian legal knowledge"),
    lifespan=lifespan,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (frontend)
        "http://localhost:3000",  # Express backend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BodyLimitMiddleware)

# ── Routes ───────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint — confirms the service is running."""
    return {
        "message": "Nyaayukti RAG Service is running",
        "docs": "/docs",
    }
