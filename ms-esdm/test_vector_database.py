import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.document import Base, Document
from services.vector_store import VectorStore
from core.config import settings
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


async def main():
    # Setup DB engine and session
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    pdf_path = "blobs/document_example_esdm.pdf"
    doc = Document(
        filename="document_example_esdm.pdf",
        file_path=pdf_path,
        total_pages=0,
        processing_status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    print(f"✅ Created Document with ID: {doc.id}")

    # ✅ Extract chunks from the PDF
    chunks = extract_pdf_chunks(pdf_path)
    print(f"📄 Extracted {len(chunks)} chunks from PDF")

    # Initialize vector store
    store = VectorStore(db)

    # ✅ Store chunks in DB with embeddings
    print("🧠 Storing chunks with embeddings...")
    for idx, (chunk_text, page_num) in enumerate(chunks):
        await store.store_chunk(chunk_text, doc.id, page_num, idx)

    # Update document status
    doc.processing_status = "completed"
    doc.total_pages = len(set(p for _, p in chunks))
    db.commit()
    print("✅ All chunks stored successfully.")

    # ✅ Run similarity search
    query = "renewable energy policy"
    print(f"\n🔍 Running similarity search for: '{query}'")
    results = await store.similarity_search(query, document_id=doc.id, k=3)
    for r in results:
        print(f"Score: {r['score']:.3f} | Page: {r['page_number']} | Text: {r['content'][:100]}...")

async def find_vector():
    # Setup DB engine and session
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Initialize vector store
    store = VectorStore(db)

    # ✅ Define the query
    query = "kegiatan apa yang dilakukan di tahun 2024"
    print(f"\n🔍 Running similarity search across ALL documents for: '{query}'")

    # Run similarity search across all chunks (no document_id filter)
    results = await store.similarity_search(query, document_id=None, k=10)

    if not results:
        print("⚠️ No matching chunks found.")
        return

    print(results)

    for idx, r in enumerate(results, 1):
        print(f"\nResult #{idx}")
        print(f"📄 DocumentChunk ID: {r['id']}")
        print(f"📃 Page: {r['page_number']}")
        print(f"💡 Score: {r['score']:.3f}")
        print(f"📝 Text: {r['content'][:300]}...")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(find_vector())
