from typing import List
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.models.schemas import (
    FAQQueryRequest, 
    FAQQueryResponse, 
    HealthResponse,
    BotMessageRequest,
    BotMessageResponse,
    HandoverResponse,
    ClaimResponse,
    AnalyticsMetricsResponse
)
from app.core.pipeline import get_pipeline
from app.core.router import handle_user_message
from app.core.handover import get_pending_handovers, claim_handover, resolve_handover
from app.core.analytics import get_analytics_metrics

router = APIRouter(tags=["bot"])


@router.post("/faq/query", response_model=FAQQueryResponse, tags=["faq"])
def query_faq(request: FAQQueryRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    pipeline = get_pipeline()
    result = pipeline.answer(request.question)
    return FAQQueryResponse(**result)


@router.get("/faq/health", response_model=HealthResponse, tags=["faq"])
def health_check():
    pipeline = get_pipeline()
    return HealthResponse(
        status="ok",
        faqs_loaded=len(pipeline.retriever.faq_lookup),
        chroma_ready=pipeline.retriever.collection.count() > 0,
        bm25_ready=pipeline.retriever.bm25 is not None,
    )


@router.post("/bot/message", response_model=BotMessageResponse)
def bot_message(request: BotMessageRequest):
    if not request.sender or not request.sender.strip():
        raise HTTPException(status_code=400, detail="sender must not be empty")
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
        
    result = handle_user_message(request.sender, request.message)
    return BotMessageResponse(**result)


@router.get("/handover/pending", response_model=List[HandoverResponse])
def pending_handovers():
    return [HandoverResponse(**h) for h in get_pending_handovers()]


@router.post("/handover/claim", response_model=ClaimResponse)
def claim_ticket(handover_id: int = Query(...), agent_name: str = Query(...)):
    success = claim_handover(handover_id, agent_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to claim handover ticket. Ensure it is pending.")
    return ClaimResponse(status="success", message=f"Handover {handover_id} claimed by {agent_name}")


@router.post("/handover/resolve", response_model=ClaimResponse)
def resolve_ticket(handover_id: int = Query(...)):
    success = resolve_handover(handover_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resolve handover ticket.")
    return ClaimResponse(status="success", message=f"Handover {handover_id} resolved and bot resumes.")


@router.get("/analytics/data", response_model=AnalyticsMetricsResponse)
def analytics_data():
    return AnalyticsMetricsResponse(**get_analytics_metrics())


@router.get("/analytics/dashboard", response_class=HTMLResponse)
def get_dashboard():
    template_path = os.path.join("app", "templates", "dashboard.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Dashboard HTML template not found")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)