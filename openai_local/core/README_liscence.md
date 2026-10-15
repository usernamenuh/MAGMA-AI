# Komponen lisensi model lokal

Folder ini menyimpan kode pemeriksaan lisensi dan dekripsi aset untuk image `openai-local`. Entrypoint menentukan apakah pemeriksaan tersebut berjalan.

## Alur pada proyek ini

`openai_local/Dockerfile` menetapkan `core/run_liscence_lock.sh` sebagai entrypoint image. Skrip ini memeriksa `license.lic`, mendekripsi aset `.enc`, lalu menjalankan `main.py`.

Service `openai-local` pada `docker-compose.yml` **mengganti entrypoint** menjadi `python3 main.py`. Compose proyek ini **tidak menjalankan pemeriksaan lisensi atau dekripsi** dari skrip tersebut. Ikuti panduan model lokal untuk memakai berkas GGUF di `data/models` tanpa langkah pembuatan lisensi.

Jangan menyimpulkan bahwa `DISABLE_LICENSE` di `ms-esdm/.env` mengubah entrypoint service `openai-local`. Variabel tersebut milik backend dan tidak mengubah perintah start pada Compose.

## Berkas yang tersedia

| Berkas | Peran |
| --- | --- |
| `license_check.py` | Memeriksa tanda tangan, masa berlaku, dan ID mesin pada `license.lic`; mengeluarkan data key jika valid. |
| `decrypt_files.py` | Mendekripsi berkas `.enc` menggunakan data key. |
| `run_liscence_lock.sh` | Menjalankan pemeriksaan lisensi, dekripsi, lalu `main.py` bila dipakai sebagai entrypoint. |
| `../setup.py` | Mengompilasi sebagian modul Python dengan Cython pada tahap build image. |

Jika image dijalankan di luar Compose tanpa override entrypoint, skrip lisensi pada Dockerfile berlaku. Sediakan lisensi yang sah melalui mekanisme distribusi yang sesuai; jangan memasukkan `license.lic`, private key, atau data key ke repo. Lihat [panduan model lokal](../LOCAL_MODEL.md) untuk pemasangan Compose yang didokumentasikan di proyek ini.
