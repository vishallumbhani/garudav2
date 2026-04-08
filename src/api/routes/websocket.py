"""
src/api/routes/websocket.py
WebSocket endpoint for real-time scan and alert events.
Register in main.py: app.include_router(ws_router)
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from src.services.auth_service import decode_token, get_user_by_id

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        # tenant_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self._connections:
            self._connections[tenant_id] = set()
        self._connections[tenant_id].add(websocket)
        logger.info(f"WS connect: tenant={tenant_id}, total={self.total_connections}")

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self._connections:
            self._connections[tenant_id].discard(websocket)
            if not self._connections[tenant_id]:
                del self._connections[tenant_id]
        logger.info(f"WS disconnect: tenant={tenant_id}, total={self.total_connections}")

    @property
    def total_connections(self) -> int:
        return sum(len(v) for v in self._connections.values())

    async def broadcast(self, data: dict, tenant_id: str | None = None):
        """Broadcast to all connections for a tenant (or all tenants if None)."""
        message = json.dumps(data, default=str)
        targets: list[WebSocket] = []
        if tenant_id and tenant_id in self._connections:
            targets = list(self._connections[tenant_id])
        elif tenant_id is None:
            for sockets in self._connections.values():
                targets.extend(sockets)

        dead: list[tuple[WebSocket, str]] = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                # Find which tenant this ws belongs to and mark for removal
                for tid, sockets in self._connections.items():
                    if ws in sockets:
                        dead.append((ws, tid))
                        break

        for ws, tid in dead:
            self.disconnect(ws, tid)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def live_feed(
    websocket: WebSocket,
    token: str = Query(None),
):
    """
    WebSocket endpoint. Requires JWT token as query param: /ws/live?token=<access_token>
    Broadcasts scan decisions and alerts to the connected client.
    """
    # Auth
    tenant_id = "default"
    if token:
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            tenant_id = payload.get("tenant_id", "default")
        else:
            await websocket.close(code=4401)
            return

    await manager.connect(websocket, tenant_id)
    try:
        # Send initial connected message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        # Keep alive: receive messages (ping/pong) until disconnect
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive heartbeat
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, tenant_id)


async def push_scan_event(event_data: dict, tenant_id: str):
    """
    Call this from scan_service.py after each scan completes.
    Example:
        from src.api.routes.websocket import push_scan_event
        await push_scan_event({
            "type": "scan",
            "event_id": request.event_id,
            "decision": response.decision,
            "score": response.score,
            "timestamp": datetime.utcnow().isoformat(),
        }, request.tenant_id)
    """
    payload = {
        "type": "scan",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event_data,
    }
    await manager.broadcast(payload, tenant_id)


async def push_alert_event(alert_data: dict, tenant_id: str | None = None):
    """
    Call this from alert_service.py after creating an alert.
    """
    payload = {
        "type": "alert",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **alert_data,
    }
    await manager.broadcast(payload, tenant_id)
