# Model bahasa lokal MAGMA AI dan NARA

Service dalam folder ini menyediakan API lokal yang kompatibel dengan antarmuka OpenAI untuk model GGUF. Proyek memakai **Qwen2.5 1.5B Instruct Q4** sebagai model lokal. Backend juga dapat memakai Groq atau OpenRouter jika kredensialnya tersedia. Pergantian model chat tidak mengubah embedding dokumen yang sudah tersimpan.

## Menyiapkan model

Ikuti [panduan pemasangan proyek](../docs/INSTALLATION_GUIDE.md) dan [panduan GGUF Qwen](LOCAL_MODEL.md). Salin konfigurasi contoh:

```bash
cp env.example .env
```

Nilai `MODEL_PATH` pada contoh adalah `models/qwen2.5-1.5b-instruct-q4_k_m.gguf`. Compose memasang direktori proyek `data/models` ke `/app/models`; letakkan GGUF di lokasi tersebut. `MODEL_NAME` harus selaras dengan `OPENAI_MODEL` pada konfigurasi backend. Jangan commit file model atau API key.

## Menjalankan dan memeriksa

Jalankan service dari root repositori dengan nama proyek Compose yang sama:

```bash
docker compose -p magma-ai-staging up -d --build openai-local
docker compose -p magma-ai-staging logs --tail=100 openai-local
```

Di jaringan Compose, backend mengakses `http://openai-local:8002/v1`. Setelah Nginx berjalan, host dapat mengakses API model melalui jalur `/openai/`. Service memuat model saat startup. Jika berkas GGUF salah atau hilang, port mungkin terbuka meskipun inferensi gagal.

Endpoint utama layanan adalah `GET /v1/models`, `POST /v1/chat/completions`, dan `POST /v1/embeddings`. Melalui Nginx, awali path dengan `/openai`, misalnya `http://localhost/openai/v1/models`. Jika `API_KEY` diaktifkan pada layanan ini, gunakan Bearer token yang sesuai dan selaraskan dengan `OPENAI_API_KEY` di backend.

## Keterbatasan

Model kecil dan kuantisasi Q4 membantu penggunaan CPU/RAM, tetapi jawaban panjang atau pertanyaan sulit tetap perlu diperiksa terhadap sumber. Waktu respons bergantung pada perangkat, panjang konteks, serta beban layanan lain. Konfigurasi dan checksum model yang digunakan tercatat di [LOCAL_MODEL.md](LOCAL_MODEL.md).
