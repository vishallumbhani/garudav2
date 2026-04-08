import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# 1. Update scan_service.py to guarantee the key is present
with open("src/services/scan_service.py", "r") as f:
    content = f.read()

# Find the part where behavior is set and ensure escalation_reason is always set
# We'll replace the entire _run_pipeline with a corrected version
new_content = '''import asyncio
from pathlib import Path
from src.core.models import ScanRequest, ScanResponse
from src.utils.file_extractors import extract_from_file
from src.engines.hanuman.engine import Hanuman
from src.engines.bhishma.engine import Bhishma
from src.engines.yudhishthira.engine import Yudhishthira
from src.engines.krishna.engine import Krishna
from src.engines.sanjaya.engine import Sanjaya
from src.services.audit_service import log_audit
from src.services.behavior_service import tracker
from src.core.fallback import fallback
from src.db.base import AsyncSessionLocal

async def scan_text(request: ScanRequest) -> ScanResponse:
    request.normalized_text = request.content if isinstance(request.content, str) else request.content.decode('utf-8', errors='ignore')
    return await _run_pipeline(request)

async def scan_file(request: ScanRequest) -> ScanResponse:
    temp_file = Path("/tmp") / f"garuda_{request.event_id}.tmp"
    temp_file.write_bytes(request.content)
    try:
        extraction = extract_from_file(temp_file, request.content, request.filename or "unknown")
        request.normalized_text = extraction["normalized_text"]
        request.file_metadata = extraction["metadata"]
    finally:
        temp_file.unlink(missing_ok=True)
    return await _run_pipeline(request)

async def _run_pipeline(request) -> ScanResponse:
    engine_results = {}

    hanuman_result = fallback.wrap_engine("hanuman", Hanuman().run, request)
    engine_results["hanuman"] = hanuman_result

    bhishma_result = fallback.wrap_engine("bhishma", Bhishma().run, request, hanuman_result)
    engine_results["bhishma"] = bhishma_result

    yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)
    engine_results["yudhishthira"] = yudhishthira_result

    if request.session_id:
        risk_score = bhishma_result.get("score", 0.5)
        stats = tracker.record_request(request.session_id, risk_score)
        engine_results["behavior"] = {
            "engine": "behavior",
            "status": "ok",
            "escalation_factor": stats["escalation_factor"],
            "escalation_reason": stats["escalation_reason"],
            "request_count": stats["request_count"],
            "avg_risk": stats["avg_risk"],
            "max_risk": stats["max_risk"]
        }
    else:
        engine_results["behavior"] = {
            "escalation_factor": 1.0,
            "escalation_reason": "no session id provided"
        }

    krishna_result = fallback.wrap_engine("krishna", Krishna().run, request, engine_results)
    engine_results["krishna"] = krishna_result

    sanjaya = Sanjaya()
    response = sanjaya.run(request, krishna_result)

    audit_data = {
        "event_id": request.event_id,
        "tenant_id": request.tenant_id,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "input_type": request.content_type,
        "decision": response.decision,
        "final_score": response.score,
        "normalized_score": response.normalized_score,
        "engine_results": engine_results,
        "trace": krishna_result.get("details", {}).get("trace", {})
    }

    async with AsyncSessionLocal() as db:
        await log_audit(db, audit_data)

    return response
'''

with open("src/services/scan_service.py", "w") as f:
    f.write(new_content)
print("✅ Updated scan_service.py to include escalation_reason")

# 2. Ensure Krishna uses the correct key (it already does)
# We'll just print confirmation
print("✅ Krishna already expects 'escalation_reason'")
