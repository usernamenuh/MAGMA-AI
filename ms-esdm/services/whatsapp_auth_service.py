import asyncio
import re
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from models.whatsapp_auth_session import WhatsAppAuthSession
from core.config import settings
from utils.jwt_utils import verify_password


SESSION_MINUTES = 30
MAX_LOGIN_ATTEMPTS = 5


def _response(output: str, authenticated: bool = False) -> dict:
    return {"handled": True, "output": output, "authenticated": authenticated}


async def _get_or_create(db: AsyncSession, session_id: str) -> WhatsAppAuthSession:
    session = await db.get(WhatsAppAuthSession, session_id)
    if session is None:
        session = WhatsAppAuthSession(session_id=session_id)
        db.add(session)
        await db.flush()
    return session


async def is_whatsapp_authenticated(db: AsyncSession, session_id: str) -> bool:
    if not session_id.startswith("whatsapp-") or "@g.us" in session_id:
        return False
    session = await db.get(WhatsAppAuthSession, session_id)
    return bool(session and _is_authenticated(session))


def _is_authenticated(session: WhatsAppAuthSession) -> bool:
    return bool(
        session.state == "authenticated"
        and session.user_id
        and session.authenticated_until
        and session.authenticated_until > datetime.utcnow()
    )


async def _authenticate_remote(username: str, password: str) -> str | None:
    """Use the same authentication service as the web frontend."""
    if not settings.AUTH_API_BASE_URL:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{settings.AUTH_API_BASE_URL.rstrip('/')}/auth/login",
                json={"username": username, "password": password},
            )
        if response.status_code < 200 or response.status_code >= 300:
            return None
        payload = response.json()
        data = payload.get("data") or payload
        user = data.get("user") or payload.get("user") or {}
        access_token = (
            data.get("accessToken") or data.get("access_token")
            or payload.get("accessToken") or payload.get("access_token")
        )
        if not access_token:
            return None
        return str(user.get("id") or user.get("user_id") or username)
    except (httpx.HTTPError, ValueError, TypeError):
        return None


async def handle_whatsapp_auth(
    db: AsyncSession,
    session_id: str,
    message: str,
) -> dict | None:
    """Handle the hidden WhatsApp login state without logging credentials."""
    if not session_id.startswith("whatsapp-"):
        return None

    normalized = (message or "").strip()
    command = normalized.lower()
    session = await _get_or_create(db, session_id)

    is_group = "@g.us" in session_id
    auth_commands = {"/login", "/status", "/logout", "/batal"}
    if is_group and (command in auth_commands or session.state.startswith("awaiting_")):
        session.state = "anonymous"
        session.pending_email = None
        session.failed_attempts = 0
        await db.commit()
        return _response(
            "Untuk keamanan, login NARA hanya dapat dilakukan melalui chat pribadi, bukan grup WhatsApp."
        )

    if session.state == "authenticated" and not _is_authenticated(session):
        session.state = "anonymous"
        session.user_id = None
        session.authenticated_until = None
        await db.commit()

    if command == "/login":
        if _is_authenticated(session):
            return _response(
                "Anda sudah login. Ketik /status untuk melihat status sesi atau /logout untuk keluar.",
                authenticated=True,
            )
        session.state = "awaiting_email"
        session.pending_email = None
        session.failed_attempts = 0
        await db.commit()
        return _response(
            "FORM LOGIN NARA\nMasukkan email akun Anda.\nKetik /batal untuk membatalkan."
        )

    if command == "/batal":
        session.state = "anonymous"
        session.pending_email = None
        session.failed_attempts = 0
        await db.commit()
        return _response("Proses login dibatalkan.")

    if command == "/logout":
        session.state = "anonymous"
        session.pending_email = None
        session.user_id = None
        session.failed_attempts = 0
        session.authenticated_until = None
        await db.commit()
        return _response("Anda telah logout dari sesi upload dokumen.")

    if command == "/status":
        if _is_authenticated(session):
            remaining = max(
                1, int((session.authenticated_until - datetime.utcnow()).total_seconds() // 60)
            )
            return _response(
                f"Status: sudah login. Sesi berakhir sekitar {remaining} menit lagi.",
                authenticated=True,
            )
        return _response("Status: belum login. Ketik /login untuk masuk.")

    if session.state == "awaiting_email":
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            return _response("Format email tidak valid. Masukkan email akun atau ketik /batal.")
        session.pending_email = normalized.lower()
        session.state = "awaiting_password"
        await db.commit()
        return _response("Masukkan password Anda. Password tidak akan disimpan dalam riwayat NARA.")

    if session.state == "awaiting_password":
        result = await db.execute(select(User).where(User.email == session.pending_email))
        user = result.scalar_one_or_none()
        local_password_valid = bool(
            user
            and user.is_active
            and user.password_hash
            and await asyncio.to_thread(verify_password, normalized, user.password_hash)
        )
        authenticated_user_id = user.user_id if local_password_valid else None
        if not authenticated_user_id:
            authenticated_user_id = await _authenticate_remote(
                session.pending_email,
                normalized,
            )
        if authenticated_user_id:
            session.state = "authenticated"
            session.user_id = authenticated_user_id
            session.pending_email = None
            session.failed_attempts = 0
            session.authenticated_until = datetime.utcnow() + timedelta(minutes=SESSION_MINUTES)
            await db.commit()
            return _response(
                "Login berhasil. Sesi NARA Anda aktif selama 30 menit. Ketik /logout untuk keluar.",
                authenticated=True,
            )

        session.failed_attempts += 1
        remaining = MAX_LOGIN_ATTEMPTS - session.failed_attempts
        if remaining <= 0:
            session.state = "anonymous"
            session.pending_email = None
            session.failed_attempts = 0
            await db.commit()
            return _response("Login dibatalkan karena terlalu banyak percobaan gagal. Ketik /login untuk mencoba lagi.")
        await db.commit()
        return _response(
            f"Email atau password tidak sesuai. Sisa percobaan: {remaining}. Ketik /batal untuk membatalkan."
        )

    return None
