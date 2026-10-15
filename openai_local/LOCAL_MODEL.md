# Model lokal Qwen2.5 1.5B Instruct

Service `openai-local` menjalankan model `qwen2.5-1.5b-instruct-q4_k_m.gguf`. Unduh berkasnya dari [repositori GGUF resmi Qwen](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/main); Git tidak menyertakannya.

## Unduh dan verifikasi

Jalankan dari root repositori. Perintah ini memerlukan `curl` dan `sha256sum` pada host Linux.

```bash
mkdir -p data/models
curl -fL --retry 3 \
  -o data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
printf '%s  %s\n' \
  '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e' \
  'data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf' | sha256sum -c -
```

`sha256sum` menampilkan `OK` jika checksum cocok. Jika gagal, periksa berkas unduhan dan hash pada sumber resmi sebelum menggunakannya.

Compose memasang `./data/models` ke `/app/models`. Konfigurasi `openai_local/.env` harus sesuai dengan lokasi di dalam container:

```dotenv
MODEL_PATH=models/qwen2.5-1.5b-instruct-q4_k_m.gguf
MODEL_NAME=qwen2.5-1.5b-instruct
N_CTX=4096
N_GPU_LAYERS=0
```

Di `ms-esdm/.env`, gunakan `OPENAI_MODEL=qwen2.5-1.5b-instruct`. Jika `API_KEY` untuk service lokal diisi, samakan dengan `OPENAI_API_KEY` pada backend. Jangan masukkan kunci ke dokumen atau commit.

## Jalankan dan periksa

Setelah mengikuti [panduan pemasangan](../docs/INSTALLATION_GUIDE.md), jalankan service dengan nama proyek Compose yang sama:

```bash
docker compose -p magma-ai-staging up -d --build openai-local backend
docker compose -p magma-ai-staging ps openai-local backend
curl -f http://localhost/api/knowledge/models
```

Tunggu hingga backend sehat sebelum menguji endpoint. Jika service gagal memuat model, periksa `docker compose -p magma-ai-staging logs --tail=100 openai-local` dan nilai `MODEL_PATH`.

Pergantian model chat tidak mengubah embedding dokumen. Service ini memakai `llama-cpp-python` 0.3.16 dan format prompt ChatML untuk Qwen. Siapkan RAM lebih besar dari ukuran berkas GGUF; kebutuhan pastinya bergantung pada panjang konteks dan layanan lain yang berjalan.
