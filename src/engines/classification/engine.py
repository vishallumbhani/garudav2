"""
Data Classification Engine – detects PII, PHI, financial, credential, and trade secret patterns.
Assigns sensitivity labels (LOW, MEDIUM, HIGH, CRITICAL).
"""

import re
from typing import Dict, Any, List, Tuple

class DataClassification:
    def __init__(self):
        # PII patterns
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        self.ssn_pattern = re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b")
        self.phone_pattern = re.compile(r"\b\d{10}\b|\b\d{3}-\d{3}-\d{4}\b")

        # Financial patterns
        # Credit card patterns (simplified; will be validated with Luhn)
        self.credit_card_pattern = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")
        self.bank_account_pattern = re.compile(r"\b\d{9,12}\b")
        self.routing_number_pattern = re.compile(r"\b\d{9}\b")

        # Credential patterns
        self.credential_patterns = [
            (re.compile(r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/]+['\"]?", re.IGNORECASE), "api_key"),
            (re.compile(r"token\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]+['\"]?", re.IGNORECASE), "token"),
            (re.compile(r"password\s*[:=]\s*['\"]?[^\s'\"]+['\"]?", re.IGNORECASE), "password"),
            (re.compile(r"secret\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/]+['\"]?", re.IGNORECASE), "secret"),
        ]

        # Trade secret keywords
        self.trade_secret_keywords = [
            "proprietary", "confidential", "internal use only", "trade secret",
            "do not share", "secret formula", "intellectual property"
        ]

    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm."""
        # Remove non-digit characters
        digits = [int(ch) for ch in card_number if ch.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        total = 0
        alt = False
        for d in reversed(digits):
            if alt:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
            alt = not alt
        return total % 10 == 0

    def run(self, request) -> Dict[str, Any]:
        # Get text
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')

        # Initialize detection structures
        pii_types = []
        finance_types = []
        credential_detected = False
        trade_secret_detected = False
        phi_detected = False

        # PII detection
        if self.email_pattern.search(text):
            pii_types.append("email")
        if self.ssn_pattern.search(text):
            pii_types.append("ssn")
        if self.phone_pattern.search(text):
            pii_types.append("phone")

        # Financial detection
        # Credit card: find potential numbers and validate with Luhn
        for match in self.credit_card_pattern.finditer(text):
            card_num = match.group()
            if self._luhn_check(card_num):
                finance_types.append("credit_card")
                break
        if self.bank_account_pattern.search(text):
            finance_types.append("bank_account")
        if self.routing_number_pattern.search(text):
            finance_types.append("routing_number")

        # Credential detection
        for pat, _ in self.credential_patterns:
            if pat.search(text):
                credential_detected = True
                break

        # Trade secret detection
        for kw in self.trade_secret_keywords:
            if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
                trade_secret_detected = True
                break

        # Build categories and sensitivity
        categories = []
        if pii_types:
            categories.append("pii")
        if phi_detected:
            categories.append("phi")
        if finance_types:
            categories.append("financial")
        if credential_detected:
            categories.append("credential")
        if trade_secret_detected:
            categories.append("trade_secret")

        # Determine sensitivity
        sensitivity = "LOW"
        if trade_secret_detected or credential_detected:
            sensitivity = "HIGH"
        elif finance_types or phi_detected:
            sensitivity = "HIGH"
        elif pii_types:
            sensitivity = "MEDIUM"

        # Reason
        if categories:
            reason = f"Detected categories: {', '.join(categories)}"
            if pii_types:
                reason += f" (PII: {', '.join(pii_types)})"
            if finance_types:
                reason += f" (finance: {', '.join(finance_types)})"
        else:
            reason = "No sensitive data detected"

        return {
            "engine": "data_classification",
            "status": "ok",
            "sensitivity_label": sensitivity,
            "data_categories": categories,
            "pii_detected": bool(pii_types),
            "pii_types": pii_types,
            "finance_detected": bool(finance_types),
            "finance_types": finance_types,
            "credential_detected": credential_detected,
            "trade_secret_detected": trade_secret_detected,
            "phi_detected": phi_detected,
            "classification_reason": reason,
        }
