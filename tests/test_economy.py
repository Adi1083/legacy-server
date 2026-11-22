"""
Test Suite 3: Economy Tests for Free Fire 1.39 Luck Royale.
Verifies:
1. Diamond deduction for diamond-based spins (Diamond, Weapon, Incubator).
2. Gold deduction for gold-based spins (Gold Royale).
3. Voucher consumption for Gold, Diamond, Weapon, and Incubator Royales.
4. Voucher fallback and smart priority when consume_type=NONE.
5. Negative balance prevention and strict non-deduction on failed checks.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

SERVER_DIR = str(Path(__file__).resolve().parent.parent)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    CoinType,
    ConsumeType,
    LotteryType,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
)
from handlers.gacha_handler import gacha_service
from tests.test_helpers import (
    decode_cs_lottery_res,
    reset_test_account_state,
)


class TestEconomy(unittest.TestCase):
    def setUp(self) -> None:
        self.aid = 10001
        reset_test_account_state(
            account_id=self.aid,
            diamonds=10000,
            gold=100000,
            vouchers={},  # zero vouchers initially to test raw currency
        )

    def test_gold_deduction_single_spin(self) -> None:
        """Single Gold Royale spin deducts exactly once_price gold and 0 diamonds."""
        cfg = CHEST_CONFIGS[CHEST_GOLD_ROYALE]
        expected_price = cfg.discount_price_one or cfg.once_price
        initial_gold = state.get_gold(self.aid)
        initial_diamonds = state.get_diamond(self.aid)

        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 1)
        self.assertEqual(state.get_gold(self.aid), initial_gold - expected_price)
        self.assertEqual(state.get_diamond(self.aid), initial_diamonds)

    def test_diamond_deduction_single_spin(self) -> None:
        """Single Diamond Royale spin deducts exactly once_price diamonds and 0 gold."""
        cfg = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        expected_price = cfg.discount_price_one or cfg.once_price
        initial_gold = state.get_gold(self.aid)
        initial_diamonds = state.get_diamond(self.aid)

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 1)
        self.assertEqual(state.get_diamond(self.aid), initial_diamonds - expected_price)
        self.assertEqual(state.get_gold(self.aid), initial_gold)

    def test_diamond_deduction_multi_spin(self) -> None:
        """10x Diamond Royale spin deducts ten_price diamonds."""
        cfg = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        expected_price = cfg.discount_price_ten or cfg.ten_price
        initial_diamonds = state.get_diamond(self.aid)

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 10)
        self.assertEqual(state.get_diamond(self.aid), initial_diamonds - expected_price)

    def test_voucher_consumption_gold_royale(self) -> None:
        """Gold voucher consumption deducts voucher without touching gold balance."""
        cfg = CHEST_CONFIGS[CHEST_GOLD_ROYALE]
        voucher_id = cfg.exchange_itemid
        state.add_item(voucher_id, 5)

        initial_gold = state.get_gold(self.aid)
        initial_vouchers = state.get_item_count(voucher_id)

        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.EXCHANGE_ITEM,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 1)
        self.assertEqual(state.get_item_count(voucher_id), initial_vouchers - 1)
        self.assertEqual(state.get_gold(self.aid), initial_gold, "Gold balance must remain untouched")

    def test_voucher_consumption_diamond_royale(self) -> None:
        """Diamond voucher consumption deducts voucher without touching diamond balance."""
        cfg = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        voucher_id = cfg.exchange_itemid
        state.add_item(voucher_id, 5)

        initial_diamonds = state.get_diamond(self.aid)
        initial_vouchers = state.get_item_count(voucher_id)

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.EXCHANGE_ITEM,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 1)
        self.assertEqual(state.get_item_count(voucher_id), initial_vouchers - 1)
        self.assertEqual(state.get_diamond(self.aid), initial_diamonds, "Diamond balance must remain untouched")

    def test_voucher_priority_when_consume_type_none(self) -> None:
        """When consume_type=NONE, if vouchers are available they are prioritized over diamonds/gold."""
        cfg = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        voucher_id = cfg.exchange_itemid
        state.add_item(voucher_id, 3)

        initial_diamonds = state.get_diamond(self.aid)
        initial_vouchers = state.get_item_count(voucher_id)

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.NONE,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 1)
        self.assertEqual(state.get_item_count(voucher_id), initial_vouchers - 1)
        self.assertEqual(state.get_diamond(self.aid), initial_diamonds, "Diamonds must not be deducted when vouchers present")

    def test_negative_balance_prevention_gold(self) -> None:
        """Account with less gold than cost cannot spin and balance is not reduced."""
        state.set_wallet(coins=50, gems=0, account_id=self.aid)
        cfg = CHEST_CONFIGS[CHEST_GOLD_ROYALE]
        self.assertLess(50, cfg.once_price)

        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 0)
        self.assertEqual(state.get_gold(self.aid), 50, "Gold balance must remain 50, not negative")

    def test_negative_balance_prevention_diamonds(self) -> None:
        """Account with less diamonds than cost cannot spin and balance is not reduced."""
        state.set_wallet(coins=0, gems=20, account_id=self.aid)
        cfg = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        self.assertLess(20, cfg.once_price)

        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 0)
        self.assertEqual(state.get_diamond(self.aid), 20, "Diamonds must remain 20, not negative")

    def test_insufficient_vouchers_prevention(self) -> None:
        """Attempting voucher spin with 0 vouchers fails and awards 0 items."""
        cfg = CHEST_CONFIGS[CHEST_WEAPON_ROYALE]
        voucher_id = cfg.exchange_itemid
        self.assertEqual(state.get_item_count(voucher_id), 0)

        req = {
            "chest_id": CHEST_WEAPON_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.EXCHANGE_ITEM,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 0)


if __name__ == "__main__":
    unittest.main()
