import asyncio
import json
import uuid
import base64
import binascii
import re
import subprocess
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
import shutil
import os
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette import status

from db.session import get_db, SessionLocal
from models import Document
from models.document import DocumentStatus
from services.auth_service import require_api_key
from services.chat_history_service import ChatHistoryService
from services.knowledge_documents_service import KnowledgeDocumentsService
from pydantic import BaseModel

from services.pipeline_knowledge import run_knowledge_pipeline
from services.pipeline_knowledge_en import run_knowledge_pipeline_en
from services.whatsapp_auth_service import handle_whatsapp_auth, is_whatsapp_authenticated
from utils.pipeline_helpers import reset_chat_model, set_chat_model
from utils.stored_text_audit import audit_stored_document
from utils.annotated_pdf import build_annotated_pdf, count_letters, read_pdf_letter_count
from utils.docling_extractor import DocumentExtractionError, readable_pdf_path

router = APIRouter()

UPLOAD_DIR = "blobs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

service = KnowledgeDocumentsService()


def build_knowledge_history_context(history):
    """Keep recent user topics; assistant answers/errors must not pollute retrieval."""
    user_messages = [
        msg.message.strip()
        for msg in history
        if msg.role == "user" and msg.message and msg.message.strip()
    ]
    # Keep all user turns available in the bounded history (currently 10 rows).
    # Repeated pronoun-only follow-ups must not displace the original subject.
    return "\n".join(user_messages)


class AnalyzeRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    document_ids: Optional[List[int]] = None


class WhatsAppDocumentUploadRequest(BaseModel):
    session_id: str
    filename: str
    mimetype: Optional[str] = None
    base64_data: str


class ManualDocumentTextRequest(BaseModel):
    content: str
    page_number: int


def document_pdf_letter_count(file_path: str) -> int:
    with readable_pdf_path(file_path) as pdf_path:
        return read_pdf_letter_count(str(pdf_path))


def document_annotated_pdf_bytes(file_path: str, chunks: list[tuple[str, int]]):
    with readable_pdf_path(file_path) as pdf_path:
        return build_annotated_pdf(str(pdf_path), chunks)


@router.get("/models")
async def list_chat_models():
    return {
        "items": [
            {"id": "local", "label": "Qwen2.5 1.5B Q4 — Local"},
            {
                "id": "openrouter:openrouter/free",
                "label": "OpenRouter Free — Otomatis",
            },
        ],
        "default": "local",
    }

@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    extraction_mode: str = Form("auto"),
    db: AsyncSession = Depends(get_db),
):
    upload_started_at = datetime.utcnow()
    allowed = (".pdf", ".doc", ".docx")

    if not file.filename.lower().endswith(allowed):
        raise HTTPException(400, "Only PDF and Word files are supported")

    allowed_modes = {"auto", "text", "docling_no_ocr", "ocr"}
    if extraction_mode not in allowed_modes:
        raise HTTPException(400, "Invalid extraction mode")

    uuid_str = str(uuid.uuid4())
    uuid_filename = f"{uuid_str}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, uuid_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        filename=file.filename,
        file_path=file_path,
        processing_status=DocumentStatus.QUEUED,
        processing_message="Waiting for document processing",
        extraction_mode=extraction_mode,
        upload_date=upload_started_at,
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    print(f"Doc info: {doc}")
    print(f"Doc_id: {doc.id}")
    return {
        "message": "Upload received",
        "document_id": doc.id,
        "status": doc.processing_status,
        "extraction_mode": extraction_mode,
    }


@router.post("/upload-whatsapp")
async def upload_whatsapp_document(
    payload: WhatsAppDocumentUploadRequest,
    api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    if not await is_whatsapp_authenticated(db, payload.session_id):
        return {
            "status": "unauthorized",
            "output": "Upload ditolak. Silakan login melalui chat pribadi menggunakan /login.",
        }

    safe_filename = os.path.basename(payload.filename or "dokumen")
    extension = os.path.splitext(safe_filename)[1].lower()
    if extension not in (".pdf", ".doc", ".docx"):
        return {
            "status": "invalid_file",
            "output": "Format dokumen tidak didukung. Kirim file PDF, DOC, atau DOCX.",
        }

    encoded = payload.base64_data
    if encoded.startswith("data:") and "," in encoded:
        encoded = encoded.split(",", 1)[1]
    try:
        file_content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return {
            "status": "invalid_file",
            "output": "Dokumen tidak dapat dibaca. Silakan kirim ulang file tersebut.",
        }

    max_size = 20 * 1024 * 1024
    if not file_content or len(file_content) > max_size:
        return {
            "status": "invalid_file",
            "output": "Ukuran dokumen harus lebih dari 0 byte dan maksimal 20 MB.",
        }

    uuid_filename = f"{uuid.uuid4()}_{safe_filename}"
    file_path = os.path.join(UPLOAD_DIR, uuid_filename)
    with open(file_path, "wb") as destination:
        destination.write(file_content)

    doc = Document(
        filename=safe_filename,
        file_path=file_path,
        processing_status=DocumentStatus.QUEUED,
        processing_message="Waiting for document processing",
        extraction_mode="auto",
        upload_date=datetime.utcnow(),
        whatsapp_session_id=payload.session_id,
        whatsapp_notification_sent=False,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {
        "status": "queued",
        "document_id": doc.id,
        "output": (
            f"Dokumen {safe_filename} telah diterima dan sedang diproses. "
            f"ID dokumen: {doc.id}."
        ),
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
    auth_result = await handle_whatsapp_auth(db, session_id, req.user_input)
    if auth_result:
        return {
            "status": "success",
            "date": datetime.utcnow().isoformat(),
            "user_input": "/auth",
            "references": [],
            "output": auth_result["output"],
            "session_id": session_id,
            "authenticated": auth_result["authenticated"],
        }
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
        history_context = build_knowledge_history_context(history)

    effective_document_ids = req.document_ids
    is_reference_followup = bool(re.search(
        r"\b(itu|tersebut|dokumen ini|tugas itu|yang tadi|sebelumnya)\b",
        req.user_input,
        re.IGNORECASE,
    ))
    if not effective_document_ids and is_reference_followup and history:
        for previous_message in reversed(history):
            if previous_message.role != "assistant" or not previous_message.references:
                continue
            referenced_ids = []
            for reference in previous_message.references:
                if isinstance(reference, dict) and reference.get("document_id") is not None:
                    referenced_ids.append(int(reference["document_id"]))
            if referenced_ids:
                effective_document_ids = list(dict.fromkeys(referenced_ids))
                break

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="user",
        message=req.user_input,
        type="knowledge_base",
        lang="id",
    )

    model_token = set_chat_model(req.model)
    try:
        result = await run_knowledge_pipeline(
            user_input=req.user_input,
            history=history_context,
            document_ids=effective_document_ids,
        )
    finally:
        reset_chat_model(model_token)
    if result["status"] == "error":
        error_msg = result.get("message", "An error occurred processing your request.")
        log_entry = {
            "status": "error",
            "date": datetime.utcnow().isoformat(),
            "user_input": req.user_input,
            "references": [],
            "output": error_msg,
            "session_id": session_id
        }
        await chat_service.create_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            message=error_msg,
            references=[],
            type="knowledge_base",
            lang="id",
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
        lang="id"
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
        history_context = build_knowledge_history_context(history)

    await chat_service.create_message(
        user_id=user_id,
        session_id=session_id,
        role="user",
        message=req.user_input,
        type="knowledge_base",
        lang='en'
    )

    model_token = set_chat_model(req.model)
    try:
        result = await run_knowledge_pipeline_en(
            user_input=req.user_input,
            history=history_context,
            document_ids=req.document_ids,
        )
    finally:
        reset_chat_model(model_token)
    if result["status"] == "error":
        error_msg = result.get("message", "An error occurred processing your request.")
        log_entry = {
            "status": "error",
            "date": datetime.utcnow().isoformat(),
            "user_input": req.user_input,
            "references": [],
            "output": error_msg,
            "session_id": session_id
        }
        await chat_service.create_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            message=error_msg,
            references=[],
            type="knowledge_base",
            lang='en'
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
    source_letters = None
    if doc.filename.lower().endswith((".pdf", ".doc", ".docx")) and chunks:
        try:
            source_letters = await asyncio.to_thread(document_pdf_letter_count, doc.file_path)
        except (FileNotFoundError, ValueError, DocumentExtractionError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired):
            pass

    return {
        "document": {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "status": doc.processing_status,
            "processing_message": doc.processing_message,
            "extraction_mode": doc.extraction_mode,
            "total_pages": doc.total_pages,
            "extraction_attempts": doc.extraction_attempts,
            "extraction_coverage_percent": doc.extraction_coverage_percent,
            "important_text_total": doc.important_text_total,
            "important_text_missing": doc.important_text_missing,
            "extraction_audit_status": doc.extraction_audit_status,
            "missing_important_text": doc.missing_important_text or [],
            "text_counts": {
                "source_letters": source_letters,
                "stored_letters": sum(count_letters(chunk.content or "") for chunk in chunks),
            },
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


@router.get("/documents/{document_id}/text-audit")
async def document_text_audit(document_id: int, _: dict = Depends(require_api_key)):
    result = await service.get_document_details(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    document, chunks = result
    return await asyncio.to_thread(
        audit_stored_document,
        document.file_path,
        [(chunk.content, chunk.page_number) for chunk in chunks],
    )


@router.get("/documents/{document_id}/annotated-pdf")
async def document_annotated_pdf(document_id: int, _: dict = Depends(require_api_key)):
    result = await service.get_document_details(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    document, chunks = result
    if not document.filename.lower().endswith((".pdf", ".doc", ".docx")):
        raise HTTPException(status_code=415, detail="Format dokumen tidak dapat ditampilkan sebagai PDF")
    try:
        pdf_bytes, stats = await asyncio.to_thread(
            document_annotated_pdf_bytes,
            document.file_path,
            [(chunk.content, chunk.page_number) for chunk in chunks],
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File PDF asli tidak ditemukan")
    except (ValueError, DocumentExtractionError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise HTTPException(status_code=422, detail="PDF tidak dapat dibaca atau ditandai")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="dokumen-bertanda.pdf"',
            "Cache-Control": "no-store",
            "X-Matched-Words": str(stats["matched_words"]),
            "X-Total-Words": str(stats["total_words"]),
            "X-PDF-Letters": str(stats["pdf_letters"]),
            "X-Stored-Letters": str(stats["stored_letters"]),
        },
    )

@router.post("/documents/{document_id}/retry")
async def retry_document(
    document_id: int,
    extraction_mode: str = "auto",
    api_key: str = Depends(require_api_key),
):
    if extraction_mode not in {"auto", "text", "docling_no_ocr", "ocr"}:
        raise HTTPException(status_code=400, detail="Mode ekstraksi tidak valid")
    result = await service.retry_document(document_id, extraction_mode)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")
    if result == "invalid_status":
        raise HTTPException(status_code=409, detail="Hanya dokumen selesai, kurang lengkap, atau gagal yang dapat diproses ulang")
    if result == "file_missing":
        raise HTTPException(status_code=409, detail="The original document file is missing")
    return {
        "document_id": document_id,
        "status": DocumentStatus.QUEUED,
        "message": "Document queued for retry",
    }


@router.post("/documents/{document_id}/manual-text")
async def add_manual_document_text(
    document_id: int,
    request: ManualDocumentTextRequest,
    _: dict = Depends(require_api_key),
):
    try:
        result = await service.add_manual_text(document_id, request.content, request.page_number)
    except (DocumentExtractionError, FileNotFoundError, subprocess.TimeoutExpired):
        raise HTTPException(status_code=422, detail="Dokumen sumber belum dapat diperiksa. Teks manual belum disimpan.")
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    if result == "invalid_status":
        raise HTTPException(status_code=409, detail="Tunggu proses dokumen selesai terlebih dahulu")
    if result == "invalid_page":
        raise HTTPException(status_code=400, detail="Nomor halaman melebihi jumlah halaman dokumen")
    if result == "duplicate":
        raise HTTPException(status_code=409, detail="Teks ini sudah ada pada halaman tersebut")
    if result == "invalid_text":
        raise HTTPException(status_code=400, detail="Isi teks atau nomor halaman tidak valid")
    return {"status": "saved", "message": "Teks manual tersimpan dan audit diperbarui"}

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, api_key: str = Depends(require_api_key)):
    deleted = await service.delete_document(document_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return
