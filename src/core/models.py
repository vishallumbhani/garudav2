from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

class ScanRequest(BaseModel):
    content_type: str
    content: Union[str, bytes]
    filename: Optional[str] = None
    tenant_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: str
    event_id: str
    timestamp: datetime
    normalized_text: Optional[str] = None
    normalized_chunks: Optional[List[str]] = None
    file_metadata: Optional[Dict[str, Any]] = None

class ScanResponse(BaseModel):
    event_id: str
    decision: str
    score: int
    normalized_score: float
    details: Dict[str, Any]

class EngineResult(BaseModel):
    engine_name: str
    score: int
    details: Dict[str, Any]
