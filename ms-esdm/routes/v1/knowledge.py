import asyncio
import json
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import shutil
import os
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette import status

from db.session import get_db, SessionLocal
from models import Document
from models.document import DocumentStatus
from routes.v1.analyze import build_history_context
from services.auth_service import require_api_key
from services.chat_history_service import ChatHistoryService
from services.knowledge_documents_service import KnowledgeDocumentsService
from pydantic import BaseModel

from services.pipeline_knowledge import run_knowledge_pipeline
from services.pipeline_knowledge_en import run_knowledge_pipeline_en
from worker.knowledge_worker import process_document_background

router = APIRouter()

UPLOAD_DIR = "blobs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

service = KnowledgeDocumentsService()

class AnalyzeRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None

@router.post("/upload")
async def upload_knowledge(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    allowed = (".pdf", ".doc", ".docx")

    if not file.filename.lower().endswith(allowed):
        raise HTTPException(400, "Only PDF and Word files are supported")

    uuid_str = str(uuid.uuid4())
    uuid_filename = f"{uuid_str}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, uuid_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        filename=file.filename,
        file_path=file_path,
        processing_status=DocumentStatus.PENDING,
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    print(f"Doc info: {doc}")
    print(f"Doc_id: {doc.id}")
    asyncio.create_task(
        service.upload_document(doc.id, file_path)
    )

    return {
        "message": "Upload received",
        "document_id": doc.id,
        "status": doc.processing_status,
    }

@router.post("/get_vector")
async def get_vector(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Run similarity search across all documents using the query string.
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        results = await service.find_vector(query, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    response = [
        {
            "document_id": r["document_id"],
            "file_path": r.get("document_path"),
            "page_number": r["page_number"],
            "content": r["content"],
            "score": r["score"],
        }
        for r in results
    ]
    return response


@router.post("/analyze")
async def analyze(req: AnalyzeRequest,
            api_key: str = Depends(require_api_key),
            db: Session = Depends(get_db)):
    # Generate session_id if not provided
    session_id = req.session_id or str(uuid.uuid4())
    # Save chat history
    chat_service = ChatHistoryService(db)
    user_id = api_key.get("id")
    history_context = None

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
        message=req.user_input,
        type="knowledge_base",
    )

    result = await run_knowledge_pipeline(
        user_input=req.user_input,
        history=history_context
    )
    if result["status"] == "error":
        log_entry = {
            "status": "error",
            "date": result["date"],
            "user_input": req.user_input,
            "references": result["references"],
            "output": result["output"],
            "session_id": session_id
        }
        await chat_service.create_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            message=result["output"],
            references=result["references"],
            type="knowledge_base",

        )
        return log_entry

    log_entry = {
        "status": "success",
        "date": result["date"],
        "user_input": req.user_input,
        "references": result["references"],
        "output": result["output"],
        "session_id": session_id
    }

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        message=result["output"],
        references=result["references"],
        type="knowledge_base"
    )

    return log_entry


@router.post("/analyze-en")
async def analyze_en(req: AnalyzeRequest,
            api_key: str = Depends(require_api_key),
            db: Session = Depends(get_db)):
    # Generate session_id if not provided
    session_id = req.session_id or str(uuid.uuid4())
    # Save chat history
    chat_service = ChatHistoryService(db)
    user_id = api_key.get("id")
    history_context = None

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
        message=req.user_input,
        type="knowledge_base",
        lang='en'
    )

    result = await run_knowledge_pipeline_en(
        user_input=req.user_input,
        history=history_context
    )
    if result["status"] == "error":
        log_entry = {
            "status": "error",
            "date": result["date"],
            "user_input": req.user_input,
            "references": result["references"],
            "output": result["output"],
            "session_id": session_id
        }
        await chat_service.create_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            message=result["output"],
            references=result["references"],
            type="knowledge_base",
            lang = 'en'
        )
        return log_entry

    log_entry = {
        "status": "success",
        "date": result["date"],
        "user_input": req.user_input,
        "references": result["references"],
        "output": result["output"],
        "session_id": session_id
    }

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        message=result["output"],
        references=result["references"],
        type="knowledge_base",
        lang='en'
    )

    return log_entry

@router.get("/documents")
async def list_documents(page: int = 1, limit: int = 10):
    try:
        result = await service.list_documents(page, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}")
async def document_details(document_id: int):
    result = await service.get_document_details(document_id)

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    doc, chunks = result

    return {
        "document": {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "status": doc.processing_status,
            "total_pages": doc.total_pages,
        },
        "chunks": [
            {
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "embedding_id": c.id,
            }
            for c in chunks
        ]
    }

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, api_key: str = Depends(require_api_key)):
    deleted = await service.delete_document(document_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return