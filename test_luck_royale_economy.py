"""
Comprehensive Test Suite for Luck Royale Economy Subsystem (Agent 5: economy_spec)
Covers all 6 required capabilities:
1. Currency deduction (Diamonds CoinType.DIAMOND=1, Gold CoinType.GOLD=2, zero-negative prevention)
2. Machine-compatible voucher deduction (Gold 110100010, Diamond 110100008, Weapon 110100009, Incubator 110100018)
3. Daily free spin cooldown tracking per machine (24h cooldown)
4. Incubator Special Exchange Forge (Blueprints 808000001/808000002 + Evolution Stones 808000003)
5. Token store exchange (FF Tokens 110200001) for cosmetic rewards
6. Double deduction prevention, concurrency safety, and audit trail logging
"""

import os
import sys
import time
import threading
import unittest

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    FREE_COOLDOWN_SECONDS,
    ITEM_BLUEPRINT_JOKER,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
    CoinType,
    ConsumeType,
    CostType,
    LotteryType,
    decode_do_gacha_special_exchange_req,
    decode_get_gacha_special_exchange_desc_req,
    decode_lottery_req,
    encode_do_gacha_special_exchange_res,
    encode_get_gacha_special_exchange_desc_res,
    encode_lottery_res,
)
from handlers.gacha_handler import (
    GachaService,
    EconomyService,
    economy_service,
    gacha_service,
    handle_gacha_request,
)
from handlers.store_handler import store_service


class TestLuckRoyaleEconomy(unittest.TestCase):

    def setUp(self):
        # Generate a unique account ID per test method to ensure complete isolation
        self.account_id = 99000 + int(time.time() * 1000) % 9000 + os.getpid() % 100
        self.service = GachaService()
        self.econ = EconomyService(self.service)
        # Ensure fresh state
        state._ensure_account(self.account_id)
        state.set_wallet(coins=10000, gems=5000, account_id=self.account_id)

    # -----------------------------------------------------------------------
    # Requirement 1: Currency Deduction & Zero-Negative Prevention
    # -----------------------------------------------------------------------
    def test_01_currency_deduction_and_negative_prevention(self):
        aid = self.account_id
        # Verify CoinType constants
        self.assertEqual(int(CoinType.DIAMOND), 1)
        self.assertEqual(int(CoinType.GOLD), 2)

        # Set specific balance
        state.set_wallet(coins=500, gems=100, account_id=aid)
        self.assertEqual(state.get_gold(aid), 500)
        self.assertEqual(state.get_diamond(aid), 100)

        # 1. Successful deduction
        ok, new_gold = state.modify_gold(aid, -300)
        self.assertTrue(ok)
        self.assertEqual(new_gold, 200)
        self.assertEqual(state.get_gold(aid), 200)

        ok, new_dia = state.modify_diamond(aid, -60)
        self.assertTrue(ok)
        self.assertEqual(new_dia, 40)
        self.assertEqual(state.get_diamond(aid), 40)

        # 2. Prevent negative balance (Gold)
        ok, bal = state.modify_gold(aid, -500)
        self.assertFalse(ok)
        self.assertEqual(bal, 200)  # Unchanged
        self.assertEqual(state.get_gold(aid), 200)

        # 3. Prevent negative balance (Diamonds)
        ok, bal = state.modify_diamond(aid, -100)
        self.assertFalse(ok)
        self.assertEqual(bal, 40)   # Unchanged
        self.assertEqual(state.get_diamond(aid), 40)

        # 4. Gacha Money Spin Deduction with Gold Royale (CHEST_GOLD_ROYALE = 5)
        # 1x spin costs 300 gold
        state.modify_gold(aid, 1000)  # Total 1200 gold
        cfg_gold = CHEST_CONFIGS[CHEST_GOLD_ROYALE]
        rec = self.service._get_chest_record(aid, CHEST_GOLD_ROYALE)
        res = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_gold,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.MONEY,
            rec=rec,
            now=int(time.time()),
        )
        self.assertTrue(res.success)
        self.assertEqual(res.cost_type, CostType.GOLD)
        self.assertEqual(res.amount_deducted, 300)
        self.assertEqual(state.get_gold(aid), 900)

        # 5. Gacha Money Spin Deduction with Diamond Royale (CHEST_DIAMOND_ROYALE = 3)
        # 1x spin costs 60 diamonds
        state.modify_diamond(aid, 100)  # Total 140 diamonds
        cfg_dia = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        rec_dia = self.service._get_chest_record(aid, CHEST_DIAMOND_ROYALE)
        res_dia = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_dia,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.MONEY,
            rec=rec_dia,
            now=int(time.time()),
        )
        self.assertTrue(res_dia.success)
        self.assertEqual(res_dia.cost_type, CostType.DIAMOND)
        self.assertEqual(res_dia.amount_deducted, 60)
        self.assertEqual(state.get_diamond(aid), 80)

        # 6. Reject spin when balance insufficient
        state.modify_diamond(aid, -70)  # Total 10 diamonds remaining (needs 60)
        res_fail = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_dia,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.MONEY,
            rec=rec_dia,
            now=int(time.time()),
        )
        self.assertFalse(res_fail.success)
        self.assertEqual(state.get_diamond(aid), 10)  # Balance untouched

    # -----------------------------------------------------------------------
    # Requirement 2: Machine-Compatible Voucher Deduction & Prioritization
    # -----------------------------------------------------------------------
    def test_02_voucher_deduction_and_prioritization(self):
        aid = self.account_id
        # Canonical vouchers:
        # Gold: 110100010, Diamond: 110100008, Weapon: 110100009, Incubator: 110100018
        self.assertEqual(VOUCHER_GOLD_ROYALE, 110100010)
        self.assertEqual(VOUCHER_DIAMOND_ROYALE, 110100008)
        self.assertEqual(VOUCHER_WEAPON_ROYALE, 110100009)
        self.assertEqual(VOUCHER_INCUBATOR, 110100018)

        # Ensure seeded stock
        self.service._ensure_seeded(aid)
        init_dia_v = state.get_item_count(VOUCHER_DIAMOND_ROYALE, account_id=aid)
        init_inc_v = state.get_item_count(VOUCHER_INCUBATOR, account_id=aid)

        # 1. Single spin with Diamond Royale Voucher
        cfg_dia = CHEST_CONFIGS[CHEST_DIAMOND_ROYALE]
        rec_dia = self.service._get_chest_record(aid, CHEST_DIAMOND_ROYALE)
        init_dia = state.get_diamond(aid)

        res = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_dia,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.EXCHANGE_ITEM,
            rec=rec_dia,
            now=int(time.time()),
        )
        self.assertTrue(res.success)
        self.assertEqual(res.cost_type, CostType.VOUCHER)
        self.assertEqual(res.amount_deducted, 1)
        self.assertEqual(state.get_item_count(VOUCHER_DIAMOND_ROYALE, account_id=aid), init_dia_v - 1)
        self.assertEqual(state.get_diamond(aid), init_dia)  # Diamonds untouched!

        # 2. Multi-spin with Incubator Voucher (5 vouchers required for 5x spin)
        cfg_inc = CHEST_CONFIGS[CHEST_INCUBATOR]
        rec_inc = self.service._get_chest_record(aid, CHEST_INCUBATOR)
        res_inc = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_inc,
            gacha_type=LotteryType.SOME,
            consume_type=ConsumeType.EXCHANGE_ITEM,
            rec=rec_inc,
            now=int(time.time()),
        )
        self.assertTrue(res_inc.success)
        self.assertEqual(res_inc.cost_type, CostType.VOUCHER)
        self.assertEqual(res_inc.amount_deducted, 5)
        self.assertEqual(state.get_item_count(VOUCHER_INCUBATOR, account_id=aid), init_inc_v - 5)

        # 3. Smart Priority: when consume_type is NONE, prioritize vouchers over raw currency
        # When cooldown is active (not free), but vouchers are present:
        rec_dia["next_free_time"] = int(time.time()) + 999999  # Free spin not ready
        res_auto = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_dia,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.NONE,
            rec=rec_dia,
            now=int(time.time()),
        )
        self.assertTrue(res_auto.success)
        self.assertEqual(res_auto.cost_type, CostType.VOUCHER)
        self.assertEqual(state.get_item_count(VOUCHER_DIAMOND_ROYALE, account_id=aid), init_dia_v - 2)

        # 4. Fail when vouchers insufficient
        rem_wep = state.get_item_count(VOUCHER_WEAPON_ROYALE, account_id=aid)
        state.consume_item(VOUCHER_WEAPON_ROYALE, rem_wep, account_id=aid)  # Now 0 weapon vouchers
        cfg_wep = CHEST_CONFIGS[CHEST_WEAPON_ROYALE]
        rec_wep = self.service._get_chest_record(aid, CHEST_WEAPON_ROYALE)
        res_wep_fail = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_wep,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.EXCHANGE_ITEM,
            rec=rec_wep,
            now=int(time.time()),
        )
        self.assertFalse(res_wep_fail.success)

    # -----------------------------------------------------------------------
    # Requirement 3: Daily Free Spin Cooldown Tracking Per Machine
    # -----------------------------------------------------------------------
    def test_03_daily_free_spin_cooldown(self):
        aid = self.account_id
        cfg_gold = CHEST_CONFIGS[CHEST_GOLD_ROYALE]
        rec_gold = self.service._get_chest_record(aid, CHEST_GOLD_ROYALE)
        now = int(time.time())

        # Machine starts with next_free_time = 0 -> Free spin allowed!
        rec_gold["next_free_time"] = 0
        res1 = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_gold,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.FREE,
            rec=rec_gold,
            now=now,
        )
        self.assertTrue(res1.success)
        self.assertEqual(res1.cost_type, CostType.FREE)
        self.assertEqual(rec_gold["next_free_time"], now + FREE_COOLDOWN_SECONDS)

        # Immediate repeat free spin during cooldown -> MUST BE REJECTED!
        res2 = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_gold,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.FREE,
            rec=rec_gold,
            now=now + 100,  # Only 100 seconds elapsed
        )
        self.assertFalse(res2.success)

        # After 24 hours (86400 seconds) -> Free spin allowed again!
        future_now = now + FREE_COOLDOWN_SECONDS + 1
        res3 = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_gold,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.FREE,
            rec=rec_gold,
            now=future_now,
        )
        self.assertTrue(res3.success)
        self.assertEqual(rec_gold["next_free_time"], future_now + FREE_COOLDOWN_SECONDS)

        # Free spins not allowed on machines with free_type=0 (e.g. Incubator)
        cfg_inc = CHEST_CONFIGS[CHEST_INCUBATOR]
        rec_inc = self.service._get_chest_record(aid, CHEST_INCUBATOR)
        res_inc = self.econ.validate_and_deduct_cost(
            account_id=aid,
            cfg=cfg_inc,
            gacha_type=LotteryType.ONE,
            consume_type=ConsumeType.FREE,
            rec=rec_inc,
            now=now,
        )
        self.assertFalse(res_inc.success)

    # -----------------------------------------------------------------------
    # Requirement 4: Incubator Special Exchange Forge
    # -----------------------------------------------------------------------
    def test_04_incubator_special_exchange_forge(self):
        aid = self.account_id
        # Material constants
        self.assertEqual(ITEM_BLUEPRINT_YINYANG, 808000001)
        self.assertEqual(ITEM_BLUEPRINT_JOKER, 808000002)
        self.assertEqual(ITEM_EVOLUTION_STONE, 808000003)

        # Target item: YinYang Male Gold Bundle (710000410) requires 3 YinYang Blueprints + 7 Evolution Stones
        target_item = 710000410
        forge_tab = 1

        # Clear existing materials (both canonical and legacy aliases)
        state.consume_item(ITEM_BLUEPRINT_YINYANG, 9999, account_id=aid)
        state.consume_item(808000011, 9999, account_id=aid)
        state.consume_item(ITEM_EVOLUTION_STONE, 9999, account_id=aid)
        state.consume_item(808000001, 9999, account_id=aid)

        # 1. Attempt craft with insufficient materials -> REJECTED
        state.add_item(ITEM_BLUEPRINT_YINYANG, 2, account_id=aid)  # needs 3
        state.add_item(ITEM_EVOLUTION_STONE, 6, account_id=aid)    # needs 7
        res_fail = self.econ.execute_special_exchange(
            account_id=aid,
            forge_tab_id=forge_tab,
            item_id=target_item,
            count=1,
        )
        self.assertFalse(res_fail.success)
        self.assertIn("Insufficient", res_fail.error_message)
        # Verify materials were not consumed
        self.assertEqual(state.get_item_count(ITEM_BLUEPRINT_YINYANG, account_id=aid), 2)
        self.assertEqual(state.get_item_count(ITEM_EVOLUTION_STONE, account_id=aid), 6)

        # 2. Grant sufficient materials and craft successfully
        state.add_item(ITEM_BLUEPRINT_YINYANG, 1, account_id=aid)  # now 3
        state.add_item(ITEM_EVOLUTION_STONE, 1, account_id=aid)    # now 7
        res_ok = self.econ.execute_special_exchange(
            account_id=aid,
            forge_tab_id=forge_tab,
            item_id=target_item,
            count=1,
        )
        self.assertTrue(res_ok.success)
        self.assertEqual(res_ok.item_id, target_item)
        self.assertEqual(res_ok.purchase_times, 1)

        # Verify materials were deducted
        self.assertEqual(state.get_item_count(ITEM_BLUEPRINT_YINYANG, account_id=aid), 0)
        self.assertEqual(state.get_item_count(ITEM_EVOLUTION_STONE, account_id=aid), 0)
        # Verify target bundle was granted
        self.assertEqual(state.get_item_count(target_item, account_id=aid), 1)

        # 3. Check limited purchase limit (limited_purchase_times = 1)
        # Add materials again
        state.add_item(ITEM_BLUEPRINT_YINYANG, 3, account_id=aid)
        state.add_item(ITEM_EVOLUTION_STONE, 7, account_id=aid)
        res_limit = self.econ.execute_special_exchange(
            account_id=aid,
            forge_tab_id=forge_tab,
            item_id=target_item,
            count=1,
        )
        self.assertFalse(res_limit.success)
        self.assertIn("limit exceeded", res_limit.error_message.lower())

        # 4. Craft Joker Tab 2 item: Royal Joker Male (710000414)
        joker_target = 710000414
        joker_tab = 2
        state.add_item(ITEM_BLUEPRINT_JOKER, 3, account_id=aid)
        state.add_item(ITEM_EVOLUTION_STONE, 7, account_id=aid)
        res_joker = self.econ.execute_special_exchange(
            account_id=aid,
            forge_tab_id=joker_tab,
            item_id=joker_target,
            count=1,
        )
        self.assertTrue(res_joker.success)
        self.assertEqual(state.get_item_count(joker_target, account_id=aid), 1)

    # -----------------------------------------------------------------------
    # Requirement 5: Token Store Exchange (FF Tokens 110200001)
    # -----------------------------------------------------------------------
    def test_05_token_store_exchange(self):
        aid = self.account_id
        self.assertEqual(ITEM_FF_TOKEN, 110200001)

        # Clear existing tokens
        state.consume_item(ITEM_FF_TOKEN, 9999, account_id=aid)

        # Commodity 3001: Streetwear Legend Bundle (700000001) costs 40 FF Tokens
        comm_id = 3001
        target_cosmetic = 700000001

        # 1. Attempt token exchange with insufficient tokens (only 20 tokens)
        state.add_item(ITEM_FF_TOKEN, 20, account_id=aid)
        req_fail = {
            "store_id": 1,
            "commodity_id": comm_id,
            "cnt": 1,
            "trans_id": 12345,
        }
        res_bytes_fail = store_service.exchange_purchase(req_fail, account_id=aid)
        # Should not grant cosmetic
        self.assertEqual(state.get_item_count(target_cosmetic, account_id=aid), 0)
        self.assertEqual(state.get_item_count(ITEM_FF_TOKEN, account_id=aid), 20)

        # 2. Add remaining tokens (now 50 tokens, needs 40)
        state.add_item(ITEM_FF_TOKEN, 30, account_id=aid)
        self.assertEqual(state.get_item_count(ITEM_FF_TOKEN, account_id=aid), 50)

        req_ok = {
            "store_id": 1,
            "commodity_id": comm_id,
            "cnt": 1,
            "trans_id": 12346,
        }
        res_bytes_ok = store_service.exchange_purchase(req_ok, account_id=aid)
        self.assertGreater(len(res_bytes_ok), 0)

        # Verify tokens deducted (50 - 40 = 10)
        self.assertEqual(state.get_item_count(ITEM_FF_TOKEN, account_id=aid), 10)
        # Verify cosmetic item granted
        self.assertEqual(state.get_item_count(target_cosmetic, account_id=aid), 1)

    # -----------------------------------------------------------------------
    # Requirement 6: Double Deductions, Concurrency Safety, and Audit Logs
    # -----------------------------------------------------------------------
    def test_06_concurrency_and_audit_history(self):
        aid = 99202
        state._ensure_account(aid)
        state.set_wallet(coins=3000, gems=0, account_id=aid)

        cfg_gold = CHEST_CONFIGS[CHEST_GOLD_ROYALE]
        rec = self.service._get_chest_record(aid, CHEST_GOLD_ROYALE)

        # Threaded concurrent spend requests:
        # Starting with 3000 gold. 20 concurrent threads attempt to spend 300 gold each.
        # Exactly 10 must succeed, and exactly 10 must fail. Final balance must be exactly 0.
        results = []
        lock = threading.Lock()

        def try_spend():
            res = self.econ.validate_and_deduct_cost(
                account_id=aid,
                cfg=cfg_gold,
                gacha_type=LotteryType.ONE,
                consume_type=ConsumeType.MONEY,
                rec=rec,
                now=int(time.time()),
            )
            with lock:
                results.append(res.success)

        threads = [threading.Thread(target=try_spend) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)
        self.assertEqual(successes, 10)
        self.assertEqual(failures, 10)
        self.assertEqual(state.get_gold(aid), 0)
        self.assertGreaterEqual(state.get_gold(aid), 0)

        # Verify Audit Log Trail
        actions = db.get_audit_logs(account_id=aid, limit=50)
        self.assertGreater(len(actions), 0)
        action_names = [a.get("action_type") for a in actions]
        self.assertIn("GACHA_CURRENCY_SPEND", action_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
