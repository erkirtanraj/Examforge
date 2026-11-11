"""Opt-in FastAPI health router for the staged MySQL runtime."""
from fastapi import APIRouter, HTTPException
from .database import DatabaseRuntime

def build_mysql_health_router(runtime: DatabaseRuntime) -> APIRouter:
    router = APIRouter(tags=["database-health"])

    @router.get("/health/mysql")
    async def mysql_health() -> dict[str, str]:
        try:
            await runtime.ping()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="MySQL unavailable") from exc
        return {"status": "ok", "database": "mysql"}

    return router
