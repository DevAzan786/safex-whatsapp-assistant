from app.services.gemini_client import generate_text
from app.core.session import get_session, set_session, clear_session
from app.core.language import detect_language, translate_to_english, translate_from_english
from app.core.lead_collection import process_lead_message
from app.core.handover import trigger_handover
from app.core.pipeline import get_pipeline
from app.core.analytics import log_message

INTENT_CLASSIFY_PROMPT = """You are an intent classification agent for SafeX Solutions' support chatbot.
Classify the following customer support message into one of these three intents:
- 'human_handover': The user is explicitly asking to talk to a human agent, representative, or person (e.g. "I want to talk to a human", "connect to agent", "handover to person", "can I speak with someone").
- 'lead_capture': The user wants to buy services, hire SafeX Solutions, get a quote, build a website, sign up/register for courses/SDC, or start a project (e.g. "pricing for seo", "build a website for me", "I want to buy digital marketing", "sign up for skill centre").
- 'faq': The user is asking a general informational question about SafeX (e.g. office hours, locations, service categories, refund policy, etc.).

Output ONLY the intent code ('human_handover', 'lead_capture', or 'faq') and absolutely nothing else. Do not include markdown formatting or quotes.

Message: "{message}"
Intent Code:"""

def classify_intent(message_english: str) -> str:
    """
    Classifies the English query into 'human_handover', 'lead_capture', or 'faq'.
    """
    # Quick heuristics for explicit human requests
    words = message_english.lower().split()
    handover_keywords = {"human", "agent", "representative", "person", "handover", "support team", "admin"}
    if any(k in words for k in handover_keywords):
        return "human_handover"
        
    try:
        prompt = INTENT_CLASSIFY_PROMPT.format(message=message_english)
        result = generate_text(prompt, temperature=0.1, max_output_tokens=15)
        intent = result.strip().lower()
        if intent in ["human_handover", "lead_capture", "faq"]:
            return intent
    except Exception:
        pass
        
    return "faq"  # Default fallback is FAQ

def handle_user_message(sender: str, message: str) -> dict:
    """
    Routes the incoming customer message through language parsing, intent classification,
    and appropriate module fulfillment.
    """
    session = get_session(sender)
    state = session.get("state", "idle")
    saved_lang = session.get("lang", "en")
    
    # 1. Active Human Handover State
    if state == "handover_active":
        reply = "An agent has been notified and will be with you shortly. Please wait."
        translated_reply = translate_from_english(reply, saved_lang)
        log_message(
            phone=sender,
            message=message,
            intent="human_handover",
            language=saved_lang,
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
            "language": saved_lang,
            "session_state": "handover_active"
        }
        
    # 2. Active Lead Collection State
    if state.startswith("lead_"):
        reply, next_state = process_lead_message(sender, message, state, session)
        translated_reply = translate_from_english(reply, saved_lang)
        log_message(
            phone=sender,
            message=message,
            intent="lead_capture",
            language=saved_lang,
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
            "language": saved_lang,
            "session_state": next_state
        }
        
    # 3. Idle / Start State: Detect Language and translate to English
    lang = detect_language(message)
    set_session(sender, state="idle", lang=lang)
    message_en = translate_to_english(message, lang)
    
    # 4. Classify Intent
    intent = classify_intent(message_en)
    
    # 5. Route accordingly
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
