"""One document job per process, allowing the queue worker to cancel it."""

import asyncio
import sys

from services.knowledge_documents_service import KnowledgeDocumentsService


async def main():
    document_id = int(sys.argv[1])
    file_path = sys.argv[2]
    extraction_mode = sys.argv[3]
    await KnowledgeDocumentsService().process_claimed_document(
        document_id, file_path, extraction_mode
    )


if __name__ == "__main__":
    asyncio.run(main())
