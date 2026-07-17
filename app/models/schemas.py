from typing import Optional, List
from pydantic import BaseModel, Field


class FAQQueryRequest(BaseModel):
    question: str = Field(..., description="The user's incoming message/question")
    language: Optional[str] = Field(
        default="en", description="'en' or 'ur' — language of the question"
    )
    user_id: Optional[str] = Field(
        default=None, description="WhatsApp user identifier, for logging/analytics"
    )


class RetrievedCandidate(BaseModel):
    faq_id: str
    question: str
    answer: str
    category: str
    score: float


class FAQQueryResponse(BaseModel):
    answer: str
    confidence: float
    matched_faq_id: Optional[str] = None
    category: Optional[str] = None
    is_confident: bool
    cached: bool = False
    candidates: Optional[List[RetrievedCandidate]] = None  # debug/analytics use


class HealthResponse(BaseModel):
    status: str
    faqs_loaded: int
    chroma_ready: bool
    bm25_ready: bool


class BotMessageRequest(BaseModel):
    sender: str = Field(..., description="The user's WhatsApp phone number or identifier")
    message: str = Field(..., description="The user's incoming message text")


class BotMessageResponse(BaseModel):
    sender: str
    reply: str
    intent: str
    language: str
    session_state: str


class LeadResponse(BaseModel):
    id: int
    phone: str
    name: str
    email: str
    requirements: str
    updated_at: str


class HandoverResponse(BaseModel):
    id: int
    phone: str
    status: str
    reason: str
    assigned_agent: Optional[str] = None
    created_at: str


class ClaimResponse(BaseModel):
    status: str
    message: str


class AnalyticsMessageLog(BaseModel):
    id: int
    timestamp: str
    phone: str
    message: str
    intent: str
    language: str
    is_faq_hit: bool
    is_lead: bool
    is_handover: bool
    confidence: float
    response: str


class AnalyticsMetricsResponse(BaseModel):
    total_messages: int
    faq_hits: int
    leads_collected: int
    handovers_triggered: int
    language_distribution: dict
    intent_distribution: dict
    recent_messages: List[AnalyticsMessageLog]