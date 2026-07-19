import requests
from app.config import settings

def generate_text(prompt: str, temperature: float = 0.3, max_output_tokens: int = None) -> str:
    """
    Single-turn text generation call using the Mistral AI API.
    Uses the OpenAI-compatible /v1/chat/completions endpoint.
    """
    api_key = settings.gemini_api_key
    if not api_key:
        raise ValueError("GEMINI_API_KEY (Mistral API key) is not set in .env")

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.gemini_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }

    if max_output_tokens is not None:
        payload["max_tokens"] = max_output_tokens

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error calling Mistral AI API: {e}")
        raise e