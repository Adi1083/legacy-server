"""End-to-End HTTP Flow tests for Luck Royale / Gacha endpoints in Free Fire 1.39."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.game_router import handle_game_post
from proto.decoder import decode_proto, get_submessages, get_varint
from proto.encoder import encode_uint32
from proto.gacha_models import (
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    ConsumeType,
    LotteryType,
)


class DummyHandler:
    def __init__(self):
        self.responses = []
        self.status = 200
        self.headers = {"Host": "127.0.0.1:8080"}

    def send_proto(self, proto_name, payload):
        self.responses.append((proto_name, payload))

    def send_error(self, code, message=None):
        self.status = code


def encode_lottery_req(chest_id, gacha_type, chest_sub_id=0, consume_type=3):
    buf = bytearray()
    buf += encode_uint32(1, chest_id)
    buf += encode_uint32(2, gacha_type)
    buf += encode_uint32(3, chest_sub_id)
    buf += encode_uint32(4, consume_type)
    return bytes(buf)


class TestGachaFlow(unittest.TestCase):
    def setUp(self):
        state.modify_gold(DEFAULT_ACCOUNT_ID, 50000)
        state.modify_diamond(DEFAULT_ACCOUNT_ID, 20000)

    def test_get_gacha_desc_flow(self):
        h = DummyHandler()
        handled = handle_game_post(h, "/GetGachaDesc", "127.0.0.1", b"")
        self.assertTrue(handled)
        self.assertEqual(len(h.responses), 1)
        proto_name, data = h.responses[0]
        self.assertEqual(proto_name, "CSGetGachaDescRes")
        self.assertTrue(len(data) > 0)

    def test_get_gacha_info_flow(self):
        h = DummyHandler()
        handled = handle_game_post(h, "/GetGachaInfo", "127.0.0.1", b"")
        self.assertTrue(handled)
        self.assertEqual(len(h.responses), 1)
        proto_name, data = h.responses[0]
        self.assertEqual(proto_name, "CSGetGachaInfoRes")
        self.assertTrue(len(data) > 0)

    def test_purchase_gacha_single_and_multi_flow(self):
        h = DummyHandler()
        # Single spin on Gold Royale
        spin_single = encode_lottery_req(CHEST_GOLD_ROYALE, LotteryType.ONE, 0, ConsumeType.MONEY)
        handled = handle_game_post(h, "/PurchaseGacha", "127.0.0.1", spin_single)
        self.assertTrue(handled)
        proto_name, data = h.responses[-1]
        self.assertEqual(proto_name, "CSLotteryRes")
        fields = decode_proto(data)
        self.assertEqual(len(get_submessages(fields, 1)), 1)

        # Multi spin on Gold Royale
        spin_multi = encode_lottery_req(CHEST_GOLD_ROYALE, LotteryType.SOME, 0, ConsumeType.MONEY)
        handled = handle_game_post(h, "/Lottery", "127.0.0.1", spin_multi)
        self.assertTrue(handled)
        proto_name, data = h.responses[-1]
        self.assertEqual(proto_name, "CSLotteryRes")
        fields = decode_proto(data)
        self.assertEqual(len(get_submessages(fields, 1)), 10)
        self.assertEqual(len(get_submessages(fields, 3)), 1)


if __name__ == "__main__":
    unittest.main()
