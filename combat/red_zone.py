"""
Authoritative Red Zone Artillery Bombardment Engine for Free Fire 1.39.
Simulates warning sirens, red circle danger zones, randomized mortar strikes,
outdoor blast damage, and building shelter checks.
"""

import math
import random
import time
from typing import Dict, Any, List, Optional, Tuple

from .world_constants import BERMUDA_LANDMARKS

class RedZoneState:
    INACTIVE = "INACTIVE"
    WARNING = "WARNING"         # Red circle displayed on minimap, sirens active
    BOMBARDING = "BOMBARDING"   # Mortar shells detonating inside zone

class RedZoneManager:
    """Authoritative server-side artillery bombardment simulation."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            
        self.state: str = RedZoneState.INACTIVE
        self.center_x: float = 0.0
        self.center_z: float = 0.0
        self.radius: float = 110.0
        
        self.warning_duration: float = 30.0     # 30 seconds siren warning
        self.bombard_duration: float = 15.0     # 15 seconds active bombing
        self.cooldown_duration: float = 75.0    # Time between red zones
        
        self.timer: float = 45.0                # Initial delay before 1st red zone
        self.shell_interval: float = 1.2        # Shell every 1.2s
        self.shell_timer: float = 0.0
        self.blast_radius: float = 5.5          # Lethal radius
        self.blast_damage: float = 180.0        # High lethal explosive damage

    def trigger_red_zone(self, target_x: Optional[float] = None, target_z: Optional[float] = None) -> None:
        """Manually trigger a red zone centered on coordinates or a random Bermuda landmark."""
        if target_x is None or target_z is None:
            landmark = random.choice(list(BERMUDA_LANDMARKS.values()))
            target_x = landmark["x"] + random.uniform(-25.0, 25.0)
            target_z = landmark["z"] + random.uniform(-25.0, 25.0)

        self.center_x = round(target_x, 2)
        self.center_z = round(target_z, 2)
        self.radius = random.uniform(95.0, 125.0)
        self.state = RedZoneState.WARNING
        self.timer = self.warning_duration
        self.shell_timer = 0.0

    def update(self, delta_time: float, players: Dict[str, Any], safe_x: float = 0.0, safe_z: float = 0.0, safe_r: float = 600.0) -> List[Dict[str, Any]]:
        """Advance red zone lifecycle and process artillery bombardments."""
        events: List[Dict[str, Any]] = []
        self.timer -= delta_time

        if self.state == RedZoneState.INACTIVE:
            if self.timer <= 0.0:
                # Pick a spot inside current safe zone
                angle = random.uniform(0.0, 2.0 * math.pi)
                dist = random.uniform(0.0, max(10.0, safe_r * 0.6))
                rx = safe_x + dist * math.cos(angle)
                rz = safe_z + dist * math.sin(angle)
                self.trigger_red_zone(rx, rz)
                events.append({
                    "event": "RED_ZONE_WARNING_START",
                    "x": self.center_x,
                    "z": self.center_z,
                    "radius": self.radius,
                    "duration": self.warning_duration
                })

        elif self.state == RedZoneState.WARNING:
            if self.timer <= 0.0:
                # Transition to active bombardment
                self.state = RedZoneState.BOMBARDING
                self.timer = self.bombard_duration
                events.append({
                    "event": "RED_ZONE_BOMBARDMENT_START",
                    "x": self.center_x,
                    "z": self.center_z,
                    "radius": self.radius
                })

        elif self.state == RedZoneState.BOMBARDING:
            self.shell_timer += delta_time
            if self.shell_timer >= self.shell_interval:
                self.shell_timer = 0.0
                
                # Detonate random mortar shell inside danger circle
                angle = random.uniform(0.0, 2.0 * math.pi)
                dist = random.uniform(0.0, self.radius)
                blast_x = self.center_x + dist * math.cos(angle)
                blast_z = self.center_z + dist * math.sin(angle)
                
                shell_event = {
                    "event": "RED_ZONE_SHELL_EXPLODE",
                    "x": blast_x,
                    "z": blast_z,
                    "blast_radius": self.blast_radius
                }
                events.append(shell_event)
                
                # Check player proximity to explosion point
                for pid, p in players.items():
                    if not getattr(p, "is_alive", True):
                        continue
                    px = getattr(p, "x", 0.0)
                    pz = getattr(p, "z", 0.0)
                    is_sheltered = getattr(p, "is_indoors", False)
                    
                    # Buildings/shelters protect from artillery
                    if is_sheltered:
                        continue
                        
                    hit_dist = math.hypot(px - blast_x, pz - blast_z)
                    if hit_dist <= self.blast_radius:
                        # Falloff based on blast center
                        falloff = max(0.4, 1.0 - (hit_dist / self.blast_radius))
                        dmg = self.blast_damage * falloff
                        
                        if hasattr(p, "take_damage"):
                            dmg_res = p.take_damage(dmg, source="artillery", attacker_id=None)
                        else:
                            p["hp"] = max(0.0, p.get("hp", 200.0) - dmg)
                            dmg_res = {
                                "victim_id": pid,
                                "damage": dmg,
                                "source": "artillery",
                                "hp_remaining": p["hp"],
                                "is_dead": p["hp"] <= 0.0
                            }
                        events.append(dmg_res)

            if self.timer <= 0.0:
                # Bombardment complete, return to cooldown
                self.state = RedZoneState.INACTIVE
                self.timer = self.cooldown_duration
                events.append({
                    "event": "RED_ZONE_ENDED",
                    "x": self.center_x,
                    "z": self.center_z
                })

        return events

    def get_sync_data(self) -> Dict[str, Any]:
        """Serialize red zone status for network broadcast."""
        return {
            "active": self.state != RedZoneState.INACTIVE,
            "state": self.state,
            "x": self.center_x,
            "z": self.center_z,
            "radius": self.radius,
            "time_remaining": max(0.0, self.timer)
        }
