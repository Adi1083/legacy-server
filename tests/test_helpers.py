"""
Shared test utilities, protobuf decoders, and mock fixtures for Luck Royale test suites.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.decoder import (
    decode_proto,
    get_bool,
    get_bytes,
    get_int64,
    get_packed_varints,
    get_string,
    get_submessage,
    get_submessages,
    get_varint,
)
from proto.encoder import encode_string, encode_uint32
from proto.gacha_models import (
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
    ITEM_EVOLUTION_STONE,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_BLUEPRINT_JOKER,
    ITEM_FF_TOKEN,
    LotteryType,
    ConsumeType,
)


class MockRequestHandler:
    """Mock HTTP handler for testing server endpoint routing."""

    def __init__(self, path: str = "/", client_ip: str = "127.0.0.1") -> None:
        self.path = path
        self.client_address = (client_ip, 12345)
        self.headers: Dict[str, str] = {"Host": "127.0.0.1:8080"}
        self.proto_calls: List[Tuple[str, bytes]] = []
        self.json_calls: List[Tuple[int, Any]] = []
        self.bytes_calls: List[Tuple[int, bytes, str]] = []
        self.text_calls: List[Tuple[int, str]] = []
        self.status: int = 200

    def send_proto(self, name: str, data: bytes) -> None:
        self.proto_calls.append((name, data))

    def send_json(self, data: Any, status: int = 200) -> None:
        self.json_calls.append((status, data))
        self.status = status

    def send_bytes(self, data: bytes, status: int = 200, content_type: str = "application/octet-stream") -> None:
        self.bytes_calls.append((status, data, content_type))
        self.status = status

    def send_text(self, text: str, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        self.text_calls.append((status, text))
        self.status = status

    def send_response(self, code: int) -> None:
        self.status = code


def encode_cs_lottery_req(
    chest_id: int,
    gacha_type: int = LotteryType.ONE,
    chest_sub_id: int = 0,
    consume_type: int = ConsumeType.MONEY,
) -> bytes:
    """Encode CSLotteryReq."""
    return (
        encode_uint32(1, chest_id)
        + encode_uint32(2, gacha_type)
        + encode_uint32(3, chest_sub_id)
        + encode_uint32(4, consume_type)
    )


def encode_cs_lottery_extra_reward_req(
    chest_id: int,
    condition_num: int,
    chest_sub_id: int = 0,
) -> bytes:
    """Encode CSLotteryExtraRewardReq."""
    return (
        encode_uint32(1, chest_id)
        + encode_uint32(2, condition_num)
        + encode_uint32(3, chest_sub_id)
    )


def encode_cs_do_gacha_special_exchange_req(
    forge_tab_id: int,
    item_id: int,
    exchange_cnt: int = 1,
) -> bytes:
    """Encode CSDoGachaSpecialExchangeReq."""
    return (
        encode_uint32(1, forge_tab_id)
        + encode_uint32(2, item_id)
        + encode_uint32(3, exchange_cnt)
    )


def encode_cs_get_gacha_special_exchange_desc_req(language: str = "en") -> bytes:
    """Encode CSGetGachaSpecialExchangeDescReq."""
    return encode_string(1, language)


def encode_cs_get_lottery_probability_req(chest_id: int, chest_sub_id: int = 0) -> bytes:
    """Encode CSGetLotteryProbabilityReq."""
    return encode_uint32(1, chest_id) + encode_uint32(2, chest_sub_id)


def decode_cs_lottery_res(data: bytes) -> Dict[str, Any]:
    """Decode CSLotteryRes protobuf body."""
    fields = decode_proto(data)
    lottery_goods = []
    for g_fields in get_submessages(fields, 1):
        lottery_goods.append({
            "dest_award_id": get_varint(g_fields, 5),
            "dest_award_num": get_varint(g_fields, 6),
            "dest_award_type": get_varint(g_fields, 4),
            "origin_award_id": get_varint(g_fields, 2),
            "origin_award_num": get_varint(g_fields, 3),
            "origin_award_type": get_varint(g_fields, 1),
        })

    extra_one_goods = []
    for g_fields in get_submessages(fields, 3):
        extra_one_goods.append({
            "dest_award_id": get_varint(g_fields, 5),
            "dest_award_num": get_varint(g_fields, 6),
            "dest_award_type": get_varint(g_fields, 4),
            "origin_award_id": get_varint(g_fields, 2),
            "origin_award_num": get_varint(g_fields, 3),
            "origin_award_type": get_varint(g_fields, 1),
        })

    return {
        "lottery_goods": lottery_goods,
        "extra_one_goods": extra_one_goods,
        "lottery_count_weekly": get_varint(fields, 4),
        "next_free_time": get_int64(fields, 5),
        "limit_purchase_count_one": get_varint(fields, 6),
        "limit_purchase_count_ten": get_varint(fields, 7),
        "not_got_num": get_varint(fields, 8),
        "first_draw_reward_num": get_varint(fields, 9),
        "exchange_item_num": get_varint(fields, 10),
        "has_big_reward": get_bool(fields, 11),
    }


def decode_cs_get_gacha_info_res(data: bytes) -> List[Dict[str, Any]]:
    """Decode CSGetGachaInfoRes protobuf body."""
    fields = decode_proto(data)
    infos = []
    for info_fields in get_submessages(fields, 1):
        exchanged = get_packed_varints(info_fields, 3)
        infos.append({
            "chest_id": get_varint(info_fields, 1),
            "lottery_count_weekly": get_varint(info_fields, 2),
            "exchanged_reward_list": exchanged,
            "next_free_time": get_int64(info_fields, 4),
            "not_got_num": get_varint(info_fields, 5),
            "limit_purchase_count_one": get_varint(info_fields, 6),
            "limit_purchase_count_ten": get_varint(info_fields, 7),
            "first_draw_reward_num": get_varint(info_fields, 8),
        })
    return infos


def decode_cs_get_lottery_probability_res(data: bytes) -> List[Tuple[int, int]]:
    """Decode CSGetLotteryProbabilityRes."""
    fields = decode_proto(data)
    res = []
    for sub in get_submessages(fields, 1):
        rare = get_varint(sub, 1)
        prob = get_varint(sub, 2)
        res.append((rare, prob))
    return res


def decode_cs_do_gacha_special_exchange_res(data: bytes) -> Dict[str, Any]:
    """Decode CSDoGachaSpecialExchangeRes."""
    fields = decode_proto(data)
    change_data = get_submessage(fields, 1)
    trans_id = get_varint(change_data, 1) if change_data else get_varint(fields, 4)
    add_items = []
    del_items = []
    if change_data:
        for sub in get_submessages(change_data, 2):
            add_items.append({
                "item_id": get_varint(sub, 1),
                "cnt": get_varint(sub, 2),
            })
        for sub in get_submessages(change_data, 3):
            del_items.append({
                "item_id": get_varint(sub, 1),
                "cnt": get_varint(sub, 2),
            })
    return {
        "add_item_list": add_items,
        "del_item_list": del_items,
        "purchase_times": get_varint(fields, 2),
        "trans_id": trans_id,
    }


def reset_test_account_state(
    account_id: int = DEFAULT_ACCOUNT_ID,
    diamonds: int = 10000,
    gold: int = 100000,
    vouchers: Optional[Dict[int, int]] = None,
    materials: Optional[Dict[int, int]] = None,
) -> None:
    """Reset player state and gacha service memory for isolated testing."""
    from core.player import player_manager
    from handlers.gacha_handler import gacha_service

    # Clean DB gacha states and inventory for clean test isolation
    try:
        conn = db._get_conn()
        conn.execute("DELETE FROM gacha_states WHERE account_id = ?;", (account_id,))
        conn.execute("DELETE FROM inventory WHERE account_id = ?;", (account_id,))
    except Exception:
        pass

    with state._lock:
        state.set_wallet(coins=gold, gems=diamonds, account_id=account_id)
        p = player_manager.get_player(account_id)
        if p:
            with p._lock:
                p.coins = gold
                p.gems = diamonds
                p._inventory.clear()
        # Clear state caches
        state._unlocked_items.clear()
        state._item_counts.clear()

        # Seed vouchers if provided
        if vouchers is not None:
            for vid, cnt in vouchers.items():
                if cnt > 0:
                    state.add_item(vid, cnt, account_id=account_id)
                    if p:
                        with p._lock:
                            p._inventory[vid] = cnt

        # Seed materials if provided
        if materials is not None:
            for mid, cnt in materials.items():
                if cnt > 0:
                    state.add_item(mid, cnt, account_id=account_id)
                    if p:
                        with p._lock:
                            p._inventory[mid] = cnt

    with gacha_service._lock:
        gacha_service._chest_state.pop(account_id, None)
        gacha_service._special_purchases.pop(account_id, None)
        # Mark as seeded so _ensure_seeded does not override custom test voucher/materials
        gacha_service._seeded_accounts.add(account_id)
