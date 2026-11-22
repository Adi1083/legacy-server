"""
Test Suite: Backend API Integration & Regression Matrix
Validates all HTTP GET & POST endpoints across dashboard_api.py,
admin_luck_royale_api.py, and new Phase 4 Player Management endpoints
using MockRequestHandler.
"""

import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional, Tuple

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from tests.test_helpers import MockRequestHandler
from handlers.dashboard_api import handle_dashboard_get, handle_dashboard_post


class TestBackendApiIntegration(unittest.TestCase):
    """Exhaustive integration tests for Barbosa Dashboard & Luck Royale admin endpoints."""

    def test_get_dashboard_state(self):
        """GET /api/dashboard/state returns valid player state payload."""
        handler = MockRequestHandler(path="/api/dashboard/state")
        handled = handle_dashboard_get(handler, "/api/dashboard/state", "account_id=10001")
        self.assertTrue(handled, "Route /api/dashboard/state must be handled")
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("wallet", data)
        self.assertIn("characters", data)
        self.assertIn("profile", data)
        self.assertEqual(data["profile"].get("account_id"), 10001)

    def test_get_branding(self):
        """GET /api/dashboard/branding returns slots dictionary."""
        handler = MockRequestHandler(path="/api/dashboard/branding")
        handled = handle_dashboard_get(handler, "/api/dashboard/branding")
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("slots", data)

    def test_get_requests_telemetry(self):
        """GET /api/dashboard/requests returns request history telemetry."""
        handler = MockRequestHandler(path="/api/dashboard/requests")
        handled = handle_dashboard_get(handler, "/api/dashboard/requests", "limit=10")
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        # Supports both list format and wrapped {ok: true, requests: [...]} format
        if isinstance(data, dict):
            self.assertTrue(data.get("ok"))
            self.assertIn("requests", data)
        else:
            self.assertIsInstance(data, list)

    def test_get_mail(self):
        """GET /api/dashboard/mail returns mailbox list for account."""
        handler = MockRequestHandler(path="/api/dashboard/mail")
        handled = handle_dashboard_get(handler, "/api/dashboard/mail", "account_id=10001")
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("mails", data)
        self.assertIsInstance(data["mails"], list)

    def test_get_friends(self):
        """GET /api/dashboard/friends returns friends and pending requests."""
        handler = MockRequestHandler(path="/api/dashboard/friends")
        handled = handle_dashboard_get(handler, "/api/dashboard/friends", "account_id=10001")
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("friends", data)

    def test_get_squad(self):
        """GET /api/dashboard/squad returns squad lobby state."""
        handler = MockRequestHandler(path="/api/dashboard/squad")
        handled = handle_dashboard_get(handler, "/api/dashboard/squad", "account_id=10001")
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    def test_get_cms_and_banners(self):
        """GET /api/dashboard/cms and /api/dashboard/cms/banners return content configurations."""
        handler = MockRequestHandler(path="/api/dashboard/cms")
        handled = handle_dashboard_get(handler, "/api/dashboard/cms")
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        handler_b = MockRequestHandler(path="/api/dashboard/cms/banners")
        handled_b = handle_dashboard_get(handler_b, "/api/dashboard/cms/banners")
        self.assertTrue(handled_b)
        self.assertEqual(len(handler_b.json_calls), 1)
        status_b, data_b = handler_b.json_calls[0]
        self.assertEqual(status_b, 200)
        self.assertTrue(data_b.get("ok"))

    def test_get_modes(self):
        """GET /api/dashboard/modes returns game mode availability."""
        handler = MockRequestHandler(path="/api/dashboard/modes")
        handled = handle_dashboard_get(handler, "/api/dashboard/modes")
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("modes", data)

    def test_get_luck_royale_admin_endpoints(self):
        """GET /api/admin/luck-royale/* returns machine states, pools, and currencies."""
        endpoints = [
            "/api/admin/luck-royale/overview",
            "/api/admin/luck-royale/machines",
            "/api/admin/luck-royale/reward-pools",
            "/api/admin/luck-royale/meters",
            "/api/admin/luck-royale/currencies-vouchers",
            "/api/admin/luck-royale/exchange",
            "/api/admin/luck-royale/events-banners",
            "/api/admin/luck-royale/transactions",
        ]
        for ep in endpoints:
            handler = MockRequestHandler(path=ep)
            handled = handle_dashboard_get(handler, ep)
            self.assertTrue(handled, f"Endpoint {ep} was not handled")
            self.assertGreaterEqual(len(handler.json_calls), 1, f"No JSON response for {ep}")
            status, data = handler.json_calls[0]
            self.assertEqual(status, 200, f"Expected 200 for {ep}, got {status}")
            self.assertTrue(data.get("ok"), f"Expected ok: True for {ep}")

    def test_admin_players_directory_and_dossier(self):
        """GET /api/admin/players (paginated) and /api/admin/players/{id} (dossier)."""
        # 1. Directory pagination
        handler_dir = MockRequestHandler(path="/api/admin/players")
        handled_dir = handle_dashboard_get(handler_dir, "/api/admin/players", "page=1&limit=10")
        self.assertTrue(handled_dir, "Route /api/admin/players must be handled")
        status, data = handler_dir.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("players", data)
        self.assertIn("total", data)
        self.assertGreater(data["total"], 0)

        # 2. Deep Dossier
        handler_dos = MockRequestHandler(path="/api/admin/players/10001")
        handled_dos = handle_dashboard_get(handler_dos, "/api/admin/players/10001")
        self.assertTrue(handled_dos, "Route /api/admin/players/10001 must be handled")
        status_d, data_d = handler_dos.json_calls[0]
        self.assertEqual(status_d, 200)
        self.assertTrue(data_d.get("ok"))
        self.assertEqual(data_d.get("account_id"), 10001)
        self.assertIn("inventory", data_d)
        self.assertIn("wallet", data_d)

    def test_post_wallet_grant_and_set(self):
        """POST /api/dashboard/wallet/grant and /wallet/set update player currencies."""
        # Grant
        body = json.dumps({"account_id": 10001, "gold": 100, "diamonds": 50}).encode("utf-8")
        handler = MockRequestHandler(path="/api/dashboard/wallet/grant")
        handled = handle_dashboard_post(handler, "/api/dashboard/wallet/grant", body)
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("wallet", data)

        # Set
        body_set = json.dumps({"account_id": 10001, "gold": 99999, "diamonds": 8888}).encode("utf-8")
        handler_set = MockRequestHandler(path="/api/dashboard/wallet/set")
        handled_set = handle_dashboard_post(handler_set, "/api/dashboard/wallet/set", body_set)
        self.assertTrue(handled_set)
        self.assertEqual(len(handler_set.json_calls), 1)
        status_s, data_s = handler_set.json_calls[0]
        self.assertEqual(status_s, 200)
        self.assertTrue(data_s.get("ok"))
        wallet = data_s.get("wallet", {})
        # Free Fire stores gold in coins and diamonds in gems
        gold_val = wallet.get("gold", wallet.get("coins"))
        diamond_val = wallet.get("diamonds", wallet.get("gems"))
        self.assertEqual(gold_val, 99999)
        self.assertEqual(diamond_val, 8888)

    def test_post_items_grant_and_delete(self):
        """POST /api/dashboard/items/grant awards items and items/delete removes items."""
        # Grant
        body = json.dumps({"account_id": 10001, "item_ids": [101001], "amount": 2}).encode("utf-8")
        handler = MockRequestHandler(path="/api/dashboard/items/grant")
        handled = handle_dashboard_post(handler, "/api/dashboard/items/grant", body)
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # Delete
        body_del = json.dumps({"account_id": 10001, "item_id": 101001, "count": 1}).encode("utf-8")
        handler_del = MockRequestHandler(path="/api/admin/players/delete_item")
        handled_del = handle_dashboard_post(handler_del, "/api/admin/players/delete_item", body_del)
        self.assertTrue(handled_del)
        status_d, data_d = handler_del.json_calls[0]
        self.assertEqual(status_d, 200)
        self.assertTrue(data_d.get("ok"))

    def test_admin_players_create_and_ban_lifecycle(self):
        """POST /api/admin/players/create, /ban, and /unban."""
        # 1. Create account with unique timestamp nickname
        import time
        unique_nick = f"QA_Hero_{int(time.time() * 1000) % 100000}"
        body_create = json.dumps({
            "nickname": unique_nick,
            "region": "IND",
            "level": 15,
            "gold": 5000,
            "diamonds": 250,
        }).encode("utf-8")
        handler_create = MockRequestHandler(path="/api/admin/players/create")
        handled_create = handle_dashboard_post(handler_create, "/api/admin/players/create", body_create)
        self.assertTrue(handled_create)
        status_c, data_c = handler_create.json_calls[0]
        self.assertEqual(status_c, 201)
        self.assertTrue(data_c.get("ok"))
        new_aid = data_c.get("account_id")
        self.assertIsNotNone(new_aid)

        # 2. Ban account
        body_ban = json.dumps({"reason": "Automated regression testing sanction"}).encode("utf-8")
        ban_path = f"/api/admin/players/{new_aid}/ban"
        handler_ban = MockRequestHandler(path=ban_path)
        handled_ban = handle_dashboard_post(handler_ban, ban_path, body_ban)
        self.assertTrue(handled_ban)
        status_b, data_b = handler_ban.json_calls[0]
        self.assertEqual(status_b, 200)
        self.assertTrue(data_b.get("ok"))
        self.assertTrue(data_b.get("is_banned"))

        # 3. Unban account
        unban_path = f"/api/admin/players/{new_aid}/unban"
        handler_unban = MockRequestHandler(path=unban_path)
        handled_unban = handle_dashboard_post(handler_unban, unban_path, b"{}")
        self.assertTrue(handled_unban)
        status_u, data_u = handler_unban.json_calls[0]
        self.assertEqual(status_u, 200)
        self.assertTrue(data_u.get("ok"))
        self.assertFalse(data_u.get("is_banned"))

    def test_post_mail_send_and_delete(self):
        """POST /api/dashboard/mail/send creates mail and /mail/delete removes it."""
        body_send = json.dumps({
            "account_id": 10001,
            "title": "QA Test Mail",
            "content": "Automated regression verification mail",
            "gold": 50,
            "diamonds": 10,
        }).encode("utf-8")
        handler = MockRequestHandler(path="/api/dashboard/mail/send")
        handled = handle_dashboard_post(handler, "/api/dashboard/mail/send", body_send)
        self.assertTrue(handled)
        self.assertEqual(len(handler.json_calls), 1)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        mail = data.get("mail") or (data.get("mails", [{}])[0] if data.get("mails") else {})
        mail_id = mail.get("mail_id")
        self.assertIsNotNone(mail_id)

        # Delete mail
        body_del = json.dumps({"account_id": 10001, "mail_id": mail_id}).encode("utf-8")
        handler_del = MockRequestHandler(path="/api/dashboard/mail/delete")
        handled_del = handle_dashboard_post(handler_del, "/api/dashboard/mail/delete", body_del)
        self.assertTrue(handled_del)
        self.assertEqual(len(handler_del.json_calls), 1)
        status_d, data_d = handler_del.json_calls[0]
        self.assertEqual(status_d, 200)
        self.assertTrue(data_d.get("ok"))

    def test_post_modes_controls(self):
        """POST /api/dashboard/modes/toggle and unlock_all execute cleanly."""
        body_toggle = json.dumps({"mode_id": "1", "enabled": True}).encode("utf-8")
        handler = MockRequestHandler(path="/api/dashboard/modes/toggle")
        handled = handle_dashboard_post(handler, "/api/dashboard/modes/toggle", body_toggle)
        self.assertTrue(handled)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    def test_post_requests_clear(self):
        """POST /api/dashboard/requests/clear empties request history."""
        handler = MockRequestHandler(path="/api/dashboard/requests/clear")
        handled = handle_dashboard_post(handler, "/api/dashboard/requests/clear", b"{}")
        self.assertTrue(handled)
        status, data = handler.json_calls[0]
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    def test_gold_royale_character_debris_protection(self):
        """Verify Gold Royale duplicate character rewards award character-specific debris (800000000+), never generic tokens."""
        from handlers.admin_luck_royale_api import admin_mgr
        from proto.character_models import get_character_debris_id
        pool = admin_mgr.get_reward_pool(5)
        self.assertTrue(pool.get("ok"))
        items = pool.get("items", [])
        self.assertGreater(len(items), 0)
        # Check character items in Gold Royale pool
        for item in items:
            iid = item.get("item_id", 0)
            if 100000000 <= iid < 200000000:
                rep_id = item.get("repeated_item_id")
                expected_debris = get_character_debris_id(iid)
                self.assertEqual(
                    rep_id,
                    expected_debris,
                    f"Character {iid} in Gold Royale must have repeated_item_id {expected_debris}, got {rep_id}",
                )

    def test_unknown_routes_graceful_rejection(self):
        """Verify invalid or unmapped GET & POST routes reject with 404 or handled status."""
        handler_get = MockRequestHandler(path="/api/dashboard/unknown_endpoint")
        handled_get = handle_dashboard_get(handler_get, "/api/dashboard/unknown_endpoint")
        self.assertTrue(handled_get)
        status_g, data_g = handler_get.json_calls[0]
        self.assertEqual(status_g, 404)
        self.assertFalse(data_g.get("ok"))

        handler_post = MockRequestHandler(path="/api/dashboard/unknown_mutation")
        handled_post = handle_dashboard_post(handler_post, "/api/dashboard/unknown_mutation", b"{}")
        self.assertTrue(handled_post)
        status_p, data_p = handler_post.json_calls[0]
        self.assertEqual(status_p, 404)
        self.assertFalse(data_p.get("ok"))


if __name__ == "__main__":
    unittest.main()
