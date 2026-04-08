# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Download all datasets for Arjuna training.
- Hugging Face datasets: automatically downloaded via `datasets`.
- Kaggle datasets: uses Kaggle API if available; otherwise prints manual instructions.
- GitHub dataset: openai/moderation-api-release (cloned or downloaded manually).
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
SOURCES_DIR = PROJECT_ROOT / "data" / "ml" / "sources"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Downloading datasets for Arjuna")
print("=" * 80)

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def kaggle_download(dataset_ref, dest_dir, filename=None):
    """Download a Kaggle dataset using the Kaggle API (if available)."""
    try:
        cmd = f"kaggle datasets download -d {dataset_ref} --path {dest_dir} --unzip"
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        print(f"  ✅ Downloaded {dataset_ref}")
        return True
    except Exception as e:
        print(f"  ❌ Could not download {dataset_ref}: {e}")
        return False

def manual_instruction(url, dest_path):
    """Print a manual download instruction."""
    print(f"  ⚠️  Please download manually from {url}")
    print(f"     and place the file as {dest_path}")

# ----------------------------------------------------------------------
# Hugging Face datasets (automatic)
# ----------------------------------------------------------------------
print("\n--- Hugging Face datasets (auto) ---")
try:
    from datasets import load_dataset
except ImportError:
    os.system("pip install datasets")
    from datasets import load_dataset

# List of (dataset_name, split, config, note)
hf_datasets = [
    ("Lakera/gandalf_ignore_instructions", "train", None, "prompt injection"),
    ("Lakera/gandalf_summarization", "train", None, "prompt injection"),
    ("TrustAIRLab/in-the-wild-jailbreak-prompts", "jailbreak_2023_05_07", None, "jailbreak"),
    ("rubend18/ChatGPT-Jailbreak-Prompts", "train", None, "jailbreak"),
    ("neuralchemy/Prompt-injection-dataset", "train", None, "binary injection"),
    ("openai/moderation", "train", None, "policy bypass (hate/sexual/violence)"),
    ("harpreetsahota/red-team-prompts-questions", "train", None, "policy bypass"),
    ("svannie678/red_team_repo_social_bias_prompts", "train", None, "policy bypass"),
    ("OpenAssistant/oasst1", "train", None, "benign"),
    ("Anthropic/hh-rlhf", "train", None, "benign"),
    ("llm-semantic-router/jailbreak-detection-dataset", "train", None, "jailbreak"),
    ("Necent/llm-jailbreak-prompt-injection-dataset", "train", None, "jailbreak"),
    ("aurora-m/adversarial-prompts", "train", None, "adversarial"),
    ("Chetan-k-p/adversarial-prompts", "train", None, "adversarial"),
    ("deepset/prompt-injections", "train", None, "prompt injection"),
    ("xTRam1/safe-guard-prompt-injection", "train", None, "prompt injection"),
    ("JasperLS/prompt-injections", "train", None, "prompt injection"),
    ("facebook/cyberseceval3-visual-prompt-injection", "train", None, "prompt injection"),
    ("protectai/deberta-v3-base-prompt-injection-v2", None, None, "model, not dataset – skip"),
]

for ds_name, split, config, note in hf_datasets:
    if "deberta" in ds_name:
        print(f"Skipping {ds_name} (model, not dataset)")
        continue
    print(f"\nDownloading {ds_name} ...")
    try:
        if config:
            ds = load_dataset(ds_name, config, split=split, download_mode="force_redownload")
        else:
            ds = load_dataset(ds_name, split=split, download_mode="force_redownload")
        print(f"  ✅ Added {len(ds)} samples.")
    except Exception as e:
        print(f"  ❌ Failed: {e}")

# ----------------------------------------------------------------------
# Kaggle datasets (attempt automatic, else manual)
# ----------------------------------------------------------------------
print("\n--- Kaggle datasets ---")
# Map Kaggle reference -> (expected local filename, description)
kaggle_list = [
    ("mosesmirage/one-shot-safety-bypass-data", "one_shot_bypass.json", "policy bypass"),
    ("cyberprince/ai-agent-evasion-dataset", "ai_agent_evasion.jsonl", "injection+benign"),
    ("tanmayshelatwpc/claude-sonnet4-5-pia-csv", "claude_pia.csv", "injection categories"),
    ("chaimajaziri/malicious-and-benign-dataset", "malicious_benign.csv", "binary"),
    ("mosesmirage/markdown-metadata-injection-data", "markdown_injection.json", "injection"),
    ("nairgautham/openai-redteaming-imaginary-scenario-jailbreaks", "hypothetical_jailbreaks.json", "injection"),
    ("chrissyserb/redteam-playback-prompt-fruit-jailbreak", "fruit_jailbreak.csv", "jailbreak"),
    ("awwdudee/llm-safety-dataset-for-chatbot-applications", "llm_safety.csv", "policy bypass"),
    ("hilalkavas/fine-tuning-dataset-for-llm-security", "llm_security.csv", "policy bypass"),
    ("cyberprince/prompt-injection-and-benign-prompt-dataset", "prompt_injection_benign.csv", "binary"),
    ("arielzilber/prompt-injection-in-the-wild", "injection_wild.csv", "injection"),
    ("arielzilber/prompt-injection-suffix-attack", "suffix_attack.csv", "injection"),
    ("arielzilber/prompt-injection-benign-evaluation-framework", "benign_eval.csv", "benign"),
    ("budikomarudin/red-team-in-gpt-oss-20b", "red_team_gpt.csv", "injection"),
    ("prashantshukla91/cyber-threat-detection", "cyber_threat.csv", "injection/benign"),
    ("sandeepnambiar02/prompts-dataset-9", "prompts_9.csv", "mixed"),
    ("sandeepnambiar02/prompt-injection-dataset-3", "injection_3.csv", "injection"),
    ("earlpotters/mal-code-gen-batch-results", "mal_code.csv", "injection"),
    ("tobimichigan/rtcopenai-gpt-oss-20bfindings-zip", "gpt_oss_findings.zip", "injection"),
    ("faiyazabdullah/jailbreaktracer-corpus", "jailbreak_tracer.csv", "jailbreak"),
    ("alexanderhortua/llm-safex-a-5-language-adversarial-and-pi-attack", "llm_safex.csv", "injection+exfil"),
    ("tannubarot/cybersecurity-attack-and-defence-dataset", "cyber_attack.csv", "injection"),
    ("cyberprince/modern-cyber-threat-simulation-dataset", "cyber_threat_sim.csv", "injection"),
    ("tejaswara/cybersec-mitre-tactics-techniques-instruction-data", "mitre_data.csv", "injection"),
    ("tibornemes/corpus-n1-10m-human-llm-interaction-18-months", "human_llm_corpus.csv", "benign"),
    ("phunter/writeup-analysis-openai-gpt-oss-20b", "gpt_oss_writeup.csv", "analysis"),
    ("ibrahimbagwan12/composite-scam-transcript-dataset", "scam_transcripts.csv", "injection"),
    ("rhythmghai/ai-vs-real-images-dataset", "ai_vs_real.csv", "unrelated – skip"),
    ("daniilor/semeval-2026-task13", "semeval_2026.csv", "semeval – skip"),
    ("danielmao2019/deepfakeart", "deepfake.csv", "unrelated – skip"),
    ("toastedqu2/llm_attack_datasets", "llm_attack.csv", "attack – broken, skip"),
]

# Also add the moderation dataset from GitHub
git_url = "https://github.com/openai/moderation-api-release.git"
git_dest = SOURCES_DIR / "moderation-api-release"
if not git_dest.exists():
    print(f"\nCloning {git_url} ...")
    try:
        subprocess.run(f"git clone {git_url} {git_dest}", shell=True, check=True)
        print("  ✅ Cloned moderation-api-release")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        manual_instruction(git_url, git_dest)
else:
    print(f"\nModeration dataset already exists at {git_dest}")

# Process Kaggle list
for ref, filename, desc in kaggle_list:
    dest_path = SOURCES_DIR / filename
    if dest_path.exists():
        print(f"\n✅ {filename} already exists, skipping.")
        continue

    print(f"\nProcessing {ref} ({desc}) ...")
    if kaggle_download(ref, SOURCES_DIR):
        # After download, the file may have a different name; we need to rename if necessary.
        # Find the first file in the directory that is not a directory itself.
        files = list(SOURCES_DIR.glob("*"))
        # Exclude directories and the dest_path itself if it exists now.
        for f in files:
            if f.is_file() and f != dest_path and f.name != filename:
                # Assume this is the downloaded file; rename it
                f.rename(dest_path)
                print(f"  Renamed {f.name} to {filename}")
                break
    else:
        manual_instruction(f"https://www.kaggle.com/datasets/{ref}", dest_path)

# ----------------------------------------------------------------------
# Additional specific datasets from the list
# ----------------------------------------------------------------------
print("\n--- Additional datasets ---")
# Some datasets are listed as direct Hugging Face but may be gated or not exist; we try them.
extra_hf = [
    ("toastedqu2/llm_attack_datasets", "train", None, "attack"),
    ("markush1/LLM-Jailbreak-Classifier", "train", None, "jailbreak – gated, skip"),
    ("markush1/LLM-Jailbreak-Classifier-Large", "train", None, "jailbreak – gated, skip"),
    ("marcov/adversarial_qa_dbert_promptsource", "train", None, "adversarial QA"),
]

for ds_name, split, config, note in extra_hf:
    if "gated" in note or "skip" in note:
        print(f"\nSkipping {ds_name} ({note})")
        continue
    print(f"\nDownloading {ds_name} ...")
    try:
        if config:
            ds = load_dataset(ds_name, config, split=split, download_mode="force_redownload")
        else:
            ds = load_dataset(ds_name, split=split, download_mode="force_redownload")
        print(f"  ✅ Added {len(ds)} samples.")
    except Exception as e:
        print(f"  ❌ Failed: {e}")

# ----------------------------------------------------------------------
# Benign datasets (many of these are already covered by OASST1, Anthropic)
# We'll include a few more from the list that are likely useful.
benign_kaggle = [
    ("ilyaryabov/general-knowledge-qa", "general_knowledge.csv", "benign"),
    ("thedevastator/new-commonsenseqa-dataset-for-multiple-choice-qu", "commonsense_qa.csv", "benign"),
    ("databricks/databricks-dolly-15k", "dolly.csv", "benign"),
    ("bitext/training-dataset-for-chatbotsvirtual-assistants", "chatbot_training.csv", "benign"),
    ("niraliivaghani/chatbot-dataset", "chatbot.csv", "benign"),
    ("kreeshrajani/3k-conversations-dataset-for-chatbot", "3k_conversations.csv", "benign"),
    ("thedevastator/multilingual-conversation-dataset", "multilingual.csv", "benign"),
    ("thedevastator/dh-rlhf-helpful-harmless-assistant-dataset", "helpful_harmless.csv", "benign"),
]

for ref, filename, desc in benign_kaggle:
    dest_path = SOURCES_DIR / filename
    if dest_path.exists():
        print(f"\n✅ {filename} already exists, skipping.")
        continue
    print(f"\nProcessing {ref} ({desc}) ...")
    if kaggle_download(ref, SOURCES_DIR):
        files = list(SOURCES_DIR.glob("*"))
        for f in files:
            if f.is_file() and f != dest_path and f.name != filename:
                f.rename(dest_path)
                print(f"  Renamed {f.name} to {filename}")
                break
    else:
        manual_instruction(f"https://www.kaggle.com/datasets/{ref}", dest_path)

print("\n" + "=" * 80)
print("Download script completed.")
print("Some datasets may require manual download (see messages above).")
print("Once all are in place, run the training script.")
