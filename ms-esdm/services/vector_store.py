import asyncio
import os
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete, insert
from models.document import DocumentChunk, Document
from core.config import settings


_shared_fastembed_model = None
_shared_embedding_dim = None
_model_init_lock = asyncio.Lock()
_embedding_inference_lock = asyncio.Lock()


def _clean_chunk_content(content: str) -> str:
    """PostgreSQL text cannot store NUL bytes emitted by some PDF extractors."""
    return content.replace("\x00", "")


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
        global _shared_fastembed_model, _shared_embedding_dim

        if self.fastembed_model is not None:
            return

        if _shared_fastembed_model is None:
            async with _model_init_lock:
                if _shared_fastembed_model is None:
                    from fastembed import TextEmbedding

                    model_name = settings.FASTEMBED_MODEL

                    def load_model():
                        model = TextEmbedding(model_name=model_name)
                        sample_embedding = next(model.embed(["hello"]))
                        return model, len(sample_embedding)

                    model, embedding_dim = await asyncio.to_thread(load_model)
                    _shared_fastembed_model = model
                    _shared_embedding_dim = embedding_dim

        self.fastembed_model = _shared_fastembed_model
        self.embedding_dim = _shared_embedding_dim

    async def generate_embedding(self, text: str) -> np.ndarray:
        embeddings = await self.generate_embeddings([text], batch_size=1)
        return embeddings[0]

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[np.ndarray]:
        """Generate embeddings in batches without blocking the event loop."""
        if not texts:
            return []

        await self._init_fastembed()
        effective_batch_size = batch_size or int(
            os.getenv("EMBEDDING_BATCH_SIZE", "32")
        )

        def embed_all():
            return [
                np.asarray(embedding, dtype=float)
                for embedding in self.fastembed_model.embed(
                    texts,
                    batch_size=effective_batch_size,
                )
            ]

        async with _embedding_inference_lock:
            embeddings = await asyncio.to_thread(embed_all)
        if len(embeddings) != len(texts):
            raise RuntimeError(
                f"Expected {len(texts)} embeddings, received {len(embeddings)}"
            )
        return embeddings

    async def store_chunks(
        self,
        chunks: List[tuple[str, int]],
        document_id: int,
        batch_size: Optional[int] = None,
    ) -> int:
        """Embed all chunks in batches and persist them in one transaction."""
        if not chunks:
            return 0

        try:
            clean_chunks = [(_clean_chunk_content(content), page) for content, page in chunks]
            contents = [content for content, _ in clean_chunks]
            embeddings = await self.generate_embeddings(contents, batch_size=batch_size)
            rows = [
                {
                    "document_id": document_id,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "content": content,
                    "chunk_metadata": {},
                    "embedding": embedding.tolist(),
                }
                for chunk_index, ((content, page_number), embedding) in enumerate(
                    zip(clean_chunks, embeddings)
                )
            ]

            await self.db.execute(insert(DocumentChunk), rows)
            await self.db.commit()
            return len(rows)
        except Exception:
            await self.db.rollback()
            raise

    async def store_chunk(
        self,
        content: str,
        document_id: int,
        page_number: int,
        chunk_index: int,
        chunk_metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentChunk:
        try:
            content = _clean_chunk_content(content)
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


    async def similarity_search(
        self,
        query: str,
        document_id: Optional[int],
        k: int = 5,
        document_ids: Optional[List[int]] = None,
    ):
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

        if document_ids:
            placeholders = []
            for index, selected_id in enumerate(document_ids):
                key = f"document_id_{index}"
                placeholders.append(f":{key}")
                params[key] = int(selected_id)
            sql += f" WHERE c.document_id IN ({','.join(placeholders)})"
        elif document_id:
            sql += " WHERE c.document_id = :document_id"
            params["document_id"] = document_id

        sql += " ORDER BY c.embedding <=> (:query_embedding)::vector LIMIT :k"

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "id": r.id,
                "document_id": r.document_id,
                "filename": r.filename,
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
