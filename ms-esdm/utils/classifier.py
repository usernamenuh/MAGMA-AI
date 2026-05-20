import logging
from typing import Tuple, Optional
from utils.responses import get_intent_response
import os
import random
import pandas as pd
import joblib
import numpy as np
import xgboost as xgb
import re
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

OUTPUT_DIR = "occ/magma_intent_model_temp"
MODELS_DIR = os.path.join(OUTPUT_DIR, "models")



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
    
class MAGMAIntentClassifier:
    """Trained intent classifier for MAGMA Assistant"""
    
    def __init__(self, model_dir=None):
        """Load trained models"""
        if model_dir is None:
            model_dir = MODELS_DIR
        
        # Load models
        self.intent_model = joblib.load(os.path.join(model_dir, "intent_xgb.joblib"))
        self.encoder = joblib.load(os.path.join(model_dir, "intent_encoder.joblib"))
        self.out_of_scope_model = joblib.load(os.path.join(model_dir, "intent_occ.joblib"))
        embedder_info = joblib.load(os.path.join(model_dir, "intent_embedder_info.joblib"))
        
        # Initialize embedder
        self.embedder = TextEmbedding(model_name=embedder_info["model_name"])
        
        # Load metadata
        metadata_path = os.path.join(model_dir, "model_metadata.json")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
    
    def clean_text(self, text: str) -> str:
        """Clean input text"""
        return clean_text(text)
    
    def predict(self, user_input: str, geo_location=None) -> Dict[str, Any]:
        """
        Predict intent for user input
        
        Returns:
            Dictionary with prediction results
        """
        # Clean text
        cleaned_text = self.clean_text(user_input)
        
        # Generate embedding
        embedding = list(self.embedder.embed([cleaned_text]))[0].flatten()
        X = np.array([embedding])

        probs = self.intent_model.predict_proba(X)[0]
        max_prob = np.max(probs)

        
        # First check if out of scope
        is_out_of_scope = self.out_of_scope_model.predict(X)[0] == -1
        # Predict intent
        proba = self.intent_model.predict_proba(X)[0]
        pred_idx = np.argmax(proba)
        confidence = proba[pred_idx]
        intent = self.encoder.inverse_transform([pred_idx])[0]
        
        if max_prob > 0.7:
            final_intent = intent
        elif is_out_of_scope:
            final_intent = "out_of_scope"
        else:
            final_intent = intent

        if final_intent == "out_of_scope":
            return {
                "status": "success",
                "intent": "out_of_scope",
                "confidence": 1.0,
                "requires_api": False,
                "cleaned_text": cleaned_text
            }
        
        
        # Special handling for location_required
        if final_intent == "location_required" and geo_location:
            final_intent = "technical"

            # if isinstance(geo_location, (list, tuple)) and len(geo_location) == 2:
            #     if geo_location[0] is not None and geo_location[1] is not None:
            #         # Has valid GPS data, treat as technical
            #         intent = "technical"
        
        return {
            "status": "success",
            "intent": final_intent,
            "confidence": float(confidence),
            "requires_api": final_intent == "technical",
            "cleaned_text": cleaned_text,
            "all_probabilities": {
                cls: float(prob) for cls, prob in zip(self.encoder.classes_, proba)
            }
        }
    
    def get_intent_description(self, intent: str) -> str:
        """Get description for an intent"""
        return self.metadata.get("intent_descriptions", {}).get(intent, "No description available")


class IntentManager:
    def __init__(self):
        self.classifier = self._load_model()

    def _load_model(self) -> Optional[MAGMAIntentClassifier]:
        """Initializes and returns the classifier."""
        try:
            model = MAGMAIntentClassifier()
            intents = model.encoder.classes_
            logger.info(f"✅ Model loaded with {len(intents)} intents: {', '.join(intents)}")
            return model
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return None

    def detect_and_respond(self, user_input: str, geo_location: str) -> Tuple[str, str]:
        """Predicts intent and fetches the corresponding response."""
        if not self.classifier:
            return "error", "I'm having trouble connecting to classifier right now."

        result = self.classifier.predict(user_input, geo_location)
        predicted_intent = result.get("intent")

        response = get_intent_response(predicted_intent, user_input)
        
        return predicted_intent, response

manager = IntentManager()

def detect_conversational_intent(user_input: str, geo_location: tuple[float, float]):
    """Refined wrapper for the original function call."""
    return manager.detect_and_respond(user_input, geo_location)