# ---------- Standard Library ----------
import os
import re
import json
import time
import math
import random
import asyncio
import unicodedata
from contextvars import ContextVar
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# ---------- Third-Party ----------
import requests
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from fastembed import TextEmbedding
from scipy.special import softmax
from rapidfuzz import fuzz

# ---------- Local Modules ----------
from services.esdm_auth import get_auth_header
from utils.extraction import detect_volcano_name
from utils.filter import extract_date_range

# ---------- Environment ----------
load_dotenv(override=True)

BASE_URL = os.getenv("BASE_URL")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://0.0.0.0:8002/v1")
SELECTED_CHAT_MODEL = ContextVar("selected_chat_model", default=None)


def set_chat_model(model):
    return SELECTED_CHAT_MODEL.set(model)


def reset_chat_model(token):
    SELECTED_CHAT_MODEL.reset(token)


def run_with_chat_model(model, function, *args, **kwargs):
    token = set_chat_model(model)
    try:
        return function(*args, **kwargs)
    finally:
        reset_chat_model(token)

# ---------- Cache ----------
CACHE_FILE = "volcano_cache.json"
CACHE_TTL = timedelta(hours=1)

# ---------- Clients ----------
session = requests.Session()

embedder = TextEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# ---------- Category Keywords ----------
category_keywords = {
    "VAR": [
        # Indonesian
        "laporan aktivitas",
        "aktivitas gunung api",
        "status gunung",
        "observasi visual",
        "seismik",
        "pengamatan",
        "aktivitas vulkanik",
        "cuaca di gunung",
        "tingkat aktivitas",
        "aktivitas harian",
        "pengamatan erupsi",

        # English
        "activity report",
        "volcanic activity",
        "volcano status",
        "visual observation",
        "seismic",
        "monitoring",
        "volcanic observations",
        "weather on volcano",
        "activity level",
        "daily activity",
    ],

    "VEN": [
        # Indonesian
        "letusan",
        "erupsi",
        "kejadian letusan",
        "peristiwa letusan",
        "foto letusan",
        "debu vulkanik",
        "awan panas",
        "lava",
        "ven",
        "tinggi kolom abu letusan",
        "pengamatan erupsi",
        "kejadian abu vulkanik",
        "kolom abu vulkanik",

        # English
        "eruption",
        "eruptive event",
        "eruption incident",
        "eruption photo",
        "volcanic ash",
        "pyroclastic flow",
        "lava flow",
        "volcanic event",
    ],

    "VONA": [
        # Indonesian
        "peringatan penerbangan",
        "notifikasi penerbangan",
        "laporan abu vulkanik",
        "ketinggian",
        "sebaran abu",
        "warna kode peringatan",
        "waktu",
        "ash advisory",
        "aviation",
        "vona",

        # English
        "flight warning",
        "flight notification",
        "volcanic ash report",
        "eruption height",
        "ash dispersion",
        "warning color code",
        "eruption time",
        "aviation warning",
        "ash cloud",
        "vona report",
    ],

    "GERAKAN_TANAH": [
        # Indonesian
        "gerakan tanah",
        "tanah longsor",
        "longsor",
        "longsoran",
        "pergerakan tanah",
        "tanah bergerak",
        "amblasan",
        "tanah ambles",
        "kejadian longsor",
        "bencana longsor",
        "rawan longsor",
        "laporan gerakan tanah",
        "status gerakan tanah",
        "info gerakan tanah",

        # English
        "landslide",
        "ground movement",
        "land movement",
        "soil movement",
        "landslide event",
        "landslide report",
        "landslide status",
    ],

    "GEMPA_BUMI": [
        # Indonesian
        "gempa",
        "gempabumi",
        "gempa bumi",
        "kejadian gempa",
        "aktivitas gempa",
        "laporan gempa",
        "gempa terkini",
        "gempa terbaru",
        "tsunami",
        "lindu",
        "seismik gempa",

        # English
        "earthquake",
        "quake",
        "seismic",
        "seismicity",
        "latest earthquake",
        "tsunami",
    ],
}

# ---------- API Endpoints ----------
endpoints = {
    "VAR": {
        "list": "{{url}}/api/v2/volcano/var",
        "latest": "{{url}}/api/v2/volcano/var",
        "detail": "{{url}}/api/v2/volcano/var/{code}",
        "filter": "{{url}}/api/v2/volcano/var/filter",
        "detail-noticenumber": "{{url}}/api/v2/volcano/var/{code}/{noticenumber}",
    },
    "VEN": {
        "list": "{{url}}/api/v2/volcano/ven",
        "latest": "{{url}}/api/v2/volcano/ven/latest",
        "detail": "{{url}}/api/v2/volcano/ven/{id}",
        "filter": "{{url}}/api/v2/volcano/ven/filter",
    },
    "VONA": {
        "list": "{{url}}/api/v2/volcano/vona",
        "latest": "{{url}}/api/v2/volcano/vona/latest",
        "detail": "{{url}}/api/v2/volcano/vona/{uuid}",
        "filter": "{{url}}/api/v2/volcano/vona/filter",
    },
    "GERAKAN_TANAH": {
        "list": "{{url}}/api/v2/ground-movement",
        "latest": "{{url}}/api/v2/ground-movement/latest",
        "detail": "{{url}}/api/v2/ground-movement/{id}",
        "filter": "{{url}}/api/v2/ground-movement/filter",
    },
    "GEMPA_BUMI": {
        "list": "{{url}}/api/v2/earthquake-tsunami",
        "latest": "{{url}}/api/v2/earthquake-tsunami/latest",
        "detail": "{{url}}/api/v2/earthquake-tsunami/{id}",
        "filter": "{{url}}/api/v2/earthquake-tsunami/filter",
    },
    "GEOHAZARD": {
        "my_location": "{{url}}/api/public/geohazard/my-location",
    },
}

# ---------- Query Utilities ----------
ERUPTION_TERMS = [
    "letusan",
    "erupsi",
    "meletus",
    "aktivitas vulkanik",
    "eruption",
    "erupt",
]

TEMPORAL_TERMS = [
    "terakhir",
    "paling baru",
    "sebelumnya",
    "riwayat",
    "kapan terakhir",
    "pernah meletus",
    "last",
    "latest",
    "most recent",
    "previous",
    "history",
    "when did.*last",
]

ERUPTION_RE = re.compile(r"\b(" + "|".join(ERUPTION_TERMS) + r")\b", re.I)
TEMPORAL_RE = re.compile(r"(" + "|".join(TEMPORAL_TERMS) + r")", re.I)

ERUPTION_KEYWORDS = [
    "meletus",
    "erupsi",
    "letusan",
    "gunung meletus",
    "eruption",
    "erupt",
    "erupted",
    "volcano erupting",
]

# ---------- Mount Level Queries ----------
MOUNT_LEVEL_QUERIES = [
    # Indonesian
    "gunung api mana yang berstatus normal",
    "gunung mana yang aman untuk pendakian",
    "gunung yang tidak dapat didaki",
    "status gunung api di indonesia saat ini",
    "status gunungapi di indonesia saat ini",
    "kondisi gunungapi di indonesia saat ini",
    "gunung api berstatus waspada",
    "gunung api berstatus siaga",
    "gunung api berstatus awas",
    "gunungapi berstatus waspada",
    "gunungapi berstatus siaga",
    "gunungapi berstatus awas",
    "berapa gunung yang aman didaki",
    "berapa gunung yang ditutup",
    "bagaimana kondisi gunungapi di indonesia saat ini",
    "bagaimana status gunungapi di indonesia saat ini",
    "gunung apa saja yang level siaga",
    "gunung mana yang sedang siaga",
    "apa saja gunung yang tidak boleh didaki",
    "gunung apa saja yang tidak aman didaki",
    "bagaimana kondisi gunung api saat ini",
    "berapa gunung api yang sedang siaga",
    "status terbaru gunung merapi",
    "status semua gunung di indonesia",
    "Daftar gunung api yang saat ini dimonitor dalam sistem",
    "Tampilkan peringatan global terkini terkait aktivitas gunung berapi.",
    "Informasi tentang tingkat aktivitas gunung api saat ini.",

    # English
    "List volcanoes currently monitored in the system",
    "which volcano is at normal status",
    "which volcano is safe to climb",
    "which volcano currently active",
    "which volcano currently on alert",
    "which volcanoes should not be climbed",
    "current condition of volcanic activity",
    "volcanoes that are closed for hiking",
    "current volcano status in indonesia",
    "volcano alert level",
    "how many active volcanoes in indonesia",
    "how many volcanoes are safe to climb",
    "volcano alert level normal",
    "volcano alert level advisory",
    "volcano alert level watch",
    "volcano alert level warning",
]

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)      # replace punctuation with space
    text = re.sub(r"\s+", " ", text)         # normalize multiple spaces
    text = re.sub(r"(.)\1{2,}", r"\1", text) # reduce repeated characters: e.g., "aaa" -> "a"
    return text.strip()

def contains_eruption_keyword(text: str) -> bool:
    return any(keyword in text for keyword in ERUPTION_KEYWORDS)

def contains_status_intent(text: str) -> bool:
    """
    Extra guard: ensure query is about status/level/safety,
    not just volcano mention.
    """
    STATUS_KEYWORDS = [
        "status", "tingkat", "level", "normal", "waspada", "siaga", "awas", 
        "aman", "pendakian", "ditutup", "kondisi",
        "tidak boleh didaki", "tidak aman", "ditutup untuk pendakian"
    ]
    return any(k in text for k in STATUS_KEYWORDS)


def check_if_mount_level(user_input: str, threshold: int = 70) -> bool:
    """
    Returns True if input query is about volcano status/level/safety,
    robust to typos, punctuation, and slight variations.
    """
    if not user_input:
        return False

    text = normalize_text(user_input)

    # Ignore eruption-specific queries
    if contains_eruption_keyword(text):
        return False

    # Ensure it mentions status/safety keywords
    if not contains_status_intent(text):
        return False

    # Compare with robust queries using fuzzy matching
    max_score = max(
        fuzz.token_set_ratio(text, q) for q in MOUNT_LEVEL_QUERIES
    )

    return max_score >= threshold


import re
from rapidfuzz import fuzz

AROUND_KEYWORDS = [
    # Indonesian
    "sekitar saya",
    "di sekitar saya",
    "di daerah saya",
    "dekat sini",
    "terdekat",
    "lokasi saya",
    "sekitar sini",

    # English
     "around me", "near me", "nearby",
    "close to me", "closest to me",
    "in my area", "local area",
    "near my location"
]

AROUND_REFERENCE_QUERIES = [
    # Indonesian
    "letusan di sekitar saya",
    "pergerakan tanah di sekitar saya",
    "gempa dekat sini",
    "status gunung api di daerah saya",
    "gunung api terdekat",
    
    # English
    "volcano eruption near me",
    "earthquake around me",
    "landslide in my area",
    "current volcano status nearby",
    "volcanoes close to me",
]



def contains_around_keyword(text: str) -> bool:
    """Check if text contains any 'around me / local area' keywords."""
    return any(k in text for k in AROUND_KEYWORDS)

def check_around(user_input: str, threshold: int = 75) -> bool:
    """
    Check if the query is asking about events around user's location.
    
    Args:
        user_input (str): User query
        threshold (int): Fuzzy matching threshold (0-100)
    
    Returns:
        bool: True if query is about "around me", else False
    """
    if not user_input:
        return False

    text = normalize_text(user_input)

    # Quick keyword check
    if contains_around_keyword(text):
        return True

    # Fuzzy match against reference queries
    max_score = max(fuzz.token_set_ratio(text, q) for q in AROUND_REFERENCE_QUERIES)
    return max_score >= threshold


def detect_eruption_query_type(text: str):
    """
    Returns:
      - 'VEN_LAST'    → last / historical eruption
      - 'VEN_GENERAL' → eruption info (non-temporal)
      - None
    """
    if not text:
        return None

    text = text.lower()

    if not ERUPTION_RE.search(text):
        return None

    if TEMPORAL_RE.search(text):
        return "VEN_LAST"

    return "VEN_GENERAL"

def _normalize(v):
    return v / (np.linalg.norm(v) + 1e-12)

GENERIC_VOLCANO_QUERIES = [
    "gunung berapi",
    "aktivitas gunung berapi",
    "kondisi gunung berapi",
    "keadaan gunung berapi",
    "status gunung berapi",
    "gunung api"
]

STOPWORDS = {
    "apa","saja","yang","tidak","aman","didaki","status","aktivitas",
    "info","hari","ini","terakhir","kapan","berapa","dimana","mengapa",
    "tampilkan","laporan","global","terkini","kondisi","keadaan"
}



VOLCANO_COMMON_ALIASES = {
    "lewotolo": "LEW",
    "ili lewotolok": "LEW",
    "lewotolok": "LEW",
    "krakatau": "KRA",
    "anak krakatau": "KRA",
    "marapi": "MAR",
    "merapi": "MER",
    "lewotobi laki-laki": "LBI",
    "lewotobi laki laki": "LBI",
    "lewotobi lakilaki": "LBI",
    "lewotobi perempuan": "LBP",
    "tangkuban perahu": "TPR",
    "tangkuban parahu": "TPR",
    "tangkuban": "TPR",
    "tandikat": "TAN",
    "dieng": "DIE",
    "ijen": "IJN",
    "raung": "RAU",
    "kelud": "KEL",
    "bromo": "BRO",
    "semeru": "SMR",
    "sinabung": "SIN",
    "kerinci": "KER",
    "soputan": "SOP",
    "lokon": "LOK",
    "karangetang": "KRG",
    "ruang": "RUA",
    "ibu": "IBU",
    "gamalama": "GAM",
    "dukono": "DUK",
    "awu": "AWU",
    "gamkonora": "GMR",
}


def _detect_volcano_name(text, volcano_list):
    if not text:
        return None
    text_low = text.lower()
    # normalize: remove volcano prefixes, keep space
    text_norm = re.sub(r"\b(gunung|gn|g|mount|mt)\.?\b", "", text_low)
    text_norm = re.sub(r"[^\w\s]", " ", text_norm)
    text_norm = re.sub(r"\s+", " ", text_norm).strip()
    tokens = [t for t in re.findall(r"\b[a-z]+\b", text_norm) if t not in STOPWORDS]

    # Common generic words that should never match as a solitary volcano token
    GENERIC_WORDS = {
        "api", "berapi", "gunungapi", "gunung", "aktif", "keaktifan", "daftar",
        "list", "semua", "apa", "saja", "mana", "indonesia", "nasional", "daerah",
        "provinsi", "wilayah", "terkini", "terbaru", "bencana"
    }

    # 1. Check known common aliases first
    for alias, code in VOLCANO_COMMON_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text_norm):
            return [code]

    if not volcano_list:
        return None

    detected = []

    # Helper to extract name and code safely
    def _v_name(v):
        if isinstance(v, dict):
            return (v.get("ga_nama_gapi") or v.get("name") or "").lower()
        return str(v).lower()

    def _v_code(v):
        if isinstance(v, dict):
            return v.get("ga_code") or v.get("code") or ""
        return str(v)

    # 2. Exact phrase match (with prefix stripping on both sides)
    for v in volcano_list:
        name = _v_name(v)
        clean_name = re.sub(r"\b(gunung|gn|g|mount|mt)\.?\b", "", name).strip()
        if clean_name and clean_name not in GENERIC_WORDS and (re.search(rf"\b{re.escape(clean_name)}\b", text_norm) or clean_name in text_norm):
            detected.append(v)

    if detected:
        return [_v_code(v) for v in detected if _v_code(v)]

    # 3. Token match (excluding generic terms like 'api' so 'gunung api aktif' never matches Banda Api)
    filtered_query_tokens = [t for t in tokens if t not in GENERIC_WORDS and len(t) > 2]
    if filtered_query_tokens:
        for v in volcano_list:
            name_tokens = (
                set(_v_name(v).split())
                - {"gunung", "g.", "gn.", "api", "berapi", "gunungapi"}
            )
            if set(filtered_query_tokens) & name_tokens:
                detected.append(v)

    if detected:
        return [_v_code(v) for v in detected if _v_code(v)]

    # 4. Token-level fuzzy and prefix fallback (handles slight typos like 'lewotolo' -> 'lewotolok', 'ged' -> 'gede')
    best_match = None
    best_score = 0
    for token in filtered_query_tokens:
        if len(token) < 3:
            continue
        for v in volcano_list:
            name = _v_name(v)
            clean_name = re.sub(r"\b(gunung|gn|g|mount|mt)\.?\b", "", name).strip()
            name_parts = clean_name.split()
            for part in name_parts:
                if len(part) < 3 or part in GENERIC_WORDS:
                    continue
                # Disambiguate between Merapi and Marapi
                if {token, part} == {"merapi", "marapi"}:
                    continue
                # Prefix match for tokens with length >= 3
                if len(token) >= 3 and part.startswith(token):
                    score = 90
                else:
                    score = fuzz.ratio(token, part) if fuzz else (100 if token == part else 0)
                if score > best_score:
                    best_score = score
                    best_match = v

    if best_match and best_score >= 75:
        print(f"[VOLCANO] Fuzzy match: {best_match.get('ga_nama_gapi')} score={best_score}")
        return [best_match["ga_code"]]

    return None


# ---------- Category embeddings ----------
def build_category_embeddings():
    cat_embs = {}
    for cat, kws in category_keywords.items():
        emb = np.array(list(embedder.embed(kws)))
        emb = np.mean(emb, axis=0)
        cat_embs[cat] = _normalize(emb)
    return cat_embs


def build_corpus(examples):
    corpus_texts = []
    corpus_meta = []
    for ex in examples:
        text = f"{ex.get('name','')} | {ex.get('method','')} | {ex.get('url','')} | {ex.get('example_response_body','')}"
        corpus_texts.append(text)
        corpus_meta.append(ex)
    corpus_embs = np.array(list(embedder.embed(corpus_texts)))
    corpus_embs = corpus_embs / (np.linalg.norm(corpus_embs, axis=1, keepdims=True) + 1e-12)
    return corpus_texts, corpus_meta, corpus_embs


# ---------- Infer category ----------
def infer_example_category(example):
    url = (example.get("url") or "").lower()
    name = (example.get("name") or "").lower()
    if "vona" in url or "vona" in name:
        return "VONA"
    if "informasi-letusan" in url or "letusan" in name:
        return "VEN"
    if "magma-var" in url or "var" in name:
        return "VAR"
    if "gerakan-tanah" in url or "gerakan tanah" in name.lower():
        return "GERAKAN_TANAH"
    return None

def is_out_of_scope(user_input, history=None, embedder=None,
                    volcano_names=None,
                    semantic_threshold=0.32):
    text = user_input.lower().strip()
    oos_person_pattern = re.compile(
        r"\b(siapa|siapakah|who|whos|whose|who is|who was|who are)\b", re.I
    )
    if oos_person_pattern.search(text):
        return True
    history_texts = []

    if history:
        if isinstance(history, str):
            history_texts = [history]
        elif isinstance(history, dict):
            # extract "content" if present
            if "content" in history and isinstance(history["content"], str):
                history_texts = [history["content"]]
        elif isinstance(history, list):
            for item in history:
                if isinstance(item, str):
                    history_texts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("content"), str):
                    history_texts.append(item["content"])

    history_text = " ".join(history_texts).lower()

    volcano_keywords = [
        "gunung", "letusan", "erupsi", "magma", "vulkan", "lava",
        "status", "aktivitas", "kawah", "abu",
        "volcano", "eruption", "erupt", "crater", "ash",
        "volcanic", "lava flow", "magma chamber",
        "alert level", "volcanology", "seismic activity",
        "alert level", "seismic", "earthquake",
        "volcanology", "volcano status"
    ]

    history_has_keyword = any(kw in history_text for kw in volcano_keywords)

    history_has_volcano_name = False
    if volcano_names:
        for gapi in volcano_names:
            if gapi["ga_nama_gapi"].lower() in history_text:
                history_has_volcano_name = True
                break

    history_in_domain = history_has_keyword or history_has_volcano_name

    current_has_keyword = any(kw in text for kw in volcano_keywords)

    current_has_name = False
    if volcano_names:
        for name in volcano_names:
            if name["ga_nama_gapi"].lower() in text:
                current_has_name = True
                break

    if embedder is not None:
        q_emb = _normalize(np.array(next(embedder.embed([user_input]))))
        domain_emb = _normalize(np.array(next(embedder.embed([
            "Informasi gunung api, status gunung, letusan, magma, vulkanologi."
        ]))))
        semantic_score = float(np.dot(q_emb, domain_emb))
    else:
        semantic_score = 0

    semantic_in_domain = semantic_score >= semantic_threshold

    if history_in_domain:
        if current_has_keyword or current_has_name or semantic_in_domain:
            return False
        else:
            return True   # OUT OF SCOPE

    if not current_has_keyword and not current_has_name and not semantic_in_domain:
        return True  # OUT OF SCOPE

    return False  # IN SCOPE



async def semantic_recommend_api_improved_async(user_input, examples, history, cache=None, top_k=3):
    import time
    t0 = time.perf_counter()

    text = user_input.strip()

    # ---- Cache setup ----
    if cache is None:
        cache = {}

    loop = asyncio.get_running_loop()

    # Build vectors in background thread (CPU heavy)
    if "cat_embs" not in cache:
        cache["cat_embs"] = await asyncio.to_thread(build_category_embeddings)

    if "corpus" not in cache:
        cache["corpus"] = await asyncio.to_thread(build_corpus, examples)

    cat_embs = cache["cat_embs"]
    corpus_texts, corpus_meta, corpus_embs = cache["corpus"]

    # ---- Step A: detect category ----
    keyword_category = None
    for cat, kws in category_keywords.items():
        for kw in kws:
            if kw in text.lower():
                keyword_category = cat
                break
        if keyword_category:
            break

    # ---- Step B: async embedding ----
    async def async_embed(text):
        return np.array(next(embedder.embed([text])))

    q_emb = await async_embed(text)
    q_emb = _normalize(q_emb)

    # Category scores
    cat_scores = {cat: float(np.dot(q_emb, emb)) for cat, emb in cat_embs.items()}
    best_cat, _ = max(cat_scores.items(), key=lambda x: x[1])
    predicted_category = keyword_category or best_cat

    # ---- Step C: filter candidate APIs ----
    candidates_idx = [
        i for i, ex in enumerate(corpus_meta)
        if infer_example_category(ex) == predicted_category
    ]

    if not candidates_idx:
        candidates_idx = list(range(len(corpus_meta)))

    # ---- Volcano code detection (async safe) ----
    api_data = await asyncio.to_thread(get_mount_code)

    if api_data:
        volcano_code = _detect_volcano_name(text, api_data)
    else:
        volcano_code = detect_volcano_name(text)


    if volcano_code:
        filtered = []
        for idx in candidates_idx:
            ex = corpus_meta[idx]
            example_body = ex.get("example_request_body") or {}

            if isinstance(example_body, list):
                if example_body and "code" in example_body[0]:
                    filtered.append(idx)
            elif isinstance(example_body, dict):
                if "code" in example_body:
                    filtered.append(idx)

        if filtered:
            candidates_idx = filtered

    # ---- Step D: semantic similarity ----
    cos_scores = corpus_embs[candidates_idx] @ q_emb

    top_indices = np.argsort(cos_scores)[::-1][:top_k]

    recommended_api = []
    params_list = []
    body_list = []

    for idx in top_indices:
        global_idx = candidates_idx[idx]
        ex = corpus_meta[global_idx]

        params = (ex.get("parameters") or {}).copy()
        if volcano_code and "code" in params:
            params["code"] = volcano_code

        example_body = ex.get("example_request_body")
        body_list.append(example_body if example_body is not None else None)

        recommended_api.append(ex.get("url"))
        params_list.append(params)

    # ---- Out-of-scope detection ----
    OOS_THRESHOLD = 0.30
    is_oos = await asyncio.to_thread(is_out_of_scope, user_input, history, embedder, api_data)

    best_cat, best_score = max(cat_scores.items(), key=lambda x: x[1])

    if best_score < OOS_THRESHOLD and is_oos:
        return ({
            "recommended_api": [],
            "out_of_scope": True
        }, cache)

    return ({
        "recommended_api": recommended_api,
        "parameters": params_list,
        "body": body_list,
        "volcano_code": volcano_code,
        "out_of_scope": False
    }, cache)


def normalize_text(text):
    """Lowercase + remove accents for more robust Indonesian/English matching."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text

def predict_query_intent(text, volcano_names=None, volcano_code=None):
    """
    Predict user intents from English/Indonesian text.
    Returns a list of intents: latest_info, by_volcano, by_date, general
    """
    text = normalize_text(text)
    intents = []

    # ---------- VOLCANO-SPECIFIC ----------
    volcano_keywords = [
        "this volcano", "that volcano", "the volcano",
        "mount", "mt ", "volcano",
        "gunung", "gn ", "kode gunung", "kode v", "volcano code",
        "volcano name",
        "which volcano",
        "about volcano"
    ]
    is_volcano = any(kw in text for kw in volcano_keywords)
    if volcano_names:
        is_volcano = is_volcano or any(normalize_text(name) in text for name in volcano_names)

    if is_volcano or volcano_code:
        intents.append("by_volcano")

    # ---------- LATEST INFO ----------
    if not is_volcano:  # only consider latest_info if NOT by_volcano
        latest_keywords = [
            "latest", "recent", "most recent", "current", "now", "update", "updated info",
            "show activity", "volcanic activity",
            "terbaru", "terkini", "paling baru", "status sekarang",
            "aktivitas terkini", "laporan terkini", "info terbaru",
            "kondisi sekarang", "aktivitas saat ini"
        ]
        if any(kw in text for kw in latest_keywords) or \
           (("aktivitas" in text and "tanggal" not in text) or ("activity" in text and "date" not in text)):
            intents.append("latest_info")

    # ---------- DATE-BASED ----------
    date_keywords = [" on ", " at ", " from ", " between ", " date ", " range ", " period ",
                     " tanggal ", " pada ", " dari ", " sampai ", " rentang ", " periode ", " mulai "]
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{1,2} \w+ \d{4}\b",
        r"\b\d{1,2} \w+ \d{2}\b",
        r"\b(202[0-9]|203[0-9])\b"
    ]
    if any(kw in text for kw in date_keywords) or any(re.search(p, text) for p in date_patterns):
        intents.append("by_date")

    # fallback
    if not intents:
        intents.append("general")

    return list(set(intents))




def build_corpus_with_category_weighted(examples, category_keywords, cat_weight=0.5):
    """
    Build corpus embeddings from examples, then apply category embedding boost.

    Each example embedding becomes:
        example_emb = normalize(example_emb + cat_weight * cat_emb)

    Returns:
        corpus_texts, corpus_meta, corpus_embs
    """
    import numpy as np

    # 1️⃣ Build category embeddings
    cat_embs = {}
    for cat, kws in category_keywords.items():
        emb = np.array(list(embedder.embed(kws)))
        emb = np.mean(emb, axis=0)
        cat_embs[cat] = _normalize(emb)

    corpus_texts = []
    corpus_meta = []
    corpus_embs = []

    for ex in examples:
        # 2️⃣ Example text embedding
        text = f"{ex.get('name', '')} | {ex.get('method', '')} | {ex.get('url', '')} | {ex.get('example_response_body', '')}"
        ex_emb = np.array(next(embedder.embed([text])))
        ex_emb = _normalize(ex_emb)

        # 3️⃣ Determine example category
        ex_cat = infer_example_category(ex)  # returns "VAR", "VEN", "VONA" or None

        # 4️⃣ Weighted combination with category embedding
        if ex_cat and ex_cat in cat_embs:
            ex_emb = _normalize(ex_emb + cat_weight * cat_embs[ex_cat])

        # 5️⃣ Add to corpus
        corpus_texts.append(text)
        corpus_meta.append(ex)
        corpus_embs.append(ex_emb)

    corpus_embs = np.array(corpus_embs)
    return corpus_texts, corpus_meta, corpus_embs, cat_embs

def is_code_endpoint(url: str) -> bool:
    return "{code}" in (url or "")

def is_notice_number(user_input: str) -> bool:
    text = user_input.lower()


    patterns = [
    r"notice\s*number",
    r"nomor\s*notice",
    r"no\.?\s*notice",
    r"notice\s*\d+",
    r"nomor\s*\d+",
    ]


    return any(re.search(p, text) for p in patterns)

def is_notice_number_endpoint(url: str, parameters: dict | None) -> bool:
    url = (url or "").lower()
    params = parameters or {}

    return (
        "{noticenumber}" in url or
        "notice_number" in params or
        "noticenumber" in params
    )

def detect_category_from_keywords(text, category_keywords):
    text = text.lower()
    scores = {}

    for cat, keywords in category_keywords.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[cat] = score

    best_cat = max(scores, key=scores.get)
    return best_cat if scores[best_cat] > 0 else None

def check_latest(text):
    latest_patterns = [
        "terbaru",
        "paling baru",
        "update terbaru",
        "laporan terbaru",
        "latest", "recent", "most recent", "current",
        "today", "right now", "currently", "as of today"
    ]
    return any(p in text.lower() for p in latest_patterns)

AVIATION_KEYWORDS = [
    # Indonesian
    "penerbangan",
    "notifikasi penerbangan",
    "peringatan penerbangan",
    "kode warna penerbangan",
    "vona",

    # English
    "flight",
    "aviation",
    "ash cloud",
    "volcanic ash advisory",
]

def is_aviation_query(text: str) -> bool:
    text = text.lower()
    return any(k in text for k in AVIATION_KEYWORDS)

def extract_eruption_id(text):
    match = re.search(r"\b(?:uuid|id)\s*(\d+)\b", text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_notice_number(text):
    match = re.search(r"\b(\d{10,12})\b", text)  # adjust length for MAGMA noticenumber
    if match:
        return match.group(1)
    return None
    
def semantic_recommend_api_improved_en(
    user_input,
    examples,
    history,
    cache=None,
    volcano_code=None,
    top_k=3,
    category_weight=0.5,
    nearest_volcano=None
):
    import re
    import numpy as np

    text = user_input.lower()
    predicted_category = detect_category_from_keywords(text, category_keywords)
    # -------------------------------
    # GERAKAN TANAH (LANDSLIDE)
    # -------------------------------
    if predicted_category == "GERAKAN_TANAH":

        if check_around(text):
            return ({
                "intents": ["around_me"],
                "recommended_api": [endpoints["GERAKAN_TANAH"]["list"]],
                "parameters": [{}],
                "body": [None],
                "method": "GET",
                "volcano_code": None,
                "out_of_scope": False
            }, cache)

        if check_latest(text):
            return ({
                "intents": ["latest"],
                "recommended_api": [endpoints["GERAKAN_TANAH"]["latest"]],
                "parameters": [{}],
                "body": [None],
                "method": "GET",
                "volcano_code": None,
                "out_of_scope": False
            }, cache)

        return ({
            "intents": ["general"],
            "recommended_api": [endpoints["GERAKAN_TANAH"]["list"]],
            "parameters": [{}],
            "body": [None],
            "method": "GET",
            "volcano_code": None,
            "out_of_scope": False
        }, cache)

    if cache is None:
        cache = {}

    # ================================
    # 🔍 HELPERS
    # ================================
    eruption_id = extract_eruption_id(text)
    notice_number = extract_notice_number(text)
    has_uuid = bool(re.search(r"\b(uuid|id)\s*\d+", text))
    date_range = extract_date_range(text)

    # ------------------------
    # 🌋 Volcano detection (VERY IMPORTANT)
    # ------------------------
    api_data = get_mount_code()
    if api_data and volcano_code is None:
        volcano_code = _detect_volcano_name(user_input, api_data)
    elif volcano_code is None:
        volcano_code = detect_volcano_name(user_input)

    print(f"[DEBUG] Detected volcano code: {volcano_code}")

    # ================================
    # 🔥 1. STRONG RULE-BASED LAYER
    # ================================

    # ------------------------
    # 1. MOST SPECIFIC → ID
    # ------------------------
    if eruption_id:
        return ({
            "intents": ["detail"],
            "recommended_api": [endpoints["VEN"]["detail"]],
            "parameters": [{}],
            "body": [{"id": eruption_id}],
            "volcano_code": None,
            "out_of_scope": False
        }, cache)

    # ------------------------
    # 2. NOTICE NUMBER
    # ------------------------
    if notice_number:
        return ({
            "intents": ["detail"],
            "recommended_api": [endpoints["VAR"]["detail-noticenumber"]],
            "parameters": [{}],
            "body": [{"code": volcano_code, "noticenumber": notice_number}],
            "volcano_code": volcano_code,
            "out_of_scope": False
        }, cache)


    if volcano_code:
        if isinstance(volcano_code, list):
            volcano_code = volcano_code[0]

        if any(k in text for k in ["latest", "report", "status", "activity", "condition"]):
            return ({
                "intents": ["by_volcano"],
                "recommended_api": [endpoints["VAR"]["detail"]],  # KEEP TEMPLATE
                "parameters": [{}],
                "body": [{"code": volcano_code}],
                "volcano_code": volcano_code,
                "out_of_scope": False
            }, cache)

        if any(k in text for k in ["eruption", "ash", "history"]):
            return ({
                "intents": ["by_volcano"],
                "recommended_api": [endpoints["VAR"]["detail"]],
                "parameters": [{}],
                "body": [{"code": volcano_code}],
                "volcano_code": volcano_code,
                "out_of_scope": False
            }, cache)

    # ------------------------
    # 🔥 4. GENERIC FILTER DETECTION (FIX FOR 422)
    # ------------------------
    FILTER_KEYWORDS = [
        "filter",
        "containing",
        "with",
        "that have",
        "where",
        "based on",
        "including"
    ]

    LIST_KEYWORDS = ["show", "list", "find"]

    HAS_FILTER_INTENT = any(k in text for k in FILTER_KEYWORDS)
    HAS_LIST_INTENT = any(k in text for k in LIST_KEYWORDS)
    HAS_DATE = date_range is not None

    if HAS_FILTER_INTENT or HAS_DATE:
        start_date, end_date = date_range if HAS_DATE else (None, None)

        body_payload = {}

        if volcano_code:
            body_payload["code"] = volcano_code

        if start_date:
            body_payload["start_date"] = start_date

        if end_date:
            body_payload["end_date"] = end_date

        if not body_payload:
            body_payload["query"] = user_input

        return ({
            "intents": ["by_filter"],
            "recommended_api": [endpoints["VEN"]["filter"]],
            "parameters": [{}],
            "body": [body_payload],
            "volcano_code": volcano_code,
            "out_of_scope": False
        }, cache)

    # ------------------------
    # 5. ASH / ERUPTION
    # ------------------------
    if any(k in text for k in ["ash", "eruption", "volcanic ash"]):
        if "latest" in text:
            return ({
                "intents": ["latest_info"],
                "recommended_api": [endpoints["VEN"]["latest"]],
                "parameters": [{}],
                "body": [None],
                "volcano_code": None,
                "out_of_scope": False
            }, cache)

        return ({
            "intents": ["by_filter"],
            "recommended_api": [endpoints["VEN"]["filter"]],
            "parameters": [{}],
            "body": [{
                "code": volcano_code,
            }],
            "volcano_code": volcano_code,
            "out_of_scope": False
        }, cache)

    # ------------------------
    # 6. AVIATION (VONA)
    # ------------------------
    if is_aviation_query(text):
        if "latest" in text:
            return ({
                "intents": ["latest_info"],
                "recommended_api": [endpoints["VONA"]["latest"]],
                "parameters": [{}],
                "body": [None],
                "volcano_code": None,
                "out_of_scope": False
            }, cache)

        return ({
            "intents": ["general"],
            "recommended_api": [endpoints["VONA"]["list"]],
            "parameters": [{}],
            "body": [None],
            "volcano_code": None,
            "out_of_scope": False
        }, cache)

    # ------------------------
    # 7. CCTV (no endpoint available — out of scope)
    # ------------------------
    if "cctv" in text or "air traffic" in text:
        return ({
            "intents": ["technical"],
            "recommended_api": [],
            "parameters": [{}],
            "body": [None],
            "volcano_code": volcano_code,
            "out_of_scope": True
        }, cache)

    # ------------------------
    # 8. SEISMIC
    # ------------------------
    if any(k in text for k in ["earthquake", "seismic", "tremor"]):
        return ({
            "intents": ["technical"],
            "recommended_api": [endpoints["VAR"]["filter"]],
            "parameters": [{}],
            "body": [{"code": volcano_code}],
            "volcano_code": volcano_code,
            "out_of_scope": False
        }, cache)

    # ------------------------
    # 9. GENERAL LATEST
    # ------------------------
    if "latest" in text and not volcano_code:
        return ({
            "intents": ["latest_info"],
            "recommended_api": [endpoints["VEN"]["latest"]],
            "parameters": [{}],
            "body": [None],
            "volcano_code": None,
            "out_of_scope": False
        }, cache)

    # ================================
    # 🧠 2. SEMANTIC FALLBACK
    # ================================
    corpus_texts, corpus_meta, corpus_embs, cat_embs = build_corpus_with_category_weighted(
        examples, category_keywords, cat_weight=category_weight
    )

    q_vec = _normalize(np.array(next(embedder.embed([user_input]))))
    scores = corpus_embs @ q_vec
    sorted_idx = np.argsort(scores)[::-1]

    filtered_idx = []
    for i in sorted_idx:
        url = corpus_meta[i]["url"]
        if "{uuid}" in url and not has_uuid:
            continue
        filtered_idx.append(i)

    top_idx = filtered_idx[:top_k]

    recommended_api = []
    params_list = []
    body_list = []

    for i in top_idx:
        ex = corpus_meta[i]
        params = (ex.get("parameters") or {}).copy()

        if volcano_code and "code" in params:
            params["code"] = volcano_code

        recommended_api.append(ex.get("url"))
        params_list.append(params)
        body_list.append(ex.get("example_request_body"))

    return ({
        "intents": ["semantic_fallback"],
        "recommended_api": recommended_api,
        "parameters": params_list,
        "body": body_list,
        "volcano_code": volcano_code,
        "out_of_scope": False
    }, cache)

def semantic_recommend_api_improved(user_input, examples, history, cache=None, volcano_code=None, top_k=3, category_weight=0.5, nearest_volcano=None):
    import numpy as np
    import time

    t0 = time.perf_counter()
    text = user_input.strip().lower()

    # -------------------------------
    # EARLY CATEGORY DETECTION
    # -------------------------------
    predicted_category = detect_category_from_keywords(text, category_keywords)

    # Landslide around-me override
    if predicted_category == "GERAKAN_TANAH":
        # Around me → use filter
        if check_around(text):
            return ({
                "intents": ["around_me"],
                "recommended_api": [endpoints["GERAKAN_TANAH"]["list"]],
                "parameters": [{}],  # lat lon should be injected later
                "body": [None],
                "volcano_code": None,
                "out_of_scope": False
            }, cache)

        # Latest info
        if check_latest(text):
            return ({
                "intents": ["latest"],
                "recommended_api": [endpoints["GERAKAN_TANAH"]["latest"]],
                "parameters": [{}],
                "body": [None],
                "volcano_code": None,
                "out_of_scope": False
            }, cache)

        # Default
        return ({
            "intents": ["general"],
            "recommended_api": [endpoints["GERAKAN_TANAH"]["list"]],
            "parameters": [{}],
            "body": [None],
            "volcano_code": None,
            "out_of_scope": False
        }, cache)

    if cache is None:
        cache = {}

    # -------------------------------
    # A. Build Corpus + Category-Weighted Embeddings
    # -------------------------------
    if "corpus" not in cache or "cat_embs" not in cache:
        corpus_texts, corpus_meta, corpus_embs, cat_embs = build_corpus_with_category_weighted(
            examples, category_keywords, cat_weight=category_weight
        )
        cache["corpus"] = (corpus_texts, corpus_meta, corpus_embs)
        cache["cat_embs"] = cat_embs
    else:
        corpus_texts, corpus_meta, corpus_embs = cache["corpus"]
        cat_embs = cache["cat_embs"]

    # -------------------------------
    # B. Predict high-level intent
    # -------------------------------
    api_data = get_mount_code()
    volcano_names = [v['ga_nama_gapi'] for v in api_data] if api_data else None
    print(f"mount codes: {volcano_names}")

    intents = predict_query_intent(user_input, volcano_names, volcano_code)

    print(f"intents: {intents}")

    # -------------------------------
    # C. Find volcano code
    # -------------------------------
    if api_data and volcano_code is None:
        volcano_code = _detect_volcano_name(user_input, api_data)
    elif volcano_code is None:
        volcano_code = detect_volcano_name(user_input)

    eruption_type = detect_eruption_query_type(text)

    if is_aviation_query(text):
        if check_latest(text):
            return ({
                "intents": ["latest_info"],
                "recommended_api": [endpoints["VONA"]["latest"]],
                "parameters": [{}],
                "body": [None],
                "volcano_code": None,
                "out_of_scope": False
            }, cache)

        return ({
            "intents": ["general"],
            "recommended_api": [endpoints["VONA"]["list"]],
            "parameters": [{}],
            "body": [None],
            "volcano_code": None,
            "out_of_scope": False
        }, cache)
        
    TODAY_TERMS = [
        "hari ini", "today",
        "sekarang", "now",
        "saat ini", "right now"
    ]
    if eruption_type in ["VEN_GENERAL", "VEN_LAST"] and any(t in text for t in TODAY_TERMS):
        return ({
            "intents": ["latest_info"],
            "recommended_api": [endpoints["VEN"]["latest"]],
            "parameters": [{}],
            "body": [None],
            "volcano_code": None,
            "out_of_scope": False
        }, cache)

    date_range = extract_date_range(text)
    volcano_code_nearest = nearest_volcano.get("ga_code") if nearest_volcano else None
    print(f"Extracted date range: {date_range}, volcano_code: {volcano_code}, nearest_volcano_code: {volcano_code_nearest}, eruption_type: {eruption_type}, predicted_category: {predicted_category}")
    if date_range and volcano_code_nearest:
        start_date, end_date = date_range
        if (intents == ["by_volcano"]):
            predicted_category = "VAR"
        print(f"Detected date range: {start_date} to {end_date}")
        return ({
                "intents": ["by_date"],
                "recommended_api": [endpoints[predicted_category]["filter"] if predicted_category else endpoints["VEN"]["filter"]],
                "parameters": [{}],
                "body": [{
                    "code": volcano_code if volcano_code else volcano_code_nearest,
                    "start_date": start_date,
                    "end_date": end_date
                }],
                "volcano_code": None,
                "out_of_scope": False
            }, cache)
            
    # Case 1: "last eruption", "letusan terakhir", etc.
    if eruption_type == "VEN_LAST" and volcano_code:
        return ({
                    "recommended_api": [
                        endpoints["VEN"]["filter"]
                    ],
                    "parameters": [{}],
                    "body": [
                        {"code": volcano_code}
                    ],
                    "volcano_code": volcano_code,
                    "out_of_scope": False
                }, cache)

    # Case 2: general eruption query → force VEN category
    if eruption_type == "VEN_GENERAL":
        predicted_category = "VEN"
    
    # -------------------------------
    # D. Filter candidates by intent
    # -------------------------------
    allowed_indices = []
    notice_required = is_notice_number(user_input)

    if eruption_type is None and intents == ["by_volcano"]:
        # Only allow volcano-related endpoints
        allowed_indices = [
            i for i, meta in enumerate(corpus_meta)
            if (
                (is_code_endpoint(meta.get("url")) or "code" in (meta.get("parameters") or {}))
            )
        ]
    elif "general" in intents or eruption_type is None:
        allowed_indices = list(range(len(corpus_meta)))

    else:
        allowed_indices = [
            i for i, meta in enumerate(corpus_meta)
            if (
                (not is_notice_number_endpoint(meta.get("url"), meta.get("parameters"))
                or notice_required)
            ) and any(
                (
                    intent == "latest_info" and (
                        "latest" in (meta.get("url") or "").lower() or
                        "current" in (meta.get("url") or "").lower() or
                        "terkini" in (meta.get("url") or "").lower() or
                        "status" in (meta.get("url") or "").lower() or
                        re.search(r"/var($|/)", (meta.get("url") or "").lower())
                    )
                ) or
                (
                    intent == "by_volcano"
                    and is_code_endpoint(meta.get("url"))
                ) or
                (
                    intent == "by_volcano"
                    and "code" in (meta.get("parameters") or {})
                ) or
                (
                    intent == "by_date" and (
                        "start_date" in (meta.get("parameters") or {}) or
                        "end_date" in (meta.get("parameters") or {})
                    )
                )
                for intent in intents
            )
        ]
    SEISMIC_KEYWORDS = [
        "seismic",
        "seismik",
        "gempa",
        "earthquake",
        "tremor"
    ]

    def contains_seismic(text):
        return any(k in text for k in SEISMIC_KEYWORDS)
        
    if not contains_seismic(text):
        allowed_indices = [
            i for i in allowed_indices
            if "seismic" not in corpus_meta[i]["url"]
        ]
    # fallback if no allowed index
    if not allowed_indices:
        allowed_indices = list(range(len(corpus_meta)))

    print(f"Allowed indices: {allowed_indices}")
    # -------------------------------
    # E. Semantic similarity ranking
    # -------------------------------
    q_raw = _normalize(np.array(next(embedder.embed([user_input]))))

    # Category boosting for the query
    cat_scores = {cat: float(np.dot(q_raw, emb)) for cat, emb in cat_embs.items()}
    sorted_cats = sorted(cat_scores.items(), key=lambda x: x[1], reverse=True)
    top_selected = sorted_cats[:top_k]

    if top_selected:
        selected_embs = np.array([cat_embs[c] for c, _ in top_selected])
        selected_scores = np.array([s for _, s in top_selected])
        weights = softmax(selected_scores)
        cat_boost = _normalize((weights[:, None] * selected_embs).sum(axis=0))
    else:
        cat_boost = np.zeros_like(q_raw)

    q_final = _normalize(q_raw + category_weight * cat_boost)

    # -------------------------------
    # E. Semantic similarity ranking
    # -------------------------------
    allowed_embs = corpus_embs[allowed_indices]
    scores = allowed_embs @ q_final

    # Single authoritative ranking
    sorted_local_idx = np.argsort(scores)[::-1]

    print("[RANKING]")
    for rank, local_i in enumerate(sorted_local_idx, start=1):
        global_i = allowed_indices[local_i]
        meta = corpus_meta[global_i]

        print(
            f"[RANK {rank}]",
            "local=", local_i,
            "global=", global_i,
            meta["url"],
            "score=",
            round(float(scores[local_i]), 4)
        )

    # Select top-k from the SAME ordering
    top_local_idx = sorted_local_idx[:top_k]
    print("Top local idx:", top_local_idx)

    # -------------------------------
    # F. Build recommended APIs
    # -------------------------------
    recommended_api = []
    params_list = []
    body_list = []

    for local_idx in top_local_idx:
        global_idx = allowed_indices[local_idx]
        ex = corpus_meta[global_idx]

        params = (ex.get("parameters") or {}).copy()
        if volcano_code and "code" in params:
            params["code"] = volcano_code if volcano_code else volcano_code_nearest

        recommended_api.append(ex.get("url"))
        params_list.append(params)
        body_list.append(ex.get("example_request_body"))

    # -------------------------------
    # G. Out-of-scope detection
    # -------------------------------
    best_cat, best_score = max(cat_scores.items(), key=lambda x: x[1])
    OOS_THRESHOLD = 0.30
    is_oos = is_out_of_scope(user_input, history, embedder, volcano_names=api_data)

    if best_score < OOS_THRESHOLD and is_oos:
        return {"recommended_api": [], "out_of_scope": True}, cache

    # /home/gunung-api/informasi-letusan/{id}
    eruption_id = extract_eruption_id(user_input)
    if eruption_id:
        return {
            "intents": ["technical"],
            "recommended_api": [endpoints["VEN"]["detail"]],
            "parameters": [{}],
            "body": [{"id": eruption_id}],
            "volcano_code": None,
            "out_of_scope": False
        }, cache

    # /magma-var/{code}/{noticenumber}
    notice_number = extract_notice_number(user_input)
    if notice_number or is_notice_number(user_input):
        return {
            "intents": ["technical"],
            "recommended_api": [endpoints["VAR"]["detail-noticenumber"]],
            "parameters": [{}],
            "body": [{"code": volcano_code, "noticenumber": notice_number}],
            "volcano_code": volcano_code if volcano_code else volcano_code_nearest,
            "out_of_scope": False
        }, cache

    return {
        "intents": intents,
        "recommended_api": recommended_api,
        "parameters": params_list,
        "body": body_list,
        "volcano_code": volcano_code if volcano_code else nearest_volcano.get("ga_code") if nearest_volcano else None,
        "out_of_scope": False
    }, cache

def get_openai_client():
    base = os.getenv("OPENAI_API_BASE", "http://localhost:8002/v1")

    return OpenAI(
        base_url=base,
        api_key=os.getenv("OPENAI_API_KEY", "my-super-secret-admin-key")
    )

def safe_json_loads(s: str):
    if not s or not isinstance(s, str):
        return {}

    s = s.strip()
    s = re.sub(r"^```(?:json)?", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"```$", "", s.strip())
    match = re.search(r"\{[\s\S]*\}", s)
    if match:
        s = match.group(0).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {}


def load_examples(path="simplified_endpoints_full_with_body.json"):
    with open(path, "r") as f:
        return json.load(f)


def call_api(api_url, method="GET", params=None, body=None, max_retries=2, backoff=1.5):
    session.headers.update(get_auth_header())
    method = method.upper()
    params = params or {}
    body = body or {}
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    def fix_date(item):
        if isinstance(item, dict):
            if item.get("start_date") and item.get("end_date"):
                if not item.get("code"):
                    item["code"] = "AGU"
            if item.get("end_date"):
                item["end_date"] = yesterday
        return item

    if isinstance(body, list):
        body = [fix_date(b) for b in body]
    elif isinstance(body, dict):
        body = fix_date(body)

    if isinstance(body, dict) and "{code}" in api_url and "code" in body:
        code = body.pop("code")

        if isinstance(code, list):
            code = code[0]

        api_url = api_url.replace("{code}", str(code))

        if not body:
            body = None

    if isinstance(body, dict) and "{noticenumber}" in api_url and "noticenumber" in body:
            notice = body.pop("noticenumber")
            api_url = api_url.replace("{noticenumber}", str(notice))
            if not body:
                body = None

    for attempt in range(max_retries):
        try:
            if method == "POST":
                response = session.post(api_url, json=body, params=params, timeout=30)
            elif method == "PUT":
                response = session.put(api_url, json=body, params=params, timeout=30)
            elif method == "DELETE":
                response = session.delete(api_url, params=params, timeout=30)
            else:
                request_kwargs = {"params": params, "timeout": 30}
                if body not in ({}, [], None):
                    request_kwargs["json"] = body
                response = session.get(api_url, **request_kwargs)

            if response.status_code == 401:
                print("⚠️ API returned 401 Unauthorized. Attempting stakeholder auto-login...")
                from services.esdm_auth import auto_login
                if auto_login():
                    session.headers.update(get_auth_header())
                    continue

            response.raise_for_status()
            return response.json()

        except Exception as e:
            if hasattr(e, "response") and getattr(e.response, "status_code", None) == 401:
                from services.esdm_auth import auto_login
                if auto_login():
                    session.headers.update(get_auth_header())
                    continue
            if attempt < max_retries - 1:
                sleep_time = backoff ** attempt + random.uniform(0, 0.3)
                print(f"⚠️ API call failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {sleep_time:.2f}s")
                time.sleep(sleep_time)
            else:
                print(f"❌ API failed permanently: {e}")
                return {"error": str(e), "api_url": api_url, "response": getattr(e, 'response', None)}


def fetch_api_simple(api_url):
    session.headers.update(get_auth_header())

    try:
        response = session.get(api_url)
        if response.status_code == 401:
            print("⚠️ fetch_api_simple returned 401 Unauthorized. Refreshing token...")
            from services.esdm_auth import auto_login
            if auto_login():
                session.headers.update(get_auth_header())
                response = session.get(api_url)

        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"❌ API failed permanently: {e}")

        safe_response = None
        if hasattr(e, "response") and e.response is not None:
            try:
                safe_response = {
                    "status_code": e.response.status_code,
                    "text": e.response.text
                }
            except:
                safe_response = None

        return {
            "error": str(e),
            "api_url": api_url,
            "response": safe_response
        }


def get_volcano_var_data(volcano_code: str):
    """
    Fetch the latest VAR (Volcano Activity Report) detail for a volcano code,
    including official PVMBG recommendations, recent visual/seismic observations.
    """
    if not volcano_code:
        return None
    url = resolve_api_url(f"/api/v2/volcano/var/{volcano_code}")
    res = fetch_api_simple(url)
    if isinstance(res, dict) and isinstance(res.get("data"), list) and res["data"]:
        return res["data"][0]
    if isinstance(res, list) and res:
        return res[0]
    if isinstance(res, dict) and not res.get("error"):
        return res
    return None


def save_volcano_cache(data):
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }

    with open(CACHE_FILE, "w") as f:
        json.dump(payload, f)

def load_volcano_cache():
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, "r") as f:
            payload = json.load(f)

        timestamp = datetime.fromisoformat(payload["timestamp"])

        if datetime.utcnow() - timestamp < CACHE_TTL:
            return payload["data"]

    except Exception as e:
        print("Cache load failed:", e)

    return None

def get_mount_code():
    api_url = resolve_api_url("/api/v2/volcano/list")

    try:
        data = fetch_api_simple(api_url)
        if isinstance(data, list) and data:
            save_volcano_cache(data)
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list) and data["data"]:
            save_volcano_cache(data["data"])
            return data["data"]
    except Exception as e:
        print(f"❌ Failed to get Mount code: {e}")

    return load_volcano_cache() or []


def get_today_eruption_events(max_pages: int = 10) -> dict:
    """Fetch today's VEN records without relying on the failing filter endpoint."""
    today = datetime.now().strftime("%Y-%m-%d")
    events = []
    api_url = resolve_api_url("/api/v2/volcano/ven")
    for page in range(1, max_pages + 1):
        payload = call_api(api_url, params={"page": page}, max_retries=1)
        if not isinstance(payload, dict) or payload.get("error"):
            return {"error": "Data erupsi belum dapat diambil", "events": events, "date": today}
        rows = payload.get("data") or []
        if not rows:
            break
        events.extend(row for row in rows if row.get("local_date") == today)
        if any(row.get("local_date") and row.get("local_date") < today for row in rows):
            break
    return {"date": today, "events": events}


def resolve_api_url(api_url: str) -> str:
    base_url = BASE_URL.rstrip("/")
    if api_url.startswith("/"):
        return f"{base_url}{api_url}"
    return api_url.replace("{{url}}", base_url)


def model_chat(
    messages,
    model=None,
    temperature=0.2,
    max_tokens=1500,
    stop=None,
    repetition_penalty=False,
    max_retries=3
):
    # repetition penalty mapping ke OpenAI-style params:
    frequency_penalty = 0.7 if repetition_penalty else 0.0
    presence_penalty = 0.2 if repetition_penalty else 0.0

    for attempt in range(max_retries):
        try:
            selected = SELECTED_CHAT_MODEL.get() or model
            is_groq = bool(selected and selected.startswith("groq:"))
            is_openrouter = bool(selected and selected.startswith("openrouter:"))

            if is_groq:
                base = "https://api.groq.com/openai/v1"
                selected_model = selected.removeprefix("groq:")
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise RuntimeError("GROQ_API_KEY belum diisi")
                effective_max_tokens = max_tokens
                timeout_val = float(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
            elif is_openrouter:
                base = "https://openrouter.ai/api/v1"
                selected_model = selected.removeprefix("openrouter:")
                api_key = os.getenv("OPENROUTER_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENROUTER_API_KEY belum diisi")
                effective_max_tokens = max_tokens
                timeout_val = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "30"))
            else:
                base = os.getenv("OPENAI_API_BASE", "http://localhost:8002/v1")
                selected_model = os.getenv("OPENAI_MODEL") or "qwen2.5-1.5b-instruct"
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY belum diisi")
                local_limit = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "2048"))
                effective_max_tokens = min(max_tokens, local_limit)
                timeout_val = float(os.getenv("LOCAL_MODEL_TIMEOUT_SECONDS", "45"))

            payload = {
                "model": selected_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": effective_max_tokens,
            }
            if stop:
                payload["stop"] = stop
            if repetition_penalty:
                payload["frequency_penalty"] = frequency_penalty
                payload["presence_penalty"] = presence_penalty
            if is_openrouter:
                # Free reasoning models can spend the whole token budget on an
                # internal trace and return no answer. Request answer-only output.
                payload["reasoning"] = {"exclude": True}
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            if is_openrouter:
                headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000")
                headers["X-OpenRouter-Title"] = os.getenv("OPENROUTER_APP_NAME", "MAGMA AI")
            response = requests.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout_val,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"].get("content")
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("Model mengembalikan jawaban kosong")
            content = content.strip()
            rejected_prefixes = (
                "user safety:",
                "assistant safety:",
                "here's a thinking process:",
                "here is a thinking process:",
            )
            lowered_content = content.lower()
            if is_openrouter and (
                lowered_content.startswith(rejected_prefixes)
                or "safety categories:" in lowered_content
            ):
                raise RuntimeError("Router memilih model klasifikasi/reasoning, mencoba model lain")
            return content

        except Exception as e:
            if not is_openrouter and not is_groq:
                print(f"❌ Local model call failed: {e}")
                return None
            # If external provider fails (429 rate limit or retries exhausted), seamlessly fallback to local model
            if "429" in str(e) or attempt >= max_retries - 1:
                provider_name = "Groq" if is_groq else "OpenRouter"
                print(f"⚠️ {provider_name} failed ({e}). Falling back to local model...")
                try:
                    local_base = os.getenv("OPENAI_API_BASE", "http://localhost:8002/v1")
                    local_model = os.getenv("OPENAI_MODEL") or "qwen2.5-1.5b-instruct"
                    local_limit = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "2048"))
                    local_payload = {
                        "model": local_model,
                        "messages": [{"role": m.role, "content": m.content} for m in messages],
                        "temperature": temperature,
                        "max_tokens": min(max_tokens, local_limit),
                    }
                    if stop:
                        local_payload["stop"] = stop
                    resp = requests.post(
                        f"{local_base}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'my-super-secret-admin-key')}",
                            "Content-Type": "application/json"
                        },
                        json=local_payload,
                        timeout=float(os.getenv("LOCAL_MODEL_TIMEOUT_SECONDS", "45")),
                    )
                    resp.raise_for_status()
                    c = resp.json()["choices"][0]["message"].get("content")
                    if isinstance(c, str) and c.strip():
                        print("✅ Fallback to local model succeeded!")
                        return c.strip()
                except Exception as loc_err:
                    print(f"❌ Fallback to local model also failed: {loc_err}")
                return None

            sleep_time = 2 ** attempt + random.uniform(0, 0.5)
            print(f"⚠️ Model call failed: {e}. Retrying in {sleep_time:.1f}s")
            time.sleep(sleep_time)


def extract_volcano_name(text):
    match = re.search(r"gunung\s+([A-Za-zÀ-ÿ'\-]+)", text, re.IGNORECASE)
    return match.group(1).strip().title() if match else None

def crosscheck_api(api_url: str, examples: list):
    """Return True if the API URL exists in the examples JSON."""
    if not api_url:
        return False
    urls = {ex.get("url") for ex in examples if "url" in ex}
    return api_url in urls

def similarity(a: str, b: str) -> float:
    """Return a similarity ratio between 0 and 1."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def recommend_api_fallback(user_input: str, examples: list):
    """
    Fallback recommender when recommend_api() returns None.
    - Matches user_input with category_keywords to find the closest category.
    - Returns the 'list' endpoint of that category as a safe default.
    - If the matched example has request body with 'code', sets code='SIN' by default.
    """

    if not user_input:
        return json.dumps({
            "recommended_api": None,
            "reason": "No user input provided for fallback"
        })

    best_category = None
    best_score = 0

    # --- Match input with category keywords ---
    for category, keywords in category_keywords.items():
        for kw in keywords:
            score = similarity(user_input, kw)
            if score > best_score:
                best_score = score
                best_category = category

    fallback_api = None
    request_body = None

    if best_category and best_score > 0.35:
        fallback_api = endpoints[best_category]["list"]
    elif examples:
        fallback_api = examples[0].get("url")

    if examples and fallback_api:
        for ex in examples:
            ex_url = ex.get("url", "")
            if ex_url and ex_url in fallback_api:
                body = ex.get("example_request_body")
                if body:
                    # Ensure code key exists and assign default
                    if isinstance(body, list):
                        body = body[0]
                    if "code" in body:
                        body["code"] = body.get("code", "SIN") or "SIN"
                    request_body = body
                break

    return json.dumps({
        "recommended_api": fallback_api,
        "category": best_category,
        "confidence": round(best_score, 3),
        "reason": "Used fallback list endpoint based on category match" if best_category else "No match; fallback to first example API",
        "body": request_body or {}
    })


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in KM
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_volcano(user_lat, user_lon, volcano_list):
    nearest = None
    min_dist = float("inf")

    for v in volcano_list:
        try:
            vlat = float(v.get("ga_lat_gapi"))
            vlon = float(v.get("ga_lon_gapi"))
        except:
            continue

        dist = haversine_distance(user_lat, user_lon, vlat, vlon)
        if dist < min_dist:
            min_dist = dist
            nearest = v

    return nearest, min_dist

def check_if_nearest_question(user_input: str) -> bool:
    text = user_input.lower()

    triggers = [
        # Indonesian
        "gunung api terdekat",
        "gunung terdekat",
        "gapi terdekat",
        "apakah daerah saya aman",
        "daerah saya aman",
        "apakah wilayah saya aman",
        "wilayah saya aman",
        "apakah lokasi saya aman",
        "lokasi saya aman",
        "aman tidak daerah saya",

        "is my area safe",
        "is my location safe",
        "is it safe here",
        "am i safe here",
        "is this area safe",
        "safety near me",
        "is my region safe"
    ]

    return any(t in text for t in triggers)

def filter_history(history_text, fallback_keyword):
    """
    Remove assistant messages that contain the fallback, and also remove the preceding user message.
    Assumes history is in format:
        user: ...
        assistant: ...
    """
    if not history_text:
        return ""

    lines = history_text.splitlines()
    filtered_lines = []
    skip_next_user = False

    for i, line in enumerate(lines):
        if line.lower().startswith("assistant:") and fallback_keyword.lower() in line.lower():
            # Mark to skip the previous user line if it exists
            if filtered_lines and filtered_lines[-1].lower().startswith("user:"):
                filtered_lines.pop()
            continue  # Skip this assistant line
        filtered_lines.append(line)

    return "\n".join(filtered_lines)

def is_empty_response(resp):
    """Determine if API response is empty or invalid."""
    if not resp:
        return True

    if isinstance(resp, dict):
        # Technical error
        if "error" in resp:
            return True
        if "error" in resp or resp.get("status") in ["error", "empty_data"]:
            return True
        # Standard data endpoints (list inside 'data')
        if "data" in resp:
            data_val = resp.get("data")
            if data_val is None:
                return True
            if isinstance(data_val, list) and len(data_val) == 0:
                return True
            # dict inside 'data' with no keys
            if isinstance(data_val, dict) and len(data_val) == 0:
                return True

        # magma-var/{code} or {code}/{noticenumber}
        if "gunung_api" in resp and "laporan_terakhir" in resp:
            # valid response
            return False

        # fallback: empty dict
        if not resp:
            return True

    # List response
    if isinstance(resp, list) and len(resp) == 0:
        return True

    return False

def get_closest_gerakan_tanah_data(api_url, user_lat, user_lon, method="GET", params=None, body=None):
    page = 1
    closest_data = None
    min_distance = float('inf')

    while True:
        url = f"{api_url}?page={page}"

        try:
            response = call_api(url, method=method, params=params, body=body)
        except Exception as e:
            print(f"⚠️ Failed fetching page {page}: {e}")
            print("Returning closest data found so far (fallback).")
            break  # stop pagination but keep existing closest_data

        if not response:
            print("⚠️ Empty response received. Stopping.")
            break

        data_list = response.get("data", [])
        if not data_list:
            break

        for item in data_list:
            lat = item.get("latitude")
            lon = item.get("longitude")

            if lat is not None and lon is not None:
                distance = haversine_distance(user_lat, user_lon, lat, lon)

                if distance < min_distance:
                    min_distance = distance
                    closest_data = item

        links = response.get("links", {})
        if not links.get("next"):
            break

    return closest_data


def get_latest_earthquake_data() -> dict:
    """
    Fetches the latest official earthquake event from MAGMA API v2.
    Falls back to BMKG open public API if MAGMA returns None or errors.
    """
    api_url = resolve_api_url("/api/v2/earthquake-tsunami/latest")
    res = call_api(api_url, max_retries=1)
    if isinstance(res, dict) and res.get("success") and res.get("data"):
        data = res["data"]
        return {
            "source": "MAGMA ESDM",
            "api_url": api_url,
            "judul": data.get("judul"),
            "datetime": data.get("local_datetime") or data.get("date"),
            "timezone": data.get("time_zone") or data.get("zone") or "WIB",
            "magnitude": data.get("magnitude"),
            "kedalaman": data.get("kedalaman"),
            "lokasi": data.get("lokasi"),
            "kota_terdekat": data.get("kota_terdekat"),
            "tsunami": data.get("berpotensi_tsunami", False),
            "rekomendasi": data.get("rekomendasi"),
            "deskripsi": data.get("deskripsi"),
            "share_url": data.get("share", {}).get("url") if isinstance(data.get("share"), dict) else None,
            "raw": data,
        }

    # Fallback to BMKG official open API
    try:
        bmkg_resp = requests.get("https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json", timeout=6)
        if bmkg_resp.status_code == 200:
            bmkg_data = bmkg_resp.json()
            eq = bmkg_data.get("Infogempa", {}).get("gempa", {})
            if eq:
                return {
                    "source": "BMKG",
                    "api_url": "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json",
                    "judul": f"Gempa Mag {eq.get('Magnitude')} di {eq.get('Wilayah')}",
                    "datetime": f"{eq.get('Tanggal')} {eq.get('Jam')}",
                    "timezone": "WIB",
                    "magnitude": eq.get("Magnitude"),
                    "kedalaman": eq.get("Kedalaman"),
                    "lokasi": eq.get("Wilayah"),
                    "kota_terdekat": eq.get("Wilayah"),
                    "tsunami": "tidak berpotensi tsunami" in eq.get("Potensi", "").lower(),
                    "rekomendasi": eq.get("Potensi"),
                    "deskripsi": f"Pusat gempa: {eq.get('Wilayah')}. Dirasakan: {eq.get('Dirasakan', '-')}",
                    "share_url": None,
                    "raw": eq,
                }
    except Exception as e:
        print(f"⚠️ BMKG fallback error: {e}")

    return {}


def get_earthquake_list() -> list:
    """
    Fetches the recent list of official earthquake events from MAGMA API v2.
    """
    api_url = resolve_api_url("/api/v2/earthquake-tsunami")
    res = call_api(api_url, max_retries=1)
    if isinstance(res, dict) and res.get("data"):
        data = res["data"]
        if isinstance(data, list):
            return data
    elif isinstance(res, list):
        return res
    return []


def get_geohazard_location_awareness(lat: float, lng: float) -> dict:
    """
    Queries MAGMA Geohazard Awareness API for given latitude and longitude.
    Returns vulnerability info for earthquake and ground movement.
    """
    try:
        api_url = resolve_api_url(f"/api/public/geohazard/my-location?lat={lat}&lng={lng}")
        res = call_api(api_url, max_retries=1)
        if isinstance(res, dict) and res.get("success") and res.get("data"):
            return res["data"]
    except Exception as e:
        print(f"⚠️ Geohazard location awareness error: {e}")
    return {}


def get_latest_ground_movement_data() -> dict:
    """
    Fetches the latest official ground movement (gerakan tanah) report from MAGMA API v2.
    """
    api_url = resolve_api_url("/api/v2/ground-movement/latest")
    res = call_api(api_url, max_retries=1)
    if isinstance(res, dict) and res.get("data"):
        data = res["data"]
        laporan = data.get("laporan", {})
        tanggapan = data.get("tanggapan", {})
        return {
            "source": "Badan Geologi (PVMBG)",
            "api_url": api_url,
            "id": laporan.get("id"),
            "judul": laporan.get("judul"),
            "datetime": laporan.get("local_datetime"),
            "pelapor": laporan.get("pelapor"),
            "deskripsi": laporan.get("deskripsi"),
            "tingkat_kerentanan": laporan.get("tingkat_kerentanan"),
            "tipe": tanggapan.get("tipe"),
            "dampak": tanggapan.get("dampak"),
            "kondisi": tanggapan.get("kondisi"),
            "rekomendasi": data.get("rekomendasi") or tanggapan.get("rekomendasi"),
            "raw": data,
        }
    return {}


def get_ground_movement_list() -> list:
    """
    Fetches the recent list of ground movement reports from MAGMA API v2.
    """
    api_url = resolve_api_url("/api/v2/ground-movement")
    res = call_api(api_url, max_retries=1)
    if isinstance(res, dict) and res.get("data"):
        data = res["data"]
        if isinstance(data, list):
            return data
    elif isinstance(res, list):
        return res
    return []

