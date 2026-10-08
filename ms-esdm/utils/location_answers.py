"""Deterministic answers for location-based questions.

Location questions have exact answers once coordinates and the PVMBG volcano
list are known, so they are answered here without an LLM. This keeps distances
and alert levels exact and avoids the intent classifier routing them to a
canned template.
"""
from __future__ import annotations

import math
import re
from typing import Iterable, Optional

# Above this radius a reported device position is too coarse to name a
# neighbourhood reliably (typical for IP / cell-tower positioning).
COARSE_ACCURACY_M = 2000
# Volcanoes above Normal within this radius are called out explicitly.
NEARBY_ALERT_RADIUS_KM = 50

STATUS_ID = {1: "Level I (Normal)", 2: "Level II (Waspada)", 3: "Level III (Siaga)", 4: "Level IV (Awas)"}
STATUS_EN = {1: "Level I (Normal)", 2: "Level II (Advisory)", 3: "Level III (Watch)", 4: "Level IV (Warning)"}

_PRONOUN_ID = r"(saya|aku|gue|gw|sy|ku)"
_WHERE_KW = r"(di ?mana|dimana|dmna|dmana|dimn|dmn)"

_WHERE_ID = [
    rf"\b{_WHERE_KW}\b.*\b(posisi|lokasi|koordinat|berada|tempat)?\s*{_PRONOUN_ID}\b",
    rf"\b{_WHERE_KW}\b.*\b(saya|aku|gue|gw|sy|ku)\b",
    rf"\b{_PRONOUN_ID}\b.*\b{_WHERE_KW}\b",
    rf"\b(lokasi|posisi|koordinat)\s+{_PRONOUN_ID}\b(?!.*\b(aman|bahaya|berbahaya)\b)",
    rf"\b(lokasi|posisi|koordinat)\s+(saat ini|sekarang|ini)\b",
    rf"\b{_WHERE_KW}\s+(lokasi|posisi|saya|saat ini)\b",
    r"\b(lokasiku|posisiku)\b",
]
_NEAREST_ID = [
    r"\b(gunung ?api|gunungapi|gunung|gapi)\b.*\bterdekat\b",
    r"\bterdekat\b.*\b(gunung ?api|gunungapi|gunung|gapi)\b",
    rf"\b(gunung ?api|gunungapi|gunung)\b.*\bdekat\s+(dengan\s+|dari\s+)?({_PRONOUN_ID}|sini|lokasi\s+{_PRONOUN_ID})\b",
]
_SAFETY_ID = [
    rf"\b(daerah|wilayah|lokasi|tempat|area|rumah|posisi)\s+{_PRONOUN_ID}\b.*\b(aman|bahaya|berbahaya)\b",
    rf"\b(aman|bahaya|berbahaya)\b.*\b(daerah|wilayah|lokasi|tempat|area|rumah|posisi)\s+{_PRONOUN_ID}\b",
    r"\b(di\s+sini|disini)\b.*\b(aman|bahaya|berbahaya)\b",
    r"\b(aman|bahaya|berbahaya)\b.*\b(di\s+sini|disini)\b",
]

_WHERE_EN = [
    r"\bwhere\s+am\s+i\b",
    r"\bwhere\s+is\s+my\s+location\b",
    r"\bmy\s+(current\s+)?(location|position|coordinates)\b(?!.*\b(safe|danger)\b)",
]
_NEAREST_EN = [r"\b(nearest|closest)\b.*\bvolcano", r"\bvolcano(es)?\b.*\b(near|close to)\s+(me|here|my location)\b"]
_SAFETY_EN = [
    r"\b(is|am)\b.*\b(my (area|location|region|place|home)|here|i)\b.*\bsafe\b",
    r"\bsafe\b.*\b(my (area|location|region)|here)\b",
]


def detect_location_question(text: str, lang: str = "id") -> Optional[str]:
    """Return 'safety', 'nearest', 'where' or None.

    Supports both Indonesian (including colloquial/shortened terms like dmna, sy)
    and English cross-lingually so questions in either language are reliably caught.
    """
    t = (text or "").lower().strip()
    if not t:
        return None

    primary_groups = (
        (("safety", _SAFETY_EN), ("nearest", _NEAREST_EN), ("where", _WHERE_EN))
        if lang == "en"
        else (("safety", _SAFETY_ID), ("nearest", _NEAREST_ID), ("where", _WHERE_ID))
    )
    for mode, patterns in primary_groups:
        if any(re.search(p, t) for p in patterns):
            return mode

    # Fallback to alternative language in case user typed Indonesian while in EN mode or vice versa
    secondary_groups = (
        (("safety", _SAFETY_ID), ("nearest", _NEAREST_ID), ("where", _WHERE_ID))
        if lang == "en"
        else (("safety", _SAFETY_EN), ("nearest", _NEAREST_EN), ("where", _WHERE_EN))
    )
    for mode, patterns in secondary_groups:
        if any(re.search(p, t) for p in patterns):
            return mode

    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_volcanoes(lat: float, lon: float, volcano_list: Iterable[dict], k: int = 3) -> list[tuple[dict, float]]:
    ranked = []
    for volcano in volcano_list or []:
        try:
            vlat = float(volcano.get("ga_lat_gapi"))
            vlon = float(volcano.get("ga_lon_gapi"))
        except (TypeError, ValueError):
            continue
        ranked.append((volcano, haversine_km(lat, lon, vlat, vlon)))
    ranked.sort(key=lambda item: item[1])
    return ranked[:k]


def _fmt_km(distance: float, lang: str) -> str:
    value = f"{distance:.1f}"
    return value.replace(".", ",") if lang == "id" else value


def _short_place(location_name: Optional[str]) -> Optional[str]:
    """Nominatim display names are long; keep the first three parts."""
    if not location_name:
        return None
    parts = [p.strip() for p in str(location_name).split(",") if p.strip()]
    # Drop postcode and country noise.
    parts = [p for p in parts if not re.fullmatch(r"\d{5}", p) and p.lower() not in {"indonesia"}]
    return ", ".join(parts[:3]) if parts else None


def _status(volcano: dict) -> Optional[int]:
    try:
        return int(volcano.get("ga_status"))
    except (TypeError, ValueError):
        return None


def build_location_answer(
    mode: str,
    lat: float,
    lon: float,
    volcano_list: list[dict],
    location_name: Optional[str] = None,
    accuracy_m: Optional[float] = None,
    lang: str = "id",
    target_volcano_name: Optional[str] = None,
) -> tuple[str, list[dict]]:
    """Build the answer text and the structured nearest list for the UI."""
    ranked = nearest_volcanoes(lat, lon, volcano_list, k=3)
    labels = STATUS_EN if lang == "en" else STATUS_ID
    place = _short_place(location_name)
    coords = f"{lat:.5f}, {lon:.5f}"
    lines: list[str] = []

    if lang == "en":
        lines.append(f"Your location: {place} ({coords})." if place else f"Your coordinates: {coords}.")
    else:
        lines.append(f"Lokasi Anda: {place} ({coords})." if place else f"Koordinat Anda: {coords}.")

    if not ranked:
        lines.append(
            "Volcano data is not available right now, so the nearest volcano cannot be calculated."
            if lang == "en"
            else "Data gunung api sedang tidak tersedia, sehingga gunung terdekat belum dapat dihitung."
        )
        return "\n".join(lines), []

    nearest, distance = ranked[0]
    name = nearest.get("ga_nama_gapi") or nearest.get("ga_code")
    level = _status(nearest)
    level_text = labels.get(level, f"Level {level}") if level else None

    if lang == "en":
        sentence = f"The nearest volcano is Mount {name}, about {_fmt_km(distance, lang)} km away"
        sentence += f", currently at {level_text}." if level_text else "."
    else:
        sentence = f"Gunung api terdekat adalah Gunung {name}, berjarak sekitar {_fmt_km(distance, lang)} km"
        sentence += f" dengan status {level_text}." if level_text else "."
    lines.append(sentence)

    others = ranked[1:]
    if others and mode in {"nearest", "safety"}:
        if lang == "en":
            lines.append("Other nearby volcanoes:")
        else:
            lines.append("Gunung api terdekat lainnya:")
        for idx, (volcano, dist) in enumerate(others, 2):
            lvl = _status(volcano)
            lvl_text = labels.get(lvl, "") if lvl else ""
            suffix = f" — {lvl_text}" if lvl_text else ""
            lines.append(f"{idx}. {volcano.get('ga_nama_gapi')} ({_fmt_km(dist, lang)} km){suffix}")

    # Specific volcano safety check if target volcano is provided
    target_volcano_obj = None
    if target_volcano_name and volcano_list:
        clean_target = re.sub(r"\b(gunung|gn|g|mount|mt)\.?\b", "", target_volcano_name, flags=re.IGNORECASE).strip().lower()
        for v in volcano_list:
            v_n = re.sub(r"\b(gunung|gn|g|mount|mt)\.?\b", "", v.get("ga_nama_gapi", ""), flags=re.IGNORECASE).strip().lower()
            if clean_target and (clean_target in v_n or v_n in clean_target):
                target_volcano_obj = v
                break

    if target_volcano_obj:
        try:
            t_lat = float(target_volcano_obj.get("ga_lat_gapi"))
            t_lon = float(target_volcano_obj.get("ga_lon_gapi"))
            t_dist = haversine_km(lat, lon, t_lat, t_lon)
            t_name = target_volcano_obj.get("ga_nama_gapi")
            t_lvl = _status(target_volcano_obj)
            t_lvl_text = labels.get(t_lvl, f"Level {t_lvl}")
            t_dist_str = _fmt_km(t_dist, lang)

            if lang == "en":
                if t_dist > 50:
                    lines.append(
                        f"\nRegarding Mount {t_name}: your current location is approximately {t_dist_str} km away "
                        f"(Status: {t_lvl_text}). Given the distance well outside the PVMBG hazard radius, "
                        f"your position is currently safe from the direct volcanic activity of Mount {t_name}."
                    )
                else:
                    lines.append(
                        f"\nRegarding Mount {t_name}: your location is approximately {t_dist_str} km away "
                        f"(Status: {t_lvl_text}). Please adhere to the official PVMBG hazard radius guidelines."
                    )
            else:
                if t_dist > 50:
                    lines.append(
                        f"\nTerkait Gunung {t_name}: jarak posisi Anda saat ini ke Gunung {t_name} adalah sekitar {t_dist_str} km "
                        f"(Status: {t_lvl_text}). Berada jauh di luar radius bahaya yang ditetapkan PVMBG, sehingga posisi Anda "
                        f"saat ini aman dari ancaman langsung aktivitas Gunung {t_name}."
                    )
                else:
                    lines.append(
                        f"\nTerkait Gunung {t_name}: jarak posisi Anda ke Gunung {t_name} adalah sekitar {t_dist_str} km "
                        f"(Status: {t_lvl_text}). Perhatikan rekomendasi resmi PVMBG mengenai radius kawah aktif."
                    )
        except Exception as e:
            print(f"Error computing target volcano distance: {e}")

    if mode == "safety":
        elevated = [
            (volcano, dist) for volcano, dist in nearest_volcanoes(lat, lon, volcano_list, k=10)
            if dist <= NEARBY_ALERT_RADIUS_KM and (_status(volcano) or 0) >= 2
        ]
        if elevated:
            names = ", ".join(
                f"{v.get('ga_nama_gapi')} ({labels.get(_status(v), '')}, {_fmt_km(d, lang)} km)" for v, d in elevated
            )
            lines.append(
                f"Attention: volcanoes above Normal within {NEARBY_ALERT_RADIUS_KM} km: {names}. "
                "Follow the official PVMBG recommendation for the danger radius/sector and local authority instructions."
                if lang == "en"
                else f"Perhatian: dalam radius {NEARBY_ALERT_RADIUS_KM} km terdapat gunung api berstatus di atas Normal: {names}. "
                "Patuhi radius/sektor bahaya dalam rekomendasi resmi PVMBG dan arahan pemerintah daerah."
            )
        else:
            lines.append(
                f"No volcano above Normal level was found within {NEARBY_ALERT_RADIUS_KM} km of your position. "
                "This only covers volcanic activity; keep monitoring official PVMBG and BMKG updates."
                if lang == "en"
                else f"Tidak ada gunung api berstatus di atas Normal dalam radius {NEARBY_ALERT_RADIUS_KM} km dari posisi Anda. "
                "Penilaian ini hanya untuk aktivitas gunung api; tetap pantau informasi resmi PVMBG dan BMKG."
            )

    if accuracy_m and accuracy_m > COARSE_ACCURACY_M:
        approx = _fmt_km(accuracy_m / 1000, lang)
        lines.append(
            f"Note: your device location is approximate (±{approx} km). Enable GPS/precise location for a more accurate result."
            if lang == "en"
            else f"Catatan: lokasi perangkat Anda masih perkiraan (±{approx} km). Aktifkan GPS/lokasi akurat agar hasil lebih tepat."
        )

    nearest_payload = [
        {
            "name": volcano.get("ga_nama_gapi"),
            "code": volcano.get("ga_code"),
            "status": _status(volcano),
            "distance_km": round(dist, 2),
            "province": volcano.get("ga_prov_gapi"),
        }
        for volcano, dist in ranked
    ]
    return "\n".join(lines), nearest_payload


def missing_location_answer(lang: str = "id") -> str:
    if lang == "en":
        return (
            "I have not received your location yet. Allow location access in the browser (the Location switch must be on), "
            "or mention a place name, for example: \"What is the nearest volcano to Bandung?\""
        )
    return (
        "Saya belum menerima lokasi Anda. Aktifkan izin lokasi di browser (sakelar Lokasi harus menyala), "
        "atau sebutkan nama daerah, misalnya: \"Gunung api terdekat dari Bandung?\""
    )
