from typing import List
import os
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from app.config import settings
from app.services.whatsapp_client import send_whatsapp_message
from app.core.crm import get_all_leads

from app.models.schemas import (
    FAQQueryRequest, 
    FAQQueryResponse, 
    HealthResponse,
    BotMessageRequest,
    BotMessageResponse,
    HandoverResponse,
    ClaimResponse,
    AnalyticsMetricsResponse,
    LeadResponse
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


@router.get("/leads/all", response_model=List[LeadResponse])
def list_all_leads():
    """Returns all captured leads with full details for the dashboard."""
    return [LeadResponse(**lead) for lead in get_all_leads()]


@router.get("/analytics/dashboard", response_class=HTMLResponse)
def get_dashboard():
    template_path = os.path.join("app", "templates", "dashboard.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Dashboard HTML template not found")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


processed_message_ids = set()

# --- OpenWA WhatsApp Webhook Endpoints ---

@router.get("/bot/whatsapp/webhook")
def verify_whatsapp_webhook():
    """
    Simple check endpoint to verify that the webhook path is running and accessible.
    """
    return HTMLResponse(content="OpenWA Webhook Endpoint Ready", status_code=200)


def process_and_reply_task(sender: str, message_text: str, from_val: str, session_id: str):
    """
    Helper background worker to execute slow LLM calls and send WhatsApp responses.
    """
    try:
        # Orchestrate through router engine
        result = handle_user_message(sender, message_text)
        # Send the response back to user's WhatsApp number using the raw chat ID
        send_whatsapp_message(from_val, result["reply"], session_id=session_id)
    except Exception as e:
        print(f"Error in background message processing: {e}")


@router.post("/bot/whatsapp/webhook")
async def receive_whatsapp_message(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint where OpenWA API pushes real-time user message events as JSON.
    """
    try:
        import json
        payload = await request.json()
        print(f"[Webhook Received] Event: {payload.get('event')}, Payload: {json.dumps(payload, ensure_ascii=True)}")
        
        # We only process message.received events
        if payload.get("event") != "message.received":
            return {"status": "ignored"}
            
        data = payload.get("data", {})
        message_id = data.get("id")
        
        # Deduplicate to prevent processing webhook retries
        if message_id:
            if message_id in processed_message_ids:
                print(f"[Webhook] Duplicate message ignored: {message_id}")
                return {"status": "duplicate"}
            processed_message_ids.add(message_id)
            # Control set size to prevent memory leaks
            if len(processed_message_ids) > 1000:
                processed_message_ids.pop()
                
        session_id = payload.get("sessionId")
        from_val = data.get("from", "")  # e.g., "923001234567@c.us"
        message_text = data.get("body", "")
        
        if from_val and message_text:
            # Extract number before the @c.us domain
            sender_phone = from_val.split("@")[0].strip()
            
            # Ensure sender is correctly formatted with + prefix
            sender = sender_phone if sender_phone.startswith("+") else f"+{sender_phone}"
            
            # Execute the heavy work asynchronously
            background_tasks.add_task(process_and_reply_task, sender, message_text, from_val, session_id)
            
    except Exception as e:
        print(f"Error handling OpenWA webhook: {e}")
        
    return {"status": "success"}