import sqlalchemy as sa

from mysql_persistence.models import (
    Base,
    Category,
    Subject,
    Question,
    QuestionOption,
    TestSeries,
    ExamTest,
    TestSection,
    TestSectionQuestion,
    Course,
    CourseSection,
    Lesson,
    StudyMaterial,
)


M3_TABLES = {
    "categories", "subjects", "questions", "question_options",
    "test_series", "tests", "test_sections", "test_section_questions",
    "courses", "course_sections", "lessons", "study_materials",
}


def test_m3_catalog_content_tables_are_registered():
    assert M3_TABLES <= set(Base.metadata.tables)


def test_category_and_subject_have_stable_catalog_keys():
    category_uniques = {
        c.name for c in Category.__table__.constraints
        if isinstance(c, sa.UniqueConstraint)
    }
    subject_uniques = {
        c.name for c in Subject.__table__.constraints
        if isinstance(c, sa.UniqueConstraint)
    }
    assert "uq_categories_slug" in category_uniques
    assert "uq_subjects_category_slug" in subject_uniques
    assert Subject.__table__.c.category_id.nullable is False


def test_question_schema_preserves_bilingual_content_and_answer_keys():
    columns = Question.__table__.columns
    assert columns["text"].type.__class__ is sa.Text
    assert columns["text_hi"].nullable is True
    assert columns["correct_answers"].type.__class__ is sa.JSON
    assert columns["subject_id"].nullable is True
    assert columns["category_id"].nullable is True
    assert columns["positive_marks"].nullable is False
    assert columns["negative_marks"].nullable is False
    checks = [str(c.sqltext) for c in Question.__table__.constraints if isinstance(c, sa.CheckConstraint)]
    assert any("mcq_single" in check and "numerical" in check for check in checks)
    assert any("easy" in check and "hard" in check for check in checks)


def test_question_options_are_unique_per_question_and_cascade():
    uniques = {
        c.name for c in QuestionOption.__table__.constraints
        if isinstance(c, sa.UniqueConstraint)
    }
    assert "uq_question_options_question_key" in uniques
    fk = next(iter(QuestionOption.__table__.c.question_id.foreign_keys))
    assert fk.target_fullname == "questions.id"
    assert fk.ondelete == "CASCADE"


def test_test_series_tests_sections_and_question_links_are_relational():
    assert TestSeries.__tablename__ == "test_series"
    assert ExamTest.__tablename__ == "tests"
    assert TestSection.__tablename__ == "test_sections"
    assert TestSectionQuestion.__tablename__ == "test_section_questions"
    assert next(iter(ExamTest.__table__.c.series_id.foreign_keys)).target_fullname == "test_series.id"
    assert next(iter(TestSection.__table__.c.test_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(TestSectionQuestion.__table__.c.question_id.foreign_keys)).ondelete == "RESTRICT"


def test_course_material_hierarchy_has_cascading_parent_relationships():
    assert Course.__tablename__ == "courses"
    assert CourseSection.__tablename__ == "course_sections"
    assert Lesson.__tablename__ == "lessons"
    assert StudyMaterial.__tablename__ == "study_materials"
    assert next(iter(CourseSection.__table__.c.course_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(Lesson.__table__.c.section_id.foreign_keys)).ondelete == "CASCADE"
    assert StudyMaterial.__table__.c.category_id.nullable is True


def test_catalog_indexes_cover_public_listing_and_question_bank_filters():
    index_names = {
        index.name
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }
    assert "ix_categories_active_position" in index_names
    assert "ix_questions_subject_difficulty" in index_names
    assert "ix_test_series_published_position" in index_names
    assert "ix_courses_published_position" in index_names
