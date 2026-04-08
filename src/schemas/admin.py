from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Rule Management
class Rule(BaseModel):
    id: Optional[int]
    engine: str  # bhishma, shakuni
    name: str
    conditions: Dict[str, Any]
    action: str  # block, challenge, monitor, allow
    enabled: bool
    priority: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class RuleCreate(BaseModel):
    engine: str
    name: str
    conditions: Dict[str, Any]
    action: str
    enabled: bool = True
    priority: int = 0

class RuleUpdate(BaseModel):
    conditions: Optional[Dict[str, Any]]
    action: Optional[str]
    enabled: Optional[bool]
    priority: Optional[int]

# Policy Management
class Policy(BaseModel):
    policy_key: str
    action: str
    policy_level: str  # global, tenant, session
    applies_to: List[str]
    conditions_json: Optional[Dict[str, Any]]
    enabled: bool
    is_overridable: bool
    override_scope: str  # none, tenant, session

class PolicyUpdate(BaseModel):
    action: Optional[str]
    enabled: Optional[bool]
    conditions_json: Optional[Dict[str, Any]]
    is_overridable: Optional[bool]

# Tenant Config
class TenantConfig(BaseModel):
    tenant_id: str
    strict_mode: bool
    thresholds: Dict[str, float]  # e.g., block_threshold, challenge_threshold
    feature_toggles: Dict[str, bool]
    overrides_summary: Optional[Dict[str, Any]]

class TenantConfigUpdate(BaseModel):
    strict_mode: Optional[bool]
    thresholds: Optional[Dict[str, float]]
    feature_toggles: Optional[Dict[str, bool]]

# API Key Management
class ApiKey(BaseModel):
    id: Optional[int]
    key_prefix: str
    tenant_id: str
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    enabled: bool

class ApiKeyCreate(BaseModel):
    tenant_id: str
    expires_days: Optional[int] = 90