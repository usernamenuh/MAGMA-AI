# Backend MAGMA AI dan NARA

Folder ini berisi API FastAPI untuk autentikasi, pertanyaan API MAGMA, Knowledge Base, unggah dan audit dokumen, riwayat chat, serta kanal WhatsApp. Worker dokumen berjalan sebagai layanan terpisah dari image backend. Lihat [README utama](../README.md) untuk gambaran proyek dan arsitektur.

## Menjalankan

Jalankan stack dari root repositori sesuai [panduan pemasangan](../docs/INSTALLATION_GUIDE.md). Salin [.env.example](.env.example) ke `.env` lokal dan isi kredensial yang diperlukan. Di jaringan Compose, backend mengakses database melalui hostname `db`. Setelah layanan sehat, buka dokumentasi endpoint di `http://localhost/api/docs`.

`knowledge-worker` memproses dokumen dan menyimpan teks yang terbaca sebagai chunk beserta embedding, lalu menjalankan audit. Jika statusnya **Kurang lengkap**, periksa PDF bertanda sebelum menambah teks manual atau menjalankan proses lanjutan. Compose tidak mengaktifkan OCR sebagai fallback otomatis karena proses itu dapat membebani CPU.

## WhatsApp dan pesan suara

Endpoint `/whatsapp/analyze` menerima pesan teks serta audio base64 melalui `audio_base64` dan `audio_mimetype`. Audio ditranskripsi menggunakan Groq Whisper (`GROQ_API_KEY`); jawaban dapat dikirim sebagai voice note melalui Edge TTS dan Evolution API. Mode `/voice` dan `/text`, pemilihan sumber, serta autentikasi unggah dijelaskan di [WHATSAPP_GUIDE.md](../docs/WHATSAPP_GUIDE.md). Keberhasilan end-to-end juga bergantung pada workflow n8n dan sesi Evolution yang aktif; keduanya tersimpan di volume runtime, bukan dalam kode backend.

## Pengujian dan referensi

Setelah menyiapkan lingkungan pengujian, jalankan test di folder `tests/`:

```bash
pytest tests
```

Rujukan endpoint dan catatan pengujian ada di [API_DOCUMENTATION.md](documentations/API_DOCUMENTATION.md) serta [TESTING.md](documentations/TESTING.md). Cocokkan contoh yang lebih lama dengan route aktual sebelum digunakan. Jangan commit `.env`, token, dokumen pribadi, atau log percakapan.
