import os
import json
import re

import requests
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

# ----------------------------
# Setup Mistral client
# ----------------------------
client = MistralClient(
    api_key="kN6YbiRPMY06W3xOX9CgD2oG7ufA5BaH",
    timeout=300
)

BASE_URL = "https://magma.esdm.go.id"

# ----------------------------
# Load Postman Examples
# ----------------------------
def load_examples(path="simplified_endpoints_full_with_body.json"):
    with open(path, "r") as f:
        return json.load(f)
def safe_json_loads(s: str):
    """Clean model output and parse JSON safely."""
    s = s.strip()

    # Remove Markdown fences like ```json ... ```
    if s.startswith("```"):
        # Remove first and last code fence
        s = re.sub(r"^```(?:json)?", "", s.strip(), flags=re.IGNORECASE).strip()
        if s.endswith("```"):
            s = s[:-3].strip()

    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        print("⚠️ Failed to parse JSON:", e)
        print("Raw string was:\n", s)
        return {}
def summarize_examples(examples):
    summarized = []
    for ex in examples:
        try:
            data = json.loads(ex["response_model"])
            fields = list(data.keys())
        except Exception:
            fields = []
        summarized.append({
            "api": ex["api"],
            "fields": fields
        })
    return summarized

# ----------------------------
# Step 1: Recommend API
# ----------------------------
def recommend_api(user_input, examples, client):
    summarized = summarize_examples(examples)

    messages = [
        ChatMessage(
            role="system",
            content="You are an assistant that selects the most relevant API for the user input."
        ),
        ChatMessage(
            role="user",
            content=(
                f"User input: {user_input}\n\n"
                f"Available APIs:\n{json.dumps(summarized[:20], indent=2)}\n\n"
                # "Return only the recommended api \n"
                "Return JSON in the format:\n"
                "{ \"recommended_api\": \"<api>\", \"reason\": \"<short reason>\" }"
            )
        )
    ]


    response = client.chat(
        model="mistral-large-latest",
        messages=messages
    )
    return response.choices[0].message.content


# ----------------------------
# Step 2: Call API
# ----------------------------
def call_api(api_url, params=None):
    response = requests.get(api_url, params=params)
    response.raise_for_status()
    return response.json()

def resolve_api_url(api_url: str) -> str:
    """Replace Postman {{url}} placeholder with BASE_URL."""
    if not api_url:
        return ""
    return api_url.replace("{{url}}", BASE_URL.rstrip("/"))

# ----------------------------
# Step 3: Analyze API Response
# ----------------------------
def analyze_response(user_input, api_response, client, max_len=2000):
    """
    Analyze API response with Mistral based on user input.
    """
    # Serialize API response safely
    response_text = json.dumps(api_response, indent=2, ensure_ascii=False)

    # Truncate if too long
    if len(response_text) > max_len:
        response_text = response_text[:max_len] + "\n... (truncated)"

    prompt = f"""
    The user asked: {user_input}

    Here is the API response:
    {response_text}

    Provide a clear, concise, and helpful answer for the user
    based only on the given response.
    """

    messages = [
        ChatMessage(role="user", content=prompt)
    ]

    resp = client.chat(
        model="mistral-large-latest",
        messages=messages
    )

    return resp.choices[0].message.content


# ----------------------------
# Full Pipeline
# ----------------------------
if __name__ == "__main__":
    user_input = "Show me the latest volcanic activity that happened in this year"

    # Load API examples (from exported Postman examples)
    examples = load_examples("simplified_endpoints_full.json")

    for i in range(1,3):
        # Step 1: Recommend API
        rec_raw = recommend_api(user_input, examples, client)
        print("API Recommendation:", rec_raw)

        rec = safe_json_loads(rec_raw)

        api_url = rec.get("recommended_api")
        reason = rec.get("reason")

        print("API Recommendation:", api_url)
        print("Reason:", reason)

        # Step 2: Call API
        api_url = resolve_api_url(rec.get("recommended_api"))
        api_response = call_api(api_url)

        # Step 3: Analyze Response
        answer = analyze_response(user_input, api_response, client)
        print(f"Final Answer {i}:", answer)
