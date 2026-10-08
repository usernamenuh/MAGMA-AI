import re
def detect_volcano_name(text):
    if not text:
        return None
    try:
        from utils.pipeline_helpers import _detect_volcano_name, load_volcano_cache, VOLCANO_COMMON_ALIASES
        cached = load_volcano_cache()
        if cached:
            detected = _detect_volcano_name(text, cached)
            if detected:
                return detected[0]
        text_norm = text.lower()
        for alias, code in VOLCANO_COMMON_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", text_norm):
                return code
    except Exception:
        pass
    return None