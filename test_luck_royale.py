"""Comprehensive Unit Tests for Free Fire 1.39 Luck Royale Architecture."""

import random
import unittest
from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.gacha_handler import GachaService
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
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
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
    def setUp(self) -> None:
        self.svc = GachaService()
        self.account_id = random.randint(910000, 999999)
        # Seed wallet
        state.grant_currency(coins=100000, gems=50000, account_id=self.account_id)
        # Ensure seeded items
        self.svc._ensure_seeded(self.account_id)

    def test_gacha_desc_and_info(self) -> None:
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
        self.assertEqual(chest_ids, {CHEST_DIAMOND_ROYALE, CHEST_WEAPON_ROYALE, CHEST_GOLD_ROYALE, CHEST_INCUBATOR})

    def test_gold_royale_single_spin_with_gold(self) -> None:
        init_coins = state.get_wallet(self.account_id)["coins"]
        # Clear vouchers to force coin spend
        state._unlocked_items.discard(VOUCHER_GOLD_ROYALE)
        state._item_counts.pop(VOUCHER_GOLD_ROYALE, None)

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(len(get_submessages(res, 1)), 1)
        self.assertEqual(len(get_submessages(res, 3)), 0)
        # Verified 300 gold deduction
        cur_coins = state.get_wallet(self.account_id)["coins"]
        self.assertEqual(init_coins - cur_coins, 300)
        # Check weekly count
        self.assertEqual(get_varint(res, 4), 1)

    def test_gold_royale_multi_spin_10_plus_1(self) -> None:
        # Give 10 gold vouchers
        state.add_item(VOUCHER_GOLD_ROYALE, 10)
        init_vouchers = state.get_item_count(VOUCHER_GOLD_ROYALE)
        self.assertTrue(init_vouchers >= 10)

        req = {"chest_id": CHEST_GOLD_ROYALE, "gacha_type": LotteryType.SOME, "consume_type": ConsumeType.EXCHANGE_ITEM}
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        # Multi-spin MUST deliver 10 main items + 1 bonus item = 11 total!
        lottery_goods = get_submessages(res, 1)
        extra_one_goods = get_submessages(res, 3)
        self.assertEqual(len(lottery_goods), 10)
        self.assertEqual(len(extra_one_goods), 1)
        self.assertEqual(len(lottery_goods) + len(extra_one_goods), 11)

        # Voucher deduction: exactly 10 vouchers consumed
        new_vouchers = state.get_item_count(VOUCHER_GOLD_ROYALE)
        self.assertEqual(init_vouchers - new_vouchers, 10)

        # Weekly counter updated by 11
        self.assertEqual(get_varint(res, 4), 11)

    def test_diamond_royale_multi_spin_10_plus_1(self) -> None:
        state.add_item(VOUCHER_DIAMOND_ROYALE, 10)
        init_vouchers = state.get_item_count(VOUCHER_DIAMOND_ROYALE)

        req = {"chest_id": CHEST_DIAMOND_ROYALE, "gacha_type": LotteryType.SOME, "consume_type": ConsumeType.EXCHANGE_ITEM}
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(len(get_submessages(res, 1)), 10)
        self.assertEqual(len(get_submessages(res, 3)), 1)
        self.assertEqual(init_vouchers - state.get_item_count(VOUCHER_DIAMOND_ROYALE), 10)

    def test_weapon_royale_multi_spin_10_plus_1(self) -> None:
        state.add_item(VOUCHER_WEAPON_ROYALE, 10)
        init_vouchers = state.get_item_count(VOUCHER_WEAPON_ROYALE)

        req = {"chest_id": CHEST_WEAPON_ROYALE, "gacha_type": LotteryType.SOME, "consume_type": ConsumeType.EXCHANGE_ITEM}
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(len(get_submessages(res, 1)), 10)
        self.assertEqual(len(get_submessages(res, 3)), 1)
        self.assertEqual(init_vouchers - state.get_item_count(VOUCHER_WEAPON_ROYALE), 10)

    def test_incubator_turntable_5_spins(self) -> None:
        state.add_item(VOUCHER_INCUBATOR, 5)
        init_vouchers = state.get_item_count(VOUCHER_INCUBATOR)

        # Incubator multi-spin is 5 spins (not 10+1)
        req = {"chest_id": CHEST_INCUBATOR, "gacha_type": LotteryType.SOME, "consume_type": ConsumeType.EXCHANGE_ITEM}
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(len(get_submessages(res, 1)), 5)
        self.assertEqual(len(get_submessages(res, 3)), 0)
        self.assertEqual(init_vouchers - state.get_item_count(VOUCHER_INCUBATOR), 5)
        self.assertEqual(get_varint(res, 4), 5)

    def test_luck_accumulation_and_pity(self) -> None:
        rec = self.svc._get_chest_record(self.account_id, CHEST_DIAMOND_ROYALE)
        rec["not_got_num"] = 149  # Pity is rare_item_max = 150

        req = {"chest_id": CHEST_DIAMOND_ROYALE, "gacha_type": LotteryType.ONE, "consume_type": ConsumeType.MONEY}
        res_bytes = self.svc.purchase_gacha(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        # Pity triggered: got rare item, not_got_num reset to 0!
        self.assertEqual(get_varint(res, 8), 0)
        self.assertTrue(get_bool(res, 11))

    def test_milestone_claim(self) -> None:
        rec = self.svc._get_chest_record(self.account_id, CHEST_GOLD_ROYALE)
        rec["lottery_count_weekly"] = 15

        req = {"chest_id": CHEST_GOLD_ROYALE, "condition_num": 5}
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
        # Give required materials: 3 YinYang Blueprints + 7 Evolution Stones
        state.add_item(ITEM_BLUEPRINT_YINYANG, 3)
        state.add_item(ITEM_EVOLUTION_STONE, 7)

        req = {"forge_tab_id": 1, "item_id": 710000410, "exchange_cnt": 1}
        res_bytes = self.svc.do_special_exchange(req, account_id=self.account_id)
        res = decode_proto(res_bytes)

        self.assertEqual(get_varint(res, 2), 1)
        change_data = get_submessage(res, 1)
        add_items = get_submessages(change_data, 2)
        del_items = get_submessages(change_data, 3)
        self.assertEqual(len(add_items), 1)
        self.assertEqual(get_varint(add_items[0], 1), 710000410)
        self.assertEqual(len(del_items), 2)
        self.assertTrue(state.is_item_unlocked(710000410))

    def test_sqlite_persistence(self) -> None:
        rec = self.svc._get_chest_record(self.account_id, CHEST_DIAMOND_ROYALE)
        rec["lottery_count_weekly"] = 42
        rec["not_got_num"] = 77
        rec["exchanged_reward_list"] = [5, 15]
        db.save_gacha_state(self.account_id, CHEST_DIAMOND_ROYALE, rec)

        # Fresh service instance
        new_svc = GachaService()
        new_svc._ensure_seeded(self.account_id)
        loaded_rec = new_svc._get_chest_record(self.account_id, CHEST_DIAMOND_ROYALE)

        self.assertEqual(loaded_rec["lottery_count_weekly"], 42)
        self.assertEqual(loaded_rec["not_got_num"], 77)
        self.assertEqual(loaded_rec["exchanged_reward_list"], [5, 15])


if __name__ == "__main__":
    unittest.main()
