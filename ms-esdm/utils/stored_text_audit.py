"""Compare independently readable document text with persisted chunk content."""

from __future__ import annotations

import re
import subprocess
from difflib import SequenceMatcher
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[\w@.+/%-]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


def _source_pages(path: Path) -> tuple[list[tuple[int | None, str]], str]:
    """Use a reader independent from the chunk extractor where possible."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
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
        return [(index, text) for index, text in enumerate(pages, 1)], "Poppler (lapisan teks PDF)"
    if suffix == ".docx":
        from docx import Document as WordDocument

        paragraphs = (p.text for p in WordDocument(str(path)).paragraphs)
        return [(None, "\n".join(paragraphs))], "Paragraf DOCX"
    if suffix == ".doc":
        result = subprocess.run(
            ["antiword", str(path)], capture_output=True, text=True, timeout=30, check=True
        )
        return [(None, result.stdout)], "Antiword"
    raise ValueError("Format dokumen tidak didukung untuk audit teks")


def compare_text_pages(
    source_pages: list[tuple[int | None, str]],
    stored_chunks: list[tuple[str, int]],
) -> dict:
    """Classify each readable source line against the saved chunk tokens.

    Alignment respects word order and occurrence counts, so repeated words do
    not make a missing line look present merely because they appear elsewhere.
    """
    page_sensitive = all(page is not None for page, _ in source_pages)
    unreadable_pages = [page for page, text in source_pages if page is not None and not _tokens(text)]
    lines = []
    matched_tokens_total = 0
    source_tokens_total = 0

    for page_number, source_text in source_pages:
        source_tokens: list[str] = []
        source_lines = []
        for raw_line in source_text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            words = _tokens(line)
            if not words:
                continue
            start = len(source_tokens)
            source_tokens.extend(words)
            source_lines.append((line, start, len(source_tokens)))

        saved_text = " ".join(
            content for content, chunk_page in stored_chunks
            if not page_sensitive or chunk_page == page_number
        )
        saved_tokens = _tokens(saved_text)
        matched = bytearray(len(source_tokens))
        matcher = SequenceMatcher(None, source_tokens, saved_tokens, autojunk=False)
        for source_start, _, size in matcher.get_matching_blocks():
            matched[source_start:source_start + size] = b"\x01" * size

        for line, start, end in source_lines:
            matched_count = sum(matched[start:end])
            count = end - start
            status = "matched" if matched_count == count else "missing" if matched_count == 0 else "partial"
            missing_words = [source_tokens[index] for index in range(start, end) if not matched[index]]
            lines.append({
                "page": page_number,
                "text": line,
                "status": status,
                "matched_words": matched_count,
                "total_words": count,
                "missing_words": missing_words,
            })
            matched_tokens_total += matched_count
            source_tokens_total += count

    counts = {status: sum(line["status"] == status for line in lines) for status in ("matched", "partial", "missing")}
    return {
        "status": "compared" if source_tokens_total else "unverifiable",
        "comparison_unit": "source_line",
        "unreadable_pages": unreadable_pages,
        "summary": {
            "total_lines": len(lines),
            **counts,
            "matched_words": matched_tokens_total,
            "total_words": source_tokens_total,
            "word_coverage_percent": round(100 * matched_tokens_total / source_tokens_total, 2) if source_tokens_total else None,
        },
        "lines": lines,
    }


def audit_stored_document(file_path: str, chunks: list[tuple[str, int]]) -> dict:
    path = Path(file_path)
    if not path.is_file():
        return {"status": "unavailable", "reason": "File sumber tidak ditemukan", "lines": []}
    try:
        source_pages, reader = _source_pages(path)
    except Exception as exc:
        return {"status": "unavailable", "reason": f"Teks sumber tidak dapat dibaca: {type(exc).__name__}", "lines": []}

    report = compare_text_pages(source_pages, chunks)
    report["source_reader"] = reader
    if report["status"] == "unverifiable":
        report["reason"] = "Tidak ada lapisan teks yang dapat dibandingkan; PDF hasil scan memerlukan pemeriksaan OCR/manual."
    return report
