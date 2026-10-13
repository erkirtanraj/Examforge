"""SMTP email settings (admin) and self-service password reset."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from urllib.parse import urlparse
from fastapi import Request
import asyncio, hashlib, secrets, smtplib, ssl, time, logging, os

log = logging.getLogger("lms.email")
RESET_TTL = timedelta(hours=1)
MAX_REQUESTS = 3
WINDOW = timedelta(minutes=15)
GENERIC = {"ok": True, "message": "If an account exists for this email, a reset link has been sent."}
_FORGOT_REQUESTS: dict[str, list[float]] = {}


def _limit_forgot_requests(request: Request) -> None:
    now = time.monotonic()
    ip = request.client.host if request.client else "unknown"
    key = hashlib.sha256(ip.encode("utf-8")).hexdigest()
    hits = [t for t in _FORGOT_REQUESTS.get(key, []) if now - t < 900]
    if len(hits) >= 20:
        retry = max(1, int(900 - (now - hits[0])))
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.",
                            headers={"Retry-After": str(retry)})
    _FORGOT_REQUESTS[key] = hits + [now]
    if len(_FORGOT_REQUESTS) > 10000:
        cutoff = now - 900
        for bucket in list(_FORGOT_REQUESTS):
            fresh = [t for t in _FORGOT_REQUESTS[bucket] if t >= cutoff]
            if fresh:
                _FORGOT_REQUESTS[bucket] = fresh
            else:
                _FORGOT_REQUESTS.pop(bucket, None)


class SmtpIn(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(587, ge=1, le=65535)
    security: Literal["starttls", "ssl", "none"] = "starttls"
    username: str = ""
    password: Optional[str] = None  # blank keeps the saved password
    from_email: EmailStr
    from_name: str = ""
    site_url: str = Field(min_length=8)


class TestEmailIn(BaseModel):
    to: EmailStr


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=20)
    password: str = Field(min_length=10, max_length=72)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _send_sync(cfg: dict, to: str, subject: str, text: str, html: str):
    msg = EmailMessage()
    msg["Subject"], msg["To"] = subject, to
    msg["From"] = formataddr((cfg.get("from_name") or "", cfg["from_email"]))
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    ctx = ssl.create_default_context()
    if cfg["security"] == "ssl":
        server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=20, context=ctx)
    else:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=20)
    with server:
        if cfg["security"] == "starttls":
            server.starttls(context=ctx)
        if cfg.get("username"):
            server.login(cfg["username"], cfg.get("password") or "")
        server.send_message(msg)


def build_email_router(db, require_roles, get_brand, hash_pw):
    r = APIRouter(prefix="/api")
    admin = Depends(require_roles("admin"))

    async def cfg():
        return await db.settings.find_one({"key": "smtp"}, {"_id": 0}) or {}

    async def send(to: str, subject: str, text: str, html: str):
        c = await cfg()
        if not c.get("host"):
            raise HTTPException(400, "Email (SMTP) is not configured yet")
        try:
            await asyncio.to_thread(_send_sync, c, to, subject, text, html)
        except smtplib.SMTPAuthenticationError:
            raise HTTPException(400, "SMTP login failed — check the username and password")
        except (smtplib.SMTPException, OSError) as e:
            raise HTTPException(400, f"Could not send email: {e}")

    @r.get("/admin/settings/email")
    async def get_email_settings(_=admin):
        c = await cfg()
        return {k: c.get(k, d) for k, d in {"host": "", "port": 587, "security": "starttls", "username": "", "from_email": "",
                                              "from_name": "", "site_url": "", "updated_at": None}.items()} | {"has_password": bool(c.get("password"))}

    @r.put("/admin/settings/email")
    async def save_email_settings(data: SmtpIn, _=admin):
        upd = data.model_dump(exclude={"password"})
        upd["site_url"] = upd["site_url"].rstrip("/")
        parsed_url = urlparse(upd["site_url"])
        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname or parsed_url.username or parsed_url.password:
            raise HTTPException(400, "Enter a valid website URL")
        if parsed_url.query or parsed_url.fragment:
            raise HTTPException(400, "Website URL must not contain a query or fragment")
        app_env = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "production")).strip().lower()
        if app_env in ("prod", "production") and parsed_url.scheme != "https":
            raise HTTPException(400, "Production website URL must use HTTPS")
        if data.security == "none" and (data.username or data.password):
            raise HTTPException(400, "SMTP authentication requires SSL or STARTTLS")
        if data.password:
            upd["password"] = data.password
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.update_one({"key": "smtp"}, {"$set": upd}, upsert=True)
        return await get_email_settings()

    @r.post("/admin/settings/email/test")
    async def test_email(data: TestEmailIn, _=admin):
        brand = await get_brand()
        await send(data.to, f"{brand} · test email", f"SMTP is working for {brand}.",
                   f"<p>SMTP is working for <b>{brand}</b>.</p>")
        return {"ok": True}

    @r.post("/auth/forgot-password")
    async def forgot_password(request: Request, data: ForgotIn):
        _limit_forgot_requests(request)
        email = data.email.lower()
        user = await db.users.find_one({"email": email}, {"_id": 0, "id": 1, "name": 1, "status": 1})
        if not user or user.get("status") == "suspended":
            return GENERIC
        now = datetime.now(timezone.utc)
        if await db.password_reset_tokens.count_documents({"user_id": user["id"], "created_at": {"$gt": now - WINDOW}}) >= MAX_REQUESTS:
            return GENERIC
        c = await cfg()
        if not c.get("host") or not c.get("site_url"):
            log.warning("Password reset requested for %s but SMTP is not configured", email)
            return GENERIC
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({"token_hash": _hash(token), "user_id": user["id"], "used": False,
                                                   "created_at": now, "expires_at": now + RESET_TTL})
        link = f"{c['site_url']}/reset-password?token={token}"
        brand = await get_brand()
        text = f"Hi {user['name']},\n\nReset your {brand} password using this link (valid for 1 hour):\n{link}\n\nIf you didn't request this, ignore this email."
        html_name = escape(user["name"])
        html_brand = escape(brand)
        html_link = escape(link, quote=True)
        html = (f"<div style='font-family:Arial,sans-serif;max-width:520px'><p>Hi {html_name},</p>"
                f"<p>We received a request to reset your <b>{html_brand}</b> password.</p>"
                f"<p><a href='{html_link}' style='display:inline-block;background:#2563eb;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none'>Reset password</a></p>"
                f"<p style='color:#666;font-size:13px'>This link expires in 1 hour and can be used once. If you didn't request it, you can ignore this email.</p></div>")
        try:
            await send(email, f"Reset your {brand} password", text, html)
        except HTTPException as e:
            log.error("Password reset email failed for %s: %s", email, e.detail)
        return GENERIC

    @r.get("/auth/reset-password/{token}")
    async def check_reset_token(token: str):
        t = await db.password_reset_tokens.find_one({"token_hash": _hash(token)}, {"_id": 0})
        if not t or t["used"]:
            return {"valid": False}
        return {"valid": t["expires_at"].replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)}

    @r.post("/auth/reset-password")
    async def reset_password(data: ResetIn):
        if len(data.password.encode("utf-8")) > 72:
            raise HTTPException(422, "Password must be 72 UTF-8 bytes or fewer")
        now = datetime.now(timezone.utc)
        t = await db.password_reset_tokens.find_one_and_update(
            {"token_hash": _hash(data.token), "used": False, "expires_at": {"$gt": now}},
            {"$set": {"used": True, "used_at": now}})
        if not t:
            raise HTTPException(400, "This reset link is invalid or has expired. Please request a new one.")
        await db.users.update_one({"id": t["user_id"]}, {"$set": {
            "password_hash": hash_pw(data.password), "tokens_valid_after": int(time.time()), "password_reset_at": now.isoformat()}})
        await db.password_reset_tokens.update_many({"user_id": t["user_id"], "used": False}, {"$set": {"used": True}})
        return {"ok": True}

    return r


async def ensure_indexes(db):
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
