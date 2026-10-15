import asyncio
import re
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.whatsapp_auth_session import WhatsAppAuthSession
from routes.v1 import analyze as api_route, knowledge as knowledge_route
from services.auth_service import require_api_key
from services.chat_history_service import ChatHistoryService
from services.tts_service import send_whatsapp_voice_note
from services.whatsapp_auth_service import handle_whatsapp_auth
from services.whatsapp_follow_ups import DynamicFollowUpGenerator, format_nara_follow_up
from services.whatsapp_location import (
    handle_whatsapp_location_query,
    parse_whatsapp_coordinates,
)
from services.whisper_transcriber import transcribe_base64_audio
from services.whatsapp_volcano_region import (
    answer_named_volcano_query,
    answer_ranked_volcano_query,
    answer_regional_volcano_query,
)
from utils.follow_ups import AFFIRM_RE, DECLINE_RE, OFFER_MARKER
from utils.location_answers import detect_location_question

_SESSION_LOCATIONS: dict[str, tuple[float, float, str | None]] = {}


router = APIRouter()

MODE_COMMANDS = {
    "/knowlage-base": "knowledge",
    "/knowledge-base": "knowledge",
    "/api-documentation": "api",
    "/auto": "auto",
}

API_TOPIC = re.compile(
    r"\b(?:gunung(?:\s+api)?|gempa(?:\s+bumi)?|gempabumi|erupsi|letusan|"
    r"vulkanik|pvmbg|magma|tsunami|longsor|gerakan\s+tanah|siaga|waspada|awas|"
    r"merapi|semeru|sinabung|krakatau|bromo|agung|marapi|lewotobi|tangkuban|"
    r"lokasi|posisi|koordinat|terdekat|aman|dmna|dimana)\b",
    re.IGNORECASE,
)
DOCUMENT_TOPIC = re.compile(
    r"\b(?:dokumen|pdf|file|berkas|laporan|proposal|proyek|project|skripsi|"
    r"bab|halaman|kutipan|ringkas|rangkum|knowledge\s+base)\b",
    re.IGNORECASE,
)


class WhatsAppAnalyzeRequest(BaseModel):
    user_input: str = ""
    session_id: str
    model: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    audio_base64: str | None = None
    audio_mimetype: str | None = None


def _route_for(message: str, mode: str, last_route: str | None) -> str:
    if mode in {"api", "knowledge"}:
        return mode
    api_match = bool(API_TOPIC.search(message))
    document_match = bool(DOCUMENT_TOPIC.search(message))
    if document_match:
        return "knowledge"
    if api_match:
        return "api"
    return last_route if last_route in {"api", "knowledge"} else "knowledge"


def strip_whatsapp_asterisks(text: str) -> str:
    """Strip all asterisk markdown formatting so WhatsApp messages are clean and plain text."""
    if not text:
        return ""
    # Convert markdown bullet "* " to "- "
    text = re.sub(r"(?m)^\s*\*\s+", "- ", text)
    # Remove markdown bold/italic asterisks: ***text***, **text**, *text*
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    # Strip any remaining stray asterisk characters
    text = text.replace("*", "")
    return text


def _response(output: str, session_id: str, mode: str, *, status: str = "success") -> dict:
    return {
        "status": status,
        "date": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "mode": mode,
        "output": strip_whatsapp_asterisks(output),
        "suggested_follow_ups": [],
    }


def _clarifying_follow_up(route: str, question: str) -> str:
    if route == "api":
        if re.search(r"(?i)\bgunung\b", question):
            return "💬 Gunung mana yang ingin Anda periksa berikutnya? NARA bisa bantu cek status atau rekomendasi resminya."
        return "💬 Informasi kebencanaan apa yang ingin Anda dalami? NARA bisa bantu mencarikannya."
    return "💬 Dokumen atau bagian mana yang ingin Anda telusuri lebih lanjut? NARA bisa bantu mencarinya."


@router.post("/analyze")
async def analyze_whatsapp(
    req: WhatsAppAnalyzeRequest,
    background_tasks: BackgroundTasks,
    api_key: dict = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    session_id = req.session_id.strip()
    if not session_id.startswith("whatsapp-") or len(session_id) > 180:
        raise HTTPException(status_code=400, detail="Sesi WhatsApp tidak valid")
    is_voice_note = False
    transcribed_text = None
    if req.audio_base64 and req.audio_base64.strip():
        try:
            mime = req.audio_mimetype or "audio/ogg"
            transcribed_text = transcribe_base64_audio(req.audio_base64, mimetype=mime)
            if transcribed_text and transcribed_text.strip():
                message = transcribed_text.strip()
                is_voice_note = True
            else:
                return _response(
                    "NARA tidak dapat menangkap suara dari pesan suara ini dengan jelas. "
                    "Silakan coba rekam ulang atau ketik pertanyaan Anda.",
                    session_id,
                    "auto",
                )
        except Exception as exc:
            return _response(
                "Terjadi kendala saat memproses pesan suara. Silakan coba kembali atau ketikkan pertanyaan Anda.",
                session_id,
                "auto",
            )
    else:
        message = (req.user_input or "").strip()

    has_coords = req.latitude is not None and req.longitude is not None
    if not message and not has_coords:
        return _response("Tulis pertanyaan atau ketik /help untuk melihat pilihan mode.", session_id, "auto")
    if not message and has_coords:
        loc_label = f", {req.location_name}" if req.location_name else ""
        message = f"[LOKASI: {req.latitude}, {req.longitude}{loc_label}]"

    state = await db.get(WhatsAppAuthSession, session_id)
    if state is None:
        state = WhatsAppAuthSession(session_id=session_id)
        db.add(state)
        await db.flush()

    def _maybe_send_voice(text_to_speak: str):
        # The reply format follows the session preference, not the input format.
        # A voice note can still be transcribed while /voice off or /text is active.
        # Check the current value so an inline "/voice <question>" also gets audio.
        if state.voice_mode and text_to_speak and text_to_speak.strip():
            sender_num = session_id.removeprefix("whatsapp-")
            background_tasks.add_task(send_whatsapp_voice_note, sender_num, text_to_speak)

    command, _, inline_question = message.partition(" ")
    command = command.casefold()

    if command in {"/voice", "/suara", "/voice-mode"}:
        sub_arg = inline_question.strip().casefold()
        if sub_arg in {"off", "mati", "nonaktif", "disable"}:
            state.voice_mode = False
            await db.commit()
            return _response(
                "Mode pesan suara dinonaktifkan. NARA akan membalas dengan teks saja.\n"
                "Ketik /voice kapan saja untuk mengaktifkan kembali pesan suara.",
                session_id,
                state.conversation_mode or "auto",
            )
        elif sub_arg in {"on", "aktif", "enable"} or not sub_arg:
            state.voice_mode = True
            await db.commit()
            desc = (
                "Mode pesan suara aktif! 🎙️\n\n"
                "Setiap jawaban NARA berikutnya akan disertai Pesan Suara (Voice Note) resmi.\n"
                "Ketik /voice off atau /text untuk kembali ke mode teks saja."
            )
            _maybe_send_voice(desc)
            return _response(desc, session_id, state.conversation_mode or "auto")
        else:
            # Inline question with voice mode enabled (e.g. "/voice bagaimana status Merapi?")
            state.voice_mode = True
            await db.commit()
            message = inline_question.strip()

    elif command in {"/text", "/teks"}:
        state.voice_mode = False
        await db.commit()
        return _response(
            "Mode teks aktif. NARA akan membalas dengan pesan teks saja.\n"
            "Ketik /voice untuk mengaktifkan pesan suara.",
            session_id,
            state.conversation_mode or "auto",
        )

    if command == "/help":
        return _response(
            "Perintah Mode Percakapan NARA di WhatsApp:\n\n"
            "- Ketik /voice : Mengaktifkan mode pesan suara (setiap jawaban akan disertai Voice Note)\n"
            "- Ketik /voice off (atau /text) : Nonaktifkan pesan suara, kembali ke mode teks saja\n"
            "- Ketik /auto : Mode otomatis (sumber jawaban dipilih otomatis sesuai pertanyaan)\n"
            "- Ketik /api-documentation : Khusus data resmi pemantauan langsung dari API MAGMA Indonesia\n"
            "- Ketik /knowledge-base : Khusus tanya jawab dan pencarian isi dokumen PDF\n"
            "- Ketik /help : Menampilkan panduan bantuan ini\n"
            "- Ketik /login : Masuk dengan email kedinasan sebelum mengunggah dokumen",
            session_id,
            state.conversation_mode or "auto",
        )
    if command in MODE_COMMANDS:
        state.conversation_mode = MODE_COMMANDS[command]
        state.pending_follow_up = None
        if state.state.startswith("awaiting_"):
            state.state = "anonymous"
            state.pending_email = None
            state.failed_attempts = 0
        await db.commit()
        if not inline_question.strip():
            descriptions = {
                "knowledge": "Mode Knowledge Base aktif. Pertanyaan berikutnya dicari dari dokumen tersimpan.",
                "api": "Mode API Documentation aktif. Pertanyaan berikutnya dijawab dari layanan informasi MAGMA.",
                "auto": "Mode otomatis aktif. Sumber jawaban dipilih dari isi pertanyaan.",
            }
            return _response(descriptions[state.conversation_mode], session_id, state.conversation_mode)
        message = inline_question.strip()

    auth_result = await handle_whatsapp_auth(db, session_id, message)
    if auth_result:
        return _response(auth_result["output"], session_id, state.conversation_mode or "auto")

    # ===================================================================
    # GREETINGS & NARA IDENTITY HANDLING FOR WHATSAPP
    # ===================================================================
    clean_msg = re.sub(r"[^\w\s]", "", message.lower()).strip()
    is_nara_greeting = bool(
        clean_msg in {
            "nara", "hai nara", "halo nara", "hallo nara", "hi nara", "hey nara", "hei nara",
            "siapa nara", "apa itu nara", "tentang nara", "kamu siapa", "siapa kamu",
            "halo", "hai", "hi", "hey", "hallo", "assalamualaikum", "assalamualaikum wr wb",
            "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "p", "permisi",
            "info", "info nara", "bantuan"
        }
        or re.match(r"^(?:hai|halo|hallo|hi|hey|hei|selamat\s+(?:pagi|siang|sore|malam))\s+nara\b", clean_msg)
        or clean_msg.startswith("siapa nara")
        or clean_msg.startswith("apa itu nara")
    )
    if is_nara_greeting:
        state.pending_follow_up = None
        await db.commit()
        intro_text = (
            "Halo! Saya NARA, asisten virtual resmi MAGMA Indonesia (Pusat Vulkanologi dan Mitigasi Bencana Geologi / PVMBG, Badan Geologi, Kementerian ESDM).\n\n"
            "Saya bertugas membantu Anda dalam dua layanan utama:\n"
            "1. Informasi Kebencanaan Geologi Real-Time (API MAGMA Indonesia):\n"
            "   - Status aktivitas 69 gunung api aktif di Indonesia dan rekomendasi jarak bahaya\n"
            "   - Laporan kejadian gempa bumi dan tsunami terkini\n"
            "   - Laporan kejadian gerakan tanah / tanah longsor\n"
            "   - Pengecekan potensi bahaya geologi terdekat dari posisi Anda\n"
            "   - Panduan mitigasi dan keselamatan bencana geologi\n\n"
            "2. Analisis & Pencarian Dokumen Kebencanaan (Knowledge Base):\n"
            "   - Mencari informasi, kutipan, dan ringkasan dari dokumen PDF atau buletin kebencanaan yang diunggah\n\n"
            "Perintah Mode Percakapan di WhatsApp:\n"
            "- Ketik /voice : Mengaktifkan mode pesan suara (setiap jawaban akan disertai Voice Note)\n"
            "- Ketik /auto : Mode otomatis (asisten memilih sumber jawaban sesuai pertanyaan Anda)\n"
            "- Ketik /api-documentation : Khusus data resmi pemantauan langsung dari API MAGMA Indonesia\n"
            "- Ketik /knowledge-base : Khusus tanya jawab dan pencarian isi dokumen PDF\n"
            "- Ketik /help : Menampilkan panduan bantuan ini\n"
            "- Ketik /login : Masuk dengan email kedinasan sebelum mengunggah dokumen\n\n"
            "Silakan ajukan pertanyaan seputar kebencanaan geologi atau dokumen yang ingin Anda tanyakan!"
        )
        _maybe_send_voice(intro_text)
        if is_voice_note and transcribed_text:
            intro_text = f"🎙️ Pesan Suara: \"{transcribed_text}\"\n\n{intro_text}"
        return _response(intro_text, session_id, state.conversation_mode or "auto")

    if AFFIRM_RE.fullmatch(message) and state.pending_follow_up:
        message = state.pending_follow_up
    elif DECLINE_RE.fullmatch(message) and state.pending_follow_up:
        state.pending_follow_up = None
        await db.commit()
        return _response("Baik. Silakan tanyakan hal lain kapan saja.", session_id, state.conversation_mode or "auto")
    state.pending_follow_up = None

    # ===================================================================
    # LOCATION SHARING & COORDINATE HANDLING FOR WHATSAPP
    # ===================================================================
    lat, lon, loc_name = parse_whatsapp_coordinates(
        message,
        latitude=req.latitude,
        longitude=req.longitude,
        location_name=req.location_name,
    )
    if lat is not None and lon is not None:
        _SESSION_LOCATIONS[session_id] = (lat, lon, loc_name)
        loc_output, follow_up_target, nearest_list = handle_whatsapp_location_query(
            lat, lon, candidate_name=loc_name
        )
        state.pending_follow_up = follow_up_target
        state.last_route = "api"
        await db.commit()

        history_id = f"{session_id}:api"
        chat_history = ChatHistoryService(db)
        user_id = api_key.get("id") or api_key.get("token")
        await chat_history.create_message(
            user_id=user_id,
            session_id=history_id,
            role="user",
            message=message,
        )
        await chat_history.create_message(
            user_id=user_id,
            session_id=history_id,
            role="assistant",
            message=loc_output,
        )

        loc_display = loc_output
        _maybe_send_voice(loc_output)
        if is_voice_note and transcribed_text:
            loc_display = f"🎙️ Pesan Suara: \"{transcribed_text}\"\n\n{loc_output}"

        resp = _response(loc_display, session_id, "api")
        resp["response"] = nearest_list
        resp["suggested_follow_ups"] = [follow_up_target] if follow_up_target else []
        return resp

    # Check if user asks about their own location/position/safety
    is_asking_location = bool(
        detect_location_question(message, lang="id")
        or re.search(
            r"\b(?:dmna|dimana|dmana|di mana)\s+(?:lokasi|posisi|tempat|daerah|saya)?\b|"
            r"\b(?:lokasi|posisi)\s+(?:saya|aku)\s*(?:dmna|dimana|dmana|di mana)?\b|"
            r"\b(?:gunung(?:\s+api)?\s+terdekat\s+(?:dari|di)?\s*(?:saya|sini|posisi\s+saya|lokasi\s+saya)|"
            r"(?:posisi|lokasi|daerah|wilayah|tempat)\s+saya\s+(?:aman|bahaya|berbahaya)|"
            r"apakah\s+(?:saya|di\s+sini|disini)\s+aman)\b",
            message,
            re.IGNORECASE,
        )
    )
    if is_asking_location:
        if session_id in _SESSION_LOCATIONS:
            cached_lat, cached_lon, cached_name = _SESSION_LOCATIONS[session_id]
            loc_output, follow_up_target, nearest_list = handle_whatsapp_location_query(
                cached_lat, cached_lon, candidate_name=cached_name
            )
            state.pending_follow_up = follow_up_target
            state.last_route = "api"
            await db.commit()

            history_id = f"{session_id}:api"
            chat_history = ChatHistoryService(db)
            user_id = api_key.get("id") or api_key.get("token")
            await chat_history.create_message(
                user_id=user_id,
                session_id=history_id,
                role="user",
                message=message,
            )
            await chat_history.create_message(
                user_id=user_id,
                session_id=history_id,
                role="assistant",
                message=loc_output,
            )

            loc_display = loc_output
            _maybe_send_voice(loc_output)
            if is_voice_note and transcribed_text:
                loc_display = f"🎙️ Pesan Suara: \"{transcribed_text}\"\n\n{loc_output}"

            resp = _response(loc_display, session_id, "api")
            resp["response"] = nearest_list
            resp["suggested_follow_ups"] = [follow_up_target] if follow_up_target else []
            return resp

        guide_text = (
            "Untuk mengetahui posisi Anda dan gunung api terdekat secara akurat:\n\n"
            "1. Kirim Lokasi Langsung (Share Location):\n"
            "   Klik tombol lampiran (📎) di WhatsApp > pilih 'Lokasi' > kirim lokasi Anda saat ini.\n\n"
            "2. Atau sebutkan nama daerah Anda:\n"
            "   Contoh: 'gunung terdekat dari Pasrujambe' atau 'gunung terdekat dari Bandung'."
        )
        _maybe_send_voice(guide_text)
        if is_voice_note and transcribed_text:
            guide_text = f"🎙️ Pesan Suara: \"{transcribed_text}\"\n\n{guide_text}"
        return _response(guide_text, session_id, state.conversation_mode or "auto")

    mode = state.conversation_mode or "auto"
    route = _route_for(message, mode, state.last_route)
    state.last_route = route
    await db.commit()

    if route == "api":
        # A reply such as "Iyaa gunung Talang" names a volcano; the filler must
        # not be fuzzy-matched to the distinct volcano named Iya.
        message = re.sub(r"(?i)^\s*(?:iya+|ya+|oke+|ok|betul)\s+(?=(?:gunung|gn\.?)\b)", "", message).strip()
        history_id = f"{session_id}:api"
        volcano_result = await answer_ranked_volcano_query(message)
        if not volcano_result and re.search(r"(?i)\bgunung\b", message):
            volcano_result = await answer_regional_volcano_query(message)
        if not volcano_result:
            volcano_result = await answer_named_volcano_query(message)
        if volcano_result:
            volcano_answer, volcanoes = volcano_result
            chat_history = ChatHistoryService(db)
            user_id = api_key.get("id") or api_key.get("token")
            await chat_history.create_message(
                user_id=user_id, session_id=history_id, role="user", message=message,
            )
            await chat_history.create_message(
                user_id=user_id, session_id=history_id, role="assistant", message=volcano_answer,
            )
            result = _response(volcano_answer, session_id, route)
            result["response"] = volcanoes
        else:
            result = await api_route.analyze(
                api_route.AnalyzeRequest(
                    user_input=message, session_id=history_id, model=req.model,
                ), api_key=api_key, db=db,
            )
    else:
        result = await knowledge_route.analyze(
            knowledge_route.AnalyzeRequest(
                user_input=message, session_id=session_id, model=req.model,
            ), api_key=api_key, db=db,
        )
        history_id = session_id

    raw_answer = str(result.get("output") or "").strip()
    answer = raw_answer.split(f"\n\n{OFFER_MARKER}", 1)[0].strip()
    if result.get("status") != "success" or not answer:
        answer = answer or "NARA belum berhasil mendapatkan jawaban untuk pertanyaan itu."
        _maybe_send_voice(answer)
        result["output"] = strip_whatsapp_asterisks(f"{answer}\n\n{_clarifying_follow_up(route, message)}")
        result["mode"] = route
        return result

    history = await ChatHistoryService(db).get_session_messages(
        user_id=api_key.get("id") or api_key.get("token"),
        session_id=history_id,
        limit=16,
    )
    previous_questions = [item.message for item in history if item.role == "user"]
    prior_offers = list(state.recent_follow_ups or [])
    suggestion = await DynamicFollowUpGenerator.generate(
        mode=route,
        question=message,
        answer=answer,
        references=result.get("references") or [],
        previous=previous_questions + prior_offers,
        model=req.model,
    )
    if suggestion:
        state.pending_follow_up = suggestion
        state.recent_follow_ups = (prior_offers + [suggestion])[-12:]
        answer += f"\n\n{format_nara_follow_up(suggestion)}"
    else:
        answer += f"\n\n{_clarifying_follow_up(route, message)}"
    await db.commit()

    _maybe_send_voice(answer)
    if is_voice_note and transcribed_text:
        answer = f"🎙️ Pesan Suara: \"{transcribed_text}\"\n\n{answer}"
    result["output"] = strip_whatsapp_asterisks(answer)
    result["mode"] = route
    result["suggested_follow_ups"] = [suggestion] if suggestion else []
    return result
