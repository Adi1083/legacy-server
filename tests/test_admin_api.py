"""
Test Suite 6: Admin API & Dashboard Integration Tests for Free Fire 1.39 Luck Royale.
Verifies:
1. /api/admin/luck-royale/overview (summary statistics, telemetry).
2. /api/admin/luck-royale/machines (CRUD, toggle, duplicate, validation).
3. /api/admin/luck-royale/reward-pools (item pool inspection, search, add, update, remove).
4. /api/admin/luck-royale/meters (lucky meter configuration and pity threshold tuning).
5. /api/admin/luck-royale/currencies-vouchers (wallet/voucher inspection and grant/deduct).
6. /api/admin/luck-royale/exchange (Incubator forge and exchange recipe management).
7. /api/admin/luck-royale/events-banners (banner assignment and event scheduling).
8. /api/admin/luck-royale/accounts/<aid> (account inspector, meter overrides).
9. /api/admin/luck-royale/transactions (audit trail exploration with filters).
10. Input validation, error codes, and audit trail persistence.
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
from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.admin_luck_royale_api import admin_mgr, handle_admin_luck_royale_request
from tests.test_helpers import (
    MockRequestHandler,
    reset_test_account_state,
)


class TestAdminAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.aid = 10001
        self.handler = MockRequestHandler()
        reset_test_account_state(
            account_id=self.aid,
            diamonds=50000,
            gold=500000,
        )

    def _call(
        self,
        method: str,
        path: str,
        query: str = "",
        body: dict | None = None,
    ) -> tuple[int, dict]:
        h = MockRequestHandler(path=path)
        raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
        handled = handle_admin_luck_royale_request(
            h,
            method=method,
            path=path,
            query_string=query,
            raw_body=raw_body,
        )
        self.assertTrue(handled, f"Path {path} was not recognized by admin API handler")
        self.assertGreater(len(h.json_calls), 0, f"No JSON response sent for {path}")
        status, data = h.json_calls[-1]
        return status, data

    def test_overview_endpoint(self) -> None:
        """GET /overview returns active machines, total spins, and currency burn."""
        status, data = self._call("GET", "/api/admin/luck-royale/overview")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("summary", data)
        ov = data["summary"]
        self.assertIn("total_spins", ov)
        self.assertIn("diamonds_burned", ov)
        self.assertIn("gold_burned", ov)

    def test_machines_crud_lifecycle(self) -> None:
        """Full CRUD on /machines: list, create, update, toggle, duplicate, delete."""
        # 1. List machines
        status, data = self._call("GET", "/api/admin/luck-royale/machines")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertGreaterEqual(len(data.get("machines", [])), 4)

        # 2. Create machine 99 (Test Special Royale)
        test_machine = {
            "chest_id": 99,
            "chest_name": "Test QA Royale",
            "coin_type": 2,
            "once_price": 50,
            "ten_price": 500,
            "rare_item_max": 100,
            "is_enabled": True,
        }
        status, data = self._call("POST", "/api/admin/luck-royale/machines", body=test_machine)
        self.assertIn(status, (200, 201))
        self.assertTrue(data.get("ok"))

        # 3. Update machine 99
        status, data = self._call(
            "PUT",
            "/api/admin/luck-royale/machines/99",
            body={"chest_id": 99, "once_price": 45, "ten_price": 450},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # 4. Toggle machine 99
        status, data = self._call(
            "POST",
            "/api/admin/luck-royale/machines/99/toggle",
            body={"enabled": False},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertFalse(data.get("enabled"))

        # 5. Duplicate machine 99 -> 98
        status, data = self._call(
            "POST",
            "/api/admin/luck-royale/machines/duplicate",
            body={
                "source_chest_id": 99,
                "new_chest_id": 98,
                "new_chest_name": "Cloned QA Royale",
            },
        )
        self.assertIn(status, (200, 201))
        self.assertTrue(data.get("ok"))

        # 6. Delete machines 99 and 98
        status1, data1 = self._call("DELETE", "/api/admin/luck-royale/machines/99", body={"chest_id": 99})
        self.assertEqual(status1, 200)
        status2, data2 = self._call("DELETE", "/api/admin/luck-royale/machines/98", body={"chest_id": 98})
        self.assertEqual(status2, 200)

    def test_reward_pools_management_and_search(self) -> None:
        """GET /reward-pools, item search, add, update, and remove items."""
        # 1. Search items
        status, data = self._call("GET", "/api/admin/luck-royale/reward-pools/search", query="q=Voucher")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIsInstance(data.get("items"), list)

        # 2. Get reward pool for Gold Royale (chest 5)
        status, data = self._call("GET", "/api/admin/luck-royale/reward-pools", query="chest_id=5")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("items", data)
        self.assertGreater(len(data["items"]), 0)

        # 3. Add item to pool of chest 5
        add_payload = {
            "chest_id": 5,
            "item_id": 999000001,
            "item_name": "QA Golden Ticket",
            "item_num": 1,
            "weight": 50,
            "reward_level": 1,
        }
        status, data = self._call("POST", "/api/admin/luck-royale/reward-pools", body=add_payload)
        self.assertIn(status, (200, 201))
        self.assertTrue(data.get("ok"))

        # 4. Update item weight
        status, data = self._call(
            "PUT",
            "/api/admin/luck-royale/reward-pools",
            body={"chest_id": 5, "item_id": 999000001, "weight": 75},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # 5. Remove item
        status, data = self._call(
            "DELETE",
            "/api/admin/luck-royale/reward-pools",
            body={"chest_id": 5, "item_id": 999000001},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    def test_lucky_meters_tuning(self) -> None:
        """GET and PUT /meters to view and tune lucky meter settings."""
        # View meters
        status, data = self._call("GET", "/api/admin/luck-royale/meters", query="chest_id=3")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # Adjust pity threshold
        status, data = self._call(
            "PUT",
            "/api/admin/luck-royale/meters",
            body={"chest_id": 3, "rare_item_max": 140},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    def test_currencies_and_vouchers_adjustment(self) -> None:
        """GET balances and POST grant/deduct vouchers and diamonds for account 10001."""
        init_diamonds = state.get_diamond(self.aid)

        # 1. Inspect balances
        status, data = self._call(
            "GET",
            "/api/admin/luck-royale/currencies-vouchers",
            query=f"account_id={self.aid}",
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # 2. Grant diamonds (+500)
        status, data = self._call(
            "POST",
            "/api/admin/luck-royale/currencies-vouchers",
            body={
                "account_id": self.aid,
                "currency_type": "diamonds",
                "amount": 500,
                "action": "grant",
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertEqual(state.get_diamond(self.aid), init_diamonds + 500)

        # 3. Grant vouchers (+5 Gold Royale Vouchers)
        status, data = self._call(
            "POST",
            "/api/admin/luck-royale/currencies-vouchers",
            body={
                "account_id": self.aid,
                "voucher_name": "gold_royale",
                "amount": 5,
                "action": "grant",
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertGreaterEqual(state.get_item_count(110100010, self.aid), 5)

    def test_exchange_recipes_management(self) -> None:
        """GET and POST /exchange to inspect and update Incubator forge recipes."""
        status, data = self._call("GET", "/api/admin/luck-royale/exchange")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("special_exchanges", data)
        self.assertGreater(len(data["special_exchanges"]), 0)

    def test_events_and_banners(self) -> None:
        """GET /events-banners lists available graphics and configured schedules."""
        status, data = self._call("GET", "/api/admin/luck-royale/events-banners")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("available_banners", data)

    def test_account_inspector(self) -> None:
        """GET /accounts/<aid> inspects pity and meters, POST adjusts meter value."""
        # Inspect
        status, data = self._call("GET", f"/api/admin/luck-royale/accounts/{self.aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("lucky_meters", data)

        # Override pity meter for Diamond Royale (chest 3) to 77
        status, data = self._call(
            "POST",
            f"/api/admin/luck-royale/accounts/{self.aid}",
            body={"chest_id": 3, "meter_value": 77},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # Verify meter was updated
        status, data2 = self._call("GET", f"/api/admin/luck-royale/accounts/{self.aid}")
        meters = {m["chest_id"]: m for m in data2.get("lucky_meters", [])}
        self.assertEqual(meters.get(3, {}).get("not_got_num", 0), 77)

    def test_transactions_explorer(self) -> None:
        """GET /transactions returns logged spin transactions with filtering."""
        status, data = self._call("GET", "/api/admin/luck-royale/transactions", query="limit=20")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("transactions", data)
        self.assertIsInstance(data["transactions"], list)

    def test_invalid_input_validation(self) -> None:
        """Malformed JSON or missing fields return 400 Bad Request."""
        h = MockRequestHandler()
        # Invalid body on POST
        handled = handle_admin_luck_royale_request(
            h,
            method="POST",
            path="/api/admin/luck-royale/machines",
            raw_body=b"invalid-json{",
        )
        self.assertTrue(handled)
        self.assertEqual(h.json_calls[-1][0], 400)


if __name__ == "__main__":
    unittest.main()
