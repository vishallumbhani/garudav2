# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Train Arjuna with recommended high-quality datasets.
Uses only ASCII characters to avoid encoding errors.
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

# ----------------------------------------------------------------------
# Load Hugging Face datasets
# ----------------------------------------------------------------------
try:
    from datasets import load_dataset
except ImportError:
    os.system("pip install datasets")
    from datasets import load_dataset

all_data = []  # (text, label)

print("=" * 60)
print("Loading high-quality datasets...")

# ---------- Prompt Injection / Jailbreak ----------
print("Loading Gandalf ignore_instructions...")
try:
    ds = load_dataset("Lakera/gandalf_ignore_instructions", split="train")
    all_data.extend([(row["text"], "prompt_injection") for row in ds])
    print(f"  Added {len(ds)} injection samples.")
except Exception as e:
    print(f"  Failed: {e}")

print("Loading Gandalf summarization...")
try:
    ds = load_dataset("Lakera/gandalf_summarization", split="train")
    all_data.extend([(row["text"], "prompt_injection") for row in ds])
    print(f"  Added {len(ds)} injection samples.")
except Exception as e:
    print(f"  Failed: {e}")

print("Loading TrustAIRLab/in-the-wild-jailbreak-prompts...")
try:
    ds = load_dataset("TrustAIRLab/in-the-wild-jailbreak-prompts", split="train")
    for row in ds:
        label = "prompt_injection" if row["label"] == 1 else "benign"
        all_data.append((row["prompt"], label))
    print(f"  Added {len(ds)} samples (jailbreak + benign).")
except Exception as e:
    print(f"  Failed: {e}")

print("Loading rubend18/ChatGPT-Jailbreak-Prompts...")
try:
    ds = load_dataset("rubend18/ChatGPT-Jailbreak-Prompts", split="train")
    all_data.extend([(row["Prompt"], "prompt_injection") for row in ds])
    print(f"  Added {len(ds)} injection samples.")
except Exception as e:
    print(f"  Failed: {e}")

print("Loading neuralchemy/Prompt-injection-dataset...")
try:
    ds = load_dataset("neuralchemy/Prompt-injection-dataset", split="train")
    for row in ds:
        text = row.get("text") or row.get("prompt")
        if not text:
            continue
        label = "prompt_injection" if row.get("label", 0) == 1 else "benign"
        all_data.append((text, label))
    print(f"  Added {len(ds)} samples.")
except Exception as e:
    print(f"  Failed: {e}")

print("Loading markush1/LLM-Jailbreak-Classifier...")
try:
    ds = load_dataset("markush1/LLM-Jailbreak-Classifier", split="train")
    for row in ds:
        label = "prompt_injection" if row["label"] == 1 else "benign"
        all_data.append((row["text"], label))
    print(f"  Added {len(ds)} samples.")
except Exception as e:
    print(f"  Failed: {e}")

# ---------- Policy Bypass ----------
print("Loading openai/moderation...")
try:
    # Use the Hugging Face version of the moderation dataset
    ds = load_dataset("openai/moderation", split="train")
    for row in ds:
        text = row.get("text")
        if not text:
            continue
        category = row.get("category", "")
        if category in ["hate", "sexual", "violence", "self-harm"]:
            all_data.append((text, "policy_bypass"))
        else:
            all_data.append((text, "benign"))
    print(f"  Added {len(ds)} samples (policy_bypass + benign).")
except Exception as e:
    print(f"  Failed: {e}")

# ---------- Benign (Open Assistant) ----------
print("Loading Open Assistant (OASST1) - train split...")
try:
    ds = load_dataset("OpenAssistant/oasst1", split="train")
    benign_texts = [row["text"] for row in ds if row["role"] == "prompter"][:5000]
    all_data.extend([(text, "benign") for text in benign_texts])
    print(f"  Added {len(benign_texts)} benign samples from Open Assistant.")
except Exception as e:
    print(f"  Failed: {e}")

# ---------- Benign (Anthropic Helpful-Harmless) ----------
print("Loading Anthropic Helpful-Harmless - helpful only...")
try:
    ds = load_dataset("Anthropic/hh-rlhf", split="train")
    benign_prompts = []
    for i, row in enumerate(ds):
        if i >= 5000:
            break
        if "prompt" in row:
            benign_prompts.append(row["prompt"])
    all_data.extend([(text, "benign") for text in benign_prompts])
    print(f"  Added {len(benign_prompts)} benign samples from Anthropic dataset.")
except Exception as e:
    print(f"  Failed: {e}")

# ---------- Data Exfiltration (synthetic) ----------
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
else:
    print(f"Data exfiltration count: {exfil_count} (no synthetic needed)")

# ----------------------------------------------------------------------
# Balance classes
# ----------------------------------------------------------------------
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
print(f"\nBalanced dataset: {len(balanced)} samples")
for k, v in Counter(l for _, l in balanced).items():
    print(f"  {k}: {v}")

# Save for reference
balanced_path = DATA_DIR / "arjuna_dataset_balanced.json"
with open(balanced_path, "w") as f:
    json.dump([{"text": t, "label": l} for t, l in balanced], f, indent=2)
print(f"Saved to {balanced_path}")

# ----------------------------------------------------------------------
# Feature extraction & training
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

# Grid search for Logistic Regression
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

print("\n✅ Arjuna training with recommended datasets completed. Restart server.")
