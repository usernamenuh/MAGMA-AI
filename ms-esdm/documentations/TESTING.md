# **API Testing Documentation**

This document describes the testing workflow and test scenarios for running the automated testing scripts that validate the `/analyze` and `/knowledge/analyze` endpoint.

There are **two types of tests**:

1. **`test_chat_api_documentation.py`** — Analyze using **data retrieved from API documentation endpoints**
2. **`test_chat_knowledge_base.py`** — Analyze using **data from the uploaded knowledge base**

Both scripts share a similar testing workflow but use different data sources.

---

## **1. Overview**

The testing scripts evaluate the **ESDM Analysis API** by sending predefined questions across four categories:

* **VONA** — Volcano Observatory Notice for Aviation
* **VEN** — Volcano Eruption Notice
* **VAR** — Volcano Activity Report
* **General Queries** — Natural language user questions

Each test runs through the `/analyze` endpoint, extracts structured fields, and logs all results into a CSV.

---

## **2. Test Types**

### **A. API Documentation Test (`test_chat_api_documentation.py`)**

This test fetches real data directly from API documentation sources, then evaluates how accurately `/analyze` interprets and summarizes it.


### **B. Knowledge Base Test (`test_chat_knowledge_base.py`)**

This test purpose to test `/knowledge/analyze` API that using curated, stable knowledge-base chunks as the data source.

---

## **3. How the Testing Workflow Works**

For both scripts:

1. Load predefined test cases for questions.
2. Send each question to:

   ```
   http://0.0.0.0:8000/analyze
   ```
   or 

   ```
   http://0.0.0.0:8000/knowledge/analyze
   ```
3. Include Bearer Authorization header.
4. Receive and parse JSON results.
5. Convert markdown output to clean plain text.
6. Save results to CSV with timestamp.

The generated file will follow this pattern:

```
testing_esdm_api_documentation_results_<timestamp>.csv
```
or
```
testing_esdm_knowledge_base_results_<timestamp>.csv
```
---

## **4. Test Case List**
### **A. API DOCUMENTATION TEST CASE**
```
[
    {"type": "VONA", "question": "Tampilkan pembaruan terbaru terkait penerbangan dan aktivitas gunung api."},
    {"type": "VONA", "question": "Berikan pemberitahuan terkini untuk Gunung Semeru."},
    {"type": "VONA", "question": "Tampilkan peringatan global terkini terkait aktivitas gunung berapi."},
    {"type": "VONA", "question": "Tampilkan laporan yang berisi perubahan arah atau intensitas abu vulkanik."},
    {"type": "VONA", "question": "Perlihatkan warna tingkat peringatan terkini untuk Gunung Ili Lewotolok."},
    {"type": "VONA", "question": "Ambil laporan abu volkanik dengan nomor UUID 6000."},
    {"type": "VONA", "question": "Tampilkan pemberitahuan yang berkaitan dengan lalu lintas udara di Sinabung."},
    {"type": "VONA", "question": "Siapa yang mengeluarkan pemberitahuan abu vulkanik terbaru?"},
    {"type": "VONA", "question": "Daftar gunung api yang memiliki peringatan penerbangan aktif."},
    {"type": "VONA", "question": "Tampilkan seluruh laporan yang diterbitkan pada bulan Juli 2021."},

    {"type": "VEN", "question": "Tampilkan peristiwa letusan terbaru di Indonesia."},
    {"type": "VEN", "question": "Daftar semua letusan gunung api yang tercatat pada tahun 2021."},
    {"type": "VEN", "question": "Berikan detail tentang letusan dengan ID 937."},
    {"type": "VEN", "question": "Saring data letusan berdasarkan nama gunung, misalnya Gunung Sinabung."},
    {"type": "VEN", "question": "Tampilkan foto-foto letusan terbaru."},
    {"type": "VEN", "question": "Ambil deskripsi dari peristiwa letusan terbaru."},
    {"type": "VEN", "question": "Dapatkan laporan letusan dengan tingkat aktivitas ‘Level III (Siaga)’."},
    {"type": "VEN", "question": "Tampilkan letusan yang terjadi di zona waktu WITA."},
    {"type": "VEN", "question": "Siapa yang melaporkan letusan Gunung Ili Lewotolok?"},
    {"type": "VEN", "question": "Tampilkan semua letusan yang terjadi pada bulan Agustus 2021."},

    {"type": "VAR", "question": "Tampilkan laporan aktivitas gunung api terbaru."},
    {"type": "VAR", "question": "Tampilkan laporan harian untuk Gunung Agung."},
    {"type": "VAR", "question": "Ambil laporan aktivitas untuk Gunung Agung dengan noticenumber 202108062400."},
    {"type": "VAR", "question": "Cari laporan aktivitas yang memuat kata kunci 'Agung'."},
    {"type": "VAR", "question": "Tampilkan laporan terbaru untuk Gunung Sinabung."},
    {"type": "VAR", "question": "Tampilkan laporan 1 tahun terakhir dengan code SIN."},
    {"type": "VAR", "question": "Dapatkan laporan yang berisi pengamatan kolom abu vulkanik."},
    {"type": "VAR", "question": "Siapa yang menyusun laporan aktivitas terbaru untuk Gunung Agung?"},
    {"type": "VAR", "question": "Daftar gunung api yang saat ini dimonitor dalam sistem VAR."},
    {"type": "VAR", "question": "Tampilkan semua laporan aktivitas dari bulan Januari 2021."},

    {"type": "GENERAL", "question": "Apakah daerah saya aman?"},
    {"type": "GENERAL", "question": "Bagaimana aktivitas gunung sinabung?"},
    {"type": "GENERAL", "question": "Bagaimana keadaan gunung semeru?"},
]
```
### **B.KNOWLEDGE BASE TEST CASE**
```
[
  "Apa itu kegiatan DPIS dan EWS yang dilaksanakan di Bali?",
  "Kapan kegiatan FGD Konsinyering Desktop Studi Modernisasi Peralatan Pemantauan Gunung Api dilaksanakan?",
  "Apa tujuan dari FGD modernisasi peralatan pemantauan gunung api?",
  "Apa kendala utama dalam modernisasi peralatan pemantauan gunung api?",
  "Gunung api apa saja yang dibahas dalam rencana modernisasi?",
  "Apa tujuan supervisi instalasi peralatan pemantauan gerakan tanah di Ponorogo?",
  "Siapa Ketua Tim pada kegiatan supervisi peralatan pemantauan gerakan tanah Ponorogo?",
  "Berapa lama kegiatan supervisi instalasi pemantauan gerakan tanah Ponorogo berlangsung?",
  "Siapa yang menandatangani lembar pengesahan dalam dokumen supervisi?"
]
```
---

## **5. CSV Output Structure**

| Column       | Description                                  | Source         |
|--------------|----------------------------------------------|----------------|
| `date`       | Date returned by the API                     | Both           |
| `status`     | success / failure                            | Both           |
| `type`       | VONA / VEN / VAR / GENERAL                   | API            |
| `user_input` | Question being tested                        | Both           |
| `api_call`   | Extracted API call from the model            | API            |
| `response`   | Raw JSON returned from the API               | API            |
| `references` | Reference that contain the document and page | Knowledge Base |
| `output`     | Cleaned, plain-text explanation              |    Both        |

---

## **6. Running Each Test**

### **A. Test using API Documentation Data**

```bash
python test_chat_api_documentation.py
```

### **B. Test using Knowledge Base Data**

```bash
python test_chat_knowledge_base.py
```

### **Completion Message**

```
✅ Done! Saved CSV to: {document_name}.csv
```
