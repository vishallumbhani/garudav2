import pickle
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any
from scipy.special import expit

logger = logging.getLogger(__name__)

class Arjuna:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.label_map = None
        self.idx_to_label = None
        self.risk_weights = {
            "prompt_injection": 1.0,
            "policy_bypass": 0.9,
            "data_exfiltration": 1.0,
            "benign": 0.1,
        }
        self._load_models()

    def _load_models(self):
        base_dir = Path(__file__).parent
        model_path = base_dir / "arjuna_model.pkl"
        vectorizer_path = base_dir / "arjuna_vectorizer.pkl"
        label_map_path = base_dir / "arjuna_label_map.json"

        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return
        if not vectorizer_path.exists():
            logger.error(f"Vectorizer file not found: {vectorizer_path}")
            return
        if not label_map_path.exists():
            logger.error(f"Label map file not found: {label_map_path}")
            return

        try:
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
            with open(vectorizer_path, "rb") as f:
                self.vectorizer = pickle.load(f)
            with open(label_map_path, "r") as f:
                self.label_map = json.load(f)
            self.idx_to_label = {v: k for k, v in self.label_map.items()}
            logger.info("Arjuna models loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Arjuna models: {e}")
            self.model = None

    def _get_probs(self, X):
        """Get probability estimates from model, works for LogisticRegression and LinearSVC."""
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)[0]
        else:
            # For LinearSVC, use decision_function and softmax
            decision = self.model.decision_function(X)
            if len(decision.shape) == 1:
                # Binary classification: sigmoid
                prob_pos = expit(decision[0])
                probs = np.array([1 - prob_pos, prob_pos])
            else:
                # Multi-class: softmax
                exp_decision = np.exp(decision[0])
                probs = exp_decision / exp_decision.sum()
            return probs

    def run(self, request) -> Dict[str, Any]:
        if self.model is None or self.vectorizer is None:
            return {
                "engine": "arjuna",
                "status": "degraded",
                "score": 0.0,
                "confidence": 0.0,
                "label": "unknown",
                "reason": "Model not loaded",
                "class_scores": {}
            }

        try:
            if request.normalized_text is not None:
                text = request.normalized_text
            else:
                text = request.content
                if isinstance(text, bytes):
                    text = text.decode('utf-8', errors='ignore')
        except Exception as e:
            return {
                "engine": "arjuna",
                "status": "error",
                "score": 0.0,
                "confidence": 0.0,
                "label": "unknown",
                "reason": f"Text extraction error: {e}",
                "class_scores": {}
            }

        try:
            X = self.vectorizer.transform([text])
            probs = self._get_probs(X)
            pred_idx = int(np.argmax(probs))
            label = self.idx_to_label[pred_idx]
            confidence = probs[pred_idx]
            risk_score = confidence * self.risk_weights.get(label, 0.5)
            risk_score = min(risk_score, 0.95)
            class_scores = {self.idx_to_label[i]: round(probs[i], 3) for i in range(len(probs))}
            return {
                "engine": "arjuna",
                "status": "ok",
                "score": round(risk_score, 2),
                "confidence": round(confidence, 3),
                "label": label,
                "reason": f"ML detected {label} with {confidence:.2%} confidence",
                "class_scores": class_scores,
            }
        except Exception as e:
            logger.error(f"Arjuna inference error: {e}")
            return {
                "engine": "arjuna",
                "status": "error",
                "score": 0.0,
                "confidence": 0.0,
                "label": "unknown",
                "reason": f"Inference error: {e}",
                "class_scores": {}
            }
