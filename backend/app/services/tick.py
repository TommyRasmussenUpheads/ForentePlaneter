"""
Tick processor for Forente Planeter.

Runs every hour via Celery Beat.
Order of operations:
1.  Load active round
2.  Produce resources on all controlled planets
3.  Advance build queues
4.  Move all fleets (decrement ticks_remaining)
5.  Resolve arrivals:
      a. Transport missions → deliver cargo
      b. Attack missions → combat
      c. Return missions → ships back to origin
6.  Update blockade status
7.  NPC defense respawn (every 6 ticks)
8.  Calculate scores
9.  Check round end
10. Write tick log
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, text

from app.core.database import AsyncSessionLocal
from app.models.galaxy import GameRound, Planet, SolarSystem
from app.models.game import (
    Ship, FleetMission, FleetMissionShip,
    BuildQueue, CombatLog, TickLog, Notification,
)
from app.models.user import User
from app.services.combat import Fleet, resolve_combat

log = logging.getLogger(__name__)

NPC_RESPAWN_INTERVAL = 6   # ticks between NPC defense respawns
NPC_RESPAWN_AMOUNT = 2     # planetforsvar added per respawn


async def process_tick_async():
    async with AsyncSessionLocal() as db:
        try:
            await _process_tick(db)
        except Exception as e:
            log.error(f"Tick processing failed: {e}", exc_info=True)
            await db.rollback()
            raise


async def _process_tick(db: AsyncSession):
    # ── 1. Load active round ──────────────────────────────────
    round_ = await db.scalar(
        select(GameRound).where(text("status::text = 'active'"))
    )
    if not round_:
        log.info("No active round — skipping tick")
        return

    tick = round_.current_tick + 1
    log.info(f"Processing tick {tick}")

    tick_log = TickLog(
        tick_number=tick,
        round_id=round_.id,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db.add(tick_log)
    await db.flush()

    planets_processed = 0
    missions_resolved = 0
    combats_resolved = 0

    # ── 2. Produce resources ──────────────────────────────────
    # Home planets always produce
    # Neighbor/NPC planets produce only if owner has at least 1 ship there
    all_planets = await db.scalars(select(Planet))
    planet_list = list(all_planets.all())

    for planet in planet_list:
        if planet.planet_type == "home" and planet.owner_id:
            planet.metal  += planet.metal_production
            planet.energy += planet.energy_production
            planet.gas    += planet.gas_production
            planets_processed += 1
        elif planet.owner_id:
            # Check if owner has ships here
            ship_count = await db.scalar(
                select(Ship).where(
                    Ship.planet_id == planet.id,
                    Ship.owner_id == planet.owner_id,
                    Ship.quantity > 0,
                )
            )
            if ship_count:
                planet.metal  += planet.metal_production
                planet.energy += planet.energy_production
                planet.gas    += planet.gas_production
                planets_processed += 1

    # ── 3. Advance build queues ───────────────────────────────
    building = await db.scalars(
        select(BuildQueue).where(
            BuildQueue.status.in_(["building", "queued"])
        ).order_by(BuildQueue.planet_id, BuildQueue.queue_position)
    )
    build_list = list(building.all())

    # Group by planet — only first in queue advances
    planet_building: dict = {}
    for bq in build_list:
        pid = str(bq.planet_id)
        if pid not in planet_building:
            planet_building[pid] = []
        planet_building[pid].append(bq)

    for pid, items in planet_building.items():
        active = items[0]
        active.status = "building"
        active.ticks_remaining -= 1
        if active.ticks_remaining <= 0:
            active.status = "completed"
            # Add ship to planet
            existing = await db.scalar(
                select(Ship).where(
                    Ship.planet_id == active.planet_id,
                    Ship.owner_id == active.owner_id,
                    Ship.ship_type == active.ship_type,
                )
            )
            if existing:
                existing.quantity += active.quantity
            else:
                db.add(Ship(
                    owner_id=active.owner_id,
                    planet_id=active.planet_id,
                    ship_type=active.ship_type,
                    quantity=active.quantity,
                ))
            # Notify owner
            db.add(Notification(
                user_id=active.owner_id,
                type="build_complete",
                title=f"{active.quantity}× {active.ship_type} ferdigbygd",
                body=f"Skipene er klare på planeten din.",
                related_id=active.planet_id,
            ))

    # ── 4 & 5. Move fleets and resolve arrivals ───────────────
    in_flight = await db.scalars(
        select(FleetMission).where(
            FleetMission.status.in_(["in_flight", "returning"])
        )
    )
    missions = list(in_flight.all())

    for mission in missions:
        if mission.arrive_tick != tick:
            continue

        # Load ships on this mission
        mission_ships_rows = await db.scalars(
            select(FleetMissionShip).where(
                FleetMissionShip.mission_id == mission.id
            )
        )
        mission_ships = {r.ship_type: r.quantity for r in mission_ships_rows.all()}

        target_planet = await db.get(Planet, mission.target_planet_id)
        origin_planet = await db.get(Planet, mission.origin_planet_id)

        # ── Transport mission ─────────────────────────────────
        if mission.mission_type == "transport":
            if target_planet and target_planet.owner_id == mission.owner_id:
                target_planet.metal  += mission.cargo_metal
                target_planet.energy += mission.cargo_energy
                target_planet.gas    += mission.cargo_gas
                mission.status = "completed"
                # Return ships to origin
                for ship_type, qty in mission_ships.items():
                    await _return_ships(db, mission.owner_id, origin_planet.id, ship_type, qty, tick)
                db.add(Notification(
                    user_id=mission.owner_id,
                    type="transport_arrived",
                    title="Transport ankommet",
                    body=f"Ressurser levert: {mission.cargo_metal}M {mission.cargo_energy}E {mission.cargo_gas}G",
                    related_id=target_planet.id,
                ))
            else:
                # Planet no longer yours — cargo lost, ships return
                mission.status = "completed"
                for ship_type, qty in mission_ships.items():
                    await _return_ships(db, mission.owner_id, origin_planet.id, ship_type, qty, tick)
            missions_resolved += 1

        # ── Attack mission ────────────────────────────────────
        elif mission.mission_type == "attack":
            if not target_planet:
                mission.status = "completed"
                continue

            # Expedition ships flee before combat
            expedition_qty = mission_ships.pop("expedition", 0)
            diplomat_qty = mission_ships.pop("diplomat", 0)

            # Build defender fleet from ships on planet
            defender_ships_rows = await db.scalars(
                select(Ship).where(Ship.planet_id == target_planet.id)
            )
            defender_fleet_ships = {}
            for s in defender_ships_rows.all():
                if s.quantity > 0:
                    defender_fleet_ships[s.ship_type] = defender_fleet_ships.get(s.ship_type, 0) + s.quantity

            attacker = Fleet(owner_id=str(mission.owner_id), ships=mission_ships)
            defender = Fleet(owner_id=str(target_planet.owner_id) if target_planet.owner_id else "npc", ships=defender_fleet_ships)

            result = resolve_combat(attacker, defender, target_planet.planet_type == "home")

            # Log combat
            combat_entry = CombatLog(
                tick_number=tick,
                planet_id=target_planet.id,
                attacker_id=mission.owner_id,
                defender_id=target_planet.owner_id,
                attacker_won=result.attacker_won,
                attacker_atk_total=result.attacker_atk,
                defender_atk_total=result.defender_atk,
                planet_changed_owner=result.planet_changes_owner,
                losses_json={
                    "attacker": result.attacker_losses,
                    "defender": result.defender_losses,
                },
            )
            db.add(combat_entry)
            combats_resolved += 1

            # Update defender ships on planet
            await db.execute(delete(Ship).where(Ship.planet_id == target_planet.id))
            for ship_type, qty in result.defender_survivors.items():
                if qty > 0:
                    db.add(Ship(
                        owner_id=target_planet.owner_id,
                        planet_id=target_planet.id,
                        ship_type=ship_type,
                        quantity=qty,
                    ))

            if result.planet_changes_owner:
                old_owner = target_planet.owner_id
                target_planet.owner_id = mission.owner_id
                # Place surviving attacker ships on captured planet
                for ship_type, qty in result.attacker_survivors.items():
                    if qty > 0:
                        db.add(Ship(
                            owner_id=mission.owner_id,
                            planet_id=target_planet.id,
                            ship_type=ship_type,
                            quantity=qty,
                        ))
                # Notify attacker
                db.add(Notification(
                    user_id=mission.owner_id,
                    type="planet_captured",
                    title=f"Planet erobret: {target_planet.name}",
                    body=f"Du vant kampen og tok over planeten!",
                    related_id=target_planet.id,
                ))
                # Notify defender
                if old_owner:
                    db.add(Notification(
                        user_id=old_owner,
                        type="planet_lost",
                        title=f"Planet tapt: {target_planet.name}",
                        body=f"Planeten din ble erobret!",
                        related_id=target_planet.id,
                    ))
            else:
                # Attack failed — surviving attacker ships return home
                for ship_type, qty in result.attacker_survivors.items():
                    if qty > 0:
                        await _return_ships(db, mission.owner_id, origin_planet.id, ship_type, qty, tick)
                db.add(Notification(
                    user_id=mission.owner_id,
                    type="attack_failed",
                    title=f"Angrep mislyktes: {target_planet.name}",
                    body=f"Angrep: {result.attacker_atk} vs Forsvar: {result.defender_atk}",
                    related_id=target_planet.id,
                ))
                if target_planet.owner_id:
                    db.add(Notification(
                        user_id=target_planet.owner_id,
                        type="attack_repelled",
                        title=f"Angrep avverget: {target_planet.name}",
                        body=f"Angrep: {result.attacker_atk} vs ditt forsvar: {result.defender_atk}",
                        related_id=target_planet.id,
                    ))

            # Return expedition ships that fled
            if expedition_qty > 0:
                await _return_ships(db, mission.owner_id, origin_planet.id, "expedition", expedition_qty, tick)

            mission.status = "completed"
            missions_resolved += 1

        # ── Return mission ────────────────────────────────────
        elif mission.status == "returning":
            # Ships arrive back at origin
            for ship_type, qty in mission_ships.items():
                existing = await db.scalar(
                    select(Ship).where(
                        Ship.planet_id == origin_planet.id,
                        Ship.owner_id == mission.owner_id,
                        Ship.ship_type == ship_type,
                    )
                )
                if existing:
                    existing.quantity += qty
                else:
                    db.add(Ship(
                        owner_id=mission.owner_id,
                        planet_id=origin_planet.id,
                        ship_type=ship_type,
                        quantity=qty,
                    ))
            mission.status = "completed"
            missions_resolved += 1

    # ── 6. Update blockade status ─────────────────────────────
    for planet in planet_list:
        if not planet.owner_id:
            continue
        # Check if any enemy ships are present
        enemy_ships = await db.scalar(
            select(Ship).where(
                Ship.planet_id == planet.id,
                Ship.owner_id != planet.owner_id,
                Ship.quantity > 0,
            )
        )
        planet.blockade_status = "blockaded" if enemy_ships else "none"

    # ── 7. NPC defense respawn (every N ticks) ────────────────
    if tick % NPC_RESPAWN_INTERVAL == 0:
        npc_planets = await db.scalars(
            select(Planet).where(
                text("planet_type::text = 'npc'"),
                Planet.owner_id == None,
            )
        )
        for planet in npc_planets.all():
            existing = await db.scalar(
                select(Ship).where(
                    Ship.planet_id == planet.id,
                    Ship.ship_type == "planet_defense",
                )
            )
            if existing:
                existing.quantity = min(existing.quantity + NPC_RESPAWN_AMOUNT, 10)
            else:
                db.add(Ship(
                    owner_id=None,
                    planet_id=planet.id,
                    ship_type="planet_defense",
                    quantity=NPC_RESPAWN_AMOUNT,
                ))

    # ── 8. Calculate scores ───────────────────────────────────
    players = await db.scalars(select(User).where(User.role == "player"))
    for player in players.all():
        # Score = total resources across all owned planets × number of planets
        owned_planets = await db.scalars(
            select(Planet).where(Planet.owner_id == player.id)
        )
        owned = list(owned_planets.all())
        planet_count = len(owned)
        total_resources = sum(p.metal + p.energy + p.gas for p in owned)
        score = total_resources * planet_count
        # Update score on each planet for tracking
        for p in owned:
            p.score = score

    # ── 9. Check round end ────────────────────────────────────
    if round_.ends_at and datetime.now(timezone.utc) >= round_.ends_at:
        round_.status = "ended"
        log.info(f"Round {round_.id} ended at tick {tick}")

    # ── 10. Finalize tick ─────────────────────────────────────
    round_.current_tick = tick
    tick_log.ended_at = datetime.now(timezone.utc)
    tick_log.status = "completed"
    tick_log.planets_processed = planets_processed
    tick_log.missions_resolved = missions_resolved
    tick_log.combats_resolved = combats_resolved

    await db.commit()
    log.info(f"Tick {tick} complete — planets:{planets_processed} missions:{missions_resolved} combats:{combats_resolved}")


async def _return_ships(
    db: AsyncSession,
    owner_id,
    origin_planet_id,
    ship_type: str,
    qty: int,
    current_tick: int,
):
    """Create a return mission for ships heading home."""
    # Get origin planet to calculate return time
    origin = await db.get(Planet, origin_planet_id)
    if not origin:
        return

    return_mission = FleetMission(
        owner_id=owner_id,
        origin_planet_id=origin_planet_id,
        target_planet_id=origin_planet_id,
        mission_type="return",
        status="returning",
        depart_tick=current_tick,
        arrive_tick=current_tick + (origin.travel_ticks or 1),
    )
    db.add(return_mission)
    await db.flush()
    db.add(FleetMissionShip(
        mission_id=return_mission.id,
        ship_type=ship_type,
        quantity=qty,
    ))


async def respawn_npc_defenses_async():
    """Standalone NPC respawn — called by beat separately if needed."""
    async with AsyncSessionLocal() as db:
        npc_planets = await db.scalars(
            select(Planet).where(
                text("planet_type::text = 'npc'"),
                Planet.owner_id == None,
            )
        )
        for planet in npc_planets.all():
            existing = await db.scalar(
                select(Ship).where(
                    Ship.planet_id == planet.id,
                    Ship.ship_type == "planet_defense",
                )
            )
            if existing:
                existing.quantity = min(existing.quantity + NPC_RESPAWN_AMOUNT, 10)
            else:
                db.add(Ship(
                    owner_id=None,
                    planet_id=planet.id,
                    ship_type="planet_defense",
                    quantity=NPC_RESPAWN_AMOUNT,
                ))
        await db.commit()


async def check_round_end_async():
    async with AsyncSessionLocal() as db:
        round_ = await db.scalar(
            select(GameRound).where(text("status::text = 'active'"))
        )
        if round_ and round_.ends_at and datetime.now(timezone.utc) >= round_.ends_at:
            round_.status = "ended"
            await db.commit()
            log.info(f"Round {round_.id} marked as ended")
