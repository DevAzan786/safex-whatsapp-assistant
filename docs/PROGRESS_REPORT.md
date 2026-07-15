# Progress Report — Week 2, FAQ Knowledge Base

**Module:** FAQ Knowledge Base
**Owner:** Azan Ali
**Group:** 10

## Completed
- FAQ dataset research and structuring (data/safex_faq_dataset.json)
- Hybrid retrieval pipeline (ChromaDB + BM25 + RRF + cross-encoder rerank)
- Confidence gate with fallback response
- Gemini 2.5 Flash query rewriting
- Redis response caching
- FastAPI service with /faq/query and /faq/health endpoints
- Unit + integration tests
- Retrieval evaluation script (Hit Rate@k, MRR, NDCG@k)

## In progress / next steps
- Deployment to Railway/Render/Fly.io
- Finalize API contract sign-off with Automated Reply Engine (Abubakr)
- Coordinate confidence threshold tuning with Human Handover Logic (Zain)
- Record demo video and screenshots
