"""
Authoritative World Engine Orchestrator for Free Fire 1.39 Bermuda Combat.
Combines Safe Zone, Airdrops, Red Zone Bombardment, Ground Loot, and Ballistics.
"""

import math
import random
import time
from typing import Dict, Any, List, Optional, Tuple

from .world_constants import (
    BERMUDA_LANDMARKS, WEAPON_REGISTRY, GEAR_REGISTRY, CONSUMABLES_REGISTRY,
    BERMUDA_WAITING_ISLAND_CENTER, BERMUDA_WAITING_ISLAND_RADIUS, BERMUDA_WAITING_ISLAND_SPAWN_RADIUS,
    WeaponCategory, AmmoType
)
from .safe_zone import SafeZoneManager, ZoneState
from .airdrop import AirdropManager, CarePackage, AirdropState
from .red_zone import RedZoneManager, RedZoneState
from .loot_spawner import LootSpawner, GroundItem
from .ballistics import CombatEngine, DamageCalculator, BodyPart, GlooWallEntity


class CombatPlayer:
    """Represents an active human or simulated bot combatant in the Bermuda world."""

    def __init__(self, player_id: str, nickname: str, is_bot: bool = False,
                 x: float = -500.0, y: float = 10.0, z: float = 800.0,
                 entity_id: int = 1, account_id: int = 0):
        self.player_id: str = player_id
        self.nickname: str = nickname
        self.is_bot: bool = is_bot
        self.entity_id: int = entity_id
        self.account_id: int = account_id
        
        # Position & Orientation (defaults to authentic Bermuda Waiting Island)
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.yaw: float = 0.0
        self.pitch: float = 0.0
        self.speed: float = 0.0
        self.physx_state: int = 0  # 0 = WALKING / IDLE
        self.physx_pose: int = 0   # 0 = STANDING
        self.is_indoors: bool = False  # Set to True when inside a building
        
        # Health & State
        self.hp: float = 200.0
        self.max_hp: float = 200.0
        self.ep: float = 0.0          # Energy points (mushrooms/inhalers)
        self.max_ep: float = 200.0
        self.is_alive: bool = True
        self.is_knocked: bool = False
        self.kills: int = 0
        self.damage_dealt: float = 0.0
        
        # Equipped Gear & Inventory
        self.vest: Optional[Dict[str, Any]] = None
        self.helmet: Optional[Dict[str, Any]] = None
        self.backpack_capacity: int = 200
        
        # Weapons: slot1, slot2 (primary), slot3 (handgun), slot4 (melee)
        self.weapons: Dict[str, Optional[Dict[str, Any]]] = {
            "primary1": None,
            "primary2": None,
            "pistol": None,
            "melee": None
        }
        self.active_weapon_slot: str = "melee"
        
        # Ammo Reserves & Utility Inventory
        self.ammo_inventory: Dict[str, int] = {
            AmmoType.AR: 0,
            AmmoType.SMG: 0,
            AmmoType.SG: 0,
            AmmoType.SNIPER: 0
        }
        self.medkits: int = 0
        self.gloo_walls: int = 0
        self.grenades: int = 0

    def take_damage(self, dmg: float, source: str = "bullet", attacker_id: Optional[str] = None) -> Dict[str, Any]:
        """Apply damage directly to player HP."""
        if not self.is_alive:
            return {"damage": 0.0, "is_dead": True}

        prev_hp = self.hp
        self.hp = max(0.0, prev_hp - dmg)
        is_dead = (self.hp <= 0.0)
        
        if is_dead:
            self.is_alive = False

        return {
            "victim_id": self.player_id,
            "attacker_id": attacker_id,
            "damage": round(dmg, 1),
            "source": source,
            "hp_remaining": round(self.hp, 1),
            "is_dead": is_dead
        }

    def heal_medkit(self) -> bool:
        """Consume 1 medkit to restore 75 HP (up to max 200 HP)."""
        if self.medkits <= 0 or self.hp >= self.max_hp or not self.is_alive:
            return False
        self.medkits -= 1
        self.hp = min(self.max_hp, self.hp + 75.0)
        return True

    def to_summary(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "nickname": self.nickname,
            "is_bot": self.is_bot,
            "pos": {"x": round(self.x, 2), "y": round(self.y, 2), "z": round(self.z, 2)},
            "hp": round(self.hp, 1),
            "ep": round(self.ep, 1),
            "is_alive": self.is_alive,
            "kills": self.kills,
            "vest": self.vest["level"] if self.vest else 0,
            "helmet": self.helmet["level"] if self.helmet else 0,
            "active_weapon": self.weapons.get(self.active_weapon_slot),
            "gloo_walls": self.gloo_walls,
            "medkits": self.medkits
        }


class WorldEngine:
    """Master Authoritative Combat & World Simulation Engine for Free Fire 1.39 Bermuda."""

    def __init__(self, seed: Optional[int] = 42):
        self.seed = seed
        self.safe_zone = SafeZoneManager(seed=seed)
        self.airdrop_mgr = AirdropManager()
        self.red_zone = RedZoneManager(seed=seed)
        self.loot_spawner = LootSpawner(seed=seed)
        self.combat = CombatEngine()
        
        self.players: Dict[str, CombatPlayer] = {}
        self.match_time: float = 0.0
        self.is_match_active: bool = False
        
        # Initial population of Bermuda loot
        self.total_initial_loot: int = self.loot_spawner.populate_bermuda_loot()

    # Bermuda Waiting Island authentic geometry
    WAITING_ISLAND_CENTER: Tuple[float, float, float] = BERMUDA_WAITING_ISLAND_CENTER
    WAITING_ISLAND_RADIUS: float = BERMUDA_WAITING_ISLAND_RADIUS
    WAITING_ISLAND_SPAWN_RADIUS: float = BERMUDA_WAITING_ISLAND_SPAWN_RADIUS

    def start_match(self) -> None:
        """Start the live Bermuda combat loop."""
        self.is_match_active = True
        self.match_time = 0.0

    @property
    def alive_player_count(self) -> int:
        """Return the authoritative count of alive players currently in the world."""
        seen = set()
        count = 0
        for p in self.players.values():
            eid = getattr(p, "entity_id", p.player_id)
            if eid not in seen:
                seen.add(eid)
                if p.is_alive:
                    count += 1
        return count

    def get_player(self, player_id: Any) -> Optional[CombatPlayer]:
        """Look up player by player_id string, entity_id, or account_id."""
        pid_str = str(player_id)
        if pid_str in self.players:
            return self.players[pid_str]
        for p in self.players.values():
            if str(getattr(p, "entity_id", "")) == pid_str or str(getattr(p, "account_id", "")) == pid_str:
                return p
        return None

    def initialize_waiting_island(self, human_player_ids: List[str]) -> None:
        """Authoritatively place human players on the Bermuda Waiting Island center pedestal."""
        sx, sy, sz = self.WAITING_ISLAND_CENTER
        for idx, pid in enumerate(human_player_ids, start=1):
            p = self.get_player(pid)
            if p:
                p.x = sx
                p.y = sy
                p.z = sz
                p.yaw = 0.0
                p.pitch = 0.0
                p.speed = 0.0
                p.physx_state = 0
                p.physx_pose = 0
                p.hp = 200.0
                p.is_alive = True
                p.entity_id = idx

    def get_living_players(self) -> List[CombatPlayer]:
        """Return list of distinct living players/bots in the world."""
        seen = set()
        result = []
        for p in self.players.values():
            eid = getattr(p, "entity_id", p.player_id)
            if eid not in seen:
                seen.add(eid)
                if p.is_alive:
                    result.append(p)
        return result

    def register_player(self, player_id: str, nickname: str, is_bot: bool = False,
                        x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None,
                        entity_id: Optional[int] = None, account_id: Optional[int] = None) -> CombatPlayer:
        """Register a player into the world instance with authentic Waiting Island placement."""
        if x is None or z is None:
            # Place on Bermuda Waiting Island spawn area
            sx, sy, sz = self.WAITING_ISLAND_CENTER
            if is_bot:
                angle = random.uniform(0.0, 2.0 * math.pi)
                dist = random.uniform(5.0, self.WAITING_ISLAND_SPAWN_RADIUS)
                x = sx + dist * math.cos(angle)
                z = sz + dist * math.sin(angle)
            else:
                x = sx
                z = sz
            y = sy if y is None else y
        elif y is None:
            y = self.WAITING_ISLAND_CENTER[1]

        # Resolve entity_id
        if entity_id is None:
            if player_id.isdigit() and int(player_id) <= 50:
                entity_id = int(player_id)
            elif is_bot:
                entity_id = len(self.players) + 1
            else:
                entity_id = 1

        acc_id = account_id or (int(player_id) if player_id.isdigit() else 0)

        player = CombatPlayer(player_id, nickname, is_bot=is_bot, x=x, y=y, z=z,
                              entity_id=entity_id, account_id=acc_id)
        # Default starting weapon: Fist / Pan
        pan_info = WEAPON_REGISTRY.get("Pan", {"name": "Pan", "item_id": 907000008, "category": WeaponCategory.MELEE})
        player.weapons["melee"] = {
            "name": pan_info["name"],
            "item_id": pan_info["item_id"],
            "category": pan_info.get("category", WeaponCategory.MELEE)
        }
        self.players[player_id] = player
        # Store entity_id alias for quick client entity lookup
        self.players[str(entity_id)] = player
        return player

    def update_player_pos(self, player_id: str, x: float, y: float, z: float,
                          yaw: float = 0.0, pitch: float = 0.0, speed: float = 0.0,
                          physx_state: Optional[int] = None, physx_pose: Optional[int] = None) -> None:
        """Update authoritative position and orientation received from client or bot."""
        player = self.players.get(player_id) or self.get_player(player_id)
        if player and player.is_alive:
            player.x = x
            player.y = y
            player.z = z
            player.yaw = yaw
            player.pitch = pitch
            player.speed = speed
            if physx_state is not None:
                player.physx_state = physx_state
            if physx_pose is not None:
                player.physx_pose = physx_pose

    def tick(self, delta_time: float) -> Dict[str, Any]:
        """
        Master authoritative simulation tick (e.g. 20 Hz / 50ms).
        Returns aggregated events (poison damage, artillery strikes, airdrops, gloo wall decay).
        """
        if not self.is_match_active:
            return {"events": []}

        self.match_time += delta_time
        events: List[Dict[str, Any]] = []

        # 1. Update Safe Zone & Apply Poison Radiation Damage
        poison_events = self.safe_zone.update(delta_time, self.players)
        for pe in poison_events:
            events.append({"type": "POISON_DAMAGE", "data": pe})
            if pe.get("is_dead"):
                victim = self.players.get(pe["victim_id"])
                if victim:
                    self.combat.kill_feed.append({
                        "attacker_id": None,
                        "attacker_name": "POISON ZONE",
                        "victim_id": victim.player_id,
                        "victim_name": victim.nickname,
                        "weapon": "Zone Radiation",
                        "is_headshot": False,
                        "timestamp": time.time()
                    })

        # 2. Update Red Zone Bombardment
        red_events = self.red_zone.update(
            delta_time, self.players,
            safe_x=self.safe_zone.white_center_x,
            safe_z=self.safe_zone.white_center_z,
            safe_r=self.safe_zone.white_radius
        )
        for re in red_events:
            events.append({"type": "RED_ZONE", "data": re})

        # 3. Update Airdrop Flights & Descending Packages
        airdrop_events = self.airdrop_mgr.update(
            delta_time,
            current_safe_x=self.safe_zone.white_center_x,
            current_safe_z=self.safe_zone.white_center_z,
            current_radius=self.safe_zone.white_radius
        )
        for ae in airdrop_events:
            events.append({"type": "AIRDROP", "data": ae})

        # 4. Update Gloo Wall Lifetimes & Decays
        destroyed_walls = self.combat.update_gloo_walls(delta_time)
        if destroyed_walls:
            events.append({"type": "GLOO_WALLS_DESTROYED", "wall_ids": destroyed_walls})

        return {
            "match_time": round(self.match_time, 2),
            "alive_count": sum(1 for p in self.players.values() if p.is_alive),
            "events": events
        }

    def player_pickup_item(self, player_id: str, pickup_id: int) -> Optional[Dict[str, Any]]:
        """Handle authoritative ground item pickup by a player."""
        player = self.players.get(player_id)
        if not player or not player.is_alive:
            return None

        item = self.loot_spawner.pickup_item(pickup_id, player.x, player.z)
        if not item:
            return None

        # Equip / add to player inventory
        if item.item_type == "weapon":
            # Assign to primary1 or primary2 or pistol
            if item.category in (WeaponCategory.AR, WeaponCategory.SMG, WeaponCategory.SNIPER, WeaponCategory.SHOTGUN):
                if player.weapons["primary1"] is None:
                    slot = "primary1"
                elif player.weapons["primary2"] is None:
                    slot = "primary2"
                else:
                    # Swap with currently held primary
                    slot = "primary1" if player.active_weapon_slot == "primary1" else "primary2"
                
                player.weapons[slot] = {
                    "name": item.name,
                    "item_id": item.item_id,
                    "category": item.category,
                    "ammo_type": item.extra_data.get("ammo_type", AmmoType.AR),
                    "ammo_in_clip": item.extra_data.get("ammo_in_clip", 30)
                }
                player.active_weapon_slot = slot

            elif item.category == WeaponCategory.PISTOL:
                player.weapons["pistol"] = {
                    "name": item.name,
                    "item_id": item.item_id,
                    "category": item.category,
                    "ammo_type": item.extra_data.get("ammo_type", AmmoType.AR),
                    "ammo_in_clip": item.extra_data.get("ammo_in_clip", 12)
                }

        elif item.item_type == "ammo":
            ammo_t = item.extra_data.get("ammo_type", AmmoType.AR)
            player.ammo_inventory[ammo_t] = player.ammo_inventory.get(ammo_t, 0) + item.count

        elif item.item_type == "gear":
            slot = item.category.lower()
            if slot == "vest":
                if player.vest is None or item.extra_data.get("level", 1) >= player.vest.get("level", 1):
                    player.vest = item.extra_data.copy()
            elif slot == "helmet":
                if player.helmet is None or item.extra_data.get("level", 1) >= player.helmet.get("level", 1):
                    player.helmet = item.extra_data.copy()
            elif slot == "backpack":
                player.backpack_capacity = 200 + item.extra_data.get("capacity_bonus", 100)

        elif item.item_type == "consumable":
            if "Medkit" in item.name:
                player.medkits += item.count
            elif "Gloo" in item.name or "Ice" in item.name:
                player.gloo_walls += item.count
            elif "Frag" in item.name:
                player.grenades += item.count

        return {"success": True, "item": item.to_dict()}

    def player_deploy_gloo_wall(self, player_id: str) -> Optional[GlooWallEntity]:
        """Deploy tactical ice cover in front of player."""
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.gloo_walls <= 0:
            return None

        player.gloo_walls -= 1
        return self.combat.deploy_gloo_wall(player_id, player.x, player.y, player.z, player.yaw)

    def player_fire_shot(self, shooter_id: str, victim_id: str, weapon_name: str,
                         body_part: str = BodyPart.CHEST) -> Dict[str, Any]:
        """Process an authoritative combat gunshot between players."""
        shooter = self.players.get(shooter_id)
        victim = self.players.get(victim_id)

        if not shooter or not shooter.is_alive:
            return {"hit": False, "reason": "SHOOTER_INVALID"}
        if not victim or not victim.is_alive:
            return {"hit": False, "reason": "VICTIM_INVALID"}

        res = self.combat.process_shot(shooter, victim, weapon_name, target_part=body_part)
        
        if res.get("hit") and res.get("target_type") == "PLAYER":
            shooter.damage_dealt += res["damage_dealt"]
            if res.get("is_killed"):
                shooter.kills += 1

        return res

    def get_world_snapshot(self) -> Dict[str, Any]:
        """Serialize complete world state for authoritative sync & debugging."""
        return {
            "match_time": round(self.match_time, 2),
            "is_active": self.is_match_active,
            "alive_count": sum(1 for p in self.players.values() if p.is_alive),
            "safe_zone": self.safe_zone.get_sync_packet_data(),
            "red_zone": self.red_zone.get_sync_data(),
            "airdrop_crates": self.airdrop_mgr.get_crates_sync(),
            "active_gloo_walls": len(self.combat.gloo_walls),
            "total_ground_loot": len(self.loot_spawner.items),
            "kill_feed": self.combat.kill_feed[-5:]
        }
