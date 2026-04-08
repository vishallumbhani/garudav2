#!/usr/bin/env python3
"""
Fix Arjuna integration: ensure engine is called and Krishna uses its score.
"""

import os
import re
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# 1. Ensure Arjuna engine files exist and model files are present
arjuna_dir = PROJECT_ROOT / "src" / "engines" / "arjuna"
arjuna_dir.mkdir(parents=True, exist_ok=True)

model_files = ["arjuna_model.pkl", "arjuna_vectorizer.pkl", "arjuna_label_map.json"]
for f in model_files:
    src = PROJECT_ROOT / "models" / f
    dst = arjuna_dir / f
    if src.exists() and not dst.exists():
        shutil.copy(src, dst)
        print(f"Copied {f} to {dst}")
    elif not src.exists():
        print(f"Warning: {src} not found. Run training first: python scripts/setup_arjuna.py")

# 2. Ensure Arjuna engine code is present
arjuna_engine = arjuna_dir / "engine.py"
if not arjuna_engine.exists():
    with open(arjuna_engine, "w") as f:
        f.write('''"""
Arjuna – Lightweight ML classifier.
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
        self.idx_to_label = {v: k for k, v in self.label_map.items()}
        self.risk_weights = {"prompt_injection": 1.0, "policy_bypass": 0.9, "data_exfiltration": 1.0, "benign": 0.1}

    def run(self, request) -> Dict[str, Any]:
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
        X = self.vectorizer.transform([text])
        probs = self.model.predict_proba(X)[0]
        pred_idx = int(self.model.predict(X)[0])
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
''')
    print("Created Arjuna engine.")

# 3. Ensure __init__.py exists
(arjuna_dir / "__init__.py").touch(exist_ok=True)

# 4. Update scan_service.py: add import and call
scan_path = PROJECT_ROOT / "src" / "services" / "scan_service.py"
with open(scan_path, "r") as f:
    scan_content = f.read()

# Add import if missing
if "from src.engines.arjuna.engine import Arjuna" not in scan_content:
    # Find where shakuni import is
    if "from src.engines.shakuni.engine import Shakuni" in scan_content:
        scan_content = scan_content.replace(
            "from src.engines.shakuni.engine import Shakuni",
            "from src.engines.shakuni.engine import Shakuni\nfrom src.engines.arjuna.engine import Arjuna"
        )
    else:
        # fallback: add near other engine imports
        scan_content = scan_content.replace(
            "from src.engines.yudhishthira.engine import Yudhishthira",
            "from src.engines.yudhishthira.engine import Yudhishthira\nfrom src.engines.arjuna.engine import Arjuna"
        )

# Add Arjuna execution after Shakuni
if "shakuni_result = fallback.wrap_engine" in scan_content and "arjuna_result" not in scan_content:
    # Insert after the line that adds shakuni_result to engine_results
    insert_point = "    engine_results[\"shakuni\"] = shakuni_result\n"
    new_lines = """    arjuna_result = fallback.wrap_engine("arjuna", Arjuna().run, request)
    engine_results["arjuna"] = arjuna_result
"""
    scan_content = scan_content.replace(insert_point, insert_point + new_lines)

with open(scan_path, "w") as f:
    f.write(scan_content)
print("Updated scan_service.py with Arjuna integration.")

# 5. Update Krishna: extract arjuna score and include in weighted sum
krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
with open(krishna_path, "r") as f:
    krishna_content = f.read()

# Ensure arjuna extraction is present
if "arjuna = engine_results.get(\"arjuna\", {})" not in krishna_content:
    # Insert after shakuni extraction
    insert_after = "shakuni = engine_results.get(\"shakuni\", {})"
    new_extract = "\n        arjuna = engine_results.get(\"arjuna\", {})"
    krishna_content = krishna_content.replace(insert_after, insert_after + new_extract)

# Add arjuna_score extraction
if "arjuna_score = arjuna.get(\"score\", 0.5)" not in krishna_content:
    # Insert after shakuni_score line
    insert_after = "shakuni_score = shakuni.get(\"score\", 0.5)"
    new_line = "\n        arjuna_score = arjuna.get(\"score\", 0.5)"
    krishna_content = krishna_content.replace(insert_after, insert_after + new_line)

# Update base_weighted calculation to include arjuna
# Find the line that sets base_weighted
base_weighted_line = r'base_weighted = \(self\.weights\["bhishma"\] \* bhishma_score \+ self\.weights\["hanuman"\] \* hanuman_score \+ self\.weights\["shakuni"\] \* shakuni_score\)'
if re.search(base_weighted_line, krishna_content):
    # Replace with version including arjuna
    new_base_weighted = 'base_weighted = (self.weights["bhishma"] * bhishma_score + self.weights["hanuman"] * hanuman_score + self.weights["shakuni"] * shakuni_score + self.weights["arjuna"] * arjuna_score)'
    krishna_content = re.sub(base_weighted_line, new_base_weighted, krishna_content)

# Add arjuna_score to trace's scores dict
# We'll add it after shakuni if present
shakuni_score_line = '"shakuni": round(shakuni_score, 3),'
if shakuni_score_line in krishna_content:
    krishna_content = krishna_content.replace(
        shakuni_score_line,
        shakuni_score_line + '\n            "arjuna": round(arjuna_score, 3),'
    )
else:
    # fallback: add before the closing brace
    krishna_content = krishna_content.replace('"scores": {', '"scores": {\n            "arjuna": round(arjuna_score, 3),')

with open(krishna_path, "w") as f:
    f.write(krishna_content)
print("Updated Krishna to include Arjuna score in weighted sum and trace.")

print("\n✅ Fixes applied. Restart the server and test.")
