import json
import re
from datetime import datetime
from mistralai.models.chat_completion import ChatMessage
from utils.extraction import detect_volcano_name

from utils.extraction import detect_volcano_name
from utils.geo_location import extract_indonesia_location, get_geolocation_indonesia
from utils.pipeline_helpers import resolve_api_url, call_api, semantic_recommend_api_improved, safe_json_loads, \
    recommend_api_fallback, model_chat, load_examples, crosscheck_api, find_nearest_volcano, check_if_nearest_question, \
    get_mount_code, fetch_api_simple, filter_history, _detect_volcano_name, check_if_mount_level, BASE_URL, check_around, get_closest_gerakan_tanah_data, is_empty_response
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
from utils.classifier import detect_conversational_intent
from services.check_status_magma import return_status
from datetime import datetime

MAX_WORKERS = 10
pipeline_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
import re

def check_today_query(user_input: str) -> bool:
    text = user_input.lower().strip()

    # Direct phrases (Indonesian + English)
    direct_phrases = [
        "hari ini",
        "today",
        "sekarang",
        "saat ini",
        "right now",
        "currently",
        "as of today",
        "update terbaru",
        "kondisi terkini",
        "terkini"
    ]

    # If direct phrase exists
    if any(p in text for p in direct_phrases):
        return True

    # Regex patterns for flexible matching
    patterns = [
        r"\bhari\s+ini\b",
        r"\btoday('?s)?\b",
        r"\bsaat\s+ini\b",
        r"\bsekarang\b",
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

            Instructions for the answer:
            Use only the information available from the USER QUESTION and the CONVERSATION HISTORY.
            Do not add knowledge or speculation.
            If the information is not sufficient to answer, respond briefly and politely: 
            “Sorry, I’m not sure how to answer this. For accurate information, please refer to the official reports on the MAGMA, VSI, or MBG Portal websites.”
            The answer must be only one paragraph and should not contain lists, bullet points, or any special markers.
            """
    else:

        # Add strict date rule ONLY if user asks about today
        date_rule = ""
        if is_today_query:
            date_rule = f"""
            - Extract ALL event dates from the data.
            - Compare each event date strictly with this date: {current_date}.
            - If the user asks about today AND no event exactly matches {current_date}, 
            ignore all historical events and respond exactly with: "No data about this event today."
            - Do NOT mention older event dates or try to connect them to today.
            """

        return f"""
            The user asked: {user_input}

            Here is the data you must analyze:
            {response_text}

    Your task has two internal stages, but output ONLY the final stage:

    Stage 1 (internal, DO NOT show to the user):
    - Analyze the content of the data thoroughly.
    {date_rule}
    - Identify general volcano conditions, status, visuals, weather, seismicity, hazards, and recommendations.
    - **STATUS MAPPING (MUST FOLLOW EXACTLY)**:
               - If "status" is 1 → Level I (Normal). Always confirm there is no eruption threat.
               - If "status" is 2 → Alert Level II (Waspada)
               - If "status" is 3 → Alert Level III (Siaga)
               - If "status" is 4 → Alert Level IV (Awas)
               - If "status" field is missing or null → DO NOT mention any alert level

    Stage 2 (FINAL OUTPUT – only this must be shown to the user):
    - Write one clear, concise, and natural response in English.
    - Do NOT use titles, numbers, or bullet points.
    - Do NOT fabricate information that does not exist in the data.
    - If Stage 1 determined there is no event for today, respond **exactly**: "No data about this event today."
    - Do NOT add "therefore", "as of today", or references to past dates.

    Mandatory rules:
    - Current date is {current_date}.
    - Use clear, natural, professional English.
    - Keep sentences short and direct.
    - Avoid unusual terminology or unnecessary jargon.
    - Focus on producing a final answer that is easy for the general public to understand.
        """



def analyze_response(user_input, api_response, geo_location=None, max_len=2000):
    response_text = json.dumps(api_response, indent=2, ensure_ascii=False)
    if len(response_text) > max_len:
        response_text = response_text[:max_len]
    location_context = f"\nLokasi pengguna (latitude, longitude): {geo_location}\n" if geo_location else ""
    prompt = build_prompt(user_input, response_text, location_context)

    system_prompt_content = (
        "Anda adalah asisten kebencanaan Indonesia. "
        "Jawab hanya berdasarkan data yang diberikan. "
        "Gunakan Bahasa Indonesia formal dalam satu paragraf. "
        "Tanpa bullet, daftar, atau informasi tambahan di luar data."
    )

    messages = [
        ChatMessage(role="system", content=system_prompt_content),
        ChatMessage(role="user", content=prompt),
    ]

    raw_output = model_chat(messages)
    cleaned_output = GoogleTranslator(source='en', target='id').translate(raw_output)
    return cleaned_output


def is_asking_location(user_input: str) -> bool:
    text = user_input.lower().strip()

    location_terms = r"(lokasi|koordinat|posisi)"
    safety_terms = r"(aman|bahaya|valid|benar|tepat|akurasi|cek|verifikasi)"

    # If asking safety about location -> NOT location request
    if re.search(location_terms, text) and re.search(safety_terms, text):
        return False

    patterns = [
        # dimana saya
        r"(di\s?mana|dimana).*(saya|sy|aku|gw)",

        # saya dimana
        r"(saya|sy|aku|gw).*(di\s?mana|dimana)",

        # lokasi/posisi sekarang
        r"(posisi|lokasi).*(saya|sy|aku|gw|sekarang|skrg)",

        # cek lokasi
        r"(cek|lihat|tahu).*(lokasi|posisi)",

        # koordinat saya
        r"koordinat\s(saya|sy|aku|gw)",

        # apakah anda tau lokasi saya
        r"(tau|tahu|know).*(lokasi|posisi|koordinat).*(saya|sy|aku|gw)"
    ]

    return any(re.search(p, text) for p in patterns)

def is_prefere_current_location(user_input: str) -> bool:
    text = user_input.lower().strip()

    patterns = [
        r"(di\s?mana|dimana).*(saya|aku|sy|gw)",
        r"(saya|aku|sy|gw).*(di\s?mana|dimana)",
        r"(lokasi|posisi).*(saya|aku|sy|gw|sekarang|skrg)",
        r"(cek|lihat|tahu).*(lokasi|posisi).*(saya|aku|sy|gw)?",
        r"koordinat\s(saya|aku|sy|gw)",
        r"(tau|tahu|know).*(lokasi|posisi|koordinat).*(saya|aku|sy|gw)",
        r"(lokasi|posisi)\s*saya\s*(sekarang|skrg)?"
    ]

    return any(re.search(p, text) for p in patterns)

def run_pipeline(user_input: str, geo_location: tuple[float, float], history: str = '', location_name: str=None):
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
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": None,
                "output": response,
                "response": None
            }
        is_asking_level_status= check_if_mount_level(user_input)
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
                    f"Lokasi Anda saat ini berada di {location_name} pada koordinat: {user_lat}, {user_lon}. "
                    "Saat ini kami tidak dapat menemukan data gunung api aktif dalam jangkauan terdekat dari posisi Anda."
                )
            else:
                volcano_name = nearest.get("ga_nama_gapi")
                output_text = (
                    f"Lokasi Anda berada di {location_name} pada {user_lat}, {user_lon}. "
                    f"Gunung api terdekat adalah {volcano_name} dengan estimasi jarak {distance_km} km."
                )

            return {
                "status": "success",
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
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": f"{BASE_URL}/api/v1/home/gunung-api",
                "output": output_text,
                "response": volcano_resp
            }


        filtered_history = filter_history(history, "Mohon maaf, saya kurang yakin")
        enriched_input = (
            "=== HISTORI PERCAKAPAN TERSEDIA ===\n"
            f"{filtered_history}\n\n"
            "=== PERTANYAAN PENGGUNA ===\n"
            f"{user_input}\n\n"
            "=== CATATAN ===\n"
            "Gunakan hanya informasi dari HISTORI jika API gagal atau tidak memberikan data."
        )

        answer = "Mohon maaf, saya kurang yakin. Untuk kepastian, silakan lihat laporan resmi di halaman web MAGMA, VSI, atau Portal MBG."
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
                    "api_call": volcano_url,
                    "output": "Data gunung api tidak tersedia sekarang. Silakan coba kembali."
                }

            nearest, distance_km = find_nearest_volcano(user_lat, user_lon, volcano_resp)
            if not nearest or not nearest.get("ga_code"):
                return {
                    "status": "error",
                    "api_call": "",
                    "output": "Tidak dapat menemukan gunung terdekat berdasarkan lokasi Anda."
                }

            ga_code = nearest["ga_code"]
            var_url = nearest["url"]
            var_resp = fetch_api_simple(var_url)

            if not var_resp:
                return {
                    "status": "error",
                    "api_call": var_url,
                    "output": "Data VAR untuk gunung terdekat tidak tersedia."
                }

            final_answer = analyze_response(
                user_input,
                var_resp,
                [user_lat, user_lon],
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

        if check_if_nearest_question(user_input):
            if not geo_location:
                return {
                    "status": "error",
                    "output": "Mohon berikan lokasi Anda dalam format latitude dan longitude."
                }

            user_lat, user_lon = geo_location

            volcano_url = resolve_api_url("/api/v1/home/gunung-api")
            volcano_resp = get_mount_code()

            if not volcano_resp or "data" not in volcano_resp:
                return {
                    "status": "error",
                    "api_call": volcano_url,
                    "output": "Data gunung api tidak tersedia saat ini."
                }

            nearest, distance_km = find_nearest_volcano(user_lat, user_lon, volcano_resp)
            if not nearest or not nearest.get("ga_code"):
                return {
                    "status": "error",
                    "api_call": "",
                    "output": "Tidak dapat menemukan gunung terdekat berdasarkan lokasi Anda."
                }

            ga_code = nearest["ga_code"]
            var_url = nearest["url"]
            var_resp = fetch_api_simple(var_url)

            if not var_resp:
                return {
                    "status": "error",
                    "api_call": var_url,
                    "output": "Data VAR untuk gunung terdekat tidak tersedia."
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

            # Always reset cache each attempt
            rec, cache = semantic_recommend_api_improved(user_input, examples, filtered_history, cache=None,
                                                         volcano_code=volcano_code, nearest_volcano=nearest)

            apis = rec.get("recommended_api", [])
            oos_status = rec.get("out_of_scope", False)
            # If no APIs found → fallback
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
                    "output": "Mohon maaf, saya kurang yakin. Untuk kepastian, silakan lihat laporan resmi di halaman web MAGMA, VSI, atau Portal MBG."
                }

            # Safe indexing
            recommended_api = apis[current_index]
            print("Recommended API:", recommended_api)

            # Validate
            if crosscheck_api(recommended_api, examples):
                print("✅ Validated recommended API:", recommended_api)
                break
            else:
                print("❌ API not found in JSON, retrying...")

        # Step 2: Handle failure after retries
        if not recommended_api or not crosscheck_api(recommended_api, examples):
            return {
                "status": "error",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": "",
                "output": answer,
                "last_recommended_api": recommended_api,
                "reason": rec.get("reason"),
            }

        api_url = resolve_api_url(recommended_api)
        method = rec.get("method", "GET").upper()
        params = rec["parameters"][current_index] or {}
        body = rec["body"][current_index] or {}

        uuid_match = re.search(r"uuid\s*([a-zA-Z0-9\-]+)", user_input.lower())
        code_match = re.search(r"kode\s*([A-Z]{3,})|code\s*([A-Z]{3,})", user_input)
        id_match = re.search(r"id\s*(\d+)", user_input.lower())
        volcano_code = rec.get("volcano_code")

        if "{uuid}" in api_url and uuid_match:
            uuid_value = uuid_match.group(1)
            api_url = api_url.replace("{uuid}", uuid_value)

        if volcano_code and body is not None:

            if isinstance(body, list) and len(body) > 0:
                first = body[0]
                if isinstance(first, dict):
                    first["code"] = volcano_code
            elif isinstance(body, dict):
                body["code"] = volcano_code
        elif code_match and body is not None:
            code_value = code_match.group(1) or code_match.group(2)
            api_url = api_url.replace("{code}", code_value)
            body["code"] = code_value

        if "{id}" in api_url and id_match:
            id_value = id_match.group(1)
            api_url = api_url.replace("{id}", id_value)

        print(f"Resolved API URL: {api_url}")
        print(f"HTTP Method: {method}")
        print(f"Params: {params}")
        print(f"Body: {body}")

        # Step 2: Call API
       
        isCheckedAround= check_around(user_input)
        print(f"User input = {user_input} with isCheckedAround = {isCheckedAround}")

        if isCheckedAround and "/api/v1/home/gerakan-tanah" in api_url:
            user_lat, user_lon = geo_location
            api_response = get_closest_gerakan_tanah_data(api_url, user_lat, user_lon, method, params, body)
            if api_response:
                print("Closest data found:", api_response)
            else:
                print("No nearby data found.")

            answer = analyze_response(user_input, api_response, geo_location)
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_url,
                "output": answer,
                "response": api_response
            }
        else:
             api_response = call_api(api_url, method=method, params=params, body=body)


        max_tries = len(rec["recommended_api"])

        while is_empty_response(api_response) and current_index < max_tries - 1:
            current_index += 1
            recommended_api = rec["recommended_api"][current_index]
            api_url = resolve_api_url(recommended_api)
            params = rec["parameters"][current_index] or {}
            body = rec["body"][current_index] or {}
            api_response = call_api(api_url, method=method, params=params, body=body)

        # ----------------- Post-retry checks -----------------
        if is_empty_response(api_response):
            print("⚠️ No more recommended APIs to try or response is empty.")
            empty_data_for_llm = {
                "status": "empty_data",
                "message": "API berhasil dipanggil tetapi tidak mengembalikan data.",
                "context_history": history,
                "latest_query": user_input
            }
            answer = (
                analyze_response(enriched_input, empty_data_for_llm, geo_location)
                if filtered_history else
                "Mohon maaf, saya kurang yakin untuk menjawab pertanyaan ini. "
                "Untuk informasi akurat, silakan merujuk pada laporan resmi di situs MAGMA, VSI, atau Portal MBG."
            )
            return {
                "status": "error",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_url,
                "output": answer,
                "response": empty_data_for_llm
            }

        # ----------------- Technical errors -----------------
        if isinstance(api_response, dict) and "error" in api_response:
            print("⚠️ API returned a technical error. Analyzing context for a fallback answer.")
            error_data_for_llm = {
                "status": "error",
                "message": f"Gagal mendapatkan data dari API: {api_response['error']}",
                "context_history": history,
                "latest_query": user_input
            }
            answer = (
                analyze_response(enriched_input, error_data_for_llm, geo_location)
                if filtered_history else
                "Mohon maaf, saya kurang yakin untuk menjawab pertanyaan ini. "
                "Untuk informasi akurat, silakan merujuk pada laporan resmi di situs MAGMA, VSI, atau Portal MBG."
            )
            return {
                "status": "error",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_url,
                "output": answer,
                "response": api_response
            }

        # ----------------- Step 3: Analyze valid response -----------------
        answer = analyze_response(
            user_input,
            api_response.get('data', api_response) if isinstance(api_response, dict) else api_response,
            geo_location
        )
        return {
            "status": "success",
            "date": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "geo_location": geo_location,
            "api_call": api_url,
            "output": answer,
            "response": api_response.get('data', api_response) if isinstance(api_response, dict) else api_response
        }
    except Exception as e:
        print("Error in the pipeline: ", e)

