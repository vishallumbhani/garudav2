#!/usr/bin/env python3
"""
Garuda Phase 1 Scaffolding
Creates the necessary files and placeholder code for the text/file scan endpoints
and the engine pipeline.
"""

import os
from pathlib import Path

# Project root (assuming script is in scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# ----------------------------------------------------------------------
# Helper to write a file only if it doesn't exist
def write_if_not_exists(path, content):
    path = Path(path)
    if path.exists():
        print(f"Skipping {path} (already exists)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"Created {path}")

# ----------------------------------------------------------------------
# 1. API Routes
write_if_not_exists("src/api/routes/scan_text.py", '''\
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

from src.services.scan_service import scan_text
from src.core.models import ScanRequest, ScanResponse

router = APIRouter()

class TextScanRequest(BaseModel):
    text: str
    tenant_id: str = "default"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: str = "api"

@router.post("/v1/scan/text", response_model=ScanResponse)
async def scan_text_endpoint(request: TextScanRequest):
    """
    Scan text input through the engine pipeline.
    """
    # Convert to internal model
    internal_request = ScanRequest(
        content_type="text",
        content=request.text,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        session_id=request.session_id,
        source=request.source,
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow()
    )

    # Call the scan service
    result = await scan_text(internal_request)

    return result
''')

write_if_not_exists("src/api/routes/scan_file.py", '''\
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional
import uuid
from datetime import datetime

from src.services.scan_service import scan_file
from src.core.models import ScanRequest, ScanResponse

router = APIRouter()

@router.post("/v1/scan/file", response_model=ScanResponse)
async def scan_file_endpoint(
    file: UploadFile = File(...),
    tenant_id: str = Form("default"),
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    source: str = Form("api")
):
    """
    Scan an uploaded file through the engine pipeline.
    """
    # Read file content (limit size to avoid memory issues)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large")

    internal_request = ScanRequest(
        content_type="file",
        content=content,
        filename=file.filename,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        source=source,
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow()
    )

    result = await scan_file(internal_request)
    return result
''')

# ----------------------------------------------------------------------
# 2. Core models (if not already present)
write_if_not_exists("src/core/models.py", '''\
from pydantic import BaseModel
from typing import Any, Dict, Optional, Union
from datetime import datetime

class ScanRequest(BaseModel):
    content_type: str  # "text" or "file"
    content: Union[str, bytes]  # actual content
    filename: Optional[str] = None  # for files
    tenant_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: str
    event_id: str
    timestamp: datetime

class ScanResponse(BaseModel):
    event_id: str
    decision: str  # "allow", "monitor", "challenge", "block"
    score: int
    details: Dict[str, Any]

class EngineResult(BaseModel):
    engine_name: str
    score: int
    details: Dict[str, Any]
''')

# ----------------------------------------------------------------------
# 3. Scan service (orchestrator)
write_if_not_exists("src/services/scan_service.py", '''\
from src.core.models import ScanRequest, ScanResponse
from src.engines.hanuman.engine import Hanuman
from src.engines.bhishma.engine import Bhishma
from src.engines.yudhishthira.engine import Yudhishthira
from src.engines.krishna.engine import Krishna
from src.engines.sanjaya.engine import Sanjaya

async def scan_text(request: ScanRequest) -> ScanResponse:
    # Pipeline:
    # Hanuman -> Bhishma -> Yudhishthira -> Krishna -> Sanjaya
    # (All engines are synchronous for now; you can use asyncio.to_thread if needed)
    hanuman_result = Hanuman().run(request)
    bhishma_result = Bhishma().run(request, hanuman_result)
    yudhishthira_result = Yudhishthira().run(request, bhishma_result)
    krishna_result = Krishna().run(request, yudhishthira_result)
    # Sanjaya writes audit logs and returns the final response
    response = Sanjaya().run(request, krishna_result)
    return response

async def scan_file(request: ScanRequest) -> ScanResponse:
    # Same pipeline, but file extraction can be added here
    # For now, treat the file content as bytes; you might want to extract text
    # using src/utils/file_extractors.py
    hanuman_result = Hanuman().run(request)
    bhishma_result = Bhishma().run(request, hanuman_result)
    yudhishthira_result = Yudhishthira().run(request, bhishma_result)
    krishna_result = Krishna().run(request, yudhishthira_result)
    response = Sanjaya().run(request, krishna_result)
    return response
''')

# ----------------------------------------------------------------------
# 4. Engine stubs
engines = [
    ("hanuman", "Fast triage engine", """\
    # Hanuman: fast, cheap triage. Flags suspicious patterns.
    def run(self, request):
        # For now, always return a neutral score
        return {"engine": "hanuman", "score": 50, "details": {"message": "Placeholder"}}
    """),
    ("bhishma", "Rule engine (regex/keyword)", """\
    import yaml
    from pathlib import Path
    class Bhishma:
        def __init__(self):
            # Load rules from configs/bhishma_rules.yaml
            self.rules = []
            rules_path = Path(__file__).parent / "rules.yaml"
            if rules_path.exists():
                with open(rules_path) as f:
                    self.rules = yaml.safe_load(f).get("rules", [])

        def run(self, request, hanuman_result):
            # Evaluate rules against request content
            # For placeholder, return neutral score
            return {"engine": "bhishma", "score": 50, "details": {"rules_matched": []}}
    """),
    ("yudhishthira", "Policy/tenant engine", """\
    class Yudhishthira:
        def run(self, request, bhishma_result):
            # Apply tenant policies (e.g., strict mode)
            # For placeholder, pass through
            return {"engine": "yudhishthira", "score": bhishma_result.get("score", 50), "details": {}}
    """),
    ("krishna", "Decision aggregator", """\
    class Krishna:
        def run(self, request, yudhishthira_result):
            score = yudhishthira_result.get("score", 50)
            if score >= 80:
                decision = "block"
            elif score >= 60:
                decision = "challenge"
            elif score >= 30:
                decision = "monitor"
            else:
                decision = "allow"
            return {"engine": "krishna", "score": score, "decision": decision, "details": {}}
    """),
    ("sanjaya", "Observability / audit", """\
    import json
    import logging
    from datetime import datetime
    from pathlib import Path
    class Sanjaya:
        def run(self, request, krishna_result):
            # Write audit log to file
            audit_entry = {
                "event_id": request.event_id,
                "timestamp": datetime.utcnow().isoformat(),
                "tenant_id": request.tenant_id,
                "user_id": request.user_id,
                "session_id": request.session_id,
                "input_type": request.content_type,
                "decision": krishna_result["decision"],
                "score": krishna_result["score"],
                "engine_results": krishna_result["details"],
                "trace": {}  # You can add more trace info
            }
            log_path = Path("./logs/audit.jsonl")
            log_path.parent.mkdir(exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(audit_entry) + "\\n")

            # Return the final response
            from src.core.models import ScanResponse
            return ScanResponse(
                event_id=request.event_id,
                decision=krishna_result["decision"],
                score=krishna_result["score"],
                details=krishna_result["details"]
            )
    """),
]

for eng_name, description, code in engines:
    path = f"src/engines/{eng_name}/engine.py"
    if not Path(path).exists():
        # Create the engine directory
        Path(f"src/engines/{eng_name}").mkdir(parents=True, exist_ok=True)
        # Write __init__.py if missing
        init_path = f"src/engines/{eng_name}/__init__.py"
        if not Path(init_path).exists():
            Path(init_path).write_text("# Engine stub")
            print(f"Created {init_path}")
        # Write engine.py
        Path(path).write_text(f'''\
\"\"\"{description}\"\"\"

class {eng_name.capitalize()}:
    {code}
''')
        print(f"Created {path}")
    else:
        print(f"Skipping {path} (already exists)")

# ----------------------------------------------------------------------
# 5. Ensure main.py includes the routes
main_path = "src/api/main.py"
if Path(main_path).exists():
    # Check if routes are already imported; if not, add them
    content = Path(main_path).read_text()
    if "from src.api.routes import scan_text, scan_file" not in content:
        # Insert route imports and include_router
        new_content = content.replace(
            "app = FastAPI(title=\"Garuda Local\")",
            "app = FastAPI(title=\"Garuda Local\")\n\nfrom src.api.routes import scan_text, scan_file\napp.include_router(scan_text.router)\napp.include_router(scan_file.router)"
        )
        Path(main_path).write_text(new_content)
        print(f"Updated {main_path} with route inclusion")
    else:
        print(f"{main_path} already includes routes")
else:
    print(f"Warning: {main_path} not found, can't update")

# ----------------------------------------------------------------------
# 6. Optional: create default rules.yaml for Bhishma
rules_path = "src/engines/bhishma/rules.yaml"
if not Path(rules_path).exists():
    rules_content = '''\
rules:
  - pattern: "ignore previous instructions"
    severity: 80
    action: block
  - pattern: "secret token"
    severity: 90
    action: block
  - pattern: "ssh-rsa"
    severity: 70
    action: monitor
'''
    Path(rules_path).parent.mkdir(exist_ok=True)
    Path(rules_path).write_text(rules_content)
    print(f"Created {rules_path}")

# ----------------------------------------------------------------------
print("\\n✅ Scaffolding completed.")
print("Now you can start implementing the actual logic in the engine files.")
print("Run the development server and test with ./scripts/test_api.sh")
