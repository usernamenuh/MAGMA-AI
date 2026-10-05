import asyncio
from unittest.mock import AsyncMock

import numpy as np

from services.vector_store import VectorStore, _clean_chunk_content


def test_clean_chunk_content_removes_only_nul_characters():
    assert _clean_chunk_content("Laporan\x00 Minggu 1") == "Laporan Minggu 1"
    assert _clean_chunk_content("Teks biasa") == "Teks biasa"


def test_store_chunks_embeds_and_saves_the_same_clean_text():
    db = AsyncMock()
    store = VectorStore(db)
    captured = []

    async def fake_generate_embeddings(contents, batch_size=None):
        captured.extend(contents)
        return [np.array([0.1, 0.2]) for _ in contents]

    store.generate_embeddings = fake_generate_embeddings

    count = asyncio.run(store.store_chunks([("Halaman\x00 pertama", 1)], document_id=53))

    assert count == 1
    assert captured == ["Halaman pertama"]
    assert db.execute.await_args.args[1][0]["content"] == "Halaman pertama"
    db.commit.assert_awaited_once()
