from typing import Dict, Any

from app.core.retrieval import HybridRetriever
from app.core.fusion import reciprocal_rank_fusion
from app.core.reranker import Reranker
from app.core.confidence import apply_confidence_gate, FALLBACK_ANSWER
from app.core.query_rewrite import rewrite_query
from app.core.cache import get_cached_response, set_cached_response


class FAQPipeline:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.reranker = Reranker()

    def answer(self, question: str, use_cache: bool = True) -> Dict[str, Any]:
        # 1. Cache check
        if use_cache:
            cached = get_cached_response(question)
            if cached is not None:
                cached["cached"] = True
                return cached

        # 2. Query rewriting (helps short/ambiguous WhatsApp messages)
        search_query = rewrite_query(question)

        # 3. Hybrid retrieval
        dense_hits = self.retriever.dense_search(search_query)
        sparse_hits = self.retriever.sparse_search(search_query)

        # 4. RRF fusion
        fused = reciprocal_rank_fusion(dense_hits, sparse_hits)

        if not fused:
            result = {
                "answer": FALLBACK_ANSWER,
                "confidence": 0.0,
                "matched_faq_id": None,
                "category": None,
                "is_confident": False,
                "cached": False,
            }
            return result

        # 5. Cross-encoder rerank
        reranked = self.reranker.rerank(search_query, fused, self.retriever)

        # 6. Confidence gate
        best, confidence, is_confident = apply_confidence_gate(reranked)

        if is_confident and best:
            result = {
                "answer": best["answer"],
                "confidence": round(confidence, 4),
                "matched_faq_id": best["faq_id"],
                "category": best["category"],
                "is_confident": True,
                "cached": False,
            }
        else:
            result = {
                "answer": FALLBACK_ANSWER,
                "confidence": round(confidence, 4),
                "matched_faq_id": best.get("faq_id") if best else None,
                "category": best.get("category") if best else None,
                "is_confident": False,
                "cached": False,
            }

        # 7. Cache write (cache the decision, including low-confidence ones,
        #    so identical repeat queries don't redo the full pipeline)
        if use_cache:
            set_cached_response(question, result)

        return result


# Singleton instance — loading the embedder/cross-encoder/ChromaDB/BM25
# index is expensive, so this should be created once at app startup, not
# per-request. See app/main.py.
_pipeline_instance = None


def get_pipeline() -> FAQPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = FAQPipeline()
    return _pipeline_instance