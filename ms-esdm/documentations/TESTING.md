# Panduan Pengujian Backend MAGMA AI

Jalankan test lokal dan periksa alur integrasi backend dengan panduan ini. Daftar endpoint ada di [dokumentasi API](API_DOCUMENTATION.md).

## Unit test lokal

Dari root repositori, aktifkan virtualenv pengujian lalu jalankan pytest di direktori `ms-esdm`:

```bash
cd ms-esdm
pytest tests
```

Cakupan pengujian di folder `tests/`:

- Normalisasi query dan entity resolution nama gunung api.
- Pipeline ekstraksi teks, chunking, dan audit kelengkapan per halaman.
- Logika pembuatan annotated PDF dan penambahan teks manual.
- State machine session mode WhatsApp dan filter intent follow-up.

Sebagian test memakai mock service. Sebelum menjalankan test yang mengakses layanan eksternal, periksa kebutuhan API key pada test tersebut.

## Checklist pengujian integrasi

Jalankan pengujian end-to-end setelah seluruh container Docker aktif:

| Modul | Skenario pengujian | Indikator keberhasilan |
| --- | --- | --- |
| API MAGMA | Query status terkini gunung api aktif | Respons memuat data MAGMA terbaru beserta rujukan waktu pengamatan. |
| Knowledge Base | Ingest file PDF dan query isi konten | Dokumen berstatus Completed, chunk tersimpan di pgvector, dan jawaban menyertakan kutipan dokumen. |
| Audit Dokumen | Upload PDF dengan scan parsial | Dokumen berstatus Kurang lengkap dan teks yang terbaca tetap bisa dicari di chat. |
| Mode Model | Pergantian model lokal ke cloud di UI | Backend merespons sesuai model yang dipilih tanpa mengubah embedding database. |
| WhatsApp Teks | Kirim perintah mode `/api-documentation` dan query | Bot mengunci rute jawaban ke data resmi MAGMA. |
| WhatsApp Voice | Kirim voice note pertanyaan saat mode `/voice` aktif | Transkripsi Groq berhasil, bot membalas via teks, lalu voice note sintetis masuk. |

## Catatan skrip evaluasi historis

File `test_chat_api_documentation.py` dan `test_chat_knowledge_base.py` di root `ms-esdm` adalah skrip benchmark manual lama dengan URL dan payload hardcoded.

Sesuaikan host server, token autentikasi, dan ID dokumen di dalam skrip sebelum menjalankannya. Jangan jadikan hasil skrip lama sebagai klaim benchmark akurasi umum. Jangan commit token atau dokumen privat ke repositori publik.
