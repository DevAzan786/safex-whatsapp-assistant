import math
from typing import List, Dict, Any, Tuple

from app.config import settings


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def apply_confidence_gate(
    reranked_candidates: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], float, bool]:
    """
    reranked_candidates: output of Reranker.rerank(), sorted best-first.
    Returns (best_candidate_or_empty_dict, confidence_score, is_confident).
    """
    if not reranked_candidates:
        return {}, 0.0, False

    best = reranked_candidates[0]
    confidence = _sigmoid(best["rerank_score"])

    is_confident = confidence >= settings.confidence_threshold
    return best, confidence, is_confident


FALLBACK_ANSWER = (
    "I'm not fully sure I have the right answer for that. "
    "Let me connect you with a member of our team who can help — "
    "you can also reach us directly at contact@safexsolutions.com "
    "or +92 327 5781580."
)