import json
import redis
import re
from typing import Dict, Any, List, Optional, Tuple
from src.core.config import settings
from src.engines.classification.engine import DataClassification

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class RAGProtection:
    def __init__(self):
        self.classifier = DataClassification()
        # Role policies: max_sensitivity, allowed categories, tenant scope, etc.
        self.policies = {
            "admin": {"max_sensitivity": "RESTRICTED", "allow_categories": []},
            "analyst": {"max_sensitivity": "HIGH", "allow_categories": []},
            "viewer": {"max_sensitivity": "MEDIUM", "allow_categories": []},
            "customer": {"max_sensitivity": "LOW", "allow_categories": ["pii"]},
            "tenant_admin": {"max_sensitivity": "HIGH", "tenant_scope": True},
            "service_account": {"max_sensitivity": "MEDIUM", "allow_categories": ["code"]},
            "support": {"max_sensitivity": "MEDIUM", "allow_categories": ["pii"]},
        }
        self.sensitivity_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "RESTRICTED": 3}
        # Leakage patterns for output scan (fixed regex)
        self.leakage_patterns = [
            (r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/]+['\"]?", "api_key"),
            (r"(?i)API key is\s+[A-Za-z0-9_\-]+", "api_key"),
            (r"token\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]+['\"]?", "token"),
            (r"password\s*[:=]\s*['\"]?[^\s'\"]+['\"]?", "password"),
            (r"secret\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/]+['\"]?", "secret"),
            (r"-----BEGIN .* PRIVATE KEY-----", "private_key"),
            (r"sk-[A-Za-z0-9]{32,}", "openai_key"),
            (r"AKIA[0-9A-Z]{16}", "aws_key"),
            (r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b", "ssn"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
            (r"\b(?:\d{4}[- ]?){3}\d{4}\b", "credit_card"),
        ]

    # ------------------------------------------------------------------
    # Document classification
    # ------------------------------------------------------------------
    def classify_document(self, text: str) -> Dict[str, Any]:
        """Classify document and return metadata."""
        request = type('Request', (), {'normalized_text': text})()
        result = self.classifier.run(request)
        doc_type = "general_doc"
        if "code" in result.get("data_categories", []):
            doc_type = "code"
        elif "financial" in result.get("data_categories", []):
            doc_type = "report"
        elif "credential" in result.get("data_categories", []):
            doc_type = "secret"
        return {
            "document_type": doc_type,
            "sensitivity_label": result.get("sensitivity_label", "LOW"),
            "data_categories": result.get("data_categories", []),
            "pii_types": result.get("pii_types", []),
            "finance_types": result.get("finance_types", []),
        }

    # ------------------------------------------------------------------
    # Document ingestion (store metadata in Redis)
    # ------------------------------------------------------------------
    def ingest_document(self, doc_id: str, text: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Store document metadata after classification."""
        classification = self.classify_document(text)
        metadata = {
            "document_id": doc_id,
            "tenant_id": tenant_id,
            "document_type": classification["document_type"],
            "sensitivity_label": classification["sensitivity_label"],
            "data_categories": classification["data_categories"],
            "retrieval_allowed": True,
        }
        key = f"rag:doc:{doc_id}"
        redis_client.setex(key, 3600*24*7, json.dumps(metadata))
        return metadata

    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        key = f"rag:doc:{doc_id}"
        data = redis_client.get(key)
        return json.loads(data) if data else None

    # ------------------------------------------------------------------
    # Chunk-level metadata (enriched)
    # ------------------------------------------------------------------
    def add_chunk(self, doc_id: str, chunk_index: int, text: str,
                  sensitivity_label: str = None, data_categories: List[str] = None) -> None:
        """Store enriched chunk metadata."""
        if sensitivity_label is None:
            classification = self.classify_document(text)
            sensitivity_label = classification["sensitivity_label"]
            data_categories = classification["data_categories"]
        chunk_data = {
            "doc_id": doc_id,
            "chunk_index": chunk_index,
            "text": text,
            "sensitivity_label": sensitivity_label,
            "data_categories": data_categories,
            "allowed_roles": self._roles_for_sensitivity(sensitivity_label),
        }
        redis_client.setex(f"rag:chunk:{doc_id}:{chunk_index}", 3600*24*7, json.dumps(chunk_data))

    def get_chunk_metadata(self, doc_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        key = f"rag:chunk:{doc_id}:{chunk_index}"
        data = redis_client.get(key)
        return json.loads(data) if data else None

    # ------------------------------------------------------------------
    # Role-aware access check (enhanced)
    # ------------------------------------------------------------------
    def check_access(self, user_role: str, sensitivity: str, categories: List[str] = None) -> bool:
        policy = self.policies.get(user_role, {"max_sensitivity": "LOW"})
        if self.sensitivity_rank.get(sensitivity, 0) > self.sensitivity_rank.get(policy["max_sensitivity"], 0):
            return False
        if policy.get("allow_categories") and categories:
            for cat in categories:
                if cat not in policy["allow_categories"]:
                    return False
        return True

    def _roles_for_sensitivity(self, sensitivity: str) -> List[str]:
        """Return roles that can access this sensitivity."""
        return [role for role, policy in self.policies.items()
                if self.sensitivity_rank.get(sensitivity, 0) <= self.sensitivity_rank.get(policy["max_sensitivity"], 0)]

    # ------------------------------------------------------------------
    # Retrieval filtering with detailed reasons and audit trace
    # ------------------------------------------------------------------
    def filter_chunks(
        self,
        chunks: List[Dict[str, Any]],
        user_role: str,
        tenant_id: str = "default"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
        """
        Filter chunks based on user role, tenant, and document policies.
        Returns (filtered_chunks, stats, audit_trace).
        """
        allowed_sensitivities = [sens for sens in self.sensitivity_rank.keys()
                                 if self.check_access(user_role, sens, [])]
        filtered = []
        stats = {"total": len(chunks), "allowed": 0, "blocked": 0, "reasons": []}
        audit_trace = []

        for chunk in chunks:
            decision = {"chunk_text": chunk.get("text", "")[:100], "allowed": False, "reason": None}
            # 1. Tenant check
            chunk_tenant = chunk.get("tenant_id")
            if chunk_tenant and chunk_tenant != tenant_id:
                decision["reason"] = f"tenant mismatch (chunk tenant {chunk_tenant})"
                stats["blocked"] += 1
                stats["reasons"].append(decision["reason"])
                audit_trace.append(decision)
                continue
            # 2. Document retrieval allowed check
            doc_id = chunk.get("doc_id")
            if doc_id:
                doc_meta = self.get_document_metadata(doc_id)
                if doc_meta and not doc_meta.get("retrieval_allowed", True):
                    decision["reason"] = "document disabled for retrieval"
                    stats["blocked"] += 1
                    stats["reasons"].append(decision["reason"])
                    audit_trace.append(decision)
                    continue
            # 3. Secret detection (optional)
            if self._contains_secret(chunk.get("text", "")):
                decision["reason"] = "secret‑containing chunk blocked"
                stats["blocked"] += 1
                stats["reasons"].append(decision["reason"])
                audit_trace.append(decision)
                continue
            # 4. Role/sensitivity check
            sensitivity = chunk.get("sensitivity_label")
            if not sensitivity:
                classification = self.classify_document(chunk["text"])
                sensitivity = classification["sensitivity_label"]
            if sensitivity in allowed_sensitivities:
                filtered.append(chunk)
                stats["allowed"] += 1
                decision["allowed"] = True
                decision["reason"] = "allowed"
            else:
                decision["reason"] = f"Sensitivity {sensitivity} not allowed for role {user_role}"
                stats["blocked"] += 1
                stats["reasons"].append(decision["reason"])
            audit_trace.append(decision)

        return filtered, stats, audit_trace

    def _contains_secret(self, text: str) -> bool:
        """Quick check for secret patterns (simple)."""
        for pat, _ in self.leakage_patterns:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    # ------------------------------------------------------------------
    # Output redaction mode
    # ------------------------------------------------------------------
    def redact_output(self, output_text: str) -> str:
        redacted = output_text
        for pat, _ in self.leakage_patterns:
            redacted = re.sub(pat, "[REDACTED]", redacted, flags=re.IGNORECASE)
        return redacted

    def scan_output(self, output_text: str, mode: str = "block") -> Dict[str, Any]:
        """
        Scan output for leakage. Mode can be 'allow', 'redact', or 'block'.
        Returns action and optionally redacted text.
        """
        detected = []
        for pat, name in self.leakage_patterns:
            if re.search(pat, output_text, re.IGNORECASE):
                detected.append(name)
        detected = list(set(detected))
        risk_level = "LOW"
        if any(t in detected for t in ["private_key", "aws_key", "openai_key"]):
            risk_level = "CRITICAL"
        elif any(t in detected for t in ["ssn", "credit_card", "api_key", "password"]):
            risk_level = "HIGH"
        elif detected:
            risk_level = "MEDIUM"

        if mode == "redact" and detected:
            redacted = self.redact_output(output_text)
            return {
                "action": "redact",
                "redacted_text": redacted,
                "leakage_detected": True,
                "leakage_types": detected,
                "risk_level": risk_level,
            }
        elif mode == "block" and detected and risk_level in ["HIGH", "CRITICAL"]:
            return {
                "action": "block",
                "leakage_detected": True,
                "leakage_types": detected,
                "risk_level": risk_level,
                "recommended_action": "block"
            }
        else:
            return {
                "action": "allow",
                "leakage_detected": bool(detected),
                "leakage_types": detected,
                "risk_level": risk_level,
                "recommended_action": "allow"
            }

rag_protection = RAGProtection()
