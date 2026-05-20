import json
import re
from datetime import datetime
from mistralai.models.chat_completion import ChatMessage
from utils.extraction import detect_volcano_name

from utils.extraction import detect_volcano_name
from utils.geo_location import extract_indonesia_location, get_geolocation_indonesia
from utils.pipeline_helpers import resolve_api_url, call_api, semantic_recommend_api_improved_en, safe_json_loads, \
    recommend_api_fallback, model_chat, load_examples, crosscheck_api, find_nearest_volcano, check_if_nearest_question, \
    get_mount_code, fetch_api_simple, filter_history, _detect_volcano_name, check_if_mount_level, BASE_URL, check_around, get_closest_gerakan_tanah_data, is_empty_response
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
from utils.classifier import detect_conversational_intent
from services.check_status_magma import return_status
from datetime import datetime

MAX_WORKERS = 10
pipeline_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def check_today_query(user_input: str) -> bool:
    text = user_input.lower().strip()

    # Direct phrases (English only)
    direct_phrases = [
        "today",
        "now",
        "right now",
        "currently",
        "as of today",
        "latest update",
        "latest condition",
        "current condition",
        "recent update"
    ]

    if any(p in text for p in direct_phrases):
        return True

    patterns = [
        r"\btoday('?s)?\b",
        r"\bright\s+now\b",
        r"\bcurrently\b",
        r"\bas\s+of\s+today\b"
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def build_prompt(user_input, response_text, location_context=""):
    is_failure = '"status": "error"' in response_text or '"status": "empty_data"' in response_text
    current_date = datetime.now().strftime("%Y-%m-%d")

    is_today_query = check_today_query(user_input)

    if is_failure:
        return f"""
The user asked: {user_input}
{location_context}

Instructions:
Use only the information from the USER QUESTION and CONVERSATION HISTORY.
Do not add external knowledge or speculation.

If the information is insufficient, respond exactly:
"Sorry, I’m not sure how to answer this. For accurate information, please refer to the official reports on the MAGMA, VSI, or MBG Portal websites."

The answer must be one paragraph only, without bullet points or lists.
"""
    else:
        date_rule = ""
        if is_today_query:
            date_rule = f"""
- Extract ALL event dates from the data.
- Compare each event date strictly with: {current_date}.
- If no event matches exactly {current_date}, respond EXACTLY:
  "No data about this event today."
- Do NOT mention older data or relate it to today.
"""

        return f"""
The user asked: {user_input}

Data:
{response_text}

Your task has two internal stages, but output ONLY the final result:

Stage 1 (internal, DO NOT show):
- Analyze all data thoroughly.
{date_rule}
- Identify volcano condition, status, visuals, weather, seismicity, hazards, and recommendations.
- STATUS MAPPING (STRICT):
    1 → Level I (Normal, no eruption threat)
    2 → Level II (Waspada)
    3 → Level III (Siaga)
    4 → Level IV (Awas)
    Missing → Do NOT mention alert level

Stage 2 (FINAL OUTPUT ONLY):
- One clear and concise paragraph in English
- No bullet points, numbering, or titles
- No hallucination
- If no data for today → EXACT:
  "No data about this event today."
- Do NOT mention past dates

Rules:
- Current date: {current_date}
- Use clear, simple, professional English
- Keep sentences short
- Avoid unnecessary technical jargon
- Make it easy for general users to understand
"""

def inject_path_params(url: str, body: dict | None):
    if not body:
        return url

    if "{code}" in url and body.get("code"):
        url = url.replace("{code}", str(body["code"]))

    if "{id}" in url and body.get("id"):
        url = url.replace("{id}", str(body["id"]))

    return url

def clean_body(body: dict | None):
    if not body:
        return None
    return {k: v for k, v in body.items() if v is not None}

def analyze_response(user_input, api_response, geo_location=None, max_len=2000):
    response_text = json.dumps(api_response, indent=2, ensure_ascii=False)

    if len(response_text) > max_len:
        response_text = response_text[:max_len]

    location_context = (
        f"\nUser location (latitude, longitude): {geo_location}\n"
        if geo_location else ""
    )

    prompt = build_prompt(user_input, response_text, location_context)

    system_prompt_content = (
        "You are a disaster information assistant. "
        "Answer only based on the provided data. "
        "Use clear and professional English in one paragraph. "
        "Do not use bullet points or add external information."
    )

    messages = [
        ChatMessage(role="system", content=system_prompt_content),
        ChatMessage(role="user", content=prompt),
    ]

    return model_chat(messages)


def is_asking_location(user_input: str) -> bool:
    text = user_input.lower().strip()

    location_terms = r"(location|coordinates|position)"
    safety_terms = r"(safe|danger|valid|correct|accurate|check|verify)"

    # If asking safety about location → NOT a location query
    if re.search(location_terms, text) and re.search(safety_terms, text):
        return False

    patterns = [
        r"(where.*(am i|my location))",
        r"(my location.*where)",
        r"(location|position).*(now|current|me)",
        r"(check|see|show).*(location|position)",
        r"(my).*coordinates",
        r"(do you know).*(my location|position|coordinates)"
    ]

    return any(re.search(p, text) for p in patterns)


def is_prefere_current_location(user_input: str) -> bool:
    text = user_input.lower().strip()

    patterns = [
        r"(where.*am i)",
        r"(my location.*where)",
        r"(location|position).*(now|current|me)",
        r"(check|see|show).*(location|position)",
        r"(my).*coordinates",
        r"(do you know).*(my location|position|coordinates)",
        r"(my location)\s*(now|current)?"
    ]

    return any(re.search(p, text) for p in patterns)


def run_pipeline_en(user_input: str, geo_location: tuple[float, float], history: str = '', location_name: str=None):
    try:
        intent, response = detect_conversational_intent(user_input, geo_location)
        volcano_url = resolve_api_url("/api/v1/home/gunung-api")
        volcano_resp = get_mount_code()

        # normalize data
        if not volcano_resp or "error" in volcano_resp:
            cached = load_volcano_cache()
            if cached:
                volcano_resp = cached
            else:
                volcano_resp = None
        if volcano_resp:
            volcano_code = _detect_volcano_name(user_input, volcano_resp)
        else:
            volcano_code = detect_volcano_name(user_input)

        print(f"Volcano code detected: {volcano_code}")
        print(f"Detected intent: {intent} Response: {response}")
        standard_intents = [
            "capability", "count_list_query", "general_chat",
            "greeting", "identity", "location_required", "out_of_scope", "status"
        ]
        if intent in standard_intents:
            return {
                "status": "success",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": None,
                "output": response,
                "response": None
            }

        is_asking_level_status = check_if_mount_level(user_input)
        print(f"Is asking level status:: {is_asking_level_status}")
        asking_loc = is_asking_location(user_input)
        print(f"Is asking location status:: {asking_loc}")

        user_lat, user_lon = geo_location
        nearest, distance_km = find_nearest_volcano(user_lat, user_lon, volcano_resp)

        if is_prefere_current_location(user_input) and geo_location:
            print(f"User prefers current location. Overriding nearest volcano detection: {nearest} with geolocation {geo_location}")
            volcano_code = nearest.get("ga_code") if nearest else None

        if intent == "technical" and asking_loc:
            print(f"Nearest volcano: {nearest}, Distance: {distance_km} km")
            print(f"Location Name: {location_name}")

            if not nearest or not nearest.get("ga_nama_gapi"):
                output_text = (
                    f"Your current location is {location_name} at coordinates: {user_lat}, {user_lon}. "
                    "We could not find any active volcano data near your location at this time."
                )
            else:
                volcano_name = nearest.get("ga_nama_gapi")
                output_text = (
                    f"Your location is {location_name} at {user_lat}, {user_lon}. "
                    f"The nearest volcano is {volcano_name} with an estimated distance of {distance_km} km."
                )

            return {
                "status": "success",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": None,
                "output": output_text,
                "response": None
            }

        elif is_asking_level_status and not volcano_code:
            output_text = return_status(user_input)
            return {
                "status": "success",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": f"{BASE_URL}/api/v1/home/gunung-api",
                "output": output_text,
                "response": volcano_resp
            }

        filtered_history = filter_history(history, "Sorry, I am not sure")
        enriched_input = (
            "=== AVAILABLE CONVERSATION HISTORY ===\n"
            f"{filtered_history}\n\n"
            "=== USER QUESTION ===\n"
            f"{user_input}\n\n"
            "=== NOTE ===\n"
            "Use only information from HISTORY if the API fails or does not return data."
        )

        answer = "Sorry, I’m not sure. For accurate information, please refer to official reports on the MAGMA, VSI, or MBG Portal websites."
        examples = load_examples("simplified_endpoints_full_with_body.json")

        current_index = 0
        max_attempts = 2
        attempt = 0
        recommended_api = None
        rec = {}
        oos_status = False

        location_name = extract_indonesia_location(user_input)
        if location_name:
            user_lat, user_lon = get_geolocation_indonesia(location_name)

            if not volcano_resp:
                return {
                    "status": "error",
                    "intent": intent,
                    "api_call": volcano_url,
                    "output": "Volcano data is currently unavailable. Please try again later."
                }

            nearest, distance_km = find_nearest_volcano(user_lat, user_lon, volcano_resp)
            if not nearest or not nearest.get("ga_code"):
                return {
                    "status": "error",
                    "intent": intent,
                    "api_call": "",
                    "output": "Unable to find the nearest volcano based on your location."
                }

            ga_code = nearest["ga_code"]
            var_url = nearest["url"]
            var_resp = fetch_api_simple(var_url)

            if not var_resp:
                return {
                    "status": "error",
                    "intent": intent,
                    "api_call": var_url,
                    "output": "VAR data for the nearest volcano is not available."
                }

            final_answer = analyze_response(
                user_input,
                var_resp,
                [user_lat, user_lon],
            )

            return {
                "status": "success",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "nearest_volcano": {
                    "name": nearest.get("ga_nama_gapi"),
                    "code": ga_code,
                    "distance_km": round(distance_km, 2)
                },
                "api_call": var_url,
                "output": final_answer,
                "response": var_resp["data"]
            }

        if check_if_nearest_question(user_input):
            if not geo_location:
                return {
                    "status": "error",
                    "output": "Please provide your location in latitude and longitude format."
                }

            user_lat, user_lon = geo_location

            volcano_url = resolve_api_url("/api/v1/home/gunung-api")
            volcano_resp = get_mount_code()

            if not volcano_resp or "data" not in volcano_resp:
                return {
                    "status": "error",
                    "api_call": volcano_url,
                    "output": "Volcano data is currently unavailable."
                }

            nearest, distance_km = find_nearest_volcano(user_lat, user_lon, volcano_resp)
            if not nearest or not nearest.get("ga_code"):
                return {
                    "status": "error",
                    "api_call": recommended_api if recommended_api else "",
                    "output": "Unable to find the nearest volcano based on your location."
                }

            ga_code = nearest["ga_code"]
            var_url = nearest["url"]
            var_resp = fetch_api_simple(var_url)

            if not var_resp:
                return {
                    "status": "error",
                    "api_call": var_url,
                    "output": "VAR data for the nearest volcano is not available."
                }

            final_answer = analyze_response(
                user_input,
                var_resp,
                geo_location
            )

            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "nearest_volcano": {
                    "name": nearest.get("ga_nama_gapi"),
                    "code": ga_code,
                    "distance_km": round(distance_km, 2)
                },
                "api_call": var_url,
                "output": final_answer,
                "response": var_resp["data"]
            }

        while attempt < max_attempts:
            attempt += 1

            rec, cache = semantic_recommend_api_improved_en(
                user_input, examples, filtered_history, cache=None,
                volcano_code=volcano_code, nearest_volcano=nearest
            )

            apis = rec.get("recommended_api", [])
            oos_status = rec.get("out_of_scope", False)

            if not apis:
                print("⚠️ No API recommended (out-of-scope detected). Using fallback.")
                rec = safe_json_loads(recommend_api_fallback(user_input, examples))
                apis = rec.get("recommended_api", [])

            if not apis:
                print("❌ No valid API found even after fallback.")
                return {
                    "status": "error",
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "output": answer
                }

            recommended_api = apis[current_index]
            print("Recommended API:", recommended_api)

            if crosscheck_api(recommended_api, examples):
                print("✅ Validated recommended API:", recommended_api)
                break
            else:
                print("❌ API not found in JSON, retrying...")

        if not recommended_api or not crosscheck_api(recommended_api, examples):
            return {
                "status": "error",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": recommended_api if recommended_api else "",
                "output": answer,
                "last_recommended_api": recommended_api,
                "reason": rec.get("reason"),
            }

        api_url = resolve_api_url(recommended_api)
        method = rec.get("method", "GET").upper()

        params_list = rec.get("parameters") or []
        body_list = rec.get("body") or []

        params = params_list[current_index] if current_index < len(params_list) else {}
        body = body_list[current_index] if current_index < len(body_list) else {}

        params = params or {}
        body = body or {}

        body = clean_body(body)
        api_url = inject_path_params(api_url, body)

        print(f"Resolved API URL: {api_url}")
        print(f"HTTP Method: {method}")
        print(f"Params: {params}")
        print(f"Body: {body}")

        isCheckedAround = check_around(user_input)
        print(f"User input = {user_input} with isCheckedAround = {isCheckedAround}")

        if isCheckedAround and "/api/v1/home/gerakan-tanah" in api_url:
            user_lat, user_lon = geo_location
            api_response = get_closest_gerakan_tanah_data(api_url, user_lat, user_lon, method, params, body)

            answer = analyze_response(user_input, api_response, geo_location)
            return {
                "status": "success",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_url,
                "output": answer,
                "response": api_response
            }
        else:
            api_response = call_api(api_url, method=method, params=params, body=body)

        print(f"API response: {api_response}")
        max_tries = len(rec["recommended_api"])

        while is_empty_response(api_response) and current_index < max_tries - 1:
            current_index += 1
            recommended_api = rec["recommended_api"][current_index]
            api_url = resolve_api_url(recommended_api)
            params = rec["parameters"][current_index] or {}
            body = rec["body"][current_index] or {}

            api_response = call_api(api_url, method=method, params=params, body=body)

        if is_empty_response(api_response):
            empty_data_for_llm = {
                "status": "empty_data",
                "message": "API returned no data",
                "context_history": history,
                "latest_query": user_input
            }

            answer = (
                analyze_response(enriched_input, empty_data_for_llm, geo_location)
                if filtered_history else
                "Sorry, I’m not sure. For accurate information, please refer to official reports on the MAGMA, VSI, or MBG Portal websites."
            )

            return {
                "status": "error",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_url,
                "output": answer,
                "response": empty_data_for_llm
            }
            
        if isinstance(api_response, dict) and "error" in api_response:
            error_data_for_llm = {
                "status": "error",
                "message": f"API error: {api_response['error']}",
                "context_history": history,
                "latest_query": user_input
            }

            answer = (
                analyze_response(enriched_input, error_data_for_llm, geo_location)
                if filtered_history else
                "Sorry, I’m not sure. For accurate information, please refer to official reports on the MAGMA, VSI, or MBG Portal websites."
            )

            return {
                "status": "error",
                "intent": intent,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_url,
                "output": answer,
                "response": api_response
            }    

        answer = analyze_response(
            user_input,
            api_response.get('data', api_response) if isinstance(api_response, dict) else api_response,
            geo_location
        )
        print(f"Final answer: {answer}")
        return {
            "status": "success",
            "intent": intent,
            "date": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "geo_location": geo_location,
            "api_call": api_url,
            "output": answer,
            "response": api_response.get('data', api_response) if isinstance(api_response, dict) else api_response
        }

    except Exception as e:
        print("Error in the pipeline: ", e)