import json
import os
import string
from typing import List, Dict, Any

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.config import settings


def clean_tokenize(text: str) -> List[str]:
    """Lowercase text and strip punctuation to build clean tokens."""
    cleaned = text.translate(str.maketrans("", "", string.punctuation)).lower()
    return cleaned.split()


class HybridRetriever:
    def __init__(self):
        self.embedder = SentenceTransformer(settings.embedding_model_name)
        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self.bm25 = None
        self.bm25_corpus_ids: List[str] = []
        self.faq_lookup: Dict[str, Dict[str, Any]] = {}

        self._load_faq_lookup()
        self._build_bm25_index()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _load_faq_lookup(self):
        """Load the raw FAQ dataset for BM25 indexing and answer lookup."""
        if not os.path.exists(settings.faq_dataset_path):
            raise FileNotFoundError(
                f"FAQ dataset not found at {settings.faq_dataset_path}. "
                f"Place safex_faq_dataset.json in the data/ folder."
            )
        with open(settings.faq_dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for faq in data["faqs"]:
            self.faq_lookup[faq["id"]] = faq

    def _build_bm25_index(self):
        """Build an in-memory BM25 index over question + keywords text."""
        corpus_tokens = []
        for faq_id, faq in self.faq_lookup.items():
            text = faq["question"] + " " + " ".join(faq.get("keywords", []))
            corpus_tokens.append(clean_tokenize(text))
            self.bm25_corpus_ids.append(faq_id)

        self.bm25 = BM25Okapi(corpus_tokens)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def dense_search(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """Semantic search over ChromaDB. Returns list of {faq_id, score}."""
        k = k or settings.dense_top_k
        # BGE v1.5 requires prepended search query instructions
        instruction = "Represent this sentence for searching relevant passages: "
        query_embedding = self.embedder.encode(instruction + query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, self.collection.count() or 1),
        )

        hits = []
        if results["ids"] and results["ids"][0]:
            for faq_id, distance in zip(results["ids"][0], results["distances"][0]):
                # Chroma cosine distance -> similarity score (higher = better)
                similarity = 1 - distance
                hits.append({"faq_id": faq_id, "score": similarity})
        return hits

    def sparse_search(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """BM25 keyword search. Returns list of {faq_id, score}."""
        k = k or settings.sparse_top_k
        tokenized_query = clean_tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        scored = list(zip(self.bm25_corpus_ids, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        return [{"faq_id": fid, "score": float(s)} for fid, s in scored[:k] if s > 0]

    def get_faq(self, faq_id: str) -> Dict[str, Any]:
        return self.faq_lookup.get(faq_id, {})
