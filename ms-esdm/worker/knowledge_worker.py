import asyncio
import logging
import os
import signal
import sys

from sqlalchemy import select, text, update

from db.session import Base, async_session, sync_engine
from models.document import Document, DocumentStatus
from services.knowledge_documents_service import KnowledgeDocumentsService


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("knowledge-worker")

POLL_INTERVAL_SECONDS = float(os.getenv("DOCUMENT_QUEUE_POLL_SECONDS", "2"))
service = KnowledgeDocumentsService()


def ensure_schema():
    """Allow the worker to start independently from the API service."""
    Base.metadata.create_all(bind=sync_engine)
    with sync_engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE documents "
            "ADD COLUMN IF NOT EXISTS extraction_mode VARCHAR DEFAULT 'auto' NOT NULL"
        ))
        connection.execute(text(
            "ALTER TABLE documents "
            "ADD COLUMN IF NOT EXISTS processing_message TEXT"
        ))
        connection.execute(text(
            "ALTER TABLE documents "
            "ADD COLUMN IF NOT EXISTS processing_duration_seconds DOUBLE PRECISION"
        ))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_attempts INTEGER DEFAULT 0"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_coverage_percent DOUBLE PRECISION"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS important_text_total INTEGER DEFAULT 0"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS important_text_missing INTEGER DEFAULT 0"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_audit_status VARCHAR"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS missing_important_text JSON"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS whatsapp_session_id VARCHAR"))
        connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS whatsapp_notification_sent BOOLEAN DEFAULT FALSE NOT NULL"))


async def recover_interrupted_jobs():
    """Return jobs interrupted by a worker restart to the persistent queue."""
    async with async_session() as db:
        await db.execute(
            update(Document)
            .where(Document.processing_status == DocumentStatus.PROCESSING)
            .values(
                processing_status=DocumentStatus.QUEUED,
                processing_message="Requeued after worker restart",
            )
        )
        await db.commit()


async def claim_next_document():
    """Atomically claim the oldest queued document."""
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(
                select(Document)
                .where(Document.processing_status == DocumentStatus.QUEUED)
                .order_by(Document.id.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            document = result.scalar_one_or_none()
            if document is None:
                return None

            document.processing_status = DocumentStatus.PROCESSING
            document.processing_message = "Document processing started"
            document.error_message = None
            return (
                document.id,
                document.file_path,
                document.extraction_mode or "auto",
            )


async def document_exists(document_id: int) -> bool:
    async with async_session() as db:
        return await db.get(Document, document_id) is not None


async def stop_document_process(process):
    # The child has its own process group, including LibreOffice subprocesses.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), timeout=3)
    except asyncio.TimeoutError:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


async def process_document_job(document_id: int, file_path: str, extraction_mode: str):
    """Run extraction separately so deleting a document can stop its CPU work."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "worker.document_job",
        str(document_id),
        file_path,
        extraction_mode,
        start_new_session=True,
    )
    while True:
        try:
            return_code = await asyncio.wait_for(process.wait(), timeout=1)
            if return_code and await document_exists(document_id):
                logger.error("Document job id=%s exited with code %s", document_id, return_code)
                async with async_session() as db:
                    await db.execute(
                        update(Document)
                        .where(
                            Document.id == document_id,
                            Document.processing_status == DocumentStatus.PROCESSING,
                        )
                        .values(
                            processing_status=DocumentStatus.FAILED,
                            processing_message="Document worker stopped unexpectedly",
                        )
                    )
                    await db.commit()
            return
        except asyncio.TimeoutError:
            if not await document_exists(document_id):
                logger.info("Document id=%s deleted; stopping its extraction process", document_id)
                await stop_document_process(process)
                return


async def run_worker():
    await asyncio.to_thread(ensure_schema)
    await recover_interrupted_jobs()
    logger.info("Knowledge worker started; concurrency=1")

    while True:
        job = await claim_next_document()
        if job is None:
            await service.send_pending_whatsapp_notifications()
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        document_id, file_path, extraction_mode = job
        logger.info("Processing document id=%s mode=%s", document_id, extraction_mode)
        await process_document_job(
            document_id,
            file_path,
            extraction_mode,
        )
        await service.send_pending_whatsapp_notifications()


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Knowledge worker stopped")
