import google.generativeai as genai
from app.config import settings

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True


def generate_text(prompt: str, temperature: float = 0.3, max_output_tokens: int = None) -> str:
    """Single-turn text generation call to Gemini."""
    _ensure_configured()
    model = genai.GenerativeModel(settings.gemini_model)
    config = {"temperature": temperature}
    if max_output_tokens is not None:
        config["max_output_tokens"] = max_output_tokens
    response = model.generate_content(
        prompt,
        generation_config=config,
    )
    return (response.text or "").strip()