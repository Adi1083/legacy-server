"""
HTTP POST handlers for Free Fire 1.39 Characters (Avatars), Character Skills,
Skill Slots, and Character Clothes endpoints.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.character_models import (
    ALL_MAX_SKILL_IDS,
    AVATAR_CATALOG,
    DEFAULT_AVATAR_ID,
    LEVEL_CARD_TARGETS,
    LEVEL_ITEM_REWARDS,
    SKILL_SLOT_UNLOCK_COSTS,
    build_default_character,
    decode_change_clothes_req,
    decode_equip_skill_req,
    decode_select_profile_req,
    decode_unlock_profile_req,
    decode_unlock_skill_slot_req,
    decode_upgrade_profile_req,
    encode_change_clothes_res,
    encode_equip_skill_res,
    encode_get_avatar_skill_slots_res,
    encode_get_hide_avatar_res,
    encode_get_profile_list_res,
    encode_get_skill_list_res,
    encode_get_unlock_profile_info_res,
    encode_login_profile_res,
    encode_select_profile_res,
    encode_unlock_profile_res,
    encode_unlock_skill_slot_res,
    encode_upgrade_profile_res,
    sync_characters_to_state,
)


# Ensure all 21 real 1.39 characters and skills replace legacy placeholder IDs.
sync_characters_to_state(state)


def _extract_endpoint(path: str) -> str:
    clean = path.split("?", 1)[0].rstrip("/")
    return clean.rsplit("/", 1)[-1] if "/" in clean else clean


def _ensure_character(avatar_id: int) -> Dict[str, Any]:
    """Return existing character from state, or materialize & register a real 1.39 default."""
    aid = int(avatar_id)
    if aid <= 0:
        aid = _get_selected_avatar_id()
    char = state.get_character(aid)
    if char is not None:
        return char

    if aid in AVATAR_CATALOG:
        default_char = build_default_character(aid, is_selected=False)
        state.unlock_character(
            avatar_id=aid,
            name=default_char["name"],
            level=default_char["unlocked_level"],
            skill_id=default_char["skill_id"],
            clothes=default_char["clothes"],
        )
        if default_char["equiped_skills"]:
            state.equip_character_skills(aid, default_char["equiped_skills"])
        return state.get_character(aid) or default_char

    return state.get_character(DEFAULT_AVATAR_ID) or build_default_character(
        DEFAULT_AVATAR_ID, is_selected=True
    )


def _get_selected_avatar_id(account_id: int = DEFAULT_ACCOUNT_ID) -> int:
    for char in state.list_characters():
        if char.get("is_selected"):
            return int(char["avatar_id"])
    prof_aid = int(state.get_profile(account_id).get("avatar_id", 0))
    return prof_aid if prof_aid in AVATAR_CATALOG else DEFAULT_AVATAR_ID


def _sync_selected_profile(char: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> None:
    """Propagate active character visuals/skills into the account profile and push TCP sync."""
    if not char.get("is_selected"):
        return
    aid = int(char["avatar_id"])
    skin_color = int(char.get("skin_color", 0))
    clothes = list(char.get("clothes") or [])
    state.update_profile(
        account_id,
        avatar_id=aid,
        skin_color=skin_color,
        clothes=clothes,
        equiped_skills=list(char.get("equiped_skills") or []),
        unlocked_level=int(char.get("unlocked_level", 8)),
        pve_primary_weapon=int(char.get("pve_primary_weapon", 0)),
    )
    try:
        from core.player import player_manager
        p = player_manager.get_player(account_id)
        if p:
            p.avatar_id = aid
            p.skin_color = skin_color
            p.clothes = list(clothes)
    except Exception:
        pass

    try:
        from handlers.inventory_handler import inventory_service
        inventory_service.notify_lobby_change(account_id)
    except Exception:
        pass


def _resolve_selected_pet(account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
    prof = state.get_profile(account_id)
    pet_id = int(prof.get("selected_pet_id", 0))
    if pet_id > 0:
        pet = state.get_pet(pet_id)
        if pet:
            return pet
    for pet in state.list_pets():
        if pet.get("is_selected"):
            return pet
    pets = state.list_pets()
    return pets[0] if pets else None


def _apply_level_progression(
    avatar_id: int,
    target_level: int,
) -> tuple[Dict[str, Any], List[int]]:
    """Unlock/upgrade character up to target_level (clamped to 1..8) and grant rewards."""
    char = _ensure_character(avatar_id)
    aid = int(char["avatar_id"])
    cur_lvl = int(char.get("unlocked_level", 1))
    final_lvl = max(cur_lvl, min(8, max(1, int(target_level))))

    meta = AVATAR_CATALOG.get(aid, {})
    skills = list(meta.get("skills") or [])
    max_skill = int(skills[-1]) if skills else int(char.get("skill_id", 0))

    for sk in skills:
        state.unlock_skill(int(sk))

    state.unlock_character(
        avatar_id=aid,
        name=str(char.get("name", meta.get("name", ""))),
        level=final_lvl,
        skill_id=max_skill,
        clothes=list(char.get("clothes") or meta.get("default_clothes") or []),
    )

    slots = list(char.get("equiped_skills") or [])
    if skills:
        slot_map = {int(s["slot_id"]): int(s["skill_id"]) for s in slots if isinstance(s, dict)}
        slot_map[0] = max_skill
        slot_map.setdefault(1, 0)
        slot_map.setdefault(2, 0)
        new_slots = [{"slot_id": sid, "skill_id": slot_map[sid]} for sid in sorted(slot_map)]
        state.equip_character_skills(aid, new_slots)

    award_items: List[int] = []
    for lvl in range(1, final_lvl + 1):
        item_id = LEVEL_ITEM_REWARDS.get((aid, lvl))
        if item_id:
            state.unlock_item(item_id, 1)
            award_items.append(item_id)

    updated = _ensure_character(aid)
    _sync_selected_profile(updated)
    return updated, award_items


# ---------------------------------------------------------------------------
# Individual Endpoint Handlers
# ---------------------------------------------------------------------------

def _handle_login_get_profile(
    handler: Any, _raw_body: bytes, account_id: int
) -> None:
    characters = state.list_characters()
    skills = sorted(state.list_unlocked_skills() or ALL_MAX_SKILL_IDS)
    selected_pet = _resolve_selected_pet(account_id)
    handler.send_proto(
        "LoginProfileRes",
        encode_login_profile_res(
            account_id=account_id,
            profiles=characters,
            skills=skills,
            selected_pet=selected_pet,
        ),
    )


def _handle_get_profiles(
    handler: Any, _raw_body: bytes, _account_id: int
) -> None:
    handler.send_proto(
        "CSGetProfileListRes",
        encode_get_profile_list_res(state.list_characters()),
    )


def _handle_get_skills(
    handler: Any, _raw_body: bytes, account_id: int
) -> None:
    skills = sorted(state.list_unlocked_skills() or ALL_MAX_SKILL_IDS)
    handler.send_proto(
        "CSGetSkillListRes",
        encode_get_skill_list_res(account_id=account_id, skills=skills),
    )


def _handle_select_profile(
    handler: Any, raw_body: bytes, account_id: int
) -> None:
    avatar_id = decode_select_profile_req(raw_body)
    if avatar_id <= 0:
        avatar_id = _get_selected_avatar_id(account_id)

    char = _ensure_character(avatar_id)
    selected = state.select_character(int(char["avatar_id"]), account_id=account_id) or char
    _sync_selected_profile(selected, account_id=account_id)

    handler.send_proto(
        "CSSelectProfileRes",
        encode_select_profile_res(selected),
    )


def _handle_unlock_profile(
    handler: Any, raw_body: bytes, _account_id: int
) -> None:
    avatar_id, unlock_level, _currency_type = decode_unlock_profile_req(raw_body)
    if avatar_id <= 0:
        avatar_id = _get_selected_avatar_id()
    updated, award_items = _apply_level_progression(avatar_id, max(8, unlock_level or 1))
    handler.send_proto(
        "CSUnlockProfileRes",
        encode_unlock_profile_res([updated], award_items=award_items),
    )


def _handle_upgrade_profile(
    handler: Any, raw_body: bytes, _account_id: int
) -> None:
    avatar_id, level_card_id = decode_upgrade_profile_req(raw_body)
    if avatar_id <= 0:
        avatar_id = _get_selected_avatar_id()
    cur = _ensure_character(avatar_id)
    target_level = LEVEL_CARD_TARGETS.get(level_card_id, max(8, int(cur.get("unlocked_level", 1)) + 1))
    updated, award_items = _apply_level_progression(avatar_id, target_level)
    handler.send_proto(
        "CSUpgradeProfileRes",
        encode_upgrade_profile_res([updated], award_items=award_items),
    )


def _handle_get_unlock_profile_info(
    handler: Any, _raw_body: bytes, _account_id: int
) -> None:
    handler.send_proto(
        "CSGetUnlockProfileInfoRes",
        encode_get_unlock_profile_info_res(),
    )


def _handle_get_avatar_skill_slots(
    handler: Any, _raw_body: bytes, _account_id: int
) -> None:
    handler.send_proto(
        "CSGetAvatarSkillSlotsRes",
        encode_get_avatar_skill_slots_res(),
    )


def _handle_unlock_skill_slot(
    handler: Any, raw_body: bytes, account_id: int
) -> None:
    avatar_id, slot_id, currency_type = decode_unlock_skill_slot_req(raw_body)
    char = _ensure_character(avatar_id)
    aid = int(char["avatar_id"])

    slots = list(char.get("equiped_skills") or [])
    slot_map = {int(s["slot_id"]): int(s["skill_id"]) for s in slots if isinstance(s, dict)}
    already_open = int(slot_id) in slot_map
    slot_map.setdefault(int(slot_id), 0)
    new_slots = [{"slot_id": sid, "skill_id": slot_map[sid]} for sid in sorted(slot_map)]
    updated = state.equip_character_skills(aid, new_slots) or char
    _sync_selected_profile(updated, account_id=account_id)

    coins_delta = 0
    gems_delta = 0
    if not already_open:
        for cfg_slot_id, gems_cost, coins_cost in SKILL_SLOT_UNLOCK_COSTS:
            if cfg_slot_id == int(slot_id):
                if currency_type == 2:
                    ok, _ = state.spend_currency(gems=gems_cost, account_id=account_id)
                    if ok:
                        gems_delta = -gems_cost
                else:
                    ok, _ = state.spend_currency(coins=coins_cost, account_id=account_id)
                    if ok:
                        coins_delta = -coins_cost
                break

    handler.send_proto(
        "CSUnlockSkillSlotRes",
        encode_unlock_skill_slot_res(
            updated,
            coins_delta=coins_delta,
            gems_delta=gems_delta,
            trans_id=int(time.time() * 1000) & 0x7FFFFFFF,
        ),
    )


def _handle_equip_skill(
    handler: Any, raw_body: bytes, account_id: int
) -> None:
    avatar_id, slot_id, skill_id = decode_equip_skill_req(raw_body)
    char = _ensure_character(avatar_id)
    aid = int(char["avatar_id"])

    slots = list(char.get("equiped_skills") or [])
    slot_map = {int(s["slot_id"]): int(s["skill_id"]) for s in slots if isinstance(s, dict)}
    slot_map[int(slot_id)] = int(skill_id)
    new_slots = [{"slot_id": sid, "skill_id": slot_map[sid]} for sid in sorted(slot_map)]

    if skill_id > 0:
        state.unlock_skill(int(skill_id))
    updated = state.equip_character_skills(aid, new_slots) or char
    _sync_selected_profile(updated, account_id=account_id)

    handler.send_proto(
        "CSEquipSkillRes",
        encode_equip_skill_res(updated),
    )


def _handle_change_clothes(
    handler: Any, raw_body: bytes, account_id: int
) -> None:
    avatar_id, clothes, skin_color = decode_change_clothes_req(raw_body)
    char = _ensure_character(avatar_id)
    aid = int(char["avatar_id"])

    if clothes:
        char = state.equip_character_clothes(aid, clothes) or char
    if skin_color is not None:
        with state._lock:
            target = state._characters.get(aid)
            if target is not None:
                target["skin_color"] = int(skin_color)
        char = state.get_character(aid) or char

    _sync_selected_profile(char, account_id=account_id)
    try:
        from handlers.inventory_handler import inventory_service
        inventory_service.notify_lobby_change(account_id)
    except Exception:
        pass
    handler.send_proto(
        "CSChangeClothesRes",
        encode_change_clothes_res(char),
    )


def _handle_get_hide_avatar(
    handler: Any, _raw_body: bytes, _account_id: int
) -> None:
    handler.send_proto("CSGetHideAvatarRes", encode_get_hide_avatar_res(()))


_ROUTES: Dict[str, Callable[[Any, bytes, int], None]] = {
    "LoginGetProfile": _handle_login_get_profile,
    "GetProfiles": _handle_get_profiles,
    "GetSkills": _handle_get_skills,
    "SelectProfile": _handle_select_profile,
    "ChooseAvatar": _handle_select_profile,
    "UnlockProfile": _handle_unlock_profile,
    "UnlockAvatar": _handle_unlock_profile,
    "UpgradeProfile": _handle_upgrade_profile,
    "GetUnlockProfileInfo": _handle_get_unlock_profile_info,
    "GetAvatarSkillSlots": _handle_get_avatar_skill_slots,
    "UnlockSkillSlot": _handle_unlock_skill_slot,
    "EquipSkill": _handle_equip_skill,
    "ChangeClothes": _handle_change_clothes,
    "GetHideAvatar": _handle_get_hide_avatar,
    "HideAvatar": _handle_get_hide_avatar,
}


def handle_character_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """Dispatch Free Fire 1.39 Character, Skill, and Clothes HTTP endpoints."""
    del client_ip
    endpoint = _extract_endpoint(path)
    fn = _ROUTES.get(endpoint)
    if fn is None:
        return False
    fn(handler, raw_body, int(account_id))
    return True


handle_character_post = handle_character_request
