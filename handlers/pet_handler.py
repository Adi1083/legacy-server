"""
HTTP request handlers for Free Fire 1.39.4 Pets System.

Handles:
- /GetPetList     -> proto.CSGetPetListRes (all 5 pets unlocked at max level + all skins/actions/skills)
- /GetPetSkins    -> proto.CSGetPetListRes (skins field)
- /GetPetActions  -> proto.CSGetPetListRes (actions field)
- /SelectPet      -> updates core.state selected pet (or unselects if is_selected=False), 200 OK
- /SelectPetSkin  -> updates core.state selected pet skin (or resets to default if is_selected=False), 200 OK
- /FeedPet        -> proto.CSFeedPetRes
- /RenamePet      -> proto.CSRenameRes
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.pet_models import (
    DEFAULT_PET_ID,
    PET_CATALOG,
    PET_FOOD_EXP,
    PET_LEVEL_EXP,
    decode_feed_pet_req,
    decode_rename_pet_req,
    decode_select_pet_req,
    decode_select_pet_skin_req,
    encode_feed_pet_res,
    encode_get_pet_actions_res,
    encode_get_pet_list_res,
    encode_get_pet_skins_res,
    encode_rename_pet_res,
    sync_pets_to_state,
)

# Sync verified 1.39 pet catalog into core.state on module load so
# /GetLoginData, /GetPlayerPersonalShow, and /api/dashboard/state all see real IDs.
sync_pets_to_state(state, account_id=DEFAULT_ACCOUNT_ID)


def _ensure_pets(account_id: int) -> List[Dict[str, Any]]:
    pets = state.list_pets()
    pet_ids = {int(p.get("id", 0)) for p in pets}
    if pet_ids != set(PET_CATALOG.keys()):
        return sync_pets_to_state(state, account_id=account_id)
    return pets


def _unselect_all_pets(account_id: int) -> None:
    with state._lock:
        for p in state._pets.values():
            p["is_selected"] = False
        prof = state._profiles.get(account_id)
        if prof is not None:
            prof["selected_pet_id"] = 0
            prof["selected_pet_skin_id"] = 0


def _rename_pet(pet_id: int, new_name: str) -> str:
    clean = str(new_name or "").strip()
    with state._lock:
        pet = state._pets.get(pet_id)
        if not pet:
            return clean
        if clean:
            pet["name"] = clean
        return str(pet.get("name", ""))


def _feed_pet(pet_id: int, food_id: int, food_num: int) -> Dict[str, int]:
    meta = PET_CATALOG.get(pet_id) or {}
    max_level = int(meta.get("max_level", 7))
    max_exp = int(meta.get("max_exp", 6000))
    unit_exp = int(PET_FOOD_EXP.get(food_id, 50))
    add_exp = max(0, unit_exp * max(1, int(food_num)))

    with state._lock:
        pet = state._pets.get(pet_id)
        if not pet:
            return {
                "old_level": max_level,
                "new_level": max_level,
                "old_exp": max_exp,
                "new_exp": max_exp,
                "add_exp": 0,
            }
        old_level = int(pet.get("level", max_level))
        old_exp = int(pet.get("exp", max_exp))
        new_exp = min(max_exp, old_exp + add_exp)
        new_level = old_level
        for lv in sorted(PET_LEVEL_EXP):
            if lv <= max_level and new_exp >= PET_LEVEL_EXP[lv]:
                new_level = max(new_level, lv)
        pet["exp"] = new_exp
        pet["level"] = new_level
        return {
            "old_level": old_level,
            "new_level": new_level,
            "old_exp": old_exp,
            "new_exp": new_exp,
            "add_exp": max(0, new_exp - old_exp),
        }


def handle_pet_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Pet HTTP endpoints. Returns True if path was handled, False otherwise.
    """
    endpoint = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]

    if endpoint == "GetPetList":
        pets = _ensure_pets(account_id)
        payload = encode_get_pet_list_res(pets)
        handler.send_proto("CSGetPetListRes", payload)
        return True

    if endpoint == "GetPetSkins":
        pets = _ensure_pets(account_id)
        payload = encode_get_pet_skins_res(pets)
        handler.send_proto("CSGetPetSkinsRes", payload)
        return True

    if endpoint == "GetPetActions":
        pets = _ensure_pets(account_id)
        payload = encode_get_pet_actions_res(pets)
        handler.send_proto("CSGetPetActionsRes", payload)
        return True

    if endpoint == "SelectPet":
        _ensure_pets(account_id)
        req = decode_select_pet_req(raw_body)
        pet_id = int(req["pet_id"]) or DEFAULT_PET_ID
        if req["is_selected"]:
            state.select_pet(pet_id, account_id=account_id)
        else:
            _unselect_all_pets(account_id)
        handler.send_proto("CSSelectPetRes", b"")
        return True

    if endpoint == "SelectPetSkin":
        _ensure_pets(account_id)
        req = decode_select_pet_skin_req(raw_body)
        pet_id = int(req["pet_id"]) or DEFAULT_PET_ID
        skin_id = int(req["skin_id"])
        if req["is_selected"] and skin_id > 0:
            state.select_pet_skin(pet_id, skin_id, account_id=account_id)
        elif not req["is_selected"]:
            default_skin = int((PET_CATALOG.get(pet_id) or {}).get("default_skin_id", 0))
            if default_skin > 0:
                state.select_pet_skin(pet_id, default_skin, account_id=account_id)
        handler.send_proto("CSSelectPetSkinRes", b"")
        return True

    if endpoint == "FeedPet":
        _ensure_pets(account_id)
        req = decode_feed_pet_req(raw_body)
        pet_id = int(req["pet_id"]) or DEFAULT_PET_ID
        res = _feed_pet(pet_id, req["food_id"], req["food_num"])
        payload = encode_feed_pet_res(
            old_level=res["old_level"],
            new_level=res["new_level"],
            old_exp=res["old_exp"],
            new_exp=res["new_exp"],
            add_exp=res["add_exp"],
        )
        handler.send_proto("CSFeedPetRes", payload)
        return True

    if endpoint == "RenamePet":
        _ensure_pets(account_id)
        req = decode_rename_pet_req(raw_body)
        pet_id = int(req["pet_id"]) or DEFAULT_PET_ID
        final_name = _rename_pet(pet_id, req["name"])
        payload = encode_rename_pet_res(pet_id, final_name)
        handler.send_proto("CSRenameRes", payload)
        return True

    return False


# Alias for router consistency
handle_pet_post = handle_pet_request
