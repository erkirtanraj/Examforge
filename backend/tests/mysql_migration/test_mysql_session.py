import asyncio
from mysql_persistence.config import load_mysql_settings
from mysql_persistence.database import create_database_runtime

def test_runtime_builds_async_engine_without_connecting():
    settings = load_mysql_settings({"MYSQL_HOST":"127.0.0.1","MYSQL_USER":"examforge_app","MYSQL_PASSWORD":"local-only","MYSQL_DATABASE":"examforge_test"})
    runtime = create_database_runtime(settings)
    try:
        assert runtime.engine.url.drivername == "mysql+asyncmy"
        assert runtime.sessions.kw["expire_on_commit"] is False
    finally:
        asyncio.run(runtime.dispose())
