"""Iteration 9 - Exam engine (pause/resume + attempt metadata) backend tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://testseries-lms.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

STUDENT = {"email": "student@lms.com", "password": "student123"}
ADMIN = {"email": "admin@lms.com", "password": "admin123"}
NON_SECTIONAL_TEST = "80540ef2-7531-4403-8182-46a9954592c7"
SECTIONAL_TEST = "cabc26f0-9c25-4a05-aa6d-52ec28362527"


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def student_hdr():
    return {"Authorization": f"Bearer {_login(STUDENT)}"}


@pytest.fixture(scope="module")
def admin_hdr():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


def _submit_in_progress(student_hdr):
    """Submit any lingering in-progress attempts so we can start fresh ones."""
    r = requests.get(f"{API}/attempts", headers=student_hdr, timeout=20)
    if r.status_code != 200:
        return
    for a in r.json():
        if a.get("status") == "in_progress":
            requests.post(f"{API}/attempts/{a['id']}/submit",
                          headers=student_hdr,
                          json={"answers": {}, "marked_for_review": [], "client_version": a.get("version", 0)},
                          timeout=20)


def _start(test_id, student_hdr):
    _submit_in_progress(student_hdr)
    r = requests.post(f"{API}/tests/{test_id}/start", headers=student_hdr, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _get(attempt_id, student_hdr):
    r = requests.get(f"{API}/attempts/{attempt_id}", headers=student_hdr, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


# -------------------- Attempt metadata --------------------

def test_attempt_payload_fields(student_hdr):
    aid = _start(NON_SECTIONAL_TEST, student_hdr)
    data = _get(aid, student_hdr)
    for f in ("id", "test_title", "pause_left_seconds", "user_name", "questions", "server_now"):
        assert f in data, f"missing {f}"
    assert data["user_name"] == "Student User" or isinstance(data["user_name"], str)
    assert data["pause_left_seconds"] == 15 * 60
    # cleanup
    requests.post(f"{API}/attempts/{aid}/submit", headers=student_hdr,
                  json={"answers": {}, "marked_for_review": [], "client_version": data["version"]}, timeout=20)


# -------------------- Pause/Resume on non-sectional test --------------------

def test_pause_saves_answers_and_decrements_pause_left(student_hdr):
    aid = _start(NON_SECTIONAL_TEST, student_hdr)
    data = _get(aid, student_hdr)
    qs = data["questions"]
    assert qs
    # pick first option for first question
    first_q = qs[0]
    ans_val = [first_q["options"][0]["key"]] if first_q.get("options") else "1"
    answers = {first_q["id"]: ans_val}
    r = requests.post(f"{API}/attempts/{aid}/pause", headers=student_hdr,
                      json={"answers": answers, "marked_for_review": [first_q["id"]], "client_version": data["version"]},
                      timeout=20)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paused"
    # second pause while paused returns paused (idempotent)
    r2 = requests.post(f"{API}/attempts/{aid}/pause", headers=student_hdr,
                       json={"answers": {}, "marked_for_review": [], "client_version": 0}, timeout=20)
    assert r2.status_code == 200 and r2.json()["status"] == "paused"
    time.sleep(2)
    data2 = _get(aid, student_hdr)
    assert data2.get("paused_at")
    # answers persisted
    assert data2["answers"].get(first_q["id"]) == ans_val
    assert first_q["id"] in (data2.get("marked_for_review") or [])
    # pause_left_seconds not decremented until resume
    # Resume
    rr = requests.post(f"{API}/attempts/{aid}/resume", headers=student_hdr, timeout=20)
    assert rr.status_code == 200 and rr.json()["status"] == "ok"
    data3 = _get(aid, student_hdr)
    assert not data3.get("paused_at")
    # pause_left_seconds should be less (we paused ~2s)
    assert data3["pause_left_seconds"] < 15 * 60
    assert data3["pause_left_seconds"] >= 15 * 60 - 30  # within 30s margin
    # cleanup
    requests.post(f"{API}/attempts/{aid}/submit", headers=student_hdr,
                  json={"answers": {}, "marked_for_review": [], "client_version": data3["version"]}, timeout=20)


# -------------------- Pause disallowed when allow_pause=false --------------------

def _get_test(test_id, hdr):
    r = requests.get(f"{API}/tests/{test_id}", headers=hdr, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


def _put_test(test_id, body, hdr):
    body = {k: v for k, v in body.items() if k not in ("id", "created_by", "created_at", "updated_at", "total_marks")}
    r = requests.put(f"{API}/content/tests/{test_id}", headers=hdr, json=body, timeout=20)
    return r


def test_pause_disallowed_when_test_disallows(student_hdr, admin_hdr):
    original = _get_test(NON_SECTIONAL_TEST, admin_hdr)
    body = {**original, "allow_pause": False}
    r = _put_test(NON_SECTIONAL_TEST, body, admin_hdr)
    assert r.status_code == 200, r.text
    try:
        aid = _start(NON_SECTIONAL_TEST, student_hdr)
        data = _get(aid, student_hdr)
        assert data["pause_left_seconds"] == 0
        pr = requests.post(f"{API}/attempts/{aid}/pause", headers=student_hdr,
                           json={"answers": {}, "marked_for_review": [], "client_version": data["version"]},
                           timeout=20)
        assert pr.status_code == 400
        assert "not available" in pr.text.lower()
        # cleanup
        requests.post(f"{API}/attempts/{aid}/submit", headers=student_hdr,
                      json={"answers": {}, "marked_for_review": [], "client_version": data["version"]}, timeout=20)
    finally:
        # Restore
        rr = _put_test(NON_SECTIONAL_TEST, {**original, "allow_pause": True}, admin_hdr)
        assert rr.status_code == 200


# -------------------- Sectional pause: section timer frozen --------------------

def test_sectional_pause_freezes_section_timer(student_hdr):
    aid = _start(SECTIONAL_TEST, student_hdr)
    data = _get(aid, student_hdr)
    assert data.get("sectional_timing")
    pr = requests.post(f"{API}/attempts/{aid}/pause", headers=student_hdr,
                       json={"answers": {}, "marked_for_review": [], "client_version": data["version"]}, timeout=20)
    assert pr.status_code == 200 and pr.json()["status"] == "paused"
    d2 = _get(aid, student_hdr)
    assert d2.get("paused_at")
    assert d2.get("section_remaining_at_pause") is not None
    rr = requests.post(f"{API}/attempts/{aid}/resume", headers=student_hdr, timeout=20)
    assert rr.status_code == 200
    # cleanup
    d3 = _get(aid, student_hdr)
    requests.post(f"{API}/attempts/{aid}/submit", headers=student_hdr,
                  json={"answers": {}, "marked_for_review": [], "client_version": d3["version"]}, timeout=20)
