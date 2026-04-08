from fastapi import FastAPI
from src.api.routes import scan_text, scan_file, auth, audit, overrides
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.admin import router as admin_router
from src.api.routes.reports import router as reports_router
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes.auth import router as auth_router
from src.api.routes.users import router as users_router   # new file
from src.api.routes.alerts import router as alerts_router # new file
from src.api.routes.websocket import router as ws_router  # new file

app = FastAPI(title="Garuda Local")

app.include_router(auth_router)       # /auth/login, /auth/refresh, /auth/me, /auth/logout
app.include_router(users_router)      # /v1/admin/users
app.include_router(alerts_router)     # /v1/alerts
app.include_router(ws_router)         # /ws/live  (WebSocket)

app.include_router(scan_text.router)
app.include_router(scan_file.router)
app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(overrides.router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.116.155:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # Allows Authorization, Content-Type, etc.
)

@app.on_event("startup")
async def startup_integrity_check():
    from src.protection.integrity import verify_signed_artifacts
    verify_signed_artifacts()
    from src.core.fallback import fallback
    import logging
    logger = logging.getLogger(__name__)
    if not fallback.check_integrity_on_startup():
        logger.critical("Integrity check failed - Garuda may be compromised")
        fallback.enable_safe_mode("Integrity check failed")
    # Phase 5: safe mode activated on integrity failure



@app.get("/health")
async def health():
    return {"status": "ok"}