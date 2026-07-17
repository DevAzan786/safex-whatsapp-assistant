from fastapi import FastAPI
from app.api.routes import router
from app.core.pipeline import get_pipeline
from app.core.db import init_db

app = FastAPI(
    title="SafeX FAQ Knowledge Base",
    description=(
        "FAQ retrieval module for SafeX Solutions' WhatsApp Auto-Reply Bot "
        "(Group 10, Week 2). Hybrid retrieval (ChromaDB + BM25) with RRF "
        "fusion, cross-encoder reranking, and a confidence gate."
    ),
    version="1.0.0",
)

app.include_router(router)


@app.on_event("startup")
def load_pipeline_on_startup():
    """
    Eagerly load the embedding model, cross-encoder, ChromaDB collection,
    and BM25 index once at startup instead of on the first request, so the
    first real user query isn't slow. Also initialize the SQLite database tables.
    """
    init_db()
    get_pipeline()


@app.get("/")
def root():
    return {
        "service": "SafeX FAQ Knowledge Base",
        "status": "running",
        "docs": "/docs",
    }
