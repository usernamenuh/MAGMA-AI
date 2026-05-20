import json
import requests
import pandas as pd
from datetime import datetime
import os
from openai import OpenAI
import google.generativeai as genai
from deep_translator import GoogleTranslator

print(f"OPENAI_API_KEY:: {os.environ['OPENAI_API_KEY']}")
print(f"GEMINI_API_KEY:: {os.environ['GEMINI_API_KEY']}")


# =========================
# CONFIG
# =========================
API_URL = "http://0.0.0.0:8000/analyze"
GEO_LOCATION = (3.5952, 98.6722)

CSV_OUTPUT = f"advanced_testing_esdm_api_documentation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

REFERENCE_USED = "api documentation"
MODEL_SIZE_TYPE = "mistral-7b-GGUF"
TRANSLATION_DOC = "GoogleTranslator en→id"

# =========================
# TEST CASES
# =========================
TEST_CASES = [
    # "Apakah daerah saya aman saat ini?",
    # "Bagaimana kondisi aktivitas Gunung Sinabung sekarang?",
    # "Apakah Gunung Semeru sedang mengalami peningkatan aktivitas?",
    # "Apakah aktivitas Gunung Anak Krakatau perlu diwaspadai?",
    # "Kapan erupsi besar terakhir Gunung Agung yang mengeluarkan awan panas guguran?",
    # "Gunung apa saja yang sedang aktif saat ini?",
    # "Apakah terjadi erupsi gunung api baru-baru ini?",
    # "Bagaimana status gunung api di Indonesia hari ini?",
    # "Apakah gempa vulkanik berpengaruh terhadap erupsi?",
    # "Bagaimana kondisi terkini Gunung Agung?",
    # "Kapan gempa bumi terakhir?",
    # "Apakah wilayah saya rawan gempa bumi?",
    # "Bagaimana aktivitas terkini Gunung Kelud?",
    "Saya berencana naik Gunung Tambora minggu depan, bagaimana kondisi aktivitasnya saat ini?",
    "Apa status aktivitas Gunung Merapi berdasarkan laporan terbaru?",
    # "Apakah ada laporan awan panas guguran hari ini?",
    # "Berapa status level Gunung Semeru saat ini menurut PVMBG?",
    # "Apakah Gunung Lewotobi menunjukkan peningkatan aktivitas akhir-akhir ini?",
    # "Kapan laporan aktivitas terakhir Gunung Marapi diterbitkan?",
    # "Apakah tercatat gempa vulkanik di sekitar Gunung Merapi hari ini?",
    # "Gunung apa saja yang berstatus Waspada saat ini?",
    "Apakah ada gunung api yang berstatus Siaga atau Awas sekarang?",
    "Apakah terjadi peningkatan status gunung api dalam beberapa hari terakhir?",
    "Bagaimana ringkasan aktivitas gunung api berdasarkan laporan MAGMA terbaru?",
    "Apakah aktivitas gunung api hari ini berdampak ke wilayah sekitar?"
]

# =========================
# PROMPT ENGINEERING (SOURCE OF TRUTH)
# =========================
def build_prompt(user_input, response_text, location_context=""):
    is_failure = '"status": "error"' in response_text or '"status": "empty_data"' in response_text

    if is_failure:
        return f"""
The user asked: {user_input}
{location_context}

Instructions for the answer:
Use only the information available from the USER QUESTION and the CONVERSATION HISTORY.
Do not add knowledge or speculation.
If the information is not sufficient to answer, respond briefly and politely:
“Sorry, I’m not sure how to answer this. For accurate information, please refer to the official reports on the MAGMA, VSI, or MBG Portal websites.”
The answer must be only one paragraph and should not contain lists, bullet points, or any special markers.
"""
    else:
        return f"""
The user asked: {user_input}

Here is the data you must analyze:
{response_text}

Your task has two internal stages, but output ONLY the final stage:

Stage 1 (internal, DO NOT show to the user):
- Analyze the content of the data thoroughly.
- Identify general volcano conditions, status, visuals, weather, seismicity, hazards, and recommendations.
- Analyze the provided volcano data. Check for a "status" value:
  If you find 1 → Level I (Normal)
  If 2 → Level II (Waspada)
  If 3 → Level III (Siaga)
  If 4 → Level IV (Awas)
  If missing → do not mention alert level

Stage 2 (FINAL OUTPUT – only this must be shown to the user):
- One clear, concise, natural response in English
- No titles, numbers, bullets, or fabricated information

Mandatory rules:
- Clear, professional English
- Short, direct sentences
- Easy for the general public to understand
"""

def build_llm_messages(user_input, api_response, geo_location, max_len=2000):
    response_text = json.dumps(api_response, indent=2, ensure_ascii=False)
    if len(response_text) > max_len:
        response_text = response_text[:max_len]

    location_context = f"\nLokasi pengguna (latitude, longitude): {geo_location}\n"

    user_prompt = build_prompt(user_input, response_text, location_context)

    system_prompt = (
        "Anda adalah asisten kebencanaan Indonesia. "
        "Jawab hanya berdasarkan data yang diberikan. "
        "Gunakan Bahasa Indonesia formal dalam satu paragraf. "
        "Tanpa bullet, daftar, atau informasi tambahan di luar data."
    )

    return system_prompt, user_prompt

# =========================
# OPENAI CLIENT
# =========================
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY)

def call_openai(system_prompt: str, user_prompt: str) -> str:
    """
    Calls OpenAI using the EXACT same prompt used in the pipeline.
    Returns Indonesian output after GoogleTranslator en→id.
    """

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  # baseline comparison model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=512,
    )

    raw_output = response.choices[0].message.content.strip()

    cleaned_output = GoogleTranslator(
        source="en",
        target="id"
    ).translate(raw_output)

    return cleaned_output

# =========================
# GEMINI CLIENT
# =========================
genai.configure(api_key=os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY)

gemini_model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 2048,
    }
)

def call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Calls Gemini using the EXACT same prompt logic.
    System prompt is injected at the top to preserve parity.
    Returns Indonesian output after GoogleTranslator en→id.
    """

    combined_prompt = f"""{system_prompt}

USER PROMPT:
{user_prompt}
"""

    response = gemini_model.generate_content(combined_prompt)

    raw_output = "".join(
        part.text for part in response.candidates[0].content.parts
    ).strip()
    print("raw output:", raw_output)

    cleaned_output = GoogleTranslator(
        source="en",
        target="id"
    ).translate(raw_output)

    return cleaned_output

# =========================
# MAIN TEST RUNNER
# =========================
def main():
    results = []

    for idx, question in enumerate(TEST_CASES, 1):
        print(f"[{idx}/{len(TEST_CASES)}] Testing: {question}")

        payload = {
            "user_input": question,
            "geo_location": GEO_LOCATION
        }
        headers = {
            "Authorization": "Bearer sk-tagflow-f3f5f86383524306bfcc76f0511eac64",
            "Content-Type": "application/json"
        }
        output = ""
        openai_answer=""
        gemini_answer=""

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
            # response = requests.post(API_URL, json=payload, timeout=720)
            # response.raise_for_status()
            output = obj.get("output", "")
            api_json = obj.get("response", "")
            system_prompt, user_prompt = build_llm_messages(
                question,
                api_json,
                GEO_LOCATION
            )
            print(f"[{idx}/{len(TEST_CASES)}] Esdm Answer: {output}")

            openai_answer = call_openai(system_prompt, user_prompt)
            print(f"[{idx}/{len(TEST_CASES)}] OpenAI Answer: {openai_answer}")

            gemini_answer = call_gemini(system_prompt, user_prompt)
            print(f"[{idx}/{len(TEST_CASES)}] Gemini Answer: {gemini_answer}")

            results.append({
                "reference_used": REFERENCE_USED,
                "question": question,
                "esdm_answer": output,
                "api_call": obj.get("api_call", ""),
                "response": obj.get("response", ""),
                "prompt_engineering_used": user_prompt.strip(),
                "model_size_type": MODEL_SIZE_TYPE,
                "translation": TRANSLATION_DOC,
                "openai_answer": openai_answer,
                "gemini_answer": gemini_answer
            })

        except Exception as e:
            print(f"[{idx}/{len(TEST_CASES)}] Exception: {e}")
            results.append({
                "reference_used": REFERENCE_USED,
                "question": question,
                "esdm_answer": output,
                "api_call": "",
                "response": "",
                "prompt_engineering_used": "",
                "model_size_type": MODEL_SIZE_TYPE,
                "translation": TRANSLATION_DOC,
                "openai_answer": openai_answer,
                "gemini_answer": gemini_answer
            })

    df = pd.DataFrame(results)
    df.to_csv(CSV_OUTPUT, index=False)
    print(f"\n✅ Test completed. CSV saved to: {CSV_OUTPUT}")

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main()
