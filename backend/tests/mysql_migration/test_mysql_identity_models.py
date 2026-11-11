import sqlalchemy as sa

from mysql_persistence.models import Base, PasswordResetToken, User


def test_identity_tables_are_registered_in_metadata():
    assert User.__tablename__ == "users"
    assert PasswordResetToken.__tablename__ == "password_reset_tokens"
    assert {"users", "password_reset_tokens"} <= set(Base.metadata.tables)


def test_user_model_preserves_api_identity_fields():
    columns = User.__table__.columns
    assert columns["id"].type.length == 36
    assert columns["email"].type.length == 320
    assert columns["password_hash"].nullable is True
    assert columns["tokens_valid_after"].type.__class__ is sa.BigInteger
    assert columns["role"].server_default is not None
    assert columns["status"].server_default is not None


def test_user_model_enforces_roles_and_account_states():
    checks = {constraint.name: str(constraint.sqltext) for constraint in User.__table__.constraints if isinstance(constraint, sa.CheckConstraint)}
    assert "valid_role" in checks
    assert "super_admin" in checks["valid_role"]
    assert "support" in checks["valid_role"]
    assert "valid_status" in checks
    assert "valid_auth_provider" in checks


def test_user_email_is_unique():
    uniques = {constraint.name for constraint in User.__table__.constraints if isinstance(constraint, sa.UniqueConstraint)}
    assert "uq_users_email" in uniques


def test_password_reset_token_is_unique_and_cascades_with_user():
    columns = PasswordResetToken.__table__.columns
    assert columns["token_hash"].type.length == 64
    assert columns["used"].nullable is False
    fk = next(iter(columns["user_id"].foreign_keys))
    assert fk.target_fullname == "users.id"
    assert fk.ondelete == "CASCADE"
    uniques = {constraint.name for constraint in PasswordResetToken.__table__.constraints if isinstance(constraint, sa.UniqueConstraint)}
    assert "uq_password_reset_tokens_token_hash" in uniques
