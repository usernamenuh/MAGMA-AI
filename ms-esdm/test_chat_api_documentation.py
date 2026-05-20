import json
import requests
from datetime import datetime
import pandas as pd


API_URL = "http://16.78.198.138/api/analyze"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_OUTPUT = f"testing_esdm_api_documentation_results_{timestamp}.csv"


# ----------------------------
# Test cases
# ----------------------------
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

    {"type": "GENERAL", "question": "Apakah daerah saya aman?"},
    {"type": "GENERAL", "question": "Bagaimana aktivitas gunung sinabung?"},
    {"type": "GENERAL", "question": "Bagaimana keadaan gunung semeru?"},
]



esdm_test=[
    {
        "question": "Apakah posisi saya dalam bahaya sekarang?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "info gerakan tanah terakhir",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "apa yang kamu lakukann",
        "description": "Test case for capability",
        "expected_intent": "capability",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "halo",
        "description": "Test case for greeting",
        "expected_intent": "greeting",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "bagaimana status tanah longsor?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Bagaimana status pergerakan tanah terdekat dengan saya?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Apakah wilayah saya rawan gempa bumi?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Gunung apa saja yang sedang aktif saat ini?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "kamu siapa?",
        "description": "Test case for identity",
        "expected_intent": "identity",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "bisakah anda prediksi tornado?",
        "description": "Test case for out_of_scope",
        "expected_intent": "out_of_scope",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "mnurut mu bahlil gimana?",
        "description": "Test case for out_of_scope",
        "expected_intent": "out_of_scope",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Hai apakabar?",
        "description": "Test case for greeting",
        "expected_intent": "greeting",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Apakah posisi saya dalam bahaya sekarang?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Apakah lokasi di yogyakarta aman?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Ada berapa gunung api di indonesia?",
        "description": "Test case for count_list_query",
        "expected_intent": "count_list_query",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Bagaimana status gunung sumeru?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Bagaimana kondisi aktivitas Gunung Sinabung sekarang?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Apakah aktivitas Gunung Anak Krakatau perlu diwaspadai?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Kapan erupsi besar terakhir Gunung Agung yang mengeluarkan awan panas guguran?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Gunung apa saja yang sedang aktif saat ini?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Apakah wilayah saya rawan gempa bumi?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "Bagaimana status pergerakan tanah terdekat dengan saya?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "bagaimana status tanah longsor?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "kamu bisa apa saja",
        "description": "Test case for capability",
        "expected_intent": "capability",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "kapan letusan terakhir sumeru",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "bagaimana status tanah longsor?",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "status tanah longsor terdekat dengan saya",
        "description": "Test case for technical",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    },
    {
        "question": "apakah anda tau lokasi saya sekarang?",
        "description": "Test case for location_required",
        "expected_intent": "technical",
        "geo_location": {
            "lat": 3.5952,
            "lon": 98.6722
        }
    }
]

# ----------------------------
# Main testing + CSV export
# ----------------------------
def main():

    results = []

    for idx, case in enumerate(test_cases, start=1):
        question = case["question"]
        print(f"🔹 [{idx}/{len(test_cases)}] Testing: {question}")

        payload = {
            "user_input": question,
            "geo_location": [3.5952, 98.6722]
        }

        headers = {
            "Authorization": "Bearer sk-tagflow-f3f5f86383524306bfcc76f0511eac64",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                API_URL,
                json=payload,
                headers=headers,
                timeout=720
            )
            response.raise_for_status()

            raw = response.text.strip()
            obj = json.loads(raw)

            results.append({
                "status": obj.get("status", ""),
                # "type": case["type"],
                "user_input": question,
                "api_call": obj.get("api_call", ""),
                "response": obj.get("response", ""),
                "output": obj.get("output", "")
            })

        except Exception as e:
            results.append({
                "status": "internal server error",
                # "type": case["type"],
                "user_input": question,
                "api_call": "",
                "response": "",
                "output": str(e)
            })

    # ----------------------------
    # Export to CSV
    # ----------------------------
    df = pd.DataFrame(results)
    df.to_csv(CSV_OUTPUT, index=False)

    print(f"\n✅ Done! Saved CSV to: {CSV_OUTPUT}")


def test_inference_classifier():

    results = []

    for idx, case in enumerate(esdm_test, start=1):
        question = case["question"]
        print(f"🔹 [{idx}/{len(esdm_test)}] Testing: {question}")

        payload = {
            "user_input": question,
            "geo_location": [3.5952, 98.6722]
        }

        headers = {
            "Authorization": "Bearer sk-tagflow-f3f5f86383524306bfcc76f0511eac64",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                API_URL,
                json=payload,
                headers=headers,
                timeout=720
            )
            response.raise_for_status()

            raw = response.text.strip()
            obj = json.loads(raw)

            results.append({
                "status": obj.get("status", ""),
                "user_input": question,
                "api_call": obj.get("api_call", ""),
                "response": obj.get("response", ""),
                "output": obj.get("output", "")
            })

        except Exception as e:
            results.append({
                "status": "internal server error",
                # "type": case["type"],
                "user_input": question,
                "api_call": "",
                "response": "",
                "output": str(e)
            })

    # ----------------------------
    # Export to CSV
    # ----------------------------
    df = pd.DataFrame(results)
    df.to_csv(CSV_OUTPUT, index=False)

    print(f"\n✅ Done! Saved CSV to: {CSV_OUTPUT}")


def interactive_test_demo():
    """
    Interactive demo so user can type queries manually.
    Type 'exit' or 'quit' to stop.
    """

    print("\n🧪 Interactive Intent Classifier Demo")
    print("Type your question and press Enter")
    print("Type 'exit' or 'quit' to stop\n")

    idx = 1

    while True:
        user_input = input("🧑 User > ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("\n👋 Exiting interactive demo...")
            break

        payload = {
            "user_input": user_input,
            "geo_location": [3.5952, 98.6722]
        }

        headers = {
            "Authorization": "Bearer sk-tagflow-f3f5f86383524306bfcc76f0511eac64",
            "Content-Type": "application/json"
        }

        print(f"\n🔹 [{idx}] Sending request...")

        try:
            response = requests.post(
                API_URL,
                json=payload,
                headers=headers,
                timeout=720
            )
            response.raise_for_status()

            obj = response.json()
            print("api_call :", obj.get("api_call"))
            print("output :", obj.get("output"))

        except Exception as e:
            print("❌ Error:")
            print(str(e))

        print("-" * 60)
        idx += 1

if __name__ == "__main__":
    # main()
    # test_inference_classifier()
    interactive_test_demo()