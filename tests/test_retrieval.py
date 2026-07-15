import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.core.fusion import reciprocal_rank_fusion
from app.core.confidence import apply_confidence_gate


def test_rrf_fusion_merges_and_ranks():
    dense = [{"faq_id": "A", "score": 0.9}, {"faq_id": "B", "score": 0.8}]
    sparse = [{"faq_id": "B", "score": 5.0}, {"faq_id": "C", "score": 3.0}]

    fused = reciprocal_rank_fusion(dense, sparse, k=60)
    fused_ids = [item["faq_id"] for item in fused]

    # B appears in both lists so it should outrank items appearing in only one
    assert fused_ids[0] == "B"
    assert set(fused_ids) == {"A", "B", "C"}


def test_rrf_fusion_handles_empty_lists():
    fused = reciprocal_rank_fusion([], [])
    assert fused == []


def test_confidence_gate_empty_candidates():
    best, confidence, is_confident = apply_confidence_gate([])
    assert best == {}
    assert confidence == 0.0
    assert is_confident is False


def test_confidence_gate_high_score_is_confident():
    candidates = [
        {"faq_id": "CON001", "answer": "test", "category": "contact", "rerank_score": 5.0}
    ]
    best, confidence, is_confident = apply_confidence_gate(candidates)
    assert is_confident is True
    assert confidence > 0.9


def test_confidence_gate_low_score_not_confident():
    candidates = [
        {"faq_id": "CON001", "answer": "test", "category": "contact", "rerank_score": -5.0}
    ]
    best, confidence, is_confident = apply_confidence_gate(candidates)
    assert is_confident is False
    assert confidence < 0.1
