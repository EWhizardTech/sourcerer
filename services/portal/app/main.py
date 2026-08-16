"""Portal service entry point.

Sourcerer as the face of the owner's Google Drive: Google sign-in, a
metadata-only catalog of the resource library, timed access requests/grants,
and access-checked in-app content viewing. No ingestion, no vector store —
this service never calls any paid API.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db.session import SessionLocal
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.catalog import router as catalog_router
from app.routes.content import router as content_router
from app.routes.requests import grants_router, me_router
from app.routes.requests import router as requests_router
from app.services.catalog_sync import periodic_sync_loop
from sourcerer_core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_task = asyncio.create_task(periodic_sync_loop(SessionLocal))
    yield
    sync_task.cancel()


app = FastAPI(
    title="Sourcerer Portal Service",
    description="Google Drive resource portal: auth, catalog, grants, viewing.",
    version="1.0.0",
    lifespan=lifespan,
)

_ALLOWED_ORIGINS = {
    origin.strip()
    for origin in settings.PORTAL_ALLOWED_ORIGINS.split(",")
    if origin.strip()
}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    """Reject state-changing cross-origin requests (belt-and-braces vs Lax).

    Fail closed: a non-safe method must carry an allowed Origin. Missing Origin
    is rejected too, so this stays a real defense if the cookie is ever set to
    SameSite=None. Browsers send Origin on all non-GET/HEAD requests, so the
    SPA's own credentialed POST/PATCH/DELETE calls are unaffected."""
    if request.method not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is None or origin not in _ALLOWED_ORIGINS:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    return await call_next(request)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(requests_router, prefix="/api/v1")
app.include_router(grants_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "portal"}
