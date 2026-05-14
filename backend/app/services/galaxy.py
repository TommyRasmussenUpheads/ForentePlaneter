"""
Galaxy generation service for Forente Planeter.

Layout:
- Players on coarse hex grid (step=2), P1 at center
- 1-2 NPC systems between each adjacent player pair
- 1 frontier NPC outside each player with no player neighbor
- Elder Race at outer edge with 3 NPC buffer
- "Unknown Regions - Do not pass beyond" guards Elder Race
"""
import random
import uuid
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.galaxy import SolarSystem, SystemRoute, Planet
from app.models.user import User


# ── Hex grid utilities ────────────────────────────────────────

HEX_DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def hex_distance(a: tuple, b: tuple) -> int:
    aq, ar = a
    bq, br = b
    return (abs(aq - bq) + abs(aq + ar - bq - br) + abs(ar - br)) // 2


def hex_ring(radius: int) -> list[tuple]:
    if radius == 0:
        return [(0, 0)]
    results = []
    q, r = HEX_DIRS[4][0] * radius, HEX_DIRS[4][1] * radius
    for side in range(6):
        for _ in range(radius):
            results.append((q, r))
            dq, dr = HEX_DIRS[side]
            q += dq
            r += dr
    return results


def hex_neighbors_at_distance(q: int, r: int, dist: int) -> list[tuple]:
    return [(q + dq * dist, r + dr * dist) for dq, dr in HEX_DIRS]


# ── NPC name generator ────────────────────────────────────────

NPC_PREFIXES = [
    "Kepler", "Zephyr", "Vortan", "Nexus", "Axiom", "Helix",
    "Cygnus", "Vega", "Pulsar", "Kronos", "Apex", "Solari",
    "Void", "Ember", "Nova", "Rift", "Echo", "Phantom", "Sigma",
    "Aether", "Lyra", "Draco", "Orion", "Hydra", "Antares",
]

NPC_SUFFIXES = [
    "Prime", "Minor", "Deep", "Station", "Reach", "Expanse",
    "Drift", "Sector", "Point", "Crossing", "Passage", "Fringe",
    "Hollow", "Wake", "Verge", "Basin", "Remnant", "Threshold",
    "Void", "Watch", "Gate", "Span", "Field", "Harbor",
]


def generate_npc_name(used_names: set[str], rng: random.Random) -> str:
    attempts = 0
    while attempts < 100:
        name = f"{rng.choice(NPC_PREFIXES)} {rng.choice(NPC_SUFFIXES)}"
        if name not in used_names:
            used_names.add(name)
            return name
        attempts += 1
    # Fallback with UUID suffix
    name = f"{rng.choice(NPC_PREFIXES)}-{str(uuid.uuid4())[:4].upper()}"
    used_names.add(name)
    return name


# ── Resource distribution ─────────────────────────────────────

def distribute_home_resources(rng: random.Random) -> dict:
    """
    1000 total, min 200 each resource.
    Distribute 400 extra among three.
    """
    remaining = 400
    a = rng.randint(0, remaining)
    b = rng.randint(0, remaining - a)
    c = remaining - a - b
    vals = [200 + a, 200 + b, 200 + c]
    rng.shuffle(vals)
    return {"metal": vals[0], "energy": vals[1], "gas": vals[2]}


def distribute_neighbor_resources(rng: random.Random) -> list[dict]:
    """
    3 neighbor planets.
    Each resource type: 1500 total across all 3 planets.
    Split freely per resource type.
    """
    planets = [{}, {}, {}]
    for res in ("metal", "energy", "gas"):
        remaining = 1500
        splits = []
        for i in range(2):
            cut = rng.randint(100, max(100, remaining - 100 * (2 - i)))
            splits.append(cut)
            remaining -= cut
        splits.append(remaining)
        rng.shuffle(splits)
        for i, p in enumerate(planets):
            p[res] = splits[i]
    return planets


def distribute_npc_resources(rng: random.Random, multiplier: float = 0.5) -> dict:
    """NPC home planet — 50% of normal production."""
    base = distribute_home_resources(rng)
    return {k: int(v * multiplier) for k, v in base.items()}


def distribute_elder_race_resources(rng: random.Random) -> dict:
    """Elder Race — massive resources (50x normal)."""
    base = distribute_home_resources(rng)
    return {k: v * 50 for k, v in base.items()}


# ── Planet factory ────────────────────────────────────────────

def make_planets_for_system(
    system: SolarSystem,
    system_type: str,  # "player" | "npc" | "elder_race"
    owner_id: Optional[uuid.UUID],
    rng: random.Random,
) -> list[Planet]:
    planets = []

    if system_type == "player":
        # Home planet
        home_res = distribute_home_resources(rng)
        home = Planet(
            solar_system_id=system.id,
            name=f"{system.name} Prime",
            planet_type="home",
            owner_id=owner_id,
            orbit_slot=0,
            travel_ticks=0,
            metal=home_res["metal"] * 10,   # starting bank
            energy=home_res["energy"] * 10,
            gas=home_res["gas"] * 10,
            metal_production=home_res["metal"],
            energy_production=home_res["energy"],
            gas_production=home_res["gas"],
        )
        planets.append(home)

        # 3 neighbor planets
        neighbor_res = distribute_neighbor_resources(rng)
        for i, res in enumerate(neighbor_res):
            travel = rng.randint(2, 4)
            neighbor = Planet(
                solar_system_id=system.id,
                name=f"{system.name} {['Alpha', 'Beta', 'Gamma'][i]}",
                planet_type="neighbor",
                owner_id=owner_id,
                orbit_slot=i + 1,
                travel_ticks=travel,
                metal=0,
                energy=0,
                gas=0,
                metal_production=res["metal"],
                energy_production=res["energy"],
                gas_production=res["gas"],
            )
            planets.append(neighbor)

    elif system_type == "npc":
        npc_res = distribute_npc_resources(rng)
        home = Planet(
            solar_system_id=system.id,
            name=f"{system.name} Prime",
            planet_type="npc",
            owner_id=None,
            orbit_slot=0,
            travel_ticks=0,
            metal=npc_res["metal"] * 5,
            energy=npc_res["energy"] * 5,
            gas=npc_res["gas"] * 5,
            metal_production=npc_res["metal"],
            energy_production=npc_res["energy"],
            gas_production=npc_res["gas"],
        )
        planets.append(home)

        # NPC neighbor planets (3 like players but 50% production)
        neighbor_res = distribute_neighbor_resources(rng)
        for i, res in enumerate(neighbor_res):
            travel = rng.randint(2, 4)
            neighbor = Planet(
                solar_system_id=system.id,
                name=f"{system.name} {['Alpha', 'Beta', 'Gamma'][i]}",
                planet_type="npc",
                owner_id=None,
                orbit_slot=i + 1,
                travel_ticks=travel,
                metal=0,
                energy=0,
                gas=0,
                metal_production=int(res["metal"] * 0.5),
                energy_production=int(res["energy"] * 0.5),
                gas_production=int(res["gas"] * 0.5),
            )
            planets.append(neighbor)

    elif system_type == "elder_race":
        er_res = distribute_elder_race_resources(rng)
        home = Planet(
            solar_system_id=system.id,
            name=f"{system.name} Eternal",
            planet_type="elder_race",
            owner_id=owner_id,
            orbit_slot=0,
            travel_ticks=0,
            metal=er_res["metal"] * 100,
            energy=er_res["energy"] * 100,
            gas=er_res["gas"] * 100,
            metal_production=er_res["metal"],
            energy_production=er_res["energy"],
            gas_production=er_res["gas"],
        )
        planets.append(home)
        for i in range(3):
            travel = rng.randint(2, 4)
            res = distribute_elder_race_resources(rng)
            neighbor = Planet(
                solar_system_id=system.id,
                name=f"{system.name} {['I', 'II', 'III'][i]}",
                planet_type="elder_race",
                owner_id=owner_id,
                orbit_slot=i + 1,
                travel_ticks=travel,
                metal=res["metal"] * 50,
                energy=res["energy"] * 50,
                gas=res["gas"] * 50,
                metal_production=res["metal"],
                energy_production=res["energy"],
                gas_production=res["gas"],
            )
            planets.append(neighbor)

    return planets


# ── Main galaxy generator ─────────────────────────────────────

async def generate_galaxy(
    db: AsyncSession,
    players: list[User],
    elder_race_user: Optional[User],
    seed: Optional[int] = None,
) -> dict:
    """
    Generate the full galaxy for a new game round.
    Returns summary stats.
    """
    rng = random.Random(seed or random.randint(0, 2**32))
    used_names: set[str] = set()
    STEP = 2  # coarse hex grid step (leaves room for NPC between players)

    # ── Build player hex positions ────────────────────────────
    player_slots = [(0, 0)]  # P1 at center
    r1 = [(q * STEP, r * STEP) for q, r in hex_ring(1)]
    r2 = [(q * STEP, r * STEP) for q, r in hex_ring(2)]
    rng.shuffle(r1)
    rng.shuffle(r2)
    all_slots = r1 + r2

    for slot in all_slots:
        if len(player_slots) >= len(players):
            break
        player_slots.append(slot)

    player_set = set(player_slots)

    # ── Create all solar systems ──────────────────────────────
    all_systems: dict[tuple, SolarSystem] = {}  # (q,r) -> system
    all_planets: list[Planet] = []
    all_routes: list[SystemRoute] = []
    route_set: set[tuple] = set()

    def add_route(a: SolarSystem, b: SolarSystem):
        key = tuple(sorted([str(a.id), str(b.id)]))
        if key not in route_set:
            route_set.add(key)
            all_routes.append(SystemRoute(
                from_system_id=a.id,
                to_system_id=b.id,
                travel_ticks=6,
            ))
            all_routes.append(SystemRoute(
                from_system_id=b.id,
                to_system_id=a.id,
                travel_ticks=6,
            ))

    # Create player systems
    for i, (q, r) in enumerate(player_slots):
        player = players[i]
        system = SolarSystem(
            name=f"System-{player.username}",
            hex_q=q,
            hex_r=r,
            owner_id=player.id,
            is_npc=False,
        )
        db.add(system)
        await db.flush()
        planets = make_planets_for_system(system, "player", player.id, rng)
        for p in planets:
            db.add(p)
        all_systems[(q, r)] = system
        all_planets.extend(planets)

    # Create NPC systems between adjacent players
    edge_set: set[str] = set()
    for i in range(len(player_slots)):
        for j in range(i + 1, len(player_slots)):
            a = player_slots[i]
            b = player_slots[j]
            if hex_distance(a, b) != STEP:
                continue
            ek = f"{min(i,j)}-{max(i,j)}"
            if ek in edge_set:
                continue
            edge_set.add(ek)

            npc_count = rng.randint(1, 2)
            prev_system = all_systems[a]

            for k in range(1, npc_count + 1):
                t = k / (npc_count + 1)
                nq = a[0] + (b[0] - a[0]) * t
                nr = a[1] + (b[1] - a[1]) * t
                nq_int = round(nq)
                nr_int = round(nr)
                coord = (nq_int, nr_int)

                if coord not in all_systems:
                    name = generate_npc_name(used_names, rng)
                    npc_sys = SolarSystem(
                        name=name,
                        hex_q=nq_int,
                        hex_r=nr_int,
                        owner_id=None,
                        is_npc=True,
                    )
                    db.add(npc_sys)
                    await db.flush()
                    planets = make_planets_for_system(npc_sys, "npc", None, rng)
                    for p in planets:
                        db.add(p)
                    all_systems[coord] = npc_sys
                    all_planets.extend(planets)

                add_route(prev_system, all_systems[coord])
                prev_system = all_systems[coord]

            add_route(prev_system, all_systems[b])

    # Frontier NPC buffer: one NPC outside each player with no player neighbor
    for pq, pr in player_slots:
        for dq, dr in HEX_DIRS:
            nq, nr = pq + dq, pr + dr
            neighbor_player = (pq + dq * STEP, pr + dr * STEP)
            if neighbor_player in player_set:
                continue
            if (nq, nr) in all_systems:
                add_route(all_systems[(pq, pr)], all_systems[(nq, nr)])
                continue

            name = generate_npc_name(used_names, rng)
            frontier_sys = SolarSystem(
                name=name,
                hex_q=nq,
                hex_r=nr,
                owner_id=None,
                is_npc=True,
            )
            db.add(frontier_sys)
            await db.flush()
            planets = make_planets_for_system(frontier_sys, "npc", None, rng)
            for p in planets:
                db.add(p)
            all_systems[(nq, nr)] = frontier_sys
            all_planets.extend(planets)
            add_route(all_systems[(pq, pr)], frontier_sys)

    # Unknown Regions + Elder Race
    # Find outermost player system and place Unknown Regions + Elder Race beyond it
    if player_slots:
        max_dist = max(hex_distance((0, 0), pos) for pos in player_slots)
        # Place Unknown Regions just outside the frontier
        ur_q, ur_r = 0, -(max_dist + 3) * STEP
        ur_sys = SolarSystem(
            name="Unknown Regions - Do not pass beyond",
            hex_q=ur_q,
            hex_r=ur_r,
            owner_id=None,
            is_npc=True,
            is_unknown_region=True,
        )
        db.add(ur_sys)
        await db.flush()
        npc_ur = make_planets_for_system(ur_sys, "npc", None, rng)
        for p in npc_ur:
            db.add(p)
        all_systems[(ur_q, ur_r)] = ur_sys
        all_planets.extend(npc_ur)

        # Elder Race beyond Unknown Regions
        if elder_race_user:
            er_q, er_r = 0, -(max_dist + 5) * STEP
            er_sys = SolarSystem(
                name="The Ancient Realm",
                hex_q=er_q,
                hex_r=er_r,
                owner_id=elder_race_user.id,
                is_elder_race=True,
            )
            db.add(er_sys)
            await db.flush()
            er_planets = make_planets_for_system(er_sys, "elder_race", elder_race_user.id, rng)
            for p in er_planets:
                db.add(p)
            all_systems[(er_q, er_r)] = er_sys
            all_planets.extend(er_planets)

            # 3 NPC buffers between Unknown Regions and Elder Race
            prev = ur_sys
            for i in range(1, 4):
                buf_q, buf_r = 0, ur_r - i * STEP
                if (buf_q, buf_r) not in all_systems:
                    name = generate_npc_name(used_names, rng)
                    buf_sys = SolarSystem(
                        name=name,
                        hex_q=buf_q,
                        hex_r=buf_r,
                        owner_id=None,
                        is_npc=True,
                    )
                    db.add(buf_sys)
                    await db.flush()
                    buf_planets = make_planets_for_system(buf_sys, "npc", None, rng)
                    for p in buf_planets:
                        db.add(p)
                    all_systems[(buf_q, buf_r)] = buf_sys
                    all_planets.extend(buf_planets)
                    add_route(prev, buf_sys)
                    prev = buf_sys

            add_route(prev, er_sys)

    # Save all routes
    for route in all_routes:
        db.add(route)

    await db.commit()

    player_systems = [s for s in all_systems.values() if not s.is_npc and not s.is_elder_race]
    npc_systems = [s for s in all_systems.values() if s.is_npc]
    elder_systems = [s for s in all_systems.values() if s.is_elder_race]

    return {
        "total_systems": len(all_systems),
        "player_systems": len(player_systems),
        "npc_systems": len(npc_systems),
        "elder_race_systems": len(elder_systems),
        "total_planets": len(all_planets),
        "total_routes": len(all_routes),
        "seed": rng.randint(0, 2**32),
    }
