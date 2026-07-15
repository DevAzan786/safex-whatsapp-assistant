import sys
import os
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.retrieval import HybridRetriever
from app.core.fusion import reciprocal_rank_fusion

from app.core.pipeline import get_pipeline

# Each entry: (paraphrased user question, expected correct faq_id)
TEST_SET = [
    ("how much does it cost to build a website", "PRC001"),
    ("whats your email", "CON001"),
    ("can i call you", "CON002"),
    ("do u guys do social media marketing", "SVC006"),
    ("where is your office located", "CON004"),
    ("what time do you open", "CON005"),
    ("can you make my company website", "SVC003"),
    ("do you protect against hackers", "SVC004"),
    ("how do i start working with you", "PRO001"),
    ("do you offer free quotes", "PRC004"),
    ("can we work together even though im not in pakistan", "SVC010"),
    ("is there a human i can talk to", "CON009"),
    ("how long will my project take", "PRO003"),
    ("do you do video shoots", "SVC007"),
    ("what happens once i message you", "PRO002"),
]

K = 5


def dcg(relevances):
    return sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))


def evaluate():
    retriever = HybridRetriever()
    pipeline = get_pipeline()

    # Raw retrieval metrics
    hits_at_k = 0
    reciprocal_ranks = []
    ndcg_scores = []

    # Production pipeline metrics
    pipeline_hits = 0
    pipeline_confident_hits = 0
    pipeline_correct_confident_hits = 0

    print("Evaluating raw retrieval and production pipeline...\n")

    for query, expected_id in TEST_SET:
        # Raw Retrieval
        dense_hits = retriever.dense_search(query, k=10)
        sparse_hits = retriever.sparse_search(query, k=10)
        fused = reciprocal_rank_fusion(dense_hits, sparse_hits)

        ranked_ids = [item["faq_id"] for item in fused][:K]

        # Hit Rate@K
        hit = expected_id in ranked_ids
        hits_at_k += int(hit)

        # MRR
        if expected_id in ranked_ids:
            rank = ranked_ids.index(expected_id) + 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0.0)

        # NDCG@K (binary relevance)
        relevances = [1 if fid == expected_id else 0 for fid in ranked_ids]
        ideal_relevances = sorted(relevances, reverse=True)
        actual_dcg = dcg(relevances)
        ideal_dcg = dcg(ideal_relevances)
        ndcg = actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0
        ndcg_scores.append(ndcg)

        # Production Pipeline
        ans = pipeline.answer(query, use_cache=False)
        matched_id = ans.get("matched_faq_id")
        is_confident = ans.get("is_confident", False)

        pipeline_hit = (matched_id == expected_id)
        if pipeline_hit:
            pipeline_hits += 1

        if is_confident:
            pipeline_confident_hits += 1
            if pipeline_hit:
                pipeline_correct_confident_hits += 1

        status = "HIT " if hit else "MISS"
        pip_status = f"MATCH (conf={ans['confidence']:.2f})" if pipeline_hit and is_confident else (f"WRONG (conf={ans['confidence']:.2f})" if is_confident else "FALLBACK")
        print(f"[{status} | Pipeline: {pip_status}] '{query}' -> expected {expected_id}, raw got {ranked_ids}, pipeline got {matched_id}")

    n = len(TEST_SET)
    print("\n--- Raw Retrieval Results ---")
    print(f"Hit Rate@{K}: {hits_at_k / n:.3f}")
    print(f"MRR: {sum(reciprocal_ranks) / n:.3f}")
    print(f"NDCG@{K}: {sum(ndcg_scores) / n:.3f}")

    print("\n--- Production Pipeline Results ---")
    print(f"Pipeline Accuracy: {pipeline_hits / n:.3f} ({pipeline_hits}/{n})")
    print(f"Confidence Rate: {pipeline_confident_hits / n:.3f} ({pipeline_confident_hits}/{n})")
    if pipeline_confident_hits > 0:
        print(f"Precision when Confident: {pipeline_correct_confident_hits / pipeline_confident_hits:.3f} ({pipeline_correct_confident_hits}/{pipeline_confident_hits})")
    else:
        print("Precision when Confident: N/A")


if __name__ == "__main__":
    evaluate()
