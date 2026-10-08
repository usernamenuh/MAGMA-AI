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
