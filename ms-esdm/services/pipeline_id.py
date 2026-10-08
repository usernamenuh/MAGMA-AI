import json
import re
import html
from datetime import datetime
from mistralai.models.chat_completion import ChatMessage
from utils.extraction import detect_volcano_name
from utils.geo_location import extract_indonesia_location, get_geolocation_indonesia
from utils.pipeline_helpers import resolve_api_url, call_api, semantic_recommend_api_improved, safe_json_loads, \
    recommend_api_fallback, model_chat, load_examples, crosscheck_api, find_nearest_volcano, check_if_nearest_question, \
    get_mount_code, get_today_eruption_events, fetch_api_simple, filter_history, _detect_volcano_name, check_if_mount_level, BASE_URL, check_around, get_closest_gerakan_tanah_data, is_empty_response, load_volcano_cache, get_volcano_var_data, \
    get_latest_earthquake_data, get_earthquake_list, get_geohazard_location_awareness, get_latest_ground_movement_data, get_ground_movement_list
from concurrent.futures import ThreadPoolExecutor
from utils.classifier import detect_conversational_intent
from services.check_status_magma import return_status
from utils.query_normalizer import normalize_indonesian_query
from utils.location_answers import (
    build_location_answer,
    detect_location_question,
    missing_location_answer,
)
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
    """Answer short safety follow-ups when no coordinates are present."""
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
            "Untuk memeriksa apakah lokasi Anda aman dari gempa bumi atau berada di kawasan rawan bencana (KRB), "
            "silakan aktifkan izin lokasi di peramban Anda atau sebutkan nama kabupaten/kota tempat Anda berada saat ini."
        )
    if re.search(r"\b(gunung|erupsi|letusan)\b", previous_question):
        return (
            "Untuk memeriksa apakah lokasi Anda aman dari aktivitas gunung api dan berada di luar radius bahaya, "
            "silakan aktifkan izin lokasi di peramban Anda atau sebutkan nama daerah/kota Anda berada (mis. Sleman, Boyolali, Bandung)."
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

    # Domain 1: Ground movement / Tanah Longsor
    is_gm = any(w in user_input.lower() for w in ["gerak tanah", "gerakan tanah", "longsor", "sigertan"]) or any(w in response_text.lower() for w in ["gerakan tanah", "tanggap darurat", "sigertan", "tanah longsor", "laporan penyelidikan"])
    if is_gm:
        return f"""
            Pertanyaan pengguna: {user_input}
            {location_context}

            Data laporan kejadian / tanggapan gerakan tanah dari Badan Geologi:
            {response_text}

    Instruksi Jawaban:
    - Analisis data gerakan tanah / tanah longsor di atas secara teliti.
    - Sampaikan ringkasan laporan kejadian secara informatif, profesional, dan mudah dipahami dalam Bahasa Indonesia.
    - Cantumkan informasi penting: judul kejadian, lokasi (kecamatan, kabupaten/kota, provinsi), waktu/tanggal kejadian, kondisi/penyebab gerakan tanah (jika ada), dampak (jika ada), dan rekomendasi mitigasi dari Badan Geologi.
    - Jika data berupa daftar beberapa laporan, rangkum kejadian-kejadian terbaru tersebut.
    - JANGAN menyangkutpautkan dengan status level gunung api (Level I/II/III/IV) atau istilah letusan/erupsi.
    - Tuliskan jawaban yang alami dan jelas dalam Bahasa Indonesia formal dan profesional.
        """

    # Domain 2: Earthquake / Gempa Bumi
    is_quake = any(w in user_input.lower() for w in ["gempa", "gempabumi", "tsunami", "seismik"]) or any(w in response_text.lower() for w in ["gempa bumi", "gempabumi", "tsunami", "magnitudo", "hiposenter", "episenter"])
    if is_quake:
        return f"""
            Pertanyaan pengguna: {user_input}
            {location_context}

            Data kejadian gempa bumi / tsunami dari Badan Geologi (PVMBG) / BMKG:
            {response_text}

    Instruksi Jawaban:
    - Analisis data gempa bumi di atas secara teliti.
    - Sampaikan rincian informasi gempa bumi secara akurat: judul analisis geologi, waktu kejadian, magnitudo, kedalaman, wilayah/pusat gempa, potensi tsunami, dan rekomendasi mitigasi resmi Badan Geologi.
    - Gunakan Bahasa Indonesia yang jelas, tenang, dan profesional.
        """

    # Domain 3: Volcano / Gunung Api
    is_asking_eruption = any(w in user_input.lower() for w in ["erupsi", "letusan", "meletus"])
    date_rule = ""
    if is_today_query and is_asking_eruption:
        date_rule = f"""
        - Periksa tanggal kejadian erupsi/letusan pada data.
        - Bandingkan dengan tanggal hari ini: {current_date}.
        - Jika pengguna menanyakan erupsi hari ini DAN tidak ada letusan yang tercatat pada tanggal {current_date}, sampaikan bahwa belum ada catatan erupsi baru yang tercatat untuk hari ini, dan kondisi aktivitas tetap sesuai tingkat pengamatan resmi terakhir.
        """
    else:
        date_rule = "- Sampaikan data pengamatan resmi atau status aktivitas gunung api terkini yang tersedia dalam data."

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
    - If user asked about eruption today and there is no event for today, jelaskan: "Belum ada catatan erupsi atau letusan baru yang tercatat untuk hari ini. Kondisi aktivitas tetap sesuai pengamatan resmi terakhir."
    - JANGAN PERNAH mengeluarkan kalimat bahasa Inggris "No data about this event today."

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

def run_pipeline(user_input: str, geo_location: tuple[float, float], history: str = '', location_name: str=None, location_accuracy: float | None = None):
    try:
        normalization = normalize_indonesian_query(user_input)
        if normalization.changed:
            print(f"Normalized Indonesian query: {normalization.replacements}")
            user_input = normalization.normalized
        # ===================================================================
        # AI Agent Router: Decision Engine with Tool-Specific Execution
        # ===================================================================
        from services.agent_router import AgentRouter
        routed_result = AgentRouter.route_and_execute(
            user_input=user_input,
            geo_location=geo_location,
            history=history,
            location_name=location_name,
            location_accuracy=location_accuracy,
            lang="id",
        )
        if routed_result:
            routed_result["date"] = datetime.utcnow().isoformat()
            routed_result["user_input"] = user_input
            if "geo_location" not in routed_result:
                routed_result["geo_location"] = geo_location
            return routed_result

        has_geo = bool(geo_location and any(geo_location))
        if not has_geo:
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

        if re.search(r"\b(gempa|gempabumi|tsunami)\b", user_input, re.IGNORECASE):
            detected_volcano = detect_volcano_name(user_input)
            if not detected_volcano:
                is_mitigation = bool(re.search(r"\b(mitigasi|panduan|keselamatan|langkah|antisipasi|tindakan|apa yang harus dilakukan)\b", user_input, re.IGNORECASE))
                if is_mitigation:
                    answer_parts = [
                        "📋 Panduan Langkah Mitigasi & Keselamatan Gempa Bumi (PVMBG & BMKG):",
                        "1. Saat Terjadi Guncangan:\n"
                        "   • Berlindung di bawah meja yang kokoh (*Drop, Cover, Hold On*) dan lindungi kepala serta leher.\n"
                        "   • Jauhi jendela kaca, lemari tinggi, dan benda gantung yang berpotensi jatuh.\n"
                        "   • Jika berada di luar ruangan, cari area terbuka yang jauh dari bangunan tinggi, tiang listrik, dan tebing curam.\n"
                        "   • Jika berada di pesisir pantai dan merasakan gempa kuat atau berayun lama, segera evakuasi ke dataran tinggi tanpa menunggu sirine.",
                        "2. Setelah Guncangan Mereda:\n"
                        "   • Waspadai potensi gempa bumi susulan (*aftershocks*).\n"
                        "   • Matikan kompor dan periksa instalasi listrik/gas guna mencegah kebakaran.\n"
                        "   • Gunakan tangga darurat untuk keluar bangunan, jangan pernah menggunakan lift.\n"
                        "   • Pantau informasi resmi hanya dari Badan Geologi (PVMBG) dan BMKG.",
                        "💬 Apakah Anda ingin saya tampilkan daftar kejadian gempa bumi penting lainnya yang tercatat baru-baru ini? Balas *ya* atau *tidak*."
                    ]
                    return {
                        "status": "success",
                        "date": datetime.utcnow().isoformat(),
                        "user_input": user_input,
                        "geo_location": geo_location,
                        "api_call": resolve_api_url("/api/v2/earthquake-tsunami"),
                        "output": "\n\n".join(answer_parts),
                        "response": None,
                    }

                extracted_place = extract_indonesia_location(user_input)
                eq = get_latest_earthquake_data()
                answer_parts = []

                if extracted_place:
                    # User specifically asks about an area / city (e.g. "aktivitas gempa di bandung")
                    coords = get_geolocation_indonesia(extracted_place)
                    target_lat, target_lng = coords if coords else (None, None)
                    loc_hazard = {}
                    if target_lat is not None and target_lng is not None:
                        loc_hazard = get_geohazard_location_awareness(target_lat, target_lng)

                    kab = (loc_hazard.get("kab_kota") or extracted_place).upper()

                    match_event = False
                    if eq and eq.get("lokasi"):
                        event_text = f"{eq.get('lokasi', '')} {eq.get('judul', '')}".lower()
                        if extracted_place.lower() in event_text:
                            match_event = True

                    if match_event:
                        dt = eq.get("datetime")
                        mag = eq.get("magnitude")
                        depth = eq.get("kedalaman")
                        lok = eq.get("lokasi") or eq.get("kota_terdekat")
                        tsunami_str = "Berpotensi tsunami" if eq.get("tsunami") else "Tidak berpotensi tsunami"
                        answer_parts.append(
                            f"Catatan Kejadian Gempa Bumi di Wilayah {kab}:\n"
                            f"{eq.get('judul')}\n"
                            f"Waktu: {dt}, Magnitudo: M {mag}, Kedalaman: {depth} km, Wilayah: {lok}. Status: {tsunami_str}."
                        )
                        rek = eq.get("rekomendasi")
                        if rek:
                            clean_rek = html.unescape(re.sub(r"<[^>]+>", " ", rek))
                            clean_rek = re.sub(r"\s+", " ", clean_rek).strip()
                            if len(clean_rek) > 280:
                                clean_rek = clean_rek[:280] + "..."
                            answer_parts.append(f"📋 Rekomendasi Resmi:\n{clean_rek}")
                    else:
                        answer_parts.append(
                            f"Untuk wilayah {kab}:\n"
                            f"Saat ini tidak ada laporan kejadian gempa bumi tektonik merusak terbaru yang tercatat di wilayah ini."
                        )

                    if loc_hazard and loc_hazard.get("earthquake"):
                        eq_hazard = loc_hazard["earthquake"]
                        kelas = eq_hazard.get("kelas", "Kawasan Rawan Bencana Gempabumi")
                        desc = eq_hazard.get("namobj", "")
                        answer_parts.append(f"Karakteristik Kerentanan Gempa:\nWilayah ini berada dalam {kelas} ({desc}).")

                    nearest_name = None
                    if target_lat is not None and target_lng is not None:
                        try:
                            v_list = get_mount_code() or load_volcano_cache()
                            near_v, dist = find_nearest_volcano(target_lat, target_lng, v_list)
                            if near_v and dist < 70:
                                nearest_name = near_v.get("ga_nama_gapi")
                                status_code = near_v.get("ga_status", 1)
                                status_label = {1: "Level I (Normal)", 2: "Level II (Waspada)", 3: "Level III (Siaga)", 4: "Level IV (Awas)"}.get(status_code, "Level I (Normal)")
                                answer_parts.append(
                                    f"Aktivitas Seismik Vulkanik Sekitar:\n"
                                    f"Gunung api terdekat adalah Gunung {nearest_name} (~{dist:.1f} km) dengan status {status_label}. Pemantauan seismik vulkanik saat ini berada dalam batas normal."
                                )
                        except Exception as e:
                            print(f"Nearest volcano check error: {e}")

                    if nearest_name:
                        answer_parts.append(f"💬 Apakah Anda ingin saya tampilkan status dan rekomendasi resmi PVMBG untuk Gunung {nearest_name}? Balas *ya* atau *tidak*.")
                    else:
                        answer_parts.append("💬 Apakah Anda ingin saya cek gunung api terdekat dari lokasi Anda saat ini? Balas *ya* atau *tidak*.")

                else:
                    # User asks general/national earthquake (e.g. "Gempa bumi terbaru", "Daftar kejadian gempa bumi terkini")
                    is_list_query = bool(re.search(r"\b(daftar|list|lainnya|semua|apa saja|riwayat|beberapa)\b", user_input, re.IGNORECASE))

                    if is_list_query:
                        eq_list = get_earthquake_list()
                        if eq_list:
                            answer_parts.append("📋 Daftar Kejadian Gempa Bumi Penting Terbaru (Badan Geologi / PVMBG):")
                            for i, item in enumerate(eq_list[:5], 1):
                                judul = item.get("judul", "Kejadian Gempa Bumi").strip()
                                dt = item.get("local_datetime") or item.get("date") or ""
                                mag = item.get("magnitude")
                                mag_str = f"M {mag} — " if mag else ""
                                dt_str = f" [{dt}]" if dt else ""
                                short_judul = re.sub(r"^ANALISIS GEOLOGI KEJADIAN GEMPA BUMI DI\s+", "", judul, flags=re.IGNORECASE)
                                short_judul = re.sub(r"\s+TANGGAL.*$", "", short_judul, flags=re.IGNORECASE).strip()
                                answer_parts.append(f"{i}. {mag_str}{short_judul}{dt_str}")
                        else:
                            answer_parts.append("Belum ada daftar kejadian gempa bumi penting lainnya yang dapat ditampilkan saat ini.")

                        answer_parts.append("💬 Apakah Anda ingin saya tampilkan panduan langkah mitigasi dan keselamatan saat terjadi gempa bumi? Balas *ya* atau *tidak*.")

                        return {
                            "status": "success",
                            "date": datetime.utcnow().isoformat(),
                            "user_input": user_input,
                            "geo_location": geo_location,
                            "api_call": resolve_api_url("/api/v2/earthquake-tsunami"),
                            "output": "\n\n".join(answer_parts),
                            "response": eq_list,
                        }

                    else:
                        if eq and eq.get("judul"):
                            source = eq.get("source", "MAGMA ESDM")
                            judul = eq.get("judul")
                            dt = eq.get("datetime")
                            mag = eq.get("magnitude")
                            depth = eq.get("kedalaman")
                            lok = eq.get("lokasi") or eq.get("kota_terdekat")
                            tsunami_str = "Berpotensi tsunami" if eq.get("tsunami") else "Tidak berpotensi tsunami"

                            details_str = f"Waktu: {dt}, Magnitudo: M {mag}, Kedalaman: {depth} km, Wilayah: {lok}. Status: {tsunami_str}."
                            answer_parts.append(f"Catatan gempa terkini ({source}):\n{judul}\n{details_str}")

                            rek = eq.get("rekomendasi")
                            if rek:
                                clean_rek = html.unescape(re.sub(r"<[^>]+>", " ", rek))
                                clean_rek = re.sub(r"\s+", " ", clean_rek).strip()
                                if clean_rek and len(clean_rek) > 10:
                                    if len(clean_rek) > 280:
                                        clean_rek = clean_rek[:280] + "..."
                                    answer_parts.append(f"📋 Rekomendasi Resmi:\n{clean_rek}")
                        else:
                            answer_parts.append("Belum ada laporan gempa bumi signifikan terbaru yang tercatat. Pantau terus kanal resmi Badan Geologi dan BMKG.")

                        answer_parts.append("💬 Apakah Anda ingin saya tampilkan informasi gempa bumi penting lainnya yang tercatat baru-baru ini? Balas *ya* atau *tidak*.")

                answer = "\n\n".join(answer_parts)
                status = "success"

                return {
                    "status": status,
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "api_call": eq.get("api_url") if eq else resolve_api_url("/api/v2/earthquake-tsunami/latest"),
                    "output": answer,
                    "response": eq.get("raw") if eq else None,
                }

        if re.search(r"\b(gerak(?:an)?\s*tanah|tanah\s*longsor|longsoran|sigertan)\b", user_input, re.IGNORECASE):
            is_mitigation = bool(re.search(r"\b(mitigasi|rekomendasi|langkah|antisipasi|tindakan|upaya)\b", user_input, re.IGNORECASE))
            is_list = bool(re.search(r"\b(daftar|list|semua|apa saja|riwayat)\b", user_input, re.IGNORECASE))

            answer_parts = []
            if is_mitigation:
                answer_parts.append(
                    "📋 Panduan Lengkap Mitigasi Bencana Gerakan Tanah & Tanah Longsor (PVMBG - Badan Geologi, Kementerian ESDM):\n\n"
                    "1. Kesiapsiagaan & Pencegahan (Pra-Bencana):\n"
                    "   • Kenali Gejala & Tanda Awal:\n"
                    "     - Munculnya retakan tanah baru melengkung atau memanjang pada lereng, jalan, atau dinding rumah.\n"
                    "     - Tiang listrik, pohon, atau tiang pagar mulai miring secara tidak wajar.\n"
                    "     - Pintu atau jendela mendadak sulit dibuka/ditutup akibat pergeseran struktur bangunan.\n"
                    "     - Air sumur atau mata air mendadak keruh berlumpur, atau muncul rembesan air baru pada lereng.\n"
                    "   • Penataan Fisik Lingkungan:\n"
                    "     - Jangan mendirikan bangunan hunian di lereng curam atau di sempadan alur longsor.\n"
                    "     - Jaga kelancaran drainase permukaan lereng agar air hujan tidak meresap menjenuhkan lereng.\n"
                    "     - Hindari memotong tebing tegak lurus tanpa dinding penahan (retaining wall).\n"
                    "     - Tanam pohon berakar dalam (akar wangi/vetiver, bambu, aren) di kawasan lereng rawan.\n\n"
                    "2. Tindakan Saat Terjadi Longsor (Tanggap Darurat):\n"
                    "   • Segera evakuasi menjauhi lereng atau lembah alur longsor menuju tempat terbuka yang datar dan stabil.\n"
                    "   • Bunyikan tanda bahaya (sirine/kentongan) jika memungkinkan.\n"
                    "   • Jangan mendekati material runtuhan karena sangat berisiko terjadi longsor susulan.\n\n"
                    "3. Tindakan Pasca-Bencana:\n"
                    "   • Waspadai longsor susulan terutama saat hujan deras masih terus turun.\n"
                    "   • Jangan langsung memasuki rumah yang rusak sebelum diperiksa oleh tim ahli geologi atau BPBD.\n"
                    "   • Pantau terus pembaruan informasi dari Badan Geologi (PVMBG) dan BPBD setempat."
                )

                return {
                    "status": "success",
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "api_call": resolve_api_url("/api/v2/ground-movement/latest"),
                    "output": "\n\n".join(answer_parts),
                    "response": gm_data.get("raw") if gm_data else None,
                }

            elif is_list:
                gm_list = get_ground_movement_list()
                if gm_list:
                    answer_parts.append("📋 Daftar Laporan Tanggapan Kejadian Gerakan Tanah Terbaru (Badan Geologi / PVMBG):")
                    for i, item in enumerate(gm_list[:5], 1):
                        judul = item.get("judul", "Laporan Gerakan Tanah").strip()
                        waktu = item.get("local_datetime") or item.get("updated_at") or ""
                        waktu_str = f" [{waktu}]" if waktu else ""
                        answer_parts.append(f"{i}. {judul}{waktu_str}")
                else:
                    answer_parts.append("Belum ada daftar laporan kejadian gerakan tanah yang dapat ditampilkan saat ini.")

                answer_parts.append("💬 Apakah Anda ingin saya tampilkan rekomendasi teknis mitigasi bencana gerakan tanah dan tanah longsor? Balas *ya* atau *tidak*.")

                return {
                    "status": "success",
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "api_call": resolve_api_url("/api/v2/ground-movement"),
                    "output": "\n\n".join(answer_parts),
                    "response": gm_list,
                }

            else:
                gm_data = get_latest_ground_movement_data()
                if gm_data and gm_data.get("judul"):
                    judul = gm_data.get("judul").strip()
                    dt = gm_data.get("datetime", "")
                    pelapor = gm_data.get("pelapor", "")
                    tipe = gm_data.get("tipe") or "Gerakan Tanah / Tanah Longsor"

                    answer_parts.append(
                        f"Laporan Tanggap Darurat Gerakan Tanah Terbaru (Badan Geologi):\n"
                        f"📌 {judul}\n"
                        f"Waktu Laporan: {dt} | Pelapor: {pelapor}\n"
                        f"Tipe Gerakan: {tipe}"
                    )

                    kondisi = gm_data.get("kondisi") or {}
                    penyebab = kondisi.get("penyebab")
                    if penyebab:
                        clean_penyebab = html.unescape(re.sub(r"<[^>]+>", " ", penyebab)).strip()
                        answer_parts.append(f"Faktor Penyebab: {clean_penyebab}")

                    rek_list = gm_data.get("rekomendasi")
                    if rek_list:
                        first_rek = ""
                        if isinstance(rek_list, list) and len(rek_list) > 0:
                            first_rek = html.unescape(re.sub(r"<[^>]+>", " ", str(rek_list[0]))).strip()
                        elif isinstance(rek_list, str):
                            first_rek = html.unescape(re.sub(r"<[^>]+>", " ", rek_list)).strip()
                        if first_rek and len(first_rek) > 10:
                            if len(first_rek) > 250:
                                first_rek = first_rek[:250] + "..."
                            answer_parts.append(f"Rekomendasi Utama: {first_rek}")
                else:
                    answer_parts.append("Belum ada laporan kejadian gerakan tanah terbaru yang tercatat di sistem saat ini.")

                answer_parts.append("💬 Apakah Anda ingin saya tampilkan rekomendasi teknis mitigasi bencana gerakan tanah dan tanah longsor? Balas *ya* atau *tidak*.")

                return {
                    "status": "success",
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "api_call": resolve_api_url("/api/v2/ground-movement/latest"),
                    "output": "\n\n".join(answer_parts),
                    "response": gm_data.get("raw") if gm_data else None,
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

        # Questions asking for a list by alert level or active volcanoes are aggregate queries.
        # Generic words such as "api" or "aktif" must not be interpreted as a particular volcano name.
        aggregate_status_query = bool(
            (check_if_mount_level(user_input) or re.search(r"\b(aktif|berapi|keaktifan)\b", user_input, re.IGNORECASE))
            and re.search(r"\b(apa saja|daftar|semua|gunung mana|mana saja|list)\b", user_input, re.IGNORECASE)
        ) or bool(
            re.search(r"^\s*(daftar\s+)?gunung(\s+api)?\s+aktif\s*$", user_input, re.IGNORECASE)
        ) or bool(
            re.search(r"\bgunung(\s+api)?\s+aktif\b", user_input, re.IGNORECASE) and not any(v in user_input.lower() for v in ["merapi", "semeru", "sinabung", "krakatau", "kelud", "bromo"])
        )
        if aggregate_status_query:
            volcano_code = None

        print(f"Volcano code detected: {volcano_code}")
        print(f"Detected intent: {intent} Response: {response}")

        query_lower = user_input.lower()
        api_call_v2 = f"{BASE_URL}/api/v2/volcano/list"

        loc_mode = detect_location_question(user_input, "id")
        if loc_mode:
            eff_geo = None
            eff_name = location_name
            eff_accuracy = location_accuracy

            # If user asks about their own location ("saya", "aku", "sini") and device geo is available,
            # prioritize their device location
            is_asking_own_pos = bool(re.search(r"\b(saya|aku|kami|kita|sini|disini|posisi\s+saya|lokasi\s+saya)\b", user_input, re.IGNORECASE))
            if is_asking_own_pos and geo_location and any(geo_location):
                try:
                    eff_geo = (float(geo_location[0]), float(geo_location[1]))
                except (TypeError, ValueError):
                    eff_geo = None

            if not eff_geo:
                # Remove volcano name phrases before extracting place names so "Gunung Banda" is not extracted as city "Banda"
                sanitized_for_loc = re.sub(r"\b(?:gunung(?:\s+api)?|gn\.|mount|mt\.)\s+[a-zA-Z\s\-]+", "", user_input, flags=re.IGNORECASE)
                extracted_loc = extract_indonesia_location(sanitized_for_loc)
                if extracted_loc:
                    loc_coords = get_geolocation_indonesia(extracted_loc)
                    if loc_coords and any(loc_coords):
                        eff_geo = (float(loc_coords[0]), float(loc_coords[1]))
                        eff_name = extracted_loc
                        eff_accuracy = None

            if not eff_geo and geo_location and any(geo_location):
                try:
                    eff_geo = (float(geo_location[0]), float(geo_location[1]))
                except (TypeError, ValueError):
                    eff_geo = None

            if not eff_geo:
                return {
                    "status": "success",
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "api_call": None,
                    "output": missing_location_answer("id"),
                    "response": None,
                }

            # Check if user asks safety relative to a specific volcano (from query or ongoing conversation)
            target_volcano_name = None
            v_match = re.search(r"gunung\s+([a-zA-Z\s\-]+?)(?:\?|$|\s+berjarak|\s+aman)", user_input, re.IGNORECASE)
            if v_match:
                cand = v_match.group(1).strip()
                if cand.lower() not in {"api", "berapi", "terdekat", "saya", "aktif"}:
                    target_volcano_name = cand
            if not target_volcano_name and history:
                prev_v = re.findall(r"(?:Gunung|Mount)\s+([A-Z][a-zA-Z\s\-]+?)(?:\s+adalah|\s+berstatus|\s+berjarak|\?|\.|\,)", history)
                if prev_v:
                    cand = prev_v[-1].strip()
                    if cand.lower() not in {"api", "berapi", "terdekat", "aktif"}:
                        target_volcano_name = cand

            out_text, nearest_items = build_location_answer(
                mode=loc_mode,
                lat=eff_geo[0],
                lon=eff_geo[1],
                volcano_list=volcano_resp or [],
                location_name=eff_name,
                accuracy_m=eff_accuracy,
                lang="id",
                target_volcano_name=target_volcano_name,
            )
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "geo_location": eff_geo,
                "api_call": api_call_v2,
                "output": out_text,
                "response": nearest_items,
                "nearest_volcano": nearest_items[0] if nearest_items else None,
            }

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
            # Rule #13: NEVER repeat long greeting in the middle of an ongoing conversation!
            if history and intent in ("greeting", "identity"):
                clean_q = re.sub(r"[^\w\s]", "", user_input.lower()).strip()
                # If it's a greeting or casual salutation, respond concisely
                if intent == "greeting" or clean_q in {"halo", "hai", "hi", "hey", "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "assalamualaikum"}:
                    return {
                        "status": "success",
                        "date": datetime.utcnow().isoformat(),
                        "user_input": user_input,
                        "geo_location": geo_location,
                        "api_call": None,
                        "output": "Halo! Ada yang bisa saya bantu terkait informasi status gunung api, gempa bumi, atau bencana geologi saat ini?",
                        "response": None
                    }
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
                r"\b(status|level|tingkat|waspada|siaga|awas|normal|kondisi|kabar|info|aktif|keaktifan|berapi)\b",
                user_input,
                re.IGNORECASE,
            )
        ) or (bool(volcano_code) and len(user_input.split()) <= 4)
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
                    code = volcano.get("ga_code")
                    location = ", ".join(filter(None, [
                        volcano.get("ga_kab_gapi"),
                        volcano.get("ga_prov_gapi"),
                    ]))
                    output_lines.append(
                        f"Status aktivitas Gunung {name} adalah "
                        f"{status_labels.get(level, f'Level {level}')}."
                        + (f" Lokasi: {location}." if location else "")
                    )
                    # Ambil rekomendasi resmi PVMBG dari VAR
                    var_data = get_volcano_var_data(code)
                    if var_data and isinstance(var_data, dict):
                        lap = var_data.get("laporan_terakhir") or {}
                        rekomendasi = lap.get("rekomendasi")
                        tgl_lap = lap.get("tanggal")
                        if rekomendasi:
                            output_lines.append(
                                f"\n📋 Rekomendasi Resmi PVMBG"
                                + (f" ({tgl_lap}):\n" if tgl_lap else ":\n")
                                + rekomendasi.strip()
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

        # Extract volcano code as string
        norm_vcode = None
        if volcano_code:
            norm_vcode = volcano_code[0] if isinstance(volcano_code, (list, tuple)) and len(volcano_code) > 0 else volcano_code
        elif code_match:
            norm_vcode = code_match.group(1) or code_match.group(2)

        if norm_vcode:
            if "{code}" in api_url:
                api_url = api_url.replace("{code}", str(norm_vcode))
            if method == "GET":
                if not isinstance(params, dict):
                    params = {}
                params["code"] = str(norm_vcode)
            else:
                if isinstance(body, list) and len(body) > 0 and isinstance(body[0], dict):
                    body[0]["code"] = str(norm_vcode)
                elif isinstance(body, dict):
                    body["code"] = str(norm_vcode)

        # For GET requests: migrate any body fields to query params and set body = None
        if method == "GET":
            if isinstance(body, dict):
                for k, v in body.items():
                    if k not in params:
                        val = v[0] if isinstance(v, (list, tuple)) and len(v) == 1 else v
                        if val is not None:
                            params[k] = val
                body = None
            elif isinstance(body, list) and len(body) > 0 and isinstance(body[0], dict):
                for k, v in body[0].items():
                    if k not in params:
                        val = v[0] if isinstance(v, (list, tuple)) and len(v) == 1 else v
                        if val is not None:
                            params[k] = val
                body = None

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

        # Check if query asks about last eruption (VEN_LAST) or eruption history of a volcano
        if "/api/v2/volcano/ven" in api_url and isinstance(api_response, dict) and api_response.get("data"):
            v_data = api_response["data"]
            if isinstance(v_data, list) and len(v_data) > 0:
                first_e = v_data[0]
                g_nama = first_e.get("nama_gunung_api") or (norm_vcode if norm_vcode else "Gunung Api")
                e_date = first_e.get("local_datetime") or first_e.get("local_date") or ""
                e_level = first_e.get("tingkat_aktivitas") or ""
                e_desc = first_e.get("deskripsi") or {}
                e_vis = e_desc.get("visual") or ""
                if e_vis:
                    clean_vis = html.unescape(re.sub(r"<[^>]+>", " ", e_vis)).strip()
                else:
                    clean_vis = f"Erupsi Gunung {g_nama} tercatat pada {e_date}."
                level_str = f"\nStatus Aktivitas Saat Ini: {e_level}" if e_level else ""

                output_text = f"🌋 Catatan Erupsi Terakhir Gunung {g_nama} (PVMBG):\n{clean_vis}{level_str}"
                return {
                    "status": "success",
                    "date": datetime.utcnow().isoformat(),
                    "user_input": user_input,
                    "geo_location": geo_location,
                    "api_call": api_url,
                    "output": output_text,
                    "response": [first_e],
                }

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
