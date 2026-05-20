import os
import asyncio
from typing import List, Dict, Any
from sqlalchemy import create_engine, select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from core.config import settings
from db.session import sync_engine, async_engine
from models.document import Base, Document, DocumentChunk, DocumentStatus
from services.vector_store import VectorStore
from utils.docx_extractor import extract_docx_chunks, convert_doc_to_docx, extract_doc_text_fallback
from utils.pdf_extractor import extract_pdf_chunks

class KnowledgeDocumentsService:
    def __init__(self):
        self.SessionLocal = async_sessionmaker(
            bind=async_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def _set_status(self, document_id: int, status: DocumentStatus, total_pages: int = None):
        async with self.SessionLocal() as db:
            doc = await db.get(Document, document_id)
            doc.processing_status = status
            if total_pages is not None:
                doc.total_pages = total_pages
            await db.commit()

    async def upload_document(self, document_id: int, file_path: str):
        print(f"Uploading {file_path} with id {document_id}")
        file_ext = os.path.splitext(file_path)[1].lower()
        try:
            await self._set_status(document_id, DocumentStatus.PROCESSING)

            if file_ext == ".pdf":
                chunks = extract_pdf_chunks(file_path)
            elif file_ext == ".docx":
                chunks = extract_docx_chunks(file_path)
            elif file_ext == ".doc":
                try:
                    docx_path = await convert_doc_to_docx(file_path)
                    chunks = extract_docx_chunks(docx_path)
                except Exception:
                    text = extract_doc_text_fallback(file_path)
                    chunks = [(text[i:i + 500], i // 500 + 1) for i in range(0, len(text), 500)]
            else:
                raise ValueError("Unsupported file type")

            for idx, (text, page_num) in enumerate(chunks):
                async with self.SessionLocal() as db:
                    store = VectorStore(db)
                    print(f"Trying chunk {idx} of {len(chunks)}")
                    await store.store_chunk(text, document_id, page_num, idx)

            await self._set_status(document_id, DocumentStatus.COMPLETED, len(set(p for _, p in chunks)))

        except Exception as e:
            print(f"[upload_document] failed for doc {document_id}: {e}")
            await self._set_status(document_id, DocumentStatus.FAILED)

    async def find_vector(self, query: str, top_k: int = 10):
        async with self.SessionLocal() as db:
            store = VectorStore(db)
            return await store.similarity_search(query, None, top_k)

    async def list_documents(self, page: int, limit: int):
        offset = (page - 1) * limit

        async with self.SessionLocal() as db:
            total = await db.scalar(select(func.count(Document.id)))

            # Items
            result = await db.execute(
                select(Document)
                .order_by(Document.id.desc())
                .offset(offset)
                .limit(limit)
            )
            items = result.scalars().all()

        return {
            "items": [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "file_path": d.file_path,
                    "processing_status": d.processing_status,
                    "total_pages": d.total_pages,
                }
                for d in items
            ],
            "total": total,
            "page": page,
            "limit": limit
        }

    async def get_document_details(self, document_id: int):
        async with self.SessionLocal() as db:
            doc = await db.get(Document, document_id)
            if not doc:
                return None

            result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
            )

            chunks = result.scalars().all()
            return doc, chunks

    async def delete_document(self, document_id: int, delete_file: bool = True) -> bool:
        async with self.SessionLocal() as db:
            doc = await db.get(Document, document_id)
            if not doc:
                return False

            file_path = doc.file_path

            store = VectorStore(db)
            await store.delete_by_document(document_id)

            await db.delete(doc)
            await db.commit()

        if delete_file and file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        return True

    def upload_document_sync(self, document_id: int, file_path: str):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self.upload_document(document_id, file_path))
        else:
            asyncio.run(self.upload_document(document_id, file_path))
