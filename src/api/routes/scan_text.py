from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from src.services.scan_service import scan_text
from src.core.models import ScanRequest, ScanResponse
from src.auth.dependencies import get_current_user

router = APIRouter()

class TextScanRequest(BaseModel):
    text: str
    tenant_id: str = "default"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: str = "api"

@router.post("/v1/scan/text", response_model=ScanResponse)
async def scan_text_endpoint(
    request: TextScanRequest,
    current_user: dict = Depends(get_current_user)
):
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