"""
Admin REST API Layer & Dashboard Integration for Free Fire 1.39 Luck Royale.
Exposes clean, authenticated JSON endpoints under /api/admin/luck-royale/:
1. /overview: Summary statistics, active machines, total spins, currency burn.
2. /machines: GET (list), POST (create), PUT (update), DELETE, POST (toggle/duplicate).
3. /reward-pools: GET, POST, PUT, DELETE, and item search helper.
4. /meters: GET, PUT (adjust lucky meter settings per machine).
5. /currencies-vouchers: GET, POST (grant/deduct currencies or vouchers to accounts).
6. /exchange: GET, POST, PUT (Incubator forge and token shop configs).
7. /events-banners: GET, POST, PUT (event scheduling and banner assignments).
8. /accounts/<account_id>: GET (meter states, gacha history, inventory), POST (manual adjustment).
9. /transactions: GET with filters (account, machine, date, reward, status).
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.character_models import (
    AVATAR_CATALOG,
    AVATAR_TO_DEBRIS_MAP,
    STARTER_AVATAR_IDS,
    get_character_debris_id,
)
import proto.gacha_models as gm
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    DEFAULT_SPECIAL_EXCHANGES,
    ITEM_BLUEPRINT_JOKER,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
    ITEM_MAGIC_CUBE,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
    ChestConfig,
    ChestTabType,
    CoinType,
    ConsumeType,
    ExtraRewardConfig,
    GachaShowItemConfig,
    ILuckRoyaleAdminService,
    LotteryType,
    RareType,
    SpecialExchangeConfig,
    config_manager,
    registry,
    validate_machine_config,
)
from proto.store_models import AwardType

logger = logging.getLogger("admin_luck_royale_api")

# Base directories
_SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_SERVER_DIR, "data")
_STATIC_DIR = os.path.join(_SERVER_DIR, "static")
_BANNERS_DIR = os.path.join(_STATIC_DIR, "banners")
ADMIN_STATE_FILE = os.path.join(_DATA_DIR, "admin_luck_royale_state.json")

# ---------------------------------------------------------------------------
# Authoritative Free Fire 1.39 Manifest & Item Data
# ---------------------------------------------------------------------------
_MANIFEST_FILE = os.path.join(_STATIC_DIR, "assets", "freefire", "1.39", "manifest.json")
_AUTHENTIC_MANIFEST: Dict[str, Any] = {}
if os.path.exists(_MANIFEST_FILE):
    try:
        with open(_MANIFEST_FILE, "r", encoding="utf-8") as _mf:
            _AUTHENTIC_MANIFEST = json.load(_mf)
    except Exception as _e:
        logger.warning("Failed to load authentic manifest: %s", _e)

_AUTHORITATIVE_ITEM_MAP: Dict[int, Dict[str, Any]] = {}
_ITEM_CSV_PATH = os.path.join(os.path.dirname(_SERVER_DIR), "scratch", "Item_authoritative.csv")
if not os.path.exists(_ITEM_CSV_PATH):
    _ITEM_CSV_PATH = os.path.join(_SERVER_DIR, "scratch", "Item_authoritative.csv")

if os.path.exists(_ITEM_CSV_PATH):
    try:
        import csv as _csv
        with open(_ITEM_CSV_PATH, "r", encoding="utf-8", errors="ignore") as _cf:
            _r = _csv.reader(_cf)
            next(_r)  # header
            next(_r)  # desc
            for _row in _r:
                if len(_row) > 9:
                    try:
                        _iid = int(_row[0])
                        _rare_val = int(_row[9]) if _row[9].isdigit() else 1
                        _type_val = _row[1]
                        _cat = "General"
                        if _type_val == "1": _cat = "Avatar"
                        elif _type_val == "2": _cat = "Clothes"
                        elif _type_val == "4": _cat = "Chest"
                        elif _type_val == "7": _cat = "Bundle"
                        elif _type_val == "8": _cat = "Consumable"
                        elif _type_val == "9": _cat = "GunSkin" if _row[3] == "7" else "Collection"
                        elif _type_val == "11": _cat = "BonusCard"
                        elif _type_val == "13": _cat = "Pet"
                        _AUTHORITATIVE_ITEM_MAP[_iid] = {
                            "name": _row[5] or f"Item #{_iid}",
                            "category": _cat,
                            "rarity": _rare_val,
                            "icon": _row[7]
                        }
                    except Exception:
                        pass
    except Exception as _e:
        logger.warning("Failed to load authoritative item CSV: %s", _e)

# Authentication configuration
ADMIN_API_TOKEN = os.environ.get("ADMIN_API_TOKEN", "ind-admin-token-2026")
REQUIRE_AUTH = os.environ.get("ADMIN_REQUIRE_AUTH", "0") == "1"

# Known Vouchers, Currencies & Tokens mapping
VOUCHER_CANONICAL_IDS = {
    "gold_royale": 110100010,
    "diamond_royale": 110100008,
    "weapon_royale": 110100009,
    "incubator": 110100018,
}
VOUCHER_LEGACY_IDS = {
    "gold_royale": 802000000,
    "diamond_royale": 802000001,
    "weapon_royale": 802000008,
    "incubator": 802000009,
}
VOUCHER_NAMES = {
    110100010: "Gold Royale Voucher",
    802000000: "Gold Royale Voucher (Legacy)",
    110100008: "Diamond Royale Voucher",
    802000001: "Diamond Royale Voucher (Legacy)",
    110100009: "Weapon Royale Voucher",
    802000008: "Weapon Royale Voucher (Legacy)",
    110100018: "Incubator Voucher",
    802000009: "Incubator Voucher (Legacy)",
}

# Catalog of known Free Fire 1.39 items for auto-complete and search helper
ITEM_CATALOG: Dict[int, Dict[str, Any]] = {
    # Vouchers
    110100010: {"name": "Gold Royale Voucher", "category": "Voucher", "rarity": 1},
    802000000: {"name": "Gold Royale Voucher (Legacy)", "category": "Voucher", "rarity": 1},
    110100008: {"name": "Diamond Royale Voucher", "category": "Voucher", "rarity": 2},
    802000001: {"name": "Diamond Royale Voucher (Legacy)", "category": "Voucher", "rarity": 2},
    110100009: {"name": "Weapon Royale Voucher", "category": "Voucher", "rarity": 2},
    802000008: {"name": "Weapon Royale Voucher (Legacy)", "category": "Voucher", "rarity": 2},
    110100018: {"name": "Incubator Voucher", "category": "Voucher", "rarity": 2},
    802000009: {"name": "Incubator Voucher (Legacy)", "category": "Voucher", "rarity": 2},
    # Tokens & Materials
    110200001: {"name": "FF Token", "category": "Token", "rarity": 1},
    800000301: {"name": "FF Token (Legacy)", "category": "Token", "rarity": 1},
    800000304: {"name": "Magic Cube", "category": "Material", "rarity": 2},
    808000003: {"name": "Evolution Stone", "category": "Material", "rarity": 2},
    808000001: {"name": "Evolution Stone / Blueprint YinYang", "category": "Material", "rarity": 2},
    808000002: {"name": "Blueprint Joker", "category": "Material", "rarity": 2},
    808000011: {"name": "Blueprint YinYang", "category": "Material", "rarity": 2},
    808000012: {"name": "Blueprint Joker", "category": "Material", "rarity": 2},
    # Incubator YinYang Bundles
    710000410: {"name": "Bundle: Golden YinYang (Male)", "category": "Bundle", "rarity": 2},
    710000411: {"name": "Bundle: Golden YinYang (Female)", "category": "Bundle", "rarity": 2},
    710000412: {"name": "Bundle: Cloud YinYang (Male)", "category": "Bundle", "rarity": 1},
    710000413: {"name": "Bundle: Cloud YinYang (Female)", "category": "Bundle", "rarity": 1},
    710000408: {"name": "Bundle: Silver YinYang (Male)", "category": "Bundle", "rarity": 0},
    710000409: {"name": "Bundle: Silver YinYang (Female)", "category": "Bundle", "rarity": 0},
    # Incubator Joker Bundles
    710000414: {"name": "Bundle: Royal Joker (Male)", "category": "Bundle", "rarity": 2},
    710000415: {"name": "Bundle: Royal Joker (Female)", "category": "Bundle", "rarity": 2},
    710000416: {"name": "Bundle: Midnight Joker (Male)", "category": "Bundle", "rarity": 1},
    710000417: {"name": "Bundle: Midnight Joker (Female)", "category": "Bundle", "rarity": 1},
    710000418: {"name": "Bundle: Harlequin Joker (Male)", "category": "Bundle", "rarity": 0},
    710000419: {"name": "Bundle: Harlequin Joker (Female)", "category": "Bundle", "rarity": 0},
    # Diamond Royale Costumes & Skins
    710000400: {"name": "Bundle: Cyber Threat (Male)", "category": "Bundle", "rarity": 2},
    710000401: {"name": "Bundle: Cyber Threat (Female)", "category": "Bundle", "rarity": 2},
    710000403: {"name": "Top: Cyber Shadow", "category": "Clothes", "rarity": 1},
    710000404: {"name": "Bottom: Cyber Shadow", "category": "Clothes", "rarity": 1},
    710000405: {"name": "Shoes: Cyber Stride", "category": "Clothes", "rarity": 1},
    710000406: {"name": "Mask: Cyber Visor", "category": "Clothes", "rarity": 1},
    203000505: {"name": "T-Shirt: Urban Camo", "category": "Clothes", "rarity": 0},
    203000506: {"name": "T-Shirt: Crimson Skull", "category": "Clothes", "rarity": 0},
    204000304: {"name": "Pants: Combat Khaki", "category": "Clothes", "rarity": 0},
    204000307: {"name": "Pants: Street Denim", "category": "Clothes", "rarity": 0},
    # Weapon Royale Skins
    907001611: {"name": "AK47 - Flaming Dragon", "category": "GunSkin", "rarity": 2},
    907001612: {"name": "MP40 - Sneaky Clown", "category": "GunSkin", "rarity": 2},
    907001613: {"name": "M4A1 - Star General", "category": "GunSkin", "rarity": 1},
    907001614: {"name": "SCAR - Blood Moon", "category": "GunSkin", "rarity": 1},
    907001615: {"name": "AWM - Cheetah", "category": "GunSkin", "rarity": 1},
    907001620: {"name": "FAMAS - Metallic", "category": "GunSkin", "rarity": 1},
    907001621: {"name": "M1014 - Cataclysm", "category": "GunSkin", "rarity": 1},
    907001622: {"name": "UMP - Wilderness Hunter", "category": "GunSkin", "rarity": 0},
    907001623: {"name": "SKS - Bumblebee", "category": "GunSkin", "rarity": 0},
    # Gold Royale Rewards
    710000422: {"name": "Bundle: Golden Striker (Male)", "category": "Bundle", "rarity": 2},
    710000423: {"name": "Bundle: Golden Striker (Female)", "category": "Bundle", "rarity": 2},
    710000303: {"name": "Cap: Gold Champion", "category": "Clothes", "rarity": 1},
    710000304: {"name": "Jersey: Gold Champion", "category": "Clothes", "rarity": 1},
    710000305: {"name": "Shorts: Gold Champion", "category": "Clothes", "rarity": 1},
    203000500: {"name": "T-Shirt: Classic White", "category": "Clothes", "rarity": 0},
    203000501: {"name": "T-Shirt: Classic Black", "category": "Clothes", "rarity": 0},
    204000300: {"name": "Pants: Classic Blue", "category": "Clothes", "rarity": 0},
    800000001: {"name": "Bounty Token", "category": "Utility", "rarity": 0},
    800000002: {"name": "Resupply Map", "category": "Utility", "rarity": 0},
    1307000001: {"name": "Pet Food", "category": "Pet", "rarity": 0},
    1101000001: {"name": "Double EXP Card (3 Days)", "category": "BonusCard", "rarity": 0},
    1102000001: {"name": "Double Gold Card (3 Days)", "category": "BonusCard", "rarity": 0},
    1101000002: {"name": "Double EXP Card (7 Days)", "category": "BonusCard", "rarity": 0},
    1102000002: {"name": "Double Gold Card (7 Days)", "category": "BonusCard", "rarity": 0},
}


DEFAULT_MACHINE_ARTWORK: Dict[int, Dict[str, str]] = {
    CHEST_DIAMOND_ROYALE: {
        "banner": "/assets/freefire/1.39/royale/UI_Lottery_Poster_P.png",
        "thumbnail": "/assets/freefire/1.39/royale/FF_Lottery_gaindiamond.png",
        "background": "/assets/freefire/1.39/royale/UI_Lottery_bg01.png",
        "featured": "/assets/freefire/1.39/royale/UI_Lottery_Poster_P.png",
        "promo": "/assets/freefire/1.39/royale/FF_Lottery_gaindiamond_big.png",
    },
    CHEST_WEAPON_ROYALE: {
        "banner": "/assets/freefire/1.39/royale/UI_Lottery_Poster_W.png",
        "thumbnail": "/assets/freefire/1.39/royale/FF_Lottery_weapon.png",
        "background": "/assets/freefire/1.39/royale/UI_Lottery_bg02.png",
        "featured": "/assets/freefire/1.39/royale/FF_Lottery_M4A1_Carnival_big.png",
        "promo": "/assets/freefire/1.39/royale/FF_Lottery_weaponman.png",
    },
    CHEST_GOLD_ROYALE: {
        "banner": "/assets/freefire/1.39/royale/UI_Lottery_Poster_G.png",
        "thumbnail": "/assets/freefire/1.39/royale/FF_Lottery_gaincoin.png",
        "background": "/assets/freefire/1.39/royale/UI_Lottery_bg01.png",
        "featured": "/assets/freefire/1.39/royale/UI_Lottery_Poster_G.png",
        "promo": "/assets/freefire/1.39/royale/FF_Lottery_gaincoin_big.png",
    },
    CHEST_INCUBATOR: {
        "banner": "/assets/freefire/1.39/royale/FF_Lottery_anni_big.png",
        "thumbnail": "/assets/freefire/1.39/royale/FF_Lottery_anni_forge.png",
        "background": "/assets/freefire/1.39/royale/UI_GachaLegendary_Prob_bg.png",
        "featured": "/assets/freefire/1.39/royale/FF_Lottery_anni_forge.png",
        "promo": "/assets/freefire/1.39/royale/FF_UI_Lottery_Animate.png",
    },
}

DEFAULT_ITEM_IMAGES: Dict[int, str] = {
    110100010: "FF_Lottery_gaincoin.png",
    802000000: "FF_Lottery_gaincoin.png",
    110100008: "FF_Lottery_gaindiamond.png",
    802000001: "FF_Lottery_gaindiamond.png",
    110100009: "FF_Lottery_weapon.png",
    802000008: "FF_Lottery_weapon.png",
    110100018: "FF_Lottery_anni_forge.png",
    802000009: "FF_Lottery_anni_forge.png",
    110200001: "FF_Lottery_gaincoin.png",
    800000301: "FF_Lottery_gaincoin.png",
    800000304: "FF_Lottery_gaindiamond_big.png",
    808000003: "FF_Lottery_Ingot1.png",
    808000001: "FF_Lottery_Ingot1.png",
    808000002: "FF_Lottery_Ingot2.png",
    808000011: "FF_Lottery_Ingot1.png",
    808000012: "FF_Lottery_Ingot2.png",
    710000410: "FF_Lottery_anni_big.png",
    710000411: "FF_Lottery_anni_big.png",
    710000412: "FF_Lottery_anni_big.png",
    710000413: "FF_Lottery_anni_big.png",
    710000414: "luck_royale_banner.png",
    710000415: "luck_royale_banner.png",
    710000400: "UI_Lottery_Poster_P.png",
    710000401: "UI_Lottery_Poster_P.png",
    710000422: "UI_Lottery_Poster_G.png",
    710000423: "UI_Lottery_Poster_G.png",
    907001611: "FF_Lottery_M4A1_Carnival_big.png",
    907001612: "FF_Lottery_gun_big.png",
    907001613: "FF_Lottery_weapon.png",
    907001614: "FF_Lottery_weapon.png",
    907001615: "FF_Lottery_weapon.png",
    907001620: "FF_Lottery_weapon.png",
    907001621: "FF_Lottery_weapon.png",
    907001622: "FF_Lottery_weapon.png",
    907001623: "FF_Lottery_weapon.png",
}


def _get_item_meta(item_id: int) -> Dict[str, Any]:
    iid = int(item_id)
    if iid in ITEM_CATALOG:
        return {"item_id": iid, **ITEM_CATALOG[iid]}
    if iid in AVATAR_CATALOG:
        return {"item_id": iid, "name": f"Character: {AVATAR_CATALOG[iid]['name']}", "category": "Avatar", "rarity": 2}
    for aid, deb_id in AVATAR_TO_DEBRIS_MAP.items():
        if deb_id == iid:
            cname = AVATAR_CATALOG[aid]["name"] if aid in AVATAR_CATALOG else f"Avatar {aid}"
            return {"item_id": iid, "name": f"{cname} Debris (Fragment)", "category": "Character Fragment", "rarity": 0}
    if iid in _AUTHORITATIVE_ITEM_MAP:
        info = _AUTHORITATIVE_ITEM_MAP[iid]
        return {"item_id": iid, "name": info["name"], "category": info["category"], "rarity": info["rarity"]}
    name = f"Item #{iid}"
    prefix = iid // 1_000_000
    cat = "General"
    if prefix in (101, 102):
        cat = "Avatar"
    elif prefix in (203, 204, 205, 208, 211):
        cat = "Clothes"
    elif prefix in (700, 710):
        cat = "Bundle"
    elif prefix == 907:
        cat = "GunSkin"
    elif prefix in (800, 802, 808):
        cat = "Consumable"
    return {"item_id": iid, "name": name, "category": cat, "rarity": 0}


# ---------------------------------------------------------------------------
# Luck Royale Admin Service Implementation
# ---------------------------------------------------------------------------

class LuckRoyaleAdminManager(ILuckRoyaleAdminService):
    """
    Central administrator manager implementing ILuckRoyaleAdminService.
    Integrates directly with core_arch registry and config_manager.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._disabled_machines: set[int] = set()
        self._events: Dict[int, Dict[str, Any]] = {}
        self._banner_assignments: Dict[int, str] = {
            CHEST_DIAMOND_ROYALE: "UI_Lottery_Poster_P.png",
            CHEST_WEAPON_ROYALE: "UI_Lottery_Poster_W.png",
            CHEST_GOLD_ROYALE: "UI_Lottery_Poster_G.png",
            CHEST_INCUBATOR: "luck_royale_banner.png",
        }
        self._machine_artwork: Dict[int, Dict[str, str]] = {}
        self._reward_images: Dict[int, str] = {}
        self._load_admin_state()

    def _load_admin_state(self) -> None:
        with self._lock:
            if not os.path.exists(ADMIN_STATE_FILE):
                return
            try:
                with open(ADMIN_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._disabled_machines = {int(x) for x in data.get("disabled_machines", [])}
                self._banner_assignments.update({int(k): str(v) for k, v in data.get("banner_assignments", {}).items()})
                self._events = {int(k): v for k, v in data.get("events", {}).items()}
                self._machine_artwork = {int(k): v for k, v in data.get("machine_artwork", {}).items()}
                self._reward_images = {int(k): str(v) for k, v in data.get("reward_images", {}).items()}
            except Exception as exc:
                logger.warning("Failed to load admin state: %s", exc)

    def _save_admin_state(self) -> None:
        with self._lock:
            try:
                os.makedirs(_DATA_DIR, exist_ok=True)
                payload = {
                    "updated_at": int(time.time()),
                    "disabled_machines": sorted(list(self._disabled_machines)),
                    "banner_assignments": {str(k): v for k, v in self._banner_assignments.items()},
                    "events": {str(k): v for k, v in self._events.items()},
                    "machine_artwork": {str(k): v for k, v in self._machine_artwork.items()},
                    "reward_images": {str(k): v for k, v in self._reward_images.items()},
                }
                tmp = f"{ADMIN_STATE_FILE}.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                os.replace(tmp, ADMIN_STATE_FILE)
            except Exception as exc:
                logger.error("Failed to save admin state: %s", exc)

    # -----------------------------------------------------------------------
    # Serialization Helpers
    # -----------------------------------------------------------------------

    def _serialize_show_item(self, it: GachaShowItemConfig) -> Dict[str, Any]:
        meta = _get_item_meta(it.item_id)
        iid = int(it.item_id)
        assigned = self._reward_images.get(iid)
        if assigned:
            img_url = assigned if assigned.startswith("/") else f"/banners/{assigned}"
            img_src = "custom_assigned"
        else:
            # 1. Check authentic extracted items
            m_items = _AUTHENTIC_MANIFEST.get("items", {})
            m_debris = _AUTHENTIC_MANIFEST.get("debris", {})
            if str(iid) in m_items and m_items[str(iid)].get("verified"):
                img_url = m_items[str(iid)]["url"]
                img_src = "authentic_extracted"
            elif str(iid) in m_debris and m_debris[str(iid)].get("verified"):
                img_url = m_debris[str(iid)]["url"]
                img_src = "authentic_extracted"
            elif os.path.isfile(os.path.join(_STATIC_DIR, "assets", "freefire", "1.39", "items", f"{iid}.png")):
                img_url = f"/assets/freefire/1.39/items/{iid}.png"
                img_src = "authentic_extracted"
            elif iid in DEFAULT_ITEM_IMAGES:
                img_url = f"/banners/{DEFAULT_ITEM_IMAGES[iid]}"
                img_src = "default_catalog"
            else:
                img_url = "/assets/freefire/1.39/ui/UI_Lottery_item_bg.png"
                img_src = "category_fallback"

        clean_fn = os.path.basename(img_url)
        if img_url.startswith("/assets/"):
            rel_path = img_url.lstrip("/")
            exists = os.path.isfile(os.path.join(_STATIC_DIR, rel_path))
        else:
            exists = os.path.isfile(os.path.join(_BANNERS_DIR, clean_fn)) or os.path.isfile(os.path.join(_BANNERS_DIR, "uploads", clean_fn))

        return {
            "item_id": it.item_id,
            "item_num": it.item_num,
            "item_type": it.item_type,
            "reward_level": it.reward_level,
            "rarity_label": "Super Rare" if it.reward_level == RareType.SUPER_RARE else ("Rare" if it.reward_level == RareType.RARE else "Normal"),
            "weight": it.weight,
            "drop_up_ratio": it.drop_up_ratio,
            "repeated_item_id": it.repeated_item_id,
            "repeated_item_num": it.repeated_item_num,
            "is_show": it.is_show,
            "turntable_props_type": it.turntable_props_type,
            "name": meta["name"],
            "category": meta["category"],
            "image_url": img_url,
            "image_source": img_src,
            "image_exists": exists,
            "image_name": clean_fn,
        }

    def _serialize_extra_reward(self, er: ExtraRewardConfig) -> Dict[str, Any]:
        meta = _get_item_meta(er.reward_id)
        return {
            "condition_num": er.cdt_value,
            "reward_id": er.reward_id,
            "reward_num": er.reward_num,
            "reward_type": er.reward_type,
            "condition_type": er.cdt_type,
            "icon": er.icon,
            "special_reward": er.special_reward,
            "name": meta["name"],
        }

    def _serialize_chest_config(self, cfg: ChestConfig) -> Dict[str, Any]:
        cid = cfg.chest_id
        is_active = cid not in self._disabled_machines
        banner = self._banner_assignments.get(cid, "luck_royale_banner.png")
        return {
            "chest_id": cfg.chest_id,
            "chest_sub_id": cfg.chest_sub_id,
            "priority": cfg.priority,
            "coin_type": cfg.coin_type,
            "coin_type_label": "Diamonds" if cfg.coin_type == CoinType.GEMS else "Gold",
            "chest_name": cfg.chest_name,
            "display_name": self._friendly_chest_name(cfg),
            "exchange_itemid": cfg.exchange_itemid,
            "exchange_item_name": VOUCHER_NAMES.get(cfg.exchange_itemid, f"Voucher #{cfg.exchange_itemid}"),
            "free_type": cfg.free_type,
            "once_price": cfg.once_price,
            "ten_price": cfg.ten_price,
            "discount_price_one": cfg.discount_price_one,
            "discount_price_ten": cfg.discount_price_ten,
            "exchange_once_num": cfg.exchange_once_num,
            "exchange_ten_num": cfg.exchange_ten_num,
            "once_num": cfg.once_num,
            "ten_num": cfg.ten_num,
            "color_id": cfg.color_id,
            "chest_model_id": cfg.chest_model_id,
            "chest_model_id2": cfg.chest_model_id2,
            "chest_model_id3": cfg.chest_model_id3,
            "show_model_male": cfg.show_model_male,
            "show_model_female": cfg.show_model_female,
            "rare_item_max": cfg.rare_item_max,
            "chest_type_enum": cfg.chest_type_enum,
            "chest_type_label": "Incubator Turntable" if cfg.chest_type_enum == ChestTabType.TURNTABLE else "Standard Royale",
            "forge_tab_id": cfg.forge_tab_id,
            "must_drop": cfg.must_drop,
            "extra_reward": cfg.extra_reward,
            "first_reward_switch": cfg.first_reward_switch,
            "first_reward_max": cfg.first_reward_max,
            "enabled": is_active,
            "banner_file": banner,
            "banner_url": f"/banners/{banner}",
            "artwork": self.get_machine_artwork(cid),
            "event": self._events.get(cid, None),
            "items_count": len(cfg.items),
            "extra_rewards_count": len(cfg.extra_rewards),
            "items": [self._serialize_show_item(it) for it in cfg.items],
            "extra_rewards": [self._serialize_extra_reward(er) for er in cfg.extra_rewards],
            "probabilities": list(cfg.probabilities),
        }

    def _friendly_chest_name(self, cfg: ChestConfig) -> str:
        if cfg.chest_id == CHEST_DIAMOND_ROYALE:
            return "Diamond Royale"
        if cfg.chest_id == CHEST_WEAPON_ROYALE:
            return "Weapon Royale"
        if cfg.chest_id == CHEST_GOLD_ROYALE:
            return "Gold Royale"
        if cfg.chest_id == CHEST_INCUBATOR:
            return "Incubator (YinYang & Joker)"
        raw = str(cfg.chest_name or "")
        return raw.replace("TXT_CHEST_NAME_", "").replace("T_12_Z_CHEST_", "").title() or f"Machine #{cfg.chest_id}"

    # -----------------------------------------------------------------------
    # 1. Overview API
    # -----------------------------------------------------------------------

    def get_overview(self) -> Dict[str, Any]:
        """Summary statistics of Luck Royale operation."""
        with self._lock:
            tx_list = db.get_gacha_transactions(limit=1000)
            total_spins = 0
            single_spins = 0
            multi_spins = 0
            diamonds_burn = 0
            gold_burn = 0
            vouchers_burn = 0
            vouchers_breakdown: Dict[str, int] = {}
            jackpots_count = 0
            spun_accounts: set[int] = set()

            for tx in tx_list:
                spun_accounts.add(tx["account_id"])
                gtype = tx.get("gacha_type", 1)
                cost_type = tx.get("cost_type", 0)
                cost_amount = tx.get("cost_amount", 0)
                if gtype == LotteryType.ONE:
                    single_spins += 1
                    total_spins += 1
                else:
                    multi_spins += 1
                    total_spins += 10

                if tx.get("has_big_reward"):
                    jackpots_count += 1

                if cost_type == CoinType.GEMS:
                    diamonds_burn += cost_amount
                elif cost_type == CoinType.COINS:
                    gold_burn += cost_amount
                elif tx.get("consume_type") == ConsumeType.EXCHANGE_ITEM:
                    vouchers_burn += cost_amount
                    cid = str(tx.get("chest_id", 0))
                    vouchers_breakdown[cid] = vouchers_breakdown.get(cid, 0) + cost_amount

            if total_spins == 0:
                audit_spins = db.get_audit_logs(action_type="GACHA_SPIN", limit=500)
                for al in audit_spins:
                    total_spins += 1
                    payload = al.get("payload") or {}
                    spun_accounts.add(al.get("account_id", DEFAULT_ACCOUNT_ID))
                    drawn = payload.get("total_drawn", 1)
                    if drawn > 1:
                        multi_spins += 1
                    else:
                        single_spins += 1

            all_machines = registry.get_all_machines()
            total_machines = len(all_machines)
            disabled_count = len([m for m in all_machines if m.chest_id in self._disabled_machines])
            active_count = max(0, total_machines - disabled_count)

            exchange_count = 0
            try:
                cur = db._get_conn().cursor()
                cur.execute("SELECT COUNT(*) as cnt FROM gacha_special_exchanges;")
                r = cur.fetchone()
                if r:
                    exchange_count = int(r["cnt"])
            except Exception:
                pass

            active_machines_summary = []
            for cfg in all_machines:
                if cfg.chest_id not in self._disabled_machines:
                    active_machines_summary.append({
                        "chest_id": cfg.chest_id,
                        "name": self._friendly_chest_name(cfg),
                        "coin_type": "Diamonds" if cfg.coin_type == CoinType.GEMS else "Gold",
                        "once_price": cfg.once_price,
                        "ten_price": cfg.ten_price,
                        "lucky_meter_cap": cfg.rare_item_max,
                        "pool_items_count": len(cfg.items),
                    })

            return {
                "ok": True,
                "summary": {
                    "total_spins": total_spins,
                    "total_single_spins": single_spins,
                    "total_multi_spins": multi_spins,
                    "diamonds_burned": diamonds_burn,
                    "gold_burned": gold_burn,
                    "vouchers_burned": vouchers_burn,
                    "vouchers_breakdown": vouchers_breakdown,
                    "active_machines_count": active_count,
                    "disabled_machines_count": disabled_count,
                    "total_machines_count": total_machines,
                    "total_jackpots_awarded": jackpots_count,
                    "total_exchange_operations": exchange_count,
                    "unique_players_spun": len(spun_accounts),
                },
                "active_machines": active_machines_summary,
                "recent_transactions": tx_list[:10],
                "server_time": int(time.time()),
            }

    # -----------------------------------------------------------------------
    # 2. Machine Manager (CRUD, Toggle, Duplicate)
    # -----------------------------------------------------------------------

    def list_machines(self, include_disabled: bool = True) -> List[Dict[str, Any]]:
        with self._lock:
            result = []
            for cfg in sorted(registry.get_all_machines(), key=lambda c: c.priority, reverse=True):
                if not include_disabled and cfg.chest_id in self._disabled_machines:
                    continue
                result.append(self._serialize_chest_config(cfg))
            return result

    def get_machine(self, chest_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cfg = registry.get_machine(int(chest_id))
            if not cfg:
                return None
            return self._serialize_chest_config(cfg)

    def create_machine(self, data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with self._lock:
            raw_cid = data.get("chest_id")
            if raw_cid is None:
                return False, "chest_id is required", None
            try:
                chest_id = int(raw_cid)
            except ValueError:
                return False, "chest_id must be an integer", None

            if chest_id <= 0:
                return False, "chest_id must be a positive integer", None

            if registry.get_machine(chest_id) is not None:
                return False, f"Machine with chest_id {chest_id} already exists", None

            chest_name = str(data.get("chest_name") or f"CHEST_{chest_id}").strip()
            if not chest_name:
                return False, "chest_name cannot be empty", None

            coin_type = int(data.get("coin_type", CoinType.GEMS))
            if coin_type not in (CoinType.COINS, CoinType.GEMS):
                return False, "coin_type must be 1 (Gold) or 2 (Diamonds)", None

            items_list: List[GachaShowItemConfig] = []
            if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
                for it in data["items"]:
                    items_list.append(
                        GachaShowItemConfig(
                            item_id=int(it["item_id"]),
                            item_num=max(1, int(it.get("item_num", 1))),
                            item_type=int(it.get("item_type", AwardType.ITEM)),
                            is_show=bool(it.get("is_show", True)),
                            reward_level=int(it.get("reward_level", RareType.NORMAL)),
                            repeated_item_id=int(it.get("repeated_item_id", ITEM_FF_TOKEN)),
                            repeated_item_num=max(1, int(it.get("repeated_item_num", 5))),
                            turntable_props_type=int(it.get("turntable_props_type", 0)),
                            drop_up_ratio=float(it.get("drop_up_ratio", 0.0)),
                            weight=max(1, int(it.get("weight", 100))),
                        )
                    )
            else:
                items_list.append(GachaShowItemConfig(item_id=ITEM_FF_TOKEN, item_num=5, weight=100))

            extra_list: List[ExtraRewardConfig] = []
            if "extra_rewards" in data and isinstance(data["extra_rewards"], list):
                for er in data["extra_rewards"]:
                    extra_list.append(
                        ExtraRewardConfig(
                            cdt_value=int(er.get("condition_num") or er.get("cdt_value") or 5),
                            reward_id=int(er.get("reward_id", 0)),
                            reward_num=max(1, int(er.get("reward_num", 1))),
                            reward_type=int(er.get("reward_type", AwardType.ITEM)),
                            cdt_type=int(er.get("condition_type") or er.get("cdt_type") or 1),
                            icon=str(er.get("icon", "")),
                            special_reward=str(er.get("special_reward", "")),
                        )
                    )

            new_cfg = ChestConfig(
                chest_id=chest_id,
                chest_sub_id=int(data.get("chest_sub_id", 1)),
                priority=int(data.get("priority", 50)),
                coin_type=coin_type,
                chest_name=chest_name,
                exchange_itemid=int(data.get("exchange_itemid", 0)),
                free_type=int(data.get("free_type", 0)),
                once_price=max(0, int(data.get("once_price", 60))),
                ten_price=max(0, int(data.get("ten_price", 600))),
                exchange_once_num=max(1, int(data.get("exchange_once_num", 1))),
                exchange_ten_num=max(1, int(data.get("exchange_ten_num", 10))),
                color_id=int(data.get("color_id", 1)),
                chest_model_id=int(data.get("chest_model_id", 203000374)),
                chest_model_id2=int(data.get("chest_model_id2", 0)),
                chest_model_id3=int(data.get("chest_model_id3", 0)),
                show_model_male=int(data.get("show_model_male", 102000010)),
                show_model_female=int(data.get("show_model_female", 101000010)),
                rare_item_max=max(1, int(data.get("rare_item_max", 150))),
                chest_type_enum=int(data.get("chest_type_enum", ChestTabType.NORMAL)),
                forge_tab_id=int(data.get("forge_tab_id", 0)),
                once_num=max(1, int(data.get("once_num", 1))),
                ten_num=max(1, int(data.get("ten_num", 10))),
                discount_price_one=int(data.get("discount_price_one", 0)),
                discount_price_ten=int(data.get("discount_price_ten", 0)),
                must_drop=bool(data.get("must_drop", True)),
                extra_reward=bool(data.get("extra_reward", True)),
                first_reward_switch=bool(data.get("first_reward_switch", False)),
                first_reward_max=int(data.get("first_reward_max", 3)),
                items=tuple(items_list),
                extra_rewards=tuple(extra_list),
            )

            is_valid, errs = validate_machine_config(new_cfg)
            if not is_valid:
                return False, f"Validation errors: {', '.join(errs)}", None

            config_manager.set_machine(new_cfg)
            registry.register_machine(new_cfg)

            if not bool(data.get("enabled", True)):
                self._disabled_machines.add(chest_id)
            else:
                self._disabled_machines.discard(chest_id)

            if data.get("banner_file"):
                self._banner_assignments[chest_id] = str(data["banner_file"]).strip()

            self._save_admin_state()
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_MACHINE_CREATE",
                f"Created Luck Royale machine {chest_id} ({chest_name})",
                {"chest_id": chest_id, "chest_name": chest_name, "coin_type": coin_type},
            )
            return True, "Machine created successfully", self._serialize_chest_config(new_cfg)

    def update_machine(self, machine_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create or update a machine configuration (ILuckRoyaleAdminService)."""
        cid = int(machine_data.get("chest_id", 0))
        ok, msg, _ = self.update_machine_with_result(cid, machine_data)
        return ok, msg

    def update_machine_with_result(
        self,
        chest_id: int,
        data: Dict[str, Any],
        operator_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with self._lock:
            cid = int(chest_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine with chest_id {cid} not found", None

            cur_dict = {k: v for k, v in cfg.__dict__.items()}
            for k in (
                "chest_name", "priority", "coin_type", "once_price", "ten_price",
                "discount_price_one", "discount_price_ten", "rare_item_max",
                "must_drop", "first_reward_switch", "first_reward_max", "free_type",
                "exchange_itemid", "exchange_once_num", "exchange_ten_num",
                "color_id", "chest_model_id", "chest_type_enum", "forge_tab_id"
            ):
                if k in data:
                    cur_dict[k] = data[k]

            updated_cfg = ChestConfig(**cur_dict)
            is_valid, errs = validate_machine_config(updated_cfg)
            if not is_valid:
                return False, f"Validation errors: {', '.join(errs)}", None

            config_manager.set_machine(updated_cfg)
            registry.register_machine(updated_cfg)

            if "enabled" in data:
                if bool(data["enabled"]):
                    self._disabled_machines.discard(cid)
                else:
                    self._disabled_machines.add(cid)

            if "banner_file" in data:
                self._banner_assignments[cid] = str(data["banner_file"]).strip()

            self._save_admin_state()
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_MACHINE_UPDATE",
                f"Updated Luck Royale machine {cid}",
                {"chest_id": cid, "updated_fields": list(data.keys())},
            )
            return True, "Machine updated successfully", self._serialize_chest_config(updated_cfg)

    def delete_machine(self, chest_id: int, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str]:
        with self._lock:
            cid = int(chest_id)
            if registry.get_machine(cid) is None:
                return False, f"Machine with chest_id {cid} not found"

            config_manager.remove_machine(cid)
            registry.unregister_machine(cid)
            self._disabled_machines.discard(cid)
            self._banner_assignments.pop(cid, None)
            self._events.pop(cid, None)
            self._save_admin_state()

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_MACHINE_DELETE",
                f"Deleted Luck Royale machine {cid}",
                {"chest_id": cid},
            )
            return True, f"Machine {cid} deleted successfully"

    def toggle_machine(self, chest_id: int, enabled: Optional[bool] = None, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, bool]:
        with self._lock:
            cid = int(chest_id)
            if registry.get_machine(cid) is None:
                return False, f"Machine with chest_id {cid} not found", False

            if enabled is None:
                new_state = cid in self._disabled_machines
            else:
                new_state = bool(enabled)

            if new_state:
                self._disabled_machines.discard(cid)
            else:
                self._disabled_machines.add(cid)

            self._save_admin_state()
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_MACHINE_TOGGLE",
                f"Toggled Luck Royale machine {cid} enabled={new_state}",
                {"chest_id": cid, "enabled": new_state},
            )
            return True, f"Machine {cid} enabled={new_state}", new_state

    def duplicate_machine(
        self,
        source_chest_id: int,
        new_chest_id: int,
        new_chest_name: str,
        operator_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with self._lock:
            src_cid = int(source_chest_id)
            tgt_cid = int(new_chest_id)

            src_cfg = registry.get_machine(src_cid)
            if not src_cfg:
                return False, f"Source machine {src_cid} not found", None
            if registry.get_machine(tgt_cid) is not None:
                return False, f"Target chest_id {tgt_cid} already exists", None
            if tgt_cid <= 0:
                return False, "Target chest_id must be a positive integer", None

            new_dict = {k: v for k, v in src_cfg.__dict__.items()}
            new_dict["chest_id"] = tgt_cid
            new_dict["chest_name"] = new_chest_name.strip() or f"Copy of {src_cfg.chest_name}"

            new_cfg = ChestConfig(**new_dict)
            config_manager.set_machine(new_cfg)
            registry.register_machine(new_cfg)
            self._disabled_machines.discard(tgt_cid)
            self._save_admin_state()

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_MACHINE_DUPLICATE",
                f"Duplicated Luck Royale machine {src_cid} to {tgt_cid} ({new_dict['chest_name']})",
                {"source_chest_id": src_cid, "new_chest_id": tgt_cid, "name": new_dict["chest_name"]},
            )
            return True, "Machine duplicated successfully", self._serialize_chest_config(new_cfg)

    # -----------------------------------------------------------------------
    # 3. Reward Pool Management
    # -----------------------------------------------------------------------

    def get_reward_pool(self, chest_id: Optional[int] = None) -> Dict[str, Any]:
        with self._lock:
            if chest_id is not None:
                cid = int(chest_id)
                cfg = registry.get_machine(cid)
                if not cfg:
                    return {"ok": False, "error": f"Machine {cid} not found"}
                return {
                    "ok": True,
                    "chest_id": cid,
                    "chest_name": self._friendly_chest_name(cfg),
                    "items": [self._serialize_show_item(it) for it in cfg.items],
                }

            pools = {}
            for cfg in registry.get_all_machines():
                pools[cfg.chest_id] = {
                    "chest_id": cfg.chest_id,
                    "chest_name": self._friendly_chest_name(cfg),
                    "items_count": len(cfg.items),
                    "items": [self._serialize_show_item(it) for it in cfg.items],
                }
            return {"ok": True, "pools": pools}

    def update_reward_pool(self, chest_id: int, items_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Update items and probabilities for a machine's reward pool (ILuckRoyaleAdminService)."""
        with self._lock:
            cid = int(chest_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found"

            new_items = []
            for it in items_data:
                new_items.append(
                    GachaShowItemConfig(
                        item_id=int(it["item_id"]),
                        item_num=max(1, int(it.get("item_num", 1))),
                        item_type=int(it.get("item_type", AwardType.ITEM)),
                        is_show=bool(it.get("is_show", True)),
                        reward_level=int(it.get("reward_level", RareType.NORMAL)),
                        repeated_item_id=int(it.get("repeated_item_id", ITEM_FF_TOKEN)),
                        repeated_item_num=max(1, int(it.get("repeated_item_num", 5))),
                        turntable_props_type=int(it.get("turntable_props_type", 0)),
                        drop_up_ratio=float(it.get("drop_up_ratio", 0.0)),
                        weight=max(1, int(it.get("weight", 100))),
                    )
                )

            updated_cfg = ChestConfig(
                **{k: v for k, v in cfg.__dict__.items() if k != "items"},
                items=tuple(new_items),
            )
            config_manager.set_machine(updated_cfg)
            registry.register_machine(updated_cfg)
            return True, "Reward pool updated successfully"

    def add_pool_item(self, chest_id: int, item_data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with self._lock:
            cid = int(chest_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found", None

            raw_item_id = item_data.get("item_id")
            if raw_item_id is None:
                return False, "item_id is required", None
            try:
                item_id = int(raw_item_id)
            except ValueError:
                return False, "item_id must be an integer", None

            raw_rep_id = item_data.get("repeated_item_id")
            rep_id = int(raw_rep_id) if raw_rep_id is not None else 0
            rep_num = max(1, int(item_data.get("repeated_item_num", 5)))
            if cid == CHEST_GOLD_ROYALE and (100000000 <= item_id < 200000000):
                # ABSOLUTE RULE: Gold Royale duplicate character rewards must produce character-specific fragments (debris 800000000+), NEVER generic FF Tokens
                debris_id = get_character_debris_id(item_id)
                if not debris_id:
                    return False, f"Character {item_id} has no valid debris mapping or is excluded from Gold Royale", None
                rep_id = debris_id
                rep_num = max(5, rep_num)
            elif not rep_id:
                rep_id = ITEM_FF_TOKEN

            new_item = GachaShowItemConfig(
                item_id=item_id,
                item_num=max(1, int(item_data.get("item_num", 1))),
                item_type=int(item_data.get("item_type", AwardType.ITEM)),
                is_show=bool(item_data.get("is_show", True)),
                reward_level=int(item_data.get("reward_level", RareType.NORMAL)),
                repeated_item_id=rep_id,
                repeated_item_num=rep_num,
                turntable_props_type=int(item_data.get("turntable_props_type", 0)),
                drop_up_ratio=float(item_data.get("drop_up_ratio", 0.0)),
                weight=max(1, int(item_data.get("weight", 100))),
            )

            current_items = list(cfg.items)
            current_items.append(new_item)

            updated_cfg = ChestConfig(
                **{k: v for k, v in cfg.__dict__.items() if k != "items"},
                items=tuple(current_items),
            )
            config_manager.set_machine(updated_cfg)
            registry.register_machine(updated_cfg)

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_POOL_ADD_ITEM",
                f"Added item {item_id} to machine {cid} reward pool",
                {"chest_id": cid, "item_id": item_id, "weight": new_item.weight, "rarity": new_item.reward_level},
            )
            return True, "Item added to reward pool successfully", self._serialize_show_item(new_item)

    def update_pool_item(self, chest_id: int, item_id: int, item_data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with self._lock:
            cid = int(chest_id)
            iid = int(item_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found", None

            items_list = list(cfg.items)
            target_idx = next((i for i, it in enumerate(items_list) if it.item_id == iid), None)
            if target_idx is None:
                return False, f"Item {iid} not found in machine {cid} pool", None

            old_it = items_list[target_idx]
            raw_rep = item_data.get("repeated_item_id")
            rep_id = int(raw_rep) if raw_rep is not None else old_it.repeated_item_id
            rep_num = int(item_data.get("repeated_item_num", old_it.repeated_item_num))
            if cid == CHEST_GOLD_ROYALE and (100000000 <= old_it.item_id < 200000000):
                # ABSOLUTE RULE: Gold Royale duplicate character rewards must produce character-specific fragments (debris 800000000+), NEVER generic FF Tokens
                debris_id = get_character_debris_id(old_it.item_id)
                if not debris_id:
                    return False, f"Character {old_it.item_id} has no valid debris mapping or is excluded from Gold Royale", None
                rep_id = debris_id
                rep_num = max(5, rep_num)
            elif not rep_id:
                rep_id = ITEM_FF_TOKEN

            updated_it = GachaShowItemConfig(
                item_id=old_it.item_id,
                item_num=int(item_data.get("item_num", old_it.item_num)),
                item_type=int(item_data.get("item_type", old_it.item_type)),
                is_show=bool(item_data.get("is_show", old_it.is_show)),
                reward_level=int(item_data.get("reward_level", old_it.reward_level)),
                repeated_item_id=rep_id,
                repeated_item_num=rep_num,
                turntable_props_type=int(item_data.get("turntable_props_type", old_it.turntable_props_type)),
                drop_up_ratio=float(item_data.get("drop_up_ratio", old_it.drop_up_ratio)),
                weight=max(1, int(item_data.get("weight", old_it.weight))),
            )
            items_list[target_idx] = updated_it

            updated_cfg = ChestConfig(
                **{k: v for k, v in cfg.__dict__.items() if k != "items"},
                items=tuple(items_list),
            )
            config_manager.set_machine(updated_cfg)
            registry.register_machine(updated_cfg)

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_POOL_UPDATE_ITEM",
                f"Updated item {iid} in machine {cid} reward pool",
                {"chest_id": cid, "item_id": iid, "weight": updated_it.weight},
            )
            return True, "Pool item updated successfully", self._serialize_show_item(updated_it)

    def remove_pool_item(self, chest_id: int, item_id: int, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str]:
        with self._lock:
            cid = int(chest_id)
            iid = int(item_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found"

            filtered = [it for it in cfg.items if it.item_id != iid]
            if len(filtered) == len(cfg.items):
                return False, f"Item {iid} not found in machine {cid} pool"

            updated_cfg = ChestConfig(
                **{k: v for k, v in cfg.__dict__.items() if k != "items"},
                items=tuple(filtered),
            )
            config_manager.set_machine(updated_cfg)
            registry.register_machine(updated_cfg)

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_POOL_REMOVE_ITEM",
                f"Removed item {iid} from machine {cid} reward pool",
                {"chest_id": cid, "item_id": iid},
            )
            return True, f"Item {iid} removed from machine {cid} pool"

    # -----------------------------------------------------------------------
    # 4. Lucky Meters
    # -----------------------------------------------------------------------

    def get_lucky_meters(self, chest_id: Optional[int] = None, account_id: Optional[int] = None) -> Dict[str, Any]:
        with self._lock:
            aid = int(account_id or DEFAULT_ACCOUNT_ID)
            gacha_states = db.get_all_gacha_states(aid)

            result = []
            targets = [registry.get_machine(chest_id)] if chest_id is not None else registry.get_all_machines()
            for cfg in targets:
                if not cfg:
                    continue
                cid = cfg.chest_id
                user_state = gacha_states.get(cid, {})
                not_got = int(user_state.get("not_got_num", 0))
                cap = cfg.rare_item_max
                pct = min(100.0, round((not_got / cap) * 100.0, 1)) if cap > 0 else 0.0
                rem = max(0, cap - not_got)

                result.append({
                    "chest_id": cid,
                    "chest_name": self._friendly_chest_name(cfg),
                    "rare_item_max": cap,
                    "must_drop_jackpot": cfg.must_drop,
                    "current_user_meter": not_got,
                    "progress_percentage": pct,
                    "spins_to_guaranteed": rem,
                    "reset_behavior": "Resets to 0 upon Rare / Super Rare drop",
                    "weekly_spins": int(user_state.get("lottery_count_weekly", 0)),
                    "next_free_time": int(user_state.get("next_free_time", 0)),
                })
            return {"ok": True, "account_id": aid, "meters": result}

    def adjust_lucky_meter(self, account_id: int, chest_id: int, value: int) -> Tuple[bool, str]:
        """Manually adjust a player's lucky meter value (ILuckRoyaleAdminService)."""
        aid = int(account_id)
        cid = int(chest_id)
        val = max(0, int(value))
        st = db.get_all_gacha_states(aid).get(cid, {})
        st["not_got_num"] = val
        db.save_gacha_state(aid, cid, st)
        return True, f"Account {aid} lucky meter set to {val} for machine {cid}"

    def update_lucky_meter_config(self, data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str]:
        with self._lock:
            cid = int(data.get("chest_id", 0))
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found"

            updated_kwargs = {k: v for k, v in cfg.__dict__.items()}
            if "rare_item_max" in data:
                updated_kwargs["rare_item_max"] = max(1, int(data["rare_item_max"]))
            if "must_drop" in data:
                updated_kwargs["must_drop"] = bool(data["must_drop"])

            new_cfg = ChestConfig(**updated_kwargs)
            config_manager.set_machine(new_cfg)
            registry.register_machine(new_cfg)

            if "account_id" in data and "not_got_num" in data:
                aid = int(data["account_id"])
                self.adjust_lucky_meter(aid, cid, int(data["not_got_num"]))

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_METER_UPDATE",
                f"Updated lucky meter settings for machine {cid}",
                data,
            )
            return True, f"Lucky meter settings updated for machine {cid}"

    # -----------------------------------------------------------------------
    # 5. Currency & Voucher Portfolio & Grant / Deduct
    # -----------------------------------------------------------------------

    def get_currencies_and_vouchers(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._lock:
            aid = int(account_id)
            prof = state.get_player(aid) or state.get_profile(aid) or {}
            gold = state.get_gold(aid)
            diamonds = state.get_diamond(aid)

            vouchers = {
                "gold_royale_voucher": {
                    "item_id": VOUCHER_CANONICAL_IDS["gold_royale"],
                    "count": state.get_item_count(VOUCHER_CANONICAL_IDS["gold_royale"], aid) + state.get_item_count(VOUCHER_LEGACY_IDS["gold_royale"], aid),
                    "name": "Gold Royale Voucher",
                },
                "diamond_royale_voucher": {
                    "item_id": VOUCHER_CANONICAL_IDS["diamond_royale"],
                    "count": state.get_item_count(VOUCHER_CANONICAL_IDS["diamond_royale"], aid) + state.get_item_count(VOUCHER_LEGACY_IDS["diamond_royale"], aid),
                    "name": "Diamond Royale Voucher",
                },
                "weapon_royale_voucher": {
                    "item_id": VOUCHER_CANONICAL_IDS["weapon_royale"],
                    "count": state.get_item_count(VOUCHER_CANONICAL_IDS["weapon_royale"], aid) + state.get_item_count(VOUCHER_LEGACY_IDS["weapon_royale"], aid),
                    "name": "Weapon Royale Voucher",
                },
                "incubator_voucher": {
                    "item_id": VOUCHER_CANONICAL_IDS["incubator"],
                    "count": state.get_item_count(VOUCHER_CANONICAL_IDS["incubator"], aid) + state.get_item_count(VOUCHER_LEGACY_IDS["incubator"], aid),
                    "name": "Incubator Voucher",
                },
            }

            tokens_and_materials = {
                "ff_token": {
                    "item_id": 110200001,
                    "count": state.get_item_count(110200001, aid) + state.get_item_count(800000301, aid),
                    "name": "FF Token",
                },
                "magic_cube": {
                    "item_id": 800000304,
                    "count": state.get_item_count(800000304, aid),
                    "name": "Magic Cube",
                },
                "evolution_stone": {
                    "item_id": 808000003,
                    "count": state.get_item_count(808000003, aid) + state.get_item_count(808000001, aid),
                    "name": "Evolution Stone",
                },
                "blueprint_yinyang": {
                    "item_id": 808000001,
                    "count": state.get_item_count(808000001, aid) + state.get_item_count(808000011, aid),
                    "name": "Blueprint: YinYang",
                },
                "blueprint_joker": {
                    "item_id": 808000002,
                    "count": state.get_item_count(808000002, aid) + state.get_item_count(808000012, aid),
                    "name": "Blueprint: Joker",
                },
            }

            return {
                "ok": True,
                "account_id": aid,
                "nickname": prof.get("nickname", f"Player_{aid}"),
                "gold": gold,
                "diamonds": diamonds,
                "vouchers": vouchers,
                "tokens_and_materials": tokens_and_materials,
            }

    def adjust_currency_or_voucher(self, data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Dict[str, Any]]:
        with self._lock:
            aid = int(data.get("account_id") or DEFAULT_ACCOUNT_ID)
            action = str(data.get("action") or "grant").lower().strip()
            ctype = str(data.get("currency_type") or data.get("type") or "").lower().strip()
            raw_amt = data.get("amount")

            if raw_amt is None:
                return False, "amount is required", {}
            try:
                amt = int(raw_amt)
            except ValueError:
                return False, "amount must be an integer", {}

            if amt <= 0:
                return False, "amount must be a positive integer", {}

            reason = str(data.get("reason") or f"Admin {action} by #{operator_id}").strip()

            # 1. Diamonds
            if ctype in ("diamond", "diamonds", "gems"):
                cur_dia = state.get_diamond(aid)
                if action == "deduct":
                    if cur_dia < amt:
                        return False, f"Insufficient diamond balance (Current: {cur_dia}, Requested deduction: {amt})", {}
                    new_val = state.modify_diamond(aid, -amt)
                else:
                    new_val = state.modify_diamond(aid, amt)
                db.log_action(
                    aid,
                    "ADMIN_LUCK_ROYALE_WALLET_ADJUST",
                    f"{action.upper()} {amt} Diamonds ({reason})",
                    {"action": action, "type": "diamonds", "amount": amt, "balance": new_val, "reason": reason},
                )
                return True, f"Successfully {action}ed {amt} Diamonds", self.get_currencies_and_vouchers(aid)

            # 2. Gold
            if ctype in ("gold", "coins"):
                cur_gold = state.get_gold(aid)
                if action == "deduct":
                    if cur_gold < amt:
                        return False, f"Insufficient gold balance (Current: {cur_gold}, Requested deduction: {amt})", {}
                    new_val = state.modify_gold(aid, -amt)
                else:
                    new_val = state.modify_gold(aid, amt)
                db.log_action(
                    aid,
                    "ADMIN_LUCK_ROYALE_WALLET_ADJUST",
                    f"{action.upper()} {amt} Gold ({reason})",
                    {"action": action, "type": "gold", "amount": amt, "balance": new_val, "reason": reason},
                )
                return True, f"Successfully {action}ed {amt} Gold", self.get_currencies_and_vouchers(aid)

            # 3. Vouchers & Stackable Items
            item_id = None
            if "item_id" in data and str(data["item_id"]).strip():
                item_id = int(data["item_id"])
            elif "voucher_name" in data:
                vn = str(data["voucher_name"]).lower().strip().replace(" ", "_")
                item_id = VOUCHER_CANONICAL_IDS.get(vn)

            if item_id is None:
                return False, "item_id or valid voucher_name is required for voucher/item adjustment", {}

            cur_cnt = state.get_item_count(item_id, aid)
            if action == "deduct":
                if cur_cnt < amt:
                    return False, f"Insufficient inventory count (Current: {cur_cnt}, Requested deduction: {amt})", {}
                new_cnt = max(0, cur_cnt - amt)
                try:
                    from core.player import player_manager
                    p = player_manager.get_player(aid)
                    if p:
                        with p._lock:
                            if new_cnt == 0:
                                p._inventory.pop(item_id, None)
                            else:
                                p._inventory[item_id] = new_cnt
                except Exception:
                    pass

                if aid == DEFAULT_ACCOUNT_ID:
                    if new_cnt == 0:
                        state._unlocked_items.discard(item_id)
                        state._item_counts.pop(item_id, None)
                    else:
                        state._item_counts[item_id] = new_cnt
                if new_cnt == 0:
                    db.delete_inventory_item(aid, item_id)
                else:
                    db.save_inventory_item(aid, item_id, new_cnt)
            else:
                state.add_item(item_id, amt, aid)

            item_name = _get_item_meta(item_id)["name"]
            db.log_action(
                aid,
                "ADMIN_LUCK_ROYALE_WALLET_ADJUST",
                f"{action.upper()} {amt}x {item_name} (Item #{item_id}) ({reason})",
                {"action": action, "item_id": item_id, "amount": amt, "reason": reason},
            )
            return True, f"Successfully {action}ed {amt}x {item_name}", self.get_currencies_and_vouchers(aid)

    # -----------------------------------------------------------------------
    # 6. Exchange System (Incubator Forge & Token Shop)
    # -----------------------------------------------------------------------

    def list_special_exchanges(self) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for cfg in config_manager.get_special_exchanges():
                results.append({
                    "forge_tab_id": cfg.forge_tab_id,
                    "tab_name": cfg.tab_name,
                    "item_id": cfg.item_id,
                    "item_name": _get_item_meta(cfg.item_id)["name"],
                    "item_num": cfg.item_num,
                    "sort_id": cfg.sort_id,
                    "limited_purchase_times": cfg.limited_purchase_times,
                    "exchange_items": [
                        {
                            "award_id": ex[0],
                            "award_num": ex[1],
                            "award_type": ex[2] if len(ex) > 2 else AwardType.ITEM,
                            "name": _get_item_meta(ex[0])["name"],
                        }
                        for ex in cfg.exchange_items
                    ],
                    "reward_level": cfg.reward_level,
                    "is_show": cfg.is_show,
                })
            return results

    def create_or_update_special_exchange(self, data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with self._lock:
            tab_id = int(data.get("forge_tab_id", 1))
            raw_iid = data.get("item_id")
            if raw_iid is None:
                return False, "item_id is required", None
            item_id = int(raw_iid)
            tab_name = str(data.get("tab_name") or f"Tab {tab_id}").strip()
            item_num = max(1, int(data.get("item_num", 1)))
            sort_id = int(data.get("sort_id", 1))
            limit = int(data.get("limited_purchase_times", 1))

            req_items = []
            for req in data.get("exchange_items", []):
                aid = int(req.get("award_id") or req.get("item_id"))
                cnt = max(1, int(req.get("award_num") or req.get("cnt") or 1))
                req_items.append((aid, cnt, AwardType.ITEM))

            if not req_items:
                return False, "exchange_items requirement list cannot be empty", None

            new_cfg = SpecialExchangeConfig(
                forge_tab_id=tab_id,
                tab_name=tab_name,
                item_id=item_id,
                item_num=item_num,
                sort_id=sort_id,
                limited_purchase_times=limit,
                exchange_items=tuple(req_items),
                reward_level=int(data.get("reward_level", RareType.SUPER_RARE)),
                is_show=bool(data.get("is_show", True)),
            )

            current_ex = list(config_manager.get_special_exchanges())
            idx = next((i for i, c in enumerate(current_ex) if c.forge_tab_id == tab_id and c.item_id == item_id), None)
            if idx is not None:
                current_ex[idx] = new_cfg
            else:
                current_ex.append(new_cfg)

            config_manager.set_special_exchanges(current_ex)

            try:
                import handlers.gacha_handler as gh
                gh._SPECIAL_EXCHANGE_INDEX[(tab_id, item_id)] = new_cfg
            except Exception:
                pass

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_EXCHANGE_SAVE",
                f"Saved special exchange recipe tab={tab_id} item={item_id}",
                {"forge_tab_id": tab_id, "item_id": item_id, "tab_name": tab_name},
            )
            return True, "Exchange recipe saved successfully", {
                "forge_tab_id": tab_id,
                "item_id": item_id,
                "tab_name": tab_name,
                "item_name": _get_item_meta(item_id)["name"],
            }

    def delete_special_exchange(self, forge_tab_id: int, item_id: int, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str]:
        with self._lock:
            tab_id = int(forge_tab_id)
            iid = int(item_id)
            current_ex = list(config_manager.get_special_exchanges())
            idx = next((i for i, c in enumerate(current_ex) if c.forge_tab_id == tab_id and c.item_id == iid), None)
            if idx is not None:
                current_ex.pop(idx)
                config_manager.set_special_exchanges(current_ex)
                try:
                    import handlers.gacha_handler as gh
                    gh._SPECIAL_EXCHANGE_INDEX.pop((tab_id, iid), None)
                except Exception:
                    pass
                db.log_action(
                    operator_id,
                    "ADMIN_LUCK_ROYALE_EXCHANGE_DELETE",
                    f"Deleted special exchange recipe tab={tab_id} item={iid}",
                    {"forge_tab_id": tab_id, "item_id": iid},
                )
                return True, f"Exchange recipe {tab_id}:{iid} deleted successfully"
            return False, f"Exchange recipe {tab_id}:{iid} not found"

    # -----------------------------------------------------------------------
    # 7. Events & Banner Assignments
    # -----------------------------------------------------------------------

    def get_events_and_banners(self) -> Dict[str, Any]:
        with self._lock:
            os.makedirs(_BANNERS_DIR, exist_ok=True)
            available_banners = []
            for f in sorted(os.listdir(_BANNERS_DIR)):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    full = os.path.join(_BANNERS_DIR, f)
                    if os.path.isfile(full):
                        available_banners.append({
                            "filename": f,
                            "url": f"/banners/{f}",
                            "size": os.path.getsize(full),
                        })

            assignments = []
            for cfg in registry.get_all_machines():
                cid = cfg.chest_id
                banner = self._banner_assignments.get(cid, "luck_royale_banner.png")
                ev = self._events.get(cid, {})
                assignments.append({
                    "chest_id": cid,
                    "chest_name": self._friendly_chest_name(cfg),
                    "banner_file": banner,
                    "banner_url": f"/banners/{banner}",
                    "active_event": ev if ev.get("active") else None,
                })

            return {
                "ok": True,
                "available_banners": available_banners,
                "machine_banners": assignments,
                "scheduled_events": list(self._events.values()),
            }

    def set_machine_banner(self, chest_id: int, banner_file: str, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str]:
        with self._lock:
            cid = int(chest_id)
            if registry.get_machine(cid) is None:
                return False, f"Machine {cid} not found"

            clean_banner = os.path.basename(str(banner_file).strip())
            self._banner_assignments[cid] = clean_banner
            self._save_admin_state()

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_BANNER_ASSIGN",
                f"Assigned banner {clean_banner} to machine {cid}",
                {"chest_id": cid, "banner": clean_banner},
            )
            return True, f"Banner {clean_banner} assigned to machine {cid}"

    def schedule_event(self, data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Dict[str, Any]]:
        with self._lock:
            cid = int(data.get("chest_id", 0))
            if registry.get_machine(cid) is None:
                return False, f"Machine {cid} not found", {}

            event_id = int(data.get("event_id") or int(time.time()))
            title = str(data.get("title") or f"Special Event for Machine {cid}").strip()
            start_ts = int(data.get("start_time") or time.time())
            end_ts = int(data.get("end_time") or (time.time() + 86400 * 7))
            discount = max(0, min(90, int(data.get("discount_percent", 0))))
            rate_up = float(data.get("rate_up_multiplier", 1.0))

            ev_payload = {
                "event_id": event_id,
                "chest_id": cid,
                "title": title,
                "start_time": start_ts,
                "end_time": end_ts,
                "discount_percent": discount,
                "rate_up_multiplier": rate_up,
                "active": bool(data.get("active", True)),
            }
            self._events[cid] = ev_payload
            self._save_admin_state()

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_EVENT_SCHEDULE",
                f"Scheduled event '{title}' for machine {cid}",
                ev_payload,
            )
            return True, "Event scheduled successfully", ev_payload

    # -----------------------------------------------------------------------
    # 8. Account Inspector & Manual Adjustments
    # -----------------------------------------------------------------------

    def inspect_account(self, account_id: int) -> Dict[str, Any]:
        with self._lock:
            aid = int(account_id)
            prof = state.get_player(aid) or state.get_profile(aid) or {}
            user_states = db.get_all_gacha_states(aid)
            recent_tx = db.get_gacha_transactions(account_id=aid, limit=50)
            exchanges = db.get_special_exchange_purchases(aid)

            meters = []
            for cfg in registry.get_all_machines():
                cid = cfg.chest_id
                st = user_states.get(cid, {})
                meters.append({
                    "chest_id": cid,
                    "chest_name": self._friendly_chest_name(cfg),
                    "not_got_num": int(st.get("not_got_num", 0)),
                    "rare_item_max": cfg.rare_item_max,
                    "lottery_count_weekly": int(st.get("lottery_count_weekly", 0)),
                    "next_free_time": int(st.get("next_free_time", 0)),
                    "exchanged_reward_list": list(st.get("exchanged_reward_list", [])),
                })

            portfolio = self.get_currencies_and_vouchers(aid)

            return {
                "ok": True,
                "account_id": aid,
                "profile": {
                    "account_id": aid,
                    "nickname": prof.get("nickname", f"Player_{aid}"),
                    "level": prof.get("level", 60),
                    "exp": prof.get("exp", 125000),
                    "is_online": prof.get("is_online", False),
                },
                "wallet_and_vouchers": portfolio,
                "lucky_meters": meters,
                "recent_spins": recent_tx,
                "special_exchange_crafts": [
                    {"forge_tab_id": k[0], "item_id": k[1], "count": v, "name": _get_item_meta(k[1])["name"]}
                    for k, v in exchanges.items()
                ],
            }

    def adjust_account_luck_state(self, account_id: int, data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Dict[str, Any]]:
        with self._lock:
            aid = int(account_id)
            cid = int(data.get("chest_id", CHEST_DIAMOND_ROYALE))
            user_states = db.get_all_gacha_states(aid)
            st = user_states.get(cid, {
                "lottery_count_weekly": 0,
                "exchanged_reward_list": [],
                "next_free_time": 0,
                "not_got_num": 0,
                "limit_purchase_count_one": 0,
                "limit_purchase_count_ten": 0,
                "first_draw_reward_num": 0,
            })

            if "not_got_num" in data:
                st["not_got_num"] = max(0, int(data["not_got_num"]))
            elif "meter_value" in data:
                st["not_got_num"] = max(0, int(data["meter_value"]))
            if "next_free_time" in data:
                st["next_free_time"] = int(data["next_free_time"])
            if "lottery_count_weekly" in data:
                st["lottery_count_weekly"] = max(0, int(data["lottery_count_weekly"]))
            if bool(data.get("clear_milestones")):
                st["exchanged_reward_list"] = []

            db.save_gacha_state(aid, cid, st)
            try:
                from handlers.gacha_handler import gacha_service
                gacha_service.set_meter(aid, cid, st["not_got_num"])
            except Exception:
                pass
            db.log_action(
                aid,
                "ADMIN_LUCK_ROYALE_ACCOUNT_ADJUST",
                f"Adjusted luck royale account state for chest {cid}",
                {"account_id": aid, "chest_id": cid, "adjustments": data},
            )
            return True, "Account state updated successfully", self.inspect_account(aid)

    # -----------------------------------------------------------------------
    # 9. Transactions Explorer
    # -----------------------------------------------------------------------

    def get_transactions(
        self,
        account_id: Optional[int] = None,
        chest_id: Optional[int] = None,
        date_from: Optional[int] = None,
        date_to: Optional[int] = None,
        reward_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query gacha transaction audit history (ILuckRoyaleAdminService)."""
        with self._lock:
            tx_list = db.get_gacha_transactions(
                account_id=account_id,
                chest_id=chest_id,
                limit=max(1, min(200, limit)),
                offset=max(0, offset),
            )

            filtered = []
            for tx in tx_list:
                ts = tx.get("timestamp", 0)
                if date_from is not None and ts < int(date_from):
                    continue
                if date_to is not None and ts > int(date_to):
                    continue
                if reward_id is not None:
                    has_rw = any(
                        int(r.get("origin_award_id", 0)) == int(reward_id)
                        or int(r.get("dest_award_id", 0)) == int(reward_id)
                        for r in tx.get("reward_list", [])
                    )
                    if not has_rw:
                        continue
                filtered.append(tx)

            return {
                "ok": True,
                "transactions": filtered,
                "total": len(filtered),
                "limit": limit,
                "offset": offset,
            }

    def record_manual_transaction(self, data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> int:
        with self._lock:
            aid = int(data.get("account_id") or DEFAULT_ACCOUNT_ID)
            cid = int(data.get("chest_id") or CHEST_DIAMOND_ROYALE)
            gtype = int(data.get("gacha_type") or 1)
            ctype = int(data.get("consume_type") or 1)
            cost_type = int(data.get("cost_type") or 1)
            cost_amt = int(data.get("cost_amount") or 0)
            rewards = list(data.get("reward_list") or [])
            lucky_before = int(data.get("lucky_before") or 0)
            lucky_after = int(data.get("lucky_after") or 0)
            has_big = bool(data.get("has_big_reward", False))

            tx_id = db.record_gacha_transaction(
                account_id=aid,
                chest_id=cid,
                gacha_type=gtype,
                consume_type=ctype,
                cost_type=cost_type,
                cost_amount=cost_amt,
                reward_list=rewards,
                lucky_before=lucky_before,
                lucky_after=lucky_after,
                has_big_reward=has_big,
            )
            return tx_id

    # -----------------------------------------------------------------------
    # Helper: Item Catalog Search Helper
    # -----------------------------------------------------------------------

    def list_assets(self, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            os.makedirs(_BANNERS_DIR, exist_ok=True)
            uploads_dir = os.path.join(_BANNERS_DIR, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)

            results: List[Dict[str, Any]] = []

            for fn in sorted(os.listdir(_BANNERS_DIR)):
                if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                full = os.path.join(_BANNERS_DIR, fn)
                if not os.path.isfile(full):
                    continue
                cat = "General"
                low = fn.lower()
                if "poster" in low or "banner" in low or "splash" in low:
                    cat = "Banners & Posters"
                elif "gun" in low or "m4a1" in low or "weapon" in low or "ak47" in low:
                    cat = "Weapons"
                elif "ingot" in low or "gaincoin" in low or "gaindiamond" in low or "btn" in low:
                    cat = "Tokens & UI"
                elif "anni" in low or "light" in low:
                    cat = "Incubator & Effects"
                results.append({
                    "filename": fn,
                    "url": f"/banners/{fn}",
                    "size_bytes": os.path.getsize(full),
                    "category": cat,
                    "is_upload": False,
                })

            for fn in sorted(os.listdir(uploads_dir)):
                if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                full = os.path.join(uploads_dir, fn)
                if not os.path.isfile(full):
                    continue
                results.append({
                    "filename": fn,
                    "url": f"/banners/uploads/{fn}",
                    "size_bytes": os.path.getsize(full),
                    "category": "Uploads",
                    "is_upload": True,
                })

            # Authentic Free Fire 1.39 assets
            ff_base = os.path.join(_STATIC_DIR, "assets", "freefire", "1.39")
            sub_folders = {
                "royale": "Royale Machine Artwork",
                "items": "Authentic Game Items",
                "characters": "Character & Debris Assets",
                "ui": "UI & Turntable Elements"
            }
            for sfolder, scat in sub_folders.items():
                p = os.path.join(ff_base, sfolder)
                if os.path.isdir(p):
                    for fn in sorted(os.listdir(p)):
                        if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                            full = os.path.join(p, fn)
                            if os.path.isfile(full):
                                results.append({
                                    "filename": fn,
                                    "url": f"/assets/freefire/1.39/{sfolder}/{fn}",
                                    "size_bytes": os.path.getsize(full),
                                    "category": scat,
                                    "is_upload": False,
                                })

            if category and category.lower() != "all":
                results = [a for a in results if a["category"].lower() == category.lower()]
            if search:
                s = search.lower().strip()
                results = [a for a in results if s in a["filename"].lower() or s in a["category"].lower()]

            return results

    def upload_asset(self, filename: str, data_bytes: bytes, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with self._lock:
            if not data_bytes or len(data_bytes) == 0:
                return False, "File data is empty", None
            if len(data_bytes) > 10 * 1024 * 1024:
                return False, "File exceeds 10MB limit", None

            clean_name = os.path.basename(filename).strip()
            clean_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", clean_name)
            if not clean_name or not clean_name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                clean_name = f"upload_{int(time.time())}.png"

            uploads_dir = os.path.join(_BANNERS_DIR, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            target_path = os.path.join(uploads_dir, clean_name)

            try:
                with open(target_path, "wb") as f:
                    f.write(data_bytes)
            except Exception as exc:
                return False, f"Failed to write file: {exc}", None

            meta = {
                "filename": clean_name,
                "url": f"/banners/uploads/{clean_name}",
                "size_bytes": len(data_bytes),
                "category": "Uploads",
                "is_upload": True,
            }
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_ASSET_UPLOAD",
                f"Uploaded asset {clean_name} ({len(data_bytes)} bytes)",
                {"filename": clean_name, "size": len(data_bytes)},
            )
            return True, "Asset uploaded successfully", meta

    def get_machine_artwork(self, chest_id: int) -> Dict[str, Any]:
        with self._lock:
            cid = int(chest_id)
            defaults = DEFAULT_MACHINE_ARTWORK.get(cid, {
                "banner": "luck_royale_banner.png",
                "thumbnail": "luck_royale_banner.png",
                "background": "FF_Lottery_onebg.png",
                "featured": "FF_Lottery_previewbg.png",
                "promo": "activity_banner.png",
            })
            custom = self._machine_artwork.get(cid, {})
            if cid in self._banner_assignments:
                custom["banner"] = self._banner_assignments[cid]

            merged = dict(defaults)
            merged.update(custom)

            def to_url(fn: str) -> str:
                if not fn:
                    return ""
                if fn.startswith("/"):
                    return fn
                if os.path.isfile(os.path.join(_STATIC_DIR, "assets", "freefire", "1.39", "royale", fn)):
                    return f"/assets/freefire/1.39/royale/{fn}"
                if fn.startswith("uploads/"):
                    return f"/banners/{fn}"
                return f"/banners/{fn}"

            return {
                "chest_id": cid,
                "banner": merged.get("banner", ""),
                "banner_url": to_url(merged.get("banner", "")),
                "thumbnail": merged.get("thumbnail", ""),
                "thumbnail_url": to_url(merged.get("thumbnail", "")),
                "background": merged.get("background", ""),
                "background_url": to_url(merged.get("background", "")),
                "featured": merged.get("featured", ""),
                "featured_url": to_url(merged.get("featured", "")),
                "promo": merged.get("promo", ""),
                "promo_url": to_url(merged.get("promo", "")),
            }

    def set_machine_artwork(self, chest_id: int, artwork_data: Dict[str, str], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Dict[str, Any]]:
        with self._lock:
            cid = int(chest_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found", {}

            if cid not in self._machine_artwork:
                self._machine_artwork[cid] = {}

            for slot in ("banner", "thumbnail", "background", "featured", "promo"):
                if slot in artwork_data and artwork_data[slot] is not None:
                    val = str(artwork_data[slot]).strip()
                    if val.startswith("/banners/"):
                        val = val[len("/banners/"):]
                    self._machine_artwork[cid][slot] = val
                    if slot == "banner":
                        self._banner_assignments[cid] = os.path.basename(val)

            self._save_admin_state()
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_ARTWORK_UPDATE",
                f"Updated artwork slots for machine {cid}",
                {"chest_id": cid, "slots": list(artwork_data.keys())},
            )
            return True, "Artwork updated successfully", self.get_machine_artwork(cid)

    def get_reward_images(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "reward_images": {str(k): v for k, v in self._reward_images.items()},
                "defaults": {str(k): v for k, v in DEFAULT_ITEM_IMAGES.items()},
            }

    def set_reward_image(self, item_id: int, image_url: str, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str]:
        with self._lock:
            iid = int(item_id)
            clean_url = str(image_url).strip()
            self._reward_images[iid] = clean_url
            self._save_admin_state()
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_REWARD_IMAGE_SET",
                f"Assigned image {clean_url} to item {iid}",
                {"item_id": iid, "image_url": clean_url},
            )
            return True, f"Image assigned to item {iid}"

    def reset_reward_image(self, item_id: int, operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str]:
        with self._lock:
            iid = int(item_id)
            self._reward_images.pop(iid, None)
            self._save_admin_state()
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_REWARD_IMAGE_RESET",
                f"Reset image for item {iid} to default",
                {"item_id": iid},
            )
            return True, f"Reset image for item {iid} to default"

    def reorder_pool_items(
        self,
        chest_id: int,
        item_id: int,
        direction: str = "up",
        operator_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        with self._lock:
            cid = int(chest_id)
            iid = int(item_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found", []

            items = list(cfg.items)
            idx = -1
            for i, it in enumerate(items):
                if it.item_id == iid:
                    idx = i
                    break

            if idx == -1:
                return False, f"Item {iid} not found in machine {cid}", []

            if direction == "up":
                if idx == 0:
                    return False, "Item is already at the top", [self._serialize_show_item(it) for it in items]
                items[idx - 1], items[idx] = items[idx], items[idx - 1]
            elif direction == "down":
                if idx == len(items) - 1:
                    return False, "Item is already at the bottom", [self._serialize_show_item(it) for it in items]
                items[idx + 1], items[idx] = items[idx], items[idx + 1]
            else:
                return False, f"Invalid direction '{direction}'", []

            updated_cfg = ChestConfig(
                **{k: v for k, v in cfg.__dict__.items() if k != "items"},
                items=tuple(items),
            )
            config_manager.set_machine(updated_cfg)
            registry.register_machine(updated_cfg)
            self._save_admin_state()

            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_POOL_REORDER",
                f"Reordered item {iid} {direction} in machine {cid}",
                {"chest_id": cid, "item_id": iid, "direction": direction},
            )
            return True, f"Item {iid} moved {direction}", [self._serialize_show_item(it) for it in items]

    def get_machine_event(self, chest_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            cid = int(chest_id)
            return self._events.get(cid, None)

    def save_machine_event(self, chest_id: int, event_data: Dict[str, Any], operator_id: int = DEFAULT_ACCOUNT_ID) -> Tuple[bool, str, Dict[str, Any]]:
        with self._lock:
            cid = int(chest_id)
            cfg = registry.get_machine(cid)
            if not cfg:
                return False, f"Machine {cid} not found", {}

            now = int(time.time())
            ev = {
                "event_id": int(event_data.get("event_id") or now),
                "chest_id": cid,
                "title": str(event_data.get("title") or f"Event for {cfg.chest_name}").strip(),
                "banner_url": str(event_data.get("banner_url") or "/banners/announce_events.png").strip(),
                "start_time": int(event_data.get("start_time") or now),
                "end_time": int(event_data.get("end_time") or (now + 7 * 86400)),
                "discount_percent": max(0, min(100, int(event_data.get("discount_percent") or 0))),
                "rate_up_multiplier": max(1.0, float(event_data.get("rate_up_multiplier") or 1.0)),
                "active": bool(event_data.get("active", True)),
                "rewards": event_data.get("rewards", []),
            }
            self._events[cid] = ev
            self._save_admin_state()
            db.log_action(
                operator_id,
                "ADMIN_LUCK_ROYALE_EVENT_SAVE",
                f"Saved event '{ev['title']}' for machine {cid}",
                {"chest_id": cid, "event": ev},
            )
            return True, f"Event saved for machine {cid}", ev

    def search_items(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        q = str(query or "").strip().lower()
        results: List[Dict[str, Any]] = []
        for iid, meta in ITEM_CATALOG.items():
            if not q or q in str(iid) or q in meta["name"].lower() or q in meta["category"].lower():
                results.append({"item_id": iid, **meta})
                if len(results) >= limit:
                    break
        return results


# Global administrator manager singleton
admin_mgr = LuckRoyaleAdminManager()


# ---------------------------------------------------------------------------
# HTTP Helpers & Request Parsing
# ---------------------------------------------------------------------------

def _parse_json_body(raw_body: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not raw_body:
        return {}, None
    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        return None, f"Invalid JSON body: {exc}"
    if not isinstance(data, dict):
        return None, "JSON body must be an object"
    return data, None


def _authenticate(handler: Any, query_params: Dict[str, List[str]]) -> Tuple[bool, Optional[str]]:
    """Verify administrator Bearer token or X-Admin-Token header."""
    auth_header = handler.headers.get("Authorization", "").strip()
    custom_token = handler.headers.get("X-Admin-Token", "").strip()
    param_token = query_params.get("token", [""])[0].strip() or query_params.get("api_key", [""])[0].strip()

    provided_token = ""
    if auth_header.startswith("Bearer "):
        provided_token = auth_header[7:].strip()
    elif custom_token:
        provided_token = custom_token
    elif param_token:
        provided_token = param_token

    if provided_token:
        if provided_token == ADMIN_API_TOKEN:
            return True, None
        return False, "Unauthorized: Invalid admin token"

    if REQUIRE_AUTH:
        return False, "Unauthorized: Missing Authorization header (Bearer token) or X-Admin-Token"

    # Default permissive local mode
    return True, None


def _extract_id_from_path(path: str, prefix: str) -> Optional[int]:
    """Extract integer ID from path such as /api/admin/luck-royale/accounts/10001."""
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix):].strip("/")
    if not rest:
        return None
    part = rest.split("/")[0]
    try:
        return int(part)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Master Request Dispatcher
# ---------------------------------------------------------------------------

def handle_admin_luck_royale_request(
    handler: Any,
    method: str,
    path: str,
    query_string: str = "",
    raw_body: bytes = b"",
) -> bool:
    """
    Exposes clean, authenticated JSON endpoints under /api/admin/luck-royale/:
    Returns True if path was recognized and handled; False otherwise.
    """
    clean_path = path.rstrip("/")
    if clean_path.startswith("/api/dashboard/luck-royale"):
        clean_path = "/api/admin/luck-royale" + clean_path[len("/api/dashboard/luck-royale"):]

    if not clean_path.startswith("/api/admin/luck-royale"):
        return False

    qp = parse_qs(query_string)

    # 1. Authentication Check
    auth_ok, auth_err = _authenticate(handler, qp)
    if not auth_ok:
        handler.send_json({"ok": False, "error": auth_err, "message": auth_err, "code": 401}, status=401)
        return True

    # Parse body
    body_data, json_err = _parse_json_body(raw_body)
    if json_err and method in ("POST", "PUT", "DELETE"):
        handler.send_json({"ok": False, "error": json_err, "message": json_err, "code": 400}, status=400)
        return True
    body_data = body_data or {}

    # Support method override (_method query param or JSON field)
    eff_method = method.upper()
    override = qp.get("_method", [""])[0] or str(body_data.get("_method") or "")
    if override.upper() in ("PUT", "DELETE", "POST", "GET"):
        eff_method = override.upper()

    sub_path = clean_path[len("/api/admin/luck-royale"):]

    try:
        # -------------------------------------------------------------------
        # Auth Check Endpoint: /auth/check
        # -------------------------------------------------------------------
        if sub_path in ("/auth/check", "/auth"):
            handler.send_json({"ok": True, "authenticated": True, "token_accepted": True})
            return True

        # -------------------------------------------------------------------
        # 1. Overview Statistics: /overview
        # -------------------------------------------------------------------
        if sub_path in ("/overview", "") and eff_method == "GET":
            handler.send_json(admin_mgr.get_overview())
            return True

        # -------------------------------------------------------------------
        # 2. Machines: /machines
        # -------------------------------------------------------------------
        if sub_path.startswith("/machines"):
            if "/toggle" in sub_path:
                cid = _extract_id_from_path(clean_path, "/api/admin/luck-royale/machines/") or body_data.get("chest_id")
                if not cid:
                    handler.send_json({"ok": False, "error": "chest_id is required to toggle", "message": "chest_id is required to toggle"}, status=400)
                    return True
                ok, msg, nstate = admin_mgr.toggle_machine(int(cid), enabled=body_data.get("enabled"))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "enabled": nstate}, status=200 if ok else 400)
                return True

            if "/duplicate" in sub_path:
                src_cid = _extract_id_from_path(clean_path, "/api/admin/luck-royale/machines/") or body_data.get("source_chest_id")
                tgt_cid = body_data.get("new_chest_id")
                tgt_name = str(body_data.get("new_chest_name") or f"Copy of Machine {src_cid}")
                if not src_cid or not tgt_cid:
                    handler.send_json({"ok": False, "error": "source_chest_id and new_chest_id are required", "message": "source_chest_id and new_chest_id are required"}, status=400)
                    return True
                ok, msg, mdata = admin_mgr.duplicate_machine(int(src_cid), int(tgt_cid), tgt_name)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "machine": mdata}, status=201 if ok else 400)
                return True

            extracted_cid = _extract_id_from_path(clean_path, "/api/admin/luck-royale/machines")

            if "/artwork" in sub_path:
                cid = extracted_cid or body_data.get("chest_id")
                if not cid:
                    handler.send_json({"ok": False, "error": "chest_id required", "message": "chest_id required"}, status=400)
                    return True
                if eff_method == "GET":
                    artwork = admin_mgr.get_machine_artwork(int(cid))
                    handler.send_json({"ok": True, "chest_id": int(cid), "artwork": artwork})
                    return True
                if eff_method in ("POST", "PUT"):
                    ok, msg, artwork = admin_mgr.set_machine_artwork(int(cid), body_data)
                    handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "artwork": artwork}, status=200 if ok else 400)
                    return True

            if "/events" in sub_path:
                cid = extracted_cid or body_data.get("chest_id")
                if not cid:
                    handler.send_json({"ok": False, "error": "chest_id required", "message": "chest_id required"}, status=400)
                    return True
                if eff_method == "GET":
                    ev = admin_mgr.get_machine_event(int(cid))
                    handler.send_json({"ok": True, "chest_id": int(cid), "event": ev})
                    return True
                if eff_method in ("POST", "PUT"):
                    ok, msg, ev = admin_mgr.save_machine_event(int(cid), body_data)
                    handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "event": ev}, status=200 if ok else 400)
                    return True

            if eff_method == "GET":
                if extracted_cid is not None:
                    m = admin_mgr.get_machine(extracted_cid)
                    if m:
                        handler.send_json({"ok": True, "machine": m})
                    else:
                        handler.send_json({"ok": False, "error": f"Machine {extracted_cid} not found", "message": f"Machine {extracted_cid} not found"}, status=404)
                    return True
                inc_dis = qp.get("include_disabled", ["1"])[0] != "0"
                handler.send_json({"ok": True, "machines": admin_mgr.list_machines(include_disabled=inc_dis)})
                return True

            if eff_method == "POST":
                action = str(body_data.get("action") or "").lower()
                if action == "toggle":
                    cid = body_data.get("chest_id") or extracted_cid
                    if not cid:
                        handler.send_json({"ok": False, "error": "chest_id required for toggle", "message": "chest_id required for toggle"}, status=400)
                        return True
                    ok, msg, nstate = admin_mgr.toggle_machine(int(cid), enabled=body_data.get("enabled"))
                    handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "enabled": nstate}, status=200 if ok else 400)
                    return True

                if action == "duplicate":
                    src_cid = body_data.get("source_chest_id") or extracted_cid
                    tgt_cid = body_data.get("new_chest_id")
                    tgt_name = str(body_data.get("new_chest_name") or "")
                    if not src_cid or not tgt_cid:
                        handler.send_json({"ok": False, "error": "source_chest_id and new_chest_id required", "message": "source_chest_id and new_chest_id required"}, status=400)
                        return True
                    ok, msg, mdata = admin_mgr.duplicate_machine(int(src_cid), int(tgt_cid), tgt_name)
                    handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "machine": mdata}, status=201 if ok else 400)
                    return True

                ok, msg, mdata = admin_mgr.create_machine(body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "machine": mdata}, status=201 if ok else 400)
                return True

            if eff_method == "PUT":
                cid = extracted_cid or body_data.get("chest_id")
                if not cid:
                    handler.send_json({"ok": False, "error": "chest_id required for update", "message": "chest_id required for update"}, status=400)
                    return True
                ok, msg, mdata = admin_mgr.update_machine_with_result(int(cid), body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "machine": mdata}, status=200 if ok else 400)
                return True

            if eff_method == "DELETE":
                cid = extracted_cid or body_data.get("chest_id")
                if not cid:
                    handler.send_json({"ok": False, "error": "chest_id required for delete", "message": "chest_id required for delete"}, status=400)
                    return True
                ok, msg = admin_mgr.delete_machine(int(cid))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # Assets & Image Management: /assets
        # -------------------------------------------------------------------
        if sub_path.startswith("/assets"):
            if "/upload" in sub_path and eff_method == "POST":
                filename = body_data.get("filename", "upload.png")
                data_b64 = body_data.get("data") or body_data.get("base64")
                if not data_b64:
                    handler.send_json({"ok": False, "error": "data or base64 field is required"}, status=400)
                    return True
                import base64
                try:
                    if "," in data_b64:
                        data_b64 = data_b64.split(",", 1)[1]
                    raw_bytes = base64.b64decode(data_b64)
                    ok, msg, meta = admin_mgr.upload_asset(filename, raw_bytes)
                    handler.send_json({"ok": ok, "error": msg if not ok else None, "asset": meta}, status=201 if ok else 400)
                except Exception as exc:
                    handler.send_json({"ok": False, "error": f"Upload failed: {exc}"}, status=400)
                return True
            if eff_method == "GET":
                cat = qp.get("category", [""])[0] or None
                search = qp.get("q", [""])[0] or None
                assets = admin_mgr.list_assets(category=cat, search=search)
                handler.send_json({"ok": True, "assets": assets, "total": len(assets)})
                return True

        # -------------------------------------------------------------------
        # Reward Image Mapping: /reward-images
        # -------------------------------------------------------------------
        if sub_path.startswith("/reward-images"):
            if eff_method == "GET":
                data = admin_mgr.get_reward_images()
                handler.send_json({"ok": True, **data})
                return True
            if eff_method in ("POST", "PUT"):
                iid = body_data.get("item_id")
                img_url = body_data.get("image_url") or body_data.get("image")
                if not iid or not img_url:
                    handler.send_json({"ok": False, "error": "item_id and image_url are required"}, status=400)
                    return True
                ok, msg = admin_mgr.set_reward_image(int(iid), str(img_url))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                return True
            if eff_method == "DELETE":
                iid = body_data.get("item_id") or qp.get("item_id", [""])[0]
                if not iid:
                    handler.send_json({"ok": False, "error": "item_id is required"}, status=400)
                    return True
                ok, msg = admin_mgr.reset_reward_image(int(iid))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # 3. Reward Pools: /reward-pools
        # -------------------------------------------------------------------
        if sub_path.startswith("/reward-pools"):
            if "/reorder" in sub_path and eff_method == "POST":
                parts = [p for p in sub_path.split("/") if p]
                path_cid = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None
                cid = body_data.get("chest_id") or path_cid
                item_id = body_data.get("item_id")
                direction = body_data.get("direction", "up")
                if not cid or not item_id:
                    handler.send_json({"ok": False, "error": "chest_id and item_id are required"}, status=400)
                    return True
                ok, msg, items = admin_mgr.reorder_pool_items(int(cid), int(item_id), str(direction))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "items": items}, status=200 if ok else 400)
                return True
            search_query = qp.get("q", [""])[0] or str(body_data.get("q") or "")
            if search_query or "/search" in sub_path:
                q = search_query or qp.get("query", [""])[0]
                handler.send_json({"ok": True, "query": q, "items": admin_mgr.search_items(q, limit=50)})
                return True

            parts = [p for p in sub_path.split("/") if p]
            path_cid = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None
            path_iid = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None

            if eff_method == "GET":
                raw_cid = path_cid or qp.get("chest_id", [""])[0]
                cid = int(raw_cid) if raw_cid else None
                handler.send_json(admin_mgr.get_reward_pool(cid))
                return True

            if eff_method == "POST":
                cid = body_data.get("chest_id") or path_cid
                if not cid:
                    handler.send_json({"ok": False, "error": "chest_id is required", "message": "chest_id is required"}, status=400)
                    return True
                ok, msg, item_meta = admin_mgr.add_pool_item(int(cid), body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "item": item_meta}, status=201 if ok else 400)
                return True

            if eff_method == "PUT":
                cid = body_data.get("chest_id") or path_cid
                iid = body_data.get("item_id") or path_iid
                if not cid or not iid:
                    handler.send_json({"ok": False, "error": "chest_id and item_id are required", "message": "chest_id and item_id are required"}, status=400)
                    return True
                ok, msg, item_meta = admin_mgr.update_pool_item(int(cid), int(iid), body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "item": item_meta}, status=200 if ok else 400)
                return True

            if eff_method == "DELETE":
                cid = body_data.get("chest_id") or path_cid or qp.get("chest_id", [""])[0]
                iid = body_data.get("item_id") or path_iid or qp.get("item_id", [""])[0]
                if not cid or not iid:
                    handler.send_json({"ok": False, "error": "chest_id and item_id are required", "message": "chest_id and item_id are required"}, status=400)
                    return True
                ok, msg = admin_mgr.remove_pool_item(int(cid), int(iid))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # 4. Lucky Meters: /meters
        # -------------------------------------------------------------------
        if sub_path.startswith("/meters"):
            parts = [p for p in sub_path.split("/") if p]
            path_cid = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None

            if eff_method == "GET":
                raw_cid = path_cid or qp.get("chest_id", [""])[0]
                raw_aid = qp.get("account_id", [""])[0]
                cid = int(raw_cid) if raw_cid else None
                aid = int(raw_aid) if raw_aid else None
                handler.send_json(admin_mgr.get_lucky_meters(cid, aid))
                return True

            if eff_method in ("PUT", "POST"):
                if path_cid and "chest_id" not in body_data:
                    body_data["chest_id"] = path_cid
                ok, msg = admin_mgr.update_lucky_meter_config(body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # 5. Currencies & Vouchers: /currencies-vouchers
        # -------------------------------------------------------------------
        if sub_path.startswith("/currencies-vouchers"):
            if "/costs/" in sub_path:
                cid = _extract_id_from_path(clean_path, "/api/admin/luck-royale/currencies-vouchers/costs")
                if cid:
                    ok, msg, mdata = admin_mgr.update_machine_with_result(cid, body_data)
                    handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "machine": mdata}, status=200 if ok else 400)
                    return True

            if eff_method == "GET":
                aid = int(qp.get("account_id", [str(DEFAULT_ACCOUNT_ID)])[0])
                handler.send_json(admin_mgr.get_currencies_and_vouchers(aid))
                return True

            if eff_method == "POST":
                ok, msg, portfolio = admin_mgr.adjust_currency_or_voucher(body_data)
                handler.send_json({
                    "ok": ok,
                    "error": msg if not ok else None,
                    "message": msg,
                    "wallet_and_vouchers": portfolio,
                }, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # 6. Exchange Systems: /exchange
        # -------------------------------------------------------------------
        if sub_path.startswith("/exchange"):
            parts = [p for p in sub_path.split("/") if p]
            path_item_id = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None

            if eff_method == "GET":
                handler.send_json({"ok": True, "special_exchanges": admin_mgr.list_special_exchanges()})
                return True

            if eff_method in ("POST", "PUT"):
                ok, msg, res_data = admin_mgr.create_or_update_special_exchange(body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "exchange": res_data}, status=200 if ok else 400)
                return True

            if eff_method == "DELETE":
                tab_id = body_data.get("forge_tab_id") or qp.get("forge_tab_id", [""])[0]
                item_id = body_data.get("item_id") or path_item_id or qp.get("item_id", [""])[0]
                # If tab_id not provided, try to find tab_id from item_id
                if not tab_id and item_id:
                    for ex in admin_mgr.list_special_exchanges():
                        if int(ex["item_id"]) == int(item_id):
                            tab_id = ex["forge_tab_id"]
                            break
                    if not tab_id:
                        tab_id = 1
                if not tab_id or not item_id:
                    handler.send_json({"ok": False, "error": "forge_tab_id and item_id are required", "message": "forge_tab_id and item_id are required"}, status=400)
                    return True
                ok, msg = admin_mgr.delete_special_exchange(int(tab_id), int(item_id))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                return True
                item_id = body_data.get("item_id") or qp.get("item_id", [""])[0]
                if not tab_id or not item_id:
                    handler.send_json({"ok": False, "error": "forge_tab_id and item_id are required", "message": "forge_tab_id and item_id are required"}, status=400)
                    return True
                ok, msg = admin_mgr.delete_special_exchange(int(tab_id), int(item_id))
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # 7. Events & Banners: /events-banners
        # -------------------------------------------------------------------
        if sub_path.startswith("/events-banners"):
            if eff_method == "GET":
                handler.send_json(admin_mgr.get_events_and_banners())
                return True

            if eff_method in ("POST", "PUT"):
                action = str(body_data.get("action") or "").lower()
                if action == "assign_banner" or "banner_file" in body_data and "chest_id" in body_data and "start_time" not in body_data:
                    cid = int(body_data["chest_id"])
                    banner = str(body_data["banner_file"]).strip()
                    ok, msg = admin_mgr.set_machine_banner(cid, banner)
                    handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg}, status=200 if ok else 400)
                    return True

                ok, msg, ev = admin_mgr.schedule_event(body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "event": ev}, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # 8. Account Inspector & Adjustments: /accounts/<account_id>
        # -------------------------------------------------------------------
        if sub_path.startswith("/accounts"):
            aid = _extract_id_from_path(clean_path, "/api/admin/luck-royale/accounts")
            if aid is None:
                raw_aid = qp.get("account_id", [""])[0] or body_data.get("account_id")
                aid = int(raw_aid) if raw_aid else DEFAULT_ACCOUNT_ID

            if eff_method == "GET":
                handler.send_json(admin_mgr.inspect_account(aid))
                return True

            if eff_method == "POST":
                ok, msg, res_state = admin_mgr.adjust_account_luck_state(aid, body_data)
                handler.send_json({"ok": ok, "error": msg if not ok else None, "message": msg, "account": res_state}, status=200 if ok else 400)
                return True

        # -------------------------------------------------------------------
        # 9. Transactions: /transactions
        # -------------------------------------------------------------------
        if sub_path.startswith("/transactions"):
            if eff_method == "GET":
                raw_aid = qp.get("account_id", [""])[0]
                raw_cid = qp.get("chest_id", [""])[0]
                raw_dfrom = qp.get("date_from", [""])[0]
                raw_dto = qp.get("date_to", [""])[0]
                raw_rid = qp.get("reward_id", [""])[0]
                raw_lim = qp.get("limit", ["50"])[0]
                raw_off = qp.get("offset", ["0"])[0]

                res = admin_mgr.get_transactions(
                    account_id=int(raw_aid) if raw_aid else None,
                    chest_id=int(raw_cid) if raw_cid else None,
                    date_from=int(raw_dfrom) if raw_dfrom else None,
                    date_to=int(raw_dto) if raw_dto else None,
                    reward_id=int(raw_rid) if raw_rid else None,
                    limit=int(raw_lim),
                    offset=int(raw_off),
                )
                handler.send_json(res)
                return True

            if eff_method == "POST":
                tx_id = admin_mgr.record_manual_transaction(body_data)
                handler.send_json({"ok": True, "trans_id": tx_id, "message": "Transaction recorded successfully"}, status=201)
                return True

        # Route not handled under /api/admin/luck-royale
        handler.send_json({
            "ok": False,
            "error": f"Unknown admin Luck Royale route: {method} {clean_path}",
            "message": f"Unknown admin Luck Royale route: {method} {clean_path}",
            "code": 404,
        }, status=404)
        return True

    except Exception as exc:
        logger.exception("Error processing admin Luck Royale API request: %s", exc)
        handler.send_json({
            "ok": False,
            "error": f"Internal admin error: {str(exc)}",
            "message": f"Internal admin error: {str(exc)}",
            "code": 500,
        }, status=500)
        return True
