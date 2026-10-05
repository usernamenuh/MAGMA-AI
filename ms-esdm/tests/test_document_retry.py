import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from models.document import DocumentStatus
from services.knowledge_documents_service import KnowledgeDocumentsService
from utils.docling_extractor import DocumentExtractionError


class _FakeResult:
    def __init__(self, document):
        self.document = document

    def scalar_one_or_none(self):
        return self.document


class _FakeSession:
    def __init__(self, document=None, chunk_count=0, audit_status=None):
        self.document = document
        self.chunk_count = chunk_count
        self.audit_status = audit_status
        self.scalar_calls = 0
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def execute(self, _):
        return _FakeResult(self.document)

    async def scalar(self, _):
        self.scalar_calls += 1
        return self.chunk_count if self.scalar_calls == 1 else self.audit_status

    async def commit(self):
        self.committed = True


class DocumentRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_document_can_be_queued_without_clearing_metadata(self):
        document = SimpleNamespace(
            processing_status=DocumentStatus.COMPLETED,
            file_path=__file__,
            extraction_mode="auto",
            processing_message="Selesai",
            error_message=None,
            total_pages=4,
            extraction_duration_seconds=3,
            processing_duration_seconds=5,
            upload_date=None,
        )
        session = _FakeSession(document)
        service = KnowledgeDocumentsService()
        service.SessionLocal = lambda: session

        result = await service.retry_document(55, "ocr")

        self.assertEqual(result, "queued")
        self.assertEqual(document.processing_status, DocumentStatus.QUEUED)
        self.assertEqual(document.extraction_mode, "ocr")
        self.assertEqual(document.total_pages, 4)
        self.assertTrue(session.committed)

    async def test_processing_document_cannot_be_queued_again(self):
        document = SimpleNamespace(processing_status=DocumentStatus.PROCESSING)
        session = _FakeSession(document)
        service = KnowledgeDocumentsService()
        service.SessionLocal = lambda: session

        self.assertEqual(await service.retry_document(55), "invalid_status")
        self.assertFalse(session.committed)

    async def test_failed_reprocess_restores_completed_status_when_chunks_exist(self):
        service = KnowledgeDocumentsService()
        service.SessionLocal = lambda: _FakeSession(chunk_count=2, audit_status="COMPLETE")
        service._set_status = AsyncMock()

        with patch(
            "services.knowledge_documents_service.extract_chunks_with_audit",
            side_effect=DocumentExtractionError("gagal membaca"),
        ):
            await service._process_document(55, "example.pdf")

        last_call = service._set_status.await_args_list[-1]
        self.assertEqual(last_call.args[1], DocumentStatus.COMPLETED)
        self.assertIn("chunk sebelumnya", last_call.kwargs["processing_message"])


if __name__ == "__main__":
    unittest.main()
