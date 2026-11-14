"""
Authoritative Airdrop Plane & Care Package System for Free Fire 1.39.
Simulates C-130 cargo plane flight paths across Bermuda, parachute drops,
smoke beacon flares, and tier-3 military loot crates.
"""

import math
import random
import time
from typing import Dict, Any, List, Optional, Tuple

from .world_constants import (
    MAP_MIN_X, MAP_MAX_X, MAP_MIN_Z, MAP_MAX_Z,
    WEAPON_REGISTRY, GEAR_REGISTRY, CONSUMABLES_REGISTRY
)

class AirdropState:
    IN_FLIGHT = "IN_FLIGHT"       # Cargo plane carrying crate
    DROPPING = "DROPPING"         # Parachute falling towards ground
    LANDED = "LANDED"             # On ground with active smoke beacon
    LOOTED = "LOOTED"             # Empty crate

class AirdropPlane:
    """Simulates an authoritative C-130 airdrop flight across the map."""

    def __init__(self, plane_id: int, target_x: float, target_z: float, flight_altitude: float = 220.0):
        self.plane_id: int = plane_id
        self.target_drop_x: float = target_x
        self.target_drop_z: float = target_z
        self.altitude: float = flight_altitude
        self.speed: float = 65.0  # meters per second
        self.dropped: bool = False
        
        # Calculate random entry and exit vectors passing through target_drop
        angle = random.uniform(0.0, 2.0 * math.pi)
        flight_distance = 1800.0  # Fly across the island
        
        self.start_x: float = target_x - math.cos(angle) * (flight_distance / 2.0)
        self.start_z: float = target_z - math.sin(angle) * (flight_distance / 2.0)
        self.end_x: float = target_x + math.cos(angle) * (flight_distance / 2.0)
        self.end_z: float = target_z + math.sin(angle) * (flight_distance / 2.0)
        
        self.curr_x: float = self.start_x
        self.curr_z: float = self.start_z
        self.curr_y: float = self.altitude
        
        self.dx: float = math.cos(angle) * self.speed
        self.dz: float = math.sin(angle) * self.speed
        
        self.total_dist: float = math.hypot(self.end_x - self.start_x, self.end_z - self.start_z)
        self.dist_traveled: float = 0.0
        self.is_finished: bool = False

    def update(self, delta_time: float) -> Optional[Dict[str, Any]]:
        """Advance airplane flight. Returns drop trigger when passing target location."""
        if self.is_finished:
            return None

        step = self.speed * delta_time
        self.dist_traveled += step
        self.curr_x += self.dx * delta_time
        self.curr_z += self.dz * delta_time

        # Check if crate should be deployed
        drop_event = None
        if not self.dropped:
            dist_to_target = math.hypot(self.curr_x - self.target_drop_x, self.curr_z - self.target_drop_z)
            if dist_to_target <= step * 1.5:
                self.dropped = True
                drop_event = {
                    "plane_id": self.plane_id,
                    "drop_x": self.curr_x,
                    "drop_y": self.curr_y,
                    "drop_z": self.curr_z
                }

        if self.dist_traveled >= self.total_dist:
            self.is_finished = True

        return drop_event


class CarePackage:
    """An individual airdrop crate descending with parachute and landing on terrain."""

    def __init__(self, crate_id: int, x: float, y: float, z: float, ground_y: float = 20.0):
        self.crate_id: int = crate_id
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.ground_y: float = ground_y
        self.fall_speed: float = 9.0  # parachute descent rate
        self.state: str = AirdropState.DROPPING
        self.smoke_timer: float = 180.0  # Smoke flare lasts 3 minutes after landing
        
        # Populate authentic high-tier military loot
        self.loot: Dict[str, Any] = self._generate_airdrop_loot()

    def _generate_airdrop_loot(self) -> Dict[str, Any]:
        """Generate authentic Free Fire airdrop loot (GROZA or AWM, L3 vest, L3 helmet, medkits, gloo walls)."""
        # Choose primary weapon
        prim_choice = random.choice(["GROZA", "AWM"])
        prim_item = WEAPON_REGISTRY[prim_choice]
        ammo_item = CONSUMABLES_REGISTRY["Ammo_AR"] if prim_choice == "GROZA" else CONSUMABLES_REGISTRY["Ammo_Sniper"]
        
        return {
            "weapon": {
                "name": prim_item["name"],
                "item_id": prim_item["item_id"],
                "ammo_type": prim_item["ammo_type"],
                "ammo_in_clip": prim_item["clip_size"],
                "reserve_ammo": prim_item["reserve_ammo"]
            },
            "ammo": {
                "name": ammo_item["name"],
                "item_id": ammo_item["item_id"],
                "count": 60 if prim_choice == "GROZA" else 20
            },
            "vest": GEAR_REGISTRY["Vest_L3"].copy(),
            "helmet": GEAR_REGISTRY["Helmet_L3"].copy(),
            "medkits": {
                "item_id": CONSUMABLES_REGISTRY["Medkit"]["item_id"],
                "name": "Medkit",
                "count": 3
            },
            "gloo_walls": {
                "item_id": CONSUMABLES_REGISTRY["GlooWall"]["item_id"],
                "name": "Gloo Wall",
                "count": 3
            }
        }

    def update(self, delta_time: float) -> None:
        """Advance parachute drop physics and smoke flare timer."""
        if self.state == AirdropState.DROPPING:
            self.y -= self.fall_speed * delta_time
            if self.y <= self.ground_y:
                self.y = self.ground_y
                self.state = AirdropState.LANDED

        elif self.state == AirdropState.LANDED:
            if self.smoke_timer > 0.0:
                self.smoke_timer -= delta_time

    def is_looted(self) -> bool:
        return self.state == AirdropState.LOOTED or not bool(self.loot)

    def loot_all(self) -> Dict[str, Any]:
        """Claim all remaining loot items from care package."""
        claimed = self.loot
        self.loot = {}
        self.state = AirdropState.LOOTED
        return claimed


class AirdropManager:
    """Manages scheduled and triggered airdrops across the match."""

    def __init__(self):
        self.next_crate_id: int = 1001
        self.next_plane_id: int = 501
        self.planes: List[AirdropPlane] = []
        self.crates: List[CarePackage] = []
        
        # Airdrop trigger schedule (at match times 90s, 240s, 380s)
        self.drop_schedule: List[float] = [90.0, 240.0, 380.0]
        self.schedule_idx: int = 0
        self.match_time: float = 0.0

    def trigger_airdrop(self, target_x: Optional[float] = None, target_z: Optional[float] = None) -> CarePackage:
        """Immediately dispatch an airdrop cargo plane to target coordinates."""
        if target_x is None or target_z is None:
            # Drop inside current playable area
            target_x = random.uniform(-300.0, 300.0)
            target_z = random.uniform(-300.0, 300.0)

        plane = AirdropPlane(self.next_plane_id, target_x, target_z)
        self.next_plane_id += 1
        self.planes.append(plane)
        
        # Also create initial crate ready to deploy
        crate = CarePackage(self.next_crate_id, target_x, plane.altitude, target_z)
        self.next_crate_id += 1
        return crate

    def update(self, delta_time: float, current_safe_x: float = 0.0, current_safe_z: float = 0.0, current_radius: float = 400.0) -> List[Dict[str, Any]]:
        """Advance all active airplanes and falling crates."""
        self.match_time += delta_time
        events = []

        # Check schedule
        if self.schedule_idx < len(self.drop_schedule):
            if self.match_time >= self.drop_schedule[self.schedule_idx]:
                self.schedule_idx += 1
                # Drop within current safe zone radius
                angle = random.uniform(0.0, 2.0 * math.pi)
                dist = random.uniform(20.0, max(50.0, current_radius * 0.7))
                tx = current_safe_x + dist * math.cos(angle)
                tz = current_safe_z + dist * math.sin(angle)
                
                plane = AirdropPlane(self.next_plane_id, tx, tz)
                self.next_plane_id += 1
                self.planes.append(plane)
                events.append({
                    "event": "AIRDROP_PLANE_SPAWNED",
                    "plane_id": plane.plane_id,
                    "target_x": tx,
                    "target_z": tz
                })

        # Update active planes
        for plane in list(self.planes):
            drop_event = plane.update(delta_time)
            if drop_event:
                crate = CarePackage(
                    self.next_crate_id,
                    drop_event["drop_x"],
                    drop_event["drop_y"],
                    drop_event["drop_z"]
                )
                self.next_crate_id += 1
                self.crates.append(crate)
                events.append({
                    "event": "CARE_PACKAGE_DROPPED",
                    "crate_id": crate.crate_id,
                    "x": crate.x,
                    "y": crate.y,
                    "z": crate.z
                })

            if plane.is_finished:
                self.planes.remove(plane)

        # Update crates
        for crate in self.crates:
            crate.update(delta_time)

        return events

    def get_crates_sync(self) -> List[Dict[str, Any]]:
        """Serialize care package state for network broadcast."""
        return [
            {
                "crate_id": c.crate_id,
                "x": c.x,
                "y": c.y,
                "z": c.z,
                "state": c.state,
                "has_smoke": c.state == AirdropState.LANDED and c.smoke_timer > 0.0,
                "is_empty": c.is_looted()
            }
            for c in self.crates
        ]
