import asyncio
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete
from models.document import DocumentChunk, Document
from core.config import settings


class VectorStore:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.fastembed_model = None
        self.embedding_dim = 1536

    async def _ensure_pgvector(self):
        try:
            await self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await self.db.commit()
        except Exception:
            await self.db.rollback()

    async def _init_fastembed(self):
        if self.fastembed_model is None:
            from fastembed import TextEmbedding

            model_name = settings.FASTEMBED_MODEL

            def load_model():
                return TextEmbedding(model_name=model_name)

            # Load model in thread
            self.fastembed_model = await asyncio.to_thread(load_model)

            sample_emb = next(self.fastembed_model.embed(["hello"]))
            self.embedding_dim = len(sample_emb)

    async def generate_embedding(self, text: str) -> np.ndarray:
        await self._init_fastembed()
        emb = next(self.fastembed_model.embed([text]))
        return np.array(emb, dtype=float)

    async def store_chunk(
        self,
        content: str,
        document_id: int,
        page_number: int,
        chunk_index: int,
        chunk_metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentChunk:
        try:

            emb = await self.generate_embedding(content)

            chunk = DocumentChunk(
                document_id=document_id,
                page_number=page_number,
                chunk_index=chunk_index,
                content=content,
                chunk_metadata=chunk_metadata or {},
                embedding=emb.tolist(),
            )

            self.db.add(chunk)
            await self.db.commit()
            await self.db.refresh(chunk)

            return chunk
        except Exception as e:
            await self.db.rollback()
            print("STORE CHUNK FAILED:", str(e))
            raise


    async def similarity_search(self, query: str, document_id: Optional[int], k: int = 5):
        query_emb = await self.generate_embedding(query)
        query_str = "[" + ",".join(str(x) for x in query_emb.tolist()) + "]"

        sql = """
        SELECT
            c.id,
            c.document_id,
            d.filename,
            d.file_path,
            c.content,
            c.page_number,
            c.chunk_metadata,
            (1 - (c.embedding <=> (:query_embedding)::vector)) AS similarity
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        """

        params = {"query_embedding": query_str, "k": k}

        if document_id:
            sql += " WHERE c.document_id = :document_id"
            params["document_id"] = document_id

        sql += " ORDER BY c.embedding <=> (:query_embedding)::vector LIMIT :k"

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "id": r.id,
                "document_id": r.document_id,
                "document_path": r.file_path,
                "content": r.content,
                "page_number": r.page_number,
                "chunk_metadata": r.chunk_metadata,
                "score": float(r.similarity),
            }
            for r in rows
        ]

    async def delete_by_document(self, document_id: int) -> int:
        result = await self.db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        )
        return result.rowcount or 0
