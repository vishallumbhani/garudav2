import json
from typing import List, Dict, Any
from sqlalchemy import text
from src.db.base import AsyncSessionLocal
from src.core.fallback import fallback

# ========== 6.1 Basic Console ==========
async def get_health_status() -> dict:
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except:
        db_ok = False
    return {
        "api": "healthy",
        "db": "healthy" if db_ok else "unhealthy",
        "redis": "healthy",  # implement if needed
        "degraded_engines": list(fallback.degraded_engines),
        "safe_mode": fallback.safe_mode,
        "integrity_status": "failed" if fallback.integrity_failures else "ok",
    }

async def get_recent_scans(limit: int = 50) -> List[dict]:
    query = text("""
        SELECT created_at, event_id, tenant_id, endpoint, decision, final_score, sensitivity_label, session_id
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"limit": limit})
        rows = result.fetchall()
        return [
            {
                "timestamp": r[0],
                "event_id": r[1],
                "tenant_id": r[2],
                "endpoint": r[3],
                "decision": r[4],
                "score": r[5],
                "sensitivity": r[6],
                "session_id": r[7],
            }
            for r in rows
        ]

async def get_recent_blocks(limit: int = 50) -> List[dict]:
    query = text("""
        SELECT created_at, event_id, session_id, decision, trace, policy_reason_codes
        FROM audit_logs
        WHERE decision = 'block'
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"limit": limit})
        rows = result.fetchall()
        blocks = []
        for r in rows:
            trace = r[4] if isinstance(r[4], dict) else json.loads(r[4]) if r[4] else {}
            policy_hits = trace.get("policy_reason_codes", []) or (r[5] if isinstance(r[5], list) else [])
            top_signals = {
                "hanuman_risk": trace.get("hanuman_risk_hint"),
                "bhishma_score": trace.get("scores", {}).get("bhishma"),
                "arjuna_label": trace.get("arjuna_label"),
            }
            blocks.append({
                "timestamp": r[0],
                "event_id": r[1],
                "session_id": r[2],
                "reason": "policy_block",
                "policy_hits": policy_hits,
                "top_signals": top_signals,
            })
        return blocks

async def get_trace(event_id: str) -> dict:
    query = text("""
        SELECT trace, playbook_actions
        FROM audit_logs
        WHERE event_id = :event_id
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"event_id": event_id})
        row = result.fetchone()
        if not row:
            return {"error": "Event not found"}
        trace = row[0] if isinstance(row[0], dict) else json.loads(row[0]) if row[0] else {}
        playbook_actions = row[1] if isinstance(row[1], dict) else json.loads(row[1]) if row[1] else {}
        return {"event_id": event_id, "trace": trace, "playbook_actions": playbook_actions}

# ========== 6.2 Sanjaya Dashboard ==========
async def get_audit_timeline(interval: str = "day", limit: int = 30) -> dict:
    sql_interval = {"hour": "hour", "day": "day", "week": "week"}.get(interval, "day")
    query = text(f"""
        SELECT
            DATE_TRUNC(:interval, created_at) AS time_bucket,
            COUNT(*) AS total,
            SUM(CASE WHEN decision = 'allow' THEN 1 ELSE 0 END) AS allow,
            SUM(CASE WHEN decision = 'monitor' THEN 1 ELSE 0 END) AS monitor,
            SUM(CASE WHEN decision = 'challenge' THEN 1 ELSE 0 END) AS challenge,
            SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) AS block
        FROM audit_logs
        GROUP BY time_bucket
        ORDER BY time_bucket DESC
        LIMIT :limit
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"interval": sql_interval, "limit": limit})
        rows = result.fetchall()
        timeline = []
        for r in rows:
            timeline.append({
                "time": r[0].isoformat() if r[0] else None,
                "total": r[1],
                "allow": r[2],
                "monitor": r[3],
                "challenge": r[4],
                "block": r[5],
            })
        return {"interval": interval, "data": timeline}

async def get_engine_outcomes(limit: int = 100) -> dict:
    query = text("""
        SELECT trace
        FROM audit_logs
        WHERE trace IS NOT NULL
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"limit": limit})
        rows = result.fetchall()
    engine_scores = {
        "hanuman": {"low": 0, "medium": 0, "high": 0, "degraded": 0},
        "bhishma": {"low": 0, "medium": 0, "high": 0, "degraded": 0},
        "shakuni": {"low": 0, "medium": 0, "high": 0, "degraded": 0},
        "arjuna": {"low": 0, "medium": 0, "high": 0, "degraded": 0},
    }
    fallback_count = 0
    for (trace,) in rows:
        if not trace:
            continue
        if isinstance(trace, str):
            try:
                trace = json.loads(trace)
            except:
                continue
        for eng in ["hanuman", "bhishma", "shakuni", "arjuna"]:
            score = trace.get("scores", {}).get(eng, 0) if isinstance(trace.get("scores"), dict) else 0
            if score < 0.3:
                engine_scores[eng]["low"] += 1
            elif score < 0.7:
                engine_scores[eng]["medium"] += 1
            else:
                engine_scores[eng]["high"] += 1
        if trace.get("fallback_used"):
            fallback_count += 1
    return {
        "engine_scores": engine_scores,
        "fallback_used_count": fallback_count,
        "total_samples": limit,
    }

async def get_policy_hits(limit: int = 50) -> dict:
    query = text("""
        SELECT policy_reason_codes, trace
        FROM audit_logs
        WHERE decision = 'block' AND policy_reason_codes IS NOT NULL
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"limit": limit})
        rows = result.fetchall()
    policy_counts = {}
    guardrail_hits = 0
    non_overridable = 0
    secret_severity_events = 0
    for (codes, trace) in rows:
        if isinstance(codes, str):
            try:
                codes = json.loads(codes)
            except:
                codes = [codes]
        if codes and isinstance(codes, list):
            for code in codes:
                policy_counts[code] = policy_counts.get(code, 0) + 1
        if isinstance(trace, str):
            try:
                trace = json.loads(trace)
            except:
                trace = {}
        if trace.get("global_guardrail_hit"):
            guardrail_hits += 1
        if trace.get("non_overridable_match"):
            non_overridable += 1
        if trace.get("secret_severity") == "critical":
            secret_severity_events += 1
    top_policies = sorted(policy_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "top_policies": [{"policy": k, "count": v} for k, v in top_policies],
        "guardrail_hits": guardrail_hits,
        "non_overridable_blocks": non_overridable,
        "critical_secret_events": secret_severity_events,
    }

async def get_session_behavior(session_id: str) -> dict:
    query = text("""
        SELECT decision, final_score, created_at, trace
        FROM audit_logs
        WHERE session_id = :session_id
        ORDER BY created_at ASC
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"session_id": session_id})
        rows = result.fetchall()
    if not rows:
        return {"error": "Session not found"}
    requests = []
    decisions = {"allow": 0, "monitor": 0, "challenge": 0, "block": 0}
    escalation_factor = 1.0
    classification = "unknown"
    for r in rows:
        created_at, decision, score, trace = r
        decisions[decision] = decisions.get(decision, 0) + 1
        if isinstance(trace, str):
            try:
                trace = json.loads(trace)
            except:
                trace = {}
        req_info = {
            "timestamp": created_at.isoformat(),
            "decision": decision,
            "score": score,
        }
        behavior = trace.get("behavior", {})
        if behavior:
            escalation_factor = behavior.get("escalation_factor", escalation_factor)
            classification = behavior.get("classification", classification)
            req_info["escalation_factor"] = behavior.get("escalation_factor")
            req_info["weighted_risk"] = behavior.get("weighted_risk")
        requests.append(req_info)
    return {
        "session_id": session_id,
        "total_requests": len(rows),
        "decisions": decisions,
        "escalation_factor": escalation_factor,
        "classification": classification,
        "history": requests,
    }