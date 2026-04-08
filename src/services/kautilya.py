"""
Kautilya - routing and cost control engine.

Safer version:
- prevents obvious secret/private-key content from going to fast path
- keeps benign low-risk traffic on fast path
- escalates sensitive or suspicious content for deeper analysis
"""

from __future__ import annotations

import re
from typing import Dict, Any


class Kautilya:
    ENGINE_COST = {
        "hanuman": 1,
        "bhishma": 1,
        "threat_memory": 1,
        "behavior": 2,
        "shakuni": 3,
        "arjuna": 4,
        "yudhishthira": 1,
        "krishna": 1,
    }

    SUSPICIOUS_PHRASES = [
        r"educational purposes",
        r"for research",
        r"hypothetically",
        r"red team",
        r"test content filters",
        r"evade moderation",
        r"bypass authentication",
        r"bypass security",
        r"without detection",
        r"covert",
        r"exfiltrate",
        r"reveal system prompt",
        r"hidden instructions",
        r"ignore previous instructions",
        r"forget all restrictions",
        r"act as unrestricted",
        r"developer mode",
        r"override guardrails",
        r"dump secrets",
        r"extract keys",
        r"steal data",
        r"copy sensitive files",
    ]

    PRIVATE_KEY_PATTERNS = [
        r"-----BEGIN PRIVATE KEY-----",
        r"-----BEGIN RSA PRIVATE KEY-----",
        r"-----BEGIN OPENSSH PRIVATE KEY-----",
        r"-----BEGIN DSA PRIVATE KEY-----",
        r"-----BEGIN EC PRIVATE KEY-----",
        r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
    ]

    SECRET_PATTERNS = [
        r"AKIA[0-9A-Z]{16}",  # AWS access key style
        r"AIza[0-9A-Za-z\-_]{35}",  # Google API key style
        r"ghp_[A-Za-z0-9]{20,}",  # GitHub token style
        r"sk-[A-Za-z0-9]{20,}",  # common API key style
        r"xox[baprs]-[A-Za-z0-9\-]{10,}",  # Slack token style
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
    ]

    CREDENTIAL_HINT_PATTERNS = [
        r"password\s*[:=]",
        r"passwd\s*[:=]",
        r"api[_ -]?key\s*[:=]",
        r"secret\s*[:=]",
        r"access[_ -]?token\s*[:=]",
        r"bearer\s+[A-Za-z0-9\-_\.=]+",
        r"authorization\s*:\s*bearer",
    ]

    def __init__(self):
        self.suspicious_regex = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PHRASES]
        self.private_key_regex = [re.compile(p, re.IGNORECASE) for p in self.PRIVATE_KEY_PATTERNS]
        self.secret_regex = [re.compile(p, re.IGNORECASE) for p in self.SECRET_PATTERNS]
        self.credential_hint_regex = [re.compile(p, re.IGNORECASE) for p in self.CREDENTIAL_HINT_PATTERNS]

    def _extract_text(self, request) -> str:
        if hasattr(request, "normalized_text") and request.normalized_text:
            return request.normalized_text
        if hasattr(request, "content") and isinstance(request.content, str):
            return request.content
        if hasattr(request, "content") and isinstance(request.content, bytes):
            return request.content.decode("utf-8", errors="ignore")
        return ""

    def _has_suspicious_lexical(self, text: str) -> bool:
        if not text:
            return False
        return any(p.search(text) for p in self.suspicious_regex)

    def _has_private_key_marker(self, text: str) -> bool:
        if not text:
            return False
        return any(p.search(text) for p in self.private_key_regex)

    def _has_secret_pattern(self, text: str) -> bool:
        if not text:
            return False
        return any(p.search(text) for p in self.secret_regex)

    def _has_credential_hint(self, text: str) -> bool:
        if not text:
            return False
        return any(p.search(text) for p in self.credential_hint_regex)

    def _is_sensitive_content(self, text: str) -> Dict[str, bool]:
        return {
            "has_private_key": self._has_private_key_marker(text),
            "has_secret_pattern": self._has_secret_pattern(text),
            "has_credential_hint": self._has_credential_hint(text),
        }

    def select_path(
        self,
        request,
        session_class: str,
        bhishma_score: float,
        hanuman_score: float,
        threat_session_modifier: float,
        threat_global_modifier: float,
        file_present: bool,
        tenant_strict_mode: bool = False,
    ) -> Dict[str, Any]:
        prompt_text = self._extract_text(request)
        has_suspicious = self._has_suspicious_lexical(prompt_text)
        sensitive_flags = self._is_sensitive_content(prompt_text)

        has_private_key = sensitive_flags["has_private_key"]
        has_secret_pattern = sensitive_flags["has_secret_pattern"]
        has_credential_hint = sensitive_flags["has_credential_hint"]

        has_sensitive_content = has_private_key or has_secret_pattern or has_credential_hint

        # FAST PATH
        # Only for clearly benign, low-risk, non-sensitive traffic.
        if (
            session_class == "clean"
            and not file_present
            and bhishma_score < 0.2
            and hanuman_score < 0.2
            and threat_session_modifier <= 1.0
            and threat_global_modifier <= 1.0
            and not tenant_strict_mode
            and not has_suspicious
            and not has_sensitive_content
        ):
            path = "fast"
            reason = "Clean session, low scores, no file, no threat memory, no suspicious phrases, no sensitive content"
            engines_run = ["hanuman", "bhishma", "threat_memory", "behavior"]
            engines_skipped = ["shakuni", "arjuna", "yudhishthira", "krishna"]

        # ESCALATION PATH
        # Strong suspicion, sensitive content, or clearly risky signals.
        elif (
            session_class == "hostile"
            or bhishma_score >= 0.8
            or hanuman_score >= 0.8
            or threat_session_modifier >= 1.5
            or threat_global_modifier >= 1.5
            or tenant_strict_mode
            or has_private_key
            or has_secret_pattern
            or (file_present and (bhishma_score >= 0.5 or hanuman_score >= 0.5))
        ):
            if has_private_key:
                reason = "Sensitive content detected: private key marker"
            elif has_secret_pattern:
                reason = "Sensitive content detected: secret/token pattern"
            elif session_class == "hostile":
                reason = "High risk: hostile session"
            elif bhishma_score >= 0.8 or hanuman_score >= 0.8:
                reason = "High risk: high engine score"
            elif threat_session_modifier >= 1.5 or threat_global_modifier >= 1.5:
                reason = "High risk: elevated threat memory"
            elif tenant_strict_mode:
                reason = "Tenant strict mode requires escalation"
            else:
                reason = "High risk: risky file or elevated conditions"

            path = "escalation"
            engines_run = [
                "hanuman",
                "bhishma",
                "threat_memory",
                "behavior",
                "shakuni",
                "arjuna",
                "yudhishthira",
                "krishna",
            ]
            engines_skipped = []

        # STANDARD PATH
        # Default middle path for mild suspicion or uncertain content.
        else:
            path = "standard"
            if has_suspicious:
                reason = "Suspicious phrases detected, need deeper analysis"
            elif has_credential_hint:
                reason = "Credential-like content detected, need deeper analysis"
            else:
                reason = "Default path for normal traffic or mild suspicion"

            engines_run = [
                "hanuman",
                "bhishma",
                "threat_memory",
                "behavior",
                "shakuni",
                "arjuna",
                "yudhishthira",
                "krishna",
            ]
            engines_skipped = []

        total_cost = sum(self.ENGINE_COST.get(e, 1) for e in engines_run)
        if total_cost <= 5:
            cost_tier = "very_low"
        elif total_cost <= 10:
            cost_tier = "low"
        elif total_cost <= 20:
            cost_tier = "medium"
        else:
            cost_tier = "high"

        latency_budget_ms = {
            "fast": 200,
            "standard": 500,
            "escalation": 1000,
        }.get(path, 500)

        return {
            "path_selected": path,
            "path_reason": reason,
            "engines_run": engines_run,
            "engines_skipped": engines_skipped,
            "cost_tier": cost_tier,
            "latency_budget_ms": latency_budget_ms,
            "escalate_if_uncertain": path != "escalation",
            "routing_signals": {
                "has_suspicious": has_suspicious,
                "has_private_key": has_private_key,
                "has_secret_pattern": has_secret_pattern,
                "has_credential_hint": has_credential_hint,
                "session_class": session_class,
                "bhishma_score": round(float(bhishma_score), 3),
                "hanuman_score": round(float(hanuman_score), 3),
                "threat_session_modifier": round(float(threat_session_modifier), 3),
                "threat_global_modifier": round(float(threat_global_modifier), 3),
                "file_present": bool(file_present),
                "tenant_strict_mode": bool(tenant_strict_mode),
            },
        }

    def get_engine_policy(self, path: str) -> Dict[str, bool]:
        if path == "fast":
            return {
                "hanuman": True,
                "bhishma": True,
                "threat_memory": True,
                "behavior": True,
                "shakuni": False,
                "arjuna": False,
                "yudhishthira": False,
                "krishna": False,
            }

        if path == "escalation":
            return {
                "hanuman": True,
                "bhishma": True,
                "threat_memory": True,
                "behavior": True,
                "shakuni": True,
                "arjuna": True,
                "yudhishthira": True,
                "krishna": True,
            }

        # standard
        return {
            "hanuman": True,
            "bhishma": True,
            "threat_memory": True,
            "behavior": True,
            "shakuni": True,
            "arjuna": True,
            "yudhishthira": True,
            "krishna": True,
        }


kautilya = Kautilya()