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

router = APIRouter()

# --------------------------
# Request model
# --------------------------
class AnalyzeRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    geo_location: Optional[Tuple[float, float]] = None
    location_name: Optional[str] = None

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


# --------------------------
# Routes
# --------------------------
@router.post("")
async def analyze(req: AnalyzeRequest,
            api_key: str = Depends(require_api_key),
            db: Session = Depends(get_db)):
    loop = asyncio.get_running_loop()
    # Generate session_id if not provided
    session_id = req.session_id or str(uuid.uuid4())
    # Save chat history
    chat_service = ChatHistoryService(db)
    user_id = api_key.get("id")
    history_context=None

    if not user_id:
        user_id = api_key.get("token")
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
        message=req.user_input
    )

    result = await loop.run_in_executor(
        pipeline_executor,
        run_pipeline,
        req.user_input,
        req.geo_location,
        history_context,
        req.location_name
    )

    if result["status"]=="error":
        log_entry = {
            "status": "error",
            "date": datetime.utcnow().isoformat(),
            "user_input": req.user_input,
            "api_call": result["api_call"],
            "output": result["output"],
            "geo_location": req.geo_location,
            "session_id": session_id
        }
        await chat_service.create_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            message=result["output"],
            api_call=result["api_call"],
            geo_location=req.geo_location,
        )
        return log_entry

    # Save to log.json
    log_entry = {
        "status": "success",
        "date": result["date"],
        "user_input": req.user_input,
        "api_call": result["api_call"],
        "output": result["output"],
        "response": result["response"],
        "geo_location": req.geo_location,
        "session_id": session_id
    }

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        message=result["output"],
        api_call = result["api_call"],
        geo_location=req.geo_location,
        response = result["response"]
    )

    return log_entry

@router.post("/en")
async def analyze_en(
    req: AnalyzeRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    loop = asyncio.get_running_loop()

    # Generate session_id if not provided
    session_id = req.session_id or str(uuid.uuid4())

    chat_service = ChatHistoryService(db)
    user_id = api_key.get("id") or api_key.get("token")

    # -------------------------------
    # HISTORY (IDENTICAL TO ID)
    # -------------------------------
    history_context = None
    if session_id:
        history = await chat_service.get_session_messages(
            user_id=user_id,
            session_id=session_id,
            limit=10
        )
        history_context = build_history_context(history)

    # Save USER message
    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="user",
        message=req.user_input,
        lang="en"
    )

    # -------------------------------
    # PIPELINE CALL (FIXED)
    # -------------------------------
    result = await loop.run_in_executor(
        pipeline_executor,
        run_pipeline_en,
        req.user_input,
        req.geo_location,
        history_context,
        req.location_name  
    )

    # -------------------------------
    # ERROR HANDLING (IDENTICAL)
    # -------------------------------
    if result["status"] == "error":
        log_entry = {
            "status": "error",
            "intent": result.get("intent"),  
            "date": datetime.utcnow().isoformat(),
            "user_input": req.user_input,
            "api_call": result.get("api_call"),
            "output": result.get("output"),
            "geo_location": req.geo_location,
            "session_id": session_id
        }

        await chat_service.create_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            message=result.get("output"),
            api_call=result.get("api_call"),
            geo_location=req.geo_location,
            lang="en"
        )

        return log_entry

    # -------------------------------
    # SUCCESS (IDENTICAL)
    # -------------------------------
    log_entry = {
        "status": "success",
        "intent": result.get("intent"),  
        "date": result["date"],
        "user_input": req.user_input,
        "api_call": result["api_call"],
        "output": result["output"],
        "response": result["response"],
        "geo_location": req.geo_location,
        "session_id": session_id
    }

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        message=result["output"],
        api_call=result["api_call"],
        response=result["response"],
        geo_location=req.geo_location,
        lang="en"
    )

    return log_entry