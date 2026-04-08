from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from src.services.admin_service import (
    list_rules, create_rule, update_rule, delete_rule,
    list_policies, update_policy,
    get_tenant_config, update_tenant_config,
    list_api_keys, create_api_key, revoke_api_key,
)
from src.schemas.admin import RuleCreate, RuleUpdate, PolicyUpdate, TenantConfigUpdate, ApiKeyCreate
from src.auth.dependencies import require_role

router = APIRouter(prefix="/v1/admin", tags=["admin"])

# All admin endpoints require admin role
admin_only = Depends(require_role(["admin"]))

@router.get("/rules")
async def get_rules(engine: Optional[str] = None, _=admin_only):
    return await list_rules(engine)

@router.post("/rules")
async def add_rule(rule: RuleCreate, _=admin_only):
    return await create_rule(rule.dict())

@router.put("/rules/{rule_id}")
async def modify_rule(rule_id: int, update: RuleUpdate, _=admin_only):
    result = await update_rule(rule_id, {k: v for k, v in update.dict().items() if v is not None})
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")
    return result

@router.delete("/rules/{rule_id}")
async def remove_rule(rule_id: int, _=admin_only):
    if not await delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "deleted"}

@router.get("/policies")
async def get_policies(tenant_id: Optional[str] = None, _=admin_only):
    return await list_policies(tenant_id)

@router.patch("/policies/{policy_key}")
async def patch_policy(policy_key: str, update: PolicyUpdate, _=admin_only):
    result = await update_policy(policy_key, {k: v for k, v in update.dict().items() if v is not None})
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result

@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, _=admin_only):
    config = await get_tenant_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return config

@router.patch("/tenants/{tenant_id}")
async def patch_tenant(tenant_id: str, update: TenantConfigUpdate, _=admin_only):
    result = await update_tenant_config(tenant_id, {k: v for k, v in update.dict().items() if v is not None})
    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result

@router.get("/api-keys")
async def get_api_keys(tenant_id: Optional[str] = None, _=admin_only):
    return await list_api_keys(tenant_id)

@router.post("/api-keys")
async def new_api_key(key_data: ApiKeyCreate, _=admin_only):
    return await create_api_key(key_data.dict())

@router.delete("/api-keys/{key_id}")
async def revoke_key(key_id: int, _=admin_only):
    if not await revoke_api_key(key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked"}