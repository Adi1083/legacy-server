"""
Test Suite 2: Spin Execution Tests for Free Fire 1.39 Luck Royale.
Verifies:
1. Single spin (1x draw) mechanics and counters.
2. Multi-spin (10x / 10+1 draw) mechanics and bonus extra item.
3. Free spin cooldown validation and abuse prevention.
4. Rollback and rejection on insufficient resources.
5. Concurrent spin thread safety (no race conditions, accurate totals).
6. Protocol serialization and HTTP endpoint routing (/PurchaseGacha).
"""

from __future__ import annotations

import concurrent.futures
import os
import sys
import time
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
)
from handlers.gacha_handler import gacha_service, handle_gacha_request
from tests.test_helpers import (
    MockRequestHandler,
    decode_cs_lottery_res,
    encode_cs_lottery_req,
    reset_test_account_state,
)


class TestSpinExecution(unittest.TestCase):
    def setUp(self) -> None:
        self.aid = 10001
        reset_test_account_state(
            account_id=self.aid,
            diamonds=50000,
            gold=500000,
        )
        self.handler = MockRequestHandler()

    def test_single_spin_gold_royale(self) -> None:
        """Single spin draws 1 item and increments weekly lottery count by 1."""
        rec_before = gacha_service._get_chest_record(self.aid, CHEST_GOLD_ROYALE)
        init_weekly = rec_before["lottery_count_weekly"]

        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 1)
        self.assertEqual(res["lottery_count_weekly"], init_weekly + 1)
        self.assertGreater(res["lottery_goods"][0]["dest_award_id"], 0)
        self.assertGreater(res["lottery_goods"][0]["dest_award_num"], 0)

    def test_multi_spin_ten_plus_one_bonus(self) -> None:
        """10x draw on Diamond Royale awards 10 items + 1 bonus extra item (10+1)."""
        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)

        self.assertEqual(len(res["lottery_goods"]), 10)
        self.assertEqual(len(res["extra_one_goods"]), 1, "Diamond Royale 10x spin must award +1 bonus good")
        self.assertEqual(res["lottery_count_weekly"], 11)

    def test_free_spin_cooldown_and_rejection(self) -> None:
        """Free spin sets 24h cooldown; subsequent free spin attempt during cooldown is rejected."""
        req_free = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.FREE,
        }
        now = int(time.time())
        # First free spin should succeed
        res_bytes1 = gacha_service.purchase_gacha(req_free, account_id=self.aid)
        res1 = decode_cs_lottery_res(res_bytes1)
        self.assertEqual(len(res1["lottery_goods"]), 1)
        self.assertGreaterEqual(res1["next_free_time"], now + 86000)

        # Immediate second free spin must fail
        res_bytes2 = gacha_service.purchase_gacha(req_free, account_id=self.aid)
        res2 = decode_cs_lottery_res(res_bytes2)
        self.assertEqual(len(res2["lottery_goods"]), 0, "Free spin during cooldown must award 0 items")

    def test_free_spin_multi_rejected(self) -> None:
        """Attempting a multi-spin (10x) with ConsumeType.FREE must be rejected."""
        req = {
            "chest_id": CHEST_GOLD_ROYALE,
            "gacha_type": LotteryType.SOME,
            "consume_type": ConsumeType.FREE,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)
        self.assertEqual(len(res["lottery_goods"]), 0)

    def test_rollback_on_insufficient_currency(self) -> None:
        """When account has 0 diamonds and 0 vouchers, Diamond Royale spin fails with no items awarded."""
        reset_test_account_state(
            account_id=self.aid,
            diamonds=0,
            gold=0,
            vouchers={},
        )
        req = {
            "chest_id": CHEST_DIAMOND_ROYALE,
            "gacha_type": LotteryType.ONE,
            "consume_type": ConsumeType.MONEY,
        }
        res_bytes = gacha_service.purchase_gacha(req, account_id=self.aid)
        res = decode_cs_lottery_res(res_bytes)
        self.assertEqual(len(res["lottery_goods"]), 0)
        self.assertEqual(state.get_diamond(self.aid), 0)

    def test_concurrent_spins_thread_safety(self) -> None:
        """Concurrent spins across 10 threads do not race and correctly increment counters."""
        reset_test_account_state(
            account_id=self.aid,
            diamonds=500000,
            gold=5000000,
        )
        rec_before = gacha_service._get_chest_record(self.aid, CHEST_GOLD_ROYALE)
        init_weekly = rec_before["lottery_count_weekly"]

        def do_spin():
            req = {
                "chest_id": CHEST_GOLD_ROYALE,
                "gacha_type": LotteryType.ONE,
                "consume_type": ConsumeType.MONEY,
            }
            return gacha_service.purchase_gacha(req, account_id=self.aid)

        num_spins = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(do_spin) for _ in range(num_spins)]
            results = [f.result() for f in futures]

        for r_bytes in results:
            res = decode_cs_lottery_res(r_bytes)
            self.assertEqual(len(res["lottery_goods"]), 1)

        rec_after = gacha_service._get_chest_record(self.aid, CHEST_GOLD_ROYALE)
        self.assertEqual(rec_after["lottery_count_weekly"], init_weekly + num_spins)

    def test_http_endpoint_purchase_gacha_routing(self) -> None:
        """Verify /PurchaseGacha endpoint correctly decodes request and responds with CSLotteryRes."""
        req_bytes = encode_cs_lottery_req(
            chest_id=CHEST_GOLD_ROYALE,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.MONEY,
        )
        handled = handle_gacha_request(
            self.handler,
            "/PurchaseGacha",
            "127.0.0.1",
            req_bytes,
            account_id=self.aid,
        )
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "CSLotteryRes")
        res = decode_cs_lottery_res(self.handler.proto_calls[-1][1])
        self.assertGreaterEqual(len(res["lottery_goods"]), 1)


if __name__ == "__main__":
    unittest.main()
