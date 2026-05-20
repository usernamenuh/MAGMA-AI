# inference.py
import os
import json
import re
import joblib
import numpy as np
from fastembed import TextEmbedding

# ======================================================
# Configuration
# ======================================================
MODELS_DIR = "output2/models"
CONFIDENCE_THRESHOLD = 0.55

# ======================================================
# Text cleaning (MUST MATCH TRAINING & EVAL)
# ======================================================
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r"[^\w\s]", "", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ======================================================
# Static Responses
# ======================================================
STATIC_RESPONSES = {
    "GREETING": (
        "Halo! Saya MAGMA dari PVMBG, Badan Geologi, Kementerian ESDM. "
        "Saya siap membantu menjawab pertanyaan seputar bahaya geologi."
    ),
    "IDENTITY": (
        "Saya MAGMA Indonesia, Asisten Virtual Mitigasi Bencana Geologi PVMBG."
    ),
    "CAPABILITY": (
        "Saya dapat memberikan informasi mengenai aktivitas gunung api, "
        "gempa bumi, tsunami, dan gerakan tanah."
    ),
}

OOS_RESPONSE = (
    "Maaf, saya hanya dapat menjawab pertanyaan umum tentang layanan MAGMA. "
    "Silakan ajukan pertanyaan terkait kemampuan atau identitas saya."
)

# ======================================================
# Load Models
# ======================================================
def load_models():
    print("📂 Loading models...")

    metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        print(f"  ✓ Model version: {metadata.get('timestamp')}")
        print(f"  ✓ Classes: {metadata.get('classes')}")
    else:
        metadata = {}
        print("  ⚠️ No metadata found")

    try:
        intent_model = joblib.load(os.path.join(MODELS_DIR, "intent_xgb.joblib"))
        encoder = joblib.load(os.path.join(MODELS_DIR, "intent_encoder.joblib"))
        occ = joblib.load(os.path.join(MODELS_DIR, "intent_occ.joblib"))
        embedder_info = joblib.load(os.path.join(MODELS_DIR, "intent_embedder_info.joblib"))

        embedder = TextEmbedding(model_name=embedder_info["model_name"])

        print("  ✓ Intent classifier loaded")
        print("  ✓ Encoder loaded")
        print("  ✓ OOS detector loaded")
        print("  ✓ Embedder initialized")

        return {
            "intent_model": intent_model,
            "encoder": encoder,
            "occ": occ,
            "embedder": embedder,
            "metadata": metadata,
        }

    except FileNotFoundError as e:
        print(f"❌ Model loading failed: {e}")
        return None

# ======================================================
# Intent Detection
# ======================================================
def detect_conversational_intent(user_input: str, models):
    raw = user_input.lower().strip()

    # Ultra-fast greeting shortcut
    if raw in {"halo", "hai", "hi", "hello"}:
        return "GREETING", STATIC_RESPONSES["GREETING"]

    cleaned = clean_text(user_input)

    if cleaned != raw:
        print(f"  🔧 Cleaned: '{user_input}' → '{cleaned}'")

    embedding = list(models["embedder"].embed([cleaned]))[0]
    X = np.array([embedding.flatten()])

    # Out-of-scope detection
    if models["occ"].predict(X)[0] == -1:
        return "OUT_OF_SCOPE", None

    # Intent classification
    probs = models["intent_model"].predict_proba(X)[0]
    idx = int(np.argmax(probs))
    confidence = float(probs[idx])
    intent = models["encoder"].inverse_transform([idx])[0]

    print(f"  📊 Confidence: {confidence:.3f}")

    if confidence < CONFIDENCE_THRESHOLD:
        return "OUT_OF_SCOPE", None

    return intent, STATIC_RESPONSES.get(intent)

# ======================================================
# Test Suite
# ======================================================
def run_test_suite(models):
    tests = [
        ("selamat pagi", "GREETING"),
        ("halo", "GREETING"),
        ("siapa kamu", "IDENTITY"),
        ("kamu bisa apa", "CAPABILITY"),
        ("berapa harga bitcoin", "OUT_OF_SCOPE"),
    ]

    print("\n🧪 Running tests")
    print("-" * 50)

    correct = 0
    for text, expected in tests:
        pred, _ = detect_conversational_intent(text, models)
        ok = "✓" if pred == expected else "✗"
        print(f"{ok} {text:30s} → {pred}")
        correct += int(pred == expected)

    print(f"\nAccuracy: {correct}/{len(tests)}")

# ======================================================
# Main
# ======================================================
def main():
    models = load_models()
    if not models:
        return

    run_test_suite(models)

    print("\n💬 Interactive mode (type 'exit')")
    while True:
        text = input("\nYou > ").strip()
        if text.lower() in {"exit", "quit"}:
            break

        intent, response = detect_conversational_intent(text, models)
        print(f"🔎 Intent   : {intent}")
        print(f"🤖 Response : {response or OOS_RESPONSE}")

if __name__ == "__main__":
    main()
