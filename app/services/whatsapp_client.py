import requests
from app.config import settings

def send_whatsapp_message(to: str, text: str, session_id: str = None) -> bool:
    """
    Sends a text message using the OpenWA REST API.
    If API URL is not configured in .env, it runs in dry-run/mock mode (printing logs).
    """
    api_url = settings.openwa_api_url
    api_key = settings.openwa_api_key
    active_session = session_id or settings.openwa_session_id
    
    if not api_url:
        print(f"[WhatsApp Mock API (OpenWA)] Message sent to {to}: '{text}'")
        return True
        
    url = f"{api_url.rstrip('/')}/api/sessions/{active_session}/messages/send-text"
    
    # If the recipient is already a formatted chat ID (e.g. contains @c.us, @lid, @g.us)
    if "@" in to:
        chat_id = to
    else:
        # Clean the recipient phone number to digits only and append @c.us
        # Strip any +, whatsapp:, spaces, or @c.us
        clean_number = to.replace("whatsapp:", "").replace("@c.us", "").strip()
        clean_number = "".join(filter(str.isdigit, clean_number))
        chat_id = f"{clean_number}@c.us"
    
    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["X-API-Key"] = api_key
        
    payload = {
        "chatId": chat_id,
        "text": text
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"[OpenWA Client] Message sent successfully to {chat_id}! Response: {response.text}")
        return True
    except Exception as e:
        print(f"Error calling OpenWA API for recipient {to}: {e}")
        if 'response' in locals() and response is not None:
            print(f"OpenWA Response: {response.text}")
        return False
