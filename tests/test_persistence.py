"""
Test Suite 7: Server Persistence Tests for Free Fire 1.39 Luck Royale.
Verifies:
1. Lucky meter (not_got_num, weekly counts) durability across simulated server restarts.
2. Milestone claim state persistence (prevents duplicate claims after reboot).
3. Inventory items, vouchers, and materials persistence across restarts.
4. Currency (Diamonds & Gold) durability across restarts.
5. Transaction logs and audit trail SQLite persistence.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

SERVER_DIR = str(Path(__file__).resolve().parent.parent)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from core.database import db
from core.player import Player, player_manager
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
)
from handlers.gacha_handler import GachaService, gacha_service
from tests.test_helpers import (
    decode_cs_get_gacha_info_res,
    reset_test_account_state,
)


class TestServerPersistence(unittest.TestCase):
    def setUp(self) -> None:
        self.aid = 10001
        reset_test_account_state(
            account_id=self.aid,
            diamonds=25000,
            gold=250000,
        )

    def test_lucky_meter_persistence_across_restart(self) -> None:
        """Simulate server reboot and verify lucky meters and weekly counters are restored."""
        cid = CHEST_DIAMOND_ROYALE
        # Set specific in-memory state and persist to database
        state_dict = {
            "lottery_count_weekly": 45,
            "exchanged_reward_list": [5, 10, 20],
            "next_free_time": 1780000000,
            "not_got_num": 89,
            "limit_purchase_count_one": 0,
            "limit_purchase_count_ten": 0,
            "first_draw_reward_num": 1,
        }
        db.save_gacha_state(self.aid, cid, state_dict)

        # Simulate complete server restart: create brand-new GachaService with cold memory
        cold_service = GachaService()
        info_bytes = cold_service.get_gacha_info(account_id=self.aid)
        infos = decode_cs_get_gacha_info_res(info_bytes)

        target_info = next((i for i in infos if i["chest_id"] == cid), None)
        self.assertIsNotNone(target_info, "Chest info must be returned by restarted service")
        self.assertEqual(target_info["not_got_num"], 89)
        self.assertEqual(target_info["lottery_count_weekly"], 45)
        self.assertEqual(target_info["next_free_time"], 1780000000)
        self.assertEqual(set(target_info["exchanged_reward_list"]), {5, 10, 20})

    def test_milestone_claim_durability_across_restart(self) -> None:
        """Claimed extra reward milestones persist across restarts and cannot be double-claimed."""
        cid = CHEST_GOLD_ROYALE
        # Seed record with 50 spins and milestone 10 claimed
        rec = {
            "lottery_count_weekly": 50,
            "exchanged_reward_list": [10],
            "next_free_time": 0,
            "not_got_num": 12,
            "limit_purchase_count_one": 0,
            "limit_purchase_count_ten": 0,
            "first_draw_reward_num": 0,
        }
        db.save_gacha_state(self.aid, cid, rec)

        # Cold restart
        cold_service = GachaService()
        # Attempt to claim milestone 10 again
        req = {"chest_id": cid, "condition_num": 10}
        res_bytes = cold_service.exchange_extra_reward(req, account_id=self.aid)

        # Check DB state
        saved = db.get_all_gacha_states(self.aid).get(cid)
        self.assertIsNotNone(saved)
        # Should only have [10] once, no duplicates
        self.assertEqual(saved["exchanged_reward_list"], [10])

    def test_inventory_and_vouchers_persistence_across_restart(self) -> None:
        """Player vouchers and materials persist in SQLite and re-hydrate accurately."""
        # Save specific inventory in DB
        db.save_inventory_item(self.aid, 110100010, 15)  # 15 Gold vouchers
        db.save_inventory_item(self.aid, 110100008, 8)   # 8 Diamond vouchers
        db.save_inventory_item(self.aid, 808000003, 12)  # 12 Evolution stones
        db.save_inventory_item(self.aid, 808000001, 4)   # 4 YinYang blueprints

        # Simulate cold player load from SQLite
        fresh_player = Player(account_id=self.aid)
        loaded = fresh_player.load_from_db()
        self.assertTrue(loaded)

        self.assertEqual(fresh_player.get_item_count(110100010), 15)
        self.assertEqual(fresh_player.get_item_count(110100008), 8)
        self.assertEqual(fresh_player.get_item_count(808000003), 12)
        self.assertEqual(fresh_player.get_item_count(808000001), 4)

    def test_wallet_currency_persistence_across_restart(self) -> None:
        """Wallet gold and diamonds persist in SQLite and re-hydrate accurately."""
        target_gold = 777777
        target_diamonds = 88888
        db.update_wallet(self.aid, gold=target_gold, diamonds=target_diamonds)

        fresh_player = Player(account_id=self.aid)
        fresh_player.load_from_db()

        self.assertEqual(fresh_player.get_gold(), target_gold)
        self.assertEqual(fresh_player.get_diamond(), target_diamonds)

    def test_transactions_and_audit_log_persistence(self) -> None:
        """Spin transactions and audit log records persist in SQLite."""
        # Record a spin transaction
        tx_id = db.record_gacha_transaction(
            account_id=self.aid,
            chest_id=CHEST_DIAMOND_ROYALE,
            gacha_type=1,
            consume_type=3,
            cost_type=2,
            cost_amount=60,
            reward_list=[{"origin_award_id": 800000304, "dest_award_id": 800000304, "num": 1}],
            lucky_before=149,
            lucky_after=0,
            has_big_reward=True,
        )
        self.assertGreater(tx_id, 0)

        # Log an admin audit action
        db.log_action(
            self.aid,
            "QA_PERSISTENCE_TEST",
            "Verified SQLite audit persistence",
            {"test": True},
        )

        # Query back from SQLite directly
        txs = db.get_gacha_transactions(account_id=self.aid, chest_id=CHEST_DIAMOND_ROYALE)
        self.assertGreater(len(txs), 0)
        found_tx = next((t for t in txs if t["trans_id"] == tx_id), None)
        self.assertIsNotNone(found_tx)
        self.assertEqual(found_tx["cost_amount"], 60)
        self.assertTrue(found_tx["has_big_reward"])

        logs = db.get_audit_logs(account_id=self.aid, limit=10)
        found_log = next((l for l in logs if l.get("action_type") == "QA_PERSISTENCE_TEST"), None)
        self.assertIsNotNone(found_log)


if __name__ == "__main__":
    unittest.main()
