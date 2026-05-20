import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    # your real root handler returns extra info
    assert "message" in response.json()
    assert response.json()["message"] == "OpenAI-compatible API server running"

def test_models(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)
    if data["data"]:
        assert "id" in data["data"][0]

def test_chat_completion(client):
    payload = {
        "model": "tinyllama-1.1b-chat",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "choices" in data

def test_model_info(client):
    response = client.get("/v1/models/tinyllama-1.1b-chat")
    assert response.status_code in (200, 404)
