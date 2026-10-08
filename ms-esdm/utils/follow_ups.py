"""Conversational follow-up offers for MAGMA AI (Web & WhatsApp).

Instead of clickable suggestion chips, the assistant itself ends its answer with
ONE contextual offer, e.g.:

    💬 Apakah Anda ingin saya cek apakah lokasi Anda saat ini aman dari Gunung Merapi?
       Balas *ya* atau *tidak*.

When the user replies with a short confirmation ("ya", "boleh", "iya dong",
"yes") the offer from the previous assistant message is resolved back into a
full question and processed normally. A decline ("tidak", "nggak usah")
gets a short polite reply.

The design is stateless: the offer sentence stored in chat history is parsed
again with the same templates, so it survives restarts and multiple workers.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - rapidfuzz is a project dependency
    fuzz = None

OFFER_MARKER = "💬"

# ---------------------------------------------------------------------------
# Offer templates: (key, offer phrase, resolved query). "{v}" = volcano name.
# The offer phrase is what the bot says, the query is what gets executed
# when the user answers "ya". Queries are chosen so they hit deterministic,
# data-backed handlers in the pipeline (no hallucination-prone free text).
# ---------------------------------------------------------------------------
TEMPLATES = {
    "id": {
        "status": (
            "tampilkan status dan rekomendasi resmi PVMBG untuk Gunung {v}",
            "Status Gunung {v}",
        ),
        "erupt_history": (
            "cek catatan erupsi atau letusan terakhir Gunung {v}",
            "Erupsi terakhir Gunung {v}",
        ),
        "safety": (
            "cek apakah lokasi Anda saat ini aman dari Gunung {v}",
            "Apakah lokasi saya aman dari Gunung {v}?",
        ),
        "nearest": (
            "cek gunung api terdekat dari lokasi Anda saat ini",
            "Gunung api terdekat dari saya",
        ),
        "raised": (
            "tampilkan daftar gunung api lain yang statusnya sedang di atas Normal",
            "Gunung apa saja yang berstatus waspada, siaga, atau awas?",
        ),
        "erupt_today": (
            "cek gunung api mana saja yang tercatat erupsi hari ini",
            "Gunung apa saja yang erupsi hari ini?",
        ),
        "quake_latest": (
            "tampilkan rincian kejadian gempa bumi terkini",
            "Gempa bumi terbaru",
        ),
        "quake_list": (
            "tampilkan informasi gempa bumi penting lainnya yang tercatat baru-baru ini",
            "Daftar kejadian gempa bumi terkini",
        ),
        "quake_mitigation": (
            "tampilkan panduan langkah mitigasi dan keselamatan saat terjadi gempa bumi",
            "Bagaimana panduan mitigasi bencana gempa bumi?",
        ),
        "quake_safety": (
            "cek potensi kerentanan bencana gempa bumi di wilayah Anda",
            "Apakah lokasi saya rawan gempa bumi?",
        ),
        "ground_movement_latest": (
            "tampilkan laporan tanggapan kejadian gerakan tanah atau longsor terbaru",
            "Kejadian gerakan tanah terbaru",
        ),
        "ground_movement_list": (
            "tampilkan daftar laporan kejadian gerakan tanah lainnya dari Badan Geologi",
            "Daftar kejadian gerakan tanah",
        ),
        "ground_movement_mitigation": (
            "tampilkan rekomendasi teknis mitigasi bencana gerakan tanah dan tanah longsor",
            "Bagaimana rekomendasi teknis mitigasi gerakan tanah?",
        ),
        "doc_summary": (
            "rangkum poin-poin penting dari dokumen tersebut",
            "Rangkum poin-poin penting dari dokumen tersebut",
        ),
    },
    "en": {
        "status": (
            "show the official PVMBG status and recommendations for Mount {v}",
            "Status of Mount {v}",
        ),
        "erupt_history": (
            "check the latest eruption record of Mount {v}",
            "Latest eruption of Mount {v}",
        ),
        "safety": (
            "check whether your current location is safe from Mount {v}",
            "Is my location safe from Mount {v}?",
        ),
        "nearest": (
            "check the nearest volcano to your current location",
            "Nearest volcano to me",
        ),
        "raised": (
            "list other volcanoes whose alert level is currently above Normal",
            "Which volcanoes are at advisory, watch, or warning level?",
        ),
        "erupt_today": (
            "check which volcanoes erupted today",
            "Which volcanoes erupted today?",
        ),
        "quake_latest": (
            "show the latest earthquake information",
            "Latest earthquake",
        ),
        "quake_list": (
            "list other significant earthquake events recently recorded",
            "Recent earthquake events",
        ),
        "quake_mitigation": (
            "show earthquake safety and mitigation guidance",
            "What are the earthquake safety and mitigation guidelines?",
        ),
        "quake_safety": (
            "check earthquake hazard susceptibility in your area",
            "Is my location prone to earthquakes?",
        ),
        "ground_movement_latest": (
            "show the latest ground movement response report",
            "Latest ground movement incident",
        ),
        "ground_movement_list": (
            "list other reported ground movement incidents",
            "List of ground movement incidents",
        ),
        "ground_movement_mitigation": (
            "show technical mitigation recommendations for ground movement and landslides",
            "What are the ground movement mitigation guidelines?",
        ),
        "doc_summary": (
            "summarize the key points of that document",
            "Summarize the key points of that document",
        ),
    },
}

OFFER_PREFIX = {
    "id": "Apakah Anda ingin saya ",
    "en": "Would you like me to ",
}
OFFER_HINT = {
    "id": "Balas *ya* atau *tidak*.",
    "en": "Reply *yes* or *no*.",
}

AFFIRM_RE = re.compile(
    r"^\s*(ya+|iy+a+|iyes|y|yup|yap|yoi|boleh|mau|oke+|ok|okay|okey|siap|lanjut|lanjutkan|tentu|"
    r"tentu saja|silakan|silahkan|gas|gass+|betul|benar|setuju|please|yes|yeah|yep|sure|"
    r"go ahead|of course)"
    r"(\s+(dong|deh|boleh|tolong|please|saja|aja|ya|kak|min|sih|banget|lah|mau|lanjut|"
    r"thanks|thank you))*\s*[.!?]*\s*$",
    re.IGNORECASE,
)
DECLINE_RE = re.compile(
    r"^\s*(tidak|tdk|ga|gak|nggak|ngga|enggak|engga|no|nope|nah|nanti|ndak|"
    r"tidak usah|ga usah|gak usah|nggak usah|tidak perlu|ga perlu|gak perlu|nanti saja|"
    r"nanti aja|no thanks|not now)"
    r"(\s+(dulu|deh|kok|kak|min|saja|aja|terima kasih|makasih|thanks|ya))*\s*[.!?]*\s*$",
    re.IGNORECASE,
)

VOLCANO_NAME_RE = re.compile(
    r"\b(?:Gunung(?:\s+api)?|Mount|G\.)\s+([A-Z][\w\-]*(?:\s+[A-Z][\w\-]*){0,2})",
    re.IGNORECASE,
)
_NAME_STOP = {"Adalah", "Is", "Yang", "Dengan", "Level", "Status", "Pada", "Di"}


def _clean_volcano_name(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    parts = []
    for word in raw.split():
        if word in _NAME_STOP:
            break
        parts.append(word)
    name = " ".join(parts).strip(" .,:;")
    if not name:
        return None
    name_l = name.lower()
    if name_l in {"banda api", "sangeang api", "sangeangapi"}:
        return name
    invalid_words = {
        "api", "berapi", "terdekat", "indonesia", "nasional", "aktif", "yang",
        "saat", "ini", "lain", "lainnya", "daerah", "provinsi", "wilayah"
    }
    if any(w.lower() in invalid_words for w in name.split()):
        return None
    return name or None


def _first_volcano(text: str) -> Optional[str]:
    match = VOLCANO_NAME_RE.search(text or "")
    return _clean_volcano_name(match.group(1)) if match else None


def _similar(a: str, b: str) -> bool:
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return False
    if fuzz is not None:
        return fuzz.token_set_ratio(a, b) >= 80
    return a == b


def _format_offer(key: str, lang: str, volcano: Optional[str] = None) -> Tuple[str, str]:
    lang = "en" if lang == "en" else "id"
    phrase, query = TEMPLATES[lang][key]
    v = volcano or ""
    return phrase.format(v=v), query.format(v=v)


def extract_executed_topics(history: str) -> set[str]:
    """Identify which topics/actions were already asked or answered in conversation history."""
    if not history:
        return set()
    hist_l = history.lower()
    executed = set()
    if re.search(r"mitigasi.*gempa|panduan.*gempa|keselamatan.*gempa|aftershocks|drop, cover", hist_l):
        executed.add("quake_mitigation")
    if re.search(r"daftar.*gempa|kejadian gempa|catatan gempa|analisis geologi kejadian gempa", hist_l):
        executed.add("quake_list")
        executed.add("quake_latest")
    if re.search(r"gerakan tanah|tanah longsor|sigertan", hist_l):
        if re.search(r"mitigasi.*gerakan tanah|rekomendasi teknis mitigasi", hist_l):
            executed.add("ground_movement_mitigation")
        if re.search(r"laporan tanggap|kejadian gerakan tanah", hist_l):
            executed.add("ground_movement_latest")
            executed.add("ground_movement_list")
    if re.search(r"erupsi.*terakhir|catatan erupsi|letusan terakhir|tinggi kolom abu", hist_l):
        executed.add("erupt_history")
    if re.search(r"status.*level|rekomendasi resmi pvmbg|tingkat aktivitas", hist_l):
        executed.add("status")
    if re.search(r"terdekat adalah|jarak.*km|posisi anda", hist_l):
        executed.add("nearest")
        executed.add("safety")
    return executed


# ---------------------------------------------------------------------------
# Offer generation
# ---------------------------------------------------------------------------
def choose_follow_up(
    user_input: str,
    output_text: str,
    lang: str = "id",
    has_location: bool = False,
    is_knowledge: bool = False,
    nearest_volcano: Optional[str] = None,
    history: str = "",
) -> Optional[Tuple[str, str]]:
    """Pick ONE follow-up that continues the current conversation progressively.

    Returns (offer_phrase, resolved_query) or None when no sensible
    continuation exists (greetings, errors, missing-location prompts).
    """
    q = (user_input or "").lower()
    out = output_text or ""
    out_l = out.lower()

    if not out.strip():
        return None
    if is_knowledge:
        if re.search(r"rangkum|ringkas|summar", q):
            return None
        return _format_offer("doc_summary", lang)

    # Do not offer anything on prompts that ask the user for something, errors,
    # or small talk.
    if re.search(
        r"belum menerima lokasi|izin lokasi|aktifkan lokasi|mohon maaf|kendala|"
        r"location permission|enable location|sorry|halo! saya|hello! i am",
        out_l,
    ):
        return None

    candidates: List[str] = []
    volcano = None

    is_ground_movement = bool(
        re.search(r"\b(gerak(?:an)?\s*tanah|tanah\s*longsor|longsor|amblas(?:an)?|galodo|landslide|ground\s*movement)\b", q)
        or re.search(r"gerakan tanah|tanah longsor|ground movement", out_l)
    )
    is_quake = bool(
        re.search(r"\b(gempa|gempabumi|earthquake|tsunami)\b", q)
        or re.search(r"gempa bumi|kejadian gempa|tsunami", out_l)
    )
    is_aggregate = bool(
        re.search(r"\b(apa saja|daftar|semua|mana saja|which|list|aktif)\b", q)
        or re.search(r"\b(daftar gunung|status level [1-4]|status level i|level iii|level ii)\b", out_l)
    )
    is_status_answer = bool(re.search(r"status aktivitas gunung|activity status of mount", out_l)) and not is_aggregate
    is_eruption_list = bool(re.search(r"kejadian erupsi|eruption events?", out_l))
    is_location_answer = bool(re.search(r"\b(lokasi anda|your location|posisi anda)\b", out_l)) and not (is_ground_movement or is_quake)

    if is_ground_movement:
        if is_aggregate or re.search(r"daftar|list|semua", q) or "daftar laporan" in out_l:
            candidates.extend(["ground_movement_mitigation", "quake_list"])
        elif re.search(r"mitigasi|panduan|rekomendasi", q):
            candidates.extend(["ground_movement_list", "quake_latest"])
        else:
            candidates.extend(["ground_movement_list", "ground_movement_mitigation"])
    elif is_quake:
        if is_aggregate or re.search(r"daftar|list|semua|riwayat", q) or "daftar kejadian gempa" in out_l:
            # User already saw the list of earthquakes; offer mitigation or safety, DO NOT loop back to latest!
            candidates.extend(["quake_mitigation", "ground_movement_list"])
        elif re.search(r"mitigasi|panduan|keselamatan", q):
            candidates.extend(["quake_list", "ground_movement_latest"])
        else:
            candidates.extend(["quake_list", "quake_mitigation"])
    elif is_location_answer:
        # The user just learnt where they are / what is nearby: continue with
        # the official status + recommendation of the nearest volcano.
        volcano = nearest_volcano or _clean_volcano_name(
            (re.search(r"(?:terdekat adalah|nearest volcano is)\s+(?:Gunung|Mount)?\s*([A-Z][\w\-]*(?:\s+[A-Z][\w\-]*){0,2})", out) or [None, None])[1]
        ) or _first_volcano(out)
        if volcano:
            candidates.append("status")
        candidates.append("raised")
    elif is_status_answer:
        volcano = _first_volcano(out)
        level_match = re.search(r"level\s+(i{1,3}v?|iv|[1-4])", out_l)
        level_raw = level_match.group(1) if level_match else "i"
        level = {"i": 1, "ii": 2, "iii": 3, "iv": 4}.get(level_raw, int(level_raw) if level_raw.isdigit() else 1)
        if level >= 2 and has_location:
            candidates.append("safety")
        if has_location:
            candidates.append("nearest")
        candidates.append("erupt_today" if level >= 2 else "raised")
    elif is_eruption_list:
        listed = re.search(r":\s*([A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)?)\b", out)
        volcano = _clean_volcano_name(listed.group(1)) if listed else None
        if volcano:
            candidates.append("status")
        candidates.append("nearest" if has_location else "raised")
    elif is_aggregate:
        candidates.append("nearest" if has_location else "erupt_today")
    else:
        volcano = _first_volcano(out)
        if volcano:
            candidates.append("status")
        candidates.append("nearest" if has_location else "raised")

    executed_actions = extract_executed_topics(history + "\n" + user_input + "\n" + out)
    for key in candidates:
        if key in executed_actions:
            continue
        if key in ("status", "safety") and not volcano:
            continue
        phrase, query = _format_offer(key, lang, volcano)
        # Never offer what the user has just asked.
        if _similar(query, user_input):
            continue
        # Never offer a query that was already asked or answered in the ongoing history.
        if history and (query.lower() in history.lower() or _similar(query, history)):
            continue
        if key == "status" and volcano and is_status_answer:
            continue
        if key == "erupt_today" and re.search(r"erupsi|erupt|letusan|meletus", q) and re.search(r"hari ini|today", q):
            continue
        if key == "raised" and re.search(r"waspada|siaga|awas|advisory|watch|warning", q) and is_aggregate:
            continue
        if key in ("nearest", "safety") and re.search(r"terdekat|nearest|aman\b|safe", q):
            continue
        return phrase, query
    return None



def append_follow_up(output_text: str, offer: Optional[Tuple[str, str]], lang: str = "id") -> str:
    """Append the conversational offer at the end of the answer."""
    if not offer or OFFER_MARKER in (output_text or ""):
        return output_text or ""
    lang = "en" if lang == "en" else "id"
    phrase, _ = offer
    return (
        f"{(output_text or '').rstrip()}\n\n"
        f"{OFFER_MARKER} {OFFER_PREFIX[lang]}{phrase}? {OFFER_HINT[lang]}"
    )


# ---------------------------------------------------------------------------
# Reply resolution
# ---------------------------------------------------------------------------
def _extract_offer_query(message: str) -> Optional[str]:
    """Map the offer sentence in a previous assistant message back to a query."""
    if not message or OFFER_MARKER not in message:
        return None
    offer_line = message[message.rfind(OFFER_MARKER):]
    for lang, templates in TEMPLATES.items():
        prefix = OFFER_PREFIX[lang]
        if prefix.lower() not in offer_line.lower():
            continue
        for phrase, query in templates.values():
            pattern = re.escape(prefix + phrase).replace(r"\{v\}", r"(?P<v>.+?)")
            match = re.search(pattern + r"\?", offer_line, re.IGNORECASE)
            if match:
                volcano = match.groupdict().get("v") or ""
                return query.format(v=volcano.strip())

    # Dynamic fallback: parse offer intent directly if exact template escaped
    action_match = re.search(r"💬\s*(?:Apakah Anda ingin saya|Would you like me to)\s+([^?]+)\?", offer_line, re.IGNORECASE)
    if action_match:
        act = action_match.group(1).strip()
        v_m = re.search(r"(?:Gunung|Mount)\s+([A-Z][a-zA-Z\s\-]+?)(?:\s*,|\s*\(|\s*\?|$)", act, re.IGNORECASE)
        v_name = v_m.group(1).strip() if v_m else ""
        if re.search(r"erupsi|letusan|erupt", act, re.IGNORECASE):
            return f"Erupsi terakhir Gunung {v_name}".strip() if v_name else "Gunung apa saja yang erupsi hari ini?"
        if re.search(r"status.*rekomendasi", act, re.IGNORECASE):
            return f"Status Gunung {v_name}".strip() if v_name else "Gunung apa saja yang berstatus waspada, siaga, atau awas?"
        if re.search(r"lokasi.*aman|safe", act, re.IGNORECASE):
            return f"Apakah lokasi saya aman dari Gunung {v_name}?".strip() if v_name else "Apakah lokasi saya aman?"
        if re.search(r"terdekat|nearest", act, re.IGNORECASE):
            return "Gunung api terdekat dari saya"
        if re.search(r"di atas normal|aktif|raised|above normal", act, re.IGNORECASE):
            return "Gunung apa saja yang berstatus waspada, siaga, atau awas?"
        if re.search(r"mitigasi.*gempa|earthquake.*mitigation", act, re.IGNORECASE):
            return "Bagaimana panduan mitigasi bencana gempa bumi?"
        if re.search(r"gempa|earthquake", act, re.IGNORECASE):
            return "Daftar kejadian gempa bumi terkini"
        if re.search(r"gerakan tanah|longsor|landslide", act, re.IGNORECASE):
            return "Daftar kejadian gerakan tanah"

    return None


def resolve_follow_up_reply(user_input: str, history_messages: Iterable, lang: str = "id"):
    """Interpret short "ya"/"tidak" replies against the last assistant offer.

    Returns:
        ("affirm", resolved_query)   -> run the pipeline with resolved_query
        ("decline", reply_text)      -> answer directly without the pipeline
        None                         -> treat the input as a normal question
    """
    text = (user_input or "").strip()
    if not text or len(text.split()) > 5:
        return None
    is_affirm = bool(AFFIRM_RE.match(text))
    is_decline = bool(DECLINE_RE.match(text)) and not is_affirm
    if not (is_affirm or is_decline):
        return None

    last_assistant_text = None
    query = None
    for msg in reversed(list(history_messages or [])):
        role = getattr(msg, "role", None) if not isinstance(msg, dict) else msg.get("role")
        if role == "assistant":
            resp = getattr(msg, "response", None) if not isinstance(msg, dict) else msg.get("response")
            if isinstance(resp, str):
                try:
                    import json
                    resp = json.loads(resp)
                except Exception:
                    pass
            if isinstance(resp, dict):
                if resp.get("pending_action"):
                    query = resp["pending_action"]
                    break
                if resp.get("follow_ups") and isinstance(resp["follow_ups"], list) and len(resp["follow_ups"]) > 0:
                    query = resp["follow_ups"][0].get("action") or resp["follow_ups"][0].get("query")
                    break
            last_assistant_text = getattr(msg, "message", None) if not isinstance(msg, dict) else msg.get("message")
            break

    if not query and last_assistant_text:
        m_comm = re.search(r"<!--\s*PENDING_ACTION:\s*(.+?)\s*-->", last_assistant_text)
        if m_comm:
            query = m_comm.group(1).strip()
        else:
            query = _extract_offer_query(last_assistant_text)

    if not query:
        return None

    if is_affirm:
        return "affirm", query
    if lang == "en":
        return "decline", "Alright. Feel free to ask anything else about volcanoes, earthquakes, or geological hazards."
    return "decline", "Baik. Silakan tanyakan hal lain seputar gunung api, gempa bumi, atau bencana geologi kapan saja."


# ---------------------------------------------------------------------------
# Backward-compatible helpers (old call sites)
# ---------------------------------------------------------------------------
def generate_follow_ups(user_input: str, output_text: Optional[str] = "", volcano_name: Optional[str] = None,
                        intent: Optional[str] = None, lang: str = "id", is_knowledge: bool = False,
                        document_titles: Optional[List[str]] = None, has_location: bool = False) -> List[str]:
    offer = choose_follow_up(user_input, output_text or "", lang, has_location, is_knowledge, volcano_name)
    return [offer[1]] if offer else []


def format_follow_ups_for_whatsapp(text: Optional[str], follow_ups: List[str], lang: str = "id") -> str:
    # Offers are now embedded in the answer itself for every channel.
    return text or ""
