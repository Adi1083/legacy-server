import sys
import os

sys.path.insert(0, os.path.abspath("server"))
from handlers.game_router import handle_game_post
from proto.encoder import encode_uint32
from proto.gacha_models import (
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    LotteryType,
    ConsumeType,
)

def encode_lottery_req(chest_id=5, gacha_type=1, chest_sub_id=0, consume_type=3):
    buf = bytearray()
    buf += encode_uint32(1, chest_id)
    buf += encode_uint32(2, gacha_type)
    buf += encode_uint32(3, chest_sub_id)
    buf += encode_uint32(4, consume_type)
    return bytes(buf)

class DummyHandler:
    headers = {"Host": "127.0.0.1:8080"}
    def __init__(self):
        self.responses = []
    def send_proto(self, name, data):
        self.responses.append((name, len(data)))
        print(f"[OK] Sent proto {name} (bytes={len(data)})")
    def send_bytes(self, data, status=200):
        self.responses.append(("BYTES", len(data)))
        print(f"[OK] Sent bytes (status={status}, bytes={len(data)})")

h = DummyHandler()

# 1. Test GetGachaDesc
handle_game_post(h, "/GetGachaDesc", "127.0.0.1", b"")

# 2. Test GetGachaInfo
handle_game_post(h, "/GetGachaInfo", "127.0.0.1", b"")

# 3. Test GetGachaProbability for Diamond Royale
req_prob = b"\x08\x03" # chest_id=3
handle_game_post(h, "/GetGachaProbability", "127.0.0.1", req_prob)

# 4. Test Single Spin Gold Royale
spin_req_single = encode_lottery_req(chest_id=CHEST_GOLD_ROYALE, gacha_type=LotteryType.ONE, consume_type=ConsumeType.MONEY)
handle_game_post(h, "/PurchaseGacha", "127.0.0.1", spin_req_single)

# 5. Test 10x Spin Gold Royale
spin_req_multi = encode_lottery_req(chest_id=CHEST_GOLD_ROYALE, gacha_type=LotteryType.SOME, consume_type=ConsumeType.MONEY)
handle_game_post(h, "/PurchaseGacha", "127.0.0.1", spin_req_multi)

# 6. Test Single Spin Incubator
spin_inc = encode_lottery_req(chest_id=CHEST_INCUBATOR, gacha_type=LotteryType.ONE, consume_type=ConsumeType.MONEY)
handle_game_post(h, "/PurchaseGacha", "127.0.0.1", spin_inc)

print(f"Total endpoints verified: {len(h.responses)}")

