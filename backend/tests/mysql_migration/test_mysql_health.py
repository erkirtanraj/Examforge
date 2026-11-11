from fastapi import FastAPI
from fastapi.testclient import TestClient
from mysql_persistence.health import build_mysql_health_router

class HealthyRuntime:
    async def ping(self):
        return True

class UnhealthyRuntime:
    async def ping(self):
        raise RuntimeError("sensitive connection details")

def test_health_router_returns_database_status():
    app = FastAPI()
    app.include_router(build_mysql_health_router(HealthyRuntime()))
    response = TestClient(app).get("/health/mysql")
    assert response.status_code == 200
    assert response.json() == {"status":"ok","database":"mysql"}

def test_health_router_does_not_leak_database_error():
    app = FastAPI()
    app.include_router(build_mysql_health_router(UnhealthyRuntime()))
    response = TestClient(app).get("/health/mysql")
    assert response.status_code == 503
    assert response.json() == {"detail":"MySQL unavailable"}
    assert "sensitive" not in response.text
