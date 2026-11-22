"""
Thread-safe global game state store for India V1 1.39 Emulation Server.
Shared across all handler modules and dashboard_api.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:
    from core.database import db
except ImportError:
    try:
        from server.core.database import db
    except ImportError:
        from .database import db

DEFAULT_ACCOUNT_ID = 10001
DEFAULT_NICKNAME = "Clack"
DEFAULT_COINS = 999999
DEFAULT_GEMS = 999999
DEFAULT_AVATAR_ID = 102000004  # Adam
DEFAULT_CLOTHES = [211000000, 208000000, 203000573, 204000345, 205000299]
DEFAULT_CMS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "lobby_cms.json",
)
CMS_CATEGORIES = (
    "splashes",
    "adverts",
    "announcements",
    "marquees",
    "broadcasts",
    "events",
    "feature_switches",
    "bonus_events",
)

MODE_MAX_MEMBERS = {
    "solo": 1,
    "duo": 2,
    "squad": 4,
}

_MATCH_ID_COUNTER = int(time.time() * 1000) % 90000000 + 10000000
_MATCH_ID_LOCK = threading.Lock()

def generate_match_id() -> int:
    """Generate a unique 8-digit dynamic match ID."""
    global _MATCH_ID_COUNTER
    with _MATCH_ID_LOCK:
        _MATCH_ID_COUNTER += 1
        return _MATCH_ID_COUNTER


def _seed_players(now: int) -> Dict[int, Dict[str, Any]]:
    """Pre-seeded online bot friends and discoverable players."""
    return {
        20001: {
            "account_id": 20001,
            "nickname": "IndiaV1_Bot",
            "region": "DEFAULT",
            "level": 65,
            "exp": 145000,
            "rank": 318,
            "ranking_points": 3420,
            "banner_id": 901000002,
            "head_pic": 902000002,
            "avatar_id": 102000014,  # Joseph
            "clan_id": 50001,
            "clan_name": "INDIA V1",
            "has_elite_pass": True,
            "badge_cnt": 250,
            "online_status": 1,  # 1 = Online in lobby
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
        20002: {
            "account_id": 20002,
            "nickname": "Kelly_Dash",
            "region": "DEFAULT",
            "level": 58,
            "exp": 98000,
            "rank": 312,
            "ranking_points": 2980,
            "banner_id": 901000003,
            "head_pic": 902000003,
            "avatar_id": 101000006,  # Kelly
            "clan_id": 50001,
            "clan_name": "INDIA V1",
            "has_elite_pass": True,
            "badge_cnt": 180,
            "online_status": 1,
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
        20003: {
            "account_id": 20003,
            "nickname": "Hayato_Blade",
            "region": "DEFAULT",
            "level": 62,
            "exp": 120000,
            "rank": 316,
            "ranking_points": 3190,
            "banner_id": 901000004,
            "head_pic": 902000004,
            "avatar_id": 102000012,  # Hayato
            "clan_id": 50001,
            "clan_name": "INDIA V1",
            "has_elite_pass": True,
            "badge_cnt": 210,
            "online_status": 1,
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
        20004: {
            "account_id": 20004,
            "nickname": "Kla_OnePunch",
            "region": "DEFAULT",
            "level": 54,
            "exp": 82000,
            "rank": 309,
            "ranking_points": 2650,
            "banner_id": 901000005,
            "head_pic": 902000005,
            "avatar_id": 102000008,  # Kla
            "clan_id": 50002,
            "clan_name": "FF_LEGENDS",
            "has_elite_pass": False,
            "badge_cnt": 85,
            "online_status": 2,  # 2 = In lobby / ready
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
        20005: {
            "account_id": 20005,
            "nickname": "Wukong_Bush",
            "region": "DEFAULT",
            "level": 51,
            "exp": 74000,
            "rank": 305,
            "ranking_points": 2410,
            "banner_id": 901000006,
            "head_pic": 902000006,
            "avatar_id": 102000011,  # Wukong
            "clan_id": 50001,
            "clan_name": "INDIA V1",
            "has_elite_pass": True,
            "badge_cnt": 130,
            "online_status": 3,  # 3 = In match
            "is_online": True,
            "can_invite": False,
            "is_bot": True,
            "last_login_at": now - 120,
        },
        20006: {
            "account_id": 20006,
            "nickname": "Moco_Eye",
            "region": "DEFAULT",
            "level": 49,
            "exp": 66000,
            "rank": 301,
            "ranking_points": 2150,
            "banner_id": 901000007,
            "head_pic": 902000007,
            "avatar_id": 101000011,  # Moco
            "clan_id": 50002,
            "clan_name": "FF_LEGENDS",
            "has_elite_pass": True,
            "badge_cnt": 115,
            "online_status": 0,  # Offline
            "is_online": False,
            "can_invite": False,
            "is_bot": True,
            "last_login_at": now - 3600,
        },
        # Non-friend discoverable players (pending requests / recommended / search)
        20007: {
            "account_id": 20007,
            "nickname": "Laura_Sniper",
            "region": "DEFAULT",
            "level": 61,
            "exp": 118000,
            "rank": 317,
            "ranking_points": 3310,
            "banner_id": 901000008,
            "head_pic": 902000008,
            "avatar_id": 101000012,  # Laura
            "clan_id": 50003,
            "clan_name": "HEADSHOT",
            "has_elite_pass": True,
            "badge_cnt": 195,
            "online_status": 1,
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
        20008: {
            "account_id": 20008,
            "nickname": "Rafael_Silent",
            "region": "DEFAULT",
            "level": 56,
            "exp": 91000,
            "rank": 311,
            "ranking_points": 2840,
            "banner_id": 901000009,
            "head_pic": 902000009,
            "avatar_id": 102000013,  # Rafael
            "clan_id": 50003,
            "clan_name": "HEADSHOT",
            "has_elite_pass": False,
            "badge_cnt": 70,
            "online_status": 1,
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
        20009: {
            "account_id": 20009,
            "nickname": "A124_Android",
            "region": "DEFAULT",
            "level": 47,
            "exp": 59000,
            "rank": 298,
            "ranking_points": 1950,
            "banner_id": 901000010,
            "head_pic": 902000010,
            "avatar_id": 101000013,  # A124
            "clan_id": 0,
            "clan_name": "",
            "has_elite_pass": True,
            "badge_cnt": 90,
            "online_status": 1,
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
        20010: {
            "account_id": 20010,
            "nickname": "Paloma_Arms",
            "region": "DEFAULT",
            "level": 53,
            "exp": 79000,
            "rank": 306,
            "ranking_points": 2520,
            "banner_id": 901000011,
            "head_pic": 902000011,
            "avatar_id": 101000009,  # Paloma
            "clan_id": 50002,
            "clan_name": "FF_LEGENDS",
            "has_elite_pass": True,
            "badge_cnt": 140,
            "online_status": 1,
            "is_online": True,
            "can_invite": True,
            "is_bot": True,
            "last_login_at": now,
        },
    }


def _seed_characters() -> Dict[int, Dict[str, Any]]:
    """Pre-seeded Free Fire 1.39 characters unlocked at max level 8 (real Avatar.csv IDs)."""
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


def _seed_pets() -> Dict[int, Dict[str, Any]]:
    """Pre-seeded Free Fire 1.39 pets unlocked at max level with real Pet.csv IDs."""
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


def _seed_unlocked_items() -> Set[int]:
    """Core seed of unlocked Free Fire 1.39 item IDs (expandable via unlock_items)."""
    items: Set[int] = set()
    # Banners & Avatars (901xxxxxx / 902xxxxxx)
    items.update(range(901000001, 901000031))
    items.update(range(902000001, 902000031))
    # Backpacks / Surfboards / Parachutes / Weapon Skins / Clothes sample ranges
    items.update(range(203000001, 203000051))  # Tops / Jackets
    items.update(range(204000001, 204000051))  # Bottoms / Pants
    items.update(range(205000001, 205000051))  # Shoes
    items.update(range(211000001, 211000051))  # Hats / Masks / Glasses
    items.update(range(907100001, 907100031))  # Weapon skins
    items.update(range(908000001, 908000021))  # Backpacks
    items.update(range(909000001, 909000021))  # Parachutes
    items.update(range(910000001, 910000021))  # Surfboards
    items.update(range(911000001, 911000021))  # Loot boxes
    items.update(DEFAULT_CLOTHES)
    return items


def _seed_lobby_cms(now: int) -> Dict[str, List[Dict[str, Any]]]:
    """Default Lobby CMS seed matching activity_handler.py & Free Fire 1.39 schemas."""
    start_ts = now - 86400
    end_ts = now + 365 * 86400
    event_end_ts = now + 30 * 86400

    splashes = [
        {
            "id": 1,
            "enabled": True,
            "region": "DEFAULT",
            "language": "en",
            "name": "India V1 Season Launch",
            "sort_id": 1,
            "start_time": start_ts,
            "end_time": end_ts,
            "image_url": "/banners/splash_welcome.png",
            "bg_img_url": "/banners/splash_welcome.png",
            "gos_pos": 7,  # NavigationType.ACTIVITY
            "type": 0,     # SplashType.NORMAL
            "link_url": "",
            "version": 1,
        },
        {
            "id": 2,
            "enabled": True,
            "region": "DEFAULT",
            "language": "en",
            "name": "Elite Pass & Luck Royale",
            "sort_id": 2,
            "start_time": start_ts,
            "end_time": end_ts,
            "image_url": "/banners/splash_elite.png",
            "bg_img_url": "/banners/splash_elite.png",
            "gos_pos": 114,  # NavigationType.ELITEPASS_MAIN
            "type": 0,
            "link_url": "",
            "version": 1,
        },
    ]

    adverts = [
        {
            "id": 1,
            "enabled": True,
            "type": 11,  # AdType.LOBBY_ADS
            "sort_id": 1,
            "language": "en",
            "advertisment_url": "/banners/lobby_ad_1.png",
            "ad_start_time": start_ts,
            "ad_end_time": end_ts,
            "go_pos": 7,  # NavigationType.ACTIVITY
            "go_to_switch": True,
            "link_url": "",
        },
        {
            "id": 2,
            "enabled": True,
            "type": 10,  # AdType.LOBBY_ACTIVITY
            "sort_id": 2,
            "language": "en",
            "advertisment_url": "/banners/lobby_ad_2.png",
            "ad_start_time": start_ts,
            "ad_end_time": end_ts,
            "go_pos": 15,  # NavigationType.GACHA
            "go_to_switch": True,
            "link_url": "",
        },
        {
            "id": 3,
            "enabled": True,
            "type": 27,  # AdType.ACTIVITY_MAINBG
            "sort_id": 3,
            "language": "en",
            "advertisment_url": "/banners/activity_banner.png",
            "ad_start_time": start_ts,
            "ad_end_time": end_ts,
            "go_pos": 7,
            "go_to_switch": True,
            "link_url": "",
        },
        {
            "id": 4,
            "enabled": True,
            "type": 4,  # AdType.EP
            "sort_id": 4,
            "language": "en",
            "advertisment_url": "/banners/splash_elite.png",
            "ad_start_time": start_ts,
            "ad_end_time": end_ts,
            "go_pos": 114,
            "go_to_switch": True,
            "link_url": "",
        },
    ]

    announcements = [
        {
            "id": 1,
            "enabled": True,
            "language": "en",
            "order_in_this_language": 1,
            "title": "Welcome to India V1!",
            "desc": "All systems online: Lobby CMS, Luck Royale, Elite Pass, Vault Unlock-All, Events & Guilds.",
            "image_url": "/banners/announce_welcome.png",
            "image_url_for_lobby": "/banners/announce_welcome.png",
            "start_time": start_ts,
            "end_time": end_ts,
            "gos_pos": 7,
            "link_url": "",
        },
        {
            "id": 2,
            "enabled": True,
            "language": "en",
            "order_in_this_language": 2,
            "title": "Season Launch Festival & Bingo",
            "desc": "Check in daily on the Attendance Calendar, flip Bingo cards, and claim free Diamonds!",
            "image_url": "/banners/announce_events.png",
            "image_url_for_lobby": "/banners/announce_events.png",
            "start_time": start_ts,
            "end_time": end_ts,
            "gos_pos": 7,
            "link_url": "",
        },
    ]

    marquees = [
        {
            "id": 1,
            "enabled": True,
            "language": "en",
            "order_in_this_language": 1,
            "content": "Welcome to India V1 Free Fire 1.39! Claim Daily Attendance & Bingo rewards now!",
            "start_time": start_ts,
            "end_time": end_ts,
            "region": "DEFAULT",
            "gos_pos": 7,
        },
        {
            "id": 2,
            "enabled": True,
            "language": "en",
            "order_in_this_language": 2,
            "content": "Season Launch Festival is live — complete missions to earn free Diamonds and Activeness chests!",
            "start_time": start_ts,
            "end_time": end_ts,
            "region": "DEFAULT",
            "gos_pos": 15,
        },
    ]

    broadcasts = [
        {
            "id": 1,
            "enabled": True,
            "nickname": DEFAULT_NICKNAME,
            "navigation_type": 15,
            "source": "Diamond Royale",
            "item_id": 203000001,
            "time_stamp": now - 120,
            "source_id": 1,
        },
        {
            "id": 2,
            "enabled": True,
            "nickname": "Kelly_Dash",
            "navigation_type": 114,
            "source": "Elite Pass",
            "item_id": 204000001,
            "time_stamp": now - 90,
            "source_id": 2,
        },
        {
            "id": 3,
            "enabled": True,
            "nickname": "Hayato_Blade",
            "navigation_type": 15,
            "source": "Weapon Royale",
            "item_id": 907100001,
            "time_stamp": now - 60,
            "source_id": 3,
        },
        {
            "id": 4,
            "enabled": True,
            "nickname": "Wukong_Bush",
            "navigation_type": 3,
            "source": "Store",
            "item_id": 211000001,
            "time_stamp": now - 30,
            "source_id": 4,
        },
    ]

    events: List[Dict[str, Any]] = [
        {
            "id": 1001,
            "activity_id": 1001,
            "enabled": True,
            "group_id": 1,
            "act_title": "Daily Login Bonus",
            "act_text": "Log in to India V1 today to claim Diamonds & Gold!",
            "award_context": "Daily Login Pack",
            "image_url": "/banners/activity_banner.png",
            "image_url_for_lobby": "/banners/lobby_ad_1.png",
            "activity_type": 0,
            "sort_id": 1,
            "is_process_show": 1,
            "act_tag": 2,  # HOT
            "gos_pos": 0,
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 1,
            "awards": [
                {"award_type": 3, "award_id": 0, "award_num": 50},
                {"award_type": 2, "award_id": 0, "award_num": 1000},
                {"award_type": 6, "award_id": 0, "award_num": 20},
            ],
            "table_type": 1,
        },
        {
            "id": 1002,
            "activity_id": 1002,
            "enabled": True,
            "group_id": 1,
            "act_title": "Play 1 Classic Match",
            "act_text": "Drop into Bermuda and survive in Classic or Ranked mode.",
            "award_context": "Match Bonus",
            "image_url": "/banners/activity_banner.png",
            "image_url_for_lobby": "/banners/lobby_ad_1.png",
            "activity_type": 0,
            "sort_id": 2,
            "is_process_show": 1,
            "act_tag": 1,  # NEW
            "gos_pos": 0,
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 1,
            "awards": [
                {"award_type": 2, "award_id": 0, "award_num": 1500},
                {"award_type": 6, "award_id": 0, "award_num": 30},
            ],
            "table_type": 1,
        },
        {
            "id": 1003,
            "activity_id": 1003,
            "enabled": True,
            "group_id": 1,
            "act_title": "Eliminate 3 Opponents",
            "act_text": "Score 3 eliminations across any mode to unlock a weapon crate.",
            "award_context": "Sharpshooter Cache",
            "image_url": "/banners/activity_banner.png",
            "image_url_for_lobby": "/banners/lobby_ad_2.png",
            "activity_type": 0,
            "sort_id": 3,
            "is_process_show": 1,
            "act_tag": 0,
            "gos_pos": 0,
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 3,
            "awards": [
                {"award_type": 1, "award_id": 901000002, "award_num": 1},
                {"award_type": 6, "award_id": 0, "award_num": 25},
            ],
            "table_type": 1,
        },
        {
            "id": 2001,
            "activity_id": 2001,
            "enabled": True,
            "group_id": 2,
            "act_title": "India V1 Festival Launch",
            "act_text": "Celebrate Free Fire 1.39 Season Launch with exclusive rewards!",
            "award_context": "Festival Gift",
            "image_url": "/banners/announce_events.png",
            "image_url_for_lobby": "/banners/lobby_ad_2.png",
            "activity_type": 5,  # FESTIVAL
            "sort_id": 1,
            "is_process_show": 1,
            "act_tag": 2,
            "gos_pos": 0,
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 1,
            "awards": [
                {"award_type": 1, "award_id": 203000003, "award_num": 1},
                {"award_type": 3, "award_id": 0, "award_num": 100},
            ],
            "table_type": 2,
        },
        {
            "id": 2002,
            "activity_id": 2002,
            "enabled": True,
            "group_id": 2,
            "act_title": "Festival Token Exchange",
            "act_text": "Exchange event tokens for legendary outfit pieces.",
            "award_context": "Exchange Bundle",
            "image_url": "/banners/announce_events.png",
            "image_url_for_lobby": "/banners/lobby_ad_2.png",
            "activity_type": 2,  # EXCHANGE
            "sort_id": 2,
            "is_process_show": 0,
            "act_tag": 3,  # LIMIT
            "gos_pos": 3,  # MALL
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 1,
            "awards": [{"award_type": 1, "award_id": 902000002, "award_num": 1}],
            "exchange_items": [{"id": 203000001, "cnt": 1}],
            "table_type": 2,
        },
        {
            "id": 3001,
            "activity_id": 3001,
            "enabled": True,
            "group_id": 3,
            "act_title": "Elite Pass Season Preview",
            "act_text": "Explore the new Fire Pass tiers and claim bonus Diamonds!",
            "award_context": "Season Preview",
            "image_url": "/banners/splash_elite.png",
            "image_url_for_lobby": "/banners/lobby_ad_1.png",
            "activity_type": 20,  # OVERVIEW
            "sort_id": 1,
            "is_process_show": 1,
            "act_tag": 1,
            "gos_pos": 114,
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 1,
            "awards": [
                {"award_type": 3, "award_id": 0, "award_num": 150},
                {"award_type": 2, "award_id": 0, "award_num": 5000},
            ],
            "table_type": 6,  # MEGA_EVENT
        },
        {
            "id": 3002,
            "activity_id": 3002,
            "enabled": True,
            "group_id": 1,
            "act_title": "Visit Luck Royale",
            "act_text": "Check out the latest Diamond Royale & Gold Royale jackpots.",
            "award_context": "Royale Preview",
            "image_url": "/banners/splash_welcome.png",
            "image_url_for_lobby": "/banners/lobby_ad_2.png",
            "activity_type": 21,  # NAVIGATION
            "sort_id": 4,
            "is_process_show": 0,
            "act_tag": 0,
            "gos_pos": 15,
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 1,
            "awards": [{"award_type": 2, "award_id": 0, "award_num": 800}],
            "table_type": 1,
        },
    ]

    bingo_cell_awards = [
        [{"award_type": 2, "award_id": 0, "award_num": 500}],
        [{"award_type": 3, "award_id": 0, "award_num": 25}],
        [{"award_type": 1, "award_id": 901000004, "award_num": 1}],
        [{"award_type": 2, "award_id": 0, "award_num": 750}],
        [{"award_type": 3, "award_id": 0, "award_num": 50}],
        [{"award_type": 1, "award_id": 902000004, "award_num": 1}],
        [{"award_type": 2, "award_id": 0, "award_num": 1000}],
        [{"award_type": 3, "award_id": 0, "award_num": 35}],
        [{"award_type": 1, "award_id": 203000007, "award_num": 1}],
    ]
    for idx, cid in enumerate(range(4001, 4010)):
        events.append({
            "id": cid,
            "activity_id": cid,
            "enabled": True,
            "group_id": 4,
            "act_title": f"Bingo Cell #{idx + 1}",
            "act_text": "Flip this card to complete a Bingo line!",
            "award_context": f"Card #{idx + 1}",
            "image_url": "/banners/activity_banner.png",
            "image_url_for_lobby": "/banners/lobby_ad_1.png",
            "activity_type": 0,
            "sort_id": idx + 1,
            "is_process_show": 1,
            "act_tag": 2,
            "gos_pos": 0,
            "start_time": start_ts,
            "end_time": event_end_ts,
            "cdt_value": 1,
            "awards": bingo_cell_awards[idx],
            "table_type": 4,  # GWBINGO
            "activity_class": 1,
        })

    switch_names = {
        1: "LOTTERY_PR",
        2: "TREASURE_BOX_PR",
        3: "SPECIAL_STORE_ICON",
        4: "GIFT_STORE_IOS",
        5: "EXCHANGE_STORE_IOS",
        6: "LEVEL_LIMITED_FOR_SPLASH_BANNER",
        7: "AD_REWARDED_VIDEO_ENTRANCE",
        8: "PRELOAD_REWARDED_VIDEO_UNDER_WIFI",
        9: "UNFINISHED_TOPUP_ICON_SHOW",
        10: "FINISHED_TOPUP_ICON_SHOW",
        11: "TP_TICK",
        12: "PVE_WEAPON_INFO_SHOW",
        13: "CATAPULT_USING",
        14: "LIVE_SHOW",
        15: "TP_INFO",
        16: "SP_UNITY",
        18: "MYSTERY_BONUS",
        20: "AFTER_MATCH_REWARD_AD",
        21: "CHAMPIONSHIP_ENTRANCE",
        22: "NATIONAL_FLAG",
        23: "ACTIVENESS_LEVEL",
        24: "SECOND_RECHARGE_ICON",
    }
    feature_switches = [
        {"id": sw_id, "name": name, "is_open": sw_id != 6, "enabled": sw_id != 6}
        for sw_id, name in sorted(switch_names.items())
    ]

    bonus_events = [
        {
            "id": 1,
            "enabled": True,
            "region": "DEFAULT",
            "start_day": "2026-01-01",
            "end_day": "2028-12-31",
            "daily_start_time": "00:00:00",
            "daily_end_time": "23:59:59",
            "match_mode": 0,
            "game_mode": 0,
            "map_id": 0,
            "group_mode": 0,
            "exp_bonus": 100,
            "gold_bonus": 100,
            "gold_limit": 5000,
            "debris_limit": 50,
            "today_start_timestamp": now - 3600,
            "today_end_timestamp": now + 82800,
            "tomorrow_start_timestamp": now + 82800,
            "tomorrow_end_timestamp": now + 169200,
        }
    ]

    return {
        "splashes": splashes,
        "adverts": adverts,
        "announcements": announcements,
        "marquees": marquees,
        "broadcasts": broadcasts,
        "events": events,
        "feature_switches": feature_switches,
        "bonus_events": bonus_events,
    }


class CurrencyResult(tuple):
    """Tuple (success, balance) that also supports bool and int for max compatibility."""
    def __new__(cls, success: bool, balance: int):
        return super().__new__(cls, (bool(success), int(balance)))

    @property
    def success(self) -> bool:
        return self[0]

    @property
    def balance(self) -> int:
        return self[1]

    def __bool__(self) -> bool:
        return self[0]

    def __int__(self) -> int:
        return self[1]


class ServerState:
    """Thread-safe central game state store for Barbosa 1.39."""

    def __init__(self, cms_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        now = int(time.time())

        # Account profile store keyed by account_id
        self._profiles: Dict[int, Dict[str, Any]] = {
            DEFAULT_ACCOUNT_ID: {
                "account_id": DEFAULT_ACCOUNT_ID,
                "account_type": 1,
                "nickname": DEFAULT_NICKNAME,
                "region": "DEFAULT",
                "level": 60,
                "exp": 99999,
                "coins": DEFAULT_COINS,
                "gems": DEFAULT_GEMS,
                "banner_id": 901000001,
                "head_pic": 902000001,
                "avatar_id": DEFAULT_AVATAR_ID,
                "skin_color": 50,
                "clothes": list(DEFAULT_CLOTHES),
                "equiped_skills": [],
                "rank": 315,
                "ranking_points": 3250,
                "role": 0,
                "clan_id": 50001,
                "clan_name": "INDIA V1",
                "has_elite_pass": True,
                "ep_event_id": 1,
                "ep_badge": 1,
                "badge_cnt": 100,
                "liked": 9999,
                "show_rank": True,
                "selected_pet_id": 1300000001,
                "selected_pet_skin_id": 1310000001,
                "signature": "India V1 1.39",
                "create_at": 1570000000,
                "last_login_at": now,
            }
        }
        self._claimed_ep_rewards: Dict[int, Set[int]] = {DEFAULT_ACCOUNT_ID: set()}

        # Dynamic mail inbox keyed by account_id -> {mail_id: mail_dict}
        self._next_mail_id = 1000
        self._mails: Dict[int, Dict[int, Dict[str, Any]]] = {DEFAULT_ACCOUNT_ID: {}}

        # Social: all known players, confirmed friends, incoming friend requests
        self._players: Dict[int, Dict[str, Any]] = _seed_players(now)
        self._friends: Dict[int, Set[int]] = {
            DEFAULT_ACCOUNT_ID: {20001, 20002, 20003, 20004, 20005, 20006}
        }
        self._friend_requests: Dict[int, Dict[int, Dict[str, Any]]] = {
            DEFAULT_ACCOUNT_ID: {
                20007: {"from_id": 20007, "to_id": DEFAULT_ACCOUNT_ID, "message": "Let's squad up!", "created_at": now - 300},
                20008: {"from_id": 20008, "to_id": DEFAULT_ACCOUNT_ID, "message": "GG last match", "created_at": now - 120},
            }
        }

        # Squad / Team lobby state
        self._next_team_id = 70001
        self._next_invite_id = 80001
        self._teams: Dict[int, Dict[str, Any]] = {}
        self._player_team: Dict[int, int] = {}
        self._team_invites: Dict[int, List[Dict[str, Any]]] = {}

        # Custom rooms state
        self._next_room_id = 90001
        self._rooms: Dict[int, Dict[str, Any]] = {}

        # Unlocked items, characters/skills, pets
        self._unlocked_items: Set[int] = _seed_unlocked_items()
        self._item_counts: Dict[int, int] = {item_id: 1 for item_id in self._unlocked_items}
        self._characters: Dict[int, Dict[str, Any]] = _seed_characters()
        self._unlocked_skills: Set[int] = {
            c["skill_id"] for c in self._characters.values() if c["skill_id"] > 0
        }
        self._pets: Dict[int, Dict[str, Any]] = _seed_pets()

        # Lobby CMS store (persisted to data/lobby_cms.json) & live event tracker
        self._cms_path: str = cms_path or DEFAULT_CMS_PATH
        self._cms: Dict[str, List[Dict[str, Any]]] = {}
        self._lobby_event_feed: List[Dict[str, Any]] = []
        self._next_lobby_event_id: int = 1
        self._load_or_init_cms(now)

        # Hydrate all accounts from PlayerManager and SQLite persistence engine
        try:
            from core.player import player_manager
            all_players = player_manager.list_all_players()
            for p in all_players:
                aid = p.account_id
                prof = p.get_profile()
                self._profiles[aid] = prof
                self._claimed_ep_rewards.setdefault(aid, set())
                self._mails.setdefault(aid, {})
                self._friends.setdefault(aid, set())
                self._friend_requests.setdefault(aid, {})
                try:
                    db_friends = db.get_friends(aid)
                    if db_friends:
                        self._friends[aid] = set(int(f) for f in db_friends)
                    claims = db.get_claims(aid, claim_type="firepass")
                    if claims:
                        self._claimed_ep_rewards[aid] = {int(c["target_id"]) for c in claims}
                    db_mails = db.get_mails(aid)
                    if db_mails:
                        self._mails[aid] = {int(m["mail_id"]): m for m in db_mails}
                        self._next_mail_id = max([self._next_mail_id] + [int(m["mail_id"]) for m in db_mails])
                    else:
                        self._seed_initial_mails(now, aid)
                except Exception:
                    pass
        except Exception as e:
            pass

        # Ensure default account 10001 is populated
        if DEFAULT_ACCOUNT_ID not in self._profiles:
            try:
                from core.player import player_manager
                p10001 = player_manager.get_or_create(DEFAULT_ACCOUNT_ID)
                self._profiles[DEFAULT_ACCOUNT_ID] = p10001.get_profile()
            except Exception:
                pass

        # Hydrate backward-compatibility mirrors for DEFAULT_ACCOUNT_ID
        try:
            db_inv = db.get_inventory(DEFAULT_ACCOUNT_ID)
            if db_inv:
                self._unlocked_items.update(db_inv.keys())
                self._item_counts.update(db_inv)
        except Exception:
            pass

        self._profile: Dict[str, Any] = self._profiles.get(DEFAULT_ACCOUNT_ID, {})
        self._wallet: Dict[str, int] = {
            "coins": self._profile.get("coins", DEFAULT_COINS),
            "gems": self._profile.get("gems", DEFAULT_GEMS),
        }

    # ------------------------------------------------------------------
    # Internal helpers (must be called under self._lock)
    # ------------------------------------------------------------------
    def _ensure_account(self, account_id: int) -> Dict[str, Any]:
        aid = int(account_id)
        if aid not in self._profiles:
            try:
                from core.player import player_manager
                p = player_manager.get_player(aid)
                if not p:
                    p = player_manager.get_or_create(aid)
                self._profiles[aid] = p.get_profile()
            except Exception:
                now = int(time.time())
                player = self._players.get(aid)
                self._profiles[aid] = {
                    "account_id": aid,
                    "account_type": 1,
                    "nickname": player["nickname"] if player else f"Player_{aid}",
                    "region": "DEFAULT",
                    "level": player["level"] if player else 60,
                    "exp": player["exp"] if player else 99999,
                    "coins": DEFAULT_COINS,
                    "gems": DEFAULT_GEMS,
                    "banner_id": player["banner_id"] if player else 901000001,
                    "head_pic": player["head_pic"] if player else 902000001,
                    "avatar_id": player["avatar_id"] if player else DEFAULT_AVATAR_ID,
                    "skin_color": 0,
                    "clothes": [211000000, 208000000, 203000573, 204000345, 205000299],
                    "equiped_skills": [],
                    "rank": player["rank"] if player else 315,
                    "ranking_points": player["ranking_points"] if player else 3250,
                    "role": 0,
                    "clan_id": player["clan_id"] if player else 0,
                    "clan_name": player["clan_name"] if player else "",
                    "has_elite_pass": True,
                    "ep_event_id": 1,
                    "ep_badge": 1,
                    "badge_cnt": 100,
                    "liked": 100,
                    "show_rank": True,
                    "selected_pet_id": 1300000001,
                    "selected_pet_skin_id": 1310000001,
                    "slots": [904000001, 209000001, 906000001, 903000001, 908000001],
                    "shows": [907000001, 907000005, 907000010, 907000013, 907000014],
                    "emotes": [[1, 909000001], [2, 909000002], [3, 909000003], [4, 909000004]],
                    "loadouts": [500000001, 500000005],
                    "ranking_cards": [],
                    "pve_primary_weapon_skin": 907000001,
                    "hidden_collections": [],
                    "signature": "",
                    "create_at": now,
                    "last_login_at": now,
                }
        self._mails.setdefault(aid, {})
        self._friends.setdefault(aid, set())
        self._friend_requests.setdefault(aid, {})
        self._claimed_ep_rewards.setdefault(aid, set())
        return self._profiles[aid]

    def _resolve_player_summary(self, account_id: int) -> Dict[str, Any]:
        aid = int(account_id)
        try:
            from core.player import player_manager
            rp = player_manager.get_player(aid)
            if rp:
                return rp.to_summary()
        except Exception:
            pass
        if aid in self._players:
            return copy.deepcopy(self._players[aid])
        prof = self._ensure_account(aid)
        return {
            "account_id": prof["account_id"],
            "nickname": prof["nickname"],
            "region": prof["region"],
            "level": prof["level"],
            "exp": prof["exp"],
            "rank": prof["rank"],
            "ranking_points": prof["ranking_points"],
            "banner_id": prof["banner_id"],
            "head_pic": prof["head_pic"],
            "avatar_id": prof["avatar_id"],
            "clan_id": prof["clan_id"],
            "clan_name": prof["clan_name"],
            "has_elite_pass": prof["has_elite_pass"],
            "badge_cnt": prof["badge_cnt"],
            "online_status": 1,
            "is_online": True,
            "can_invite": True,
            "is_bot": False,
            "last_login_at": prof["last_login_at"],
        }

    def _seed_initial_mails(self, now: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        self.add_mail(
            title="Welcome to India V1",
            content="All characters, pets, and vault items are unlocked. Enjoy infinite coins and diamonds!",
            attachments=[{"item_id": 901000001, "count": 1, "type": 1}],
            coins=50000,
            gems=10000,
            mail_type=1,
            sender_nick="India V1 Admin",
            account_id=account_id,
        )
        self.add_mail(
            title="Season Elite Care Package",
            content="Claim your bonus diamonds and gold from the server.",
            attachments=[{"item_id": 907100001, "count": 1, "type": 1}],
            coins=100000,
            gems=5000,
            mail_type=3,
            sender_nick="System",
            account_id=account_id,
        )

    # ------------------------------------------------------------------
    # Profile & Wallet API
    # ------------------------------------------------------------------
    def get_profile(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.get_profile()
            except Exception:
                pass
            return copy.deepcopy(self._ensure_account(account_id))

    def update_profile(self, account_id: int = DEFAULT_ACCOUNT_ID, **kwargs: Any) -> Dict[str, Any]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    updated = p.update_profile(**kwargs)
                    p.save()
                    self._profiles[account_id] = copy.deepcopy(updated)
                    if account_id == DEFAULT_ACCOUNT_ID:
                        self._wallet["coins"] = updated["coins"]
                        self._wallet["gems"] = updated["gems"]
                    return copy.deepcopy(updated)
            except Exception:
                pass
            prof = self._ensure_account(account_id)
            for k, v in kwargs.items():
                if v is not None:
                    prof[k] = copy.deepcopy(v)
            if "coins" in kwargs:
                prof["gold"] = int(kwargs["coins"])
            elif "gold" in kwargs:
                prof["coins"] = int(kwargs["gold"])
            if "gems" in kwargs:
                prof["diamonds"] = int(kwargs["gems"])
            elif "diamonds" in kwargs:
                prof["gems"] = int(kwargs["diamonds"])
            if "avatar_id" in kwargs:
                prof["selected_avatar_id"] = int(kwargs["avatar_id"])
            elif "selected_avatar_id" in kwargs:
                prof["avatar_id"] = int(kwargs["selected_avatar_id"])
            if "selected_pet_id" in kwargs:
                prof["pet_id"] = int(kwargs["selected_pet_id"])
            elif "pet_id" in kwargs:
                prof["selected_pet_id"] = int(kwargs["pet_id"])
            if account_id == DEFAULT_ACCOUNT_ID:
                self._wallet["coins"] = int(prof.get("coins", DEFAULT_COINS))
                self._wallet["gems"] = int(prof.get("gems", DEFAULT_GEMS))
            try:
                db.save_profile(account_id, prof)
                db.log_action(
                    account_id,
                    "PROFILE_UPDATE",
                    f"Profile updated: {list(kwargs.keys())}",
                    kwargs,
                )
            except Exception:
                pass
            return copy.deepcopy(prof)

    def get_wallet(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, int]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    w = p.get_wallet()
                    return {"coins": w["coins"], "gems": w["gems"]}
            except Exception:
                pass
            prof = self._ensure_account(account_id)
            return {"coins": int(prof["coins"]), "gems": int(prof["gems"])}

    def set_wallet(
        self,
        coins: Optional[int] = None,
        gems: Optional[int] = None,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Dict[str, int]:
        with self._lock:
            prof = self._ensure_account(account_id)
            if coins is not None:
                prof["coins"] = max(0, int(coins))
            if gems is not None:
                prof["gems"] = max(0, int(gems))
            c = int(prof["coins"])
            g = int(prof["gems"])
            prof["gold"] = c
            prof["diamonds"] = g
            if account_id == DEFAULT_ACCOUNT_ID:
                self._wallet["coins"] = c
                self._wallet["gems"] = g
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    with p._lock:
                        p.coins = c
                        p.gems = g
            except Exception:
                pass
            try:
                db.update_wallet(account_id, gold=c, diamonds=g)
                db.log_action(
                    account_id,
                    "WALLET_SET",
                    f"Wallet set: coins={c}, gems={g}",
                    {"coins": c, "gems": g},
                )
            except Exception:
                pass
            return {"coins": c, "gems": g}

    def grant_currency(
        self,
        coins: int = 0,
        gems: int = 0,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Dict[str, int]:
        with self._lock:
            prof = self._ensure_account(account_id)
            prof["coins"] = max(0, int(prof["coins"]) + int(coins))
            prof["gems"] = max(0, int(prof["gems"]) + int(gems))
            c = int(prof["coins"])
            g = int(prof["gems"])
            prof["gold"] = c
            prof["diamonds"] = g
            if account_id == DEFAULT_ACCOUNT_ID:
                self._wallet["coins"] = c
                self._wallet["gems"] = g
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    with p._lock:
                        p.coins = c
                        p.gems = g
            except Exception:
                pass
            try:
                db.update_wallet(account_id, gold=c, diamonds=g)
                db.log_action(
                    account_id,
                    "WALLET_GRANT",
                    f"Granted coins={coins}, gems={gems}; balance: coins={c}, gems={g}",
                    {"coins_added": coins, "gems_added": gems, "coins": c, "gems": g},
                )
            except Exception:
                pass
            return {"coins": c, "gems": g}

    def spend_currency(
        self,
        coins: int = 0,
        gems: int = 0,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Tuple[bool, Dict[str, int]]:
        with self._lock:
            prof = self._ensure_account(account_id)
            need_coins = max(0, int(coins))
            need_gems = max(0, int(gems))
            if prof["coins"] < need_coins or prof["gems"] < need_gems:
                return False, {"coins": prof["coins"], "gems": prof["gems"]}
            prof["coins"] -= need_coins
            prof["gems"] -= need_gems
            c = int(prof["coins"])
            g = int(prof["gems"])
            prof["gold"] = c
            prof["diamonds"] = g
            if account_id == DEFAULT_ACCOUNT_ID:
                self._wallet["coins"] = c
                self._wallet["gems"] = g
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    with p._lock:
                        p.coins = c
                        p.gems = g
            except Exception:
                pass
            try:
                db.update_wallet(account_id, gold=c, diamonds=g)
                db.log_action(
                    account_id,
                    "WALLET_SPEND",
                    f"Spent coins={need_coins}, gems={need_gems}; balance: coins={c}, gems={g}",
                    {"coins_spent": need_coins, "gems_spent": need_gems, "coins": c, "gems": g},
                )
            except Exception:
                pass
            return True, {"coins": c, "gems": g}

    def get_gold(self, account_id: int = DEFAULT_ACCOUNT_ID) -> int:
        return self.get_wallet(account_id).get("coins", 0)

    def get_diamond(self, account_id: int = DEFAULT_ACCOUNT_ID) -> int:
        return self.get_wallet(account_id).get("gems", 0)

    def modify_gold(self, account_id_or_delta: int, delta: Optional[int] = None) -> CurrencyResult:
        with self._lock:
            if delta is None:
                aid = DEFAULT_ACCOUNT_ID
                d = int(account_id_or_delta)
            else:
                aid = int(account_id_or_delta)
                d = int(delta)
            cur = self.get_gold(aid)
            if d < 0 and cur + d < 0:
                return CurrencyResult(False, cur)
            new_val = cur + d
            self.set_wallet(coins=new_val, account_id=aid)
            try:
                from core.player import player_manager
                p = player_manager.get_player(aid)
                if p:
                    p.coins = new_val
            except Exception:
                pass
            return CurrencyResult(True, new_val)

    def modify_diamond(self, account_id_or_delta: int, delta: Optional[int] = None) -> CurrencyResult:
        with self._lock:
            if delta is None:
                aid = DEFAULT_ACCOUNT_ID
                d = int(account_id_or_delta)
            else:
                aid = int(account_id_or_delta)
                d = int(delta)
            cur = self.get_diamond(aid)
            if d < 0 and cur + d < 0:
                return CurrencyResult(False, cur)
            new_val = cur + d
            self.set_wallet(gems=new_val, account_id=aid)
            try:
                from core.player import player_manager
                p = player_manager.get_player(aid)
                if p:
                    p.gems = new_val
            except Exception:
                pass
            return CurrencyResult(True, new_val)

    def claim_ep_reward(self, reward_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            self._ensure_account(account_id)
            claimed = self._claimed_ep_rewards[account_id]
            rid = int(reward_id)
            if rid in claimed:
                return False
            claimed.add(rid)
            try:
                db.record_claim(account_id, "firepass", rid, {"reward_id": rid})
                db.log_action(
                    account_id,
                    "FIREPASS_CLAIM",
                    f"Claimed Fire Pass reward #{rid}",
                    {"reward_id": rid},
                )
            except Exception:
                pass
            return True

    def get_claimed_ep_rewards(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[int]:
        with self._lock:
            self._ensure_account(account_id)
            return sorted(self._claimed_ep_rewards[account_id])

    # ------------------------------------------------------------------
    # Dynamic Mail Inbox API
    # ------------------------------------------------------------------
    def add_mail(
        self,
        title: str,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        coins: int = 0,
        gems: int = 0,
        mail_type: int = 1,
        sender_id: int = 0,
        sender_nick: str = "System",
        source: int = 1,
        action_type: int = 0,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Dict[str, Any]:
        with self._lock:
            self._ensure_account(account_id)
            self._next_mail_id += 1
            mail_id = self._next_mail_id
            norm_attachments: List[Dict[str, Any]] = []
            for att in (attachments or []):
                if isinstance(att, dict) and "item_id" in att:
                    norm_attachments.append({
                        "item_id": int(att["item_id"]),
                        "count": int(att.get("count", 1)),
                        "type": int(att.get("type", 1)),
                    })
                elif isinstance(att, int):
                    norm_attachments.append({"item_id": int(att), "count": 1, "type": 1})

            mail = {
                "mail_id": mail_id,
                "account_id": account_id,
                "type": int(mail_type),
                "title": str(title),
                "content": str(content),
                "sender_id": int(sender_id),
                "sender_nick": str(sender_nick),
                "attachments": norm_attachments,
                "coins": max(0, int(coins)),
                "gems": max(0, int(gems)),
                "receive_time": int(time.time()),
                "status": 0,  # 0=unread, 1=read, 2=claimed
                "is_read": False,
                "is_claimed": False,
                "source": int(source),
                "action_type": int(action_type),
            }
            self._mails[account_id][mail_id] = mail
            try:
                db.save_mail(account_id, mail)
                db.log_action(
                    account_id,
                    "MAIL_SEND",
                    f"Sent mail #{mail_id}: {title}",
                    {"mail_id": mail_id, "title": title, "coins": coins, "gems": gems, "attachments": norm_attachments},
                )
            except Exception:
                pass
            return copy.deepcopy(mail)

    def list_mails(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            self._ensure_account(account_id)
            try:
                db_mails = db.get_mails(account_id)
                if db_mails:
                    for m in db_mails:
                        mid = int(m["mail_id"])
                        if mid not in self._mails[account_id]:
                            self._mails[account_id][mid] = m
                        else:
                            self._mails[account_id][mid]["is_claimed"] = bool(m.get("is_claimed", False))
                            self._mails[account_id][mid]["is_read"] = bool(m.get("is_read", False))
                            self._mails[account_id][mid]["status"] = 2 if self._mails[account_id][mid]["is_claimed"] else (1 if self._mails[account_id][mid]["is_read"] else 0)
                        if mid > self._next_mail_id:
                            self._next_mail_id = mid
            except Exception:
                pass
            mails = list(self._mails[account_id].values())
            mails.sort(key=lambda m: m["mail_id"], reverse=True)
            return copy.deepcopy(mails)

    def get_mail(self, mail_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._ensure_account(account_id)
            mail = self._mails[account_id].get(int(mail_id))
            return copy.deepcopy(mail) if mail else None

    def read_mail(self, mail_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._ensure_account(account_id)
            mail = self._mails[account_id].get(int(mail_id))
            if not mail:
                return None
            mail["is_read"] = True
            if mail["status"] == 0:
                mail["status"] = 1
            try:
                db.update_mail(mail_id, is_read=True)
            except Exception:
                pass
            return copy.deepcopy(mail)

    def claim_mail(self, mail_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._lock:
            self._ensure_account(account_id)
            mail = self._mails[account_id].get(int(mail_id))
            if not mail:
                return {
                    "ok": False,
                    "reason": "not_found",
                    "mail": None,
                    "rewards": [],
                    "coins_added": 0,
                    "gems_added": 0,
                    "wallet": self.get_wallet(account_id),
                }
            if mail["is_claimed"]:
                return {
                    "ok": False,
                    "reason": "already_claimed",
                    "mail": copy.deepcopy(mail),
                    "rewards": [],
                    "coins_added": 0,
                    "gems_added": 0,
                    "wallet": self.get_wallet(account_id),
                }

            mail["is_read"] = True
            mail["is_claimed"] = True
            mail["status"] = 2

            coins_added = int(mail.get("coins", 0))
            gems_added = int(mail.get("gems", 0))
            if coins_added or gems_added:
                self.grant_currency(coins=coins_added, gems=gems_added, account_id=account_id)

            rewards = copy.deepcopy(mail.get("attachments", []))
            for att in rewards:
                self.add_item(att["item_id"], att.get("count", 1))

            try:
                db.update_mail(mail_id, is_read=True, is_claimed=True)
                db.record_claim(account_id, "mail", mail_id, {"mail_id": mail_id, "coins": coins_added, "gems": gems_added, "rewards": rewards})
                db.log_action(
                    account_id,
                    "MAIL_CLAIM",
                    f"Claimed mail #{mail_id}: coins={coins_added}, gems={gems_added}",
                    {"mail_id": mail_id, "coins": coins_added, "gems": gems_added, "rewards": rewards},
                )
            except Exception:
                pass

            return {
                "ok": True,
                "reason": "claimed",
                "mail": copy.deepcopy(mail),
                "rewards": rewards,
                "coins_added": coins_added,
                "gems_added": gems_added,
                "wallet": self.get_wallet(account_id),
            }

    def claim_all_mails(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._lock:
            self._ensure_account(account_id)
            claimed_ids: List[int] = []
            total_coins = 0
            total_gems = 0
            all_rewards: List[Dict[str, Any]] = []
            for mail_id in list(self._mails[account_id].keys()):
                mail = self._mails[account_id][mail_id]
                if not mail["is_claimed"]:
                    res = self.claim_mail(mail_id, account_id=account_id)
                    if res["ok"]:
                        claimed_ids.append(mail_id)
                        total_coins += res["coins_added"]
                        total_gems += res["gems_added"]
                        all_rewards.extend(res["rewards"])
            return {
                "ok": True,
                "claimed_mail_ids": claimed_ids,
                "coins_added": total_coins,
                "gems_added": total_gems,
                "rewards": all_rewards,
                "wallet": self.get_wallet(account_id),
            }

    def delete_mail(self, mail_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            self._ensure_account(account_id)
            res = self._mails[account_id].pop(int(mail_id), None) is not None
            try:
                db.delete_mail(mail_id)
                db.log_action(
                    account_id,
                    "MAIL_DELETE",
                    f"Deleted mail #{mail_id}",
                    {"mail_id": mail_id},
                )
            except Exception:
                pass
            return res

    # ------------------------------------------------------------------
    # Friends & Social API
    # ------------------------------------------------------------------
    def get_player(self, account_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            if account_id in self._players:
                return copy.deepcopy(self._players[account_id])
            if account_id in self._profiles:
                return self._resolve_player_summary(account_id)
            return None

    def upsert_player(self, account_id: int, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            now = int(time.time())
            if account_id not in self._players:
                self._players[account_id] = {
                    "account_id": int(account_id),
                    "nickname": fields.get("nickname", f"Player_{account_id}"),
                    "region": fields.get("region", "DEFAULT"),
                    "level": int(fields.get("level", 50)),
                    "exp": int(fields.get("exp", 50000)),
                    "rank": int(fields.get("rank", 305)),
                    "ranking_points": int(fields.get("ranking_points", 2400)),
                    "banner_id": int(fields.get("banner_id", 901000001)),
                    "head_pic": int(fields.get("head_pic", 902000001)),
                    "avatar_id": int(fields.get("avatar_id", DEFAULT_AVATAR_ID)),
                    "clan_id": int(fields.get("clan_id", 0)),
                    "clan_name": fields.get("clan_name", ""),
                    "has_elite_pass": bool(fields.get("has_elite_pass", True)),
                    "badge_cnt": int(fields.get("badge_cnt", 50)),
                    "online_status": int(fields.get("online_status", 1)),
                    "is_online": bool(fields.get("is_online", True)),
                    "can_invite": bool(fields.get("can_invite", True)),
                    "is_bot": bool(fields.get("is_bot", True)),
                    "last_login_at": int(fields.get("last_login_at", now)),
                }
            else:
                for k, v in fields.items():
                    if v is not None:
                        self._players[account_id][k] = copy.deepcopy(v)
            return copy.deepcopy(self._players[account_id])

    def set_player_online(self, account_id: int, online_status: int = 1) -> Optional[Dict[str, Any]]:
        with self._lock:
            player = self._players.get(int(account_id))
            if not player:
                return None
            status = int(online_status)
            player["online_status"] = status
            player["is_online"] = status > 0
            player["can_invite"] = status in (1, 2)
            if status > 0:
                player["last_login_at"] = int(time.time())
            return copy.deepcopy(player)

    def add_friend(
        self,
        friend_id: int,
        account_id: int = DEFAULT_ACCOUNT_ID,
        auto_accept: bool = False,
    ) -> Dict[str, Any]:
        with self._lock:
            self._ensure_account(account_id)
            fid = int(friend_id)
            if fid == account_id:
                return {"ok": False, "status": "self", "player": None}

            player = self.get_player(fid)
            if not player:
                player = self.upsert_player(fid)

            if fid in self._friends[account_id]:
                return {"ok": True, "status": "already_friends", "player": player}

            if auto_accept:
                self._friends[account_id].add(fid)
                self._friends.setdefault(fid, set()).add(account_id)
                self._friend_requests[account_id].pop(fid, None)
                self._friend_requests.setdefault(fid, {}).pop(account_id, None)
                try:
                    db.save_friend(account_id, fid, status="accepted")
                    db.save_friend(fid, account_id, status="accepted")
                    db.log_action(
                        account_id,
                        "FRIEND_ADD",
                        f"Added friend {fid} ({player.get('nickname')})",
                        {"friend_id": fid, "nickname": player.get("nickname")},
                    )
                except Exception:
                    pass
                return {"ok": True, "status": "added", "player": player}

            # Create outgoing request (on target's incoming request map)
            self._friend_requests.setdefault(fid, {})[account_id] = {
                "from_id": account_id,
                "to_id": fid,
                "message": "Add friend",
                "created_at": int(time.time()),
            }
            return {"ok": True, "status": "requested", "player": player}

    def send_friend_request(
        self,
        from_id: int,
        to_id: int = DEFAULT_ACCOUNT_ID,
        message: str = "Let's play!",
    ) -> Dict[str, Any]:
        with self._lock:
            self._ensure_account(to_id)
            fid = int(from_id)
            player = self.get_player(fid)
            if not player:
                player = self.upsert_player(fid)
            if fid in self._friends[to_id]:
                return {"ok": True, "status": "already_friends", "player": player}
            req = {
                "from_id": fid,
                "to_id": to_id,
                "message": str(message),
                "created_at": int(time.time()),
            }
            self._friend_requests.setdefault(to_id, {})[fid] = req
            return {"ok": True, "status": "requested", "request": copy.deepcopy(req), "player": player}

    def accept_friend(self, friend_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._ensure_account(account_id)
            fid = int(friend_id)
            player = self.get_player(fid)
            if not player:
                player = self.upsert_player(fid)
            self._friend_requests[account_id].pop(fid, None)
            self._friend_requests.setdefault(fid, {}).pop(account_id, None)
            self._friends[account_id].add(fid)
            self._friends.setdefault(fid, set()).add(account_id)
            try:
                db.save_friend(account_id, fid, status="accepted")
                db.save_friend(fid, account_id, status="accepted")
                db.log_action(
                    account_id,
                    "FRIEND_ACCEPT",
                    f"Accepted friend {fid} ({player.get('nickname')})",
                    {"friend_id": fid, "nickname": player.get("nickname")},
                )
            except Exception:
                pass
            return player

    def reject_friend(self, friend_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            self._ensure_account(account_id)
            fid = int(friend_id)
            removed_in = self._friend_requests[account_id].pop(fid, None) is not None
            removed_out = self._friend_requests.get(fid, {}).pop(account_id, None) is not None
            return removed_in or removed_out

    def remove_friend(self, friend_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            self._ensure_account(account_id)
            fid = int(friend_id)
            had = fid in self._friends[account_id]
            self._friends[account_id].discard(fid)
            self._friends.get(fid, set()).discard(account_id)
            try:
                db.delete_friend(account_id, fid)
                db.delete_friend(fid, account_id)
                db.log_action(
                    account_id,
                    "FRIEND_REMOVE",
                    f"Removed friend {fid}",
                    {"friend_id": fid},
                )
            except Exception:
                pass
            return had

    def list_friends(
        self,
        account_id: int = DEFAULT_ACCOUNT_ID,
        online_only: bool = False,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            self._ensure_account(account_id)
            res: List[Dict[str, Any]] = []
            for fid in sorted(self._friends[account_id]):
                p = self._resolve_player_summary(fid)
                if online_only and not p.get("is_online", False):
                    continue
                res.append(p)
            # Online & invitable bots first
            res.sort(key=lambda p: (not p.get("is_online", False), not p.get("can_invite", False), p["account_id"]))
            return res

    def list_friend_ids(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[int]:
        with self._lock:
            self._ensure_account(account_id)
            return sorted(self._friends[account_id])

    def list_friend_requests(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            self._ensure_account(account_id)
            reqs: List[Dict[str, Any]] = []
            for req in self._friend_requests[account_id].values():
                entry = copy.deepcopy(req)
                entry["player"] = self._resolve_player_summary(req["from_id"])
                reqs.append(entry)
            reqs.sort(key=lambda r: r["created_at"], reverse=True)
            return reqs

    def list_recommended_friends(
        self,
        account_id: int = DEFAULT_ACCOUNT_ID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            self._ensure_account(account_id)
            friend_ids = self._friends[account_id]
            pending_ids = set(self._friend_requests[account_id].keys())
            candidates = [
                copy.deepcopy(p)
                for pid, p in self._players.items()
                if pid != account_id and pid not in friend_ids and pid not in pending_ids
            ]
            candidates.sort(key=lambda p: (not p.get("is_online", False), -p.get("level", 0)))
            return candidates[: max(0, int(limit))]

    def search_players(
        self,
        query: Any,
        limit: int = 20,
        exclude_account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            q = str(query or "").strip().lower()
            matches: List[Dict[str, Any]] = []
            all_ids = set(self._players.keys()) | set(self._profiles.keys())
            for pid in sorted(all_ids):
                if exclude_account_id is not None and pid == exclude_account_id:
                    continue
                p = self._resolve_player_summary(pid)
                if not q or q in str(p["account_id"]) or q in p["nickname"].lower():
                    matches.append(p)
            return matches[: max(0, int(limit))]

    # ------------------------------------------------------------------
    # Squad / Team Lobby API
    # ------------------------------------------------------------------
    def create_team(
        self,
        leader_id: int = DEFAULT_ACCOUNT_ID,
        mode: str = "squad",
        max_members: Optional[int] = None,
        game_mode: int = 1,
        map_id: int = 1,
        team_name: str = "India V1 Squad",
    ) -> Dict[str, Any]:
        with self._lock:
            # Leave any existing team first
            if leader_id in self._player_team:
                self.leave_team(player_id=leader_id)

            mode_norm = str(mode or "squad").lower()
            cap = int(max_members) if max_members is not None else MODE_MAX_MEMBERS.get(mode_norm, 4)
            cap = max(1, min(4, cap))

            self._next_team_id += 1
            team_id = self._next_team_id
            now = int(time.time())
            leader = self._resolve_player_summary(leader_id)
            team = {
                "team_id": team_id,
                "team_name": str(team_name),
                "leader_id": int(leader_id),
                "mode": mode_norm,
                "max_members": cap,
                "game_mode": int(game_mode),
                "map_id": int(map_id),
                "region": leader.get("region", "DEFAULT"),
                "created_at": now,
                "auto_group": False,
                "matchmaking": False,
                "matchmaking_started_at": 0,
                "members": [
                    {
                        "account_id": leader["account_id"],
                        "nickname": leader["nickname"],
                        "avatar_id": leader["avatar_id"],
                        "level": leader["level"],
                        "rank": leader["rank"],
                        "banner_id": leader["banner_id"],
                        "head_pic": leader["head_pic"],
                        "role": 1,  # 1=leader, 0=member
                        "ready": True,
                        "is_bot": leader.get("is_bot", False),
                        "joined_at": now,
                    }
                ],
            }
            self._teams[team_id] = team
            self._player_team[leader_id] = team_id
            return copy.deepcopy(team)

    def get_team(
        self,
        team_id: Optional[int] = None,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            tid = int(team_id) if team_id is not None else self._player_team.get(account_id)
            if tid is None:
                return None
            team = self._teams.get(tid)
            return copy.deepcopy(team) if team else None

    def invite_player(
        self,
        team_id: int,
        target_id: int,
        inviter_id: int = DEFAULT_ACCOUNT_ID,
        auto_join_bot: bool = False,
    ) -> Dict[str, Any]:
        with self._lock:
            team = self._teams.get(int(team_id))
            if not team:
                return {"ok": False, "reason": "team_not_found", "invite": None, "team": None}
            target = self._resolve_player_summary(int(target_id))
            inviter = self._resolve_player_summary(int(inviter_id))

            self._next_invite_id += 1
            invite = {
                "invite_id": self._next_invite_id,
                "team_id": team["team_id"],
                "team_name": team["team_name"],
                "inviter_id": inviter["account_id"],
                "inviter_nick": inviter["nickname"],
                "target_id": target["account_id"],
                "mode": team["mode"],
                "game_mode": team["game_mode"],
                "map_id": team["map_id"],
                "created_at": int(time.time()),
                "status": "pending",
            }
            invites = self._team_invites.setdefault(target["account_id"], [])
            # Replace prior pending invite for same team
            self._team_invites[target["account_id"]] = [
                inv for inv in invites if inv["team_id"] != team["team_id"]
            ]
            self._team_invites[target["account_id"]].append(invite)

            if team["max_members"] < 4:
                team["max_members"] = 4
                team["mode"] = "squad"

            if auto_join_bot and target.get("is_bot", False) and target.get("can_invite", True):
                joined = self.join_team(team["team_id"], player_id=target["account_id"])
                invite["status"] = "accepted" if joined["ok"] else "pending"
                return {
                    "ok": joined["ok"],
                    "reason": "bot_joined" if joined["ok"] else joined["reason"],
                    "invite": copy.deepcopy(invite),
                    "team": joined["team"],
                }

            return {
                "ok": True,
                "reason": "invited",
                "invite": copy.deepcopy(invite),
                "team": copy.deepcopy(team),
            }

    def join_team(self, team_id: int, player_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._lock:
            team = self._teams.get(int(team_id))
            if not team:
                return {"ok": False, "reason": "team_not_found", "team": None}

            pid = int(player_id)
            if any(m["account_id"] == pid for m in team["members"]):
                return {"ok": True, "reason": "already_member", "team": copy.deepcopy(team)}

            if len(team["members"]) >= team["max_members"]:
                if team["max_members"] < 4:
                    team["max_members"] = 4
                    team["mode"] = "squad"
                else:
                    return {"ok": False, "reason": "team_full", "team": copy.deepcopy(team)}

            # Leave previous team if in another
            prev_tid = self._player_team.get(pid)
            if prev_tid is not None and prev_tid != team["team_id"]:
                self.leave_team(player_id=pid, team_id=prev_tid)

            p = self._resolve_player_summary(pid)
            team["members"].append({
                "account_id": p["account_id"],
                "nickname": p["nickname"],
                "avatar_id": p["avatar_id"],
                "level": p["level"],
                "rank": p["rank"],
                "banner_id": p["banner_id"],
                "head_pic": p["head_pic"],
                "role": 0,
                "ready": True if p.get("is_bot", False) else False,
                "is_bot": p.get("is_bot", False),
                "joined_at": int(time.time()),
            })
            self._player_team[pid] = team["team_id"]
            # Clear pending invites for this team
            if pid in self._team_invites:
                self._team_invites[pid] = [
                    inv for inv in self._team_invites[pid] if inv["team_id"] != team["team_id"]
                ]
            return {"ok": True, "reason": "joined", "team": copy.deepcopy(team)}

    def leave_team(self, player_id: int = DEFAULT_ACCOUNT_ID, team_id: Optional[int] = None) -> bool:
        with self._lock:
            pid = int(player_id)
            tid = int(team_id) if team_id is not None else self._player_team.get(pid)
            if tid is None or tid not in self._teams:
                self._player_team.pop(pid, None)
                return False

            team = self._teams[tid]
            before = len(team["members"])
            team["members"] = [m for m in team["members"] if m["account_id"] != pid]
            self._player_team.pop(pid, None)
            if len(team["members"]) == before:
                return False

            if not team["members"]:
                del self._teams[tid]
            elif team["leader_id"] == pid:
                team["leader_id"] = team["members"][0]["account_id"]
                team["members"][0]["role"] = 1
                team["members"][0]["ready"] = True
            return True

    def kick_player(
        self,
        team_id: int,
        target_id: int,
        requester_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Dict[str, Any]:
        with self._lock:
            team = self._teams.get(int(team_id))
            if not team:
                return {"ok": False, "reason": "team_not_found", "team": None}
            if team["leader_id"] != int(requester_id):
                return {"ok": False, "reason": "not_leader", "team": copy.deepcopy(team)}
            if int(target_id) == int(requester_id):
                return {"ok": False, "reason": "cannot_kick_self", "team": copy.deepcopy(team)}
            removed = self.leave_team(player_id=int(target_id), team_id=int(team_id))
            return {
                "ok": removed,
                "reason": "kicked" if removed else "member_not_found",
                "team": self.get_team(team_id=int(team_id)),
            }

    def set_team_ready(
        self,
        team_id: int,
        player_id: int = DEFAULT_ACCOUNT_ID,
        ready: bool = True,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            team = self._teams.get(int(team_id))
            if not team:
                return None
            for m in team["members"]:
                if m["account_id"] == int(player_id):
                    m["ready"] = bool(ready)
                    break
            return copy.deepcopy(team)

    def update_team_settings(
        self,
        team_id: int,
        mode: Optional[str] = None,
        game_mode: Optional[int] = None,
        map_id: Optional[int] = None,
        max_members: Optional[int] = None,
        auto_group: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            team = self._teams.get(int(team_id))
            if not team:
                return None
            if auto_group is not None:
                team["auto_group"] = bool(auto_group)
            if mode is not None:
                mode_norm = str(mode).lower()
                team["mode"] = mode_norm
                if max_members is None and mode_norm in MODE_MAX_MEMBERS:
                    team["max_members"] = MODE_MAX_MEMBERS[mode_norm]
            if max_members is not None:
                team["max_members"] = max(1, min(4, int(max_members)))
            if game_mode is not None:
                team["game_mode"] = int(game_mode)
            if map_id is not None:
                team["map_id"] = int(map_id)
            return copy.deepcopy(team)

    def list_team_invitations(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            invites = self._team_invites.get(int(account_id), [])
            # Filter out invitations to disbanded teams
            active = [copy.deepcopy(inv) for inv in invites if inv["team_id"] in self._teams]
            self._team_invites[int(account_id)] = active
            return copy.deepcopy(active)

    def decline_team_invitation(self, invite_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            invites = self._team_invites.get(int(account_id), [])
            new_invites = [inv for inv in invites if inv["invite_id"] != int(invite_id)]
            changed = len(new_invites) != len(invites)
            self._team_invites[int(account_id)] = new_invites
            return changed

    def start_matchmaking(
        self,
        team_id: Optional[int] = None,
        account_id: int = DEFAULT_ACCOUNT_ID,
        game_mode: Optional[int] = None,
        map_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            team_dict = self.get_team(team_id=team_id, account_id=account_id)
            if not team_dict:
                team_dict = self.create_team(
                    leader_id=account_id,
                    mode="solo",
                    game_mode=game_mode if game_mode is not None else 1,
                    map_id=map_id if map_id is not None else 1,
                )
            team = self._teams[team_dict["team_id"]]
            if game_mode is not None:
                team["game_mode"] = int(game_mode)
            if map_id is not None:
                team["map_id"] = int(map_id)
            team["matchmaking"] = True
            team["matchmaking_started_at"] = int(time.time())
            return copy.deepcopy(team)

    def cancel_matchmaking(
        self,
        team_id: Optional[int] = None,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            tid = int(team_id) if team_id is not None else self._player_team.get(account_id)
            if tid is None or tid not in self._teams:
                return None
            team = self._teams[tid]
            team["matchmaking"] = False
            team["matchmaking_started_at"] = 0
            return copy.deepcopy(team)

    # ------------------------------------------------------------------
    # Custom Rooms API
    # ------------------------------------------------------------------
    def list_rooms(self) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(list(self._rooms.values()))

    def create_room(
        self,
        owner_id: int = DEFAULT_ACCOUNT_ID,
        name: str = "India V1 Custom Room",
        map_id: int = 1,
        game_mode: int = 1,
        max_players: int = 48,
        password: str = "",
    ) -> Dict[str, Any]:
        with self._lock:
            self._next_room_id += 1
            rid = self._next_room_id
            owner = self._resolve_player_summary(owner_id)
            room = {
                "room_id": rid,
                "name": str(name),
                "owner_id": owner["account_id"],
                "owner_nick": owner["nickname"],
                "map_id": int(map_id),
                "game_mode": int(game_mode),
                "max_players": int(max_players),
                "has_password": bool(password),
                "password": str(password),
                "members": [owner["account_id"]],
                "created_at": int(time.time()),
            }
            self._rooms[rid] = room
            return copy.deepcopy(room)

    def join_room(self, room_id: int, player_id: int = DEFAULT_ACCOUNT_ID, password: str = "") -> Dict[str, Any]:
        with self._lock:
            room = self._rooms.get(int(room_id))
            if not room:
                return {"ok": False, "reason": "room_not_found", "room": None}
            if room["password"] and room["password"] != str(password):
                return {"ok": False, "reason": "wrong_password", "room": None}
            if int(player_id) not in room["members"]:
                if len(room["members"]) >= room["max_players"]:
                    return {"ok": False, "reason": "room_full", "room": copy.deepcopy(room)}
                room["members"].append(int(player_id))
            return {"ok": True, "reason": "joined", "room": copy.deepcopy(room)}

    # ------------------------------------------------------------------
    # Unlocked Items API
    # ------------------------------------------------------------------
    def get_unlocked_items(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Set[int]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.get_unlocked_items()
            except Exception:
                pass
            return set(self._unlocked_items)

    def is_item_unlocked(self, item_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.is_item_unlocked(item_id)
            except Exception:
                pass
            return int(item_id) in self._unlocked_items

    def unlock_item(self, item_id: int, count: int = 1, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            iid = int(item_id)
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    is_new = p.unlock_item(iid, count)
                    if account_id == DEFAULT_ACCOUNT_ID:
                        self._unlocked_items.add(iid)
                        self._item_counts[iid] = max(self._item_counts.get(iid, 0), int(count))
                    return is_new
            except Exception:
                pass
            is_new = iid not in self._unlocked_items
            self._unlocked_items.add(iid)
            cnt = max(self._item_counts.get(iid, 0), int(count))
            self._item_counts[iid] = cnt
            try:
                db.save_inventory_item(account_id, iid, cnt)
            except Exception:
                pass
            return is_new

    def unlock_items(self, item_ids: Iterable[int], account_id: int = DEFAULT_ACCOUNT_ID) -> int:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    added = p.unlock_items(item_ids)
                    if account_id == DEFAULT_ACCOUNT_ID:
                        for raw_id in item_ids:
                            self._unlocked_items.add(int(raw_id))
                            self._item_counts.setdefault(int(raw_id), 1)
                    return added
            except Exception:
                pass
            added = 0
            batch: Dict[int, int] = {}
            for raw_id in item_ids:
                iid = int(raw_id)
                if iid not in self._unlocked_items:
                    self._unlocked_items.add(iid)
                    self._item_counts.setdefault(iid, 1)
                    batch[iid] = self._item_counts[iid]
                    added += 1
            if batch:
                try:
                    db.save_inventory_batch(account_id, batch)
                except Exception:
                    pass
            return added

    def lock_item(self, item_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            iid = int(item_id)
            existed = iid in self._unlocked_items
            self._unlocked_items.discard(iid)
            self._item_counts.pop(iid, None)
            return existed

    def add_item(self, item_id: int, count: int = 1, account_id: int = DEFAULT_ACCOUNT_ID) -> int:
        with self._lock:
            iid = int(item_id)
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    new_cnt = p.add_item(iid, count)
                    if account_id == DEFAULT_ACCOUNT_ID:
                        self._unlocked_items.add(iid)
                        self._item_counts[iid] = new_cnt
                    return new_cnt
            except Exception:
                pass
            self._unlocked_items.add(iid)
            new_cnt = self._item_counts.get(iid, 0) + max(1, int(count))
            self._item_counts[iid] = new_cnt
            try:
                db.save_inventory_item(account_id, iid, new_cnt)
            except Exception:
                pass
            return self._item_counts[iid]

    def consume_item(self, item_id: int, count: int = 1, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            iid = int(item_id)
            qty = max(1, int(count))
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    ok = p.consume_item(iid, qty)
                    if ok and account_id == DEFAULT_ACCOUNT_ID:
                        cur = self._item_counts.get(iid, 0)
                        rem = cur - qty
                        if rem <= 0:
                            self._unlocked_items.discard(iid)
                            self._item_counts.pop(iid, None)
                        else:
                            self._item_counts[iid] = rem
                    return ok
            except Exception:
                pass
            cur = self._item_counts.get(iid, 0)
            if cur < qty:
                return False
            rem = cur - qty
            if rem <= 0:
                self._unlocked_items.discard(iid)
                self._item_counts.pop(iid, None)
            else:
                self._item_counts[iid] = rem
            try:
                db.save_inventory_item(account_id, iid, rem)
            except Exception:
                pass
            return True

    def get_item_count(self, item_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> int:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.get_item_count(item_id)
            except Exception:
                pass
            iid = int(item_id)
            if iid not in self._unlocked_items:
                return 0
            return self._item_counts.get(iid, 1)

    def consume_item(self, item_id: int, count: int = 1, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        with self._lock:
            iid = int(item_id)
            need = max(1, int(count))
            cur = self.get_item_count(iid, account_id=account_id)
            if cur < need:
                return False
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    p.consume_item(iid, need)
            except Exception:
                pass
            new_cnt = cur - need
            if new_cnt <= 0:
                self._unlocked_items.discard(iid)
                self._item_counts.pop(iid, None)
                try:
                    db.delete_inventory_item(account_id, iid)
                except Exception:
                    pass
            else:
                self._item_counts[iid] = new_cnt
                try:
                    db.save_inventory_item(account_id, iid, new_cnt)
                except Exception:
                    pass
            return True

    def get_all_item_counts(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[int, int]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.get_all_item_counts()
            except Exception:
                pass
            return dict(self._item_counts)

    # ------------------------------------------------------------------
    # Unlocked Characters & Skills API
    # ------------------------------------------------------------------
    def list_characters(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.list_characters()
            except Exception:
                pass
            chars = list(self._characters.values())
            chars.sort(key=lambda c: c["avatar_id"])
            return copy.deepcopy(chars)

    def get_character(self, avatar_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.get_character(avatar_id)
            except Exception:
                pass
            c = self._characters.get(int(avatar_id))
            return copy.deepcopy(c) if c else None

    def select_character(self, avatar_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            aid = int(avatar_id)
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    res = p.select_character(aid)
                    prof = self._ensure_account(account_id)
                    prof["avatar_id"] = aid
                    prof["selected_avatar_id"] = aid
                    return res
            except Exception:
                pass
            if aid not in self._characters:
                return None
            for cid, char in self._characters.items():
                char["is_selected"] = (cid == aid)
            prof = self._ensure_account(account_id)
            prof["avatar_id"] = aid
            prof["selected_avatar_id"] = aid
            try:
                db.save_character(account_id, self._characters[aid])
                db.save_profile(account_id, prof)
                db.log_action(
                    account_id,
                    "CHARACTER_SELECT",
                    f"Selected character avatar {aid}",
                    {"avatar_id": aid},
                )
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
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Dict[str, Any]:
        with self._lock:
            aid = int(avatar_id)
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.unlock_character(aid, name, level, skill_id, clothes)
            except Exception:
                pass
            existing = self._characters.get(aid)
            if existing:
                existing["unlocked_level"] = max(int(level), existing["unlocked_level"])
                if name:
                    existing["name"] = name
                if skill_id > 0:
                    existing["skill_id"] = int(skill_id)
                    existing["skill_level"] = 6
                    self._unlocked_skills.add(int(skill_id))
                if clothes is not None:
                    existing["clothes"] = [int(x) for x in clothes]
                try:
                    db.save_character(account_id, existing)
                except Exception:
                    pass
                return copy.deepcopy(existing)

            slots = [{"slot_id": 1, "skill_id": int(skill_id)}] if skill_id > 0 else []
            char = {
                "avatar_id": aid,
                "name": name or f"Character_{aid}",
                "unlocked_level": int(level),
                "exp": 99999,
                "skin_color": 0,
                "clothes": [int(x) for x in (clothes or [])],
                "equiped_skills": slots,
                "skill_id": int(skill_id),
                "skill_level": 6 if skill_id > 0 else 0,
                "is_selected": False,
                "pve_primary_weapon": 0,
            }
            self._characters[aid] = char
            if skill_id > 0:
                self._unlocked_skills.add(int(skill_id))
            try:
                db.save_character(account_id, char)
            except Exception:
                pass
            return copy.deepcopy(char)

    def register_characters(self, characters: Iterable[Dict[str, Any]], account_id: int = DEFAULT_ACCOUNT_ID) -> int:
        with self._lock:
            count = 0
            for c in characters:
                aid = int(c["avatar_id"])
                self.unlock_character(
                    avatar_id=aid,
                    name=c.get("name", ""),
                    level=int(c.get("unlocked_level", 8)),
                    skill_id=int(c.get("skill_id", 0)),
                    clothes=c.get("clothes"),
                    account_id=account_id,
                )
                count += 1
            return count

    def list_unlocked_skills(self) -> Set[int]:
        with self._lock:
            return set(self._unlocked_skills)

    def unlock_skill(self, skill_id: int) -> bool:
        with self._lock:
            sid = int(skill_id)
            is_new = sid not in self._unlocked_skills
            self._unlocked_skills.add(sid)
            return is_new

    def equip_character_skills(self, avatar_id: int, skill_slots: List[Dict[str, int]], account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    for s in skill_slots:
                        p.equip_skill(avatar_id, s.get("slot_id", 0), s.get("skill_id", 0))
                    return p.get_character(avatar_id)
            except Exception:
                pass
            char = self._characters.get(int(avatar_id))
            if not char:
                return None
            normalized = [
                {"slot_id": int(s["slot_id"]), "skill_id": int(s["skill_id"])}
                for s in skill_slots
            ]
            char["equiped_skills"] = normalized
            for s in normalized:
                if s["skill_id"] > 0:
                    self._unlocked_skills.add(s["skill_id"])
            prof = self._ensure_account(account_id)
            if char["is_selected"]:
                prof["equiped_skills"] = copy.deepcopy(normalized)
            try:
                db.save_character(account_id, char)
                db.save_profile(account_id, prof)
                db.log_action(
                    account_id,
                    "CHARACTER_EQUIP_SKILLS",
                    f"Equipped skills for avatar {avatar_id}",
                    {"avatar_id": avatar_id, "skills": normalized},
                )
            except Exception:
                pass
            return copy.deepcopy(char)

    def equip_character_clothes(self, avatar_id: int, clothes: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.equip_clothes(avatar_id, clothes)
            except Exception:
                pass
            char = self._characters.get(int(avatar_id))
            if not char:
                return None
            clean_clothes = [int(c) for c in clothes]
            char["clothes"] = clean_clothes
            for c in clean_clothes:
                self._unlocked_items.add(c)
                self._item_counts.setdefault(c, 1)
            prof = self._ensure_account(account_id)
            if char["is_selected"]:
                prof["clothes"] = list(clean_clothes)
            try:
                db.save_character(account_id, char)
                db.save_profile(account_id, prof)
                db.log_action(
                    account_id,
                    "CHARACTER_EQUIP_CLOTHES",
                    f"Equipped clothes for avatar {avatar_id}",
                    {"avatar_id": avatar_id, "clothes": clean_clothes},
                )
            except Exception:
                pass
            return copy.deepcopy(char)

    # ------------------------------------------------------------------
    # Unlocked Pets API
    # ------------------------------------------------------------------
    def list_pets(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.list_pets()
            except Exception:
                pass
            pets = list(self._pets.values())
            pets.sort(key=lambda p: p["id"])
            return copy.deepcopy(pets)

    def get_pet(self, pet_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.get_pet(pet_id)
            except Exception:
                pass
            p = self._pets.get(int(pet_id))
            return copy.deepcopy(p) if p else None

    def select_pet(
        self,
        pet_id: int,
        skin_id: Optional[int] = None,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            pid = int(pet_id)
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    res = p.select_pet(pid, skin_id=skin_id)
                    prof = self._ensure_account(account_id)
                    prof["selected_pet_id"] = pid
                    prof["pet_id"] = pid
                    if res:
                        prof["selected_pet_skin_id"] = res.get("skin_id", 0)
                    return res
            except Exception:
                pass
            if pid not in self._pets:
                return None
            for k, pet in self._pets.items():
                pet["is_selected"] = (k == pid)
            selected = self._pets[pid]
            if skin_id is not None:
                sid = int(skin_id)
                if sid not in selected["unlocked_skins"]:
                    selected["unlocked_skins"].append(sid)
                selected["skin_id"] = sid
            prof = self._ensure_account(account_id)
            prof["selected_pet_id"] = pid
            prof["pet_id"] = pid
            prof["selected_pet_skin_id"] = selected["skin_id"]
            try:
                db.save_pet(account_id, selected)
                db.save_profile(account_id, prof)
                db.log_action(
                    account_id,
                    "PET_SELECT",
                    f"Selected pet #{pid} (skin {selected['skin_id']})",
                    {"pet_id": pid, "skin_id": selected["skin_id"]},
                )
            except Exception:
                pass
            return copy.deepcopy(selected)

    def unlock_pet(
        self,
        pet_id: int,
        name: str = "",
        level: int = 7,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Dict[str, Any]:
        with self._lock:
            pid = int(pet_id)
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    return p.unlock_pet(pid, name=name, level=level)
            except Exception:
                pass
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
                db.save_pet(account_id, res)
            except Exception:
                pass
            return copy.deepcopy(res)

    def select_pet_skin(
        self,
        pet_id: int,
        skin_id: int,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            pid = int(pet_id)
            pet = self._pets.get(pid)
            if not pet:
                return None
            sid = int(skin_id)
            if sid not in pet["unlocked_skins"]:
                pet["unlocked_skins"].append(sid)
            pet["skin_id"] = sid
            prof = self._ensure_account(account_id)
            if pet["is_selected"]:
                prof["selected_pet_skin_id"] = sid
            try:
                db.save_pet(account_id, pet)
                if pet["is_selected"]:
                    db.save_profile(account_id, prof)
                db.log_action(
                    account_id,
                    "PET_SKIN_SELECT",
                    f"Selected pet skin #{sid} for pet #{pid}",
                    {"pet_id": pid, "skin_id": sid},
                )
            except Exception:
                pass
            return copy.deepcopy(pet)

    def unlock_pet(
        self,
        pet_id: int,
        name: str = "",
        level: int = 7,
        skin_id: int = 0,
        skins: Optional[List[int]] = None,
        actions: Optional[List[int]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            pid = int(pet_id)
            existing = self._pets.get(pid)
            if existing:
                existing["level"] = max(int(level), existing["level"])
                if name:
                    existing["name"] = name
                if skins:
                    for s in skins:
                        if int(s) not in existing["unlocked_skins"]:
                            existing["unlocked_skins"].append(int(s))
                if actions:
                    for a in actions:
                        if int(a) not in existing["actions"]:
                            existing["actions"].append(int(a))
                if skills:
                    existing["skills"] = copy.deepcopy(skills)
                try:
                    db.save_pet(DEFAULT_ACCOUNT_ID, existing)
                except Exception:
                    pass
                return copy.deepcopy(existing)

            skin_list = [int(s) for s in (skins or ([skin_id] if skin_id else []))]
            pet = {
                "id": pid,
                "name": name or f"Pet_{pid}",
                "level": int(level),
                "exp": 99999,
                "is_selected": False,
                "skin_id": int(skin_id) or (skin_list[0] if skin_list else 0),
                "unlocked_skins": skin_list,
                "actions": [int(a) for a in (actions or [1, 2, 3, 4])],
                "skills": copy.deepcopy(skills or []),
            }
            self._pets[pid] = pet
            try:
                db.save_pet(DEFAULT_ACCOUNT_ID, pet)
            except Exception:
                pass
            return copy.deepcopy(pet)

    def register_pets(self, pets: Iterable[Dict[str, Any]]) -> int:
        with self._lock:
            count = 0
            for p in pets:
                self.unlock_pet(
                    pet_id=int(p["id"]),
                    name=p.get("name", ""),
                    level=int(p.get("level", 7)),
                    skin_id=int(p.get("skin_id", 0)),
                    skins=p.get("unlocked_skins"),
                    actions=p.get("actions"),
                    skills=p.get("skills"),
                )
                count += 1
            return count

    # ------------------------------------------------------------------
    # Lobby CMS Store (Persisted to data/lobby_cms.json) & Live Tracker
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_cms_category(category: str) -> str:
        cat = str(category or "").strip().lower()
        aliases = {
            "splash": "splashes",
            "advert": "adverts",
            "ads": "adverts",
            "announcement": "announcements",
            "news": "announcements",
            "marquee": "marquees",
            "broadcast": "broadcasts",
            "event": "events",
            "activity": "events",
            "activities": "events",
            "switch": "feature_switches",
            "switches": "feature_switches",
            "bonus": "bonus_events",
            "bonus_event": "bonus_events",
        }
        cat = aliases.get(cat, cat)
        if cat not in CMS_CATEGORIES:
            raise ValueError(f"Unknown CMS category: {category!r} (valid: {CMS_CATEGORIES})")
        return cat

    @staticmethod
    def _cms_order_field(category: str) -> str:
        if category in ("announcements", "marquees"):
            return "order_in_this_language"
        if category in ("splashes", "adverts", "events"):
            return "sort_id"
        return "id"

    @staticmethod
    def _cms_sort_key(category: str, item: Dict[str, Any]) -> Tuple[int, int]:
        order_field = ServerState._cms_order_field(category)
        return (int(item.get(order_field, item.get("id", 0))), int(item.get("id", 0)))

    def _normalize_cms_item(self, category: str, item: Dict[str, Any], next_id: int) -> Dict[str, Any]:
        entry = copy.deepcopy(item)
        now = int(time.time())
        item_id = entry.get("id")
        if category == "events" and item_id is None and entry.get("activity_id") is not None:
            item_id = entry["activity_id"]
        if item_id is None or int(item_id) <= 0:
            item_id = next_id
        item_id = int(item_id)
        entry["id"] = item_id

        if category == "feature_switches":
            is_open = bool(entry.get("is_open", entry.get("enabled", True)))
            entry["is_open"] = is_open
            entry["enabled"] = is_open
            entry.setdefault("name", f"SWITCH_{item_id}")
            return entry

        entry["enabled"] = bool(entry.get("enabled", True))
        if category == "splashes":
            entry.setdefault("region", "DEFAULT")
            entry.setdefault("language", "en")
            entry.setdefault("name", f"Splash #{item_id}")
            entry.setdefault("sort_id", item_id)
            entry.setdefault("start_time", now - 86400)
            entry.setdefault("end_time", now + 365 * 86400)
            entry.setdefault("image_url", "/banners/splash_welcome.png")
            entry.setdefault("bg_img_url", entry["image_url"])
            entry.setdefault("gos_pos", 0)
            entry.setdefault("type", 0)
            entry.setdefault("link_url", "")
            entry["version"] = int(entry.get("version", 1))
        elif category == "adverts":
            entry.setdefault("type", 11)
            entry.setdefault("sort_id", item_id)
            entry.setdefault("language", "en")
            entry.setdefault("advertisment_url", "/banners/lobby_ad_1.png")
            entry.setdefault("ad_start_time", now - 86400)
            entry.setdefault("ad_end_time", now + 365 * 86400)
            entry.setdefault("go_pos", 0)
            entry.setdefault("go_to_switch", True)
            entry.setdefault("link_url", "")
        elif category == "announcements":
            entry.setdefault("language", "en")
            entry.setdefault("order_in_this_language", item_id)
            entry.setdefault("title", f"Announcement #{item_id}")
            entry.setdefault("desc", "")
            entry.setdefault("image_url", "/banners/announce_welcome.png")
            entry.setdefault("image_url_for_lobby", entry["image_url"])
            entry.setdefault("start_time", now - 86400)
            entry.setdefault("end_time", now + 365 * 86400)
            entry.setdefault("gos_pos", 0)
            entry.setdefault("link_url", "")
        elif category == "marquees":
            entry.setdefault("language", "en")
            entry.setdefault("order_in_this_language", item_id)
            entry.setdefault("content", "")
            entry.setdefault("start_time", now - 86400)
            entry.setdefault("end_time", now + 365 * 86400)
            entry.setdefault("region", "DEFAULT")
            entry.setdefault("gos_pos", 0)
        elif category == "broadcasts":
            entry.setdefault("nickname", DEFAULT_NICKNAME)
            entry.setdefault("navigation_type", 15)
            entry.setdefault("source", "Diamond Royale")
            entry.setdefault("item_id", 203000001)
            entry.setdefault("time_stamp", now)
            entry.setdefault("source_id", item_id)
        elif category == "events":
            entry["activity_id"] = int(entry.get("activity_id", item_id))
            entry["id"] = entry["activity_id"]
            entry.setdefault("group_id", 1)
            entry.setdefault("act_title", f"Event #{item_id}")
            entry.setdefault("act_text", "")
            entry.setdefault("award_context", "Event Reward")
            entry.setdefault("image_url", "/banners/activity_banner.png")
            entry.setdefault("image_url_for_lobby", "/banners/lobby_ad_1.png")
            entry.setdefault("activity_type", 0)
            entry.setdefault("sort_id", item_id)
            entry.setdefault("is_process_show", 1)
            entry.setdefault("act_tag", 0)
            entry.setdefault("gos_pos", 0)
            entry.setdefault("start_time", now - 86400)
            entry.setdefault("end_time", now + 30 * 86400)
            entry.setdefault("cdt_value", 1)
            entry.setdefault("table_type", 1)
            entry.setdefault("awards", [])
        elif category == "bonus_events":
            entry.setdefault("region", "DEFAULT")
            entry.setdefault("start_day", "2026-01-01")
            entry.setdefault("end_day", "2028-12-31")
            entry.setdefault("daily_start_time", "00:00:00")
            entry.setdefault("daily_end_time", "23:59:59")
            entry.setdefault("match_mode", 0)
            entry.setdefault("game_mode", 0)
            entry.setdefault("map_id", 0)
            entry.setdefault("group_mode", 0)
            entry.setdefault("exp_bonus", 100)
            entry.setdefault("gold_bonus", 100)
            entry.setdefault("gold_limit", 5000)
            entry.setdefault("debris_limit", 50)
            entry.setdefault("today_start_timestamp", now - 3600)
            entry.setdefault("today_end_timestamp", now + 82800)
            entry.setdefault("tomorrow_start_timestamp", now + 82800)
            entry.setdefault("tomorrow_end_timestamp", now + 169200)
        return entry

    def _load_or_init_cms(self, now: Optional[int] = None) -> None:
        ts = now if now is not None else int(time.time())
        defaults = _seed_lobby_cms(ts)
        loaded: Optional[Dict[str, Any]] = None
        if os.path.exists(self._cms_path):
            try:
                with open(self._cms_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    loaded = raw
            except Exception:
                loaded = None

        self._cms = {}
        for cat in CMS_CATEGORIES:
            raw_list = loaded.get(cat) if (loaded and isinstance(loaded.get(cat), list)) else defaults[cat]
            norm_list = []
            for idx, item in enumerate(raw_list, 1):
                if isinstance(item, dict):
                    norm_list.append(self._normalize_cms_item(cat, item, idx))
            norm_list.sort(key=lambda x: self._cms_sort_key(cat, x))
            self._cms[cat] = norm_list

        if loaded is None:
            self.save_cms()

    def save_cms(self) -> str:
        """Persist current Lobby CMS store atomically to lobby_cms.json."""
        with self._lock:
            parent = os.path.dirname(os.path.abspath(self._cms_path))
            os.makedirs(parent, exist_ok=True)
            tmp_path = f"{self._cms_path}.tmp"
            payload = {cat: self._cms.get(cat, []) for cat in CMS_CATEGORIES}
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._cms_path)
            return self._cms_path

    def reload_cms(self) -> Dict[str, List[Dict[str, Any]]]:
        """Reload Lobby CMS store from disk."""
        with self._lock:
            self._load_or_init_cms()
            return self.get_cms_snapshot(include_disabled=True)

    def reset_cms(self, category: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Reset one CMS category or all CMS categories back to defaults and persist."""
        with self._lock:
            defaults = _seed_lobby_cms(int(time.time()))
            if category is not None:
                cat = self._validate_cms_category(category)
                self._cms[cat] = copy.deepcopy(defaults[cat])
            else:
                self._cms = copy.deepcopy(defaults)
            self.save_cms()
            return self.get_cms_snapshot(include_disabled=True)

    def get_cms_snapshot(self, include_disabled: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Return a deep copy of all Lobby CMS categories."""
        with self._lock:
            snap: Dict[str, List[Dict[str, Any]]] = {}
            for cat in CMS_CATEGORIES:
                items = self._cms.get(cat, [])
                if not include_disabled:
                    flag = "is_open" if cat == "feature_switches" else "enabled"
                    items = [x for x in items if x.get(flag, True)]
                snap[cat] = copy.deepcopy(items)
            return snap

    def list_cms(self, category: str, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List items in a Lobby CMS category sorted by display order."""
        with self._lock:
            cat = self._validate_cms_category(category)
            items = self._cms.get(cat, [])
            if enabled_only:
                flag = "is_open" if cat == "feature_switches" else "enabled"
                items = [x for x in items if x.get(flag, True)]
            return copy.deepcopy(items)

    def get_cms_item(self, category: str, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single item by id from a Lobby CMS category."""
        with self._lock:
            cat = self._validate_cms_category(category)
            target_id = int(item_id)
            for item in self._cms.get(cat, []):
                if int(item.get("id", 0)) == target_id:
                    return copy.deepcopy(item)
            return None

    def upsert_cms_item(self, category: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an item in a Lobby CMS category and persist to disk."""
        with self._lock:
            cat = self._validate_cms_category(category)
            items = self._cms.setdefault(cat, [])
            max_id = max((int(x.get("id", 0)) for x in items), default=0)
            raw_id = item.get("id")
            if cat == "events" and raw_id is None and item.get("activity_id") is not None:
                raw_id = item["activity_id"]

            if raw_id is not None and int(raw_id) > 0:
                target_id = int(raw_id)
                for idx, existing in enumerate(items):
                    if int(existing.get("id", 0)) == target_id:
                        merged = copy.deepcopy(existing)
                        merged.update(copy.deepcopy(item))
                        if cat == "splashes":
                            merged["version"] = int(existing.get("version", 1)) + 1
                        norm = self._normalize_cms_item(cat, merged, target_id)
                        items[idx] = norm
                        items.sort(key=lambda x: self._cms_sort_key(cat, x))
                        self.save_cms()
                        return copy.deepcopy(norm)

            next_id = int(raw_id) if (raw_id is not None and int(raw_id) > 0) else (max_id + 1)
            norm = self._normalize_cms_item(cat, item, next_id)
            items.append(norm)
            items.sort(key=lambda x: self._cms_sort_key(cat, x))
            self.save_cms()
            return copy.deepcopy(norm)

    def delete_cms_item(self, category: str, item_id: int) -> bool:
        """Delete an item by id from a Lobby CMS category and persist."""
        with self._lock:
            cat = self._validate_cms_category(category)
            target_id = int(item_id)
            items = self._cms.get(cat, [])
            kept = [x for x in items if int(x.get("id", 0)) != target_id]
            if len(kept) == len(items):
                return False
            self._cms[cat] = kept
            self.save_cms()
            return True

    def toggle_cms_item(
        self,
        category: str,
        item_id: int,
        enabled: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Enable/disable (or toggle) an item in a Lobby CMS category and persist."""
        with self._lock:
            cat = self._validate_cms_category(category)
            target_id = int(item_id)
            for item in self._cms.get(cat, []):
                if int(item.get("id", 0)) == target_id:
                    cur = bool(item.get("is_open" if cat == "feature_switches" else "enabled", True))
                    new_val = (not cur) if enabled is None else bool(enabled)
                    item["enabled"] = new_val
                    if cat == "feature_switches":
                        item["is_open"] = new_val
                    if cat == "splashes":
                        item["version"] = int(item.get("version", 1)) + 1
                    self.save_cms()
                    return copy.deepcopy(item)
            return None

    def reorder_cms(self, category: str, ordered_ids: List[int]) -> List[Dict[str, Any]]:
        """Reorder items in a Lobby CMS category by ordered_ids and persist."""
        with self._lock:
            cat = self._validate_cms_category(category)
            items = self._cms.get(cat, [])
            order_field = self._cms_order_field(cat)
            rank_map = {int(iid): idx + 1 for idx, iid in enumerate(ordered_ids)}
            tail_rank = len(rank_map) + 1
            for item in items:
                iid = int(item.get("id", 0))
                if iid in rank_map:
                    item[order_field] = rank_map[iid]
                else:
                    item[order_field] = tail_rank
                    tail_rank += 1
                if cat == "splashes":
                    item["version"] = int(item.get("version", 1)) + 1
            items.sort(key=lambda x: self._cms_sort_key(cat, x))
            self.save_cms()
            return copy.deepcopy(items)

    # Convenience category wrappers
    def list_splashes(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return self.list_cms("splashes", enabled_only=enabled_only)

    def upsert_splash(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.upsert_cms_item("splashes", item)

    def delete_splash(self, item_id: int) -> bool:
        return self.delete_cms_item("splashes", item_id)

    def toggle_splash(self, item_id: int, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.toggle_cms_item("splashes", item_id, enabled=enabled)

    def reorder_splashes(self, ordered_ids: List[int]) -> List[Dict[str, Any]]:
        return self.reorder_cms("splashes", ordered_ids)

    def list_adverts(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return self.list_cms("adverts", enabled_only=enabled_only)

    def upsert_advert(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.upsert_cms_item("adverts", item)

    def delete_advert(self, item_id: int) -> bool:
        return self.delete_cms_item("adverts", item_id)

    def toggle_advert(self, item_id: int, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.toggle_cms_item("adverts", item_id, enabled=enabled)

    def reorder_adverts(self, ordered_ids: List[int]) -> List[Dict[str, Any]]:
        return self.reorder_cms("adverts", ordered_ids)

    def list_announcements(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return self.list_cms("announcements", enabled_only=enabled_only)

    def upsert_announcement(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.upsert_cms_item("announcements", item)

    def delete_announcement(self, item_id: int) -> bool:
        return self.delete_cms_item("announcements", item_id)

    def toggle_announcement(self, item_id: int, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.toggle_cms_item("announcements", item_id, enabled=enabled)

    def reorder_announcements(self, ordered_ids: List[int]) -> List[Dict[str, Any]]:
        return self.reorder_cms("announcements", ordered_ids)

    def list_marquees(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return self.list_cms("marquees", enabled_only=enabled_only)

    def upsert_marquee(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.upsert_cms_item("marquees", item)

    def delete_marquee(self, item_id: int) -> bool:
        return self.delete_cms_item("marquees", item_id)

    def toggle_marquee(self, item_id: int, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.toggle_cms_item("marquees", item_id, enabled=enabled)

    def reorder_marquees(self, ordered_ids: List[int]) -> List[Dict[str, Any]]:
        return self.reorder_cms("marquees", ordered_ids)

    def list_broadcasts(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return self.list_cms("broadcasts", enabled_only=enabled_only)

    def upsert_broadcast(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.upsert_cms_item("broadcasts", item)

    def delete_broadcast(self, item_id: int) -> bool:
        return self.delete_cms_item("broadcasts", item_id)

    def toggle_broadcast(self, item_id: int, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.toggle_cms_item("broadcasts", item_id, enabled=enabled)

    def list_events(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return self.list_cms("events", enabled_only=enabled_only)

    def upsert_event(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.upsert_cms_item("events", item)

    def delete_event(self, item_id: int) -> bool:
        return self.delete_cms_item("events", item_id)

    def toggle_event(self, item_id: int, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.toggle_cms_item("events", item_id, enabled=enabled)

    def reorder_events(self, ordered_ids: List[int]) -> List[Dict[str, Any]]:
        return self.reorder_cms("events", ordered_ids)

    def list_feature_switches(self) -> List[Dict[str, Any]]:
        return self.list_cms("feature_switches", enabled_only=False)

    def set_feature_switch(self, switch_id: int, is_open: bool) -> Dict[str, Any]:
        return self.upsert_cms_item(
            "feature_switches",
            {"id": int(switch_id), "is_open": bool(is_open), "enabled": bool(is_open)},
        )

    def list_bonus_events(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        return self.list_cms("bonus_events", enabled_only=enabled_only)

    def upsert_bonus_event(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return self.upsert_cms_item("bonus_events", item)

    def delete_bonus_event(self, item_id: int) -> bool:
        return self.delete_cms_item("bonus_events", item_id)

    def toggle_bonus_event(self, item_id: int, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        return self.toggle_cms_item("bonus_events", item_id, enabled=enabled)

    def record_lobby_event(
        self,
        endpoint: str,
        category: str,
        summary: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a served banner/popup/news/event hit for live dashboard tracking."""
        with self._lock:
            entry = {
                "event_id": self._next_lobby_event_id,
                "timestamp": int(time.time()),
                "time_str": time.strftime("%H:%M:%S"),
                "endpoint": str(endpoint),
                "category": str(category),
                "summary": str(summary),
                "detail": copy.deepcopy(detail or {}),
            }
            self._next_lobby_event_id += 1
            self._lobby_event_feed.insert(0, entry)
            if len(self._lobby_event_feed) > 300:
                self._lobby_event_feed.pop()
            return copy.deepcopy(entry)

    def get_lobby_event_feed(
        self,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent live popup/banner/news/event hits (newest first)."""
        with self._lock:
            items = self._lobby_event_feed
            if category:
                cat = str(category).strip().lower()
                items = [e for e in items if e["category"].lower() == cat]
            return copy.deepcopy(items[: max(0, int(limit))])

    def clear_lobby_event_feed(self) -> int:
        """Clear recorded live lobby event feed. Returns count cleared."""
        with self._lock:
            cnt = len(self._lobby_event_feed)
            self._lobby_event_feed.clear()
            return cnt

    # ------------------------------------------------------------------
    # Dashboard / Diagnostics Snapshot
    # ------------------------------------------------------------------
    def get_snapshot(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._lock:
            return {
                "profile": self.get_profile(account_id),
                "wallet": self.get_wallet(account_id),
                "mails": self.list_mails(account_id),
                "friends": self.list_friends(account_id),
                "friend_requests": self.list_friend_requests(account_id),
                "recommended_friends": self.list_recommended_friends(account_id),
                "team": self.get_team(account_id=account_id),
                "team_invitations": self.list_team_invitations(account_id),
                "rooms": self.list_rooms(),
                "unlocked_items_count": len(self._unlocked_items),
                "characters_count": len(self._characters),
                "skills_count": len(self._unlocked_skills),
                "pets_count": len(self._pets),
                "characters": self.list_characters(),
                "pets": self.list_pets(),
                "cms": self.get_cms_snapshot(include_disabled=True),
                "lobby_event_feed": self.get_lobby_event_feed(limit=50),
            }


# Global singleton imported by handlers and dashboard_api
state = ServerState()


def get_state() -> ServerState:
    """Return the global thread-safe ServerState singleton."""
    return state
