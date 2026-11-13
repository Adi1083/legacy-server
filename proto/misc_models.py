"""
Protobuf encoders, decoders, and enums for Manual, Live/Streamer/Video,
GiftRank, MysteryBonus, WinnerTakesAll (WTA), CollectionHide, Loadout, and
Entitlement endpoints in Barbosa Project (Free Fire 1.39).

Verified against global-metadata.dat (v23) and XOR-0x03 libil2cpp.so.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

from proto.activity_models import AwardType, encode_award_data, encode_award_desc
from proto.decoder import decode_proto, get_packed_varints, get_string, get_varint
from proto.encoder import (
    encode_bool,
    encode_int64,
    encode_packed_uint32,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EManualState:
    """EManual.State [TypeDef 5126]"""
    COLLECTING = 0
    FINISHED = 1
    AWARDED = 2


class EManualEventType:
    """EManual.EventType [TypeDef 5127]"""
    NONE = 0
    WEAPON = 1
    MAP = 2
    SUP = 3
    MOV = 4
    EVE = 5


class GenderType:
    """GenderType [TypeDef 4934]"""
    NONE = 0
    WOMAN = 1
    MAN = 2


class FollowerType:
    """ELive.FollowerType [TypeDef 5123]"""
    NONE = 0
    YES = 1
    NO = 2


class VideoType:
    """ELive.VideoType [TypeDef 5124]"""
    NONE = 0
    HOTEST = 1
    LIVE_NOW = 2
    EXPLORE = 3
    TUTORIAL = 4
    ALL = 100
    NEWEST = 101
    POPULAR = 102
    OTHER = 103


class GiftRankType:
    """GiftRankType [TypeDef 5116]"""
    NONE = 0
    RECEIVER = 1
    GIVER = 2


class WinnerTakesAllCurrencyType:
    """WinnerTakesAllCurrencyType [TypeDef 4992]"""
    NONE = 0
    CHIP = 1
    DIAMOND = 2
    FREE = 3


# ---------------------------------------------------------------------------
# Manual Encoders & Decoders
# ---------------------------------------------------------------------------

def encode_get_manual_collect_info_res(manual_event_ids: Iterable[int]) -> bytes:
    """proto.CSGetManualCollectInfoRes [5474]"""
    ids = [int(x) for x in manual_event_ids]
    return encode_packed_uint32(1, ids) if ids else b""


def encode_manual_weapon_reward(quantity_period: int, state: int) -> bytes:
    """proto.ManualWeaponReward [5481]"""
    return encode_uint32(1, int(quantity_period)) + encode_uint32(2, int(state))


def encode_get_manual_all_weapon_reward_states_res(
    weapon_rewards: Iterable[Dict[str, Any]],
) -> bytes:
    """proto.CSGetManualAllWeaponRewardStatesRes [5475]"""
    buf = bytearray()
    for rw in weapon_rewards:
        sub = encode_manual_weapon_reward(rw["quantity_period"], rw.get("state", EManualState.COLLECTING))
        buf += encode_submessage(1, sub)
    return bytes(buf)


def encode_manual_map_reward(map_id: int, state: int) -> bytes:
    """proto.ManualMapReward [5482]"""
    return encode_uint32(1, int(map_id)) + encode_uint32(2, int(state))


def encode_get_manual_all_map_reward_states_res(
    map_rewards: Iterable[Dict[str, Any]],
) -> bytes:
    """proto.CSGetManualAllMapRewardStatesRes [5476]"""
    buf = bytearray()
    for rw in map_rewards:
        sub = encode_manual_map_reward(rw["map_id"], rw.get("state", EManualState.COLLECTING))
        buf += encode_submessage(1, sub)
    return bytes(buf)


def decode_manual_weapon_reward_req(raw_body: bytes) -> int:
    """proto.CSGetManualWeaponRewardReq [5477]"""
    return get_varint(decode_proto(raw_body), 1, 0)


def encode_manual_weapon_reward_res(
    items: Optional[Iterable[Dict[str, Any]]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
) -> bytes:
    """proto.CSGetManualWeaponRewardRes [5478]"""
    return encode_submessage(
        1,
        encode_award_data(items=items, coins=coins, gems=gems, exps=exps, activeness=activeness),
    )


def decode_manual_map_reward_req(raw_body: bytes) -> int:
    """proto.CSGetManualMapRewardReq [5479]"""
    return get_varint(decode_proto(raw_body), 1, 0)


def encode_manual_map_reward_res(
    items: Optional[Iterable[Dict[str, Any]]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
) -> bytes:
    """proto.CSGetManualMapRewardRes [5480]"""
    return encode_submessage(
        1,
        encode_award_data(items=items, coins=coins, gems=gems, exps=exps, activeness=activeness),
    )


# ---------------------------------------------------------------------------
# Live / Streamer / Video Encoders & Decoders
# ---------------------------------------------------------------------------

def encode_streamer_base_info(s: Dict[str, Any]) -> bytes:
    """proto.StreamerBaseInfo [5469]"""
    buf = bytearray()
    buf += encode_uint64(1, int(s.get("account_id", 20001)))
    buf += encode_string(2, str(s.get("nickname", "Barbosa_Streamer")))
    buf += encode_uint32(3, int(s.get("head_pic", 902000001)))
    buf += encode_uint32(4, int(s.get("banner_id", 901000001)))
    return bytes(buf)


def decode_follow_streamer_list_req(raw_body: bytes) -> int:
    """proto.CSGetFollowStreamerListReq [5470]"""
    return get_varint(decode_proto(raw_body), 1, 0)


def encode_follow_streamer_list_res(
    streamer_list: Iterable[Dict[str, Any]],
    recommended_streamer_list: Iterable[Dict[str, Any]],
) -> bytes:
    """proto.CSGetFollowStreamerListRes [5471]"""
    buf = bytearray()
    for st in streamer_list:
        buf += encode_submessage(1, encode_streamer_base_info(st))
    for st in recommended_streamer_list:
        buf += encode_submessage(2, encode_streamer_base_info(st))
    return bytes(buf)


def decode_other_live_info_req(raw_body: bytes) -> int:
    """proto.CSGetOtherLiveInfoReq [5457]"""
    return get_varint(decode_proto(raw_body), 1, 0)


def encode_get_live_info_res(info: Dict[str, Any]) -> bytes:
    """proto.CSGetLiveInfoRes [5456]"""
    buf = bytearray()
    buf += encode_bool(1, bool(info.get("is_streamer", True)))
    buf += encode_string(2, str(info.get("nickname", "Clack")))
    buf += encode_uint32(3, int(info.get("sex", GenderType.MAN)))
    buf += encode_uint32(4, int(info.get("head_pic", 902000001)))
    buf += encode_uint32(5, int(info.get("banner_id", 901000001)))
    buf += encode_uint32(6, int(info.get("fan_count", 0)))
    return bytes(buf)


def encode_video_detail(v: Dict[str, Any]) -> bytes:
    """proto.VideoDetail [5466]"""
    now = int(time.time())
    buf = bytearray()
    buf += encode_uint32(1, int(v.get("video_id", 1)))
    buf += encode_string(2, str(v.get("video_url", "")))
    buf += encode_uint32(3, int(v.get("video_type", VideoType.HOTEST)))
    buf += encode_string(4, str(v.get("video_name", "Barbosa Highlight")))
    buf += encode_uint32(5, int(v.get("video_sort_id", 1)))
    buf += encode_string(6, str(v.get("thumbnail_url", "")))
    buf += encode_uint32(7, int(v.get("create_at", now - 3600)))
    buf += encode_uint64(8, int(v.get("hit_count", 100)))
    buf += encode_uint64(9, int(v.get("streamer_account_id", 20001)))
    buf += encode_string(10, str(v.get("streamer_nickname", "Barbosa_Bot")))
    buf += encode_uint32(11, int(v.get("streamer_sex", GenderType.MAN)))
    buf += encode_string(12, str(v.get("create_date", "2026-11-12")))
    return bytes(buf)


def decode_personal_video_zone_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSGetPersonalVideoZoneReq [5458]"""
    fields = decode_proto(raw_body)
    return {
        "other_account_id": get_varint(fields, 1, 0),
        "video_type": get_varint(fields, 2, VideoType.ALL),
        "page_id": get_varint(fields, 3, 0),
    }


def encode_personal_video_zone_res(zone: Dict[str, Any]) -> bytes:
    """proto.CSGetPersonalVideoZoneRes [5459]"""
    buf = bytearray()
    buf += encode_string(1, str(zone.get("nickname", "Barbosa_Bot")))
    buf += encode_uint32(2, int(zone.get("sex", GenderType.MAN)))
    buf += encode_uint32(3, int(zone.get("fan_count", 1250)))
    buf += encode_uint32(4, int(zone.get("head_pic", 902000001)))
    buf += encode_uint32(5, int(zone.get("follower_type", FollowerType.YES)))
    for v in zone.get("video_list", ()):
        buf += encode_submessage(6, encode_video_detail(v))
    return bytes(buf)


def decode_recommended_video_list_req(raw_body: bytes) -> int:
    """proto.CSGetRecommendedVideoListReq [5460]"""
    return get_varint(decode_proto(raw_body), 1, 0)


def encode_recommended_video_list_res(videos: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSGetRecommendedVideoListRes [5461]"""
    buf = bytearray()
    for v in videos:
        buf += encode_submessage(1, encode_video_detail(v))
    return bytes(buf)


def decode_all_video_list_by_type_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSGetAllVideoListByVideoTypeReq [5462]"""
    fields = decode_proto(raw_body)
    return {
        "video_type": get_varint(fields, 1, VideoType.ALL),
        "page_id": get_varint(fields, 2, 0),
    }


def encode_all_video_list_by_type_res(videos: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSGetAllVideoListByVideoTypeRes [5463]"""
    buf = bytearray()
    for v in videos:
        buf += encode_submessage(1, encode_video_detail(v))
    return bytes(buf)


def decode_live_table_names_req(raw_body: bytes) -> str:
    """proto.CSGetLiveTableNamesReq [5467]"""
    if not raw_body:
        return "en"
    return get_string(decode_proto(raw_body), 1, "en") or "en"


def encode_live_table_name_desc(tab: Dict[str, Any]) -> bytes:
    """proto.LiveTableNameDesc [5749]"""
    buf = bytearray()
    buf += encode_uint32(1, int(tab.get("id", VideoType.HOTEST)))
    buf += encode_string(2, str(tab.get("content", "Hottest")))
    buf += encode_string(3, str(tab.get("language", "en")))
    return bytes(buf)


def encode_live_table_names_res(tabs: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSGetLiveTableNamesRes [5468]"""
    buf = bytearray()
    for t in tabs:
        buf += encode_submessage(1, encode_live_table_name_desc(t))
    return bytes(buf)


def decode_update_video_hit_count_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSUpdateVideoHitCountReq [5464]"""
    fields = decode_proto(raw_body)
    return {
        "streamer_id": get_varint(fields, 1, 0),
        "video_id": get_varint(fields, 2, 0),
    }


def decode_update_account_follow_stat_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSUpdateAccountFollowStatReq [5465]"""
    fields = decode_proto(raw_body)
    return {
        "streamer_id": get_varint(fields, 1, 0),
        "follower_type": get_varint(fields, 2, FollowerType.YES),
    }


# ---------------------------------------------------------------------------
# GiftRank Encoders & Decoders
# ---------------------------------------------------------------------------

def encode_client_gift_rank_desc(desc: Dict[str, Any]) -> bytes:
    """proto.ClientGiftRankDesc [5432]"""
    now = int(time.time())
    buf = bytearray()
    buf += encode_uint32(1, int(desc.get("rank_id", 1)))
    buf += encode_string(2, str(desc.get("rank_name", "Barbosa Gift Ranking")))
    buf += encode_int64(3, int(desc.get("open_time", now - 86400)))
    buf += encode_int64(4, int(desc.get("close_time", now + 30 * 86400)))
    buf += encode_bool(5, bool(desc.get("is_time_show", True)))
    buf += encode_uint32(6, int(desc.get("giver_item_id", 203000001)))
    buf += encode_uint32(7, int(desc.get("receiver_item_id", 204000001)))
    buf += encode_uint32(8, int(desc.get("gift_ratio", 10)))
    return bytes(buf)


def encode_gift_reward_desc(rw: Dict[str, Any]) -> bytes:
    """proto.GiftRewardDesc [5706]"""
    buf = bytearray()
    buf += encode_uint32(1, int(rw.get("rank_tab_id", GiftRankType.RECEIVER)))
    buf += encode_uint32(2, int(rw.get("gift_item_num", 10)))
    buf += encode_uint32(3, int(rw.get("reward_item_type", AwardType.GEMS)))
    buf += encode_string(4, str(rw.get("reward_item_name", "Diamonds")))
    buf += encode_uint32(5, int(rw.get("reward_item_id", 0)))
    buf += encode_uint32(6, int(rw.get("reward_item_num", 50)))
    return bytes(buf)


def encode_gift_reward_detail(detail: Dict[str, Any]) -> bytes:
    """proto.GiftRewardDetail [5447]"""
    buf = bytearray()
    buf += encode_uint32(1, int(detail.get("gift_rank_type", GiftRankType.RECEIVER)))
    for rw in detail.get("gift_rewards", ()):
        buf += encode_submessage(2, encode_gift_reward_desc(rw))
    return bytes(buf)


def encode_get_gift_rank_desc_res(
    gift_rank_desc: Dict[str, Any],
    gift_reward_detail: Iterable[Dict[str, Any]],
) -> bytes:
    """proto.CSGetGiftRankDescRes [5433]"""
    buf = bytearray()
    buf += encode_submessage(1, encode_client_gift_rank_desc(gift_rank_desc))
    for det in gift_reward_detail:
        buf += encode_submessage(2, encode_gift_reward_detail(det))
    return bytes(buf)


def decode_gift_rank_reward_info_req(raw_body: bytes) -> int:
    """proto.CSGetGiftRankRewardInfoReq [5434]"""
    return get_varint(decode_proto(raw_body), 1, 1)


def encode_gift_rank_reward_info_res(
    receiver_rewarded_list: Iterable[int],
    giver_rewarded_list: Iterable[int],
) -> bytes:
    """proto.CSGetGiftRankRewardInfoRes [5435]"""
    buf = bytearray()
    recv = [int(x) for x in receiver_rewarded_list]
    give = [int(x) for x in giver_rewarded_list]
    if recv:
        buf += encode_packed_uint32(1, recv)
    if give:
        buf += encode_packed_uint32(2, give)
    return bytes(buf)


def decode_get_gift_rank_reward_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSGetGiftRankRewardReq [5436]"""
    fields = decode_proto(raw_body)
    return {
        "rank_id": get_varint(fields, 1, 1),
        "gift_rank_type": get_varint(fields, 2, GiftRankType.RECEIVER),
        "gift_item_num": get_varint(fields, 3, 10),
    }


def encode_get_gift_rank_reward_res(
    award: Dict[str, Any],
    rewarded_list: Iterable[int],
) -> bytes:
    """proto.CSGetGiftRankRewardRes [5437]"""
    buf = bytearray()
    buf += encode_submessage(
        1,
        encode_award_desc(
            award_type=int(award.get("award_type", AwardType.GEMS)),
            award_id=int(award.get("award_id", 0)),
            award_num=int(award.get("award_num", 50)),
        ),
    )
    rl = [int(x) for x in rewarded_list]
    if rl:
        buf += encode_packed_uint32(2, rl)
    return bytes(buf)


# ---------------------------------------------------------------------------
# MysteryBonus & WinnerTakesAll Encoders
# ---------------------------------------------------------------------------

def encode_mystery_bonus_res(
    bonus_max: int = 5000,
    start_time: str = "2026-01-01 00:00:00",
    end_time: str = "2028-12-31 23:59:59",
    start_time_stamp: int = 0,
    end_time_stamp: int = 0,
    bonus_percent: int = 100,
    bonus_topup_times: int = 3,
) -> bytes:
    """proto.CSMysteryBonusRes [5241]"""
    now = int(time.time())
    if not start_time_stamp:
        start_time_stamp = now - 86400
    if not end_time_stamp:
        end_time_stamp = now + 30 * 86400
    buf = bytearray()
    buf += encode_uint32(1, bonus_max)
    buf += encode_string(2, start_time)
    buf += encode_string(3, end_time)
    buf += encode_uint32(4, start_time_stamp)
    buf += encode_uint32(5, end_time_stamp)
    buf += encode_uint32(6, bonus_percent)
    buf += encode_uint32(7, bonus_topup_times)
    return bytes(buf)


def encode_mystery_bonus_spin_res(bonus_percent: int = 100) -> bytes:
    """proto.CSMysteryBonusSpinRes [5242]"""
    return encode_uint32(1, int(bonus_percent))


def encode_winner_takes_all_desc(
    region: str = "DEFAULT",
    chip_cost: int = 100,
    diamond_cost: int = 10,
) -> bytes:
    """proto.WinnerTakesAllDesc [5675]"""
    buf = bytearray()
    buf += encode_string(1, region)
    buf += encode_uint32(2, chip_cost)
    buf += encode_uint32(3, diamond_cost)
    return bytes(buf)


def encode_get_winner_takes_all_info_res(
    account_id: int,
    match_num: int = 3,
    last_update_at: int = 0,
    wta_desc: Optional[Dict[str, Any]] = None,
    refresh_at: int = 0,
) -> bytes:
    """proto.CSGetWinnerTakesAllInfoRes [5182]"""
    now = int(time.time())
    if not last_update_at:
        last_update_at = now - 600
    if not refresh_at:
        refresh_at = now + 86400
    desc = wta_desc or {}
    buf = bytearray()
    buf += encode_uint64(1, int(account_id))
    buf += encode_uint32(2, int(match_num))
    buf += encode_uint32(3, int(last_update_at))
    buf += encode_submessage(
        4,
        encode_winner_takes_all_desc(
            region=str(desc.get("region", "DEFAULT")),
            chip_cost=int(desc.get("chip_cost", 100)),
            diamond_cost=int(desc.get("diamond_cost", 10)),
        ),
    )
    buf += encode_int64(5, int(refresh_at))
    return bytes(buf)


# ---------------------------------------------------------------------------
# CollectionHide & Loadout Encoders / Decoders
# ---------------------------------------------------------------------------

def encode_get_hide_collections_res(item_ids: Iterable[int]) -> bytes:
    """proto.CSGetHideCollectionsRes [5223]"""
    ids = [int(x) for x in item_ids]
    return encode_packed_uint32(1, ids) if ids else b""


def decode_choose_loadout_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSChooseLoadoutReq [5216]"""
    fields = decode_proto(raw_body)
    return {
        "loadouts": get_packed_varints(fields, 1),
        "group_id": get_varint(fields, 2, 0),
    }
