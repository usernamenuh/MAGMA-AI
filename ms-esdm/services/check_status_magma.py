import json
import sys
from deep_translator import GoogleTranslator

from services.esdm_auth import get_auth_header
from utils.pipeline_helpers import model_chat, get_mount_code
from mistralai.models.chat_completion import ChatMessage
from rapidfuzz import fuzz, process
from collections import defaultdict

INTENT_KEYWORDS = {
    "UNSAFE_ALL": [
        "tidak aman", "tidak bisa didaki", "tidak dapat didaki", "tidak boleh didaki",
        "ditutup", "dilarang", "bahaya", "rawan", "evakuasi"
    ],
    "LEVEL_1": [
        "aman", "normal", "dibuka", "bisa didaki", "dapat didaki", "level 1", "level i"
    ],
    "LEVEL_2": ["waspada", "level 2", "level ii"],
    "LEVEL_3": ["siaga", "level 3", "level iii"],
    "LEVEL_4": ["awas", "level 4", "level iv"],
    "GENERAL": [
        "bagaimana kondisi gunungapi",
        "bagaimana kondisi gunung api",
        "bagaimana kondisi gunung berapi",
        "kondisi gunung api saat ini",
        "status gunung api indonesia",
        "daftar gunung api indonesia",
        "daftar gunung berapi",
        "update gunung api",
        "laporan gunung api",
        "situasi gunung api",
        "ringkasan gunung api",
        "summary gunung api",
        "status gunung api nasional"
    ]
}

def fuzzy_match(query, keywords, threshold=80):
    for kw in keywords:
        score = fuzz.partial_ratio(query, kw)
        if score >= threshold:
            return True
    return False

def map_user_intent(user_input: str) -> str:
    q = user_input.lower().strip()

    for intent in ["UNSAFE_ALL", "LEVEL_4", "LEVEL_3", "LEVEL_2", "LEVEL_1"]:
        for kw in INTENT_KEYWORDS[intent]:
            if kw in q:
                return intent

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            score = fuzz.partial_ratio(q, kw)
            if score >= 85:
                print(f"[FUZZY] '{q}' ~ '{kw}' => {intent} ({score})")
                return intent

    return "GENERAL"


def process_api_response(api_response):
    if not isinstance(api_response, list):
        return None

    status_groups = {
        1: {"name": "Normal", "mountains": []},
        2: {"name": "Waspada", "mountains": []},
        3: {"name": "Siaga", "mountains": []},
        4: {"name": "Awas", "mountains": []}
    }

    for mount in api_response:
        status = mount.get("ga_status")
        if status in status_groups:
            status_groups[status]["mountains"].append({
                "name": mount.get("ga_nama_gapi"),
                "province": mount.get("ga_prov_gapi"),
                "regency": mount.get("ga_kab_gapi"),
                "elevation": mount.get("ga_elev_gapi"),
                "code": mount.get("ga_code"),
                "status": status
            })

    return status_groups

def filter_data_by_intent(api_response, intent):
    grouped = process_api_response(api_response)

    if intent == "LEVEL_1":
        return grouped[1]["mountains"]

    if intent == "LEVEL_2":
        return grouped[2]["mountains"]

    if intent == "LEVEL_3":
        return grouped[3]["mountains"]

    if intent == "LEVEL_4":
        return grouped[4]["mountains"]

    if intent == "UNSAFE_ALL":
        return (
            grouped[2]["mountains"] +
            grouped[3]["mountains"] +
            grouped[4]["mountains"]
        )

    return grouped

STATUS_MAP = {
    1: "Level I: Normal (Aman/Dapat Didaki)",
    2: "Level II: Waspada - TIDAK AMAN/DITUTUP",
    3: "Level III: Siaga - TIDAK AMAN/DITUTUP",
    4: "Level IV: Awas - TIDAK AMAN/DITUTUP",
}

STATUS_EMOJI = {
    1: "🟢",
    2: "🟡",
    3: "🟠",
    4: "🔴",
}
def format_volcano_status_markdown(filtered_data) -> str:
    if not filtered_data:
        return "Tidak ditemukan gunung berapi dengan kriteria yang Anda cari."

    # --- Normalize GENERAL dict format → flat list ---
    if isinstance(filtered_data, dict):
        flat_list = []
        for status, obj in filtered_data.items():
            for v in obj.get("mountains", []):
                flat_list.append(v)
        filtered_data = flat_list

    # Safety check
    if not isinstance(filtered_data, list):
        return "Format data tidak valid."

    # Group by status
    grouped = {}
    for v in filtered_data:
        status = v.get("status")
        if status is None:
            continue
        grouped.setdefault(status, []).append(v)

    # Intro text
    intro = (
        "Berikut adalah status aktivitas gunung api di Indonesia saat ini "
        "berdasarkan data resmi PVMBG:\n"
        "🟢 Normal | 🟡 Waspada | 🟠 Siaga | 🔴 Awas\n"
    )

    output_lines = [intro]

    # Sort by status level
    for status in sorted(grouped.keys()):
        status_title = STATUS_MAP.get(status, f"Level {status}")
        emoji = STATUS_EMOJI.get(status, "❓")

        output_lines.append(f"\n**{emoji} Status {status_title}**")

        # Sort volcano names alphabetically
        volcanoes = sorted(grouped[status], key=lambda x: x.get("name", ""))

        for idx, v in enumerate(volcanoes, 1):
            name = v.get("name", "Unknown")
            province = v.get("province", "-")
            regency = v.get("regency", "-")
            output_lines.append(f"{idx}. {name} - {province}, {regency}")

    return "\n".join(output_lines).strip()

def format_grouped_volcanoes(grouped):
    status_mapping = {
        1: "Level I: Normal (Aman/Dapat Didaki)",
        2: "Level II: Waspada - TIDAK AMAN/DITUTUP",
        3: "Level III: Siaga - TIDAK AMAN/DITUTUP",
        4: "Level IV: Awas - TIDAK AMAN/DITUTUP",
    }

    output = ""

    for status in sorted(grouped.keys()):
        output += f"**Status Level {status}: {status_mapping.get(status, '')}**\n"
        for i, v in enumerate(grouped[status], 1):
            output += f"{i}. {v['name']} ({v['province']}, {v['regency']})\n"
        output += "\n"

    return output.strip()


def analyze_response(user_input, api_response, geo_location=None):
    intent = map_user_intent(user_input)
    filtered_data = filter_data_by_intent(api_response, intent)

    if intent == "GENERAL":
        return format_volcano_status_markdown(filtered_data)

    if not filtered_data:
        return "Tidak ditemukan gunung berapi dengan kriteria yang Anda cari."

    # 🔹 GROUP IN PYTHON
    grouped = defaultdict(list)
    for item in filtered_data:
        grouped[item["status"]].append(item)

    # 🔹 Prepare text for LLM (formatting only)
    status_mapping = {
        1: "Level I: Normal (Aman/Dapat Didaki)",
        2: "Level II: Waspada - TIDAK AMAN/DITUTUP",
        3: "Level III: Siaga - TIDAK AMAN/DITUTUP",
        4: "Level IV: Awas - TIDAK AMAN/DITUTUP",
    }

    structured_text = ""
    for status in sorted(grouped.keys()):
        structured_text += f"\nStatus {status} - {status_mapping.get(status, '')}:\n"
        for v in grouped[status]:
            structured_text += f"- {v['name']} ({v['province']}, {v['regency']})\n"

    system_prompt = """
You are the official Indonesian volcano status reporting system (PVMBG).

You are NOT allowed to summarize.

STRICT RULES (MANDATORY):
- Output ALL volcano entries exactly as provided.
- DO NOT skip any entry.
- DO NOT summarize.
- DO NOT use ellipsis (...).
- DO NOT write phrases like:
  "Data selebihnya sudah disediakan..."
  "dan lainnya"
  "etc"
- DO NOT add explanations.
- DO NOT modify volcano names.
- DO NOT change province or regency.
- DO NOT combine entries.

If even ONE entry is missing, the output is INVALID.

OUTPUT FORMAT (EXACTLY):

**Status Level X: [Description]**
1. Volcano Name (Province, Regency)
2. Volcano Name (Province, Regency)
3. Volcano Name (Province, Regency)

Repeat for each status group.

Output ONLY the formatted result.
"""

    prompt = f"""
User input: {user_input}

Grouped volcano data:
{structured_text}

Format according to required format.
"""

    messages = [
        ChatMessage(role="system", content=system_prompt.strip()),
        ChatMessage(role="user", content=prompt.strip()),
    ]

    try:
        raw_output = model_chat(messages)

        if raw_output and "**Status Level" in raw_output:
            return GoogleTranslator(source="en", target="id").translate(raw_output)
        else:
            print("⚠️ LLM output invalid. Using fallback formatter.")
            return format_grouped_volcanoes(grouped)

    except Exception as e:
        print(f"⚠️ LLM failed: {e}. Using fallback formatter.")
        return format_grouped_volcanoes(grouped)

def fix_markdown(text):
    lines = [l.strip() for l in text.split("\n")]
    return "\n".join(lines)

def return_status(user_input):
    api_data = get_mount_code()
    return analyze_response(user_input, api_data)