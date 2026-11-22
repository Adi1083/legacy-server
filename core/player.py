"""
Thread-safe multi-player state, player session lifecycle, and persistence engine
for Free Fire 1.39 Emulation Server.

Removes hardcoded single-player / singleton assumptions, providing:
- Full per-player account state (profiles, levels, currencies, clothes, inventory, characters, pets)
- Fresh account creation flow (region selection, nickname deduplication, starter bundle provisioning)
- Multi-client concurrent session tracking across HTTP and TCP connections
- High-performance SQLite persistence with thread-safe synchronization
"""

from __future__ import annotations

import copy
import json
import logging
import re
import threading
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger("PlayerManager")

try:
    from core.database import db
except ImportError:
    try:
        from server.core.database import db
    except ImportError:
        from .database import db

# ---------------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------------

DEFAULT_ACCOUNT_ID = 10001
DEFAULT_AVATAR_ID = 102000004  # Adam
DEFAULT_EVA_AVATAR_ID = 101000001  # Eva
DEFAULT_NICKNAME = "PushpaGG"
DEFAULT_STARTER_COINS = 999999
DEFAULT_STARTER_GEMS = 999999
DEFAULT_STARTER_LEVEL = 60
DEFAULT_STARTER_EXP = 99999

DEFAULT_CLOTHES = [211000000, 208000000, 203000573, 204000345, 205000299]

# Starter collection items granted to every new account
DEFAULT_STARTER_ITEMS = [
    211000000, 208000000, 203000573, 204000345, 205000299,  # Starter clothes
    901000001, 901000020,  # Banners
    902000001, 902000030,  # Head pics / Avatars
    903000001, 903000004,  # Lootboxes
    904000001, 904000005,  # Backpacks
    906000001, 906000008,  # Skyboards
    907000001, 907000014,  # Weapon showcases
    209000001, 209000015,  # Parachutes
    909000001, 909000002, 909000003, 909000004, 909000010,  # Emotes
    500000001, 500000005,  # Loadouts
]

SUPPORTED_REGIONS = ("IND", "NA", "SAC", "DEFAULT", "ID", "SG", "BR", "VN", "TH", "RU", "TW")


def _seed_default_characters() -> Dict[int, Dict[str, Any]]:
    """Generate default character roster for new players."""
    roster = [
        (101000001, "Eva", 0),
        (101000005, "Olivia", 106),
        (101000006, "Kelly", 206),
        (101000007, "Nikita", 306),
        (101000008, "Misha", 406),
        (101000009, "Paloma", 506),
        (101000010, "Caroline", 606),
        (101000011, "Moco", 706),
        (101000012, "Laura", 806),
        (101000013, "A124", 906),
        (102000004, "Adam", 0),
        (102000005, "Andrew", 1006),
        (102000006, "Ford", 1106),
        (102000007, "Maxim", 1206),
        (102000008, "Kla", 1306),
        (102000009, "Miguel", 1406),
        (102000010, "Antonio", 1506),
        (102000011, "Wukong", 1706),
        (102000012, "Hayato", 1806),
        (102000013, "Rafael", 1906),
        (102000014, "Joseph", 2006),
    ]
    chars: Dict[int, Dict[str, Any]] = {}
    for avatar_id, name, skill_id in roster:
        slots = [{"slot_id": 0, "skill_id": skill_id}] if skill_id else []
        chars[avatar_id] = {
            "avatar_id": avatar_id,
            "name": name,
            "unlocked_level": 8,
            "exp": 99999,
            "skin_color": 50 if avatar_id in (101000001, 102000004) else 0,
            "clothes": list(DEFAULT_CLOTHES) if avatar_id == DEFAULT_AVATAR_ID else [],
            "equiped_skills": slots,
            "skill_id": skill_id,
            "skill_level": 6 if skill_id else 0,
            "is_selected": avatar_id == DEFAULT_AVATAR_ID,
            "pve_primary_weapon": 0,
        }
    return chars


def _seed_default_pets() -> Dict[int, Dict[str, Any]]:
    """Generate default pets roster for new players."""
    pet_defs = [
        (1300000001, "Kitty", 6, 3000, 1310000001, [1310000001, 1310000002, 1310000003, 1310000004, 1310000005], [1309000001, 1309000002, 1309000003, 1309000004, 1309000005, 1309000006], []),
        (1300000011, "Mechanical Pup", 7, 6000, 1310000011, [1310000011, 1310000012, 1310000013, 1310000014], [1309000011, 1309000012, 1309000013, 1309000014, 1309000015, 1309000016], []),
        (1300000021, "Night Panther", 7, 6000, 1310000021, [1310000021, 1310000022, 1310000023, 1310000024], [1309000021, 1309000022, 1309000023, 1309000024], [{"pet_id": 1300000021, "skill_id": 1315000001, "skill_level": 3}]),
        (1300000031, "Detective Panda", 7, 6000, 1310000031, [1310000031, 1310000032, 1310000033, 1310000034], [1309000031, 1309000032, 1309000033, 1309000034], [{"pet_id": 1300000031, "skill_id": 1315000002, "skill_level": 3}]),
        (1300000041, "Shiba", 7, 6000, 1310000041, [1310000041, 1310000042, 1310000043, 1310000044], [1309000041, 1309000042, 1309000043, 1309000044], [{"pet_id": 1300000041, "skill_id": 1315000003, "skill_level": 3}]),
    ]
    pets: Dict[int, Dict[str, Any]] = {}
    for idx, (pet_id, name, max_lv, max_exp, default_skin, skins, actions, skills) in enumerate(pet_defs):
        pets[pet_id] = {
            "id": pet_id,
            "pet_id": pet_id,
            "name": name,
            "level": max_lv,
            "exp": max_exp,
            "is_selected": idx == 0,
            "skin_id": default_skin,
            "unlocked_skins": list(skins),
            "actions": list(actions),
            "skills": copy.deepcopy(skills),
        }
    return pets


# ---------------------------------------------------------------------------
# Individual Player Account
# ---------------------------------------------------------------------------

class Player:
    """Thread-safe state container for an individual Free Fire 1.39 player account."""

    def __init__(
        self,
        account_id: int,
        nickname: str = "Player",
        region: str = "DEFAULT",
        level: int = DEFAULT_STARTER_LEVEL,
        exp: int = DEFAULT_STARTER_EXP,
        coins: int = DEFAULT_STARTER_COINS,
        gems: int = DEFAULT_STARTER_GEMS,
        avatar_id: int = DEFAULT_AVATAR_ID,
        open_id: str = "",
        device_id: str = "",
        token: str = "",
    ) -> None:
        self._lock = threading.RLock()
        now = int(time.time())

        self.account_id = int(account_id)
        self.nickname = str(nickname)
        self.region = str(region or "DEFAULT")
        self.level = int(level)
        self.exp = int(exp)
        self.coins = int(coins)
        self.gems = int(gems)
        self.avatar_id = int(avatar_id)
        self.skin_color = 50 if self.avatar_id in (101000001, 102000004) else 0
        self.clothes: List[int] = list(DEFAULT_CLOTHES)
        self.selected_pet_id = 1300000001
        self.selected_pet_skin_id = 1310000001
        self.banner_id = 901000001
        self.head_pic = 902000001
        self.clan_id = 0
        self.clan_name = ""
        self.role = 0
        self.rank = 315
        self.ranking_points = 3250
        self.has_elite_pass = True
        self.ep_event_id = 1
        self.ep_badge = 1
        self.badge_cnt = 100
        self.liked = 100
        self.show_rank = True
        self.signature = "India V1 1.39"
        self.create_at = now
        self.last_login_at = now
        self.online_status = 1  # 0=Offline, 1=Lobby, 2=Ready, 3=Match
        self.is_online = True
        self.can_invite = True
        self.is_bot = False
        self.is_banned = False

        # Authentication metadata
        self.open_id = str(open_id or "")
        self.device_id = str(device_id or "")
        self.token = str(token or f"ff_tok_{self.account_id}_{uuid.uuid4().hex[:12]}")

        # Slots & showcases
        self.slots: List[int] = [904000001, 209000001, 906000001, 903000001, 908000001]
        self.shows: List[int] = [907000001, 907000005, 907000010, 907000013, 907000014]
        self.emotes: List[List[int]] = [[1, 909000001], [2, 909000002], [3, 909000003], [4, 909000004]]
        self.loadouts: List[int] = [500000001, 500000005]
        self.ranking_cards: List[int] = []
        self.pve_primary_weapon_skin = 907000001
        self.hidden_collections: List[int] = []
        self.equiped_skills: List[Dict[str, Any]] = []

        # Per-player stores
        self._inventory: Dict[int, int] = {item_id: 1 for item_id in DEFAULT_STARTER_ITEMS}
        self._characters: Dict[int, Dict[str, Any]] = _seed_default_characters()
        self._pets: Dict[int, Dict[str, Any]] = _seed_default_pets()

    # -----------------------------------------------------------------------
    # Profile & Currencies
    # -----------------------------------------------------------------------

    def get_profile(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "account_id": self.account_id,
                "account_type": 1,
                "nickname": self.nickname,
                "region": self.region,
                "level": self.level,
                "exp": self.exp,
                "coins": self.coins,
                "gems": self.gems,
                "gold": self.coins,
                "diamonds": self.gems,
                "avatar_id": self.avatar_id,
                "selected_avatar_id": self.avatar_id,
                "skin_color": self.skin_color,
                "clothes": list(self.clothes),
                "equiped_skills": list(self.equiped_skills),
                "rank": self.rank,
                "ranking_points": self.ranking_points,
                "role": self.role,
                "clan_id": self.clan_id,
                "clan_name": self.clan_name,
                "has_elite_pass": self.has_elite_pass,
                "ep_event_id": self.ep_event_id,
                "ep_badge": self.ep_badge,
                "badge_cnt": self.badge_cnt,
                "liked": self.liked,
                "show_rank": self.show_rank,
                "selected_pet_id": self.selected_pet_id,
                "selected_pet_skin_id": self.selected_pet_skin_id,
                "banner_id": self.banner_id,
                "head_pic": self.head_pic,
                "signature": self.signature,
                "create_at": self.create_at,
                "last_login_at": self.last_login_at,
                "online_status": self.online_status,
                "is_online": self.is_online,
                "can_invite": self.can_invite,
                "is_bot": self.is_bot,
                "is_banned": self.is_banned,
                "slots": list(self.slots),
                "shows": list(self.shows),
                "emotes": copy.deepcopy(self.emotes),
                "loadouts": list(self.loadouts),
                "ranking_cards": list(self.ranking_cards),
                "pve_primary_weapon_skin": self.pve_primary_weapon_skin,
                "hidden_collections": list(self.hidden_collections),
                "open_id": self.open_id,
                "device_id": self.device_id,
                "token": self.token,
            }

    def update_profile(self, **kwargs: Any) -> Dict[str, Any]:
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k) and not k.startswith("_"):
                    if k in ("clothes", "slots", "shows", "loadouts", "ranking_cards", "hidden_collections"):
                        setattr(self, k, [int(x) for x in v] if v is not None else [])
                    elif k == "emotes":
                        setattr(self, k, copy.deepcopy(v))
                    else:
                        setattr(self, k, v)
            # Synonyms
            if "gold" in kwargs:
                self.coins = int(kwargs["gold"])
            elif "coins" in kwargs:
                self.coins = int(kwargs["coins"])
            if "diamonds" in kwargs:
                self.gems = int(kwargs["diamonds"])
            elif "gems" in kwargs:
                self.gems = int(kwargs["gems"])
            if "selected_avatar_id" in kwargs:
                self.avatar_id = int(kwargs["selected_avatar_id"])
            elif "avatar_id" in kwargs:
                self.avatar_id = int(kwargs["avatar_id"])
            if "selected_pet_id" in kwargs:
                self.selected_pet_id = int(kwargs["selected_pet_id"])
            if "is_banned" in kwargs:
                self.is_banned = bool(kwargs["is_banned"])
            self.last_login_at = int(time.time())
            return self.get_profile()

    def get_wallet(self) -> Dict[str, int]:
        with self._lock:
            return {"coins": self.coins, "gems": self.gems, "gold": self.coins, "diamonds": self.gems}

    def grant_currency(self, coins: int = 0, gems: int = 0) -> Dict[str, int]:
        with self._lock:
            self.coins = max(0, self.coins + max(0, int(coins)))
            self.gems = max(0, self.gems + max(0, int(gems)))
            try:
                db.update_wallet(self.account_id, self.coins, self.gems)
            except Exception:
                pass
            return self.get_wallet()

    def spend_currency(self, coins: int = 0, gems: int = 0) -> bool:
        with self._lock:
            c_cost = max(0, int(coins))
            g_cost = max(0, int(gems))
            if self.coins < c_cost or self.gems < g_cost:
                return False
            self.coins -= c_cost
            self.gems -= g_cost
            try:
                db.update_wallet(self.account_id, self.coins, self.gems)
            except Exception:
                pass
            return True

    def get_diamond(self) -> int:
        with self._lock:
            return int(self.gems)

    def modify_diamond(self, delta: int) -> Tuple[bool, int]:
        with self._lock:
            new_val = self.gems + int(delta)
            if new_val < 0:
                return False, self.gems
            self.gems = new_val
            try:
                db.update_wallet(self.account_id, self.coins, self.gems)
            except Exception:
                pass
            return True, self.gems

    def get_gold(self) -> int:
        with self._lock:
            return int(self.coins)

    def modify_gold(self, delta: int) -> Tuple[bool, int]:
        with self._lock:
            new_val = self.coins + int(delta)
            if new_val < 0:
                return False, self.coins
            self.coins = new_val
            try:
                db.update_wallet(self.account_id, self.coins, self.gems)
            except Exception:
                pass
            return True, self.coins

    # -----------------------------------------------------------------------
    # Inventory
    # -----------------------------------------------------------------------

    def get_unlocked_items(self) -> Set[int]:
        with self._lock:
            return set(self._inventory.keys())

    def is_item_unlocked(self, item_id: int) -> bool:
        with self._lock:
            return int(item_id) in self._inventory

    def unlock_item(self, item_id: int, count: int = 1) -> bool:
        with self._lock:
            iid = int(item_id)
            is_new = iid not in self._inventory
            cnt = max(self._inventory.get(iid, 0), int(count))
            self._inventory[iid] = cnt
            try:
                db.save_inventory_item(self.account_id, iid, cnt)
            except Exception:
                pass
            return is_new

    def unlock_items(self, item_ids: Iterable[int]) -> int:
        with self._lock:
            added = 0
            batch: Dict[int, int] = {}
            for raw_id in item_ids:
                iid = int(raw_id)
                if iid not in self._inventory:
                    self._inventory[iid] = 1
                    batch[iid] = 1
                    added += 1
            if batch:
                try:
                    db.save_inventory_batch(self.account_id, batch)
                except Exception:
                    pass
            return added

    def add_item(self, item_id: int, count: int = 1) -> int:
        with self._lock:
            iid = int(item_id)
            new_cnt = self._inventory.get(iid, 0) + max(1, int(count))
            self._inventory[iid] = new_cnt
            try:
                db.save_inventory_item(self.account_id, iid, new_cnt)
            except Exception:
                pass
            return new_cnt

    def consume_item(self, item_id: int, count: int = 1) -> bool:
        with self._lock:
            iid = int(item_id)
            qty = max(1, int(count))
            cur = self._inventory.get(iid, 0)
            if cur < qty:
                return False
            rem = cur - qty
            if rem <= 0:
                self._inventory.pop(iid, None)
                self._unlocked_items.discard(iid)
            else:
                self._inventory[iid] = rem
            try:
                db.save_inventory_item(self.account_id, iid, rem)
            except Exception:
                pass
            return True

    def get_item_count(self, item_id: int) -> int:
        with self._lock:
            return self._inventory.get(int(item_id), 0)

    def get_all_item_counts(self) -> Dict[int, int]:
        with self._lock:
            return dict(self._inventory)

    def delete_item(self, item_id: int, count: Optional[int] = None) -> bool:
        """Delete an item completely or reduce its count from the player's inventory and DB."""
        with self._lock:
            iid = int(item_id)
            if iid not in self._inventory:
                return False
            if count is None or int(count) >= self._inventory[iid]:
                self._inventory.pop(iid, None)
                try:
                    db.delete_inventory_item(self.account_id, iid)
                except Exception:
                    pass
            else:
                new_cnt = self._inventory[iid] - int(count)
                self._inventory[iid] = new_cnt
                try:
                    db.save_inventory_item(self.account_id, iid, new_cnt)
                except Exception:
                    pass
            return True

    def set_banned(self, banned: bool = True) -> bool:
        """Mark account as banned or unbanned and sync to DB."""
        with self._lock:
            self.is_banned = bool(banned)
            try:
                db.set_player_banned(self.account_id, self.is_banned)
            except Exception:
                pass
            return self.is_banned

    # -----------------------------------------------------------------------
    # Characters & Skills
    # -----------------------------------------------------------------------

    def list_characters(self) -> List[Dict[str, Any]]:
        with self._lock:
            chars = list(self._characters.values())
            chars.sort(key=lambda c: c["avatar_id"])
            return copy.deepcopy(chars)

    def get_character(self, avatar_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            c = self._characters.get(int(avatar_id))
            return copy.deepcopy(c) if c else None

    def select_character(self, avatar_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            aid = int(avatar_id)
            if aid not in self._characters:
                return None
            for cid, c in self._characters.items():
                c["is_selected"] = (cid == aid)
            self.avatar_id = aid
            try:
                db.save_character(self.account_id, self._characters[aid])
                db.save_profile(self.account_id, self.get_profile())
            except Exception:
                pass
            return copy.deepcopy(self._characters[aid])

    def unlock_character(
        self,
        avatar_id: int,
        name: str = "",
        level: int = 8,
        skill_id: int = 0,
        clothes: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            aid = int(avatar_id)
            existing = self._characters.get(aid)
            if existing:
                existing["unlocked_level"] = max(int(level), existing["unlocked_level"])
                if name:
                    existing["name"] = name
                if clothes is not None:
                    existing["clothes"] = [int(x) for x in clothes]
                res = existing
            else:
                slots = [{"slot_id": 0, "skill_id": int(skill_id)}] if skill_id else []
                new_c = {
                    "avatar_id": aid,
                    "name": name or f"Avatar_{aid}",
                    "unlocked_level": int(level),
                    "exp": 99999,
                    "skin_color": 50 if aid in (101000001, 102000004) else 0,
                    "clothes": [int(x) for x in clothes] if clothes else [],
                    "equiped_skills": slots,
                    "skill_id": int(skill_id),
                    "skill_level": 6 if skill_id else 0,
                    "is_selected": False,
                    "pve_primary_weapon": 0,
                }
                self._characters[aid] = new_c
                res = new_c
            try:
                db.save_character(self.account_id, res)
            except Exception:
                pass
            return copy.deepcopy(res)

    def equip_clothes(self, avatar_id: int, clothes: List[int]) -> Optional[Dict[str, Any]]:
        with self._lock:
            aid = int(avatar_id)
            c = self._characters.get(aid)
            if not c:
                return None
            c["clothes"] = [int(x) for x in clothes]
            if aid == self.avatar_id:
                self.clothes = list(c["clothes"])
            try:
                db.save_character(self.account_id, c)
                db.save_profile(self.account_id, self.get_profile())
            except Exception:
                pass
            return copy.deepcopy(c)

    def equip_skill(self, avatar_id: int, slot_id: int, skill_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            aid = int(avatar_id)
            c = self._characters.get(aid)
            if not c:
                return None
            slots = [s for s in c.get("equiped_skills", []) if s.get("slot_id") != int(slot_id)]
            if skill_id > 0:
                slots.append({"slot_id": int(slot_id), "skill_id": int(skill_id)})
            slots.sort(key=lambda s: s["slot_id"])
            c["equiped_skills"] = slots
            if aid == self.avatar_id:
                self.equiped_skills = list(slots)
            try:
                db.save_character(self.account_id, c)
            except Exception:
                pass
            return copy.deepcopy(c)

    # -----------------------------------------------------------------------
    # Pets
    # -----------------------------------------------------------------------

    def list_pets(self) -> List[Dict[str, Any]]:
        with self._lock:
            pets = list(self._pets.values())
            pets.sort(key=lambda p: p["id"])
            return copy.deepcopy(pets)

    def get_pet(self, pet_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            p = self._pets.get(int(pet_id))
            return copy.deepcopy(p) if p else None

    def select_pet(self, pet_id: int, skin_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            pid = int(pet_id)
            if pid not in self._pets:
                return None
            for p_id, p in self._pets.items():
                p["is_selected"] = (p_id == pid)
            pet = self._pets[pid]
            if skin_id is not None and int(skin_id) > 0:
                pet["skin_id"] = int(skin_id)
            self.selected_pet_id = pid
            self.selected_pet_skin_id = int(pet.get("skin_id", 0))
            try:
                db.save_pet(self.account_id, pet)
                db.save_profile(self.account_id, self.get_profile())
            except Exception:
                pass
            return copy.deepcopy(pet)

    def unlock_pet(self, pet_id: int, name: str = "", level: int = 7) -> Dict[str, Any]:
        with self._lock:
            pid = int(pet_id)
            existing = self._pets.get(pid)
            if existing:
                existing["level"] = max(int(level), existing["level"])
                if name:
                    existing["name"] = name
                res = existing
            else:
                new_p = {
                    "id": pid,
                    "pet_id": pid,
                    "name": name or f"Pet_{pid}",
                    "level": int(level),
                    "exp": 6000,
                    "is_selected": False,
                    "skin_id": pid + 9999000,
                    "unlocked_skins": [pid + 9999000],
                    "actions": [1, 2, 3, 4],
                    "skills": [],
                }
                self._pets[pid] = new_p
                res = new_p
            try:
                db.save_pet(self.account_id, res)
            except Exception:
                pass
            return copy.deepcopy(res)

    # -----------------------------------------------------------------------
    # Database Persistence & Hydration
    # -----------------------------------------------------------------------

    def save(self) -> None:
        """Persist full player state to SQLite."""
        with self._lock:
            prof = self.get_profile()
            db.save_profile(self.account_id, prof)
            if self._inventory:
                db.save_inventory_batch(self.account_id, self._inventory)
            for c in self._characters.values():
                db.save_character(self.account_id, c)
            for p in self._pets.values():
                db.save_pet(self.account_id, p)

    def load_from_db(self) -> bool:
        """Hydrate player state from SQLite. Returns True if record existed."""
        with self._lock:
            prof = db.get_profile(self.account_id)
            if not prof:
                return False
            self.nickname = str(prof.get("nickname", self.nickname))
            self.region = str(prof.get("region", self.region))
            self.level = int(prof.get("level", self.level))
            self.exp = int(prof.get("exp", self.exp))
            self.coins = int(prof.get("coins", prof.get("gold", self.coins)))
            self.gems = int(prof.get("gems", prof.get("diamonds", self.gems)))
            self.avatar_id = int(prof.get("avatar_id", prof.get("selected_avatar_id", self.avatar_id)))
            self.selected_pet_id = int(prof.get("selected_pet_id", self.selected_pet_id))
            self.selected_pet_skin_id = int(prof.get("selected_pet_skin_id", self.selected_pet_skin_id))
            self.banner_id = int(prof.get("banner_id", self.banner_id))
            self.head_pic = int(prof.get("head_pic", self.head_pic))
            self.clan_id = int(prof.get("clan_id", self.clan_id))
            self.clan_name = str(prof.get("clan_name", self.clan_name))
            self.has_elite_pass = bool(prof.get("has_elite_pass", self.has_elite_pass))
            self.badge_cnt = int(prof.get("badge_cnt", self.badge_cnt))
            self.signature = str(prof.get("signature", self.signature))
            self.create_at = int(prof.get("create_at", self.create_at))
            self.last_login_at = int(prof.get("last_login_at", self.last_login_at))
            self.open_id = str(prof.get("open_id", self.open_id))
            self.device_id = str(prof.get("device_id", self.device_id))
            self.token = str(prof.get("token", self.token))
            self.is_banned = bool(prof.get("is_banned", self.is_banned))

            if "clothes" in prof and isinstance(prof["clothes"], list) and prof["clothes"]:
                self.clothes = [int(x) for x in prof["clothes"]]
            if "slots" in prof and isinstance(prof["slots"], list):
                self.slots = [int(x) for x in prof["slots"]]
            if "shows" in prof and isinstance(prof["shows"], list):
                self.shows = [int(x) for x in prof["shows"]]
            if "emotes" in prof and isinstance(prof["emotes"], list):
                self.emotes = copy.deepcopy(prof["emotes"])
            if "loadouts" in prof and isinstance(prof["loadouts"], list):
                self.loadouts = [int(x) for x in prof["loadouts"]]

            # Hydrate inventory
            try:
                db_inv = db.get_inventory(self.account_id)
                if db_inv:
                    self._inventory.update(db_inv)
            except Exception:
                pass

            # Hydrate characters
            try:
                db_chars = db.get_characters(self.account_id)
                for char_data in db_chars:
                    cid = int(char_data.get("avatar_id", 0))
                    if cid > 0:
                        existing = self._characters.get(cid)
                        if existing:
                            existing.update(char_data)
                        else:
                            self._characters[cid] = char_data
            except Exception:
                pass

            # Hydrate pets
            try:
                db_pets = db.get_pets(self.account_id)
                for pet_data in db_pets:
                    pid = int(pet_data.get("pet_id", pet_data.get("id", 0)))
                    if pid > 0:
                        existing = self._pets.get(pid)
                        if existing:
                            existing.update(pet_data)
                        else:
                            self._pets[pid] = pet_data
            except Exception:
                pass

            return True

    def to_summary(self) -> Dict[str, Any]:
        """Summary dict for player listings, friend suggestions, and lobby displays."""
        with self._lock:
            return {
                "account_id": self.account_id,
                "nickname": self.nickname,
                "region": self.region,
                "level": self.level,
                "exp": self.exp,
                "rank": self.rank,
                "ranking_points": self.ranking_points,
                "banner_id": self.banner_id,
                "head_pic": self.head_pic,
                "avatar_id": self.avatar_id,
                "clan_id": self.clan_id,
                "clan_name": self.clan_name,
                "has_elite_pass": self.has_elite_pass,
                "badge_cnt": self.badge_cnt,
                "online_status": self.online_status,
                "is_online": self.is_online,
                "can_invite": self.can_invite,
                "is_bot": self.is_bot,
                "is_banned": self.is_banned,
                "last_login_at": self.last_login_at,
            }


# ---------------------------------------------------------------------------
# Central Multi-Player Manager
# ---------------------------------------------------------------------------

class PlayerManager:
    """Thread-safe central registry, lifecycle controller, and session coordinator."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._players: Dict[int, Player] = {}
        self._by_token: Dict[str, int] = {}
        self._by_open_id: Dict[str, int] = {}
        self._by_device_id: Dict[str, int] = {}
        self._ip_sessions: Dict[str, int] = {}  # client_ip -> account_id

        # Hydrate all existing accounts from SQLite on startup
        self.hydrate_all()

    def hydrate_all(self) -> int:
        """Hydrate all registered players from the SQLite database."""
        with self._lock:
            count = 0
            try:
                account_ids = db.get_all_account_ids()
                for aid in account_ids:
                    player = Player(account_id=aid)
                    if player.load_from_db():
                        self._index_player(player)
                        count += 1
            except Exception as e:
                logger.warning("Failed to hydrate all players from DB: %s", e)

            # Ensure default account 10001 always exists
            if DEFAULT_ACCOUNT_ID not in self._players:
                p10001 = Player(
                    account_id=DEFAULT_ACCOUNT_ID,
                    nickname=DEFAULT_NICKNAME,
                    region="DEFAULT",
                    level=60,
                    exp=99999,
                    coins=DEFAULT_STARTER_COINS,
                    gems=DEFAULT_STARTER_GEMS,
                )
                p10001.save()
                self._index_player(p10001)
                count += 1

            return count

    def _index_player(self, player: Player) -> None:
        """Update internal indexes for fast token/open_id/device_id lookup."""
        aid = player.account_id
        self._players[aid] = player
        if player.token:
            self._by_token[player.token] = aid
        if player.open_id:
            self._by_open_id[player.open_id] = aid
        if player.device_id:
            self._by_device_id[player.device_id] = aid

    def get_player(self, account_id: int) -> Optional[Player]:
        """Fetch player by account_id, lazily hydrating from DB if necessary."""
        aid = int(account_id)
        with self._lock:
            player = self._players.get(aid)
            if player:
                return player
            # Try lazy load from database
            try:
                db_prof = db.get_profile(aid)
                if db_prof:
                    p = Player(account_id=aid)
                    if p.load_from_db():
                        self._index_player(p)
                        return p
            except Exception:
                pass
            return None

    def find_account_by_token(self, token: str) -> Optional[Player]:
        """Look up player by token from memory or database."""
        clean_tok = str(token or "").strip()
        if not clean_tok:
            return None
        with self._lock:
            aid = self._by_token.get(clean_tok)
            if aid:
                return self.get_player(aid)
            try:
                row = db.find_account_by_token(clean_tok)
                if row:
                    return self.get_player(int(row["account_id"]))
            except Exception:
                pass
            return None

    def find_account_by_open_id(self, open_id: str) -> Optional[Player]:
        """Look up player by open_id from memory or database."""
        clean_oid = str(open_id or "").strip()
        if not clean_oid:
            return None
        with self._lock:
            aid = self._by_open_id.get(clean_oid)
            if aid:
                return self.get_player(aid)
            try:
                row = db.find_account_by_open_id(clean_oid)
                if row:
                    return self.get_player(int(row["account_id"]))
            except Exception:
                pass
            return None

    def find_account_by_device_id(self, device_id: str) -> Optional[Player]:
        """Look up player by device_id from memory or database."""
        clean_did = str(device_id or "").strip()
        if not clean_did:
            return None
        with self._lock:
            aid = self._by_device_id.get(clean_did)
            if aid:
                return self.get_player(aid)
            try:
                row = db.find_account_by_device_id(clean_did)
                if row:
                    return self.get_player(int(row["account_id"]))
            except Exception:
                pass
            return None

    def get_or_create(self, account_id: int, **kwargs: Any) -> Player:
        """Fetch existing player or create with given account_id."""
        aid = int(account_id)
        with self._lock:
            player = self.get_player(aid)
            if player:
                return player
            player = Player(account_id=aid, **kwargs)
            player.save()
            self._index_player(player)
            return player

    def delete_account(self, account_id: int) -> bool:
        """Remove account from memory and delete from database."""
        with self._lock:
            aid = int(account_id)
            player = self._players.pop(aid, None)
            if player:
                if player.token:
                    self._by_token.pop(player.token, None)
                if player.open_id:
                    self._by_open_id.pop(player.open_id, None)
                if player.device_id:
                    self._by_device_id.pop(player.device_id, None)
            return db.delete_account(aid)

    def is_nickname_taken(self, nickname: str, exclude_account_id: int = 0) -> bool:
        """Check if a nickname is already in use by another account."""
        clean = str(nickname or "").strip().lower()
        if not clean:
            return True
        with self._lock:
            # Check in-memory active players
            for p in self._players.values():
                if p.account_id != int(exclude_account_id) and p.nickname.strip().lower() == clean:
                    return True
            # Check database
            try:
                row = db.find_account_by_nickname(clean)
                if row and int(row.get("account_id", 0)) != int(exclude_account_id):
                    return True
            except Exception:
                pass
            return False

    def change_nickname(self, account_id: int, new_nickname: str) -> Tuple[bool, str, str]:
        """
        Safely modify player's nickname with deduplication & validation checks.
        Returns: (success: bool, final_nickname: str, message: str)
        """
        aid = int(account_id)
        clean = str(new_nickname or "").strip()[:32]
        if not clean:
            return False, "", "Nickname cannot be empty"

        with self._lock:
            player = self.get_player(aid)
            if not player:
                return False, "", f"Account {aid} not found"

            if player.nickname == clean:
                return True, clean, "Nickname unchanged"

            if self.is_nickname_taken(clean, exclude_account_id=aid):
                return False, player.nickname, "Nickname already taken"

            player.nickname = clean
            player.save()

            # Broadcast name change to active lobby squad if in one
            try:
                from handlers.team_handler import broadcast_group_change
                broadcast_group_change(aid)
            except Exception:
                pass

            return True, clean, "Nickname changed successfully"

    def change_region(self, account_id: int, new_region: str) -> bool:
        """Update player region (e.g. IND / NA / SAC / DEFAULT)."""
        aid = int(account_id)
        clean_reg = str(new_region or "DEFAULT").strip().upper()
        with self._lock:
            player = self.get_player(aid)
            if not player:
                return False
            player.region = clean_reg
            player.save()
            return True

    def create_account(
        self,
        nickname: str = "",
        region: str = "DEFAULT",
        avatar_id: int = DEFAULT_AVATAR_ID,
        open_id: str = "",
        device_id: str = "",
        initial_gold: int = DEFAULT_STARTER_COINS,
        initial_diamonds: int = DEFAULT_STARTER_GEMS,
        level: int = DEFAULT_STARTER_LEVEL,
        exp: int = DEFAULT_STARTER_EXP,
        is_banned: bool = False,
        client_ip: str = "",
    ) -> Player:
        """
        Create a brand new player account with dynamic account_id, starter bundle,
        and immediate persistence.
        """
        with self._lock:
            # Allocate unique monotonic ID
            new_aid = db.get_next_account_id()
            while new_aid in self._players:
                new_aid += 1

            # Resolve unique nickname
            clean_nick = str(nickname or "").strip()[:32]
            if not clean_nick or self.is_nickname_taken(clean_nick):
                clean_nick = f"Player_{new_aid}"
                # Ensure generated fallback nickname is uniquely numbered
                suffix = 1
                while self.is_nickname_taken(clean_nick):
                    clean_nick = f"Player_{new_aid}_{suffix}"
                    suffix += 1

            clean_reg = str(region or "DEFAULT").strip().upper()
            if clean_reg not in SUPPORTED_REGIONS and clean_reg != "DEFAULT":
                clean_reg = "IND"

            player = Player(
                account_id=new_aid,
                nickname=clean_nick,
                region=clean_reg,
                level=int(level) if level > 0 else DEFAULT_STARTER_LEVEL,
                exp=int(exp) if exp >= 0 else DEFAULT_STARTER_EXP,
                coins=initial_gold,
                gems=initial_diamonds,
                avatar_id=avatar_id if avatar_id in (DEFAULT_AVATAR_ID, DEFAULT_EVA_AVATAR_ID) else DEFAULT_AVATAR_ID,
                open_id=open_id,
                device_id=device_id,
            )
            player.is_banned = bool(is_banned)

            # Persist to SQLite
            player.save()
            self._index_player(player)

            if client_ip:
                self.bind_session(client_ip, new_aid, player.token)

            logger.info("Created new multi-player account: aid=%d, nick='%s', reg='%s'", new_aid, clean_nick, clean_reg)
            return player

    def ban_player(self, account_id: int) -> bool:
        """Ban player account, setting is_banned in memory and DB."""
        aid = int(account_id)
        with self._lock:
            p = self.get_player(aid)
            if not p:
                return False
            p.set_banned(True)
            p.is_online = False
            p.online_status = 0
            return True

    def unban_player(self, account_id: int) -> bool:
        """Unban player account, clearing is_banned in memory and DB."""
        aid = int(account_id)
        with self._lock:
            p = self.get_player(aid)
            if not p:
                return False
            p.set_banned(False)
            return True

    def is_player_banned(self, account_id: int) -> bool:
        """Check if player account is currently banned."""
        aid = int(account_id)
        with self._lock:
            p = self.get_player(aid)
            if p:
                return bool(p.is_banned)
            return db.is_player_banned(aid)

    def list_players_paginated(
        self,
        search: str = "",
        sort_by: str = "account_id",
        sort_dir: str = "asc",
        page: int = 1,
        limit: int = 20,
        is_banned: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Server-side paginated player search and sorting."""
        with self._lock:
            raw_rows, total = db.list_accounts_paged(
                search=search,
                sort_by=sort_by,
                sort_dir=sort_dir,
                page=page,
                limit=limit,
                is_banned=is_banned,
            )
            summaries: List[Dict[str, Any]] = []
            for r in raw_rows:
                aid = int(r["account_id"])
                player = self.get_player(aid)
                if player:
                    summaries.append(player.to_summary())
                else:
                    summaries.append({
                        "account_id": aid,
                        "nickname": r.get("nickname", f"Player_{aid}"),
                        "region": r.get("region", "DEFAULT"),
                        "level": r.get("level", 60),
                        "exp": r.get("exp", 0),
                        "rank": r.get("rank", 315),
                        "ranking_points": r.get("ranking_points", 3250),
                        "banner_id": r.get("banner_id", 901000001),
                        "head_pic": r.get("head_pic", 902000001),
                        "avatar_id": r.get("avatar_id", DEFAULT_AVATAR_ID),
                        "clan_id": r.get("clan_id", 0),
                        "clan_name": r.get("clan_name", ""),
                        "has_elite_pass": bool(r.get("has_elite_pass", False)),
                        "badge_cnt": r.get("badge_cnt", 0),
                        "online_status": 0,
                        "is_online": False,
                        "is_banned": bool(r.get("is_banned", 0)),
                        "can_invite": False,
                        "is_bot": False,
                        "last_login_at": r.get("updated_at", 0),
                    })
            return summaries, total

    def authenticate(
        self,
        account_id: int = 0,
        open_id: str = "",
        device_id: str = "",
        token: str = "",
        client_ip: str = "",
        nickname: str = "",
        region: str = "DEFAULT",
    ) -> Tuple[Player, bool]:
        """
        Multi-client login resolver. Looks up existing account or provisions a fresh one.
        Returns: (player: Player, is_new: bool)
        """
        with self._lock:
            # 1. Direct account_id lookup if specified and valid
            if account_id > 0:
                p = self.get_player(account_id)
                if p:
                    if client_ip:
                        self.bind_session(client_ip, p.account_id, p.token)
                    return p, False

            # 2. Token lookup
            if token and token in self._by_token:
                aid = self._by_token[token]
                p = self.get_player(aid)
                if p:
                    if client_ip:
                        self.bind_session(client_ip, p.account_id, p.token)
                    return p, False

            # 3. OpenID lookup
            if open_id:
                if open_id in self._by_open_id:
                    aid = self._by_open_id[open_id]
                    p = self.get_player(aid)
                    if p:
                        if client_ip:
                            self.bind_session(client_ip, p.account_id, p.token)
                        return p, False
                try:
                    db_p = db.find_account_by_open_id(open_id)
                    if db_p:
                        p = self.get_player(int(db_p["account_id"]))
                        if p:
                            if client_ip:
                                self.bind_session(client_ip, p.account_id, p.token)
                            return p, False
                except Exception:
                    pass

            # 4. Device ID lookup
            if device_id:
                if device_id in self._by_device_id:
                    aid = self._by_device_id[device_id]
                    p = self.get_player(aid)
                    if p:
                        if client_ip:
                            self.bind_session(client_ip, p.account_id, p.token)
                        return p, False
                try:
                    db_p = db.find_account_by_device_id(device_id)
                    if db_p:
                        p = self.get_player(int(db_p["account_id"]))
                        if p:
                            if client_ip:
                                self.bind_session(client_ip, p.account_id, p.token)
                            return p, False
                except Exception:
                    pass

            # 5. IP session check (if localhost / 127.0.0.1, distinguish by open_id/device_id;
            # if unique IP and existing session bound, reuse)
            if client_ip and client_ip not in ("127.0.0.1", "::1", "10.0.2.2"):
                bound_aid = self._ip_sessions.get(client_ip)
                if bound_aid:
                    p = self.get_player(bound_aid)
                    if p:
                        return p, False

            # 6. Not found -> Provision fresh new multi-player account!
            new_player = self.create_account(
                nickname=nickname,
                region=region,
                open_id=open_id,
                device_id=device_id,
                client_ip=client_ip,
            )
            return new_player, True

    def bind_session(self, client_ip: str, account_id: int, token: Optional[str] = None) -> None:
        """Bind client IP and optional token to account_id."""
        with self._lock:
            clean_ip = str(client_ip or "").replace("::ffff:", "")
            aid = int(account_id)
            if clean_ip:
                self._ip_sessions[clean_ip] = aid
            if token:
                self._by_token[str(token)] = aid

    def get_session_account_id(self, client_ip: str, token: Optional[str] = None) -> Optional[int]:
        """Resolve account_id from token or client_ip."""
        with self._lock:
            if token and token in self._by_token:
                return self._by_token[token]
            clean_ip = str(client_ip or "").replace("::ffff:", "")
            if clean_ip in self._ip_sessions:
                return self._ip_sessions[clean_ip]
            return None

    def search_players(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search active and registered players by nickname prefix or substring."""
        clean = str(query or "").strip().lower()
        if not clean:
            return []
        with self._lock:
            results: List[Dict[str, Any]] = []
            seen: Set[int] = set()

            # First search loaded in-memory players
            for p in self._players.values():
                if clean in p.nickname.lower():
                    results.append(p.to_summary())
                    seen.add(p.account_id)
                    if len(results) >= limit:
                        return results

            # Search database
            try:
                db_matches = db.search_accounts_by_nickname(clean, limit=limit)
                for row in db_matches:
                    aid = int(row.get("account_id", 0))
                    if aid not in seen:
                        seen.add(aid)
                        p = self.get_player(aid)
                        if p:
                            results.append(p.to_summary())
                        else:
                            results.append(row)
                        if len(results) >= limit:
                            break
            except Exception:
                pass

            return results

    def list_all_players(self) -> List[Player]:
        with self._lock:
            return list(self._players.values())


# Global singleton instance
player_manager = PlayerManager()
