import re
from app.core.session import set_session, clear_session
from app.core.crm import sync_lead
from app.services.gemini_client import generate_text

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Regex patterns to extract names from common Roman Urdu and English phrases
# These cover the most frequent ways people state their name
_NAME_PATTERNS = [
    # Roman Urdu patterns
    re.compile(r"(?:mera\s+naam|mera\s+name)\s+(.+?)(?:\s+(?:hai|hay|hey|he|h|hy)\.?\s*$)", re.IGNORECASE),
    re.compile(r"(?:naam|name)\s+(.+?)(?:\s+(?:hai|hay|hey|he|h|hy)\.?\s*$)", re.IGNORECASE),
    re.compile(r"(?:mein|main|me)\s+(.+?)(?:\s+(?:hun|hoon|hu|houn)\.?\s*$)", re.IGNORECASE),
    re.compile(r"^(?:ji|g)\s+(?:mera\s+naam\s+)?(.+?)(?:\s+(?:hai|hay|hey|he|h|hy)\.?\s*$)?$", re.IGNORECASE),

    # English patterns
    re.compile(r"(?:my\s+name\s+is|i\s+am|i'm|im|this\s+is|it'?s|its|call\s+me)\s+(.+?)\.?\s*$", re.IGNORECASE),
    re.compile(r"^(?:name\s*:\s*)(.+?)\.?\s*$", re.IGNORECASE),

    # Mixed patterns
    re.compile(r"(?:mera\s+name\s+is|my\s+naam\s+is|my\s+naam)\s+(.+?)(?:\s+(?:hai|hay|hey|he|h|hy)\.?\s*$)?$", re.IGNORECASE),
]

EXTRACT_NAME_PROMPT = """Extract ONLY the person's name from the following message. The message may be in English, Roman Urdu, or Urdu.
Examples:
- "Mera naam Azan Ali hay" → Azan Ali
- "My name is John Smith" → John Smith
- "Ali" → Ali
- "I am Muhammad Hassan" → Muhammad Hassan
- "mein Sara hun" → Sara
- "Its Azan" → Azan
- "ji mera naam Fatima hai" → Fatima
- "naam Ahmed hay" → Ahmed
- "main Ali hun" → Ali

Output ONLY the extracted name, nothing else. No quotes, no explanation.

Message: "{message}"
Name:"""

EXTRACT_REQUIREMENTS_PROMPT = """Extract the project requirements or service interest from the following message. The message may be in English, Roman Urdu, or Urdu.
Translate it to clear English if needed. Output ONLY the extracted requirement in English, nothing else.

Examples:
- "Mujhe website banwani hai apni company ke liye" → Need a website built for my company
- "I need SEO for my business" → Need SEO for my business
- "digital marketing chahiye" → Need digital marketing services

Message: "{message}"
Requirement:"""


def _clean_extracted_name(name: str) -> str:
    """Post-process an extracted name to remove common artifacts."""
    name = name.strip().strip('"').strip("'").strip()
    # Remove leading/trailing filler words the LLM might include
    filler_start = re.compile(
        r"^(?:my name is|i am|i'm|mera naam|mera name|naam|name|it's|its|call me|ji|this is)\s+",
        re.IGNORECASE,
    )
    filler_end = re.compile(
        r"\s+(?:hai|hay|hey|he|h|hy|hun|hoon|hu|houn|sir|madam)\.?\s*$",
        re.IGNORECASE,
    )
    name = filler_start.sub("", name)
    name = filler_end.sub("", name)
    return name.strip()


def _extract_name(message: str) -> str:
    """
    Extract just the person's name from a message,
    handling Roman Urdu, English, and mixed inputs.
    Uses regex patterns first for speed and reliability,
    then falls back to LLM extraction for unusual phrasing.
    """
    msg = message.strip()

    # 1. If it looks like just a plain name (1-3 words, all alphabetic), use it directly
    words = msg.split()
    if len(words) <= 3 and all(w.isalpha() for w in words):
        return msg

    # 2. Try regex-based extraction first (fast, deterministic, multilingual)
    for pattern in _NAME_PATTERNS:
        match = pattern.search(msg)
        if match:
            extracted = match.group(1).strip()
            if extracted and len(extracted) >= 2:
                return _clean_extracted_name(extracted)

    # 3. Fallback to LLM extraction for unusual phrasing
    try:
        prompt = EXTRACT_NAME_PROMPT.format(message=msg)
        name = generate_text(prompt, temperature=0.1, max_output_tokens=50)
        if name:
            cleaned = _clean_extracted_name(name)
            if cleaned and len(cleaned) >= 2:
                return cleaned
    except Exception:
        pass

    return msg


def _extract_requirements(message: str) -> str:
    """
    Use LLM to translate/extract requirements from Roman Urdu or other languages to English.
    Falls back to the raw message if extraction fails.
    """
    # If already in English (basic heuristic: no common Roman Urdu markers), use directly
    words = message.strip().lower().split()
    roman_urdu_markers = {"hai", "hay", "hey", "hain", "ka", "ki", "ke", "ko",
                          "mujhe", "mein", "mera", "mere", "chahiye", "banwani",
                          "karna", "karwana", "wala", "wali"}
    if not any(w in roman_urdu_markers for w in words):
        return message.strip()

    try:
        prompt = EXTRACT_REQUIREMENTS_PROMPT.format(message=message)
        result = generate_text(prompt, temperature=0.2, max_output_tokens=100)
        if result and len(result.strip()) > 0:
            return result.strip()
    except Exception:
        pass

    return message.strip()


def process_lead_message(sender: str, message: str, current_state: str, session: dict) -> tuple:
    """
    Processes a message from a user who is currently in the Lead Collection flow.
    Returns: (reply_text, next_state)
    """
    message = message.strip()
    session_data = session.get("data", {})
    
    if current_state == "lead_name":
        # Extract just the name from the message (handles "Mera naam X hay" etc.)
        name = _extract_name(message)
        session_data["name"] = name
        set_session(sender, state="lead_email", data=session_data)
        reply = f"Thank you, {name}! What is your email address so our team can reach out to you?"
        return reply, "lead_email"
        
    elif current_state == "lead_email":
        # Try to find an email in the message even if surrounded by other text
        email_match = EMAIL_REGEX.search(message)
        if not email_match:
            reply = "That doesn't look like a valid email. Please enter a valid email address (e.g., name@example.com):"
            return reply, "lead_email"
            
        session_data["email"] = email_match.group()
        set_session(sender, state="lead_requirements", data=session_data)
        reply = "Got it. Finally, could you briefly describe your project or the services you are interested in?"
        return reply, "lead_requirements"
        
    elif current_state == "lead_requirements":
        # Extract and translate requirements to English
        requirements = _extract_requirements(message)
        name = session_data.get("name", "Customer")
        email = session_data.get("email", "")
        
        # Save lead to CRM
        sync_lead(sender, name, email, requirements)
        
        # Reset session state
        clear_session(sender)
        
        reply = "Thank you! We've captured your details and our team will get in touch with you shortly. Have a great day!"
        return reply, "idle"
        
    else:
        # Default starting point
        set_session(sender, state="lead_name", data={})
        reply = "We would love to help you! To get started, could you please tell me your name?"
        return reply, "lead_name"
