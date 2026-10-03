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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

register_exception_handlers(app)

app.include_router(auth_router, prefix=settings.api_v1_prefix)


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