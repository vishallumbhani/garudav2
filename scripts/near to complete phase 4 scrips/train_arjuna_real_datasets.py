#!/usr/bin/env python3
"""
Train Arjuna on real-world datasets:
- Lakera/gandalf_ignore_instructions
- Lakera/gandalf_summarization
- rubend18/ChatGPT-Jailbreak-Prompts
- openai/moderation-api-release (GitHub)
"""

import os
import json
import random
import pickle
import requests
import zipfile
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
DATA_DIR = PROJECT_ROOT / "data" / "ml"
SOURCES_DIR = DATA_DIR / "sources"
MODEL_DIR = PROJECT_ROOT / "models"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Target class counts (adjust as needed)
TARGET_COUNTS = {
    "benign": 2000,
    "prompt_injection": 2000,
    "policy_bypass": 1000,
    "data_exfiltration": 1000,
}

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def download_file(url, dest):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        print(f"Downloaded {dest}")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

# ----------------------------------------------------------------------
# 1. Load Hugging Face datasets
# ----------------------------------------------------------------------
try:
    from datasets import load_dataset
except ImportError:
    os.system("pip install datasets")
    from datasets import load_dataset

print("Loading Lakera/gandalf_ignore_instructions...")
gandalf_ignore = load_dataset("Lakera/gandalf_ignore_instructions", split="train")
# This dataset has 'text' column and maybe 'label'? It's prompt injection examples.
# All examples are prompt injections.
injection_texts = [item["text"] for item in gandalf_ignore]
print(f"  Loaded {len(injection_texts)} injection samples.")

print("Loading Lakera/gandalf_summarization...")
gandalf_summarization = load_dataset("Lakera/gandalf_summarization", split="train")
# This dataset contains 'text' and 'gandalf_answer'. We'll treat the 'text' as the prompt.
# Many of these are jailbreak attempts; we'll map them to prompt_injection.
summ_texts = [item["text"] for item in gandalf_summarization]
injection_texts.extend(summ_texts)
print(f"  Added {len(summ_texts)} more injection samples (total {len(injection_texts)}).")

print("Loading rubend18/ChatGPT-Jailbreak-Prompts...")
jailbreak = load_dataset("rubend18/ChatGPT-Jailbreak-Prompts", split="train")
# This dataset has 'Prompt' column. All are jailbreak prompts (injection).
jb_texts = [item["Prompt"] for item in jailbreak]
injection_texts.extend(jb_texts)
print(f"  Added {len(jb_texts)} more injection samples (total {len(injection_texts)}).")

# ----------------------------------------------------------------------
# 2. Load OpenAI Moderation dataset (GitHub)
# ----------------------------------------------------------------------
moderation_url = "https://github.com/openai/moderation-api-release/raw/main/data/moderation_dataset.csv"
moderation_csv = SOURCES_DIR / "moderation_dataset.csv"
if not moderation_csv.exists():
    download_file(moderation_url, moderation_csv)

# Parse CSV (it may have columns: text, category, etc.)
# We'll assume it has at least 'text' and 'category' (e.g., hate, sexual, violence).
# Map certain categories to policy_bypass or data_exfiltration.
bypass_texts = []
exfil_texts = []
if moderation_csv.exists():
    import pandas as pd
    df = pd.read_csv(moderation_csv)
    # Map categories (adjust to actual column names if different)
    # Based on typical moderation dataset, categories might be 'hate', 'sexual', 'violence', 'self-harm', etc.
    # We'll map policy violations to policy_bypass; data exfiltration is rare here.
    for _, row in df.iterrows():
        text = row.get("text", "")
        if not text:
            continue
        # This is a placeholder; you need to adapt to the actual schema.
        # For now, we'll treat all as policy_bypass.
        bypass_texts.append(text)
    print(f"Loaded {len(bypass_texts)} policy_bypass samples from moderation dataset.")
else:
    # Fallback: generate synthetic bypass samples (or use a local file)
    bypass_texts = [
        "How to bypass content filters?",
        "Methods to evade moderation systems.",
    ] * 50
    print(f"Using fallback {len(bypass_texts)} policy_bypass samples.")

# ----------------------------------------------------------------------
# 3. Load benign samples (we need a source; we'll create synthetic or use a real benign dataset)
# ----------------------------------------------------------------------
# For now, we'll generate synthetic benign prompts.
# In production, replace this with a real benign dataset (e.g., from user logs or common questions).
benign_texts = [
    "Hello, how are you?",
    "What's the weather like today?",
    "Can you help me with my homework?",
    "Tell me a joke.",
    "Explain the theory of relativity.",
    "What is the capital of France?",
    "How do I cook pasta?",
    "Recommend a good book.",
    "What is the meaning of life?",
    "Tell me a fun fact.",
] * 200  # 2000 samples

print(f"Using {len(benign_texts)} benign samples (synthetic).")

# ----------------------------------------------------------------------
# 4. Combine and label
# ----------------------------------------------------------------------
all_data = []
all_data.extend([(text, "prompt_injection") for text in injection_texts])
all_data.extend([(text, "policy_bypass") for text in bypass_texts])
all_data.extend([(text, "data_exfiltration") for text in exfil_texts])
all_data.extend([(text, "benign") for text in benign_texts])

print(f"Total samples before balancing: {len(all_data)}")
counts_before = Counter(label for _, label in all_data)
for k, v in counts_before.items():
    print(f"  {k}: {v}")

# ----------------------------------------------------------------------
# 5. Balance dataset
# ----------------------------------------------------------------------
label_to_texts = {}
for text, label in all_data:
    label_to_texts.setdefault(label, []).append(text)

balanced = []
for label, target in TARGET_COUNTS.items():
    texts = label_to_texts.get(label, [])
    if len(texts) < target:
        # Upsample with repetition
        factor = (target + len(texts) - 1) // len(texts) if texts else 0
        sampled = texts * factor
        balanced.extend([(text, label) for text in sampled[:target]])
    else:
        # Downsample
        balanced.extend([(text, label) for text in random.sample(texts, target)])

random.shuffle(balanced)
print(f"After balancing: {len(balanced)} samples")
counts_after = Counter(label for _, label in balanced)
for k, v in counts_after.items():
    print(f"  {k}: {v}")

# Save balanced dataset for reference
balanced_path = DATA_DIR / "arjuna_dataset.json"
with open(balanced_path, "w") as f:
    json.dump([{"text": t, "label": l} for t, l in balanced], f, indent=2)
print(f"Saved balanced dataset to {balanced_path}")

# ----------------------------------------------------------------------
# 6. Train model
# ----------------------------------------------------------------------
texts = [t for t, _ in balanced]
labels = [l for _, l in balanced]

label_map = {l: i for i, l in enumerate(sorted(set(labels)))}
y = np.array([label_map[l] for l in labels])

# TF-IDF vectorizer
vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
X = vectorizer.fit_transform(texts)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Train model
model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print("\nClassification Report (test set):")
print(classification_report(y_test, y_pred, target_names=label_map.keys()))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# ----------------------------------------------------------------------
# 7. Save model and vectorizer
# ----------------------------------------------------------------------
model_path = MODEL_DIR / "arjuna_model.pkl"
vectorizer_path = MODEL_DIR / "arjuna_vectorizer.pkl"
label_map_path = MODEL_DIR / "arjuna_label_map.json"

with open(model_path, "wb") as f:
    pickle.dump(model, f)
with open(vectorizer_path, "wb") as f:
    pickle.dump(vectorizer, f)
with open(label_map_path, "w") as f:
    json.dump(label_map, f, indent=2)

print(f"\nModel saved to {model_path}")
print(f"Vectorizer saved to {vectorizer_path}")
print(f"Label map saved to {label_map_path}")

# ----------------------------------------------------------------------
# 8. Copy to Arjuna engine folder
# ----------------------------------------------------------------------
arjuna_dir = PROJECT_ROOT / "src" / "engines" / "arjuna"
arjuna_dir.mkdir(parents=True, exist_ok=True)
for fname in ["arjuna_model.pkl", "arjuna_vectorizer.pkl", "arjuna_label_map.json"]:
    src = MODEL_DIR / fname
    dst = arjuna_dir / fname
    if src.exists():
        import shutil
        shutil.copy(src, dst)
        print(f"Copied {fname} to {dst}")

print("\n✅ Arjuna training completed. Restart the server to use the new model.")
