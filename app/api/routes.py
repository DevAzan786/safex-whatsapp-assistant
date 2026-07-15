from fastapi import APIRouter, HTTPException

from app.models.schemas import FAQQueryRequest, FAQQueryResponse, HealthResponse
from app.core.pipeline import get_pipeline

router = APIRouter(prefix="/faq", tags=["faq"])


@router.post("/query", response_model=FAQQueryResponse)
def query_faq(request: FAQQueryRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    pipeline = get_pipeline()
    result = pipeline.answer(request.question)
    return FAQQueryResponse(**result)


@router.get("/health", response_model=HealthResponse)
def health_check():
    pipeline = get_pipeline()
    return HealthResponse(
        status="ok",
        faqs_loaded=len(pipeline.retriever.faq_lookup),
        chroma_ready=pipeline.retriever.collection.count() > 0,
        bm25_ready=pipeline.retriever.bm25 is not None,
    )