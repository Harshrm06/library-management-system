"""FastAPI application entry point.

Run locally with::

    uvicorn app.main:app --reload

from the ``backend`` directory.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.auth_middleware import AuthMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.book_routes import router as book_router
from app.routes.borrowing_routes import router as borrowing_router
from app.utils.exceptions import register_exception_handlers

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "REST API for the Library Management System: authentication, book "
        "catalog, borrowing and administration."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware registration order is the reverse of how it reads.
#
# `add_middleware` *prepends*, so the LAST call is the OUTERMOST layer and is the
# one that sees a request first. CORSMiddleware therefore has to be added LAST in
# order to be outermost. When it is added first (as it used to be here) it ends up
# nested inside AuthMiddleware, and because AuthMiddleware answered preflights
# itself without calling the inner app, CORS headers were never attached: the
# browser saw a 200 with no `Access-Control-Allow-Origin` and blocked the request.
app.add_middleware(AuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    # Configurable rather than hardcoded, so the dev origin can be corrected
    # without a code change. `*` is kept as the fallback default for local work.
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(book_router)
app.include_router(borrowing_router)


@app.get("/health", tags=["System"], summary="Service health check")
def health() -> Dict[str, Any]:
    """Report service liveness.

    Returns:
        dict: Service name, version and status.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["System"], summary="Service metadata")
def root() -> Dict[str, Any]:
    """Return basic API metadata.

    Returns:
        dict: Service metadata and documentation links.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.api_v1_prefix,
    }