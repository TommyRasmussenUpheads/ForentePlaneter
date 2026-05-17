from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.galaxy import Planet, SolarSystem, GameRound
from app.models.game import Ship, FleetMission, FleetMissionShip, BuildQueue, Notification
from app.models.user import User
from app.services.combat import SHIP_STATS

router = APIRouter(prefix="/fleet", tags=["fleet"])

SHIP_BUILD_COSTS = {
    "fighter":        {"ticks": 2, "metal": 50,  "energy": 20,  "gas": 10},
    "cruiser":        {"ticks": 4, "metal": 120, "energy": 30,  "gas": 20},
    "bomber":         {"ticks": 3, "metal": 40,  "energy": 150, "gas": 20},
    "planet_defense": {"ticks": 5, "metal": 60,  "energy": 20,  "gas": 120},
    "transport":      {"ticks": 4, "metal": 200, "energy": 40,  "gas": 30},
    "expedition":     {"ticks": 6, "metal": 80,  "energy": 100, "gas": 60},
    "diplomat":       {"ticks": 8, "metal": 100, "energy": 150, "gas": 80},
}

EXPEDITION_TYPES = {"expedition"}
TRANSPORT_TYPES  = {"transport"}
MILITARY_TYPES   = {"fighter", "cruiser", "bomber", "planet_defense", "diplomat"}


def classify_fleet(ships: dict[str, int]) -> str:
    active = {k for k, v in ships.items() if v > 0}
    if active & MILITARY_TYPES:
        return "military"
    if active & TRANSPORT_TYPES:
        return "transport"
    return "expedition"


# ── My ships overview ─────────────────────────────────────────

@router.get("/my-ships")
async def get_my_ships(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ships = await db.scalars(
        select(Ship).where(Ship.owner_id == current_user.id, Ship.quantity > 0)
    )
    result = {}
    for s in ships.all():
        planet = await db.get(Planet, s.planet_id) if s.planet_id else None
        system = await db.get(SolarSystem, planet.solar_system_id) if planet else None
        pid = str(s.planet_id) if s.planet_id else "transit"
        if pid not in result:
            result[pid] = {
                "planet_name": planet.name if planet else "In transit",
                "planet_id": str(s.planet_id) if s.planet_id else None,
                "system_name": system.name if system else None,
                "system_id": str(system.id) if system else None,
                "ships": {}
            }
        result[pid]["ships"][s.ship_type] = result[pid]["ships"].get(s.ship_type, 0) + s.quantity
    return {"locations": result}


# ── Active missions ───────────────────────────────────────────

@router.get("/my-missions")
async def get_my_missions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    missions = await db.scalars(
        select(FleetMission).where(
            FleetMission.owner_id == current_user.id,
            FleetMission.status.in_(["in_flight", "returning"]),
        ).order_by(FleetMission.arrive_tick)
    )
    result = []
    for m in missions.all():
        ships_rows = await db.scalars(
            select(FleetMissionShip).where(FleetMissionShip.mission_id == m.id)
        )
        ships = {r.ship_type: r.quantity for r in ships_rows.all()}
        origin = await db.get(Planet, m.origin_planet_id)
        target = await db.get(Planet, m.target_planet_id)
        round_ = await db.scalar(select(GameRound).order_by(GameRound.id.desc()))
        current_tick = round_.current_tick if round_ else 0
        result.append({
            "id": str(m.id),
            "type": m.mission_type,
            "status": m.status,
            "origin": origin.name if origin else "?",
            "target": target.name if target else "?",
            "ships": ships,
            "depart_tick": m.depart_tick,
            "arrive_tick": m.arrive_tick,
            "ticks_remaining": max(0, m.arrive_tick - current_tick),
            "cargo": {
                "metal": m.cargo_metal,
                "energy": m.cargo_energy,
                "gas": m.cargo_gas,
            } if m.mission_type == "transport" else None,
        })
    return result


# ── Send fleet ────────────────────────────────────────────────

class SendFleetRequest(BaseModel):
    origin_planet_id: str
    target_planet_id: str
    mission_type: str   # attack | defend | transport | expedition
    ships: dict[str, int]
    cargo_metal: int = 0
    cargo_energy: int = 0
    cargo_gas: int = 0


@router.post("/send")
async def send_fleet(
    body: SendFleetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.mission_type not in ("attack", "defend", "transport", "expedition"):
        raise HTTPException(400, "Ugyldig oppdragstype")

    origin = await db.get(Planet, uuid.UUID(body.origin_planet_id))
    target = await db.get(Planet, uuid.UUID(body.target_planet_id))

    if not origin or not target:
        raise HTTPException(404, "Planet ikke funnet")
    if origin.owner_id != current_user.id:
        raise HTTPException(403, "Du eier ikke opprinnelsesplaneten")

    active_ships = {k: v for k, v in body.ships.items() if v > 0}
    if not active_ships:
        raise HTTPException(400, "Velg minst ett skip")

    # Valider tilgjengelighet
    for ship_type, qty in active_ships.items():
        if ship_type not in SHIP_STATS:
            raise HTTPException(400, f"Ukjent skiptype: {ship_type}")
        available = await db.scalar(
            select(Ship).where(
                Ship.planet_id == origin.id,
                Ship.owner_id == current_user.id,
                Ship.ship_type == ship_type,
            )
        )
        if not available or available.quantity < qty:
            raise HTTPException(400,
                f"Ikke nok {ship_type} (har {available.quantity if available else 0}, trenger {qty})"
            )

    # Valider last for transport
    if body.mission_type == "transport":
        total_cargo = body.cargo_metal + body.cargo_energy + body.cargo_gas
        if total_cargo == 0:
            raise HTTPException(400, "Velg last å transportere")
        transport_qty = active_ships.get("transport", 0)
        if total_cargo > transport_qty * 10000:
            raise HTTPException(400, f"For mye last. Maks {transport_qty * 10000}")
        if body.cargo_metal > origin.metal or body.cargo_energy > origin.energy or body.cargo_gas > origin.gas:
            raise HTTPException(400, "Ikke nok ressurser på planeten")

    # Beregn reisetid
    round_ = await db.scalar(select(GameRound).order_by(GameRound.id.desc()))
    current_tick = round_.current_tick if round_ else 0
    inter_system = origin.solar_system_id != target.solar_system_id

    if not inter_system:
        travel_ticks = target.travel_ticks if target.travel_ticks > 0 else 1
    else:
        only_expedition = all(t in EXPEDITION_TYPES for t in active_ships)
        only_diplomat   = list(active_ships.keys()) == ["diplomat"]
        if only_diplomat:
            travel_ticks = 1
        elif only_expedition:
            travel_ticks = 3
        else:
            travel_ticks = 6

    # Trekk skip fra origin
    for ship_type, qty in active_ships.items():
        ship = await db.scalar(
            select(Ship).where(
                Ship.planet_id == origin.id,
                Ship.owner_id == current_user.id,
                Ship.ship_type == ship_type,
            )
        )
        ship.quantity -= qty
        if ship.quantity == 0:
            await db.delete(ship)

    # Trekk last
    if body.mission_type == "transport":
        origin.metal  -= body.cargo_metal
        origin.energy -= body.cargo_energy
        origin.gas    -= body.cargo_gas

    mission = FleetMission(
        owner_id=current_user.id,
        origin_planet_id=origin.id,
        target_planet_id=target.id,
        mission_type=body.mission_type,
        status="in_flight",
        depart_tick=current_tick,
        arrive_tick=current_tick + travel_ticks,
        cargo_metal=body.cargo_metal,
        cargo_energy=body.cargo_energy,
        cargo_gas=body.cargo_gas,
    )
    db.add(mission)
    await db.flush()

    for ship_type, qty in active_ships.items():
        db.add(FleetMissionShip(mission_id=mission.id, ship_type=ship_type, quantity=qty))

    # ── Tidlig varsling ved angrep ────────────────────────────
    if body.mission_type == "attack" and target.owner_id and target.owner_id != current_user.id:
        planet_defense = await db.scalar(
            select(Ship).where(
                Ship.planet_id == target.id,
                Ship.ship_type == "planet_defense",
                Ship.quantity > 0,
            )
        )
        if planet_defense:
            db.add(Notification(
                user_id=target.owner_id,
                type="attack_incoming",
                title=f"⚠ Fiendtlig flåte oppdaget!",
                body=f"Planetforsvaret på {target.name} har oppdaget en innkommende fiendtlig flåte. Ankomst om {travel_ticks} tick(s).",
                related_id=target.id,
            ))

    await db.commit()

    return {
        "message": f"Flåte sendt — ankommer tick {mission.arrive_tick}",
        "mission_id": str(mission.id),
        "mission_type": body.mission_type,
        "arrive_tick": mission.arrive_tick,
        "ticks_travel": travel_ticks,
        "inter_system": inter_system,
    }


# ── Build queue ───────────────────────────────────────────────

class BuildRequest(BaseModel):
    planet_id: str
    ship_type: str
    quantity: int = 1


@router.post("/build")
async def build_ships(
    body: BuildRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.ship_type not in SHIP_BUILD_COSTS:
        raise HTTPException(400, f"Ukjent skiptype: {body.ship_type}")
    if body.quantity < 1:
        raise HTTPException(400, "Må bygge minst 1 skip")

    planet = await db.get(Planet, uuid.UUID(body.planet_id))
    if not planet or planet.owner_id != current_user.id:
        raise HTTPException(403, "Du eier ikke denne planeten")

    if planet.blockade_status == "blockaded" and body.ship_type != "diplomat":
        raise HTTPException(403, "Planeten er under blokade — kan kun bygge diplomatskip")

    costs = SHIP_BUILD_COSTS[body.ship_type]
    total_metal  = costs["metal"]  * body.quantity
    total_energy = costs["energy"] * body.quantity
    total_gas    = costs["gas"]    * body.quantity

    if planet.metal < total_metal or planet.energy < total_energy or planet.gas < total_gas:
        raise HTTPException(400,
            f"Ikke nok ressurser. Trenger {total_metal}M {total_energy}E {total_gas}G, "
            f"har {planet.metal}M {planet.energy}E {planet.gas}G"
        )

    existing_queue = await db.scalars(
        select(BuildQueue).where(
            BuildQueue.planet_id == planet.id,
            BuildQueue.status.in_(["queued", "building"]),
        ).order_by(BuildQueue.queue_position)
    )
    queue_items = list(existing_queue.all())
    next_position = len(queue_items) + 1

    planet.metal  -= total_metal
    planet.energy -= total_energy
    planet.gas    -= total_gas

    for i in range(body.quantity):
        is_first = (not queue_items) and (i == 0)
        db.add(BuildQueue(
            planet_id=planet.id,
            owner_id=current_user.id,
            ship_type=body.ship_type,
            quantity=1,
            ticks_remaining=costs["ticks"],
            ticks_total=costs["ticks"],
            status="building" if is_first else "queued",
            queue_position=next_position + i,
            metal_cost=costs["metal"],
            energy_cost=costs["energy"],
            gas_cost=costs["gas"],
        ))

    await db.commit()

    return {
        "message": f"Bygger {body.quantity}× {body.ship_type} — første klar om {costs['ticks']} tick(s)",
        "queue_position_start": next_position,
        "ticks_per_ship": costs["ticks"],
        "total_cost": {"metal": total_metal, "energy": total_energy, "gas": total_gas},
    }


@router.get("/build-queue/{planet_id}")
async def get_build_queue(
    planet_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    planet = await db.get(Planet, uuid.UUID(planet_id))
    if not planet or planet.owner_id != current_user.id:
        raise HTTPException(403, "Du eier ikke denne planeten")

    queue = await db.scalars(
        select(BuildQueue).where(
            BuildQueue.planet_id == planet.id,
            BuildQueue.status.in_(["queued", "building"]),
        ).order_by(BuildQueue.queue_position)
    )
    return [
        {
            "id": str(bq.id),
            "ship_type": bq.ship_type,
            "quantity": bq.quantity,
            "ticks_remaining": bq.ticks_remaining,
            "status": bq.status,
            "queue_position": bq.queue_position,
        }
        for bq in queue.all()
    ]


@router.get("/ship-stats")
async def get_ship_stats():
    result = {}
    for ship_type, stats in SHIP_STATS.items():
        costs = SHIP_BUILD_COSTS.get(ship_type, {})
        result[ship_type] = {
            **stats,
            "build_ticks": costs.get("ticks", 0),
            "cost_metal":  costs.get("metal", 0),
            "cost_energy": costs.get("energy", 0),
            "cost_gas":    costs.get("gas", 0),
        }
    return result
