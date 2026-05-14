from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.database import get_db
from app.core.deps import require_admin, require_superadmin
from app.core.config import get_settings
from app.models.user import User, Invitation

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


# ── Player overview ───────────────────────────────────────────

@router.get("/players")
async def list_players(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    players = await db.scalars(
        select(User)
        .where(User.role == "player")
        .order_by(User.created_at.desc())
    )
    return [
        {
            "id": str(p.id),
            "username": p.username,
            "email": p.email,
            "email_verified": p.email_verified,
            "is_active": p.is_active,
            "honor_points": p.honor_points,
            "honor_rank": p.honor_rank,
            "invites_remaining": p.invites_remaining,
            "fp_member": p.fp_member,
            "created_at": p.created_at,
        }
        for p in players.all()
    ]


# ── Admin creates invite (rewards go to Elder Race) ───────────

class AdminInviteRequest(BaseModel):
    email: Optional[EmailStr] = None  # optional — can create generic link


@router.post("/invite")
async def admin_create_invite(
    body: AdminInviteRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.email import send_invite_email

    invite = Invitation(
        invited_by=current_user.id,
        invited_email=body.email,
        expires_at=datetime.now(timezone.utc) + timedelta(
            days=settings.invite_token_expire_days
        ),
    )
    db.add(invite)
    await db.commit()

    invite_url = f"{settings.game_base_url}/register?invite={invite.token}"

    if body.email:
        send_invite_email(body.email, "Forente Planeter Admin", str(invite.token))
        return {"message": f"Invitasjon sendt til {body.email}", "invite_url": invite_url}

    return {
        "message": "Invitasjonslenke opprettet",
        "invite_url": invite_url,
        "token": str(invite.token),
        "expires_at": invite.expires_at,
    }


# ── List all invites ──────────────────────────────────────────

@router.get("/invites")
async def list_invites(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    invites = await db.scalars(
        select(Invitation).order_by(Invitation.created_at.desc()).limit(100)
    )
    return [
        {
            "id": str(i.id),
            "invited_email": i.invited_email,
            "invited_by": str(i.invited_by),
            "used": i.used_by is not None,
            "used_at": i.used_at,
            "expires_at": i.expires_at,
            "reward_applied": i.reward_applied,
        }
        for i in invites.all()
    ]


# ── Deactivate player ─────────────────────────────────────────

@router.post("/players/{user_id}/deactivate")
async def deactivate_player(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    from uuid import UUID
    user = await db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(404, "Bruker ikke funnet")
    if user.role in ("admin", "superadmin"):
        raise HTTPException(403, "Kan ikke deaktivere admin-brukere")
    user.is_active = False
    await db.commit()
    return {"message": f"{user.username} er deaktivert"}


# ── Stats overview ────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    total_players = await db.scalar(
        select(func.count()).where(User.role == "player")
    )
    active_players = await db.scalar(
        select(func.count()).where(User.role == "player", User.is_active == True)
    )
    total_invites = await db.scalar(select(func.count(Invitation.id)))
    used_invites = await db.scalar(
        select(func.count()).where(Invitation.used_by != None)
    )
    return {
        "total_players": total_players,
        "active_players": active_players,
        "total_invites_sent": total_invites,
        "invites_used": used_invites,
    }
