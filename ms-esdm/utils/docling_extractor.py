from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

_converter = None
_converter_no_ocr = None

# A page with only a page number/header should not be considered a usable text
# layer. Requiring most pages to contain text also keeps mixed/scanned PDFs on
# the Docling + OCR path.
MIN_TOTAL_TEXT_CHARS = 100
MIN_TEXT_CHARS_PER_PAGE = 50
MIN_TEXT_PAGE_RATIO = 0.8
MIN_SCAN_IMAGE_COVERAGE = 0.8
MIN_SCAN_PAGE_RATIO = 0.8


class DocumentExtractionError(ValueError):
    """An extraction failure whose message is safe to show in the UI."""


@contextmanager
def readable_pdf_path(file_path: str):
    """Use the original PDF or render Word to a temporary PDF with real pages."""
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        yield path
        return
    if path.suffix.lower() not in {".doc", ".docx"}:
        raise DocumentExtractionError("Format dokumen tidak didukung")
    with tempfile.TemporaryDirectory(prefix="document-preview-") as temp_dir:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", temp_dir, str(path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        converted_path = Path(temp_dir) / f"{path.stem}.pdf"
        if result.returncode != 0 or not converted_path.exists():
            detail = (result.stderr or result.stdout or "unknown conversion error").strip()
            raise DocumentExtractionError(f"The Word document could not be rendered: {detail}")
        yield converted_path


def _normalize_audit_text(text: str) -> str:
    return " ".join(re.findall(r"[\w@.+/%-]+", (text or "").casefold()))


def _is_important_segment(text: str) -> bool:
    normalized = text.strip()
    if len(_normalize_audit_text(normalized)) < 8 or normalized.isdigit():
        return False
    return (
        len(normalized) >= 20
        or ":" in normalized
        or bool(re.search(r"\d|@|%|\b(?:tanggal|nomor|nama|alamat|pendidikan|pengalaman)\b", normalized, re.I))
        or (len(normalized) >= 8 and normalized == normalized.upper())
    )


def _source_segments(path: Path) -> tuple[list[tuple[str, int]], bool]:
    """Return independently readable source text and whether it can be audited."""
    suffix = path.suffix.lower()
    page_texts: list[tuple[str, int]] = []
    try:
        if suffix == ".pdf":
            # Poppler is independent of the PDFium extraction path. Auditing
            # against the same parser can silently certify dropped text.
            result = subprocess.run(
                ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            pages = result.stdout.split("\f")
            if pages and not pages[-1].strip():
                pages.pop()
            page_texts = [(text, index) for index, text in enumerate(pages, 1)]
            usable_pages = sum(
                len(text.strip()) >= MIN_TEXT_CHARS_PER_PAGE
                for text, _ in page_texts
            )
            if not page_texts or usable_pages / len(page_texts) < MIN_TEXT_PAGE_RATIO:
                # A partial text layer is not an independent ground truth for
                # scanned/mixed PDFs; report that manual OCR review is needed.
                return [], False
        elif suffix == ".docx":
            from docx import Document as WordDocument
            page_texts = [("\n".join(p.text for p in WordDocument(str(path)).paragraphs), 1)]
        elif suffix == ".doc":
            result = subprocess.run(["antiword", str(path)], capture_output=True, text=True, timeout=30, check=True)
            page_texts = [(result.stdout, 1)]
    except Exception as exc:
        logger.info("Independent extraction audit unavailable for %s: %s", path.name, exc)
        return [], False

    segments: list[tuple[str, int]] = []
    for page_text, page_number in page_texts:
        for part in re.split(r"[\n\r]+|(?<=[.!?])\s+", page_text):
            part = re.sub(r"\s+", " ", part).strip()
            if _is_important_segment(part):
                segments.append((part, page_number))
    return segments, bool(segments)


def audit_chunks(file_path: str, chunks: list[tuple[str, int]]) -> dict:
    """Compare important source segments with the text that will be embedded."""
    path = Path(file_path)
    segments, verifiable = _source_segments(path)
    total_pages = None
    if path.suffix.lower() == ".pdf":
        try:
            from PyPDF2 import PdfReader
            total_pages = len(PdfReader(str(path), strict=False).pages)
        except Exception:
            pass
    extracted_by_page: dict[int, str] = {}
    for content, page in chunks:
        extracted_by_page[page] = f"{extracted_by_page.get(page, '')} {content}"

    if not verifiable:
        return {
            "status": "OCR_REVIEW_REQUIRED",
            "important_text_total": 0,
            "important_text_missing": 0,
            "coverage_percent": None,
            "missing_texts": [],
            "total_pages": total_pages,
        }

    missing = []
    for source_text, page in segments:
        expected = _normalize_audit_text(source_text)
        actual = _normalize_audit_text(extracted_by_page.get(page, ""))
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        word_coverage = len(expected_words & actual_words) / max(len(expected_words), 1)
        # A single missing date or identifier can change the meaning even
        # when most words in a long line are present.
        expected_numbers = set(re.findall(r"\d+", expected))
        actual_numbers = set(re.findall(r"\d+", actual))
        if expected not in actual and (
            word_coverage < 0.95 or not expected_numbers <= actual_numbers
        ):
            missing.append({"page": page, "text": source_text})

    total = len(segments)
    coverage = round(((total - len(missing)) / total) * 100, 2)
    return {
        "status": "COMPLETE" if not missing else "INCOMPLETE",
        "important_text_total": total,
        "important_text_missing": len(missing),
        "coverage_percent": coverage,
        "missing_texts": missing,
        "total_pages": total_pages,
    }


def extract_chunks_with_audit(file_path: str, max_attempts: int = 3, **kwargs):
    """Extract once and report missing text; stronger methods require user action."""
    original_path = Path(file_path)
    if original_path.suffix.lower() in {".doc", ".docx"}:
        # Word pagination depends on fonts, margins and the rendering engine;
        # paragraph extraction cannot provide reliable page numbers. Render a
        # temporary PDF first so both chunks and the audit share real pages.
        with readable_pdf_path(file_path) as converted_path:
            chunks = extract_chunks_with_audit(
                str(converted_path),
                max_attempts=max_attempts,
                **kwargs,
            )
            metadata = kwargs.get("extraction_metadata")
            if metadata is not None:
                method = metadata.get("method", "text_layer")
                metadata["method"] = f"word_to_pdf_{method}"
            return chunks

    requested_mode = kwargs.pop("extraction_mode", "auto")
    metadata = kwargs.pop("extraction_metadata", None)
    modes = [requested_mode]

    best_chunks = []
    best_audit = None
    attempt_methods = []
    for attempt, mode in enumerate(modes[:max_attempts], 1):
        attempt_metadata = {}
        try:
            chunks = extract_chunks(file_path, extraction_mode=mode, extraction_metadata=attempt_metadata, **kwargs)
        except Exception:
            if attempt == 1:
                raise
            logger.exception("Extraction retry %d failed for %s", attempt, file_path)
            continue
        audit = audit_chunks(file_path, chunks)
        attempt_methods.append(attempt_metadata.get("method", mode))
        if best_audit is None or audit["important_text_missing"] < best_audit["important_text_missing"]:
            best_chunks, best_audit = chunks, audit
        break

    best_audit["attempts"] = len(attempt_methods)
    best_audit["attempt_methods"] = attempt_methods
    if metadata is not None:
        metadata.update(best_audit)
        metadata["method"] = attempt_methods[-1] if attempt_methods else requested_mode
    return best_chunks


def _pdf_has_images(page) -> bool:
    """Detect regular PDF image objects without rendering the page."""
    try:
        resources = page.get("/Resources")
        resources = resources.get_object() if resources else None
        xobjects = resources.get("/XObject") if resources else None
        xobjects = xobjects.get_object() if xobjects else None
        if not xobjects:
            return False
        return any(
            obj.get_object().get("/Subtype") == "/Image"
            for obj in xobjects.values()
        )
    except Exception:
        return False


def _looks_like_scanned_pdf(path: Path, page_count: int) -> bool:
    """Return True when a large bitmap covers most pages of the PDF."""
    import pypdfium2 as pdfium
    from pypdfium2 import raw as pdfium_c

    scan_like_pages = 0
    pdf = pdfium.PdfDocument(str(path))
    try:
        for page_index in range(page_count):
            page = pdf[page_index]
            try:
                page_width, page_height = page.get_size()
                page_area = page_width * page_height
                if page_area <= 0:
                    continue

                largest_coverage = 0.0
                for image in page.get_objects(
                    filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE],
                    max_depth=15,
                ):
                    left, bottom, right, top = image.get_bounds()
                    image_width = max(0.0, min(right, page_width) - max(left, 0.0))
                    image_height = max(0.0, min(top, page_height) - max(bottom, 0.0))
                    coverage = (image_width * image_height) / page_area
                    largest_coverage = max(largest_coverage, coverage)

                if largest_coverage >= MIN_SCAN_IMAGE_COVERAGE:
                    scan_like_pages += 1
            finally:
                page.close()
    finally:
        pdf.close()

    return (scan_like_pages / page_count) >= MIN_SCAN_PAGE_RATIO


def _inspect_pdf(path: Path) -> tuple[int, bool, bool]:
    """Reject unreadable/encrypted PDFs and inspect their image structure."""
    from PyPDF2 import PdfReader

    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception:
                unlocked = 0
            if not unlocked:
                raise DocumentExtractionError("The document is encrypted")

        page_count = len(reader.pages)
        if page_count == 0:
            raise DocumentExtractionError("The document has no content")
        has_images = any(_pdf_has_images(page) for page in reader.pages)
        looks_scanned = _looks_like_scanned_pdf(path, page_count) if has_images else False
        return page_count, has_images, looks_scanned
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("The PDF file could not be read") from exc


def _get_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter
        _converter = DocumentConverter()
    return _converter


def _get_converter_no_ocr():
    global _converter_no_ocr
    if _converter_no_ocr is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        _converter_no_ocr = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )
    return _converter_no_ocr


def _chunk_page_text(text: str, max_tokens: int) -> list[str]:
    """Create lightweight, overlapping chunks without loading a tokenizer."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []

    # For Indonesian prose, ~0.7 words/token is a conservative approximation.
    max_words = max(80, int(max_tokens * 0.7))
    overlap_words = min(40, max_words // 8)
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_words

    return chunks


def _extract_text_layer_chunks(
    path: Path,
    max_tokens: int,
    inspection_metadata: dict | None = None,
) -> list[tuple[str, int]] | None:
    """Return lightweight PDF chunks, or None when OCR/layout fallback is needed."""
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(path))
        try:
            page_texts = []
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                try:
                    text_page = page.get_textpage()
                    try:
                        page_texts.append(text_page.get_text_range().strip())
                    finally:
                        text_page.close()
                finally:
                    page.close()
        finally:
            pdf.close()
    except Exception as exc:
        logger.info("Text-layer extraction failed for %s: %s", path.name, exc)
        return None

    if not page_texts:
        return None

    usable_pages = sum(len(text) >= MIN_TEXT_CHARS_PER_PAGE for text in page_texts)
    text_page_ratio = usable_pages / len(page_texts)
    total_chars = sum(len(text) for text in page_texts)
    if inspection_metadata is not None:
        inspection_metadata["text_layer_chars"] = total_chars

    if total_chars < MIN_TOTAL_TEXT_CHARS or text_page_ratio < MIN_TEXT_PAGE_RATIO:
        logger.info(
            "PDF %s has insufficient text layer (%d chars, %.0f%% usable pages); "
            "falling back to Docling/OCR",
            path.name,
            total_chars,
            text_page_ratio * 100,
        )
        return None

    chunks = []
    for page_number, text in enumerate(page_texts, start=1):
        for chunk in _chunk_page_text(text, max_tokens):
            chunks.append((chunk, page_number))

    logger.info(
        "Extracted %d chunks from %s using lightweight PDF text layer",
        len(chunks),
        path.name,
    )
    return chunks


def extract_chunks(
    file_path: str,
    max_tokens: int = 512,
    tokenizer: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    extraction_mode: str = "auto",
    extraction_metadata: dict | None = None,
) -> list[tuple[str, int]]:
    """
    Extract structured chunks from PDF, DOCX, or DOC.
    Returns list of (chunk_text, page_number).
    Heading context prepended to each chunk for better retrieval.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if extraction_mode not in {"auto", "text", "docling_no_ocr", "ocr"}:
        raise ValueError(f"Unsupported extraction mode: {extraction_mode}")

    pdf_has_images = False
    pdf_looks_scanned = False
    if path.suffix.lower() == ".pdf":
        _, pdf_has_images, pdf_looks_scanned = _inspect_pdf(path)

    if path.suffix.lower() == ".pdf" and extraction_mode in {"auto", "text"}:
        text_layer_metadata = {}
        lightweight_chunks = _extract_text_layer_chunks(
            path,
            max_tokens,
            text_layer_metadata,
        )
        if lightweight_chunks is not None:
            if extraction_metadata is not None:
                extraction_metadata["method"] = "text_layer"
            return lightweight_chunks
        if extraction_mode == "text":
            raise DocumentExtractionError("The document does not contain enough text")
        if extraction_mode == "auto":
            raise DocumentExtractionError(
                "Lapisan teks tidak cukup. Pilih proses lanjutan atau OCR dari detail dokumen."
            )
        if not pdf_has_images:
            text_layer_chars = text_layer_metadata.get("text_layer_chars", 0)
            message = (
                "The document has no content"
                if text_layer_chars == 0
                else "The document does not contain enough text"
            )
            raise DocumentExtractionError(message)
        if not pdf_looks_scanned:
            raise DocumentExtractionError(
                "The image was not identified as a scanned document"
            )

    use_docling_without_ocr = (
        path.suffix.lower() == ".pdf" and extraction_mode == "docling_no_ocr"
    )
    logger.info(
        "Converting document with Docling (%s): %s",
        "OCR disabled" if use_docling_without_ocr else "OCR enabled",
        path.name,
    )
    from docling.chunking import HybridChunker

    converter = _get_converter_no_ocr() if use_docling_without_ocr else _get_converter()
    try:
        result = converter.convert(str(path))
    except Exception as exc:
        if path.suffix.lower() == ".pdf":
            raise DocumentExtractionError("The PDF file could not be read") from exc
        raise

    chunker = HybridChunker(
        tokenizer=tokenizer,
        max_tokens=max_tokens,
        merge_peers=True,
    )

    chunks: list[tuple[str, int]] = []

    for chunk in chunker.chunk(result.document):
        page = 1
        meta = chunk.meta
        for item in (meta.doc_items or []):
            if getattr(item, 'prov', None):
                prov0 = item.prov[0]
                if hasattr(prov0, 'page_no'):
                    page = prov0.page_no
                    break

        headings = meta.headings or []
        captions = meta.captions or []
        heading_ctx = " > ".join(headings) if headings else ""
        caption_ctx = " | ".join(captions) if captions else ""

        prefix_parts = [p for p in [heading_ctx, caption_ctx] if p]
        prefix = "\n".join(prefix_parts)

        chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
        text = f"{prefix}\n{chunk_text}".strip() if prefix else chunk_text.strip()

        if text:
            chunks.append((text, page))

    logger.info("Extracted %d chunks from %s", len(chunks), path.name)

    total_text_chars = sum(len(text.strip()) for text, _ in chunks)
    if path.suffix.lower() == ".pdf" and total_text_chars < MIN_TOTAL_TEXT_CHARS:
        if total_text_chars == 0:
            message = (
                "No text was found after OCR"
                if pdf_has_images and not use_docling_without_ocr
                else "The document has no content"
            )
        else:
            message = "The document does not contain enough text"
        raise DocumentExtractionError(message)

    if extraction_metadata is not None:
        extraction_metadata["method"] = (
            "docling_no_ocr" if use_docling_without_ocr else "ocr"
        )
    return chunks
