import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
import os

logger = logging.getLogger(__name__)

# Optional webhook URL (set via env or config)
WEBHOOK_URL = os.environ.get("GARUDA_ALERT_WEBHOOK", None)

def send_alert(severity: int, title: str, description: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Send alert to log and optionally to webhook."""
    alert = {
        "timestamp": datetime.utcnow().isoformat(),
        "severity": severity,
        "title": title,
        "description": description,
        "context": context or {},
    }
    # Always log
    log_func = logger.critical if severity <= 2 else (logger.error if severity == 3 else logger.warning)
    log_func(f"ALERT: {json.dumps(alert)}")

    # Optional webhook
    if WEBHOOK_URL:
        try:
            import requests
            requests.post(WEBHOOK_URL, json=alert, timeout=2)
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")