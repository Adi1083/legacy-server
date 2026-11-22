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
    UNLOCKED_ITEM_DEFS,
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

    def notify_lobby_change(self, account_id: int) -> None:
        """Immediately sync player equipment state and push real-time TCP sync packets to client socket."""
        try:
            self._ensure_selected_defaults(account_id)
            sel = self.get_selected_items(account_id)
            loadout_ids = [lo["loadout_id"] if isinstance(lo, dict) else int(lo) for lo in sel.get("loadouts", [])]
            state.update_profile(
                account_id=account_id,
                avatar_id=sel["avatar_id"],
                skin_color=sel["skin_color"],
                clothes=sel["clothes"],
                slots=sel["slots"],
                shows=sel["shows"],
                banner_id=sel["banner_id"],
                head_pic=sel["head_pic"],
                emotes=sel["emotes"],
                loadouts=loadout_ids,
                pve_primary_weapon_skin=sel["pve_primary_weapon_skin"],
                ranking_cards=sel["ranking_cards"],
            )
            try:
                from core.player import player_manager
                p = player_manager.get_player(account_id)
                if p:
                    p.avatar_id = sel["avatar_id"]
                    p.skin_color = sel["skin_color"]
                    p.clothes = list(sel["clothes"])
                    p.slots = list(sel["slots"])
                    p.shows = list(sel["shows"])
                    p.banner_id = sel["banner_id"]
                    p.head_pic = sel["head_pic"]
                    p.emotes = list(sel["emotes"])
            except Exception:
                pass
        except Exception:
            pass

        try:
            from handlers.team_handler import broadcast_group_change
            broadcast_group_change(account_id)
        except Exception:
            pass

        try:
            from tcp_server import push_collection_sync
            push_collection_sync(account_id)
        except Exception:
            pass

    def _ensure_selected_defaults(self, account_id: int) -> None:
        prof = state.get_profile(account_id) or {}
        if account_id not in self._loadouts:
            stored_loadouts = prof.get("loadouts")
            self._loadouts[account_id] = list(stored_loadouts) if stored_loadouts else list(DEFAULT_LOADOUTS)
        if account_id not in self._slots:
            stored_slots = prof.get("slots")
            self._slots[account_id] = list(stored_slots) if stored_slots else list(DEFAULT_COLLECTION_SLOTS)
        if account_id not in self._shows:
            stored_shows = prof.get("shows")
            self._shows[account_id] = list(stored_shows) if stored_shows else list(DEFAULT_WEAPON_SHOWS)
        if account_id not in self._emotes:
            stored_emotes = prof.get("emotes")
            if stored_emotes and isinstance(stored_emotes, (list, tuple)):
                self._emotes[account_id] = {int(slot): int(eid) for slot, eid in stored_emotes}
            else:
                self._emotes[account_id] = {slot: eid for slot, eid in DEFAULT_EMOTES}
        if account_id not in self._ranking_cards:
            self._ranking_cards[account_id] = list(prof.get("ranking_cards") or [])
        if account_id not in self._pve_weapons:
            self._pve_weapons[account_id] = int(prof.get("pve_primary_weapon_skin", 907000001))
        if account_id not in self._hidden_collections:
            self._hidden_collections[account_id] = list(prof.get("hidden_collections") or [])

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
                avatar_id=aid,
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

            self.notify_lobby_change(account_id)

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
            state.update_profile(account_id=account_id, loadouts=list(self._loadouts[account_id]))
            self.notify_lobby_change(account_id)

    def choose_slots(self, slots: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        """
        Equip collection slots:
        [0: Gamebag/Backpack (ct=4 / prefix 904),
         1: Parachute (ct=5 / prefix 209),
         2: Skyboard/Surfboard (ct=6 / prefix 906),
         3: Lootbox/Deathbox (ct=3 / prefix 903),
         4: Vehicle (ct=8 / prefix 908)].
        Supports both full 5-slot arrays and selective single/partial slot replacements.
        """
        with self._lock:
            self._ensure_selected_defaults(account_id)
            current_slots = list(self._slots[account_id])
            while len(current_slots) < 5:
                current_slots.append(DEFAULT_COLLECTION_SLOTS[len(current_slots)])

            if len(slots) >= 5:
                for idx in range(min(5, len(slots))):
                    current_slots[idx] = int(slots[idx])
            elif slots:
                ct_map = {4: 0, 5: 1, 6: 2, 3: 3, 8: 4}
                for s in slots:
                    sid = int(s)
                    if not sid:
                        continue
                    meta = UNLOCKED_ITEM_DEFS.get(sid)
                    ct = meta[2] if meta else 0
                    prefix = str(sid)[:3]
                    if ct in ct_map:
                        current_slots[ct_map[ct]] = sid
                    elif prefix == "904":  # Backpack
                        current_slots[0] = sid
                    elif prefix == "209":  # Parachute
                        current_slots[1] = sid
                    elif prefix == "906":  # Skyboard
                        current_slots[2] = sid
                    elif prefix == "903":  # Lootbox
                        current_slots[3] = sid
                    elif prefix == "908":  # Vehicle
                        current_slots[4] = sid
                    elif prefix == "907":  # Weapon skin -> redirect to shows
                        self._shows[account_id] = [sid]
                        state.update_profile(account_id=account_id, shows=[sid])
                    elif prefix == "901":  # Banner -> redirect to banner
                        state.update_profile(account_id=account_id, banner_id=sid)
                    elif prefix == "902":  # Headpic -> redirect to headpic
                        state.update_profile(account_id=account_id, head_pic=sid)
                    else:
                        if sid not in current_slots:
                            current_slots.append(sid)
            self._slots[account_id] = current_slots[:5]
            state.update_profile(account_id=account_id, slots=list(self._slots[account_id]))
            self.notify_lobby_change(account_id)

    def choose_shows(self, shows: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        """Equip Armory weapon skin showcase (rendered in character's hand in lobby)."""
        with self._lock:
            self._ensure_selected_defaults(account_id)
            norm_shows = [int(x) for x in shows] if shows else list(DEFAULT_WEAPON_SHOWS)
            self._shows[account_id] = norm_shows
            state.update_profile(account_id=account_id, shows=norm_shows)
            self.notify_lobby_change(account_id)

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
                self.choose_shows(ids, account_id=account_id)
            else:
                self.choose_slots(ids, account_id=account_id)

    def choose_emote(self, slot_id: int, emote_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        """Assign or unassign an emote to an emote wheel slot (1..8)."""
        with self._lock:
            self._ensure_selected_defaults(account_id)
            sid = max(1, min(8, int(slot_id)))
            eid = int(emote_id)
            if eid == 0:
                self._emotes[account_id].pop(sid, None)
            else:
                self._emotes[account_id][sid] = eid
            emotes_list = sorted(self._emotes[account_id].items())
            state.update_profile(account_id=account_id, emotes=emotes_list)
            self.notify_lobby_change(account_id)

    def play_emote(self, emote_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        """Trigger realtime emote playback in lobby squad."""
        try:
            from handlers.team_handler import trigger_team_show_emote
            trigger_team_show_emote(account_id=account_id, emote_id=int(emote_id))
        except Exception:
            pass

    def choose_banner(self, banner_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            bid = int(banner_id)
            if bid:
                state.update_profile(account_id=account_id, banner_id=bid)
                self.notify_lobby_change(account_id)

    def choose_head_pic(self, head_pic: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            hid = int(head_pic)
            if hid:
                state.update_profile(account_id=account_id, head_pic=hid)
                self.notify_lobby_change(account_id)

    def get_hidden_collections(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[int]:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            return list(self._hidden_collections[account_id])

    def set_hidden_collections(self, item_ids: List[int], account_id: int = DEFAULT_ACCOUNT_ID) -> List[int]:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            self._hidden_collections[account_id] = [int(x) for x in item_ids]
            state.update_profile(account_id=account_id, hidden_collections=list(self._hidden_collections[account_id]))
            return list(self._hidden_collections[account_id])

    def choose_ranking_card(self, card_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            if card_id:
                self._ranking_cards[account_id] = [int(card_id)]
            else:
                self._ranking_cards[account_id] = []
            state.update_profile(account_id=account_id, ranking_cards=list(self._ranking_cards[account_id]))
            self.notify_lobby_change(account_id)

    def choose_pve_primary_weapon(self, weapon_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> None:
        with self._lock:
            self._ensure_selected_defaults(account_id)
            self._pve_weapons[account_id] = int(weapon_id)
            state.update_profile(account_id=account_id, pve_primary_weapon_skin=int(weapon_id))
            self.notify_lobby_change(account_id)

    def unlock_collection_item(self, item_id: int, count: int = 1, account_id: int = DEFAULT_ACCOUNT_ID) -> bool:
        """Unlock a collection item into player inventory state and DB."""
        with self._lock:
            iid = int(item_id)
            if iid:
                state.add_item(iid, max(1, count))
                state.unlock_items([iid])
                return True
            return False

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

    if endpoint in ("ChangeClothes", "cmd_change_clothes"):
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

    if endpoint in ("ChooseLoadout", "ChooseLoadouts"):
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

    if endpoint in ("ChooseSlots", "ChooseSlot"):
        slots = decode_choose_slots_req(raw_body)
        inventory_service.choose_slots(slots, account_id=account_id)
        handler.send_proto("Empty (ChooseSlots)", b"")
        return True

    if endpoint in ("ChooseShow", "ChooseShows"):
        shows = decode_choose_show_req(raw_body)
        inventory_service.choose_shows(shows, account_id=account_id)
        handler.send_proto("Empty (ChooseShow)", b"")
        return True

    if endpoint in ("EquipWeaponSkin", "EquipWeapon"):
        inventory_service.equip_single_or_list(raw_body, target="weapon", account_id=account_id)
        handler.send_proto("Empty (EquipWeaponSkin)", b"")
        return True

    if endpoint in ("EquipCollection", "EquipItem", "cmd_equip", "Equip"):
        inventory_service.equip_single_or_list(raw_body, target="collection", account_id=account_id)
        handler.send_proto("Empty (EquipCollection)", b"")
        return True

    if endpoint in ("UnequipItem", "Unequip", "cmd_unequip"):
        f = decode_proto(raw_body) if raw_body else {}
        item_id = get_varint(f, 1, 0)
        prefix = str(item_id)[:3]
        if prefix == "907":
            inventory_service.choose_shows(DEFAULT_WEAPON_SHOWS, account_id=account_id)
        else:
            inventory_service.notify_lobby_change(account_id)
        handler.send_proto("Empty (UnequipItem)", b"")
        return True

    if endpoint in ("ChooseEmote", "EquipEmote"):
        req = decode_choose_emote_req(raw_body)
        inventory_service.choose_emote(req["slot_id"], req["emote_id"], account_id=account_id)
        handler.send_proto("Empty (ChooseEmote)", b"")
        return True

    if endpoint in ("ChooseRankingCards", "ChooseRankingCard"):
        cid = decode_choose_ranking_cards_req(raw_body)
        inventory_service.choose_ranking_card(cid, account_id=account_id)
        handler.send_proto("Empty (ChooseRankingCards)", b"")
        return True

    if endpoint == "ChoosePVEPrimaryWeapon":
        req = decode_choose_pve_primary_weapon_req(raw_body)
        inventory_service.choose_pve_primary_weapon(req["primary_weapon_id"], account_id=account_id)
        handler.send_proto("Empty (ChoosePVEPrimaryWeapon)", b"")
        return True

    if endpoint in ("ChooseBanner", "EquipBanner"):
        bid = decode_choose_banner_req(raw_body)
        if bid:
            inventory_service.choose_banner(bid, account_id=account_id)
        handler.send_proto("Empty (ChooseBanner)", b"")
        return True

    if endpoint in ("ChooseHeadPic", "EquipHeadPic"):
        hid = decode_choose_head_pic_req(raw_body)
        if hid:
            inventory_service.choose_head_pic(hid, account_id=account_id)
        handler.send_proto("Empty (ChooseHeadPic)", b"")
        return True

    if endpoint in ("ShowEmote", "RequestShowEmote", "PlayEmote"):
        req = decode_choose_emote_req(raw_body)
        eid = req.get("emote_id") or get_varint(decode_proto(raw_body), 2, 0) or get_varint(decode_proto(raw_body), 1, 0)
        if eid:
            inventory_service.play_emote(eid, account_id=account_id)
        handler.send_proto("Empty (ShowEmote)", b"")
        return True

    if endpoint in ("UnlockCollection", "UnlockItem"):
        f = decode_proto(raw_body) if raw_body else {}
        item_id = get_varint(f, 1, 0)
        cnt = get_varint(f, 2, 1)
        if item_id:
            inventory_service.unlock_collection_item(item_id, cnt, account_id=account_id)
        handler.send_proto("Empty (UnlockCollection)", b"")
        return True

    if endpoint in ("GetSelectedItems", "GetSelectedCollection"):
        handler.send_proto("CSGetBackpackRes", inventory_service.get_backpack(account_id=account_id))
        return True

    if endpoint == "BuySticker":
        req = decode_buy_sticker_req(raw_body)
        inventory_service.buy_sticker(req["item_id"], account_id=account_id)
        handler.send_proto("Empty (BuySticker)", b"")
        return True

    return False


handle_inventory_post = handle_inventory_request
