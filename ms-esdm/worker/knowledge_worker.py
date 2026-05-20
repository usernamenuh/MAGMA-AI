import asyncio

from db.session import SessionLocal
from models import Document
from models.document import DocumentStatus
from services.knowledge_documents_service import KnowledgeDocumentsService

service = KnowledgeDocumentsService()

def process_document_background(doc_id: int, file_path: str):
    db = SessionLocal()

    try:
        doc = db.get(Document, doc_id)
        if not doc:
            return

        doc.processing_status = DocumentStatus.PROCESSING
        db.commit()

        service.upload_document_sync(doc_id, file_path)

    except Exception as e:
        doc.processing_status = DocumentStatus.FAILED
        doc.error_message = str(e)
        db.commit()

    finally:
        db.close()


