"""FastAPI routes for health and readiness."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.v1.dependencies.settings import get_health_service

router = APIRouter(tags=["operations"])


@router.get("/health")
def health_endpoint(health_service=Depends(get_health_service)) -> JSONResponse:
    report = health_service.check_health()
    status_code = 200 if report["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=report)


@router.get("/ready")
def ready_endpoint(health_service=Depends(get_health_service)) -> JSONResponse:
    report = health_service.check_ready()
    status_code = 200 if report["ready"] else 503
    return JSONResponse(status_code=status_code, content=report)
