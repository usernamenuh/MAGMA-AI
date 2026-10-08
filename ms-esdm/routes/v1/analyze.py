from datetime import datetime
from typing import Optional, Tuple
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from db.session import get_db
from services.auth_service import require_api_key
from services.pipeline_en import run_pipeline_en, pipeline_executor
from services.pipeline_id import run_pipeline, pipeline_executor
from services.logger import save_log
from services.chat_history_service import ChatHistoryService
import uuid
import asyncio
from functools import partial
from utils.pipeline_helpers import run_with_chat_model
from utils.follow_ups import choose_follow_up, append_follow_up, resolve_follow_up_reply, OFFER_MARKER

router = APIRouter()

# --------------------------
# Request model
# --------------------------
class AnalyzeRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    geo_location: Optional[Tuple[float, float]] = None
    location_name: Optional[str] = None
    location_accuracy: Optional[float] = None
    model: Optional[str] = None

    @field_validator("geo_location", mode="before")
    def handle_null_list(cls, v):
        if isinstance(v, list) and all(x is None for x in v):
            return None
        return v

def build_history_context(history):
    ctx = []
    for msg in history:
        role = "user" if msg.role == "user" else "assistant"
        text = msg.message[:500]
        ctx.append(f"{role}: {text}")
    return "\n".join(ctx)


def _nearest_name(result: dict) -> Optional[str]:
    nearest = result.get("nearest_volcano") if isinstance(result, dict) else None
    if isinstance(nearest, dict):
        return nearest.get("name") or nearest.get("ga_nama_gapi")
    return None


async def _handle_analyze(req: AnalyzeRequest, api_key, db, lang: str):
    loop = asyncio.get_running_loop()
    session_id = req.session_id or str(uuid.uuid4())
    chat_service = ChatHistoryService(db)
    user_id = api_key.get("id") or api_key.get("token")
    msg_lang = {"lang": "en"} if lang == "en" else {}

    history = []
    history_context = None
    if session_id:
        history = await chat_service.get_session_messages(
            user_id=user_id,
            session_id=session_id,
            limit=10
        )
        history_context = build_history_context(history)

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="user",
        message=req.user_input,
        **msg_lang,
    )

    # Short replies such as "ya" / "tidak" answer the offer the assistant made
    # at the end of its previous message.
    effective_input = req.user_input
    reply = resolve_follow_up_reply(req.user_input, history, lang)
    if reply and reply[0] == "decline":
        await chat_service.create_message(
            user_id=user_id, session_id=session_id, role="assistant",
            message=reply[1], geo_location=req.geo_location, **msg_lang,
        )
        return {
            "status": "success",
            "date": datetime.utcnow().isoformat(),
            "user_input": req.user_input,
            "api_call": None,
            "output": reply[1],
            "response": None,
            "geo_location": req.geo_location,
            "session_id": session_id,
            "suggested_follow_ups": [],
        }
    if reply and reply[0] == "affirm":
        effective_input = reply[1]
        print(f"[FOLLOW-UP] '{req.user_input}' resolved to '{effective_input}'")

    pipeline = run_pipeline_en if lang == "en" else run_pipeline
    result = await loop.run_in_executor(
        pipeline_executor,
        partial(run_with_chat_model, req.model, pipeline,
                effective_input, req.geo_location, history_context, req.location_name,
                req.location_accuracy)
    )

    if result is None or result.get("status") == "error":
        default_err = (
            "An error occurred while processing your request." if lang == "en"
            else "Terjadi kesalahan pada layanan pemrosesan."
        )
        err_output = (result.get("output") if result else None) or default_err
        api_call = result.get("api_call") if result else None
        await chat_service.create_message(
            user_id=user_id, session_id=session_id, role="assistant",
            message=err_output, api_call=api_call, geo_location=req.geo_location, **msg_lang,
        )
        return {
            "status": "error",
            "intent": result.get("intent") if result else None,
            "date": datetime.utcnow().isoformat(),
            "user_input": req.user_input,
            "api_call": api_call,
            "output": err_output,
            "geo_location": req.geo_location,
            "session_id": session_id,
            "suggested_follow_ups": [],
        }

    output_text = result.get("output") or result.get("answer") or ""
    clean_answer = result.get("answer") or output_text
    if "<!--" in clean_answer:
        clean_answer = clean_answer.split("<!--")[0].strip()
    if "<!--" in output_text:
        output_text = output_text.split("<!--")[0].strip()

    has_explicit_follow_ups = "follow_ups" in result
    follow_ups = result.get("follow_ups") if has_explicit_follow_ups else []
    pending_act = result.get("pending_action") or (follow_ups[0].get("action") if follow_ups else None)

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        message=clean_answer,
        api_call=result.get("api_call"),
        geo_location=req.geo_location,
        response={
            "api_response": result.get("response"),
            "follow_ups": follow_ups,
            "pending_action": pending_act,
        },
        references=[],
        **msg_lang,
    )

    suggested_follow_ups = result.get("suggested_follow_ups") or [fu.get("action", fu.get("query")) for fu in follow_ups]

    return {
        "status": "success",
        "intent": result.get("intent"),
        "date": result.get("date"),
        "user_input": req.user_input,
        "resolved_input": effective_input if effective_input != req.user_input else None,
        "api_call": result.get("api_call"),
        "references": [],
        "output": clean_answer,
        "answer": clean_answer,
        "follow_ups": follow_ups,
        "suggested_follow_ups": suggested_follow_ups,
        "context": {
            "intent": result.get("intent"),
            "entity": result.get("entity"),
            "pending_action": pending_act,
            "executed_actions": (result.get("context") or {}).get("executed_actions") or [],
        },
        "response": result.get("response"),
        "geo_location": req.geo_location,
        "session_id": session_id,
    }


# --------------------------
# Routes
# --------------------------
@router.post("")
async def analyze(req: AnalyzeRequest,
            api_key: str = Depends(require_api_key),
            db: Session = Depends(get_db)):
    return await _handle_analyze(req, api_key, db, "id")


@router.post("/en")
async def analyze_en(
    req: AnalyzeRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    return await _handle_analyze(req, api_key, db, "en")
