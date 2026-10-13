"""Iteration 7: Announcement Bar tests (PUT /api/admin/site/announcement, GET /api/site)."""
import os
from datetime import datetime, timedelta, timezone
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://testseries-lms.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "admin@lms.com", "password": "admin123"}
STUDENT = {"email": "student@lms.com", "password": "student123"}


@pytest.fixture(scope="module")
def admin_h():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=20)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def student_h():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=STUDENT, timeout=20)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _put(body, h):
    return requests.put(f"{BASE_URL}/api/admin/site/announcement", json=body, headers=h, timeout=20)


def test_student_forbidden(student_h):
    r = _put({"enabled": False, "message": ""}, student_h)
    assert r.status_code in (401, 403), r.text


def test_unauth():
    r = requests.put(f"{BASE_URL}/api/admin/site/announcement", json={"enabled": False, "message": ""}, timeout=20)
    assert r.status_code in (401, 403)


def test_enabled_requires_message(admin_h):
    r = _put({"enabled": True, "message": "   "}, admin_h)
    assert r.status_code == 400


def test_end_after_start(admin_h):
    now = datetime.now(timezone.utc)
    r = _put({
        "enabled": True, "message": "x", "style": "offer",
        "starts_at": now.isoformat(),
        "ends_at": (now - timedelta(hours=1)).isoformat(),
    }, admin_h)
    assert r.status_code == 400


def test_save_uppercases_coupon_and_versions(admin_h):
    body = {"enabled": True, "message": "Hello world", "style": "info", "cta_label": "Go",
            "cta_url": "/x", "coupon_code": "welcome20"}
    r1 = _put(body, admin_h)
    assert r1.status_code == 200, r1.text
    a1 = r1.json()["announcement"]
    assert a1["coupon_code"] == "WELCOME20"
    assert a1.get("version")
    r2 = _put(body, admin_h)
    a2 = r2.json()["announcement"]
    assert a2["version"] != a1["version"], "Version must change on each save"


def test_public_site_returns_ann_when_active(admin_h):
    _put({"enabled": True, "message": "Live now", "style": "offer",
          "cta_label": "Explore", "cta_url": "/test-series", "coupon_code": "WELCOME20"}, admin_h)
    r = requests.get(f"{BASE_URL}/api/site", timeout=20)
    assert r.status_code == 200
    j = r.json()
    assert j["announcement"] is not None
    assert j["announcement"]["message"] == "Live now"
    assert j["announcement"]["coupon_code"] == "WELCOME20"
    assert j["announcement"].get("version")


def test_public_site_null_when_disabled(admin_h):
    _put({"enabled": False, "message": "whatever"}, admin_h)
    r = requests.get(f"{BASE_URL}/api/site", timeout=20)
    assert r.json()["announcement"] is None


def test_public_site_null_when_scheduled(admin_h):
    future = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    _put({"enabled": True, "message": "future", "style": "info",
          "starts_at": future}, admin_h)
    r = requests.get(f"{BASE_URL}/api/site", timeout=20)
    assert r.json()["announcement"] is None


def test_public_site_null_when_expired(admin_h):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    past2 = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    _put({"enabled": True, "message": "past", "style": "info",
          "starts_at": past2, "ends_at": past}, admin_h)
    r = requests.get(f"{BASE_URL}/api/site", timeout=20)
    assert r.json()["announcement"] is None


def test_final_state_enabled_offer(admin_h):
    """Leave the announcement enabled with required final state per request."""
    body = {"enabled": True, "message": "Get 20% off your first test series",
            "style": "offer", "cta_label": "Explore", "cta_url": "/test-series",
            "coupon_code": "WELCOME20", "starts_at": None, "ends_at": None}
    r = _put(body, admin_h)
    assert r.status_code == 200
    a = r.json()["announcement"]
    assert a["enabled"] is True
    assert a["message"] == "Get 20% off your first test series"
    assert a["style"] == "offer"
    assert a["cta_label"] == "Explore"
    assert a["cta_url"] == "/test-series"
    assert a["coupon_code"] == "WELCOME20"
    # verify via public endpoint
    pr = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
    assert pr["announcement"]["message"] == "Get 20% off your first test series"
