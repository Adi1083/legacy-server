"""
Comprehensive Unit & Integration Test Suite for Admin Players API
Verifies:
1. GET /api/admin/players (server-side pagination, search by nickname or id, sort).
2. GET /api/admin/players/{id}` (deep dossier).
3. POST /api/admin/players/create (create account).
4. POST /api/admin/players/{id}/ban and unban (with is_banned DB column).
5. DELETE /api/admin/players/{id}/items/{item_id}.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import db
from core.player import player_manager, DEFAULT_ACCOUNT_ID
from core.state import state
from handlers.dashboard_api import (
    handle_dashboard_get,
    handle_dashboard_post,
    handle_dashboard_delete,
)


class MockHandler:
    def __init__(self):
        self.status = 200
        self.headers = {}
        self.json_data = None
        self.text_data = None
        self.bytes_data = None

    def send_json(self, data, status=200):
        self.status = status
        self.json_data = data

    def send_text(self, text, status=200, content_type="text/plain"):
        self.status = status
        self.text_data = text

    def send_bytes(self, b, status=200, content_type="application/octet-stream"):
        self.status = status
        self.bytes_data = b


class TestAdminPlayersAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure default player exists
        cls.default_p = player_manager.get_or_create(DEFAULT_ACCOUNT_ID)

    def test_01_create_player(self):
        import uuid
        unique_nick = f"TestChamp_{uuid.uuid4().hex[:8]}"
        handler = MockHandler()
        body = json.dumps({
            "nickname": unique_nick,
            "region": "IND",
            "level": 65,
            "exp": 150000,
            "coins": 500000,
            "gems": 25000,
        }).encode("utf-8")

        handled = handle_dashboard_post(handler, "/api/admin/players/create", body)
        self.assertTrue(handled)
        self.assertIn(handler.status, (200, 201))
        self.assertTrue(handler.json_data.get("ok"))
        created_aid = handler.json_data.get("account_id")
        self.assertGreaterEqual(created_aid, 10001)

        # Verify created player in player_manager and database
        p = player_manager.get_player(created_aid)
        self.assertIsNotNone(p)
        self.assertEqual(p.nickname, unique_nick)
        self.assertEqual(p.level, 65)
        self.assertEqual(p.coins, 500000)
        self.assertEqual(p.gems, 25000)
        self.assertFalse(p.is_banned)

        db_prof = db.get_profile(created_aid)
        self.assertIsNotNone(db_prof)
        self.assertEqual(db_prof["nickname"], unique_nick)
        self.assertFalse(db_prof["is_banned"])

        # Duplicate nickname creation returns 400
        handler_dup = MockHandler()
        handled_dup = handle_dashboard_post(handler_dup, "/api/admin/players/create", body)
        self.assertTrue(handled_dup)
        self.assertEqual(handler_dup.status, 400)
        self.assertFalse(handler_dup.json_data.get("ok"))

    def test_02_get_players_pagination_search_sort(self):
        # 1. Basic listing
        h = MockHandler()
        handled = handle_dashboard_get(h, "/api/admin/players", "page=1&limit=5&sort=account_id&order=asc")
        self.assertTrue(handled)
        self.assertEqual(h.status, 200)
        self.assertTrue(h.json_data.get("ok"))
        self.assertIn("players", h.json_data)
        self.assertGreater(h.json_data["total"], 0)
        self.assertLessEqual(len(h.json_data["players"]), 5)

        # 2. Search by nickname
        h_search = MockHandler()
        handled = handle_dashboard_get(h_search, "/api/admin/players", "search=TestChampion")
        self.assertTrue(handled)
        self.assertEqual(h_search.status, 200)
        found = any("TestChampion" in p["nickname"] for p in h_search.json_data["players"])
        self.assertTrue(found)

        # 3. Search by account_id
        h_search_id = MockHandler()
        handled = handle_dashboard_get(h_search_id, "/api/admin/players", f"search={DEFAULT_ACCOUNT_ID}")
        self.assertTrue(handled)
        self.assertEqual(h_search_id.status, 200)
        self.assertTrue(any(p["account_id"] == DEFAULT_ACCOUNT_ID for p in h_search_id.json_data["players"]))

        # 4. Sorting desc by level
        h_sort = MockHandler()
        handled = handle_dashboard_get(h_sort, "/api/admin/players", "sort=level&order=desc&limit=10")
        self.assertTrue(handled)
        levels = [p["level"] for p in h_sort.json_data["players"]]
        self.assertEqual(levels, sorted(levels, reverse=True))

    def test_03_get_player_dossier(self):
        h = MockHandler()
        handled = handle_dashboard_get(h, f"/api/admin/players/{DEFAULT_ACCOUNT_ID}", "")
        self.assertTrue(handled)
        self.assertEqual(h.status, 200)
        res = h.json_data
        self.assertTrue(res.get("ok"))
        self.assertEqual(res["account_id"], DEFAULT_ACCOUNT_ID)
        self.assertIn("profile", res)
        self.assertIn("wallet", res)
        self.assertIn("inventory", res)
        self.assertIn("characters", res)
        self.assertIn("pets", res)
        self.assertIn("mails", res)
        self.assertIn("friends", res)
        self.assertIn("gacha_states", res)
        self.assertIn("claims", res)
        self.assertIn("audit_logs", res)
        self.assertIn("is_banned", res)

        # Dossier for non-existent player returns 404
        h_404 = MockHandler()
        handled_404 = handle_dashboard_get(h_404, "/api/admin/players/99999999", "")
        self.assertTrue(handled_404)
        self.assertEqual(h_404.status, 404)
        self.assertFalse(h_404.json_data.get("ok"))

    def test_04_ban_and_unban_player(self):
        # Create dedicated player for ban test
        p_test = player_manager.create_account(nickname="BanTarget_X", region="IND")
        aid = p_test.account_id

        # 1. Ban player
        h_ban = MockHandler()
        ban_body = json.dumps({"reason": "Speed hack detected"}).encode("utf-8")
        handled = handle_dashboard_post(h_ban, f"/api/admin/players/{aid}/ban", ban_body)
        self.assertTrue(handled)
        self.assertEqual(h_ban.status, 200)
        self.assertTrue(h_ban.json_data.get("ok"))
        self.assertTrue(h_ban.json_data.get("is_banned"))

        # Verify in memory and in SQLite DB
        self.assertTrue(player_manager.get_player(aid).is_banned)
        self.assertTrue(db.is_player_banned(aid))
        db_prof = db.get_profile(aid)
        self.assertTrue(db_prof["is_banned"])

        # 2. Unban player
        h_unban = MockHandler()
        unban_body = json.dumps({"reason": "Appeal accepted"}).encode("utf-8")
        handled = handle_dashboard_post(h_unban, f"/api/admin/players/{aid}/unban", unban_body)
        self.assertTrue(handled)
        self.assertEqual(h_unban.status, 200)
        self.assertTrue(h_unban.json_data.get("ok"))
        self.assertFalse(h_unban.json_data.get("is_banned"))

        # Verify unbanned in memory and in SQLite DB
        self.assertFalse(player_manager.get_player(aid).is_banned)
        self.assertFalse(db.is_player_banned(aid))
        db_prof2 = db.get_profile(aid)
        self.assertFalse(db_prof2["is_banned"])

        # Ban non-existent player returns 404
        h_ban_404 = MockHandler()
        handle_dashboard_post(h_ban_404, "/api/admin/players/99999999/ban", b"{}")
        self.assertEqual(h_ban_404.status, 404)

    def test_05_delete_player_item(self):
        p_test = player_manager.create_account(nickname="ItemTarget_Y", region="IND")
        aid = p_test.account_id
        item_id = 907000001  # starter weapon skin

        # Make sure item exists
        p_test.unlock_item(item_id, count=5)
        self.assertEqual(p_test.get_item_count(item_id), 5)

        # 1. Partial delete (count=2)
        h_del_part = MockHandler()
        del_part_body = json.dumps({"count": 2}).encode("utf-8")
        handled = handle_dashboard_delete(h_del_part, f"/api/admin/players/{aid}/items/{item_id}", del_part_body)
        self.assertTrue(handled)
        self.assertEqual(h_del_part.status, 200)
        self.assertTrue(h_del_part.json_data.get("ok"))
        self.assertEqual(h_del_part.json_data.get("remaining_count"), 3)
        self.assertEqual(p_test.get_item_count(item_id), 3)

        # 2. Full delete (no count)
        h_del_full = MockHandler()
        handled = handle_dashboard_delete(h_del_full, f"/api/admin/players/{aid}/items/{item_id}", b"")
        self.assertTrue(handled)
        self.assertEqual(h_del_full.status, 200)
        self.assertTrue(h_del_full.json_data.get("ok"))
        self.assertEqual(h_del_full.json_data.get("remaining_count"), 0)
        self.assertEqual(p_test.get_item_count(item_id), 0)

        # Check DB reflects removal
        inv_db = db.get_inventory(aid)
        self.assertNotIn(item_id, inv_db)

        # 3. Deleting non-existent item returns 404
        h_del_404 = MockHandler()
        handled = handle_dashboard_delete(h_del_404, f"/api/admin/players/{aid}/items/99999999", b"")
        self.assertTrue(handled)
        self.assertEqual(h_del_404.status, 404)


class TestAdminPlayersLiveHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        import urllib.request
        from server import ThreadedDualStackServer, BarbosaHandler

        cls.httpd = ThreadedDualStackServer(("127.0.0.1", 0), BarbosaHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_live_01_create_player(self):
        import urllib.request
        import uuid
        unique_nick = f"LiveTester_{uuid.uuid4().hex[:8]}"
        url = f"{self.base_url}/api/admin/players/create"
        payload = json.dumps({
            "nickname": unique_nick,
            "region": "IND",
            "level": 55,
            "coins": 777777,
            "gems": 8888,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            self.assertIn(resp.status, (200, 201))
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertIn("account_id", data)
            self.assertEqual(data["player"]["nickname"], unique_nick)

    def test_live_02_get_players(self):
        import urllib.request
        url = f"{self.base_url}/api/admin/players?page=1&limit=10&sort=account_id&order=asc"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertIn("players", data)
            self.assertGreater(data["total"], 0)

    def test_live_03_get_player_dossier(self):
        import urllib.request
        url = f"{self.base_url}/api/admin/players/{DEFAULT_ACCOUNT_ID}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertEqual(data["account_id"], DEFAULT_ACCOUNT_ID)
            self.assertIn("profile", data)
            self.assertIn("inventory", data)

    def test_live_04_ban_and_unban_player(self):
        import urllib.request
        p = player_manager.create_account(nickname="LiveBanTarget", region="IND")
        aid = p.account_id

        # Ban
        ban_url = f"{self.base_url}/api/admin/players/{aid}/ban"
        ban_req = urllib.request.Request(ban_url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(ban_req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertTrue(data.get("is_banned"))
        self.assertTrue(player_manager.get_player(aid).is_banned)

        # Unban
        unban_url = f"{self.base_url}/api/admin/players/{aid}/unban"
        unban_req = urllib.request.Request(unban_url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(unban_req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertFalse(data.get("is_banned"))
        self.assertFalse(player_manager.get_player(aid).is_banned)

    def test_live_05_delete_player_item(self):
        import urllib.request
        p = player_manager.create_account(nickname="LiveItemTarget", region="IND")
        aid = p.account_id
        item_id = 907000001
        p.unlock_item(item_id, count=3)

        del_url = f"{self.base_url}/api/admin/players/{aid}/items/{item_id}"
        del_req = urllib.request.Request(del_url, method="DELETE")
        with urllib.request.urlopen(del_req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("remaining_count"), 0)
        self.assertEqual(p.get_item_count(item_id), 0)


if __name__ == "__main__":
    unittest.main()
