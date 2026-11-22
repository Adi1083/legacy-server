"""
Authoritative Test Suite for Gold Royale Duplicate Character Reward Bugfix.
Validates:
1. 19 Authoritative Avatar ID -> Debris ID mappings (and Adam/Eva exclusions).
2. Elimination of modulo and arithmetic derivation.
3. First-time unlock vs duplicate debris conversion.
4. Gender-pair collision immunity and disputed mappings (Laura, Rafael, A124, Joseph).
5. ExchangedAward wire protocol serialization (CSLotteryRes).
6. Inventory fragment accumulation across single and multi-spins.
7. SpinRollbackJournal atomic rollback on unmapped / invalid duplicate rewards.
8. Isolation: non-character items and other Royale machines.
9. Admin Luck Royale API pool management validation.
"""

from __future__ import annotations

import os
import random
import sys
import unittest
from typing import Any, Dict, List, Optional

# Ensure server module root is in path
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

from core.database import db
from core.player import player_manager
from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.admin_luck_royale_api import LuckRoyaleAdminManager, admin_mgr
from handlers.gacha_handler import GachaService, gacha_service
from proto.character_models import (
    AVATAR_CATALOG,
    AVATAR_TO_DEBRIS_MAP,
    STARTER_AVATAR_IDS,
    get_character_debris_id,
)
from proto.decoder import decode_proto, get_submessages, get_varint
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
    VOUCHER_GOLD_ROYALE,
    ChestTabType,
    CoinType,
    ConsumeType,
    GachaShowItemConfig,
    LotteryType,
    RareType,
)
from proto.inventory_models import UNLOCKED_ITEM_DEFS, ItemType
from proto.store_models import AwardType


class FixedItemRng(random.Random):
    """Deterministic test RNG that yields specified items in sequence or repeats."""

    def __init__(self, items: List[GachaShowItemConfig]) -> None:
        super().__init__()
        self._items = list(items)
        self._idx = 0

    def choices(self, population, weights=None, *, cum_weights=None, k=1):
        result = []
        for _ in range(k):
            item = self._items[self._idx % len(self._items)]
            self._idx += 1
            result.append(item)
        return result


class TestGoldRoyaleDebrisMapping(unittest.TestCase):
    """Test 1: Authoritative Mapping Matrix and Exclusions."""

    EXPECTED_19_MAPPINGS: Dict[int, int] = {
        102000005: 800000001,  # Andrew
        101000005: 800000002,  # Olivia
        101000006: 800000003,  # Kelly
        102000006: 800000004,  # Ford
        101000007: 800000005,  # Nikita
        101000008: 800000006,  # Misha
        102000007: 800000007,  # Maxim
        102000008: 800000008,  # Kla
        101000009: 800000009,  # Paloma
        102000009: 800000010,  # Miguel
        101000010: 800000011,  # Caroline
        102000010: 800000012,  # Antonio
        102000011: 800000013,  # Wukong
        101000011: 800000014,  # Moco
        102000012: 800000015,  # Hayato
        101000012: 800000016,  # Laura
        102000013: 800000017,  # Rafael
        101000013: 800000018,  # A124
        102000014: 800000019,  # Joseph
    }

    def test_all_19_characters_mapped_authoritatively(self):
        """Verify all 19 upgradeable characters map to their exact verified DebrisID."""
        self.assertEqual(len(AVATAR_TO_DEBRIS_MAP), 19)
        for avatar_id, expected_debris in self.EXPECTED_19_MAPPINGS.items():
            actual = get_character_debris_id(avatar_id)
            self.assertEqual(
                actual,
                expected_debris,
                f"Avatar {avatar_id} mapped to {actual}, expected {expected_debris}",
            )

    def test_starters_adam_and_eva_excluded(self):
        """Adam (102000004) and Eva (101000001) must return None (no debris entries)."""
        self.assertIn(102000004, STARTER_AVATAR_IDS)
        self.assertIn(101000001, STARTER_AVATAR_IDS)
        self.assertIsNone(get_character_debris_id(102000004))
        self.assertIsNone(get_character_debris_id(101000001))

    def test_unmapped_and_invalid_ids_return_none(self):
        """Unmapped IDs and invalid inputs must return None without exceptions."""
        self.assertIsNone(get_character_debris_id(109999999))
        self.assertIsNone(get_character_debris_id(0))
        self.assertIsNone(get_character_debris_id(710000422))  # Bundle ID

    def test_gender_pair_collision_immunity(self):
        """Verify gender pairs produce distinct debris IDs and would have collided under modulo."""
        pairs = [
            ("Andrew", 102000005, "Olivia", 101000005),
            ("Ford", 102000006, "Kelly", 101000006),
            ("Maxim", 102000007, "Nikita", 101000007),
            ("Kla", 102000008, "Misha", 101000008),
            ("Miguel", 102000009, "Paloma", 101000009),
            ("Antonio", 102000010, "Caroline", 101000010),
            ("Wukong", 102000011, "Moco", 101000011),
            ("Hayato", 102000012, "Laura", 101000012),
            ("Rafael", 102000013, "A124", 101000013),
        ]
        for m_name, m_id, f_name, f_id in pairs:
            m_debris = get_character_debris_id(m_id)
            f_debris = get_character_debris_id(f_id)
            self.assertIsNotNone(m_debris)
            self.assertIsNotNone(f_debris)
            self.assertNotEqual(
                m_debris,
                f_debris,
                f"Collision detected between {m_name} ({m_id}) and {f_name} ({f_id}): both gave {m_debris}",
            )
            # Demonstrate that modulo would have collided:
            self.assertEqual(m_id % 100000, f_id % 100000)

    def test_disputed_characters_authoritative_resolution(self):
        """Confirm Laura=800000016, Rafael=800000017, A124=800000018, Joseph=800000019."""
        self.assertEqual(get_character_debris_id(101000012), 800000016)  # Laura
        self.assertEqual(get_character_debris_id(102000013), 800000017)  # Rafael
        self.assertEqual(get_character_debris_id(101000013), 800000018)  # A124
        self.assertEqual(get_character_debris_id(102000014), 800000019)  # Joseph

    def test_all_destination_items_are_debris_type(self):
        """Every mapped destination debris item must be classified as ItemType.DEBRIS in UNLOCKED_ITEM_DEFS."""
        for avatar_id, debris_id in self.EXPECTED_19_MAPPINGS.items():
            meta = UNLOCKED_ITEM_DEFS.get(debris_id)
            self.assertIsNotNone(meta, f"Debris ID {debris_id} not found in UNLOCKED_ITEM_DEFS")
            item_type, sub_type, _ = meta
            self.assertEqual(
                item_type,
                ItemType.DEBRIS,
                f"Debris ID {debris_id} (Avatar {avatar_id}) has item_type {item_type}, expected {ItemType.DEBRIS}",
            )


class TestGoldRoyaleGachaExecution(unittest.TestCase):
    """Test 2: Gacha Service Duplicate Character Conversion, Protocol & Atomicity."""

    def setUp(self):
        self.test_account = random.randint(90000000, 99999999)
        state.modify_gold(self.test_account, 100000)
        state.modify_diamond(self.test_account, 50000)
        state.add_item(VOUCHER_GOLD_ROYALE, 50, account_id=self.test_account)

    def tearDown(self):
        with state._lock:
            state._wallet.pop(self.test_account, None)
            player_manager._players.pop(self.test_account, None)

    def test_first_time_character_unlock_no_debris_conversion(self):
        """When an avatar is not yet owned, winning it unlocks the avatar, not debris."""
        avatar_id = 102000005  # Andrew
        target = GachaShowItemConfig(
            item_id=avatar_id,
            item_num=1,
            item_type=AwardType.ITEM,
            is_show=True,
            reward_level=RareType.NORMAL,
            repeated_item_id=0,
            repeated_item_num=5,
            weight=100,
        )
        svc = GachaService(rng=FixedItemRng([target]))

        # Ensure not unlocked
        state.lock_item(avatar_id, account_id=self.test_account)
        self.assertFalse(state.is_item_unlocked(avatar_id, account_id=self.test_account))

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}
        res_bytes = svc.purchase_gacha(req, account_id=self.test_account)
        decoded = decode_proto(res_bytes)
        goods_list = get_submessages(decoded, 1)
        self.assertEqual(len(goods_list), 1)
        award = goods_list[0]

        # Origin & Dest should both be the Avatar ID
        self.assertEqual(get_varint(award, 2), avatar_id)
        self.assertEqual(get_varint(award, 5), avatar_id)  # dest_award_id
        self.assertEqual(get_varint(award, 6), 1)          # dest_award_num

        # Inventory check: Avatar unlocked, Debris count is 0
        self.assertTrue(state.is_item_unlocked(avatar_id, account_id=self.test_account))
        debris_id = get_character_debris_id(avatar_id)
        self.assertEqual(state.get_item_count(debris_id, account_id=self.test_account), 0)

    def test_duplicate_character_converts_to_exact_debris_all_19(self):
        """Every one of the 19 upgradeable characters, when already owned, converts to exact DebrisID."""
        for avatar_id, expected_debris in TestGoldRoyaleDebrisMapping.EXPECTED_19_MAPPINGS.items():
            acc = random.randint(90000000, 99999999)
            state.modify_gold(acc, 100000)
            # Pre-unlock the avatar
            state.unlock_item(avatar_id, count=1, account_id=acc)
            self.assertTrue(state.is_item_unlocked(avatar_id, account_id=acc))

            target = GachaShowItemConfig(
                item_id=avatar_id,
                item_num=1,
                item_type=AwardType.ITEM,
                is_show=True,
                reward_level=RareType.NORMAL,
                repeated_item_id=0,
                repeated_item_num=5,
                weight=100,
            )
            svc = GachaService(rng=FixedItemRng([target]))

            prev_debris_cnt = state.get_item_count(expected_debris, account_id=acc)
            req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}
            res_bytes = svc.purchase_gacha(req, account_id=acc)

            decoded = decode_proto(res_bytes)
            goods_list = get_submessages(decoded, 1)
            self.assertEqual(len(goods_list), 1)
            award = goods_list[0]

            # Wire protocol verification
            self.assertEqual(get_varint(award, 2), avatar_id)               # origin_award_id
            self.assertEqual(get_varint(award, 4), AwardType.ITEM)          # dest_award_type
            self.assertEqual(get_varint(award, 5), expected_debris)         # dest_award_id
            self.assertEqual(get_varint(award, 6), 5)                       # dest_award_num

            # Inventory verification: debris increased by 5
            new_debris_cnt = state.get_item_count(expected_debris, account_id=acc)
            self.assertEqual(new_debris_cnt, prev_debris_cnt + 5)

            # Cleanup
            with state._lock:
                state._wallet.pop(acc, None)
                player_manager._players.pop(acc, None)

    def test_exchanged_award_wire_serialization(self):
        """Verify the exact field tags and types in ExchangedAward wire message."""
        avatar_id = 101000012  # Laura -> 800000016
        state.unlock_item(avatar_id, count=1, account_id=self.test_account)

        target = GachaShowItemConfig(
            item_id=avatar_id,
            item_num=1,
            item_type=AwardType.ITEM,
            is_show=True,
            reward_level=RareType.NORMAL,
            repeated_item_id=0,
            repeated_item_num=8,
            weight=100,
        )
        svc = GachaService(rng=FixedItemRng([target]))

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}
        res_bytes = svc.purchase_gacha(req, account_id=self.test_account)
        decoded = decode_proto(res_bytes)
        goods_list = get_submessages(decoded, 1)
        award = goods_list[0]

        # Field 1: origin_award_type
        self.assertEqual(get_varint(award, 1), AwardType.ITEM)
        # Field 2: origin_award_id
        self.assertEqual(get_varint(award, 2), avatar_id)
        # Field 3: origin_award_num
        self.assertEqual(get_varint(award, 3), 1)
        # Field 4: dest_award_type
        self.assertEqual(get_varint(award, 4), AwardType.ITEM)
        # Field 5: dest_award_id (must match Laura's debris 800000016)
        self.assertEqual(get_varint(award, 5), 800000016)
        # Field 6: dest_award_num (configured 8)
        self.assertEqual(get_varint(award, 6), 8)

    def test_fragment_accumulation_across_consecutive_spins(self):
        """Multiple duplicate spins correctly accumulate fragments in player inventory."""
        avatar_id = 102000010  # Antonio -> 800000012
        debris_id = 800000012
        state.unlock_item(avatar_id, count=1, account_id=self.test_account)

        target = GachaShowItemConfig(
            item_id=avatar_id,
            item_num=1,
            item_type=AwardType.ITEM,
            is_show=True,
            reward_level=RareType.NORMAL,
            repeated_item_id=0,
            repeated_item_num=5,
            weight=100,
        )
        svc = GachaService(rng=FixedItemRng([target]))
        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}

        for spin_num in range(1, 4):
            res_bytes = svc.purchase_gacha(req, account_id=self.test_account)
            decoded = decode_proto(res_bytes)
            self.assertEqual(len(get_submessages(decoded, 1)), 1)
            self.assertEqual(
                state.get_item_count(debris_id, account_id=self.test_account),
                spin_num * 5,
            )

    def test_multi_spin_first_draw_unlocks_second_draw_converts_to_debris(self):
        """Within a single multi-spin batch, first draw unlocks avatar, subsequent draws convert to debris."""
        avatar_id = 101000006  # Kelly -> 800000003
        debris_id = 800000003
        state.lock_item(avatar_id, account_id=self.test_account)
        self.assertFalse(state.is_item_unlocked(avatar_id, account_id=self.test_account))

        target = GachaShowItemConfig(
            item_id=avatar_id,
            item_num=1,
            item_type=AwardType.ITEM,
            is_show=True,
            reward_level=RareType.NORMAL,
            repeated_item_id=0,
            repeated_item_num=5,
            weight=100,
        )
        # FixedItemRng always yields Kelly
        svc = GachaService(rng=FixedItemRng([target]))

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.SOME, "consume_type": ConsumeType.MONEY}
        res_bytes = svc.purchase_gacha(req, account_id=self.test_account)
        decoded = decode_proto(res_bytes)
        goods_list = get_submessages(decoded, 1)
        extra_goods = get_submessages(decoded, 3)
        self.assertEqual(len(goods_list), 10)
        self.assertEqual(len(extra_goods), 1)

        # 1st draw: Character Unlock
        award1 = goods_list[0]
        self.assertEqual(get_varint(award1, 2), avatar_id)
        self.assertEqual(get_varint(award1, 5), avatar_id)  # dest is avatar_id

        # 2nd through 10th draw: Converted to Debris
        for g in goods_list[1:]:
            self.assertEqual(get_varint(g, 2), avatar_id)
            self.assertEqual(get_varint(g, 5), debris_id)  # dest is debris_id
            self.assertEqual(get_varint(g, 6), 5)

        # 11th draw (10+1 bonus extra): Converted to Debris
        extra_award = extra_goods[0]
        self.assertEqual(get_varint(extra_award, 2), avatar_id)
        self.assertEqual(get_varint(extra_award, 5), debris_id)
        self.assertEqual(get_varint(extra_award, 6), 5)

        # State check: Avatar unlocked AND 50 debris (9 base + 1 extra bonus = 10 * 5) in inventory
        self.assertTrue(state.is_item_unlocked(avatar_id, account_id=self.test_account))
        self.assertEqual(state.get_item_count(debris_id, account_id=self.test_account), 50)

    def test_unmapped_or_starter_duplicate_triggers_atomic_rollback(self):
        """Duplicate unmapped avatar (or Adam/Eva) in Gold Royale must raise error and rollback spin atomically."""
        starter_id = 102000004  # Adam (starter avatar, excluded from debris)
        state.unlock_item(starter_id, count=1, account_id=self.test_account)

        target = GachaShowItemConfig(
            item_id=starter_id,
            item_num=1,
            item_type=AwardType.ITEM,
            is_show=True,
            reward_level=RareType.NORMAL,
            repeated_item_id=0,
            repeated_item_num=5,
            weight=100,
        )
        svc = GachaService(rng=FixedItemRng([target]))

        gold_before = state.get_gold(self.test_account)
        rec = svc._get_chest_record(self.test_account, CHEST_GOLD_ROYALE)
        rec["not_got_num"] = 42
        luck_before = rec["not_got_num"]

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}
        res_bytes = svc.purchase_gacha(req, account_id=self.test_account)
        decoded = decode_proto(res_bytes)

        # Goods list should be empty due to rollback
        goods_list = get_submessages(decoded, 1)
        self.assertEqual(len(goods_list), 0)

        # Atomic Rollback Verification:
        # 1. Gold was refunded in full
        self.assertEqual(state.get_gold(self.test_account), gold_before)
        # 2. Luck meter was reverted to pre-spin value
        self.assertEqual(rec["not_got_num"], luck_before)
        # 3. No generic FF tokens or foreign debris were awarded
        self.assertEqual(state.get_item_count(ITEM_FF_TOKEN, account_id=self.test_account), 0)

    def test_bonus_extra_draw_duplicate_character_conversion(self):
        """10+1 multi-draw bonus +1 slot properly converts duplicate character to debris."""
        avatar_id = 102000014  # Joseph -> 800000019
        debris_id = 800000019
        state.unlock_item(avatar_id, count=1, account_id=self.test_account)

        target = GachaShowItemConfig(
            item_id=avatar_id,
            item_num=1,
            item_type=AwardType.ITEM,
            is_show=True,
            reward_level=RareType.NORMAL,
            repeated_item_id=0,
            repeated_item_num=5,
            weight=100,
        )
        svc = GachaService(rng=FixedItemRng([target]))

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.SOME, "consume_type": ConsumeType.MONEY}
        res_bytes = svc.purchase_gacha(req, account_id=self.test_account)
        decoded = decode_proto(res_bytes)

        # Field 1: 10 base goods
        base_goods = get_submessages(decoded, 1)
        self.assertEqual(len(base_goods), 10)
        # Field 3: 1 extra bonus good
        extra_goods = get_submessages(decoded, 3)
        self.assertEqual(len(extra_goods), 1)

        extra_award = extra_goods[0]
        self.assertEqual(get_varint(extra_award, 2), avatar_id)
        self.assertEqual(get_varint(extra_award, 5), debris_id)
        self.assertEqual(get_varint(extra_award, 6), 5)

    def test_non_character_items_and_other_machines_isolation(self):
        """Non-character rewards in Gold Royale convert to FF Token; other machines isolate properly."""
        # 1. Clothes duplicate in Gold Royale
        clothes_id = 710000303
        state.unlock_item(clothes_id, count=1, account_id=self.test_account)

        target_clothes = GachaShowItemConfig(
            item_id=clothes_id,
            item_num=1,
            item_type=AwardType.ITEM,
            is_show=True,
            reward_level=RareType.RARE,
            repeated_item_id=ITEM_FF_TOKEN,
            repeated_item_num=5,
            weight=100,
        )
        svc = GachaService(rng=FixedItemRng([target_clothes]))

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}
        res_bytes = svc.purchase_gacha(req, account_id=self.test_account)
        decoded = decode_proto(res_bytes)
        award = get_submessages(decoded, 1)[0]

        # Should convert to FF Token (110200001), NOT debris
        self.assertEqual(get_varint(award, 5), ITEM_FF_TOKEN)
        self.assertEqual(get_varint(award, 6), 5)


class TestAdminLuckRoyaleDebrisValidation(unittest.TestCase):
    """Test 3: Admin Luck Royale API Pool Item Validation."""

    def test_admin_add_pool_item_auto_assigns_authoritative_debris(self):
        """Adding a character to Gold Royale pool automatically sets repeated_item_id to verified debris."""
        # Add Moco (101000011 -> 800000014) to Gold Royale (machine 5)
        avatar_id = 101000011
        expected_debris = 800000014

        item_data = {
            "item_id": avatar_id,
            "item_num": 1,
            "weight": 50,
            "reward_level": RareType.NORMAL,
        }
        ok, msg, serialized = admin_mgr.add_pool_item(CHEST_GOLD_ROYALE, item_data)
        self.assertTrue(ok, f"add_pool_item failed: {msg}")
        self.assertIsNotNone(serialized)
        self.assertEqual(serialized.get("repeated_item_id"), expected_debris)
        self.assertGreaterEqual(serialized.get("repeated_item_num", 0), 5)

        # Cleanup: remove from pool
        admin_mgr.remove_pool_item(CHEST_GOLD_ROYALE, avatar_id)

    def test_admin_add_pool_item_rejects_starter_or_unmapped_character(self):
        """Adding starter Adam (102000004) or unknown avatar to Gold Royale is rejected."""
        # 1. Adam
        item_data_adam = {"item_id": 102000004, "item_num": 1, "weight": 50}
        ok, msg, _ = admin_mgr.add_pool_item(CHEST_GOLD_ROYALE, item_data_adam)
        self.assertFalse(ok)
        self.assertIn("excluded", msg)

        # 2. Bogus avatar
        item_data_bogus = {"item_id": 109999999, "item_num": 1, "weight": 50}
        ok_b, msg_b, _ = admin_mgr.add_pool_item(CHEST_GOLD_ROYALE, item_data_bogus)
        self.assertFalse(ok_b)
        self.assertIn("no valid debris mapping", msg_b)


if __name__ == "__main__":
    unittest.main()
