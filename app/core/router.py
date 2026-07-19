from app.services.gemini_client import generate_text
from app.core.session import get_session, set_session, clear_session
from app.core.language import detect_language, translate_to_english, translate_from_english
from app.core.lead_collection import process_lead_message
from app.core.handover import trigger_handover
from app.core.pipeline import get_pipeline
from app.core.analytics import log_message

# Common greetings in English, Urdu (Roman), and Arabic-script Urdu
GREETINGS = {
    "hi", "hello", "hey", "yo", "sup", "howdy", "hola", "greetings",
    "salam", "aoa", "assalamualaikum", "assalamoalaikum",
    "walaikumassalam", "wa alaikum assalam",
    "good morning", "good afternoon", "good evening",
}

WELCOME_MESSAGE = (
    "Hello! 👋 Welcome to SafeX Solutions. How can I help you today?\n\n"
    "You can ask me about:\n"
    "• Our services (web dev, cybersecurity, AI, marketing)\n"
    "• Pricing & quotes\n"
    "• Getting started with a project\n"
    "• Or type anything else and I'll do my best to help!"
)

INTENT_CLASSIFY_PROMPT = """You are an intent classification agent for SafeX Solutions' support chatbot.
Classify the following customer support message into one of these three intents:
- 'human_handover': The user is explicitly asking to talk to a human agent, representative, or person (e.g. "I want to talk to a human", "connect to agent", "handover to person", "can I speak with someone").
- 'lead_capture': The user explicitly wants to buy services, hire SafeX Solutions, get a custom quote, build a website, sign up/register for courses/SDC, or start a project (e.g. "pricing for seo", "build a website for me", "I want to buy digital marketing", "sign up for skill centre").
- 'faq': The user is asking a general informational question about SafeX (e.g. office hours, locations, service categories, refund policy, contact details, address, phone number, email, team members, etc.).

CRITICAL RULES:
- If the user is asking for SafeX Solutions' contact details, address, phone number, email, office location, or any information ABOUT the company, classify as 'faq' — NOT 'lead_capture'.
- 'lead_capture' is ONLY when the user wants to purchase, hire, or start a project.
- Asking "do you have contact details?" or "what is your email?" or "where is your office?" is always 'faq'.

Output ONLY the intent code ('human_handover', 'lead_capture', or 'faq') and absolutely nothing else. Do not include markdown formatting or quotes.

Message: "{message}"
Intent Code:"""

# Keywords that indicate the user is asking FOR information about the company (FAQ intent)
_INFO_QUERY_PATTERNS = {
    "contact details", "contact info", "contact information", "contact number",
    "phone number", "email address", "your email", "your number", "your phone",
    "your address", "your office", "your location", "office address", "office location",
    "where are you located", "where is your office", "how can i reach you",
    "how to contact", "how do i contact", "do you have contact",
    "what is your email", "what is your number", "what is your phone",
    "what is your address", "company address", "company email", "company phone",
    "safex contact", "safex email", "safex phone", "safex address", "safex number",
    "safex office", "safex location",
}

def classify_intent(message_english: str) -> str:
    """
    Classifies the English query into 'human_handover', 'lead_capture', or 'faq'.
    """
    msg_lower = message_english.lower().strip()
    words = msg_lower.split()
    
    # Quick heuristics for explicit human requests
    handover_keywords = {"human", "agent", "representative", "person", "handover", "support team", "admin"}
    if any(k in words for k in handover_keywords):
        return "human_handover"
    
    # Pre-check: If the user is asking for company info/contact details, it's FAQ
    if any(pattern in msg_lower for pattern in _INFO_QUERY_PATTERNS):
        return "faq"
        
    try:
        prompt = INTENT_CLASSIFY_PROMPT.format(message=message_english)
        result = generate_text(prompt, temperature=0.1, max_output_tokens=15)
        intent = result.strip().lower()
        if intent in ["human_handover", "lead_capture", "faq"]:
            return intent
    except Exception:
        pass
        
    return "faq"  # Default fallback is FAQ

def _is_greeting(message: str) -> bool:
    """Check if the message is a simple greeting."""
    cleaned = message.strip().lower().rstrip("!.?,")
    return cleaned in GREETINGS

def handle_user_message(sender: str, message: str) -> dict:
    """
    Routes the incoming customer message through language parsing, intent classification,
    and appropriate module fulfillment.
    """
    # Support manual session reset via keyword for testing/debugging convenience
    if message.strip().lower() in ["/reset", "reset", "reset session"]:
        clear_session(sender)
        return {
            "sender": sender,
            "reply": "Session reset successfully! Send any query to start fresh.",
            "intent": "faq",
            "language": "en",
            "session_state": "idle"
        }

    session = get_session(sender)
    state = session.get("state", "idle")

    # 1. Detect language first for ALL incoming messages to support dynamic mid-chat language switching
    lang = detect_language(message)
    set_session(sender, state=state, lang=lang)

    # Greeting detection — respond immediately without LLM calls
    # Only when session is idle (not in handover or lead collection flow)
    if state == "idle" and _is_greeting(message):
        translated_welcome = translate_from_english(WELCOME_MESSAGE, lang)
        log_message(
            phone=sender,
            message=message,
            intent="faq",
            language=lang,
            is_faq_hit=True,
            is_lead=False,
            is_handover=False,
            confidence=1.0,
            response=translated_welcome
        )
        return {
            "sender": sender,
            "reply": translated_welcome,
            "intent": "faq",
            "language": lang,
            "session_state": "idle"
        }
    
    # 2. Active Human Handover State
    if state == "handover_active":
        reply = "An agent has been notified and will be with you shortly. Please wait."
        translated_reply = translate_from_english(reply, lang)
        log_message(
            phone=sender,
            message=message,
            intent="human_handover",
            language=lang,
            is_faq_hit=False,
            is_lead=False,
            is_handover=True,
            confidence=1.0,
            response=translated_reply
        )
        return {
            "sender": sender,
            "reply": translated_reply,
            "intent": "human_handover",
            "language": lang,
            "session_state": "handover_active"
        }
        
    # 3. Active Lead Collection State
    if state.startswith("lead_"):
        # For lead collection, first translate the input to English if it is in Urdu/Roman Urdu
        # so name/email/requirements extraction works with highest accuracy
        message_en = translate_to_english(message, lang)
        reply, next_state = process_lead_message(sender, message_en, state, session)
        translated_reply = translate_from_english(reply, lang)
        log_message(
            phone=sender,
            message=message,
            intent="lead_capture",
            language=lang,
            is_faq_hit=False,
            is_lead=True,
            is_handover=False,
            confidence=1.0,
            response=translated_reply
        )
        return {
            "sender": sender,
            "reply": translated_reply,
            "intent": "lead_capture",
            "language": lang,
            "session_state": next_state
        }
        
    # 4. Idle / Start State: Translate detected non-English queries
    message_en = translate_to_english(message, lang)
    
    # 5. Classify Intent
    intent = classify_intent(message_en)
    
    # 6. Route accordingly
    if intent == "human_handover":
        reply = trigger_handover(sender, reason="explicit_user_request")
        translated_reply = translate_from_english(reply, lang)
        log_message(
            phone=sender,
            message=message,
            intent="human_handover",
            language=lang,
            is_faq_hit=False,
            is_lead=False,
            is_handover=True,
            confidence=1.0,
            response=translated_reply
        )
        return {
            "sender": sender,
            "reply": translated_reply,
            "intent": "human_handover",
            "language": lang,
            "session_state": "handover_active"
        }
        
    elif intent == "lead_capture":
        # Transition to lead flow
        reply, next_state = process_lead_message(sender, message_en, "idle", session)
        translated_reply = translate_from_english(reply, lang)
        log_message(
            phone=sender,
            message=message,
            intent="lead_capture",
            language=lang,
            is_faq_hit=False,
            is_lead=True,
            is_handover=False,
            confidence=1.0,
            response=translated_reply
        )
        return {
            "sender": sender,
            "reply": translated_reply,
            "intent": "lead_capture",
            "language": lang,
            "session_state": next_state
        }
        
    else:  # intent == "faq"
        pipeline = get_pipeline()
        faq_res = pipeline.answer(message_en, use_cache=True)
        
        if faq_res["is_confident"]:
            ans = faq_res["answer"]
            translated_reply = translate_from_english(ans, lang)
            log_message(
                phone=sender,
                message=message,
                intent="faq",
                language=lang,
                is_faq_hit=True,
                is_lead=False,
                is_handover=False,
                confidence=faq_res["confidence"],
                response=translated_reply
            )
            return {
                "sender": sender,
                "reply": translated_reply,
                "intent": "faq",
                "language": lang,
                "session_state": "idle"
            }
        else:
            # Fallback to human handover due to low confidence
            reason = f"low_confidence_faq_match ({faq_res['confidence']})"
            reply = trigger_handover(sender, reason=reason)
            translated_reply = translate_from_english(reply, lang)
            log_message(
                phone=sender,
                message=message,
                intent="human_handover",
                language=lang,
                is_faq_hit=False,
                is_lead=False,
                is_handover=True,
                confidence=faq_res["confidence"],
                response=translated_reply
            )
            return {
                "sender": sender,
                "reply": translated_reply,
                "intent": "human_handover",
                "language": lang,
                "session_state": "handover_active"
            }
