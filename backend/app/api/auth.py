from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.config import get_settings
from app.services.email import (
    send_verification_email, send_invite_email, send_password_reset_email
)
from app.schemas.auth import (
    RegisterRequest, LoginRequest, InviteRequest,
    TokenResponse, MessageResponse,
)
from app.models.user import User, Invitation, EmailVerification

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


# ── Register ─────────────────────────────────────────────────

@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Validate invite token
    invite = await db.scalar(
        select(Invitation).where(
            Invitation.token == body.invite_token,
            Invitation.used_by == None,
            Invitation.expires_at > datetime.now(timezone.utc),
        )
    )
    if not invite:
        raise HTTPException(400, "Ugyldig eller utløpt invitasjon")

    # Check uniqueness
    existing = await db.scalar(
        select(User).where(
            (User.email == body.email) | (User.username == body.username)
        )
    )
    if existing:
        raise HTTPException(400, "E-post eller brukernavn er allerede i bruk")

    # Create user
    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        invited_by=invite.invited_by,
        invites_remaining=settings.invites_per_player,
    )
    db.add(user)
    await db.flush()  # get user.id

    # Mark invite as used
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)

    # Create email verification token
    verification = EmailVerification(
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(
            hours=settings.email_verify_token_expire_hours
        ),
    )
    db.add(verification)
    await db.commit()

    # Send verification email
    send_verification_email(user.email, user.username, str(verification.token))

    return {"message": "Konto opprettet. Sjekk e-posten din for bekreftelseslenke."}


# ── Verify email ─────────────────────────────────────────────

@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    verification = await db.scalar(
        select(EmailVerification).where(
            EmailVerification.token == token,
            EmailVerification.verified_at == None,
            EmailVerification.expires_at > datetime.now(timezone.utc),
        )
    )
    if not verification:
        raise HTTPException(400, "Ugyldig eller utløpt verifiseringslenke")

    verification.verified_at = datetime.now(timezone.utc)
    user = await db.get(User, verification.user_id)
    user.email_verified = True
    user.is_active = True
    await db.commit()

    return {"message": "E-post bekreftet! Du kan nå logge inn."}


# ── Login ─────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email))

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Feil e-post eller passord")
    if not user.email_verified:
        raise HTTPException(403, "E-post ikke bekreftet ennå")
    if not user.is_active:
        raise HTTPException(403, "Konto er deaktivert")

    # Superadmin requires TOTP
    if user.role == "superadmin":
        if not body.totp_code:
            raise HTTPException(401, "TOTP-kode kreves for superadmin")
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(body.totp_code):
            raise HTTPException(401, "Ugyldig TOTP-kode")

    payload = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    # httpOnly cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


# ── Refresh token ─────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(401, "Ingen refresh token")

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Ugyldig refresh token")

    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "Bruker ikke funnet")

    new_payload = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(new_payload)
    new_refresh = create_refresh_token(new_payload)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ── Logout ────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logget ut"}


# ── Send invite ───────────────────────────────────────────────

@router.post("/invite", response_model=MessageResponse)
async def send_invite(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    # current_user injected via dependency in real impl
):
    # TODO: inject current_user via get_current_user dependency
    # For now, placeholder showing the logic
    raise HTTPException(501, "Krever auth dependency — implementeres i neste steg")


# ── Forgot password ───────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == email))
    # Always return same message to avoid email enumeration
    if user and user.email_verified:
        token = str(uuid.uuid4())
        # Store reset token in Redis with 2hr expiry (via worker)
        send_password_reset_email(user.email, user.username, token)
    return {"message": "Om e-posten finnes, er en tilbakestillingslenke sendt."}
