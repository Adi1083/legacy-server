"""
Phase 2 Stage 3 — End-to-End Backend API Audit Suite
Tests and verifies all endpoints across:
- `server/handlers/dashboard_api.py`
- `server/handlers/admin_luck_royale_api.py`
- `server/server.py`
"""

import json
import os
import sys
import threading
import time
import unittest
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import ThreadedDualStackServer, BarbosaHandler
from core.state import DEFAULT_ACCOUNT_ID, state
from core.player import player_manager


class TestBackendE2EAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadedDualStackServer(("127.0.0.1", 0), BarbosaHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.test_aid = DEFAULT_ACCOUNT_ID

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _req(self, method, path, body=None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if "json" in resp.headers.get("Content-Type", "") else raw
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
            return exc.code, parsed

    # -------------------------------------------------------------
    # 1. Player Directory, Dossier, Create, Ban, Item Deletion
    # -------------------------------------------------------------
    def test_01_players_crud_audit(self):
        # GET /api/admin/players
        status, data = self._req("GET", "/api/admin/players?page=1&limit=5&sort=account_id&order=asc")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("players", data)

        # POST /api/admin/players/create
        status, data = self._req("POST", "/api/admin/players/create", {
            "nickname": f"AuditBot_{int(time.time()*1000)%100000}",
            "region": "IND",
            "level": 60,
            "coins": 999999,
            "gems": 999999,
        })
        self.assertIn(status, (200, 201))
        self.assertTrue(data.get("ok"))
        created_aid = data["account_id"]

        # GET /api/admin/players/{id}
        status, data = self._req("GET", f"/api/admin/players/{created_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data["account_id"], created_aid)
        self.assertIn("profile", data)
        self.assertIn("wallet", data)
        self.assertIn("inventory", data)

        # POST /api/admin/players/{id}/ban
        status, data = self._req("POST", f"/api/admin/players/{created_aid}/ban", {"reason": "Audit verification"})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertTrue(data.get("is_banned"))

        # POST /api/admin/players/{id}/unban
        status, data = self._req("POST", f"/api/admin/players/{created_aid}/unban", {})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertFalse(data.get("is_banned"))

        # DELETE /api/admin/players/{id}/items/{item_id}
        p = player_manager.get_player(created_aid)
        p.unlock_item(907000001, count=2)
        status, data = self._req("DELETE", f"/api/admin/players/{created_aid}/items/907000001")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    # -------------------------------------------------------------
    # 2. Overview, State & Telemetry Endpoints
    # -------------------------------------------------------------
    def test_02_overview_and_telemetry_audit(self):
        # GET /api/dashboard/state
        status, data = self._req("GET", f"/api/dashboard/state?account_id={self.test_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("server", data)
        self.assertIn("profile", data)

        # GET /api/dashboard/requests
        status, data = self._req("GET", "/api/dashboard/requests?limit=10")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("requests", data)

        # POST /api/dashboard/requests/clear
        status, data = self._req("POST", "/api/dashboard/requests/clear", {})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # POST /api/dashboard/decode (Hex protobuf)
        status, data = self._req("POST", "/api/dashboard/decode", {"hex": "08011002"})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("decoded", data)

    # -------------------------------------------------------------
    # 3. Economy, Wallet & Inventory Grant Endpoints
    # -------------------------------------------------------------
    def test_03_economy_and_inventory_audit(self):
        # POST /api/dashboard/wallet/grant
        status, data = self._req("POST", "/api/dashboard/wallet/grant", {
            "account_id": self.test_aid,
            "coins": 1000,
            "gems": 50,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # POST /api/dashboard/wallet/set
        status, data = self._req("POST", "/api/dashboard/wallet/set", {
            "account_id": self.test_aid,
            "coins": 999999,
            "gems": 999999,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # POST /api/dashboard/items/grant
        status, data = self._req("POST", "/api/dashboard/items/grant", {
            "account_id": self.test_aid,
            "item_id": 907000001,
            "count": 1,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # POST /api/dashboard/character/select
        status, data = self._req("POST", "/api/dashboard/character/select", {
            "account_id": self.test_aid,
            "avatar_id": 102000004,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # POST /api/dashboard/pet/select
        status, data = self._req("POST", "/api/dashboard/pet/select", {
            "account_id": self.test_aid,
            "pet_id": 1300000001,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    # -------------------------------------------------------------
    # 4. Social & Communication Endpoints
    # -------------------------------------------------------------
    def test_04_social_endpoints_audit(self):
        # GET /api/dashboard/mail
        status, data = self._req("GET", f"/api/dashboard/mail?account_id={self.test_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("mails", data)

        # POST /api/dashboard/mail/send
        status, data = self._req("POST", "/api/dashboard/mail/send", {
            "account_id": self.test_aid,
            "title": "Audit Test Mail",
            "content": "Automated verification payload",
            "coins": 100,
            "gems": 10,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/dashboard/friends
        status, data = self._req("GET", f"/api/dashboard/friends?account_id={self.test_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("friends", data)

        # GET /api/dashboard/squad
        status, data = self._req("GET", f"/api/dashboard/squad?account_id={self.test_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("team", data)

        # POST /api/dashboard/squad/create
        status, data = self._req("POST", "/api/dashboard/squad/create", {
            "account_id": self.test_aid,
            "mode": "squad",
            "team_name": "Audit Squad",
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # POST /api/dashboard/squad/leave
        status, data = self._req("POST", "/api/dashboard/squad/leave", {
            "player_id": self.test_aid,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    # -------------------------------------------------------------
    # 5. CMS, Banners & Game Modes Endpoints
    # -------------------------------------------------------------
    def test_05_cms_and_modes_audit(self):
        # GET /api/dashboard/cms
        status, data = self._req("GET", "/api/dashboard/cms")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/dashboard/cms/banners
        status, data = self._req("GET", "/api/dashboard/cms/banners")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/dashboard/modes
        status, data = self._req("GET", "/api/dashboard/modes")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("modes", data)

        # POST /api/dashboard/modes/toggle
        status, data = self._req("POST", "/api/dashboard/modes/toggle", {
            "map_id": 1,
            "game_mode": 1,
            "match_mode": 1,
            "enable": True,
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

    # -------------------------------------------------------------
    # 6. Admin Luck Royale Endpoints
    # -------------------------------------------------------------
    def test_06_luck_royale_admin_audit(self):
        # GET /api/admin/luck-royale/overview
        status, data = self._req("GET", "/api/admin/luck-royale/overview")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/admin/luck-royale/machines
        status, data = self._req("GET", "/api/admin/luck-royale/machines")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("machines", data)

        # GET /api/admin/luck-royale/meters
        status, data = self._req("GET", "/api/admin/luck-royale/meters")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/admin/luck-royale/currencies-vouchers
        status, data = self._req("GET", f"/api/admin/luck-royale/currencies-vouchers?account_id={self.test_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/admin/luck-royale/exchange
        status, data = self._req("GET", f"/api/admin/luck-royale/exchange?account_id={self.test_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/admin/luck-royale/events-banners
        status, data = self._req("GET", "/api/admin/luck-royale/events-banners")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/admin/luck-royale/accounts/{id}
        status, data = self._req("GET", f"/api/admin/luck-royale/accounts/{self.test_aid}")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))

        # GET /api/admin/luck-royale/transactions
        status, data = self._req("GET", "/api/admin/luck-royale/transactions?limit=5")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))


if __name__ == "__main__":
    unittest.main()
