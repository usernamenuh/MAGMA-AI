import os
import asyncio
import re
import httpx
from time import perf_counter
from datetime import datetime
from typing import List, Dict, Any
from rapidfuzz.fuzz import ratio
from sqlalchemy import create_engine, select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from core.config import settings
from db.session import sync_engine, async_engine
from models.document import Base, Document, DocumentChunk, DocumentStatus
from services.vector_store import VectorStore
from utils.docling_extractor import DocumentExtractionError, audit_chunks, extract_chunks_with_audit, readable_pdf_path


def audit_saved_text(file_path: str, chunks: list[tuple[str, int]]) -> dict:
    with readable_pdf_path(file_path) as pdf_path:
        return audit_chunks(str(pdf_path), chunks)


SEARCH_STOPWORDS = {
    "apa", "coba", "dan", "dari", "di", "dia", "dokumen", "file", "ini", "isi",
    "jelaskan", "lanjutan", "mengenai", "pertanyaan", "saat", "tentang", "tolong", "yang", "the", "please",
    "explain", "document", "content",
}

ENTITY_QUERY_STOPWORDS = SEARCH_STOPWORDS | {
    "adalah", "anda", "apakah", "asal", "bagaimana", "bekerja", "berapa",
    "bernama", "dimana", "kamu", "kenal", "mana", "mengenal", "orang",
    "kuliah", "laki", "perempuan", "pendidikan", "punya", "riwayat", "saya",
    "sekolah", "si", "sih", "siapa", "tahu", "where", "who", "isinya",
    "bikin", "buat", "membuat", "proyek", "tugas",
}


def _normalize_entity_text(text: str) -> str:
    text = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", text or "")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _extract_entity_candidates(contents: list[str]) -> list[str]:
    """Extract reusable proper-name candidates without hard-coding a document."""
    candidates: dict[str, str] = {}
    pattern = re.compile(
        r"\b[A-Z][a-z]{2,}(?:[ '-][A-Z][a-z]{2,}){1,3}\b"
    )
    for content in contents:
        prepared = re.sub(
            r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", content or ""
        )
        for match in pattern.finditer(prepared):
            candidate = re.sub(r"\s+", " ", match.group(0)).strip()
            normalized = _normalize_entity_text(candidate)
            words = normalized.split()
            if len(words) < 2 or all(word in ENTITY_QUERY_STOPWORDS for word in words):
                continue
            candidates.setdefault(normalized, candidate)
    return list(candidates.values())


def _resolve_entity_from_candidates(query: str, candidates: list[str]) -> dict | None:
    """Resolve partial/misspelled entities, returning ambiguity instead of guessing."""
    query_tokens = [
        token for token in _normalize_entity_text(query).split()
        if len(token) >= 3 and token not in ENTITY_QUERY_STOPWORDS
    ]
    if not query_tokens:
        return None

    ranked = []
    for candidate in candidates:
        candidate_tokens = _normalize_entity_text(candidate).split()
        matched_scores = []
        exact_matches = 0
        prefix_matches = 0
        for query_token in query_tokens:
            if query_token in candidate_tokens:
                exact_matches += 1
                matched_scores.append(100)
                continue
            if len(query_token) >= 4 and any(
                candidate_token.startswith(query_token) for candidate_token in candidate_tokens
            ):
                prefix_matches += 1
                matched_scores.append(96)
                continue
            best_similarity = max(
                ratio(query_token, candidate_token) for candidate_token in candidate_tokens
            )
            if best_similarity >= 80:
                matched_scores.append(best_similarity)

        # Unrelated conversational words do not lower the entity score. A
        # single token is accepted only when it is exact, a meaningful prefix
        # a meaningful prefix, or a strong typo match.
        if not matched_scores:
            continue
        score = (
            sum(matched_scores) / len(matched_scores)
            + exact_matches * 6
            + prefix_matches * 4
            + min(len(matched_scores), 2) * 2
        )
        ranked.append((score, candidate))

    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[0], len(item[1]), item[1]))
    best_score, best = ranked[0]
    if best_score < 78:
        return None

    alternatives = []
    best_tokens = set(_normalize_entity_text(best).split())
    for score, candidate in ranked[1:]:
        candidate_tokens = set(_normalize_entity_text(candidate).split())
        if score < best_score - 5 or candidate_tokens <= best_tokens or best_tokens <= candidate_tokens:
            continue
        alternatives.append(candidate)
        if len(alternatives) == 2:
            break

    if alternatives:
        return {"status": "ambiguous", "candidates": [best, *alternatives]}
    return {"status": "resolved", "entity": best, "score": best_score}


def _resolve_document_from_candidates(query: str, documents: list[tuple[int, str]]) -> dict | None:
    """Resolve abbreviated titles/names against filenames without domain-specific aliases."""
    query_tokens = [
        token for token in _normalize_entity_text(query).split()
        if len(token) >= 3 and token not in ENTITY_QUERY_STOPWORDS
    ]
    if not query_tokens:
        return None

    ranked = []
    for document_id, filename in documents:
        stem = os.path.splitext(os.path.basename(filename))[0]
        filename_tokens = _normalize_entity_text(stem).split()
        scores = []
        for query_token in query_tokens:
            if query_token in filename_tokens:
                scores.append(100)
            elif len(query_token) >= 3 and any(
                token.startswith(query_token) for token in filename_tokens
            ):
                scores.append(96)
            else:
                similarity = max(
                    (ratio(query_token, token) for token in filename_tokens),
                    default=0,
                )
                if similarity >= 84:
                    scores.append(similarity)
        if scores:
            ranked.append((sum(scores) / len(scores) + min(len(scores), 3) * 3, document_id, filename))

    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[0], len(item[2]), item[2]))
    best_score, best_id, best_filename = ranked[0]
    close = [item for item in ranked[1:] if item[0] >= best_score - 2]
    if close:
        choices = [{"id": best_id, "filename": best_filename}]
        choices.extend({"id": item[1], "filename": item[2]} for item in close[:2])
        return {"status": "ambiguous", "candidates": choices}
    return {
        "status": "resolved",
        "document_id": best_id,
        "filename": best_filename,
        "score": best_score,
    }

# CPU-only deployments must not run multiple OCR/Docling jobs concurrently.
_document_processing_semaphore = asyncio.Semaphore(1)


def _search_terms(text: str) -> set[str]:
    # Split CamelCase filenames (CvPDFDigital -> Cv PDF Digital) before tokenizing.
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text or "").lower()
    return {
        token for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) >= 2 and token not in SEARCH_STOPWORDS
    }


def _is_abstract_section(content: str) -> bool:
    """Recognize an abstract heading, not ordinary words such as 'objek abstrak'."""
    return bool(re.search(r"\b(?:ABSTRAK|ABSTRACT)\b", content or ""))


def _rerank_search_results(query: str, rows: list[dict], limit: int = 4) -> list[dict]:
    """Combine semantic similarity with lexical evidence and drop weak matches."""
    if not rows:
        return []

    query_terms = _search_terms(query)
    overview_query = bool(re.search(
        r"\b(tentang apa|isinya|bikin apa|buat apa|proyek apa|jelaskan|ringkas(?:an)?|topik|membahas apa|overview|summary)\b",
        query,
        re.IGNORECASE,
    ))
    for row in rows:
        filename = row.get("filename") or os.path.basename(row["document_path"])
        searchable = f"{filename} {row['content']}"
        terms = _search_terms(searchable)
        lexical = len(query_terms & terms) / max(len(query_terms), 1)
        filename_terms = _search_terms(filename)
        filename_match = bool(query_terms & filename_terms)
        row["lexical_score"] = lexical
        row["filename_match"] = filename_match
        row["relevance_score"] = (
            (0.30 * row["score"])
            + (0.45 * lexical)
            + (0.25 if filename_match else 0.0)
        )
        if overview_query:
            content_lower = row["content"].lower()
            # Prefer summary sections over boilerplate pages.
            if _is_abstract_section(row["content"]):
                row["relevance_score"] += 0.80
                row["overview_section"] = True
            elif any(marker in content_lower for marker in ("tujuan penelitian", "kesimpulan", "latar belakang")):
                row["relevance_score"] += 0.35
                row["overview_section"] = True
            else:
                row["overview_section"] = False

            if any(marker in content_lower for marker in (
                "lembar pernyataan", "lembar pengesahan", "lembar persetujuan",
                "hak atas kekayaan intelektual", "daftar isi",
            )):
                row["relevance_score"] -= 0.60
                row["overview_section"] = False

    filename_matches = [row for row in rows if row["filename_match"]]
    strongest_lexical = max(row["lexical_score"] for row in rows)
    if filename_matches:
        # When the user explicitly names a document (for example "CV" or
        # "Merapi"), do not mix similarly worded chunks from other files.
        filtered = filename_matches
    elif strongest_lexical > 0:
        # Keep candidates carrying at least half of the best lexical evidence.
        minimum_lexical = max(0.10, strongest_lexical * 0.50)
        filtered = [row for row in rows if row["lexical_score"] >= minimum_lexical]
    else:
        # Synonym-only queries fall back to scores close to the best vector match.
        best_semantic = max(row["score"] for row in rows)
        minimum_semantic = max(0.20, best_semantic * 0.75)
        filtered = [row for row in rows if row["score"] >= minimum_semantic]

    filtered.sort(key=lambda row: row["relevance_score"], reverse=True)
    if overview_query and filtered:
        overview_rows = [row for row in filtered if row.get("overview_section")]
        if overview_rows:
            overview_rows.sort(key=lambda row: row["relevance_score"], reverse=True)
            # Duplicate uploads of the same thesis must not be mixed into one
            # answer. Use the document containing the strongest overview chunk.
            best_document_id = overview_rows[0]["document_id"]
            same_document = [row for row in overview_rows if row["document_id"] == best_document_id]
            abstract_rows = [
                row for row in same_document
                if _is_abstract_section(row["content"])
            ]
            title_rows = [
                row for row in same_document
                if (row.get("page_number") or 999) <= 2 and row not in abstract_rows
            ]
            filtered = (abstract_rows + title_rows) if abstract_rows else same_document
    return filtered[:limit]


class KnowledgeDocumentsService:
    def __init__(self):
        self.SessionLocal = async_sessionmaker(
            bind=async_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def _set_status(
        self,
        document_id: int,
        status: DocumentStatus,
        total_pages: int = None,
        extraction_duration_seconds: float = None,
        processing_message: str = None,
        extraction_audit: dict = None,
    ):
        async with self.SessionLocal() as db:
            doc = await db.get(Document, document_id)
            if doc is None:
                return False
            doc.processing_status = status
            if total_pages is not None:
                doc.total_pages = total_pages
            if extraction_duration_seconds is not None:
                doc.extraction_duration_seconds = extraction_duration_seconds
            if status in (DocumentStatus.COMPLETED, DocumentStatus.INCOMPLETE, DocumentStatus.FAILED) and doc.upload_date:
                doc.processing_duration_seconds = max(
                    0.0,
                    (datetime.utcnow() - doc.upload_date).total_seconds(),
                )
            if processing_message is not None:
                doc.processing_message = processing_message
                doc.error_message = processing_message if status == DocumentStatus.FAILED else None
            if extraction_audit is not None:
                doc.extraction_attempts = extraction_audit.get("attempts", 0)
                doc.extraction_coverage_percent = extraction_audit.get("coverage_percent")
                doc.important_text_total = extraction_audit.get("important_text_total", 0)
                doc.important_text_missing = extraction_audit.get("important_text_missing", 0)
                doc.extraction_audit_status = extraction_audit.get("status")
                doc.missing_important_text = extraction_audit.get("missing_texts", [])
            await db.commit()
            return True

    async def send_pending_whatsapp_notifications(self):
        """Notify the uploader after a WhatsApp document reaches a terminal state."""
        evolution_url = os.getenv("EVOLUTION_INTERNAL_URL", "http://evolution-api:8080").rstrip("/")
        evolution_key = os.getenv("EVOLUTION_API_KEY")
        evolution_instance = os.getenv("EVOLUTION_INSTANCE", "esdm-assistant")
        if not evolution_key:
            return

        async with self.SessionLocal() as db:
            result = await db.execute(
                select(Document)
                .where(
                    Document.whatsapp_session_id.is_not(None),
                    Document.whatsapp_notification_sent.is_(False),
                    Document.processing_status.in_((DocumentStatus.COMPLETED, DocumentStatus.INCOMPLETE, DocumentStatus.FAILED)),
                )
                .order_by(Document.id.asc())
                .limit(10)
            )
            documents = result.scalars().all()

            async with httpx.AsyncClient(timeout=15) as client:
                for doc in documents:
                    number = doc.whatsapp_session_id.removeprefix("whatsapp-")
                    if "@g.us" in number:
                        continue
                    if doc.processing_status in (DocumentStatus.COMPLETED, DocumentStatus.INCOMPLETE):
                        chunk_count = await db.scalar(
                            select(func.count(DocumentChunk.id)).where(
                                DocumentChunk.document_id == doc.id
                            )
                        )
                        coverage = doc.extraction_coverage_percent
                        coverage_text = f"{coverage:.2f}%" if coverage is not None else "-"
                        message = (
                            f"Dokumen {doc.filename} sudah memiliki chunk tersimpan"
                            f"{' tetapi masih kurang lengkap' if doc.processing_status == DocumentStatus.INCOMPLETE else ' dan siap digunakan'}.\n\n"
                            f"- Status: {doc.processing_status}\n"
                            f"- Total halaman: {doc.total_pages or 0}\n"
                            f"- Jumlah chunk: {chunk_count or 0}\n"
                            f"- Kelengkapan ekstraksi: {coverage_text}\n"
                            f"- Teks penting tertinggal: {doc.important_text_missing or 0}"
                        )
                    else:
                        message = (
                            f"Dokumen {doc.filename} gagal diproses. "
                            "Silakan periksa file lalu kirim ulang."
                        )

                    try:
                        response = await client.post(
                            f"{evolution_url}/message/sendText/{evolution_instance}",
                            headers={"apikey": evolution_key},
                            json={"number": number, "text": message},
                        )
                        response.raise_for_status()
                    except httpx.HTTPError as exc:
                        import logging
                        logging.getLogger(__name__).warning(
                            "Failed sending WhatsApp completion for document %s: %s",
                            doc.id,
                            exc,
                        )
                        continue

                    doc.whatsapp_notification_sent = True
                    await db.commit()

    async def upload_document(self, document_id: int, file_path: str, extraction_mode: str = "auto"):
        queued = await self._set_status(
            document_id,
            DocumentStatus.QUEUED,
            processing_message="Waiting for document processing",
        )
        if not queued:
            return

        async with _document_processing_semaphore:
            exists = await self._set_status(
                document_id,
                DocumentStatus.PROCESSING,
                processing_message="Document processing started",
            )
            if not exists:
                return
            await self._process_document(document_id, file_path, extraction_mode)

    async def process_claimed_document(
        self,
        document_id: int,
        file_path: str,
        extraction_mode: str = "auto",
    ):
        """Process a database job already claimed by the dedicated worker."""
        async with _document_processing_semaphore:
            await self._process_document(document_id, file_path, extraction_mode)

    async def _process_document(self, document_id: int, file_path: str, extraction_mode: str = "auto"):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Uploading %s with id %d", file_path, document_id)
        file_ext = os.path.splitext(file_path)[1].lower()
        extraction_started_at = None
        async with self.SessionLocal() as db:
            previous_chunk_count = await db.scalar(
                select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
            ) or 0
            previous_audit_status = await db.scalar(
                select(Document.extraction_audit_status).where(Document.id == document_id)
            )
        try:
            if file_ext not in (".pdf", ".docx", ".doc"):
                raise ValueError(f"Unsupported file type: {file_ext}")

            extraction_started_at = perf_counter()
            extraction_metadata = {}
            chunks = await asyncio.to_thread(
                extract_chunks_with_audit,
                file_path,
                max_tokens=512,
                tokenizer="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                extraction_mode=extraction_mode,
                extraction_metadata=extraction_metadata,
            )
            if not chunks:
                raise DocumentExtractionError("Tidak ada teks yang berhasil diekstraksi")
            extraction_duration_seconds = perf_counter() - extraction_started_at
            await self._set_status(
                document_id,
                DocumentStatus.PROCESSING,
                extraction_duration_seconds=extraction_duration_seconds,
            )

            embedding_started_at = perf_counter()
            async with self.SessionLocal() as db:
                store = VectorStore(db)
                # Replace old chunks in the same transaction as the insert.
                # Failed extraction/embedding must not erase a prior result.
                await store.delete_by_document(document_id)
                stored_count = await store.store_chunks(chunks, document_id)
            logger.info(
                "Embedded and stored %d chunks for document %d in %.3f seconds",
                stored_count,
                document_id,
                perf_counter() - embedding_started_at,
            )

            method = extraction_metadata.get("method")
            success_message = (
                "Successfully processed using OCR"
                if method == "ocr"
                else "Extraction completed successfully"
            )
            if extraction_metadata.get("status") == "OCR_REVIEW_REQUIRED":
                success_message += "; OCR result requires manual review"
            elif extraction_metadata.get("important_text_missing", 0):
                success_message += f"; {extraction_metadata['important_text_missing']} important text sections may be missing"
            final_status = (
                DocumentStatus.INCOMPLETE
                if extraction_metadata.get("status") != "COMPLETE"
                else DocumentStatus.COMPLETED
            )
            await self._set_status(
                document_id,
                final_status,
                extraction_metadata.get("total_pages") or len(set(p for _, p in chunks)),
                processing_message=success_message,
                extraction_audit=extraction_metadata,
            )

        except Exception as e:
            print(f"[upload_document] failed for doc {document_id}: {e}")
            duration = perf_counter() - extraction_started_at if extraction_started_at else None
            message = str(e) if isinstance(e, DocumentExtractionError) else "Document processing failed"
            await self._set_status(
                document_id,
                (DocumentStatus.COMPLETED if previous_audit_status == "COMPLETE" else DocumentStatus.INCOMPLETE)
                if previous_chunk_count else DocumentStatus.FAILED,
                extraction_duration_seconds=duration,
                processing_message=(
                    "Ekstraksi ulang gagal; chunk sebelumnya tetap digunakan"
                    if previous_chunk_count else message
                ),
            )

    async def find_vector(
        self,
        query: str,
        top_k: int = 10,
        document_ids: list[int] = None,
        entity_hint: str = None,
    ):
        async with self.SessionLocal() as db:
            store = VectorStore(db)
            # Reranking can only recover a strong lexical match when that
            # document is present in the semantic candidate set.  A small
            # initial limit is easily dominated by duplicate documents that
            # happen to mention the same person or subject, so retrieve a
            # wider (still bounded) pool before applying the hybrid score.
            overview_query = bool(re.search(
                r"\b(tentang apa|isinya|bikin apa|buat apa|proyek apa|jelaskan|ringkas(?:an)?|topik|membahas apa|overview|summary)\b",
                query,
                re.IGNORECASE,
            ))
            candidate_k = max(top_k * 5, 200 if overview_query else 50)
            rows = await store.similarity_search(
                query,
                None,
                candidate_k,
                document_ids=document_ids,
            )
            if entity_hint:
                # A short document can be absent from the semantic candidate
                # pool when larger documents dominate it. Always merge chunks
                # that literally contain the safely resolved entity.
                statement = select(DocumentChunk, Document).join(
                    Document, Document.id == DocumentChunk.document_id
                ).where(
                    Document.processing_status.in_((DocumentStatus.COMPLETED, DocumentStatus.INCOMPLETE)),
                    DocumentChunk.content.contains(entity_hint, autoescape=True),
                )
                if document_ids:
                    statement = statement.where(DocumentChunk.document_id.in_(document_ids))
                exact_result = await db.execute(statement.limit(20))
                known_ids = {row["id"] for row in rows}
                for chunk, document in exact_result.all():
                    if chunk.id in known_ids:
                        continue
                    rows.append({
                        "id": chunk.id,
                        "document_id": chunk.document_id,
                        "filename": document.filename,
                        "document_path": document.file_path,
                        "content": chunk.content,
                        "page_number": chunk.page_number,
                        "chunk_metadata": chunk.chunk_metadata,
                        "score": 1.0,
                    })
                literal_entity_rows = [
                    row for row in rows
                    if entity_hint.lower() in row["content"].lower()
                ]
                if literal_entity_rows:
                    rows = literal_entity_rows
            return _rerank_search_results(query, rows, limit=min(top_k, 4))

    async def resolve_query_entity(
        self,
        query: str,
        document_ids: list[int] = None,
    ) -> dict | None:
        """Resolve a name/term against entities extracted from selected documents."""
        async with self.SessionLocal() as db:
            statement = select(DocumentChunk.content).join(
                Document, Document.id == DocumentChunk.document_id
            ).where(Document.processing_status.in_((DocumentStatus.COMPLETED, DocumentStatus.INCOMPLETE)))
            if document_ids:
                statement = statement.where(DocumentChunk.document_id.in_(document_ids))
            result = await db.execute(statement)
            candidates = _extract_entity_candidates(list(result.scalars()))
        return _resolve_entity_from_candidates(query, candidates)

    async def resolve_query_document(
        self,
        query: str,
        document_ids: list[int] = None,
    ) -> dict | None:
        """Resolve an abbreviated user phrase against completed document filenames."""
        async with self.SessionLocal() as db:
            statement = select(Document.id, Document.filename).where(
                Document.processing_status.in_((DocumentStatus.COMPLETED, DocumentStatus.INCOMPLETE))
            )
            if document_ids:
                statement = statement.where(Document.id.in_(document_ids))
            result = await db.execute(statement)
            documents = [(row.id, row.filename) for row in result.all()]
        return _resolve_document_from_candidates(query, documents)

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
                    "extraction_duration_seconds": d.extraction_duration_seconds,
                    "processing_duration_seconds": d.processing_duration_seconds,
                    "processing_message": d.processing_message,
                    "extraction_attempts": d.extraction_attempts,
                    "extraction_coverage_percent": d.extraction_coverage_percent,
                    "important_text_total": d.important_text_total,
                    "important_text_missing": d.important_text_missing,
                    "extraction_audit_status": d.extraction_audit_status,
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

    async def get_document_overview_results(self, document_id: int) -> list[dict]:
        """Return grounded title/background/objective chunks for overview questions."""
        async with self.SessionLocal() as db:
            document = await db.get(Document, document_id)
            if not document:
                return []
            result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
            )
            chunks = result.scalars().all()

        selected = []
        markers = (
            "abstrak", "abstract", "latar belakang", "tujuan penelitian",
            "tujuan dan kegunaan", "kesimpulan",
        )
        for chunk in chunks:
            content_lower = (chunk.content or "").lower()
            if (chunk.page_number or 0) == 1 or any(marker in content_lower for marker in markers):
                selected.append({
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "filename": document.filename,
                    "document_path": document.file_path,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "chunk_metadata": chunk.chunk_metadata,
                    "score": 1.0,
                })
            if len(selected) == 4:
                break
        return selected

    async def get_document_section_results(
        self,
        document_id: int,
        section: str,
    ) -> list[dict]:
        """Select chunks belonging to a requested logical document section."""
        async with self.SessionLocal() as db:
            document = await db.get(Document, document_id)
            if not document:
                return []
            result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
            )
            chunks = result.scalars().all()

        patterns = {
            "methodology": (
                r"metodologi penelitian", r"metodologi penyelesaian", r"pendekatan penelitian",
                r"desain penelitian", r"teknik pengumpulan data", r"teknik analisis data",
            ),
            "objective": (r"tujuan penelitian", r"tujuan dan kegunaan penelitian"),
            "conclusion": (r"(?:^|\n)\s*(?:bab\s+[ivxlcdm]+\s+)?kesimpulan\b",),
        }
        section_patterns = patterns.get(section, ())
        selected = []
        for chunk in chunks:
            content = chunk.content or ""
            if not any(re.search(pattern, content, re.IGNORECASE) for pattern in section_patterns):
                continue
            # Skip table-of-contents entries dominated by dotted leaders.
            if content.count(".") > 35 and "daftar isi" in content.lower():
                continue
            selected.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "filename": document.filename,
                "document_path": document.file_path,
                "content": content,
                "page_number": chunk.page_number,
                "chunk_metadata": chunk.chunk_metadata,
                "score": 1.0,
            })
            if len(selected) == 4:
                break
        return selected

    async def retry_document(self, document_id: int, extraction_mode: str = "auto") -> str:
        async with self.SessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == document_id).with_for_update()
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return "not_found"
            if doc.processing_status not in (DocumentStatus.FAILED, DocumentStatus.COMPLETED, DocumentStatus.INCOMPLETE):
                return "invalid_status"
            if not doc.file_path or not os.path.exists(doc.file_path):
                return "file_missing"

            doc.processing_status = DocumentStatus.QUEUED
            doc.extraction_mode = extraction_mode
            doc.processing_message = "Menunggu ekstraksi ulang"
            doc.error_message = None
            doc.extraction_duration_seconds = None
            doc.processing_duration_seconds = None
            doc.upload_date = datetime.utcnow()
            await db.commit()
            return "queued"

    async def add_manual_text(self, document_id: int, content: str, page_number: int) -> str:
        content = content.replace("\x00", "").strip()
        if not content or len(content) > 10000 or page_number < 1:
            return "invalid_text"
        async with self.SessionLocal() as db:
            doc = await db.get(Document, document_id)
            if not doc:
                return "not_found"
            if doc.processing_status not in (DocumentStatus.INCOMPLETE, DocumentStatus.COMPLETED):
                return "invalid_status"
            if doc.total_pages and page_number > doc.total_pages:
                return "invalid_page"
            existing = await db.scalar(
                select(DocumentChunk.id).where(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.page_number == page_number,
                    DocumentChunk.content == content,
                ).limit(1)
            )
            if existing:
                return "duplicate"
            next_index = await db.scalar(
                select(func.max(DocumentChunk.chunk_index)).where(DocumentChunk.document_id == document_id)
            )
            result = await db.execute(
                select(DocumentChunk.content, DocumentChunk.page_number)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
            )
            chunks = [(row.content, row.page_number) for row in result.all()]
            chunks.append((content, page_number))
            audit = await asyncio.to_thread(audit_saved_text, doc.file_path, chunks)
            store = VectorStore(db)
            await store.store_chunk(
                content, document_id, page_number, (next_index or 0) + 1,
                chunk_metadata={"source": "manual"},
            )
            doc.text_chunks_count = len(chunks)
            doc.extraction_coverage_percent = audit.get("coverage_percent")
            doc.important_text_total = audit.get("important_text_total", 0)
            doc.important_text_missing = audit.get("important_text_missing", 0)
            doc.extraction_audit_status = audit.get("status")
            doc.missing_important_text = audit.get("missing_texts", [])
            doc.processing_status = (
                DocumentStatus.COMPLETED if audit.get("status") == "COMPLETE"
                else DocumentStatus.INCOMPLETE
            )
            doc.processing_message = "Teks manual ditambahkan; kelengkapan diperiksa ulang"
            await db.commit()
            return "saved"

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
