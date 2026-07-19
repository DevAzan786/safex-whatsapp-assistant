import sys
import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.db import init_db, get_db_connection
from app.core.session import get_session, set_session, clear_session
from app.core.handover import get_pending_handovers, claim_handover, resolve_handover
from app.core.crm import get_all_leads

client = TestClient(app)

# Helper mock for Gemini
def mock_generate_text(prompt, temperature=0.3, max_output_tokens=None):
    prompt_lower = prompt.lower()
    
    # Extract query/message from the prompt to avoid matching prompt template instructions
    query = ""
    if 'message: "' in prompt_lower:
        query = prompt_lower.split('message: "')[1].split('"')[0]
    elif 'message:' in prompt_lower:
        query = prompt_lower.split('message:')[1].strip()
    elif 'response: "' in prompt_lower:
        query = prompt_lower.split('response: "')[1].split('"')[0]
    elif 'response:' in prompt_lower:
        query = prompt_lower.split('response:')[1].strip()
        
    if "classify the language" in prompt_lower:
        if "office kahan" in query or "kahan" in query or "kya" in query:
            return "roman_urdu"
        elif "دفتر" in query or "کہاں" in query:
            return "ur"
        return "en"
    elif "translate the following customer support message from" in prompt_lower:
        if "office kahan" in query or "دفتر" in query:
            return "Where is your office?"
        if "website banani" in query:
            return "I want to build a website"
        return query
    elif "translate the following english response to" in prompt_lower:
        if "roman_urdu" in prompt_lower:
            if "office" in query or "location" in query or "headquartered" in query or "islamabad" in query:
                return "Hamara office Islamabad me hai."
            return f"Translated to Roman Urdu: {query}"
        elif "ur" in prompt_lower:
            if "office" in query or "location" in query or "headquartered" in query or "islamabad" in query:
                return "ہمارا دفتر اسلام آباد میں ہے۔"
            return f"Translated to Urdu: {query}"
        return query
    elif "classify the following customer support message into one of these three intents" in prompt_lower:
        if "website" in query or "build" in query or "hire" in query:
            return "lead_capture"
        if "agent" in query or "human" in query or "connect" in query:
            return "human_handover"
        return "faq"
    elif "rewrite the short customer message below" in prompt_lower:
        return query
    return "default mock response"


@pytest.fixture(autouse=True)
def setup_database():
    """
    Ensure the database is initialized and empty before each test.
    """
    # Override sqlite path for testing so we don't mess with dev database
    from app.config import settings
    settings.sqlite_db_path = "data/safex_bot_test.db"
    
    init_db()
    
    # Clean tables
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads")
    cursor.execute("DELETE FROM handovers")
    cursor.execute("DELETE FROM analytics_logs")
    conn.commit()
    conn.close()
    
    yield
    
    # Cleanup test db file
    try:
        if os.path.exists("data/safex_bot_test.db"):
            os.remove("data/safex_bot_test.db")
    except Exception:
        pass


@patch("app.core.language.generate_text", side_effect=mock_generate_text)
@patch("app.core.router.generate_text", side_effect=mock_generate_text)
def test_end_to_end_lead_collection(mock_router_gen, mock_lang_gen):
    sender = "+923123456789"
    clear_session(sender)
    
    # Step 1: User says they want to build a website (Trigger Lead Flow)
    response = client.post("/bot/message", json={"sender": sender, "message": "I want to build a website"})
    assert response.status_code == 200
    body = response.json()
    assert "name" in body["reply"].lower()
    assert body["intent"] == "lead_capture"
    assert body["session_state"] == "lead_name"
    
    # Step 2: User provides name
    response = client.post("/bot/message", json={"sender": sender, "message": "Ali Hussain"})
    assert response.status_code == 200
    body = response.json()
    assert "email" in body["reply"].lower()
    assert body["session_state"] == "lead_email"
    
    # Step 3: User provides invalid email
    response = client.post("/bot/message", json={"sender": sender, "message": "not-an-email"})
    assert response.status_code == 200
    body = response.json()
    assert "valid email" in body["reply"].lower()
    assert body["session_state"] == "lead_email"  # remains in email collection state
    
    # Step 4: User provides valid email
    response = client.post("/bot/message", json={"sender": sender, "message": "ali@safex.com"})
    assert response.status_code == 200
    body = response.json()
    assert "describe your project" in body["reply"].lower() or "requirements" in body["reply"].lower()
    assert body["session_state"] == "lead_requirements"
    
    # Step 5: User provides requirements (Closes Lead Flow, Syncs to CRM)
    response = client.post("/bot/message", json={"sender": sender, "message": "E-commerce store with payment integration"})
    assert response.status_code == 200
    body = response.json()
    assert "touch" in body["reply"].lower() or "captured" in body["reply"].lower()
    assert body["session_state"] == "idle"  # resets to idle
    
    # Verify lead in database
    leads = get_all_leads()
    assert len(leads) == 1
    assert leads[0]["phone"] == sender
    assert leads[0]["name"] == "Ali Hussain"
    assert leads[0]["email"] == "ali@safex.com"
    assert "E-commerce" in leads[0]["requirements"]


@patch("app.core.language.generate_text", side_effect=mock_generate_text)
@patch("app.core.router.generate_text", side_effect=mock_generate_text)
def test_handover_flow(mock_router_gen, mock_lang_gen):
    sender = "+923000000001"
    clear_session(sender)
    
    # Step 1: User explicitly asks for human agent
    response = client.post("/bot/message", json={"sender": sender, "message": "connect me to human"})
    assert response.status_code == 200
    body = response.json()
    assert "agent" in body["reply"].lower() or "human" in body["reply"].lower()
    assert body["intent"] == "human_handover"
    assert body["session_state"] == "handover_active"
    
    # Verify pending ticket exists
    tickets = get_pending_handovers()
    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket["phone"] == sender
    assert ticket["status"] == "pending"
    
    # Step 2: User messages again, bot should remind they are escalated
    response = client.post("/bot/message", json={"sender": sender, "message": "any update?"})
    assert response.status_code == 200
    body = response.json()
    assert "agent has been notified" in body["reply"].lower() or "wait" in body["reply"].lower()
    assert body["session_state"] == "handover_active"
    
    # Step 3: Agent claims ticket via API
    response = client.post(f"/handover/claim?handover_id={ticket['id']}&agent_name=Zain")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Step 4: Agent resolves ticket
    response = client.post(f"/handover/resolve?handover_id={ticket['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify user session is restored to idle
    session = get_session(sender)
    assert session["state"] == "idle"


@patch("app.core.language.generate_text", side_effect=mock_generate_text)
@patch("app.core.router.generate_text", side_effect=mock_generate_text)
def test_multilingual_faq_routing(mock_router_gen, mock_lang_gen):
    sender = "+923000000002"
    clear_session(sender)
    
    # Test Roman Urdu message -> translates to English -> fetches FAQ (which we mock or use DB) -> translates answer back
    # Wait, the FAQ pipeline uses the live ChromaDB. Let's make sure it doesn't fail if ChromaDB is populated
    response = client.post("/bot/message", json={"sender": sender, "message": "office kahan hai?"})
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "roman_urdu"
    assert "office" in body["reply"].lower() or "islamabad" in body["reply"].lower()


@patch("app.core.language.generate_text", side_effect=mock_generate_text)
@patch("app.core.router.generate_text", side_effect=mock_generate_text)
@patch("app.api.routes.send_whatsapp_message")
def test_openwa_webhook_flow(mock_send_whatsapp, mock_router_gen, mock_lang_gen):
    sender_phone = "+923001234567"
    clear_session(sender_phone)
    
    # Send a JSON POST request simulating an OpenWA webhook event
    response = client.post(
        "/bot/whatsapp/webhook",
        json={
            "event": "message.received",
            "data": {
                "from": f"{sender_phone}@c.us",
                "body": "office kahan hai?"
            }
        }
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify that send_whatsapp_message was called to send the reply back to the user
    mock_send_whatsapp.assert_called_once()
    called_args = mock_send_whatsapp.call_args[0]
    assert called_args[0] == f"{sender_phone}@c.us"
    assert "office" in called_args[1].lower() or "islamabad" in called_args[1].lower()

