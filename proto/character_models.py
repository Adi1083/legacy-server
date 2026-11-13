"""
Protobuf models, catalogs, and ServerState synchronization for Free Fire 1.39
Characters (Avatars), Character Skills, Skill Slots, and Clothes.

All ServiceMessageTypeHTTP endpoints, ProtoMember tags, wire types, and packed
flags are verified against Free Fire 1.39 x86 libil2cpp.so + dump.cs and
DES-decrypted APK config CSVs (Avatar.csv, AvatarSkill.csv, AvatarProfile.csv,
AvatarSkillSlot.csv, AvatarSuit.csv, AvatarLevelCard.csv).
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .decoder import decode_proto, get_packed_varints, get_varint
from .encoder import (
    encode_bool,
    encode_packed_uint32,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)
from .pet_models import encode_pet_info
from .store_models import TransReason, encode_exchange_change_data, encode_item


# ---------------------------------------------------------------------------
# Free Fire 1.39 Real Avatar, Skill & Level Catalogs (from APK Config CSVs)
# ---------------------------------------------------------------------------

DEFAULT_AVATAR_ID = 102000004  # Adam (Male base)
DEFAULT_BASE_CLOTHES: List[int] = [
    211000000,  # Hair
    208000000,  # Face
    203000573,  # Top
    204000345,  # Pants
    205000299,  # Shoes
]

# avatar_id -> metadata extracted from Avatar.csv, AvatarSuit.csv, AvatarSkill.csv
AVATAR_CATALOG: Dict[int, Dict[str, Any]] = {
    101000001: {
        "avatar_id": 101000001,
        "name": "Eva",
        "gender": 1,
        "skin_color": 50,
        "default_clothes": [211000000, 208000000, 203000573, 204000345, 205000299],
        "skills": [],
        "pve_primary_weapon": 907100098,
    },
    101000005: {
        "avatar_id": 101000005,
        "name": "Olivia",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000058, 204000045, 205000028],
        "skills": [101, 102, 103, 104, 105, 106],
        "pve_primary_weapon": 0,
    },
    101000006: {
        "avatar_id": 101000006,
        "name": "Kelly",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000059, 204000046, 205000029],
        "skills": [201, 202, 203, 204, 205, 206],
        "pve_primary_weapon": 0,
    },
    101000007: {
        "avatar_id": 101000007,
        "name": "Nikita",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000090, 204000062, 205000046],
        "skills": [501, 502, 503, 504, 505, 506],
        "pve_primary_weapon": 0,
    },
    101000008: {
        "avatar_id": 101000008,
        "name": "Misha",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000127, 204000075, 205000055],
        "skills": [601, 602, 603, 604, 605, 606],
        "pve_primary_weapon": 0,
    },
    101000009: {
        "avatar_id": 101000009,
        "name": "Paloma",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000243, 204000140, 205000116],
        "skills": [901, 902, 903, 904, 905, 906],
        "pve_primary_weapon": 0,
    },
    101000010: {
        "avatar_id": 101000010,
        "name": "Caroline",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000295],
        "skills": [1101, 1102, 1103, 1104, 1105, 1106],
        "pve_primary_weapon": 907100106,
    },
    101000011: {
        "avatar_id": 101000011,
        "name": "Moco",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000376, 204000213, 205000178],
        "skills": [1401, 1402, 1403, 1404, 1405, 1406],
        "pve_primary_weapon": 0,
    },
    101000012: {
        "avatar_id": 101000012,
        "name": "Laura",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000455, 204000263, 205000221],
        "skills": [1701, 1702, 1703, 1704, 1705, 1706],
        "pve_primary_weapon": 907100094,
    },
    101000013: {
        "avatar_id": 101000013,
        "name": "A124",
        "gender": 1,
        "skin_color": 0,
        "default_clothes": [211000000, 203000566, 204000340, 205000294],
        "skills": [1901, 1902, 1903, 1904, 1905, 1906],
        "pve_primary_weapon": 0,
    },
    102000004: {
        "avatar_id": 102000004,
        "name": "Adam",
        "gender": 2,
        "skin_color": 50,
        "default_clothes": [211000000, 208000000, 203000573, 204000345, 205000299],
        "skills": [],
        "pve_primary_weapon": 907100098,
    },
    102000005: {
        "avatar_id": 102000005,
        "name": "Andrew",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000056, 204000043, 205000026],
        "skills": [401, 402, 403, 404, 405, 406],
        "pve_primary_weapon": 0,
    },
    102000006: {
        "avatar_id": 102000006,
        "name": "Ford",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000057, 204000044, 205000027],
        "skills": [301, 302, 303, 304, 305, 306],
        "pve_primary_weapon": 0,
    },
    102000007: {
        "avatar_id": 102000007,
        "name": "Maxim",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000160, 204000096, 205000072],
        "skills": [701, 702, 703, 704, 705, 706],
        "pve_primary_weapon": 907100100,
    },
    102000008: {
        "avatar_id": 102000008,
        "name": "Kla",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000177, 204000107, 205000092],
        "skills": [801, 802, 803, 804, 805, 806],
        "pve_primary_weapon": 0,
    },
    102000009: {
        "avatar_id": 102000009,
        "name": "Miguel",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000268, 204000151, 205000121],
        "skills": [1001, 1002, 1003, 1004, 1005, 1006],
        "pve_primary_weapon": 907100099,
    },
    102000010: {
        "avatar_id": 102000010,
        "name": "Antonio",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000333, 204000188, 205000155],
        "skills": [1301, 1302, 1303, 1304, 1305, 1306],
        "pve_primary_weapon": 907100102,
    },
    102000011: {
        "avatar_id": 102000011,
        "name": "Wukong",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000353, 204000200, 205000167],
        "skills": [1201, 1202, 1203, 1204, 1205, 1206],
        "pve_primary_weapon": 0,
    },
    102000012: {
        "avatar_id": 102000012,
        "name": "Hayato",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000418, 204000237, 205000198],
        "skills": [1501, 1502, 1503, 1504, 1505, 1506],
        "pve_primary_weapon": 0,
    },
    102000013: {
        "avatar_id": 102000013,
        "name": "Rafael",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000528, 204000310, 205000266],
        "skills": [1801, 1802, 1803, 1804, 1805, 1806],
        "pve_primary_weapon": 907100108,
    },
    102000014: {
        "avatar_id": 102000014,
        "name": "Joseph",
        "gender": 2,
        "skin_color": 0,
        "default_clothes": [211000000, 203000572, 204000344, 205000298],
        "skills": [2001, 2002, 2003, 2004, 2005, 2006],
        "pve_primary_weapon": 0,
    },
}

SPECIAL_AVATAR_IDS: List[int] = [
    aid for aid, meta in AVATAR_CATALOG.items() if meta["skills"]
]

ALL_MAX_SKILL_IDS: List[int] = [
    meta["skills"][-1] for meta in AVATAR_CATALOG.values() if meta["skills"]
]

# level -> (debris_count, coins, gems) from AvatarProfile.csv
UNLOCK_PROFILE_COSTS: Dict[int, Tuple[int, int, int]] = {
    1: (0, 0, 0),
    2: (100, 500, 25),
    3: (300, 2000, 80),
    4: (500, 4500, 160),
    5: (700, 8000, 270),
    6: (1500, 12000, 400),
    7: (3000, 20000, 500),
    8: (6000, 30000, 750),
}

# (slot_id, gems, coins) from AvatarSkillSlot.csv
SKILL_SLOT_UNLOCK_COSTS: Tuple[Tuple[int, int, int], ...] = (
    (1, 100, 8000),
    (2, 150, 12000),
)

# AvatarLevelCard.csv -> target max level
LEVEL_CARD_TARGETS: Dict[int, int] = {
    812000001: 4,
    812000002: 6,
    812000003: 8,
}

# Level 5 & Level 7 item rewards from AvatarProfile.csv
LEVEL_ITEM_REWARDS: Dict[Tuple[int, int], int] = {
    (101000005, 5): 700000009, (101000005, 7): 901000013,
    (101000006, 5): 700000010, (101000006, 7): 901000012,
    (102000005, 5): 700000007, (102000005, 7): 901000011,
    (102000006, 5): 700000008, (102000006, 7): 901000014,
    (101000007, 5): 700000012, (101000007, 7): 901000015,
    (101000008, 5): 700000018, (101000008, 7): 901000016,
    (102000007, 5): 203000174, (102000007, 7): 901000035,
    (102000008, 5): 203000209, (102000008, 7): 901000044,
    (101000009, 5): 203000244, (101000009, 7): 901000061,
    (102000009, 5): 203000264, (102000009, 7): 901000062,
    (101000010, 5): 203000287, (101000010, 7): 901000075,
    (102000010, 5): 203000339, (102000010, 7): 901000086,
    (102000011, 5): 203000347, (102000011, 7): 901000094,
    (101000011, 5): 203000377, (101000011, 7): 901000108,
    (102000012, 5): 203000415, (102000012, 7): 901000126,
    (101000012, 5): 203000472, (101000012, 7): 901000145,
    (102000013, 5): 203000505, (102000013, 7): 901000164,
    (101000013, 5): 203000561, (101000013, 7): 901000188,
    (102000014, 5): 203000565, (102000014, 7): 901000189,
}


# ---------------------------------------------------------------------------
# State Helpers & Synchronization
# ---------------------------------------------------------------------------

def build_default_equiped_skills(avatar_id: int) -> List[Dict[str, int]]:
    """Build default unlocked skill slots for a character (slot 0 innate + slots 1, 2)."""
    meta = AVATAR_CATALOG.get(int(avatar_id))
    if not meta or not meta["skills"]:
        return []
    max_skill = int(meta["skills"][-1])
    return [
        {"slot_id": 0, "skill_id": max_skill},
        {"slot_id": 1, "skill_id": 0},
        {"slot_id": 2, "skill_id": 0},
    ]


def build_default_character(avatar_id: int, is_selected: bool = False) -> Dict[str, Any]:
    """Construct a complete max-level character state entry for avatar_id."""
    aid = int(avatar_id)
    meta = AVATAR_CATALOG[aid]
    skills = meta["skills"]
    max_skill = int(skills[-1]) if skills else 0
    return {
        "avatar_id": aid,
        "name": meta["name"],
        "unlocked_level": 8,
        "exp": 99999,
        "skin_color": int(meta["skin_color"]),
        "clothes": list(meta["default_clothes"]),
        "equiped_skills": build_default_equiped_skills(aid),
        "skill_id": max_skill,
        "skill_level": 6 if max_skill else 0,
        "is_selected": bool(is_selected),
        "pve_primary_weapon": int(meta["pve_primary_weapon"]),
    }


def _normalize_existing_character(aid: int, existing: Dict[str, Any], is_selected: bool) -> Dict[str, Any]:
    """Merge an existing valid 1.39 character entry with real defaults while preserving customizations."""
    meta = AVATAR_CATALOG[aid]
    skills = meta["skills"]
    max_skill = int(skills[-1]) if skills else 0

    clothes = [int(c) for c in (existing.get("clothes") or []) if int(c) > 0]
    if not clothes:
        clothes = list(meta["default_clothes"])

    raw_slots = existing.get("equiped_skills") or []
    slot_map: Dict[int, int] = {}
    for entry in raw_slots:
        if isinstance(entry, dict):
            slot_map[int(entry.get("slot_id", 0))] = int(entry.get("skill_id", 0))
    if skills:
        # Ensure slot 0 has the character's innate skill and slots 1, 2 remain unlocked.
        if 0 not in slot_map or slot_map[0] <= 0:
            slot_map[0] = max_skill
        slot_map.setdefault(1, 0)
        slot_map.setdefault(2, 0)
        equiped_skills = [{"slot_id": sid, "skill_id": slot_map[sid]} for sid in sorted(slot_map)]
    else:
        equiped_skills = []

    skin_color = int(existing.get("skin_color", meta["skin_color"]))
    if skin_color == 0 and meta["skin_color"] != 0:
        skin_color = int(meta["skin_color"])

    return {
        "avatar_id": aid,
        "name": meta["name"],
        "unlocked_level": max(8, int(existing.get("unlocked_level", 8))),
        "exp": int(existing.get("exp", 99999)),
        "skin_color": skin_color,
        "clothes": clothes,
        "equiped_skills": equiped_skills,
        "skill_id": max_skill,
        "skill_level": 6 if max_skill else 0,
        "is_selected": bool(is_selected),
        "pve_primary_weapon": int(existing.get("pve_primary_weapon") or meta["pve_primary_weapon"]),
    }


def sync_profile_with_character(account: Dict[str, Any], char: Dict[str, Any]) -> None:
    """Copy a selected character's visual/skill fields into an account profile dict."""
    account["avatar_id"] = int(char["avatar_id"])
    account["skin_color"] = int(char.get("skin_color", 0))
    account["clothes"] = list(char.get("clothes") or DEFAULT_BASE_CLOTHES)
    account["equiped_skills"] = copy.deepcopy(char.get("equiped_skills") or [])
    account["unlocked_level"] = int(char.get("unlocked_level", 8))
    account["pve_primary_weapon"] = int(char.get("pve_primary_weapon", 0))


def sync_characters_to_state(state_obj: Any, account_id: int = 10001) -> List[Dict[str, Any]]:
    """
    Replace legacy placeholder character IDs (1..23) in ServerState with all 21
    real Free Fire 1.39 characters at max level, unlock all clothes and skills,
    and align the account profile's avatar_id/clothes/skills for 3D rendering.
    """
    with state_obj._lock:
        existing_chars: Dict[int, Dict[str, Any]] = dict(state_obj._characters)
        account = state_obj._ensure_account(account_id)

        selected_aid = 0
        for aid, char in existing_chars.items():
            if int(aid) in AVATAR_CATALOG and char.get("is_selected"):
                selected_aid = int(aid)
                break
        if selected_aid not in AVATAR_CATALOG:
            prof_aid = int(account.get("avatar_id", 0))
            selected_aid = prof_aid if prof_aid in AVATAR_CATALOG else DEFAULT_AVATAR_ID

        new_chars: Dict[int, Dict[str, Any]] = {}
        for aid, meta in AVATAR_CATALOG.items():
            is_sel = aid == selected_aid
            prev = existing_chars.get(aid)
            if prev is not None:
                char_entry = _normalize_existing_character(aid, prev, is_sel)
            else:
                char_entry = build_default_character(aid, is_selected=is_sel)
            new_chars[aid] = char_entry

            for cloth_id in char_entry["clothes"]:
                if int(cloth_id) > 0:
                    state_obj._unlocked_items.add(int(cloth_id))

        state_obj._characters.clear()
        state_obj._characters.update(new_chars)

        # Keep real skill IDs (>= 100) and ensure all 19 max-level character skills are unlocked.
        cleaned_skills = {int(s) for s in state_obj._unlocked_skills if int(s) >= 100}
        cleaned_skills.update(ALL_MAX_SKILL_IDS)
        state_obj._unlocked_skills.clear()
        state_obj._unlocked_skills.update(cleaned_skills)

        # Ensure all level-unlock clothes/bundles/banners are marked owned too.
        for item_id in LEVEL_ITEM_REWARDS.values():
            state_obj._unlocked_items.add(int(item_id))

        sync_profile_with_character(account, new_chars[selected_aid])
        return copy.deepcopy(list(new_chars.values()))


# ---------------------------------------------------------------------------
# Request Decoders
# ---------------------------------------------------------------------------

def decode_select_profile_req(data: bytes) -> int:
    """Decode proto.CSSelectProfileReq (1: uint avatar_id)."""
    if not data:
        return 0
    return get_varint(decode_proto(data), 1, 0)


def decode_unlock_profile_req(data: bytes) -> Tuple[int, int, int]:
    """Decode proto.CSUnlockProfileReq (1: avatar_id, 2: unlock_level, 3: currency_type)."""
    if not data:
        return 0, 1, 1
    fields = decode_proto(data)
    return (
        get_varint(fields, 1, 0),
        get_varint(fields, 2, 1),
        get_varint(fields, 3, 1),
    )


def decode_upgrade_profile_req(data: bytes) -> Tuple[int, int]:
    """Decode proto.CSUpgradeProfileReq (1: avatar_id, 2: level_card_id)."""
    if not data:
        return 0, 0
    fields = decode_proto(data)
    return get_varint(fields, 1, 0), get_varint(fields, 2, 0)


def decode_unlock_skill_slot_req(data: bytes) -> Tuple[int, int, int]:
    """Decode proto.CSUnlockSkillSlotReq (1: avatar_id, 2: slot_id, 3: currency_type)."""
    if not data:
        return 0, 1, 1
    fields = decode_proto(data)
    return (
        get_varint(fields, 1, 0),
        get_varint(fields, 2, 1),
        get_varint(fields, 3, 1),
    )


def decode_equip_skill_req(data: bytes) -> Tuple[int, int, int]:
    """Decode proto.CSEquipSkillReq (1: avatar_id, 2: slot_id, 3: skill_id)."""
    if not data:
        return 0, 0, 0
    fields = decode_proto(data)
    return (
        get_varint(fields, 1, 0),
        get_varint(fields, 2, 0),
        get_varint(fields, 3, 0),
    )


def decode_change_clothes_req(data: bytes) -> Tuple[int, List[int], Optional[int]]:
    """Decode proto.CSChangeClothesReq (1: avatar_id, 2: uint[] clothes, 3: skin_color)."""
    if not data:
        return 0, [], None
    fields = decode_proto(data)
    avatar_id = get_varint(fields, 1, 0)
    clothes = [int(c) for c in get_packed_varints(fields, 2) if int(c) > 0]
    skin_color = get_varint(fields, 3, -1)
    return avatar_id, clothes, (None if skin_color < 0 else skin_color)


# ---------------------------------------------------------------------------
# Response Encoders
# ---------------------------------------------------------------------------

def encode_avatar_skill_slot(slot_id: int, skill_id: int) -> bytes:
    """Encode proto.AvatarSkillSlot (1: uint slot_id, 2: uint skill_id)."""
    return encode_uint32(1, int(slot_id)) + encode_uint32(2, int(skill_id))


def encode_avatar_profile(profile: Dict[str, Any]) -> bytes:
    """
    Encode proto.AvatarProfile:
      1: uint avatar_id
      2: uint unlocked_level
      3: uint skin_color
      4: uint[] clothes [PACKED]
      5: List<AvatarSkillSlot> equiped_skills (keeps skill_id=0 for open empty slots)
      6: bool is_selected
      7: uint pve_primary_weapon
    """
    avatar_id = int(profile.get("avatar_id", DEFAULT_AVATAR_ID))
    clothes = [int(c) for c in (profile.get("clothes") or []) if int(c) > 0]
    pve_weapon = int(profile.get("pve_primary_weapon", 0))

    skill_bytes = bytearray()
    for idx, entry in enumerate(profile.get("equiped_skills") or []):
        if isinstance(entry, dict):
            slot_id = int(entry.get("slot_id", idx))
            skill_id = int(entry.get("skill_id", 0))
        elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
            slot_id = int(entry[0])
            skill_id = int(entry[1])
        else:
            slot_id = idx
            skill_id = int(entry)
        skill_bytes += encode_submessage(5, encode_avatar_skill_slot(slot_id, skill_id))

    parts = [
        encode_uint32(1, avatar_id),
        encode_uint32(2, int(profile.get("unlocked_level", 8))),
        encode_uint32(3, int(profile.get("skin_color", 0))),
        encode_packed_uint32(4, clothes),
        bytes(skill_bytes),
        encode_bool(6, bool(profile.get("is_selected", False))),
    ]
    if pve_weapon:
        parts.append(encode_uint32(7, pve_weapon))
    return b"".join(parts)


def encode_get_profile_list_res(profiles: Sequence[Dict[str, Any]]) -> bytes:
    """Encode proto.CSGetProfileListRes (1: List<AvatarProfile> profiles)."""
    return b"".join(encode_submessage(1, encode_avatar_profile(p)) for p in profiles)


def encode_get_skill_list_res(account_id: int, skills: Sequence[int]) -> bytes:
    """Encode proto.CSGetSkillListRes (1: ulong account_id, 2: uint[] skills [PACKED])."""
    clean_skills = sorted({int(s) for s in skills if int(s) > 0})
    parts = [encode_uint64(1, int(account_id))]
    if clean_skills:
        parts.append(encode_packed_uint32(2, clean_skills))
    return b"".join(parts)


def encode_login_profile_res(
    account_id: int,
    profiles: Sequence[Dict[str, Any]],
    skills: Sequence[int],
    selected_pet: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Encode proto.LoginProfileRes (/LoginGetProfile):
      1: CSGetProfileListRes profile_res
      2: CSGetSkillListRes skill_res
      3: PetInfo pet_info
    """
    parts = [
        encode_submessage(1, encode_get_profile_list_res(profiles)),
        encode_submessage(2, encode_get_skill_list_res(account_id, skills)),
    ]
    if selected_pet:
        parts.append(encode_submessage(3, encode_pet_info(selected_pet)))
    return b"".join(parts)


def encode_select_profile_res(profile: Dict[str, Any]) -> bytes:
    """Encode proto.CSSelectProfileRes (1: AvatarProfile profile)."""
    return encode_submessage(1, encode_avatar_profile(profile))


def _encode_award_items(award_items: Sequence[Any]) -> bytes:
    buf = bytearray()
    for item in award_items:
        if isinstance(item, int):
            buf += encode_submessage(2, encode_item(item_id=item, cnt=1))
        elif isinstance(item, dict):
            buf += encode_submessage(2, encode_item(**item))
        else:
            buf += encode_submessage(2, bytes(item))
    return bytes(buf)


def encode_unlock_profile_res(
    affected_profiles: Sequence[Dict[str, Any]],
    award_items: Sequence[Any] = (),
) -> bytes:
    """
    Encode proto.CSUnlockProfileRes:
      1: List<AvatarProfile> affected_profiles
      2: List<Item> award_items
    """
    parts = [encode_submessage(1, encode_avatar_profile(p)) for p in affected_profiles]
    if award_items:
        parts.append(_encode_award_items(award_items))
    return b"".join(parts)


def encode_upgrade_profile_res(
    affected_profiles: Sequence[Dict[str, Any]],
    award_items: Sequence[Any] = (),
) -> bytes:
    """
    Encode proto.CSUpgradeProfileRes:
      1: List<AvatarProfile> affected_profiles
      2: List<Item> award_items
    """
    parts = [encode_submessage(1, encode_avatar_profile(p)) for p in affected_profiles]
    if award_items:
        parts.append(_encode_award_items(award_items))
    return b"".join(parts)


def encode_unlock_profile_config(
    avatar_id: int,
    level: int,
    debris_count: int,
    coins: int,
    gems: int,
) -> bytes:
    """
    Encode proto.UnlockProfileConfig (tags skip 3..6):
      1: uint avatar_id
      2: uint level
      7: uint debris_count
      8: uint coins
      9: uint gems
    """
    return b"".join([
        encode_uint32(1, int(avatar_id)),
        encode_uint32(2, int(level)),
        encode_uint32(7, int(debris_count)),
        encode_uint32(8, int(coins)),
        encode_uint32(9, int(gems)),
    ])


def encode_get_unlock_profile_info_res() -> bytes:
    """Encode proto.CSGetUnlockProfileInfoRes (1: List<UnlockProfileConfig> infos)."""
    parts: List[bytes] = []
    for avatar_id in SPECIAL_AVATAR_IDS:
        for level, (debris, coins, gems) in UNLOCK_PROFILE_COSTS.items():
            parts.append(
                encode_submessage(
                    1,
                    encode_unlock_profile_config(avatar_id, level, debris, coins, gems),
                )
            )
    return b"".join(parts)


def encode_avatar_skill_slot_unlock_info(
    avatar_id: int,
    slot_id: int,
    gems: int,
    coins: int,
) -> bytes:
    """
    Encode proto.AvatarSkillSlotUnlockInfo:
      1: uint avatar_id
      2: uint slot_id
      3: uint gems
      4: uint coins
    """
    return b"".join([
        encode_uint32(1, int(avatar_id)),
        encode_uint32(2, int(slot_id)),
        encode_uint32(3, int(gems)),
        encode_uint32(4, int(coins)),
    ])


def encode_get_avatar_skill_slots_res() -> bytes:
    """Encode proto.CSGetAvatarSkillSlotsRes (1: List<AvatarSkillSlotUnlockInfo> infos)."""
    parts: List[bytes] = []
    for avatar_id in SPECIAL_AVATAR_IDS:
        for slot_id, gems, coins in SKILL_SLOT_UNLOCK_COSTS:
            parts.append(
                encode_submessage(
                    1,
                    encode_avatar_skill_slot_unlock_info(avatar_id, slot_id, gems, coins),
                )
            )
    return b"".join(parts)


def encode_unlock_skill_slot_res(
    profile: Dict[str, Any],
    coins_delta: int = 0,
    gems_delta: int = 0,
    trans_id: int = 1,
) -> bytes:
    """
    Encode proto.CSUnlockSkillSlotRes:
      1: AvatarProfile profile
      2: ExchangeChangeData change_data
    """
    change_data = encode_exchange_change_data(
        trans_id=trans_id,
        coins_delta=coins_delta,
        gems_delta=gems_delta,
        reason=TransReason.PURCHASE,
    )
    return (
        encode_submessage(1, encode_avatar_profile(profile))
        + encode_submessage(2, change_data)
    )


def encode_equip_skill_res(profile: Dict[str, Any]) -> bytes:
    """Encode proto.CSEquipSkillRes (1: AvatarProfile profile)."""
    return encode_submessage(1, encode_avatar_profile(profile))


def encode_change_clothes_res(profile: Dict[str, Any]) -> bytes:
    """Encode proto.CSChangeClothesRes (1: AvatarProfile profile)."""
    return encode_submessage(1, encode_avatar_profile(profile))


def encode_get_hide_avatar_res(hidden_avatar_ids: Sequence[int] = ()) -> bytes:
    """Encode proto.CSGetHideAvatarRes (1: uint[] avatar_id [PACKED])."""
    clean = [int(aid) for aid in hidden_avatar_ids if int(aid) > 0]
    return encode_packed_uint32(1, clean) if clean else b""
