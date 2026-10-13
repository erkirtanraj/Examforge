"""Performance middleware: short-lived server cache for public catalog reads + static upload headers."""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

CACHE_TTL = 60
CACHEABLE = {"/api/site", "/api/categories", "/api/subjects", "/api/test-series", "/api/courses", "/api/study-materials"}
NO_INVALIDATE = ("/api/auth", "/api/attempts", "/api/payments", "/api/webhooks", "/api/my", "/api/coupons", "/api/tests/", "/api/announcement/", "/api/lessons/")


class PublicCacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.store = {}

    async def dispatch(self, request, call_next):
        path, method = request.url.path, request.method
        if path.startswith("/api/uploads/"):
            resp = await call_next(request)
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            resp.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
            resp.headers["X-Content-Type-Options"] = "nosniff"
            return resp
        if method == "GET" and path in CACHEABLE:
            key = f"{path}?{request.url.query}"
            hit = self.store.get(key)
            if hit and hit[0] > time.monotonic():
                return Response(hit[1], media_type="application/json", headers={"X-Cache": "HIT"})
            resp = await call_next(request)
            if resp.status_code != 200:
                return resp
            body = b"".join([chunk async for chunk in resp.body_iterator])
            self.store[key] = (time.monotonic() + CACHE_TTL, body)
            return Response(body, media_type="application/json", headers={"X-Cache": "MISS"})
        resp = await call_next(request)
        if method in ("POST", "PUT", "PATCH", "DELETE") and resp.status_code < 400 and not path.startswith(NO_INVALIDATE):
            self.store.clear()
        return resp
