from app.services.gemini_client import generate_text

DETECT_LANG_PROMPT = """You are a language detection agent for a customer support chatbot.
Classify the language of the following message into one of these exact codes:
- 'en' (English)
- 'ur' (Urdu in Arabic script)
- 'roman_urdu' (Urdu written in Latin/English alphabets, e.g., "website banani hai", "apka office kahan hai", "pricing kiya hai")

Output ONLY the code ('en', 'ur', or 'roman_urdu') and absolutely nothing else. Do not include markdown formatting or quotes.

Message: "{text}"
Language Code:"""

TRANSLATE_TO_EN_PROMPT = """You are an expert translator. Translate the following customer support message from {source_lang} to English.
Only output the translated text. Do not add explanations, comments, or quotes.

Message: "{text}"
Translation:"""

TRANSLATE_FROM_EN_PROMPT = """You are an expert translator. Translate the following English response to {target_lang} for a customer support bot.
Ensure the tone is professional, polite, and helpful.
If the target language is 'roman_urdu', translate to Roman Urdu (Urdu written in English/Latin alphabets, using simple, clear words).
Only output the translated text. Do not add explanations, comments, or quotes.

Response: "{text}"
Translation:"""

def detect_language(text: str) -> str:
    """
    Detects if the incoming message is English ('en'), Urdu ('ur'), or Roman Urdu ('roman_urdu').
    """
    if not text or not text.strip():
        return "en"
    
    # Quick heuristic check for Arabic script (Urdu)
    # Range for Arabic/Persian/Urdu Unicode characters
    if any(ord(char) >= 0x0600 and ord(char) <= 0x06FF for char in text):
        return "ur"
        
    try:
        prompt = DETECT_LANG_PROMPT.format(text=text)
        result = generate_text(prompt, temperature=0.1, max_output_tokens=10)
        code = result.strip().lower()
        if code in ["en", "ur", "roman_urdu"]:
            return code
    except Exception:
        pass
    
    # Fallback to English
    return "en"

def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translates a query to English if the language is 'ur' or 'roman_urdu'.
    """
    if source_lang == "en" or not text or not text.strip():
        return text
        
    try:
        prompt = TRANSLATE_TO_EN_PROMPT.format(source_lang=source_lang, text=text)
        translation = generate_text(prompt, temperature=0.2)
        if translation:
            return translation
    except Exception:
        pass
        
    return text

def translate_from_english(text: str, target_lang: str) -> str:
    """
    Translates an English response back to the user's preferred language.
    """
    if target_lang == "en" or not text or not text.strip():
        return text
        
    try:
        prompt = TRANSLATE_FROM_EN_PROMPT.format(target_lang=target_lang, text=text)
        translation = generate_text(prompt, temperature=0.3)
        if translation:
            return translation
    except Exception:
        pass
        
    return text
