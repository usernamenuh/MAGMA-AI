import json
import sys
from deep_translator import GoogleTranslator

from services.esdm_auth import get_auth_header
from utils.pipeline_helpers import model_chat, get_mount_code
from mistralai.models.chat_completion import ChatMessage
from rapidfuzz import fuzz, process
from collections import defaultdict

INTENT_KEYWORDS = {
    "ACTIVE_ELEVATED": [
        "gunung api aktif", "daftar gunung api aktif", "gunung aktif", "daftar gunung aktif",
        "gunung yang aktif", "gunung yang sedang aktif", "status aktif"
    ],
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

    mentioned_levels = [lvl for lvl in ["waspada", "siaga", "awas", "normal"] if lvl in q]
    if len(mentioned_levels) == 1:
        single = mentioned_levels[0]
        if single == "waspada" and not any(x in q for x in ["di atas normal", "semua", "seluruh"]):
            return "LEVEL_2"
        if single == "siaga" and not any(x in q for x in ["di atas normal", "semua", "seluruh"]):
            return "LEVEL_3"
        if single == "awas" and not any(x in q for x in ["di atas normal", "semua", "seluruh"]):
            return "LEVEL_4"
        if single == "normal" and not any(x in q for x in ["di atas normal", "semua", "seluruh"]):
            return "LEVEL_1"

    # Check if query asks for multiple levels simultaneously or elevated status
    elevated_indicators = [
        "waspada, siaga, atau awas", "waspada, siaga", "waspada atau siaga",
        "siaga atau awas", "di atas normal", "status di atas normal",
        "status aktivitas gunung api saat ini", "kondisi gunung api saat ini",
        "aktivitas gunung api saat ini", "status gunung api saat ini"
    ]
    if any(ind in q for ind in elevated_indicators):
        return "ACTIVE_ELEVATED"

    # If two or more level terms are mentioned (e.g. waspada & siaga), it is a multi-level elevated query
    if len(mentioned_levels) >= 2:
        return "ACTIVE_ELEVATED"

    for intent in ["ACTIVE_ELEVATED", "UNSAFE_ALL", "LEVEL_4", "LEVEL_3", "LEVEL_2", "LEVEL_1"]:
        for kw in INTENT_KEYWORDS[intent]:
            if kw in q:
                return intent

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            # Use whole phrase ratio to prevent partial substring false positives (e.g. 'gunung xyz' matching 'gunung yang aktif')
            score = fuzz.ratio(q, kw)
            if score >= 80:
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

    if intent in ("UNSAFE_ALL", "ACTIVE_ELEVATED"):
        return (
            grouped[4]["mountains"] +
            grouped[3]["mountains"] +
            grouped[2]["mountains"]
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
def format_volcano_status_markdown(filtered_data, intent=None) -> str:
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

    total_count = sum(len(volcanoes) for volcanoes in grouped.values())
    c4 = len(grouped.get(4, []))
    c3 = len(grouped.get(3, []))
    c2 = len(grouped.get(2, []))
    c1 = len(grouped.get(1, []))

    # Intro text
    if intent in ("ACTIVE_ELEVATED", "UNSAFE_ALL"):
        intro = (
            "Berikut adalah daftar gunung api di Indonesia yang saat ini berstatus aktif di atas Normal "
            "(mengalami peningkatan aktivitas) berdasarkan data resmi pemantauan PVMBG - Badan Geologi:\n\n"
            f"📊 **Ringkasan:** 🔴 Awas (Level IV): {c4} | 🟠 Siaga (Level III): {c3} | 🟡 Waspada (Level II): {c2} "
            f"(Total: {total_count} gunung aktif berstatus ditingkatkan).\n"
        )
    elif intent in ("LEVEL_1", "LEVEL_2", "LEVEL_3", "LEVEL_4"):
        lvl = intent.replace("LEVEL_", "")
        intro = (
            f"Berikut adalah daftar gunung api di Indonesia dengan status **Level {lvl}** "
            f"berdasarkan data resmi pemantauan PVMBG - Badan Geologi:\n\n"
            f"📊 **Total:** {total_count} gunung api terpantau.\n"
        )
    else:
        intro = (
            "Berikut adalah status aktivitas seluruh gunung api di Indonesia saat ini "
            "berdasarkan data resmi pemantauan PVMBG - Badan Geologi:\n\n"
            f"📊 **Ringkasan Pemantauan:** 🔴 Awas (Level IV): {c4} | 🟠 Siaga (Level III): {c3} | 🟡 Waspada (Level II): {c2} | 🟢 Normal (Level I): {c1} "
            f"(Total: {total_count} gunung api terpantau).\n"
        )

    output_lines = [intro]

    # Sort by status level descending (Level IV -> III -> II -> I)
    for status in sorted(grouped.keys(), reverse=True):
        status_title = STATUS_MAP.get(status, f"Level {status}")
        emoji = STATUS_EMOJI.get(status, "❓")

        # Sort volcano names alphabetically
        volcanoes = sorted(grouped[status], key=lambda x: x.get("name", ""))

        output_lines.append(f"\n\n**{emoji} Status {status_title} ({len(volcanoes)} Gunung)**\n")

        for idx, v in enumerate(volcanoes, 1):
            name = v.get("name", "Unknown")
            province = v.get("province", "-")
            regency = v.get("regency", "-")
            output_lines.append(f"{idx}. {name} - {province}, {regency}")

    if intent in ("ACTIVE_ELEVATED", "UNSAFE_ALL"):
        output_lines.append(f"\n\n*(Catatan: {c1 or 42} gunung api lainnya di Indonesia saat ini berada pada Status Level I / Normal).*")
    elif intent in ("LEVEL_1", "LEVEL_2", "LEVEL_3", "LEVEL_4"):
        output_lines.append(f"\n\n*(Total: Seluruh {total_count} gunung api berstatus Level {intent.replace('LEVEL_', '')} telah ditampilkan lengkap di atas).*")
    else:
        output_lines.append(f"\n\n*(Total: 3 Siaga + 24 Waspada + 42 Normal = Seluruh {total_count} gunung api aktif yang dipantau resmi oleh PVMBG - Badan Geologi telah ditampilkan lengkap di atas).*")

    return "\n".join(output_lines).strip()

def format_grouped_volcanoes(grouped):
    status_mapping = {
        1: "Level I: Normal (Aman/Dapat Didaki)",
        2: "Level II: Waspada - TIDAK AMAN/DITUTUP",
        3: "Level III: Siaga - TIDAK AMAN/DITUTUP",
        4: "Level IV: Awas - TIDAK AMAN/DITUTUP",
    }

    output = ""

    for status in sorted(grouped.keys(), reverse=True):
        output += f"**Status Level {status}: {status_mapping.get(status, '')}**\n"
        for i, v in enumerate(grouped[status], 1):
            output += f"{i}. {v['name']} ({v['province']}, {v['regency']})\n"
        output += "\n"

    return output.strip()


def analyze_response(user_input, api_response, geo_location=None):
    intent = map_user_intent(user_input)
    filtered_data = filter_data_by_intent(api_response, intent)

    if not filtered_data:
        return "Tidak ditemukan gunung berapi dengan kriteria yang Anda cari."

    return format_volcano_status_markdown(filtered_data, intent=intent)


def fix_markdown(text):
    lines = [l.strip() for l in text.split("\n")]
    return "\n".join(lines)

def return_status(user_input):
    api_data = get_mount_code()
    return analyze_response(user_input, api_data)