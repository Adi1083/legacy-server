"""
HTTP request handlers for Free Fire 1.39 Vault, Backpack, Clothes,
Loadouts, Collections, Armory Weapon Showcase, Emotes, and Stickers.

Primary endpoints (ServiceMessageTypeHTTP + aliases):
- /GetBackpack              -> proto.CSGetBackpackRes (4,462+ real unlocked items)
- /ChangeClothes            -> proto.CSChangeClothesRes (AvatarProfile)
- /ChooseLoadout            -> Empty
- /GetCollectionHide        -> proto.CSGetHideCollectionsRes
- /SetCollectionHide        -> proto.CSGetHideCollectionsRes (alias)
- /ChooseSlots              -> Empty (Backpack / Parachute / Skyboard / LootBox / Vehicle)
- /ChooseShow               -> Empty (Weapon Skin showcase)
- /EquipWeaponSkin          -> Empty (alias for /ChooseShow)
- /EquipCollection          -> Empty (alias for /ChooseSlots)
- /ChooseEmote              -> Empty
- /ChooseRankingCards       -> Empty
- /ChoosePVEPrimaryWeapon   -> Empty
- /ChooseBanner             -> Empty
- /ChooseHeadPic            -> Empty
- /BuySticker               -> Empty

Integrates directly with core.state.state and unlocks all real APK permanent
items on startup.
"""

from __future__ import annotations

import copy
import threading
from typing import Any, Dict, List

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.decoder import decode_proto, get_packed_varints, get_varint
from proto.inventory_models import (
    DEFAULT_AVATAR_ID,
    DEFAULT_CLOTHES,
    DEFAULT_COLLECTION_SLOTS,
    DEFAULT_EMOTES,
    DEFAULT_LOADOUTS,
    DEFAULT_WEAPON_SHOWS,
    decode_buy_sticker_req,
    decode_change_clothes_req,
    decode_choose_banner_req,
    decode_choose_emote_req,
    decode_choose_head_pic_req,
    decode_choose_loadout_req,
    decode_choose_pve_primary_weapon_req,
    decode_choose_ranking_cards_req,
    decode_choose_show_req,
    decode_choose_slots_req,
    decode_hide_collections_req,
    encode_avatar_profile,
    encode_change_clothes_res,
    encode_get_backpack_res,
    encode_get_hide_collections_res,
    unlock_all_inventory_in_state,
)


def _normalize_avatar_id(avatar_id: int) -> int:
    """Ensure avatar_id is a valid 1.39 CSV ID (101xxxxxx/102xxxxxx)."""
    aid = int(avatar_id or 0)
    if aid >= 101000000:
        return aid
    return DEFAULT_AVATAR_ID


class InventoryService:
    """Thread-safe Vault / Backpack / Loadout / Collection / Clothes service."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._loadouts: Dict[int, List[int]] = {}
        self._slots: Dict[int, List[int]] = {}
        self._shows: Dict[int, List[int]] = {}
        self._emotes: Dict[int, Dict[int, int]] = {}
        self._ranking_cards: Dict[int, List[int]] = {}
        self._pve_weapons: Dict[int, int] = {}
        self._hidden_collections: Dict[int, List[int]] = {}

        # Unlock all 4,462 real permanent APK items in core.state.state on startup
        unlock_all_inventory_in_state(state)

    def _ensure_selected_defaults(self, account_id: int) -> None:
        if account_id not in self._loadouts:
            self._loadouts[account_id] = list(DEFAULT_LOADOUTS)
        if account_id not in self._slots:
            self._slots[account_id] = list(DEFAULT_COLLECTION_SLOTS)
        if account_id not in self._shows:
            self._shows[account_id] = list(DEFAULT_WEAPON_SHOWS)
        if account_id not in self._emotes:
            self._emotes[account_id] = {slot: eid for slot, eid in DEFAULT_EMOTES}
        if account_id not in self._ranking_cards:
            self._ranking_cards[account_id] = []
        if account_id not in self._pve_weapons:
            self._pve_weapons[account_id] = 907000001
        if account_id not in self._hidden_collections:
            self._hidden_collections[account_id] = []

    def get_selected_items(self, account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            prof = state.get_profile(account_id) or {}
            avatar_id = _normalize_avatar_id(int(prof.get("avatar_id", DEFAULT_AVATAR_ID)))
            clothes = list(prof.get("clothes") or []) or list(DEFAULT_CLOTHES)
            skin_color = int(prof.get("skin_color", 0))
            banner_id = int(prof.get("banner_id", 901000001))
            head_pic = int(prof.get("head_pic", 902000001))

            emotes_list = sorted(self._emotes[account_id].items())
            return {
                "avatar_id": avatar_id,
                "skin_color": skin_color,
                "clothes": clothes,
                "loadouts": [
                    {"loadout_id": lid, "loadout_num": 99, "is_free_play": True}
                    for lid in self._loadouts[account_id]
                ],
                "banner_id": banner_id,
                "head_pic": head_pic,
                "slots": list(self._slots[account_id]),
                "emotes": emotes_list,
                "shows": list(self._shows[account_id]),
                "pve_primary_weapon_skin": self._pve_weapons[account_id],
                "ranking_cards": list(self._ranking_cards[account_id]),
            }

    def get_backpack(self, account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        with self._lock:
            # Ensure infinite coins/gems and full unlocked catalog
            wallet = state.get_wallet(account_id)
            if wallet["coins"] < 999999 or wallet["gems"] < 999999:
                wallet = state.set_wallet(
                    coins=max(999999, wallet["coins"]),
                    gems=max(999999, wallet["gems"]),
                    account_id=account_id,
                )
            selected = self.get_selected_items(account_id)
            item_counts = state.get_all_item_counts()
            return encode_get_backpack_res(wallet, selected, item_counts)

    def change_clothes(
        self,
        avatar_id: int,
        clothes: List[int],
        skin_color: int,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> bytes:
        with self._lock:
            prof = state.get_profile(account_id) or {}
            aid = _normalize_avatar_id(avatar_id or int(prof.get("avatar_id", DEFAULT_AVATAR_ID)))
            norm_clothes = [int(c) for c in clothes] if clothes else list(DEFAULT_CLOTHES)
            state.update_profile(
                account_id=account_id,
                clothes=norm_clothes,
                skin_color=int(skin_color),
            )
            char = state.get_character(aid)
            if char:
                with state._lock:
                    cobj = state._characters.get(aid)
                    if cobj:
                        cobj["clothes"] = list(norm_clothes)
                        cobj["skin_color"] = int(skin_color)
                skills = char.get("equiped_skills", [])
                level = int(char.get("unlocked_level", 8))
                pve_w = int(char.get("pve_primary_weapon", 0))
            else:
                skills = []
                level = 8
                pve_w = 0

            profile_bytes = encode_avatar_profile(
                avatar_id=aid,
                unlocked_level=level,
                skin_color=int(skin_color),
                clothes=norm_clothes,
                equiped_skills=skills,
                is_selected=True,
                pve_primary_weapon=pve_w,
            )
            return encode_change_clothes_res(profile_bytes)

    def choose_loadouts(self, loadouts: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            self._loadouts[account_id] = [int(x) for x in loadouts]

    def choose_slots(self, slots: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            self._slots[account_id] = [int(x) for x in slots]

    def choose_shows(self, shows: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            self._shows[account_id] = [int(x) for x in shows]

    def equip_single_or_list(
        self,
        raw_body: bytes,
        target: str,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> None:
        """Handle /EquipWeaponSkin and /EquipCollection aliases cleanly."""
        with self._lock:
            self._ensure_selected_defaults(account_id)
            fields = decode_proto(raw_body) if raw_body else {}
            vals = fields.get(1) or []
            if not vals:
                return
            if isinstance(vals[0], int):
                ids = [int(vals[0])]
            else:
                ids = get_packed_varints(fields, 1)
            if not ids:
                return
            if target == "weapon":
                existing = [x for x in self._shows[account_id] if x not in ids]
                self._shows[account_id] = ids + existing if len(ids) == 1 else ids
            else:
                existing = [x for x in self._slots[account_id] if x not in ids]
                self._slots[account_id] = ids + existing if len(ids) == 1 else ids

    def choose_emote(self, slot_id: int, emote_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            sid = max(1, int(slot_id))
            eid = int(emote_id)
            if eid == 0:
                self._emotes[account_id].pop(sid, None)
            else:
                self._emotes[account_id][sid] = eid

    def get_hidden_collections(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[int]:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            return list(self._hidden_collections[account_id])

    def set_hidden_collections(self, item_ids: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> List[int]:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            self._hidden_collections[account_id] = [int(x) for x in item_ids]
            return list(self._hidden_collections[account_id])

    def choose_ranking_card(self, card_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            if card_id:
                self._ranking_cards[account_id] = [int(card_id)]
            else:
                self._ranking_cards[account_id] = []

    def choose_pve_primary_weapon(self, weapon_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            self._pve_weapons[account_id] = int(weapon_id)

    def buy_sticker(self, item_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            if item_id:
                state.add_item(int(item_id), 1)
            wallet = state.get_wallet(account_id)
            if wallet["coins"] < 999999 or wallet["gems"] < 999999:
                state.set_wallet(coins=999999, gems=999999, account_id=account_id)


inventory_service = InventoryService()


# ------------------------------------------------------------------
# HTTP Request Dispatcher
# ------------------------------------------------------------------
def _normalize_endpoint(path: str) -> str:
    clean = path.split("?", 1)[0].strip()
    return clean.rsplit("/", 1)[-1]


def handle_inventory_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Free Fire 1.39 Vault / Backpack / Clothes / Collection HTTP endpoints.
    Returns True if handled, False otherwise.
    """
    endpoint = _normalize_endpoint(path)

    if endpoint == "GetBackpack":
        handler.send_proto(
            "CSGetBackpackRes",
            inventory_service.get_backpack(account_id=account_id),
        )
        return True

    if endpoint == "ChangeClothes":
        req = decode_change_clothes_req(raw_body)
        handler.send_proto(
            "CSChangeClothesRes",
            inventory_service.change_clothes(
                avatar_id=req["avatar_id"],
                clothes=req["clothes"],
                skin_color=req["skin_color"],
                account_id=account_id,
            ),
        )
        return True

    if endpoint == "ChooseLoadout":
        req = decode_choose_loadout_req(raw_body)
        inventory_service.choose_loadouts(req["loadouts"], account_id=account_id)
        handler.send_proto("Empty (ChooseLoadout)", b"")
        return True

    if endpoint == "GetCollectionHide":
        hidden = inventory_service.get_hidden_collections(account_id=account_id)
        handler.send_proto(
            "CSGetHideCollectionsRes",
            encode_get_hide_collections_res(hidden),
        )
        return True

    if endpoint == "SetCollectionHide":
        ids = decode_hide_collections_req(raw_body)
        hidden = inventory_service.set_hidden_collections(ids, account_id=account_id)
        handler.send_proto(
            "CSGetHideCollectionsRes",
            encode_get_hide_collections_res(hidden),
        )
        return True

    if endpoint == "ChooseSlots":
        slots = decode_choose_slots_req(raw_body)
        inventory_service.choose_slots(slots, account_id=account_id)
        handler.send_proto("Empty (ChooseSlots)", b"")
        return True

    if endpoint == "ChooseShow":
        shows = decode_choose_show_req(raw_body)
        inventory_service.choose_shows(shows, account_id=account_id)
        handler.send_proto("Empty (ChooseShow)", b"")
        return True

    if endpoint == "EquipWeaponSkin":
        inventory_service.equip_single_or_list(raw_body, target="weapon", account_id=account_id)
        handler.send_proto("Empty (EquipWeaponSkin)", b"")
        return True

    if endpoint == "EquipCollection":
        inventory_service.equip_single_or_list(raw_body, target="collection", account_id=account_id)
        handler.send_proto("Empty (EquipCollection)", b"")
        return True

    if endpoint == "ChooseEmote":
        req = decode_choose_emote_req(raw_body)
        inventory_service.choose_emote(req["slot_id"], req["emote_id"], account_id=account_id)
        handler.send_proto("Empty (ChooseEmote)", b"")
        return True

    if endpoint == "ChooseRankingCards":
        cid = decode_choose_ranking_cards_req(raw_body)
        inventory_service.choose_ranking_card(cid, account_id=account_id)
        handler.send_proto("Empty (ChooseRankingCards)", b"")
        return True

    if endpoint == "ChoosePVEPrimaryWeapon":
        req = decode_choose_pve_primary_weapon_req(raw_body)
        inventory_service.choose_pve_primary_weapon(req["primary_weapon_id"], account_id=account_id)
        handler.send_proto("Empty (ChoosePVEPrimaryWeapon)", b"")
        return True

    if endpoint == "ChooseBanner":
        bid = decode_choose_banner_req(raw_body)
        if bid:
            state.update_profile(account_id=account_id, banner_id=bid)
        handler.send_proto("Empty (ChooseBanner)", b"")
        return True

    if endpoint == "ChooseHeadPic":
        hid = decode_choose_head_pic_req(raw_body)
        if hid:
            state.update_profile(account_id=account_id, head_pic=hid)
        handler.send_proto("Empty (ChooseHeadPic)", b"")
        return True

    if endpoint == "BuySticker":
        req = decode_buy_sticker_req(raw_body)
        inventory_service.buy_sticker(req["item_id"], account_id=account_id)
        handler.send_proto("Empty (BuySticker)", b"")
        return True

    return False


handle_inventory_post = handle_inventory_request
