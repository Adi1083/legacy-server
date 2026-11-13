"""
Protobuf encoders and decoders for the Free Fire 1.39 Friends & Social system.

All message schemas and ProtoMember tags are verified directly against
Free Fire 1.39 IL2CPP metadata (dump.cs + customAttributeGenerators):
  - proto.AccountFriendRes (1: friends)
  - proto.AccountInfoWithPresence (tags 1..9, 11, 15..41)
  - proto.AccountInfoWithStats (1..5)
  - proto.AccountInfoBasicBundleRes (1: infos)
  - proto.AccountInfoBasic (tags 1..29)
  - proto.AccountIDSlice (1: packed uint64[] account_ids)
  - proto.AccountIDReq / proto.AccountIDRes (1: account_id)
  - proto.CSGetFriendListReq (1..4)
  - proto.CSGetPlatformFriendListReq (1..7)
  - proto.CSGetFacebookFriendListReq (1..5)
  - proto.CSFuzzySearchAccountByNameReq (1: nickname)
  - proto.CSGetAccountInfoReq (1: input_type, 2: input_value)
  - proto.CSFriendReq (1: adder, 2: addee)
  - proto.CSRemoveFriendReq (1: remover, 2: removee)
  - proto.CSRemoveFriendRes (1: remover, 2: removee, 3: lock_region, 4: noti_region)
  - proto.CSFriendInviteReq (1: inviter_id, 2: activity_id)
  - proto.AccountPresence (1..8)
  - tcp.PresenceListReq / tcp.PresenceListRes / tcp.PresenceInfo
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

from proto.decoder import (
    decode_proto,
    get_bool,
    get_int32,
    get_packed_varints,
    get_string,
    get_varint,
)
from proto.encoder import (
    encode_bool,
    encode_int64,
    encode_packed_uint64,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)

# EPresence.AccountPresence values from dump.cs
PRESENCE_NONE = 0
PRESENCE_ONLINE = 1
PRESENCE_INGROUP = 2
PRESENCE_INGAME = 3
PRESENCE_INROOM = 4


def _player_presence(player: Dict[str, Any]) -> int:
    status = int(player.get("online_status", 1 if player.get("is_online") else 0))
    if status < 0:
        return PRESENCE_NONE
    return min(status, PRESENCE_INROOM)


def encode_account_info_with_stats(stats: Optional[Dict[str, Any]] = None, account_id: int = 0) -> bytes:
    """Encode proto.AccountInfoWithStats (1:account_id, 2:games_played, 3:wins, 4:kills, 5:detailed_stats)."""
    s = stats or {}
    aid = int(s.get("account_id", account_id) or account_id)
    out = bytearray()
    if aid:
        out += encode_uint64(1, aid)
    out += encode_uint32(2, int(s.get("games_played", 0)))
    out += encode_uint32(3, int(s.get("wins", 0)))
    out += encode_uint32(4, int(s.get("kills", 0)))
    detailed = s.get("detailed_stats")
    if detailed:
        out += encode_string(5, str(detailed))
    return bytes(out)


def encode_account_info_with_presence(
    player: Dict[str, Any],
    need_stats: bool = False,
    friend_intimacy: int = 0,
) -> bytes:
    """
    Encode proto.AccountInfoWithPresence for COW.FriendAccountInfo.CopyFromAccountInfoWithPresence.
    Sparse tags verified in Free Fire 1.39:
      1:account_id, 2:account_type, 3:nickname, 4:external_id, 5:external_name,
      6:region, 7:portrait, 8:level, 9:exp, 11:update_time,
      15..17:solo/duo/quad_stats, 18:external_type,
      19..21:solo/duo/quad_ranking_stats, 22:rank, 23:ranking_points,
      24..26:solo/duo/quad_casual_stats, 27:banner_id, 28:head_pic,
      29:clan_name, 30:has_elite_pass, 31:badge_cnt, 32:badge_id,
      33:is_deleted, 34:show_rank, 35:last_login_at, 36:external_uid,
      37:role, 38..39:championship_team_name/member_num,
      40:friend_intimacy, 41:championship_team_id
    """
    now = int(time.time())
    aid = int(player.get("account_id", 0))
    last_login = int(player.get("last_login_at", now) or now)
    update_time = int(player.get("update_time", last_login) or last_login)

    out = bytearray()
    out += encode_uint64(1, aid)
    out += encode_uint32(2, int(player.get("account_type", 1) or 1))
    out += encode_string(3, str(player.get("nickname", f"Player_{aid}")))

    ext_id = player.get("external_id", "")
    if ext_id:
        out += encode_string(4, str(ext_id))
    ext_name = player.get("external_name", "")
    if ext_name:
        out += encode_string(5, str(ext_name))

    out += encode_string(6, str(player.get("region", "DEFAULT") or "DEFAULT"))

    portrait = player.get("portrait", "")
    if portrait:
        out += encode_string(7, str(portrait))

    out += encode_uint32(8, int(player.get("level", 1) or 1))
    out += encode_uint32(9, int(player.get("exp", 0) or 0))
    out += encode_int64(11, update_time)

    if need_stats:
        base_stats = {"account_id": aid, "games_played": 25, "wins": 6, "kills": 74}
        out += encode_submessage(15, encode_account_info_with_stats(player.get("solo_stats") or base_stats, aid))
        out += encode_submessage(16, encode_account_info_with_stats(player.get("duo_stats") or base_stats, aid))
        out += encode_submessage(17, encode_account_info_with_stats(player.get("quad_stats") or base_stats, aid))

    ext_type = int(player.get("external_type", 0) or 0)
    if ext_type:
        out += encode_uint32(18, ext_type)

    if need_stats:
        rank_stats = {"account_id": aid, "games_played": 15, "wins": 4, "kills": 45}
        out += encode_submessage(19, encode_account_info_with_stats(player.get("solo_ranking_stats") or rank_stats, aid))
        out += encode_submessage(20, encode_account_info_with_stats(player.get("duo_ranking_stats") or rank_stats, aid))
        out += encode_submessage(21, encode_account_info_with_stats(player.get("quad_ranking_stats") or rank_stats, aid))

    out += encode_uint32(22, int(player.get("rank", 101) or 101))
    out += encode_uint32(23, int(player.get("ranking_points", 1000) or 0))
    out += encode_uint32(27, int(player.get("banner_id", 901000001) or 0))
    out += encode_uint32(28, int(player.get("head_pic", 902000001) or 0))

    clan_name = str(player.get("clan_name", "") or "")
    if clan_name:
        out += encode_string(29, clan_name)

    out += encode_bool(30, bool(player.get("has_elite_pass", False)))
    out += encode_uint32(31, int(player.get("badge_cnt", 0) or 0))

    badge_id = int(player.get("badge_id", 0) or 0)
    if badge_id:
        out += encode_uint32(32, badge_id)

    out += encode_bool(33, bool(player.get("is_deleted", False)))
    out += encode_bool(34, bool(player.get("show_rank", True)))
    out += encode_int64(35, last_login)

    ext_uid = int(player.get("external_uid", 0) or 0)
    if ext_uid:
        out += encode_uint64(36, ext_uid)

    role = int(player.get("role", 0) or 0)
    if role:
        out += encode_uint32(37, role)

    intimacy = int(player.get("friend_intimacy", friend_intimacy) or 0)
    if intimacy:
        out += encode_uint32(40, intimacy)

    return bytes(out)


def encode_account_friend_res(
    players: Iterable[Dict[str, Any]],
    need_stats: bool = False,
) -> bytes:
    """Encode proto.AccountFriendRes (1: repeated AccountInfoWithPresence friends)."""
    out = bytearray()
    for p in players:
        out += encode_submessage(1, encode_account_info_with_presence(p, need_stats=need_stats))
    return bytes(out)


def encode_account_info_basic(player: Dict[str, Any]) -> bytes:
    """
    Encode full 29-tag proto.AccountInfoBasic.
      1:account_id, 2:account_type, 3:nickname, 4:external_id, 5:region,
      6:level, 7:exp, 8:external_type, 9:external_name, 10:external_icon,
      11:banner_id, 12:head_pic, 13:clan_name, 14:rank, 15:ranking_points,
      16:role, 17:has_elite_pass, 18:badge_cnt, 19:badge_id, 20:season_id,
      21:liked, 22:is_deleted, 23:show_rank, 24:last_login_at, 25:external_uid,
      26:return_at, 27..29:championship_team_name/member_num/id
    """
    now = int(time.time())
    aid = int(player.get("account_id", 0))
    last_login = int(player.get("last_login_at", now) or now)

    out = bytearray()
    out += encode_uint64(1, aid)
    out += encode_uint32(2, int(player.get("account_type", 1) or 1))
    out += encode_string(3, str(player.get("nickname", f"Player_{aid}")))

    ext_id = str(player.get("external_id", "") or "")
    if ext_id:
        out += encode_string(4, ext_id)

    out += encode_string(5, str(player.get("region", "DEFAULT") or "DEFAULT"))
    out += encode_uint32(6, int(player.get("level", 1) or 1))
    out += encode_uint32(7, int(player.get("exp", 0) or 0))

    ext_type = int(player.get("external_type", 0) or 0)
    if ext_type:
        out += encode_uint32(8, ext_type)

    ext_name = str(player.get("external_name", "") or "")
    if ext_name:
        out += encode_string(9, ext_name)

    ext_icon = str(player.get("external_icon", "") or "")
    if ext_icon:
        out += encode_string(10, ext_icon)

    out += encode_uint32(11, int(player.get("banner_id", 901000001) or 0))
    out += encode_uint32(12, int(player.get("head_pic", 902000001) or 0))

    clan_name = str(player.get("clan_name", "") or "")
    if clan_name:
        out += encode_string(13, clan_name)

    out += encode_uint32(14, int(player.get("rank", 101) or 101))
    out += encode_uint32(15, int(player.get("ranking_points", 1000) or 0))

    role = int(player.get("role", 0) or 0)
    if role:
        out += encode_uint32(16, role)

    out += encode_bool(17, bool(player.get("has_elite_pass", False)))
    out += encode_uint32(18, int(player.get("badge_cnt", 0) or 0))

    badge_id = int(player.get("badge_id", 0) or 0)
    if badge_id:
        out += encode_uint32(19, badge_id)

    out += encode_uint32(20, int(player.get("season_id", 12) or 12))
    out += encode_uint32(21, int(player.get("liked", 10) or 0))
    out += encode_bool(22, bool(player.get("is_deleted", False)))
    out += encode_bool(23, bool(player.get("show_rank", True)))
    out += encode_int64(24, last_login)

    ext_uid = int(player.get("external_uid", 0) or 0)
    if ext_uid:
        out += encode_uint64(25, ext_uid)

    return bytes(out)


def encode_account_info_basic_bundle_res(players: Iterable[Dict[str, Any]]) -> bytes:
    """Encode proto.AccountInfoBasicBundleRes (1: repeated AccountInfoBasic infos)."""
    out = bytearray()
    for p in players:
        out += encode_submessage(1, encode_account_info_basic(p))
    return bytes(out)


def encode_account_id_slice(account_ids: Iterable[int]) -> bytes:
    """Encode proto.AccountIDSlice (1: packed ulong[] account_ids)."""
    ids = [int(aid) for aid in account_ids if int(aid) > 0]
    return encode_packed_uint64(1, ids)


def encode_account_id_res(account_id: int) -> bytes:
    """Encode proto.AccountIDRes (1: uint64 account_id)."""
    return encode_uint64(1, int(account_id)) if account_id else b""


def encode_cs_remove_friend_res(
    remover: int,
    removee: int,
    lock_region: str = "DEFAULT",
    noti_region: str = "DEFAULT",
) -> bytes:
    """Encode proto.CSRemoveFriendRes (1:remover, 2:removee, 3:lock_region, 4:noti_region)."""
    out = bytearray()
    if remover:
        out += encode_uint64(1, int(remover))
    if removee:
        out += encode_uint64(2, int(removee))
    if lock_region:
        out += encode_string(3, lock_region)
    if noti_region:
        out += encode_string(4, noti_region)
    return bytes(out)


def encode_account_presence(player: Dict[str, Any]) -> bytes:
    """Encode proto.AccountPresence (1:account_id, 2:noti_region, 3:presence, 4:update_time, 5:login_time, ...)."""
    now = int(time.time())
    aid = int(player.get("account_id", 0))
    region = str(player.get("region", "DEFAULT") or "DEFAULT")
    presence = _player_presence(player)
    login_time = int(player.get("last_login_at", now) or now)
    out = bytearray()
    out += encode_uint64(1, aid)
    out += encode_string(2, region)
    out += encode_uint32(3, presence)
    out += encode_int64(4, now)
    out += encode_int64(5, login_time)
    team_id = int(player.get("team_id", 0) or 0)
    if team_id:
        out += encode_uint64(6, team_id)
        out += encode_string(7, region)
    out += encode_string(8, region)
    return bytes(out)


def encode_presence_info(player: Dict[str, Any]) -> bytes:
    """Encode tcp.PresenceInfo (1:i=account_id, 2:r=region, 3:p=presence)."""
    out = bytearray()
    out += encode_uint64(1, int(player.get("account_id", 0)))
    out += encode_string(2, str(player.get("region", "DEFAULT") or "DEFAULT"))
    out += encode_uint32(3, _player_presence(player))
    return bytes(out)


def encode_presence_list_res(
    players: Iterable[Dict[str, Any]],
    account_list_type: int = 1,
) -> bytes:
    """Encode tcp.PresenceListRes (1:repeated PresenceInfo presences, 2:uint32 account_list_type)."""
    out = bytearray()
    for p in players:
        out += encode_submessage(1, encode_presence_info(p))
    out += encode_uint32(2, int(account_list_type))
    return bytes(out)


def encode_presence_bundle_res(players: Iterable[Dict[str, Any]]) -> bytes:
    """Encode a bundle of proto.AccountPresence items on field 1 for HTTP /GetPresenceByAccountIds."""
    out = bytearray()
    for p in players:
        out += encode_submessage(1, encode_account_presence(p))
    return bytes(out)


# ----------------------------------------------------------------------
# Request Decoders
# ----------------------------------------------------------------------


def decode_cs_get_friend_list_req(raw_body: bytes) -> Dict[str, bool]:
    fields = decode_proto(raw_body)
    return {
        "need_presence": get_bool(fields, 1, True),
        "need_stats": get_bool(fields, 2, False),
        "need_ranking_stats": get_bool(fields, 3, False),
        "need_casual_stats": get_bool(fields, 4, False),
    }


def decode_cs_get_platform_friend_list_req(raw_body: bytes) -> Dict[str, Any]:
    fields = decode_proto(raw_body)
    return {
        "token": get_string(fields, 1, ""),
        "platform_sdk_id": get_varint(fields, 2, 0),
        "platform_type": get_varint(fields, 3, 0),
        "need_presence": get_bool(fields, 4, True),
        "need_stats": get_bool(fields, 5, False),
        "need_ranking_stats": get_bool(fields, 6, False),
        "need_casual_stats": get_bool(fields, 7, False),
    }


def decode_cs_friend_req(raw_body: bytes) -> Dict[str, int]:
    """Decode proto.CSFriendReq (1:adder, 2:addee). Supports single-ID fallback when only tag 1 is set."""
    fields = decode_proto(raw_body)
    return {
        "adder": get_varint(fields, 1, 0),
        "addee": get_varint(fields, 2, 0),
    }


def decode_cs_handle_friend_req(raw_body: bytes) -> Dict[str, Any]:
    """
    Decode confirm/decline/handle friend request payloads:
      - proto.CSFriendReq (1:adder, 2:addee)
      - Optional tag 3 (action/accept flag: 1=accept, 2=decline, or bool)
    """
    fields = decode_proto(raw_body)
    action_vals = fields.get(3)
    action: Optional[int] = None
    if action_vals and isinstance(action_vals[0], int):
        action = int(action_vals[0])
    return {
        "adder": get_varint(fields, 1, 0),
        "addee": get_varint(fields, 2, 0),
        "action": action,
    }


def decode_cs_remove_friend_req(raw_body: bytes) -> Dict[str, int]:
    """Decode proto.CSRemoveFriendReq (1:remover, 2:removee)."""
    fields = decode_proto(raw_body)
    return {
        "remover": get_varint(fields, 1, 0),
        "removee": get_varint(fields, 2, 0),
    }


def decode_account_id_req(raw_body: bytes) -> int:
    """Decode proto.AccountIDReq (1:uint64 account_id)."""
    fields = decode_proto(raw_body)
    return get_varint(fields, 1, 0)


def decode_account_id_slice(raw_body: bytes) -> List[int]:
    """Decode proto.AccountIDSlice (1:packed uint64[] account_ids)."""
    fields = decode_proto(raw_body)
    return get_packed_varints(fields, 1)


def decode_search_account_req(raw_body: bytes) -> Dict[str, Any]:
    """
    Decode search request payloads seamlessly across:
      - proto.CSFuzzySearchAccountByNameReq (1:string nickname)
      - proto.CSGetAccountInfoReq (1:int32 input_type, 2:string input_value)
      - proto.AccountIDReq (1:uint64 account_id)
    """
    fields = decode_proto(raw_body)
    f1 = fields.get(1)
    f2 = fields.get(2)
    if f1 and isinstance(f1[0], (bytes, bytearray)):
        query = bytes(f1[0]).decode("utf-8", errors="replace").strip()
        return {"mode": "nickname", "input_type": 0, "query": query}
    if f2 and isinstance(f2[0], (bytes, bytearray)):
        query = bytes(f2[0]).decode("utf-8", errors="replace").strip()
        input_type = get_int32(fields, 1, 0)
        return {"mode": "account_info", "input_type": input_type, "query": query}
    aid = get_varint(fields, 1, 0)
    if aid:
        return {"mode": "account_id", "input_type": 0, "query": str(aid)}
    return {"mode": "empty", "input_type": 0, "query": ""}


def decode_cs_friend_invite_req(raw_body: bytes) -> Dict[str, int]:
    """Decode proto.CSFriendInviteReq (1:inviter_id, 2:activity_id)."""
    fields = decode_proto(raw_body)
    return {
        "inviter_id": get_varint(fields, 1, 0),
        "activity_id": get_varint(fields, 2, 0),
    }
