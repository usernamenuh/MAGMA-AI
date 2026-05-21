from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_converter = None


def _get_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter
        _converter = DocumentConverter()
    return _converter


def extract_chunks(
    file_path: str,
    max_tokens: int = 512,
    tokenizer: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> list[tuple[str, int]]:
    """
    Extract structured chunks from PDF, DOCX, or DOC.
    Returns list of (chunk_text, page_number).
    Heading context prepended to each chunk for better retrieval.
    """
    from docling.chunking import HybridChunker

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info("Converting document: %s", path.name)
    converter = _get_converter()
    result = converter.convert(str(path))

    chunker = HybridChunker(
        tokenizer=tokenizer,
        max_tokens=max_tokens,
        merge_peers=True,
    )

    chunks: list[tuple[str, int]] = []

    for chunk in chunker.chunk(result.document):
        page = 1
        if chunk.meta.page_numbers:
            page = chunk.meta.page_numbers[0]

        heading_ctx = " > ".join(chunk.meta.headings) if chunk.meta.headings else ""
        caption_ctx = " | ".join(chunk.meta.captions) if chunk.meta.captions else ""

        prefix_parts = [p for p in [heading_ctx, caption_ctx] if p]
        prefix = "\n".join(prefix_parts)

        text = f"{prefix}\n{chunk.text}".strip() if prefix else chunk.text.strip()

        if text:
            chunks.append((text, page))

    logger.info("Extracted %d chunks from %s", len(chunks), path.name)
    return chunks
