import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/faq/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["faqs_loaded"] > 0


def test_query_returns_expected_shape():
    response = client.post("/faq/query", json={"question": "what is your email address"})
    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "confidence" in body
    assert "is_confident" in body
    assert 0.0 <= body["confidence"] <= 1.0


def test_query_rejects_empty_question():
    response = client.post("/faq/query", json={"question": "   "})
    assert response.status_code == 400


def test_query_matches_correct_faq_for_clear_question():
    response = client.post("/faq/query", json={"question": "what are your office hours"})
    body = response.json()
    assert body["is_confident"] is True
    assert body["matched_faq_id"] == "CON005"


def test_list_all_leads():
    response = client.get("/leads/all")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)

