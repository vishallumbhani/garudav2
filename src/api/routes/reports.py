from fastapi import APIRouter, HTTPException, Depends, Response
from datetime import datetime
from src.services.report_service import export_incidents_csv, get_incident_summary
from src.auth.dependencies import get_current_user

router = APIRouter(prefix="/v1/reports", tags=["reports"])

@router.get("/incidents/csv")
async def incidents_csv(
    start_date: str,
    end_date: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    csv_data = await export_incidents_csv(start_date, end_date)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=incidents_{start_date}_to_{end_date}.csv"}
    )

@router.get("/incidents/summary")
async def incidents_summary(
    start_date: str,
    end_date: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    return await get_incident_summary(start_date, end_date)