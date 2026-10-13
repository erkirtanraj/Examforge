"""
Test Series + LMS Platform - FastAPI Backend
Secure, server-authoritative examination engine with autosave, scoring, Razorpay payments.
"""
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, uuid, logging, hashlib, hmac, jwt as pyjwt
import bcrypt
import razorpay

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALG = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "168"))
RZP_KEY = os.environ.get("RAZORPAY_KEY_ID", "")
RZP_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RZP_WEBHOOK = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
rzp_client = razorpay.Client(auth=(RZP_KEY, RZP_SECRET)) if RZP_KEY and RZP_SECRET else None

app = FastAPI(title="LMS Test Series API")
api = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lms")

# ========== Helpers ==========
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def gen_id() -> str:
    return str(uuid.uuid4())

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_pw(pw: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), h.encode())
    except Exception:
        return False

def make_token(user_id: str, role: str) -> str:
    payload = {
        "uid": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        data = pyjwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    user = await db.users.find_one({"id": data["uid"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user

def require_roles(*roles):
    async def _dep(user=Depends(get_current_user)):
        if user["role"] not in roles and user["role"] != "super_admin":
            raise HTTPException(403, "Insufficient permissions")
        return user
    return _dep

# ========== Models ==========
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[Literal["student", "teacher"]] = "student"

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class CategoryIn(BaseModel):
    name: str
    slug: str
    description: Optional[str] = ""
    icon: Optional[str] = "GraduationCap"

class SubjectIn(BaseModel):
    name: str
    category_id: str

class QuestionOption(BaseModel):
    key: str  # A, B, C, D
    text: str

class QuestionIn(BaseModel):
    text: str
    type: Literal["mcq_single", "mcq_multi", "true_false", "numerical"] = "mcq_single"
    options: List[QuestionOption] = []
    correct: List[str]  # list of correct keys / value
    explanation: Optional[str] = ""
    subject_id: Optional[str] = None
    category_id: Optional[str] = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    language: str = "en"
    positive_marks: float = 1.0
    negative_marks: float = 0.0
    image_url: Optional[str] = None

class TestSeriesIn(BaseModel):
    title: str
    description: str = ""
    category_id: Optional[str] = None
    thumbnail: Optional[str] = None
    language: str = "en"
    is_free: bool = True
    price: int = 0  # in paise
    validity_days: int = 365

class TestIn(BaseModel):
    series_id: str
    title: str
    duration_minutes: int = 60
    total_marks: Optional[float] = None
    passing_marks: Optional[float] = None
    instructions: Optional[str] = ""
    question_ids: List[str] = []
    is_published: bool = True

class CourseIn(BaseModel):
    title: str
    description: str = ""
    category_id: Optional[str] = None
    thumbnail: Optional[str] = None
    is_free: bool = True
    price: int = 0

class SectionIn(BaseModel):
    course_id: str
    title: str
    position: int = 0

class LessonIn(BaseModel):
    section_id: str
    title: str
    content_type: Literal["video", "text", "pdf"] = "video"
    content_url: Optional[str] = None
    text_content: Optional[str] = None
    position: int = 0
    duration_minutes: int = 0

class StudyMaterialIn(BaseModel):
    title: str
    description: str = ""
    category_id: Optional[str] = None
    file_url: Optional[str] = None
    is_free: bool = True
    price: int = 0

class AutosaveIn(BaseModel):
    answers: Dict[str, Any]  # question_id -> answer value
    marked_for_review: List[str] = []
    client_version: int = 0

class SubmitIn(BaseModel):
    answers: Dict[str, Any]
    marked_for_review: List[str] = []

class OrderIn(BaseModel):
    item_type: Literal["test_series", "course", "study_material"]
    item_id: str

class VerifyPaymentIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    order_id: str

# ========== Auth ==========
@api.post("/auth/register")
async def register(data: RegisterIn):
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    uid = gen_id()
    doc = {
        "id": uid,
        "name": data.name,
        "email": data.email.lower(),
        "password_hash": hash_pw(data.password),
        "role": data.role or "student",
        "created_at": now_iso(),
        "avatar_url": None,
    }
    await db.users.insert_one(doc)
    token = make_token(uid, doc["role"])
    return {"token": token, "user": {"id": uid, "name": doc["name"], "email": doc["email"], "role": doc["role"]}}

@api.post("/auth/login")
async def login(data: LoginIn):
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not verify_pw(data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = make_token(user["id"], user["role"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}}

@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user

# ========== Categories & Subjects ==========
@api.get("/categories")
async def list_categories():
    rows = await db.categories.find({}, {"_id": 0}).to_list(1000)
    return rows

@api.post("/categories")
async def create_category(data: CategoryIn, _=Depends(require_roles("admin"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_at": now_iso()}
    await db.categories.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/subjects")
async def list_subjects(category_id: Optional[str] = None):
    q = {"category_id": category_id} if category_id else {}
    return await db.subjects.find(q, {"_id": 0}).to_list(1000)

@api.post("/subjects")
async def create_subject(data: SubjectIn, _=Depends(require_roles("admin", "teacher"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_at": now_iso()}
    await db.subjects.insert_one(doc)
    doc.pop("_id", None)
    return doc

# ========== Questions ==========
@api.get("/questions")
async def list_questions(category_id: Optional[str] = None, subject_id: Optional[str] = None,
                         difficulty: Optional[str] = None, limit: int = 100,
                         _=Depends(require_roles("admin", "teacher"))):
    q = {}
    if category_id: q["category_id"] = category_id
    if subject_id: q["subject_id"] = subject_id
    if difficulty: q["difficulty"] = difficulty
    return await db.questions.find(q, {"_id": 0}).to_list(limit)

@api.post("/questions")
async def create_question(data: QuestionIn, user=Depends(require_roles("admin", "teacher"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_by": user["id"], "created_at": now_iso()}
    await db.questions.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.post("/questions/bulk")
async def bulk_questions(items: List[QuestionIn], user=Depends(require_roles("admin", "teacher"))):
    docs = [{"id": gen_id(), **q.model_dump(), "created_by": user["id"], "created_at": now_iso()} for q in items]
    if docs:
        await db.questions.insert_many(docs)
    return {"inserted": len(docs)}

# ========== Test Series & Tests ==========
@api.get("/test-series")
async def list_series(category_id: Optional[str] = None, is_free: Optional[bool] = None):
    q = {}
    if category_id: q["category_id"] = category_id
    if is_free is not None: q["is_free"] = is_free
    rows = await db.test_series.find(q, {"_id": 0}).to_list(500)
    for r in rows:
        r["tests_count"] = await db.tests.count_documents({"series_id": r["id"]})
    return rows

@api.get("/test-series/{series_id}")
async def get_series(series_id: str):
    s = await db.test_series.find_one({"id": series_id}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Not found")
    s["tests"] = await db.tests.find({"series_id": series_id}, {"_id": 0, "question_ids": 0}).to_list(500)
    return s

@api.post("/test-series")
async def create_series(data: TestSeriesIn, user=Depends(require_roles("admin", "teacher"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_by": user["id"], "created_at": now_iso(), "is_published": True}
    await db.test_series.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.post("/tests")
async def create_test(data: TestIn, user=Depends(require_roles("admin", "teacher"))):
    # Compute total marks from questions
    questions = await db.questions.find({"id": {"$in": data.question_ids}}, {"_id": 0}).to_list(1000)
    total = sum(q.get("positive_marks", 1.0) for q in questions)
    doc = {"id": gen_id(), **data.model_dump(), "total_marks": data.total_marks or total,
           "created_by": user["id"], "created_at": now_iso()}
    await db.tests.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/tests/{test_id}")
async def get_test(test_id: str, user=Depends(get_current_user)):
    t = await db.tests.find_one({"id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Not found")
    return t

# ========== Entitlement check ==========
async def has_access(user_id: str, item_type: str, item_id: str) -> bool:
    """Check if user has entitlement to this item."""
    # Admins have all access
    user = await db.users.find_one({"id": user_id}, {"role": 1})
    if user and user["role"] in ("admin", "super_admin"):
        return True
    # Check if series is free
    if item_type == "test_series":
        s = await db.test_series.find_one({"id": item_id})
        if s and s.get("is_free"):
            return True
    if item_type == "course":
        c = await db.courses.find_one({"id": item_id})
        if c and c.get("is_free"):
            return True
    # Check entitlements
    ent = await db.entitlements.find_one({
        "user_id": user_id,
        "item_type": item_type,
        "item_id": item_id,
        "$or": [{"expires_at": None}, {"expires_at": {"$gt": now_iso()}}],
    })
    return bool(ent)

# ========== Exam Engine ==========
@api.post("/tests/{test_id}/start")
async def start_attempt(test_id: str, user=Depends(get_current_user)):
    t = await db.tests.find_one({"id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Test not found")
    series = await db.test_series.find_one({"id": t["series_id"]}, {"_id": 0})
    if series and not await has_access(user["id"], "test_series", series["id"]):
        raise HTTPException(403, "Purchase required")
    # Reuse existing in-progress attempt
    existing = await db.test_attempts.find_one(
        {"user_id": user["id"], "test_id": test_id, "status": "in_progress"}, {"_id": 0}
    )
    if existing:
        return existing
    now_dt = datetime.now(timezone.utc)
    end_dt = now_dt + timedelta(minutes=t["duration_minutes"])
    attempt = {
        "id": gen_id(),
        "user_id": user["id"],
        "test_id": test_id,
        "series_id": t["series_id"],
        "started_at": now_dt.isoformat(),
        "ends_at": end_dt.isoformat(),
        "duration_minutes": t["duration_minutes"],
        "status": "in_progress",
        "answers": {},
        "marked_for_review": [],
        "version": 0,
        "question_ids": t["question_ids"],
    }
    await db.test_attempts.insert_one(attempt)
    attempt.pop("_id", None)
    return attempt

@api.get("/attempts/{attempt_id}")
async def get_attempt(attempt_id: str, user=Depends(get_current_user)):
    a = await db.test_attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not a or a["user_id"] != user["id"]:
        raise HTTPException(404, "Attempt not found")
    # Load questions (without correct answers)
    qs = await db.questions.find({"id": {"$in": a["question_ids"]}}, {"_id": 0, "correct": 0, "explanation": 0}).to_list(1000)
    qmap = {q["id"]: q for q in qs}
    a["questions"] = [qmap[qid] for qid in a["question_ids"] if qid in qmap]
    return a

@api.post("/attempts/{attempt_id}/autosave")
async def autosave(attempt_id: str, data: AutosaveIn, user=Depends(get_current_user)):
    a = await db.test_attempts.find_one({"id": attempt_id})
    if not a or a["user_id"] != user["id"]:
        raise HTTPException(404, "Attempt not found")
    if a["status"] != "in_progress":
        raise HTTPException(400, "Attempt not active")
    # Server-authoritative time check
    ends = datetime.fromisoformat(a["ends_at"])
    if datetime.now(timezone.utc) > ends:
        # Auto-submit on timeout
        await _finalize_attempt(a, data.answers, data.marked_for_review, auto=True)
        return {"status": "auto_submitted"}
    # Stale-write guard: only accept if newer version
    if data.client_version < a.get("version", 0):
        return {"status": "stale", "server_version": a.get("version", 0)}
    new_version = a.get("version", 0) + 1
    await db.test_attempts.update_one(
        {"id": attempt_id, "version": a.get("version", 0)},
        {"$set": {"answers": data.answers, "marked_for_review": data.marked_for_review,
                  "version": new_version, "last_saved_at": now_iso()}},
    )
    return {"status": "ok", "version": new_version}

async def _finalize_attempt(attempt: dict, answers: dict, marked: list, auto: bool = False):
    """Score and finalize attempt. Idempotent via unique attempt_id."""
    existing_result = await db.test_results.find_one({"attempt_id": attempt["id"]})
    if existing_result:
        return existing_result
    # Load questions with correct answers
    qs = await db.questions.find({"id": {"$in": attempt["question_ids"]}}).to_list(1000)
    score = 0.0
    total_marks = 0.0
    correct_count = 0
    wrong_count = 0
    unattempted = 0
    details = []
    for q in qs:
        total_marks += q.get("positive_marks", 1.0)
        qid = q["id"]
        ans = answers.get(qid)
        is_correct = False
        if ans is None or (isinstance(ans, list) and len(ans) == 0) or ans == "":
            unattempted += 1
            details.append({"qid": qid, "status": "unattempted", "awarded": 0})
            continue
        correct = q.get("correct", [])
        if q["type"] == "mcq_single" or q["type"] == "true_false":
            is_correct = (isinstance(ans, list) and ans and ans[0] == correct[0]) or (ans == correct[0] if correct else False)
        elif q["type"] == "mcq_multi":
            is_correct = isinstance(ans, list) and sorted(ans) == sorted(correct)
        elif q["type"] == "numerical":
            try:
                is_correct = abs(float(ans) - float(correct[0])) < 1e-6
            except Exception:
                is_correct = False
        if is_correct:
            awarded = q.get("positive_marks", 1.0)
            score += awarded
            correct_count += 1
            details.append({"qid": qid, "status": "correct", "awarded": awarded})
        else:
            neg = q.get("negative_marks", 0.0)
            score -= neg
            wrong_count += 1
            details.append({"qid": qid, "status": "wrong", "awarded": -neg})
    submitted_at = now_iso()
    # Update attempt transactionally (unique by id)
    update_res = await db.test_attempts.update_one(
        {"id": attempt["id"], "status": "in_progress"},
        {"$set": {"status": "submitted", "submitted_at": submitted_at,
                  "answers": answers, "marked_for_review": marked, "auto_submitted": auto}},
    )
    if update_res.matched_count == 0:
        # Already submitted
        existing = await db.test_results.find_one({"attempt_id": attempt["id"]}, {"_id": 0})
        if existing:
            return existing
    result = {
        "id": gen_id(),
        "attempt_id": attempt["id"],
        "user_id": attempt["user_id"],
        "test_id": attempt["test_id"],
        "series_id": attempt.get("series_id"),
        "score": round(score, 2),
        "total_marks": round(total_marks, 2),
        "correct": correct_count,
        "wrong": wrong_count,
        "unattempted": unattempted,
        "accuracy": round((correct_count / max(1, correct_count + wrong_count)) * 100, 2),
        "details": details,
        "created_at": submitted_at,
    }
    try:
        await db.test_results.insert_one(result)
    except Exception:
        existing = await db.test_results.find_one({"attempt_id": attempt["id"]}, {"_id": 0})
        if existing:
            return existing
        raise
    result.pop("_id", None)
    return result

@api.post("/attempts/{attempt_id}/submit")
async def submit_attempt(attempt_id: str, data: SubmitIn, user=Depends(get_current_user)):
    a = await db.test_attempts.find_one({"id": attempt_id})
    if not a or a["user_id"] != user["id"]:
        raise HTTPException(404, "Attempt not found")
    if a["status"] == "submitted":
        res = await db.test_results.find_one({"attempt_id": attempt_id}, {"_id": 0})
        return res
    result = await _finalize_attempt(a, data.answers, data.marked_for_review)
    result.pop("_id", None)
    return result

@api.get("/attempts/{attempt_id}/result")
async def get_result(attempt_id: str, user=Depends(get_current_user)):
    a = await db.test_attempts.find_one({"id": attempt_id})
    if not a or a["user_id"] != user["id"]:
        raise HTTPException(404, "Not found")
    res = await db.test_results.find_one({"attempt_id": attempt_id}, {"_id": 0})
    if not res:
        raise HTTPException(404, "Result not available yet")
    # Load full questions with answers for review
    qs = await db.questions.find({"id": {"$in": a["question_ids"]}}, {"_id": 0}).to_list(1000)
    res["questions"] = qs
    res["user_answers"] = a.get("answers", {})
    return res

@api.get("/my/attempts")
async def my_attempts(user=Depends(get_current_user)):
    rows = await db.test_attempts.find({"user_id": user["id"]}, {"_id": 0, "answers": 0, "question_ids": 0}).sort("started_at", -1).to_list(200)
    # Attach test titles
    test_ids = list({r["test_id"] for r in rows})
    tests = await db.tests.find({"id": {"$in": test_ids}}, {"_id": 0, "id": 1, "title": 1}).to_list(500)
    tmap = {t["id"]: t["title"] for t in tests}
    for r in rows:
        r["test_title"] = tmap.get(r["test_id"], "Test")
    return rows

# ========== Courses ==========
@api.get("/courses")
async def list_courses(category_id: Optional[str] = None):
    q = {"category_id": category_id} if category_id else {}
    return await db.courses.find(q, {"_id": 0}).to_list(500)

@api.get("/courses/{course_id}")
async def get_course(course_id: str):
    c = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Not found")
    sections = await db.course_sections.find({"course_id": course_id}, {"_id": 0}).sort("position", 1).to_list(200)
    for s in sections:
        s["lessons"] = await db.lessons.find({"section_id": s["id"]}, {"_id": 0}).sort("position", 1).to_list(200)
    c["sections"] = sections
    return c

@api.post("/courses")
async def create_course(data: CourseIn, user=Depends(require_roles("admin", "teacher"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_by": user["id"], "created_at": now_iso()}
    await db.courses.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.post("/sections")
async def create_section(data: SectionIn, _=Depends(require_roles("admin", "teacher"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_at": now_iso()}
    await db.course_sections.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.post("/lessons")
async def create_lesson(data: LessonIn, _=Depends(require_roles("admin", "teacher"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_at": now_iso()}
    await db.lessons.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.post("/lessons/{lesson_id}/complete")
async def complete_lesson(lesson_id: str, user=Depends(get_current_user)):
    await db.lesson_progress.update_one(
        {"user_id": user["id"], "lesson_id": lesson_id},
        {"$set": {"completed_at": now_iso()}},
        upsert=True,
    )
    return {"ok": True}

@api.get("/my/progress/{course_id}")
async def course_progress(course_id: str, user=Depends(get_current_user)):
    sections = await db.course_sections.find({"course_id": course_id}, {"_id": 0, "id": 1}).to_list(500)
    sec_ids = [s["id"] for s in sections]
    lessons = await db.lessons.find({"section_id": {"$in": sec_ids}}, {"_id": 0, "id": 1}).to_list(1000)
    total = len(lessons)
    lesson_ids = [l["id"] for l in lessons]
    done = await db.lesson_progress.count_documents({"user_id": user["id"], "lesson_id": {"$in": lesson_ids}})
    return {"total": total, "completed": done, "percent": round((done / total * 100) if total else 0, 1)}

# ========== Study Materials ==========
@api.get("/study-materials")
async def list_materials(category_id: Optional[str] = None):
    q = {"category_id": category_id} if category_id else {}
    return await db.study_materials.find(q, {"_id": 0}).to_list(500)

@api.post("/study-materials")
async def create_material(data: StudyMaterialIn, user=Depends(require_roles("admin", "teacher"))):
    doc = {"id": gen_id(), **data.model_dump(), "created_by": user["id"], "created_at": now_iso()}
    await db.study_materials.insert_one(doc)
    doc.pop("_id", None)
    return doc

# ========== Orders & Razorpay ==========
async def _get_item(item_type: str, item_id: str):
    coll_map = {"test_series": db.test_series, "course": db.courses, "study_material": db.study_materials}
    if item_type not in coll_map:
        raise HTTPException(400, "Invalid item type")
    item = await coll_map[item_type].find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Item not found")
    return item

@api.post("/orders")
async def create_order(data: OrderIn, user=Depends(get_current_user)):
    item = await _get_item(data.item_type, data.item_id)
    if item.get("is_free") or int(item.get("price", 0)) <= 0:
        # Grant free entitlement immediately
        oid = gen_id()
        order = {"id": oid, "user_id": user["id"], "item_type": data.item_type, "item_id": data.item_id,
                 "amount": 0, "currency": "INR", "status": "paid", "created_at": now_iso(),
                 "razorpay_order_id": None, "receipt": oid[:40]}
        await db.orders.insert_one(order)
        await _grant_entitlement(user["id"], data.item_type, data.item_id, order["id"])
        order.pop("_id", None)
        return order
    amount = int(item["price"])
    oid = gen_id()
    receipt = oid[:40]
    rzp_order = None
    if rzp_client:
        try:
            rzp_order = rzp_client.order.create({
                "amount": amount, "currency": "INR", "receipt": receipt, "payment_capture": 1,
                "notes": {"user_id": user["id"], "item_type": data.item_type, "item_id": data.item_id}
            })
        except Exception as e:
            log.error(f"Razorpay create failed: {e}")
            raise HTTPException(502, "Payment gateway unavailable")
    order = {"id": oid, "user_id": user["id"], "item_type": data.item_type, "item_id": data.item_id,
             "amount": amount, "currency": "INR", "status": "created", "created_at": now_iso(),
             "razorpay_order_id": rzp_order["id"] if rzp_order else None, "receipt": receipt,
             "item_title": item.get("title")}
    await db.orders.insert_one(order)
    order.pop("_id", None)
    return {**order, "razorpay_key": RZP_KEY, "demo_mode": not bool(rzp_client)}

async def _grant_entitlement(user_id: str, item_type: str, item_id: str, order_id: str):
    item = await _get_item(item_type, item_id)
    validity = item.get("validity_days", 365)
    expires = (datetime.now(timezone.utc) + timedelta(days=validity)).isoformat() if validity else None
    doc = {"id": gen_id(), "user_id": user_id, "item_type": item_type, "item_id": item_id,
           "order_id": order_id, "granted_at": now_iso(), "expires_at": expires}
    # Idempotent: skip if exists
    exists = await db.entitlements.find_one({"user_id": user_id, "item_type": item_type, "item_id": item_id, "order_id": order_id})
    if not exists:
        await db.entitlements.insert_one(doc)

@api.post("/orders/verify")
async def verify_payment(data: VerifyPaymentIn, user=Depends(get_current_user)):
    order = await db.orders.find_one({"id": data.order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] == "paid":
        return {"status": "already_paid"}
    # Verify signature
    if rzp_client:
        try:
            rzp_client.utility.verify_payment_signature({
                "razorpay_order_id": data.razorpay_order_id,
                "razorpay_payment_id": data.razorpay_payment_id,
                "razorpay_signature": data.razorpay_signature,
            })
        except Exception:
            raise HTTPException(400, "Invalid payment signature")
    await db.orders.update_one(
        {"id": order["id"]},
        {"$set": {"status": "paid", "razorpay_payment_id": data.razorpay_payment_id, "paid_at": now_iso()}},
    )
    await _grant_entitlement(user["id"], order["item_type"], order["item_id"], order["id"])
    return {"status": "paid"}

@api.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if RZP_WEBHOOK:
        expected = hmac.new(RZP_WEBHOOK.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(400, "Invalid signature")
    try:
        payload = (await request.json())
    except Exception:
        return {"ok": True}
    event = payload.get("event", "")
    if event == "payment.captured":
        rp = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = rp.get("notes", {}).get("user_id")  # not reliable; we use order_id lookup
        rp_order_id = rp.get("order_id")
        order = await db.orders.find_one({"razorpay_order_id": rp_order_id})
        if order and order["status"] != "paid":
            await db.orders.update_one({"id": order["id"]},
                {"$set": {"status": "paid", "razorpay_payment_id": rp.get("id"), "paid_at": now_iso()}})
            await _grant_entitlement(order["user_id"], order["item_type"], order["item_id"], order["id"])
    return {"ok": True}

@api.get("/my/orders")
async def my_orders(user=Depends(get_current_user)):
    return await db.orders.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)

@api.get("/my/entitlements")
async def my_entitlements(user=Depends(get_current_user)):
    ents = await db.entitlements.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    return ents

# ========== Student Dashboard ==========
@api.get("/my/dashboard")
async def student_dashboard(user=Depends(get_current_user)):
    attempts = await db.test_attempts.count_documents({"user_id": user["id"]})
    submitted = await db.test_attempts.count_documents({"user_id": user["id"], "status": "submitted"})
    results = await db.test_results.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    avg_accuracy = round(sum(r.get("accuracy", 0) for r in results) / max(1, len(results)), 2) if results else 0
    total_score = sum(r.get("score", 0) for r in results)
    ents = await db.entitlements.count_documents({"user_id": user["id"]})
    courses_enrolled = await db.entitlements.count_documents({"user_id": user["id"], "item_type": "course"})
    return {
        "attempts": attempts, "submitted": submitted, "avg_accuracy": avg_accuracy,
        "total_score": round(total_score, 2), "entitlements": ents, "courses_enrolled": courses_enrolled,
    }

# ========== Admin ==========
@api.get("/admin/stats")
async def admin_stats(_=Depends(require_roles("admin"))):
    return {
        "users": await db.users.count_documents({}),
        "questions": await db.questions.count_documents({}),
        "test_series": await db.test_series.count_documents({}),
        "tests": await db.tests.count_documents({}),
        "courses": await db.courses.count_documents({}),
        "attempts": await db.test_attempts.count_documents({}),
        "orders_paid": await db.orders.count_documents({"status": "paid"}),
        "revenue": sum([o.get("amount", 0) async for o in db.orders.find({"status": "paid"}, {"amount": 1})]),
    }

@api.get("/admin/users")
async def admin_users(_=Depends(require_roles("admin"))):
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)

@api.get("/admin/orders")
async def admin_orders(_=Depends(require_roles("admin"))):
    return await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)

# ========== Health ==========
@api.get("/")
async def root():
    return {"status": "ok", "service": "LMS Test Series API", "time": now_iso()}

# ========== Seed Data ==========
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.test_attempts.create_index([("user_id", 1), ("test_id", 1), ("status", 1)])
    await db.test_results.create_index("attempt_id", unique=True)
    await db.entitlements.create_index([("user_id", 1), ("item_type", 1), ("item_id", 1), ("order_id", 1)], unique=True)
    await db.orders.create_index("razorpay_order_id")
    # Seed admin + sample data if missing
    if not await db.users.find_one({"email": "admin@lms.com"}):
        await _seed_data()

async def _seed_data():
    log.info("Seeding sample data...")
    users = [
        {"id": gen_id(), "name": "Super Admin", "email": "admin@lms.com", "password_hash": hash_pw("admin123"),
         "role": "admin", "created_at": now_iso()},
        {"id": gen_id(), "name": "Prof. Mehta", "email": "teacher@lms.com", "password_hash": hash_pw("teacher123"),
         "role": "teacher", "created_at": now_iso()},
        {"id": gen_id(), "name": "Riya Student", "email": "student@lms.com", "password_hash": hash_pw("student123"),
         "role": "student", "created_at": now_iso()},
    ]
    await db.users.insert_many(users)
    teacher_id = users[1]["id"]

    categories = [
        {"id": gen_id(), "name": "SSC CGL", "slug": "ssc-cgl", "description": "Staff Selection Commission CGL Exam", "icon": "FileText", "created_at": now_iso()},
        {"id": gen_id(), "name": "UPSC Civil Services", "slug": "upsc", "description": "Union Public Service Commission", "icon": "Scale", "created_at": now_iso()},
        {"id": gen_id(), "name": "Banking (SBI/IBPS PO)", "slug": "banking", "description": "Banking Probationary Officer", "icon": "Landmark", "created_at": now_iso()},
        {"id": gen_id(), "name": "Railways RRB NTPC", "slug": "rrb-ntpc", "description": "Railways Recruitment", "icon": "Train", "created_at": now_iso()},
        {"id": gen_id(), "name": "NEET / JEE", "slug": "neet-jee", "description": "Medical & Engineering Entrance", "icon": "Atom", "created_at": now_iso()},
    ]
    await db.categories.insert_many(categories)

    # Sample questions for Quantitative Aptitude
    qbank = [
        ("What is 15% of 200?", ["A", "30"], ["B", "25"], ["C", "20"], ["D", "35"], "A", "15% × 200 = 30"),
        ("If a train travels 60 km in 1.5 hours, what is its speed?", ["A", "35 km/h"], ["B", "40 km/h"], ["C", "45 km/h"], ["D", "50 km/h"], "B", "Speed = Distance/Time = 60/1.5 = 40 km/h"),
        ("The square root of 144 is:", ["A", "10"], ["B", "11"], ["C", "12"], ["D", "13"], "C", "12 × 12 = 144"),
        ("What is 7 × 8?", ["A", "54"], ["B", "56"], ["C", "58"], ["D", "60"], "B", "7 × 8 = 56"),
        ("Compound interest on ₹1000 at 10% for 2 years is:", ["A", "₹200"], ["B", "₹210"], ["C", "₹220"], ["D", "₹231"], "B", "CI = P(1+r/100)^n - P = 1000 × 1.21 - 1000 = 210"),
        ("The ratio 3:4 is equal to:", ["A", "0.65"], ["B", "0.70"], ["C", "0.75"], ["D", "0.80"], "C", "3÷4 = 0.75"),
        ("If x + 5 = 12, then x =", ["A", "5"], ["B", "6"], ["C", "7"], ["D", "8"], "C", "x = 12 - 5 = 7"),
        ("Which is a prime number?", ["A", "15"], ["B", "17"], ["C", "21"], ["D", "25"], "B", "17 has only 1 and 17 as factors"),
        ("Area of circle with radius 7 (π=22/7):", ["A", "154"], ["B", "144"], ["C", "164"], ["D", "174"], "A", "πr² = 22/7 × 49 = 154"),
        ("20% of 150 is:", ["A", "25"], ["B", "28"], ["C", "30"], ["D", "35"], "C", "20% × 150 = 30"),
    ]
    qdocs = []
    for text, oA, oB, oC, oD, correct, expl in qbank:
        qdocs.append({
            "id": gen_id(), "text": text, "type": "mcq_single",
            "options": [{"key": "A", "text": oA[1]}, {"key": "B", "text": oB[1]},
                        {"key": "C", "text": oC[1]}, {"key": "D", "text": oD[1]}],
            "correct": [correct], "explanation": expl, "difficulty": "medium", "language": "en",
            "positive_marks": 2.0, "negative_marks": 0.5, "category_id": categories[0]["id"],
            "created_by": teacher_id, "created_at": now_iso(),
        })
    await db.questions.insert_many(qdocs)
    question_ids = [q["id"] for q in qdocs]

    # Sample test series
    series_list = [
        {"id": gen_id(), "title": "SSC CGL 2026 Full Mock Series", "description": "20 full-length mocks matching latest exam pattern. Covers Quant, Reasoning, English, GA.",
         "category_id": categories[0]["id"], "thumbnail": "https://images.unsplash.com/photo-1551836022-deb4988cc6c0?w=800", "language": "en",
         "is_free": True, "price": 0, "validity_days": 365, "is_published": True, "created_by": teacher_id, "created_at": now_iso()},
        {"id": gen_id(), "title": "UPSC Prelims Test Series", "description": "Full-length prelims mocks with detailed solutions and all-India ranking.",
         "category_id": categories[1]["id"], "thumbnail": "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=800", "language": "en",
         "is_free": False, "price": 99900, "validity_days": 365, "is_published": True, "created_by": teacher_id, "created_at": now_iso()},
        {"id": gen_id(), "title": "SBI PO Prelims Sprint", "description": "Sectional + full-length mocks tailored for SBI PO Prelims.",
         "category_id": categories[2]["id"], "thumbnail": "https://images.unsplash.com/photo-1554224154-26032fced8bd?w=800", "language": "en",
         "is_free": True, "price": 0, "validity_days": 365, "is_published": True, "created_by": teacher_id, "created_at": now_iso()},
        {"id": gen_id(), "title": "NEET Biology Mastery", "description": "Topic-wise mocks covering Botany & Zoology with NCERT-aligned explanations.",
         "category_id": categories[4]["id"], "thumbnail": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=800", "language": "en",
         "is_free": False, "price": 49900, "validity_days": 180, "is_published": True, "created_by": teacher_id, "created_at": now_iso()},
    ]
    await db.test_series.insert_many(series_list)

    # Each series gets 2 tests
    tests = []
    for s in series_list:
        for i in range(1, 3):
            tests.append({
                "id": gen_id(), "series_id": s["id"], "title": f"{s['title'][:30]} - Mock {i}",
                "duration_minutes": 60, "total_marks": sum(q["positive_marks"] for q in qdocs),
                "passing_marks": 10, "instructions": "Read all questions carefully. Negative marking applicable.",
                "question_ids": question_ids, "is_published": True,
                "created_by": teacher_id, "created_at": now_iso(),
            })
    await db.tests.insert_many(tests)

    # Sample courses
    courses = [
        {"id": gen_id(), "title": "Complete Quantitative Aptitude", "description": "Master Quant for SSC, Banking & Railways in 40 structured lessons.",
         "category_id": categories[0]["id"], "thumbnail": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800",
         "is_free": True, "price": 0, "created_by": teacher_id, "created_at": now_iso()},
        {"id": gen_id(), "title": "English Grammar Masterclass", "description": "Comprehensive grammar + comprehension course for all competitive exams.",
         "category_id": categories[2]["id"], "thumbnail": "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=800",
         "is_free": False, "price": 149900, "created_by": teacher_id, "created_at": now_iso()},
    ]
    await db.courses.insert_many(courses)

    # Add sections + lessons for the first course
    first_course = courses[0]
    secs = [
        {"id": gen_id(), "course_id": first_course["id"], "title": "Module 1: Number System", "position": 1, "created_at": now_iso()},
        {"id": gen_id(), "course_id": first_course["id"], "title": "Module 2: Percentage & Ratio", "position": 2, "created_at": now_iso()},
    ]
    await db.course_sections.insert_many(secs)
    lessons = []
    for sec in secs:
        for i in range(1, 4):
            lessons.append({
                "id": gen_id(), "section_id": sec["id"], "title": f"Lesson {i}: {sec['title'].split(': ')[1]} - Part {i}",
                "content_type": "video", "content_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
                "text_content": "Detailed lesson notes available.", "position": i, "duration_minutes": 15,
                "created_at": now_iso(),
            })
    await db.lessons.insert_many(lessons)

    # Study materials
    materials = [
        {"id": gen_id(), "title": "SSC CGL Previous Year Papers (2020-2024)", "description": "All PYQs with answer keys.",
         "category_id": categories[0]["id"], "file_url": "https://example.com/ssc-pyq.pdf", "is_free": True, "price": 0, "created_by": teacher_id, "created_at": now_iso()},
        {"id": gen_id(), "title": "UPSC Current Affairs Compendium", "description": "Monthly current affairs for Prelims & Mains.",
         "category_id": categories[1]["id"], "file_url": "https://example.com/upsc-ca.pdf", "is_free": False, "price": 29900, "created_by": teacher_id, "created_at": now_iso()},
        {"id": gen_id(), "title": "Banking Awareness Handbook", "description": "RBI, SEBI, insurance & current banking developments.",
         "category_id": categories[2]["id"], "file_url": "https://example.com/banking.pdf", "is_free": True, "price": 0, "created_by": teacher_id, "created_at": now_iso()},
    ]
    await db.study_materials.insert_many(materials)
    log.info("Seed data complete.")

@app.on_event("shutdown")
async def shutdown():
    client.close()

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
