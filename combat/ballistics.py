"""
Authoritative Ballistics, Hit-Registration, Armor Mitigation, Gloo Wall Obstacles,
and Kill-Feed Notification System for Free Fire 1.39.
"""

import math
import random
import time
from typing import Dict, Any, List, Optional, Tuple

from .world_constants import WEAPON_REGISTRY, GEAR_REGISTRY, CONSUMABLES_REGISTRY

class BodyPart:
    HEAD = "HEAD"
    CHEST = "CHEST"
    BODY = "CHEST"
    STOMACH = "STOMACH"
    LIMBS = "LIMBS"

class GlooWallEntity:
    """A deployed tactical ice cover in the combat world."""

    def __init__(self, wall_id: int, owner_id: str, x: float, y: float, z: float, yaw: float, hp: float = 300.0, lifetime: float = 45.0):
        self.wall_id: int = wall_id
        self.owner_id: str = owner_id
        self.x: float = x
        self.y: float = y
        self.z: float = z
        self.yaw: float = yaw  # orientation degrees
        self.hp: float = hp
        self.max_hp: float = hp
        self.width: float = 3.6
        self.height: float = 2.2
        self.lifetime: float = lifetime
        self.is_destroyed: bool = False

    def take_damage(self, dmg: float) -> bool:
        """Apply damage to gloo wall. Returns True if wall was destroyed."""
        self.hp -= dmg
        if self.hp <= 0.0:
            self.hp = 0.0
            self.is_destroyed = True
            return True
        return False

    def intersects_ray(self, start_x: float, start_z: float, end_x: float, end_z: float) -> bool:
        """2D line segment bounding box intersection test for bullet interception."""
        # Check if line between shooter and victim intersects gloo wall segment
        rad = math.radians(self.yaw + 90.0)
        half_w = self.width / 2.0
        wx1 = self.x - math.cos(rad) * half_w
        wz1 = self.z - math.sin(rad) * half_w
        wx2 = self.x + math.cos(rad) * half_w
        wz2 = self.z + math.sin(rad) * half_w

        return self._line_segments_intersect(start_x, start_z, end_x, end_z, wx1, wz1, wx2, wz2)

    @staticmethod
    def _line_segments_intersect(x1: float, y1: float, x2: float, y2: float,
                                 x3: float, y3: float, x4: float, y4: float) -> bool:
        """Compute 2D line segment intersection."""
        def ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
            return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

        return (ccw(x1, y1, x3, y3, x4, y4) != ccw(x2, y2, x3, y3, x4, y4) and
                ccw(x1, y1, x2, y2, x3, y3) != ccw(x1, y1, x2, y2, x4, y4))


class DamageCalculator:
    """Authoritative Free Fire 1.39 damage calculation engine with armor and distance falloff."""

    @staticmethod
    def calculate_shot_damage(weapon_name: str, distance: float, body_part: str,
                              vest: Optional[Dict[str, Any]] = None,
                              helmet: Optional[Dict[str, Any]] = None) -> Tuple[float, float, float, bool]:
        """
        Calculate authoritative damage dealt to player and durability absorbed by armor.
        Returns: (final_damage_to_hp, vest_durability_loss, helmet_durability_loss, is_headshot)
        """
        wep = WEAPON_REGISTRY.get(weapon_name, WEAPON_REGISTRY["M4A1"])
        base_dmg = wep["base_damage"]
        is_headshot = (body_part == BodyPart.HEAD)

        # 1. Distance Falloff
        falloff_start = wep.get("falloff_start_dist", 30.0)
        falloff_end = wep.get("falloff_end_dist", 70.0)
        falloff_min = wep.get("damage_falloff_min", 0.7)

        if distance <= falloff_start:
            dist_factor = 1.0
        elif distance >= falloff_end:
            dist_factor = falloff_min
        else:
            t = (distance - falloff_start) / max(1.0, (falloff_end - falloff_start))
            dist_factor = 1.0 - t * (1.0 - falloff_min)

        effective_base = base_dmg * dist_factor

        # 2. Body Part Multiplier
        if is_headshot:
            mult = wep.get("headshot_multiplier", 2.5)
        elif body_part in (BodyPart.CHEST, BodyPart.STOMACH):
            mult = 1.0
        else:
            mult = wep.get("limb_multiplier", 0.75)

        raw_damage = effective_base * mult

        # 3. Armor Mitigation
        vest_loss = 0.0
        helmet_loss = 0.0
        final_damage = raw_damage

        if is_headshot and helmet and helmet.get("durability", 0.0) > 0:
            reduction = helmet.get("damage_reduction", 0.33)
            absorbed = raw_damage * reduction
            durability = helmet.get("durability", 0.0)
            actual_absorb = min(absorbed, durability)
            
            final_damage = raw_damage - actual_absorb
            helmet_loss = actual_absorb

        elif not is_headshot and body_part != BodyPart.LIMBS and vest and vest.get("durability", 0.0) > 0:
            reduction = vest.get("damage_reduction", 0.33)
            absorbed = raw_damage * reduction
            durability = vest.get("durability", 0.0)
            actual_absorb = min(absorbed, durability)
            
            final_damage = raw_damage - actual_absorb
            vest_loss = actual_absorb

        return round(final_damage, 1), round(vest_loss, 1), round(helmet_loss, 1), is_headshot


class CombatEngine:
    """Authoritative hit-registration, gloo wall blocking, and combat event processor."""

    def __init__(self):
        self.gloo_walls: Dict[int, GlooWallEntity] = {}
        self.next_wall_id: int = 80001
        self.kill_feed: List[Dict[str, Any]] = []

    def deploy_gloo_wall(self, owner_id: str, px: float, py: float, pz: float, yaw: float) -> GlooWallEntity:
        """Place an authoritative Gloo Wall 2.5 meters in front of the deploying player."""
        rad = math.radians(yaw)
        forward_dist = 2.5
        wx = px + math.sin(rad) * forward_dist
        wz = pz + math.cos(rad) * forward_dist
        
        wall = GlooWallEntity(self.next_wall_id, owner_id, wx, py, wz, yaw)
        self.next_wall_id += 1
        self.gloo_walls[wall.wall_id] = wall
        return wall

    def update_gloo_walls(self, delta_time: float) -> List[int]:
        """Advance gloo wall decay timers and remove expired/destroyed walls."""
        destroyed_ids = []
        for wid, wall in list(self.gloo_walls.items()):
            wall.lifetime -= delta_time
            if wall.lifetime <= 0.0 or wall.is_destroyed:
                destroyed_ids.append(wid)
                del self.gloo_walls[wid]
        return destroyed_ids

    def apply_damage(self, victim: Any, damage: float, attacker: Optional[Any] = None,
                     source: str = "bullet", is_headshot: bool = False) -> Dict[str, Any]:
        """Direct authoritative damage application to player with armor mitigation and kill-feed."""
        if not getattr(victim, "is_alive", True):
            return {"damage": 0.0, "is_dead": True}

        # Apply armor mitigation if equipped
        vest = getattr(victim, "vest", None)
        helmet = getattr(victim, "helmet", None)
        final_dmg = damage

        if is_headshot and helmet and helmet.get("durability", 0.0) > 0:
            reduction = helmet.get("damage_reduction", 0.33)
            absorbed = min(damage * reduction, helmet.get("durability", 0.0))
            final_dmg = max(1.0, damage - absorbed)
            helmet["durability"] = max(0.0, helmet["durability"] - absorbed)
            if helmet["durability"] <= 0.0:
                victim.helmet = None
        elif not is_headshot and vest and vest.get("durability", 0.0) > 0:
            reduction = vest.get("damage_reduction", 0.33)
            absorbed = min(damage * reduction, vest.get("durability", 0.0))
            final_dmg = max(1.0, damage - absorbed)
            vest["durability"] = max(0.0, vest["durability"] - absorbed)
            if vest["durability"] <= 0.0:
                victim.vest = None

        prev_hp = getattr(victim, "hp", 200.0)
        new_hp = max(0.0, prev_hp - final_dmg)
        victim.hp = new_hp
        is_killed = (new_hp <= 0.0)

        kill_entry = None
        if is_killed:
            victim.is_alive = False
            kill_entry = {
                "attacker_id": getattr(attacker, "player_id", "unknown") if attacker else None,
                "attacker_name": getattr(attacker, "nickname", "Player") if attacker else "World",
                "victim_id": getattr(victim, "player_id", "unknown"),
                "victim_name": getattr(victim, "nickname", "Bot"),
                "weapon": source,
                "is_headshot": is_headshot,
                "timestamp": time.time()
            }
            self.kill_feed.append(kill_entry)
            if attacker and hasattr(attacker, "kills"):
                attacker.kills += 1

        if attacker and hasattr(attacker, "damage_dealt"):
            attacker.damage_dealt += final_dmg

        return {
            "hit": True,
            "target_type": "PLAYER",
            "victim_id": getattr(victim, "player_id", None),
            "damage_dealt": round(final_dmg, 1),
            "is_headshot": is_headshot,
            "victim_hp_remaining": round(new_hp, 1),
            "is_killed": is_killed,
            "kill_feed_entry": kill_entry
        }

    def process_shot(self, shooter: Any, victim: Any, weapon_name: str,
                     target_part: str = BodyPart.CHEST) -> Dict[str, Any]:
        """
        Execute an authoritative weapon shot:
        1. Range & line-of-sight validation
        2. Gloo Wall obstruction check (intercepts bullets)
        3. Accurate damage computation with armor degradation
        4. Victim HP deduction, knockdown, and kill-feed broadcast
        """
        sx, sy, sz = getattr(shooter, "x", 0.0), getattr(shooter, "y", 0.0), getattr(shooter, "z", 0.0)
        vx, vy, vz = getattr(victim, "x", 0.0), getattr(victim, "y", 0.0), getattr(victim, "z", 0.0)
        
        distance = math.hypot(vx - sx, vz - sz)
        wep = WEAPON_REGISTRY.get(weapon_name, WEAPON_REGISTRY["M4A1"])

        # Check maximum effective weapon range
        if distance > wep.get("effective_range", 70.0) * 1.5:
            return {"hit": False, "reason": "OUT_OF_RANGE", "distance": distance}

        # Check Gloo Wall interception
        for wid, wall in self.gloo_walls.items():
            if wall.intersects_ray(sx, sz, vx, vz):
                # Bullet hit gloo wall instead of player!
                wall_destroyed = wall.take_damage(wep["base_damage"])
                return {
                    "hit": True,
                    "target_type": "GLOO_WALL",
                    "wall_id": wid,
                    "damage_dealt": wep["base_damage"],
                    "wall_destroyed": wall_destroyed,
                    "wall_hp_remaining": wall.hp
                }

        # Authoritative damage calculation
        vest = getattr(victim, "vest", None)
        helmet = getattr(victim, "helmet", None)

        final_dmg, vest_loss, helmet_loss, is_headshot = DamageCalculator.calculate_shot_damage(
            weapon_name, distance, target_part, vest=vest, helmet=helmet
        )

        # Apply durability loss to gear
        if vest and vest_loss > 0:
            vest["durability"] = max(0.0, vest.get("durability", 0.0) - vest_loss)
            if vest["durability"] <= 0.0:
                victim.vest = None  # Broken vest

        if helmet and helmet_loss > 0:
            helmet["durability"] = max(0.0, helmet.get("durability", 0.0) - helmet_loss)
            if helmet["durability"] <= 0.0:
                victim.helmet = None  # Broken helmet

        # Deduct Victim HP
        prev_hp = getattr(victim, "hp", 200.0)
        new_hp = max(0.0, prev_hp - final_dmg)
        victim.hp = new_hp

        is_killed = (new_hp <= 0.0)
        kill_entry = None

        if is_killed:
            victim.is_alive = False
            kill_entry = {
                "attacker_id": getattr(shooter, "player_id", "unknown"),
                "attacker_name": getattr(shooter, "nickname", "Player"),
                "victim_id": getattr(victim, "player_id", "unknown"),
                "victim_name": getattr(victim, "nickname", "Bot"),
                "weapon": weapon_name,
                "is_headshot": is_headshot,
                "timestamp": time.time()
            }
            self.kill_feed.append(kill_entry)

        return {
            "hit": True,
            "target_type": "PLAYER",
            "victim_id": getattr(victim, "player_id", None),
            "damage_dealt": final_dmg,
            "is_headshot": is_headshot,
            "body_part": target_part,
            "distance": round(distance, 1),
            "victim_hp_remaining": new_hp,
            "is_killed": is_killed,
            "kill_feed_entry": kill_entry
        }
