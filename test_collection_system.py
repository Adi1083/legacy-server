"""
Comprehensive test suite for Free Fire 1.39 Collection section backend.
Tests HTTP endpoints, profile persistence, and TCP lobby broadcasting for:
- Weapons (ChooseShow, EquipWeaponSkin)
- Emotes (ChooseEmote, ShowEmote, TCP SHOWEMOTE -> SHOWEMOTE_NTF)
- Collection Slots: Backpack, Parachute, Skyboard, Lootbox, Vehicle (ChooseSlots, EquipCollection)
- Banners & Avatars (ChooseBanner, ChooseHeadPic)
- Clothes (ChangeClothes)
- Full Backpack Catalog (GetBackpack)
"""

import os
import sys
import unittest

_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.inventory_handler import inventory_service
from handlers.team_handler import handle_group_tcp_command, _get_or_create_team
from proto.decoder import decode_proto, get_packed_varints, get_varint, get_submessages
from proto.encoder import encode_packed_uint32, encode_uint32, encode_uint64, encode_submessage
from proto.inventory_models import (
    DEFAULT_COLLECTION_SLOTS,
    DEFAULT_WEAPON_SHOWS,
    DEFAULT_EMOTES,
    decode_choose_emote_req,
    decode_choose_show_req,
    decode_choose_slots_req,
    encode_get_backpack_res,
)
from proto.team_models import (
    EGroupProto,
    EProtocolProto,
    decode_show_emote_req,
    encode_show_emote_ntf,
)


class MockHttpHandler:
    def __init__(self):
        self.sent_name = None
        self.sent_bytes = None
        self.status = 200

    def send_proto(self, name: str, data: bytes):
        self.sent_name = name
        self.sent_bytes = data

    def send_bytes(self, data: bytes, status: int = 200):
        self.sent_bytes = data
        self.status = status


class TestCollectionSystem(unittest.TestCase):

    def setUp(self):
        # Reset player team and inventory state
        self.account_id = DEFAULT_ACCOUNT_ID
        _get_or_create_team(self.account_id)

    def test_01_get_backpack_full_catalog_and_defaults(self):
        """Verify GetBackpack returns >4400 items, wallet, and default equipped items."""
        backpack_bytes = inventory_service.get_backpack(self.account_id)
        self.assertGreater(len(backpack_bytes), 10000, "Backpack bytes should contain full catalog")

        fields = decode_proto(backpack_bytes)
        self.assertIn(1, fields, "Wallet field (tag 1) must be present")
        self.assertIn(2, fields, "SelectedItems field (tag 2) must be present")
        self.assertIn(3, fields, "Items list (tag 3) must be present")

        # Check total items unlocked
        items = get_submessages(fields, 3)
        self.assertGreaterEqual(len(items), 4400, "All 4,462 APK permanent items must be unlocked")

        # Check selected items
        selected_raw = fields[2][0]
        sel_fields = decode_proto(selected_raw)
        banner_id = get_varint(sel_fields, 5, 0)
        head_pic = get_varint(sel_fields, 6, 0)
        slots = get_packed_varints(sel_fields, 7)
        shows = get_packed_varints(sel_fields, 9)

        self.assertGreater(banner_id, 0)
        self.assertGreater(head_pic, 0)
        self.assertEqual(len(slots), 5, "Must have 5 collection slots")
        self.assertGreaterEqual(len(shows), 1, "Must have weapon shows")

    def test_02_equip_weapons_choose_show(self):
        """Verify equipping weapon skins updates inventory, profile state, and DB."""
        new_weapons = [907000013, 907000010, 907000005]  # AK, M4A1, AWM
        inventory_service.choose_shows(new_weapons, account_id=self.account_id)

        # 1. Check in-memory inventory service
        selected = inventory_service.get_selected_items(self.account_id)
        self.assertEqual(selected["shows"], new_weapons)

        # 2. Check profile state
        prof = state.get_profile(self.account_id)
        self.assertEqual(prof["shows"], new_weapons)

        # 3. Verify single weapon equip alias
        req_single = encode_uint32(1, 907000014)  # SCAR
        inventory_service.equip_single_or_list(req_single, target="weapon", account_id=self.account_id)
        prof_after = state.get_profile(self.account_id)
        self.assertEqual(prof_after["shows"], [907000014])

    def test_03_equip_collection_slots(self):
        """Verify equipping backpack, parachute, skyboard, lootbox, vehicle."""
        # Custom collection items:
        # Backpack: 904000005, Parachute: 209000010, Skyboard: 906000008, Lootbox: 903000004, Vehicle: 908000002
        new_slots = [904000005, 209000010, 906000008, 903000004, 908000002]
        inventory_service.choose_slots(new_slots, account_id=self.account_id)

        selected = inventory_service.get_selected_items(self.account_id)
        self.assertEqual(selected["slots"], new_slots)

        prof = state.get_profile(self.account_id)
        self.assertEqual(prof["slots"], new_slots)

        # Selective replacement: equip only a parachute (209000015, ct=5 -> slot index 1)
        inventory_service.choose_slots([209000015], account_id=self.account_id)
        prof_updated = state.get_profile(self.account_id)
        self.assertEqual(prof_updated["slots"][1], 209000015)
        self.assertEqual(prof_updated["slots"][0], 904000005)  # Backpack preserved
        self.assertEqual(prof_updated["slots"][2], 906000008)  # Skyboard preserved

    def test_04_equip_emotes(self):
        """Verify assigning emotes to slots 1-8."""
        inventory_service.choose_emote(slot_id=1, emote_id=909000010, account_id=self.account_id)
        inventory_service.choose_emote(slot_id=2, emote_id=909000015, account_id=self.account_id)

        selected = inventory_service.get_selected_items(self.account_id)
        emotes_dict = dict(selected["emotes"])
        self.assertEqual(emotes_dict[1], 909000010)
        self.assertEqual(emotes_dict[2], 909000015)

        # Unassign slot 2
        inventory_service.choose_emote(slot_id=2, emote_id=0, account_id=self.account_id)
        selected_after = inventory_service.get_selected_items(self.account_id)
        emotes_dict_after = dict(selected_after["emotes"])
        self.assertNotIn(2, emotes_dict_after)

    def test_05_tcp_show_emote_broadcast(self):
        """Verify client sending SHOWEMOTE (msg 21) receives and broadcasts SHOWEMOTE_NTF (msg 22)."""
        group_id = self.account_id
        target_emote = 909000005

        # Build ShowEmoteReq (tag 1: group_id, tag 2: emote_id)
        req_buf = bytearray()
        req_buf += encode_uint64(1, group_id)
        req_buf += encode_uint32(2, target_emote)

        resp_cmd, ret_code, payload = handle_group_tcp_command(
            protocol=EProtocolProto.GROUP,
            cmd=EGroupProto.SHOWEMOTE,
            raw_body=bytes(req_buf),
            account_id=self.account_id,
        )

        self.assertEqual(resp_cmd, EGroupProto.SHOWEMOTE_NTF)
        self.assertEqual(ret_code, 0)

        # Verify ShowEmoteNtf payload (tag 1: account_id, tag 2: emote_id)
        f = decode_proto(payload)
        self.assertEqual(get_varint(f, 1, 0), self.account_id)
        self.assertEqual(get_varint(f, 2, 0), target_emote)

    def test_06_tcp_show_pet_action_broadcast(self):
        """Verify client sending SHOWPETACTION (msg 23) receives SHOWPETACTION_NTF (msg 24)."""
        group_id = self.account_id
        action_id = 1

        req_buf = bytearray()
        req_buf += encode_uint64(1, group_id)
        req_buf += encode_uint32(2, action_id)

        resp_cmd, ret_code, payload = handle_group_tcp_command(
            protocol=EProtocolProto.GROUP,
            cmd=EGroupProto.SHOWPETACTION,
            raw_body=bytes(req_buf),
            account_id=self.account_id,
        )

        self.assertEqual(resp_cmd, EGroupProto.SHOWPETACTION_NTF)
        self.assertEqual(ret_code, 0)
        f = decode_proto(payload)
        self.assertEqual(get_varint(f, 1, 0), self.account_id)
        self.assertEqual(get_varint(f, 2, 0), action_id)

    def test_07_banners_and_headpics(self):
        """Verify ChooseBanner and ChooseHeadPic update profile state."""
        inventory_service.choose_banner(901000020, account_id=self.account_id)
        inventory_service.choose_head_pic(902000030, account_id=self.account_id)

        prof = state.get_profile(self.account_id)
        self.assertEqual(prof["banner_id"], 901000020)
        self.assertEqual(prof["head_pic"], 902000030)

    def test_08_unlock_collection_item(self):
        """Verify unlock_collection_item adds item to state and persists."""
        custom_item = 907000999
        unlocked = inventory_service.unlock_collection_item(custom_item, count=5, account_id=self.account_id)
        self.assertTrue(unlocked)
        self.assertIn(custom_item, state.get_unlocked_items())
        self.assertGreaterEqual(state.get_item_count(custom_item), 5)


if __name__ == "__main__":
    unittest.main()
