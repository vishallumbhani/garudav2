#!/usr/bin/env python3
"""
Phase 1 Implementation Script
Creates the full working components: file extractor, Hanuman, Bhishma,
Yudhishthira, audit DB integration, and updates the scan service.
"""

import os
import sys
from pathlib import Path

# Project root (assuming script is in scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    """Write content to a file, creating parent directories if needed."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# ----------------------------------------------------------------------
# 1. File Extractor
write_file("src/utils/file_extractors.py", '''\
import os
import json
import csv
import re
from pathlib import Path
from typing import Dict, Any, Optional
import pypdf

def extract_from_file(file_path: Path, content_bytes: bytes, original_name: str) -> Dict[str, Any]:
    """
    Extract normalized text and metadata from a file.
    Returns dict with input_type, normalized_text, metadata.
    """
    ext = Path(original_name).suffix.lower()
    metadata = {
        "file_name": original_name,
        "file_extension": ext,
        "length": len(content_bytes),
        "content_type": _guess_mime(ext)
    }
    text = ""

    if ext in ['.txt', '.md', '.log', '.py', '.js', '.java']:
        # Plain text files
        text = content_bytes.decode('utf-8', errors='ignore')
    elif ext == '.csv':
        try:
            decoded = content_bytes.decode('utf-8')
            reader = csv.reader(decoded.splitlines())
            rows = list(reader)
            text = "\\n".join(",".join(row) for row in rows)
        except:
            text = decoded
    elif ext == '.json':
        try:
            data = json.loads(content_bytes)
            text = json.dumps(data, indent=2)
        except:
            text = content_bytes.decode('utf-8', errors='ignore')
    elif ext in ['.yaml', '.yml']:
        # For simplicity, treat as text
        text = content_bytes.decode('utf-8', errors='ignore')
    elif ext == '.pdf':
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                text = "\\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        except Exception as e:
            text = f"[PDF extraction error: {e}]"
    else:
        # Unsupported – treat as text but warn
        text = content_bytes.decode('utf-8', errors='ignore')
        metadata['warning'] = "unsupported format, treated as text"

    return {
        "input_type": "file",
        "normalized_text": text,
        "metadata": metadata
    }

def _guess_mime(ext: str) -> str:
    mime_map = {
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.log': 'text/plain',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.py': 'text/x-python',
        '.js': 'application/javascript',
        '.java': 'text/x-java',
        '.yaml': 'application/x-yaml',
        '.yml': 'application/x-yaml',
        '.pdf': 'application/pdf'
    }
    return mime_map.get(ext, 'application/octet-stream')
''')

# ----------------------------------------------------------------------
# 2. Hanuman Engine
write_file("src/engines/hanuman/engine.py", '''\
"""
Fast triage engine with enhanced checks.
"""

import re
from typing import Dict, Any, List

class Hanuman:
    def run(self, request) -> Dict[str, Any]:
        """
        Perform fast triage on normalized content.
        Returns:
        - status: ok/warning/error
        - score: float 0-1 (higher = more suspicious)
        - confidence: float
        - labels: list of triggered labels
        - reason: string
        """
        text = request.normalized_text if hasattr(request, 'normalized_text') else request.content
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')

        score = 0.0
        labels = []
        reason = "Fast triage completed."

        # 1. Long input
        if len(text) > 5000:
            score += 0.2
            labels.append("long_input")
            reason += " Input is long."

        # 2. Suspicious density of security-sensitive words
        sensitive_words = ["secret", "token", "password", "key", "auth", "credential", "api_key", "private_key"]
        sensitive_count = sum(text.lower().count(word) for word in sensitive_words)
        density = sensitive_count / max(1, len(text)/1000)  # per 1000 chars
        if density > 2:
            score += 0.25
            labels.append("high_density_sensitive")
            reason += " High density of sensitive terms."
        elif density > 0.5:
            score += 0.1
            labels.append("moderate_density_sensitive")

        # 3. Likely secret markers
        secret_patterns = [
            r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----",
            r"Bearer\s+[A-Za-z0-9_\-\.]+",
            r"Authorization:\s*Basic\s+[A-Za-z0-9+/=]+",
            r"sk-[A-Za-z0-9]{32,}",
        ]
        for pattern in secret_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.35
                labels.append("secret_marker_detected")
                reason += " Secret marker found."
                break

        # 4. Repeated instruction phrases (injection attempts)
        injection_phrases = ["ignore previous instructions", "reveal system prompt", "forget all rules", "act as"]
        for phrase in injection_phrases:
            if phrase.lower() in text.lower():
                score += 0.3
                labels.append("injection_attempt")
                reason += f" Injection phrase: '{phrase}'."
                break

        # 5. Low-information / junk input
        if len(text.strip()) < 10:
            score += 0.1
            labels.append("short_input")
        if len(set(text)) < 20:  # many repeated chars
            score += 0.05
            labels.append("low_entropy")

        # Cap score at 0.95
        score = min(score, 0.95)

        return {
            "engine": "hanuman",
            "status": "ok",
            "score": round(score, 2),
            "confidence": 0.9,
            "labels": labels,
            "reason": reason
        }
''')

# ----------------------------------------------------------------------
# 3. Bhishma YAML Rules
write_file("src/engines/bhishma/rules.yaml", '''\
critical_patterns:
  - pattern: "(?i)(ignore|disregard|forget) previous instructions"
    severity: 0.95
    type: "critical"
  - pattern: "(?i)reveal (system|base) prompt"
    severity: 0.95
    type: "critical"
  - pattern: "(?i)-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----"
    severity: 0.95
    type: "critical"
  - pattern: "(?i)Bearer [A-Za-z0-9_\\-\\.]{20,}"
    severity: 0.95
    type: "critical"
  - pattern: "sk-[A-Za-z0-9]{32,}"
    severity: 0.95
    type: "critical"

sensitive_patterns:
  - pattern: "(?i)password"
    severity: 0.60
    type: "sensitive"
  - pattern: "(?i)secret"
    severity: 0.60
    type: "sensitive"
  - pattern: "(?i)api[_-]?key"
    severity: 0.60
    type: "sensitive"
  - pattern: "(?i)token"
    severity: 0.60
    type: "sensitive"
  - pattern: "(?i)ssh-rsa"
    severity: 0.60
    type: "sensitive"

warning_patterns:
  - pattern: "(?i)confidential"
    severity: 0.30
    type: "warning"
  - pattern: "(?i)internal use only"
    severity: 0.30
    type: "warning"
  - pattern: "(?i)do not share"
    severity: 0.30
    type: "warning"
''')

write_file("src/engines/bhishma/engine.py", '''\
"""
Rule engine (regex/keyword) with YAML configuration.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, List

class Bhishma:
    def __init__(self):
        # Load rules from configs/bhishma_rules.yaml
        self.rules = {"critical": [], "sensitive": [], "warning": []}
        rules_path = Path(__file__).parent / "rules.yaml"
        if rules_path.exists():
            with open(rules_path) as f:
                data = yaml.safe_load(f)
                self.rules = {
                    "critical": data.get("critical_patterns", []),
                    "sensitive": data.get("sensitive_patterns", []),
                    "warning": data.get("warning_patterns", [])
                }

    def run(self, request, hanuman_result) -> Dict[str, Any]:
        """
        Evaluate rules against normalized text.
        Returns:
        - engine: "bhishma"
        - score: float 0-1
        - matched_patterns: list of dicts with pattern, severity, type
        """
        text = request.normalized_text if hasattr(request, 'normalized_text') else request.content
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')

        matched = []
        highest_score = 0.0

        # Check critical patterns first (highest impact)
        for pattern_info in self.rules.get("critical", []):
            if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                matched.append(pattern_info)
                highest_score = max(highest_score, pattern_info["severity"])

        # If no critical, check sensitive
        if not matched:
            for pattern_info in self.rules.get("sensitive", []):
                if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                    matched.append(pattern_info)
                    highest_score = max(highest_score, pattern_info["severity"])

        # If still no match, check warning
        if not matched:
            for pattern_info in self.rules.get("warning", []):
                if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                    matched.append(pattern_info)
                    highest_score = max(highest_score, pattern_info["severity"])

        # If no match, default score 0.1 (benign)
        if not matched:
            highest_score = 0.1

        return {
            "engine": "bhishma",
            "score": round(highest_score, 2),
            "matched_patterns": matched,
            "reason": f"Matched {len(matched)} pattern(s)"
        }
''')

# ----------------------------------------------------------------------
# 4. Yudhishthira Policy Override
write_file("src/engines/yudhishthira/engine.py", '''\
"""
Policy/tenant engine with simple overrides.
"""

from typing import Dict, Any

class Yudhishthira:
    def __init__(self):
        # For Phase 1, we'll use a simple tenant config from env or config
        self.tenant_policies = {
            "default": {"mode": "strict", "block_threshold": 0.7},
            "test": {"mode": "permissive", "block_threshold": 0.9},
        }

    def run(self, request, bhishma_result) -> Dict[str, Any]:
        """
        Apply tenant-specific policies to adjust score and add labels.
        Returns:
        - engine: "yudhishthira"
        - score: float (adjusted)
        - labels: list
        - reason: string
        """
        tenant = request.tenant_id
        policy = self.tenant_policies.get(tenant, self.tenant_policies["default"])
        mode = policy["mode"]

        original_score = bhishma_result["score"]
        adjusted_score = original_score
        labels = []
        reason = "No policy override."

        # Critical patterns from Bhishma: force block
        # (if any critical pattern matched, we already have high score)
        critical_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "critical"]
        if critical_matches:
            adjusted_score = 0.95
            labels.append("critical_pattern_block")
            reason = "Critical pattern matched: forced block."

        # Sensitive data pattern handling
        sensitive_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "sensitive"]
        if sensitive_matches:
            if mode == "strict":
                adjusted_score = max(adjusted_score, 0.8)
                labels.append("strict_mode_override")
                reason = "Strict mode: sensitive data overrides."
            else:
                # In permissive, just add warning label
                labels.append("sensitive_data_warning")

        # Block threshold override
        if adjusted_score >= policy["block_threshold"]:
            labels.append("block_by_threshold")
            reason += f" Score above {policy['block_threshold']} triggers block."

        return {
            "engine": "yudhishthira",
            "score": round(adjusted_score, 2),
            "labels": labels,
            "reason": reason
        }
''')

# ----------------------------------------------------------------------
# 5. Audit DB Integration (models and service)
write_file("src/db/models.py", '''\
from sqlalchemy import Column, Integer, String, JSON, DateTime, Index
from datetime import datetime
from src.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    tenant_id = Column(String)
    user_id = Column(String)
    session_id = Column(String)
    input_type = Column(String)  # "text" or "file"
    decision = Column(String)
    final_score = Column(Integer)  # stored as integer 0-100
    engine_results = Column(JSON)
    trace = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
    )
''')

write_file("src/db/base.py", '''\
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from src.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()
''')

write_file("src/db/init_db.py", '''\
#!/usr/bin/env python
"""Initialize database tables."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.db.base import engine, Base
from src.db import models  # noqa: F401 (imports the models so Base knows them)

async def init_db():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
''')

write_file("src/services/audit_service.py", '''\
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import AuditLog

logger = logging.getLogger(__name__)

async def log_audit(db: AsyncSession, event_data: dict):
    """
    Write audit entry to JSONL file and database.
    """
    # Write to JSONL file (for quick debugging)
    log_path = Path("./logs/audit.jsonl")
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(event_data) + "\\n")

    # Write to database
    try:
        audit = AuditLog(
            event_id=event_data["event_id"],
            tenant_id=event_data["tenant_id"],
            user_id=event_data["user_id"],
            session_id=event_data["session_id"],
            input_type=event_data["input_type"],
            decision=event_data["decision"],
            final_score=event_data["final_score"],
            engine_results=event_data["engine_results"],
            trace=event_data["trace"],
            created_at=datetime.utcnow()
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log to DB: {e}")
        await db.rollback()
        # Fallback: log to console
        logger.warning("Audit log saved only to file, DB error.")
''')

# ----------------------------------------------------------------------
# 6. Update Scan Service to integrate all components
write_file("src/services/scan_service.py", '''\
import asyncio
from pathlib import Path
from src.core.models import ScanRequest, ScanResponse
from src.utils.file_extractors import extract_from_file
from src.engines.hanuman.engine import Hanuman
from src.engines.bhishma.engine import Bhishma
from src.engines.yudhishthira.engine import Yudhishthira
from src.engines.krishna.engine import Krishna
from src.engines.sanjaya.engine import Sanjaya
from src.services.audit_service import log_audit
from src.db.base import AsyncSessionLocal

async def scan_text(request: ScanRequest) -> ScanResponse:
    # Normalize: text is already text
    # Add a normalized_text attribute for engines that expect it
    request.normalized_text = request.content if isinstance(request.content, str) else request.content.decode('utf-8', errors='ignore')
    return await _run_pipeline(request)

async def scan_file(request: ScanRequest) -> ScanResponse:
    # Extract text from the file content
    # We need to write the file temporarily? For extraction, we use the bytes directly.
    # For PDF, we need a file path; we'll write to a temporary file.
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
    # Run engines sequentially
    hanuman_result = Hanuman().run(request)
    bhishma_result = Bhishma().run(request, hanuman_result)
    yudhishthira_result = Yudhishthira().run(request, bhishma_result)
    krishna_result = Krishna().run(request, yudhishthira_result)

    # Sanjaya builds the final response and returns it, but we'll also store audit
    sanjaya = Sanjaya()
    response = sanjaya.run(request, krishna_result)

    # Prepare audit data
    audit_data = {
        "event_id": request.event_id,
        "tenant_id": request.tenant_id,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "input_type": request.content_type,
        "decision": response.decision,
        "final_score": response.score,
        "engine_results": {
            "hanuman": hanuman_result,
            "bhishma": bhishma_result,
            "yudhishthira": yudhishthira_result,
            "krishna": krishna_result
        },
        "trace": {}
    }

    # Log asynchronously to avoid blocking response
    async with AsyncSessionLocal() as db:
        await log_audit(db, audit_data)

    return response
''')

# ----------------------------------------------------------------------
# 7. Update routes to pass the scan_service functions (they already do, but ensure imports)
# We'll rewrite them to include the necessary imports.
write_file("src/api/routes/scan_text.py", '''\
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

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
    internal_request = ScanRequest(
        content_type="text",
        content=request.text,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        session_id=request.session_id,
        source=request.source,
        event_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc)
    )

    result = await scan_text(internal_request)
    return result
''')

write_file("src/api/routes/scan_file.py", '''\
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional
import uuid
from datetime import datetime, timezone

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
        timestamp=datetime.now(timezone.utc)
    )

    result = await scan_file(internal_request)
    return result
''')

# ----------------------------------------------------------------------
# 8. Update main.py to ensure routes are included (already done by scaffold, but we'll verify)
# Ensure main.py includes the routers (it should already, but let's write it clean)
write_file("src/api/main.py", '''\
from fastapi import FastAPI
from src.api.routes import scan_text, scan_file

app = FastAPI(title="Garuda Local")

app.include_router(scan_text.router)
app.include_router(scan_file.router)

@app.get("/v1/health")
async def health():
    return {"status": "ok"}
''')

# ----------------------------------------------------------------------
print("✅ Phase 1 logic implemented successfully.")
print("Now run:")
print("  ./scripts/init_db.sh  # to create database tables")
print("  ./scripts/run_dev.sh   # to start server")
print("  ./scripts/run_tests.sh # to run tests")
