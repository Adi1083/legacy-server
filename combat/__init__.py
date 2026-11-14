"""
Free Fire 1.39 Authoritative Combat & World Engine Package.
Authoritative Match Lifecycle, UDP Networking, World Systems, and AI Opponent Controllers.
"""

from .world_constants import (
    BERMUDA_LANDMARKS,
    WEAPON_REGISTRY,
    GEAR_REGISTRY,
    CONSUMABLES_REGISTRY,
    SAFE_ZONE_PHASES,
    WeaponCategory,
    AmmoType,
    BodyPart,
)
from .safe_zone import SafeZoneManager, ZoneState
from .airdrop import AirdropManager, CarePackage, AirdropState
from .red_zone import RedZoneManager, RedZoneState
from .loot_spawner import LootSpawner, GroundItem
from .ballistics import CombatEngine, DamageCalculator, GlooWallEntity
from .world_engine import WorldEngine, CombatPlayer
from .bot_controller import (
    BotController,
    SimulatedBot,
    BotProfile,
    BotLifecycleState,
    PhysxState,
    PhysxPose,
    Vector3,
    BERMUDA_HOT_DROPS,
    AUTHENTIC_BOT_NICKNAMES,
)
from .match_director import (
    MatchDirector,
    MatchInstance,
    MatchState,
    ParachutePhase,
    AirplaneTrajectory,
    global_match_director,
)

__all__ = [
    "BERMUDA_LANDMARKS",
    "WEAPON_REGISTRY",
    "GEAR_REGISTRY",
    "CONSUMABLES_REGISTRY",
    "SAFE_ZONE_PHASES",
    "WeaponCategory",
    "AmmoType",
    "BodyPart",
    "SafeZoneManager",
    "ZoneState",
    "AirdropManager",
    "CarePackage",
    "AirdropState",
    "RedZoneManager",
    "RedZoneState",
    "LootSpawner",
    "GroundItem",
    "CombatEngine",
    "DamageCalculator",
    "GlooWallEntity",
    "WorldEngine",
    "CombatPlayer",
    "BotController",
    "SimulatedBot",
    "BotProfile",
    "BotLifecycleState",
    "PhysxState",
    "PhysxPose",
    "Vector3",
    "BERMUDA_HOT_DROPS",
    "AUTHENTIC_BOT_NICKNAMES",
    "MatchDirector",
    "MatchInstance",
    "MatchState",
    "ParachutePhase",
    "AirplaneTrajectory",
    "global_match_director",
]
