"""
Combat resolution for Forente Planeter.

Kill order: transports first → military → expedition ships last
Attacker needs higher total ATK than defender total ATK to win.
Tie goes to defender.
Survivors: proportional to (1 - enemy_atk / own_hp)
"""
from dataclasses import dataclass, field
from typing import Optional
import math

SHIP_STATS = {
    "fighter":        {"atk": 10, "def": 3,  "dies_first": False, "dies_last": False, "immune": False},
    "cruiser":        {"atk": 6,  "def": 12, "dies_first": False, "dies_last": False, "immune": False},
    "bomber":         {"atk": 20, "def": 1,  "dies_first": False, "dies_last": False, "immune": False},
    "planet_defense": {"atk": 1,  "def": 20, "dies_first": False, "dies_last": False, "immune": False},
    "transport":      {"atk": 0,  "def": 30, "dies_first": True,  "dies_last": False, "immune": False},
    "expedition":     {"atk": 0,  "def": 0,  "dies_first": False, "dies_last": True,  "immune": False},
    "diplomat":       {"atk": 0,  "def": 0,  "dies_first": False, "dies_last": False, "immune": True},
}


@dataclass
class Fleet:
    owner_id: str
    ships: dict[str, int]  # ship_type -> quantity

    def total_atk(self) -> int:
        total = 0
        for ship_type, qty in self.ships.items():
            stats = SHIP_STATS.get(ship_type, {})
            if not stats.get("immune"):
                total += stats.get("atk", 0) * qty
        return total

    def total_hp(self) -> int:
        total = 0
        for ship_type, qty in self.ships.items():
            stats = SHIP_STATS.get(ship_type, {})
            if not stats.get("immune") and not stats.get("dies_last"):
                total += stats.get("def", 0) * qty
        return total

    def combat_ships(self) -> dict[str, int]:
        """Ships that actually participate in combat (not immune, not dies_last in first pass)."""
        return {
            k: v for k, v in self.ships.items()
            if not SHIP_STATS.get(k, {}).get("immune")
        }

    def immune_ships(self) -> dict[str, int]:
        return {k: v for k, v in self.ships.items() if SHIP_STATS.get(k, {}).get("immune")}

    def expedition_ships(self) -> dict[str, int]:
        return {k: v for k, v in self.ships.items() if SHIP_STATS.get(k, {}).get("dies_last")}

    def transport_ships(self) -> dict[str, int]:
        return {k: v for k, v in self.ships.items() if SHIP_STATS.get(k, {}).get("dies_first")}

    def military_ships(self) -> dict[str, int]:
        return {
            k: v for k, v in self.ships.items()
            if not SHIP_STATS.get(k, {}).get("immune")
            and not SHIP_STATS.get(k, {}).get("dies_first")
            and not SHIP_STATS.get(k, {}).get("dies_last")
        }


@dataclass
class CombatResult:
    attacker_won: bool
    attacker_atk: int
    defender_atk: int
    attacker_survivors: dict[str, int]
    defender_survivors: dict[str, int]
    attacker_losses: dict[str, int]
    defender_losses: dict[str, int]
    planet_changes_owner: bool


def resolve_combat(
    attacker: Fleet,
    defender: Fleet,
    is_home_planet: bool = False,
) -> CombatResult:
    """
    Resolve combat between attacker and defender fleets.

    Diplomat ships are immune and survive regardless.
    Expedition ships flee before combat (attacker) or die last (defender).
    Transport ships die first.
    """

    # Attacker expedition ships always flee home — not in combat
    atk_ships = {k: v for k, v in attacker.ships.items()
                 if not SHIP_STATS[k]["immune"] and not SHIP_STATS[k]["dies_last"]}
    def_ships = {k: v for k, v in defender.ships.items()
                 if not SHIP_STATS[k]["immune"]}

    # Calculate total ATK for each side
    atk_total = sum(SHIP_STATS[k]["atk"] * v for k, v in atk_ships.items())
    def_total = sum(SHIP_STATS[k]["atk"] * v for k, v in def_ships.items())

    # Attacker wins only if strictly greater ATK (tie = defender wins)
    attacker_won = atk_total > def_total

    # Survival calculation for winner
    def calc_survivors(winner_ships: dict, loser_atk: int) -> tuple[dict, dict]:
        survivors = {}
        losses = {}

        # Phase 1: absorb damage through transports first
        remaining_damage = loser_atk

        # Transports die first
        for ship_type in ["transport"]:
            qty = winner_ships.get(ship_type, 0)
            if qty == 0:
                continue
            hp_pool = SHIP_STATS[ship_type]["def"] * qty
            if remaining_damage >= hp_pool:
                remaining_damage -= hp_pool
                survivors[ship_type] = 0
                losses[ship_type] = qty
            else:
                # Proportional survival
                survival_rate = max(0, 1 - remaining_damage / hp_pool)
                survived = math.ceil(qty * survival_rate)
                survivors[ship_type] = survived
                losses[ship_type] = qty - survived
                remaining_damage = 0

        # Phase 2: military ships
        military = {k: v for k, v in winner_ships.items()
                    if not SHIP_STATS[k]["dies_first"]
                    and not SHIP_STATS[k]["dies_last"]}
        mil_hp = sum(SHIP_STATS[k]["def"] * v for k, v in military.items())

        if mil_hp > 0 and remaining_damage > 0:
            mil_survival_rate = max(0, 1 - remaining_damage / mil_hp)
            for ship_type, qty in military.items():
                survived = math.ceil(qty * mil_survival_rate)
                survivors[ship_type] = survived
                losses[ship_type] = qty - survived
            remaining_damage = max(0, remaining_damage - mil_hp)
        else:
            for ship_type, qty in military.items():
                survivors[ship_type] = qty
                losses[ship_type] = 0

        # Phase 3: expedition ships die last
        for ship_type in ["expedition"]:
            qty = winner_ships.get(ship_type, 0)
            if qty == 0:
                continue
            if remaining_damage > 0:
                survivors[ship_type] = 0
                losses[ship_type] = qty
            else:
                survivors[ship_type] = qty
                losses[ship_type] = 0

        return survivors, losses

    if attacker_won:
        win_survivors, win_losses = calc_survivors(atk_ships, def_total)
        atk_survivors = win_survivors
        atk_losses = win_losses
        def_survivors = {k: 0 for k in def_ships}
        def_losses = def_ships.copy()
    else:
        win_survivors, win_losses = calc_survivors(def_ships, atk_total)
        def_survivors = win_survivors
        def_losses = win_losses
        atk_survivors = {k: 0 for k in atk_ships}
        atk_losses = atk_ships.copy()

    # Immune ships (diplomats) always survive on both sides
    for ship_type, qty in attacker.immune_ships().items():
        atk_survivors[ship_type] = qty
        atk_losses[ship_type] = 0

    for ship_type, qty in defender.immune_ships().items():
        def_survivors[ship_type] = qty
        def_losses[ship_type] = 0

    # Attacker expedition ships fled — they return home separately
    for ship_type, qty in attacker.expedition_ships().items():
        atk_survivors[ship_type] = qty  # they fled, not lost

    # Home planet: attacker can never take over
    planet_changes_owner = attacker_won and not is_home_planet

    return CombatResult(
        attacker_won=attacker_won,
        attacker_atk=atk_total,
        defender_atk=def_total,
        attacker_survivors={k: v for k, v in atk_survivors.items() if v > 0},
        defender_survivors={k: v for k, v in def_survivors.items() if v > 0},
        attacker_losses={k: v for k, v in atk_losses.items() if v > 0},
        defender_losses={k: v for k, v in def_losses.items() if v > 0},
        planet_changes_owner=planet_changes_owner,
    )
