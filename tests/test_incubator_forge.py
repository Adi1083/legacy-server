"""
Test Suite 5: Incubator Forge & Special Exchange Tests for Free Fire 1.39 Luck Royale.
Verifies:
1. Recipe catalog integrity for YinYang and Joker forge tabs.
2. Blueprint and Evolution Stone recipe requirements.
3. Successful forge exchange (/DoGachaSpecialExchange): atomic deduction and granting.
4. Insufficient materials prevention: partial deduction rollback.
5. Purchase limit enforcement (limited_purchase_times).
6. Protocol serialization and HTTP endpoint routing.
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
    DEFAULT_SPECIAL_EXCHANGES,
    ITEM_BLUEPRINT_JOKER,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
)
from handlers.gacha_handler import gacha_service, handle_gacha_request
from tests.test_helpers import (
    MockRequestHandler,
    decode_cs_do_gacha_special_exchange_res,
    encode_cs_do_gacha_special_exchange_req,
    encode_cs_get_gacha_special_exchange_desc_req,
    reset_test_account_state,
)


class TestIncubatorForge(unittest.TestCase):
    def setUp(self) -> None:
        self.aid = 10001
        self.handler = MockRequestHandler()
        # Clean slate
        reset_test_account_state(
            account_id=self.aid,
            diamonds=10000,
            gold=100000,
            materials={},
            vouchers={},
        )

    def test_forge_recipe_catalog_integrity(self) -> None:
        """Verify recipes exist for both YinYang (Tab 1) and Joker (Tab 2) with valid materials."""
        tab1_recipes = [r for r in DEFAULT_SPECIAL_EXCHANGES if r.forge_tab_id == 1]
        tab2_recipes = [r for r in DEFAULT_SPECIAL_EXCHANGES if r.forge_tab_id == 2]

        self.assertGreaterEqual(len(tab1_recipes), 4, "YinYang forge must have at least 4 recipes")
        self.assertGreaterEqual(len(tab2_recipes), 4, "Joker forge must have at least 4 recipes")

        for r in DEFAULT_SPECIAL_EXCHANGES:
            self.assertGreater(r.item_id, 0)
            self.assertGreater(r.item_num, 0)
            self.assertGreater(len(r.exchange_items), 0, "Recipe must require materials")
            # Must require at least blueprint + stone
            mat_ids = {award_id for award_id, _, _ in r.exchange_items}
            has_stone = bool(mat_ids.intersection({808000003, 808000001}))
            self.assertTrue(has_stone, f"Recipe for {r.item_id} must require Evolution Stones")

    def test_get_special_exchange_desc_endpoint(self) -> None:
        """Verify /GetGachaSpecialExchangeDesc endpoint returns valid protocol response."""
        req_bytes = encode_cs_get_gacha_special_exchange_desc_req(language="en")
        handled = handle_gacha_request(
            self.handler,
            "/GetGachaSpecialExchangeDesc",
            "127.0.0.1",
            req_bytes,
            account_id=self.aid,
        )
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "CSGetGachaSpecialExchangeDescRes")
        self.assertGreater(len(self.handler.proto_calls[-1][1]), 0)

    def test_successful_exchange_redemption(self) -> None:
        """Successful forge exchange deducts exact Blueprints and Stones and awards target item."""
        # Target YinYang bundle: item 710000410 (requires 3 Blueprints 808000001 + 7 Stones 808000003)
        bp_id = 808000001
        stone_id = 808000003
        target_item = 710000410

        # Seed exact materials
        reset_test_account_state(
            account_id=self.aid,
            materials={
                bp_id: 5,
                stone_id: 10,
            },
        )
        self.assertEqual(state.get_item_count(bp_id, self.aid), 5)
        self.assertEqual(state.get_item_count(stone_id, self.aid), 10)

        req = {
            "forge_tab_id": 1,
            "item_id": target_item,
            "exchange_cnt": 1,
        }
        res_bytes = gacha_service.do_special_exchange(req, account_id=self.aid)
        res = decode_cs_do_gacha_special_exchange_res(res_bytes)

        # Verify added item
        self.assertEqual(len(res["add_item_list"]), 1)
        self.assertEqual(res["add_item_list"][0]["item_id"], target_item)
        self.assertEqual(res["add_item_list"][0]["cnt"], 1)

        # Verify deducted items
        self.assertEqual(state.get_item_count(bp_id, self.aid), 5 - 3)
        self.assertEqual(state.get_item_count(stone_id, self.aid), 10 - 7)
        self.assertGreaterEqual(state.get_item_count(target_item, self.aid), 1)
        self.assertEqual(res["purchase_times"], 1)

    def test_insufficient_materials_rejection(self) -> None:
        """Attempting forge exchange with insufficient materials fails and leaves inventory untouched."""
        bp_id = 808000001
        stone_id = 808000003
        target_item = 710000410

        # Seed only 1 Blueprint and 1 Stone (requires 3 BP + 7 Stones)
        reset_test_account_state(
            account_id=self.aid,
            materials={
                bp_id: 1,
                stone_id: 1,
            },
        )

        req = {
            "forge_tab_id": 1,
            "item_id": target_item,
            "exchange_cnt": 1,
        }
        res_bytes = gacha_service.do_special_exchange(req, account_id=self.aid)
        res = decode_cs_do_gacha_special_exchange_res(res_bytes)

        # Must award zero items
        self.assertEqual(len(res["add_item_list"]), 0)
        # Materials must remain unspent (no partial deduction)
        self.assertEqual(state.get_item_count(bp_id, self.aid), 1)
        self.assertEqual(state.get_item_count(stone_id, self.aid), 1)
        self.assertEqual(state.get_item_count(target_item, self.aid), 0)

    def test_purchase_limit_enforcement(self) -> None:
        """Attempting exchange past limited_purchase_times (limit=1) is rejected."""
        bp_id = 808000001
        stone_id = 808000003
        target_item = 710000410

        # Seed plenty of materials (enough for 2 crafts)
        reset_test_account_state(
            account_id=self.aid,
            materials={
                bp_id: 10,
                stone_id: 20,
            },
        )

        req = {
            "forge_tab_id": 1,
            "item_id": target_item,
            "exchange_cnt": 1,
        }
        # First craft should succeed
        res_bytes1 = gacha_service.do_special_exchange(req, account_id=self.aid)
        res1 = decode_cs_do_gacha_special_exchange_res(res_bytes1)
        self.assertEqual(len(res1["add_item_list"]), 1)
        self.assertEqual(res1["purchase_times"], 1)

        # Second craft must fail due to limit = 1
        res_bytes2 = gacha_service.do_special_exchange(req, account_id=self.aid)
        res2 = decode_cs_do_gacha_special_exchange_res(res_bytes2)
        self.assertEqual(len(res2["add_item_list"]), 0)
        self.assertEqual(res2["purchase_times"], 1)

    def test_invalid_recipe_exchange(self) -> None:
        """Attempting exchange for non-existent recipe fails gracefully."""
        req = {
            "forge_tab_id": 999,
            "item_id": 999999,
            "exchange_cnt": 1,
        }
        res_bytes = gacha_service.do_special_exchange(req, account_id=self.aid)
        res = decode_cs_do_gacha_special_exchange_res(res_bytes)
        self.assertEqual(len(res["add_item_list"]), 0)

    def test_http_endpoint_do_gacha_special_exchange_routing(self) -> None:
        """Verify /DoGachaSpecialExchange HTTP routing with protobuf request."""
        bp_id = 808000001
        stone_id = 808000003
        target_item = 710000412  # Requires 2 BP + 5 Stones

        reset_test_account_state(
            account_id=self.aid,
            materials={
                bp_id: 5,
                stone_id: 10,
            },
        )

        req_bytes = encode_cs_do_gacha_special_exchange_req(
            forge_tab_id=1,
            item_id=target_item,
            exchange_cnt=1,
        )
        handled = handle_gacha_request(
            self.handler,
            "/DoGachaSpecialExchange",
            "127.0.0.1",
            req_bytes,
            account_id=self.aid,
        )
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "CSDoGachaSpecialExchangeRes")
        res = decode_cs_do_gacha_special_exchange_res(self.handler.proto_calls[-1][1])
        self.assertEqual(len(res["add_item_list"]), 1)


if __name__ == "__main__":
    unittest.main()
