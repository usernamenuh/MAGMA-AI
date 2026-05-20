import json
import sys

import requests
from datetime import datetime
import pandas as pd
from rapidfuzz import fuzz

API_URL = "http://0.0.0.0:8000/knowledge/analyze"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_OUTPUT = f"testing_esdm_knowledge_base_results_{timestamp}.csv"

# -------------------------------------------------
# Test cases with expected keywords
# -------------------------------------------------
test_cases = [
    {
        "query": "Apa itu kegiatan DPIS dan EWS yang dilaksanakan di Bali?",
        "expected_keywords": [
            "Peresmian (Launching) DPIS dan EWS",
            "Diseminasi Informasi Bencana melalui Siaran TV Digital",
            "The Trans Resort Bali",
            "23-24 September 2024",
        ]
    },
    {
        "query": "Kapan kegiatan FGD Konsinyering Desktop Studi Modernisasi Peralatan Pemantauan Gunung Api dilaksanakan?",
        "expected_keywords": [
            "5 – 7 Mei 2024",
            "kegiatan inti berlangsung pada 6 Mei 2024"
        ]
    },
    {
        "query": "Apa tujuan dari FGD modernisasi peralatan pemantauan gunung api?",
        "expected_keywords": [
            "mendiskusikan dan mengevaluasi rencana lokasi modernisasi peralatan pemantau",
            "mendukung evaluasi mitigasi bencana geologi",
            "memastikan keselarasan lokasi stasiun dengan sistem telemetri"
        ]
    },
    {
        "query": "Apa kendala utama dalam modernisasi peralatan pemantauan gunung api?",
        "expected_keywords": [
            "perizinan penggunaan lahan",
            "akses lokasi yang sulit",
            "proses pembangunan stasiun memakan waktu",
            "kesenjangan realisasi pemasangan sensor"
        ]
    },
    {
        "query": "Gunung api apa saja yang dibahas dalam rencana modernisasi?",
        "expected_keywords": [
            "Gunung Api Gede",
            "Gunung Api Awu",
            "Gunung Api Kerinci",
            "Gunung Api Dukono",
            "Gunung Api Tangkuban Parahu"
        ]
    },
    {
        "query": "Apa tujuan supervisi instalasi peralatan pemantauan gerakan tanah di Ponorogo?",
        "expected_keywords": [
            "menindaklanjuti kegiatan Survei Lokasi",
            "memastikan pekerjaan sesuai spesifikasi teknis",
            "mendukung program instalasi peralatan pemantauan gerakan tanah"
        ]
    },
    {
        "query": "Siapa Ketua Tim pada kegiatan supervisi peralatan pemantauan gerakan tanah Ponorogo?",
        "expected_keywords": [
            "Achmad Fathoni"
        ]
    },
    {
        "query": "Berapa lama kegiatan supervisi instalasi pemantauan gerakan tanah Ponorogo berlangsung?",
        "expected_keywords": [
            "09 - 14 September 2024"
        ]
    },
    {
        "query": "Siapa yang menandatangani lembar pengesahan dalam dokumen supervisi?",
        "expected_keywords": [
            "Ahmad Barnes",
            "Achmad Fathoni",
            "Pejabat Pembuat Komitmen"
        ]
    },
    {
        "query": "Di mana lokasi pelaksanaan kegiatan Launching DPIS dan EWS?",
        "expected_keywords": [
            "The Trans Resort Bali"
        ]
    },
    {
        "query": "Berapa lama kegiatan Launching DPIS dan EWS di Bali berlangsung?",
        "expected_keywords": [
            "2 hari",
            "23-24 September 2024"
        ]
    },
    {
        "query": "Apa tema FGD yang dibahas dalam laporan tersebut?",
        "expected_keywords": [
            "Konsinyering Desktop Studi Modernisasi Peralatan Pemantauan Gunung Api"
        ]
    },
    {
        "query": "Siapa Ketua Tim Instrumentasi, Data dan Informasi yang memberikan sambutan pada FGD?",
        "expected_keywords": [
            "Ahmad Barnes"
        ]
    },
    {
        "query": "Kapan FGD dilaksanakan secara keseluruhan dan kapan kegiatan intinya?",
        "expected_keywords": [
            "5 – 7 Mei 2024",
            "kegiatan inti berlangsung pada tanggal 6 Mei 2024"
        ]
    },
    {
        "query": "Apa saja masalah utama yang diidentifikasi dalam FGD modernisasi peralatan?",
        "expected_keywords": [
            "perizinan penggunaan lahan",
            "akses lokasi yang sulit",
            "proses pembangunan stasiun dan instalasi peralatan memakan waktu"
        ]
    },
    {
        "query": "Gunung api mana yang mengalami kendala dalam studi desktop karena belum adanya perencanaan dari Tim Kerja?",
        "expected_keywords": [
            "Gunung Api Dukono"
        ]
    },
    {
        "query": "Apa maksud kegiatan supervisi instalasi peralatan pemantauan gerakan tanah di Ponorogo?",
        "expected_keywords": [
            "menindaklanjuti kegiatan Survei Lokasi",
            "Peralatan Pemantauan Gerakan Tanah Kabupaten Ponorogo"
        ]
    },
    {
        "query": "Apa tujuan supervisi instalasi pemantauan gerakan tanah sesuai dokumen?",
        "expected_keywords": [
            "memastikan bahwa pekerjaan yang dilakukan oleh penyedia sesuai dengan spesifikasi teknis"
        ]
    },
    {
        "query": "Siapa saja anggota tim supervisi instalasi pemantauan gerakan tanah Ponorogo?",
        "expected_keywords": [
            "Achmad Fathoni",
            "Iyan Mulyana",
            "Asep Nur"
        ]
    },
    {
        "query": "Siapa saja yang menandatangani lembar pengesahan dalam proposal supervisi Ponorogo?",
        "expected_keywords": [
            "Ahmad Barnes",
            "Achmad Fathoni",
            "Pejabat Pembuat Komitmen"
        ]
    }

]

test_cases_en = [
    {
        "query": "What are the DPIS and EWS activities conducted in Bali?",
        "expected_keywords": [
            "Launching of DPIS and EWS",
            "Dissemination of Disaster Information through Digital TV Broadcasting",
            "The Trans Resort Bali",
            "23–24 September 2024",
        ]
    },
    {
        "query": "When was the FGD Consignment Desktop Study on the Modernization of Volcanic Monitoring Equipment conducted?",
        "expected_keywords": [
            "5–7 May 2024",
            "the core activity took place on 6 May 2024"
        ]
    },
    {
        "query": "What was the purpose of the FGD on the modernization of volcanic monitoring equipment?",
        "expected_keywords": [
            "to discuss and evaluate the planned locations for the modernization of monitoring equipment",
            "to support the evaluation of geological disaster mitigation",
            "to ensure alignment of station locations with the telemetry system"
        ]
    },
    {
        "query": "What were the main challenges in the modernization of volcanic monitoring equipment?",
        "expected_keywords": [
            "land-use permitting",
            "difficult site access",
            "station construction process is time-consuming",
            "gap in the realization of sensor installation"
        ]
    },
    {
        "query": "Which volcanoes were discussed in the modernization plan?",
        "expected_keywords": [
            "Mount Gede",
            "Mount Awu",
            "Mount Kerinci",
            "Mount Dukono",
            "Mount Tangkuban Parahu"
        ]
    },
    {
        "query": "What was the purpose of the supervision of landslide monitoring equipment installation in Ponorogo?",
        "expected_keywords": [
            "to follow up on the Site Survey activity",
            "to ensure that the work complies with technical specifications",
            "to support the installation program for landslide monitoring equipment"
        ]
    },
    {
        "query": "Who was the Team Leader for the supervision of landslide monitoring equipment in Ponorogo?",
        "expected_keywords": [
            "Achmad Fathoni"
        ]
    },
    {
        "query": "How long did the supervision of landslide monitoring equipment installation in Ponorogo take place?",
        "expected_keywords": [
            "09–14 September 2024"
        ]
    },
    {
        "query": "Who signed the approval sheet in the supervision document?",
        "expected_keywords": [
            "Ahmad Barnes",
            "Achmad Fathoni",
            "Commitment Making Officer"
        ]
    },
    {
        "query": "Where was the DPIS and EWS Launching activity conducted?",
        "expected_keywords": [
            "The Trans Resort Bali"
        ]
    },
    {
        "query": "How long did the DPIS and EWS Launching activity in Bali last?",
        "expected_keywords": [
            "2 days",
            "23–24 September 2024"
        ]
    },
    {
        "query": "What was the theme of the FGD discussed in the report?",
        "expected_keywords": [
            "Consignment Desktop Study on the Modernization of Volcanic Monitoring Equipment"
        ]
    },
    {
        "query": "Who was the Head of the Instrumentation, Data, and Information Team who delivered the opening remarks at the FGD?",
        "expected_keywords": [
            "Ahmad Barnes"
        ]
    },
    {
        "query": "When was the FGD conducted overall, and when did the core activity take place?",
        "expected_keywords": [
            "5–7 May 2024",
            "the core activity took place on 6 May 2024"
        ]
    },
    {
        "query": "What were the main issues identified in the FGD on equipment modernization?",
        "expected_keywords": [
            "land-use permitting",
            "difficult site access",
            "station construction and equipment installation are time-consuming"
        ]
    },
    {
        "query": "Which volcano faced constraints in the desktop study due to the absence of planning from the Working Team?",
        "expected_keywords": [
            "Mount Dukono"
        ]
    },
    {
        "query": "What was the purpose of the supervision activity for landslide monitoring equipment installation in Ponorogo?",
        "expected_keywords": [
            "to follow up on the Site Survey activity",
            "Landslide Monitoring Equipment of Ponorogo Regency"
        ]
    },
    {
        "query": "What was the objective of the supervision of landslide monitoring equipment installation according to the document?",
        "expected_keywords": [
            "to ensure that the work carried out by the provider complies with technical specifications"
        ]
    },
    {
        "query": "Who were the members of the supervision team for landslide monitoring equipment installation in Ponorogo?",
        "expected_keywords": [
            "Achmad Fathoni",
            "Iyan Mulyana",
            "Asep Nur"
        ]
    },
    {
        "query": "Who signed the approval sheet in the Ponorogo supervision proposal?",
        "expected_keywords": [
            "Ahmad Barnes",
            "Achmad Fathoni",
            "Commitment Making Officer"
        ]
    }
]

# test_cases = [{
#         "query": "Apa tujuan supervisi instalasi pemantauan gerakan tanah sesuai dokumen?",
#         "expected_keywords": [
#             "memastikan bahwa pekerjaan yang dilakukan oleh penyedia sesuai dengan spesifikasi teknis"
#         ]
#     }]


def evaluate_keywords(output: str, expected_keywords: list, threshold: int = 50):
    """
    Evaluate keyword presence using fuzzy similarity instead of raw substring match.

    threshold: minimum similarity score (0–100) to consider a keyword 'matched'.
    """

    output_lower = output.lower()

    matched = []
    missing = []

    for kw in expected_keywords:
        kw_lower = kw.lower()

        # Compute similarity between keyword and the entire output
        similarity = fuzz.partial_ratio(kw_lower, output_lower)

        if similarity >= threshold:
            matched.append({"keyword": kw, "similarity": similarity})
        else:
            missing.append({"keyword": kw, "similarity": similarity})

    score = round((len(matched) / len(expected_keywords)) * 100, 2)
    all_matched = len(missing) == 0
    print(f"matched: {matched} | missing: {missing} | score: {score} | all_matched: {all_matched}")
    return matched, missing, score, all_matched

# -------------------------------------------------
# Main
# -------------------------------------------------
def main(lang):
    results = []
    test_cases_final = test_cases_en if lang == 'en' else test_cases
    for idx, case in enumerate(test_cases_final, start=1):
        question = case["query"]
        expected_keywords = case["expected_keywords"]

        print(f"🔹 [{idx}/{len(test_cases_final)}] Testing: {question}")

        payload = {"user_input": question}

        headers = {
            "Authorization": "Bearer sk-tagflow-f3f5f86383524306bfcc76f0511eac64",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                API_URL if lang =='id' else API_URL+'-en',
                json=payload,
                headers=headers,
                timeout=720
            )
            response.raise_for_status()

            obj = response.json()

            # ---- keyword evaluation ----
            matched, missing, score, all_matched = evaluate_keywords(
                obj.get("output", ""), expected_keywords
            )

            results.append({
                "date": obj.get("date", ""),
                "status": obj.get("status", ""),
                "user_input": question,
                "results": obj.get("results", ""),
                "output": obj.get("output", ""),
                "expected_keywords": ", ".join(expected_keywords),
                "matched_keywords": ", ".join(
                    [f"{m['keyword']} ({m['similarity']})" for m in matched]
                ),
                "missing_keywords": ", ".join(
                    [f"{m['keyword']} ({m['similarity']})" for m in missing]
                ),
                "match_score": score,
                "all_matched": all_matched
            })

        except Exception as e:
            results.append({
                "date": "",
                "status": "internal error",
                "user_input": question,
                "expected_keywords": ", ".join(expected_keywords),
                "matched_keywords": "",
                "missing_keywords": "",
                "match_score": 0,
                "all_matched": False,
                "output": str(e)
            })

    df = pd.DataFrame(results)
    df.to_csv(CSV_OUTPUT, index=False)

    print(f"\n✅ Done! Saved CSV to: {CSV_OUTPUT}")


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "id"
    main(lang)
