"""Backend tests for Iteration 3: Bulk Import, Exam Sections (free-nav + sectional_timing), Leaderboards."""
import os, io, csv, uuid, json
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import openpyxl

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


def _csv(headers, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


# -------------------- IMPORT --------------------
class TestImport:
    batches_to_cleanup = []

    def test_student_forbidden(self, student):
        f = _csv(["question", "option_a", "option_b", "correct"], [["q", "a", "b", "A"]])
        r = requests.post(f"{API}/questions/import", headers=student["h"],
                          files={"file": ("q.csv", f, "text/csv")}, data={"commit": "false"})
        assert r.status_code == 403

    def test_missing_headers_400(self, teacher):
        f = _csv(["q", "answer_only"], [["x", "y"]])  # 'q' aliases to question, missing correct
        r = requests.post(f"{API}/questions/import", headers=teacher["h"],
                          files={"file": ("bad.csv", f, "text/csv")}, data={"commit": "false"})
        assert r.status_code == 400

    def test_bad_extension_400(self, teacher):
        r = requests.post(f"{API}/questions/import", headers=teacher["h"],
                          files={"file": ("x.txt", b"hi", "text/plain")}, data={"commit": "false"})
        assert r.status_code == 400

    def test_preview_counts_and_errors(self, teacher):
        hdr = ["question", "type", "option_a", "option_b", "option_c", "option_d", "correct", "category", "difficulty"]
        rows = [
            ["Capital of France?", "mcq", "Paris", "London", "Rome", "Berlin", "A", "", "easy"],
            ["Pick primes", "multi", "2", "3", "4", "6", "A,B", "", "medium"],  # multi
            ["Is sky blue?", "true_false", "", "", "", "", "True", "", ""],  # tf
            ["Value of pi (2dp)?", "numerical", "", "", "", "", "3.14", "", ""],
            # ---- errors ----
            ["No answer row", "mcq", "a", "b", "", "", "", "", ""],  # missing correct
            ["Gap options", "mcq", "a", "", "c", "", "A", "", ""],  # gap in options
            ["Bad single multiple", "mcq", "a", "b", "c", "d", "A,B", "", ""],  # multiple on single
            ["Unknown cat", "mcq", "a", "b", "c", "d", "A", "ZZZZ_NO_CAT", ""],  # bad cat
        ]
        f = _csv(hdr, rows)
        r = requests.post(f"{API}/questions/import", headers=teacher["h"],
                          files={"file": ("mix.csv", f, "text/csv")}, data={"commit": "false"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total"] == 8
        assert d["valid"] == 4
        assert d["error_count"] == 4
        rows_err = {e["row"] for e in d["errors"]}
        # row numbers are 1-indexed with header on row 1 => data starts row 2
        assert rows_err == {6, 7, 8, 9}

    def test_commit_and_undo(self, teacher):
        hdr = ["question", "option_a", "option_b", "option_c", "option_d", "correct"]
        rows = [
            [f"TEST_IMP_Q1_{uuid.uuid4().hex[:6]}", "a", "b", "c", "d", "A"],
            [f"TEST_IMP_Q2_{uuid.uuid4().hex[:6]}", "a", "b", "c", "d", "B"],
            [f"TEST_IMP_Q3_{uuid.uuid4().hex[:6]}", "a", "b", "c", "d", "C"],
        ]
        f = _csv(hdr, rows)
        r = requests.post(f"{API}/questions/import", headers=teacher["h"],
                          files={"file": ("ok.csv", f, "text/csv")},
                          data={"commit": "true", "positive_marks": "2", "negative_marks": "0.5"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["valid"] == 3
        assert d["inserted"] == 3
        batch = d["batch_id"]
        assert mdb.questions.count_documents({"import_batch": batch}) == 3
        # verify defaults applied
        q = mdb.questions.find_one({"import_batch": batch})
        assert q["positive_marks"] == 2.0
        assert q["negative_marks"] == 0.5
        # Undo
        r = requests.delete(f"{API}/questions/import/{batch}", headers=teacher["h"])
        assert r.status_code == 200
        assert r.json()["deleted"] == 3
        assert mdb.questions.count_documents({"import_batch": batch}) == 0

    def test_undo_detaches_from_tests(self, teacher, admin):
        # Create 2 imported questions, attach one to a test (both as a section member), then undo => removed from test
        hdr = ["question", "option_a", "option_b", "correct"]
        rows = [[f"TEST_DETACH_{i}_{uuid.uuid4().hex[:4]}", "a", "b", "A"] for i in range(2)]
        f = _csv(hdr, rows)
        r = requests.post(f"{API}/questions/import", headers=teacher["h"],
                          files={"file": ("d.csv", f, "text/csv")}, data={"commit": "true"})
        d = r.json()
        batch = d["batch_id"]
        qids = [q["id"] for q in mdb.questions.find({"import_batch": batch}, {"id": 1})]
        # Pick an existing free series
        s = next(x for x in requests.get(f"{API}/test-series").json() if x.get("is_free"))
        r = requests.post(f"{API}/tests", headers=admin["h"], json={
            "series_id": s["id"], "title": f"TEST_detach_{uuid.uuid4().hex[:4]}",
            "duration_minutes": 10,
            "sections": [{"name": "S1", "question_ids": qids}],
            "question_ids": [],
        })
        assert r.status_code == 200, r.text
        tid = r.json()["id"]
        # Confirm qids present
        t_before = mdb.tests.find_one({"id": tid})
        assert set(t_before["question_ids"]) == set(qids)
        assert set(t_before["sections"][0]["question_ids"]) == set(qids)
        # Undo import
        r = requests.delete(f"{API}/questions/import/{batch}", headers=teacher["h"])
        assert r.status_code == 200
        t_after = mdb.tests.find_one({"id": tid})
        assert t_after["question_ids"] == [] or all(q not in t_after["question_ids"] for q in qids)
        assert all(q not in t_after["sections"][0]["question_ids"] for q in qids)
        # cleanup test
        requests.delete(f"{API}/content/tests/{tid}", headers=admin["h"])

    def test_xlsx_import(self, teacher):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["question", "type", "option_a", "option_b", "correct"])
        ws.append([f"TEST_XLSX_{uuid.uuid4().hex[:5]}", "mcq", "yes", "no", "A"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        r = requests.post(f"{API}/questions/import", headers=teacher["h"],
                          files={"file": ("q.xlsx", buf.getvalue(),
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                          data={"commit": "true"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["inserted"] == 1
        requests.delete(f"{API}/questions/import/{d['batch_id']}", headers=teacher["h"])


# -------------------- SEEDED SECTIONAL TESTS --------------------
class TestSectionalSeeded:
    def test_ssc_sectional_exists(self):
        t = mdb.tests.find_one({"title": "SSC CGL Tier I · Sectional Mock 1"})
        assert t
        assert t["sectional_timing"] is False
        assert len(t["sections"]) == 4
        assert t["duration_minutes"] == 60

    def test_sbi_sectional_exists(self):
        t = mdb.tests.find_one({"title": "SBI PO Prelims · Sectional Mock 1"})
        assert t
        assert t["sectional_timing"] is True
        assert len(t["sections"]) == 3
        # total = sum of 5 min sections
        assert t["duration_minutes"] == sum(s["duration_minutes"] for s in t["sections"])


# -------------------- FREE-NAV SECTIONAL EXAM --------------------
class TestFreeNavSectional:
    def test_start_returns_all_sections_and_qs(self, student):
        t = mdb.tests.find_one({"title": "SSC CGL Tier I · Sectional Mock 1"})
        r = requests.post(f"{API}/tests/{t['id']}/start", headers=student["h"])
        assert r.status_code == 200, r.text
        a = r.json()
        # Could be existing in-progress - fine
        assert a["sectional_timing"] is False
        assert len(a["sections"]) == 4
        # fetch attempt => all questions revealed
        r = requests.get(f"{API}/attempts/{a['id']}", headers=student["h"])
        assert r.status_code == 200
        d = r.json()
        total_qs = sum(len(s["question_ids"]) for s in d["sections"])
        assert len(d["questions"]) == total_qs

    def test_result_has_section_breakdown(self, student):
        # Find existing SBI submitted result (manual curl) OR submit SSC
        t = mdb.tests.find_one({"title": "SSC CGL Tier I · Sectional Mock 1"})
        r = requests.post(f"{API}/tests/{t['id']}/start", headers=student["h"])
        a = r.json()
        if a["status"] == "in_progress":
            full = requests.get(f"{API}/attempts/{a['id']}", headers=student["h"]).json()
            qs = full["questions"]
            answers = {q["id"]: [mdb.questions.find_one({"id": q["id"]})["correct"][0]] for q in qs[:2]}
            r = requests.post(f"{API}/attempts/{a['id']}/submit",
                              headers=student["h"], json={"answers": answers, "marked_for_review": []})
            assert r.status_code == 200
            res = r.json()
        else:
            res = requests.get(f"{API}/attempts/{a['id']}/result", headers=student["h"]).json()
        assert "sections" in res
        assert len(res["sections"]) == 4
        for s in res["sections"]:
            assert set(s.keys()) >= {"name", "score", "total_marks", "correct", "wrong", "unattempted", "accuracy"}


# -------------------- TIMED SECTIONAL --------------------
class TestTimedSectional:
    def test_only_current_section_qs_served(self, student):
        t = mdb.tests.find_one({"title": "SBI PO Prelims · Sectional Mock 1"})
        # Prior manual test may have submitted it already. Need fresh student if so.
        exist = mdb.test_attempts.find_one({"user_id": student["user"]["id"], "test_id": t["id"], "status": "submitted"})
        if exist:
            # register fresh test student
            email = f"TEST_sec_{uuid.uuid4().hex[:6]}@x.com"
            r = requests.post(f"{API}/auth/register",
                              json={"name": "SecS", "email": email, "password": "pass1234"})
            tok = r.json()["token"]
            h = {"Authorization": f"Bearer {tok}"}
            uid = r.json()["user"]["id"]
        else:
            h = student["h"]
            uid = student["user"]["id"]
        r = requests.post(f"{API}/tests/{t['id']}/start", headers=h)
        assert r.status_code == 200, r.text
        a = r.json()
        assert a["sectional_timing"] is True
        r = requests.get(f"{API}/attempts/{a['id']}", headers=h)
        d = r.json()
        cur_qids = set(d["sections"][d["current_section"]]["question_ids"])
        returned = {q["id"] for q in d["questions"]}
        assert returned == cur_qids
        assert len(d["questions"]) == len(cur_qids)

        # autosave for non-current section question should be ignored (merged out)
        other_q = next(q for s in d["sections"][d["current_section"] + 1:] for q in s["question_ids"])
        r = requests.post(f"{API}/attempts/{a['id']}/autosave",
                          headers=h,
                          json={"answers": {other_q: ["A"]}, "marked_for_review": [], "client_version": d.get("version", 0)})
        assert r.status_code == 200
        # DB check: other_q should NOT be in saved answers
        fresh = mdb.test_attempts.find_one({"id": a["id"]})
        assert other_q not in (fresh.get("answers") or {})

        # Advance to next section
        r = requests.post(f"{API}/attempts/{a['id']}/next-section",
                          headers=h,
                          json={"answers": {}, "marked_for_review": [], "client_version": 0})
        assert r.status_code == 200
        assert r.json()["status"] in ("section_advanced", "submitted")
        fresh2 = mdb.test_attempts.find_one({"id": a["id"]})
        if fresh2["status"] == "in_progress":
            assert fresh2["current_section"] >= 1

        # Simulate section expiry → sync advances
        mdb.test_attempts.update_one({"id": a["id"]}, {"$set": {"section_ends_at": "2020-01-01T00:00:00+00:00"}})
        r = requests.get(f"{API}/attempts/{a['id']}", headers=h)
        assert r.status_code == 200
        d2 = r.json()
        # It either advanced further or finalized
        if d2.get("status") == "submitted":
            res = requests.get(f"{API}/attempts/{a['id']}/result", headers=h).json()
            assert len(res["sections"]) == 3
        else:
            assert d2["current_section"] > fresh2.get("current_section", 0)

        # cleanup fresh test student if created
        if exist:
            mdb.users.delete_one({"id": uid})
            mdb.test_attempts.delete_many({"user_id": uid})
            mdb.test_results.delete_many({"user_id": uid})


# -------------------- SECTIONS EDITOR (TEST BUILDER) VALIDATION --------------------
class TestBuilderSections:
    def test_timed_without_duration_errors(self, admin):
        s = next(x for x in requests.get(f"{API}/test-series").json() if x.get("is_free"))
        # need some qids - grab first 2 from seeded SSC sectional
        t = mdb.tests.find_one({"title": "SSC CGL Tier I · Sectional Mock 1"})
        qids = t["sections"][0]["question_ids"][:2]
        r = requests.post(f"{API}/tests", headers=admin["h"], json={
            "series_id": s["id"], "title": "TEST_badsections",
            "duration_minutes": 30, "sectional_timing": True,
            "question_ids": [],
            "sections": [{"name": "A", "question_ids": qids}],  # no duration
        })
        assert r.status_code in (400, 422), r.text

    def test_sectional_duration_sums(self, admin):
        s = next(x for x in requests.get(f"{API}/test-series").json() if x.get("is_free"))
        t = mdb.tests.find_one({"title": "SSC CGL Tier I · Sectional Mock 1"})
        q1 = t["sections"][0]["question_ids"][:2]
        q2 = t["sections"][1]["question_ids"][:2]
        r = requests.post(f"{API}/tests", headers=admin["h"], json={
            "series_id": s["id"], "title": f"TEST_sec_{uuid.uuid4().hex[:4]}",
            "duration_minutes": 999, "sectional_timing": True,
            "question_ids": [],
            "sections": [
                {"name": "A", "duration_minutes": 7, "question_ids": q1},
                {"name": "B", "duration_minutes": 11, "question_ids": q2},
            ],
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["duration_minutes"] == 18  # sum, overrides passed 999
        assert len(d["sections"]) == 2
        tid = d["id"]
        requests.delete(f"{API}/content/tests/{tid}", headers=admin["h"])


# -------------------- LEADERBOARD --------------------
class TestLeaderboard:
    def test_list_public_no_auth(self):
        r = requests.get(f"{API}/leaderboards")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Should include seeded tests
        titles = {x["title"] for x in data}
        assert "SSC CGL 2026 Full Mock Series - Mock 1" in titles or any("Mock" in t for t in titles)
        for row in data:
            assert "user_id" not in row
            assert "email" not in row
            assert "participants" in row

    def test_leaderboard_no_user_data_leaked(self, student):
        # pick a test that has a submitted result
        res = mdb.test_results.find_one({})
        if not res:
            pytest.skip("No test_results in DB")
        tid = res["test_id"]
        r = requests.get(f"{API}/tests/{tid}/leaderboard")  # no auth
        assert r.status_code == 200
        d = r.json()
        txt = json.dumps(d)
        assert "user_id" not in txt
        assert "@" not in txt  # no email leaked
        assert d["participants"] >= 1
        assert "entries" in d
        for e in d["entries"]:
            assert "rank" in e and "name" in e and "score" in e
            assert "user_id" not in e

    def test_ranking_order_and_ties(self, admin):
        # Create a dedicated test series+test with 2 questions, then have 3 students submit:
        # student A: 2/2 (score=2, time_taken_sec ~ small)
        # student B: 2/2 (same score, slower -> rank behind A on tie? spec: ties share rank)
        # student C: 1/2
        # Expect: A rank 1, B rank 1 (tie), C rank 3
        s = next(x for x in requests.get(f"{API}/test-series").json() if x.get("is_free"))
        # create 2 questions
        qids = []
        for i in range(2):
            r = requests.post(f"{API}/questions", headers=admin["h"], json={
                "text": f"TEST_LBQ_{i}_{uuid.uuid4().hex[:4]}", "type": "mcq_single",
                "options": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}],
                "correct": ["A"], "positive_marks": 1.0, "negative_marks": 0.0
            })
            qids.append(r.json()["id"])
        r = requests.post(f"{API}/tests", headers=admin["h"], json={
            "series_id": s["id"], "title": f"TEST_LB_{uuid.uuid4().hex[:4]}",
            "duration_minutes": 10, "question_ids": qids,
        })
        tid = r.json()["id"]

        studs = []
        for i in range(3):
            email = f"TEST_lb_{uuid.uuid4().hex[:6]}@x.com"
            r = requests.post(f"{API}/auth/register", json={"name": f"LB{i}", "email": email, "password": "pass1234"})
            studs.append({"h": {"Authorization": f"Bearer {r.json()['token']}"}, "uid": r.json()["user"]["id"]})

        attempts = []
        for idx, cred in enumerate(studs):
            r = requests.post(f"{API}/tests/{tid}/start", headers=cred["h"])
            att = r.json()
            if idx == 2:
                ans = {qids[0]: ["A"], qids[1]: ["B"]}  # 1 wrong
            else:
                ans = {qids[0]: ["A"], qids[1]: ["A"]}  # perfect
            r = requests.post(f"{API}/attempts/{att['id']}/submit",
                              headers=cred["h"], json={"answers": ans, "marked_for_review": []})
            assert r.status_code == 200
            attempts.append(r.json())

        r = requests.get(f"{API}/tests/{tid}/leaderboard")
        d = r.json()
        assert d["participants"] == 3
        assert d["top_score"] == 2.0
        ranks = {e["name"]: e["rank"] for e in d["entries"]}
        # Two with score 2 share rank 1, next is rank 3 (bisect skip-rank)
        rank_values = sorted([e["rank"] for e in d["entries"]])
        assert rank_values == [1, 1, 3], f"ranks were {rank_values}"

        # cleanup
        for s_ in studs:
            mdb.users.delete_one({"id": s_["uid"]})
            mdb.test_attempts.delete_many({"user_id": s_["uid"]})
            mdb.test_results.delete_many({"user_id": s_["uid"]})
        requests.delete(f"{API}/content/tests/{tid}", headers=admin["h"])
        for q in qids:
            requests.delete(f"{API}/content/questions/{q}", headers=admin["h"])

    def test_me_card_for_logged_in(self, student):
        # Student has submitted SBI sectional mock (per prior manual curl). Hit leaderboard.
        t = mdb.tests.find_one({"title": "SBI PO Prelims · Sectional Mock 1"})
        res = mdb.test_results.find_one({"test_id": t["id"], "user_id": student["user"]["id"]})
        if not res:
            pytest.skip("Student has no submitted result for SBI sectional yet")
        r = requests.get(f"{API}/tests/{t['id']}/leaderboard", headers=student["h"])
        d = r.json()
        assert d.get("me") is not None
        assert d["me"]["is_you"] is True
        assert "rank" in d["me"]


# -------------------- REGRESSION: Non-sectional test --------------------
class TestRegression:
    def test_normal_test_still_works(self, student):
        # pick 'SSC CGL 2026 Full Mock Series - Mock 1' or any non-sectional
        tests = list(mdb.tests.find({"$or": [{"sections": {"$size": 0}}, {"sections": {"$exists": False}}]}))
        if not tests:
            pytest.skip("No non-sectional tests")
        tid = tests[0]["id"]
        r = requests.post(f"{API}/tests/{tid}/start", headers=student["h"])
        assert r.status_code == 200, r.text
        a = r.json()
        r = requests.get(f"{API}/attempts/{a['id']}", headers=student["h"])
        assert r.status_code == 200
        d = r.json()
        if d.get("status") == "submitted":
            return  # already done
        qs = d.get("questions", [])
        # autosave 1 question
        if qs:
            r = requests.post(f"{API}/attempts/{a['id']}/autosave", headers=student["h"],
                              json={"answers": {qs[0]["id"]: ["A"]}, "marked_for_review": [], "client_version": d.get("version", 0)})
            assert r.status_code == 200
            assert r.json()["status"] in ("ok", "stale", "auto_submitted")


# ---------------- cleanup ----------------
def teardown_module(module):
    mdb.users.delete_many({"email": {"$regex": "^TEST_"}})
    mdb.questions.delete_many({"text": {"$regex": "^TEST_"}})
    mdb.tests.delete_many({"title": {"$regex": "^TEST_"}})
    mdb.test_series.delete_many({"title": {"$regex": "^TEST_"}})
