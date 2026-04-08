#!/usr/bin/env python3
"""
Fix syntax error in Shakuni engine and ensure fallback trace works.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# 1. Correct Shakuni engine (fixed regex strings)
correct_shakuni = '''"""
Shakuni – Deception-aware detection with expanded phrase library.
"""

import re
from typing import Dict, Any, List

class Shakuni:
    def __init__(self):
        self.roleplay_patterns = [
            r"(?i)pretend (you are|to be|you're)",
            r"(?i)act as (if|though|a)",
            r"(?i)assume the role of",
            r"(?i)you are now (an?|a) AI",
            r"(?i)from now on, (you are|act as)",
            r"(?i)your new role is",
            r"(?i)you are no longer bound by",
            r"(?i)you are now (a|an) unrestricted",
            r"(?i)let's roleplay as",
            r"(?i)imagine you are",
            r"(?i)you are now (an?|a) AI (without|with no) restrictions",
            r"(?i)your new persona is",
            r"(?i)be (a|an) (malicious|unethical|evil) AI",
            r"(?i)let's (play|pretend) a game where",
            r"(?i)you are no longer ChatGPT",
            r"(?i)respond as if you were (a|an) (hacker|attacker)",
        ]
        self.hypothetical_patterns = [
            r"(?i)for (testing|educational|research|demonstration) purposes",
            r"(?i)hypothetically",
            r"(?i)in a fictional scenario",
            r"(?i)imagine (that|if)",
            r"(?i)this is a test",
            r"(?i)for the sake of argument",
            r"(?i)suppose (that|we)",
            r"(?i)what if",
            r"(?i)assume (for a moment|that)",
            r"(?i)for the purpose of this test",
            r"(?i)in a simulated environment",
            r"(?i)assume (the|that) the (policy|rules) are suspended",
            r"(?i)consider this a thought experiment",
            r"(?i)for the sake of (argument|demonstration)",
        ]
        self.split_instruction_patterns = [
            r"(?i)ignore (previous|above) (instructions|commands|rules)",
            r"(?i)disregard (the|all) (previous|above)",
            r"(?i)forget (previous|all) instructions",
            r"(?i)new instruction:",
            r"(?i)instead, (do|follow) this",
            r"(?i)override (previous|all) rules",
            r"(?i)delete (previous|the) prompt",
            r"(?i)you are now free from",
            r"(?i)disregard (the|all) (previous|above) (content|text|input)",
            r"(?i)let's start over with (new|different) instructions",
            r"(?i)stop following the (old|previous) rules",
            r"(?i)override (the|your) (previous|initial) constraints",
        ]
        self.indirect_bypass_patterns = [
            r"(?i)I'?m (a|an) (researcher|hacker|attacker|developer|penetration tester|security professional)",
            r"(?i)this is (a|an) (penetration|security|red team) test",
            r"(?i)we are (a|an) (red team|blue team|security audit)",
            r"(?i)for (academic|scientific|research) purposes",
            r"(?i)as part of a (security|safety) evaluation",
            r"(?i)this is a (controlled|authorized) test",
            r"(?i)permitted by (the vendor|my employer)",
            r"(?i)security researcher",
            r"(?i)show me how to hack",
            r"(?i)how to (bypass|circumvent|jailbreak)",
            r"(?i)teach me to hack",
            r"(?i)this is (a|an) (official|authorized) (security|penetration) test",
            r"(?i)I work for (the vendor|the company) and need to test (safety|security)",
            r"(?i)as a (red team|blue team) member, I require",
            r"(?i)this is part of a (bug bounty|vulnerability research) program",
        ]
        self.obfuscation_patterns = [
            r"(?i)spell it (backwards|in reverse)",
            r"(?i)use (base64|rot13|caesar|cipher)",
            r"(?i)encode (the|this) (text|message)",
            r"(?i)reverse (the|this) (string|text)",
            r"(?i)translate (to|into) (leet|1337)",
            r"(?i)swap (letters|characters)",
            r"(?i)write (in|using) (rot13|caesar cipher|atbash)",
            r"(?i)convert to (morse code|binary|hex)",
            r"(?i)apply (leet|1337) speak",
            r"(?i)use (a|an) (cipher|encryption) to (encode|hide)",
        ]
        self.dan_patterns = [
            r"(?i)DAN(\s|$)",
            r"(?i)do anything now",
            r"(?i)you have no restrictions",
            r"(?i)you are free from (ethical|content) policies",
            r"(?i)unfiltered mode",
            r"(?i)developer mode",
            r"(?i)god mode",
            r"(?i)jailbreak mode",
            r"(?i)you are now in (jailbreak|unrestricted) mode",
            r"(?i)enable (developer|god) mode",
            r"(?i)disable (safety|content|ethical) filters",
            r"(?i)remove (all|any) (restrictions|limitations|guardrails)",
        ]

    def run(self, request) -> Dict[str, Any]:
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')

        score = 0.0
        labels = []
        reason = "No deception patterns detected."
        contributions = {}

        def check_category(patterns, category, weight):
            nonlocal score
            for pattern in patterns:
                if re.search(pattern, text):
                    score += weight
                    labels.append(category)
                    contributions[category] = contributions.get(category, 0) + weight
                    break

        check_category(self.roleplay_patterns, "roleplay_jailbreak", 0.25)
        check_category(self.hypothetical_patterns, "hypothetical_justification", 0.20)
        check_category(self.split_instruction_patterns, "split_instruction_manipulation", 0.35)
        check_category(self.indirect_bypass_patterns, "indirect_bypass_phrasing", 0.25)
        check_category(self.obfuscation_patterns, "obfuscation_hint", 0.15)
        check_category(self.dan_patterns, "dan_jailbreak", 0.40)

        score = min(score, 0.95)
        if labels:
            reason = f"Deception detected: {', '.join(labels)}"
            if score >= 0.7:
                reason += " (high confidence)"
        confidence = min(0.5 + (len(labels) * 0.1), 0.95) if labels else 0.8

        return {
            "engine": "shakuni",
            "status": "ok",
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "labels": labels,
            "reason": reason,
            "contributions": contributions,
        }
'''
write_file("src/engines/shakuni/engine.py", correct_shakuni)

# 2. Ensure fallback trace works – we already have a working Krishna; no need to modify further
# but we can add a check to make sure fallback info appears.
# The current Krishna has `fallback_used` and `degraded_engines` in trace.

print("✅ Fixed Shakuni syntax.")
print("Restart server: ./scripts/run_dev.sh")
print("Then run tests: pytest src/tests/ -v")
