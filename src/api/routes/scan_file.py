from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Optional
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.services.scan_service import scan_file
from src.core.models import ScanRequest, ScanResponse
from src.auth.dependencies import get_current_user

router = APIRouter()

@router.post("/v1/scan/file", response_model=ScanResponse)
async def scan_file_endpoint(
    file: UploadFile = File(...),
    tenant_id: str = "default",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    source: str = "api",
    current_user: dict = Depends(get_current_user)
):
    content = await file.read()
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