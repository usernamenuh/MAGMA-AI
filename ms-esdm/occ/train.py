import os
import random
import pandas as pd
import joblib
import numpy as np
import xgboost as xgb
import re
import json
from datetime import datetime

from fastembed import TextEmbedding
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import OneClassSVM


# ======================================================
# Configuration
# ======================================================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Create output directory structure
OUTPUT_DIR = "output2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Create subdirectories
MODELS_DIR = os.path.join(OUTPUT_DIR, "models")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Training timestamp
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ======================================================
# Text cleaning function
# ======================================================
def clean_text(text):
    """Clean text by removing punctuation and normalizing"""
    if not isinstance(text, str):
        text = str(text)
    # Remove punctuation but keep letters, numbers, and spaces
    text = re.sub(r'[^\w\s]', '', text)
    # Lowercase
    text = text.lower()
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ======================================================
# Data Augmentation Functions
# ======================================================
def typo_augment(text, prob=0.15):
    if len(text) < 4 or random.random() > prob:
        return text

    i = random.randint(1, len(text) - 2)
    op = random.choice(["delete", "swap", "repeat"])

    if op == "delete":
        return text[:i] + text[i + 1:]

    if op == "swap":
        return text[:i - 1] + text[i] + text[i - 1] + text[i + 1:]

    if op == "repeat":
        return text[:i] + text[i] + text[i:]

    return text


def short_augment(text):
    words = text.split()
    if len(words) <= 1:
        return text
    cut = random.randint(1, len(words) - 1)
    return " ".join(words[:cut])


def punctuation_augment(text, prob=0.3):
    """Add/remove punctuation variations"""
    variations = [text]
    
    if random.random() < prob:
        # Add question mark if not present
        if '?' not in text:
            variations.append(text + '?')
    
    if random.random() < prob:
        # Add period if not present
        if '.' not in text and '?' not in text and '!' not in text:
            variations.append(text + '.')
    
    if random.random() < prob:
        # Add comma in the middle (if long enough)
        words = text.split()
        if len(words) >= 3:
            insert_pos = random.randint(1, len(words) - 1)
            words_with_comma = words[:insert_pos] + [words[insert_pos] + ','] + words[insert_pos + 1:]
            variations.append(' '.join(words_with_comma))
    
    return variations


def greeting_augment(text, label):
    """Special augmentation for greetings"""
    if label != "GREETING":
        return [text]
    
    variations = [text]
    
    # Check if it's a time-based greeting
    time_keywords = ['pagi', 'siang', 'sore', 'malam']
    if any(keyword in text.lower() for keyword in time_keywords):
        for time in time_keywords:
            if time not in text.lower():
                # Add missing time greetings
                if 'selamat' in text.lower():
                    variations.append(f"selamat {time}")
                else:
                    variations.append(f"selamat {time}")
    
    # Add/remove honorifics
    honorifics = ['kak', 'admin', 'pak', 'bu', 'mas', 'mbak']
    for honorific in honorifics:
        if honorific in text.lower():
            # Remove honorific
            cleaned = text.lower().replace(honorific, '').strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if cleaned:
                variations.append(cleaned)
        else:
            # Add honorific
            variations.append(f"{text} {honorific}")
    
    return variations


def synonym_augment(text, label):
    """Replace words with synonyms (simple version)"""
    if label not in ["GREETING", "CAPABILITY", "IDENTITY"]:
        return [text]
    
    synonyms_map = {
        'bisa': ['dapat', 'mampu', 'bisa'],
        'apa': ['apa', 'apa saja', 'apa-apa'],
        'kamu': ['anda', 'kamu', 'kalian'],
        'lakukan': ['kerjakan', 'buat', 'lakukan', 'tanggung'],
        'fungsi': ['tugas', 'peran', 'fungsi', 'kegunaan'],
        'siapa': ['siapakah', 'siapa', 'identitas'],
        'nama': ['nama', 'sebutan', 'panggilan'],
        'halo': ['hai', 'halo', 'hei'],
        'selamat': ['selamat', 'salam'],
        'tanya': ['bertanya', 'tanya', 'bertanya-tanya'],
        'ingin': ['mau', 'ingin', 'hendak'],
        'bantu': ['tolong', 'bantu', 'bantuan'],
    }
    
    words = text.lower().split()
    augmented = []
    
    # Try to replace each word with synonym
    for i, word in enumerate(words):
        if word in synonyms_map:
            for synonym in synonyms_map[word]:
                new_words = words.copy()
                new_words[i] = synonym
                augmented.append(' '.join(new_words))
    
    return augmented if augmented else [text]


# ======================================================
# Save training configuration
# ======================================================
def save_training_config():
    config = {
        "timestamp": TIMESTAMP,
        "seed": SEED,
        "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "xgb_params": {
            "n_estimators": 300,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "eval_metric": "mlogloss"
        },
        "ocsvm_params": {
            "kernel": "rbf",
            "nu": 0.30,
            "gamma": "scale"
        },
        "augmentation": {
            "typo_prob": 0.15,
            "short_augment": True,
            "punctuation_prob": 0.3,
            "synonym_augment": True,
            "greeting_augment": True
        },
        "text_cleaning_function": "clean_text (built-in)"
    }
    
    config_path = os.path.join(LOGS_DIR, f"training_config_{TIMESTAMP}.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return config_path


# ======================================================
# Save augmented dataset
# ======================================================
def save_augmented_dataset(aug_texts, aug_labels):
    aug_df = pd.DataFrame({
        'text': aug_texts,
        'label': aug_labels
    })
    
    aug_csv_path = os.path.join(LOGS_DIR, f"augmented_dataset_{TIMESTAMP}.csv")
    aug_df.to_csv(aug_csv_path, index=False, encoding='utf-8')
    
    # Also save sample of augmented data
    sample_df = aug_df.sample(min(50, len(aug_df)))
    sample_path = os.path.join(LOGS_DIR, f"augmented_sample_{TIMESTAMP}.csv")
    sample_df.to_csv(sample_path, index=False, encoding='utf-8')
    
    return aug_csv_path, sample_path


# ======================================================
# Save model metadata
# ======================================================
def save_model_metadata(encoder, X_shape, aug_texts_count):
    metadata = {
        "timestamp": TIMESTAMP,
        "classes": encoder.classes_.tolist(),
        "num_classes": len(encoder.classes_),
        "embedding_dim": X_shape[1],
        "total_samples": X_shape[0],
        "augmented_samples": aug_texts_count,
        "model_files": {
            "intent_classifier": "intent_xgb.joblib",
            "label_encoder": "intent_encoder.joblib",
            "out_of_scope_detector": "intent_occ.joblib",
            "embedder_info": "intent_embedder_info.joblib"
        },
        "text_cleaning": {
            "function": "clean_text",
            "description": "Removes punctuation, lowercases, removes extra spaces"
        }
    }
    
    metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return metadata_path


# ======================================================
# Main Training Function
# ======================================================
def main():
    print(f"Training started at: {TIMESTAMP}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Save training configuration
    config_path = save_training_config()
    print(f"✓ Training configuration saved to: {config_path}")
    
    # ======================================================
    # Load training data
    # ======================================================
    df = pd.read_csv("train.csv")
    
    # Clean the text data
    df['cleaned_text'] = df['text'].apply(clean_text)
    texts = df['cleaned_text'].tolist()
    labels = df['label'].astype(str).tolist()
    
    print(f"\n✓ Loaded {len(texts)} training samples")
    print(f"  Sample cleaned texts: {texts[:3]}")
    print(f"  Labels: {set(labels)}")
    
    # ======================================================
    # Augment dataset
    # ======================================================
    print("\n⚙️ Augmenting dataset...")
    aug_texts = []
    aug_labels = []
    
    for text, label in zip(texts, labels):
        # Add original cleaned text
        aug_texts.append(text)
        aug_labels.append(label)
        
        # Typo augmentation
        typo_text = typo_augment(text)
        aug_texts.append(typo_text)
        aug_labels.append(label)
        
        # Short augmentation
        short_text = short_augment(text)
        aug_texts.append(short_text)
        aug_labels.append(label)
        
        # Combined typo + short
        aug_texts.append(short_augment(typo_augment(text)))
        aug_labels.append(label)
        
        # Punctuation augmentation
        for punct_text in punctuation_augment(text):
            aug_texts.append(punct_text)
            aug_labels.append(label)
        
        # Greeting-specific augmentation
        for greeting_text in greeting_augment(text, label):
            aug_texts.append(greeting_text)
            aug_labels.append(label)
        
        # Synonym augmentation
        for synonym_text in synonym_augment(text, label):
            aug_texts.append(synonym_text)
            aug_labels.append(label)
    
    # Remove duplicates while preserving order
    unique_pairs = list(dict.fromkeys(zip(aug_texts, aug_labels)))
    aug_texts, aug_labels = zip(*unique_pairs) if unique_pairs else ([], [])
    
    print(f"✓ Augmented to {len(aug_texts)} unique samples")
    
    # Save augmented dataset
    aug_csv_path, sample_path = save_augmented_dataset(aug_texts, aug_labels)
    print(f"✓ Augmented dataset saved to: {aug_csv_path}")
    print(f"✓ Sample dataset saved to: {sample_path}")
    
    # ======================================================
    # FastEmbed Embedder
    # ======================================================
    print("\n⚙️ Generating embeddings...")
    embedder = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # Embed in batches for efficiency
    X_list = []
    batch_size = 32
    for i in range(0, len(aug_texts), batch_size):
        batch = aug_texts[i:i + batch_size]
        embeddings = list(embedder.embed(batch))
        X_list.extend([emb.flatten() for emb in embeddings])
    
    X = np.array(X_list)
    print(f"✓ Embeddings generated: {X.shape}")
    
    # ======================================================
    # Encode labels
    # ======================================================
    encoder = LabelEncoder()
    y = encoder.fit_transform(aug_labels)
    print(f"✓ Labels encoded")
    print(f"  In-scope intents: {list(encoder.classes_)}")
    print(f"  Number of classes: {len(encoder.classes_)}")
    
    # ======================================================
    # Intent Classifier
    # ======================================================
    print("\n⚙️ Training Intent Classifier...")
    intent_model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(encoder.classes_),
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=SEED,
        n_jobs=-1
    )
    
    intent_model.fit(X, y)
    print("✓ Intent classifier trained")
    
    # ======================================================
    # Out-of-Scope Detector
    # ======================================================
    print("\n⚙️ Training Out-of-Scope Detector...")
    occ = OneClassSVM(
        kernel="rbf",
        nu=0.25,
        gamma="scale"
    )
    occ.fit(X)
    print("✓ Out-of-scope detector trained")
    
    # ======================================================
    # Save models
    # ======================================================
    print("\n💾 Saving models...")
    
    # Save main models
    joblib.dump(intent_model, os.path.join(MODELS_DIR, "intent_xgb.joblib"))
    print(f"  ✓ Intent classifier saved to: {MODELS_DIR}/intent_xgb.joblib")
    
    joblib.dump(encoder, os.path.join(MODELS_DIR, "intent_encoder.joblib"))
    print(f"  ✓ Label encoder saved to: {MODELS_DIR}/intent_encoder.joblib")
    
    joblib.dump(occ, os.path.join(MODELS_DIR, "intent_occ.joblib"))
    print(f"  ✓ Out-of-scope detector saved to: {MODELS_DIR}/intent_occ.joblib")
    
    # Save embedder configuration
    embedder_info = {
        "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "embedding_dim": X.shape[1],
        "batch_size": 32
    }
    joblib.dump(embedder_info, os.path.join(MODELS_DIR, "intent_embedder_info.joblib"))
    print(f"  ✓ Embedder info saved to: {MODELS_DIR}/intent_embedder_info.joblib")
    
    # Save model metadata
    metadata_path = save_model_metadata(encoder, X.shape, len(aug_texts))
    print(f"  ✓ Model metadata saved to: {metadata_path}")
    
    # ======================================================
    # Training Summary
    # ======================================================
    print(f"\n{'='*50}")
    print("✅ TRAINING COMPLETE")
    print(f"{'='*50}")
    print(f"📁 Output Structure:")
    print(f"  ├── {OUTPUT_DIR}/")
    print(f"  │   ├── models/         # Saved models")
    print(f"  │   └── logs/           # Training logs & configs")
    print(f"\n📊 Training Summary:")
    print(f"  ├── Original samples: {len(texts)}")
    print(f"  ├── Augmented samples: {len(aug_texts)}")
    print(f"  ├── Embedding dimension: {X.shape[1]}")
    print(f"  ├── Number of classes: {len(encoder.classes_)}")
    print(f"  └── Classes: {', '.join(encoder.classes_)}")
    print(f"\n⏰ Timestamp: {TIMESTAMP}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()