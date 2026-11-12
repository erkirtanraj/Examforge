"""M3 catalog and content relational schema.

Revision ID: 0003_m3_catalog_content
Revises: 0002_m2_identity_authz
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_m3_catalog_content"
down_revision: Union[str, None] = "0002_m2_identity_authz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("icon", sa.String(120), server_default="GraduationCap", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_categories_slug"))
    op.create_index("ix_categories_active_position", "categories", ["is_active", "position"])

    op.create_table("subjects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.UniqueConstraint("category_id", "slug", name="uq_subjects_category_slug"))
    op.create_index("ix_subjects_category_active_position", "subjects", ["category_id", "is_active", "position"])

    op.create_table("questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hi", sa.Text(), nullable=True),
        sa.Column("question_type", sa.String(24), server_default="mcq_single", nullable=False),
        sa.Column("correct_answers", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("explanation_hi", sa.Text(), nullable=True),
        sa.Column("subject_id", sa.String(36), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("difficulty", sa.String(12), server_default="medium", nullable=False),
        sa.Column("language", sa.String(12), server_default="en", nullable=False),
        sa.Column("positive_marks", sa.Float(), server_default="1", nullable=False),
        sa.Column("negative_marks", sa.Float(), server_default="0", nullable=False),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("question_type IN ('mcq_single', 'mcq_multi', 'true_false', 'numerical')", name="ck_questions_valid_question_type"),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_questions_valid_difficulty"))
    op.create_index("ix_questions_subject_difficulty", "questions", ["subject_id", "difficulty"])
    op.create_index("ix_questions_category_created", "questions", ["category_id", "created_at"])
    op.create_index("ix_questions_status_created", "questions", ["status", "created_at"])

    op.create_table("question_options",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_key", sa.String(8), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hi", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("question_id", "option_key", name="uq_question_options_question_key"))

    op.create_table("test_series",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("thumbnail", sa.String(2048), nullable=True),
        sa.Column("language", sa.String(12), server_default="en", nullable=False),
        sa.Column("is_free", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("price", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("validity_days", sa.Integer(), server_default="365", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("ix_test_series_published_position", "test_series", ["is_published", "position"])

    op.create_table("tests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("series_id", sa.String(36), sa.ForeignKey("test_series.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column("total_marks", sa.Float(), nullable=True),
        sa.Column("passing_marks", sa.Float(), nullable=True),
        sa.Column("instructions", sa.Text(), server_default="", nullable=False),
        sa.Column("sectional_timing", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("live_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_window_minutes", sa.Integer(), server_default="120", nullable=False),
        sa.Column("allow_pause", sa.Boolean(), server_default=sa.text("1"), nullable=False))
    op.create_index("ix_tests_series_published", "tests", ["series_id", "is_published"])

    op.create_table("test_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("test_id", sa.String(36), sa.ForeignKey("tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("positive_marks", sa.Float(), nullable=True),
        sa.Column("negative_marks", sa.Float(), nullable=True),
        sa.Column("language", sa.String(12), server_default="bilingual", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("test_id", "position", name="uq_test_sections_test_position"))

    op.create_table("test_section_questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("section_id", sa.String(36), sa.ForeignKey("test_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("section_id", "question_id", name="uq_test_section_questions_pair"))

    op.create_table("courses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("thumbnail", sa.String(2048), nullable=True),
        sa.Column("is_free", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("price", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("certificate_enabled", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False))
    op.create_index("ix_courses_published_position", "courses", ["is_published", "position"])

    op.create_table("course_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("course_id", "position", name="uq_course_sections_course_position"))

    op.create_table("lessons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("section_id", sa.String(36), sa.ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("content_type", sa.String(12), server_default="video", nullable=False),
        sa.Column("content_url", sa.String(2048), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("section_id", "position", name="uq_lessons_section_position"))

    op.create_table("study_materials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("file_url", sa.String(2048), nullable=True),
        sa.Column("thumbnail", sa.String(2048), nullable=True),
        sa.Column("is_free", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("ix_study_materials_category_created", "study_materials", ["category_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_study_materials_category_created", table_name="study_materials")
    op.drop_table("study_materials")
    op.drop_table("lessons")
    op.drop_table("course_sections")
    op.drop_index("ix_courses_published_position", table_name="courses")
    op.drop_table("courses")
    op.drop_table("test_section_questions")
    op.drop_table("test_sections")
    op.drop_index("ix_tests_series_published", table_name="tests")
    op.drop_table("tests")
    op.drop_index("ix_test_series_published_position", table_name="test_series")
    op.drop_table("test_series")
    op.drop_table("question_options")
    op.drop_index("ix_questions_status_created", table_name="questions")
    op.drop_index("ix_questions_category_created", table_name="questions")
    op.drop_index("ix_questions_subject_difficulty", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_subjects_category_active_position", table_name="subjects")
    op.drop_table("subjects")
    op.drop_index("ix_categories_active_position", table_name="categories")
    op.drop_table("categories")
