import pytest
from openai import OpenAI
from fastapi.testclient import TestClient
from main import app

def test_openai_compatibility():
    """Test OpenAI client compatibility with our local server"""
    # Use FastAPI TestClient instead of making real HTTP requests
    with TestClient(app) as test_client:
        # Create OpenAI client that uses the test client
        # Note: We can't directly use OpenAI client with TestClient,
        # so we'll test the API endpoints directly
        
        # Define a function for tool calling
        tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"]
                        }
                    },
                    "required": ["location"]
                }
            }
        }]

        # Test basic chat completion
        payload = {
            "model": "tinyllama-1.1b-chat",
            "messages": [{"role": "user", "content": "What's the weather in New York?"}],
            "tools": tools,
            "tool_choice": "auto"
        }
        
        response = test_client.post("/v1/chat/completions", json=payload)
        
        # Basic assertions
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        
        # Check if response has the expected structure
        choice = data["choices"][0]
        assert "message" in choice
        
        print(f"✅ OpenAI compatibility test passed")
        if choice["message"].get("tool_calls"):
            for tool_call in choice["message"]["tool_calls"]:
                print(f"Function: {tool_call['function']['name']}")
                print(f"Arguments: {tool_call['function']['arguments']}")

def test_openai_models_endpoint():
    """Test that the models endpoint works"""
    with TestClient(app) as test_client:
        response = test_client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)