# Achievements — FAQ Knowledge Base (Week 2)

- Researched and structured a 50+ entry FAQ dataset covering SafeX
  Solutions' services, pricing, process, and contact information, sourced
  directly from safexsolutions.com.
- Built a hybrid retrieval pipeline combining dense (ChromaDB) and sparse
  (BM25) search, fused with Reciprocal Rank Fusion.
- Added a cross-encoder reranking stage for precision on the final
  candidate shortlist.
- Implemented a confidence gate that hands off low-confidence queries to
  the Human Handover module instead of guessing.
- Integrated Gemini 2.5 Flash for query rewriting on short/ambiguous
  WhatsApp messages.
- Added a Redis-backed response cache to reduce repeat-query latency.
- Exposed the module as a FastAPI service (`POST /faq/query`) ready for
  integration with the Automated Reply Engine.
- Wrote an evaluation script reporting Hit Rate@k, MRR, and NDCG@k against
  a labeled paraphrase test set.