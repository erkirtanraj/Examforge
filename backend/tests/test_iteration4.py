"""Backend tests for Iteration 4:
Live mocks, Discount coupons (admin CRUD + checkout + one-use), Weak-topic report,
Bilingual questions (seed + import + attempt safety)."""
import os, io, csv, uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient


def _read_env(path, key, default=None):
    try:
        for line in open(path):
            if line.startswith(key + "="):
                return line.strip().split("=", 1)[1].strip('"').strip("'")
    except Exception:
        pass
    return default


BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_env("/app/frontend/.env", "REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"
MONGO_URL = _read_env("/app/backend/.env", "MONGO_URL", "mongodb://localhost:27017")
DB_NAME = _read_env("/app/backend/.env", "DB_NAME", "test_database")
mdb = MongoClient(MONGO_URL)[DB_NAME]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


def _register(email, password, name="Test User"):
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": password, "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="module")
def admin():
    t, u = _login("admin@lms.com", "admin123")
    return {"token": t, "user": u, "h": {"Authorization": f"Bearer {t}"}}


@pytest.fixture(scope="module")
def teacher():
    t, u = _login("teacher@lms.com", "teacher123")
    return {"token": t, "user": u, "h": {"Authorization": f"Bearer {t}"}}


@pytest.fixture(scope="module")
def student():
    t, u = _login("student@lms.com", "student123")
    return {"token": t, "user": u, "h": {"Authorization": f"Bearer {t}"}}


# =============== LIVE MOCKS ===============
class TestLiveMocks:
    created_tests = []

    def test_live_mocks_includes_seeded(self):
        r = requests.get(f"{API}/live-mocks", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "server_now" in data and "mocks" in data
        titles = [m["title"] for m in data["mocks"]]
        assert "All-India Live Mock · SSC CGL #1" in titles
        m = next(x for x in data["mocks"] if x["title"] == "All-India Live Mock · SSC CGL #1")
        assert m["status"] in ("upcoming", "live")
        # Should be upcoming (seeded ~2 days ahead)
        start = datetime.fromisoformat(m["live_start_at"])
        assert start > datetime.now(timezone.utc)
        assert m["series"]["title"] == "SSC CGL 2026 Full Mock Series"

    def test_start_before_live_returns_403(self, student):
        r = requests.get(f"{API}/live-mocks", timeout=15).json()
        m = next(x for x in r["mocks"] if x["title"] == "All-India Live Mock · SSC CGL #1")
        r2 = requests.post(f"{API}/tests/{m['id']}/start", headers=student["h"], timeout=15)
        assert r2.status_code == 403
        assert "hasn't opened" in r2.text or "live mock" in r2.text.lower()

    def test_admin_edit_live_start_past_allows_start_then_restore(self, admin, student):
        # Fetch the seeded test
        all_tests = requests.get(f"{API}/admin/tests", headers=admin["h"]).json()
        t = next(x for x in all_tests if x["title"] == "All-India Live Mock · SSC CGL #1")
        original_start = t["live_start_at"]
        try:
            past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            body = {**t, "live_start_at": past, "live_window_minutes": 120}
            # Strip server-only fields
            for k in ("_id", "id", "created_at", "updated_at", "total_marks"):
                body.pop(k, None)
            body["series_id"] = t["series_id"]
            r = requests.put(f"{API}/content/tests/{t['id']}", json=body, headers=admin["h"], timeout=15)
            assert r.status_code == 200, r.text
            # Now student should be able to start
            r2 = requests.post(f"{API}/tests/{t['id']}/start", headers=student["h"], timeout=15)
            # Student may or may not have access depending on series (SSC series is free); should succeed
            assert r2.status_code == 200, r2.text
            # Live-mocks should show status=live
            lm = requests.get(f"{API}/live-mocks").json()
            found = next((x for x in lm["mocks"] if x["id"] == t["id"]), None)
            assert found and found["status"] == "live"
        finally:
            # Restore
            body = {**t, "live_start_at": original_start, "live_window_minutes": 120}
            for k in ("_id", "id", "created_at", "updated_at", "total_marks"):
                body.pop(k, None)
            r = requests.put(f"{API}/content/tests/{t['id']}", json=body, headers=admin["h"], timeout=15)
            assert r.status_code == 200

    def test_invalid_live_start_datetime_422(self, admin):
        all_tests = requests.get(f"{API}/admin/tests", headers=admin["h"]).json()
        t = next(x for x in all_tests if x["title"] == "All-India Live Mock · SSC CGL #1")
        body = {**t, "live_start_at": "not-a-date"}
        for k in ("_id", "id", "created_at", "updated_at", "total_marks"):
            body.pop(k, None)
        r = requests.put(f"{API}/content/tests/{t['id']}", json=body, headers=admin["h"], timeout=15)
        assert r.status_code == 422

    def test_clear_live_start_makes_normal_test(self, admin, student):
        # Create a fresh test so we don't permanently alter the seed
        qs = requests.get(f"{API}/admin/tests", headers=admin["h"]).json()
        src = next(x for x in qs if x["title"] == "All-India Live Mock · SSC CGL #1")
        new_body = {"series_id": src["series_id"], "title": f"TEST_live_clear_{uuid.uuid4().hex[:6]}",
                    "duration_minutes": 60, "question_ids": src["question_ids"][:3], "is_published": True,
                    "live_start_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
                    "live_window_minutes": 60, "sections": [], "sectional_timing": False, "instructions": ""}
        r = requests.post(f"{API}/tests", json=new_body, headers=admin["h"], timeout=15)
        assert r.status_code == 200, r.text
        new_t = r.json()
        TestLiveMocks.created_tests.append(new_t["id"])
        # Before clearing: student should get 403
        r2 = requests.post(f"{API}/tests/{new_t['id']}/start", headers=student["h"])
        assert r2.status_code == 403
        # Clear live_start_at
        new_body["live_start_at"] = None
        r3 = requests.put(f"{API}/content/tests/{new_t['id']}", json=new_body, headers=admin["h"])
        assert r3.status_code == 200
        assert r3.json().get("live_start_at") in (None, "")
        # Now start works
        r4 = requests.post(f"{API}/tests/{new_t['id']}/start", headers=student["h"])
        assert r4.status_code == 200, r4.text

    @classmethod
    def teardown_class(cls):
        for tid in cls.created_tests:
            mdb.tests.delete_one({"id": tid})
            mdb.test_attempts.delete_many({"test_id": tid})


# =============== COUPONS ADMIN ===============
class TestCouponsAdmin:
    created = []
    upsc_series_id = None

    @classmethod
    def setup_class(cls):
        s = mdb.test_series.find_one({"title": "UPSC Prelims Test Series"}, {"id": 1})
        cls.upsc_series_id = s["id"]

    def test_student_cannot_list_coupons(self, student):
        r = requests.get(f"{API}/admin/coupons", headers=student["h"])
        assert r.status_code == 403

    def test_create_percent_coupon(self, admin):
        code = f"TESTP{uuid.uuid4().hex[:6].upper()}"
        body = {"code": code, "discount_type": "percent", "value": 15, "max_uses": 10,
                "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "item_ids": [self.upsc_series_id], "active": True, "description": "test"}
        r = requests.post(f"{API}/admin/coupons", json=body, headers=admin["h"])
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["code"] == code and c["value"] == 15 and c["used_count"] == 0
        TestCouponsAdmin.created.append(c["id"])

    def test_create_flat_coupon(self, admin):
        code = f"TESTF{uuid.uuid4().hex[:6].upper()}"
        body = {"code": code, "discount_type": "flat", "value": 100, "max_uses": None,
                "valid_until": None, "item_ids": [], "active": True, "description": ""}
        r = requests.post(f"{API}/admin/coupons", json=body, headers=admin["h"])
        assert r.status_code == 200
        TestCouponsAdmin.created.append(r.json()["id"])

    def test_duplicate_code_rejected(self, admin):
        code = f"TESTD{uuid.uuid4().hex[:6].upper()}"
        body = {"code": code, "discount_type": "percent", "value": 10, "item_ids": [], "active": True}
        r = requests.post(f"{API}/admin/coupons", json=body, headers=admin["h"])
        assert r.status_code == 200
        TestCouponsAdmin.created.append(r.json()["id"])
        r2 = requests.post(f"{API}/admin/coupons", json=body, headers=admin["h"])
        assert r2.status_code == 400

    def test_invalid_code_format_422(self, admin):
        body = {"code": "a b", "discount_type": "percent", "value": 10, "item_ids": [], "active": True}
        r = requests.post(f"{API}/admin/coupons", json=body, headers=admin["h"])
        # Code is normalized (spaces stripped) → "AB" which is only 2 chars → fails length check
        assert r.status_code == 422

    def test_percent_over_100_rejected(self, admin):
        body = {"code": f"TESTX{uuid.uuid4().hex[:5].upper()}", "discount_type": "percent", "value": 150,
                "item_ids": [], "active": True}
        r = requests.post(f"{API}/admin/coupons", json=body, headers=admin["h"])
        assert r.status_code == 422

    def test_update_coupon(self, admin):
        code = f"TESTU{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{API}/admin/coupons", json={"code": code, "discount_type": "percent", "value": 10,
                                                         "item_ids": [], "active": True}, headers=admin["h"])
        cid = r.json()["id"]
        TestCouponsAdmin.created.append(cid)
        r2 = requests.put(f"{API}/admin/coupons/{cid}", json={"code": code, "discount_type": "percent",
                                                               "value": 25, "item_ids": [], "active": False},
                          headers=admin["h"])
        assert r2.status_code == 200
        assert r2.json()["value"] == 25 and r2.json()["active"] is False

    def test_delete_coupon(self, admin):
        code = f"TESTR{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{API}/admin/coupons", json={"code": code, "discount_type": "percent", "value": 10,
                                                         "item_ids": [], "active": True}, headers=admin["h"])
        cid = r.json()["id"]
        r2 = requests.delete(f"{API}/admin/coupons/{cid}", headers=admin["h"])
        assert r2.status_code == 200
        r3 = requests.delete(f"{API}/admin/coupons/{cid}", headers=admin["h"])
        assert r3.status_code == 404

    @classmethod
    def teardown_class(cls):
        for cid in cls.created:
            mdb.coupons.delete_one({"id": cid})


# =============== COUPON CHECKOUT ===============
class TestCouponCheckout:
    upsc_series_id = None
    created_orders = []
    created_coupons = []
    temp_users = []

    @classmethod
    def setup_class(cls):
        s = mdb.test_series.find_one({"title": "UPSC Prelims Test Series"}, {"id": 1, "price": 1})
        cls.upsc_series_id = s["id"]
        cls.upsc_price = s["price"]
        assert cls.upsc_price == 99900

    def _fresh_user(self):
        email = f"TEST_cp_{uuid.uuid4().hex[:8]}@test.lms"
        t, u = _register(email, "pass1234", "Coupon Tester")
        TestCouponCheckout.temp_users.append(u["id"])
        return {"token": t, "user": u, "h": {"Authorization": f"Bearer {t}"}}

    def test_welcome20_applies(self):
        u = self._fresh_user()
        r = requests.post(f"{API}/orders",
                          json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": "WELCOME20"},
                          headers=u["h"])
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["amount"] == 79920, o
        assert o["coupon_code"] == "WELCOME20"
        assert o["discount"] == 19980
        assert o["original_amount"] == 99900
        assert o["demo_mode"] is True
        TestCouponCheckout.created_orders.append(o["id"])

    def test_invalid_code_errors(self):
        u = self._fresh_user()
        r = requests.post(f"{API}/orders",
                          json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": "NOPE_NOPE"},
                          headers=u["h"])
        assert r.status_code == 400

    def test_inactive_code_errors(self, admin):
        code = f"TESTI{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{API}/admin/coupons", json={"code": code, "discount_type": "percent", "value": 10,
                                                         "item_ids": [], "active": False}, headers=admin["h"])
        TestCouponCheckout.created_coupons.append(r.json()["id"])
        u = self._fresh_user()
        r2 = requests.post(f"{API}/orders",
                           json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": code},
                           headers=u["h"])
        assert r2.status_code == 400

    def test_expired_code_errors(self, admin):
        code = f"TESTE{uuid.uuid4().hex[:6].upper()}"
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        r = requests.post(f"{API}/admin/coupons", json={"code": code, "discount_type": "percent", "value": 10,
                                                         "valid_until": past, "item_ids": [], "active": True},
                          headers=admin["h"])
        TestCouponCheckout.created_coupons.append(r.json()["id"])
        u = self._fresh_user()
        r2 = requests.post(f"{API}/orders",
                           json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": code},
                           headers=u["h"])
        assert r2.status_code == 400
        assert "expired" in r2.text.lower()

    def test_used_up_code_errors(self, admin):
        code = f"TESTM{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{API}/admin/coupons", json={"code": code, "discount_type": "percent", "value": 10,
                                                         "max_uses": 1, "item_ids": [], "active": True},
                          headers=admin["h"])
        cid = r.json()["id"]
        TestCouponCheckout.created_coupons.append(cid)
        # Fake it: set used_count = 1
        mdb.coupons.update_one({"id": cid}, {"$set": {"used_count": 1}})
        u = self._fresh_user()
        r2 = requests.post(f"{API}/orders",
                           json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": code},
                           headers=u["h"])
        assert r2.status_code == 400
        assert "limit" in r2.text.lower() or "used" in r2.text.lower()

    def test_not_applicable_item(self, admin):
        # Coupon only valid for a specific OTHER series
        other = mdb.test_series.find_one({"title": "SBI PO Prelims Sprint"}, {"id": 1})
        code = f"TESTN{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{API}/admin/coupons",
                          json={"code": code, "discount_type": "percent", "value": 10,
                                "item_ids": [other["id"]], "active": True}, headers=admin["h"])
        TestCouponCheckout.created_coupons.append(r.json()["id"])
        u = self._fresh_user()
        r2 = requests.post(f"{API}/orders",
                           json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": code},
                           headers=u["h"])
        assert r2.status_code == 400
        assert "valid" in r2.text.lower() or "applicable" in r2.text.lower() or "isn't" in r2.text.lower()

    def test_100_percent_coupon_free_enrollment_and_one_use(self, admin):
        code = f"TESTFREE{uuid.uuid4().hex[:4].upper()}"
        r = requests.post(f"{API}/admin/coupons",
                          json={"code": code, "discount_type": "percent", "value": 100,
                                "item_ids": [self.upsc_series_id], "active": True}, headers=admin["h"])
        cid = r.json()["id"]
        TestCouponCheckout.created_coupons.append(cid)
        u = self._fresh_user()
        r2 = requests.post(f"{API}/orders",
                           json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": code},
                           headers=u["h"])
        assert r2.status_code == 200, r2.text
        o = r2.json()
        assert o["amount"] == 0 and o["status"] == "paid"
        assert o["coupon_code"] == code
        # Entitlement granted
        ent = mdb.entitlements.find_one({"user_id": u["user"]["id"], "item_id": self.upsc_series_id})
        assert ent is not None
        # used_count incremented
        c = mdb.coupons.find_one({"id": cid})
        assert c["used_count"] == 1
        # Second use → "already used"
        r3 = requests.post(f"{API}/orders",
                           json={"item_type": "test_series", "item_id": self.upsc_series_id, "coupon_code": code},
                           headers=u["h"])
        assert r3.status_code == 400
        assert "already" in r3.text.lower()

    def test_coupons_validate_endpoint(self):
        u = self._fresh_user()
        r = requests.post(f"{API}/coupons/validate",
                          json={"item_type": "test_series", "item_id": self.upsc_series_id, "code": "WELCOME20"},
                          headers=u["h"])
        assert r.status_code == 200
        d = r.json()
        assert d["code"] == "WELCOME20" and d["original"] == 99900 and d["final_amount"] == 79920

    @classmethod
    def teardown_class(cls):
        for oid in cls.created_orders:
            mdb.orders.delete_one({"id": oid})
        for cid in cls.created_coupons:
            mdb.coupons.delete_one({"id": cid})
        for uid in cls.temp_users:
            mdb.orders.delete_many({"user_id": uid})
            mdb.entitlements.delete_many({"user_id": uid})
            mdb.users.delete_one({"id": uid})


# =============== WEAK TOPICS ===============
class TestWeakTopics:
    def test_student_weak_topics(self, student):
        r = requests.get(f"{API}/my/weak-topics", headers=student["h"])
        assert r.status_code == 200
        data = r.json()
        assert "topics" in data and "results_analyzed" in data
        # Student is known to have at least one sectional result
        if data["results_analyzed"] > 0:
            assert len(data["topics"]) > 0
            # sorted ascending by score_pct
            scores = [t["score_pct"] for t in data["topics"]]
            assert scores == sorted(scores)
            for t in data["topics"]:
                assert t["level"] in ("weak", "average", "strong")
                assert "accuracy" in t and "attempts" in t and "suggestions" in t
                for sug in t["suggestions"]:
                    assert "test_id" in sug and "has_access" in sug and "attempted" in sug

    def test_fresh_student_empty(self):
        email = f"TEST_wk_{uuid.uuid4().hex[:8]}@test.lms"
        t, u = _register(email, "pass1234", "Fresh Wk")
        try:
            r = requests.get(f"{API}/my/weak-topics", headers={"Authorization": f"Bearer {t}"})
            assert r.status_code == 200
            d = r.json()
            assert d["results_analyzed"] == 0 and d["topics"] == []
        finally:
            mdb.users.delete_one({"id": u["id"]})

    def test_suggestions_exclude_future_live_mocks(self, student):
        r = requests.get(f"{API}/my/weak-topics", headers=student["h"]).json()
        for t in r["topics"]:
            for sug in t["suggestions"]:
                test_doc = mdb.tests.find_one({"id": sug["test_id"]}, {"live_start_at": 1})
                if test_doc and test_doc.get("live_start_at"):
                    start = datetime.fromisoformat(test_doc["live_start_at"])
                    assert start <= datetime.now(timezone.utc), f"Future live mock {sug['test_id']} in suggestions"


# =============== BILINGUAL ===============
class TestBilingual:
    def test_hindi_seed_present(self):
        q = mdb.questions.find_one({"text": "Which planet is known as the Red Planet?"})
        assert q is not None
        assert q.get("text_hi") == "किस ग्रह को लाल ग्रह कहा जाता है?"
        assert q.get("explanation_hi")
        # Options have text_hi
        hi_opts = [o for o in q["options"] if o.get("text_hi")]
        assert len(hi_opts) == 4

    def test_attempt_does_not_expose_explanation_hi_or_correct(self, student):
        # Start the SSC sectional mock (free)
        tests = mdb.tests.find({"title": "SSC CGL Tier I · Sectional Mock 1"})
        t = next(tests, None)
        assert t
        r = requests.post(f"{API}/tests/{t['id']}/start", headers=student["h"])
        assert r.status_code == 200
        attempt_id = r.json()["id"]
        r2 = requests.get(f"{API}/attempts/{attempt_id}", headers=student["h"])
        assert r2.status_code == 200
        a = r2.json()
        if a.get("status") == "in_progress":
            for q in a.get("questions", []):
                assert "correct" not in q
                assert "explanation" not in q
                assert "explanation_hi" not in q
                # text_hi IS allowed to be exposed (for Hindi UI)

    def test_import_with_hindi_columns(self, admin):
        buf = io.StringIO()
        w = csv.writer(buf)
        headers = ["text", "type", "option_a", "option_b", "option_c", "option_d", "correct",
                   "question_hi", "option_a_hi", "option_b_hi", "option_c_hi", "option_d_hi",
                   "explanation", "explanation_hi"]
        w.writerow(headers)
        w.writerow(["TEST_Capital of India?", "mcq_single", "Delhi", "Mumbai", "Kolkata", "Chennai", "A",
                    "भारत की राजधानी?", "दिल्ली", "मुंबई", "कोलकाता", "चेन्नई",
                    "New Delhi is the capital", "नई दिल्ली राजधानी है"])
        # true_false
        w.writerow(["TEST_Earth is round.", "true_false", "", "", "", "", "A",
                    "पृथ्वी गोल है।", "", "", "", "",
                    "Earth is roughly spherical", "पृथ्वी लगभग गोलाकार है"])
        content = buf.getvalue().encode("utf-8")
        files = {"file": ("hi.csv", content, "text/csv")}
        data = {"commit": "true"}
        r = requests.post(f"{API}/questions/import", files=files, data=data, headers=admin["h"])
        assert r.status_code == 200, r.text
        rj = r.json()
        batch_id = rj.get("batch_id")
        assert batch_id and rj.get("inserted", 0) >= 2
        try:
            # Verify Hindi stored
            q1 = mdb.questions.find_one({"text": "TEST_Capital of India?"})
            assert q1 and q1.get("text_hi") == "भारत की राजधानी?"
            assert q1.get("explanation_hi") == "नई दिल्ली राजधानी है"
            opt_hi = {o["key"]: o.get("text_hi") for o in q1["options"]}
            assert opt_hi.get("A") == "दिल्ली"
            # true_false gets Hindi option labels
            q2 = mdb.questions.find_one({"text": "TEST_Earth is round."})
            assert q2 and q2.get("text_hi") == "पृथ्वी गोल है।"
            tf_hi = {o["key"]: o.get("text_hi") for o in q2["options"]}
            assert tf_hi.get("A") == "सत्य" and tf_hi.get("B") == "असत्य"
        finally:
            # Undo
            requests.delete(f"{API}/questions/import/{batch_id}", headers=admin["h"])

    def test_import_template_has_hindi_columns(self, admin):
        r = requests.get(f"{API}/questions/import/template", headers=admin["h"])
        # Template may be .csv under different paths; let's just check if endpoint exists
        if r.status_code in (404, 405):
            pytest.skip("No backend template endpoint (template generated client-side)")
        assert r.status_code == 200
        content = r.text if "text" in r.headers.get("content-type", "") else r.content.decode("utf-8", "ignore")
        assert "question_hi" in content or "text_hi" in content.lower()
