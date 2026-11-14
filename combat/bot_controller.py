"""
Free Fire 1.39 AI Bots & Opponent Controller.
Authoritative simulated bot opponents, authentic Free Fire profiles,
lifecycle state machine (Spawn Island -> Airplane -> Parachute -> Ground Roam -> Combat -> Death),
hot-drop town pathfinding, and UDP state synchronization.

Verified against Free Fire 1.39 metadata, client IL2CPP conventions, and Bermuda world engine.
"""

from __future__ import annotations

import math
import random
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple

import sys
import os
_SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

from proto.character_models import AVATAR_CATALOG
from proto.inventory_models import (
    CLOTHES_IDS,
    BANNER_IDS,
    HEADPIC_IDS,
    LOOTBOX_IDS,
    PARACHUTE_IDS,
    SKYBOARD_IDS,
    WEAPON_SKIN_IDS,
)
from combat.world_constants import (
    BERMUDA_LANDMARKS,
    WEAPON_REGISTRY,
    GEAR_REGISTRY,
    CONSUMABLES_REGISTRY,
    BodyPart,
)


# ---------------------------------------------------------------------------
# Free Fire 1.39 Combat Protocol Constants & Enums
# ---------------------------------------------------------------------------

class PhysxState(IntEnum):
    """TypeDef [4466]: message.‚DL|vmS (EPHYSXSTATE)"""
    WALKING = 0
    FALLING = 1
    PARACHUTING = 2
    ONBOARD = 3
    SKYDIVING = 4
    HITFLY = 5
    SWIMMING = 6
    ONSTROP = 7
    FOOTBALL = 8
    JETFLY = 9
    GLIDING = 10
    ONGRAPPLINGHOOK = 11


class PhysxPose(IntEnum):
    """TypeDef [4467]: message.rqWMv`d (EPHYSXPOSE)"""
    STANDING = 0
    CROUCHING = 1
    DASHING = 2
    CREEPING = 3
    SWIMDASH = 4
    SKYDIVING = 5
    CROSSOVER = 6
    CLIMBOVER = 7
    KNOCKDOWN = 8
    SWIMSURFING = 9
    HIGHFALLING = 10
    LOWFALLING = 11
    JETFLYRUSH = 12
    SECONDFALLING = 13
    SITTING = 14
    CATAPULTFALLING = 15
    CATAPULTSTANDING = 16
    GLIDING = 17
    GLIDEFALLING = 18


class BotLifecycleState(IntEnum):
    """Bot lifecycle phases across match progression"""
    WAITING_ISLAND = 0   # On Spawn Island waiting 60s countdown
    AIRPLANE = 1         # Aboard cargo plane along Bermuda flight path
    SKYDIVING = 2        # High speed free fall after ejecting
    PARACHUTING = 3      # Parachute deployed, gliding to hot-drop destination
    GROUND_ROAMING = 4   # On ground navigating waypoints & searching loot
    LOOTING = 5          # Moving to and picking up weapons/items
    COMBAT_ENGAGING = 6  # Aiming & firing at spotted enemy
    TAKING_COVER = 7     # Retreating / hiding / using medkit
    DEAD = 8             # Eliminated, lootbox dropped


def parse_body_part_code(part: Any) -> int:
    """Safely convert BodyPart enum/string/int to Free Fire integer code."""
    if isinstance(part, int):
        return part
    p_str = str(part).upper()
    if "HEAD" in p_str:
        return 1
    elif "BODY" in p_str or "CHEST" in p_str or "STOMACH" in p_str:
        return 2
    elif "LIMB" in p_str:
        return 3
    return 2


# ---------------------------------------------------------------------------
# Vector3 Math Helper
# ---------------------------------------------------------------------------

@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance_to(self, other: "Vector3") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def horizontal_distance_to(self, other: "Vector3") -> float:
        dx = self.x - other.x
        dz = self.z - other.z
        return math.sqrt(dx * dx + dz * dz)

    def direction_to(self, other: "Vector3") -> "Vector3":
        dist = self.distance_to(other)
        if dist < 1e-5:
            return Vector3(0.0, 0.0, 0.0)
        return Vector3(
            (other.x - self.x) / dist,
            (other.y - self.y) / dist,
            (other.z - self.z) / dist,
        )

    def to_dict(self) -> Dict[str, float]:
        return {"x": round(self.x, 2), "y": round(self.y, 2), "z": round(self.z, 2)}

    def copy(self) -> "Vector3":
        return Vector3(self.x, self.y, self.z)


# ---------------------------------------------------------------------------
# Bermuda Coordinates (Matching world_constants.py & match_director.py)
# ---------------------------------------------------------------------------

# Spawn Island waiting area: authentic Bermuda waiting island
SPAWN_ISLAND_CENTER = Vector3(-500.0, 10.0, 800.0)
SPAWN_ISLAND_RADIUS = 50.0

# Strategic hot-drop towns and key locations on Bermuda
BERMUDA_HOT_DROPS: Dict[str, Dict[str, Any]] = {
    "Peak": {
        "center": Vector3(BERMUDA_LANDMARKS["Peak"]["x"], BERMUDA_LANDMARKS["Peak"]["y"], BERMUDA_LANDMARKS["Peak"]["z"]),
        "radius": BERMUDA_LANDMARKS["Peak"]["radius"],
        "tier": "very_high",
        "description": "High plateau central compound with prime high-tier loot",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Peak"]["x"] - 25.0, BERMUDA_LANDMARKS["Peak"]["y"], BERMUDA_LANDMARKS["Peak"]["z"] - 20.0),
            Vector3(BERMUDA_LANDMARKS["Peak"]["x"] + 25.0, BERMUDA_LANDMARKS["Peak"]["y"], BERMUDA_LANDMARKS["Peak"]["z"] + 20.0),
            Vector3(BERMUDA_LANDMARKS["Peak"]["x"] - 15.0, BERMUDA_LANDMARKS["Peak"]["y"], BERMUDA_LANDMARKS["Peak"]["z"] + 30.0),
            Vector3(BERMUDA_LANDMARKS["Peak"]["x"] + 30.0, BERMUDA_LANDMARKS["Peak"]["y"], BERMUDA_LANDMARKS["Peak"]["z"] - 15.0),
        ],
    },
    "Clock Tower": {
        "center": Vector3(BERMUDA_LANDMARKS["Clock_Tower"]["x"], BERMUDA_LANDMARKS["Clock_Tower"]["y"], BERMUDA_LANDMARKS["Clock_Tower"]["z"]),
        "radius": BERMUDA_LANDMARKS["Clock_Tower"]["radius"],
        "tier": "high",
        "description": "Western fortress with multi-story buildings and iconic clock tower",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Clock_Tower"]["x"] - 20.0, BERMUDA_LANDMARKS["Clock_Tower"]["y"], BERMUDA_LANDMARKS["Clock_Tower"]["z"] - 20.0),
            Vector3(BERMUDA_LANDMARKS["Clock_Tower"]["x"] + 20.0, BERMUDA_LANDMARKS["Clock_Tower"]["y"], BERMUDA_LANDMARKS["Clock_Tower"]["z"] + 20.0),
            Vector3(BERMUDA_LANDMARKS["Clock_Tower"]["x"] - 10.0, BERMUDA_LANDMARKS["Clock_Tower"]["y"], BERMUDA_LANDMARKS["Clock_Tower"]["z"] + 30.0),
        ],
    },
    "Factory": {
        "center": Vector3(BERMUDA_LANDMARKS["Factory"]["x"], BERMUDA_LANDMARKS["Factory"]["y"], BERMUDA_LANDMARKS["Factory"]["z"]),
        "radius": BERMUDA_LANDMARKS["Factory"]["radius"],
        "tier": "very_high",
        "description": "Industrial roof and warehouse complex, heavy early combat",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Factory"]["x"] - 20.0, BERMUDA_LANDMARKS["Factory"]["y"], BERMUDA_LANDMARKS["Factory"]["z"] - 20.0),
            Vector3(BERMUDA_LANDMARKS["Factory"]["x"] + 25.0, BERMUDA_LANDMARKS["Factory"]["y"], BERMUDA_LANDMARKS["Factory"]["z"] + 15.0),
            Vector3(BERMUDA_LANDMARKS["Factory"]["x"], BERMUDA_LANDMARKS["Factory"]["y"], BERMUDA_LANDMARKS["Factory"]["z"] + 30.0),
        ],
    },
    "Pochinok": {
        "center": Vector3(BERMUDA_LANDMARKS["Pochinok"]["x"], BERMUDA_LANDMARKS["Pochinok"]["y"], BERMUDA_LANDMARKS["Pochinok"]["z"]),
        "radius": BERMUDA_LANDMARKS["Pochinok"]["radius"],
        "tier": "high",
        "description": "Dense southern village with extensive loot in residential compounds",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Pochinok"]["x"] - 30.0, BERMUDA_LANDMARKS["Pochinok"]["y"], BERMUDA_LANDMARKS["Pochinok"]["z"] - 20.0),
            Vector3(BERMUDA_LANDMARKS["Pochinok"]["x"] + 25.0, BERMUDA_LANDMARKS["Pochinok"]["y"], BERMUDA_LANDMARKS["Pochinok"]["z"] + 25.0),
            Vector3(BERMUDA_LANDMARKS["Pochinok"]["x"] - 10.0, BERMUDA_LANDMARKS["Pochinok"]["y"], BERMUDA_LANDMARKS["Pochinok"]["z"] + 35.0),
        ],
    },
    "Bimasakti": {
        "center": Vector3(BERMUDA_LANDMARKS["Bimasakti_Strip"]["x"], BERMUDA_LANDMARKS["Bimasakti_Strip"]["y"], BERMUDA_LANDMARKS["Bimasakti_Strip"]["z"]),
        "radius": BERMUDA_LANDMARKS["Bimasakti_Strip"]["radius"],
        "tier": "high",
        "description": "Central road and tower complex below Peak",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Bimasakti_Strip"]["x"] - 25.0, BERMUDA_LANDMARKS["Bimasakti_Strip"]["y"], BERMUDA_LANDMARKS["Bimasakti_Strip"]["z"] - 20.0),
            Vector3(BERMUDA_LANDMARKS["Bimasakti_Strip"]["x"] + 25.0, BERMUDA_LANDMARKS["Bimasakti_Strip"]["y"], BERMUDA_LANDMARKS["Bimasakti_Strip"]["z"] + 25.0),
        ],
    },
    "Shipyard": {
        "center": Vector3(BERMUDA_LANDMARKS["Shipyard"]["x"], BERMUDA_LANDMARKS["Shipyard"]["y"], BERMUDA_LANDMARKS["Shipyard"]["z"]),
        "radius": BERMUDA_LANDMARKS["Shipyard"]["radius"],
        "tier": "high",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Shipyard"]["x"] - 25.0, BERMUDA_LANDMARKS["Shipyard"]["y"], BERMUDA_LANDMARKS["Shipyard"]["z"] - 20.0),
            Vector3(BERMUDA_LANDMARKS["Shipyard"]["x"] + 25.0, BERMUDA_LANDMARKS["Shipyard"]["y"], BERMUDA_LANDMARKS["Shipyard"]["z"] + 25.0),
        ],
    },
    "Mill": {
        "center": Vector3(BERMUDA_LANDMARKS["Mill"]["x"], BERMUDA_LANDMARKS["Mill"]["y"], BERMUDA_LANDMARKS["Mill"]["z"]),
        "radius": BERMUDA_LANDMARKS["Mill"]["radius"],
        "tier": "very_high",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Mill"]["x"] - 20.0, BERMUDA_LANDMARKS["Mill"]["y"], BERMUDA_LANDMARKS["Mill"]["z"] - 15.0),
            Vector3(BERMUDA_LANDMARKS["Mill"]["x"] + 20.0, BERMUDA_LANDMARKS["Mill"]["y"], BERMUDA_LANDMARKS["Mill"]["z"] + 20.0),
        ],
    },
    "Mars Electric": {
        "center": Vector3(BERMUDA_LANDMARKS["Mars_Electric"]["x"], BERMUDA_LANDMARKS["Mars_Electric"]["y"], BERMUDA_LANDMARKS["Mars_Electric"]["z"]),
        "radius": BERMUDA_LANDMARKS["Mars_Electric"]["radius"],
        "tier": "medium",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Mars_Electric"]["x"] - 20.0, BERMUDA_LANDMARKS["Mars_Electric"]["y"], BERMUDA_LANDMARKS["Mars_Electric"]["z"] - 20.0),
        ],
    },
    "Katulistiwa": {
        "center": Vector3(BERMUDA_LANDMARKS["Katulistiwa"]["x"], BERMUDA_LANDMARKS["Katulistiwa"]["y"], BERMUDA_LANDMARKS["Katulistiwa"]["z"]),
        "radius": BERMUDA_LANDMARKS["Katulistiwa"]["radius"],
        "tier": "medium",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Katulistiwa"]["x"] - 15.0, BERMUDA_LANDMARKS["Katulistiwa"]["y"], BERMUDA_LANDMARKS["Katulistiwa"]["z"] - 15.0),
        ],
    },
    "Hangar": {
        "center": Vector3(BERMUDA_LANDMARKS["Hangar"]["x"], BERMUDA_LANDMARKS["Hangar"]["y"], BERMUDA_LANDMARKS["Hangar"]["z"]),
        "radius": BERMUDA_LANDMARKS["Hangar"]["radius"],
        "tier": "medium",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Hangar"]["x"] - 20.0, BERMUDA_LANDMARKS["Hangar"]["y"], BERMUDA_LANDMARKS["Hangar"]["z"] - 20.0),
        ],
    },
    "Cape Town": {
        "center": Vector3(BERMUDA_LANDMARKS["Cape_Town"]["x"], BERMUDA_LANDMARKS["Cape_Town"]["y"], BERMUDA_LANDMARKS["Cape_Town"]["z"]),
        "radius": BERMUDA_LANDMARKS["Cape_Town"]["radius"],
        "tier": "medium",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Cape_Town"]["x"] - 20.0, BERMUDA_LANDMARKS["Cape_Town"]["y"], BERMUDA_LANDMARKS["Cape_Town"]["z"] - 20.0),
        ],
    },
    "Sentosa": {
        "center": Vector3(BERMUDA_LANDMARKS["Sentosa"]["x"], BERMUDA_LANDMARKS["Sentosa"]["y"], BERMUDA_LANDMARKS["Sentosa"]["z"]),
        "radius": BERMUDA_LANDMARKS["Sentosa"]["radius"],
        "tier": "high",
        "waypoints": [
            Vector3(BERMUDA_LANDMARKS["Sentosa"]["x"] - 20.0, BERMUDA_LANDMARKS["Sentosa"]["y"], BERMUDA_LANDMARKS["Sentosa"]["z"] - 20.0),
        ],
    },
}


# ---------------------------------------------------------------------------
# Authentic Free Fire Bot Nicknames (Curated 49 realistic identities)
# ---------------------------------------------------------------------------

AUTHENTIC_BOT_NICKNAMES: List[str] = [
    "★Killer_Pro★",
    "ShadowNinja",
    "Vampire99",
    "Alpha_Wolf",
    "Devil_Hunter",
    "Sk_Sabir_Fan",
    "BadBoy_YT",
    "ThunderBolt",
    "SniperGod",
    "GhostRider",
    "DarkKnight",
    "Phoenix_Fire",
    "NoobMaster69",
    "Total_Gaming_Fan",
    "RaiStar_Army",
    "Toxic_Soul",
    "Venom_Strike",
    "Crazy_Frog",
    "Eagle_Eye",
    "Bullet_Proof",
    "Black_Panther",
    "Dragon_Slayer",
    "Red_Devil",
    "Night_Fury",
    "Hyper_Beast",
    "Master_Mind",
    "Silent_Killer",
    "Storm_Bringer",
    "War_Machine",
    "Apex_Predator",
    "Frost_Bite",
    "Iron_Man_07",
    "Savage_King",
    "Death_Bringer",
    "Blood_Seeker",
    "Cyber_Samurai",
    "Soul_Eater",
    "Viper_Strike",
    "Thunder_Storm",
    "Ghost_Hunter",
    "Wild_Hunter",
    "Fire_Storm",
    "Neon_Ninja",
    "Titan_Fall",
    "Omega_Zero",
    "Blade_Runner",
    "Shadow_Fiend",
    "Crimson_Tide",
    "Silver_Bullet",
]


# ---------------------------------------------------------------------------
# Authentic Bot Profile
# ---------------------------------------------------------------------------

@dataclass
class BotProfile:
    bot_id: int               # 1..49
    account_id: int           # 2000001..2000049
    nickname: str
    avatar_id: int            # Authentic character avatar ID (101000001..)
    avatar_name: str
    gender: int               # 1: Female, 2: Male
    level: int                # 15..65
    rank_id: int              # 1: Bronze .. 6: Heroic
    rank_name: str
    rank_score: int           # 1000..3400
    banner_id: int
    headpic_id: int
    lootbox_id: int
    parachute_id: int
    skyboard_id: int
    equipped_clothes: List[int]
    primary_weapon: int
    primary_weapon_name: str
    secondary_weapon: int
    secondary_weapon_name: str
    weapon_skin: int
    target_town: str
    player_id: int = 0
    spawn_position: Vector3 = field(default_factory=lambda: Vector3(-500.0, 10.0, 800.0))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_id": self.bot_id,
            "account_id": self.account_id,
            "nickname": self.nickname,
            "avatar_id": self.avatar_id,
            "avatar_name": self.avatar_name,
            "gender": self.gender,
            "level": self.level,
            "rank": self.rank_name,
            "rank_score": self.rank_score,
            "banner_id": self.banner_id,
            "headpic_id": self.headpic_id,
            "lootbox_id": self.lootbox_id,
            "parachute_id": self.parachute_id,
            "skyboard_id": self.skyboard_id,
            "equipped_clothes": self.equipped_clothes,
            "primary_weapon": self.primary_weapon,
            "primary_weapon_name": self.primary_weapon_name,
            "secondary_weapon": self.secondary_weapon,
            "secondary_weapon_name": self.secondary_weapon_name,
            "target_town": self.target_town,
            "spawn_position": self.spawn_position.to_dict(),
        }


# ---------------------------------------------------------------------------
# Simulated Bot Opponent Entity
# ---------------------------------------------------------------------------

class SimulatedBot:
    """
    Authoritative state & behavior model for a single simulated Free Fire opponent.
    Handles movement, physics pose, animation state, combat, taking damage, and loot dropping.
    """

    def __init__(self, profile: BotProfile):
        self.profile = profile
        self.bot_id = profile.bot_id
        self.account_id = profile.account_id
        self.player_id = profile.player_id if getattr(profile, "player_id", 0) > 0 else (profile.bot_id + 1)
        self.nickname = profile.nickname

        # Spatial Transform
        self.position = profile.spawn_position.copy()
        self.velocity = Vector3(0.0, 0.0, 0.0)
        self.rotation_yaw = 0.0   # Horizontal facing angle in degrees (0..360)
        self.rotation_pitch = 0.0 # Vertical look angle in degrees (-89..89)
        self.speed = 0.0

        # Animation & Physics State
        self.physx_state = PhysxState.WALKING
        self.physx_pose = PhysxPose.STANDING

        # Health & Combat Attributes
        self.max_hp = 200
        self.hp = 200
        self.max_ep = 200
        self.ep = 50
        self.vest_durability = 100.0    # Absorbs body damage
        self.helmet_durability = 100.0  # Absorbs head damage
        self.vest_level = random.choice([1, 2, 3])
        self.helmet_level = random.choice([1, 2, 3])
        self.is_firing = False
        self.item_on_hand = profile.primary_weapon
        self.current_weapon_name = profile.primary_weapon_name
        self.medkits_count = random.randint(2, 4)
        self.ammo_count = 120
        self.kill_count = 0

        # Lifecycle & Behavior State
        self.lifecycle_state = BotLifecycleState.WAITING_ISLAND
        self.target_town = profile.target_town
        self.target_location = BERMUDA_HOT_DROPS.get(
            profile.target_town, {}
        ).get("center", Vector3(0.0, 30.0, 0.0)).copy()

        # Navigation & Roaming AI
        self.current_waypoint: Optional[Vector3] = None
        self.state_timer = 0.0
        self.fire_timer = 0.0
        self.roam_pause_timer = 0.0

        # Target Engagement
        self.target_entity_id: Optional[int] = None
        self.target_position: Optional[Vector3] = None
        self.detection_radius = random.uniform(55.0, 80.0)
        self.accuracy = random.uniform(0.40, 0.65) # 40-65% hit rate

        # Death Lootbox
        self.dropped_lootbox: Optional[Dict[str, Any]] = None

    def spawn_on_island(self) -> None:
        """Place bot on the Bermuda spawn island waiting area"""
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(5.0, SPAWN_ISLAND_RADIUS)
        self.position = Vector3(
            SPAWN_ISLAND_CENTER.x + r * math.cos(angle),
            SPAWN_ISLAND_CENTER.y,
            SPAWN_ISLAND_CENTER.z + r * math.sin(angle),
        )
        self.rotation_yaw = random.uniform(0, 360)
        self.rotation_pitch = 0.0
        self.physx_state = PhysxState.WALKING
        self.physx_pose = PhysxPose.STANDING
        self.lifecycle_state = BotLifecycleState.WAITING_ISLAND
        self.hp = 200
        self.speed = 0.0

    def board_airplane(self, flight_pos: Vector3) -> None:
        """Board cargo plane for match drop sequence"""
        self.position = flight_pos.copy()
        self.physx_state = PhysxState.ONBOARD
        self.physx_pose = PhysxPose.STANDING
        self.lifecycle_state = BotLifecycleState.AIRPLANE
        self.speed = 60.0

    def eject_and_skydive(self) -> None:
        """Eject from plane and begin skydiving toward hot drop town"""
        self.physx_state = PhysxState.SKYDIVING
        self.physx_pose = PhysxPose.SKYDIVING
        self.lifecycle_state = BotLifecycleState.SKYDIVING
        self.velocity = Vector3(0.0, -35.0, 0.0)

    def deploy_parachute(self) -> None:
        """Deploy parachute when reaching deployment altitude (~65m)"""
        self.physx_state = PhysxState.PARACHUTING
        self.physx_pose = PhysxPose.STANDING
        self.lifecycle_state = BotLifecycleState.PARACHUTING
        self.velocity = Vector3(0.0, -8.0, 0.0)

    def land_on_ground(self) -> None:
        """Touchdown on the town surface and transition to ground combat roaming"""
        self.position.y = self.target_location.y
        self.physx_state = PhysxState.WALKING
        self.physx_pose = PhysxPose.STANDING
        self.lifecycle_state = BotLifecycleState.GROUND_ROAMING
        self.speed = 0.0
        self._select_next_town_waypoint()

    def _select_next_town_waypoint(self) -> None:
        """Pick next roaming waypoint within the town compound"""
        town_info = BERMUDA_HOT_DROPS.get(self.target_town)
        if town_info and "waypoints" in town_info and town_info["waypoints"]:
            wps = town_info["waypoints"]
            self.current_waypoint = random.choice(wps).copy()
            self.current_waypoint.x += random.uniform(-8.0, 8.0)
            self.current_waypoint.z += random.uniform(-8.0, 8.0)
        else:
            offset_x = random.uniform(-30.0, 30.0)
            offset_z = random.uniform(-30.0, 30.0)
            self.current_waypoint = Vector3(
                self.target_location.x + offset_x,
                self.target_location.y,
                self.target_location.z + offset_z,
            )

    def tick(
        self,
        dt: float,
        safe_zone_center: Optional[Vector3] = None,
        safe_zone_radius: Optional[float] = None,
        potential_targets: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute one bot simulation tick of duration `dt` seconds.
        Returns a list of generated combat events.
        """
        events: List[Dict[str, Any]] = []

        if self.lifecycle_state == BotLifecycleState.DEAD:
            return events

        self.state_timer += dt

        # 1. Spawn Island Phase
        if self.lifecycle_state == BotLifecycleState.WAITING_ISLAND:
            self._tick_island_roam(dt)

        # 2. Airplane Phase (handled by controller flight update)
        elif self.lifecycle_state == BotLifecycleState.AIRPLANE:
            pass

        # 3. Skydiving Phase
        elif self.lifecycle_state == BotLifecycleState.SKYDIVING:
            self._tick_skydiving(dt)

        # 4. Parachuting Phase
        elif self.lifecycle_state == BotLifecycleState.PARACHUTING:
            self._tick_parachuting(dt)

        # 5. Ground Roaming & Looting Phase
        elif self.lifecycle_state in (
            BotLifecycleState.GROUND_ROAMING,
            BotLifecycleState.LOOTING,
        ):
            self._tick_ground_roam(dt, safe_zone_center, safe_zone_radius)
            if potential_targets:
                self._scan_and_engage_targets(potential_targets)

        # 6. Combat Engagement Phase
        elif self.lifecycle_state == BotLifecycleState.COMBAT_ENGAGING:
            combat_events = self._tick_combat(dt, potential_targets)
            events.extend(combat_events)

        # 7. Taking Cover & Healing Phase
        elif self.lifecycle_state == BotLifecycleState.TAKING_COVER:
            self._tick_healing(dt)

        return events

    def _tick_island_roam(self, dt: float) -> None:
        """Casual roaming, dashing, and idling on Spawn Island"""
        self.roam_pause_timer -= dt
        if self.roam_pause_timer <= 0:
            if random.random() < 0.25:
                self.speed = 0.0
                self.physx_pose = PhysxPose.STANDING
                self.roam_pause_timer = random.uniform(1.0, 2.5)
            else:
                self.rotation_yaw = random.uniform(0, 360)
                self.speed = random.choice([3.5, 6.2])
                self.physx_pose = PhysxPose.DASHING if self.speed > 4.5 else PhysxPose.STANDING
                self.roam_pause_timer = random.uniform(2.0, 4.0)

        if self.speed > 0:
            rad = math.radians(self.rotation_yaw)
            dx = math.sin(rad) * self.speed * dt
            dz = math.cos(rad) * self.speed * dt
            new_x = self.position.x + dx
            new_z = self.position.z + dz
            dist = math.sqrt((new_x - SPAWN_ISLAND_CENTER.x) ** 2 + (new_z - SPAWN_ISLAND_CENTER.z) ** 2)
            if dist < SPAWN_ISLAND_RADIUS:
                self.position.x = new_x
                self.position.z = new_z
            else:
                self.rotation_yaw = (self.rotation_yaw + 180) % 360

    def _tick_skydiving(self, dt: float) -> None:
        """Fast free fall toward the designated town center"""
        self.position.y += self.velocity.y * dt

        h_dir = Vector3(
            self.target_location.x - self.position.x,
            0.0,
            self.target_location.z - self.position.z,
        )
        h_dist = math.sqrt(h_dir.x * h_dir.x + h_dir.z * h_dir.z)
        glide_speed = 40.0
        if h_dist > 5.0:
            step = min(h_dist, glide_speed * dt)
            self.position.x += (h_dir.x / h_dist) * step
            self.position.z += (h_dir.z / h_dist) * step
            self.rotation_yaw = (math.degrees(math.atan2(h_dir.x, h_dir.z)) + 360) % 360

        if self.position.y <= 65.0:
            self.deploy_parachute()

    def _tick_parachuting(self, dt: float) -> None:
        """Gentle glide descent onto town landing zone"""
        self.position.y += self.velocity.y * dt

        h_dir = Vector3(
            self.target_location.x - self.position.x,
            0.0,
            self.target_location.z - self.position.z,
        )
        h_dist = math.sqrt(h_dir.x * h_dir.x + h_dir.z * h_dir.z)
        glide_speed = 14.0
        if h_dist > 2.0:
            step = min(h_dist, glide_speed * dt)
            self.position.x += (h_dir.x / h_dist) * step
            self.position.z += (h_dir.z / h_dist) * step
            self.rotation_yaw = (math.degrees(math.atan2(h_dir.x, h_dir.z)) + 360) % 360

        if self.position.y <= self.target_location.y:
            self.land_on_ground()

    def _tick_ground_roam(
        self,
        dt: float,
        safe_zone_center: Optional[Vector3],
        safe_zone_radius: Optional[float],
    ) -> None:
        """Navigate town compounds, loot ground items, and obey safe zone boundaries"""
        if self.current_waypoint is None:
            self._select_next_town_waypoint()
            return

        # Redirect toward white circle center if near or outside safe zone perimeter
        if safe_zone_center and safe_zone_radius:
            dist_to_sz = self.position.horizontal_distance_to(safe_zone_center)
            if dist_to_sz > safe_zone_radius * 0.80:
                dir_sz = self.position.direction_to(safe_zone_center)
                self.current_waypoint = Vector3(
                    self.position.x + dir_sz.x * 50.0,
                    self.position.y,
                    self.position.z + dir_sz.z * 50.0,
                )

        dist = self.position.horizontal_distance_to(self.current_waypoint)
        sprint_speed = 6.2 # Free Fire sprint speed
        if dist < 2.5:
            self._select_next_town_waypoint()
            self.speed = 0.0
            self.physx_pose = PhysxPose.STANDING
        else:
            dir_wp = self.position.direction_to(self.current_waypoint)
            step = min(dist, sprint_speed * dt)
            self.position.x += dir_wp.x * step
            self.position.z += dir_wp.z * step
            self.speed = sprint_speed
            self.physx_pose = PhysxPose.DASHING
            self.rotation_yaw = (math.degrees(math.atan2(dir_wp.x, dir_wp.z)) + 360) % 360

    def _scan_and_engage_targets(self, targets: List[Dict[str, Any]]) -> None:
        """Scan field of view for enemy players or opposing bots within detection radius"""
        closest_dist = self.detection_radius
        chosen_target: Optional[Dict[str, Any]] = None

        for t in targets:
            if t.get("entity_id") == self.bot_id or t.get("hp", 0) <= 0:
                continue

            pos_dict = t.get("position", {})
            t_pos = Vector3(pos_dict.get("x", 0), pos_dict.get("y", 0), pos_dict.get("z", 0))
            dist = self.position.distance_to(t_pos)

            if dist < closest_dist:
                closest_dist = dist
                chosen_target = t

        if chosen_target:
            self.target_entity_id = chosen_target.get("entity_id")
            pos_dict = chosen_target.get("position", {})
            self.target_position = Vector3(pos_dict.get("x", 0), pos_dict.get("y", 0), pos_dict.get("z", 0))
            self.lifecycle_state = BotLifecycleState.COMBAT_ENGAGING
            self.speed = 0.0
            self.physx_pose = PhysxPose.STANDING

            # Calculate initial aim angles immediately upon acquisition
            dx = self.target_position.x - self.position.x
            dy = self.target_position.y - self.position.y
            dz = self.target_position.z - self.position.z
            h_dist = math.sqrt(dx * dx + dz * dz)
            self.rotation_yaw = (math.degrees(math.atan2(dx, dz)) + 360) % 360
            self.rotation_pitch = math.degrees(math.atan2(dy, h_dist)) if h_dist > 1e-5 else 0.0

    def _tick_combat(
        self,
        dt: float,
        potential_targets: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Aim at acquired target, shoot in bursts, strafe, and dispatch hit/fire events"""
        events: List[Dict[str, Any]] = []

        curr_target = None
        if potential_targets and self.target_entity_id is not None:
            for t in potential_targets:
                if t.get("entity_id") == self.target_entity_id and t.get("hp", 0) > 0:
                    curr_target = t
                    pos_dict = t.get("position", {})
                    self.target_position = Vector3(pos_dict.get("x", 0), pos_dict.get("y", 0), pos_dict.get("z", 0))
                    break

        if not curr_target or not self.target_position:
            self.lifecycle_state = BotLifecycleState.GROUND_ROAMING
            self.target_entity_id = None
            self.is_firing = False
            return events

        dist = self.position.distance_to(self.target_position)
        if dist > 90.0:
            self.lifecycle_state = BotLifecycleState.GROUND_ROAMING
            self.target_entity_id = None
            self.is_firing = False
            return events

        # Aim rotation
        dx = self.target_position.x - self.position.x
        dy = self.target_position.y - self.position.y
        dz = self.target_position.z - self.position.z
        h_dist = math.sqrt(dx * dx + dz * dz)

        self.rotation_yaw = (math.degrees(math.atan2(dx, dz)) + 360) % 360
        self.rotation_pitch = math.degrees(math.atan2(dy, h_dist)) if h_dist > 1e-5 else 0.0

        # Weapon stats lookup
        w_meta = WEAPON_REGISTRY.get(self.current_weapon_name, WEAPON_REGISTRY["M4A1"])
        fire_rate = w_meta.get("fire_rate", 0.12)
        base_dmg = w_meta.get("base_damage", 29.0)

        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.is_firing = True
            self.fire_timer = fire_rate * random.uniform(1.2, 2.2)

            is_hit = random.random() < self.accuracy
            hit_part_val = BodyPart.BODY
            dmg = int(base_dmg)

            if is_hit:
                if random.random() < 0.18:
                    hit_part_val = BodyPart.HEAD
                    dmg = int(base_dmg * w_meta.get("headshot_multiplier", 2.5))

            events.append({
                "event": "BOT_FIRE",
                "attacker_id": self.bot_id,
                "target_id": self.target_entity_id,
                "weapon_name": self.current_weapon_name,
                "weapon_id": self.item_on_hand,
                "yaw": round(self.rotation_yaw, 2),
                "pitch": round(self.rotation_pitch, 2),
                "damage": dmg if is_hit else 0,
                "hit_part": parse_body_part_code(hit_part_val),
                "hit_part_name": str(hit_part_val),
                "is_hit": is_hit,
            })

            if random.random() < 0.35:
                self.physx_pose = PhysxPose.CROUCHING
            else:
                self.physx_pose = PhysxPose.STANDING

        return events

    def _tick_healing(self, dt: float) -> None:
        """Consume medkit to restore HP when safe"""
        if self.state_timer >= 4.0:
            self.hp = min(self.max_hp, self.hp + 75)
            self.medkits_count = max(0, self.medkits_count - 1)
            self.lifecycle_state = BotLifecycleState.GROUND_ROAMING
            self.physx_pose = PhysxPose.STANDING

    def take_damage(
        self,
        damage: int,
        attacker_id: int,
        hit_part: Any = BodyPart.BODY,
        weapon_id: int = 0,
        weapon_name: str = "Weapon",
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Apply damage to bot. Absorbs with armor, checks death, and drops loot box.
        Returns (is_dead, death_event_dict).
        """
        if self.lifecycle_state == BotLifecycleState.DEAD:
            return True, None

        part_code = parse_body_part_code(hit_part)
        effective_dmg = float(damage)

        if part_code == 1 and self.helmet_durability > 0: # HEAD
            reduction = 0.33 if self.helmet_level == 1 else (0.45 if self.helmet_level == 2 else 0.57)
            mitigated = effective_dmg * reduction
            self.helmet_durability = max(0.0, self.helmet_durability - effective_dmg * 0.35)
            effective_dmg = max(1.0, effective_dmg - mitigated)
        elif part_code == 2 and self.vest_durability > 0: # BODY
            reduction = 0.33 if self.vest_level == 1 else (0.50 if self.vest_level == 2 else 0.65)
            mitigated = effective_dmg * reduction
            self.vest_durability = max(0.0, self.vest_durability - effective_dmg * 0.25)
            effective_dmg = max(1.0, effective_dmg - mitigated)

        self.hp -= int(effective_dmg)

        if self.lifecycle_state not in (
            BotLifecycleState.DEAD,
            BotLifecycleState.COMBAT_ENGAGING,
        ):
            self.target_entity_id = attacker_id
            self.lifecycle_state = BotLifecycleState.COMBAT_ENGAGING

        if self.hp < 45 and self.medkits_count > 0:
            self.lifecycle_state = BotLifecycleState.TAKING_COVER
            self.physx_pose = PhysxPose.CROUCHING
            self.state_timer = 0.0

        if self.hp <= 0:
            self.hp = 0
            self.lifecycle_state = BotLifecycleState.DEAD
            self.physx_pose = PhysxPose.KNOCKDOWN
            self.physx_state = PhysxState.WALKING
            self.is_firing = False

            self.dropped_lootbox = {
                "lootbox_id": self.profile.lootbox_id,
                "position": self.position.to_dict(),
                "items": [
                    {"item_id": self.profile.primary_weapon, "name": self.profile.primary_weapon_name, "count": 1},
                    {"item_id": self.profile.secondary_weapon, "name": self.profile.secondary_weapon_name, "count": 1},
                    {"item_id": 501000001, "name": "AR Ammo", "count": 90},
                    {"item_id": 401000001, "name": "Medkit", "count": self.medkits_count},
                ],
                "owner_id": self.bot_id,
            }

            death_event = {
                "event": "BOT_DEAD",
                "victim_id": self.bot_id,
                "victim_name": self.nickname,
                "attacker_id": attacker_id,
                "hit_part": part_code,
                "hit_part_name": str(hit_part),
                "weapon_id": weapon_id,
                "weapon_name": weapon_name,
                "lootbox": self.dropped_lootbox,
            }
            return True, death_event

        return False, None

    def to_state_dict(self) -> Dict[str, Any]:
        """Authoritative state dictionary for high-level JSON/UDP broadcasts"""
        return {
            "entity_id": self.bot_id,
            "player_id": getattr(self, "player_id", self.bot_id + 1),
            "account_id": self.account_id,
            "nickname": self.nickname,
            "position": self.position.to_dict(),
            "rotation": {
                "yaw": round(self.rotation_yaw, 2),
                "pitch": round(self.rotation_pitch, 2),
            },
            "yaw": round(self.rotation_yaw, 2),
            "pitch": round(self.rotation_pitch, 2),
            "speed": round(self.speed, 2),
            "physx_state": int(self.physx_state),
            "physx_pose": int(self.physx_pose),
            "hp": self.hp,
            "max_hp": self.max_hp,
            "item_on_hand": self.item_on_hand,
            "weapon_name": self.current_weapon_name,
            "is_firing": self.is_firing,
            "lifecycle_state": int(self.lifecycle_state),
            "is_alive": (self.hp > 0),
            "is_dead": (self.lifecycle_state == BotLifecycleState.DEAD),
        }

    def encode_binary_udp_state(self) -> bytes:
        """
        Encode low-latency binary state packet for UDP transmission.
        Format (39 bytes):
          uint32 entity_id
          float  x, y, z
          float  yaw, pitch
          float  speed
          uint8  physx_state
          uint8  physx_pose
          uint16 hp
          uint16 max_hp
          uint32 item_on_hand
          uint8  is_firing
        """
        return struct.pack(
            "<Ifff ff f BB HH I B",
            self.bot_id,
            float(self.position.x),
            float(self.position.y),
            float(self.position.z),
            float(self.rotation_yaw),
            float(self.rotation_pitch),
            float(self.speed),
            int(self.physx_state),
            int(self.physx_pose),
            int(self.hp),
            int(self.max_hp),
            int(self.item_on_hand),
            1 if self.is_firing else 0,
        )

    def encode_s2c_player_join(self, match_id: int = 10001) -> bytes:
        """Encode official S2C_PlayerJoin packet (Opcode 101) for this bot."""
        from .combat_packet_codec import S2C_PlayerJoin
        pkt = S2C_PlayerJoin(
            player_id=self.bot_id,
            account_id=self.account_id,
            team_id=self.bot_id,
            camp=1,
            match_id=match_id,
            nickname=self.nickname,
            avatar_id=self.profile.avatar_id,
            is_bot=True,
            level=self.profile.level,
            rank=self.profile.rank_score,
            is_ready=True,
            clothes=list(self.profile.equipped_clothes),
            gender=self.profile.gender,
            is_alive=(self.hp > 0),
            skills=[],
            region="IND",
            banner_id=self.profile.banner_id,
            headpic=str(self.profile.headpic_id),
        )
        return pkt.serialize()

    def encode_udp_position_only(self) -> bytes:
        """Encode UDP_PLAYER_POSITION_ONLY (Opcode 1014) for fast position sync."""
        from .combat_packet_codec import UDP_PlayerPositionOnly
        pkt = UDP_PlayerPositionOnly(
            player_id=getattr(self, "player_id", self.bot_id + 1),
            x=self.position.x,
            y=self.position.y,
            z=self.position.z,
            speed=self.speed,
            physx_state=int(self.physx_state),
            physx_pose=int(self.physx_pose),
        )
        return pkt.serialize()

    def encode_udp_aim_rotation(self) -> bytes:
        """Encode UDP_SYNC_AIM_ROTATION (Opcode 1016) for aim angles sync."""
        from .combat_packet_codec import UDP_SyncAimRotation
        pkt = UDP_SyncAimRotation(
            player_id=getattr(self, "player_id", self.bot_id + 1),
            yaw=self.rotation_yaw,
            pitch=self.rotation_pitch,
        )
        return pkt.serialize()


# ---------------------------------------------------------------------------
# Bot Controller (Manager for 49 Simulated Match Opponents)
# ---------------------------------------------------------------------------

class BotController:
    """
    Authoritative AI Bots & Opponent Controller for Free Fire 1.39.
    Spawns 49 bots, generates authentic profiles, oversees match lifecycle,
    and synchronizes state with @udp_engine and @match_director.
    """

    def __init__(self, match_id: int = 10001):
        self.match_id = match_id
        self.bots: Dict[int, SimulatedBot] = {} # bot_id (1..49) -> SimulatedBot
        self.account_id_map: Dict[int, SimulatedBot] = {} # account_id -> SimulatedBot
        self.player_id_map: Dict[int, SimulatedBot] = {} # player_id (2..50) -> SimulatedBot
        self.match_started = False
        self.flight_progress = 0.0
        # Bermuda airplane trajectory
        self.flight_start = Vector3(800.0, 300.0, 800.0)
        self.flight_end = Vector3(-800.0, 300.0, -800.0)
        self.current_flight_pos = Vector3(800.0, 300.0, 800.0)
        self.killfeed: List[Dict[str, Any]] = []
        self._world_engine: Optional[Any] = None

    def attach_world_engine(self, world_engine: Any) -> None:
        """Link WorldEngine instance for bidirectional combat simulation"""
        self._world_engine = world_engine

    def spawn_bots(self, count: int = 49) -> List[BotProfile]:
        """
        Spawn `count` (default 49) simulated bot opponents with authentic Free Fire profiles.
        """
        self.bots.clear()
        self.account_id_map.clear()
        self.player_id_map.clear()

        avatar_keys = list(AVATAR_CATALOG.keys())
        primary_hot_drops = ["Peak", "Clock Tower", "Factory", "Pochinok", "Bimasakti"]
        all_town_keys = list(BERMUDA_HOT_DROPS.keys())

        weapon_choices = [
            (907000010, "M4A1"),
            (907000013, "AK47"),
            (907000014, "SCAR"),
            (907000002, "MP40"),
            (907000003, "UMP"),
            (907000006, "M1014"),
            (907000005, "AWM"),
        ]

        profiles: List[BotProfile] = []

        for i in range(count):
            bot_id = i + 1
            account_id = 2000000 + bot_id

            if count == 2:
                player_id = 2 if i == 0 else 3
                if i == 0:
                    nickname = "Bot_Kelly"
                    avatar_id = 101000006
                    avatar_meta = AVATAR_CATALOG.get(avatar_id, {})
                    avatar_name = "Kelly"
                    gender = 1
                    equipped_clothes = [211000000, 203000059, 204000046, 205000029]
                else:
                    nickname = "Bot_Andrew"
                    avatar_id = 102000005
                    avatar_meta = AVATAR_CATALOG.get(avatar_id, {})
                    avatar_name = "Andrew"
                    gender = 2
                    equipped_clothes = [211000000, 203000056, 204000043, 205000026]
            else:
                player_id = bot_id + 1
                nickname = AUTHENTIC_BOT_NICKNAMES[i % len(AUTHENTIC_BOT_NICKNAMES)]
                avatar_id = avatar_keys[i % len(avatar_keys)]
                avatar_meta = AVATAR_CATALOG[avatar_id]
                avatar_name = avatar_meta.get("name", "Adam")
                gender = avatar_meta.get("gender", 2)
                default_clothes = avatar_meta.get("default_clothes", [])
                equipped_clothes = list(default_clothes) if default_clothes else [203000573, 204000345, 205000299]
                # Ensure at least 3 outfit items for full visual presentation
                if len(equipped_clothes) < 3:
                    baseline = [203000573, 204000345, 205000299]
                    for item in baseline:
                        if item not in equipped_clothes and len(equipped_clothes) < 3:
                            equipped_clothes.append(item)

            rank_tiers = [
                ("Bronze I", 1, 1000),
                ("Bronze II", 1, 1100),
                ("Silver I", 2, 1300),
                ("Gold II", 3, 1600),
                ("Gold IV", 3, 1900),
                ("Platinum I", 4, 2100),
                ("Platinum III", 4, 2300),
                ("Diamond II", 5, 2700),
                ("Heroic", 6, 3200),
            ]
            r_name, r_id, r_score = rank_tiers[i % len(rank_tiers)]
            level = random.randint(22, 60)

            pri_wid, pri_wname = weapon_choices[i % len(weapon_choices)]
            sec_wid, sec_wname = (907000001, "USP")

            banner_id = BANNER_IDS[i % len(BANNER_IDS)]
            headpic_id = HEADPIC_IDS[i % len(HEADPIC_IDS)]
            lootbox_id = LOOTBOX_IDS[i % len(LOOTBOX_IDS)]
            parachute_id = PARACHUTE_IDS[i % len(PARACHUTE_IDS)]
            skyboard_id = SKYBOARD_IDS[i % len(SKYBOARD_IDS)]
            skin_id = WEAPON_SKIN_IDS[i % len(WEAPON_SKIN_IDS)]

            if i < 35:
                target_town = primary_hot_drops[i % len(primary_hot_drops)]
            else:
                target_town = all_town_keys[i % len(all_town_keys)]

            # Individual spawn island position
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(5.0, SPAWN_ISLAND_RADIUS)
            spawn_pos = Vector3(
                SPAWN_ISLAND_CENTER.x + r * math.cos(angle),
                SPAWN_ISLAND_CENTER.y,
                SPAWN_ISLAND_CENTER.z + r * math.sin(angle),
            )

            profile = BotProfile(
                bot_id=bot_id,
                account_id=account_id,
                nickname=nickname,
                avatar_id=avatar_id,
                avatar_name=avatar_name,
                gender=gender,
                level=level,
                rank_id=r_id,
                rank_name=r_name,
                rank_score=r_score,
                banner_id=banner_id,
                headpic_id=headpic_id,
                lootbox_id=lootbox_id,
                parachute_id=parachute_id,
                skyboard_id=skyboard_id,
                equipped_clothes=equipped_clothes,
                primary_weapon=pri_wid,
                primary_weapon_name=pri_wname,
                secondary_weapon=sec_wid,
                secondary_weapon_name=sec_wname,
                weapon_skin=skin_id,
                target_town=target_town,
                player_id=player_id,
                spawn_position=spawn_pos,
            )

            bot = SimulatedBot(profile)
            self.bots[bot_id] = bot
            self.account_id_map[account_id] = bot
            self.player_id_map[player_id] = bot
            profiles.append(profile)

        return profiles

    def start_island_phase(self) -> None:
        """Place all 49 bots on the waiting Spawn Island"""
        for bot in self.bots.values():
            bot.spawn_on_island()

    def board_airplane(self, flight_pos: Vector3) -> None:
        """Board all living bots aboard the cargo airplane"""
        self.flight_progress = 0.0
        self.current_flight_pos = flight_pos.copy()
        for bot in self.bots.values():
            bot.board_airplane(self.current_flight_pos)

    def start_airplane_phase(
        self,
        flight_start: Optional[Vector3] = None,
        flight_end: Optional[Vector3] = None,
    ) -> None:
        """Move all living bots into cargo plane for Bermuda parachute flight"""
        if flight_start:
            self.flight_start = flight_start
        if flight_end:
            self.flight_end = flight_end

        self.flight_progress = 0.0
        self.current_flight_pos = self.flight_start.copy()

        for bot in self.bots.values():
            bot.board_airplane(self.current_flight_pos)

    def update_airplane_flight(self, progress: float) -> None:
        """
        Update plane position across Bermuda map (progress: 0.0 to 1.0).
        Automatically triggers skydiving eject for bots as plane reaches closest drop point.
        """
        self.flight_progress = max(0.0, min(1.0, progress))
        self.current_flight_pos = Vector3(
            self.flight_start.x + (self.flight_end.x - self.flight_start.x) * self.flight_progress,
            300.0,
            self.flight_start.z + (self.flight_end.z - self.flight_start.z) * self.flight_progress,
        )

        for bot in self.bots.values():
            if bot.lifecycle_state == BotLifecycleState.AIRPLANE:
                bot.position = self.current_flight_pos.copy()
                h_dist = self.current_flight_pos.horizontal_distance_to(bot.target_location)
                if h_dist <= 260.0 or self.flight_progress >= 0.85:
                    bot.eject_and_skydive()

    def tick(
        self,
        dt: float,
        safe_zone_center: Optional[Vector3] = None,
        safe_zone_radius: Optional[float] = None,
        player_position: Optional[Vector3] = None,
        player_hp: int = 200,
    ) -> Dict[str, Any]:
        """
        Tick all 49 bots and collect state broadcasts & combat events.
        Compatible with match_director, udp_server, and world_engine.
        """
        targets: List[Dict[str, Any]] = []
        if player_position and player_hp > 0:
            targets.append({
                "entity_id": 0,
                "position": player_position.to_dict(),
                "hp": player_hp,
            })

        for bot in self.bots.values():
            if bot.lifecycle_state not in (
                BotLifecycleState.DEAD,
                BotLifecycleState.WAITING_ISLAND,
                BotLifecycleState.AIRPLANE,
            ):
                targets.append({
                    "entity_id": bot.bot_id,
                    "position": bot.position.to_dict(),
                    "hp": bot.hp,
                })

        all_events: List[Dict[str, Any]] = []

        for bot in self.bots.values():
            events = bot.tick(
                dt=dt,
                safe_zone_center=safe_zone_center,
                safe_zone_radius=safe_zone_radius,
                potential_targets=targets,
            )
            for ev in events:
                all_events.append(ev)
                if ev.get("event") in ("BOT_DEAD", "bot_dead"):
                    self.killfeed.append(ev)

        bot_states = [bot.to_state_dict() for bot in self.bots.values()]

        return {
            "alive_count": sum(1 for b in self.bots.values() if b.hp > 0),
            "bot_states": bot_states,
            "events": all_events,
            "combat_events": all_events,
            "killfeed": list(self.killfeed[-10:]),
        }

    def apply_player_attack_on_bot(
        self,
        bot_id: int,
        damage: int,
        hit_part: Any = BodyPart.BODY,
        weapon_id: int = 907000010,
        weapon_name: str = "M4A1",
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Player inflicts damage on a bot.
        Returns (is_dead, death_event_dict).
        """
        bot = self.get_bot(bot_id)
        if not bot:
            return False, None

        is_dead, death_ev = bot.take_damage(
            damage=damage,
            attacker_id=0,
            hit_part=hit_part,
            weapon_id=weapon_id,
            weapon_name=weapon_name,
        )
        if death_ev:
            self.killfeed.append(death_ev)

        return is_dead, death_ev

    def get_binary_udp_broadcast_frames(self) -> bytes:
        """
        Encode all living bots' state into concatenated binary UDP frames.
        Ready for single-datagram or chunked UDP transmission by @udp_engine.
        """
        frames = bytearray()
        for bot in self.bots.values():
            if bot.hp > 0:
                frames += bot.encode_binary_udp_state()
        return bytes(frames)

    def get_all_player_join_packets(self) -> List[bytes]:
        """Encode S2C_PlayerJoin (Opcode 101) packets for all 49 bots."""
        return [b.encode_s2c_player_join(self.match_id) for b in self.bots.values()]

    def get_udp_position_packets(self) -> List[bytes]:
        """Encode UDP_PLAYER_POSITION_ONLY (Opcode 1014) packets for all living bots."""
        return [b.encode_udp_position_only() for b in self.bots.values() if b.hp > 0]

    def get_udp_aim_rotation_packets(self) -> List[bytes]:
        """Encode UDP_SYNC_AIM_ROTATION (Opcode 1016) packets for all living bots."""
        return [b.encode_udp_aim_rotation() for b in self.bots.values() if b.hp > 0]

    def get_bot(self, bot_id: int) -> Optional[SimulatedBot]:
        return self.bots.get(bot_id) or self.account_id_map.get(bot_id) or self.player_id_map.get(bot_id)

    def get_bot_by_account_id(self, account_id: int) -> Optional[SimulatedBot]:
        return self.account_id_map.get(account_id)

    def get_alive_count(self) -> int:
        return sum(1 for b in self.bots.values() if b.hp > 0)

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        return [b.profile.to_dict() for b in self.bots.values()]


# Global singleton instance for UDP server dispatch
global_bot_controller = BotController()
global_bot_controller.spawn_bots(count=49)

