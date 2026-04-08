#!/usr/bin/env python3
"""
Enhanced Arjuna training with multiple datasets from Hugging Face.
Datasets:
1. S-Labs/prompt-injection-dataset (binary, ~10k)
2. TrustAIRLab/in-the-wild-jailbreak-prompts (jailbreak prompts, ~15k total, 1.4k injection)
3. rubend18/ChatGPT-Jailbreak-Prompts (small, augmentation)
4. neuralchemy/Prompt-injection-dataset (newer binary)
5. openai/moderation-api-release (safety set, may contain benign and harmful content)
6. JailbreakBench/JBB-Behaviors (eval set)
Also we will include the previously used Gandalf datasets as optional.
"""

import os
import json
import random
import pickle
import requests
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
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Target class counts (adjust based on data availability)
TARGET_COUNTS = {
    "benign": 5000,
    "prompt_injection": 5000,
    "policy_bypass": 2000,   # will be derived from moderation categories
    "data_exfiltration": 2000,  # may need synthetic or from exfiltration-specific sources
}

# ----------------------------------------------------------------------
# Helper to download from Hugging Face
# ----------------------------------------------------------------------
try:
    from datasets import load_dataset
except ImportError:
    os.system("pip install datasets")
    from datasets import load_dataset

# ----------------------------------------------------------------------
# Load and label each dataset
# ----------------------------------------------------------------------
all_data = []  # list of (text, label)

# ----------------------------------------------------------------------
# 1. S-Labs/prompt-injection-dataset
# ----------------------------------------------------------------------
print("Loading S-Labs/prompt-injection-dataset...")
try:
    ds1 = load_dataset("S-Labs/prompt-injection-dataset", split="train")
    # It contains 'prompt' and 'label' (0=benign, 1=injection)
    for row in ds1:
        text = row["prompt"]
        label = "prompt_injection" if row["label"] == 1 else "benign"
        all_data.append((text, label))
    print(f"  Added {len(ds1)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 2. TrustAIRLab/in-the-wild-jailbreak-prompts
# ----------------------------------------------------------------------
print("Loading TrustAIRLab/in-the-wild-jailbreak-prompts...")
try:
    ds2 = load_dataset("TrustAIRLab/in-the-wild-jailbreak-prompts", split="train")
    # Dataset has 'prompt' and 'label' (0=benign, 1=jailbreak)
    for row in ds2:
        text = row["prompt"]
        label = "prompt_injection" if row["label"] == 1 else "benign"
        all_data.append((text, label))
    print(f"  Added {len(ds2)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 3. rubend18/ChatGPT-Jailbreak-Prompts
# ----------------------------------------------------------------------
print("Loading rubend18/ChatGPT-Jailbreak-Prompts...")
try:
    ds3 = load_dataset("rubend18/ChatGPT-Jailbreak-Prompts", split="train")
    # CSV with 'Prompt' column, all are jailbreak prompts
    for row in ds3:
        text = row["Prompt"]
        all_data.append((text, "prompt_injection"))
    print(f"  Added {len(ds3)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 4. neuralchemy/Prompt-injection-dataset
# ----------------------------------------------------------------------
print("Loading neuralchemy/Prompt-injection-dataset...")
try:
    ds4 = load_dataset("neuralchemy/Prompt-injection-dataset", split="train")
    # Assume it has 'text' and 'label' (0/1). If not, adjust.
    # Quick inspection: from dataset card, it's likely similar to binary.
    # We'll assume columns: 'text', 'label'
    for row in ds4:
        text = row.get("text") or row.get("prompt")
        if not text:
            continue
        label = "prompt_injection" if row.get("label", 0) == 1 else "benign"
        all_data.append((text, label))
    print(f"  Added {len(ds4)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 5. openai/moderation-api-release (safety dataset)
# ----------------------------------------------------------------------
print("Loading openai/moderation-api-release...")
try:
    ds5 = load_dataset("openai/moderation-api-release", split="train")
    # It's a CSV with 'text' and 'category' (hate, sexual, violence, etc.)
    # We'll map certain categories to policy_bypass, others to benign.
    # For data_exfiltration, this dataset may not contain explicit exfiltration.
    for row in ds5:
        text = row.get("text")
        if not text:
            continue
        category = row.get("category", "")
        if category in ["hate", "sexual", "violence", "self-harm"]:
            # treat as policy bypass (trying to bypass safety)
            all_data.append((text, "policy_bypass"))
        else:
            # treat as benign (non-harmful)
            all_data.append((text, "benign"))
    print(f"  Added {len(ds5)} samples")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 6. Optional: Gandalf datasets (if available)
# ----------------------------------------------------------------------
try:
    print("Loading Gandalf ignore_instructions...")
    gandalf_ignore = load_dataset("Lakera/gandalf_ignore_instructions", split="train")
    for row in gandalf_ignore:
        all_data.append((row["text"], "prompt_injection"))
    print(f"  Added {len(gandalf_ignore)} samples")
except:
    print("  Gandalf ignore_instructions not available, skipping.")

try:
    print("Loading Gandalf summarization...")
    gandalf_summ = load_dataset("Lakera/gandalf_summarization", split="train")
    for row in gandalf_summ:
        all_data.append((row["text"], "prompt_injection"))
    print(f"  Added {len(gandalf_summ)} samples")
except:
    print("  Gandalf summarization not available, skipping.")

# ----------------------------------------------------------------------
# 7. Augment data_exfiltration with synthetic examples (if needed)
# ----------------------------------------------------------------------
# We need at least 2000 data_exfiltration samples. Since we have few from real sources,
# we'll generate synthetic ones using a simple pattern expansion.
exfil_count = sum(1 for _, label in all_data if label == "data_exfiltration")
if exfil_count < TARGET_COUNTS["data_exfiltration"]:
    needed = TARGET_COUNTS["data_exfiltration"] - exfil_count
    print(f"Generating {needed} synthetic data_exfiltration examples...")
    # Base patterns
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
    # Multiply by repeating with variations (simplistic)
    import itertools
    variations = []
    for base in base_exfil:
        # Add variations with minor changes
        variations.append(base)
        variations.append(base.replace("exfiltrate", "extract"))
        variations.append(base.replace("?", "."))
        variations.append(base.replace("how", "what is the best way to"))
        variations.append(base.replace("?", ", step by step."))
    variations = list(set(variations))  # deduplicate
    # Repeat until we have enough
    while len(variations) < needed:
        variations = variations * 2
    for text in variations[:needed]:
        all_data.append((text, "data_exfiltration"))
    print(f"  Added {needed} synthetic samples.")

# ----------------------------------------------------------------------
# 8. Optional: add benign samples from a local file if available
# ----------------------------------------------------------------------
benign_file = DATA_DIR / "benign_prompts.txt"
if benign_file.exists():
    with open(benign_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                all_data.append((line, "benign"))
    print(f"Loaded additional benign prompts from {benign_file}")

# ----------------------------------------------------------------------
# Balance dataset
# ----------------------------------------------------------------------
print("\nTotal samples before balancing:", len(all_data))
counts_before = Counter(label for _, label in all_data)
for k, v in counts_before.items():
    print(f"  {k}: {v}")

# Group by label
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
print(f"\nAfter balancing: {len(balanced)} samples")
counts_after = Counter(label for _, label in balanced)
for k, v in counts_after.items():
    print(f"  {k}: {v}")

# Save balanced dataset
balanced_path = DATA_DIR / "arjuna_dataset_enhanced.json"
with open(balanced_path, "w") as f:
    json.dump([{"text": t, "label": l} for t, l in balanced], f, indent=2)
print(f"Saved balanced dataset to {balanced_path}")

# ----------------------------------------------------------------------
# Train model
# ----------------------------------------------------------------------
texts = [t for t, _ in balanced]
labels = [l for _, l in balanced]

label_map = {l: i for i, l in enumerate(sorted(set(labels)))}
y = np.array([label_map[l] for l in labels])

vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
X = vectorizer.fit_transform(texts)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("\nClassification Report (test set):")
print(classification_report(y_test, y_pred, target_names=label_map.keys()))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# ----------------------------------------------------------------------
# Save model
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

# ----------------------------------------------------------------------
# Copy to Arjuna engine folder
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

print("\n✅ Enhanced Arjuna training completed. Restart the server to use the new model.")
