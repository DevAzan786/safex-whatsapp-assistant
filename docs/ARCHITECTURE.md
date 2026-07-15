# Architecture

## Pipeline flow

```
User question
     |
     v
[1] Cache check (Redis, normalized exact-match)
     | (miss)
     v
[2] Query rewrite (Gemini 2.5 Flash) — only for short/ambiguous queries
     |
     v
[3] Hybrid retrieval (parallel)
     ├── Dense search: ChromaDB, BAAI/bge-small-en-v1.5 embeddings
     └── Sparse search: BM25 over question text + keywords
     |
     v
[4] Reciprocal Rank Fusion (RRF) — merges both ranked lists
     |
     v
[5] Cross-encoder rerank (ms-marco-MiniLM-L-6-v2) over top candidates
     |
     v
[6] Confidence gate — sigmoid(rerank_score) vs. threshold
     ├── confident  -> return matched FAQ answer
     └── not confident -> return fallback text, is_confident=false
     |
     v
[7] Cache write (Redis)
     |
     v
Response: {answer, confidence, matched_faq_id, category, is_confident}
```

## Why hybrid retrieval + RRF

Dense (embedding) search is good at catching paraphrases and semantic
similarity ("how much does it cost" ~ "what's the pricing"), but can miss
exact keyword matches on short queries. BM25 is the opposite — strong on
exact keyword overlap but blind to paraphrasing. Running both and fusing
with RRF gets the benefit of each without needing to tune a single blended
score across two very different scales.

## Why a cross-encoder rerank stage

RRF fusion only ranks based on retrieval scores from two relatively coarse
methods. A cross-encoder scores the (query, candidate) pair jointly,
which is significantly more accurate at the final decision of "is this
really the right FAQ" — but it's too slow to run over the entire dataset,
so it only reranks the small shortlist RRF already narrowed down.

## Why a confidence gate

Not every question SafeX's WhatsApp bot receives will be in the FAQ
dataset. The confidence gate is what lets this module say "I don't know"
instead of guessing — which is the signal the Human Handover Logic module
(Zain, Group 10) uses to escalate to a real person instead of sending a
wrong or irrelevant answer.

## Module integration point

This service is called by the Automated Reply Engine (Abubakr, Group 10)
over HTTP via `POST /faq/query`. See the root README for the exact request/
response contract.
