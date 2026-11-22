"""
Test Suite 1: Machine Configuration Tests for Free Fire 1.39 Luck Royale.
Verifies:
1. Machine configuration loading and catalog integrity.
2. Standard machines (Diamond Royale, Weapon Royale, Gold Royale, Incubator).
3. Availability, pricing, currencies, vouchers, and drop rules.
4. Handling invalid chest IDs gracefully.
5. Milestone / extra reward configuration.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

SERVER_DIR = str(Path(__file__).resolve().parent.parent)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    CoinType,
    LotteryType,
    RareType,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
)
from handlers.gacha_handler import gacha_service, handle_gacha_request
from tests.test_helpers import (
    MockRequestHandler,
    decode_cs_get_gacha_info_res,
    decode_cs_lottery_res,
)


class TestMachineConfiguration(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = MockRequestHandler()

    def test_standard_machines_exist(self) -> None:
        """Verify all standard Luck Royale machines exist in configuration."""
        expected_ids = {
            CHEST_DIAMOND_ROYALE,
            CHEST_WEAPON_ROYALE,
            CHEST_GOLD_ROYALE,
            CHEST_INCUBATOR,
        }
        actual_ids = set(CHEST_CONFIGS.keys())
        self.assertTrue(expected_ids.issubset(actual_ids), f"Missing machines: {expected_ids - actual_ids}")

    def test_machine_properties(self) -> None:
        """Verify essential properties of each configured machine."""
        for chest_id, cfg in CHEST_CONFIGS.items():
            with self.subTest(chest_id=chest_id):
                self.assertIsInstance(cfg.chest_id, int)
                self.assertIsInstance(cfg.chest_name, str)
                self.assertGreater(len(cfg.chest_name), 0)
                self.assertIn(cfg.coin_type, (CoinType.COINS, CoinType.GEMS, CoinType.NONE))
                self.assertGreater(cfg.once_price, 0)
                self.assertGreater(cfg.ten_price, 0)
                self.assertGreaterEqual(cfg.once_num, 1)
                self.assertGreaterEqual(cfg.ten_num, 1)
                self.assertGreater(cfg.rare_item_max, 0, "Guaranteed drop threshold must be > 0")
                self.assertTrue(len(cfg.items) > 0, "Item pool must not be empty")

    def test_currency_and_voucher_mapping(self) -> None:
        """Verify currency types and voucher item mappings for standard machines."""
        # Gold Royale consumes Coins and Gold Vouchers
        gold_cfg = CHEST_CONFIGS[CHEST_GOLD_ROYALE]
        self.assertEqual(gold_cfg.coin_type, CoinType.COINS)
        self.assertIn(gold_cfg.exchange_itemid, (VOUCHER_GOLD_ROYALE, 110100010))

        # Diamond Royale consumes Gems and Diamond Vouchers
        diamond_cfg = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        self.assertEqual(diamond_cfg.coin_type, CoinType.GEMS)
        self.assertIn(diamond_cfg.exchange_itemid, (VOUCHER_DIAMOND_ROYALE, 110100008))

        # Weapon Royale consumes Gems and Weapon Vouchers
        weapon_cfg = CHEST_CONFIGS[CHEST_WEAPON_ROYALE]
        self.assertEqual(weapon_cfg.coin_type, CoinType.GEMS)
        self.assertIn(weapon_cfg.exchange_itemid, (VOUCHER_WEAPON_ROYALE, 110100009))

        # Incubator consumes Gems and Incubator Vouchers
        incubator_cfg = CHEST_CONFIGS[CHEST_INCUBATOR]
        self.assertEqual(incubator_cfg.coin_type, CoinType.GEMS)
        self.assertIn(incubator_cfg.exchange_itemid, (VOUCHER_INCUBATOR, 110100018))

    def test_item_pools_isolated_and_valid(self) -> None:
        """Verify item pools are populated with valid weights and reward levels."""
        for chest_id, cfg in CHEST_CONFIGS.items():
            rare_found = False
            for item in cfg.items:
                self.assertGreater(item.item_id, 0)
                self.assertGreater(item.item_num, 0)
                self.assertGreater(item.weight, 0)
                self.assertIn(item.reward_level, (RareType.NORMAL, RareType.RARE, RareType.SUPER_RARE))
                if item.reward_level >= RareType.RARE:
                    rare_found = True
            self.assertTrue(rare_found, f"Chest {chest_id} must have at least one rare item in pool")

    def test_milestone_extra_rewards(self) -> None:
        """Verify milestone rewards have increasing thresholds and valid reward configs."""
        for chest_id, cfg in CHEST_CONFIGS.items():
            if cfg.extra_rewards:
                prev_cdt = 0
                for reward in cfg.extra_rewards:
                    self.assertGreater(reward.cdt_value, prev_cdt, "Milestone thresholds must increase")
                    self.assertGreater(reward.reward_id, 0)
                    self.assertGreater(reward.reward_num, 0)
                    prev_cdt = reward.cdt_value

    def test_get_gacha_desc_endpoint(self) -> None:
        """Verify /GetGachaDesc protocol response contains valid bytes."""
        desc_bytes = gacha_service.get_gacha_desc()
        self.assertIsInstance(desc_bytes, bytes)
        self.assertGreater(len(desc_bytes), 0)

        # HTTP routing test
        handled = handle_gacha_request(self.handler, "/GetGachaDesc", "127.0.0.1", b"")
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "CSGetGachaDescRes")

    def test_get_gacha_info_endpoint(self) -> None:
        """Verify /GetGachaInfo protocol response returns status for configured machines."""
        info_bytes = gacha_service.get_gacha_info(account_id=10001)
        self.assertIsInstance(info_bytes, bytes)
        self.assertGreater(len(info_bytes), 0)

        infos = decode_cs_get_gacha_info_res(info_bytes)
        self.assertGreaterEqual(len(infos), 4)
        info_chest_ids = {info["chest_id"] for info in infos}
        self.assertTrue({3, 4, 5, 6}.issubset(info_chest_ids))

        # HTTP routing test
        handled = handle_gacha_request(self.handler, "/GetGachaInfo", "127.0.0.1", b"", account_id=10001)
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "CSGetGachaInfoRes")

    def test_invalid_chest_id_probability(self) -> None:
        """Requesting probability for unknown chest ID returns empty response safely."""
        prob_bytes = gacha_service.get_probability(999999)
        self.assertIsInstance(prob_bytes, bytes)

    def test_invalid_chest_id_purchase(self) -> None:
        """Attempting to spin an unknown chest ID fails safely and awards zero items."""
        req = {
            "chest_id": 999999,
            "gacha_type": LotteryType.ONE,
            "consume_type": 1,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=10001)
        self.assertIsInstance(res_bytes, bytes)
        res = decode_cs_lottery_res(res_bytes)
        self.assertEqual(len(res["lottery_goods"]), 0)


if __name__ == "__main__":
    unittest.main()
