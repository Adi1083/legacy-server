"""
Protobuf serializers and deserializers for Free Fire 1.39 Clan / Guild System.

All ProtoMember tags, wire types, and enum values verified against
D:\\LEGACY\\dump\\dump.cs, global-metadata.dat (v23), and x86 libil2cpp.so:

- proto.ClanInfo:
    1: uint64 clan_id, 2: string clan_name, 3: uint64 create_at,
    4: uint64 captain_id, 5: uint32 clan_level, 6: uint32 capacity,
    7: uint32 member_num, 8: uint32 entry_level, 9: uint32 entry_type,
    10: string clan_logo, 11: string announcement, 12: string slogan,
    13: string region, 14: string misc, 15: string vice_captains,
    16: uint32 honor_point, 17: uint32 race_point, 18: uint64 last_gain_rp_at,
    19: uint64 claim_rp_award_at, 20: uint32 area_id, 21: uint32 play_style
- proto.CSClanInfoBundleRes:
    1: List<proto.ClanInfo> infos
- proto.CSClanInfoReq:
    1: uint64 clan_id, 2: bool ignore_region
- proto.CSClanIDReq / proto.CSClanIDRes / proto.CSJoinClanReq /
  proto.CSDismissClanReq / proto.CSQuitClanReq / proto.CSGetClanNewsReq:
    1: uint64 clan_id
- proto.CSClanNameReq:
    1: string clan_name
- proto.CSRandomClanListReq:
    1: ClanMainType clan_list_type, 2: uint32 area_id, 3: uint32 play_style
- proto.CSCreateClanReq:
    1: string clan_name, 2: uint64 captain_id, 3: string announcement,
    4: string slogan, 5: uint32 currency_type, 6: uint32 entry_type,
    7: uint32 area_id, 8: uint32 play_style
- proto.ClanMemberWithAccountInfo (NOTE: tag 2 is skipped!):
    1: AccountInfoBasic basic_info, 3: uint64 clan_id, 4: uint32 member_type,
    5: uint64 join_at, 6: string region, 7: uint32 honor_point,
    8: uint32 race_point, 9: uint64 last_gain_rp_at
- proto.ClanMemberListWithAccountInfo:
    1: List<proto.ClanMemberWithAccountInfo> member_list
- proto.CSClanMemberRes:
    1: uint64 clan_id, 2: uint64 member_id, 3: uint32 member_type,
    4: uint64 join_at, 5: uint32 honor_point, 6: uint32 race_point,
    7: uint64 last_gain_rp_at
- proto.CSClanMemberListRes:
    1: List<proto.CSClanMemberRes> member_list
- proto.ClanNewsContent:
    1: uint64 account_id, 2: uint32 member_type, 3: uint32 level
- proto.ClanNews:
    1: NewsType type, 2: ClanNewsContent content, 3: uint64 update_time
- proto.CSClanNewsRes:
    1: List<proto.ClanNews> news
- proto.AwardDesc:
    1: AwardType award_type, 2: uint32 award_id, 3: uint32 award_num,
    4: uint32 award_max_num, 5: uint32 award_expire_time
- proto.ClanSignInRewardsDesc:
    1: uint32 sign_in_group, 2: uint32 clan_level, 3: uint32 weekday,
    4: AwardDesc award
- proto.ClanSignInRewardItem:
    1: ClanSignInRewardsDesc desc, 2: uint32 status
- proto.CSClanSignInRes:
    1: List<proto.ClanSignInRewardItem> rewards, 2: bool is_newcomer
- proto.CSGetClanSignInRewardsByLevelReq:
    1: uint32 clan_level, 2: string clan_region
- proto.ClanRaceOpeningInfoDesc:
    1: string region, 2: uint32 start_week_day, 3: string start_time,
    4: uint32 end_week_day, 5: string end_time
- proto.ClanRaceRewardsDesc:
    1: uint32 stage_id, 2: uint32 min_race_point, 3: uint32 race_point_cost,
    4: uint32 reward_honor, 5: AwardDesc all_member_award, 6: AwardDesc unlock_award
- proto.RaceAwardExchange:
    1: uint64 account_id, 2: uint32 stage, 3: uint64 exchange_at
- proto.ClanRaceCloseDesc:
    1: string region, 2: string start_time, 3: string end_time
- proto.CSGetClanRaceInfoRes:
    1: ClanRaceOpeningInfoDesc opening_info, 2: uint32 stage, 3: bool is_open,
    4: List<ClanRaceRewardsDesc> rewards, 5: uint32 race_point,
    6: uint32 latest_race_week_id, 7: List<RaceAwardExchange> exchange_info,
    8: ClanRaceCloseDesc race_close_info, 9: int64 timezone_offset_secs
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, List, Optional

from .decoder import (
    decode_proto,
    get_bool,
    get_string,
    get_varint,
)
from .encoder import (
    encode_bool,
    encode_int32,
    encode_int64,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)


# ---------------------------------------------------------------------------
# Free Fire 1.39 Clan Enums (verified from global-metadata.dat)
# ---------------------------------------------------------------------------
class MemberType:
    NONE = 0
    NORMAL_MEMBER = 1
    VICE_CAPTAIN = 2
    CAPTAIN = 3


class EntryType:
    NONE = 0
    MANUALLY = 1
    AUTO = 2


class ClanMainType:
    NONE = 0
    REGION = 1
    AREA = 2
    PLAY_STYLE = 3


class ClanSignInRewardStatus:
    NOT_SIGNED = 0
    SIGNED = 1
    CLAIMED = 2


class NewsType:
    NONE = 0
    JOIN = 1
    CHANGE_TYPE = 2
    EP_BUNDLE = 3
    IAP = 4
    LEVEL_UP = 5
    OTHERS = 6


class AwardType:
    NONE = 0
    ITEM = 1
    COINS = 2
    GEMS = 3
    SKILL = 4
    EXP = 5
    ACTIVENESS = 6


# ---------------------------------------------------------------------------
# Request Decoders
# ---------------------------------------------------------------------------
def decode_clan_id_req(raw: bytes) -> Dict[str, int]:
    """Decode CSClanIDReq / CSGetClanNewsReq / CSJoinClanReq / CSQuitClanReq / CSDismissClanReq."""
    f = decode_proto(raw)
    return {"clan_id": get_varint(f, 1, 0)}


def decode_clan_info_req(raw: bytes) -> Dict[str, Any]:
    """Decode proto.CSClanInfoReq (1: clan_id, 2: ignore_region)."""
    f = decode_proto(raw)
    return {
        "clan_id": get_varint(f, 1, 0),
        "ignore_region": get_bool(f, 2, False),
    }


def decode_clan_name_req(raw: bytes) -> Dict[str, str]:
    """Decode proto.CSClanNameReq (1: clan_name)."""
    f = decode_proto(raw)
    return {"clan_name": get_string(f, 1, "")}


def decode_random_clan_list_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSRandomClanListReq (1: clan_list_type, 2: area_id, 3: play_style)."""
    f = decode_proto(raw)
    return {
        "clan_list_type": get_varint(f, 1, ClanMainType.NONE),
        "area_id": get_varint(f, 2, 0),
        "play_style": get_varint(f, 3, 0),
    }


def decode_create_clan_req(raw: bytes) -> Dict[str, Any]:
    """Decode proto.CSCreateClanReq (tags 1..8)."""
    f = decode_proto(raw)
    return {
        "clan_name": get_string(f, 1, ""),
        "captain_id": get_varint(f, 2, 0),
        "announcement": get_string(f, 3, ""),
        "slogan": get_string(f, 4, ""),
        "currency_type": get_varint(f, 5, 0),
        "entry_type": get_varint(f, 6, EntryType.AUTO),
        "area_id": get_varint(f, 7, 1),
        "play_style": get_varint(f, 8, 1),
    }


def decode_modify_clan_info_req(raw: bytes) -> Dict[str, Any]:
    """Decode proto.CSModifyClanInfoReq (tags 1..6)."""
    f = decode_proto(raw)
    return {
        "clan_id": get_varint(f, 1, 0),
        "announcement": get_string(f, 2, "") if 2 in f else None,
        "slogan": get_string(f, 3, "") if 3 in f else None,
        "entry_type": get_varint(f, 4, 0) if 4 in f else None,
        "area_id": get_varint(f, 5, 0) if 5 in f else None,
        "play_style": get_varint(f, 6, 0) if 6 in f else None,
    }


def decode_modify_clan_name_req(raw: bytes) -> Dict[str, Any]:
    """Decode proto.CSModifyClanNameReq (1: clan_id, 2: clan_name)."""
    f = decode_proto(raw)
    return {
        "clan_id": get_varint(f, 1, 0),
        "clan_name": get_string(f, 2, ""),
    }


def decode_get_clan_signin_rewards_req(raw: bytes) -> Dict[str, Any]:
    """Decode proto.CSGetClanSignInRewardsByLevelReq (1: clan_level, 2: clan_region)."""
    f = decode_proto(raw)
    return {
        "clan_level": get_varint(f, 1, 1),
        "clan_region": get_string(f, 2, "DEFAULT"),
    }


def decode_claim_signin_reward_req(raw: bytes) -> Dict[str, int]:
    """Decode ClaimSignInReward request (weekday / day index on tag 1)."""
    f = decode_proto(raw)
    return {"weekday": get_varint(f, 1, 0)}


def decode_process_join_clan_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSProcessJoinClanReq (1: applicant_id, 2: clan_id)."""
    f = decode_proto(raw)
    return {
        "applicant_id": get_varint(f, 1, 0),
        "clan_id": get_varint(f, 2, 0),
    }


def decode_invite_to_clan_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSInviteToClanReq (1: invitee_id)."""
    f = decode_proto(raw)
    return {"invitee_id": get_varint(f, 1, 0)}


def decode_process_invite_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSProcessInviteToClanReq (1: inviter_id, 2: clan_id)."""
    f = decode_proto(raw)
    return {
        "inviter_id": get_varint(f, 1, 0),
        "clan_id": get_varint(f, 2, 0),
    }


def decode_change_member_type_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSChangeMemberTypeReq (1: changee_id, 2: target_type)."""
    f = decode_proto(raw)
    return {
        "changee_id": get_varint(f, 1, 0),
        "target_type": get_varint(f, 2, MemberType.NORMAL_MEMBER),
    }


def decode_reassign_captain_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSReassignCaptainReq (1: reassignee_id)."""
    f = decode_proto(raw)
    return {"reassignee_id": get_varint(f, 1, 0)}


def decode_remove_clan_member_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSRemoveClanMemberReq (1: clan_id, 2: removee_id)."""
    f = decode_proto(raw)
    return {
        "clan_id": get_varint(f, 1, 0),
        "removee_id": get_varint(f, 2, 0),
    }


def decode_exchange_award_with_rp_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSExchangeAwardWithRPReq (1: clan_id, 2: stage)."""
    f = decode_proto(raw)
    return {
        "clan_id": get_varint(f, 1, 0),
        "stage": get_varint(f, 2, 1),
    }


def decode_draw_lucky_bag_req(raw: bytes) -> Dict[str, int]:
    """Decode proto.CSDrawClanLuckyBagReq (1: clan_id, 2: bag_id)."""
    f = decode_proto(raw)
    return {
        "clan_id": get_varint(f, 1, 0),
        "bag_id": get_varint(f, 2, 0),
    }


# ---------------------------------------------------------------------------
# AccountInfoBasic Encoder (tags 1..29 verified from global-metadata.dat)
# ---------------------------------------------------------------------------
def encode_account_info_basic(player: Dict[str, Any]) -> bytes:
    """Encode proto.AccountInfoBasic (tags 1..29)."""
    aid = int(player.get("account_id", 10001))
    nickname = str(player.get("nickname", f"Player_{aid}"))
    region = str(player.get("region", "DEFAULT"))
    buf = bytearray()
    buf += encode_uint64(1, aid)
    buf += encode_uint32(2, int(player.get("account_type", 1)))
    buf += encode_string(3, nickname)
    buf += encode_string(4, str(player.get("external_id", aid)))
    buf += encode_string(5, region)
    buf += encode_uint32(6, int(player.get("level", 60)))
    buf += encode_uint32(7, int(player.get("exp", 99999)))
    buf += encode_uint32(8, int(player.get("external_type", 1)))
    buf += encode_string(9, str(player.get("external_name", nickname)))
    buf += encode_string(10, str(player.get("external_icon", "")))
    buf += encode_uint32(11, int(player.get("banner_id", 901000001)))
    buf += encode_uint32(12, int(player.get("head_pic", 902000001)))
    buf += encode_string(13, str(player.get("clan_name", "")))
    buf += encode_uint32(14, int(player.get("rank", 315)))
    buf += encode_uint32(15, int(player.get("ranking_points", 3250)))
    buf += encode_uint32(16, int(player.get("role", 0)))
    buf += encode_bool(17, bool(player.get("has_elite_pass", True)))
    buf += encode_uint32(18, int(player.get("badge_cnt", 100)))
    buf += encode_uint32(19, int(player.get("badge_id", 1)))
    buf += encode_uint32(20, int(player.get("season_id", 10)))
    buf += encode_uint32(21, int(player.get("liked", 100)))
    buf += encode_bool(22, bool(player.get("is_deleted", False)))
    buf += encode_bool(23, bool(player.get("show_rank", True)))
    buf += encode_int64(24, int(player.get("last_login_at", int(time.time()))))
    buf += encode_uint64(25, int(player.get("external_uid", aid)))
    buf += encode_int64(26, int(player.get("return_at", 0)))
    buf += encode_string(27, str(player.get("championship_team_name", "")))
    buf += encode_uint32(28, int(player.get("championship_team_member_num", 0)))
    buf += encode_uint64(29, int(player.get("championship_team_id", 0)))
    return bytes(buf)


def encode_account_info_basic_bundle_res(players: Iterable[Dict[str, Any]]) -> bytes:
    """Encode proto.AccountInfoBasicBundleRes (1: List<AccountInfoBasic> infos)."""
    buf = bytearray()
    for p in players:
        buf += encode_submessage(1, encode_account_info_basic(p))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Core Clan Encoders
# ---------------------------------------------------------------------------
def encode_clan_info(clan: Dict[str, Any]) -> bytes:
    """
    Encode proto.ClanInfo (tags 1..21).

    Note from COW.ClanInfo.op_Implicit & GetExtendTimeFromMiscellaneous:
    - misc (tag 14) is parsed via LitJson.JsonMapper.ToObject expecting {"extended_times": int}.
    - vice_captains (tag 15) is split via String.Split(',') into uint64 IDs if non-empty.
    """
    extended_times = int(clan.get("extended_times", 0))
    misc = clan.get("misc")
    if misc is None:
        misc = json.dumps({"extended_times": extended_times}, separators=(",", ":"))

    vice = clan.get("vice_captains", "")
    if isinstance(vice, (list, tuple, set)):
        vice_str = ",".join(str(int(x)) for x in vice if int(x) > 0)
    else:
        vice_str = str(vice or "")

    buf = bytearray()
    buf += encode_uint64(1, int(clan.get("clan_id", 50001)))
    buf += encode_string(2, str(clan.get("clan_name", "BARBOSA")))
    buf += encode_uint64(3, int(clan.get("create_at", 1570000000)))
    buf += encode_uint64(4, int(clan.get("captain_id", 10001)))
    buf += encode_uint32(5, int(clan.get("clan_level", 4)))
    buf += encode_uint32(6, int(clan.get("capacity", 35)))
    buf += encode_uint32(7, int(clan.get("member_num", 1)))
    buf += encode_uint32(8, int(clan.get("entry_level", 1)))
    buf += encode_uint32(9, int(clan.get("entry_type", EntryType.AUTO)))
    buf += encode_string(10, str(clan.get("clan_logo", "")))
    buf += encode_string(11, str(clan.get("announcement", "")))
    buf += encode_string(12, str(clan.get("slogan", "")))
    buf += encode_string(13, str(clan.get("region", "DEFAULT")))
    buf += encode_string(14, str(misc))
    buf += encode_string(15, vice_str)
    buf += encode_uint32(16, int(clan.get("honor_point", 0)))
    buf += encode_uint32(17, int(clan.get("race_point", 0)))
    buf += encode_uint64(18, int(clan.get("last_gain_rp_at", 0)))
    buf += encode_uint64(19, int(clan.get("claim_rp_award_at", 0)))
    buf += encode_uint32(20, int(clan.get("area_id", 1)))
    buf += encode_uint32(21, int(clan.get("play_style", 1)))
    return bytes(buf)


def encode_clan_info_bundle_res(clans: Iterable[Dict[str, Any]]) -> bytes:
    """Encode proto.CSClanInfoBundleRes (1: List<proto.ClanInfo> infos)."""
    buf = bytearray()
    for c in clans:
        buf += encode_submessage(1, encode_clan_info(c))
    return bytes(buf)


def encode_clan_id_res(clan_id: int) -> bytes:
    """Encode proto.CSClanIDRes (1: uint64 clan_id)."""
    return encode_uint64(1, int(clan_id))


def encode_clan_member_with_account_info(member: Dict[str, Any]) -> bytes:
    """
    Encode proto.ClanMemberWithAccountInfo.
    Exact tags: 1: basic_info, 3: clan_id, 4: member_type, 5: join_at,
                6: region, 7: honor_point, 8: race_point, 9: last_gain_rp_at.
    (Tag 2 is skipped in Free Fire 1.39 metadata.)
    """
    basic = member.get("basic_info", member)
    buf = bytearray()
    buf += encode_submessage(1, encode_account_info_basic(basic))
    buf += encode_uint64(3, int(member.get("clan_id", 0)))
    buf += encode_uint32(4, int(member.get("member_type", MemberType.NORMAL_MEMBER)))
    buf += encode_uint64(5, int(member.get("join_at", 1570000000)))
    buf += encode_string(6, str(member.get("region", basic.get("region", "DEFAULT"))))
    buf += encode_uint32(7, int(member.get("honor_point", 0)))
    buf += encode_uint32(8, int(member.get("race_point", 0)))
    buf += encode_uint64(9, int(member.get("last_gain_rp_at", 0)))
    return bytes(buf)


def encode_clan_member_list_with_account_info(members: Iterable[Dict[str, Any]]) -> bytes:
    """Encode proto.ClanMemberListWithAccountInfo (1: List<ClanMemberWithAccountInfo> member_list)."""
    buf = bytearray()
    for m in members:
        buf += encode_submessage(1, encode_clan_member_with_account_info(m))
    return bytes(buf)


def encode_cs_clan_member_res(member: Dict[str, Any]) -> bytes:
    """Encode proto.CSClanMemberRes (tags 1..7)."""
    buf = bytearray()
    buf += encode_uint64(1, int(member.get("clan_id", 0)))
    buf += encode_uint64(2, int(member.get("member_id", member.get("account_id", 0))))
    buf += encode_uint32(3, int(member.get("member_type", MemberType.NORMAL_MEMBER)))
    buf += encode_uint64(4, int(member.get("join_at", 1570000000)))
    buf += encode_uint32(5, int(member.get("honor_point", 0)))
    buf += encode_uint32(6, int(member.get("race_point", 0)))
    buf += encode_uint64(7, int(member.get("last_gain_rp_at", 0)))
    return bytes(buf)


def encode_cs_clan_member_list_res(members: Iterable[Dict[str, Any]]) -> bytes:
    """Encode proto.CSClanMemberListRes (1: List<CSClanMemberRes> member_list)."""
    buf = bytearray()
    for m in members:
        buf += encode_submessage(1, encode_cs_clan_member_res(m))
    return bytes(buf)


def encode_extend_clan_scale_res(clan_id: int, capacity: int, extended_times: int) -> bytes:
    """Encode proto.CSExtendClanScaleRes (1: clan_id, 2: capacity, 3: extended_times)."""
    buf = bytearray()
    buf += encode_uint64(1, int(clan_id))
    buf += encode_uint32(2, int(capacity))
    buf += encode_uint32(3, int(extended_times))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Clan News Encoders
# ---------------------------------------------------------------------------
def encode_clan_news_content(content: Dict[str, Any]) -> bytes:
    """Encode proto.ClanNewsContent (1: account_id, 2: member_type, 3: level)."""
    buf = bytearray()
    buf += encode_uint64(1, int(content.get("account_id", 10001)))
    buf += encode_uint32(2, int(content.get("member_type", MemberType.NORMAL_MEMBER)))
    buf += encode_uint32(3, int(content.get("level", 1)))
    return bytes(buf)


def encode_clan_news(news_item: Dict[str, Any]) -> bytes:
    """Encode proto.ClanNews (1: NewsType type, 2: ClanNewsContent content, 3: uint64 update_time)."""
    content = news_item.get("content") or {
        "account_id": news_item.get("account_id", 10001),
        "member_type": news_item.get("member_type", MemberType.NORMAL_MEMBER),
        "level": news_item.get("level", 1),
    }
    buf = bytearray()
    buf += encode_int32(1, int(news_item.get("type", NewsType.JOIN)))
    buf += encode_submessage(2, encode_clan_news_content(content))
    buf += encode_uint64(3, int(news_item.get("update_time", int(time.time()))))
    return bytes(buf)


def encode_clan_news_res(news_list: Iterable[Dict[str, Any]]) -> bytes:
    """Encode proto.CSClanNewsRes (1: List<proto.ClanNews> news)."""
    buf = bytearray()
    for n in news_list:
        buf += encode_submessage(1, encode_clan_news(n))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Clan Sign-In Encoders
# ---------------------------------------------------------------------------
def encode_award_desc(award: Dict[str, Any]) -> bytes:
    """Encode proto.AwardDesc (1: award_type, 2: award_id, 3: award_num, 4: award_max_num, 5: award_expire_time)."""
    buf = bytearray()
    buf += encode_int32(1, int(award.get("award_type", AwardType.COINS)))
    buf += encode_uint32(2, int(award.get("award_id", 0)))
    buf += encode_uint32(3, int(award.get("award_num", 0)))
    buf += encode_uint32(4, int(award.get("award_max_num", award.get("award_num", 0))))
    buf += encode_uint32(5, int(award.get("award_expire_time", 0)))
    return bytes(buf)


def encode_clan_signin_rewards_desc(desc: Dict[str, Any]) -> bytes:
    """Encode proto.ClanSignInRewardsDesc (1: sign_in_group, 2: clan_level, 3: weekday, 4: AwardDesc award)."""
    buf = bytearray()
    buf += encode_uint32(1, int(desc.get("sign_in_group", 1)))
    buf += encode_uint32(2, int(desc.get("clan_level", 1)))
    buf += encode_uint32(3, int(desc.get("weekday", 1)))
    buf += encode_submessage(4, encode_award_desc(desc.get("award", {})))
    return bytes(buf)


def encode_clan_signin_reward_item(item: Dict[str, Any]) -> bytes:
    """Encode proto.ClanSignInRewardItem (1: ClanSignInRewardsDesc desc, 2: uint32 status)."""
    desc = item.get("desc", item)
    buf = bytearray()
    buf += encode_submessage(1, encode_clan_signin_rewards_desc(desc))
    buf += encode_uint32(2, int(item.get("status", ClanSignInRewardStatus.NOT_SIGNED)))
    return bytes(buf)


def encode_clan_signin_res(rewards: Iterable[Dict[str, Any]], is_newcomer: bool = False) -> bytes:
    """Encode proto.CSClanSignInRes (1: List<ClanSignInRewardItem> rewards, 2: bool is_newcomer)."""
    buf = bytearray()
    for item in rewards:
        buf += encode_submessage(1, encode_clan_signin_reward_item(item))
    buf += encode_bool(2, bool(is_newcomer))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Clan Race Encoders
# ---------------------------------------------------------------------------
def encode_clan_race_opening_info_desc(info: Dict[str, Any]) -> bytes:
    """Encode proto.ClanRaceOpeningInfoDesc (tags 1..5)."""
    buf = bytearray()
    buf += encode_string(1, str(info.get("region", "DEFAULT")))
    buf += encode_uint32(2, int(info.get("start_week_day", 1)))
    buf += encode_string(3, str(info.get("start_time", "00:00:00")))
    buf += encode_uint32(4, int(info.get("end_week_day", 6)))
    buf += encode_string(5, str(info.get("end_time", "23:59:59")))
    return bytes(buf)


def encode_clan_race_rewards_desc(desc: Dict[str, Any]) -> bytes:
    """Encode proto.ClanRaceRewardsDesc (tags 1..6)."""
    buf = bytearray()
    buf += encode_uint32(1, int(desc.get("stage_id", 1)))
    buf += encode_uint32(2, int(desc.get("min_race_point", 500)))
    buf += encode_uint32(3, int(desc.get("race_point_cost", 100)))
    buf += encode_uint32(4, int(desc.get("reward_honor", 100)))
    buf += encode_submessage(5, encode_award_desc(desc.get("all_member_award", {})))
    buf += encode_submessage(6, encode_award_desc(desc.get("unlock_award", {})))
    return bytes(buf)


def encode_race_award_exchange(ex: Dict[str, Any]) -> bytes:
    """Encode proto.RaceAwardExchange (1: account_id, 2: stage, 3: exchange_at)."""
    buf = bytearray()
    buf += encode_uint64(1, int(ex.get("account_id", 10001)))
    buf += encode_uint32(2, int(ex.get("stage", 1)))
    buf += encode_uint64(3, int(ex.get("exchange_at", int(time.time()))))
    return bytes(buf)


def encode_clan_race_close_desc(info: Dict[str, Any]) -> bytes:
    """Encode proto.ClanRaceCloseDesc (1: region, 2: start_time, 3: end_time)."""
    buf = bytearray()
    buf += encode_string(1, str(info.get("region", "DEFAULT")))
    buf += encode_string(2, str(info.get("start_time", "")))
    buf += encode_string(3, str(info.get("end_time", "")))
    return bytes(buf)


def encode_clan_race_info_res(race_info: Dict[str, Any]) -> bytes:
    """Encode proto.CSGetClanRaceInfoRes (tags 1..9)."""
    buf = bytearray()
    buf += encode_submessage(
        1, encode_clan_race_opening_info_desc(race_info.get("opening_info") or {})
    )
    buf += encode_uint32(2, int(race_info.get("stage", 1)))
    buf += encode_bool(3, bool(race_info.get("is_open", True)))
    for rew in race_info.get("rewards") or []:
        buf += encode_submessage(4, encode_clan_race_rewards_desc(rew))
    buf += encode_uint32(5, int(race_info.get("race_point", 0)))
    buf += encode_uint32(6, int(race_info.get("latest_race_week_id", 1)))
    for ex in race_info.get("exchange_info") or []:
        buf += encode_submessage(7, encode_race_award_exchange(ex))
    if race_info.get("race_close_info"):
        buf += encode_submessage(
            8, encode_clan_race_close_desc(race_info["race_close_info"])
        )
    buf += encode_int64(9, int(race_info.get("timezone_offset_secs", 0)))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Clan Lucky Bags & Leaderboard Info Encoders
# ---------------------------------------------------------------------------
def encode_clan_lucky_bag(bag: Dict[str, Any]) -> bytes:
    """Encode proto.ClanLuckyBag (tags 1..7)."""
    buf = bytearray()
    buf += encode_uint64(1, int(bag.get("clan_id", 50001)))
    buf += encode_uint64(2, int(bag.get("bag_id", 1)))
    buf += encode_uint64(3, int(bag.get("creater_id", 10001)))
    buf += encode_uint64(4, int(bag.get("created_at", int(time.time()))))
    buf += encode_uint32(5, int(bag.get("total_num", 10)))
    buf += encode_uint32(6, int(bag.get("taken_num", 1)))
    buf += encode_uint32(7, int(bag.get("reason", 1)))
    return bytes(buf)


def encode_lucky_bag_draw(draw: Dict[str, Any]) -> bytes:
    """Encode proto.LuckyBagDraw (1: account_id, 2: bag_id, 3: opened_at)."""
    buf = bytearray()
    buf += encode_uint64(1, int(draw.get("account_id", 10001)))
    buf += encode_uint64(2, int(draw.get("bag_id", 1)))
    buf += encode_uint64(3, int(draw.get("opened_at", int(time.time()))))
    return bytes(buf)


def encode_clan_lucky_bag_info_res(
    lucky_bags: Iterable[Dict[str, Any]],
    draws: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """Encode proto.CSGetClanLuckyBagInfoRes (1: List<ClanLuckyBag>, 2: List<LuckyBagDraw>)."""
    buf = bytearray()
    for bag in lucky_bags:
        buf += encode_submessage(1, encode_clan_lucky_bag(bag))
    for draw in (draws or []):
        buf += encode_submessage(2, encode_lucky_bag_draw(draw))
    return bytes(buf)


def encode_draw_clan_lucky_bag_res(account_id: int, bag_id: int, get_token_num: int) -> bytes:
    """Encode proto.CSDrawClanLuckyBagRes (1: account_id, 2: bag_id, 3: get_token_num)."""
    buf = bytearray()
    buf += encode_uint64(1, int(account_id))
    buf += encode_uint64(2, int(bag_id))
    buf += encode_uint32(3, int(get_token_num))
    return bytes(buf)


def encode_clan_week_leaderboard_info_res(main_key: int, next_refresh_time: int) -> bytes:
    """Encode proto.CSGetClanWeekLeaderboardInfoRes (1: int64 main_key, 2: uint32 next_refresh_time)."""
    buf = bytearray()
    buf += encode_int64(1, int(main_key))
    buf += encode_uint32(2, int(next_refresh_time))
    return bytes(buf)
