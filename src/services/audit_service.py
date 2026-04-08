import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.protection.log_integrity import add_hash_chain_fields, verify_hash_chain
from src.db.base import AsyncSessionLocal
from src.db.models import AuditLog

logger = logging.getLogger(__name__)


async def log_audit(event_data: dict):
    """
    Write audit entry to JSONL file and database.
    Uses a dedicated DB session to avoid async session conflicts.
    """
    log_path = Path("./logs/audit.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Phase 5: add tamper-evident hash chain
    event_data = add_hash_chain_fields(event_data, log_path)

    # Write to JSONL file first
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event_data, ensure_ascii=False, default=str) + "\n")

    # Write to database using a fresh session
    try:
        async with AsyncSessionLocal() as db:
            audit = AuditLog(
                event_id=event_data["event_id"],
                tenant_id=event_data.get("tenant_id"),
                user_id=event_data.get("user_id"),
                session_id=event_data.get("session_id"),
                input_type=event_data["input_type"],
                endpoint=event_data.get("endpoint"),
                decision=event_data["decision"],
                final_score=event_data["final_score"],
                policy_action=event_data.get("policy_action"),
                policy_reason_codes=event_data.get("policy_reason_codes", []),
                override_applied=event_data.get("override_applied", False),
                engine_results=event_data["engine_results"],
                trace=event_data["trace"],
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(audit)
            await db.commit()
    except Exception as e:
        logger.error("Failed to write audit log to DB: %s", e, exc_info=True)
        logger.warning("Audit log saved only to file, DB error.")


def verify_audit_chain() -> bool:
    """Verify tamper-evident audit hash chain."""
    return verify_hash_chain()