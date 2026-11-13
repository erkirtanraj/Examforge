"""MySQL catalog repository for M3 catalog and question-bank operations."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select

from .models import Category, Subject, Question, QuestionOption, TestSectionQuestion


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else (value.isoformat() if value else None)


class CatalogRepository:
    """Owns catalog/question persistence; each mutation is an atomic transaction."""

    def __init__(self, sessions):
        self._sessions = sessions

    @staticmethod
    def _category(row):
        return {"id": row.id, "name": row.name, "slug": row.slug, "description": row.description,
                "icon": row.icon, "created_at": _iso(row.created_at)}

    @staticmethod
    def _subject(row):
        return {"id": row.id, "name": row.name, "slug": row.slug, "description": row.description,
                "category_id": row.category_id}

    @staticmethod
    def _question(row, options):
        return {
            "id": row.id, "text": row.text, "text_hi": row.text_hi,
            "type": row.question_type, "options": [
                {"key": item.option_key, "text": item.text, "text_hi": item.text_hi}
                for item in options
            ],
            "correct": row.correct_answers, "explanation": row.explanation,
            "explanation_hi": row.explanation_hi, "subject_id": row.subject_id,
            "category_id": row.category_id, "difficulty": row.difficulty,
            "language": row.language, "positive_marks": row.positive_marks,
            "negative_marks": row.negative_marks, "image_url": row.image_url,
            "created_by": row.created_by, "created_at": _iso(row.created_at),
            **({"import_batch": row.import_batch} if row.import_batch else {}),
        }

    async def list_categories(self):
        async with self._sessions() as session:
            rows = (await session.scalars(select(Category).where(Category.is_active.is_(True))
                    .order_by(Category.position, Category.name))).all()
            return [self._category(row) for row in rows]

    async def create_category(self, data: dict):
        row = Category(id=str(uuid4()), name=data["name"], slug=data["slug"],
                       description=data.get("description") or "", icon=data.get("icon") or "GraduationCap",
                       created_at=_now())
        async with self._sessions() as session, session.begin():
            session.add(row)
            await session.flush()
            return self._category(row)

    async def list_subjects(self, category_id=None):
        async with self._sessions() as session:
            stmt = select(Subject).where(Subject.is_active.is_(True))
            if category_id:
                stmt = stmt.where(Subject.category_id == category_id)
            rows = (await session.scalars(stmt.order_by(Subject.position, Subject.name))).all()
            return [self._subject(row) for row in rows]

    async def create_subject(self, data: dict):
        slug = data.get("slug") or "-".join(data["name"].strip().lower().split())
        row = Subject(id=str(uuid4()), category_id=data["category_id"], name=data["name"],
                      slug=slug, description=data.get("description") or "")
        async with self._sessions() as session, session.begin():
            session.add(row)
            await session.flush()
            return self._subject(row)

    async def list_questions(self, *, category_id=None, subject_id=None, difficulty=None, limit=2000):
        async with self._sessions() as session:
            stmt = select(Question).where(Question.status == "active")
            if category_id:
                stmt = stmt.where(Question.category_id == category_id)
            if subject_id:
                stmt = stmt.where(Question.subject_id == subject_id)
            if difficulty:
                stmt = stmt.where(Question.difficulty == difficulty)
            rows = (await session.scalars(stmt.order_by(Question.created_at.desc()).limit(max(1, min(limit, 5000))))).all()
            if not rows:
                return []
            ids = [row.id for row in rows]
            options = (await session.scalars(select(QuestionOption).where(
                QuestionOption.question_id.in_(ids)).order_by(QuestionOption.position, QuestionOption.id))).all()
            by_question = {}
            for option in options:
                by_question.setdefault(option.question_id, []).append(option)
            return [self._question(row, by_question.get(row.id, [])) for row in rows]

    async def create_question(self, data: dict, *, created_by: str):
        question_id = str(uuid4())
        row = Question(
            id=question_id, text=data["text"], text_hi=data.get("text_hi"),
            question_type=data.get("type", "mcq_single"), correct_answers=data["correct"],
            explanation=data.get("explanation") or "", explanation_hi=data.get("explanation_hi"),
            subject_id=data.get("subject_id"), category_id=data.get("category_id"),
            difficulty=data.get("difficulty", "medium"), language=data.get("language", "en"),
            positive_marks=data.get("positive_marks", 1.0), negative_marks=data.get("negative_marks", 0.0),
            image_url=data.get("image_url"), created_by=created_by, created_at=_now(),
        )
        async with self._sessions() as session, session.begin():
            session.add(row)
            session.add_all([QuestionOption(question_id=question_id, option_key=o["key"], text=o["text"],
                text_hi=o.get("text_hi"), position=i) for i, o in enumerate(data.get("options") or [])])
            await session.flush()
            options = (await session.scalars(select(QuestionOption).where(
                QuestionOption.question_id == question_id).order_by(QuestionOption.position))).all()
            return self._question(row, options)

    async def bulk_create_questions(self, items: list[dict], *, created_by: str):
        batch = str(uuid4())
        async with self._sessions() as session, session.begin():
            for data in items:
                qid = str(uuid4())
                row = Question(id=qid, text=data["text"], text_hi=data.get("text_hi"),
                    question_type=data.get("type", "mcq_single"), correct_answers=data["correct"],
                    explanation=data.get("explanation") or "", explanation_hi=data.get("explanation_hi"),
                    subject_id=data.get("subject_id"), category_id=data.get("category_id"),
                    difficulty=data.get("difficulty", "medium"), language=data.get("language", "en"),
                    positive_marks=data.get("positive_marks", 1.0), negative_marks=data.get("negative_marks", 0.0),
                    image_url=data.get("image_url"), created_by=created_by, created_at=_now(), import_batch=batch)
                session.add(row)
                session.add_all([QuestionOption(question_id=qid, option_key=o["key"], text=o["text"],
                    text_hi=o.get("text_hi"), position=i) for i, o in enumerate(data.get("options") or [])])
            await session.flush()
        return {"inserted": len(items), "batch_id": batch}

    async def undo_import(self, batch_id: str):
        async with self._sessions() as session, session.begin():
            ids = list((await session.scalars(select(Question.id).where(Question.import_batch == batch_id))).all())
            if not ids:
                return None
            await session.execute(delete(TestSectionQuestion).where(TestSectionQuestion.question_id.in_(ids)))
            await session.execute(delete(Question).where(Question.id.in_(ids)))
            return len(ids)
