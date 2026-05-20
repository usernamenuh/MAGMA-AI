#!/usr/bin/env python3
"""
Test client for OpenAI-compatible API server
Demonstrates both streaming and non-streaming requests
"""

import requests
import json
import sys
import os
from typing import List, Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8002"
MODEL_NAME = "tinyllama-1.1b-chat"  # Update this to match your model
API_KEY = os.getenv("API_KEY", "")  # Get API key from environment


def get_headers():
    """Get request headers with optional Bearer token"""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def check_models_endpoint():
    """Test the /v1/models endpoint"""
    print("\n" + "="*50)
    print("Testing /v1/models endpoint...")
    print("="*50)
    
    response = requests.get(f"{API_BASE_URL}/v1/models", headers=get_headers())
    if response.status_code == 200:
        models = response.json()
        print(f"✅ Success! Found {len(models['data'])} models:")
        for model in models['data']:
            print(f"  - {model['id']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    
    return response.status_code == 200


def check_chat_completion(messages: List[Dict[str, str]], stream: bool = False):
    """Test the /v1/chat/completions endpoint"""
    print("\n" + "="*50)
    print(f"Testing /v1/chat/completions (stream={stream})...")
    print("="*50)
    
    # Print the conversation
    print("\nConversation:")
    for msg in messages:
        print(f"  {msg['role'].upper()}: {msg['content']}")
    
    # Prepare request
    request_data = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512,
        "stream": stream
    }
    
    print("\nSending request...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json=request_data,
            headers=get_headers(),
            stream=stream
        )
        
        if response.status_code == 200:
            print("✅ Success! Response:")
            print("-" * 30)
            
            if stream:
                # Handle streaming response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and data['choices']:
                                    delta = data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        print(content, end='', flush=True)
                                        full_response += content
                            except json.JSONDecodeError:
                                pass
                print("\n" + "-" * 30)
                print(f"\nFull response length: {len(full_response)} characters")
            else:
                # Handle non-streaming response
                data = response.json()
                assistant_message = data['choices'][0]['message']['content']
                print(assistant_message)
                print("-" * 30)
                print(f"\nUsage:")
                print(f"  Prompt tokens: {data['usage']['prompt_tokens']}")
                print(f"  Completion tokens: {data['usage']['completion_tokens']}")
                print(f"  Total tokens: {data['usage']['total_tokens']}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        print(f"   Make sure the server is running at {API_BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


def test_openai_client():
    """Test using the official OpenAI Python client"""
    print("\n" + "="*50)
    print("Testing with OpenAI Python client...")
    print("="*50)
    
    try:
        from openai import OpenAI
        
        # Configure client to use local API
        client = OpenAI(
            api_key=API_KEY or "not-needed",  # Use API key if configured
            base_url=f"{API_BASE_URL}/v1"
        )
        
        # Test chat completion
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is Python?"}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        print("✅ Success! Response from OpenAI client:")
        print("-" * 30)
        print(response.choices[0].message.content)
        print("-" * 30)
        
        # Test streaming
        print("\n🔄 Testing streaming with OpenAI client...")
        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": "Count from 1 to 5"}
            ],
            stream=True,
            max_tokens=50
        )
        
        print("Response: ", end="")
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()
        
        return True
        
    except ImportError:
        print("⚠️  OpenAI Python client not installed")
        print("   Install with: pip install openai")
        print("   This is optional - the API works with any HTTP client")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# Pytest tests that use proper test structure
def test_models_endpoint():
    """Pytest test for models endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/v1/models", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    except requests.exceptions.ConnectionError:
        # Skip test if server is not running
        import pytest
        pytest.skip("Server not running")


def test_chat_completion():
    """Pytest test for chat completion"""
    try:
        request_data = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 50
        }
        
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json=request_data,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
    except requests.exceptions.ConnectionError:
        # Skip test if server is not running
        import pytest
        pytest.skip("Server not running")


def main():
    """Run all tests"""
    print("\n🚀 OpenAI-Compatible API Test Client")
    print("="*60)
    
    # Check if server is running
    try:
        response = requests.get(API_BASE_URL)
        print(f"✅ Server is running at {API_BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {API_BASE_URL}")
        print("\nPlease start the server first:")
        print("  python main.py")
        sys.exit(1)
    
    # Run tests
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Models endpoint
    tests_total += 1
    if check_models_endpoint():
        tests_passed += 1
    
    # Test 2: Simple chat completion
    tests_total += 1
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! Can you tell me a fun fact?"}
    ]
    if check_chat_completion(messages, stream=False):
        tests_passed += 1
    
    # Test 3: Streaming chat completion
    tests_total += 1
    messages = [
        {"role": "user", "content": "Write a haiku about programming"}
    ]
    if check_chat_completion(messages, stream=True):
        tests_passed += 1
    
    # Test 4: Multi-turn conversation
    tests_total += 1
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "What is recursion?"},
        {"role": "assistant", "content": "Recursion is a programming technique where a function calls itself to solve a problem by breaking it down into smaller subproblems."},
        {"role": "user", "content": "Can you give a simple example?"}
    ]
    if check_chat_completion(messages, stream=False):
        tests_passed += 1
    
    # Test 5: OpenAI client (optional)
    test_openai_client()  # Don't count this in tests_total as it's optional
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("✅ All tests passed!")
    else:
        print(f"⚠️  {tests_total - tests_passed} test(s) failed")
    
    print("\n💡 Tip: You can use this API with any OpenAI-compatible client:")
    print("   - OpenAI Python SDK")
    print("   - LangChain")
    print("   - Curl/HTTP requests")
    print("   - Any application that supports OpenAI API")


if __name__ == "__main__":
    main() 