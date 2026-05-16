from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.deps import require_admin, get_current_user
from app.models.galaxy import GameRound, SolarSystem, Planet, SystemRoute, ExploredSystem
from app.models.user import User
from app.services.galaxy import generate_galaxy
from app.services.visibility import (
    reveal_own_system, get_explored_system_ids,
    reveal_system_and_neighbors
)

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    round_ = await db.scalar(
        select(GameRound).order_by(GameRound.id.desc())
    )
    if not round_:
        return {"status": "no_round", "message": "Ingen spillrunde opprettet ennå"}
    return {
        "round_id": round_.id,
        "status": round_.status,
        "current_tick": round_.current_tick,
        "duration_days": round_.duration_days,
        "started_at": round_.started_at,
        "ends_at": round_.ends_at,
    }


@router.get("/galaxy")
async def get_galaxy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returnerer bare systemer spilleren har utforsket (fog of war).
    Admin/superadmin/elder_race ser hele galaksen.
    """
    all_systems = await db.scalars(select(SolarSystem))
    system_list = list(all_systems.all())

    # Admin ser alt
    if current_user.role in ("admin", "superadmin", "elder_race"):
        result = []
        for s in system_list:
            # Hent naboer
            routes = await db.scalars(
                select(SystemRoute.to_system_id).where(
                    SystemRoute.from_system_id == s.id
                )
            )
            neighbors = [str(r) for r in routes.all()]
            result.append({
                "id": str(s.id),
                "name": s.name,
                "hex_q": s.hex_q,
                "hex_r": s.hex_r,
                "owner_id": str(s.owner_id) if s.owner_id else None,
                "is_npc": s.is_npc,
                "is_elder_race": s.is_elder_race,
                "is_unknown_region": s.is_unknown_region,
                "neighbors": neighbors,
                "explored": True,
            })
        return {"systems": result, "total": len(result)}

    # Vanlig spiller — bare utforskede systemer
    explored_ids = await get_explored_system_ids(db, current_user.id)

    result = []
    for s in system_list:
        if s.id not in explored_ids:
            continue
        routes = await db.scalars(
            select(SystemRoute.to_system_id).where(
                SystemRoute.from_system_id == s.id
            )
        )
        neighbors = [str(r) for r in routes.all()]
        result.append({
            "id": str(s.id),
            "name": s.name,
            "hex_q": s.hex_q,
            "hex_r": s.hex_r,
            "owner_id": str(s.owner_id) if s.owner_id else None,
            "is_npc": s.is_npc,
            "is_elder_race": s.is_elder_race,
            "is_unknown_region": s.is_unknown_region,
            "neighbors": neighbors,
            "explored": True,
        })

    return {"systems": result, "total": len(result)}


@router.get("/galaxy/target-planets")
async def get_target_planets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returnerer alle planeter i utforskede systemer som spilleren
    kan sende flåter til. Brukes i fleet-send UI.
    """
    explored_ids = await get_explored_system_ids(db, current_user.id)

    if not explored_ids:
        return {"planets": []}

    planets = await db.scalars(
        select(Planet).where(Planet.solar_system_id.in_(explored_ids))
    )

    result = []
    for p in planets.all():
        system = await db.get(SolarSystem, p.solar_system_id)
        result.append({
            "id": str(p.id),
            "name": p.name,
            "system_id": str(p.solar_system_id),
            "system_name": system.name if system else "?",
            "planet_type": p.planet_type,
            "owner_id": str(p.owner_id) if p.owner_id else None,
            "is_own": p.owner_id == current_user.id,
            "same_system": p.solar_system_id in [
                s for s in explored_ids
                if s == p.solar_system_id
            ],
            "travel_ticks": p.travel_ticks,
        })

    return {"planets": result}


class StartGameRequest(BaseModel):
    duration_days: int = 30
    seed: Optional[int] = None


@router.post("/start")
async def start_game(
    body: StartGameRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = await db.scalar(
        text("SELECT id FROM game_round WHERE status::text = 'active' LIMIT 1")
    )
    if existing:
        raise HTTPException(400, "Det finnes allerede en aktiv spillrunde")

    result = await db.execute(
        text("SELECT id FROM users WHERE role::text = 'player' AND is_active = true AND email_verified = true")
    )
    player_ids = [row[0] for row in result.fetchall()]

    if not player_ids:
        raise HTTPException(400, "Ingen aktive spillere å starte runden med")

    players = await db.scalars(
        select(User).where(User.id.in_(player_ids))
    )
    player_list = list(players.all())

    elder_result = await db.execute(
        text("SELECT id FROM users WHERE role::text = 'elder_race' AND is_active = true LIMIT 1")
    )
    elder_row = elder_result.fetchone()
    elder_race = None
    if elder_row:
        elder_race = await db.get(User, elder_row[0])

    now = datetime.now(timezone.utc)
    round_ = GameRound(
        status="active",
        current_tick=0,
        duration_days=body.duration_days,
        started_at=now,
        ends_at=now + timedelta(days=body.duration_days),
    )
    db.add(round_)
    await db.flush()

    stats = await generate_galaxy(db, player_list, elder_race, body.seed)

    # Avslør eget system for alle spillere ved game start
    for player in player_list:
        await reveal_own_system(db, player.id)
    if elder_race:
        await reveal_own_system(db, elder_race.id)

    await db.commit()

    return {
        "message": f"Spillrunde startet med {len(player_list)} spillere",
        "round_id": round_.id,
        "duration_days": body.duration_days,
        "ends_at": round_.ends_at,
        **stats,
    }


@router.post("/reset")
async def reset_game(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.models.game import TickLog, CombatLog, Ship, FleetMission, FleetMissionShip, BuildQueue
    await db.execute(delete(FleetMissionShip))
    await db.execute(delete(FleetMission))
    await db.execute(delete(BuildQueue))
    await db.execute(delete(Ship))
    await db.execute(delete(CombatLog))
    await db.execute(delete(TickLog))
    await db.execute(delete(ExploredSystem))
    await db.execute(delete(Planet))
    await db.execute(delete(SystemRoute))
    await db.execute(delete(SolarSystem))
    await db.execute(delete(GameRound))
    # Reset exploration flags på brukere
    await db.execute(
        text("UPDATE users SET has_built_expedition = FALSE")
    )
    await db.commit()
    return {"message": "Spillet er nullstilt. Klar for ny runde."}


@router.get("/my-system")
async def get_my_system(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    system = await db.scalar(
        select(SolarSystem).where(SolarSystem.owner_id == current_user.id)
    )
    if not system:
        return {"message": "Du har ikke et solsystem ennå — venter på spillstart"}

    planets = await db.scalars(
        select(Planet)
        .where(Planet.solar_system_id == system.id)
        .order_by(Planet.orbit_slot)
    )

    planet_list = []
    for p in planets.all():
        planet_list.append({
            "id": str(p.id),
            "name": p.name,
            "type": p.planet_type,
            "orbit_slot": p.orbit_slot,
            "travel_ticks": p.travel_ticks,
            "blockade_status": p.blockade_status,
            "resources": {
                "metal": p.metal,
                "energy": p.energy,
                "gas": p.gas,
            },
            "production_per_tick": {
                "metal": p.metal_production,
                "energy": p.energy_production,
                "gas": p.gas_production,
            },
            "score": p.score,
        })

    return {
        "system": {
            "id": str(system.id),
            "name": system.name,
            "hex_q": system.hex_q,
            "hex_r": system.hex_r,
        },
        "planets": planet_list,
        "total_production_per_tick": {
            "metal": sum(p["production_per_tick"]["metal"] for p in planet_list),
            "energy": sum(p["production_per_tick"]["energy"] for p in planet_list),
            "gas": sum(p["production_per_tick"]["gas"] for p in planet_list),
        },
    }


@router.post("/tick")
async def trigger_tick(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.services.tick import _process_tick
    await _process_tick(db)
    return {"message": "Tick prosessert"}


@router.get("/tick-log")
async def get_tick_log(
    db: AsyncSession = Depends(get_db),
):
    from app.models.game import TickLog
    logs = await db.scalars(
        select(TickLog).order_by(TickLog.tick_number.desc()).limit(20)
    )
    return [
        {
            "tick": t.tick_number,
            "status": t.status,
            "started_at": t.started_at,
            "ended_at": t.ended_at,
            "planets_processed": t.planets_processed,
            "missions_resolved": t.missions_resolved,
            "combats_resolved": t.combats_resolved,
        }
        for t in logs.all()
    ]
