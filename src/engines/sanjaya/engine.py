"""
Observability / audit: writes logs and returns response.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from src.core.models import ScanResponse

logger = logging.getLogger(__name__)

class Sanjaya:
    def run(self, request, krishna_result):
        # Safe extraction with fallbacks
        decision = krishna_result.get("decision", "challenge")
        score = krishna_result.get("score", 95 if krishna_result.get("status") == "error" else 0)
        normalized_score = krishna_result.get("normalized_score", score / 100.0)
        details = krishna_result.get("details", {})
        trace = details.get("trace", {})

        # Build final response
        response = ScanResponse(
            event_id=request.event_id,
            decision=decision,
            score=score,
            normalized_score=normalized_score,
            details=details
        )

        # Prepare audit entry
        audit_entry = {
            "event_id": request.event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "input_type": request.content_type,
            "decision": response.decision,
            "score": response.score,
            "normalized_score": response.normalized_score,
            "trace": trace
        }

        # Write to JSONL file
        log_path = Path("./logs/audit.jsonl")
        log_path.parent.mkdir(exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")

        return response
