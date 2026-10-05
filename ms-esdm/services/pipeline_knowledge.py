import json
import os
import re
from datetime import datetime
from utils.query_normalizer import normalize_indonesian_query

from mistralai.models.chat_completion import ChatMessage
from services.knowledge_documents_service import KnowledgeDocumentsService
from utils.pipeline_helpers import model_chat
service = KnowledgeDocumentsService()

NARA_INTRODUCTION = (
    "Halo, saya NARA ESDM, asisten virtual untuk membantu mencari informasi "
    "berdasarkan dokumen yang tersedia. Silakan sebutkan nama, judul, atau "
    "topik yang ingin ditanyakan."
)

NARA_CLARIFICATION = (
    "Saya NARA ESDM. Pesan Anda belum cukup jelas; mohon sebutkan nama, judul, "
    "atau topik dokumen yang ingin ditanyakan."
)


def get_nara_response(user_input: str, has_history: bool = False) -> str | None:
    """Only introduce NARA for greetings or genuinely context-free messages."""
    normalized = re.sub(r"[^a-z0-9]+", " ", (user_input or "").lower()).strip()
    greetings = {
        "halo", "hallo", "hai", "hi", "hy", "hey", "hello", "p", "permisi",
        "assalamualaikum", "assalamualaikum wr wb", "selamat pagi",
        "selamat siang", "selamat sore", "selamat malam",
    }
    vague_messages = {
        "", "bantu", "bantu saya", "mau tanya", "mohon bantu", "tolong",
        "tolong jelaskan", "jelaskan", "info", "info dong", "ini apa", "itu apa",
    }
    if normalized in greetings:
        return NARA_INTRODUCTION
    if not has_history and normalized in vague_messages:
        return NARA_CLARIFICATION
    return None

def map_references(results):
    unique = set()
    refs = []

    for r in results:
        key = (r["document_id"], r["page_number"])
        basename = os.path.basename(r["document_path"])
        uuid_part, original_filename = basename.split("_", 1)
        preview_url = f"/blobs/preview/{uuid_part}"

        # Ensure uniqueness
        if key in unique:
            continue
        unique.add(key)

        refs.append({
            "document_id": r["document_id"],
            "filename": original_filename,
            "path": r["document_path"],
            "url": preview_url ,
            "page": r["page_number"],
        })

    return refs

def extract_contents_for_analysis(results):
    return [
        {
            "filename":  r["document_path"].split("_", 1)[1].rsplit(".", 2)[0],
            "content": r["content"]
        }
        for r in results
    ]


def build_prompt(user_input, response_text):
    is_failure = '"status": "error"' in response_text or '"status": "empty_data"' in response_text
    if isinstance(response_text, list):
        formatted = ""
        for item in response_text:
            content = item.get("content", "")
            formatted += f"{content} \n"
        response_text = formatted

    if is_failure:
        return f"""
        Pertanyaan pengguna:
        {user_input}

        Data tidak tersedia.

        Instruksi jawaban:
        - Jawab sangat singkat berdasarkan topik pertanyaan.
        - Jangan menyebut error, API, data kosong, status, atau detail teknis.
        - Jangan menambahkan opini, asumsi, atau spekulasi.
        - Gunakan Bahasa Indonesia, maksimal 2 kalimat.
        """
    else:
        return f"""
        Pertanyaan pengguna:
        {user_input}

        Instruksi jawaban:
        - Jawab hanya berdasarkan pertanyaan dan data referensi berikut.
        - Jika informasi tidak ditemukan, jawab:
            "Maaf, NARA belum menemukan informasi tersebut dalam dokumen yang tersedia. Silakan sebutkan nama, judul, atau topik secara lebih spesifik."
        - Jangan menambahkan opini, asumsi, spekulasi, atau penjelasan teknis.
        - Salin nama orang, judul, lokasi, metode, angka, dan istilah persis seperti referensi; jangan mengubah ejaannya.
        - Untuk pertanyaan ringkasan dokumen, utamakan bagian ABSTRAK dan judul.
        - Gunakan Bahasa Indonesia formal dan maksimal 3 kalimat.

        Data referensi:
        {response_text}
        """


def analyze_response(user_input, contents_for_llm, max_len=8000):
    if isinstance(contents_for_llm, list):
        formatted = "".join(item.get("content", "") + " \n" for item in contents_for_llm)
        if len(formatted) > max_len:
            formatted = formatted[:max_len]
        contents_for_llm = formatted

    prompt = build_prompt(user_input, contents_for_llm)
    system_prompt_content = (
        "You are a document analysis assistant. "
        "Always respond in formal, clear, and concise Indonesian. "
        "Preserve all names, titles, numbers, locations, methods, and technical terms exactly as written in the references. "
        "Do NOT greet the user, introduce yourself, provide long conclusions, "
    )

    messages = [
        ChatMessage(role="system", content=system_prompt_content),
        ChatMessage(role="user", content=prompt),
    ]

    return model_chat(messages)


def enrich_document_query(user_input: str) -> tuple[str, str]:
    """Expand short conversational wording into retrieval and answer intent."""
    normalized = re.sub(r"\s+", " ", (user_input or "").strip())
    overview = bool(re.search(
        r"\b(isinya|tentang apa|membahas apa|ringkas(?:an)?|resume|bikin apa|buat apa|"
        r"proyek apa|tujuannya apa)\b",
        normalized,
        re.IGNORECASE,
    ))
    if not overview:
        return normalized, normalized
    search_query = (
        f"{normalized}\nCari ringkasan, judul, abstrak, tujuan, hasil, proyek, dan kesimpulan dokumen."
    )
    answer_query = (
        f"Jelaskan secara ringkas isi utama, tujuan, atau hasil yang dibuat dalam dokumen.\n"
        f"Pertanyaan asli pengguna: {normalized}"
    )
    return search_query, answer_query


def build_extractive_fallback(results: list[dict]) -> str:
    """Return grounded evidence when the selected LLM is temporarily unavailable."""
    if not results:
        return (
            "Maaf, NARA belum menemukan informasi tersebut dalam dokumen yang tersedia. "
            "Silakan sebutkan nama, judul, atau topik secara lebih spesifik."
        )
    filename = results[0].get("filename") or "dokumen"
    first_text = re.sub(r"\s+", " ", results[0].get("content", "")).strip()
    title = re.split(r"\b(?:Disusun|Oleh|ABSTRAK|ABSTRACT)\b", first_text, maxsplit=1)[0].strip(" .:-")
    if len(title) > 220:
        title = title[:220].rsplit(" ", 1)[0]

    snippets = []
    preferred_markers = ("abstrak", "latar belakang", "tujuan", "kesimpulan", "rekomendasi")
    ordered_results = sorted(
        results,
        key=lambda item: (
            not any(marker in (item.get("content") or "").lower() for marker in preferred_markers),
            item.get("page_number") or 999,
        ),
    )
    for result in ordered_results:
        text = re.sub(r"\s+", " ", result.get("content", "")).strip()
        if not text or ("daftar isi" in text.lower() and text.count(".") > 25):
            continue
        if text == first_text:
            continue
        sentences = re.split(r"(?<=[.!?])\s+", text)
        snippet = " ".join(sentences[:2]).strip()
        if snippet:
            snippets.append(snippet)
        if len(snippets) == 2:
            break
    evidence = " ".join(snippets).strip()
    if not evidence:
        evidence = first_text
    if len(evidence) > 850:
        shortened = evidence[:850]
        sentence_end = max(shortened.rfind("."), shortened.rfind("!"), shortened.rfind("?"))
        if sentence_end >= 250:
            evidence = shortened[: sentence_end + 1].strip()
        else:
            evidence = shortened.rsplit(" ", 1)[0].rstrip(" ,;:-") + "."
    elif evidence and evidence[-1] not in ".!?\"'”’":
        evidence += "."
    title_text = f" Topik dokumen: {title}." if title else ""
    return f"Berdasarkan dokumen {filename}.{title_text} {evidence}".strip()


def is_unhelpful_model_answer(answer: str) -> bool:
    normalized = (answer or "").lower()
    markers = (
        "belum menemukan informasi",
        "informasi yang diminta tidak ditemukan",
        "information not found",
        "trouble connecting to the model",
        "please try again",
    )
    return not normalized.strip() or any(marker in normalized for marker in markers)


def is_incomplete_model_answer(answer: str) -> bool:
    text = (answer or "").strip()
    return len(text) >= 80 and text[-1] not in ".!?\"'”’"


def analyze_input_chat(enriched_user_input):
    system_prompt_content = """
    You are an assistant for document query analysis.

    MANDATORY RULES:
    1. The answer must be in formal and concise Indonesian.
    2. The answer must be based ONLY on the given user text.
    3. No opinions, speculation, inference, or additional analysis.
    4. No labels, points, scores, categories, or metadata of any kind.
    5. The final result must be a single short sentence/paragraph summarizing the user's main intent.
    6. If no information can be concluded, answer:
       "Information not found in the provided data."
    7. Maximum 3 sentences. No reasons, explanations, or additional narration.
    """

    prompt = f"""
    Summarize and restate the main intent of the following user query
    into a single very clear sentence or short paragraph,
    to be used as a document search query:
    {enriched_user_input}
    """

    messages = [
        ChatMessage(role="system", content=system_prompt_content),
        ChatMessage(role="user", content=prompt),
    ]

    return model_chat(messages)


async def run_knowledge_pipeline(
    user_input: str,
    history: str,
    document_ids: list[int] = None,
):
    try:
        normalization = normalize_indonesian_query(user_input)
        if normalization.changed:
            print(f"Normalized knowledge query: {normalization.replacements}")
            user_input = normalization.normalized
        nara_response = get_nara_response(user_input, has_history=bool(history))
        if nara_response:
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "references": [],
                "results": [],
                "output": nara_response,
            }

        search_query, answer_query = enrich_document_query(user_input)

        selection_source_query = None
        matched_history_line = None
        document_resolution = await service.resolve_query_document(
            user_input,
            document_ids=document_ids,
        )
        # A single document selected by the UI mention is authoritative. The
        # user should not have to repeat its filename, and entity names inside
        # that document must not trigger an unrelated ambiguity prompt.
        if not document_resolution and document_ids and len(document_ids) == 1:
            details = await service.get_document_details(document_ids[0])
            if details:
                selected_document, _ = details
                document_resolution = {
                    "status": "resolved",
                    "document_id": selected_document.id,
                    "filename": selected_document.filename,
                }
        if not document_resolution and history:
            # Resolve the most recent explicit document mention for follow-ups
            # such as "metodologinya apa?" or "kesimpulannya?".
            history_lines = [line.strip() for line in history.splitlines() if line.strip()]
            for history_line in reversed(history_lines):
                document_resolution = await service.resolve_query_document(
                    history_line,
                    document_ids=document_ids,
                )
                if document_resolution:
                    matched_history_line = history_line
                    break
        if document_resolution and document_resolution["status"] == "ambiguous" and history:
            ordinal_match = re.search(
                r"\b(?:yang\s+)?(?:dokumen\s+)?(pertama|kedua|ketiga|1|2|3)\b",
                user_input,
                re.IGNORECASE,
            )
            if ordinal_match:
                ordinal_map = {"pertama": 0, "kedua": 1, "ketiga": 2, "1": 0, "2": 1, "3": 2}
                selected_index = ordinal_map[ordinal_match.group(1).lower()]
                candidates = document_resolution["candidates"]
                if selected_index < len(candidates):
                    selected = candidates[selected_index]
                    selection_source_query = matched_history_line
                    document_resolution = {
                        "status": "resolved",
                        "document_id": selected["id"],
                        "filename": selected["filename"],
                    }
        if document_resolution and document_resolution["status"] == "ambiguous":
            choices = ", ".join(
                candidate["filename"] for candidate in document_resolution["candidates"]
            )
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "references": [],
                "results": [],
                "output": f"NARA menemukan beberapa dokumen yang mungkin dimaksud: {choices}. Mohon pilih salah satunya.",
            }

        resolved_document = None
        effective_document_ids = document_ids
        if document_resolution and document_resolution["status"] == "resolved":
            resolved_document = document_resolution
            effective_document_ids = [document_resolution["document_id"]]
            if selection_source_query:
                search_query, answer_query = enrich_document_query(selection_source_query)
                answer_query = (
                    f"{answer_query}\nPengguna memilih dokumen urutan ke-{selected_index + 1}."
                )
            search_query = (
                f"{search_query}\nDokumen yang dimaksud: {document_resolution['filename']}"
            )
            answer_query = (
                f"{answer_query}\nGunakan hanya dokumen: {document_resolution['filename']}"
            )

        entity_resolution = None
        if not resolved_document:
            entity_resolution = await service.resolve_query_entity(
                user_input,
                document_ids=effective_document_ids,
            )
        if entity_resolution and entity_resolution["status"] == "ambiguous":
            candidates = entity_resolution["candidates"]
            choices = ", ".join(candidates[:-1]) + f" atau {candidates[-1]}"
            return {
                "status": "success",
                "date": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "references": [],
                "results": [],
                "output": f"Apakah yang dimaksud {choices}?",
            }

        resolved_entity = None
        if entity_resolution and entity_resolution["status"] == "resolved":
            resolved_entity = entity_resolution["entity"]
            search_query = f"{user_input}\nNama atau istilah pada dokumen: {resolved_entity}"
            asks_if_known = bool(re.search(
                r"\b(tahu|kenal|mengenal)\b", user_input, re.IGNORECASE
            ))
            if asks_if_known:
                answer_query = (
                    f"Jelaskan secara singkat siapa {resolved_entity} berdasarkan referensi.\n"
                    f"Pertanyaan asli pengguna: {user_input}"
                )
            else:
                answer_query = (
                    f"{user_input}\n"
                    f"Nama atau istilah yang telah dicocokkan dengan dokumen: {resolved_entity}"
                )

        # An explicit entity starts a clear topic and must not be polluted by
        # unrelated older WhatsApp turns. History remains useful for pronoun
        # follow-ups such as "pendidikannya apa?" where no entity is present.
        if history and not resolved_entity and not resolved_document:
            history_lines = [line.strip() for line in history.splitlines() if line.strip()]
            topic_anchor = history_lines[0] if history_lines else history
            entity_hint = f"\nEntitas dokumen: {resolved_entity}" if resolved_entity else ""
            search_query = f"{history}\nPertanyaan lanjutan: {user_input}{entity_hint}"
            answer_query = (
                f"Topik rujukan: {topic_anchor}\n"
                f"Pertanyaan terbaru: {user_input}\n"
                + (f"Nama atau istilah yang telah dicocokkan: {resolved_entity}\n" if resolved_entity else "")
                +
                "Jawab hanya pertanyaan terbaru dan jangan mengulang jawaban sebelumnya."
            )

        results = await service.find_vector(
            search_query,
            document_ids=effective_document_ids,
            entity_hint=resolved_entity,
        )

        section_intent = None
        if re.search(r"\b(metodologi(?:nya)?|metode penelitian|pendekatan penelitian)\b", user_input, re.IGNORECASE):
            section_intent = "methodology"
        elif re.search(r"\b(tujuan(?:nya)?|tujuan penelitian)\b", user_input, re.IGNORECASE):
            section_intent = "objective"
        elif re.search(r"\b(kesimpulan(?:nya)?|simpulan(?:nya)?)\b", user_input, re.IGNORECASE):
            section_intent = "conclusion"

        missing_section_message = None
        if resolved_document and section_intent:
            section_results = await service.get_document_section_results(
                resolved_document["document_id"],
                section_intent,
            )
            if section_results:
                results = section_results
            elif section_intent == "conclusion":
                missing_section_message = (
                    f"Dokumen {resolved_document['filename']} belum memuat bagian kesimpulan yang eksplisit. "
                    "Dokumen tersebut masih berupa rancangan atau proposal penelitian."
                )
                results = []

        intent_query = selection_source_query or user_input
        is_overview_question = bool(re.search(
            r"\b(isinya|tentang apa|membahas apa|ringkas(?:an)?|resume|bikin apa|buat apa|proyek apa|tujuannya apa)\b",
            intent_query,
            re.IGNORECASE,
        ))
        if resolved_document and is_overview_question:
            overview_results = await service.get_document_overview_results(
                resolved_document["document_id"]
            )
            if overview_results:
                results = overview_results

        references = map_references(results)
        contents_for_llm = extract_contents_for_analysis(results)

        if missing_section_message:
            answer = missing_section_message
        elif not results:
            answer = build_extractive_fallback([])
        else:
            try:
                answer = analyze_response(answer_query, contents_for_llm)
                if is_incomplete_model_answer(answer):
                    answer = analyze_response(answer_query, contents_for_llm)
                    if is_incomplete_model_answer(answer):
                        answer = build_extractive_fallback(results)
                if is_unhelpful_model_answer(answer):
                    answer = build_extractive_fallback(results)
            except Exception as model_error:
                print(f"Document model fallback: {type(model_error).__name__}")
                answer = build_extractive_fallback(results)

        return {
            "status": "success",
            "date": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "references": references,
            "results": contents_for_llm,
            "output": answer,
        }

    except Exception as e:
        print("Error in the pipeline:", e)
        return {"status": "error", "message": str(e)}
