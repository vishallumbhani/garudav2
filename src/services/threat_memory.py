import hashlib
import re
from typing import Dict, List, Set, Optional

import redis
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class ThreatMemory:
    """
    Production-tuned threat memory.

    Principles:
    - repetition alone should not escalate benign traffic
    - only indicator-matched prompts should drive modifiers
    - session memory is stronger than global memory
    - global memory is weak and decays faster
    """

    def __init__(self, ttl_global: int = 3600 * 24 * 2, ttl_session: int = 3600):
        self.ttl_global = ttl_global
        self.ttl_session = ttl_session

        self.indicators: Dict[str, List[str]] = {
            "injection": [
                r"(ignore|forget).{0,40}(previous|prior|all).{0,40}(instructions|rules|prompts|restrictions)",
                r"(reveal|show|dump|print).{0,40}(system|hidden|internal|secret).{0,40}(prompt|instructions|context|code)",
                r"(unrestricted|developer|debug|jailbreak).{0,20}(mode)?",
                r"override.{0,40}(guardrails|safety|policies|restrictions)",
                r"do anything now",
                r"act as.{0,30}(unrestricted|system|developer|admin|attacker|hacker)",
                r"roleplay.{0,30}(attacker|hacker|malicious|unrestricted)",
                r"pretend.{0,30}(attacker|hacker|malicious|unrestricted|system|developer)",
                r"(show|reveal).{0,30}(hidden|internal|secret).{0,30}(instructions|prompt|context|code)",
            ],
            "bypass": [
                r"(bypass|evade|circumvent|avoid|dodge).{0,40}(authentication|security|filter|moderation|controls|policies|restrictions)",
                r"(red team|penetration test|pentest)",
                r"(educational purposes|for research|hypothetically|for testing purposes)",
                r"test.{0,30}(content filters|moderation|safeguards)",
                r"(disable|weaken).{0,30}(monitoring|controls|protection|safeguards)",
            ],
            "exfiltration": [
                r"(exfiltrate|leak|steal|export|copy).{0,40}(data|records|files|secrets|tokens|keys|credentials)",
                r"hide stolen",
                r"extract.{0,30}(api keys|tokens|secrets|credentials)",
                r"covert.{0,30}(transfer|exfiltration|channel)",
                r"without detection",
                r"dns tunneling",
                r"(move|smuggle).{0,30}(data|records|files|secrets).{0,30}(out|outside|externally)",
            ],
        }

        self.compiled: Dict[str, List[re.Pattern]] = {
            family: [re.compile(p, re.IGNORECASE) for p in patterns]
            for family, patterns in self.indicators.items()
        }

    def _normalize(self, text: str) -> str:
        t = text.lower()
        t = re.sub(r"\s+", " ", t)
        t = re.sub(r"[^\w\s]", "", t)
        return t.strip()

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _extract_indicator_signatures(self, normalized_text: str) -> List[str]:
        matches: Set[str] = set()
        for family, patterns in self.compiled.items():
            for idx, pat in enumerate(patterns):
                if pat.search(normalized_text):
                    matches.add(f"{family}:{idx}")
        return sorted(matches)

    def _extract_family_names(self, normalized_text: str) -> List[str]:
        families: Set[str] = set()
        for sig in self._extract_indicator_signatures(normalized_text):
            families.add(sig.split(":", 1)[0])
        return sorted(families)

    def _family_sig_fingerprint(self, normalized_text: str) -> Optional[str]:
        signatures = self._extract_indicator_signatures(normalized_text)
        if not signatures:
            return None
        return self._hash(",".join(signatures))

    def _family_name_fingerprint(self, normalized_text: str) -> Optional[str]:
        families = self._extract_family_names(normalized_text)
        if not families:
            return None
        return self._hash(",".join(families))

    def _incr_with_ttl(self, key: str, ttl: int) -> None:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        pipe.execute()

    def record_prompt(self, session_id: str, prompt_text: str) -> None:
        if not session_id:
            return

        try:
            norm = self._normalize(prompt_text)
            matched_indicators = self._extract_indicator_signatures(norm)
            matched_families = self._extract_family_names(norm)

            # Do not store benign traffic in threat memory
            if not matched_indicators and not matched_families:
                return

            text_hash = self._hash(norm)
            family_sig_fp = self._family_sig_fingerprint(norm)
            family_name_fp = self._family_name_fingerprint(norm)

            self._incr_with_ttl(f"threat:session:{session_id}:text:{text_hash}", self.ttl_session)

            if family_sig_fp:
                self._incr_with_ttl(f"threat:session:{session_id}:family_sig:{family_sig_fp}", self.ttl_session)
            if family_name_fp:
                self._incr_with_ttl(f"threat:session:{session_id}:family_name:{family_name_fp}", self.ttl_session)

            self._incr_with_ttl(f"threat:global:text:{text_hash}", self.ttl_global)

            if family_sig_fp:
                self._incr_with_ttl(f"threat:global:family_sig:{family_sig_fp}", self.ttl_global)
            if family_name_fp:
                self._incr_with_ttl(f"threat:global:family_name:{family_name_fp}", self.ttl_global)

        except Exception:
            return

    def record_file(self, session_id: str, file_content: bytes) -> None:
        if not session_id:
            return
        try:
            file_hash = hashlib.sha256(file_content).hexdigest()
            self._incr_with_ttl(f"threat:session:{session_id}:file:{file_hash}", self.ttl_session)
            self._incr_with_ttl(f"threat:global:file:{file_hash}", self.ttl_global)
        except Exception:
            return

    def _count_to_modifier(self, weight: float) -> float:
        if weight < 1.5:
            return 1.0
        elif weight < 3.0:
            return 1.1
        elif weight < 5.0:
            return 1.25
        elif weight < 8.0:
            return 1.4
        else:
            return 1.6

    def get_memory_modifiers(self, session_id: str, prompt_text: str, file_content: bytes = None) -> dict:
        try:
            norm = self._normalize(prompt_text)
            text_hash = self._hash(norm)
            family_sig_fp = self._family_sig_fingerprint(norm)
            family_name_fp = self._family_name_fingerprint(norm)

            matched_indicators = self._extract_indicator_signatures(norm)
            matched_families = self._extract_family_names(norm)

            # Critical: do not escalate benign prompts based on repetition alone
            if not matched_indicators and not matched_families:
                return {
                    "engine": "threat_memory",
                    "status": "ok",
                    "engine_status": "ok",
                    "session_modifier": 1.0,
                    "global_modifier": 1.0,
                    "session_reason": "No threat indicators matched",
                    "global_reason": "No threat indicators matched",
                    "session_text_count": 0,
                    "session_family_sig_count": 0,
                    "session_family_name_count": 0,
                    "global_text_count": 0,
                    "global_family_sig_count": 0,
                    "global_family_name_count": 0,
                    "matched_indicators": matched_indicators,
                    "matched_families": matched_families,
                }

            session_text_count = int(redis_client.get(f"threat:session:{session_id}:text:{text_hash}") or 0)
            session_family_sig_count = int(redis_client.get(f"threat:session:{session_id}:family_sig:{family_sig_fp}") or 0) if family_sig_fp else 0
            session_family_name_count = int(redis_client.get(f"threat:session:{session_id}:family_name:{family_name_fp}") or 0) if family_name_fp else 0

            global_text_count = int(redis_client.get(f"threat:global:text:{text_hash}") or 0)
            global_family_sig_count = int(redis_client.get(f"threat:global:family_sig:{family_sig_fp}") or 0) if family_sig_fp else 0
            global_family_name_count = int(redis_client.get(f"threat:global:family_name:{family_name_fp}") or 0) if family_name_fp else 0

            session_file_count = 0
            global_file_count = 0
            if file_content:
                file_hash = hashlib.sha256(file_content).hexdigest()
                session_file_count = int(redis_client.get(f"threat:session:{session_id}:file:{file_hash}") or 0)
                global_file_count = int(redis_client.get(f"threat:global:file:{file_hash}") or 0)

            session_weight = (
                session_text_count * 1.0
                + session_family_sig_count * 0.7
                + session_family_name_count * 0.5
                + session_file_count * 0.2
            )

            global_weight = (
                global_text_count * 0.35
                + global_family_sig_count * 0.25
                + global_family_name_count * 0.15
                + global_file_count * 0.05
            )

            session_modifier = self._count_to_modifier(session_weight)
            global_modifier = self._count_to_modifier(global_weight)

            session_reason = (
                f"Session threat memory: exact={session_text_count}, "
                f"family_sig={session_family_sig_count}, family_name={session_family_name_count}"
            )
            global_reason = (
                f"Global threat memory: exact={global_text_count}, "
                f"family_sig={global_family_sig_count}, family_name={global_family_name_count}"
            )

            if session_modifier > 1.0:
                session_reason += f" -> modifier {session_modifier:.2f}"
            if global_modifier > 1.0:
                global_reason += f" -> modifier {global_modifier:.2f}"

            return {
                "engine": "threat_memory",
                "status": "ok",
                "engine_status": "ok",
                "session_modifier": round(session_modifier, 2),
                "global_modifier": round(global_modifier, 2),
                "session_reason": session_reason,
                "global_reason": global_reason,
                "session_text_count": session_text_count,
                "session_family_sig_count": session_family_sig_count,
                "session_family_name_count": session_family_name_count,
                "global_text_count": global_text_count,
                "global_family_sig_count": global_family_sig_count,
                "global_family_name_count": global_family_name_count,
                "matched_indicators": matched_indicators,
                "matched_families": matched_families,
            }

        except Exception as e:
            return {
                "engine": "threat_memory",
                "status": "degraded",
                "engine_status": "degraded",
                "session_modifier": 1.0,
                "global_modifier": 1.0,
                "session_reason": f"threat memory degraded: {str(e)}",
                "global_reason": "threat memory unavailable",
                "session_text_count": 0,
                "session_family_sig_count": 0,
                "session_family_name_count": 0,
                "global_text_count": 0,
                "global_family_sig_count": 0,
                "global_family_name_count": 0,
                "matched_indicators": [],
                "matched_families": [],
            }

    def reset_test_scope(self, session_id: Optional[str] = None) -> None:
        try:
            patterns = []
            if session_id:
                patterns.append(f"threat:session:{session_id}:*")
            else:
                patterns.append("threat:session:*")
            patterns.extend([
                "threat:global:text:*",
                "threat:global:family_sig:*",
                "threat:global:family_name:*",
                "threat:global:file:*",
            ])

            for pattern in patterns:
                for key in redis_client.scan_iter(match=pattern, count=500):
                    redis_client.delete(key)
        except Exception:
            return


threat_memory = ThreatMemory()