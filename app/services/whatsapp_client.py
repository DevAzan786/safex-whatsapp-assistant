import requests
from app.config import settings

def send_whatsapp_message(to: str, text: str) -> bool:
    """
    Sends a text message using the official Meta WhatsApp Cloud API.
    If credentials are not configured in .env, it runs in dry-run mode (printing logs).
    """
    token = settings.whatsapp_cloud_api_token
    phone_number_id = settings.whatsapp_phone_number_id
    
    if not token or not phone_number_id:
        print(f"[WhatsApp Mock API] Message sent to {to}: '{text}'")
        return True
        
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "body": text
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error calling WhatsApp API for recipient {to}: {e}")
        return False
