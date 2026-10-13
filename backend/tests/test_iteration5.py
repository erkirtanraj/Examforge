"""Iteration 5: Site Settings, Home Settings, Legal Pages tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://testseries-lms.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@lms.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def student_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "student@lms.com", "password": "student123"})
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def student_headers(student_token):
    return {"Authorization": f"Bearer {student_token}"}


# ---------- Public /api/site ----------
class TestPublicSite:
    def test_public_site_structure(self):
        r = requests.get(f"{BASE_URL}/api/site")
        assert r.status_code == 200
        d = r.json()
        for k in ("header", "hero", "stats", "features", "footer", "metrics"):
            assert k in d, f"missing {k}"
        # stats have display
        for s in d["stats"]:
            assert "display" in s
        # live placeholder replaced
        assert "{live}" not in d["hero"]["badge_text"]

    def test_stats_live_db_count(self):
        r = requests.get(f"{BASE_URL}/api/site").json()
        m = r["metrics"]
        for s in r["stats"]:
            if s["source"] in ("students", "questions", "tests") and not s["override"]:
                # Display should not be empty for seeded data
                assert s["display"] != ""


# ---------- Admin site endpoints ----------
class TestAdminSite:
    def test_admin_site_get(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_headers)
        assert r.status_code == 200
        assert "header" in r.json()

    def test_admin_site_forbidden_for_student(self, student_headers):
        r = requests.get(f"{BASE_URL}/api/admin/site", headers=student_headers)
        assert r.status_code == 403

    def test_put_layout_requires_admin(self, student_headers):
        r = requests.put(f"{BASE_URL}/api/admin/site/layout", headers=student_headers,
                         json={"header": {"brand_name": "X", "nav_links": [], "cta_label": "x", "cta_url": "/"},
                               "footer": {"tagline": "", "copyright": "", "links": []}})
        assert r.status_code == 403

    def test_put_layout_and_persist(self, admin_headers):
        # get current
        orig = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_headers).json()
        payload = {"header": {**orig["header"], "brand_name": "TEST_Brand"},
                   "footer": orig["footer"]}
        r = requests.put(f"{BASE_URL}/api/admin/site/layout", headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        # Verify via public
        pub = requests.get(f"{BASE_URL}/api/site").json()
        assert pub["header"]["brand_name"] == "TEST_Brand"
        # restore
        requests.put(f"{BASE_URL}/api/admin/site/layout", headers=admin_headers,
                     json={"header": {**orig["header"]}, "footer": orig["footer"]})

    def test_put_home_with_override(self, admin_headers):
        orig = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_headers).json()
        stats = [dict(s) for s in orig["stats"]]
        if stats:
            stats[0]["override"] = "99K+"
        payload = {"hero": orig["hero"], "stats": stats, "features": orig["features"]}
        r = requests.put(f"{BASE_URL}/api/admin/site/home", headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        pub = requests.get(f"{BASE_URL}/api/site").json()
        assert pub["stats"][0]["display"] == "99K+"
        # restore
        stats[0]["override"] = ""
        requests.put(f"{BASE_URL}/api/admin/site/home", headers=admin_headers,
                     json={"hero": orig["hero"], "stats": stats, "features": orig["features"]})

    def test_home_stats_max_6(self, admin_headers):
        orig = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_headers).json()
        stats = [{"label": f"S{i}", "source": "manual", "override": "1"} for i in range(7)]
        r = requests.put(f"{BASE_URL}/api/admin/site/home", headers=admin_headers,
                         json={"hero": orig["hero"], "stats": stats, "features": orig["features"]})
        assert r.status_code == 422


# ---------- Legal pages ----------
class TestLegalPages:
    SEEDED = ["privacy", "terms", "refund-policy", "contact"]

    def test_seeded_pages_public(self):
        for slug in self.SEEDED:
            r = requests.get(f"{BASE_URL}/api/pages/{slug}")
            assert r.status_code == 200, f"{slug} not seeded"
            assert r.json()["slug"] == slug

    def test_admin_list_pages(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/pages", headers=admin_headers)
        assert r.status_code == 200
        slugs = [p["slug"] for p in r.json()]
        for s in self.SEEDED:
            assert s in slugs

    def test_admin_pages_forbidden_for_student(self, student_headers):
        r = requests.get(f"{BASE_URL}/api/admin/pages", headers=student_headers)
        assert r.status_code == 403

    def test_create_and_crud_page(self, admin_headers):
        # Create
        payload = {"title": "TEST_Page", "slug": "test-page-xyz", "content": "## Hello", "published": True}
        r = requests.post(f"{BASE_URL}/api/admin/pages", headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        page = r.json()
        pid = page["id"]
        assert page["slug"] == "test-page-xyz"

        # Public GET
        r = requests.get(f"{BASE_URL}/api/pages/test-page-xyz")
        assert r.status_code == 200

        # Duplicate slug
        r = requests.post(f"{BASE_URL}/api/admin/pages", headers=admin_headers,
                          json={"title": "Dup", "slug": "test-page-xyz", "content": "", "published": True})
        assert r.status_code == 400

        # Update - toggle draft
        r = requests.put(f"{BASE_URL}/api/admin/pages/{pid}", headers=admin_headers,
                         json={"title": "TEST_Page2", "slug": "test-page-xyz", "content": "## Updated", "published": False})
        assert r.status_code == 200
        assert r.json()["published"] is False

        # Draft -> 404 publicly
        r = requests.get(f"{BASE_URL}/api/pages/test-page-xyz")
        assert r.status_code == 404

        # Delete
        r = requests.delete(f"{BASE_URL}/api/admin/pages/{pid}", headers=admin_headers)
        assert r.status_code == 200
        r = requests.get(f"{BASE_URL}/api/pages/test-page-xyz")
        assert r.status_code == 404

    def test_slug_slugified(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/pages", headers=admin_headers,
                          json={"title": "T", "slug": "Hello World!!", "content": "", "published": True})
        assert r.status_code == 200
        pid = r.json()["id"]
        assert r.json()["slug"] == "hello-world"
        # cleanup
        requests.delete(f"{BASE_URL}/api/admin/pages/{pid}", headers=admin_headers)
