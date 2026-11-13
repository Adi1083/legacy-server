"""
Protobuf encoders, request decoders, and verified Free Fire 1.39.4 Pet catalog.

All IDs, levels, skins, actions, and skills are extracted directly from the
decrypted 1.39 config TextAssets (Pet, PetSkin, PetAction, PetSkillInfo,
PetSkillLevel, PetLevelExp, PetFood) and all ProtoMember tags / wire types /
IsPacked attributes are verified from FF 1.39 metadata and x86 libil2cpp.so.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from proto.decoder import decode_proto, get_bool, get_string, get_varint
from proto.encoder import (
    encode_bool,
    encode_packed_uint32,
    encode_string,
    encode_submessage,
    encode_uint32,
)

# ---------------------------------------------------------------------------
# Verified Free Fire 1.39.4 Pet Config Catalog
# ---------------------------------------------------------------------------

PET_LEVEL_EXP: Dict[int, int] = {
    1: 0,
    2: 100,
    3: 200,
    4: 500,
    5: 1200,
    6: 3000,
    7: 6000,
}

PET_FOOD_EXP: Dict[int, int] = {
    1307000001: 50,
}

PET_CATALOG: Dict[int, Dict[str, Any]] = {
    1300000001: {
        "id": 1300000001,
        "name": "Kitty",
        "default_name_key": "T_12_O_CAT_NAME",
        "rare_type": 4,
        "max_level": 6,
        "max_exp": 3000,
        "default_skin_id": 1310000001,
        "skins": [1310000001, 1310000002, 1310000003, 1310000004, 1310000005],
        "actions": [1309000001, 1309000002, 1309000003, 1309000004, 1309000005, 1309000006],
        "skills": [],
    },
    1300000011: {
        "id": 1300000011,
        "name": "Mechanical Pup",
        "default_name_key": "T_14_O_DOG_NAME",
        "rare_type": 4,
        "max_level": 7,
        "max_exp": 6000,
        "default_skin_id": 1310000011,
        "skins": [1310000011, 1310000012, 1310000013, 1310000014],
        "actions": [1309000011, 1309000012, 1309000013, 1309000014, 1309000015, 1309000016],
        "skills": [],
    },
    1300000021: {
        "id": 1300000021,
        "name": "Night Panther",
        "default_name_key": "T_15_O_PANTHER_NAME",
        "rare_type": 5,
        "max_level": 7,
        "max_exp": 6000,
        "default_skin_id": 1310000021,
        "skins": [1310000021, 1310000022, 1310000023, 1310000024],
        "actions": [1309000021, 1309000022, 1309000023, 1309000024],
        "skills": [
            {"pet_id": 1300000021, "skill_id": 1315000001, "skill_level": 3},
        ],
    },
    1300000031: {
        "id": 1300000031,
        "name": "Detective Panda",
        "default_name_key": "T_16_Y_PANDA_NAME",
        "rare_type": 5,
        "max_level": 7,
        "max_exp": 6000,
        "default_skin_id": 1310000031,
        "skins": [1310000031, 1310000032, 1310000033, 1310000034],
        "actions": [1309000031, 1309000032, 1309000033, 1309000034],
        "skills": [
            {"pet_id": 1300000031, "skill_id": 1315000002, "skill_level": 3},
        ],
    },
    1300000041: {
        "id": 1300000041,
        "name": "Shiba",
        "default_name_key": "T_17_O_SHIBA_NAME",
        "rare_type": 5,
        "max_level": 7,
        "max_exp": 6000,
        "default_skin_id": 1310000041,
        "skins": [1310000041, 1310000042, 1310000043, 1310000044],
        "actions": [1309000041, 1309000042, 1309000043, 1309000044],
        "skills": [
            {"pet_id": 1300000041, "skill_id": 1315000003, "skill_level": 3},
        ],
    },
}

DEFAULT_PET_ID = 1300000001


def build_default_unlocked_pets(selected_pet_id: int = DEFAULT_PET_ID) -> List[Dict[str, Any]]:
    """Build the full list of FF 1.39 pets unlocked at max level with all skins/actions/skills."""
    pets: List[Dict[str, Any]] = []
    for pid, meta in PET_CATALOG.items():
        pets.append(
            {
                "id": pid,
                "name": meta["name"],
                "level": meta["max_level"],
                "exp": meta["max_exp"],
                "is_selected": pid == selected_pet_id,
                "skin_id": meta["default_skin_id"],
                "unlocked_skins": list(meta["skins"]),
                "actions": list(meta["actions"]),
                "skills": [dict(sk) for sk in meta["skills"]],
            }
        )
    return pets


def sync_pets_to_state(state_obj: Any, account_id: int = 10001) -> List[Dict[str, Any]]:
    """
    Ensure ServerState holds the real 1.39 Pet IDs (removing any legacy
    placeholder IDs not in PET_CATALOG) and unlocks all skins, actions,
    and max-level skills while preserving existing selection and custom names.
    """
    with state_obj._lock:
        existing_pets: Dict[int, Dict[str, Any]] = dict(state_obj._pets)
        # Drop placeholder IDs (e.g., 1300000002..1300000007) not in FF 1.39 Pet.csv
        for pid in list(state_obj._pets.keys()):
            if pid not in PET_CATALOG:
                state_obj._pets.pop(pid, None)

        prof = state_obj._profiles.get(account_id)
        prof_selected = int(prof.get("selected_pet_id", DEFAULT_PET_ID)) if prof else DEFAULT_PET_ID
        if prof_selected not in PET_CATALOG and prof_selected != 0:
            prof_selected = DEFAULT_PET_ID

        selected_id = 0
        for pid, p in state_obj._pets.items():
            if p.get("is_selected"):
                selected_id = pid
                break
        if selected_id == 0 and prof_selected in PET_CATALOG:
            selected_id = prof_selected

        for pid, meta in PET_CATALOG.items():
            prev = existing_pets.get(pid) or {}
            prev_skin = int(prev.get("skin_id", 0))
            skin_id = prev_skin if prev_skin in meta["skins"] else meta["default_skin_id"]

            prev_name = str(prev.get("name") or "").strip()
            name = prev_name if prev_name else meta["name"]

            is_sel = (pid == selected_id) if selected_id else False

            state_obj._pets[pid] = {
                "id": pid,
                "name": name,
                "level": meta["max_level"],
                "exp": meta["max_exp"],
                "is_selected": is_sel,
                "skin_id": skin_id,
                "unlocked_skins": list(meta["skins"]),
                "actions": list(meta["actions"]),
                "skills": [dict(sk) for sk in meta["skills"]],
            }

        if prof is not None:
            if selected_id in PET_CATALOG:
                prof["selected_pet_id"] = selected_id
                prof["selected_pet_skin_id"] = state_obj._pets[selected_id]["skin_id"]
            else:
                prof["selected_pet_id"] = 0
                prof["selected_pet_skin_id"] = 0

        return [dict(state_obj._pets[pid]) for pid in PET_CATALOG]


# ---------------------------------------------------------------------------
# Protobuf Submessage Encoders
# ---------------------------------------------------------------------------

def encode_pet_skill_info(pet_id: int, skill_id: int, skill_level: int = 3) -> bytes:
    """
    Encode proto.PetSkillInfo (TypeDefIndex 5060):
      1: uint32 pet_id
      2: uint32 skill_id
      3: uint32 skill_level
    """
    return b"".join(
        [
            encode_uint32(1, int(pet_id)),
            encode_uint32(2, int(skill_id)),
            encode_uint32(3, int(skill_level)),
        ]
    )


def encode_pet_skin_info(pet_id: int, skin_id: int, is_selected: bool = False) -> bytes:
    """
    Encode proto.PetSkinInfo (TypeDefIndex 5058):
      1: uint32 pet_id
      2: uint32 skin_id
      3: bool is_selected
    """
    return b"".join(
        [
            encode_uint32(1, int(pet_id)),
            encode_uint32(2, int(skin_id)),
            encode_bool(3, bool(is_selected)),
        ]
    )


def encode_pet_action_info(pet_id: int, action_id: int) -> bytes:
    """
    Encode proto.PetActionInfo (TypeDefIndex 5059):
      1: uint32 pet_id
      2: uint32 action_id
    """
    return b"".join(
        [
            encode_uint32(1, int(pet_id)),
            encode_uint32(2, int(action_id)),
        ]
    )


def _normalize_pet_skills(pet_id: int, raw_skills: Iterable[Any]) -> List[Dict[str, int]]:
    out: List[Dict[str, int]] = []
    for sk in raw_skills or ():
        if isinstance(sk, dict):
            s_id = int(sk.get("skill_id", 0))
            if s_id <= 0:
                continue
            out.append(
                {
                    "pet_id": int(sk.get("pet_id", pet_id)),
                    "skill_id": s_id,
                    "skill_level": int(sk.get("skill_level", 3)),
                }
            )
        elif isinstance(sk, int) and sk > 0:
            out.append({"pet_id": pet_id, "skill_id": sk, "skill_level": 3})
    return out


def encode_pet_info(pet: Dict[str, Any]) -> bytes:
    """
    Encode proto.PetInfo (TypeDefIndex 5057):
      1: uint32 id
      2: string name
      3: uint32 level
      4: uint32 exp
      5: bool is_selected
      6: uint32 skin_id
      7: uint32[] actions (IsPacked = true)
      8: List<proto.PetSkillInfo> skills
    """
    pet_id = int(pet.get("id", pet.get("pet_id", DEFAULT_PET_ID)))
    meta = PET_CATALOG.get(pet_id, {})
    name = str(pet.get("name") or meta.get("name") or "Kitty")
    level = int(pet.get("level", meta.get("max_level", 7)))
    exp = int(pet.get("exp", meta.get("max_exp", 6000)))
    is_selected = bool(pet.get("is_selected", False))
    skin_id = int(pet.get("skin_id", meta.get("default_skin_id", 0)))

    actions = [int(a) for a in (pet.get("actions") or meta.get("actions") or []) if int(a) > 0]
    skills = _normalize_pet_skills(pet_id, pet.get("skills") if "skills" in pet else meta.get("skills", []))

    parts = [
        encode_uint32(1, pet_id),
        encode_string(2, name),
        encode_uint32(3, level),
        encode_uint32(4, exp),
        encode_bool(5, is_selected),
        encode_uint32(6, skin_id),
    ]
    if actions:
        parts.append(encode_packed_uint32(7, actions))
    for sk in skills:
        parts.append(
            encode_submessage(
                8,
                encode_pet_skill_info(sk["pet_id"], sk["skill_id"], sk["skill_level"]),
            )
        )
    return b"".join(parts)


# ---------------------------------------------------------------------------
# Response Encoders
# ---------------------------------------------------------------------------

def _collect_skins_and_actions_and_skills(
    pets: Sequence[Dict[str, Any]],
) -> tuple[List[bytes], List[bytes], List[bytes]]:
    skin_msgs: List[bytes] = []
    action_msgs: List[bytes] = []
    skill_msgs: List[bytes] = []

    for pet in pets:
        pet_id = int(pet.get("id", pet.get("pet_id", 0)))
        if pet_id <= 0:
            continue
        meta = PET_CATALOG.get(pet_id, {})
        equipped_skin = int(pet.get("skin_id", meta.get("default_skin_id", 0)))

        raw_skins = list(pet.get("unlocked_skins") or meta.get("skins") or [])
        if equipped_skin and equipped_skin not in raw_skins:
            raw_skins.insert(0, equipped_skin)
        seen_skins = set()
        for sid in raw_skins:
            sid_int = int(sid)
            if sid_int <= 0 or sid_int in seen_skins:
                continue
            seen_skins.add(sid_int)
            skin_msgs.append(encode_pet_skin_info(pet_id, sid_int, sid_int == equipped_skin))

        raw_actions = list(pet.get("actions") or meta.get("actions") or [])
        seen_actions = set()
        for aid in raw_actions:
            aid_int = int(aid)
            if aid_int <= 0 or aid_int in seen_actions:
                continue
            seen_actions.add(aid_int)
            action_msgs.append(encode_pet_action_info(pet_id, aid_int))

        raw_skills = pet.get("skills") if "skills" in pet else meta.get("skills", [])
        for sk in _normalize_pet_skills(pet_id, raw_skills):
            skill_msgs.append(
                encode_pet_skill_info(sk["pet_id"], sk["skill_id"], sk["skill_level"])
            )

    return skin_msgs, action_msgs, skill_msgs


def encode_get_pet_list_res(pets: Optional[Sequence[Dict[str, Any]]] = None) -> bytes:
    """
    Encode proto.CSGetPetListRes (TypeDefIndex 5194):
      1: List<proto.PetInfo> pets
      2: List<proto.PetSkinInfo> skins
      3: List<proto.PetActionInfo> actions
      4: List<proto.PetSkillInfo> skills
    """
    pet_list = list(pets) if pets is not None else build_default_unlocked_pets()
    skin_msgs, action_msgs, skill_msgs = _collect_skins_and_actions_and_skills(pet_list)

    parts: List[bytes] = []
    for pet in pet_list:
        parts.append(encode_submessage(1, encode_pet_info(pet)))
    for sm in skin_msgs:
        parts.append(encode_submessage(2, sm))
    for am in action_msgs:
        parts.append(encode_submessage(3, am))
    for skm in skill_msgs:
        parts.append(encode_submessage(4, skm))
    return b"".join(parts)


def encode_get_pet_skins_res(pets: Optional[Sequence[Dict[str, Any]]] = None) -> bytes:
    """
    Encode skin list response (tag 2: List<proto.PetSkinInfo>, matching CSGetPetListRes.skins).
    """
    pet_list = list(pets) if pets is not None else build_default_unlocked_pets()
    skin_msgs, _, _ = _collect_skins_and_actions_and_skills(pet_list)
    return b"".join(encode_submessage(2, sm) for sm in skin_msgs)


def encode_get_pet_actions_res(pets: Optional[Sequence[Dict[str, Any]]] = None) -> bytes:
    """
    Encode action list response (tag 3: List<proto.PetActionInfo>, matching CSGetPetListRes.actions).
    """
    pet_list = list(pets) if pets is not None else build_default_unlocked_pets()
    _, action_msgs, _ = _collect_skins_and_actions_and_skills(pet_list)
    return b"".join(encode_submessage(3, am) for am in action_msgs)


def encode_feed_pet_res(
    old_level: int,
    new_level: int,
    old_exp: int,
    new_exp: int,
    add_exp: int = 0,
) -> bytes:
    """
    Encode proto.CSFeedPetRes (TypeDefIndex 5196):
      1: uint32 old_level
      2: uint32 new_level
      3: uint32 old_exp
      4: uint32 new_exp
      5: uint32 add_exp
    """
    return b"".join(
        [
            encode_uint32(1, int(old_level)),
            encode_uint32(2, int(new_level)),
            encode_uint32(3, int(old_exp)),
            encode_uint32(4, int(new_exp)),
            encode_uint32(5, int(add_exp)),
        ]
    )


def encode_rename_pet_res(pet_id: int, name: str) -> bytes:
    """
    Encode proto.CSRenameRes (TypeDefIndex 5199):
      1: uint32 pet_id
      2: string name
    """
    return b"".join(
        [
            encode_uint32(1, int(pet_id)),
            encode_string(2, str(name)),
        ]
    )


# ---------------------------------------------------------------------------
# Request Decoders
# ---------------------------------------------------------------------------

def decode_select_pet_req(data: bytes) -> Dict[str, Any]:
    """
    Decode proto.CSSelectPetReq (TypeDefIndex 5197):
      1: uint32 pet_id
      2: bool is_selected
    """
    fields = decode_proto(data)
    return {
        "pet_id": get_varint(fields, 1, 0),
        "is_selected": get_bool(fields, 2, False),
    }


def decode_select_pet_skin_req(data: bytes) -> Dict[str, Any]:
    """
    Decode proto.CSSelectPetSkinReq (TypeDefIndex 5200):
      1: uint32 pet_id
      2: uint32 skin_id
      3: bool is_selected
    """
    fields = decode_proto(data)
    return {
        "pet_id": get_varint(fields, 1, 0),
        "skin_id": get_varint(fields, 2, 0),
        "is_selected": get_bool(fields, 3, False),
    }


def decode_feed_pet_req(data: bytes) -> Dict[str, int]:
    """
    Decode proto.CSFeedPetReq (TypeDefIndex 5195):
      1: uint32 pet_id
      2: uint32 food_id
      3: uint32 food_num
    """
    fields = decode_proto(data)
    return {
        "pet_id": get_varint(fields, 1, 0),
        "food_id": get_varint(fields, 2, 0),
        "food_num": get_varint(fields, 3, 1),
    }


def decode_rename_pet_req(data: bytes) -> Dict[str, Any]:
    """
    Decode proto.CSRenamePetReq (TypeDefIndex 5198):
      1: uint32 pet_id
      2: string name
    """
    fields = decode_proto(data)
    return {
        "pet_id": get_varint(fields, 1, 0),
        "name": get_string(fields, 2, ""),
    }
