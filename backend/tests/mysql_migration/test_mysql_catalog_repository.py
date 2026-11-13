from datetime import datetime
from types import SimpleNamespace

from mysql_persistence.catalog import CatalogRepository
from mysql_persistence.models import Question


def test_question_model_tracks_import_batch_for_undo():
    assert "import_batch" in Question.__table__.columns
    assert Question.__table__.c.import_batch.nullable is True


def test_question_serializer_preserves_legacy_api_shape():
    row = SimpleNamespace(
        id="q-1", text="Question?", text_hi="प्रश्न?", question_type="mcq_single",
        correct_answers=["B"], explanation="Because", explanation_hi="क्योंकि",
        subject_id="sub-1", category_id="cat-1", difficulty="easy", language="hi",
        positive_marks=2.0, negative_marks=0.5, image_url=None, created_by="teacher-1",
        created_at=datetime(2026, 1, 2, 3, 4, 5), import_batch="batch-1",
    )
    options = [
        SimpleNamespace(option_key="A", text="First", text_hi="पहला"),
        SimpleNamespace(option_key="B", text="Second", text_hi="दूसरा"),
    ]

    result = CatalogRepository._question(row, options)

    assert result["type"] == "mcq_single"
    assert result["correct"] == ["B"]
    assert result["options"] == [
        {"key": "A", "text": "First", "text_hi": "पहला"},
        {"key": "B", "text": "Second", "text_hi": "दूसरा"},
    ]
    assert result["import_batch"] == "batch-1"
    assert result["created_at"] == "2026-01-02T03:04:05+00:00"
