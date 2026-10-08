"""WhatsApp-only conversation modes and answer follow-ups."""

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.whatsapp_auth_session import WhatsAppAuthSession
from routes.v1 import analyze as api_route, knowledge as knowledge_route
from services.auth_service import require_api_key
from services.chat_history_service import ChatHistoryService
from services.whatsapp_auth_service import handle_whatsapp_auth
from services.whatsapp_follow_ups import DynamicFollowUpGenerator, format_nara_follow_up
from services.whatsapp_volcano_region import answer_regional_volcano_query
from utils.follow_ups import AFFIRM_RE, DECLINE_RE, OFFER_MARKER


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
    r"merapi|semeru|sinabung|krakatau|bromo|agung|marapi|lewotobi|tangkuban)\b",
    re.IGNORECASE,
)
DOCUMENT_TOPIC = re.compile(
    r"\b(?:dokumen|pdf|file|berkas|laporan|proposal|proyek|project|skripsi|"
    r"bab|halaman|kutipan|ringkas|rangkum|knowledge\s+base)\b",
    re.IGNORECASE,
)


class WhatsAppAnalyzeRequest(BaseModel):
    user_input: str
    session_id: str
    model: str | None = None


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


def _response(output: str, session_id: str, mode: str, *, status: str = "success") -> dict:
    return {
        "status": status,
        "date": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "mode": mode,
        "output": output,
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
    api_key: dict = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    session_id = req.session_id.strip()
    if not session_id.startswith("whatsapp-") or len(session_id) > 180:
        raise HTTPException(status_code=400, detail="Sesi WhatsApp tidak valid")
    message = req.user_input.strip()
    if not message:
        return _response("Tulis pertanyaan atau ketik /help untuk melihat pilihan mode.", session_id, "auto")

    state = await db.get(WhatsAppAuthSession, session_id)
    if state is None:
        state = WhatsAppAuthSession(session_id=session_id)
        db.add(state)
        await db.flush()

    command, _, inline_question = message.partition(" ")
    command = command.casefold()
    if command == "/help":
        return _response(
            "Ketik /knowlage-base untuk bertanya khusus tentang dokumen, "
            "/api-documentation untuk informasi MAGMA, atau /auto agar dipilih sesuai pertanyaan. "
            "Ketik /login sebelum mengunggah dokumen.", session_id, state.conversation_mode or "auto",
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

    if AFFIRM_RE.fullmatch(message) and state.pending_follow_up:
        message = state.pending_follow_up
    elif DECLINE_RE.fullmatch(message) and state.pending_follow_up:
        state.pending_follow_up = None
        await db.commit()
        return _response("Baik. Silakan tanyakan hal lain kapan saja.", session_id, state.conversation_mode or "auto")
    state.pending_follow_up = None

    mode = state.conversation_mode or "auto"
    route = _route_for(message, mode, state.last_route)
    state.last_route = route
    await db.commit()

    if route == "api":
        history_id = f"{session_id}:api"
        regional = await answer_regional_volcano_query(message) if re.search(r"(?i)\bgunung\b", message) else None
        if regional:
            regional_answer, volcanoes = regional
            chat_history = ChatHistoryService(db)
            user_id = api_key.get("id") or api_key.get("token")
            await chat_history.create_message(
                user_id=user_id, session_id=history_id, role="user", message=message,
            )
            await chat_history.create_message(
                user_id=user_id, session_id=history_id, role="assistant", message=regional_answer,
            )
            result = _response(regional_answer, session_id, route)
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
        result["output"] = f"{answer}\n\n{_clarifying_follow_up(route, message)}"
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

    result["output"] = answer
    result["mode"] = route
    result["suggested_follow_ups"] = [suggestion] if suggestion else []
    return result
