"""Iteration 8: Brand colours (ThemeIn) + announcement events + stats."""
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
ADMIN = {"email": "admin@lms.com", "password": "admin123"}
STUDENT = {"email": "student@lms.com", "password": "student123"}

DEFAULT_HEADER = {
    "brand_name": "ExamForge", "logo_url": "", "favicon_url": "", "show_brand_name": True,
    "nav_links": [{"label": "Test Series", "url": "/test-series"}],
    "cta_label": "Get Started", "cta_url": "/register",
}
DEFAULT_FOOTER = {"tagline": "x", "copyright": "y", "links": []}


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


def _put_layout(theme, h):
    body = {"header": DEFAULT_HEADER, "footer": DEFAULT_FOOTER, "theme": theme}
    return requests.put(f"{BASE_URL}/api/admin/site/layout", json=body, headers=h, timeout=20)


def _put_ann(body, h):
    return requests.put(f"{BASE_URL}/api/admin/site/announcement", json=body, headers=h, timeout=20)


# ---------- Theme ----------
class TestTheme:
    def test_default_theme_in_public_site(self):
        r = requests.get(f"{BASE_URL}/api/site", timeout=20)
        assert r.status_code == 200
        t = r.json().get("theme")
        assert t is not None
        assert set(t.keys()) >= {"preset", "primary", "accent"}

    def test_save_emerald_preset(self, admin_h):
        r = _put_layout({"preset": "emerald", "primary": "#059669", "accent": "#a3e635"}, admin_h)
        assert r.status_code == 200, r.text
        assert r.json()["theme"] == {"preset": "emerald", "primary": "#059669", "accent": "#a3e635"}
        # persists for logged-out
        pub = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
        assert pub["theme"]["preset"] == "emerald"
        assert pub["theme"]["primary"] == "#059669"

    def test_save_custom_hex(self, admin_h):
        r = _put_layout({"preset": "custom", "primary": "#123456", "accent": "#abcdef"}, admin_h)
        assert r.status_code == 200
        assert r.json()["theme"]["primary"] == "#123456"

    def test_invalid_primary_hex(self, admin_h):
        r = _put_layout({"preset": "custom", "primary": "red", "accent": "#abcdef"}, admin_h)
        assert r.status_code == 422

    def test_invalid_accent_hex(self, admin_h):
        r = _put_layout({"preset": "custom", "primary": "#123456", "accent": "#zzzzzz"}, admin_h)
        assert r.status_code == 422

    def test_short_hex_rejected(self, admin_h):
        r = _put_layout({"preset": "custom", "primary": "#123", "accent": "#abcdef"}, admin_h)
        assert r.status_code == 422

    def test_reset_to_ocean(self, admin_h):
        r = _put_layout({"preset": "ocean", "primary": "#2563eb", "accent": "#06b6d4"}, admin_h)
        assert r.status_code == 200
        assert r.json()["theme"]["preset"] == "ocean"


# ---------- Announcement events ----------
class TestAnnouncementEvents:
    @pytest.fixture(scope="class")
    def version(self, admin_h):
        body = {"enabled": True, "message": "TEST_evt banner", "style": "offer",
                "cta_label": "Go", "cta_url": "/x", "coupon_code": "EVT20"}
        r = _put_ann(body, admin_h)
        assert r.status_code == 200
        return r.json()["announcement"]["version"]

    def test_event_view_public(self, version):
        r = requests.post(f"{BASE_URL}/api/announcement/events",
                          json={"version": version, "type": "view"}, timeout=20)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_all_event_types(self, version):
        for t in ["view", "click", "copy", "close"]:
            r = requests.post(f"{BASE_URL}/api/announcement/events",
                              json={"version": version, "type": t}, timeout=20)
            assert r.status_code == 200, (t, r.text)

    def test_unknown_version_404(self):
        r = requests.post(f"{BASE_URL}/api/announcement/events",
                          json={"version": "nope_" + "0" * 10, "type": "view"}, timeout=20)
        assert r.status_code == 404

    def test_invalid_type_422(self, version):
        r = requests.post(f"{BASE_URL}/api/announcement/events",
                          json={"version": version, "type": "like"}, timeout=20)
        assert r.status_code == 422

    def test_repeats_counted(self, admin_h, version):
        # take baseline
        r0 = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=admin_h, timeout=20)
        assert r0.status_code == 200
        row0 = next((x for x in r0.json() if x["version"] == version), None)
        assert row0 is not None
        views0 = row0.get("views", 0)
        for _ in range(3):
            requests.post(f"{BASE_URL}/api/announcement/events",
                          json={"version": version, "type": "view"}, timeout=20)
        r1 = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=admin_h, timeout=20)
        row1 = next((x for x in r1.json() if x["version"] == version), None)
        assert row1["views"] >= views0 + 3


# ---------- Stats auth ----------
class TestStatsAuth:
    def test_stats_requires_admin(self, student_h):
        r = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=student_h, timeout=20)
        assert r.status_code in (401, 403)

    def test_stats_unauth(self):
        r = requests.get(f"{BASE_URL}/api/admin/announcement/stats", timeout=20)
        assert r.status_code in (401, 403)

    def test_stats_returns_rows(self, admin_h):
        r = requests.get(f"{BASE_URL}/api/admin/announcement/stats", headers=admin_h, timeout=20)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        for row in rows:
            assert "views" in row and "clicks" in row and "copies" in row and "closes" in row
            assert "click_rate" in row and "is_current" in row
            assert "version" in row and "message" in row
        # Only one is_current true
        currents = [x for x in rows if x["is_current"]]
        assert len(currents) <= 1


# ---------- Save-announcement version behaviour ----------
class TestAnnouncementVersioning:
    def test_same_content_keeps_version(self, admin_h):
        body = {"enabled": True, "message": "TEST_ver stable", "style": "info",
                "cta_label": "A", "cta_url": "/a", "coupon_code": "VSAME"}
        r1 = _put_ann(body, admin_h)
        v1 = r1.json()["announcement"]["version"]
        # Toggle enabled off (not a content key) -> same version
        r2 = _put_ann({**body, "enabled": False}, admin_h)
        v2 = r2.json()["announcement"]["version"]
        assert v2 == v1
        # Re-save identical content -> same version
        r3 = _put_ann(body, admin_h)
        assert r3.json()["announcement"]["version"] == v1

    def test_content_change_new_version(self, admin_h):
        body = {"enabled": True, "message": "TEST_ver A", "style": "info", "coupon_code": ""}
        v1 = _put_ann(body, admin_h).json()["announcement"]["version"]
        body2 = {**body, "message": "TEST_ver B"}
        v2 = _put_ann(body2, admin_h).json()["announcement"]["version"]
        assert v1 != v2


# ---------- Final restoration ----------
class TestFinalRestore:
    def test_restore_theme_ocean(self, admin_h):
        r = _put_layout({"preset": "ocean", "primary": "#2563eb", "accent": "#06b6d4"}, admin_h)
        assert r.status_code == 200
        assert r.json()["theme"] == {"preset": "ocean", "primary": "#2563eb", "accent": "#06b6d4"}

    def test_restore_announcement(self, admin_h):
        body = {"enabled": True, "message": "Get 20% off your first test series",
                "style": "offer", "cta_label": "Explore", "cta_url": "/test-series",
                "coupon_code": "WELCOME20", "starts_at": None, "ends_at": None}
        r = _put_ann(body, admin_h)
        assert r.status_code == 200
        pub = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
        assert pub["announcement"]["message"] == "Get 20% off your first test series"
        assert pub["announcement"]["coupon_code"] == "WELCOME20"
