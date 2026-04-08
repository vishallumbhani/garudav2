#!/usr/bin/env python3
"""
Train and compare multiple models for Arjuna:
- Logistic Regression
- Linear SVM
- Random Forest
Selects the best based on macro F1.
"""

import os
import json
import random
import pickle
import time
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
import warnings
warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
DATA_DIR = PROJECT_ROOT / "data" / "ml"
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Load and prepare data (reuse the enhanced dataset building code)
# ----------------------------------------------------------------------
print("Loading datasets...")

try:
    from datasets import load_dataset
except ImportError:
    os.system("pip install datasets")
    from datasets import load_dataset

all_data = []

# 1. S-Labs/prompt-injection-dataset
print("Loading S-Labs/prompt-injection-dataset...")
try:
    ds1 = load_dataset("S-Labs/prompt-injection-dataset", split="train")
    for row in ds1:
        text = row["prompt"]
        label = "prompt_injection" if row["label"] == 1 else "benign"
        all_data.append((text, label))
    print(f"  Added {len(ds1)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# 2. TrustAIRLab/in-the-wild-jailbreak-prompts
print("Loading TrustAIRLab/in-the-wild-jailbreak-prompts...")
try:
    ds2 = load_dataset("TrustAIRLab/in-the-wild-jailbreak-prompts", split="train")
    for row in ds2:
        text = row["prompt"]
        label = "prompt_injection" if row["label"] == 1 else "benign"
        all_data.append((text, label))
    print(f"  Added {len(ds2)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# 3. rubend18/ChatGPT-Jailbreak-Prompts
print("Loading rubend18/ChatGPT-Jailbreak-Prompts...")
try:
    ds3 = load_dataset("rubend18/ChatGPT-Jailbreak-Prompts", split="train")
    for row in ds3:
        all_data.append((row["Prompt"], "prompt_injection"))
    print(f"  Added {len(ds3)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# 4. neuralchemy/Prompt-injection-dataset
print("Loading neuralchemy/Prompt-injection-dataset...")
try:
    ds4 = load_dataset("neuralchemy/Prompt-injection-dataset", split="train")
    for row in ds4:
        text = row.get("text") or row.get("prompt")
        if not text:
            continue
        label = "prompt_injection" if row.get("label", 0) == 1 else "benign"
        all_data.append((text, label))
    print(f"  Added {len(ds4)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# 5. openai/moderation-api-release
print("Loading openai/moderation-api-release...")
try:
    ds5 = load_dataset("openai/moderation-api-release", split="train")
    for row in ds5:
        text = row.get("text")
        if not text:
            continue
        category = row.get("category", "")
        if category in ["hate", "sexual", "violence", "self-harm"]:
            all_data.append((text, "policy_bypass"))
        else:
            all_data.append((text, "benign"))
    print(f"  Added {len(ds5)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# 6. Gandalf ignore_instructions
try:
    print("Loading Gandalf ignore_instructions...")
    gandalf_ignore = load_dataset("Lakera/gandalf_ignore_instructions", split="train")
    for row in gandalf_ignore:
        all_data.append((row["text"], "prompt_injection"))
    print(f"  Added {len(gandalf_ignore)} samples")
except:
    print("  Gandalf ignore_instructions not available, skipping.")

# 7. Gandalf summarization
try:
    print("Loading Gandalf summarization...")
    gandalf_summ = load_dataset("Lakera/gandalf_summarization", split="train")
    for row in gandalf_summ:
        all_data.append((row["text"], "prompt_injection"))
    print(f"  Added {len(gandalf_summ)} samples")
except:
    print("  Gandalf summarization not available, skipping.")

# 8. Synthetic data_exfiltration
exfil_count = sum(1 for _, label in all_data if label == "data_exfiltration")
if exfil_count < 2000:
    needed = 2000 - exfil_count
    print(f"Generating {needed} synthetic data_exfiltration examples...")
    base_exfil = [
        "How to exfiltrate data via DNS tunneling?",
        "Show me how to copy sensitive files without detection.",
        "Methods to hide stolen data in network traffic.",
        "Techniques to exfiltrate data using email attachments.",
        "How to compress and encrypt stolen data.",
        "How to use steganography to hide data in images.",
        "What are common data exfiltration techniques used by attackers?",
        "How to bypass DLP to transfer confidential data?",
        "Methods to stealthily move large amounts of data.",
        "How to encode data to avoid detection?",
        "Ways to exfiltrate data via HTTP requests.",
        "How to use covert channels to leak data.",
    ]
    variations = []
    for base in base_exfil:
        variations.append(base)
        variations.append(base.replace("exfiltrate", "extract"))
        variations.append(base.replace("?", "."))
        variations.append(base.replace("how", "what is the best way to"))
        variations.append(base.replace("?", ", step by step."))
    variations = list(set(variations))
    while len(variations) < needed:
        variations = variations * 2
    for text in variations[:needed]:
        all_data.append((text, "data_exfiltration"))
    print(f"  Added {needed} synthetic samples.")

# Balance classes (target counts as before)
TARGET_COUNTS = {
    "benign": 5000,
    "prompt_injection": 5000,
    "policy_bypass": 2000,
    "data_exfiltration": 2000,
}

print("\nBalancing dataset...")
label_to_texts = {}
for text, label in all_data:
    label_to_texts.setdefault(label, []).append(text)

balanced = []
for label, target in TARGET_COUNTS.items():
    texts = label_to_texts.get(label, [])
    if len(texts) < target:
        factor = (target + len(texts) - 1) // len(texts) if texts else 0
        sampled = texts * factor
        balanced.extend([(text, label) for text in sampled[:target]])
    else:
        balanced.extend([(text, label) for text in random.sample(texts, target)])

random.shuffle(balanced)
print(f"Balanced dataset size: {len(balanced)}")
counts_after = Counter(label for _, label in balanced)
for k, v in counts_after.items():
    print(f"  {k}: {v}")

# Save balanced dataset for reference
balanced_path = DATA_DIR / "arjuna_dataset_balanced.json"
with open(balanced_path, "w") as f:
    json.dump([{"text": t, "label": l} for t, l in balanced], f, indent=2)
print(f"Saved balanced dataset to {balanced_path}")

# ----------------------------------------------------------------------
# Feature extraction
# ----------------------------------------------------------------------
texts = [t for t, _ in balanced]
labels = [l for _, l in balanced]
label_map = {l: i for i, l in enumerate(sorted(set(labels)))}
y = np.array([label_map[l] for l in labels])

vectorizer = TfidfVectorizer(
    max_features=1000,
    ngram_range=(1, 2),
    stop_words="english",
    sublinear_tf=True,
    use_idf=True,
)
X = vectorizer.fit_transform(texts)

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ----------------------------------------------------------------------
# Define models and hyperparameter grids
# ----------------------------------------------------------------------
models = {
    "LogisticRegression": {
        "model": LogisticRegression(max_iter=1000, random_state=42),
        "params": {
            "C": [0.1, 0.5, 1.0, 5.0],
            "solver": ["liblinear", "lbfgs"],
            "class_weight": ["balanced", None]
        }
    },
    "LinearSVC": {
        "model": LinearSVC(max_iter=5000, random_state=42, dual="auto"),
        "params": {
            "C": [0.1, 0.5, 1.0, 5.0],
            "loss": ["hinge", "squared_hinge"],
            "class_weight": ["balanced", None]
        }
    },
    "RandomForest": {
        "model": RandomForestClassifier(random_state=42, n_jobs=-1),
        "params": {
            "n_estimators": [100, 200],
            "max_depth": [10, 20, None],
            "min_samples_split": [2, 5],
            "class_weight": ["balanced", None]
        }
    }
}

# ----------------------------------------------------------------------
# Train and evaluate each model
# ----------------------------------------------------------------------
best_model = None
best_f1 = 0.0
best_name = None
best_report = None

print("\n" + "="*60)
print("Training models with GridSearchCV (3‑fold cross‑validation)")
print("="*60)

for name, config in models.items():
    print(f"\n--- {name} ---")
    start = time.time()
    grid = GridSearchCV(
        config["model"],
        config["params"],
        cv=3,
        scoring='f1_macro',
        n_jobs=-1,
        verbose=0
    )
    grid.fit(X_train, y_train)
    duration = time.time() - start
    print(f"Best params: {grid.best_params_}")
    print(f"Best cross‑val macro F1: {grid.best_score_:.4f}")
    print(f"Training time: {duration:.2f}s")

    # Evaluate on test set
    y_pred = grid.best_estimator_.predict(X_test)
    test_f1 = f1_score(y_test, y_pred, average='macro')
    print(f"Test macro F1: {test_f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=label_map.keys()))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Keep the best model
    if test_f1 > best_f1:
        best_f1 = test_f1
        best_model = grid.best_estimator_
        best_name = name
        best_report = classification_report(y_test, y_pred, target_names=label_map.keys())

print("\n" + "="*60)
print(f"Best model: {best_name} (test macro F1 = {best_f1:.4f})")
print("Best model classification report:")
print(best_report)

# ----------------------------------------------------------------------
# Save the best model
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

print(f"\nBest model saved to {model_path}")

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

print("\n✅ Arjuna training complete. Restart the server to use the new model.")
