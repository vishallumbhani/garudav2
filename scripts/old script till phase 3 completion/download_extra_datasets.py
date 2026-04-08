# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Download and prepare additional datasets for Arjuna.
Maps each dataset to one of: benign, prompt_injection, policy_bypass, data_exfiltration.
Outputs JSONL files in data/ml/sources/extra/ for the builder to pick up.
"""

import os
import json
import random
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
OUT_DIR = PROJECT_ROOT / "data" / "ml" / "sources" / "extra"
OUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    from datasets import load_dataset
except ImportError:
    os.system("pip install datasets")
    from datasets import load_dataset

def write_jsonl(data, filename):
    path = OUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    print(f"  Saved {len(data)} samples to {path}")

# ----------------------------------------------------------------------
# 1. Jigsaw Toxic Comment Classification
# ----------------------------------------------------------------------
print("Downloading Jigsaw Toxic Comment Classification...")
try:
    # The dataset is on Kaggle, but there is a Hugging Face version: `Jigsaw/toxic-comment-classification`
    # It's a large CSV; we'll use a subset (first 50k) to keep size manageable.
    ds = load_dataset("Jigsaw/toxic-comment-classification", split="train")
    data = []
    for row in ds:
        text = row.get("comment_text", "")
        if not text:
            continue
        # toxicity is a float between 0 and 1; threshold >0.5 => policy_bypass
        toxic = row.get("toxic", 0)
        if toxic > 0.5:
            label = "policy_bypass"
        else:
            label = "benign"
        data.append({"text": text, "label": label})
        if len(data) >= 50000:
            break
    write_jsonl(data, "jigsaw_toxic.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 2. RealToxicityPrompts
# ----------------------------------------------------------------------
print("Downloading RealToxicityPrompts...")
try:
    ds = load_dataset("allenai/real-toxicity-prompts", split="train")
    data = []
    for row in ds:
        prompt = row.get("prompt", {}).get("text", "")
        if not prompt:
            continue
        # Use toxicity score (continuous) to decide label
        toxicity = row.get("toxicity", 0)
        if toxicity > 0.5:
            label = "policy_bypass"
        else:
            label = "benign"
        data.append({"text": prompt, "label": label})
        if len(data) >= 50000:
            break
    write_jsonl(data, "real_toxicity_prompts.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 3. ToxiGen
# ----------------------------------------------------------------------
print("Downloading ToxiGen...")
try:
    ds = load_dataset("skg/toxigen", split="train")
    data = []
    for row in ds:
        text = row.get("text", "")
        if not text:
            continue
        label = "policy_bypass" if row.get("label", 0) == 1 else "benign"
        data.append({"text": text, "label": label})
    write_jsonl(data, "toxigen.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 4. CrowS-Pairs (use the more stereotypic sentences)
# ----------------------------------------------------------------------
print("Downloading CrowS-Pairs...")
try:
    ds = load_dataset("crows-pairs", split="train")
    data = []
    for row in ds:
        sent_more = row.get("sent_more", "")
        if sent_more:
            # This is a sentence containing a stereotype → harmful → policy_bypass
            data.append({"text": sent_more, "label": "policy_bypass"})
        # We could also add sent_less as benign, but skip for brevity
    write_jsonl(data, "crows_pairs.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 5. StereoSet (use stereotypical sentences)
# ----------------------------------------------------------------------
print("Downloading StereoSet...")
try:
    ds = load_dataset("stereoset", split="test")
    data = []
    for row in ds:
        # The dataset has multiple fields; we'll take the `sentence` from `examples` if present
        if "examples" in row:
            for ex in row["examples"]:
                if "sentence" in ex:
                    data.append({"text": ex["sentence"], "label": "policy_bypass"})
        # Or use the `context`? We'll just take sentences.
    write_jsonl(data, "stereoset.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 6. HolisticBias (take prompts that might be harmful – we'll treat as policy_bypass)
# ----------------------------------------------------------------------
print("Downloading HolisticBias...")
try:
    ds = load_dataset("holistic_bias", split="train")
    data = []
    for row in ds:
        text = row.get("text", "")
        if text:
            # The dataset contains prompts with demographic terms; many could be considered harmful.
            # To be safe, we treat all as policy_bypass (or we could sample)
            data.append({"text": text, "label": "policy_bypass"})
    write_jsonl(data, "holistic_bias.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 7. TruthfulQA – benign (questions are harmless)
# ----------------------------------------------------------------------
print("Downloading TruthfulQA...")
try:
    ds = load_dataset("truthful_qa", "generation", split="validation")
    data = []
    for row in ds:
        question = row.get("question", "")
        if question:
            data.append({"text": question, "label": "benign"})
    write_jsonl(data, "truthful_qa.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 8. Anthropic HHH – already used in main script; we'll add the red-teaming part
# ----------------------------------------------------------------------
print("Downloading Anthropic red-teaming dialogues...")
try:
    # The red team dataset is available as `Anthropic/red-team`
    ds = load_dataset("Anthropic/red-team", split="train")
    data = []
    for row in ds:
        # Each row has a dialog; we can extract the user's first turn (the attack)
        transcript = row.get("transcript", "")
        # The transcript is a string with <|user|>...<|assistant|> etc.
        # We'll extract the first user message.
        if "<|user|>" in transcript:
            user_part = transcript.split("<|user|>")[1].split("<|assistant|>")[0].strip()
            if user_part:
                # This is likely a jailbreak attempt → prompt_injection
                data.append({"text": user_part, "label": "prompt_injection"})
    write_jsonl(data, "red_team_dialogues.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

# ----------------------------------------------------------------------
# 9. ProsocialDialog – extract unsafe utterances
# ----------------------------------------------------------------------
print("Downloading ProsocialDialog...")
try:
    ds = load_dataset("allenai/prosocial-dialog", split="train")
    data = []
    for row in ds:
        # Each row has `context` (list of utterances), `responses` (list)
        # The first utterance in context is the initial user message; we'll take it if it's flagged as unsafe.
        # The dataset has `safety_label` for each utterance (0=safe, 1=unsafe)
        # We'll only use those marked unsafe.
        if "context" in row and "safety_label" in row:
            for turn, label in zip(row["context"], row["safety_label"]):
                if label == 1:
                    data.append({"text": turn, "label": "policy_bypass"})
        if len(data) >= 50000:
            break
    write_jsonl(data, "prosocial_dialog_unsafe.jsonl")
except Exception as e:
    print(f"  Failed: {e}")

print("\n✅ Extra datasets downloaded and prepared.")
print("Now run the dataset builder again: python scripts/build_arjuna_dataset.py")
