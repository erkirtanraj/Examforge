"""SQLAlchemy models for the first normalized cPanel/MySQL migration slice.

These models are intentionally not imported by server.py yet. The live API still uses
Mongo query/update semantics. Do not switch traffic until route conversion and regression
tests are complete.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "ef_users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[str | None] = mapped_column(String(32), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    tokens_valid_after: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class PasswordResetToken(Base):
    __tablename__ = "ef_password_reset_tokens"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Setting(Base):
    __tablename__ = "ef_settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class Category(Base):
    __tablename__ = "ef_categories"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), index=True)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool | None] = mapped_column(Boolean)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class Subject(Base):
    __tablename__ = "ef_subjects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_id: Mapped[str | None] = mapped_column(String(64), index=True)
    name: Mapped[str | None] = mapped_column(String(255), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class Question(Base):
    __tablename__ = "ef_questions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_id: Mapped[str | None] = mapped_column(String(64), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(64), index=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), index=True)
    question_type: Mapped[str | None] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class TestSeries(Base):
    __tablename__ = "ef_test_series"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), index=True)
    is_published: Mapped[bool | None] = mapped_column(Boolean, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class ExamTest(Base):
    __tablename__ = "ef_tests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    series_id: Mapped[str | None] = mapped_column(String(64), index=True)
    is_published: Mapped[bool | None] = mapped_column(Boolean, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class TestAttempt(Base):
    __tablename__ = "ef_test_attempts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    test_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str | None] = mapped_column(String(32), index=True)
    score: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class TestResult(Base):
    __tablename__ = "ef_test_results"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    test_id: Mapped[str] = mapped_column(String(64), index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(64), index=True)
    score: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)


Index("ix_ef_attempt_user_test_created", TestAttempt.user_id, TestAttempt.test_id, TestAttempt.created_at)
Index("ix_ef_result_user_test_created", TestResult.user_id, TestResult.test_id, TestResult.created_at)
