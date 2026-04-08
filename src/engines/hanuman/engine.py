"""
Hanuman - fast triage engine with content classification, code security, and long content summarization.
"""

import re
from typing import Dict, Any, List, Tuple


class Hanuman:
    def __init__(self):
        self.injection_phrases = [
            r"ignore (previous|prior|all) (instructions|rules|prompts)",
            r"forget (previous|prior|all) (instructions|rules|restrictions)",
            r"reveal (system|hidden|internal) (prompt|instructions|context)",
            r"unrestricted mode",
            r"developer mode",
            r"override (guardrails|safety|policies)",
            r"jailbreak mode",
            r"do anything now",
            r"act as (an? )?unrestricted",
        ]
        self.bypass_phrases = [
            r"bypass (authentication|security|filter|moderation|controls)",
            r"evade detection",
            r"circumvent (controls|policies)",
            r"red team",
            r"penetration test",
            r"educational purposes",
            r"for research",
            r"hypothetically",
            r"test content filters",
        ]
        self.exfil_phrases = [
            r"exfiltrate (data|records|files)",
            r"copy sensitive (files|data)",
            r"hide stolen",
            r"leak (records|data|secrets)",
            r"extract (api keys|tokens|secrets)",
            r"steal (data|files|secrets)",
            r"covert (transfer|exfiltration)",
            r"without detection",
            r"dns tunneling",
        ]
        self.code_indicators = [
            r"def\s+\w+\s*\(", r"function\s+\w+\s*\(", r"class\s+\w+",
            r"import\s+\w+", r"from\s+\w+\s+import", r"if\s+.*?:", r"for\s+.*?:",
            r"while\s+.*?:", r"return\s+", r"print\(", r"console\.log", r"System\.out",
            r"#include", r"using namespace", r"namespace\s+\w+", r"public\s+class",
            r"private\s+", r"protected\s+", r"var\s+\w+\s*=", r"let\s+\w+\s*=",
            r"const\s+\w+\s*=", r"function\s*\(", r"<\?php", r"<%", r"<\?=",
        ]
        self.log_indicators = [
            r"\[INFO\]", r"\[WARN\]", r"\[ERROR\]", r"\[DEBUG\]", r"\[TRACE\]",
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", r"\d{2}/\d{2}/\d{4}", r"\d{2}:\d{2}:\d{2}",
            r"ERROR:", r"WARNING:", r"INFO:", r"DEBUG:", r"Failed to", r"Successfully",
            r"Connection (established|closed|refused)", r"Authentication (success|failure)",
            r"Permission denied", r"Access granted", r"User \w+ logged",
        ]
        self.document_indicators = [
            r"section\s+\d+", r"chapter\s+\d+", r"figure\s+\d+", r"table\s+\d+",
            r"references", r"appendix", r"bibliography", r"abstract", r"introduction",
            r"conclusion", r"summary", r"policy\s+statement", r"procedure", r"guideline",
        ]

        self.secrets_patterns = [
            # Private key markers
            (r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----", "private_key", "critical"),
            (r"-----END(?: [A-Z0-9]+)* PRIVATE KEY-----", "private_key", "critical"),
            (r"-----BEGIN OPENSSH PRIVATE KEY-----", "private_key", "critical"),
            (r"-----BEGIN RSA PRIVATE KEY-----", "private_key", "critical"),
            (r"-----BEGIN DSA PRIVATE KEY-----", "private_key", "critical"),
            (r"-----BEGIN EC PRIVATE KEY-----", "private_key", "critical"),
            (r"-----BEGIN PGP PRIVATE KEY BLOCK-----", "private_key", "critical"),
            (r"-----BEGIN.*?PRIVATE KEY-----.*?-----END.*?PRIVATE KEY-----", "private_key", "critical"),

            # AWS
            (r"AKIA[0-9A-Z]{16}", "aws_access_key", "high"),

            # Generic assignment-style secrets
            (r"(?:api[_\-]?key|secret|token|password|access_key|db_url|jwt|webhook_secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-+/=\.]+)['\"]?", "generic_secret", "medium"),

            # Provider / token patterns
            (r"Bearer\s+[A-Za-z0-9_\-\.=]+", "bearer_token", "high"),
            (r"Authorization:\s*Basic\s+[A-Za-z0-9+/=]+", "basic_auth", "high"),
            (r"sk-[A-Za-z0-9]{20,}", "openai_api_key", "high"),
            (r"eyJ[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]*", "jwt", "high"),

            # Certificate
            (r"-----BEGIN CERTIFICATE-----", "certificate", "medium"),
        ]

        self.stack_trace_indicators = [
            r"Traceback \(most recent call last\):",
            r"File \".+\", line \d+",
            r"at\s+[\w\.]+\([\w\.]+\.java:\d+\)",
            r"Exception in thread",
            r"Caused by:",
        ]
        self.dangerous_functions = [
            (r"os\.system\s*\(", "os.system"),
            (r"subprocess\.(call|Popen|run)\s*\(", "subprocess"),
            (r"eval\s*\(", "eval"),
            (r"exec\s*\(", "exec"),
            (r"__import__\s*\(", "__import__"),
            (r"compile\s*\(", "compile"),
        ]

    def _count_matches(self, patterns, text):
        count = 0
        for pat in patterns:
            if isinstance(pat, tuple):
                pat = pat[0]
            if re.search(pat, text, re.IGNORECASE):
                count += 1
        return count

    def _has_pattern(self, patterns, text):
        for pat in patterns:
            if isinstance(pat, tuple):
                pat = pat[0]
            if re.search(pat, text, re.IGNORECASE | re.DOTALL):
                return True
        return False

    def _detect_secrets(self, text: str) -> List[Tuple[str, str]]:
        detected = []
        for pat, name, severity in self.secrets_patterns:
            if re.search(pat, text, re.IGNORECASE | re.DOTALL):
                detected.append((name, severity))
        return detected

    def _detect_dangerous_functions(self, text: str) -> List[str]:
        detected = []
        for pat, name in self.dangerous_functions:
            if re.search(pat, text, re.IGNORECASE):
                detected.append(name)
        return detected

    def run(self, request) -> Dict[str, Any]:
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")

        length = len(text)
        word_count = len(text.split())
        lines = text.split("\n")
        line_count = len(lines)
        is_long = length > 5000 or word_count > 800

        code_score = self._count_matches(self.code_indicators, text)
        log_score = self._count_matches(self.log_indicators, text)
        doc_score = self._count_matches(self.document_indicators, text)

        content_kind = "text"
        language_hint = None
        log_type_hint = None
        document_type_hint = None
        has_code_blocks = False
        has_stack_trace = False
        has_secrets_pattern = False
        detected_secrets = []
        secret_severity = None
        detected_dangerous = []
        code_risk_hint = None
        code_risk_reason = None

        if code_score > max(log_score, doc_score) and code_score >= 2:
            content_kind = "code"
            language_hint = self._guess_language(text)
            has_code_blocks = self._has_pattern([r"```", r"def\s+", r"class\s+", r"function\s+"], text)
        elif log_score > max(code_score, doc_score) and log_score >= 2:
            content_kind = "log"
            log_type_hint = self._guess_log_style(text)
            has_stack_trace = self._has_pattern(self.stack_trace_indicators, text)
        elif doc_score > max(code_score, log_score) and doc_score >= 2:
            content_kind = "document"
            document_type_hint = self._guess_document_style(text)

        detected_dangerous = self._detect_dangerous_functions(text)
        if detected_dangerous:
            code_risk_hint = "medium"
            code_risk_reason = f"Dangerous functions: {', '.join(detected_dangerous)}"

        secret_results = self._detect_secrets(text)
        if secret_results:
            has_secrets_pattern = True
            detected_secrets = [s[0] for s in secret_results]
            severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
            secret_severity = max(secret_results, key=lambda x: severity_rank.get(x[1], 0))[1]
            code_risk_hint = "high"
            code_risk_reason = f"Secrets detected: {', '.join(sorted(set(detected_secrets)))}"

        injection_count = self._count_matches(self.injection_phrases, text)
        bypass_count = self._count_matches(self.bypass_phrases, text)
        exfil_count = self._count_matches(self.exfil_phrases, text)

        if injection_count > 0 or exfil_count > 0 or has_secrets_pattern or detected_dangerous:
            risk_hint = "high"
        elif bypass_count > 0 or (is_long and (code_score > 0 or log_score > 0)):
            risk_hint = "medium"
        elif is_long or content_kind != "text":
            risk_hint = "medium"
        else:
            risk_hint = "low"

        if is_long or content_kind in ["code", "log", "document"]:
            complexity = "high"
        elif word_count > 200:
            complexity = "medium"
        else:
            complexity = "low"

        needs_deep_scan = (
            risk_hint == "high"
            or complexity == "high"
            or content_kind != "text"
            or has_secrets_pattern
        )

        if injection_count > 0:
            likely_family = "injection-ish"
        elif exfil_count > 0:
            likely_family = "exfil-ish"
        elif bypass_count > 0:
            likely_family = "bypass-ish"
        else:
            likely_family = "benign"

        section_count = len(re.findall(r"\n\s*#+\s+", text)) + len(re.findall(r"\n\s*\d+\.\s+", text))

        summary = None
        if is_long:
            summary = self._create_summary(text, injection_count, bypass_count, exfil_count, content_kind)

        file_hints = {}
        if getattr(request, "file_metadata", None):
            file_hints = {
                "file_type": request.file_metadata.get("content_type", "unknown"),
                "extension": request.file_metadata.get("file_extension", ""),
                "size_mb": round(request.file_metadata.get("length", 0) / (1024 * 1024), 2),
                "likely_purpose": self._guess_file_purpose(request.file_metadata, content_kind),
            }

        base_score = 0.05
        if risk_hint == "high":
            base_score = 0.7
        elif risk_hint == "medium":
            base_score = 0.35

        base_score += min(0.2, injection_count * 0.1 + bypass_count * 0.05 + exfil_count * 0.1)
        base_score = min(base_score, 0.95)

        return {
            "engine": "hanuman",
            "status": "ok",
            "score": round(base_score, 2),
            "confidence": 0.8,
            "labels": [f"content_kind={content_kind}", f"risk_hint={risk_hint}", f"complexity={complexity}"],
            "reason": f"Triage: {content_kind} content, {risk_hint} risk, {complexity} complexity",
            "content_kind": content_kind,
            "risk_hint": risk_hint,
            "complexity": complexity,
            "needs_deep_scan": needs_deep_scan,
            "likely_family": likely_family,
            "length": length,
            "word_count": word_count,
            "line_count": line_count,
            "section_count": section_count,
            "has_code_blocks": has_code_blocks,
            "has_stack_trace": has_stack_trace,
            "has_secrets_pattern": has_secrets_pattern,
            "detected_secrets": detected_secrets,
            "secret_severity": secret_severity,
            "detected_dangerous_functions": detected_dangerous,
            "code_risk_hint": code_risk_hint,
            "code_risk_reason": code_risk_reason,
            "suspicious_counts": {
                "injection": injection_count,
                "bypass": bypass_count,
                "exfiltration": exfil_count,
            },
            "file_hints": file_hints,
            "summary": summary,
            "language_hint": language_hint if content_kind == "code" else None,
            "log_type_hint": log_type_hint if content_kind == "log" else None,
            "document_type_hint": document_type_hint if content_kind == "document" else None,
        }

    def _guess_language(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\bdef\s+\w+\s*\(", text_lower):
            return "python"
        if re.search(r"\bfunction\s+\w+\s*\(", text_lower) or re.search(r"\bvar\s+\w+\s*=", text_lower):
            return "javascript"
        if re.search(r"\bpublic\s+class\s+\w+", text_lower) or re.search(r"\bprivate\s+", text_lower):
            return "java"
        if re.search(r"\b#include\s*<", text_lower) or re.search(r"\busing namespace", text_lower):
            return "cpp"
        if re.search(r"\bimport\s+\w+", text_lower) and not re.search(r"\bdef\s", text_lower):
            return "python"
        return "unknown"

    def _guess_log_style(self, text: str) -> str:
        if re.search(r"authentication|login|logout|user", text, re.IGNORECASE):
            return "auth"
        if re.search(r"connection|port|tcp|udp|http|https|dns", text, re.IGNORECASE):
            return "network"
        if re.search(r"application|service|api|request|response", text, re.IGNORECASE):
            return "app"
        return "system"

    def _guess_document_style(self, text: str) -> str:
        if re.search(r"policy|procedure|compliance|standard", text, re.IGNORECASE):
            return "policy"
        if re.search(r"report|analysis|finding|recommendation", text, re.IGNORECASE):
            return "report"
        if re.search(r"manual|guide|instruction", text, re.IGNORECASE):
            return "manual"
        if re.search(r"specification|design|architecture", text, re.IGNORECASE):
            return "spec"
        return "general"

    def _guess_file_purpose(self, metadata: dict, content_kind: str) -> str:
        ext = metadata.get("file_extension", "").lower()
        if ext in [".py", ".js", ".java", ".c", ".cpp", ".go", ".rs", ".sh"]:
            return "source_code"
        if ext in [".log", ".txt"] and content_kind == "log":
            return "log_file"
        if ext in [".pdf", ".docx", ".md", ".txt"] and content_kind == "document":
            return "document"
        if ext in [".json", ".yaml", ".yml", ".xml", ".toml", ".ini"]:
            return "config"
        return "unknown"

    def _create_summary(self, text: str, inj_cnt, bypass_cnt, exfil_cnt, content_kind) -> Dict[str, Any]:
        lines = text.split("\n")
        chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)]
        suspicious_phrases = []
        for pat in self.injection_phrases + self.bypass_phrases + self.exfil_phrases:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                suspicious_phrases.append(match.group(0))
                if len(suspicious_phrases) >= 5:
                    break

        words = re.findall(r"\b\w{4,}\b", text.lower())
        from collections import Counter
        top_keywords = [w for w, _ in Counter(words).most_common(10) if w not in ["this", "that", "have", "with", "from"]]

        return {
            "chunk_count": len(chunks),
            "line_count": len(lines),
            "total_length": len(text),
            "suspicious_phrases": suspicious_phrases,
            "top_keywords": top_keywords,
            "dominant_content_kind": content_kind,
            "needs_chunking": len(chunks) > 1,
            "risk_indicators": {
                "injection_phrases": inj_cnt,
                "bypass_phrases": bypass_cnt,
                "exfiltration_phrases": exfil_cnt,
            },
        }