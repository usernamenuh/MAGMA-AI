"""Grounded, non-repeating follow-up questions for the WhatsApp channel."""

import asyncio
import json
import re
from difflib import SequenceMatcher

from mistralai.models.chat_completion import ChatMessage

from utils.pipeline_helpers import model_chat


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


def _api_candidates(question: str, answer: str) -> list[dict[str, str]]:
    text = f"{question} {answer}".casefold()
    candidates = []
    volcano = re.search(r"\b(?:gunung(?:\s+api)?|mount)\s+([A-Za-z][A-Za-z\-]*(?:\s+[A-Za-z][A-Za-z\-]*)?)", question, re.I)
    if volcano and volcano.group(1).split()[0].casefold() not in {
        "api", "berapi", "aktif", "yang", "status", "ini", "terdekat",
    }:
        name = volcano.group(1).strip()
        candidates.extend([
            {"id": "volcano_recommendation", "question": f"Apa rekomendasi resmi PVMBG untuk Gunung {name}?"},
            {"id": "volcano_status", "question": f"Bagaimana status aktivitas Gunung {name} saat ini?"},
            {"id": "volcano_eruption", "question": f"Kapan erupsi terakhir Gunung {name}?"},
        ])
    if re.search(r"\bgempa|gempabumi|earthquake\b", text):
        candidates.extend([
            {"id": "earthquake_latest", "question": "Apa rincian gempa bumi terbaru?"},
            {"id": "earthquake_list", "question": "Apa saja kejadian gempa bumi terkini lainnya?"},
            {"id": "earthquake_mitigation", "question": "Bagaimana panduan mitigasi saat terjadi gempa bumi?"},
        ])
    if re.search(r"longsor|gerakan tanah", text):
        candidates.extend([
            {"id": "ground_movement_latest", "question": "Apa laporan gerakan tanah terbaru?"},
            {"id": "ground_movement_mitigation", "question": "Bagaimana panduan mitigasi gerakan tanah?"},
        ])
    if re.search(r"gunung|vulkan|erupsi|status|siaga|waspada|awas", text):
        candidates.extend([
            {"id": "volcano_active_list", "question": "Gunung apa saja yang berstatus Waspada, Siaga, atau Awas saat ini?"},
            {"id": "volcano_status_levels", "question": "Apa arti tiap tingkat status aktivitas gunung api?"},
        ])
    asked = question.casefold()
    asked_status_meaning = bool(
        re.search(r"arti|makna|maksud|tingkat|level|definisi", asked)
        and re.search(r"status|aktivitas|normal|waspada|siaga|awas", asked)
    )
    asked_active_list = bool(
        re.search(r"berapa|daftar|apa saja|mana saja|jumlah", asked)
        and re.search(r"gunung|status|siaga|waspada|awas", asked)
    )
    asked_latest_quake = bool(re.search(r"gempa", asked) and re.search(r"terbaru|terkini|terakhir", asked))
    asked_quake_mitigation = bool(re.search(r"gempa", asked) and re.search(r"mitigasi|panduan|keselamatan", asked))
    excluded = set()
    if asked_status_meaning:
        excluded.add("volcano_status_levels")
    if asked_active_list:
        excluded.add("volcano_active_list")
    if asked_latest_quake:
        excluded.add("earthquake_latest")
    if asked_quake_mitigation:
        excluded.add("earthquake_mitigation")
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


class DynamicFollowUpGenerator:
    """Ask the LLM after the answer, then validate against the active channel."""

    @staticmethod
    async def generate(
        *, mode: str, question: str, answer: str, references: list[dict],
        previous: list[str], model: str | None,
    ) -> str | None:
        clean_answer = (answer or "").strip()
        if len(clean_answer) < 35 or re.match(r"(?i)^(maaf|tidak ditemukan|tidak ada data|terjadi kesalahan)", clean_answer):
            return None

        if mode == "api":
            candidates = [item for item in _api_candidates(question, clean_answer)
                          if not _repeats(item["question"], previous + [question])]
            if not candidates:
                return None
            prompt = (
                "Pilih SATU pertanyaan lanjutan paling relevan setelah jawaban MAGMA. "
                "Pilih hanya id dari daftar, jangan membuat pertanyaan baru. "
                "Hindari topik yang sudah terjawab. Balas JSON {\"id\":\"...\"}.\n"
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
            ChatMessage(role="system", content="Anda menyusun pertanyaan lanjutan ESDM Assistant. Keluarkan JSON saja."),
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
