"""Iteration 9: Admin users, questions pagination/bulk, subjects, test sections marks/language, banner stats, theme."""
import io
import os
import time
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
ADMIN = {"email": "admin@lms.com", "password": "admin123"}
STUDENT = {"email": "student@lms.com", "password": "student123"}

PAGE_SIZES = (10, 50, 100, 500, 1000, 5000)


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def admin():
    d = _login(ADMIN)
    return {"token": d["token"], "user": d["user"], "h": {"Authorization": f"Bearer {d['token']}"}}


@pytest.fixture(scope="module")
def student():
    d = _login(STUDENT)
    return {"token": d["token"], "user": d["user"], "h": {"Authorization": f"Bearer {d['token']}"}}


# ---------------- Theme (A) ----------------
DEFAULT_HEADER = {
    "brand_name": "ExamForge", "logo_url": "", "favicon_url": "", "show_brand_name": True,
    "nav_links": [{"label": "Test Series", "url": "/test-series"}],
    "cta_label": "Get Started", "cta_url": "/register",
}
DEFAULT_FOOTER = {"tagline": "x", "copyright": "y", "links": []}


def _put_layout(theme, h):
    body = {"header": DEFAULT_HEADER, "footer": DEFAULT_FOOTER, "theme": theme}
    return requests.put(f"{BASE_URL}/api/admin/site/layout", json=body, headers=h, timeout=20)


class TestTheme:
    def test_emerald_preset_saves_and_public(self, admin):
        r = _put_layout({"preset": "emerald", "primary": "#059669", "accent": "#a3e635"}, admin["h"])
        assert r.status_code == 200
        assert r.json()["theme"] == {"preset": "emerald", "primary": "#059669", "accent": "#a3e635"}
        pub = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
        assert pub["theme"]["preset"] == "emerald"
        assert pub["theme"]["primary"] == "#059669"

    def test_invalid_hex_rejected(self, admin):
        r = _put_layout({"preset": "custom", "primary": "abc", "accent": "#06b6d4"}, admin["h"])
        assert r.status_code == 422

    def test_restore_ocean(self, admin):
        r = _put_layout({"preset": "ocean", "primary": "#2563eb", "accent": "#06b6d4"}, admin["h"])
        assert r.status_code == 200
        assert r.json()["theme"]["preset"] == "ocean"


# ---------------- Banner stats (B) ----------------
class TestBannerStats:
    def test_stats_shape_and_current(self, admin):
        r = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=admin["h"], timeout=20)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        for row in rows:
            for k in ("views", "clicks", "copies", "closes", "click_rate", "is_current", "version", "message"):
                assert k in row
        assert sum(1 for x in rows if x["is_current"]) <= 1

    def test_event_unknown_version_404(self):
        r = requests.post(f"{BASE_URL}/api/announcement/events",
                          json={"version": "zzz000000000", "type": "view"}, timeout=20)
        assert r.status_code == 404

    def test_event_invalid_type_422(self):
        pub = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
        ann = pub.get("announcement") or {}
        v = ann.get("version") or "zzz000000000"
        r = requests.post(f"{BASE_URL}/api/announcement/events",
                          json={"version": v, "type": "bogus"}, timeout=20)
        assert r.status_code == 422

    def test_events_increment_counters_no_dedupe(self, admin):
        pub = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
        ann = pub.get("announcement")
        if not ann:
            pytest.skip("No current announcement to count against")
        v = ann["version"]
        r0 = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=admin["h"], timeout=20).json()
        base = next((x for x in r0 if x["version"] == v), {"views": 0, "clicks": 0})
        for _ in range(3):
            requests.post(f"{BASE_URL}/api/announcement/events", json={"version": v, "type": "view"}, timeout=10)
            requests.post(f"{BASE_URL}/api/announcement/events", json={"version": v, "type": "click"}, timeout=10)
        r1 = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=admin["h"], timeout=20).json()
        new = next((x for x in r1 if x["version"] == v), None)
        assert new is not None
        assert new["views"] >= base.get("views", 0) + 3
        assert new["clicks"] >= base.get("clicks", 0) + 3

    def test_stats_requires_admin(self, student):
        r = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=student["h"], timeout=20)
        assert r.status_code in (401, 403)


# ---------------- Subjects + question pagination + bulk delete (E) ----------------
@pytest.fixture(scope="module")
def category(admin):
    cats = requests.get(f"{BASE_URL}/api/categories", timeout=20).json()
    assert cats
    return cats[0]


@pytest.fixture(scope="module")
def temp_subject(admin, category):
    body = {"name": f"TEST_sub_{uuid.uuid4().hex[:6]}", "category_id": category["id"]}
    r = requests.post(f"{BASE_URL}/api/subjects", json=body, headers=admin["h"], timeout=20)
    assert r.status_code == 200, r.text
    sub = r.json()
    yield sub
    # subjects have no delete endpoint in the admin router? Check for subject delete via content endpoint
    # Fallback: leave it (not critical)
    requests.delete(f"{BASE_URL}/api/content/subjects/{sub['id']}", headers=admin["h"], timeout=20)


class TestSubjects:
    def test_list_subjects_seeded(self):
        r = requests.get(f"{BASE_URL}/api/subjects", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_subject_and_filter_by_category(self, admin, category, temp_subject):
        r = requests.get(f"{BASE_URL}/api/subjects?category_id={category['id']}", timeout=20)
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert temp_subject["id"] in ids


class TestQuestionsPagination:
    def test_list_with_valid_sizes(self, admin):
        for ps in (10, 50):
            r = requests.get(f"{BASE_URL}/api/admin/questions?page=1&page_size={ps}",
                             headers=admin["h"], timeout=30)
            assert r.status_code == 200, r.text
            d = r.json()
            for k in ("items", "total", "page", "page_size", "pages", "grand_total"):
                assert k in d
            assert d["page_size"] == ps
            assert len(d["items"]) <= ps

    def test_invalid_page_size_400(self, admin):
        r = requests.get(f"{BASE_URL}/api/admin/questions?page=1&page_size=7",
                         headers=admin["h"], timeout=20)
        assert r.status_code == 400

    def test_search_and_filter(self, admin):
        r = requests.get(f"{BASE_URL}/api/admin/questions?page=1&page_size=10&search=the",
                         headers=admin["h"], timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["grand_total"] >= d["total"]

    def test_requires_staff(self, student):
        r = requests.get(f"{BASE_URL}/api/admin/questions", headers=student["h"], timeout=20)
        assert r.status_code in (401, 403)


@pytest.fixture
def throwaway_questions(admin, category, temp_subject):
    created = []
    for i in range(3):
        body = {
            "text": f"TEST_q9 {uuid.uuid4().hex[:5]} #{i}", "type": "mcq_single",
            "options": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}],
            "correct": ["A"], "explanation": "", "category_id": category["id"],
            "subject_id": temp_subject["id"], "difficulty": "medium",
            "positive_marks": 1.0, "negative_marks": 0.0,
        }
        r = requests.post(f"{BASE_URL}/api/questions", json=body, headers=admin["h"], timeout=20)
        assert r.status_code == 200, r.text
        created.append(r.json()["id"])
    yield created
    requests.post(f"{BASE_URL}/api/admin/questions/bulk-delete",
                  json={"ids": created}, headers=admin["h"], timeout=20)


class TestBulkDelete:
    def test_bulk_delete_by_ids(self, admin, throwaway_questions):
        ids = throwaway_questions[:2]
        r = requests.post(f"{BASE_URL}/api/admin/questions/bulk-delete",
                          json={"ids": ids}, headers=admin["h"], timeout=20)
        assert r.status_code == 200
        assert r.json()["deleted"] == 2

    def test_bulk_delete_empty_400(self, admin):
        r = requests.post(f"{BASE_URL}/api/admin/questions/bulk-delete",
                          json={"ids": []}, headers=admin["h"], timeout=20)
        assert r.status_code == 400

    def test_bulk_delete_all_matching_scoped(self, admin, throwaway_questions, temp_subject):
        # delete all questions on temp_subject only (throwaways)
        r = requests.post(f"{BASE_URL}/api/admin/questions/bulk-delete",
                          json={"all_matching": True,
                                "filters": {"subject_id": temp_subject["id"]}},
                          headers=admin["h"], timeout=30)
        assert r.status_code == 200
        assert r.json()["deleted"] >= 1
        # Verify none left on that subject
        r2 = requests.get(f"{BASE_URL}/api/admin/questions?page=1&page_size=10&subject_id={temp_subject['id']}",
                          headers=admin["h"], timeout=20)
        assert r2.json()["total"] == 0


# ---------------- CSV import with subject column ----------------
def _csv(rows, header):
    buf = io.StringIO()
    buf.write(",".join(header) + "\n")
    for row in rows:
        buf.write(",".join(f'"{v}"' for v in row) + "\n")
    return buf.getvalue().encode("utf-8")


class TestCsvImport:
    def test_import_with_subject_column(self, admin, category, temp_subject):
        header = ["question", "type", "option_a", "option_b", "correct", "subject", "difficulty"]
        rows = [
            [f"TEST_imp Q1 {uuid.uuid4().hex[:4]}", "mcq", "A", "B", "A", temp_subject["name"], "easy"],
            [f"TEST_imp Q2 {uuid.uuid4().hex[:4]}", "mcq", "X", "Y", "Y", "No_Such_Subject_X", "easy"],
        ]
        files = {"file": ("qs.csv", _csv(rows, header), "text/csv")}
        data = {"category_id": category["id"], "commit": "true"}
        r = requests.post(f"{BASE_URL}/api/questions/import", files=files, data=data,
                          headers=admin["h"], timeout=30)
        assert r.status_code == 200, r.text
        resp = r.json()
        # one success + one row-error (unknown subject)
        assert resp.get("valid", 0) >= 1
        assert resp.get("error_count", 0) >= 1
        err_rows = resp.get("errors") or []
        assert any("subject" in e.get("message", "").lower() for e in err_rows)
        # Rollback the import
        batch = resp.get("batch_id")
        if batch:
            requests.delete(f"{BASE_URL}/api/questions/import/{batch}", headers=admin["h"], timeout=20)


# ---------------- Admin user management (D) ----------------
@pytest.fixture
def temp_user(admin):
    body = {"name": "TEST User", "email": f"test_{uuid.uuid4().hex[:8]}@ex.com",
            "phone": "9999999999", "role": "student", "password": "pass1234"}
    r = requests.post(f"{BASE_URL}/api/admin/users", json=body, headers=admin["h"], timeout=20)
    assert r.status_code == 200, r.text
    u = r.json()
    yield {**u, "password": body["password"]}
    requests.delete(f"{BASE_URL}/api/admin/users/{u['id']}", headers=admin["h"], timeout=20)


class TestUserManagement:
    def test_create_duplicate_email_400(self, admin, temp_user):
        body = {"name": "Dup", "email": temp_user["email"], "phone": "", "role": "student", "password": "pass1234"}
        r = requests.post(f"{BASE_URL}/api/admin/users", json=body, headers=admin["h"], timeout=20)
        assert r.status_code == 400

    def test_edit_user(self, admin, temp_user):
        body = {"name": "Edited", "email": temp_user["email"], "phone": "1234567890", "role": "student"}
        r = requests.put(f"{BASE_URL}/api/admin/users/{temp_user['id']}", json=body,
                         headers=admin["h"], timeout=20)
        assert r.status_code == 200
        assert r.json()["name"] == "Edited"
        assert r.json()["phone"] == "1234567890"

    def test_reset_password_invalidates_old_token(self, admin, temp_user):
        # Login as that user first
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": temp_user["email"], "password": temp_user["password"]}, timeout=20)
        assert r.status_code == 200
        old_token = r.json()["token"]
        time.sleep(1.1)  # ensure iat differs
        # Reset password
        r = requests.post(f"{BASE_URL}/api/admin/users/{temp_user['id']}/reset-password",
                          json={"password": "newpass123"}, headers=admin["h"], timeout=20)
        assert r.status_code == 200
        # Old token should now 401
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}, timeout=20)
        assert r.status_code == 401
        # Old password rejected
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": temp_user["email"], "password": temp_user["password"]}, timeout=20)
        assert r.status_code == 401
        # New password works
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": temp_user["email"], "password": "newpass123"}, timeout=20)
        assert r.status_code == 200

    def test_suspend_then_activate(self, admin, temp_user):
        # suspend
        r = requests.put(f"{BASE_URL}/api/admin/users/{temp_user['id']}/status",
                         json={"suspended": True}, headers=admin["h"], timeout=20)
        assert r.status_code == 200
        # login should 403
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": temp_user["email"], "password": temp_user["password"]}, timeout=20)
        assert r.status_code == 403
        # activate
        r = requests.put(f"{BASE_URL}/api/admin/users/{temp_user['id']}/status",
                         json={"suspended": False}, headers=admin["h"], timeout=20)
        assert r.status_code == 200
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": temp_user["email"], "password": temp_user["password"]}, timeout=20)
        assert r.status_code == 200

    def test_cannot_suspend_self(self, admin):
        r = requests.put(f"{BASE_URL}/api/admin/users/{admin['user']['id']}/status",
                         json={"suspended": True}, headers=admin["h"], timeout=20)
        assert r.status_code == 400

    def test_cannot_delete_self(self, admin):
        r = requests.delete(f"{BASE_URL}/api/admin/users/{admin['user']['id']}",
                            headers=admin["h"], timeout=20)
        assert r.status_code == 400

    def test_cannot_grant_super_admin_as_admin(self, admin, temp_user):
        # admin@lms.com is role "admin" (not super_admin). Granting super_admin should 403.
        body = {"name": temp_user["name"], "email": temp_user["email"], "phone": "", "role": "super_admin"}
        r = requests.put(f"{BASE_URL}/api/admin/users/{temp_user['id']}", json=body,
                         headers=admin["h"], timeout=20)
        assert r.status_code == 403

    def test_delete_removes_user(self, admin):
        body = {"name": "TEST Del", "email": f"del_{uuid.uuid4().hex[:6]}@ex.com",
                "phone": "", "role": "student", "password": "pass1234"}
        r = requests.post(f"{BASE_URL}/api/admin/users", json=body, headers=admin["h"], timeout=20)
        assert r.status_code == 200
        uid = r.json()["id"]
        r = requests.delete(f"{BASE_URL}/api/admin/users/{uid}", headers=admin["h"], timeout=20)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        # GET admin user record should 404
        r = requests.get(f"{BASE_URL}/api/admin/users/{uid}", headers=admin["h"], timeout=20)
        assert r.status_code == 404


# ---------------- Test section marks & language overrides (C) ----------------
def _get_series_cat(admin, category_id):
    rows = requests.get(f"{BASE_URL}/api/test-series", timeout=20).json()
    for s in rows:
        if s.get("category_id") == category_id:
            return s
    # fall back: pick any
    return rows[0] if rows else None


@pytest.fixture
def section_test(admin, category, temp_subject):
    # Create 4 questions, 2 bilingual with text_hi, 2 english
    qids = []
    for i in range(4):
        body = {
            "text": f"TEST_sec Q{i} {uuid.uuid4().hex[:4]} EN",
            "text_hi": "हिंदी प्रश्न" if i >= 2 else None,
            "type": "mcq_single",
            "options": [{"key": "A", "text": "a", "text_hi": "ए" if i >= 2 else None},
                        {"key": "B", "text": "b", "text_hi": "बी" if i >= 2 else None}],
            "correct": ["A"], "explanation": "", "category_id": category["id"],
            "subject_id": temp_subject["id"], "difficulty": "medium",
            "positive_marks": 1.0, "negative_marks": 0.0,
        }
        r = requests.post(f"{BASE_URL}/api/questions", json=body, headers=admin["h"], timeout=20)
        assert r.status_code == 200, r.text
        qids.append(r.json()["id"])
    series = _get_series_cat(admin, category["id"])
    assert series
    body = {
        "series_id": series["id"], "title": f"TEST_sec_test {uuid.uuid4().hex[:5]}",
        "duration_minutes": 30,
        "sections": [
            {"name": "S1", "question_ids": qids[:2], "positive_marks": 2.0,
             "negative_marks": 0.5, "language": "en"},
            {"name": "S2", "question_ids": qids[2:], "language": "hi"},
        ],
    }
    r = requests.post(f"{BASE_URL}/api/tests", json=body, headers=admin["h"], timeout=20)
    assert r.status_code == 200, r.text
    t = r.json()
    yield {"test": t, "qids": qids}
    requests.delete(f"{BASE_URL}/api/content/tests/{t['id']}", headers=admin["h"], timeout=20)
    requests.post(f"{BASE_URL}/api/admin/questions/bulk-delete",
                  json={"ids": qids}, headers=admin["h"], timeout=20)


class TestSectionRules:
    def test_total_marks_uses_override(self, section_test):
        t = section_test["test"]
        # S1: 2 Q * 2.0 = 4; S2: 2 Q * default (1.0) = 2 -> total 6
        assert t["total_marks"] == pytest.approx(6.0)

    def test_attempt_returns_section_overrides_and_localized(self, admin, section_test, student):
        tid = section_test["test"]["id"]
        # start as student
        r = requests.post(f"{BASE_URL}/api/tests/{tid}/start", headers=student["h"], timeout=20)
        assert r.status_code == 200, r.text
        aid = r.json()["id"]
        r = requests.get(f"{BASE_URL}/api/attempts/{aid}", headers=student["h"], timeout=20)
        assert r.status_code == 200
        qs = r.json()["questions"]
        s1 = [q for q in qs if q["id"] in section_test["qids"][:2]]
        s2 = [q for q in qs if q["id"] in section_test["qids"][2:]]
        for q in s1:
            assert q["positive_marks"] == 2.0
            assert q["negative_marks"] == 0.5
            assert q["display_language"] == "en"
            assert "text_hi" not in q
        for q in s2:
            assert q["display_language"] == "hi"
            assert "text_hi" not in q
            assert q["text"] == "हिंदी प्रश्न"
        # Submit all correct for S1 (A), S2 wrong (B)
        answers = {}
        for q in s1:
            answers[q["id"]] = ["A"]
        for q in s2:
            answers[q["id"]] = ["B"]
        r = requests.post(f"{BASE_URL}/api/attempts/{aid}/submit",
                          json={"answers": answers, "marked_for_review": [], "client_version": 0},
                          headers=student["h"], timeout=20)
        assert r.status_code == 200, r.text
        # expected: S1 correct = +2*2 = 4; S2 wrong = -0*2 = 0 (default negative 0) -> total 4
        r = requests.get(f"{BASE_URL}/api/attempts/{aid}/result", headers=student["h"], timeout=20)
        assert r.status_code == 200
        res = r.json()
        assert res["score"] == pytest.approx(4.0)
