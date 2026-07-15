from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

from app.config import settings
from app.core.retrieval import HybridRetriever


class Reranker:
    def __init__(self):
        self.model = CrossEncoder(settings.reranker_model_name)

    def rerank(
        self,
        query: str,
        fused_candidates: List[Dict[str, Any]],
        retriever: HybridRetriever,
        top_n: int = None,
    ) -> List[Dict[str, Any]]:
        """
        fused_candidates: output of reciprocal_rank_fusion(), list of
        {"faq_id": str, "rrf_score": float}.
        Returns list of {"faq_id", "question", "answer", "category",
        "rerank_score"} sorted best-first, trimmed to top_n.
        """
        top_n = top_n or settings.rerank_top_n
        shortlist = fused_candidates[: max(top_n * 2, top_n)]  # headroom before cutting

        pairs = []
        faq_details = []
        for candidate in shortlist:
            faq = retriever.get_faq(candidate["faq_id"])
            if not faq:
                continue
            keywords_str = " ".join(faq.get("keywords", []))
            passage = f"{faq['question']} {keywords_str} {faq['answer']}"
            pairs.append((query, passage))
            faq_details.append(faq)

        if not pairs:
            return []

        scores = self.model.predict(pairs)

        reranked = [
            {
                "faq_id": faq["id"],
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq["category"],
                "rerank_score": float(score),
            }
            for faq, score in zip(faq_details, scores)
        ]
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_n]