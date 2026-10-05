import json
import re
from datetime import datetime
from mistralai.models.chat_completion import ChatMessage
from utils.extraction import detect_volcano_name

from utils.extraction import detect_volcano_name
from utils.geo_location import extract_indonesia_location, get_geolocation_indonesia
from utils.pipeline_helpers import resolve_api_url, call_api, semantic_recommend_api_improved, safe_json_loads, \
    recommend_api_fallback, model_chat, load_examples, crosscheck_api, find_nearest_volcano, check_if_nearest_question, \
    get_mount_code, get_today_eruption_events, fetch_api_simple, filter_history, _detect_volcano_name, check_if_mount_level, BASE_URL, check_around, get_closest_gerakan_tanah_data, is_empty_response, load_volcano_cache
from concurrent.futures import ThreadPoolExecutor
from utils.classifier import detect_conversational_intent
from services.check_status_magma import return_status
from utils.query_normalizer import normalize_indonesian_query
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


def contextual_safety_followup(user_input: str, history: str) -> str | None:
    """Answer short safety follow-ups using the previous question's topic."""
    if not history or len(user_input.split()) > 8:
        return None
    if not re.search(r"\b(aman|bahaya|berbahaya)\b", user_input, re.IGNORECASE):
        return None

    previous_questions = re.findall(r"(?m)^user: (.*)$", history)
    if not previous_questions:
        return None
    previous_question = previous_questions[-1].lower()
    if re.search(r"\b(gempa|gempabumi)\b", previous_question):
        return (
            "Belum bisa dipastikan aman. Informasi gempa terkini pada jawaban sebelumnya "
            "belum terverifikasi, sehingga saya tidak bisa menilai kondisi di lokasi Anda. "
            "Periksa pembaruan resmi BMKG dan ikuti arahan BPBD setempat."
        )
    if re.search(r"\b(gunung|erupsi|letusan)\b", previous_question):
        return (
            "Belum bisa disimpulkan aman hanya dari status atau laporan sebelumnya. "
            "Kondisi dan zona bahaya dapat berubah; ikuti rekomendasi terbaru PVMBG "
            "untuk gunung dan lokasi yang dimaksud."
        )
    return None

def build_prompt(user_input, response_text, location_context=""):
    is_failure = '"status": "error"' in response_text or '"status": "empty_data"' in response_text
    current_date = datetime.now().strftime("%Y-%m-%d")

    is_today_query = check_today_query(user_input)

    if is_failure:
        return f"""
            Pertanyaan pengguna: {user_input}
            {location_context}

            Instruksi jawaban:
            Gunakan hanya informasi dari PERTANYAAN PENGGUNA dan RIWAYAT PERCAKAPAN.
            Jangan menambahkan pengetahuan atau spekulasi.
            Jika informasinya tidak cukup, jawab singkat dan sopan:
            “Maaf, informasi yang dibutuhkan tidak tersedia. Silakan merujuk laporan resmi pada portal MAGMA, VSI, atau MBG.”
            Jawaban wajib menggunakan Bahasa Indonesia, satu paragraf, tanpa daftar atau penanda khusus.
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
            Pertanyaan pengguna: {user_input}

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

    Stage 2 (JAWABAN AKHIR – hanya bagian ini yang ditampilkan):
    - Tulis satu jawaban yang jelas, ringkas, dan alami dalam Bahasa Indonesia.
    - Do NOT use titles, numbers, or bullet points.
    - Do NOT fabricate information that does not exist in the data.
    - If Stage 1 determined there is no event for today, respond **exactly**: "No data about this event today."
    - Do NOT add "therefore", "as of today", or references to past dates.

    Mandatory rules:
    - Current date is {current_date}.
    - Gunakan Bahasa Indonesia yang jelas, alami, dan profesional.
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

    return model_chat(messages)


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
        normalization = normalize_indonesian_query(user_input)
        if normalization.changed:
            print(f"Normalized Indonesian query: {normalization.replacements}")
            user_input = normalization.normalized
        safety_answer = contextual_safety_followup(user_input, history)
        if safety_answer:
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": None,
                "output": safety_answer,
                "response": None,
            }

        if re.search(r"\b(gempa|gempabumi)\b", user_input, re.IGNORECASE) and check_today_query(user_input):
            earthquake_url = resolve_api_url("/api/v1/home/gempa-bumi/latest")
            earthquake_data = call_api(earthquake_url, max_retries=1)
            event = earthquake_data.get("data", earthquake_data) if isinstance(earthquake_data, dict) else earthquake_data
            if isinstance(event, list):
                event = event[0] if event else None
            if isinstance(event, dict):
                event = event.get("data", event)
            if isinstance(event, dict) and (event.get("local_datetime") or event.get("judul")):
                details = [event.get("local_datetime"), event.get("time_zone"), event.get("lokasi")]
                summary = ", ".join(str(value) for value in details if value) or event["judul"]
                magnitude = event.get("magnitude")
                if magnitude is not None:
                    summary += f", magnitudo {magnitude}"
                answer = f"Catatan gempa terbaru yang tersedia di MAGMA: {summary}. Periksa waktu kejadian dan pembaruan resmi sebelum menilai kondisi saat ini."
                status = "success"
            else:
                answer = (
                    "Saya belum dapat mengambil data gempa terkini dari sumber MAGMA saat ini. "
                    "Karena itu saya tidak bisa memastikan ada atau tidaknya gempa terbaru. "
                    "Periksa pembaruan resmi BMKG."
                )
                status = "error"
            return {
                "status": status,
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": earthquake_url,
                "output": answer,
                "response": event if status == "success" else None,
            }
        intent, response = detect_conversational_intent(user_input, geo_location)
        volcano_url = resolve_api_url("/api/v2/volcano/list")
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

        # Questions asking for a list by alert level are aggregate queries.
        # Generic words such as "api" must not be fuzzily interpreted as a
        # particular volcano name (for example Banda Api).
        aggregate_status_query = bool(
            check_if_mount_level(user_input)
            and re.search(r"\b(apa saja|daftar|semua|gunung mana)\b", user_input, re.IGNORECASE)
        )
        if aggregate_status_query:
            volcano_code = None

        print(f"Volcano code detected: {volcano_code}")
        print(f"Detected intent: {intent} Response: {response}")

        query_lower = user_input.lower()
        api_call_v2 = f"{BASE_URL}/api/v2/volcano/list"

        if (
            re.search(r"\b(erupsi|erupt|letusan|meletus)\b", query_lower)
            and re.search(r"\b(hari ini|today|sekarang|saat ini)\b", query_lower)
        ):
            eruption_data = get_today_eruption_events()
            events = eruption_data.get("events", [])
            if eruption_data.get("error") and not events:
                output_text = "Data erupsi hari ini belum dapat diambil dari MAGMA. Silakan coba beberapa saat lagi."
            elif not events:
                output_text = "Belum ada kejadian erupsi yang tercatat dalam data MAGMA hari ini."
            else:
                volcano_names = sorted({
                    event.get("nama_gunung_api") for event in events if event.get("nama_gunung_api")
                })
                output_text = (
                    f"Hari ini tercatat {len(events)} kejadian erupsi dari "
                    f"{len(volcano_names)} gunung api: {', '.join(volcano_names)}."
                )
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": f"{BASE_URL}/api/v2/volcano/ven",
                "output": output_text,
                "response": events,
            }

        level_guidance = re.search(
            r"(?:jika|kalau|saat|ketika)?\s*(?:terjadi\s*)?level\s*(3|iii)\b",
            query_lower,
        )
        if level_guidance and re.search(r"harus|lakukan|tindakan|antisipasi|bagaimana", query_lower):
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_call_v2,
                "output": (
                    "Level III (Siaga) berarti aktivitas gunung api meningkat nyata. "
                    "Tetap tenang, ikuti informasi resmi PVMBG dan pemerintah daerah, "
                    "jangan memasuki zona bahaya yang ditetapkan untuk gunung tersebut, "
                    "siapkan dokumen penting serta perlengkapan darurat, dan segera ikuti "
                    "arahan evakuasi jika diperintahkan. Radius bahaya berbeda pada setiap "
                    "gunung, jadi sebutkan nama gunung agar NARA dapat memberikan rekomendasi yang lebih spesifik."
                ),
                "response": None,
            }

        if volcano_resp and re.search(r"\bgunung(?: api)?\b", query_lower):
            provinces = sorted({
                (volcano.get("ga_prov_gapi") or "").strip()
                for volcano in volcano_resp
                if volcano.get("ga_prov_gapi")
            }, key=len, reverse=True)
            requested_province = next(
                (province for province in provinces if province.lower() in query_lower),
                None,
            )
            if requested_province:
                matches = sorted(
                    [v for v in volcano_resp if (v.get("ga_prov_gapi") or "").lower() == requested_province.lower()],
                    key=lambda item: item.get("ga_nama_gapi") or "",
                )
                status_labels = {1: "Normal", 2: "Waspada", 3: "Siaga", 4: "Awas"}
                lines = [f"Gunung api yang berada di {requested_province} berdasarkan data resmi PVMBG:"]
                lines.extend(
                    f"{index}. {volcano.get('ga_nama_gapi')} — Level {volcano.get('ga_status')} "
                    f"({status_labels.get(volcano.get('ga_status'), 'Tidak diketahui')})"
                    for index, volcano in enumerate(matches, 1)
                )
                return {
                    "status": "success",
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "api_call": api_call_v2,
                    "output": "\n".join(lines),
                    "response": matches,
                }

        if volcano_resp and re.search(r"\b(bahaya|berbahaya|tertinggi|paling tinggi)\b", query_lower):
            highest_level = max((v.get("ga_status") or 0) for v in volcano_resp)
            highest = sorted(
                [v for v in volcano_resp if v.get("ga_status") == highest_level],
                key=lambda item: item.get("ga_nama_gapi") or "",
            )
            status_labels = {1: "Normal", 2: "Waspada", 3: "Siaga", 4: "Awas"}
            lines = [
                f"Status aktivitas tertinggi saat ini adalah Level {highest_level} "
                f"({status_labels.get(highest_level, 'Tidak diketahui')})."
            ]
            lines.extend(
                f"{index}. {volcano.get('ga_nama_gapi')} — {volcano.get('ga_prov_gapi')}"
                for index, volcano in enumerate(highest, 1)
            )
            lines.append("Tetap ikuti rekomendasi resmi PVMBG karena tingkat aktivitas dan zona bahaya dapat berubah.")
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": api_call_v2,
                "output": "\n".join(lines),
                "response": highest,
            }

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
        is_asking_level_status = check_if_mount_level(user_input) or bool(
            re.search(
                r"\b(status|level|tingkat|waspada|siaga|awas|normal)\b",
                user_input,
                re.IGNORECASE,
            )
        )
        print(f"Is asking level status:: {is_asking_level_status}")
        asking_loc = is_asking_location(user_input)
        print(f"Is asking location status:: {asking_loc}")
        user_lat, user_lon = geo_location if geo_location else (None, None)
        nearest, distance_km = (
            find_nearest_volcano(user_lat, user_lon, volcano_resp)
            if geo_location else (None, None)
        )

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

        elif is_asking_level_status and volcano_code:
            requested_codes = set(volcano_code if isinstance(volcano_code, list) else [volcano_code])
            selected_volcanoes = [
                volcano for volcano in volcano_resp
                if volcano.get("ga_code") in requested_codes
            ]
            status_labels = {
                1: "Level I (Normal)",
                2: "Level II (Waspada)",
                3: "Level III (Siaga)",
                4: "Level IV (Awas)",
            }
            if selected_volcanoes:
                output_lines = []
                for volcano in selected_volcanoes:
                    level = volcano.get("ga_status")
                    name = volcano.get("ga_nama_gapi") or volcano.get("ga_code")
                    location = ", ".join(filter(None, [
                        volcano.get("ga_kab_gapi"),
                        volcano.get("ga_prov_gapi"),
                    ]))
                    output_lines.append(
                        f"Status aktivitas Gunung {name} adalah "
                        f"{status_labels.get(level, f'Level {level}')}."
                        + (f" Lokasi: {location}." if location else "")
                    )
                output_text = "\n".join(output_lines)
            else:
                output_text = "Data status gunung api yang diminta tidak ditemukan."
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": f"{BASE_URL}/api/v2/volcano/list",
                "output": output_text,
                "response": selected_volcanoes,
            }

        elif is_asking_level_status and not volcano_code:
            output_text = return_status(user_input)
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": geo_location,
                "api_call": f"{BASE_URL}/api/v2/volcano/list",
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

            volcano_url = resolve_api_url("/api/v2/volcano/list")
            volcano_resp = get_mount_code()

            volcano_rows = (
                volcano_resp.get("data", [])
                if isinstance(volcano_resp, dict)
                else volcano_resp
            )
            if not volcano_rows:
                return {
                    "status": "error",
                    "api_call": volcano_url,
                    "output": "Data gunung api tidak tersedia saat ini."
                }

            nearest, distance_km = find_nearest_volcano(user_lat, user_lon, volcano_rows)
            if not nearest or not nearest.get("ga_code"):
                return {
                    "status": "error",
                    "api_call": "",
                    "output": "Tidak dapat menemukan gunung terdekat berdasarkan lokasi Anda."
                }

            ga_code = nearest["ga_code"]
            volcano_name = nearest.get("ga_nama_gapi") or ga_code
            final_answer = (
                f"Gunung api terdekat dari lokasi Anda adalah Gunung {volcano_name}, "
                f"dengan estimasi jarak {distance_km:.2f} km."
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
                "api_call": volcano_url,
                "output": final_answer,
                "response": nearest
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

        if isCheckedAround and "/api/v2/ground-movement" in api_url:
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
