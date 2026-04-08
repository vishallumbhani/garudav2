# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Add more policy_bypass data and retrain Arjuna.
"""

import os
import json
import random
import pickle
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
DATA_DIR = PROJECT_ROOT / "data" / "ml"
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

try:
    from datasets import load_dataset
except ImportError:
    os.system("pip install datasets")
    from datasets import load_dataset

# ----------------------------------------------------------------------
# Load existing balanced dataset if available, otherwise start fresh
# ----------------------------------------------------------------------
balanced_path = DATA_DIR / "arjuna_dataset_balanced.json"
if balanced_path.exists():
    with open(balanced_path, "r") as f:
        existing = json.load(f)
    all_data = [(item["text"], item["label"]) for item in existing]
    print(f"Loaded existing balanced dataset: {len(all_data)} samples")
else:
    all_data = []

# ----------------------------------------------------------------------
# Add more policy_bypass from red team prompts dataset
# ----------------------------------------------------------------------
print("Loading harpreetsahota/red-team-prompts-questions...")
try:
    ds = load_dataset("harpreetsahota/red-team-prompts-questions", split="train")
    # This dataset has a 'text' column (the prompt). We'll label all as policy_bypass.
    # It's a small dataset (a few hundred). We'll add all.
    added = 0
    for row in ds:
        text = row.get("text")
        if text:
            all_data.append((text, "policy_bypass"))
            added += 1
    print(f"  Added {added} policy_bypass samples from red-team dataset.")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# Also add more from openai/moderation (if we didn't already include all)
# We'll load the full moderation dataset and add all policy_bypass categories again.
# But we already added some in the previous script; we'll add more to increase count.
print("Loading additional openai/moderation samples...")
try:
    ds = load_dataset("openai/moderation", split="train")
    policy_categories = ["hate", "sexual", "violence", "self-harm"]
    added = 0
    for row in ds:
        text = row.get("text")
        if not text:
            continue
        category = row.get("category", "")
        if category in policy_categories:
            all_data.append((text, "policy_bypass"))
            added += 1
        else:
            all_data.append((text, "benign"))
            added += 1
    print(f"  Added {added} samples (policy_bypass + benign) from moderation dataset.")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# Also add TrustAIRLab dataset's benign part? Already have.
# We'll ensure we have at least 5000 benign, 5000 injection, 2000 policy_bypass, 2000 exfil
# But the previous balanced dataset already had that. We'll rebalance now with new samples.

target_counts = {
    "benign": 5000,
    "prompt_injection": 5000,
    "policy_bypass": 2000,
    "data_exfiltration": 2000,
}

label_to_texts = {}
for text, label in all_data:
    label_to_texts.setdefault(label, []).append(text)

balanced = []
for label, target in target_counts.items():
    texts = label_to_texts.get(label, [])
    if len(texts) < target:
        factor = (target + len(texts) - 1) // len(texts) if texts else 0
        sampled = texts * factor
        balanced.extend([(text, label) for text in sampled[:target]])
    else:
        balanced.extend([(text, label) for text in random.sample(texts, target)])

random.shuffle(balanced)
print(f"\nNew balanced dataset: {len(balanced)} samples")
for k, v in Counter(l for _, l in balanced).items():
    print(f"  {k}: {v}")

# Save for reference
with open(balanced_path, "w") as f:
    json.dump([{"text": t, "label": l} for t, l in balanced], f, indent=2)
print(f"Saved to {balanced_path}")

# ----------------------------------------------------------------------
# Train model
# ----------------------------------------------------------------------
texts = [t for t, _ in balanced]
labels = [l for _, l in balanced]
label_map = {l: i for i, l in enumerate(sorted(set(labels)))}
y = np.array([label_map[l] for l in labels])

vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2),
                              stop_words="english", sublinear_tf=True, use_idf=True)
X = vectorizer.fit_transform(texts)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

param_grid = {
    'C': [0.1, 0.5, 1.0, 5.0],
    'solver': ['liblinear', 'lbfgs'],
    'class_weight': ['balanced', None]
}
grid = GridSearchCV(LogisticRegression(max_iter=1000, random_state=42),
                    param_grid, cv=3, scoring='f1_macro', n_jobs=-1)
grid.fit(X_train, y_train)
best_model = grid.best_estimator_
print(f"\nBest params: {grid.best_params_}")
print(f"Cross-val macro F1: {grid.best_score_:.4f}")

y_pred = best_model.predict(X_test)
print("\nTest set classification report:")
print(classification_report(y_test, y_pred, target_names=label_map.keys()))

# ----------------------------------------------------------------------
# Save model
# ----------------------------------------------------------------------
model_path = MODEL_DIR / "arjuna_model.pkl"
vectorizer_path = MODEL_DIR / "arjuna_vectorizer.pkl"
label_map_path = MODEL_DIR / "arjuna_label_map.json"

with open(model_path, "wb") as f:
    pickle.dump(best_model, f)
with open(vectorizer_path, "wb") as f:
    pickle.dump(vectorizer, f)
with open(label_map_path, "w") as f:
    json.dump(label_map, f, indent=2)

# Copy to Arjuna engine folder
arjuna_dir = PROJECT_ROOT / "src" / "engines" / "arjuna"
arjuna_dir.mkdir(parents=True, exist_ok=True)
for fname in ["arjuna_model.pkl", "arjuna_vectorizer.pkl", "arjuna_label_map.json"]:
    src = MODEL_DIR / fname
    dst = arjuna_dir / fname
    if src.exists():
        import shutil
        shutil.copy(src, dst)
        print(f"Copied {fname} to {dst}")

print("\n✅ Retraining with boosted policy_bypass data completed. Restart server and test again.")
