from PyPDF2 import PdfReader

def extract_pdf_chunks(pdf_path: str, max_chunk_size: int = 10000) -> list[str]:
    """
    Extract text from PDF and split into chunks of ~max_chunk_size tokens.
    """
    reader = PdfReader(pdf_path)
    chunks = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.replace("\n", " ").strip()
        # Split long text into smaller chunks
        for i in range(0, len(text), max_chunk_size):
            chunk_text = text[i:i + max_chunk_size]
            if chunk_text.strip():
                chunks.append((chunk_text, page_num))
    return chunks
