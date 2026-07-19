import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # LLM
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "mistral-small-latest")

    # ChromaDB
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    chroma_collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "safex_faq")

    # Embedding model
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5"
    )

    # Reranker
    reranker_model_name: str = os.getenv(
        "RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    cache_similarity_threshold: float = float(
        os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.95")
    )

    # Confidence gate
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))

    # Retrieval
    dense_top_k: int = int(os.getenv("DENSE_TOP_K", "10"))
    sparse_top_k: int = int(os.getenv("SPARSE_TOP_K", "10"))
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    rerank_top_n: int = int(os.getenv("RERANK_TOP_N", "5"))

    # Dataset path
    faq_dataset_path: str = os.getenv("FAQ_DATASET_PATH", "data/safex_faq_dataset.json")

    # Database
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "data/safex_bot.db")

    # OpenWA
    openwa_api_url: str = os.getenv("OPENWA_API_URL", "http://localhost:2785")
    openwa_api_key: str = os.getenv("OPENWA_API_KEY", "")
    openwa_session_id: str = os.getenv("OPENWA_SESSION_ID", "default")


settings = Settings()
