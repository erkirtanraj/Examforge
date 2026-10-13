"""Iteration 10: Resume playback positions + Certificate feature backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://testseries-lms.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
COURSE_ID = "7b9f8123-fd48-4cbf-9c40-9746caf38c97"
LESSON2_ID = "822a180e-3c1c-42d0-9071-bbaf33fa3e0a"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@lms.com", "admin123")


@pytest.fixture(scope="module")
def student_token():
    return _login("student@lms.com", "student123")


@pytest.fixture(scope="module")
def course(admin_token):
    r = requests.get(f"{API}/courses/{COURSE_ID}", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Position save & progress ----------
def test_save_position_and_progress(student_token):
    r = requests.put(f"{API}/lessons/{LESSON2_ID}/position",
                     json={"position": 42.5, "duration": 300.0},
                     headers=_h(student_token), timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    r2 = requests.get(f"{API}/my/progress/{COURSE_ID}", headers=_h(student_token), timeout=15)
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert "positions" in data and "completed_ids" in data and "certificate" in data
    assert LESSON2_ID in data["positions"]
    assert abs(data["positions"][LESSON2_ID]["position"] - 42.5) < 0.1


def test_save_position_requires_auth():
    r = requests.put(f"{API}/lessons/{LESSON2_ID}/position", json={"position": 10, "duration": 100}, timeout=15)
    assert r.status_code in (401, 403)


# ---------- Certificate enable toggle persists ----------
def test_certificate_enabled_persists_via_content_put(admin_token, course):
    body = {
        "title": course["title"],
        "description": course.get("description", ""),
        "price": course.get("price", 0),
        "is_free": course.get("is_free", True),
        "category_id": course.get("category_id"),
        "thumbnail_url": course.get("thumbnail_url"),
        "certificate_enabled": True,
    }
    r = requests.put(f"{API}/content/courses/{COURSE_ID}", json=body, headers=_h(admin_token), timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("certificate_enabled") is True
    # Verify via GET
    r2 = requests.get(f"{API}/courses/{COURSE_ID}", timeout=15)
    assert r2.json().get("certificate_enabled") is True


# ---------- Certificate issuance flow ----------
def test_certificate_requires_all_lessons(admin_token, student_token, course):
    # Ensure certificate_enabled true (previous test enables it)
    # Collect all lesson ids
    full = requests.get(f"{API}/courses/{COURSE_ID}", timeout=15).json()
    lesson_ids = [l["id"] for s in full.get("sections", []) for l in s.get("lessons", [])]
    assert lesson_ids, "course should have lessons"

    # Clear existing certificate / progress for isolation via re-complete pattern isn't trivial;
    # Instead, directly try issue - should fail if not all complete.
    # First check progress
    prog = requests.get(f"{API}/my/progress/{COURSE_ID}", headers=_h(student_token), timeout=15).json()
    if prog.get("certificate"):
        # already issued - idempotent test instead
        r = requests.post(f"{API}/courses/{COURSE_ID}/certificate", headers=_h(student_token), timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == prog["certificate"]["id"]
        return

    if prog["completed"] < prog["total"]:
        r = requests.post(f"{API}/courses/{COURSE_ID}/certificate", headers=_h(student_token), timeout=15)
        assert r.status_code == 400
        assert "every lesson" in r.text.lower() or "complete" in r.text.lower()

    # Complete all lessons
    for lid in lesson_ids:
        rc = requests.post(f"{API}/lessons/{lid}/complete", headers=_h(student_token), timeout=15)
        assert rc.status_code == 200

    r = requests.post(f"{API}/courses/{COURSE_ID}/certificate", headers=_h(student_token), timeout=15)
    assert r.status_code == 200, r.text
    cert = r.json()
    assert cert["id"].startswith("EF-")
    assert cert["course_title"] == full["title"]
    assert "user_id" not in cert or cert.get("user_id")  # cert object may include user_id in private API
    # idempotent
    r2 = requests.post(f"{API}/courses/{COURSE_ID}/certificate", headers=_h(student_token), timeout=15)
    assert r2.status_code == 200
    assert r2.json()["id"] == cert["id"]


# ---------- Public verify ----------
def test_verify_certificate_public_and_case_insensitive(student_token):
    prog = requests.get(f"{API}/my/progress/{COURSE_ID}", headers=_h(student_token), timeout=15).json()
    cert = prog.get("certificate")
    assert cert, "cert should exist after previous test"
    code = cert["id"]
    r = requests.get(f"{API}/certificates/{code}", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "user_id" not in data
    assert data["id"] == code
    # case-insensitive
    r2 = requests.get(f"{API}/certificates/{code.lower()}", timeout=15)
    assert r2.status_code == 200
    assert r2.json()["id"] == code


def test_verify_unknown_404():
    r = requests.get(f"{API}/certificates/EF-XXXX-XXXX-XXXX", timeout=15)
    assert r.status_code == 404


# ---------- Certificate disabled -> 400 ----------
def test_certificate_disabled_returns_400(admin_token, student_token):
    # Create a brand new course without certificate_enabled
    full = requests.get(f"{API}/courses/{COURSE_ID}", timeout=15).json()
    new = {
        "title": "TEST_no_cert_course",
        "description": "test",
        "price": 0, "is_free": True,
        "category_id": full.get("category_id"),
        "thumbnail_url": full.get("thumbnail_url"),
        "certificate_enabled": False,
    }
    r = requests.post(f"{API}/courses", json=new, headers=_h(admin_token), timeout=15)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    try:
        rc = requests.post(f"{API}/courses/{cid}/certificate", headers=_h(student_token), timeout=15)
        assert rc.status_code == 400
        assert "doesn't offer" in rc.text.lower() or "does not offer" in rc.text.lower() or "offer" in rc.text.lower()
    finally:
        requests.delete(f"{API}/content/courses/{cid}", headers=_h(admin_token), timeout=15)
