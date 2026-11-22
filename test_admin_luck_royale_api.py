#!/usr/bin/env python3
"""
Comprehensive automated test suite for Free Fire 1.39 Luck Royale Admin REST API.
Verifies all 9 core administrative endpoints under /api/admin/luck-royale/:
1. /overview
2. /machines (CRUD + toggle + duplicate)
3. /reward-pools (GET + POST + PUT + DELETE + item search)
4. /meters (GET + PUT machine caps and user meters)
5. /currencies-vouchers (GET + grant + deduct with negative prevention)
6. /exchange (GET + POST + PUT + DELETE Incubator forge recipes)
7. /events-banners (GET + banner assignment + event scheduling)
8. /accounts/<aid> (GET inspection + POST manual adjustments)
9. /transactions (GET with rich filters + POST manual transaction)
10. Authentication & security tests (Bearer token, X-Admin-Token, 401 handling)
"""

import io
import json
import os
import sys
import unittest
from typing import Any, Dict, Optional
from urllib.parse import urlparse

# Ensure server module is importable
server_dir = os.path.dirname(os.path.abspath(__file__))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.admin_luck_royale_api import (
    ADMIN_API_TOKEN,
    admin_mgr,
    handle_admin_luck_royale_request,
)
import proto.gacha_models as gm


class MockHTTPHandler:
    """Mock BaseHTTPRequestHandler capturing responses."""

    def __init__(self, headers: Optional[Dict[str, str]] = None) -> None:
        self.headers = headers or {}
        self.status = 200
        self.response_headers: Dict[str, str] = {}
        self.response_bytes = b""
        self.response_json: Optional[Dict[str, Any]] = None

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers[key] = value

    def end_headers(self) -> None:
        pass

    def send_bytes(self, data: bytes, status: int = 200, content_type: str = "application/octet-stream") -> None:
        self.status = status
        self.response_bytes = data

    def send_json(self, data: Any, status: int = 200) -> None:
        self.status = status
        self.response_json = data
        self.response_bytes = json.dumps(data).encode("utf-8")

    def send_text(self, text: str, status: int = 200, content_type: str = "text/plain") -> None:
        self.status = status
        self.response_bytes = text.encode("utf-8")


def call_api(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Dict[str, Any]]:
    parsed = urlparse(path)
    raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
    h = MockHTTPHandler(headers=headers)
    handled = handle_admin_luck_royale_request(
        handler=h,
        method=method,
        path=parsed.path,
        query_string=parsed.query,
        raw_body=raw_body,
    )
    if not handled:
        return 404, {"ok": False, "error": "Endpoint not handled"}
    return h.status, h.response_json or {}


class TestLuckRoyaleAdminAPI(unittest.TestCase):
    """Full test suite covering all 9 admin endpoints and edge cases."""

    def setUp(self) -> None:
        # Pre-seed test account 10001
        self.aid = DEFAULT_ACCOUNT_ID
        state.grant_currency(coins=100000, gems=50000, account_id=self.aid)

    # -----------------------------------------------------------------------
    # 0. Authentication Tests
    # -----------------------------------------------------------------------

    def test_00_auth_bearer_and_custom_header(self) -> None:
        # Valid Bearer token
        status, res = call_api("GET", "/api/admin/luck-royale/auth/check", headers={"Authorization": f"Bearer {ADMIN_API_TOKEN}"})
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        self.assertTrue(res.get("authenticated"))

        # Valid X-Admin-Token
        status, res = call_api("GET", "/api/admin/luck-royale/auth/check", headers={"X-Admin-Token": ADMIN_API_TOKEN})
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))

        # Invalid token must fail with 401
        status, res = call_api("GET", "/api/admin/luck-royale/overview", headers={"Authorization": "Bearer bad-token-123"})
        self.assertEqual(status, 401)
        self.assertFalse(res.get("ok"))
        self.assertIn("Invalid admin token", res.get("error", ""))

    # -----------------------------------------------------------------------
    # 1. Overview Endpoint Tests
    # -----------------------------------------------------------------------

    def test_01_overview(self) -> None:
        status, res = call_api("GET", "/api/admin/luck-royale/overview")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        self.assertIn("summary", res)
        summary = res["summary"]
        self.assertIn("total_spins", summary)
        self.assertIn("diamonds_burned", summary)
        self.assertIn("gold_burned", summary)
        self.assertIn("active_machines_count", summary)
        self.assertIn("active_machines", res)
        self.assertGreater(len(res["active_machines"]), 0)

    # -----------------------------------------------------------------------
    # 2. Machines Endpoint Tests (List, Get, Create, Toggle, Duplicate, Update, Delete)
    # -----------------------------------------------------------------------

    def test_02_machines_crud(self) -> None:
        # 1. List machines
        status, res = call_api("GET", "/api/admin/luck-royale/machines")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        machines = res.get("machines", [])
        self.assertGreaterEqual(len(machines), 4)

        # 2. Get specific machine (Diamond Royale = 3)
        status, res = call_api("GET", "/api/admin/luck-royale/machines/3")
        self.assertEqual(status, 200)
        self.assertEqual(res["machine"]["chest_id"], 3)
        self.assertEqual(res["machine"]["coin_type"], 2)  # Diamonds

        # 3. Create machine validation failures
        status, res = call_api("POST", "/api/admin/luck-royale/machines", body={
            "chest_id": 3,  # Already exists
            "chest_name": "Duplicate ID Test",
        })
        self.assertEqual(status, 400)
        self.assertIn("already exists", res.get("error", ""))

        # 4. Create new custom machine (chest_id 999)
        new_machine_payload = {
            "chest_id": 999,
            "chest_name": "Test Royale 999",
            "coin_type": 2,
            "once_price": 50,
            "ten_price": 500,
            "rare_item_max": 120,
            "must_drop": True,
            "enabled": True,
        }
        status, res = call_api("POST", "/api/admin/luck-royale/machines", body=new_machine_payload)
        self.assertEqual(status, 201)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res["machine"]["chest_id"], 999)

        # 5. Toggle machine disabled/enabled
        status, res = call_api("POST", "/api/admin/luck-royale/machines/999/toggle", body={"enabled": False})
        self.assertEqual(status, 200)
        self.assertFalse(res.get("enabled"))

        # Re-fetch machine and verify disabled
        status, res = call_api("GET", "/api/admin/luck-royale/machines/999")
        self.assertFalse(res["machine"]["enabled"])

        # 6. Duplicate machine (999 -> 998)
        status, res = call_api("POST", "/api/admin/luck-royale/machines/duplicate", body={
            "source_chest_id": 999,
            "new_chest_id": 998,
            "new_chest_name": "Clone Royale 998",
        })
        self.assertEqual(status, 201)
        self.assertEqual(res["machine"]["chest_id"], 998)

        # 7. Update machine (change once_price to 80)
        status, res = call_api("PUT", "/api/admin/luck-royale/machines/998", body={
            "once_price": 80,
            "ten_price": 750,
            "rare_item_max": 200,
        })
        self.assertEqual(status, 200)
        self.assertEqual(res["machine"]["once_price"], 80)
        self.assertEqual(res["machine"]["rare_item_max"], 200)

        # 8. Delete test machines (clean up)
        status, res = call_api("DELETE", "/api/admin/luck-royale/machines/999")
        self.assertEqual(status, 200)
        status, res = call_api("DELETE", "/api/admin/luck-royale/machines/998")
        self.assertEqual(status, 200)

        # Verify 999 no longer exists
        status, res = call_api("GET", "/api/admin/luck-royale/machines/999")
        self.assertEqual(status, 404)

    # -----------------------------------------------------------------------
    # 3. Reward Pools Tests (List, Search Helper, Add Item, Update, Remove)
    # -----------------------------------------------------------------------

    def test_03_reward_pools(self) -> None:
        # 1. Search helper
        status, res = call_api("GET", "/api/admin/luck-royale/reward-pools?q=Dragon")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        items = res.get("items", [])
        self.assertTrue(any("Dragon" in it["name"] for it in items))

        # 2. Get machine pool (Diamond Royale = 3)
        status, res = call_api("GET", "/api/admin/luck-royale/reward-pools?chest_id=3")
        self.assertEqual(status, 200)
        self.assertEqual(res["chest_id"], 3)
        initial_count = len(res["items"])

        # 3. Add new item to Diamond Royale pool
        test_item_id = 907001615  # AWM Cheetah
        status, res = call_api("POST", "/api/admin/luck-royale/reward-pools", body={
            "chest_id": 3,
            "item_id": test_item_id,
            "item_num": 1,
            "reward_level": 2,  # Super Rare
            "weight": 15,
        })
        self.assertEqual(status, 201)
        self.assertEqual(res["item"]["item_id"], test_item_id)
        self.assertEqual(res["item"]["weight"], 15)

        # 4. Update item weight
        status, res = call_api("PUT", "/api/admin/luck-royale/reward-pools", body={
            "chest_id": 3,
            "item_id": test_item_id,
            "weight": 25,
            "reward_level": 1,
        })
        self.assertEqual(status, 200)
        self.assertEqual(res["item"]["weight"], 25)

        # 5. Remove item from pool
        status, res = call_api("DELETE", "/api/admin/luck-royale/reward-pools", body={
            "chest_id": 3,
            "item_id": test_item_id,
        })
        self.assertEqual(status, 200)

        # Verify pool count returned to initial
        status, res = call_api("GET", "/api/admin/luck-royale/reward-pools?chest_id=3")
        self.assertEqual(len(res["items"]), initial_count)

    # -----------------------------------------------------------------------
    # 4. Lucky Meters Tests (Machine caps + User meters)
    # -----------------------------------------------------------------------

    def test_04_lucky_meters(self) -> None:
        # 1. Get meters
        status, res = call_api("GET", f"/api/admin/luck-royale/meters?chest_id=3&account_id={self.aid}")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        self.assertEqual(len(res["meters"]), 1)
        m = res["meters"][0]
        self.assertEqual(m["chest_id"], 3)
        self.assertIn("rare_item_max", m)
        self.assertIn("current_user_meter", m)

        # 2. Adjust machine meter cap and user's current luck meter
        status, res = call_api("PUT", "/api/admin/luck-royale/meters", body={
            "chest_id": 3,
            "rare_item_max": 180,
            "account_id": self.aid,
            "not_got_num": 175,
        })
        self.assertEqual(status, 200)

        # Re-fetch and verify user meter = 175, cap = 180
        status, res = call_api("GET", f"/api/admin/luck-royale/meters?chest_id=3&account_id={self.aid}")
        m = res["meters"][0]
        self.assertEqual(m["rare_item_max"], 180)
        self.assertEqual(m["current_user_meter"], 175)
        self.assertEqual(m["spins_to_guaranteed"], 5)

    # -----------------------------------------------------------------------
    # 5. Currencies & Vouchers Tests (Grant, Deduct, Negative Prevention)
    # -----------------------------------------------------------------------

    def test_05_currencies_and_vouchers(self) -> None:
        # 1. Portfolio inspection
        status, res = call_api("GET", f"/api/admin/luck-royale/currencies-vouchers?account_id={self.aid}")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        init_dia = res["diamonds"]
        init_gold = res["gold"]

        # 2. Grant Diamonds
        status, res = call_api("POST", "/api/admin/luck-royale/currencies-vouchers", body={
            "account_id": self.aid,
            "action": "grant",
            "currency_type": "diamonds",
            "amount": 5000,
            "reason": "Admin test grant",
        })
        self.assertEqual(status, 200)
        self.assertEqual(res["wallet_and_vouchers"]["diamonds"], init_dia + 5000)

        # 3. Deduct Diamonds
        status, res = call_api("POST", "/api/admin/luck-royale/currencies-vouchers", body={
            "account_id": self.aid,
            "action": "deduct",
            "currency_type": "diamonds",
            "amount": 2000,
            "reason": "Admin test deduct",
        })
        self.assertEqual(status, 200)
        self.assertEqual(res["wallet_and_vouchers"]["diamonds"], init_dia + 3000)

        # 4. Negative Balance Prevention: Attempt to deduct more than balance
        excess_amt = res["wallet_and_vouchers"]["diamonds"] + 1000000
        status, res = call_api("POST", "/api/admin/luck-royale/currencies-vouchers", body={
            "account_id": self.aid,
            "action": "deduct",
            "currency_type": "diamonds",
            "amount": excess_amt,
        })
        self.assertEqual(status, 400)
        self.assertFalse(res.get("ok"))
        self.assertIn("Insufficient diamond balance", res.get("error", ""))

        # 5. Grant Vouchers (Diamond Royale Voucher = 110100008)
        status, res = call_api("POST", "/api/admin/luck-royale/currencies-vouchers", body={
            "account_id": self.aid,
            "action": "grant",
            "currency_type": "voucher",
            "voucher_name": "diamond_royale",
            "amount": 25,
            "reason": "Reward drop",
        })
        self.assertEqual(status, 200)
        vcount = res["wallet_and_vouchers"]["vouchers"]["diamond_royale_voucher"]["count"]
        self.assertGreaterEqual(vcount, 25)

        # 6. Deduct Vouchers
        status, res = call_api("POST", "/api/admin/luck-royale/currencies-vouchers", body={
            "account_id": self.aid,
            "action": "deduct",
            "currency_type": "voucher",
            "item_id": 110100008,
            "amount": 5,
        })
        self.assertEqual(status, 200)
        new_vcount = res["wallet_and_vouchers"]["vouchers"]["diamond_royale_voucher"]["count"]
        self.assertEqual(new_vcount, vcount - 5)

    # -----------------------------------------------------------------------
    # 6. Exchange Systems Tests (Incubator Forge Recipes)
    # -----------------------------------------------------------------------

    def test_06_exchange(self) -> None:
        # 1. List special exchanges
        status, res = call_api("GET", "/api/admin/luck-royale/exchange")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        ex_list = res.get("special_exchanges", [])
        self.assertGreater(len(ex_list), 0)

        # 2. Create new exchange recipe
        test_recipe = {
            "forge_tab_id": 99,
            "tab_name": "Special Test Forge",
            "item_id": 710000410,
            "item_num": 1,
            "limited_purchase_times": 3,
            "exchange_items": [
                {"award_id": 808000001, "award_num": 2},  # Blueprint
                {"award_id": 808000003, "award_num": 5},  # Stones
            ],
            "reward_level": 2,
        }
        status, res = call_api("POST", "/api/admin/luck-royale/exchange", body=test_recipe)
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))

        # 3. Delete exchange recipe
        status, res = call_api("DELETE", "/api/admin/luck-royale/exchange", body={
            "forge_tab_id": 99,
            "item_id": 710000410,
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))

    # -----------------------------------------------------------------------
    # 7. Events & Banners Tests
    # -----------------------------------------------------------------------

    def test_07_events_and_banners(self) -> None:
        # 1. Get events & banners
        status, res = call_api("GET", "/api/admin/luck-royale/events-banners")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        self.assertIn("available_banners", res)
        self.assertIn("machine_banners", res)

        # 2. Assign banner to machine
        status, res = call_api("POST", "/api/admin/luck-royale/events-banners", body={
            "action": "assign_banner",
            "chest_id": 3,
            "banner_file": "UI_Lottery_Poster_P.png",
        })
        self.assertEqual(status, 200)

        # 3. Schedule rate-up event
        status, res = call_api("POST", "/api/admin/luck-royale/events-banners", body={
            "chest_id": 3,
            "title": "2x Magic Cube Drop Weekend",
            "discount_percent": 30,
            "rate_up_multiplier": 2.0,
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res["event"]["discount_percent"], 30)

    # -----------------------------------------------------------------------
    # 8. Account Inspector Tests
    # -----------------------------------------------------------------------

    def test_08_account_inspector_and_adjustment(self) -> None:
        # 1. Inspect account
        status, res = call_api("GET", f"/api/admin/luck-royale/accounts/{self.aid}")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res["account_id"], self.aid)
        self.assertIn("wallet_and_vouchers", res)
        self.assertIn("lucky_meters", res)

        # 2. Adjust account lucky meter and reset free cooldown
        status, res = call_api("POST", f"/api/admin/luck-royale/accounts/{self.aid}", body={
            "chest_id": 3,
            "not_got_num": 149,
            "next_free_time": 0,
            "lottery_count_weekly": 50,
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))

        # Verify adjustment took effect
        status, res = call_api("GET", f"/api/admin/luck-royale/accounts/{self.aid}")
        dia_meter = next((m for m in res["lucky_meters"] if m["chest_id"] == 3), None)
        self.assertIsNotNone(dia_meter)
        self.assertEqual(dia_meter["not_got_num"], 149)
        self.assertEqual(dia_meter["next_free_time"], 0)
        self.assertEqual(dia_meter["lottery_count_weekly"], 50)

    # -----------------------------------------------------------------------
    # 9. Transactions Tests (Rich Filters & Manual Record)
    # -----------------------------------------------------------------------

    def test_09_transactions(self) -> None:
        # 1. Record manual test transaction
        test_tx_payload = {
            "account_id": self.aid,
            "chest_id": 3,
            "gacha_type": 2,  # Multi-spin
            "consume_type": 3,  # Money
            "cost_type": 2,  # Gems
            "cost_amount": 600,
            "lucky_before": 100,
            "lucky_after": 110,
            "has_big_reward": True,
            "reward_list": [
                {"origin_award_id": 800000304, "origin_award_num": 1, "is_rare": True},
            ],
        }
        status, res = call_api("POST", "/api/admin/luck-royale/transactions", body=test_tx_payload)
        self.assertEqual(status, 201)
        self.assertTrue(res.get("ok"))
        tx_id = res.get("trans_id")
        self.assertGreater(tx_id, 0)

        # 2. Query transactions with filters
        status, res = call_api("GET", f"/api/admin/luck-royale/transactions?account_id={self.aid}&chest_id=3&limit=10")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("ok"))
        txs = res.get("transactions", [])
        self.assertGreater(len(txs), 0)
        matching = [t for t in txs if t["trans_id"] == tx_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["cost_amount"], 600)
        self.assertTrue(matching[0]["has_big_reward"])

    # -----------------------------------------------------------------------
    # 10. Audit Logging Verification
    # -----------------------------------------------------------------------

    def test_10_audit_logging_integrity(self) -> None:
        audit_entries = db.get_audit_logs(limit=20)
        self.assertGreater(len(audit_entries), 0)
        admin_actions = [a["action_type"] for a in audit_entries if "ADMIN_LUCK_ROYALE" in a["action_type"]]
        self.assertGreater(len(admin_actions), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
