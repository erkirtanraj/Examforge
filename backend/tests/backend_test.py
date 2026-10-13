"""Backend tests for LMS iteration 2 (admin content, auth, payments, ranks)."""
import os, time, json, hmac, hashlib, uuid
import pytest
import requests
from pymongo import MongoClient

def _read_env(path, key, default=None):
    try:
        for line in open(path):
            if line.startswith(key + "="):
                return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return default

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_env("/app/frontend/.env", "REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# Try reading backend .env if MONGO_URL not set in environment
if "MONGO_URL" not in os.environ:
    try:
        for line in open("/app/backend/.env"):
            if line.startswith("MONGO_URL="):
                MONGO_URL = line.strip().split("=", 1)[1]
            if line.startswith("DB_NAME="):
                DB_NAME = line.strip().split("=", 1)[1]
    except Exception:
        pass

mclient = MongoClient(MONGO_URL)
mdb = mclient[DB_NAME]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="session")
def admin():
    t, u = _login("admin@lms.com", "admin123")
    return {"token": t, "user": u, "h": {"Authorization": f"Bearer {t}"}}


@pytest.fixture(scope="session")
def teacher():
    t, u = _login("teacher@lms.com", "teacher123")
    return {"token": t, "user": u, "h": {"Authorization": f"Bearer {t}"}}


@pytest.fixture(scope="session")
def student():
    t, u = _login("student@lms.com", "student123")
    return {"token": t, "user": u, "h": {"Authorization": f"Bearer {t}"}}


# ------- Auth: Google ---------
class TestGoogleAuth:
    def test_invalid_session_returns_401(self):
        r = requests.post(f"{API}/auth/google", json={"session_id": "bogus-session-id"}, timeout=20)
        assert r.status_code == 401


# ------- Admin stats role scoping ---------
class TestAdminStats:
    def test_admin_sees_revenue(self, admin):
        r = requests.get(f"{API}/admin/stats", headers=admin["h"])
        assert r.status_code == 200
        d = r.json()
        assert "revenue" in d and "orders_paid" in d

    def test_teacher_no_revenue(self, teacher):
        r = requests.get(f"{API}/admin/stats", headers=teacher["h"])
        assert r.status_code == 200
        d = r.json()
        assert "revenue" not in d and "orders_paid" not in d

    def test_student_forbidden(self, student):
        r = requests.get(f"{API}/admin/stats", headers=student["h"])
        assert r.status_code == 403


# ------- Admin settings access ---------
class TestPaymentSettings:
    def test_teacher_cannot_read_settings(self, teacher):
        r = requests.get(f"{API}/admin/settings/payment", headers=teacher["h"])
        assert r.status_code == 403

    def test_student_cannot_read_settings(self, student):
        r = requests.get(f"{API}/admin/settings/payment", headers=student["h"])
        assert r.status_code == 403

    def test_admin_initial_demo_mode(self, admin):
        # ensure clean state - demo mode means no key saved
        mdb.settings.delete_many({"key": "payment"})
        r = requests.get(f"{API}/admin/settings/payment", headers=admin["h"])
        assert r.status_code == 200
        d = r.json()
        assert d["mode"] == "demo"
        assert d["has_secret"] is False

    def test_generate_webhook_secret(self, admin):
        r = requests.post(f"{API}/admin/settings/payment/webhook-secret", headers=admin["h"])
        assert r.status_code == 200
        sec = r.json()["razorpay_webhook_secret"]
        assert len(sec) > 20
        # verify persisted
        r2 = requests.get(f"{API}/admin/settings/payment", headers=admin["h"])
        assert r2.json()["has_webhook_secret"] is True
        assert r2.json()["webhook_secret_hint"].endswith(sec[-4:])
        assert "razorpay_webhook_secret" not in r2.json()

    def test_save_fake_keys_mode_test(self, admin):
        r = requests.put(f"{API}/admin/settings/payment", headers=admin["h"], json={
            "razorpay_key_id": "rzp_test_fake123", "razorpay_key_secret": "fakesecret"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["mode"] == "test"
        assert d["has_secret"] is True
        assert d["secret_hint"].endswith("cret")

    def test_blank_secret_keeps_old(self, admin):
        r = requests.put(f"{API}/admin/settings/payment", headers=admin["h"], json={
            "razorpay_key_id": "rzp_test_fake123", "razorpay_key_secret": ""
        })
        assert r.status_code == 200
        d = r.json()
        assert d["has_secret"] is True  # old secret preserved

    def test_test_connection_fake_keys(self, admin):
        r = requests.post(f"{API}/admin/settings/payment/test", headers=admin["h"])
        assert r.status_code == 400  # Razorpay rejects fake keys

    def test_verify_payment_rejected_when_fake(self, student):
        # Create an order in DB with fake razorpay_order_id
        oid = str(uuid.uuid4())
        mdb.orders.insert_one({
            "id": oid, "user_id": student["user"]["id"], "item_type": "test_series",
            "item_id": "anything", "amount": 1000, "currency": "INR", "status": "created",
            "razorpay_order_id": "order_fake", "receipt": oid[:40], "created_at": "2026-01-01T00:00:00+00:00"
        })
        # verify with wrong signature -> 400 (signature invalid)
        r = requests.post(f"{API}/orders/verify", headers=student["h"], json={
            "razorpay_order_id": "order_fake", "razorpay_payment_id": "pay_x",
            "razorpay_signature": "badsig", "order_id": oid
        })
        assert r.status_code == 400
        # order remains not paid
        row = mdb.orders.find_one({"id": oid})
        assert row["status"] != "paid"
        mdb.orders.delete_one({"id": oid})


# ------- Webhook security ---------
class TestWebhook:
    def test_bad_signature_rejected(self):
        r = requests.post(f"{API}/webhooks/razorpay", headers={"X-Razorpay-Signature": "bad"},
                          data=b'{"event":"payment.captured"}')
        assert r.status_code == 400

    def test_valid_signature_marks_paid(self, student):
        # ensure webhook secret present (configured above)
        s = mdb.settings.find_one({"key": "payment"}) or {}
        wh_secret = s.get("razorpay_webhook_secret")
        assert wh_secret, "Webhook secret should be configured by prior test"
        rp_order_id = f"order_wh_{uuid.uuid4().hex[:8]}"
        oid = str(uuid.uuid4())
        # need a real item for entitlement grant
        series = mdb.test_series.find_one({})
        assert series
        mdb.orders.insert_one({
            "id": oid, "user_id": student["user"]["id"], "item_type": "test_series",
            "item_id": series["id"], "amount": 1000, "currency": "INR", "status": "created",
            "razorpay_order_id": rp_order_id, "receipt": oid[:40],
            "created_at": "2026-01-01T00:00:00+00:00"
        })
        payload = {"event": "payment.captured",
                   "payload": {"payment": {"entity": {"id": "pay_wh1", "order_id": rp_order_id}}}}
        body = json.dumps(payload).encode()
        sig = hmac.new(wh_secret.encode(), body, hashlib.sha256).hexdigest()
        r = requests.post(f"{API}/webhooks/razorpay",
                          headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
                          data=body)
        assert r.status_code == 200
        row = mdb.orders.find_one({"id": oid})
        assert row["status"] == "paid"
        ent = mdb.entitlements.find_one({"order_id": oid})
        assert ent is not None
        # cleanup
        mdb.orders.delete_one({"id": oid})
        mdb.entitlements.delete_many({"order_id": oid})


# ------- Question CRUD (admin content) ---------
class TestQuestionCRUD:
    created_id = None

    def test_create_mcq(self, admin):
        payload = {
            "text": "TEST_What is 2+2?", "type": "mcq_single",
            "options": [{"key": "A", "text": "3"}, {"key": "B", "text": "4"},
                        {"key": "C", "text": "5"}, {"key": "D", "text": "6"}],
            "correct": ["B"], "explanation": "basic math",
            "positive_marks": 2.0, "negative_marks": 0.5, "difficulty": "easy"
        }
        r = requests.post(f"{API}/questions", headers=admin["h"], json=payload)
        assert r.status_code == 200
        d = r.json()
        assert d["correct"] == ["B"]
        assert "id" in d
        TestQuestionCRUD.created_id = d["id"]

    def test_update_question(self, admin):
        qid = TestQuestionCRUD.created_id
        assert qid
        payload = {
            "text": "TEST_What is 2+2? (edited)", "type": "mcq_single",
            "options": [{"key": "A", "text": "3"}, {"key": "B", "text": "4"},
                        {"key": "C", "text": "5"}, {"key": "D", "text": "6"}],
            "correct": ["B"], "positive_marks": 3.0, "negative_marks": 0.0
        }
        r = requests.put(f"{API}/content/questions/{qid}", headers=admin["h"], json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["positive_marks"] == 3.0
        assert "edited" in r.json()["text"]

    def test_student_cannot_delete(self, student):
        qid = TestQuestionCRUD.created_id
        r = requests.delete(f"{API}/content/questions/{qid}", headers=student["h"])
        assert r.status_code == 403

    def test_delete_question(self, admin):
        qid = TestQuestionCRUD.created_id
        r = requests.delete(f"{API}/content/questions/{qid}", headers=admin["h"])
        assert r.status_code == 200


# ------- Test series + Test builder ---------
class TestSeriesAndTests:
    series_id = None
    test_id = None
    q_ids = []

    def test_create_paid_series(self, admin):
        r = requests.post(f"{API}/test-series", headers=admin["h"], json={
            "title": "TEST_Paid Series", "description": "d", "is_free": False,
            "price": 19900, "validity_days": 180
        })
        assert r.status_code == 200
        d = r.json()
        assert d["price"] == 19900
        assert d["is_free"] is False
        TestSeriesAndTests.series_id = d["id"]
        # confirm in public catalog
        pub = requests.get(f"{API}/test-series").json()
        assert any(s["id"] == d["id"] for s in pub)

    def test_create_test_with_questions(self, admin):
        # create 3 questions with 2 marks each
        ids = []
        for i in range(3):
            r = requests.post(f"{API}/questions", headers=admin["h"], json={
                "text": f"TEST_Q{i}", "type": "mcq_single",
                "options": [{"key": "A", "text": "1"}, {"key": "B", "text": "2"},
                            {"key": "C", "text": "3"}, {"key": "D", "text": "4"}],
                "correct": ["A"], "positive_marks": 2.0, "negative_marks": 0.0
            })
            ids.append(r.json()["id"])
        TestSeriesAndTests.q_ids = ids
        r = requests.post(f"{API}/tests", headers=admin["h"], json={
            "series_id": TestSeriesAndTests.series_id, "title": "TEST_Test1",
            "duration_minutes": 30, "question_ids": ids
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_marks"] == 6.0
        TestSeriesAndTests.test_id = d["id"]

    def test_edit_test_recalc_total(self, admin):
        tid = TestSeriesAndTests.test_id
        new_qs = TestSeriesAndTests.q_ids[:2]
        r = requests.put(f"{API}/content/tests/{tid}", headers=admin["h"], json={
            "series_id": TestSeriesAndTests.series_id, "title": "TEST_Test1 edited",
            "duration_minutes": 30, "question_ids": new_qs, "total_marks": None
        })
        assert r.status_code == 200, r.text
        assert r.json()["total_marks"] == 4.0

    def test_delete_series_cascades(self, admin):
        sid = TestSeriesAndTests.series_id
        r = requests.delete(f"{API}/content/test-series/{sid}", headers=admin["h"])
        assert r.status_code == 200
        # Tests of that series should be gone
        rem = requests.get(f"{API}/admin/tests", headers=admin["h"]).json()
        assert not any(t["series_id"] == sid for t in rem)
        # cleanup qs
        for qid in TestSeriesAndTests.q_ids:
            requests.delete(f"{API}/content/questions/{qid}", headers=admin["h"])


# ------- Course builder ---------
class TestCourseBuilder:
    course_id = None
    section_id = None
    lesson_id = None

    def test_create_course_section_lesson(self, admin):
        r = requests.post(f"{API}/courses", headers=admin["h"], json={
            "title": "TEST_Course", "description": "d", "is_free": True
        })
        assert r.status_code == 200
        TestCourseBuilder.course_id = r.json()["id"]
        r = requests.post(f"{API}/sections", headers=admin["h"], json={
            "course_id": TestCourseBuilder.course_id, "title": "TEST_S1", "position": 1
        })
        assert r.status_code == 200
        TestCourseBuilder.section_id = r.json()["id"]
        r = requests.post(f"{API}/lessons", headers=admin["h"], json={
            "section_id": TestCourseBuilder.section_id, "title": "TEST_L1",
            "content_type": "video", "content_url": "https://x.com/v", "position": 1
        })
        assert r.status_code == 200
        TestCourseBuilder.lesson_id = r.json()["id"]
        # verify public course detail
        r = requests.get(f"{API}/courses/{TestCourseBuilder.course_id}")
        assert r.status_code == 200
        d = r.json()
        assert len(d["sections"]) == 1
        assert len(d["sections"][0]["lessons"]) == 1

    def test_delete_section_cascades_lessons(self, admin):
        r = requests.delete(f"{API}/content/sections/{TestCourseBuilder.section_id}",
                            headers=admin["h"])
        assert r.status_code == 200
        r = requests.get(f"{API}/courses/{TestCourseBuilder.course_id}")
        assert all(len(s["lessons"]) == 0 for s in r.json()["sections"])
        requests.delete(f"{API}/content/courses/{TestCourseBuilder.course_id}",
                        headers=admin["h"])


# ------- User role management ---------
class TestUserRole:
    def test_admin_cannot_change_own_role(self, admin):
        r = requests.put(f"{API}/admin/users/{admin['user']['id']}/role",
                         headers=admin["h"], json={"role": "teacher"})
        assert r.status_code == 400

    def test_non_super_cannot_grant_super(self, admin, student):
        r = requests.put(f"{API}/admin/users/{student['user']['id']}/role",
                         headers=admin["h"], json={"role": "super_admin"})
        assert r.status_code == 403

    def test_admin_can_change_other_user_role(self, admin, teacher):
        r = requests.put(f"{API}/admin/users/{teacher['user']['id']}/role",
                         headers=admin["h"], json={"role": "teacher"})
        assert r.status_code == 200


# ------- All-India Rank ---------
class TestRank:
    def test_rank_after_two_submits(self, admin, student):
        # Create 2 extra students
        extras = []
        for i in range(2):
            email = f"TEST_rank_{uuid.uuid4().hex[:6]}@x.com"
            r = requests.post(f"{API}/auth/register", json={
                "name": f"Rank Student {i}", "email": email, "password": "SafePassphrase123!"
            })
            assert r.status_code == 200
            extras.append({"token": r.json()["token"], "user": r.json()["user"],
                           "h": {"Authorization": f"Bearer {r.json()['token']}"}})

        # pick a free SSC test
        series_list = requests.get(f"{API}/test-series").json()
        ssc = next((s for s in series_list if s.get("is_free") and "SSC" in s["title"]), None)
        assert ssc
        tests = requests.get(f"{API}/test-series/{ssc['id']}").json()["tests"]
        test_id = tests[0]["id"]

        # student submits perfect
        results = []
        for cred, correct_frac in [(student, 1.0), (extras[0], 0.5), (extras[1], 0.0)]:
            # start fresh attempt - may need to delete prior
            r = requests.post(f"{API}/tests/{test_id}/start", headers=cred["h"])
            assert r.status_code == 200, r.text
            att = r.json()
            # fetch questions
            full = requests.get(f"{API}/attempts/{att['id']}", headers=cred["h"]).json()
            qs = full["questions"]
            n_correct = int(len(qs) * correct_frac)
            # need actual correct options - fetch via admin
            answers = {}
            for i, q in enumerate(qs):
                if i < n_correct:
                    # we don't know correct answer from student side; cheat by picking admin's view
                    full_q = mdb.questions.find_one({"id": q["id"]})
                    answers[q["id"]] = [full_q["correct"][0]]
                else:
                    answers[q["id"]] = ["Z"]  # wrong
            r = requests.post(f"{API}/attempts/{att['id']}/submit",
                              headers=cred["h"], json={"answers": answers, "marked_for_review": []})
            assert r.status_code == 200, r.text
            results.append((cred, r.json()["attempt_id"]))

        # Check student's result has rank card
        r = requests.get(f"{API}/attempts/{results[0][1]}/result", headers=student["h"])
        assert r.status_code == 200
        rk = r.json().get("rank")
        assert rk is not None
        assert rk["rank"] == 1
        assert rk["total"] >= 3
        assert rk["percentile"] == 100.0
        assert isinstance(rk["top"], list) and len(rk["top"]) >= 3
        # cleanup
        for e in extras:
            mdb.users.delete_one({"id": e["user"]["id"]})
            mdb.test_attempts.delete_many({"user_id": e["user"]["id"]})
            mdb.test_results.delete_many({"user_id": e["user"]["id"]})


# ------- Cleanup fixture: reset payment settings ---------
def teardown_module(module):
    # Keep DB clean - return to demo mode
    mdb.settings.delete_many({"key": "payment"})
    mdb.users.delete_many({"email": {"$regex": "^TEST_"}})
