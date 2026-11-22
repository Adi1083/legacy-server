"""
World constants, weapon definitions, item catalogs, and Bermuda map landmarks
for Free Fire 1.39 Authoritative Combat & World Engine.
"""

from typing import Dict, Any, List, Tuple

# ---------------------------------------------------------------------------
# Bermuda Map Geometry & Coordinates (centered at 0, 0 or 1000, 1000)
# Coordinate system: X (East-West), Y (Altitude), Z (North-South)
# ---------------------------------------------------------------------------
MAP_MIN_X = -1000.0
MAP_MAX_X = 1000.0
MAP_MIN_Z = -1000.0
MAP_MAX_Z = 1000.0
MAP_CENTER_X = 0.0
MAP_CENTER_Z = 0.0
MAP_SIZE = 2000.0

# Bermuda Map Key Hot-drop Towns & Landmark Spawns
BERMUDA_LANDMARKS: Dict[str, Dict[str, Any]] = {
    "Peak": {
        "x": 0.0, "z": 50.0, "y": 70.0, "radius": 120.0, "tier": 3,
        "description": "High plateau central compound with prime high-tier loot"
    },
    "Bimasakti_Strip": {
        "x": 40.0, "z": -120.0, "y": 30.0, "radius": 140.0, "tier": 3,
        "description": "Central road and tower complex below Peak"
    },
    "Clock_Tower": {
        "x": -350.0, "z": -80.0, "y": 45.0, "radius": 110.0, "tier": 3,
        "description": "Western fortress with multi-story buildings and iconic clock tower"
    },
    "Factory": {
        "x": -180.0, "z": -320.0, "y": 25.0, "radius": 130.0, "tier": 3,
        "description": "Industrial roof and warehouse complex, heavy early combat"
    },
    "Pochinok": {
        "x": -30.0, "z": -400.0, "y": 20.0, "radius": 130.0, "tier": 3,
        "description": "Dense southern village with extensive loot in residential compounds"
    },
    "Mill": {
        "x": 480.0, "z": 450.0, "y": 65.0, "radius": 120.0, "tier": 3,
        "description": "North-eastern mountain mill with tier-3 sniper & military gear"
    },
    "Shipyard": {
        "x": 300.0, "z": 620.0, "y": 15.0, "radius": 150.0, "tier": 3,
        "description": "Northern container terminal and dry docks"
    },
    "Mars_Electric": {
        "x": 40.0, "z": -750.0, "y": 15.0, "radius": 160.0, "tier": 2,
        "description": "Far southern powerplant with cooling towers and warehouse silos"
    },
    "Cape_Town": {
        "x": 680.0, "z": -420.0, "y": 18.0, "radius": 140.0, "tier": 2,
        "description": "South-eastern coastal suburban villas and compounds"
    },
    "Katulistiwa": {
        "x": -150.0, "z": 200.0, "y": 35.0, "radius": 100.0, "tier": 2,
        "description": "Lakeside settlement west of Bimasakti"
    },
    "Hangar": {
        "x": -520.0, "z": -200.0, "y": 20.0, "radius": 140.0, "tier": 2,
        "description": "Aircraft hangars and airfields southwest of Clock Tower"
    },
    "Rim_Nam_Village": {
        "x": -720.0, "z": -400.0, "y": 10.0, "radius": 110.0, "tier": 2,
        "description": "Stilt house fishing village on south-western coast"
    },
    "Graveyard": {
        "x": 80.0, "z": 420.0, "y": 30.0, "radius": 110.0, "tier": 2,
        "description": "Northern cemetery and manor estate"
    },
    "Plantation": {
        "x": -280.0, "z": 380.0, "y": 25.0, "radius": 120.0, "tier": 2,
        "description": "Agricultural greenhouses and farming barracks"
    },
    "Kota_Tua": {
        "x": 260.0, "z": -260.0, "y": 20.0, "radius": 110.0, "tier": 2,
        "description": "Old town ruins east of Pochinok"
    },
    "Sentosa": {
        "x": 750.0, "z": -100.0, "y": 15.0, "radius": 180.0, "tier": 3,
        "description": "Island estate across southern bridge with military grade loot"
    },
    "Riverside": {
        "x": -100.0, "z": 480.0, "y": 15.0, "radius": 100.0, "tier": 1,
        "description": "River bridge and cottage clusters"
    },
    "Waiting_Island": {
        "x": -500.0, "z": 800.0, "y": 10.0, "radius": 60.0, "tier": 1,
        "description": "Bermuda Waiting Island pre-match gathering zone and obstacle course"
    },
}

# Bermuda Waiting Island Authentic Spawn Zone Constants
BERMUDA_WAITING_ISLAND_CENTER: Tuple[float, float, float] = (-500.0, 10.0, 800.0)
BERMUDA_WAITING_ISLAND_RADIUS: float = 60.0
BERMUDA_WAITING_ISLAND_SPAWN_RADIUS: float = 25.0

# ---------------------------------------------------------------------------
# Weapon Types, Categories & Baseline Performance
# ---------------------------------------------------------------------------
class BodyPart:
    HEAD = "HEAD"
    CHEST = "CHEST"
    BODY = "CHEST"
    STOMACH = "STOMACH"
    LIMBS = "LIMBS"

class WeaponCategory:
    AR = "AR"
    SMG = "SMG"
    SNIPER = "SNIPER"
    SHOTGUN = "SHOTGUN"
    PISTOL = "PISTOL"
    MELEE = "MELEE"
    THROWABLE = "THROWABLE"

class AmmoType:
    AR = "ammo_ar"
    SMG = "ammo_smg"
    SG = "ammo_sg"
    SNIPER = "ammo_sniper"
    NONE = "none"

WEAPON_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Assault Rifles
    "M4A1": {
        "item_id": 907000010,
        "name": "M4A1",
        "category": WeaponCategory.AR,
        "ammo_type": AmmoType.AR,
        "clip_size": 30,
        "reserve_ammo": 60,
        "base_damage": 29.0,
        "headshot_multiplier": 2.5,
        "limb_multiplier": 0.75,
        "fire_rate": 0.105,       # ~9.5 rounds/sec
        "effective_range": 79.0,
        "bullet_speed": 400.0,    # m/s
        "accuracy": 0.82,
        "recoil_bloom": 0.04,
        "damage_falloff_min": 0.70,
        "falloff_start_dist": 45.0,
        "falloff_end_dist": 90.0,
        "spawn_weight": 25,
    },
    "AK47": {
        "item_id": 907000013,
        "name": "AK47",
        "category": WeaponCategory.AR,
        "ammo_type": AmmoType.AR,
        "clip_size": 30,
        "reserve_ammo": 60,
        "base_damage": 38.0,
        "headshot_multiplier": 2.5,
        "limb_multiplier": 0.75,
        "fire_rate": 0.125,       # 8 rounds/sec
        "effective_range": 73.0,
        "bullet_speed": 380.0,
        "accuracy": 0.72,
        "recoil_bloom": 0.07,
        "damage_falloff_min": 0.65,
        "falloff_start_dist": 40.0,
        "falloff_end_dist": 85.0,
        "spawn_weight": 20,
    },
    "SCAR": {
        "item_id": 907000014,
        "name": "SCAR",
        "category": WeaponCategory.AR,
        "ammo_type": AmmoType.AR,
        "clip_size": 30,
        "reserve_ammo": 60,
        "base_damage": 30.0,
        "headshot_multiplier": 2.5,
        "limb_multiplier": 0.75,
        "fire_rate": 0.100,       # 10 rounds/sec
        "effective_range": 68.0,
        "bullet_speed": 390.0,
        "accuracy": 0.85,
        "recoil_bloom": 0.035,
        "damage_falloff_min": 0.70,
        "falloff_start_dist": 35.0,
        "falloff_end_dist": 80.0,
        "spawn_weight": 22,
    },
    "GROZA": {
        "item_id": 907000015,
        "name": "GROZA",
        "category": WeaponCategory.AR,
        "ammo_type": AmmoType.AR,
        "clip_size": 30,
        "reserve_ammo": 60,
        "base_damage": 35.0,
        "headshot_multiplier": 2.5,
        "limb_multiplier": 0.75,
        "fire_rate": 0.102,
        "effective_range": 77.0,
        "bullet_speed": 420.0,
        "accuracy": 0.88,
        "recoil_bloom": 0.03,
        "damage_falloff_min": 0.75,
        "falloff_start_dist": 50.0,
        "falloff_end_dist": 95.0,
        "airdrop_only": True,
        "spawn_weight": 0,
    },
    "M14": {
        "item_id": 907000016,
        "name": "M14",
        "category": WeaponCategory.AR,
        "ammo_type": AmmoType.AR,
        "clip_size": 15,
        "reserve_ammo": 45,
        "base_damage": 76.0,
        "headshot_multiplier": 2.5,
        "limb_multiplier": 0.75,
        "fire_rate": 0.280,       # Semi-auto
        "effective_range": 85.0,
        "bullet_speed": 450.0,
        "accuracy": 0.90,
        "recoil_bloom": 0.08,
        "damage_falloff_min": 0.80,
        "falloff_start_dist": 60.0,
        "falloff_end_dist": 110.0,
        "spawn_weight": 14,
    },
    # Submachine Guns
    "MP40": {
        "item_id": 907000020,
        "name": "MP40",
        "category": WeaponCategory.SMG,
        "ammo_type": AmmoType.SMG,
        "clip_size": 20,
        "reserve_ammo": 60,
        "base_damage": 22.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.80,
        "fire_rate": 0.072,       # 13.8 rounds/sec - fastest in game
        "effective_range": 22.0,
        "bullet_speed": 320.0,
        "accuracy": 0.75,
        "recoil_bloom": 0.05,
        "damage_falloff_min": 0.50,
        "falloff_start_dist": 15.0,
        "falloff_end_dist": 40.0,
        "spawn_weight": 24,
    },
    "UMP": {
        "item_id": 907000021,
        "name": "UMP",
        "category": WeaponCategory.SMG,
        "ammo_type": AmmoType.SMG,
        "clip_size": 30,
        "reserve_ammo": 60,
        "base_damage": 24.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.80,
        "fire_rate": 0.090,
        "effective_range": 32.0,
        "bullet_speed": 340.0,
        "accuracy": 0.80,
        "recoil_bloom": 0.04,
        "damage_falloff_min": 0.55,
        "falloff_start_dist": 20.0,
        "falloff_end_dist": 50.0,
        "spawn_weight": 25,
    },
    "MP5": {
        "item_id": 907000022,
        "name": "MP5",
        "category": WeaponCategory.SMG,
        "ammo_type": AmmoType.SMG,
        "clip_size": 30,
        "reserve_ammo": 60,
        "base_damage": 25.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.80,
        "fire_rate": 0.088,
        "effective_range": 31.0,
        "bullet_speed": 330.0,
        "accuracy": 0.82,
        "recoil_bloom": 0.04,
        "damage_falloff_min": 0.55,
        "falloff_start_dist": 22.0,
        "falloff_end_dist": 52.0,
        "spawn_weight": 22,
    },
    # Snipers
    "AWM": {
        "item_id": 907000005,
        "name": "AWM",
        "category": WeaponCategory.SNIPER,
        "ammo_type": AmmoType.SNIPER,
        "clip_size": 5,
        "reserve_ammo": 15,
        "base_damage": 150.0,
        "headshot_multiplier": 3.0,  # 450 dmg - instant kill through any helmet
        "limb_multiplier": 0.80,
        "fire_rate": 1.25,        # Bolt action
        "effective_range": 91.0,
        "bullet_speed": 600.0,
        "accuracy": 0.99,
        "recoil_bloom": 0.15,
        "damage_falloff_min": 0.90,
        "falloff_start_dist": 100.0,
        "falloff_end_dist": 250.0,
        "airdrop_only": True,
        "spawn_weight": 0,
    },
    "Kar98k": {
        "item_id": 907000006,
        "name": "Kar98k",
        "category": WeaponCategory.SNIPER,
        "ammo_type": AmmoType.SNIPER,
        "clip_size": 5,
        "reserve_ammo": 15,
        "base_damage": 90.0,
        "headshot_multiplier": 3.0,  # 270 dmg
        "limb_multiplier": 0.80,
        "fire_rate": 1.15,
        "effective_range": 84.0,
        "bullet_speed": 550.0,
        "accuracy": 0.95,
        "recoil_bloom": 0.12,
        "damage_falloff_min": 0.85,
        "falloff_start_dist": 80.0,
        "falloff_end_dist": 200.0,
        "spawn_weight": 12,
    },
    # Shotguns
    "M1014": {
        "item_id": 907000030,
        "name": "M1014",
        "category": WeaponCategory.SHOTGUN,
        "ammo_type": AmmoType.SG,
        "clip_size": 6,
        "reserve_ammo": 24,
        "base_damage": 94.0,      # All 6 pellets combined
        "pellet_count": 6,
        "pellet_damage": 15.6,
        "headshot_multiplier": 1.5,
        "limb_multiplier": 0.70,
        "fire_rate": 0.40,
        "effective_range": 10.0,
        "bullet_speed": 280.0,
        "accuracy": 0.45,
        "recoil_bloom": 0.15,
        "damage_falloff_min": 0.20,
        "falloff_start_dist": 6.0,
        "falloff_end_dist": 20.0,
        "spawn_weight": 20,
    },
    "SPAS12": {
        "item_id": 907000031,
        "name": "SPAS12",
        "category": WeaponCategory.SHOTGUN,
        "ammo_type": AmmoType.SG,
        "clip_size": 5,
        "reserve_ammo": 20,
        "base_damage": 97.0,
        "pellet_count": 6,
        "pellet_damage": 16.1,
        "headshot_multiplier": 1.5,
        "limb_multiplier": 0.70,
        "fire_rate": 0.45,
        "effective_range": 15.0,
        "bullet_speed": 290.0,
        "accuracy": 0.50,
        "recoil_bloom": 0.16,
        "damage_falloff_min": 0.20,
        "falloff_start_dist": 8.0,
        "falloff_end_dist": 25.0,
        "spawn_weight": 18,
    },
    # Pistols
    "USP": {
        "item_id": 907000001,
        "name": "USP",
        "category": WeaponCategory.PISTOL,
        "ammo_type": AmmoType.AR,
        "clip_size": 12,
        "reserve_ammo": 24,
        "base_damage": 19.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.70,
        "fire_rate": 0.18,
        "effective_range": 29.0,
        "bullet_speed": 300.0,
        "accuracy": 0.78,
        "recoil_bloom": 0.05,
        "damage_falloff_min": 0.50,
        "falloff_start_dist": 15.0,
        "falloff_end_dist": 40.0,
        "spawn_weight": 35,
    },
    "DesertEagle": {
        "item_id": 907000002,
        "name": "Desert Eagle",
        "category": WeaponCategory.PISTOL,
        "ammo_type": AmmoType.AR,
        "clip_size": 7,
        "reserve_ammo": 21,
        "base_damage": 54.0,
        "headshot_multiplier": 2.5,
        "limb_multiplier": 0.70,
        "fire_rate": 0.35,
        "effective_range": 38.0,
        "bullet_speed": 350.0,
        "accuracy": 0.85,
        "recoil_bloom": 0.10,
        "damage_falloff_min": 0.60,
        "falloff_start_dist": 25.0,
        "falloff_end_dist": 55.0,
        "spawn_weight": 15,
    },
    # Melee
    "Pan": {
        "item_id": 907000040,
        "name": "Pan",
        "category": WeaponCategory.MELEE,
        "ammo_type": AmmoType.NONE,
        "clip_size": 1,
        "reserve_ammo": 0,
        "base_damage": 62.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.80,
        "fire_rate": 0.65,
        "effective_range": 2.5,
        "bullet_speed": 0.0,
        "accuracy": 1.0,
        "recoil_bloom": 0.0,
        "damage_falloff_min": 1.0,
        "falloff_start_dist": 2.5,
        "falloff_end_dist": 2.5,
        "spawn_weight": 16,
    },
    "Katana": {
        "item_id": 907000041,
        "name": "Katana",
        "category": WeaponCategory.MELEE,
        "ammo_type": AmmoType.NONE,
        "clip_size": 1,
        "reserve_ammo": 0,
        "base_damage": 66.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.80,
        "fire_rate": 0.55,
        "effective_range": 3.0,
        "bullet_speed": 0.0,
        "accuracy": 1.0,
        "recoil_bloom": 0.0,
        "damage_falloff_min": 1.0,
        "falloff_start_dist": 3.0,
        "falloff_end_dist": 3.0,
        "spawn_weight": 12,
    },
    "Bat": {
        "item_id": 907000042,
        "name": "Bat",
        "category": WeaponCategory.MELEE,
        "ammo_type": AmmoType.NONE,
        "clip_size": 1,
        "reserve_ammo": 0,
        "base_damage": 55.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.80,
        "fire_rate": 0.60,
        "effective_range": 2.8,
        "bullet_speed": 0.0,
        "accuracy": 1.0,
        "recoil_bloom": 0.0,
        "damage_falloff_min": 1.0,
        "falloff_start_dist": 2.8,
        "falloff_end_dist": 2.8,
        "spawn_weight": 14,
    },
    "Machete": {
        "item_id": 907000043,
        "name": "Machete",
        "category": WeaponCategory.MELEE,
        "ammo_type": AmmoType.NONE,
        "clip_size": 1,
        "reserve_ammo": 0,
        "base_damage": 58.0,
        "headshot_multiplier": 2.0,
        "limb_multiplier": 0.80,
        "fire_rate": 0.60,
        "effective_range": 2.6,
        "bullet_speed": 0.0,
        "accuracy": 1.0,
        "recoil_bloom": 0.0,
        "damage_falloff_min": 1.0,
        "falloff_start_dist": 2.6,
        "falloff_end_dist": 2.6,
        "spawn_weight": 14,
    },
}

# ---------------------------------------------------------------------------
# Armor, Vests, Helmets & Gear
# ---------------------------------------------------------------------------
GEAR_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Vests
    "Vest_L1": {
        "item_id": 301000001,
        "name": "Kevlar Vest Level 1",
        "slot": "vest",
        "level": 1,
        "damage_reduction": 0.33,
        "durability": 150.0,
        "max_durability": 150.0,
        "spawn_weight": 25,
    },
    "Vest_L2": {
        "item_id": 301000002,
        "name": "Kevlar Vest Level 2",
        "slot": "vest",
        "level": 2,
        "damage_reduction": 0.50,
        "durability": 200.0,
        "max_durability": 200.0,
        "spawn_weight": 18,
    },
    "Vest_L3": {
        "item_id": 301000003,
        "name": "Kevlar Vest Level 3",
        "slot": "vest",
        "level": 3,
        "damage_reduction": 0.66,
        "durability": 260.0,
        "max_durability": 260.0,
        "spawn_weight": 8,
    },
    # Helmets
    "Helmet_L1": {
        "item_id": 302000001,
        "name": "Motorcycle Helmet Level 1",
        "slot": "helmet",
        "level": 1,
        "damage_reduction": 0.33,
        "durability": 70.0,
        "max_durability": 70.0,
        "spawn_weight": 25,
    },
    "Helmet_L2": {
        "item_id": 302000002,
        "name": "Tactical Helmet Level 2",
        "slot": "helmet",
        "level": 2,
        "damage_reduction": 0.45,
        "durability": 115.0,
        "max_durability": 115.0,
        "spawn_weight": 18,
    },
    "Helmet_L3": {
        "item_id": 302000003,
        "name": "Assault Helmet Level 3",
        "slot": "helmet",
        "level": 3,
        "damage_reduction": 0.57,
        "durability": 180.0,
        "max_durability": 180.0,
        "spawn_weight": 8,
    },
    # Backpacks
    "Backpack_L1": {
        "item_id": 904000001,
        "name": "Light Backpack Level 1",
        "slot": "backpack",
        "level": 1,
        "capacity_bonus": 100,
        "spawn_weight": 30,
    },
    "Backpack_L2": {
        "item_id": 904000002,
        "name": "Tactical Backpack Level 2",
        "slot": "backpack",
        "level": 2,
        "capacity_bonus": 200,
        "spawn_weight": 20,
    },
    "Backpack_L3": {
        "item_id": 904000003,
        "name": "Military Backpack Level 3",
        "slot": "backpack",
        "level": 3,
        "capacity_bonus": 300,
        "spawn_weight": 10,
    },
}

# ---------------------------------------------------------------------------
# Consumables, Throwables & Utility
# ---------------------------------------------------------------------------
CONSUMABLES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "Medkit": {
        "item_id": 401000001,
        "name": "Medkit",
        "heal_amount": 75.0,
        "use_time": 4.0,
        "max_stack": 10,
        "spawn_weight": 35,
    },
    "Inhaler": {
        "item_id": 401000002,
        "name": "Inhaler",
        "heal_amount": 25.0,
        "ep_amount": 25.0,
        "use_time": 2.0,
        "max_stack": 10,
        "spawn_weight": 20,
    },
    "GlooWall": {
        "item_id": 402000001,
        "name": "Gloo Wall (Ice Wall)",
        "wall_hp": 300.0,
        "width": 3.6,
        "height": 2.2,
        "lifetime": 45.0,
        "max_stack": 5,
        "spawn_weight": 30,
    },
    "FragGrenade": {
        "item_id": 402000002,
        "name": "Frag Grenade",
        "blast_damage": 200.0,
        "blast_radius": 8.0,
        "fuse_time": 3.0,
        "max_stack": 5,
        "spawn_weight": 20,
    },
    "Ammo_AR": {
        "item_id": 501000001,
        "name": "AR Ammo (30x)",
        "ammo_type": AmmoType.AR,
        "count": 30,
        "spawn_weight": 40,
    },
    "Ammo_SMG": {
        "item_id": 501000002,
        "name": "SMG Ammo (30x)",
        "ammo_type": AmmoType.SMG,
        "count": 30,
        "spawn_weight": 40,
    },
    "Ammo_SG": {
        "item_id": 501000003,
        "name": "SG Shells (10x)",
        "ammo_type": AmmoType.SG,
        "count": 10,
        "spawn_weight": 30,
    },
    "Ammo_Sniper": {
        "item_id": 501000004,
        "name": "Sniper Ammo (10x)",
        "ammo_type": AmmoType.SNIPER,
        "count": 10,
        "spawn_weight": 18,
    },
}

# ---------------------------------------------------------------------------
# Safe Zone Shrink Phases Configuration
# Matches authentic Free Fire 1.39 circle timeline and damage curve
# ---------------------------------------------------------------------------
SAFE_ZONE_PHASES: List[Dict[str, Any]] = [
    {
        "phase": 1,
        "wait_duration": 120.0,   # 2 minutes initial grace period
        "shrink_duration": 90.0,  # 1.5 minutes shrinking
        "start_radius": 950.0,    # Covers almost entire Bermuda map
        "target_radius": 550.0,
        "dps": 1.0,               # 1 HP per second poison tick damage
    },
    {
        "phase": 2,
        "wait_duration": 90.0,
        "shrink_duration": 70.0,
        "start_radius": 550.0,
        "target_radius": 320.0,
        "dps": 2.0,               # 2 HP/sec
    },
    {
        "phase": 3,
        "wait_duration": 75.0,
        "shrink_duration": 55.0,
        "start_radius": 320.0,
        "target_radius": 180.0,
        "dps": 4.0,               # 4 HP/sec
    },
    {
        "phase": 4,
        "wait_duration": 60.0,
        "shrink_duration": 40.0,
        "start_radius": 180.0,
        "target_radius": 75.0,
        "dps": 8.0,               # 8 HP/sec
    },
    {
        "phase": 5,
        "wait_duration": 40.0,
        "shrink_duration": 30.0,
        "start_radius": 75.0,
        "target_radius": 0.0,     # Shrinks completely to 0 (death zone)
        "dps": 12.0,              # 12 HP/sec
    },
]
