from sqlalchemy import Column, Integer, String, JSON, DateTime, Index, Boolean
from datetime import datetime
from src.db.base import Base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Index, Boolean, UUID
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from datetime import datetime
import uuid

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    tenant_id = Column(String)
    user_id = Column(String)
    session_id = Column(String)
    input_type = Column(String)  # "text" or "file"

    # ? NEW FIELD (fixes your error)
    endpoint = Column(String(50), nullable=True)

    decision = Column(String)
    final_score = Column(Integer)  # stored as integer 0-100

    # ? NEW FIELDS (Phase 4 governance)
    policy_action = Column(String(50), nullable=True)
    policy_reason_codes = Column(JSON, nullable=True)
    override_applied = Column(Boolean, default=False)

    engine_results = Column(JSON)
    trace = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
    )

# ─── NEW: User model ─────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="viewer")  # admin | operator | viewer | auditor
    tenant_id = Column(String(100), nullable=True, default="default")
    enabled = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_users_tenant_role", "tenant_id", "role"),
    )


# ─── NEW: Alert model ─────────────────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(pgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    severity = Column(String(20), nullable=False)  # critical | high | medium | low
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    context = Column(JSON, nullable=True)
    tenant_id = Column(String(100), nullable=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_alerts_tenant_severity", "tenant_id", "severity"),
        Index("ix_alerts_created_at", "created_at"),
    )
