"""WhatsApp location sharing handler and nearest volcano hazard evaluator."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Tuple

from geopy.exc import GeocoderServiceError, GeocoderTimedOut

from utils.geo_location import PREDEFINED_INDONESIA_COORDINATES, geolocator
from utils.location_answers import haversine_km, nearest_volcanoes
from utils.pipeline_helpers import get_mount_code, get_volcano_var_data, load_volcano_cache

logger = logging.getLogger(__name__)

STATUS_NAMES = {
    1: "Level I Normal",
    2: "Level II Waspada",
    3: "Level III Siaga",
    4: "Level IV Awas",
}

DEFAULT_DANGER_RADIUS = {
    1: 1.0,
    2: 3.0,
    3: 5.0,
    4: 7.0,
}

_LOC_TAG_RE = re.compile(
    r"\[LOKASI:\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)(?:,\s*([^\]]+))?\]",
    re.IGNORECASE,
)
_GMAPS_RE = re.compile(
    r"(?:q=|@|loc:)(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_RAW_COORDS_RE = re.compile(
    r"(-?\d{1,2}(?:\.\d+)?)\s*,\s*(\d{2,3}(?:\.\d+)?)",
)


def parse_whatsapp_coordinates(
    user_input: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_name: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Extract coordinates and place name from explicit parameters or text body."""
    # 1. Explicit numeric parameters
    if latitude is not None and longitude is not None:
        try:
            lat = float(latitude)
            lon = float(longitude)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, location_name
        except (ValueError, TypeError):
            pass

    text = (user_input or "").strip()
    if not text:
        return None, None, None

    # 2. Tag format: [LOKASI: lat, lon, name]
    m_tag = _LOC_TAG_RE.search(text)
    if m_tag:
        try:
            lat = float(m_tag.group(1))
            lon = float(m_tag.group(2))
            tag_name = m_tag.group(3).strip() if m_tag.group(3) else None
            return lat, lon, tag_name or location_name
        except (ValueError, TypeError):
            pass

    # 3. Google Maps URL coordinates
    m_gmaps = _GMAPS_RE.search(text)
    if m_gmaps:
        try:
            lat = float(m_gmaps.group(1))
            lon = float(m_gmaps.group(2))
            return lat, lon, location_name
        except (ValueError, TypeError):
            pass

    # 4. Raw coordinate pair in text (e.g. "-8.125, 113.01")
    m_raw = _RAW_COORDS_RE.search(text)
    if m_raw:
        try:
            val1 = float(m_raw.group(1))
            val2 = float(m_raw.group(2))
            # Validate within Indonesia bounding box (-11.5 to 6.5 lat, 94 to 142 lon)
            if -11.5 <= val1 <= 6.5 and 94.0 <= val2 <= 142.0:
                return val1, val2, location_name
            # Swapped coordinates (lon, lat)
            if 94.0 <= val1 <= 142.0 and -11.5 <= val2 <= 6.5:
                return val2, val1, location_name
        except (ValueError, TypeError):
            pass

    return None, None, None


def reverse_geocode_locality(
    lat: float,
    lon: float,
    candidate_name: Optional[str] = None,
) -> str:
    """Resolve human-readable administrative locality (Kecamatan, Kabupaten)."""
    if candidate_name and candidate_name.strip():
        cleaned = candidate_name.strip()
        # If candidate already has administrative markers or comma, return as-is
        if any(marker in cleaned.lower() for marker in ["kec.", "kecamatan", "kab.", "kabupaten", "kota", "desa", ","]):
            return cleaned

    # Try reverse-geocoding with Nominatim
    try:
        loc = geolocator.reverse(f"{lat}, {lon}", timeout=3, language="id")
        if loc and getattr(loc, "raw", None):
            addr = loc.raw.get("address", {})
            subdistrict = (
                addr.get("subdistrict")
                or addr.get("municipality")
                or addr.get("district")
            )
            village = addr.get("village") or addr.get("hamlet")
            county = addr.get("county") or addr.get("city")
            state = addr.get("state")

            if subdistrict and county:
                return f"Kec. {subdistrict}, {county}"
            if village and county:
                return f"Desa {village}, {county}"
            if subdistrict and state:
                return f"Kec. {subdistrict}, {state}"
            if county and state:
                return f"{county}, {state}"

            parts = [p.strip() for p in (loc.address or "").split(",") if p.strip()]
            parts = [p for p in parts if not re.fullmatch(r"\d{5}", p) and p.lower() != "indonesia"]
            if parts:
                return ", ".join(parts[:2])
    except (GeocoderTimedOut, GeocoderServiceError, Exception) as exc:
        logger.warning("Reverse geocoding failed for (%s, %s): %s", lat, lon, exc)

    # Fallback to closest predefined Indonesian city/regency
    closest_city = None
    min_dist = 60.0  # within 60 km
    for city_name, (c_lat, c_lon) in PREDEFINED_INDONESIA_COORDINATES.items():
        dist = haversine_km(lat, lon, c_lat, c_lon)
        if dist < min_dist:
            min_dist = dist
            closest_city = city_name.title()

    if closest_city:
        return f"sekitar {closest_city}"

    return f"koordinat ({lat:.4f}, {lon:.4f})"


def get_volcano_danger_radius(volcano: dict) -> Tuple[float, str]:
    """Determine official danger radius from PVMBG VAR report or standard baseline."""
    level = int(volcano.get("ga_status") or 1)
    default_radius = DEFAULT_DANGER_RADIUS.get(level, 3.0)

    code = volcano.get("ga_code")
    if not code:
        return default_radius, f"{default_radius:.1f} km"

    try:
        var_data = get_volcano_var_data(code)
        if isinstance(var_data, dict):
            lap = var_data.get("laporan_terakhir") or {}
            rekomendasi = lap.get("rekomendasi") or ""
            if rekomendasi:
                # Look for radius pattern like "radius 5 Km" or "radius 3 km"
                match = re.search(r"radius\s+(\d+(?:[.,]\d+)?)\s*(?:km|kilo)", rekomendasi, re.IGNORECASE)
                if match:
                    parsed_r = float(match.group(1).replace(",", "."))
                    return parsed_r, f"{parsed_r:.1f} km"
    except Exception as exc:
        logger.debug("Failed fetching VAR recommendation for %s: %s", code, exc)

    return default_radius, f"{default_radius:.1f} km"


def format_whatsapp_location_response(
    lat: float,
    lon: float,
    locality: str,
    volcano_list: list[dict],
) -> Tuple[str, str, list[dict]]:
    """Construct clean WhatsApp response with zero asterisks and follow-up offer."""
    ranked = nearest_volcanoes(lat, lon, volcano_list, k=3)
    if not ranked:
        msg = (
            f"Berdasarkan koordinat Anda di {locality}:\n"
            "Data pemantauan gunung api saat ini sedang tidak dapat diakses. "
            "Silakan periksa kembali beberapa saat lagi."
        )
        return msg, "", []

    nearest, dist = ranked[0]
    name = nearest.get("ga_nama_gapi") or nearest.get("ga_code") or "Gunung Api"
    status_code = int(nearest.get("ga_status") or 1)
    status_str = STATUS_NAMES.get(status_code, f"Level {status_code}")
    dist_str = f"{dist:.1f}".replace(".", ",")

    danger_radius, _ = get_volcano_danger_radius(nearest)
    radius_fmt = f"{danger_radius:.1f}".replace(".", ",").rstrip("0").rstrip(",")

    if dist > danger_radius:
        safety_text = f"Jarak Anda aman dari radius rekomendasi bahaya {radius_fmt} km."
    else:
        safety_text = (
            f"PERINGATAN: Posisi Anda berada di DALAM radius rekomendasi bahaya ({radius_fmt} km) "
            f"dari kawah/puncak Gunung {name}. Harap berhati-hati dan patuhi arahan mitigasi PVMBG / BPBD setempat."
        )

    coords_str = f"{lat:.5f}, {lon:.5f}"
    maps_link = f"https://www.google.com/maps?q={lat:.5f},{lon:.5f}"

    lines = [
        f"Berdasarkan lokasi Anda di {locality}:",
        f"Titik Koordinat: {coords_str}",
        f"Link Peta: {maps_link}\n",
        f"Gunung api terdekat adalah Gunung {name} (berjarak {dist_str} km, Status {status_str}). {safety_text}",
    ]

    others = ranked[1:]
    if others:
        lines.append("\nGunung api terdekat lainnya:")
        for idx, (v, d) in enumerate(others, 2):
            v_name = v.get("ga_nama_gapi") or v.get("ga_code")
            v_status_code = int(v.get("ga_status") or 1)
            v_status_str = STATUS_NAMES.get(v_status_code, f"Level {v_status_code}")
            v_dist_str = f"{d:.1f}".replace(".", ",")
            lines.append(f"{idx}. Gunung {v_name} (berjarak {v_dist_str} km, Status {v_status_str})")

    follow_up_prompt = f"Rekomendasi resmi PVMBG Gunung {name}"
    lines.append(
        f"\n💬 Apakah Anda ingin tahu rekomendasi resmi PVMBG untuk Gunung {name}? NARA bisa bantu mencari jawabannya.\n"
        "Balas ya jika ingin NARA lanjutkan."
    )

    full_output = "\n".join(lines)
    return full_output, follow_up_prompt, [item[0] for item in ranked]


def handle_whatsapp_location_query(
    lat: float,
    lon: float,
    candidate_name: Optional[str] = None,
) -> Tuple[str, str, list[dict]]:
    """Entrypoint to handle location query, resolve locality, and format response."""
    locality = reverse_geocode_locality(lat, lon, candidate_name)
    volcano_list = get_mount_code() or load_volcano_cache() or []
    return format_whatsapp_location_response(lat, lon, locality, volcano_list)
