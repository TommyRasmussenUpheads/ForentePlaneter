import asyncio
import logging
from app.worker import app

log = logging.getLogger(__name__)


def _make_engine():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import get_settings
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, SessionLocal


def _run(coro_fn):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro_fn())
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
            asyncio.set_event_loop(None)


@app.task(name="app.tasks.tick.process_tick")
def process_tick():
    async def _inner():
        from app.services.tick import _process_tick
        engine, SessionLocal = _make_engine()
        try:
            async with SessionLocal() as db:
                await _process_tick(db)
        finally:
            await engine.dispose()
    _run(_inner)


@app.task(name="app.tasks.tick.respawn_npc_defenses")
def respawn_npc_defenses():
    async def _inner():
        from sqlalchemy import select, text
        from app.models.galaxy import Planet
        from app.models.game import Ship
        engine, SessionLocal = _make_engine()
        try:
            async with SessionLocal() as db:
                npc_planets = await db.scalars(
                    select(Planet).where(text("planet_type::text = 'npc'"), Planet.owner_id == None)
                )
                for planet in npc_planets.all():
                    existing = await db.scalar(
                        select(Ship).where(Ship.planet_id == planet.id, Ship.ship_type == "planet_defense")
                    )
                    if existing:
                        existing.quantity = min(existing.quantity + 2, 10)
                    else:
                        db.add(Ship(owner_id=None, planet_id=planet.id, ship_type="planet_defense", quantity=2))
                await db.commit()
        finally:
            await engine.dispose()
    _run(_inner)


@app.task(name="app.tasks.tick.check_round_end")
def check_round_end():
    async def _inner():
        from sqlalchemy import select, text
        from app.models.galaxy import GameRound
        from datetime import datetime, timezone
        engine, SessionLocal = _make_engine()
        try:
            async with SessionLocal() as db:
                round_ = await db.scalar(select(GameRound).where(text("status::text = 'active'")))
                if round_ and round_.ends_at and datetime.now(timezone.utc) >= round_.ends_at:
                    round_.status = "ended"
                    await db.commit()
        finally:
            await engine.dispose()
    _run(_inner)
