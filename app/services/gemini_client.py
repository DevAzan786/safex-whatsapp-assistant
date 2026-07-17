import requests
from app.config import settings

def generate_text(prompt: str, temperature: float = 0.3, max_output_tokens: int = None) -> str:
    """
    Single-turn text generation call using the free, OpenAI-compatible llm7.io API.
    Routes queries seamlessly without hitting the daily Google AI Studio quota.
    """
    # Use configured API key from .env if present, otherwise default to a free token placeholder
    api_key = settings.gemini_api_key or "sk-llm7-free-access-token"
    
    url = "https://api.llm7.io/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "default",
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
        print(f"Error calling llm7.io chat completions API: {e}")
        raise e