"""
Test Series + LMS Platform - FastAPI Backend
Secure, server-authoritative examination engine with autosave, scoring, Razorpay payments.
"""
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict, ValidationError
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, uuid, logging, hashlib, hmac, jwt as pyjwt
import bcrypt, secrets, asyncio, requests, bisect, csv, io, re
import openpyxl
from fastapi import UploadFile, File, Form
import razorpay
from site_routes import build_site_router, seed_pages, UPLOAD_DIR
from admin_routes import build_admin_router
from email_routes import build_email_router, ensure_indexes as ensure_email_indexes
from perf import PublicCacheMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

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

async def _payment_settings() -> dict:
    return await db.settings.find_one({"key": "payment"}, {"_id": 0}) or {}

async def get_rzp():
    """Razorpay client from admin settings (falls back to env)."""
    s = await _payment_settings()
    kid = s.get("razorpay_key_id") or RZP_KEY
    sec = s.get("razorpay_key_secret") or RZP_SECRET
    wh = s.get("razorpay_webhook_secret") or RZP_WEBHOOK
    return (razorpay.Client(auth=(kid, sec)) if kid and sec else None), kid, wh

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
    if user.get("status") == "suspended":
        raise HTTPException(403, "Your account has been suspended. Please contact support.")
    if data.get("iat", 0) < user.pop("tokens_valid_after", 0):
        raise HTTPException(401, "Your session has expired. Please sign in again.")
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
    text_hi: Optional[str] = None

class QuestionIn(BaseModel):
    text: str
    type: Literal["mcq_single", "mcq_multi", "true_false", "numerical"] = "mcq_single"
    options: List[QuestionOption] = []
    correct: List[str]  # list of correct keys / value
    explanation: Optional[str] = ""
    text_hi: Optional[str] = None
    explanation_hi: Optional[str] = None
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

class TestSection(BaseModel):
    name: str
    duration_minutes: Optional[int] = None
    question_ids: List[str] = []
    positive_marks: Optional[float] = Field(None, ge=0)
    negative_marks: Optional[float] = Field(None, ge=0)
    language: Literal["bilingual", "en", "hi"] = "bilingual"

class TestIn(BaseModel):
    series_id: str
    title: str
    duration_minutes: int = 60
    total_marks: Optional[float] = None
    passing_marks: Optional[float] = None
    instructions: Optional[str] = ""
    question_ids: List[str] = []
    sections: List[TestSection] = []
    sectional_timing: bool = False
    is_published: bool = True
    live_start_at: Optional[str] = None
    live_window_minutes: int = 120

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
    thumbnail: Optional[str] = None
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
    coupon_code: Optional[str] = None

class CouponCheckIn(BaseModel):
    item_type: Literal["test_series", "course", "study_material"]
    item_id: str
    code: str

class CouponIn(BaseModel):
    code: str
    discount_type: Literal["percent", "flat"] = "percent"
    value: float  # percent (1-100) or rupees
    max_uses: Optional[int] = None
    valid_until: Optional[str] = None
    item_ids: List[str] = []
    active: bool = True
    description: str = ""

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
    if not user or not verify_pw(data.password, user.get("password_hash") or ""):
        raise HTTPException(401, "Invalid credentials")
    if user.get("status") == "suspended":
        raise HTTPException(403, "Your account has been suspended. Please contact support.")
    token = make_token(user["id"], user["role"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}}

@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user

class GoogleSessionIn(BaseModel):
    session_id: str

@api.post("/auth/google")
async def google_login(data: GoogleSessionIn):
    try:
        r = await asyncio.to_thread(
            requests.get, "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": data.session_id}, timeout=15,
        )
    except Exception:
        raise HTTPException(502, "Google sign-in service unavailable")
    if r.status_code != 200:
        raise HTTPException(401, "Google session invalid or expired")
    info = r.json()
    email = (info.get("email") or "").lower()
    if not email:
        raise HTTPException(401, "Google account has no email")
    user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if not user:
        user = {"id": gen_id(), "name": info.get("name") or email.split("@")[0], "email": email,
                "role": "student", "created_at": now_iso(), "avatar_url": info.get("picture"),
                "auth_provider": "google"}
        await db.users.insert_one(dict(user))
    elif user.get("status") == "suspended":
        raise HTTPException(403, "Your account has been suspended. Please contact support.")
    elif not user.get("avatar_url") and info.get("picture"):
        await db.users.update_one({"id": user["id"]}, {"$set": {"avatar_url": info["picture"]}})
    token = make_token(user["id"], user["role"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}}

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
                         difficulty: Optional[str] = None, limit: int = 2000,
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

async def _detach_questions(ids: list):
    await db.tests.update_many({"question_ids": {"$in": ids}}, {"$pull": {"question_ids": {"$in": ids}}})
    await db.tests.update_many({"sections.question_ids": {"$in": ids}}, {"$pull": {"sections.$[].question_ids": {"$in": ids}}})

# ---- Bulk import (CSV / Excel) ----
IMPORT_TYPES = {"": None, "mcq": "mcq_single", "single": "mcq_single", "mcq_single": "mcq_single", "multi": "mcq_multi",
                "multiple": "mcq_multi", "mcq_multi": "mcq_multi", "tf": "true_false", "true_false": "true_false",
                "true/false": "true_false", "truefalse": "true_false", "numerical": "numerical", "num": "numerical",
                "numeric": "numerical", "integer": "numerical"}
HEADER_ALIASES = {"question_text": "question", "text": "question", "q": "question", "answer": "correct",
                  "correct_answer": "correct", "correct_option": "correct", "answer_key": "correct", "key": "correct",
                  "marks": "positive_marks", "positive": "positive_marks", "negative": "negative_marks",
                  "negative_mark": "negative_marks", "level": "difficulty", "solution": "explanation",
                  "image": "image_url", "exam": "category", "question_type": "type"}
OPT_KEYS = "ABCDEFGH"
DIFFS = {"easy": "easy", "e": "easy", "medium": "medium", "m": "medium", "moderate": "medium", "hard": "hard", "h": "hard", "difficult": "hard"}
MAX_IMPORT_ROWS = 2000

def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, bool):
        return "True" if v else "False"
    return str(v).strip()

def _norm_base(h: str) -> str:
    m = re.fullmatch(r"(?:option_?|opt_?)?([a-h])", h)
    return f"option_{m.group(1)}" if m else HEADER_ALIASES.get(h, h)

def _norm_header(h) -> str:
    h = re.sub(r"[^a-z0-9_/]", "", _cell(h).lower().replace(" ", "_").replace("-", "_"))
    m = re.fullmatch(r"(.+?)_(?:hi|hindi)", h)
    return f"{_norm_base(m.group(1))}_hi" if m else _norm_base(h)

def _read_rows(filename: str, content: bytes) -> list:
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        try:
            ws = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True).worksheets[0]
        except Exception:
            raise HTTPException(400, "Could not read this Excel file")
        it = ws.iter_rows(values_only=True)
        header, rows = next(it, None) or [], [list(r) for r in it]
    elif name.endswith(".csv"):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        reader = csv.reader(io.StringIO(text))
        header, rows = next(reader, []), list(reader)
    else:
        raise HTTPException(400, "Upload a .csv or .xlsx file")
    keys = [_norm_header(h) for h in header]
    if "question" not in keys or "correct" not in keys:
        raise HTTPException(400, "The first row must contain headers incl. 'question' and 'correct'. Download the template.")
    out = []
    for n, r in enumerate(rows, start=2):
        vals = [_cell(v) for v in r]
        if any(vals):
            out.append((n, dict(zip(keys, vals))))
    return out

def _parse_correct_choice(raw: str, options: list, multi_allowed: bool):
    keys = {o["key"] for o in options}
    hit = next((o["key"] for o in options if o["text"].lower() == raw.lower()), None)
    if hit:
        return [hit], None
    out = []
    for tok in [t for t in re.split(r"[,;/|\s]+", raw) if t]:
        t = tok.upper().strip("().")
        if t in keys:
            out.append(t)
        elif t.isdigit() and 1 <= int(t) <= len(options):
            out.append(OPT_KEYS[int(t) - 1])
        else:
            return None, f"Correct answer '{tok}' doesn't match any option"
    out = list(dict.fromkeys(out))
    if len(out) > 1 and not multi_allowed:
        return None, "Several correct answers given — set type to 'multi'"
    return out, None

def _parse_import_row(row: dict, cats: dict, defaults: dict, subjects: dict):
    text = row.get("question", "")
    if not text:
        return None, "Question text is empty"
    raw_type = row.get("type", "").lower().replace(" ", "")
    if raw_type not in IMPORT_TYPES:
        return None, f"Unknown type '{row.get('type')}' (use mcq, multi, true_false or numerical)"
    qtype = IMPORT_TYPES[raw_type]
    correct_raw = row.get("correct", "")
    if not correct_raw:
        return None, "Correct answer is missing"
    options, gap = [], False
    for k in OPT_KEYS:
        v = row.get(f"option_{k.lower()}", "")
        if v and gap:
            return None, "Options must be filled in order (no gaps)"
        if v:
            options.append({"key": k, "text": v, "text_hi": row.get(f"option_{k.lower()}_hi") or None})
        else:
            gap = True
    if qtype is None:
        if not options and correct_raw.lower() in ("true", "false"):
            qtype = "true_false"
        elif not options:
            qtype = "numerical"
        else:
            qtype = "mcq_multi" if len([t for t in re.split(r"[,;/|\s]+", correct_raw) if t]) > 1 and not any(o["text"].lower() == correct_raw.lower() for o in options) else "mcq_single"
    if qtype == "true_false":
        v = correct_raw.lower()
        correct = ["A"] if v in ("true", "t", "a", "1", "yes") else ["B"] if v in ("false", "f", "b", "0", "no") else None
        if not correct:
            return None, "True/False answer must be True or False"
        options = [{"key": "A", "text": "True", "text_hi": "सत्य"}, {"key": "B", "text": "False", "text_hi": "असत्य"}]
    elif qtype == "numerical":
        try:
            float(correct_raw)
        except ValueError:
            return None, f"Numerical answer '{correct_raw}' is not a number"
        options, correct = [], [correct_raw]
    else:
        if len(options) < 2:
            return None, "Needs at least 2 options"
        correct, err = _parse_correct_choice(correct_raw, options, qtype == "mcq_multi")
        if err:
            return None, err
    cat_name = row.get("category", "")
    cid = cats.get(cat_name.lower()) if cat_name else defaults["category_id"]
    if cat_name and not cid:
        return None, f"Unknown category '{cat_name}'"
    sub_name, sid = row.get("subject", ""), defaults.get("subject_id")
    if sub_name:
        matches = subjects.get(sub_name.lower(), [])
        hit = next((x for x in matches if x["category_id"] == cid), None) or (matches[0] if matches and not cid else None)
        if not hit:
            return None, f"Unknown subject '{sub_name}'" + (" in this category" if matches else " — add it under Subjects first")
        sid, cid = hit["id"], cid or hit["category_id"]
    diff = DIFFS.get(row.get("difficulty", "").lower() or "medium")
    if not diff:
        return None, f"Unknown difficulty '{row.get('difficulty')}' (easy, medium, hard)"
    try:
        pos = float(row.get("positive_marks") or defaults["positive_marks"])
        neg = abs(float(row.get("negative_marks") or defaults["negative_marks"]))
    except ValueError:
        return None, "Marks must be numbers"
    try:
        q = QuestionIn(text=text, type=qtype, options=options, correct=correct, explanation=row.get("explanation", ""),
                       text_hi=row.get("question_hi") or None, explanation_hi=row.get("explanation_hi") or None,
                       category_id=cid, subject_id=sid or None, difficulty=diff, positive_marks=pos, negative_marks=neg,
                       image_url=row.get("image_url") or None)
    except ValidationError as e:
        return None, e.errors()[0].get("msg", "Invalid row")
    return q.model_dump(), None

@api.post("/questions/import")
async def import_questions(file: UploadFile = File(...), commit: bool = Form(False), category_id: str = Form(""),
                           positive_marks: float = Form(1.0), negative_marks: float = Form(0.0), subject_id: str = Form(""),
                           user=Depends(require_roles("admin", "teacher"))):
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "File is larger than 5 MB")
    rows = _read_rows(file.filename or "", content)
    if not rows:
        raise HTTPException(400, "The file has no question rows")
    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(400, f"Up to {MAX_IMPORT_ROWS} questions per file")
    cats = {}
    async for c in db.categories.find({}, {"_id": 0, "id": 1, "name": 1, "slug": 1}):
        cats[c["name"].lower()] = c["id"]
        cats[c["slug"].lower()] = c["id"]
    subjects = {}
    async for x in db.subjects.find({}, {"_id": 0, "id": 1, "name": 1, "category_id": 1}):
        subjects.setdefault(x["name"].strip().lower(), []).append(x)
    defaults = {"category_id": category_id or None, "positive_marks": positive_marks, "negative_marks": negative_marks,
                "subject_id": subject_id or None}
    valid, errors = [], []
    for n, row in rows:
        q, err = _parse_import_row(row, cats, defaults, subjects)
        if err:
            errors.append({"row": n, "message": err})
        else:
            valid.append(q)
    resp = {"total": len(rows), "valid": len(valid), "error_count": len(errors), "errors": errors[:200], "preview": valid[:5]}
    if commit and valid:
        batch = gen_id()
        docs = [{"id": gen_id(), **q, "created_by": user["id"], "created_at": now_iso(), "import_batch": batch} for q in valid]
        await db.questions.insert_many(docs)
        resp.update(inserted=len(docs), batch_id=batch)
    return resp

@api.delete("/questions/import/{batch_id}")
async def undo_import(batch_id: str, _=Depends(require_roles("admin", "teacher"))):
    ids = [q["id"] async for q in db.questions.find({"import_batch": batch_id}, {"id": 1})]
    if not ids:
        raise HTTPException(404, "Import not found")
    await db.questions.delete_many({"import_batch": batch_id})
    await _detach_questions(ids)
    return {"deleted": len(ids)}

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
    doc = {"id": gen_id(), **(await _prepare_test(data.model_dump())), "created_by": user["id"], "created_at": now_iso()}
    await db.tests.insert_one(doc)
    doc.pop("_id", None)
    return doc

def _parse_dt(v: Optional[str], label: str) -> Optional[str]:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, f"Invalid {label}")
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat()

def _live_window(t: dict):
    if not t.get("live_start_at"):
        return None, None
    start = datetime.fromisoformat(t["live_start_at"])
    return start, start + timedelta(minutes=t.get("live_window_minutes") or 120)

@api.get("/live-mocks")
async def live_mocks():
    now = datetime.now(timezone.utc)
    rows = await db.tests.find({"is_published": True, "live_start_at": {"$ne": None}}, {"_id": 0, "question_ids": 0}).to_list(500)
    out = []
    for t in rows:
        start, end = _live_window(t)
        if now > end:
            continue
        s = await db.test_series.find_one({"id": t["series_id"]}, {"_id": 0, "id": 1, "title": 1, "is_free": 1, "price": 1})
        out.append({"id": t["id"], "title": t["title"], "series": s, "live_start_at": start.isoformat(), "live_end_at": end.isoformat(),
                    "status": "live" if now >= start else "upcoming", "duration_minutes": t.get("duration_minutes"),
                    "total_marks": t.get("total_marks"), "sections": [x["name"] for x in t.get("sections") or []]})
    out.sort(key=lambda x: x["live_start_at"])
    return {"server_now": now.isoformat(), "mocks": out}

def _section_of(sections) -> dict:
    return {qid: s for s in sections or [] for qid in s["question_ids"]}

def _marks(q: dict, sec: dict) -> tuple:
    pos, neg = sec.get("positive_marks"), sec.get("negative_marks")
    return (q.get("positive_marks", 1.0) if pos is None else pos, q.get("negative_marks", 0.0) if neg is None else neg)

def _localize(q: dict, lang: str):
    """English-only drops Hindi; Hindi-only swaps Hindi in (falls back to English where blank)."""
    if lang == "hi":
        q["text"] = q.get("text_hi") or q["text"]
        if q.get("explanation_hi"):
            q["explanation"] = q["explanation_hi"]
        q["options"] = [{**o, "text": o.get("text_hi") or o["text"]} for o in q.get("options") or []]
    if lang in ("en", "hi"):
        q.pop("text_hi", None)
        q.pop("explanation_hi", None)
        q["options"] = [{k: v for k, v in o.items() if k != "text_hi"} for o in q.get("options") or []]

def _apply_section_rules(qs: list, sections) -> list:
    smap = _section_of(sections)
    for q in qs:
        sec = smap.get(q["id"], {})
        q["positive_marks"], q["negative_marks"] = _marks(q, sec)
        q["display_language"] = sec.get("language", "bilingual")
        _localize(q, q["display_language"])
    return qs

async def _prepare_test(data: dict) -> dict:
    """Normalise sections, flatten question_ids, compute duration (sectional) and total marks."""
    data["live_start_at"] = _parse_dt(data.get("live_start_at"), "live start time")
    data["live_window_minutes"] = max(1, int(data.get("live_window_minutes") or 120))
    secs = [s for s in data.get("sections") or [] if s["question_ids"]]
    if secs:
        seen = set()
        for s in secs:
            s["name"] = s["name"].strip() or "Section"
            s["question_ids"] = [q for q in s["question_ids"] if not (q in seen or seen.add(q))]
        data["question_ids"] = [q for s in secs for q in s["question_ids"]]
        if data.get("sectional_timing"):
            if any(not s.get("duration_minutes") or s["duration_minutes"] <= 0 for s in secs):
                raise HTTPException(422, "Every section needs a duration when sectional timing is on")
            data["duration_minutes"] = sum(s["duration_minutes"] for s in secs)
    else:
        data["sectional_timing"] = False
    data["sections"] = secs
    if not data["question_ids"]:
        raise HTTPException(422, "Add at least one question")
    qs = await db.questions.find({"id": {"$in": data["question_ids"]}}, {"_id": 0, "id": 1, "positive_marks": 1}).to_list(5000)
    smap = _section_of(secs)
    data["total_marks"] = data.get("total_marks") or sum(_marks(q, smap.get(q["id"], {}))[0] for q in qs)
    return data

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
    live_start, _end = _live_window(t)
    if live_start and datetime.now(timezone.utc) < live_start:
        raise HTTPException(403, "This live mock hasn't opened yet")
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
        "sections": t.get("sections") or [],
        "sectional_timing": bool(t.get("sectional_timing") and t.get("sections")),
    }
    if attempt["sectional_timing"]:
        attempt["current_section"] = 0
        attempt["section_ends_at"] = (now_dt + timedelta(minutes=attempt["sections"][0]["duration_minutes"])).isoformat()
    await db.test_attempts.insert_one(attempt)
    attempt.pop("_id", None)
    return attempt

@api.get("/attempts/{attempt_id}")
async def get_attempt(attempt_id: str, user=Depends(get_current_user)):
    a = await _own_attempt(attempt_id, user)
    a = await _sync_sections(a)
    if a["status"] != "in_progress":
        return {"id": a["id"], "status": a["status"]}
    # Sectional mode only reveals the current section's questions
    qids = a["sections"][a["current_section"]]["question_ids"] if a.get("sectional_timing") else a["question_ids"]
    qs = await db.questions.find({"id": {"$in": qids}}, {"_id": 0, "correct": 0, "explanation": 0, "explanation_hi": 0}).to_list(5000)
    qmap = {q["id"]: q for q in qs}
    a["questions"] = _apply_section_rules([qmap[qid] for qid in qids if qid in qmap], a.get("sections"))
    t = await db.tests.find_one({"id": a["test_id"]}, {"_id": 0, "title": 1})
    a["test_title"] = t["title"] if t else "Online Examination"
    a["server_now"] = now_iso()
    return a

async def _own_attempt(attempt_id: str, user: dict) -> dict:
    a = await db.test_attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not a or a["user_id"] != user["id"]:
        raise HTTPException(404, "Attempt not found")
    return a

SECTION_GRACE = timedelta(seconds=15)

def _merge_section_answers(a: dict, answers: dict, marked: list):
    """Only the current section's answers may change in sectional mode."""
    allowed = set(a["sections"][a["current_section"]]["question_ids"])
    merged = {k: v for k, v in (a.get("answers") or {}).items() if k not in allowed}
    merged.update({k: v for k, v in answers.items() if k in allowed})
    mk = [q for q in a.get("marked_for_review") or [] if q not in allowed] + [q for q in marked if q in allowed]
    return merged, mk

async def _sync_sections(a: dict) -> dict:
    """Advance expired sections by server time; finalize when the last one expires."""
    if a["status"] != "in_progress" or not a.get("sectional_timing"):
        return a
    now = datetime.now(timezone.utc)
    cur, end, secs = a["current_section"], datetime.fromisoformat(a["section_ends_at"]), a["sections"]
    if now <= end:
        return a
    while now > end and cur < len(secs) - 1:
        cur += 1
        end = end + timedelta(minutes=secs[cur]["duration_minutes"])
    if now > end:
        await _finalize_attempt(a, a.get("answers") or {}, a.get("marked_for_review") or [], auto=True)
        return {**a, "status": "submitted"}
    await db.test_attempts.update_one(
        {"id": a["id"], "current_section": a["current_section"]},
        {"$set": {"current_section": cur, "section_ends_at": end.isoformat()}, "$inc": {"version": 1}},
    )
    return await db.test_attempts.find_one({"id": a["id"]}, {"_id": 0})

async def _sectional_save(a: dict, answers: dict, marked: list, advance: bool):
    """Save current-section answers (with grace), then advance on request or on expiry."""
    now = datetime.now(timezone.utc)
    end = datetime.fromisoformat(a["section_ends_at"])
    if now <= end + SECTION_GRACE:
        ans, mk = _merge_section_answers(a, answers, marked)
        await db.test_attempts.update_one(
            {"id": a["id"], "current_section": a["current_section"]},
            {"$set": {"answers": ans, "marked_for_review": mk, "last_saved_at": now_iso()}, "$inc": {"version": 1}},
        )
        a = {**a, "answers": ans, "marked_for_review": mk, "version": a.get("version", 0) + 1}
    if not advance and now <= end:
        return "ok", a
    if a["current_section"] >= len(a["sections"]) - 1:
        await _finalize_attempt(a, a.get("answers") or {}, a.get("marked_for_review") or [], auto=not advance)
        return "submitted", a
    if advance and now <= end:
        nxt = a["current_section"] + 1
        new_end = now + timedelta(minutes=a["sections"][nxt]["duration_minutes"])
        await db.test_attempts.update_one(
            {"id": a["id"], "current_section": a["current_section"]},
            {"$set": {"current_section": nxt, "section_ends_at": new_end.isoformat()}, "$inc": {"version": 1}},
        )
        return "section_advanced", a
    fresh = await _sync_sections(await db.test_attempts.find_one({"id": a["id"]}, {"_id": 0}))
    return ("submitted" if fresh["status"] == "submitted" else "section_advanced"), fresh

@api.post("/attempts/{attempt_id}/next-section")
async def next_section(attempt_id: str, data: AutosaveIn, user=Depends(get_current_user)):
    a = await _own_attempt(attempt_id, user)
    if a["status"] != "in_progress":
        return {"status": "submitted"}
    if not a.get("sectional_timing"):
        raise HTTPException(400, "This test has no timed sections")
    status, _a = await _sectional_save(a, data.answers, data.marked_for_review, advance=True)
    return {"status": status}

@api.post("/attempts/{attempt_id}/autosave")
async def autosave(attempt_id: str, data: AutosaveIn, user=Depends(get_current_user)):
    a = await _own_attempt(attempt_id, user)
    if a["status"] != "in_progress":
        raise HTTPException(400, "Attempt not active")
    if a.get("sectional_timing"):
        status, a2 = await _sectional_save(a, data.answers, data.marked_for_review, advance=False)
        return {"status": "auto_submitted" if status == "submitted" else status, "version": a2.get("version", 0)}
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
    qs = await db.questions.find({"id": {"$in": attempt["question_ids"]}}).to_list(5000)
    smap = _section_of(attempt.get("sections"))
    for q in qs:
        q["positive_marks"], q["negative_marks"] = _marks(q, smap.get(q["id"], {}))
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
    dmap = {d["qid"]: d for d in details}
    qmarks = {q["id"]: q.get("positive_marks", 1.0) for q in qs}
    section_summary = []
    for s in attempt.get("sections") or []:
        ds = [dmap[q] for q in s["question_ids"] if q in dmap]
        c = sum(d["status"] == "correct" for d in ds)
        w = sum(d["status"] == "wrong" for d in ds)
        section_summary.append({
            "name": s["name"], "score": round(sum(d["awarded"] for d in ds), 2),
            "total_marks": round(sum(qmarks.get(q, 0) for q in s["question_ids"]), 2),
            "correct": c, "wrong": w, "unattempted": len(ds) - c - w,
            "accuracy": round(c / max(1, c + w) * 100, 2),
        })
    started = datetime.fromisoformat(attempt["started_at"])
    time_taken = int(min((datetime.now(timezone.utc) - started).total_seconds(), attempt.get("duration_minutes", 0) * 60 or 10**9))
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
        "sections": section_summary,
        "time_taken_sec": time_taken,
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
    a = await _own_attempt(attempt_id, user)
    if a["status"] == "submitted":
        res = await db.test_results.find_one({"attempt_id": attempt_id}, {"_id": 0})
        return res
    answers, marked = data.answers, data.marked_for_review
    if a.get("sectional_timing"):
        status, a = await _sectional_save(a, answers, marked, advance=False)
        if status == "submitted":
            return await db.test_results.find_one({"attempt_id": attempt_id}, {"_id": 0})
        answers, marked = a.get("answers") or {}, a.get("marked_for_review") or []
    result = await _finalize_attempt(a, answers, marked)
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
    qs = await db.questions.find({"id": {"$in": a["question_ids"]}}, {"_id": 0}).to_list(5000)
    res["questions"] = _apply_section_rules(qs, a.get("sections"))
    res["user_answers"] = a.get("answers", {})
    res["rank"] = await _rank_for(res)
    return res

def _short_name(n: Optional[str]) -> str:
    parts = (n or "Student").split()
    return parts[0] + (f" {parts[-1][0]}." if len(parts) > 1 else "")

async def _board(test_id: str) -> list:
    """Ranked first attempts for a test: score desc, then faster time. Rank ties on equal score."""
    rows = await db.test_results.find(
        {"test_id": test_id},
        {"_id": 0, "user_id": 1, "score": 1, "attempt_id": 1, "created_at": 1, "accuracy": 1, "time_taken_sec": 1},
    ).sort("created_at", 1).to_list(None)
    first = {}
    for r in rows:
        first.setdefault(r["user_id"], r)
    entries = sorted(first.values(), key=lambda r: (-r["score"], r.get("time_taken_sec") if r.get("time_taken_sec") is not None else 10**9))
    asc = sorted(e["score"] for e in entries)
    n = len(entries)
    for e in entries:
        e["rank"] = n - bisect.bisect_right(asc, e["score"]) + 1
        e["percentile"] = 100.0 if n <= 1 else round(bisect.bisect_left(asc, e["score"]) / (n - 1) * 100, 2)
    return entries

async def _names(user_ids) -> dict:
    users = await db.users.find({"id": {"$in": list(user_ids)}}, {"_id": 0, "id": 1, "name": 1}).to_list(None)
    return {u["id"]: _short_name(u["name"]) for u in users}

def _board_entry(e: dict, names: dict, me: Optional[str]) -> dict:
    return {"rank": e["rank"], "name": names.get(e["user_id"], "Student"), "score": e["score"],
            "accuracy": e.get("accuracy"), "time_taken_sec": e.get("time_taken_sec"),
            "percentile": e["percentile"], "is_you": e["user_id"] == me}

async def _rank_for(result: dict) -> dict:
    """All-India rank among all students, using each student's first attempt of this test."""
    board = await _board(result["test_id"])
    mine = next((e for e in board if e["user_id"] == result["user_id"]), None)
    top = board[:5]
    names = await _names([e["user_id"] for e in top])
    return {"rank": mine["rank"] if mine else 1, "total": len(board), "percentile": mine["percentile"] if mine else 100.0,
            "top": [_board_entry(e, names, result["user_id"]) for e in top],
            "is_official": bool(mine and mine["attempt_id"] == result["attempt_id"])}

def _optional_user_id(creds: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if not creds:
        return None
    try:
        return pyjwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])["uid"]
    except Exception:
        return None

@api.get("/tests/{test_id}/leaderboard")
async def test_leaderboard(test_id: str, limit: int = 50, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    t = await db.tests.find_one({"id": test_id}, {"_id": 0, "id": 1, "title": 1, "series_id": 1, "total_marks": 1, "duration_minutes": 1, "sections": 1})
    if not t:
        raise HTTPException(404, "Test not found")
    s = await db.test_series.find_one({"id": t["series_id"]}, {"_id": 0, "id": 1, "title": 1})
    me = _optional_user_id(creds)
    board = await _board(test_id)
    limit = max(1, min(limit, 200))
    mine = next((e for e in board if e["user_id"] == me), None) if me else None
    names = await _names([e["user_id"] for e in board[:limit]] + ([me] if mine else []))
    scores = [e["score"] for e in board]
    return {
        "test": {"id": t["id"], "title": t["title"], "total_marks": t.get("total_marks"), "duration_minutes": t.get("duration_minutes"),
                 "sections": [x["name"] for x in t.get("sections") or []]},
        "series": s,
        "participants": len(board),
        "top_score": max(scores) if scores else None,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "entries": [_board_entry(e, names, me) for e in board[:limit]],
        "me": _board_entry(mine, names, me) if mine else None,
        "updated_at": now_iso(),
    }

@api.get("/leaderboards")
async def leaderboards():
    tests = await db.tests.find({"is_published": True}, {"_id": 0, "id": 1, "title": 1, "series_id": 1, "total_marks": 1, "sections": 1}).to_list(1000)
    series = {s["id"]: s["title"] async for s in db.test_series.find({}, {"_id": 0, "id": 1, "title": 1})}
    agg = db.test_results.aggregate([{"$group": {"_id": "$test_id", "users": {"$addToSet": "$user_id"}, "top": {"$max": "$score"}}}])
    stats = {g["_id"]: (len(g["users"]), g["top"]) async for g in agg}
    out = [{"id": t["id"], "title": t["title"], "series_title": series.get(t["series_id"]), "total_marks": t.get("total_marks"),
            "sections": len(t.get("sections") or []), "participants": stats.get(t["id"], (0, None))[0],
            "top_score": stats.get(t["id"], (0, None))[1]} for t in tests]
    return sorted(out, key=lambda x: -x["participants"])

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
    done_ids = await db.lesson_progress.distinct("lesson_id", {"user_id": user["id"], "lesson_id": {"$in": lesson_ids}})
    done = len(done_ids)
    return {"total": total, "completed": done, "percent": round((done / total * 100) if total else 0, 1), "completed_ids": done_ids}

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
    coupon_code, discount = None, 0
    if data.coupon_code:
        c, d = await _apply_coupon(data.coupon_code, user["id"], data.item_id, amount)
        final = _final_amount(amount, d)
        coupon_code, discount, amount = c["code"], amount - final, final
    if amount == 0:
        order = {"id": gen_id(), "user_id": user["id"], "item_type": data.item_type, "item_id": data.item_id,
                 "amount": 0, "currency": "INR", "status": "paid", "created_at": now_iso(), "razorpay_order_id": None,
                 "item_title": item.get("title"), "coupon_code": coupon_code, "discount": discount, "original_amount": discount}
        await db.orders.insert_one(order)
        await _grant_entitlement(user["id"], data.item_type, data.item_id, order["id"])
        order.pop("_id", None)
        return order
    oid = gen_id()
    receipt = oid[:40]
    rzp_order = None
    rzp_client, rzp_key, _ = await get_rzp()
    if rzp_client:
        try:
            rzp_order = await asyncio.to_thread(rzp_client.order.create, {
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
    order.update(coupon_code=coupon_code, discount=discount, original_amount=amount + discount)
    await db.orders.insert_one(order)
    order.pop("_id", None)
    return {**order, "razorpay_key": rzp_key, "demo_mode": not bool(rzp_client)}

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
        order = await db.orders.find_one({"id": order_id}, {"_id": 0, "coupon_code": 1})
        if order and order.get("coupon_code"):
            await db.coupons.update_one({"code": order["coupon_code"]}, {"$inc": {"used_count": 1}})

# ---- Coupons ----
async def _apply_coupon(code: str, user_id: str, item_id: str, amount: int):
    c = await db.coupons.find_one({"code": code.strip().upper()}, {"_id": 0})
    if not c or not c.get("active"):
        raise HTTPException(400, "Invalid or inactive coupon")
    if c.get("valid_until") and datetime.now(timezone.utc) > datetime.fromisoformat(c["valid_until"]):
        raise HTTPException(400, "This coupon has expired")
    if c.get("max_uses") and c.get("used_count", 0) >= c["max_uses"]:
        raise HTTPException(400, "This coupon has reached its usage limit")
    if c.get("item_ids") and item_id not in c["item_ids"]:
        raise HTTPException(400, "This coupon isn't valid for this item")
    if amount <= 0:
        raise HTTPException(400, "Coupons apply to paid items only")
    if await db.orders.find_one({"user_id": user_id, "coupon_code": c["code"], "status": "paid"}):
        raise HTTPException(400, "You've already used this coupon")
    d = round(amount * c["value"] / 100) if c["discount_type"] == "percent" else int(round(c["value"] * 100))
    return c, min(d, amount)

def _final_amount(amount: int, discount: int) -> int:
    f = amount - discount
    return 0 if f <= 0 else max(f, 100)  # Razorpay minimum is ₹1

@api.post("/coupons/validate")
async def validate_coupon(data: CouponCheckIn, user=Depends(get_current_user)):
    item = await _get_item(data.item_type, data.item_id)
    amount = 0 if item.get("is_free") else int(item.get("price", 0))
    c, d = await _apply_coupon(data.code, user["id"], data.item_id, amount)
    final = _final_amount(amount, d)
    return {"code": c["code"], "original": amount, "discount": amount - final, "final_amount": final, "description": c.get("description", "")}

def _coupon_doc(data: CouponIn) -> dict:
    code = re.sub(r"\s+", "", data.code).upper()
    if not re.fullmatch(r"[A-Z0-9_-]{3,30}", code):
        raise HTTPException(422, "Code must be 3-30 letters, numbers, - or _")
    if data.discount_type == "percent" and not 0 < data.value <= 100:
        raise HTTPException(422, "Percent discount must be between 1 and 100")
    if data.discount_type == "flat" and data.value <= 0:
        raise HTTPException(422, "Flat discount must be more than ₹0")
    if data.max_uses is not None and data.max_uses < 1:
        raise HTTPException(422, "Max uses must be at least 1")
    return {**data.model_dump(), "code": code, "valid_until": _parse_dt(data.valid_until, "expiry date")}

@api.get("/admin/coupons")
async def list_coupons(_=Depends(require_roles("admin"))):
    return await db.coupons.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.post("/admin/coupons")
async def create_coupon(data: CouponIn, user=Depends(require_roles("admin"))):
    doc = _coupon_doc(data)
    if await db.coupons.find_one({"code": doc["code"]}):
        raise HTTPException(400, "A coupon with this code already exists")
    doc.update(id=gen_id(), used_count=0, created_by=user["id"], created_at=now_iso())
    await db.coupons.insert_one(dict(doc))
    return doc

@api.put("/admin/coupons/{coupon_id}")
async def update_coupon(coupon_id: str, data: CouponIn, _=Depends(require_roles("admin"))):
    doc = _coupon_doc(data)
    if await db.coupons.find_one({"code": doc["code"], "id": {"$ne": coupon_id}}):
        raise HTTPException(400, "A coupon with this code already exists")
    res = await db.coupons.update_one({"id": coupon_id}, {"$set": {**doc, "updated_at": now_iso()}})
    if not res.matched_count:
        raise HTTPException(404, "Coupon not found")
    return await db.coupons.find_one({"id": coupon_id}, {"_id": 0})

@api.delete("/admin/coupons/{coupon_id}")
async def delete_coupon(coupon_id: str, _=Depends(require_roles("admin"))):
    res = await db.coupons.delete_one({"id": coupon_id})
    if not res.deleted_count:
        raise HTTPException(404, "Coupon not found")
    return {"ok": True}

# ---- Weak topic report ----
@api.get("/my/weak-topics")
async def weak_topics(user=Depends(get_current_user)):
    results = await db.test_results.find({"user_id": user["id"], "sections.0": {"$exists": True}},
                                         {"_id": 0, "sections": 1, "created_at": 1}).sort("created_at", 1).to_list(1000)
    topics = {}
    for r in results:
        for s in r["sections"]:
            t = topics.setdefault(s["name"].strip().lower(), {"name": s["name"], "attempts": 0, "score": 0.0, "total": 0.0,
                                                              "correct": 0, "wrong": 0, "skipped": 0, "history": []})
            t["attempts"] += 1
            t["score"] += s["score"]
            t["total"] += s["total_marks"]
            t["correct"] += s["correct"]
            t["wrong"] += s["wrong"]
            t["skipped"] += s["unattempted"]
            t["history"].append(round(max(0, s["score"]) / s["total_marks"] * 100, 1) if s["total_marks"] else 0)
    attempted = set(await db.test_attempts.distinct("test_id", {"user_id": user["id"]}))
    owned = set(await db.entitlements.distinct("item_id", {"user_id": user["id"], "item_type": "test_series"}))
    series = {s["id"]: s async for s in db.test_series.find({}, {"_id": 0, "id": 1, "title": 1, "is_free": 1})}
    tests = await db.tests.find({"is_published": True, "sections.0": {"$exists": True}},
                                {"_id": 0, "id": 1, "title": 1, "series_id": 1, "sections.name": 1, "live_start_at": 1}).to_list(1000)
    now = datetime.now(timezone.utc)
    is_admin = user["role"] in ("admin", "super_admin")
    out = []
    for key, t in topics.items():
        pct = round(max(0, t["score"]) / t["total"] * 100, 1) if t["total"] else 0
        h = t["history"]
        item = {"name": t["name"], "attempts": t["attempts"], "score_pct": pct, "correct": t["correct"], "wrong": t["wrong"],
                "skipped": t["skipped"], "accuracy": round(t["correct"] / max(1, t["correct"] + t["wrong"]) * 100, 1),
                "trend": round(h[-1] - h[-2], 1) if len(h) > 1 else None,
                "level": "weak" if pct < 50 else "average" if pct < 75 else "strong", "suggestions": []}
        if item["level"] != "strong":
            cands = []
            for x in tests:
                if not any(s["name"].strip().lower() == key for s in x.get("sections") or []):
                    continue
                if x.get("live_start_at") and datetime.fromisoformat(x["live_start_at"]) > now:
                    continue
                s = series.get(x["series_id"]) or {}
                access = is_admin or bool(s.get("is_free")) or x["series_id"] in owned
                cands.append({"test_id": x["id"], "title": x["title"], "series_id": x["series_id"], "series_title": s.get("title"),
                              "attempted": x["id"] in attempted, "has_access": access})
            cands.sort(key=lambda c: (c["attempted"], not c["has_access"]))
            item["suggestions"] = cands[:3]
        out.append(item)
    out.sort(key=lambda x: x["score_pct"])
    return {"topics": out, "results_analyzed": len(results), "subjects": await _subject_report(user["id"])}

async def _subject_report(user_id: str) -> list:
    results = await db.test_results.find({"user_id": user_id}, {"_id": 0, "details": 1}).to_list(1000)
    qids = list({d["qid"] for r in results for d in r.get("details") or []})
    qinfo = {q["id"]: q async for q in db.questions.find({"id": {"$in": qids}}, {"_id": 0, "id": 1, "subject_id": 1, "positive_marks": 1})}
    names = {s["id"]: s["name"] async for s in db.subjects.find({}, {"_id": 0, "id": 1, "name": 1})}
    agg = {}
    for r in results:
        for d in r.get("details") or []:
            sid = (qinfo.get(d["qid"]) or {}).get("subject_id")
            if not sid or sid not in names:
                continue
            t = agg.setdefault(sid, {"subject_id": sid, "name": names[sid], "questions": 0, "correct": 0, "wrong": 0, "skipped": 0})
            t["questions"] += 1
            t[{"correct": "correct", "wrong": "wrong"}.get(d["status"], "skipped")] += 1
    out = []
    for t in agg.values():
        acc = round(t["correct"] / max(1, t["correct"] + t["wrong"]) * 100, 1)
        score = round(t["correct"] / max(1, t["questions"]) * 100, 1)
        out.append({**t, "accuracy": acc, "score_pct": score, "level": "weak" if score < 50 else "average" if score < 75 else "strong"})
    return sorted(out, key=lambda x: x["score_pct"])

@api.post("/orders/verify")
async def verify_payment(data: VerifyPaymentIn, user=Depends(get_current_user)):
    order = await db.orders.find_one({"id": data.order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] == "paid":
        return {"status": "already_paid"}
    rzp_client, _, _ = await get_rzp()
    if not rzp_client:
        raise HTTPException(400, "Payments are not configured")
    if order.get("razorpay_order_id") != data.razorpay_order_id:
        raise HTTPException(400, "Order mismatch")
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
    _, _, wh_secret = await get_rzp()
    if not wh_secret:
        raise HTTPException(400, "Webhook not configured")
    expected = hmac.new(wh_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(400, "Invalid signature")
    try:
        payload = (await request.json())
    except Exception:
        return {"ok": True}
    event = payload.get("event", "")
    if event == "payment.captured":
        rp = payload.get("payload", {}).get("payment", {}).get("entity", {})
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
async def admin_stats(user=Depends(require_roles("admin", "teacher"))):
    stats = {
        "users": await db.users.count_documents({}),
        "questions": await db.questions.count_documents({}),
        "test_series": await db.test_series.count_documents({}),
        "tests": await db.tests.count_documents({}),
        "courses": await db.courses.count_documents({}),
        "attempts": await db.test_attempts.count_documents({}),
        "orders_paid": await db.orders.count_documents({"status": "paid"}),
        "revenue": sum([o.get("amount", 0) async for o in db.orders.find({"status": "paid"}, {"amount": 1})]),
    }
    if user["role"] == "teacher":
        stats.pop("revenue")
        stats.pop("orders_paid")
    return stats

@api.get("/admin/users")
async def admin_users(_=Depends(require_roles("admin"))):
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)

@api.get("/admin/orders")
async def admin_orders(_=Depends(require_roles("admin"))):
    return await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)

class RoleIn(BaseModel):
    role: Literal["super_admin", "admin", "teacher", "student", "support"]

@api.put("/admin/users/{user_id}/role")
async def set_user_role(user_id: str, data: RoleIn, user=Depends(require_roles("admin"))):
    if user_id == user["id"]:
        raise HTTPException(400, "You cannot change your own role")
    if data.role == "super_admin" and user["role"] != "super_admin":
        raise HTTPException(403, "Only a super admin can grant super admin")
    res = await db.users.update_one({"id": user_id}, {"$set": {"role": data.role}})
    if not res.matched_count:
        raise HTTPException(404, "User not found")
    return {"ok": True}

@api.get("/admin/tests")
async def admin_tests(_=Depends(require_roles("admin", "teacher"))):
    return await db.tests.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)

# ---- Generic content update/delete (admin + teacher) ----
CONTENT = {
    "questions": (db.questions, QuestionIn),
    "test-series": (db.test_series, TestSeriesIn),
    "tests": (db.tests, TestIn),
    "courses": (db.courses, CourseIn),
    "sections": (db.course_sections, SectionIn),
    "lessons": (db.lessons, LessonIn),
    "study-materials": (db.study_materials, StudyMaterialIn),
    "categories": (db.categories, CategoryIn),
    "subjects": (db.subjects, SubjectIn),
}

def _content(kind: str):
    if kind not in CONTENT:
        raise HTTPException(404, "Unknown content type")
    return CONTENT[kind]

@api.put("/content/{kind}/{item_id}")
async def update_content(kind: str, item_id: str, body: Dict[str, Any], _=Depends(require_roles("admin", "teacher"))):
    coll, model = _content(kind)
    try:
        data = model(**body).model_dump()
    except ValidationError as e:
        raise HTTPException(422, e.errors()[0].get("msg", "Invalid data"))
    if kind == "tests":
        data = await _prepare_test(data)
    res = await coll.update_one({"id": item_id}, {"$set": {**data, "updated_at": now_iso()}})
    if not res.matched_count:
        raise HTTPException(404, "Not found")
    return await coll.find_one({"id": item_id}, {"_id": 0})

@api.delete("/content/{kind}/{item_id}")
async def delete_content(kind: str, item_id: str, _=Depends(require_roles("admin", "teacher"))):
    coll, _m = _content(kind)
    res = await coll.delete_one({"id": item_id})
    if not res.deleted_count:
        raise HTTPException(404, "Not found")
    if kind == "test-series":
        await db.tests.delete_many({"series_id": item_id})
    elif kind == "courses":
        sec_ids = [s["id"] async for s in db.course_sections.find({"course_id": item_id}, {"id": 1})]
        await db.lessons.delete_many({"section_id": {"$in": sec_ids}})
        await db.course_sections.delete_many({"course_id": item_id})
    elif kind == "sections":
        await db.lessons.delete_many({"section_id": item_id})
    elif kind == "questions":
        await _detach_questions([item_id])
    elif kind == "subjects":
        await db.questions.update_many({"subject_id": item_id}, {"$set": {"subject_id": None}})
    return {"ok": True}

# ---- Payment settings (admin) ----
class PaymentSettingsIn(BaseModel):
    razorpay_key_id: str = ""
    razorpay_key_secret: Optional[str] = None  # blank keeps the saved secret
    razorpay_webhook_secret: Optional[str] = None

async def _payment_view() -> dict:
    s = await _payment_settings()
    kid = s.get("razorpay_key_id") or RZP_KEY
    sec = s.get("razorpay_key_secret") or RZP_SECRET
    mode = "demo" if not (kid and sec) else ("live" if kid.startswith("rzp_live") else "test")
    return {"razorpay_key_id": kid, "has_secret": bool(sec), "secret_hint": f"••••{sec[-4:]}" if sec else "",
            "razorpay_webhook_secret": s.get("razorpay_webhook_secret") or RZP_WEBHOOK,
            "mode": mode, "updated_at": s.get("updated_at")}

@api.get("/admin/settings/payment")
async def get_payment_settings(_=Depends(require_roles("admin"))):
    return await _payment_view()

@api.put("/admin/settings/payment")
async def save_payment_settings(data: PaymentSettingsIn, user=Depends(require_roles("admin"))):
    upd = {"razorpay_key_id": data.razorpay_key_id.strip(), "updated_at": now_iso(), "updated_by": user["id"]}
    if data.razorpay_key_secret:
        upd["razorpay_key_secret"] = data.razorpay_key_secret.strip()
    if data.razorpay_webhook_secret is not None:
        upd["razorpay_webhook_secret"] = data.razorpay_webhook_secret.strip()
    await db.settings.update_one({"key": "payment"}, {"$set": upd}, upsert=True)
    return await _payment_view()

@api.post("/admin/settings/payment/webhook-secret")
async def generate_webhook_secret(_=Depends(require_roles("admin"))):
    sec = secrets.token_urlsafe(32)
    await db.settings.update_one({"key": "payment"}, {"$set": {"razorpay_webhook_secret": sec, "updated_at": now_iso()}}, upsert=True)
    return {"razorpay_webhook_secret": sec}

@api.post("/admin/settings/payment/test")
async def test_payment_settings(_=Depends(require_roles("admin"))):
    c, _k, _w = await get_rzp()
    if not c:
        raise HTTPException(400, "Razorpay keys are not configured")
    try:
        await asyncio.to_thread(c.order.all, {"count": 1})
    except Exception:
        raise HTTPException(400, "Razorpay rejected these keys. Check Key ID and Secret.")
    return {"ok": True}

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
    await _seed_sectional_mocks()
    await _seed_extras()
    await seed_pages(db)
    await _seed_subjects()
    await ensure_email_indexes(db)

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

SECTION_SEED = {
    "Quantitative Aptitude": [
        ("A shopkeeper sells an item for ₹550 at 10% profit. What is the cost price?", ["₹480", "₹495", "₹500", "₹505"], "C", "CP = 550 / 1.1 = 500"),
        ("The average of 5 numbers is 24. If one number is removed, the average becomes 25. The removed number is:", ["18", "20", "22", "24"], "B", "Total 120 − (4 × 25) = 20"),
        ("A can finish a work in 12 days and B in 18 days. Together they finish it in:", ["6.8 days", "7.2 days", "7.5 days", "8 days"], "B", "1/12 + 1/18 = 5/36 → 36/5 = 7.2 days"),
        ("Simple interest on ₹4000 at 5% per annum for 3 years is:", ["₹500", "₹550", "₹600", "₹650"], "C", "SI = 4000 × 5 × 3 / 100 = 600"),
    ],
    "Reasoning Ability": [
        ("Find the next term: 2, 6, 12, 20, 30, ?", ["40", "42", "44", "46"], "B", "Differences 4, 6, 8, 10, 12 → 42"),
        ("If CAT is coded as DBU, how is DOG coded?", ["EPH", "EOH", "FPH", "EPG"], "A", "Each letter shifts +1"),
        ("Pointing to a man, Riya says 'He is the son of my grandfather's only son.' The man is Riya's:", ["Cousin", "Uncle", "Brother", "Father"], "C", "Grandfather's only son is her father; his son is her brother"),
        ("Which one is the odd one out?", ["Square", "Triangle", "Circle", "Rectangle"], "C", "Circle has no straight sides"),
    ],
    "English Language": [
        ("Choose the synonym of 'ABUNDANT':", ["Scarce", "Plentiful", "Rare", "Meagre"], "B", "Abundant means existing in large quantities"),
        ("Choose the antonym of 'OBSCURE':", ["Vague", "Hidden", "Clear", "Dim"], "C", "Obscure means unclear; the opposite is clear"),
        ("Fill in the blank: She has been working here ___ 2019.", ["for", "since", "from", "by"], "B", "'Since' is used with a point in time"),
        ("Identify the correctly spelt word:", ["Accomodate", "Acommodate", "Accommodate", "Acomodate"], "C", "Accommodate has double c and double m"),
    ],
    "General Awareness": [
        ("Who is known as the 'Father of the Indian Constitution'?", ["Mahatma Gandhi", "B. R. Ambedkar", "Jawaharlal Nehru", "Sardar Patel"], "B", "Dr. B. R. Ambedkar chaired the Drafting Committee"),
        ("The Reserve Bank of India was established in:", ["1935", "1947", "1950", "1969"], "A", "RBI was established on 1 April 1935"),
        ("Which planet is known as the Red Planet?", ["Venus", "Jupiter", "Mars", "Saturn"], "C", "Iron oxide gives Mars its red colour"),
        ("The headquarters of the International Monetary Fund is in:", ["Geneva", "New York", "Paris", "Washington, D.C."], "D", "IMF is headquartered in Washington, D.C."),
    ],
}

async def _seed_sectional_mocks():
    """Idempotently add two demo mocks that use exam sections."""
    if await db.tests.find_one({"title": "SBI PO Prelims · Sectional Mock 1"}):
        return
    ssc = await db.test_series.find_one({"title": "SSC CGL 2026 Full Mock Series"}, {"_id": 0})
    sbi = await db.test_series.find_one({"title": "SBI PO Prelims Sprint"}, {"_id": 0})
    if not ssc or not sbi:
        return
    by_section = {}
    for name, items in SECTION_SEED.items():
        docs = [{"id": gen_id(), "text": text, "type": "mcq_single",
                 "options": [{"key": k, "text": o} for k, o in zip("ABCD", opts)], "correct": [ans], "explanation": expl,
                 "difficulty": "medium", "language": "en", "positive_marks": 1.0, "negative_marks": 0.25,
                 "category_id": ssc.get("category_id"), "created_at": now_iso()} for text, opts, ans, expl in items]
        await db.questions.insert_many(docs)
        by_section[name] = [d["id"] for d in docs]
    mocks = [
        (ssc["id"], "SSC CGL Tier I · Sectional Mock 1", False, 60, list(SECTION_SEED)),
        (sbi["id"], "SBI PO Prelims · Sectional Mock 1", True, None, ["English Language", "Quantitative Aptitude", "Reasoning Ability"]),
    ]
    for series_id, title, timed, duration, names in mocks:
        data = {"series_id": series_id, "title": title, "duration_minutes": duration or 0, "total_marks": None, "passing_marks": None,
                "instructions": "Sections have their own timer. You cannot return to a section once it ends." if timed else "Move freely between sections within the overall time.",
                "question_ids": [], "is_published": True, "sectional_timing": timed,
                "sections": [{"name": n, "duration_minutes": 5 if timed else None, "question_ids": by_section[n]} for n in names]}
        await db.tests.insert_one({"id": gen_id(), **(await _prepare_test(data)), "created_at": now_iso()})
    log.info("Seeded sectional mocks")

HINDI_SEED = {
    "A shopkeeper sells an item for ₹550 at 10% profit. What is the cost price?": ("एक दुकानदार 10% लाभ पर एक वस्तु ₹550 में बेचता है। क्रय मूल्य क्या है?", None, "क्रय मूल्य = 550 / 1.1 = 500"),
    "The average of 5 numbers is 24. If one number is removed, the average becomes 25. The removed number is:": ("5 संख्याओं का औसत 24 है। एक संख्या हटाने पर औसत 25 हो जाता है। हटाई गई संख्या है:", None, "कुल 120 − (4 × 25) = 20"),
    "A can finish a work in 12 days and B in 18 days. Together they finish it in:": ("A किसी काम को 12 दिनों में और B 18 दिनों में पूरा कर सकता है। दोनों मिलकर इसे कितने दिनों में पूरा करेंगे?", ["6.8 दिन", "7.2 दिन", "7.5 दिन", "8 दिन"], "1/12 + 1/18 = 5/36 → 36/5 = 7.2 दिन"),
    "Simple interest on ₹4000 at 5% per annum for 3 years is:": ("₹4000 पर 5% वार्षिक दर से 3 वर्ष का साधारण ब्याज है:", None, "साधारण ब्याज = 4000 × 5 × 3 / 100 = 600"),
    "Who is known as the 'Father of the Indian Constitution'?": ("'भारतीय संविधान के जनक' के रूप में किसे जाना जाता है?", ["महात्मा गांधी", "बी. आर. अम्बेडकर", "जवाहरलाल नेहरू", "सरदार पटेल"], "डॉ. बी. आर. अम्बेडकर प्रारूप समिति के अध्यक्ष थे"),
    "The Reserve Bank of India was established in:": ("भारतीय रिज़र्व बैंक की स्थापना किस वर्ष हुई थी?", None, "RBI की स्थापना 1 अप्रैल 1935 को हुई"),
    "Which planet is known as the Red Planet?": ("किस ग्रह को लाल ग्रह कहा जाता है?", ["शुक्र", "बृहस्पति", "मंगल", "शनि"], "आयरन ऑक्साइड के कारण मंगल लाल दिखाई देता है"),
    "The headquarters of the International Monetary Fund is in:": ("अंतर्राष्ट्रीय मुद्रा कोष (IMF) का मुख्यालय कहाँ है?", ["जिनेवा", "न्यूयॉर्क", "पेरिस", "वाशिंगटन, डी.सी."], "IMF का मुख्यालय वाशिंगटन, डी.सी. में है"),
}
LIVE_TITLE = "All-India Live Mock · SSC CGL #1"

async def _seed_extras():
    """Idempotent demo data: Hindi translations, a scheduled live mock, a welcome coupon."""
    for text, (hi, opts_hi, expl_hi) in HINDI_SEED.items():
        q = await db.questions.find_one({"text": text, "text_hi": None}, {"_id": 0, "id": 1, "options": 1})
        if q:
            opts = [{**o, "text_hi": opts_hi[i] if opts_hi else None} for i, o in enumerate(q["options"])]
            await db.questions.update_one({"id": q["id"]}, {"$set": {"text_hi": hi, "explanation_hi": expl_hi, "options": opts}})
    if not await db.tests.find_one({"title": LIVE_TITLE}):
        src = await db.tests.find_one({"title": "SSC CGL Tier I · Sectional Mock 1"}, {"_id": 0})
        if src:
            start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
            await db.tests.insert_one({**src, "id": gen_id(), "title": LIVE_TITLE, "live_start_at": start.isoformat(),
                                       "live_window_minutes": 120, "created_at": now_iso(),
                                       "instructions": "All-India live mock. Opens for everyone at the scheduled time."})
    if not await db.coupons.find_one({"code": "WELCOME20"}):
        await db.coupons.insert_one({"id": gen_id(), "code": "WELCOME20", "discount_type": "percent", "value": 20, "max_uses": None,
                                     "valid_until": None, "item_ids": [], "active": True, "used_count": 0,
                                     "description": "20% off your first purchase", "created_at": now_iso()})

@app.on_event("shutdown")
async def shutdown():
    client.close()

SEED_SUBJECTS = {
    "SSC CGL": ["Quantitative Aptitude", "General Intelligence & Reasoning", "English Comprehension", "General Awareness"],
    "Banking (SBI/IBPS PO)": ["Quantitative Aptitude", "Reasoning Ability", "English Language"],
    "UPSC Civil Services": ["History", "Polity", "Geography", "Economy"],
    "Railways RRB NTPC": ["Mathematics", "General Intelligence & Reasoning", "General Awareness"],
    "NEET / JEE": ["Physics", "Chemistry", "Biology", "Mathematics"],
}

async def _seed_subjects():
    """Seed default subjects once and tag untagged questions using their test section names."""
    if await db.subjects.count_documents({}) == 0:
        async for c in db.categories.find({}, {"_id": 0, "id": 1, "name": 1}):
            for name in SEED_SUBJECTS.get(c["name"], []):
                await db.subjects.insert_one({"id": gen_id(), "name": name, "category_id": c["id"], "created_at": now_iso()})
    subs = {(x["category_id"], x["name"].lower()): x["id"] async for x in db.subjects.find({}, {"_id": 0})}
    series_cat = {x["id"]: x.get("category_id") async for x in db.test_series.find({}, {"_id": 0, "id": 1, "category_id": 1})}
    async for t in db.tests.find({"sections.1": {"$exists": True}}, {"_id": 0, "series_id": 1, "sections": 1}):
        for sec in t["sections"]:
            cid = series_cat.get(t["series_id"])
            if not cid or sec["name"].strip().lower() == "general":
                continue
            sid = subs.get((cid, sec["name"].strip().lower()))
            if not sid:
                sid = gen_id()
                await db.subjects.insert_one({"id": sid, "name": sec["name"].strip(), "category_id": cid, "created_at": now_iso()})
                subs[(cid, sec["name"].strip().lower())] = sid
            await db.questions.update_many({"id": {"$in": sec["question_ids"]}, "subject_id": None}, {"$set": {"subject_id": sid}})

app.include_router(api)
app.include_router(build_site_router(db, require_roles))
app.include_router(build_admin_router(db, require_roles, hash_pw, _detach_questions))

async def _brand_name() -> str:
    doc = await db.settings.find_one({"key": "site"}, {"_id": 0, "header.brand_name": 1}) or {}
    return (doc.get("header") or {}).get("brand_name") or "ExamForge"

app.include_router(build_email_router(db, require_roles, _brand_name, hash_pw))
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.add_middleware(PublicCacheMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=800)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
