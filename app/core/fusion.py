from typing import List, Dict, Any
from app.config import settings


def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]],
    sparse_results: List[Dict[str, Any]],
    k: int = None,
) -> List[Dict[str, Any]]:
    """
    dense_results / sparse_results: list of {"faq_id": str, "score": float},
    already sorted best-first.
    Returns fused list of {"faq_id": str, "rrf_score": float}, sorted best-first.
    """
    k = k or settings.rrf_k
    fused_scores: Dict[str, float] = {}

    for rank, item in enumerate(dense_results):
        fused_scores[item["faq_id"]] = fused_scores.get(item["faq_id"], 0.0) + 1.0 / (
            k + rank + 1
        )

    for rank, item in enumerate(sparse_results):
        fused_scores[item["faq_id"]] = fused_scores.get(item["faq_id"], 0.0) + 1.0 / (
            k + rank + 1
        )

    fused = [
        {"faq_id": faq_id, "rrf_score": score}
        for faq_id, score in fused_scores.items()
    ]
    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused
