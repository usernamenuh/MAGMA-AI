# Panduan Penggunaan NARA di Web

Gunakan antarmuka web MAGMA AI untuk bertanya dan memeriksa dokumen Knowledge Base. Untuk menyiapkan aplikasi, ikuti [panduan pemasangan](INSTALLATION_GUIDE.md). Perintah WhatsApp ada di [panduan WhatsApp](WHATSAPP_GUIDE.md).

## Daftar isi

- [Masuk ke aplikasi](#masuk-ke-aplikasi)
- [Bertanya melalui chat](#bertanya-melalui-chat)
- [Menggunakan Knowledge Base](#menggunakan-knowledge-base)
- [Memeriksa hasil ekstraksi dokumen](#memeriksa-hasil-ekstraksi-dokumen)
- [Pengaturan lain](#pengaturan-lain)
- [Jika jawaban belum sesuai](#jika-jawaban-belum-sesuai)

## Masuk ke aplikasi

Buka alamat aplikasi dari pengelola, atau `http://localhost/` untuk instalasi lokal. Masuk dengan akun yang tersedia. Jika pendaftaran aktif, buat akun melalui halaman **Register**. Pada perangkat bersama, gunakan **Logout** di sidebar setelah selesai.

## Bertanya melalui chat

1. Buka **Chat baru**.
2. Pilih sumber **API Documentation** untuk informasi MAGMA atau **Knowledge Base** untuk isi dokumen. Pemilihan sumber penting karena kedua jalur memakai data berbeda.
3. Pilih model bahasa yang tersedia bila diperlukan: Qwen lokal atau opsi Groq/OpenRouter yang terkonfigurasi. Model berbasis jaringan memerlukan koneksi dan API key; pilihan default dapat berubah sesuai konfigurasi backend.
4. Tulis pertanyaan yang spesifik lalu kirim. Untuk pertanyaan kebencanaan, sebutkan nama gunung atau lokasi serta rentang waktu. Untuk dokumen, sebutkan judul atau topiknya.
5. Baca jawaban beserta rujukan yang ditampilkan, lalu verifikasi informasi penting pada sumber asal.

Browser dapat meminta izin lokasi jika fitur tersebut aktif. Berikan izin hanya jika ingin memakai lokasi perangkat dalam pertanyaan. Sidebar menampilkan riwayat percakapan sesuai sesi dan akun.

## Menggunakan Knowledge Base

1. Buka halaman **Knowledge Base** dan pilih **Upload Document**.
2. Pilih berkas PDF atau Word yang didukung. Antarmuka web membatasi unggahan hingga 50 MB.
3. Periksa status pada daftar: **Queued**, **Processing**, **Completed**, **Kurang lengkap**, atau **Failed**. Pemrosesan dokumen berjalan di background; berkas besar dapat memerlukan waktu lebih lama.
4. Buka detail dokumen untuk melihat teks/chunk yang benar-benar tersimpan. Di chat Knowledge Base, ketik `@` untuk memilih dokumen tertentu sebelum bertanya.

Status **Completed** berarti worker selesai mengekstrak dokumen. Tabel kompleks dan hasil pindai buram masih bisa kehilangan teks. Bandingkan hasil ekstraksi dengan dokumen sumber sebelum mengandalkannya.

## Memeriksa hasil ekstraksi dokumen

Pada halaman detail, bandingkan teks tersimpan, jumlah chunk, dan hasil audit dengan berkas sumber. Jika ada bagian penting yang belum masuk:

1. Buka **Lihat PDF bertanda** untuk melihat bagian yang berhasil dicocokkan dengan teks tersimpan. Untuk berkas Word, sistem membuat pratinjau PDF; tata letaknya dapat berbeda dari aplikasi asal.
2. Gunakan **Tambahkan teks manual** beserta nomor halaman bila bagian yang hilang diketahui dan pendek.
3. Gunakan **Proses lanjutan** jika ekstraksi awal belum cukup. OCR ditujukan untuk halaman yang membutuhkan pembacaan gambar dan dapat memakai CPU lebih lama.

Pada status **Kurang lengkap**, sistem tetap menyimpan hasil awal meskipun audit menemukan teks yang belum masuk. Persentase audit tidak mewakili persentase seluruh karakter dokumen.

## Pengaturan lain

- **API Keys:** Buat dan kelola kunci sesuai akses akun. Simpan kunci yang baru dibuat di tempat aman; jangan masukkan ke screenshot atau repositori.
- **API Documentation:** Buka dokumentasi endpoint interaktif yang disediakan aplikasi. Pada instalasi lokal tersedia pula di `http://localhost/api/docs`.
- **Bahasa dan model:** Bila pilihan tersedia pada antarmuka, sesuaikan dengan kebutuhan pertanyaan. Pemilihan model chat tidak mengubah embedding dokumen yang sudah tersimpan.

## Jika jawaban belum sesuai

- Pastikan sumber jawaban yang dipilih benar: API MAGMA untuk kondisi kebencanaan, Knowledge Base untuk isi dokumen.
- Sampaikan pertanyaan lebih spesifik, termasuk nama gunung, waktu, judul dokumen, atau bagian yang dimaksud.
- Untuk pertanyaan dokumen, periksa apakah dokumen sudah selesai diproses dan teks relevan memang tersimpan.
- Informasi kebencanaan yang berubah cepat perlu dikonfirmasi pada kanal resmi; NARA adalah alat bantu, bukan sumber keputusan keselamatan tunggal.

Untuk masalah layanan atau pemasangan, lihat [panduan pemasangan](INSTALLATION_GUIDE.md).
