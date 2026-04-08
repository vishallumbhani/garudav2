from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class HealthStatus(BaseModel):
    api: str
    db: str
    redis: str
    degraded_engines: List[str]
    safe_mode: bool
    integrity_status: str

class RecentScan(BaseModel):
    timestamp: datetime
    event_id: str
    tenant_id: Optional[str]
    endpoint: str
    decision: str
    score: int
    sensitivity: Optional[str]
    session_id: Optional[str]

class RecentBlock(BaseModel):
    timestamp: datetime
    event_id: str
    session_id: Optional[str]
    reason: str
    policy_hits: List[str]
    top_signals: Dict[str, Any]

class TraceResponse(BaseModel):
    event_id: str
    trace: Dict[str, Any]
    playbook_actions: Optional[Dict[str, Any]]