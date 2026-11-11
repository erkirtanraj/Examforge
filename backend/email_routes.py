"""SMTP email settings and MySQL-backed self-service password reset."""
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
import asyncio
import hashlib
import logging
import secrets
import smtplib
import ssl

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional

from mysql_persistence.identity import InvalidOrExpiredResetToken

log = logging.getLogger("lms.email")
RESET_TTL = timedelta(hours=1)
MAX_REQUESTS = 3
WINDOW = timedelta(minutes=15)
GENERIC = {"ok": True, "message": "If an account exists for this email, a reset link has been sent."}


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
    password: str = Field(min_length=6, max_length=128)


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
        if not upd["site_url"].startswith(("http://", "https://")):
            raise HTTPException(400, "Website URL must start with http:// or https://")
        if data.password:
            upd["password"] = data.password
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.update_one({"key": "smtp"}, {"$set": upd}, upsert=True)
        return await get_email_settings()

    @r.post("/admin/settings/email/test")
    async def test_email(data: TestEmailIn, _=admin):
        brand = await get_brand()
        await send(data.to, f"{brand} · test email", f"SMTP is working for {brand}.",
                   f"<p>SMTP is working for <b>{escape(brand)}</b>.</p>")
        return {"ok": True}

    @r.post("/auth/forgot-password")
    async def forgot_password(data: ForgotIn, request: Request):
        repository = getattr(request.app.state, "identity_repository", None)
        if repository is None:
            raise HTTPException(503, "Identity service unavailable")

        email = str(data.email).strip().lower()
        user = await repository.get_by_email(email, include_password_hash=False)
        if not user or user.get("status") != "active":
            return GENERIC

        c = await cfg()
        if not c.get("host") or not c.get("site_url"):
            log.warning("Password reset requested while SMTP is not configured")
            return GENERIC

        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        allowed = await repository.create_reset_token_if_below_limit(
            token_hash=_hash(token),
            user_id=user["id"],
            expires_at=now + RESET_TTL,
            since=now - WINDOW,
            max_requests=MAX_REQUESTS,
        )
        if not allowed:
            return GENERIC

        link = f"{c['site_url'].rstrip('/')}/reset-password?token={token}"
        brand = await get_brand()
        safe_name, safe_brand, safe_link = escape(user.get("name") or "there"), escape(brand), escape(link, quote=True)
        text = (f"Hi {user.get('name') or 'there'},\n\nReset your {brand} password using this link "
                f"(valid for 1 hour):\n{link}\n\nIf you didn't request this, ignore this email.")
        html = (
            "<div style='font-family:Arial,sans-serif;max-width:520px'>"
            f"<p>Hi {safe_name},</p><p>We received a request to reset your <b>{safe_brand}</b> password.</p>"
            f"<p><a href='{safe_link}' style='display:inline-block;background:#2563eb;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none'>Reset password</a></p>"
            "<p style='color:#666;font-size:13px'>This link expires in 1 hour and can be used once. "
            "If you didn't request this, you can ignore this email.</p></div>"
        )
        try:
            await send(email, f"Reset your {brand} password", text, html)
        except HTTPException as exc:
            # Preserve the generic response to avoid disclosing account existence.
            log.error("Password reset email delivery failed: %s", exc.detail)
        return GENERIC

    @r.get("/auth/reset-password/{token}")
    async def check_reset_token(token: str, request: Request):
        repository = getattr(request.app.state, "identity_repository", None)
        if repository is None:
            raise HTTPException(503, "Identity service unavailable")
        reset = await repository.get_valid_reset_token(token_hash=_hash(token))
        return {"valid": reset is not None}

    @r.post("/auth/reset-password")
    async def reset_password(data: ResetIn, request: Request):
        repository = getattr(request.app.state, "identity_repository", None)
        if repository is None:
            raise HTTPException(503, "Identity service unavailable")
        try:
            await repository.consume_reset_token(
                token_hash=_hash(data.token),
                new_password_hash=hash_pw(data.password),
            )
        except InvalidOrExpiredResetToken as exc:
            raise HTTPException(
                400,
                "This reset link is invalid or has expired. Please request a new one.",
            ) from exc
        return {"ok": True}

    return r
