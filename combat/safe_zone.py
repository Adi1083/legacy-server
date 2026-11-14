"""
Authoritative Safe Zone & Poison Zone Simulation Engine for Free Fire 1.39.
Simulates white circle countdowns, blue poison ring shrinking, and radiation tick damage.
"""

import math
import random
import time
from typing import Dict, Any, List, Optional, Tuple

from .world_constants import SAFE_ZONE_PHASES, MAP_MIN_X, MAP_MAX_X, MAP_MIN_Z, MAP_MAX_Z

class ZoneState:
    WAITING = "WAITING"     # Pre-shrink countdown, white circle indicates destination
    SHRINKING = "SHRINKING" # Poison ring moving inward towards safe circle
    COMPLETED = "COMPLETED" # Zone shrunk completely to zero

class SafeZoneManager:
    """Authoritative server-side Safe Zone & Poison Radiation simulation."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.phase_idx: int = 0
        self.phase_count: int = len(SAFE_ZONE_PHASES)
        self.state: str = ZoneState.WAITING
        self.timer: float = 0.0
        
        # Center coordinates
        self.blue_center_x: float = 0.0
        self.blue_center_z: float = 0.0
        self.blue_radius: float = SAFE_ZONE_PHASES[0]["start_radius"]
        
        # Initial phase setup
        self._setup_initial_phase()
        
        # Damage accumulation timer (ticks every 1.0s)
        self.damage_tick_acc: float = 0.0
        self.damage_interval: float = 1.0  # 1 second damage tick

    def _setup_initial_phase(self) -> None:
        """Initialize Phase 1 white and blue zone geometry."""
        cfg = SAFE_ZONE_PHASES[0]
        self.phase_idx = 0
        self.state = ZoneState.WAITING
        self.timer = cfg["wait_duration"]
        
        # Blue circle starts at the map perimeter
        self.blue_center_x = 0.0
        self.blue_center_z = 0.0
        self.blue_radius = cfg["start_radius"]
        self.blue_start_radius = self.blue_radius
        self.blue_start_center_x = self.blue_center_x
        self.blue_start_center_z = self.blue_center_z
        
        # White target circle generated inside the current blue radius
        self.white_radius = cfg["target_radius"]
        self._generate_next_white_circle(self.blue_center_x, self.blue_center_z, self.blue_radius, self.white_radius)
        self.current_dps = cfg["dps"]

    def _generate_next_white_circle(self, parent_x: float, parent_z: float, parent_r: float, target_r: float) -> None:
        """Generate a random new safe center guaranteed to fit inside current safe bounds."""
        max_dist = max(0.0, parent_r - target_r)
        # Weight slightly toward the center so circle stays on the island
        dist = random.uniform(0.0, max_dist) * random.uniform(0.5, 1.0)
        angle = random.uniform(0.0, 2.0 * math.pi)
        
        new_x = parent_x + dist * math.cos(angle)
        new_z = parent_z + dist * math.sin(angle)
        
        # Clamp to Bermuda map extents with buffer
        new_x = max(MAP_MIN_X + target_r, min(MAP_MAX_X - target_r, new_x))
        new_z = max(MAP_MIN_Z + target_r, min(MAP_MAX_Z - target_r, new_z))
        
        self.white_center_x = round(new_x, 2)
        self.white_center_z = round(new_z, 2)

    def update(self, delta_time: float, players: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Advance safe zone simulation by delta_time.
        Applies authoritative poison tick damage to any player outside the blue circle.
        Returns list of damage events generated this tick.
        """
        if self.state == ZoneState.COMPLETED:
            return self._apply_poison_damage(delta_time, players)

        self.timer -= delta_time
        cfg = SAFE_ZONE_PHASES[self.phase_idx]

        if self.state == ZoneState.WAITING:
            if self.timer <= 0.0:
                # Transition from WAITING to SHRINKING
                self.state = ZoneState.SHRINKING
                self.timer = cfg["shrink_duration"]
                self.blue_start_center_x = self.blue_center_x
                self.blue_start_center_z = self.blue_center_z
                self.blue_start_radius = self.blue_radius

        elif self.state == ZoneState.SHRINKING:
            # Interpolate blue circle position and radius towards white circle
            shrink_dur = cfg["shrink_duration"]
            t = 1.0 - max(0.0, self.timer / shrink_dur)
            t = min(1.0, max(0.0, t))
            
            # Smooth interpolation
            self.blue_radius = self.blue_start_radius + (self.white_radius - self.blue_start_radius) * t
            self.blue_center_x = self.blue_start_center_x + (self.white_center_x - self.blue_start_center_x) * t
            self.blue_center_z = self.blue_start_center_z + (self.white_center_z - self.blue_start_center_z) * t
            
            if self.timer <= 0.0:
                # Shrink phase complete
                self.blue_radius = self.white_radius
                self.blue_center_x = self.white_center_x
                self.blue_center_z = self.white_center_z
                
                # Advance to next phase if available
                if self.phase_idx + 1 < self.phase_count:
                    self.phase_idx += 1
                    next_cfg = SAFE_ZONE_PHASES[self.phase_idx]
                    self.state = ZoneState.WAITING
                    self.timer = next_cfg["wait_duration"]
                    self.current_dps = next_cfg["dps"]
                    
                    self.white_radius = next_cfg["target_radius"]
                    self._generate_next_white_circle(
                        self.blue_center_x, self.blue_center_z, self.blue_radius, self.white_radius
                    )
                else:
                    self.state = ZoneState.COMPLETED
                    self.current_dps = 15.0  # Final endgame poison DPS

        # Apply radiation poison damage tick
        return self._apply_poison_damage(delta_time, players)

    def _apply_poison_damage(self, delta_time: float, players: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate and apply authoritative poison radiation damage to all players outside the blue circle."""
        damage_events: List[Dict[str, Any]] = []
        self.damage_tick_acc += delta_time
        
        if self.damage_tick_acc < self.damage_interval:
            return damage_events

        # Damage tick fired
        ticks = int(self.damage_tick_acc / self.damage_interval)
        self.damage_tick_acc -= ticks * self.damage_interval
        tick_damage = self.current_dps * self.damage_interval * ticks

        for pid, player in players.items():
            # Check if player is alive
            if not getattr(player, "is_alive", True):
                continue
                
            px = getattr(player, "x", 0.0)
            pz = getattr(player, "z", 0.0)
            
            dist = math.hypot(px - self.blue_center_x, pz - self.blue_center_z)
            if dist > self.blue_radius:
                # Player is inside poison radiation zone!
                damage_taken = tick_damage
                if hasattr(player, "take_damage"):
                    event = player.take_damage(damage_taken, source="poison_zone", attacker_id=None)
                else:
                    # Generic dict structure
                    player["hp"] = max(0.0, player.get("hp", 200.0) - damage_taken)
                    event = {
                        "victim_id": pid,
                        "attacker_id": None,
                        "damage": damage_taken,
                        "is_headshot": False,
                        "source": "poison_zone",
                        "hp_remaining": player["hp"],
                        "is_dead": player["hp"] <= 0.0
                    }
                damage_events.append(event)

        return damage_events

    def is_in_safe_zone(self, x: float, z: float) -> bool:
        """Check if position is inside the blue safe area (not taking poison damage)."""
        dist = math.hypot(x - self.blue_center_x, z - self.blue_center_z)
        return dist <= self.blue_radius

    def is_in_white_circle(self, x: float, z: float) -> bool:
        """Check if position is already inside the next white safe circle."""
        dist = math.hypot(x - self.white_center_x, z - self.white_center_z)
        return dist <= self.white_radius

    def get_sync_packet_data(self) -> Dict[str, Any]:
        """
        Returns serialized zone definition matching Free Fire 1.39 ZoneDefinition:
        OuterCenter, OuterRadius, InnerCenter, InnerRadius, TimeSpanType, StartTime, EndTime.
        """
        return {
            "stage_id": self.phase_idx + 1,
            "state": self.state,
            "outer_center": {"x": self.blue_center_x, "y": 0.0, "z": self.blue_center_z},
            "outer_radius": self.blue_radius,
            "inner_center": {"x": self.white_center_x, "y": 0.0, "z": self.white_center_z},
            "inner_radius": self.white_radius,
            "time_remaining": max(0.0, self.timer),
            "dps": self.current_dps,
        }
