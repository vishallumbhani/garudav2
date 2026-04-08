"""
Arjuna – Lightweight ML classifier for prompt injection and policy bypass.
"""

import pickle
import json
from pathlib import Path
from typing import Dict, Any

class Arjuna:
    def __init__(self):
        model_path = Path(__file__).parent / "arjuna_model.pkl"
        vectorizer_path = Path(__file__).parent / "arjuna_vectorizer.pkl"
        label_map_path = Path(__file__).parent / "arjuna_label_map.json"
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)
        with open(vectorizer_path, "rb") as f:
            self.vectorizer = pickle.load(f)
        with open(label_map_path, "r") as f:
            self.label_map = json.load(f)
        # Inverse map: label index -> label name
        self.idx_to_label = {v: k for k, v in self.label_map.items()}
        # Class weights for risk score
        self.risk_weights = {
            "prompt_injection": 1.0,
            "policy_bypass": 0.9,
            "data_exfiltration": 1.0,
            "benign": 0.1,
        }

    def run(self, request) -> Dict[str, Any]:
        # Extract text from request
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')

        # Transform text
        X = self.vectorizer.transform([text])
        # Predict probabilities
        probs = self.model.predict_proba(X)[0]
        # Get predicted class index and confidence
        pred_idx = int(self.model.predict(X)[0])
        label = self.idx_to_label[pred_idx]
        confidence = probs[pred_idx]

        # Map confidence to a risk score (0-1)
        if confidence < 0.4:
            risk_score = confidence * self.risk_weights.get(label, 0.5)
        else:
            risk_score = confidence * self.risk_weights.get(label, 0.5)

        # Cap at 0.95
        risk_score = min(risk_score, 0.95)

        # Build class_scores dict
        class_scores = {self.idx_to_label[i]: round(probs[i], 3) for i in range(len(probs))}

        return {
            "engine": "arjuna",
            "status": "ok",
            "score": round(risk_score, 2),
            "confidence": round(confidence, 3),
            "label": label,
            "reason": f"ML classifier detected {label} with {confidence:.2%} confidence",
            "class_scores": class_scores,
        }
