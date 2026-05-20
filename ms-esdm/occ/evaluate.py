# evaluate.py
import os
import json
import pandas as pd
import joblib
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import re

from fastembed import TextEmbedding

# ======================================================
# Configuration
# ======================================================
MODELS_DIR = "output2/models"  # Updated to match your new output directory
EVAL_DATA_PATH = "evaluate.csv"

# ======================================================
# Text cleaning function (must match training)
# ======================================================
def clean_text(text):
    """Clean text by removing punctuation and normalizing - MUST MATCH TRAINING"""
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
# Load Models and Metadata
# ======================================================
def load_models():
    """Load all models from the organized structure"""
    
    print("📂 Loading models...")
    
    try:
        # Load model metadata
        metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            print(f"  ✓ Model version: {metadata['timestamp']}")
            print(f"  ✓ Classes: {metadata['classes']}")
        else:
            metadata = {}
            print("  ⚠️ No metadata found")
        
        # Load intent classifier
        intent_model = joblib.load(os.path.join(MODELS_DIR, "intent_xgb.joblib"))
        print("  ✓ Intent classifier loaded")
        
        # Load label encoder
        encoder = joblib.load(os.path.join(MODELS_DIR, "intent_encoder.joblib"))
        print("  ✓ Label encoder loaded")
        
        # Load out-of-scope detector
        occ = joblib.load(os.path.join(MODELS_DIR, "intent_occ.joblib"))
        print("  ✓ Out-of-scope detector loaded")
        
        # Load embedder info and initialize
        embedder_info = joblib.load(os.path.join(MODELS_DIR, "intent_embedder_info.joblib"))
        print("  ✓ Embedder info loaded")
        
        # Initialize embedder
        embedder = TextEmbedding(model_name=embedder_info["model_name"])
        print("  ✓ Embedder initialized")
        
        return {
            'intent_model': intent_model,
            'encoder': encoder,
            'occ': occ,
            'embedder': embedder,
            'metadata': metadata
        }
        
    except FileNotFoundError as e:
        print(f"  ❌ Error loading models: {e}")
        print(f"  Please ensure models are trained and saved in: {MODELS_DIR}")
        print(f"  Available files: {os.listdir(MODELS_DIR) if os.path.exists(MODELS_DIR) else 'Directory not found'}")
        return None

# ======================================================
# Main Evaluation Function
# ======================================================
def main():
    """Main evaluation function"""
    
    print("🧪 Model Evaluation")
    print("="*60)
    
    # Load models
    models = load_models()
    if models is None:
        return
    
    # Load evaluation data
    if not os.path.exists(EVAL_DATA_PATH):
        print(f"❌ Evaluation data not found: {EVAL_DATA_PATH}")
        return
    
    df = pd.read_csv(EVAL_DATA_PATH)
    
    # Clean the text data (MUST match training preprocessing)
    df['cleaned_text'] = df['text'].apply(clean_text)
    texts = df['cleaned_text'].tolist()
    labels = df['label'].astype(str).tolist()
    
    print(f"\n📊 Evaluation Data:")
    print(f"  ✓ Samples: {len(texts)}")
    print(f"  ✓ Classes in data: {sorted(set(labels))}")
    
    # Generate embeddings
    print(f"\n⚙️ Generating embeddings...")
    embeddings = list(models['embedder'].embed(texts))
    X = np.array([emb.flatten() for emb in embeddings])
    print(f"  ✓ Embeddings shape: {X.shape}")
    
    # =========================
    # OCC decision
    # =========================
    print(f"\n🔍 Running out-of-scope detection...")
    occ_pred = models['occ'].predict(X)   # +1 = in-scope, -1 = OOS
    
    y_true = []
    y_pred = []
    
    print(f"\n📝 Making predictions...")
    for i, label in enumerate(labels):
        if occ_pred[i] == -1:
            y_pred.append("OUT_OF_SCOPE")
        else:
            intent_idx = models['intent_model'].predict(X[i].reshape(1, -1))[0]
            y_pred.append(models['encoder'].inverse_transform([intent_idx])[0])
        
        y_true.append(label)
    
    # =========================
    # Detailed Analysis
    # =========================
    print(f"\n{'='*60}")
    print("📊 PREDICTION DISTRIBUTION")
    print(f"{'='*60}")
    
    # True distribution
    true_counts = pd.Series(y_true).value_counts().sort_index()
    print("True label distribution:")
    for label, count in true_counts.items():
        print(f"  {label:15s}: {count:3d} samples")
    
    # Predicted distribution
    pred_counts = pd.Series(y_pred).value_counts().sort_index()
    print("\nPredicted label distribution:")
    for label, count in pred_counts.items():
        print(f"  {label:15s}: {count:3d} samples")
    
    # =========================
    # Calculate accuracy
    # =========================
    accuracy = accuracy_score(y_true, y_pred)
    print(f"\n📈 Overall Accuracy: {accuracy:.3f}")
    
    # =========================
    # Confusion Matrix
    # =========================
    print(f"\n{'='*60}")
    print("📊 CONFUSION MATRIX")
    print(f"{'='*60}")
    
    # Get all labels
    all_labels = sorted(set(y_true) | set(y_pred))
    
    # Create confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=all_labels)
    cm_df = pd.DataFrame(cm, index=all_labels, columns=all_labels)
    
    print("\nConfusion Matrix:")
    print(cm_df.to_string())
    
    # =========================
    # Classification Report
    # =========================
    print(f"\n{'='*60}")
    print("📊 CLASSIFICATION REPORT")
    print(f"{'='*60}")
    
    report = classification_report(
        y_true,
        y_pred,
        labels=all_labels,
        output_dict=False,
        zero_division=0
    )
    
    print(report)
    
    # =========================
    # Detailed metrics
    # =========================
    print(f"\n{'='*60}")
    print("📊 DETAILED METRICS")
    print(f"{'='*60}")
    
    # Calculate per-class metrics
    report_dict = classification_report(
        y_true,
        y_pred,
        labels=all_labels,
        output_dict=True,
        zero_division=0
    )
    
    for label in all_labels:
        if label in report_dict:
            metrics = report_dict[label]
            print(f"\n{label}:")
            print(f"  Precision: {metrics['precision']:.3f}")
            print(f"  Recall:    {metrics['recall']:.3f}")
            print(f"  F1-score:  {metrics['f1-score']:.3f}")
            print(f"  Support:   {metrics['support']}")
    
    # =========================
    # Error Analysis
    # =========================
    print(f"\n{'='*60}")
    print("🔍 ERROR ANALYSIS")
    print(f"{'='*60}")
    
    errors = []
    for i, (true, pred) in enumerate(zip(y_true, y_pred)):
        if true != pred:
            errors.append({
                'text': df.iloc[i]['text'],
                'cleaned_text': texts[i],
                'true': true,
                'pred': pred
            })
    
    print(f"\nTotal errors: {len(errors)} out of {len(y_true)} samples")
    print(f"Error rate: {len(errors)/len(y_true)*100:.1f}%")
    
    if errors:
        print(f"\nFirst 10 errors:")
        for i, error in enumerate(errors[:10]):
            print(f"\n{i+1}. '{error['text']}'")
            print(f"   Cleaned: '{error['cleaned_text']}'")
            print(f"   True: {error['true']}, Predicted: {error['pred']}")
    
    # =========================
    # OOC Detection Analysis
    # =========================
    print(f"\n{'='*60}")
    print("🎯 OUT-OF-SCOPE DETECTION ANALYSIS")
    print(f"{'='*60}")
    
    # Count OOS predictions
    oos_true = sum(1 for label in y_true if label == "OUT_OF_SCOPE")
    oos_pred = sum(1 for label in y_pred if label == "OUT_OF_SCOPE")
    
    print(f"\nOut-of-scope samples:")
    print(f"  True OUT_OF_SCOPE: {oos_true}")
    print(f"  Predicted OUT_OF_SCOPE: {oos_pred}")
    
    # Calculate OOS detection metrics
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == "OUT_OF_SCOPE" and p == "OUT_OF_SCOPE")
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != "OUT_OF_SCOPE" and p == "OUT_OF_SCOPE")
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == "OUT_OF_SCOPE" and p != "OUT_OF_SCOPE")
    
    oos_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    oos_recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    oos_f1 = 2 * oos_precision * oos_recall / (oos_precision + oos_recall) if (oos_precision + oos_recall) > 0 else 0
    
    print(f"\nOut-of-scope detection metrics:")
    print(f"  Precision: {oos_precision:.3f}")
    print(f"  Recall:    {oos_recall:.3f}")
    print(f"  F1-score:  {oos_f1:.3f}")
    
    # =========================
    # Save Results
    # =========================
    print(f"\n{'='*60}")
    print("💾 SAVING RESULTS")
    print(f"{'='*60}")
    
    # Create results directory
    results_dir = os.path.join("output2", "evaluation_results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Create results DataFrame
    results_df = pd.DataFrame({
        'text': df['text'],
        'cleaned_text': texts,
        'true_label': y_true,
        'predicted_label': y_pred,
        'correct': [t == p for t, p in zip(y_true, y_pred)]
    })
    
    # Save detailed results
    results_csv = os.path.join(results_dir, "detailed_predictions.csv")
    results_df.to_csv(results_csv, index=False, encoding='utf-8')
    print(f"✓ Detailed predictions saved to: {results_csv}")
    
    # Save summary
    summary = {
        'accuracy': accuracy,
        'total_samples': len(y_true),
        'errors': len(errors),
        'error_rate': len(errors)/len(y_true)*100,
        'oos_detection': {
            'precision': oos_precision,
            'recall': oos_recall,
            'f1': oos_f1
        },
        'classification_report': report_dict
    }
    
    summary_json = os.path.join(results_dir, "evaluation_summary.json")
    with open(summary_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Evaluation summary saved to: {summary_json}")
    
    print(f"\n{'='*60}")
    print("✅ EVALUATION COMPLETE")
    print(f"{'='*60}")
    
    return {
        'accuracy': accuracy,
        'errors': errors,
        'y_true': y_true,
        'y_pred': y_pred,
        'results_df': results_df
    }

# ======================================================
# Command Line Interface
# ======================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate intent classification model")
    parser.add_argument("--eval-data", type=str, default=EVAL_DATA_PATH,
                       help="Path to evaluation CSV file")
    parser.add_argument("--models-dir", type=str, default=MODELS_DIR,
                       help="Path to models directory")
    
    args = parser.parse_args()
    
    # Update configuration
    EVAL_DATA_PATH = args.eval_data
    MODELS_DIR = args.models_dir
    
    # Run evaluation
    results = main()