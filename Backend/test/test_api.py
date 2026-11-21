import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ["LLM_API_KEYS"] = "fake_key_1,fake_key_2"
os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _mock_response(text="Paris", cache_hit=False):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5),
        _hidden_params={"cache_hit": cache_hit},
    )


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["keys_configured"] == 2
    assert body["cache_enabled"] is True


def test_validation_422():
    res = client.post("/chat", json={"session_id": "s-1", "message": "   "})
    assert res.status_code == 422


@patch("app.llm.litellm.completion")
def test_chat_and_failover(mock_comp):
    mock_comp.return_value = _mock_response("Paris", cache_hit=False)

    # Simulate key_1 failing -> should fall back to key_2
    res = client.post(
        "/chat",
        headers={"X-Simulate-Failure": "key_1=429"},
        json={"session_id": "s-failover", "message": "Capital of France?"},
    )
    assert res.status_code == 200
    meta = res.json()["metadata"]
    assert meta["key_id"] == "key_2"
    assert meta["fallback_attempts"] == 1

    # Simulate all keys failing -> 503 and nothing saved
    res_503 = client.post(
        "/chat",
        headers={"X-Simulate-Failure": "*=429"},
        json={"session_id": "s-all-fail", "message": "Hello"},
    )
    assert res_503.status_code == 503
    assert res_503.json() == {"detail": "all providers unavailable"}

    res_404 = client.get("/sessions/s-all-fail/messages")
    assert res_404.status_code == 404