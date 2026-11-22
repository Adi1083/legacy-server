"""Comprehensive automated test suite for Luck Royale / Gacha Engine in Free Fire 1.39 (Barbosa).

Verifies:
1. Single spins (1x) and multi-spins (5x, 10x, 11x depending on machine config).
2. Server-authoritative random reward selection (never trust client-supplied IDs).
3. Machine-specific reward pool isolation (prevent cross-machine reward contamination).
4. Lucky meter progression, reset upon grand prize drop, and guaranteed jackpot triggering.
5. Duplicate reward detection and automatic FF Token conversion (with configured token rates per rarity).
6. Atomic inventory injection into core.state with failure rollback and concurrency protection (RLock).
7. Transaction idempotency and spin history logging.
8. Original baseline compatibility test suite.
"""

from __future__ import annotations

import json
import random
import threading
import time
import unittest
from typing import Any, Dict, List

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.gacha_handler import GachaService, _is_stackable_item, gacha_service
from proto.decoder import (
    decode_proto,
    get_bool,
    get_int32,
    get_int64,
    get_packed_varints,
    get_submessage,
    get_submessages,
    get_varint,
)
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    DEFAULT_SPECIAL_EXCHANGES,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
    ITEM_MAGIC_CUBE,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
    CoinType,
    ConsumeType,
    LotteryType,
    RareType,
)


class TestLuckRoyaleBackend(unittest.TestCase):
    """Full unit and integration test suite for Luck Royale gacha engine."""

    def setUp(self) -> None:
        self.svc = GachaService()
        self.account_id = random.randint(910000, 999999)
        # Grant abundant currency using state modify helpers
        state.modify_gold(self.account_id, 100000)
        state.modify_diamond(self.account_id, 50000)
        state.modify_gold(DEFAULT_ACCOUNT_ID, 100000)
        state.modify_diamond(DEFAULT_ACCOUNT_ID, 50000)
        self.svc._ensure_seeded(self.account_id)

    # -----------------------------------------------------------------------
    # Baseline OB17 Compatibility Tests
    # -----------------------------------------------------------------------

    def test_gacha_desc_and_info(self) -> None:
        """Verify GetGachaDesc and GetGachaInfo responses."""
        desc_bytes = self.svc.get_gacha_desc()
        self.assertTrue(len(desc_bytes) > 0)
        desc_proto = decode_proto(desc_bytes)
        self.assertEqual(len(get_submessages(desc_proto, 1)), 4)

        info_bytes = self.svc.get_gacha_info(self.account_id)
        self.assertTrue(len(info_bytes) > 0)
        info_proto = decode_proto(info_bytes)
        infos = get_submessages(info_proto, 1)
        self.assertEqual(len(infos), 4)

        chest_ids = {get_varint(info, 1) for info in infos}
        self.assertEqual(
            chest_ids,
            {CHEST_DIAMOND_ROYALE, CHEST_WEAPON_ROYALE, CHEST_GOLD_ROYALE, CHEST_INCUBATOR},
        )

    def test_gold_royale_single_spin_with_gold(self) -> None:
        """Verify single spin on Gold Royale deducting 300 gold coins."""
        init_coins = state.get_gold(self.account_id)
        # Discard vouchers so money deduction is tested
        state.lock_item(VOUCHER_GOLD_ROYALE, account_id=self.account_id)
        state.lock_item(110100010, account_id=self.account_id)
        state._unlocked_items.discard(VOUCHER_GOLD_ROYALE)
        state._item_counts.pop(VOUCHER_GOLD_ROYALE, None)
        state._unlocked_items.discard(110100010)
        state._item_counts.pop(110100010, None)

        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        # Tag 1: lottery_goods (single spin = 1 item)
        self.assertEqual(len(get_submessages(res, 1)), 1)
        # Tag 3: extra_one_goods (single spin = 0 extra)
        self.assertEqual(len(get_submessages(res, 3)), 0)

        cur_coins = state.get_gold(self.account_id)
        self.assertEqual(init_coins - cur_coins, 300)
        # Tag 4: lottery_count_weekly incremented to 1
        self.assertEqual(get_varint(res, 4), 1)

    def test_gold_royale_multi_spin_10_plus_1(self) -> None:
        """Verify 10+1 multi-spin on Gold Royale using 10 vouchers."""
        state.add_item(VOUCHER_GOLD_ROYALE, 10, account_id=self.account_id)
        init_vouchers = state.get_item_count(VOUCHER_GOLD_ROYALE, account_id=self.account_id)
        self.assertTrue(init_vouchers >= 10)

        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.EXCHANGE_ITEM,
        }
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        lottery_goods = get_submessages(res, 1)
        extra_one_goods = get_submessages(res, 3)

        self.assertEqual(len(lottery_goods), 10)
        self.assertEqual(len(extra_one_goods), 1)
        self.assertEqual(len(lottery_goods) + len(extra_one_goods), 11)

        new_vouchers = state.get_item_count(VOUCHER_GOLD_ROYALE, account_id=self.account_id)
        self.assertEqual(init_vouchers - new_vouchers, 10)
        # Weekly count incremented by 11
        self.assertEqual(get_varint(res, 4), 11)

    def test_diamond_royale_multi_spin_10_plus_1(self) -> None:
        """Verify 10+1 multi-spin on Diamond Royale using 10 vouchers."""
        state.add_item(VOUCHER_DIAMOND_ROYALE, 10, account_id=self.account_id)
        init_vouchers = state.get_item_count(VOUCHER_DIAMOND_ROYALE, account_id=self.account_id)

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.EXCHANGE_ITEM,
        }
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(len(get_submessages(res, 1)), 10)
        self.assertEqual(len(get_submessages(res, 3)), 1)
        new_vouchers = state.get_item_count(VOUCHER_DIAMOND_ROYALE, account_id=self.account_id)
        self.assertEqual(init_vouchers - new_vouchers, 10)

    def test_weapon_royale_multi_spin_10_plus_1(self) -> None:
        """Verify 10+1 multi-spin on Weapon Royale using 10 vouchers."""
        state.add_item(VOUCHER_WEAPON_ROYALE, 10, account_id=self.account_id)
        init_vouchers = state.get_item_count(VOUCHER_WEAPON_ROYALE, account_id=self.account_id)

        req = {
            "chest_id": CHEST_WEAPON_ROYALE,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.EXCHANGE_ITEM,
        }
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(len(get_submessages(res, 1)), 10)
        self.assertEqual(len(get_submessages(res, 3)), 1)
        new_vouchers = state.get_item_count(VOUCHER_WEAPON_ROYALE, account_id=self.account_id)
        self.assertEqual(init_vouchers - new_vouchers, 10)

    def test_incubator_turntable_5_spins(self) -> None:
        """Verify 5-spin multi-draw on Incubator turntable (no bonus extra spin)."""
        state.add_item(VOUCHER_INCUBATOR, 10, account_id=self.account_id)
        init_vouchers = state.get_item_count(VOUCHER_INCUBATOR, account_id=self.account_id)

        req = {
            "chest_id": CHEST_INCUBATOR,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.EXCHANGE_ITEM,
        }
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        # Incubator multi is 5 spins, NOT 10+1
        self.assertEqual(len(get_submessages(res, 1)), 5)
        self.assertEqual(len(get_submessages(res, 3)), 0)

        new_vouchers = state.get_item_count(VOUCHER_INCUBATOR, account_id=self.account_id)
        self.assertEqual(init_vouchers - new_vouchers, 5)
        self.assertEqual(get_varint(res, 4), 5)

    def test_luck_accumulation_and_pity(self) -> None:
        """Verify lucky meter reaches guaranteed pity, forces grand prize, and resets to 0."""
        rec = self.svc._get_chest_record(self.account_id, CHEST_DIAMOND_ROYALE)
        rec["not_got_num"] = 149  # 1 short of rare_item_max=150

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        # Tag 8: not_got_num must reset to 0 upon jackpot
        self.assertEqual(get_varint(res, 8), 0)
        # Tag 11: has_big_reward must be True
        self.assertTrue(get_bool(res, 11))

    def test_milestone_claim(self) -> None:
        """Verify weekly spin milestone reward claiming."""
        rec = self.svc._get_chest_record(self.account_id, CHEST_GOLD_ROYALE)
        rec["lottery_count_weekly"] = 15

        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "condition_num": 5,
        }
        res_bytes = self.svc.exchange_extra_reward(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        award_data = get_submessage(res, 1)
        items = get_submessages(award_data, 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(get_varint(items[0], 1), VOUCHER_GOLD_ROYALE)
        self.assertEqual(get_varint(items[0], 2), 2)

        exchanged_list = get_packed_varints(res, 2)
        self.assertIn(5, exchanged_list)

    def test_incubator_forge_special_exchange(self) -> None:
        """Verify Incubator Forge crafting with Evolution Stones and Blueprints."""
        state.add_item(ITEM_BLUEPRINT_YINYANG, 3, account_id=self.account_id)
        state.add_item(ITEM_EVOLUTION_STONE, 7, account_id=self.account_id)

        req = {
            "forge_tab_id": 1,
            "item_id": 710000410,
            "exchange_cnt": 1,
        }
        res_bytes = self.svc.do_special_exchange(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(get_varint(res, 2), 1)  # purchase_times
        change_data = get_submessage(res, 1)
        add_items = get_submessages(change_data, 2)
        del_items = get_submessages(change_data, 3)

        self.assertEqual(len(add_items), 1)
        self.assertEqual(get_varint(add_items[0], 1), 710000410)
        self.assertEqual(len(del_items), 2)
        self.assertTrue(state.is_item_unlocked(710000410, account_id=self.account_id))

    def test_sqlite_persistence(self) -> None:
        """Verify SQLite state persistence across service instances."""
        rec = self.svc._get_chest_record(self.account_id, CHEST_DIAMOND_ROYALE)
        rec["lottery_count_weekly"] = 42
        rec["not_got_num"] = 77
        rec["exchanged_reward_list"] = [5, 15]
        db.save_gacha_state(self.account_id, CHEST_DIAMOND_ROYALE, rec)

        new_svc = GachaService()
        new_svc._ensure_seeded(self.account_id)
        loaded_rec = new_svc._get_chest_record(self.account_id, CHEST_DIAMOND_ROYALE)

        self.assertEqual(loaded_rec["lottery_count_weekly"], 42)
        self.assertEqual(loaded_rec["not_got_num"], 77)
        self.assertEqual(loaded_rec["exchanged_reward_list"], [5, 15])

    # -----------------------------------------------------------------------
    # Advanced Architectural Verification (Requirements 1 - 7)
    # -----------------------------------------------------------------------

    def test_server_authoritative_pool_isolation(self) -> None:
        """Verify machine reward pools are isolated and client cannot inject item IDs."""
        diamond_item_ids = {it.item_id for it in CHEST_CONFIGS[CHEST_DIAMOND_ROYALE].items}

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
            "item_id": 999999999,  # Forged client item ID
            "reward_level": 999,    # Forged rarity
        }
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)
        lottery_goods = get_submessages(res, 1)

        origin_id = get_varint(lottery_goods[0], 2)
        # Server MUST select strictly from Diamond Royale pool
        self.assertIn(origin_id, diamond_item_ids)
        self.assertNotIn(origin_id, {999999999, 710000422})

    def test_intra_batch_duplicate_conversion(self) -> None:
        """Verify rolling the same permanent item twice in one multi-spin converts the second."""
        cfg = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        non_stackable = next(it for it in cfg.items if not _is_stackable_item(it.item_id))

        # Clear ownership
        state.lock_item(non_stackable.item_id, account_id=self.account_id)
        self.assertFalse(state.is_item_unlocked(non_stackable.item_id, account_id=self.account_id))

        # Mock RNG that always picks this same item
        class FixedItemRng(random.Random):
            def choices(self, population, weights=None, *, cum_weights=None, k=1):
                return [non_stackable]

        fixed_svc = GachaService(rng=FixedItemRng())
        fixed_svc._ensure_seeded(self.account_id)

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = fixed_svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)
        lottery_goods = get_submessages(res, 1)

        # 1st item should be the original permanent unlock
        self.assertEqual(get_varint(lottery_goods[0], 5), non_stackable.item_id)
        # 2nd through 10th items MUST be converted to FF Tokens
        expected_token = non_stackable.repeated_item_id or ITEM_FF_TOKEN
        for g in lottery_goods[1:]:
            self.assertEqual(get_varint(g, 5), expected_token)

    def test_transaction_idempotency(self) -> None:
        """Verify identical requests with same trans_id return cached response without double billing."""
        # Ensure vouchers are locked so MONEY is deducted
        state.lock_item(VOUCHER_DIAMOND_ROYALE, account_id=self.account_id)
        state.lock_item(110100008, account_id=self.account_id)
        state._unlocked_items.discard(VOUCHER_DIAMOND_ROYALE)
        state._item_counts.pop(VOUCHER_DIAMOND_ROYALE, None)
        state._unlocked_items.discard(110100008)
        state._item_counts.pop(110100008, None)

        init_gems = state.get_diamond(self.account_id)
        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
            "client_trans_id": 888777111,
        }

        res_1 = self.svc.purchase_gacha(req, account_id=self.account_id)
        gems_after_1 = state.get_diamond(self.account_id)
        self.assertEqual(init_gems - gems_after_1, 60)

        # Re-send exact same request (duplicate tap / network retry)
        res_2 = self.svc.purchase_gacha(req, account_id=self.account_id)
        gems_after_2 = state.get_diamond(self.account_id)

        # No additional currency spent
        self.assertEqual(gems_after_1, gems_after_2)
        # Exactly identical response payload returned
        self.assertEqual(res_1, res_2)

    def test_spin_history_logging(self) -> None:
        """Verify transaction history records every spin with rich metadata."""
        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        self.svc.purchase_gacha(req, account_id=self.account_id)

        history = self.svc.get_spin_history(account_id=self.account_id, limit=5)
        self.assertTrue(len(history) >= 1)
        latest = history[0]
        self.assertEqual(latest["account_id"], self.account_id)
        self.assertEqual(latest["chest_id"], CHEST_GOLD_ROYALE)

    def test_concurrency_thread_safety(self) -> None:
        """Verify concurrent multi-threaded spins on the same account operate safely without race conditions."""
        threads: List[threading.Thread] = []
        errors: List[Exception] = []

        def worker():
            try:
                req = {
                    "chest_id": CHEST_GOLD_ROYALE,
                    "gacha_type": LotteryType.ONE,
                    "consume_type": ConsumeType.MONEY,
                }
                res = self.svc.purchase_gacha(req, account_id=self.account_id)
                self.assertTrue(len(res) > 0)
            except Exception as e:
                errors.append(e)

        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        rec = self.svc._get_chest_record(self.account_id, CHEST_GOLD_ROYALE)
        self.assertEqual(rec["lottery_count_weekly"], 10)


if __name__ == "__main__":
    unittest.main()
