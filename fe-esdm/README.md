# Frontend MAGMA AI dan NARA

Folder ini berisi antarmuka web NARA berbasis React 19, Vite, Material UI, dan React Router. Fitur utama mencakup chat API MAGMA dan Knowledge Base, riwayat percakapan, pengelolaan dokumen, autentikasi, serta halaman API key. Gambaran sistem ada di [README utama](../README.md). Tabel perintah WhatsApp ada di [panduan WhatsApp](../docs/WHATSAPP_GUIDE.md).

## Menjalankan

Jalankan stack dari root repositori sesuai [panduan pemasangan](../docs/INSTALLATION_GUIDE.md). Buka frontend melalui Nginx di `http://localhost/`. Compose juga membuka port frontend langsung di `http://localhost:3000/`.

Untuk pengembangan frontend terpisah:

```bash
cp .env.example .env
npm ci --legacy-peer-deps
npm run dev
```

Atur `VITE_API_URL` dan `VITE_AUTH_API_BASE_URL` ke alamat yang dapat dijangkau **browser**. Nilai `/api` pada contoh berlaku saat membuka frontend melalui Nginx proyek. Jika membuka Vite langsung, sesuaikan URL atau proxy pengembangan. Build ulang setelah mengubah variabel `VITE_*` karena nilainya masuk ke aset frontend. Jangan menaruh kredensial produksi di variabel yang terlihat oleh browser.

## Pemeriksaan kode

```bash
npm run build
npm run lint
npm run security:check:rsc
```

Panduan penggunaan antarmuka ada di [USER_GUIDE.md](../docs/USER_GUIDE.md). Dokumen backend dan API berada di [ms-esdm](../ms-esdm/README.md).
