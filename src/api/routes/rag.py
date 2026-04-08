from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.services.rag_protection import rag_protection

router = APIRouter(prefix="/v1/rag", tags=["RAG"])

class IngestRequest(BaseModel):
    doc_id: str
    text: str
    tenant_id: str = "default"

class IngestResponse(BaseModel):
    doc_id: str
    metadata: Dict[str, Any]

class ChunkRequest(BaseModel):
    doc_id: str
    chunk_index: int
    text: str

class FilterRequest(BaseModel):
    chunks: List[Dict[str, Any]]  # each chunk: {"text": ..., "sensitivity_label": ...} optional
    user_role: str
    tenant_id: str = "default"

class FilterResponse(BaseModel):
    filtered_chunks: List[Dict[str, Any]]
    stats: Dict[str, Any]

class OutputScanRequest(BaseModel):
    output_text: str

class OutputScanResponse(BaseModel):
    leakage_detected: bool
    leakage_types: List[str]
    risk_level: str
    recommended_action: str

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest):
    metadata = rag_protection.ingest_document(req.doc_id, req.text, req.tenant_id)
    return IngestResponse(doc_id=req.doc_id, metadata=metadata)

@router.post("/add_chunk")
async def add_chunk(req: ChunkRequest):
    rag_protection.add_chunk(req.doc_id, req.chunk_index, req.text)
    return {"status": "ok"}

@router.post("/filter", response_model=FilterResponse)
async def filter_chunks(req: FilterRequest):
    filtered, stats = rag_protection.filter_chunks(req.chunks, req.user_role, req.tenant_id)
    return FilterResponse(filtered_chunks=filtered, stats=stats)

@router.post("/scan_output", response_model=OutputScanResponse)
async def scan_output(req: OutputScanRequest):
    result = rag_protection.scan_output(req.output_text)
    return OutputScanResponse(**result)
