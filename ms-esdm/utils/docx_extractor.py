from docx import Document as DocxDocument
import asyncio
import subprocess
from pathlib import Path

LIBREOFFICE_BIN = "soffice"

async def convert_doc_to_docx(file_path: str) -> str:
    return await asyncio.to_thread(_convert_doc_to_docx_sync, file_path)

def _convert_doc_to_docx_sync(file_path: str) -> str:
    input_path = Path(file_path).resolve()
    output_dir = input_path.parent

    subprocess.run(
        [
            LIBREOFFICE_BIN,
            "--headless",
            "--convert-to", "docx",
            str(input_path),
            "--outdir", str(output_dir),
        ],
        check=True,
    )

    output_path = input_path.with_suffix(".docx")
    if not output_path.exists():
        raise FileNotFoundError(f"Conversion failed: {output_path}")

    return str(output_path)

def extract_doc_text_fallback(file_path: str) -> str:
    result = subprocess.run(
        ["antiword", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout


def extract_docx_chunks(file_path: str, chunk_size: int = 500):
    """
    Extract text from a Word (.docx) file and break into chunks.
    Returns list of (text, page_number)
    """
    doc = DocxDocument(file_path)
    full_text = []

    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    full_text.append(cell.text.strip())

    merged = " ".join(full_text)

    # Simple chunking
    chunks = []
    page_num = 1

    for i in range(0, len(merged), chunk_size):
        chunk = merged[i:i + chunk_size]
        chunks.append((chunk, page_num))
        page_num += 1

    return chunks
