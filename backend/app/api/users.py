from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.models.user import User, Invitation
from app.services.email import send_invite_email

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


# ── Current user profile ──────────────────────────────────────

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "honor_points": current_user.honor_points,
        "honor_rank": current_user.honor_rank,
        "fp_member": current_user.fp_member,
        "invites_remaining": current_user.invites_remaining,
        "created_at": current_user.created_at,
    }


# ── Send invite ───────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: EmailStr


@router.post("/invite")
async def send_invite(
    body: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.invites_remaining <= 0:
        raise HTTPException(400, "Du har ingen invitasjoner igjen")

    # Check not already invited
    existing = await db.scalar(
        select(Invitation).where(
            Invitation.invited_email == body.email,
            Invitation.used_by == None,
            Invitation.expires_at > datetime.now(timezone.utc),
        )
    )
    if existing:
        raise HTTPException(400, "Denne e-posten har allerede en aktiv invitasjon")

    # Check not already a user
    existing_user = await db.scalar(
        select(User).where(User.email == body.email)
    )
    if existing_user:
        raise HTTPException(400, "Denne e-posten er allerede registrert")

    invite = Invitation(
        invited_by=current_user.id,
        invited_email=body.email,
        expires_at=datetime.now(timezone.utc) + timedelta(
            days=settings.invite_token_expire_days
        ),
    )
    db.add(invite)
    current_user.invites_remaining -= 1
    await db.commit()

    send_invite_email(body.email, current_user.username, str(invite.token))

    return {
        "message": f"Invitasjon sendt til {body.email}",
        "invites_remaining": current_user.invites_remaining,
    }


# ── My invites ────────────────────────────────────────────────

@router.get("/my-invites")
async def get_my_invites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    invites = await db.scalars(
        select(Invitation)
        .where(Invitation.invited_by == current_user.id)
        .order_by(Invitation.created_at.desc())
    )
    result = []
    for inv in invites.all():
        result.append({
            "email": inv.invited_email,
            "used": inv.used_by is not None,
            "used_at": inv.used_at,
            "expires_at": inv.expires_at,
            "reward_applied": inv.reward_applied,
        })
    return result
