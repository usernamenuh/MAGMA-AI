"""Province-scoped volcano lists for WhatsApp, backed by the PVMBG list API."""

import asyncio
import re

from utils.pipeline_helpers import get_mount_code


STATUS_NAMES = {1: "Normal", 2: "Waspada", 3: "Siaga", 4: "Awas"}


def _provinces(item: dict) -> list[str]:
    location = str(item.get("ga_prov_gapi") or "")
    return [part.strip() for part in re.split(r",\s*|\s+dan\s+", location, flags=re.I) if part.strip()]


def requested_province(question: str, volcanoes: list[dict]) -> str | None:
    if not re.search(r"(?i)\b(?:gunung(?:\s+api)?|vulkan|volcano)\b", question):
        return None
    provinces = {province for item in volcanoes if isinstance(item, dict)
                 for province in _provinces(item)}
    for province in sorted(provinces - {""}, key=len, reverse=True):
        if re.search(rf"(?i)(?<!\w){re.escape(province)}(?!\w)", question):
            return province
    return None


def regional_volcano_answer(question: str, volcanoes: list[dict]) -> tuple[str, list[dict]] | None:
    province = requested_province(question, volcanoes)
    if not province:
        return None
    # A named volcano is a different intent; leave its status to the normal API route.
    names = [str(item.get("ga_nama_gapi") or "").strip() for item in volcanoes]
    if any(name and re.search(rf"(?i)(?<!\w){re.escape(name)}(?!\w)", question)
           for name in names):
        return None
    matches = [item for item in volcanoes
               if province.casefold() in {part.casefold() for part in _provinces(item)}]
    if not matches:
        return None
    lower = question.casefold()
    level = next((code for word, code in (("awas", 4), ("siaga", 3), ("waspada", 2), ("normal", 1))
                  if re.search(rf"\b{word}\b", lower)), None)
    elevated = level is None and bool(re.search(r"\baktif\b|di atas normal|meningkat", lower))
    selected = [item for item in matches if item.get("ga_status") == level] if level else (
        [item for item in matches if item.get("ga_status") in (2, 3, 4)] if elevated else matches
    )
    selected.sort(key=lambda item: (-int(item.get("ga_status") or 0), str(item.get("ga_nama_gapi") or "")))
    criterion = f"berstatus {STATUS_NAMES[level]}" if level else (
        "berstatus di atas Normal" if elevated else "yang terpantau"
    )
    if not selected:
        answer = (f"Menurut daftar PVMBG yang tersedia, tidak ada gunung api di {province} "
                  f"{criterion}. Terdapat {len(matches)} gunung api terpantau di provinsi ini.")
        examples = sorted(matches, key=lambda item: str(item.get("ga_nama_gapi") or ""))[:3]
        answer += "\nContoh gunung yang terpantau:\n" + "\n".join(
            f"{index}. {item.get('ga_nama_gapi')} — Level {item.get('ga_status')} "
            f"({STATUS_NAMES.get(item.get('ga_status'), 'Belum diketahui')})"
            for index, item in enumerate(examples, 1)
        )
    else:
        lines = [f"Gunung api di {province} {criterion} menurut daftar PVMBG yang tersedia "
                 f"({len(selected)} gunung):"]
        for index, item in enumerate(selected, 1):
            status = STATUS_NAMES.get(item.get("ga_status"), "Belum diketahui")
            lines.append(f"{index}. {item.get('ga_nama_gapi')} — Level {item.get('ga_status')} ({status})")
        answer = "\n".join(lines)
    return answer, selected or matches


async def answer_regional_volcano_query(question: str) -> tuple[str, list[dict]] | None:
    volcanoes = await asyncio.to_thread(get_mount_code)
    return regional_volcano_answer(question, volcanoes or [])


def ranked_volcano_answer(question: str, volcanoes: list[dict]) -> tuple[str, list[dict]] | None:
    """Show highest alert levels without presenting them as an eruption-frequency ranking."""
    if not re.search(r"(?i)\bgunung(?:\s+api)?\b", question) or not re.search(
        r"(?i)\btop\s*\d+\b|paling\s+aktif|teraktif", question
    ):
        return None
    requested = re.search(r"(?i)\btop\s*(\d+)\b", question)
    count = min(max(int(requested.group(1)), 1), 10) if requested else 3
    eligible = [item for item in volcanoes if isinstance(item, dict)
                and item.get("ga_nama_gapi") and item.get("ga_status") in (2, 3, 4)]
    eligible.sort(key=lambda item: (-item["ga_status"], item["ga_nama_gapi"].casefold()))
    chosen = eligible[:count]
    if not chosen:
        return ("Daftar PVMBG yang tersedia belum menunjukkan gunung api berstatus di atas Normal. "
                "Status aktivitas tidak sama dengan jumlah kejadian erupsi.", [])
    lines = [
        "Daftar status PVMBG yang digunakan NARA tidak memuat peringkat gunung api ‘paling aktif’. "
        f"Jika yang dimaksud tingkat kewaspadaan tertinggi, berikut {len(chosen)} contoh dari data "
        "yang tersedia (status sama diurutkan menurut nama, bukan frekuensi erupsi):"
    ]
    for index, item in enumerate(chosen, 1):
        lines.append(
            f"{index}. {item['ga_nama_gapi']} — Level {item['ga_status']} "
            f"({STATUS_NAMES[item['ga_status']]})"
        )
    return "\n".join(lines), chosen


async def answer_ranked_volcano_query(question: str) -> tuple[str, list[dict]] | None:
    if not re.search(r"(?i)\btop\s*\d+\b|paling\s+aktif|teraktif", question):
        return None
    volcanoes = await asyncio.to_thread(get_mount_code)
    return ranked_volcano_answer(question, volcanoes or [])


def named_volcano_answer(question: str, volcanoes: list[dict]) -> tuple[str, list[dict]] | None:
    """Resolve a short volcano-name reply exactly, without fuzzy matching 'Iyaa' to Iya."""
    match = re.fullmatch(r"(?i)(?:gunung|gn\.?)\s+([\w\s-]+?)(?:\s+(?:sekarang|saat\s+ini))?[?.!]*", question.strip())
    if not match:
        return None
    requested = " ".join(match.group(1).casefold().split())
    volcano = next((item for item in volcanoes if isinstance(item, dict)
                    and str(item.get("ga_nama_gapi") or "").casefold() == requested), None)
    if not volcano or volcano.get("ga_status") not in STATUS_NAMES:
        return None
    name = volcano["ga_nama_gapi"]
    level = volcano["ga_status"]
    location = ", ".join(filter(None, [volcano.get("ga_kab_gapi"), volcano.get("ga_prov_gapi")]))
    answer = f"Status Gunung {name} menurut daftar PVMBG yang tersedia: Level {level} ({STATUS_NAMES[level]})."
    if location:
        answer += f" Lokasi: {location}."
    return answer, [volcano]


async def answer_named_volcano_query(question: str) -> tuple[str, list[dict]] | None:
    if not re.match(r"(?i)^\s*(?:gunung|gn\.?)\s+", question):
        return None
    volcanoes = await asyncio.to_thread(get_mount_code)
    return named_volcano_answer(question, volcanoes or [])
