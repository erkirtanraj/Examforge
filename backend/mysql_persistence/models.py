"""Declarative SQLAlchemy models and deterministic constraint naming conventions."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Float,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    text as sql_text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class User(Base):
    """Identity record preserving the existing API's string UUID and role fields.

    Datetimes are stored as UTC values. MySQL DATETIME does not retain timezone
    metadata, so persistence services must normalize values to/from UTC.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint(
            "role IN ('super_admin', 'admin', 'teacher', 'student', 'support')",
            name="valid_role",
        ),
        CheckConstraint("status IN ('active', 'suspended')", name="valid_status"),
        CheckConstraint("auth_provider IN ('email', 'google')", name="valid_auth_provider"),
        Index("ix_users_role_status", "role", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=sql_text("'student'"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=sql_text("'active'"))
    auth_provider: Mapped[str] = mapped_column(String(20), nullable=False, server_default=sql_text("'email'"))
    phone: Mapped[str] = mapped_column(String(20), nullable=False, server_default=sql_text("''"))
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tokens_valid_after: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=sql_text("0"))
    password_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class PasswordResetToken(Base):
    """Hashed, one-time password reset token with expiry and user ownership."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
        Index("ix_password_reset_tokens_user_created", "user_id", "created_at"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_categories_slug"),
        Index("ix_categories_active_position", "is_active", "position"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(120), nullable=False, server_default=sql_text("'GraduationCap'"))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("category_id", "slug", name="uq_subjects_category_slug"),
        Index("ix_subjects_category_active_position", "category_id", "is_active", "position"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("question_type IN ('mcq_single', 'mcq_multi', 'true_false', 'numerical')", name="valid_question_type"),
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="valid_difficulty"),
        Index("ix_questions_subject_difficulty", "subject_id", "difficulty"),
        Index("ix_questions_category_created", "category_id", "created_at"),
        Index("ix_questions_status_created", "status", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_type: Mapped[str] = mapped_column(String(24), nullable=False, server_default=sql_text("'mcq_single'"))
    correct_answers: Mapped[list] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_id: Mapped[str | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(12), nullable=False, server_default=sql_text("'medium'"))
    language: Mapped[str] = mapped_column(String(12), nullable=False, server_default=sql_text("'en'"))
    positive_marks: Mapped[float] = mapped_column(Float, nullable=False, server_default=sql_text("1"))
    negative_marks: Mapped[float] = mapped_column(Float, nullable=False, server_default=sql_text("0"))
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=sql_text("'active'"))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    import_batch: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (UniqueConstraint("question_id", "option_key", name="uq_question_options_question_key"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    option_key: Mapped[str] = mapped_column(String(8), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))


class TestSeries(Base):
    __test__ = False  # Prevent pytest from treating this ORM model as a test class.
    __tablename__ = "test_series"
    __table_args__ = (Index("ix_test_series_published_position", "is_published", "position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    language: Mapped[str] = mapped_column(String(12), nullable=False, server_default=sql_text("'en'"))
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("1"))
    price: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=sql_text("0"))
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("365"))
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("0"))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))


class ExamTest(Base):
    __tablename__ = "tests"
    __table_args__ = (Index("ix_tests_series_published", "series_id", "is_published"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    series_id: Mapped[str] = mapped_column(ForeignKey("test_series.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("60"))
    total_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    passing_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    sectional_timing: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("0"))
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("0"))
    live_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live_window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("120"))
    allow_pause: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("1"))


class TestSection(Base):
    __test__ = False  # Prevent pytest from treating this ORM model as a test class.
    __tablename__ = "test_sections"
    __table_args__ = (UniqueConstraint("test_id", "position", name="uq_test_sections_test_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    test_id: Mapped[str] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positive_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    negative_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str] = mapped_column(String(12), nullable=False, server_default=sql_text("'bilingual'"))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))


class TestSectionQuestion(Base):
    __test__ = False  # Prevent pytest from treating this ORM model as a test class.
    __tablename__ = "test_section_questions"
    __table_args__ = (UniqueConstraint("section_id", "question_id", name="uq_test_section_questions_pair"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    section_id: Mapped[str] = mapped_column(ForeignKey("test_sections.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (Index("ix_courses_published_position", "is_published", "position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("1"))
    price: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=sql_text("0"))
    certificate_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("0"))
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("0"))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))


class CourseSection(Base):
    __tablename__ = "course_sections"
    __table_args__ = (UniqueConstraint("course_id", "position", name="uq_course_sections_course_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("section_id", "position", name="uq_lessons_section_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    section_id: Mapped[str] = mapped_column(ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content_type: Mapped[str] = mapped_column(String(12), nullable=False, server_default=sql_text("'video'"))
    content_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))


class StudyMaterial(Base):
    __tablename__ = "study_materials"
    __table_args__ = (Index("ix_study_materials_category_created", "category_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("1"))
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sql_text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=sql_text("CURRENT_TIMESTAMP"))
