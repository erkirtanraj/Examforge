import pytest
from mysql_persistence.config import MySQLConfigurationError, load_mysql_settings, require_approved_test_database

def valid_env(**overrides):
    values = {"MYSQL_HOST":"127.0.0.1","MYSQL_USER":"examforge_app","MYSQL_PASSWORD":"p@ss:/word?&","MYSQL_DATABASE":"examforge_test","MYSQL_PORT":"3306"}
    values.update(overrides)
    return values

def test_builds_async_mysql_url_and_encodes_credentials():
    settings = load_mysql_settings(valid_env())
    assert settings.url.drivername == "mysql+asyncmy"
    assert settings.url.password == "p@ss:/word?&"
    assert settings.database_name == "examforge_test"
    assert "p@ss" not in settings.safe_url()
    assert "***" in settings.safe_url()

def test_accepts_explicit_async_database_url():
    settings = load_mysql_settings({"DATABASE_URL":"mysql+asyncmy://examforge_app:secret@127.0.0.1:3306/examforge_test"})
    assert settings.database_name == "examforge_test"

def test_rejects_missing_configuration():
    with pytest.raises(MySQLConfigurationError, match="Missing MySQL configuration"):
        load_mysql_settings({})

@pytest.mark.parametrize("url", ["sqlite+aiosqlite:///./test.db", "mysql+pymysql://user:pass@localhost/examforge_test"])
def test_rejects_non_asyncmy_driver(url):
    with pytest.raises(MySQLConfigurationError, match="mysql"):
        load_mysql_settings({"DATABASE_URL":url})

def test_rejects_invalid_pool_values():
    with pytest.raises(MySQLConfigurationError, match="MYSQL_POOL_SIZE"):
        load_mysql_settings(valid_env(MYSQL_POOL_SIZE="0"))

def test_test_database_guard_accepts_only_exact_test_database():
    require_approved_test_database(load_mysql_settings(valid_env()))
    local = load_mysql_settings(valid_env(MYSQL_DATABASE="examforge_local"))
    with pytest.raises(MySQLConfigurationError, match="examforge_test"):
        require_approved_test_database(local)
