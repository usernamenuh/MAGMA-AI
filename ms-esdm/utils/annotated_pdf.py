"""Mark text-layer words that align with persisted document chunks in a PDF copy."""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import ArrayObject, DecodedStreamObject, NameObject

from utils.stored_text_audit import _tokens

XHTML = "{http://www.w3.org/1999/xhtml}"


def count_letters(text: str) -> int:
    """Count Unicode letters, excluding spaces, digits, and punctuation."""
    return sum(character.isalpha() for character in text)


def read_pdf_letter_count(file_path: str) -> int:
    """Count readable letters in the PDF text layer without creating a copy."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(file_path)
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )
    root = ET.fromstring(result.stdout)
    return sum(count_letters(word.text or "") for word in root.iter(f"{XHTML}word"))


def _page_marks(page, saved_text: str) -> tuple[list[tuple[float, float, float]], int, int]:
    """Return underline coordinates in Poppler's top-left page space."""
    words = []
    source_tokens = []
    source_lines = []
    for line in page.iter(f"{XHTML}line"):
        line_words = []
        line_start = len(source_tokens)
        for word in line.iter(f"{XHTML}word"):
            tokens = _tokens(word.text or "")
            if not tokens:
                continue
            start = len(source_tokens)
            source_tokens.extend(tokens)
            line_words.append((word, start, len(source_tokens)))
        words.append(line_words)
        if len(source_tokens) > line_start:
            source_lines.append((line_start, len(source_tokens)))

    matched = bytearray(len(source_tokens))
    saved_tokens = _tokens(saved_text)
    matcher = SequenceMatcher(
        None, source_tokens, saved_tokens, autojunk=len(source_tokens) > 3000
    )
    for start, _, length in matcher.get_matching_blocks():
        matched[start:start + length] = b"\x01" * length

    # Multi-column PDFs can store the same words in a different order from
    # Poppler's visual reading order. Match remaining words within each line,
    # but require a phrase (or the whole short line) and respect word counts.
    candidates = bytearray(len(source_tokens))
    for start, end in source_lines:
        line_tokens = source_tokens[start:end]
        line_matcher = SequenceMatcher(None, line_tokens, saved_tokens, autojunk=False)
        for source_start, _, length in line_matcher.get_matching_blocks():
            if length >= 3 or length == len(line_tokens):
                candidates[start + source_start:start + source_start + length] = b"\x01" * length
    remaining = Counter(saved_tokens) - Counter(
        token for index, token in enumerate(source_tokens) if matched[index]
    )
    for index, token in enumerate(source_tokens):
        if not matched[index] and candidates[index] and remaining[token] > 0:
            matched[index] = 1
            remaining[token] -= 1

    marks = []
    matched_words = 0
    total_words = 0
    for line_words in words:
        run = None
        for word, start, end in line_words:
            total_words += 1
            if not all(matched[start:end]):
                if run:
                    marks.append(run)
                    run = None
                continue
            matched_words += 1
            left = float(word.attrib["xMin"])
            right = float(word.attrib["xMax"])
            bottom = float(word.attrib["yMax"])
            if run and left - run[1] <= 8 and abs(bottom - run[2]) <= 2:
                run = (run[0], right, max(run[2], bottom))
            else:
                if run:
                    marks.append(run)
                run = (left, right, bottom)
        if run:
            marks.append(run)
    return marks, matched_words, total_words


def build_annotated_pdf(file_path: str, chunks: list[tuple[str, int]]) -> tuple[bytes, dict]:
    """Create a marked PDF in memory; never modify the uploaded original."""
    path = Path(file_path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Hanya dokumen PDF yang dapat ditandai")
    if not path.is_file():
        raise FileNotFoundError(file_path)

    result = subprocess.run(
        ["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )
    root = ET.fromstring(result.stdout)
    layout_pages = root.findall(f".//{XHTML}page")
    reader = PdfReader(str(path), strict=False)
    if len(layout_pages) != len(reader.pages):
        raise ValueError("Jumlah halaman PDF tidak cocok dengan hasil pembacaan teks")

    writer = PdfWriter()
    stats = {
        "matched_words": 0,
        "total_words": 0,
        "pdf_letters": 0,
        "stored_letters": sum(count_letters(content) for content, _ in chunks),
        "marked_pages": 0,
        "skipped_pages": 0,
    }
    for index, layout in enumerate(layout_pages):
        stats["pdf_letters"] += sum(
            count_letters(word.text or "") for word in layout.iter(f"{XHTML}word")
        )
        source_page = reader.pages[index]
        page = writer.add_page(source_page)
        width = float(source_page.cropbox.width)
        height = float(source_page.cropbox.height)
        layout_width = float(layout.attrib["width"])
        layout_height = float(layout.attrib["height"])
        if (source_page.get("/Rotate", 0) % 360 != 0
                or abs(width - layout_width) > 2
                or abs(height - layout_height) > 2):
            stats["skipped_pages"] += 1
            continue

        saved_text = " ".join(
            content for content, number in chunks if number == index + 1
        )
        marks, matched_words, total_words = _page_marks(layout, saved_text)
        stats["matched_words"] += matched_words
        stats["total_words"] += total_words
        if not marks:
            continue
        stats["marked_pages"] += 1
        commands = ["q", "0.87 0.12 0.15 RG", "0.85 w"]
        x_offset = float(source_page.cropbox.left)
        y_offset = float(source_page.cropbox.bottom)
        for left, right, bottom in marks:
            y = y_offset + height - bottom - 1.2
            commands.append(
                f"{x_offset + left:.2f} {y:.2f} m {x_offset + right:.2f} {y:.2f} l S"
            )
        commands.append("Q")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(commands).encode("ascii"))
        reference = writer._add_object(stream)
        graphics_start = DecodedStreamObject()
        graphics_start.set_data(b"q\n")
        graphics_end = DecodedStreamObject()
        graphics_end.set_data(b"Q\n")
        start_reference = writer._add_object(graphics_start)
        end_reference = writer._add_object(graphics_end)
        original_contents = page.get("/Contents")
        resolved_contents = original_contents.get_object() if original_contents else None
        if original_contents is None:
            page[NameObject("/Contents")] = reference
        elif isinstance(resolved_contents, ArrayObject):
            page[NameObject("/Contents")] = ArrayObject(
                [start_reference, *resolved_contents, end_reference, reference]
            )
        else:
            page[NameObject("/Contents")] = ArrayObject(
                [start_reference, original_contents, end_reference, reference]
            )

    output = BytesIO()
    writer.write(output)
    return output.getvalue(), stats
