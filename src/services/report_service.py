import csv
import json
from io import StringIO
from datetime import datetime
from sqlalchemy import text
from src.db.base import AsyncSessionLocal

async def export_incidents_csv(start_date: str, end_date: str) -> str:
    """Return CSV string of incidents (blocks/challenges) in date range."""
    # Convert string dates to datetime objects
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    # Set end date to end of day
    end_dt = end_dt.replace(hour=23, minute=59, second=59)
    
    query = text("""
        SELECT created_at, event_id, session_id, decision, final_score, policy_reason_codes, trace
        FROM audit_logs
        WHERE decision IN ('block', 'challenge')
          AND created_at BETWEEN :start AND :end
        ORDER BY created_at DESC
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"start": start_dt, "end": end_dt})
        rows = result.fetchall()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Event ID", "Session ID", "Decision", "Score", "Policy Hits", "Top Signal"])
    
    for row in rows:
        policy_hits = row[5] if isinstance(row[5], list) else json.loads(row[5]) if row[5] else []
        trace = row[6] if isinstance(row[6], dict) else json.loads(row[6]) if row[6] else {}
        top_signal = trace.get("hanuman_risk_hint") or trace.get("arjuna_label") or ""
        writer.writerow([
            row[0].isoformat(), row[1], row[2], row[3], row[4],
            ";".join(policy_hits), top_signal
        ])
    return output.getvalue()

async def get_incident_summary(start_date: str, end_date: str) -> dict:
    """Return counts of blocks and challenges in date range."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    end_dt = end_dt.replace(hour=23, minute=59, second=59)
    
    query = text("""
        SELECT decision, COUNT(*) as cnt
        FROM audit_logs
        WHERE decision IN ('block', 'challenge')
          AND created_at BETWEEN :start AND :end
        GROUP BY decision
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"start": start_dt, "end": end_dt})
        rows = result.fetchall()
    
    summary = {"block": 0, "challenge": 0}
    for row in rows:
        summary[row[0]] = row[1]
    return summary