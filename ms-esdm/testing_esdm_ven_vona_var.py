import json
import requests
from datetime import datetime

API_URL = "http://0.0.0.0:8000/analyze"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f"testing_esdm_ven_vona_var_results_{timestamp}.txt"


test_cases = [
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
]

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for idx, case in enumerate(test_cases, start=1):
            question = case["question"]
            payload = {"user_input": question}

            print(f"🔹 [{idx}/{len(test_cases)}] Testing: {question}")

            headers = {
                "Authorization": "Bearer sk-tagflow-f3f5f86383524306bfcc76f0511eac64",
                "Content-Type": "application/json"
            }

            try:
                # Synchronous request with timeout
                response = requests.post(
                    API_URL,
                    json=payload,
                    headers=headers,
                    timeout=720   # prevents infinite hanging
                )

                # Raise exception for HTTP errors
                response.raise_for_status()

                result_text = response.text.strip()

                block = (
                    # f"[{idx}] Type: {case['type']}\n"
                    # f"Question: {question}\n"
                    f"\n{result_text},"
                    # f"{'='*80}\n\n"
                )

                print(block)
                f.write(block)

            except Exception as e:
                error = {
                    "date": "",
                    "status": "internal server error",
                    "user_input": question,
                    "api_call": "",
                    "output": e
                }
                error_msg = (
                    f"\n{error},"
                )
                print(error_msg)
                f.write(error_msg)

    print(f"\n✅ All results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()