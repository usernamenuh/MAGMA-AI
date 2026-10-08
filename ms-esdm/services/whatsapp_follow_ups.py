"""Grounded, non-repeating follow-up questions for the WhatsApp channel."""

import asyncio
import json
import re
from difflib import SequenceMatcher

from mistralai.models.chat_completion import ChatMessage

from utils.pipeline_helpers import VOLCANO_COMMON_ALIASES, load_volcano_cache, model_chat


def _normalized(value: str) -> str:
    return " ".join(re.findall(r"[\w]+", (value or "").casefold()))


def _repeats(question: str, previous: list[str]) -> bool:
    current = _normalized(question)
    if not current:
        return True
    for item in previous:
        old = _normalized(item)
        if not old:
            continue
        if current == old or SequenceMatcher(None, current, old).ratio() >= 0.78:
            return True
        current_words, old_words = set(current.split()), set(old.split())
        if len(current_words & old_words) >= 4 and len(current_words & old_words) / min(len(current_words), len(old_words)) >= 0.8:
            return True
    return False


def _known_volcano_from_question(question: str) -> str | None:
    """Accept only an explicit volcano name, never a province or generic phrase."""
    cached_names = {}
    for volcano in load_volcano_cache() or []:
        if not isinstance(volcano, dict):
            continue
        name = str(volcano.get("ga_nama_gapi") or volcano.get("name") or "").strip()
        if name:
            cached_names[_normalized(re.sub(r"^gunung\s+", "", name, flags=re.I))] = name

    for match in re.finditer(r"\b(?:gunung(?:\s+api)?|mount)\s+([^?.!,;]+)", question, re.I):
        words = re.findall(r"[A-Za-z][A-Za-z\-]*", match.group(1))[:4]
        for length in range(len(words), 0, -1):
            name = " ".join(words[:length])
            normalized = _normalized(name)
            if normalized in cached_names:
                return re.sub(r"^gunung\s+", "", cached_names[normalized], flags=re.I)
            if normalized in VOLCANO_COMMON_ALIASES:
                return " ".join(word.capitalize() for word in words[:length])
    return None


def _api_candidates(question: str, answer: str) -> list[dict[str, str]]:
    text = f"{question} {answer}".casefold()
    answered_lower = (answer or "").casefold()
    asked_lower = (question or "").casefold()
    candidates = []

    regional_names = re.findall(r"(?m)^\d+\.\s+(.+?)\s+—\s+Level\s+[1-4]", answer)
    for regional_name in regional_names[:2]:
        candidates.append({
            "id": f"regional_status_{len(candidates)}",
            "question": f"Bagaimana status dan rekomendasi resmi untuk Gunung {regional_name} saat ini?",
        })

    answered_status = bool(
        re.search(r"\b(?:status\s+aktivitas\s+gunung|level\s+(?:i{1,3}|iv|[1-4])\b|tingkat\s+aktivitas)", answered_lower)
        or re.search(r"level\s+[1-4iv]+.*(?:normal|waspada|siaga|awas)", answered_lower)
    )
    answered_recommendation = bool(
        re.search(r"rekomendasi\s+(?:resmi\s+)?pvmbg", answered_lower)
        or re.search(r"(?:masyarakat|pengunjung|wisatawan)\s+(?:dan|agar|dihimbau|diimbau|tidak|dilarang)", answered_lower)
        or re.search(r"radius\s+(?:rekomendasi\s+)?bahaya", answered_lower)
    )
    answered_eruption = bool(
        re.search(r"erupsi\s+terakhir|letusan\s+terakhir|terakhir\s+(?:kali\s+)?(?:meletus|mengalami\s+erupsi)", answered_lower)
    )
    answered_status_meaning = bool(
        re.search(r"definisi/arti|tingkat\s+dasar\s+\(baseline\)", answered_lower)
        or (re.search(r"level\s+(?:i\b|1\b|normal)", answered_lower) and re.search(r"level\s+(?:ii\b|2\b|waspada)", answered_lower) and re.search(r"level\s+(?:iii\b|3\b|siaga)", answered_lower))
    )
    answered_active_list = bool(
        re.search(r"gunung\s+apa\s+saja\s+yang\s+berstatus\s+(?:waspada|siaga|awas)", answered_lower)
        or (re.search(r"daftar\s+gunung|gunung\s+api\s+.*yang\s+berstatus", answered_lower) and re.search(r"waspada|siaga|awas", answered_lower))
    )
    answered_quake_latest = bool(re.search(r"magnitudo|kedalaman|pusat\s+gempa|koordinat", answered_lower))
    answered_gm_latest = bool(re.search(r"laporan\s+kejadian|lokasi\s+kejadian|dampak\s+gerakan\s+tanah", answered_lower))

    name = _known_volcano_from_question(question)
    if not name:
        for match in re.finditer(r"\b(?:gunung(?:\s+api)?|mount)\s+([^?.!,;\n]+)", answer, re.I):
            words = re.findall(r"[A-Za-z][A-Za-z\-]*", match.group(1))[:4]
            for length in range(len(words), 0, -1):
                cname = " ".join(words[:length])
                norm = _normalized(cname)
                for volcano in load_volcano_cache() or []:
                    if not isinstance(volcano, dict):
                        continue
                    vname = str(volcano.get("ga_nama_gapi") or volcano.get("name") or "").strip()
                    if norm == _normalized(re.sub(r"^gunung\s+", "", vname, flags=re.I)):
                        name = re.sub(r"^gunung\s+", "", vname, flags=re.I)
                        break
                if name:
                    break
            if name:
                break

    if name:
        if not answered_eruption:
            candidates.append({
                "id": "volcano_eruption",
                "question": f"Kapan erupsi terakhir Gunung {name}?",
            })

        # Sibling volcanoes in the same province
        volcano_province = None
        prov_match = re.search(r"(?:Lokasi|Provinsi|Prov\.)\s*:\s*(?:[^,\n]+,\s*)?([A-Za-z\s]+)", answer)
        if prov_match:
            volcano_province = prov_match.group(1).strip()
        if not volcano_province:
            for v in load_volcano_cache() or []:
                if not isinstance(v, dict):
                    continue
                vname = str(v.get("ga_nama_gapi") or v.get("name") or "").strip()
                if _normalized(re.sub(r"^gunung\s+", "", vname, flags=re.I)) == _normalized(name):
                    raw_prov = str(v.get("ga_prov_gapi") or "").strip()
                    if raw_prov:
                        volcano_province = raw_prov.split(",")[0].strip()
                    break
        if volcano_province and len(volcano_province) >= 4 and not re.search(rf"\b{re.escape(volcano_province.casefold())}\b", asked_lower):
            short_prov = re.sub(r"(?i)\s*(?:dan|,).*$", "", volcano_province).strip()
            candidates.append({
                "id": "regional_siblings",
                "question": f"Gunung api aktif apa lagi yang berada di {short_prov}?",
            })

        candidates.append({
            "id": "volcano_hazard",
            "question": f"Bagaimana potensi bahaya atau karakteristik letusan Gunung {name}?",
        })

        if not answered_recommendation and not re.search(r"rekomendasi|imbauan|radius", asked_lower):
            candidates.append({
                "id": "volcano_recommendation",
                "question": f"Apa rekomendasi resmi PVMBG untuk Gunung {name}?",
            })
        if not answered_status and not re.search(r"status|kondisi|bagaimana|periksa", asked_lower):
            candidates.append({
                "id": "volcano_status",
                "question": f"Bagaimana status aktivitas Gunung {name} saat ini?",
            })

    if re.search(r"\bgempa|gempabumi|earthquake\b", text):
        if not answered_quake_latest and not re.search(r"terbaru|terkini|terakhir", asked_lower):
            candidates.append({"id": "earthquake_latest", "question": "Apa rincian gempa bumi terbaru?"})
        candidates.append({"id": "earthquake_list", "question": "Apa saja kejadian gempa bumi terkini lainnya?"})
        candidates.append({"id": "earthquake_mitigation", "question": "Bagaimana panduan mitigasi saat terjadi gempa bumi?"})

    if re.search(r"longsor|gerakan tanah", text):
        if not answered_gm_latest and not re.search(r"terbaru|terkini|terakhir", asked_lower):
            candidates.append({"id": "ground_movement_latest", "question": "Apa laporan gerakan tanah terbaru?"})
        candidates.append({"id": "ground_movement_mitigation", "question": "Bagaimana panduan mitigasi gerakan tanah?"})

    if re.search(r"gunung|vulkan|erupsi|status|siaga|waspada|awas", text):
        if not answered_active_list and not re.search(r"daftar|berapa|apa saja|mana saja", asked_lower):
            candidates.append({"id": "volcano_active_list", "question": "Gunung apa saja yang berstatus Waspada, Siaga, atau Awas saat ini?"})
        if not answered_status_meaning and not re.search(r"arti|makna|maksud|definisi|tingkat", asked_lower):
            candidates.append({"id": "volcano_status_levels", "question": "Apa arti tiap tingkat status aktivitas gunung api?"})

    asked_status_meaning = bool(
        re.search(r"arti|makna|maksud|tingkat|level|definisi", asked_lower)
        and re.search(r"status|aktivitas|normal|waspada|siaga|awas", asked_lower)
    )
    asked_active_list = bool(
        re.search(r"berapa|daftar|apa saja|mana saja|jumlah", asked_lower)
        and re.search(r"gunung|status|siaga|waspada|awas", asked_lower)
    )
    asked_latest_quake = bool(re.search(r"gempa", asked_lower) and re.search(r"terbaru|terkini|terakhir", asked_lower))
    asked_quake_mitigation = bool(re.search(r"gempa", asked_lower) and re.search(r"mitigasi|panduan|keselamatan", asked_lower))
    asked_eruption = bool(re.search(r"erupsi|letusan", asked_lower) and re.search(r"kapan|terakhir|sejarah", asked_lower))

    excluded = set()
    if asked_status_meaning or answered_status_meaning:
        excluded.add("volcano_status_levels")
    if asked_active_list or answered_active_list:
        excluded.add("volcano_active_list")
    if asked_latest_quake or answered_quake_latest:
        excluded.add("earthquake_latest")
    if asked_quake_mitigation:
        excluded.add("earthquake_mitigation")
    if asked_eruption or answered_eruption:
        excluded.add("volcano_eruption")
    if answered_status:
        excluded.add("volcano_status")
    if answered_recommendation:
        excluded.add("volcano_recommendation")

    return [item for item in {item["id"]: item for item in candidates}.values()
            if item["id"] not in excluded]


def _parse_json(raw: str) -> dict:
    if not raw:
        return {}
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        data = json.loads(raw[start:end + 1])
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def format_nara_follow_up(question: str) -> str:
    """Phrase the executable question as a natural offer from NARA."""
    phrase = question.strip().rstrip("?. ")
    document = re.match(r"^Dalam dokumen (.+?),\s*(.+)$", phrase, re.I)
    if document:
        phrase = f"{document.group(2)} menurut dokumen {document.group(1)}"
    if phrase.casefold().startswith("apa ") and not phrase.casefold().startswith("apa saja "):
        phrase = phrase[4:]
    phrase = phrase[0].lower() + phrase[1:]
    return (
        f"💬 Apakah Anda ingin tahu {phrase}? NARA bisa bantu mencari jawabannya.\n"
        "Balas ya jika ingin NARA lanjutkan."
    )


class DynamicFollowUpGenerator:
    """Ask the LLM after the answer, then validate against the active channel."""

    @staticmethod
    async def generate(
        *, mode: str, question: str, answer: str, references: list[dict],
        previous: list[str], model: str | None,
    ) -> str | None:
        clean_answer = (answer or "").strip()
        if not clean_answer or re.search(
            r"(?i)tidak ditemukan|periksa kembali ejaan|belum tersedia|tidak ada data|"
            r"terjadi kesalahan|tidak dapat ditemukan", clean_answer,
        ):
            return None
        if re.search(r"(?i)\b(jawa|sumatera|sulawesi|kalimantan|papua|maluku|lampung)\b", question) \
                and re.search(r"(?i)seluruh gunung api di indonesia", clean_answer[:250]):
            return None

        if mode == "api":
            candidates = [item for item in _api_candidates(question, clean_answer)
                          if not _repeats(item["question"], previous + [question])]
            if not candidates:
                return None
            prompt = (
                "Pilih SATU pertanyaan lanjutan paling relevan setelah jawaban MAGMA. "
                "Pilih hanya id dari daftar, jangan membuat pertanyaan baru. "
                "PENTING: Jangan pilih pertanyaan yang topiknya sudah dijawab pada teks jawaban di atas! "
                "Balas JSON {\"id\":\"...\"}.\n"
                f"Pertanyaan: {question[:400]}\nJawaban: {clean_answer[:1400]}\n"
                f"Pilihan: {json.dumps(candidates, ensure_ascii=False)}"
            )
            fallback = candidates[0]["question"]
        else:
            filenames = [str(ref.get("filename", "")).strip() for ref in references if isinstance(ref, dict)]
            if not filenames:
                return None
            filename = filenames[0]
            prompt = (
                "Buat 2 pertanyaan lanjutan yang SPESIFIK tentang isi dokumen setelah jawaban berikut. "
                "Pertanyaan harus bisa dijawab dengan mencari dokumen yang sama, menanyakan rincian yang belum "
                "dijelaskan, dan menyebut fakta atau istilah yang ada pada jawaban. "
                "Jangan mengulang pertanyaan sebelumnya, jangan menawarkan ringkasan umum, dan jangan mengarang fakta. "
                "Balas JSON {\"questions\":[\"...?\",\"...?\"]}.\n"
                f"Dokumen: {filename[:100]}\nPertanyaan: {question[:400]}\n"
                f"Jawaban: {clean_answer[:1700]}\n"
                f"Pernah ditanyakan/ditawarkan: {json.dumps(previous[-8:], ensure_ascii=False)}"
            )
            fallback = None

        messages = [
            ChatMessage(role="system", content="Anda membantu NARA menyusun pertanyaan lanjutan yang relevan. Keluarkan JSON saja."),
            ChatMessage(role="user", content=prompt),
        ]
        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(model_chat, messages, model=model, temperature=0.1, max_tokens=180, max_retries=1),
                timeout=25,
            )
        except Exception:
            raw = None
        data = _parse_json(raw)

        if mode == "api":
            selected = next((item["question"] for item in candidates if item["id"] == data.get("id")), None)
            return selected or fallback

        answer_words = set(_normalized(clean_answer).split()) - {
            "dalam", "adalah", "yang", "dengan", "untuk", "pada", "dari", "atau", "tentang", "dokumen",
        }
        for candidate in data.get("questions", []) if isinstance(data.get("questions"), list) else []:
            if not isinstance(candidate, str):
                continue
            candidate = candidate.strip().strip('"')
            words = set(_normalized(candidate).split())
            if not 18 <= len(candidate) <= 180 or not candidate.endswith("?"):
                continue
            if len(words & answer_words) < 2 or _repeats(candidate, previous + [question]):
                continue
            if re.search(r"(?i)ringkas|rangkum|apa isi dokumen|pertanyaan lanjutan", candidate):
                continue
            if filename.casefold() not in candidate.casefold():
                candidate = f"Dalam dokumen {filename}, {candidate[0].lower() + candidate[1:]}"
            return candidate

        # A source-check question remains answerable when the model cannot produce a safe proposal.
        source_question = f"Bagian mana dalam dokumen {filename} yang menjadi dasar jawaban tentang {question.rstrip('?')}?"
        return source_question if len(source_question) <= 180 and not _repeats(source_question, previous + [question]) else None
