# Dokumentasi API MAGMA AI dan NARA

Web dan WhatsApp memakai endpoint backend FastAPI dalam tabel berikut. Saat stack berjalan, buka **Swagger UI** di `http://localhost/api/docs` untuk melihat skema request dan respons. Nginx menambahkan awalan `/api`; di dalam jaringan Compose, backend melayani port `8000` tanpa awalan itu.

## Endpoint utama

| Metode dan path melalui Nginx | Fungsi |
| --- | --- |
| `POST /api/analyze` | Menjawab pertanyaan menggunakan alur informasi MAGMA. |
| `POST /api/analyze/en` | Varian bahasa Inggris untuk alur MAGMA. |
| `GET /api/knowledge/models` | Daftar model chat yang tersedia dan pilihan default. |
| `POST /api/knowledge/analyze` | Menjawab dari dokumen Knowledge Base; dapat dibatasi dengan `document_ids`. |
| `POST /api/knowledge/analyze-en` | Varian bahasa Inggris untuk Knowledge Base. |
| `POST /api/knowledge/upload` | Mengunggah PDF/Word ke antrean pemrosesan. |
| `GET /api/knowledge/documents` | Daftar dokumen dan status pemrosesan. |
| `GET /api/knowledge/documents/{id}` | Detail dokumen dan chunk tersimpan. |
| `GET /api/knowledge/documents/{id}/text-audit` | Hasil pemeriksaan kelengkapan teks. |
| `GET /api/knowledge/documents/{id}/annotated-pdf` | PDF dengan penandaan teks yang cocok. |
| `POST /api/knowledge/documents/{id}/retry` | Pemrosesan lanjutan dokumen. |
| `POST /api/knowledge/documents/{id}/manual-text` | Menambahkan teks manual dengan nomor halaman. |
| `DELETE /api/knowledge/documents/{id}` | Menghapus dokumen. |
| `POST /api/whatsapp/analyze` | Menerima pesan WhatsApp teks atau audio dari workflow n8n. |
| `POST /api/knowledge/upload-whatsapp` | Mengunggah dokumen dari sesi WhatsApp yang telah login. |

Backend menyembunyikan sebagian route integrasi, log, autentikasi, dan administrasi dari Swagger (`include_in_schema=False`). Periksa kode di `ms-esdm/routes/v1/` sebelum memanggilnya; beberapa route memerlukan kunci API. `{id}` pada tabel berarti ID dokumen.

## Bentuk request penting

Untuk `POST /api/analyze`, field utama adalah `user_input`; `session_id`, `geo_location`, `location_name`, dan `model` bersifat opsional. Untuk `POST /api/knowledge/analyze`, field utama adalah `user_input`; `session_id`, `model`, dan daftar `document_ids` bersifat opsional.

Untuk `POST /api/whatsapp/analyze`, backend menerima `session_id` yang diawali `whatsapp-`, `user_input` untuk teks, dan opsional `audio_base64` serta `audio_mimetype` untuk voice note. Audio ditranskripsi memakai Groq Whisper. Mode `/api-documentation`, `/knowlage-base`, `/auto`, `/voice`, dan `/text` dikelola per sesi. Balasan suara dibuat melalui Edge TTS dan dikirim melalui Evolution API hanya saat mode `/voice` aktif; voice note masuk tidak otomatis mengaktifkan balasan suara. Workflow n8n harus meneruskan audio ke field yang benar; keberadaan endpoint tidak menjamin alur end-to-end sudah aktif.

## Autentikasi dan keamanan

Sebagian besar endpoint aplikasi memerlukan autentikasi atau kunci API sesuai dependency pada route. Jangan menyalin kunci asli ke contoh request, issue, atau screenshot. Konfigurasi lokal mengikuti [panduan pemasangan](../../docs/INSTALLATION_GUIDE.md); penggunaan WhatsApp ada di [panduan WhatsApp](../../docs/WHATSAPP_GUIDE.md).

Informasi kebencanaan berubah dari waktu ke waktu. Simpan waktu dan rujukan jawaban saat mengevaluasi hasil; respons AI bukan pengganti sumber resmi.
