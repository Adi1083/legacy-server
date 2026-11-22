"""
Authoritative Ground Item Loot Spawner & Pickup Manager for Free Fire 1.39 Bermuda map.
Populates landmarks and compounds with authentic weapons, ammo, armor, medkits, and gloo walls.
"""

import math
import random
from typing import Dict, Any, List, Optional, Tuple, Set

from .world_constants import (
    BERMUDA_LANDMARKS, WEAPON_REGISTRY, GEAR_REGISTRY, CONSUMABLES_REGISTRY,
    WeaponCategory, AmmoType
)

class GroundItem:
    """An authoritative item entity positioned on the terrain."""

    def __init__(self, pickup_id: int, item_type: str, item_id: int, name: str,
                 category: str, x: float, y: float, z: float, count: int = 1,
                 extra_data: Optional[Dict[str, Any]] = None):
        self.pickup_id: int = pickup_id
        self.item_type: str = item_type  # "weapon", "gear", "consumable", "ammo"
        self.item_id: int = item_id
        self.name: str = name
        self.category: str = category
        self.x: float = round(x, 2)
        self.y: float = round(y, 2)
        self.z: float = round(z, 2)
        self.count: int = count
        self.extra_data: Dict[str, Any] = extra_data or {}
        self.is_collected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pickup_id": self.pickup_id,
            "item_type": self.item_type,
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "pos": {"x": self.x, "y": self.y, "z": self.z},
            "count": self.count,
            "extra": self.extra_data
        }


class LootSpawner:
    """Authoritative loot population and spatial query manager for Bermuda."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

        self.next_pickup_id: int = 200001
        self.items: Dict[int, GroundItem] = {}
        
        # Spatial Grid: cell size 50m for rapid O(1) proximity lookups
        self.grid_cell_size: float = 50.0
        self.spatial_grid: Dict[Tuple[int, int], List[int]] = {}

    def _grid_coord(self, x: float, z: float) -> Tuple[int, int]:
        return (int(x // self.grid_cell_size), int(z // self.grid_cell_size))

    def _add_to_grid(self, item: GroundItem) -> None:
        key = self._grid_coord(item.x, item.z)
        if key not in self.spatial_grid:
            self.spatial_grid[key] = []
        self.spatial_grid[key].append(item.pickup_id)

    def _remove_from_grid(self, item: GroundItem) -> None:
        key = self._grid_coord(item.x, item.z)
        if key in self.spatial_grid and item.pickup_id in self.spatial_grid[key]:
            self.spatial_grid[key].remove(item.pickup_id)

    def populate_bermuda_loot(self) -> int:
        """Spawn authoritative initial match loot across all Bermuda landmarks."""
        total_spawned = 0

        # Weighted weapon list
        spawnable_weapons = [w for w in WEAPON_REGISTRY.values() if w.get("spawn_weight", 0) > 0]
        weapon_weights = [w["spawn_weight"] for w in spawnable_weapons]

        # Weighted gear list
        spawnable_gear = [g for g in GEAR_REGISTRY.values() if g.get("spawn_weight", 0) > 0]
        gear_weights = [g["spawn_weight"] for g in spawnable_gear]

        # Weighted consumables
        spawnable_consumables = [c for c in CONSUMABLES_REGISTRY.values() if c.get("spawn_weight", 0) > 0]
        consumable_weights = [c["spawn_weight"] for c in spawnable_consumables]

        for lm_name, lm in BERMUDA_LANDMARKS.items():
            cx = lm["x"]
            cz = lm["z"]
            cy = lm["y"]
            tier = lm.get("tier", 2)
            radius = lm.get("radius", 100.0)
            
            # Density based on tier
            spots_count = int(radius * (0.25 if tier == 3 else (0.18 if tier == 2 else 0.12)))

            for _ in range(spots_count):
                # Cluster offset within town
                angle = random.uniform(0.0, 2.0 * math.pi)
                dist = random.uniform(5.0, radius * 0.95)
                ix = cx + dist * math.cos(angle)
                iz = cz + dist * math.sin(angle)
                iy = cy + random.uniform(0.0, 3.0)

                # Determine spawn roll
                roll = random.random()

                if roll < 0.35:
                    # Weapon spawn + paired ammo
                    wep = random.choices(spawnable_weapons, weights=weapon_weights, k=1)[0]
                    w_item = GroundItem(
                        self.next_pickup_id,
                        "weapon",
                        wep["item_id"],
                        wep["name"],
                        wep["category"],
                        ix, iy, iz,
                        count=1,
                        extra_data={"ammo_in_clip": wep["clip_size"], "ammo_type": wep["ammo_type"]}
                    )
                    self.next_pickup_id += 1
                    self.items[w_item.pickup_id] = w_item
                    self._add_to_grid(w_item)
                    total_spawned += 1

                    # Spawn paired ammo nearby
                    if wep["ammo_type"] != AmmoType.NONE:
                        ammo_name = {
                            AmmoType.AR: "Ammo_AR",
                            AmmoType.SMG: "Ammo_SMG",
                            AmmoType.SG: "Ammo_SG",
                            AmmoType.SNIPER: "Ammo_Sniper"
                        }.get(wep["ammo_type"])
                        if ammo_name and ammo_name in CONSUMABLES_REGISTRY:
                            ammo_info = CONSUMABLES_REGISTRY[ammo_name]
                            a_item = GroundItem(
                                self.next_pickup_id,
                                "ammo",
                                ammo_info["item_id"],
                                ammo_info["name"],
                                "AMMO",
                                ix + random.uniform(-1.0, 1.0), iy, iz + random.uniform(-1.0, 1.0),
                                count=ammo_info["count"]
                            )
                            self.next_pickup_id += 1
                            self.items[a_item.pickup_id] = a_item
                            self._add_to_grid(a_item)
                            total_spawned += 1

                elif roll < 0.60:
                    # Armor or Backpack spawn
                    gear = random.choices(spawnable_gear, weights=gear_weights, k=1)[0]
                    g_item = GroundItem(
                        self.next_pickup_id,
                        "gear",
                        gear["item_id"],
                        gear["name"],
                        gear["slot"].upper(),
                        ix, iy, iz,
                        count=1,
                        extra_data=gear.copy()
                    )
                    self.next_pickup_id += 1
                    self.items[g_item.pickup_id] = g_item
                    self._add_to_grid(g_item)
                    total_spawned += 1

                else:
                    # Consumables / Throwables (Medkits, Gloo Walls, Grenades, Ammo)
                    cons = random.choices(spawnable_consumables, weights=consumable_weights, k=1)[0]
                    c_item = GroundItem(
                        self.next_pickup_id,
                        "consumable",
                        cons["item_id"],
                        cons["name"],
                        "UTILITY",
                        ix, iy, iz,
                        count=cons.get("count", 1),
                        extra_data=cons.copy()
                    )
                    self.next_pickup_id += 1
                    self.items[c_item.pickup_id] = c_item
                    self._add_to_grid(c_item)
                    total_spawned += 1

        # Populate Waiting Island practice loot
        total_spawned += self.populate_waiting_island_loot()
        return total_spawned

    def populate_waiting_island_loot(self, center: Tuple[float, float, float] = (-500.0, 10.0, 800.0), radius: float = 40.0) -> int:
        """
        Populate authentic Bermuda Waiting Island pre-match practice loot:
        Spawns melee weapons, practice firearms, ammo, and interactive easter egg items
        organized onto dedicated pedestal stations around the spawn island plaza.
        """
        cx, cy, cz = center
        spawned = 0

        pedestal_stations = [
            # North Pedestal Station (Assault Rifles & AR Ammo)
            {"name": "M4A1", "type": "weapon", "cfg": WEAPON_REGISTRY.get("M4A1", {}), "pos": (cx - 8.0, cy, cz + 15.0), "pedestal": "AR_Station"},
            {"name": "AK47", "type": "weapon", "cfg": WEAPON_REGISTRY.get("AK47", {}), "pos": (cx - 4.0, cy, cz + 15.0), "pedestal": "AR_Station"},
            {"name": "SCAR", "type": "weapon", "cfg": WEAPON_REGISTRY.get("SCAR", {}), "pos": (cx, cy, cz + 15.0), "pedestal": "AR_Station"},
            {"name": "Ammo_AR", "type": "ammo", "cfg": CONSUMABLES_REGISTRY.get("Ammo_AR", {}), "pos": (cx + 4.0, cy, cz + 15.0), "pedestal": "AR_Station"},
            {"name": "Ammo_AR", "type": "ammo", "cfg": CONSUMABLES_REGISTRY.get("Ammo_AR", {}), "pos": (cx + 8.0, cy, cz + 15.0), "pedestal": "AR_Station"},

            # South Pedestal Station (Submachine Guns & SMG Ammo)
            {"name": "MP40", "type": "weapon", "cfg": WEAPON_REGISTRY.get("MP40", {}), "pos": (cx - 6.0, cy, cz - 15.0), "pedestal": "SMG_Station"},
            {"name": "UMP", "type": "weapon", "cfg": WEAPON_REGISTRY.get("UMP", {}), "pos": (cx - 2.0, cy, cz - 15.0), "pedestal": "SMG_Station"},
            {"name": "MP5", "type": "weapon", "cfg": WEAPON_REGISTRY.get("MP5", {}), "pos": (cx + 2.0, cy, cz - 15.0), "pedestal": "SMG_Station"},
            {"name": "Ammo_SMG", "type": "ammo", "cfg": CONSUMABLES_REGISTRY.get("Ammo_SMG", {}), "pos": (cx + 6.0, cy, cz - 15.0), "pedestal": "SMG_Station"},

            # East Pedestal Station (Shotguns, Snipers & Ammo)
            {"name": "M1014", "type": "weapon", "cfg": WEAPON_REGISTRY.get("M1014", {}), "pos": (cx + 15.0, cy, cz - 5.0), "pedestal": "Shotgun_Station"},
            {"name": "SPAS12", "type": "weapon", "cfg": WEAPON_REGISTRY.get("SPAS12", {}), "pos": (cx + 15.0, cy, cz), "pedestal": "Shotgun_Station"},
            {"name": "AWM", "type": "weapon", "cfg": WEAPON_REGISTRY.get("AWM", {}), "pos": (cx + 15.0, cy, cz + 5.0), "pedestal": "Sniper_Station"},
            {"name": "Ammo_SG", "type": "ammo", "cfg": CONSUMABLES_REGISTRY.get("Ammo_SG", {}), "pos": (cx + 18.0, cy, cz - 3.0), "pedestal": "Shotgun_Station"},
            {"name": "Ammo_Sniper", "type": "ammo", "cfg": CONSUMABLES_REGISTRY.get("Ammo_Sniper", {}), "pos": (cx + 18.0, cy, cz + 3.0), "pedestal": "Sniper_Station"},

            # West Pedestal Station (Melee Weapons, Gloo Wall & Medkit)
            {"name": "Pan", "type": "weapon", "cfg": WEAPON_REGISTRY.get("Pan", {}), "pos": (cx - 15.0, cy, cz - 6.0), "pedestal": "Melee_Station"},
            {"name": "Katana", "type": "weapon", "cfg": WEAPON_REGISTRY.get("Katana", {}), "pos": (cx - 15.0, cy, cz - 2.0), "pedestal": "Melee_Station"},
            {"name": "Bat", "type": "weapon", "cfg": WEAPON_REGISTRY.get("Bat", {}), "pos": (cx - 15.0, cy, cz + 2.0), "pedestal": "Melee_Station"},
            {"name": "Machete", "type": "weapon", "cfg": WEAPON_REGISTRY.get("Machete", {}), "pos": (cx - 15.0, cy, cz + 6.0), "pedestal": "Melee_Station"},
            {"name": "GlooWall", "type": "consumable", "cfg": CONSUMABLES_REGISTRY.get("GlooWall", CONSUMABLES_REGISTRY.get("Gloo_Wall", {})), "pos": (cx - 18.0, cy, cz - 2.0), "pedestal": "Defense_Station"},
            {"name": "Medkit", "type": "consumable", "cfg": CONSUMABLES_REGISTRY.get("Medkit", {}), "pos": (cx - 18.0, cy, cz + 2.0), "pedestal": "Defense_Station"},

            # Interactive Easter Egg Station (WaitingIslandGiantEasterEggHp = 1000)
            {"name": "GiantEasterEgg", "type": "easter_egg", "cfg": {"item_id": 999000001, "name": "GiantEasterEgg", "category": "EASTER_EGG", "hp": 1000.0, "count": 1}, "pos": (cx, cy, cz - 20.0), "pedestal": "EasterEgg_Plaza"}
        ]

        for item in pedestal_stations:
            cfg = item.get("cfg", {})
            if not cfg:
                continue
            ix, iy, iz = item["pos"]
            itype = item["type"]
            name = item["name"]

            item_id = cfg.get("item_id", 907000008)
            cat = str(cfg.get("category", cfg.get("slot", "MELEE"))).upper()
            extra = {"is_practice": True, "pedestal_station": item.get("pedestal", "Plaza")}
            if itype == "weapon":
                extra.update({"ammo_in_clip": cfg.get("clip_size", 30), "ammo_type": cfg.get("ammo_type", "ammo_ar")})
            elif itype == "ammo":
                extra.update({"ammo_type": cfg.get("ammo_type", "ammo_ar")})
            elif itype == "consumable":
                extra.update(cfg.copy())
            elif itype == "easter_egg":
                extra.update({"hp": cfg.get("hp", 1000.0), "max_hp": cfg.get("hp", 1000.0)})

            g_item = GroundItem(
                pickup_id=self.next_pickup_id,
                item_type=itype,
                item_id=item_id,
                name=name,
                category=cat,
                x=ix,
                y=iy,
                z=iz,
                count=cfg.get("count", 1),
                extra_data=extra
            )
            self.next_pickup_id += 1
            self.items[g_item.pickup_id] = g_item
            self._add_to_grid(g_item)
            spawned += 1

        return spawned

    def get_items_near(self, x: float, z: float, radius: float = 3.0) -> List[GroundItem]:
        """Query all ground items within pickup interaction radius of coordinates."""
        results: List[GroundItem] = []
        cell_range = int(math.ceil(radius / self.grid_cell_size)) + 1
        cx, cz = self._grid_coord(x, z)

        for gx in range(cx - cell_range, cx + cell_range + 1):
            for gz in range(cz - cell_range, cz + cell_range + 1):
                pids = self.spatial_grid.get((gx, gz), [])
                for pid in pids:
                    item = self.items.get(pid)
                    if item and not item.is_collected:
                        dist = math.hypot(item.x - x, item.z - z)
                        if dist <= radius:
                            results.append(item)
        return results

    def pickup_item(self, pickup_id: int, player_x: float, player_z: float, max_dist: float = 3.5) -> Optional[GroundItem]:
        """
        Authoritatively validate and collect a ground item.
        Checks distance <= max_dist and item availability.
        """
        item = self.items.get(pickup_id)
        if not item or item.is_collected:
            return None

        dist = math.hypot(item.x - player_x, item.z - player_z)
        if dist > max_dist:
            return None

        # Collect
        item.is_collected = True
        self._remove_from_grid(item)
        del self.items[pickup_id]
        return item

    def drop_item(self, item_type: str, item_id: int, name: str, category: str,
                  x: float, y: float, z: float, count: int = 1,
                  extra_data: Optional[Dict[str, Any]] = None) -> GroundItem:
        """Create a new ground item when a player drops loot from inventory."""
        item = GroundItem(
            self.next_pickup_id,
            item_type,
            item_id,
            name,
            category,
            x, y, z,
            count=count,
            extra_data=extra_data
        )
        self.next_pickup_id += 1
        self.items[item.pickup_id] = item
        self._add_to_grid(item)
        return item
