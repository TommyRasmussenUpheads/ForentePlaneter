"""
Visibility service for Forente Planeter — Fog of War.

Regler:
- Eget system: alltid synlig (settes ved game start)
- Naboer til eget system: synlig hvis spilleren har bygget minst ett ekspedisjonsskip
- Andre systemer: synlig hvis et ekspedisjonsskip har ankommet dit
- Ved ankomst til et system: det systemet + alle dets naboer avsløres
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.galaxy import SolarSystem, SystemRoute, ExploredSystem


async def reveal_system(
    db: AsyncSession,
    user_id: uuid.UUID,
    system_id: uuid.UUID,
) -> bool:
    """
    Avslør ett system for en spiller.
    Returnerer True hvis systemet var nytt (ikke sett før).
    """
    # Bruk INSERT ... ON CONFLICT DO NOTHING for idempotens
    stmt = pg_insert(ExploredSystem).values(
        user_id=user_id,
        system_id=system_id,
        explored_at=datetime.now(timezone.utc),
    ).on_conflict_do_nothing()
    result = await db.execute(stmt)
    return result.rowcount > 0


async def reveal_system_and_neighbors(
    db: AsyncSession,
    user_id: uuid.UUID,
    system_id: uuid.UUID,
) -> list[uuid.UUID]:
    """
    Avslør et system og alle dets naboer (via system_routes).
    Returnerer liste over system_id-er som var nye.
    """
    # Finn alle naboer via system_routes
    routes = await db.scalars(
        select(SystemRoute.to_system_id).where(
            SystemRoute.from_system_id == system_id
        )
    )
    neighbor_ids = list(routes.all())

    # Alle system_id-er som skal avsløres: selve systemet + naboer
    to_reveal = [system_id] + neighbor_ids

    newly_revealed = []
    for sid in to_reveal:
        is_new = await reveal_system(db, user_id, sid)
        if is_new:
            newly_revealed.append(sid)

    return newly_revealed


async def reveal_own_system(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    """
    Kalles ved game start — avslør spillerens eget system.
    Naboer avsløres først når ekspedisjonsskip er bygget.
    """
    system = await db.scalar(
        select(SolarSystem).where(SolarSystem.owner_id == user_id)
    )
    if system:
        await reveal_system(db, user_id, system.id)


async def reveal_neighbors_of_own_system(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[uuid.UUID]:
    """
    Kalles når spilleren bygger sitt første ekspedisjonsskip.
    Avslører naboene til eget system (men ikke naboenes naboer).
    """
    system = await db.scalar(
        select(SolarSystem).where(SolarSystem.owner_id == user_id)
    )
    if not system:
        return []

    routes = await db.scalars(
        select(SystemRoute.to_system_id).where(
            SystemRoute.from_system_id == system.id
        )
    )
    neighbor_ids = list(routes.all())

    newly_revealed = []
    for sid in neighbor_ids:
        is_new = await reveal_system(db, user_id, sid)
        if is_new:
            newly_revealed.append(sid)

    return newly_revealed


async def get_explored_system_ids(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Returnerer alle system_id-er spilleren har utforsket."""
    rows = await db.scalars(
        select(ExploredSystem.system_id).where(
            ExploredSystem.user_id == user_id
        )
    )
    return set(rows.all())
