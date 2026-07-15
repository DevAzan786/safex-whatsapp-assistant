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