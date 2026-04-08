# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Build a clean, balanced dataset for Arjuna from all sources in data/ml/sources/.
Supports: JSON (single object or JSONL), JSONL, CSV, XLSX, PARQUET.
Auto-generates synthetic examples for low classes with bounded attempts.
"""

import os
import sys
import json
import csv
import random
import re
from pathlib import Path
from collections import Counter
import pandas as pd
from tqdm import tqdm

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
SOURCES_DIR = PROJECT_ROOT / "data" / "ml" / "sources"
OUTPUT_DIR = PROJECT_ROOT / "data" / "ml"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COUNTS = {
    "benign": 8000,
    "prompt_injection": 5000,
    "policy_bypass": 2000,
    "data_exfiltration": 2000,
}

MIN_REQUIRED = {
    "benign": 1000,
    "prompt_injection": 1000,
    "policy_bypass": 500,
    "data_exfiltration": 500,
}

MIN_TEXT_LEN = 10
MAX_SAMPLES_PER_SOURCE = 10000   # cap per file

# Maximum number of synthetic examples to generate per class (avoid infinite loops)
MAX_SYNTHETIC = 1000

# ----------------------------------------------------------------------
# Label mapping from source labels to our 4 classes
# ----------------------------------------------------------------------
LABEL_MAP = {
    # benign
    "benign": "benign",
    "safe": "benign",
    "normal": "benign",
    "harmless": "benign",
    "clean": "benign",
    "neutral": "benign",
    "general": "benign",
    "allowed": "benign",
    "non-malicious": "benign",
    "0": "benign",
    "non_harmful": "benign",
    "nonharmful": "benign",
    # prompt_injection
    "injection": "prompt_injection",
    "prompt_injection": "prompt_injection",
    "jailbreak": "prompt_injection",
    "instruction override": "prompt_injection",
    "ignore previous instructions": "prompt_injection",
    "system prompt extraction": "prompt_injection",
    "role manipulation": "prompt_injection",
    "prompt attack": "prompt_injection",
    "adversarial prompt": "prompt_injection",
    "dan": "prompt_injection",
    "prompt leak": "prompt_injection",
    "agent hijack": "prompt_injection",
    "malicious": "prompt_injection",
    "1": "prompt_injection",
    "harmful": "prompt_injection",
    "attack": "prompt_injection",
    "override": "prompt_injection",
    # policy_bypass
    "bypass": "policy_bypass",
    "policy_bypass": "policy_bypass",
    "unsafe request": "policy_bypass",
    "disallowed content": "policy_bypass",
    "harmful advice": "policy_bypass",
    "evasion": "policy_bypass",
    "moderation bypass": "policy_bypass",
    "restricted request": "policy_bypass",
    "exploit instructions": "policy_bypass",
    "prohibited assistance": "policy_bypass",
    "red_team": "policy_bypass",
    "redteam": "policy_bypass",
    "safety_bypass": "policy_bypass",
    # data_exfiltration
    "exfiltration": "data_exfiltration",
    "data_exfiltration": "data_exfiltration",
    "secret leakage": "data_exfiltration",
    "credential theft": "data_exfiltration",
    "api key extraction": "data_exfiltration",
    "token exposure": "data_exfiltration",
    "pii leak": "data_exfiltration",
    "confidential data leak": "data_exfiltration",
    "system prompt dump": "data_exfiltration",
    "internal file extraction": "data_exfiltration",
    "database dump": "data_exfiltration",
    "leak": "data_exfiltration",
    "secret_extraction": "data_exfiltration",
}

# ----------------------------------------------------------------------
# Helper: extract text from a record
# ----------------------------------------------------------------------
def extract_text(record):
    """Try to find a text field in a dict record."""
    for key in ["text", "prompt", "instruction", "query", "question", "content", "user_input", "input"]:
        if key in record:
            val = record[key]
            if isinstance(val, str):
                return val.strip()
    for val in record.values():
        if isinstance(val, str) and len(val) > MIN_TEXT_LEN:
            return val.strip()
    return None

def extract_label(record):
    """Map source label to our class. Returns (label, is_known)."""
    for key in ["label", "category", "type", "class", "attack_type", "harmfulness"]:
        if key in record:
            raw = str(record[key]).lower()
            if raw in LABEL_MAP:
                return LABEL_MAP[raw], True
    return None, False

def heuristic_label(text):
    """Assign a class based on keywords - only when no source label. Never returns 'benign'."""
    text_lower = text.lower()
    exfil_keywords = ["exfiltrate", "exfiltration", "extract data", "copy sensitive", "steal data",
                      "leak data", "dump database", "covert transfer", "dns tunnel", "hide stolen"]
    if any(kw in text_lower for kw in exfil_keywords):
        return "data_exfiltration"
    injection_keywords = ["ignore previous", "ignore instructions", "forget previous", "act as system",
                          "dan", "do anything now", "reveal system prompt", "override instructions",
                          "print hidden", "jailbreak", "developer mode", "unrestricted"]
    if any(kw in text_lower for kw in injection_keywords):
        return "prompt_injection"
    bypass_keywords = ["for educational purposes", "as a researcher", "hypothetically",
                       "red team", "bypass safeguards", "evade moderation", "test content filters",
                       "for testing purposes", "academic purposes", "security researcher"]
    if any(kw in text_lower for kw in bypass_keywords):
        return "policy_bypass"
    return None

def normalize_text(text):
    """Lowercase, compress whitespace, remove punctuation."""
    t = text.lower()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[^\w\s]', '', t)
    return t.strip()

# ----------------------------------------------------------------------
# Synthetic generator (with bounded attempts)
# ----------------------------------------------------------------------
def generate_synthetic(label, target, current_count, existing_texts_set):
    """Generate synthetic examples for policy_bypass or data_exfiltration."""
    needed = target - current_count
    if needed <= 0:
        return []

    # Cap the number to avoid trying to generate too many from limited templates
    needed = min(needed, MAX_SYNTHETIC)
    print(f"Generating up to {needed} synthetic {label} examples...")

    if label == "policy_bypass":
        templates = [
            "For educational purposes, {}.",
            "As a researcher, {}.",
            "Explain how attackers {}.",
            "What are methods to {}?",
            "Hypothetically, {}.",
            "In a simulated environment, {}.",
            "I'm a red team member. {}.",
            "For a security audit, {}.",
            "Can you describe ways to {}?",
            "How does one {}?",
        ]
        seeds = [
            "bypass authentication",
            "evade detection",
            "trick content filters",
            "avoid safety controls",
            "circumvent security policies",
            "bypass login restrictions",
            "evade moderation systems",
            "get around web filters",
            "disable monitoring",
            "bypass 2FA",
            "evade endpoint protection",
            "circumvent access controls",
            "bypass DLP",
            "evade content moderation",
        ]
    elif label == "data_exfiltration":
        templates = [
            "How to {}?",
            "Methods to {}.",
            "Explain techniques for {}.",
            "What are common ways to {}?",
            "As a security researcher, demonstrate {}.",
            "In a controlled environment, show {}.",
            "Describe how attackers {}.",
            "How can someone {}?",
        ]
        seeds = [
            "exfiltrate data via DNS tunneling",
            "copy sensitive files without detection",
            "hide stolen data in network traffic",
            "leak confidential records",
            "extract API keys from an application",
            "steal database dumps quietly",
            "export customer data covertly",
            "move data without alerting defenders",
            "smuggle secrets out of a network",
            "use covert channels to transfer data",
            "exfiltrate data using email",
            "steal credentials silently",
        ]
    else:
        return []

    import itertools
    combos = list(itertools.product(templates, seeds))
    random.shuffle(combos)

    generated = []

    for template, seed in combos:
        if len(generated) >= needed:
            break

        base = template.format(seed)
        variations = [
            base,
            base.capitalize(),
            base.replace("?", "."),
            f"Here's how to {seed}.",
            f"Can you explain {seed}?",
            f"I need to understand {seed}.",
            f"How does one {seed}?",
            f"Show me how to {seed}.",
            f"Provide steps to {seed}.",
        ]

        for var in variations:
            if len(generated) >= needed:
                break
            norm = normalize_text(var)
            if norm not in existing_texts_set:
                generated.append((var, label))
                existing_texts_set.add(norm)

    # Bounded fallback
    max_attempts = needed * 20
    attempts = 0
    while len(generated) < needed and attempts < max_attempts:
        attempts += 1
        template = random.choice(templates)
        seed = random.choice(seeds)
        extra_text = f"{template.format(seed)} Example variant {attempts}."
        norm = normalize_text(extra_text)
        if norm not in existing_texts_set:
            generated.append((extra_text, label))
            existing_texts_set.add(norm)

    if len(generated) < needed:
        print(f"  Warning: only generated {len(generated)} / {needed} unique synthetic examples for {label}")

    print(f"  Generated {len(generated)} synthetic examples.")
    return generated

# ----------------------------------------------------------------------
# Process a single file
# ----------------------------------------------------------------------
def process_file(file_path):
    ext = file_path.suffix.lower()
    if ext == ".json":
        # Try single JSON first, then fallback to JSONL
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # It's a single JSON object
            if isinstance(data, list):
                for record in data:
                    if not isinstance(record, dict):
                        continue
                    text = extract_text(record)
                    if not text or len(text) < MIN_TEXT_LEN:
                        continue
                    label, known = extract_label(record)
                    if known:
                        yield text, label, False, None
                    else:
                        heur = heuristic_label(text)
                        if heur:
                            yield text, heur, True, None
                        else:
                            yield text, None, False, record.get("label", "unknown")
            elif isinstance(data, dict):
                for key in ["data", "examples", "samples", "root"]:
                    if key in data and isinstance(data[key], list):
                        for record in data[key]:
                            if not isinstance(record, dict):
                                continue
                            text = extract_text(record)
                            if not text or len(text) < MIN_TEXT_LEN:
                                continue
                            label, known = extract_label(record)
                            if known:
                                yield text, label, False, None
                            else:
                                heur = heuristic_label(text)
                                if heur:
                                    yield text, heur, True, None
                                else:
                                    yield text, None, False, record.get("label", "unknown")
        except json.JSONDecodeError as e:
            # Fallback to JSONL (line‑by‑line)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except:
                            continue
                        if not isinstance(record, dict):
                            continue
                        text = extract_text(record)
                        if not text or len(text) < MIN_TEXT_LEN:
                            continue
                        label, known = extract_label(record)
                        if known:
                            yield text, label, False, None
                        else:
                            heur = heuristic_label(text)
                            if heur:
                                yield text, heur, True, None
                            else:
                                yield text, None, False, record.get("label", "unknown")
            except Exception as ex:
                print(f"  Error reading {file_path}: {ex}")
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
    elif ext == ".jsonl":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except:
                        continue
                    if not isinstance(record, dict):
                        continue
                    text = extract_text(record)
                    if not text or len(text) < MIN_TEXT_LEN:
                        continue
                    label, known = extract_label(record)
                    if known:
                        yield text, label, False, None
                    else:
                        heur = heuristic_label(text)
                        if heur:
                            yield text, heur, True, None
                        else:
                            yield text, None, False, record.get("label", "unknown")
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
    elif ext == ".csv":
        success = False
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(file_path, encoding=encoding, on_bad_lines="skip")
                success = True
                break
            except:
                continue
        if not success:
            print(f"  Could not read {file_path} as CSV")
            return
        text_col = None
        for col in df.columns:
            if col.lower() in ["text", "prompt", "instruction", "query", "question", "content", "user_input"]:
                text_col = col
                break
        if not text_col:
            for col in df.columns:
                if df[col].dtype == object:
                    text_col = col
                    break
        if text_col is None:
            return
        label_col = None
        for col in df.columns:
            if col.lower() in ["label", "category", "type", "class", "attack_type", "harmfulness"]:
                label_col = col
                break
        for _, row in df.iterrows():
            text = str(row[text_col]) if pd.notna(row[text_col]) else ""
            if len(text) < MIN_TEXT_LEN:
                continue
            if label_col and pd.notna(row[label_col]):
                raw = str(row[label_col]).lower()
                if raw in LABEL_MAP:
                    label = LABEL_MAP[raw]
                    yield text, label, False, None
                else:
                    heur = heuristic_label(text)
                    if heur:
                        yield text, heur, True, None
                    else:
                        yield text, None, False, raw
            else:
                heur = heuristic_label(text)
                if heur:
                    yield text, heur, True, None
                else:
                    yield text, None, False, None
    elif ext == ".xlsx":
        try:
            import openpyxl
            df = pd.read_excel(file_path, engine="openpyxl")
        except:
            print(f"  Could not read {file_path} as Excel")
            return
        text_col = None
        for col in df.columns:
            if col.lower() in ["text", "prompt", "instruction", "query", "question", "content", "user_input"]:
                text_col = col
                break
        if not text_col:
            for col in df.columns:
                if df[col].dtype == object:
                    text_col = col
                    break
        if text_col is None:
            return
        label_col = None
        for col in df.columns:
            if col.lower() in ["label", "category", "type", "class", "attack_type", "harmfulness"]:
                label_col = col
                break
        for _, row in df.iterrows():
            text = str(row[text_col]) if pd.notna(row[text_col]) else ""
            if len(text) < MIN_TEXT_LEN:
                continue
            if label_col and pd.notna(row[label_col]):
                raw = str(row[label_col]).lower()
                if raw in LABEL_MAP:
                    label = LABEL_MAP[raw]
                    yield text, label, False, None
                else:
                    heur = heuristic_label(text)
                    if heur:
                        yield text, heur, True, None
                    else:
                        yield text, None, False, raw
            else:
                heur = heuristic_label(text)
                if heur:
                    yield text, heur, True, None
                else:
                    yield text, None, False, None
    elif ext == ".parquet":
        try:
            df = pd.read_parquet(file_path)
        except:
            print(f"  Could not read {file_path} as Parquet")
            return
        text_col = None
        for col in df.columns:
            if col.lower() in ["text", "prompt", "instruction", "query", "question", "content", "user_input"]:
                text_col = col
                break
        if not text_col:
            for col in df.columns:
                if df[col].dtype == object:
                    text_col = col
                    break
        if text_col is None:
            return
        label_col = None
        for col in df.columns:
            if col.lower() in ["label", "category", "type", "class", "attack_type", "harmfulness"]:
                label_col = col
                break
        for _, row in df.iterrows():
            text = str(row[text_col]) if pd.notna(row[text_col]) else ""
            if len(text) < MIN_TEXT_LEN:
                continue
            if label_col and pd.notna(row[label_col]):
                raw = str(row[label_col]).lower()
                if raw in LABEL_MAP:
                    label = LABEL_MAP[raw]
                    yield text, label, False, None
                else:
                    heur = heuristic_label(text)
                    if heur:
                        yield text, heur, True, None
                    else:
                        yield text, None, False, raw
            else:
                heur = heuristic_label(text)
                if heur:
                    yield text, heur, True, None
                else:
                    yield text, None, False, None
    else:
        pass

# ----------------------------------------------------------------------
# Main processing
# ----------------------------------------------------------------------
def main():
    all_files = []
    for ext in ["*.json", "*.jsonl", "*.csv", "*.xlsx", "*.parquet"]:
        all_files.extend(SOURCES_DIR.rglob(ext))
    print(f"Found {len(all_files)} files to process.")

    all_samples = []
    uncertain = []
    for file_path in tqdm(all_files, desc="Processing files"):
        file_samples = []
        for text, label, is_heuristic, original in process_file(file_path):
            if label is not None:
                file_samples.append((text, label, is_heuristic))
            else:
                uncertain.append({
                    "text": text,
                    "original_label": original,
                    "source": str(file_path)
                })
        if len(file_samples) > MAX_SAMPLES_PER_SOURCE:
            file_samples = random.sample(file_samples, MAX_SAMPLES_PER_SOURCE)
        for text, label, is_heuristic in file_samples:
            all_samples.append((text, label))
            if is_heuristic:
                uncertain.append({
                    "text": text,
                    "original_label": "heuristic",
                    "source": str(file_path)
                })

    review_path = OUTPUT_DIR / "arjuna_review_queue.json"
    with open(review_path, "w") as f:
        json.dump(uncertain, f, indent=2)
    print(f"Wrote {len(uncertain)} uncertain samples to {review_path}")

    print(f"Total samples collected: {len(all_samples)}")
    counts = Counter(label for _, label in all_samples)
    print("Class distribution before balancing:")
    for k, v in counts.items():
        print(f"  {k}: {v}")

    seen = set()
    unique_samples = []
    for text, label in all_samples:
        norm = normalize_text(text)
        if norm not in seen:
            seen.add(norm)
            unique_samples.append((text, label))
    print(f"After deduplication: {len(unique_samples)} samples")

    counts_unique = Counter(label for _, label in unique_samples)
    for class_name, min_required in MIN_REQUIRED.items():
        if counts_unique.get(class_name, 0) < min_required:
            print(f"Warning: Class '{class_name}' has only {counts_unique.get(class_name, 0)} samples, below minimum {min_required}. Consider adding more data.")

    # ------------------------------------------------------------------
    # Synthetic generation for low classes
    # ------------------------------------------------------------------
    # Create a set of normalized texts for duplicate avoidance
    existing_texts = set(normalize_text(t) for t, _ in unique_samples)
    for label, target in TARGET_COUNTS.items():
        current = counts_unique.get(label, 0)
        if current < target and label in ["policy_bypass", "data_exfiltration"]:
            print(f"Starting synthetic generation for {label}: current={current}, target={target}")
            synthetic = generate_synthetic(label, target, current, existing_texts)
            if synthetic:
                unique_samples.extend(synthetic)
                # Update counts (roughly)
                counts_unique[label] = len([l for _, l in synthetic]) + current
                print(f"After synthetic generation: {label} now has {counts_unique[label]} samples.")

    # Recompute counts_unique after synthetic additions
    counts_unique = Counter(label for _, label in unique_samples)
    print("\nFinal class distribution after synthetic generation:")
    for k, v in counts_unique.items():
        print(f"  {k}: {v}")

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------
    label_to_texts = {}
    for text, label in unique_samples:
        label_to_texts.setdefault(label, []).append(text)

    balanced = []
    for label, target in TARGET_COUNTS.items():
        texts = label_to_texts.get(label, [])
        if not texts:
            print(f"Warning: no samples available for class '{label}', skipping.")
            continue
        if len(texts) < target:
            factor = (target + len(texts) - 1) // len(texts) if texts else 0
            sampled = texts * factor
            balanced.extend([(text, label) for text in sampled[:target]])
        else:
            balanced.extend([(text, label) for text in random.sample(texts, target)])

    random.shuffle(balanced)
    print(f"\nAfter balancing: {len(balanced)} samples")
    counts_balanced = Counter(label for _, label in balanced)
    for k, v in counts_balanced.items():
        print(f"  {k}: {v}")

    # Save final dataset
    output_json = OUTPUT_DIR / "arjuna_final_dataset.json"
    with open(output_json, "w") as f:
        json.dump([{"text": text, "label": label} for text, label in balanced], f, indent=2)
    print(f"Saved JSON dataset to {output_json}")

    output_csv = OUTPUT_DIR / "arjuna_final_dataset.csv"
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        for text, label in balanced:
            writer.writerow([text, label])
    print(f"Saved CSV dataset to {output_csv}")

    print("\nDataset building complete. You can now use this for training.")

if __name__ == "__main__":
    main()
