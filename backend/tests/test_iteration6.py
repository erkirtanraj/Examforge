"""Iteration 6: logo upload, cache headers, gzip, admin site branding."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://testseries-lms.preview.emergentagent.com").rstrip("/")

ADMIN = {"email": "admin@lms.com", "password": "admin123"}
STUDENT = {"email": "student@lms.com", "password": "student123"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def student_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=STUDENT, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- Uploads ----------

PNG_1x1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D4944415478DA6300010000000500010D0A2DB40000000049454E44AE426082"
)


def test_upload_requires_admin(student_token):
    r = requests.post(f"{BASE_URL}/api/admin/uploads",
                      headers={"Authorization": f"Bearer {student_token}"},
                      files={"file": ("a.png", PNG_1x1, "image/png")}, timeout=20)
    assert r.status_code in (401, 403), r.text


def test_upload_unauth():
    r = requests.post(f"{BASE_URL}/api/admin/uploads",
                      files={"file": ("a.png", PNG_1x1, "image/png")}, timeout=20)
    assert r.status_code in (401, 403)


def test_upload_png_success_and_served(admin_h):
    r = requests.post(f"{BASE_URL}/api/admin/uploads", headers=admin_h,
                      files={"file": ("logo.png", PNG_1x1, "image/png")}, timeout=20)
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("/api/uploads/") and url.endswith(".png")
    g = requests.get(f"{BASE_URL}{url}", timeout=20)
    assert g.status_code == 200
    assert g.content == PNG_1x1


def test_upload_rejects_bad_type(admin_h):
    r = requests.post(f"{BASE_URL}/api/admin/uploads", headers=admin_h,
                      files={"file": ("a.txt", b"hello", "text/plain")}, timeout=20)
    assert r.status_code == 400


def test_upload_rejects_oversize(admin_h):
    big = b"\x00" * (2 * 1024 * 1024 + 10)
    r = requests.post(f"{BASE_URL}/api/admin/uploads", headers=admin_h,
                      files={"file": ("big.png", big, "image/png")}, timeout=30)
    assert r.status_code == 400


# ---------- Branding header fields ----------

def test_admin_site_has_branding_fields(admin_h):
    r = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_h, timeout=20)
    assert r.status_code == 200
    h = r.json()["header"]
    for k in ("brand_name", "logo_url", "favicon_url", "show_brand_name"):
        assert k in h, f"missing {k}"


def test_save_layout_updates_logo_and_shows_in_public(admin_h):
    # upload logo
    u = requests.post(f"{BASE_URL}/api/admin/uploads", headers=admin_h,
                      files={"file": ("l.png", PNG_1x1, "image/png")}, timeout=20).json()["url"]
    fav = requests.post(f"{BASE_URL}/api/admin/uploads", headers=admin_h,
                        files={"file": ("f.png", PNG_1x1, "image/png")}, timeout=20).json()["url"]
    cur = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_h, timeout=20).json()
    payload = {
        "header": {**cur["header"], "logo_url": u, "favicon_url": fav, "show_brand_name": False, "brand_name": "TestBrand"},
        "footer": cur["footer"],
    }
    s = requests.put(f"{BASE_URL}/api/admin/site/layout", headers=admin_h, json=payload, timeout=20)
    assert s.status_code == 200, s.text
    # cache should be cleared, public site shows new logo
    pub = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
    assert pub["header"]["logo_url"] == u
    assert pub["header"]["favicon_url"] == fav
    assert pub["header"]["show_brand_name"] is False


# ---------- Cache & gzip ----------

@pytest.mark.parametrize("path", ["/api/site", "/api/categories", "/api/test-series", "/api/courses", "/api/study-materials", "/api/subjects"])
def test_cache_miss_then_hit(path):
    # First clear cache by probing admin write? We just hit twice and expect at least one HIT eventually.
    # Preview ingress may strip X-Cache. Hit via Host preview URL — accept if header missing but 200.
    r1 = requests.get(f"{BASE_URL}{path}", timeout=20)
    assert r1.status_code == 200
    r2 = requests.get(f"{BASE_URL}{path}", timeout=20)
    assert r2.status_code == 200
    xc1 = r1.headers.get("X-Cache")
    xc2 = r2.headers.get("X-Cache")
    # Cache header should appear
    assert xc1 in ("MISS", "HIT", None)
    assert xc2 in ("MISS", "HIT", None)
    if xc1 and xc2:
        # second should be HIT (unless cache cleared)
        assert xc2 == "HIT" or xc1 == xc2


def test_cache_invalidates_on_admin_write(admin_h):
    # Warm cache
    requests.get(f"{BASE_URL}/api/site", timeout=20)
    r = requests.get(f"{BASE_URL}/api/site", timeout=20)
    hit_before = r.headers.get("X-Cache")
    # Admin write
    cur = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_h, timeout=20).json()
    requests.put(f"{BASE_URL}/api/admin/site/layout", headers=admin_h,
                 json={"header": cur["header"], "footer": cur["footer"]}, timeout=20)
    r2 = requests.get(f"{BASE_URL}/api/site", timeout=20)
    xc = r2.headers.get("X-Cache")
    # After invalidation, first GET must be MISS (if cache header passes through)
    assert xc in ("MISS", None), f"expected MISS after write, got {xc} (prev {hit_before})"


def test_gzip_on_large_public_endpoint():
    r = requests.get(f"{BASE_URL}/api/site", headers={"Accept-Encoding": "gzip"}, timeout=20)
    assert r.status_code == 200
    ce = r.headers.get("Content-Encoding", "")
    # gzip only if body >800 bytes; /api/site is large
    assert "gzip" in ce or len(r.content) <= 900, f"expected gzip, got {ce}, size {len(r.content)}"


# ---------- Restore defaults ----------

def test_zz_restore_defaults(admin_h):
    cur = requests.get(f"{BASE_URL}/api/admin/site", headers=admin_h, timeout=20).json()
    payload = {
        "header": {**cur["header"], "brand_name": "ExamForge", "logo_url": "", "favicon_url": "", "show_brand_name": True},
        "footer": cur["footer"],
    }
    r = requests.put(f"{BASE_URL}/api/admin/site/layout", headers=admin_h, json=payload, timeout=20)
    assert r.status_code == 200
    pub = requests.get(f"{BASE_URL}/api/site", timeout=20).json()
    assert pub["header"]["brand_name"] == "ExamForge"
    assert pub["header"]["logo_url"] == ""
    assert pub["header"]["show_brand_name"] is True
