from typing import List
import os
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from app.config import settings
from app.services.whatsapp_client import send_whatsapp_message

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


# --- Official WhatsApp Business Webhook Endpoints ---

@router.get("/bot/whatsapp/webhook")
def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Endpoint for Meta to verify our webhook URL during subscription setup.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        # Challenge must be returned as plain text response
        return HTMLResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/bot/whatsapp/webhook")
async def receive_whatsapp_message(request: Request):
    """
    Endpoint where Meta WhatsApp Cloud API pushes real-time user message events.
    """
    try:
        payload = await request.json()
        # Extract WhatsApp message details (sender ID & text body)
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        message_obj = value.get("messages", [])[0]
        
        sender = message_obj.get("from")  # e.g., "923001234567"
        message_text = message_obj.get("text", {}).get("body", "")
        
        if sender and message_text:
            # Format sender to have a plus sign if it's missing (WhatsApp payload standard is plain digits)
            formatted_sender = sender if sender.startswith("+") else f"+{sender}"
            # Orchestrate through router engine
            result = handle_user_message(formatted_sender, message_text)
            # Send the response back to user's WhatsApp number
            send_whatsapp_message(sender, result["reply"])
            
    except Exception:
        # Silently pass events that aren't user text messages (reads, deliveries, statuses)
        pass
        
    return {"status": "success"}