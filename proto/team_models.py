"""
Protobuf encoders, decoders, and constants for Free Fire 1.39 Lobby Squad/Group,
Matchmaking, and Championship Team protocols.

All field numbers, packed array flags, and enum constants match the decompiled
Assembly-CSharp / Il2CppDumper schema (`proto.*`, `tcp.*`, `EProtocol`, `EGroup`,
`EMatchmaking`, `EMatch`) for v1.39.4.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from .decoder import (
    decode_proto,
    get_bool,
    get_bytes,
    get_int32,
    get_int64,
    get_packed_varints,
    get_string,
    get_submessages,
    get_varint,
)
from .encoder import (
    encode_bool,
    encode_bytes,
    encode_int32,
    encode_int64,
    encode_packed_uint32,
    encode_packed_uint64,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)


# ---------------------------------------------------------------------------
# Protocol & Mode Constants (from EProtocol / EGroup / EMatchmaking / EMatch)
# ---------------------------------------------------------------------------

class EProtocolProto:
    MATCHMAKING = 3
    GROUP = 5


class EGroupProto:
    CREATE = 1
    INVITE = 2
    INVITE_NTF = 3
    ACCEPT = 4
    REFUSE = 5
    JOIN_NTF = 6
    LEAVE = 7
    LEAVE_NTF = 8
    START = 9
    START_NTF = 10
    STOP = 11
    STOP_NTF = 12
    DISMISS_NTF = 13
    GROUPINFO = 14
    READY = 15
    READY_NTF = 16
    CHANGE = 17
    CHANGE_NTF = 18
    JOINROOM = 19
    SPECTATEROOM = 20
    SHOWEMOTE = 21
    SHOWEMOTE_NTF = 22
    SHOWPETACTION = 23
    SHOWPETACTION_NTF = 24


class EGroupLeaveReason:
    NORMAL = 0
    OFFLINE = 1
    DROPMATCH = 2
    ALLJOINROOM = 3
    SOLOJOINROOM = 4


class EMatchmakingProto:
    START = 1
    CANCEL = 2
    GROUPSTART = 3
    GROUPCANCEL = 4
    MATCHMAKINGSUSS_NTF = 5
    DROPMATCH = 6
    GAMEOPENINGINFO = 7


class GroupMode:
    SOLO = 0
    DUAL = 1
    TRIPLE = 2
    QUAD = 3


class MatchMode:
    NONE = 0
    CASUAL = 1
    RANKING = 2
    ROOM = 3
    CHAMPIONSHIP = 4


class GameMode:
    BATTLE_ROYALE = 1
    SPEED_ROYALE = 2
    FATE_ROYALE = 3
    PURGE = 8
    PURGE_ALT = 12
    CS = 11
    CS_ALT = 15
    BIG_HEAD = 16


class TeamMemberType:
    NORMAL = 0
    CAPTAIN = 1


GROUP_MODE_TO_STR: Dict[int, str] = {
    GroupMode.SOLO: "solo",
    GroupMode.DUAL: "duo",
    GroupMode.TRIPLE: "squad",
    GroupMode.QUAD: "squad",
}

STR_TO_GROUP_MODE: Dict[str, int] = {
    "solo": GroupMode.SOLO,
    "duo": GroupMode.DUAL,
    "dual": GroupMode.DUAL,
    "trio": GroupMode.TRIPLE,
    "triple": GroupMode.TRIPLE,
    "squad": GroupMode.QUAD,
    "quad": GroupMode.QUAD,
}

GROUP_MODE_MAX_MEMBERS: Dict[int, int] = {
    GroupMode.SOLO: 1,
    GroupMode.DUAL: 2,
    GroupMode.TRIPLE: 3,
    GroupMode.QUAD: 4,
}


def group_mode_from_team(team: Dict[str, Any]) -> int:
    """Resolve `EMatch.GroupMode` from a state team dict."""
    if "_explicit_group_mode" in team:
        return int(team["_explicit_group_mode"])
    raw_mode = str(team.get("mode", "squad")).lower()
    max_members = int(team.get("max_members", 4))
    if max_members == 1 or raw_mode == "solo":
        return GroupMode.SOLO
    if max_members == 2 or raw_mode in ("duo", "dual"):
        return GroupMode.DUAL
    if max_members == 3 or raw_mode in ("trio", "triple"):
        return GroupMode.TRIPLE
    return GroupMode.QUAD


def _encode_repeated_submessages(
    field_num: int,
    items: Iterable[Any],
    encoder_fn: Callable[[Any], bytes],
) -> bytes:
    out = bytearray()
    for item in items:
        out += encode_submessage(field_num, encoder_fn(item))
    return bytes(out)


# ---------------------------------------------------------------------------
# HTTP Championship / Team Request Decoders (`proto.*`)
# ---------------------------------------------------------------------------

def decode_cs_create_team_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSCreateTeamReq`: 1: team_name, 2: contact_info, 3: country_or_area."""
    f = decode_proto(data)
    return {
        "team_name": get_string(f, 1),
        "contact_info": get_string(f, 2),
        "country_or_area": get_string(f, 3),
    }


def decode_team_id_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `TeamIDReq` / `CSTeamIDReq` / `CSJoinTeamReq` / `CSDismissTeamReq` / `CSQuitTeamReq`.
    Tag 1: uint64 team_id.
    """
    f = decode_proto(data)
    return {"team_id": get_varint(f, 1, 0)}


def decode_team_id_slice(data: bytes) -> Dict[str, Any]:
    """Decode `proto.TeamIDSlice`: 1: uint64[] team_ids [PACKED]."""
    f = decode_proto(data)
    return {"team_ids": get_packed_varints(f, 1)}


def decode_cs_team_info_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSTeamInfoReq`: 1: uint64 team_id, 2: bool ignore_region."""
    f = decode_proto(data)
    return {
        "team_id": get_varint(f, 1, 0),
        "ignore_region": get_bool(f, 2, False),
    }


def decode_cs_team_name_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSTeamNameReq`: 1: string team_name."""
    f = decode_proto(data)
    return {"team_name": get_string(f, 1)}


def decode_cs_modify_team_info_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSModifyTeamInfoReq`: 1: team_id, 2: team_name, 3: country_or_area."""
    f = decode_proto(data)
    return {
        "team_id": get_varint(f, 1, 0),
        "team_name": get_string(f, 2),
        "country_or_area": get_string(f, 3),
    }


def decode_cs_add_team_contact_info_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSAddTeamContactInfoReq`: 1: uint64 team_id, 2: string contact_info."""
    f = decode_proto(data)
    return {
        "team_id": get_varint(f, 1, 0),
        "contact_info": get_string(f, 2),
    }


def decode_cs_approve_join_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSApproveJoinApplicationReq`: 1: applicant_id, 2: team_id."""
    f = decode_proto(data)
    return {
        "applicant_id": get_varint(f, 1, 0),
        "team_id": get_varint(f, 2, 0),
    }


def decode_cs_decline_join_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSDeclineJoinApplicationReq`: 1: uint64[] applicant_ids [PACKED], 2: team_id."""
    f = decode_proto(data)
    return {
        "applicant_ids": get_packed_varints(f, 1),
        "team_id": get_varint(f, 2, 0),
    }


def decode_cs_invite_to_team_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSInviteToTeamReq`: 1: uint64 invitee_id, 2: uint64 team_id."""
    f = decode_proto(data)
    return {
        "invitee_id": get_varint(f, 1, 0),
        "team_id": get_varint(f, 2, 0),
    }


def decode_cs_approve_invite_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSApproveInviteToTeamReq`: 1: uint64 inviter_id, 2: uint64 team_id."""
    f = decode_proto(data)
    return {
        "inviter_id": get_varint(f, 1, 0),
        "team_id": get_varint(f, 2, 0),
    }


def decode_cs_decline_invite_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSDeclineInviteToTeamReq`: 1: uint64[] inviter_ids [PACKED]."""
    f = decode_proto(data)
    return {"inviter_ids": get_packed_varints(f, 1)}


def decode_cs_remove_member_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSRemoveTeamMemberReq`: 1: uint64 team_id, 2: uint64 removee_id."""
    f = decode_proto(data)
    return {
        "team_id": get_varint(f, 1, 0),
        "removee_id": get_varint(f, 2, 0),
    }


def decode_cs_init_championship_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSInitTeamChampionshipInfoReq`: 1: uint32 championship_type."""
    f = decode_proto(data)
    return {"championship_type": get_varint(f, 1, 1)}


def decode_cs_get_championship_req(data: bytes) -> Dict[str, Any]:
    """Decode `proto.CSGetTeamChampionshipInfoReq`: 1: championship_type, 2: championship_id."""
    f = decode_proto(data)
    return {
        "championship_type": get_varint(f, 1, 1),
        "championship_id": get_varint(f, 2, 1),
    }


def decode_cs_team_season_stats_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `proto.CSTeamChampionshipSeasonStatsReq`:
    1: team_id, 2: championship_type, 3: championship_id, 4: need_members_info.
    """
    f = decode_proto(data)
    return {
        "team_id": get_varint(f, 1, 0),
        "championship_type": get_varint(f, 2, 1),
        "championship_id": get_varint(f, 3, 1),
        "need_members_info": get_bool(f, 4, False),
    }


def decode_cs_team_match_stats_history_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `proto.CSTeamMatchStatsHistoryReq`:
    1: team_id, 2: championship_type, 3: championship_id.
    """
    f = decode_proto(data)
    return {
        "team_id": get_varint(f, 1, 0),
        "championship_type": get_varint(f, 2, 1),
        "championship_id": get_varint(f, 3, 1),
    }


# ---------------------------------------------------------------------------
# TCP Lobby Group & Matchmaking Request Decoders (`tcp.*`)
# ---------------------------------------------------------------------------

def _decode_ping_list(fields: Dict[int, List[Any]], field_num: int) -> List[Dict[str, Any]]:
    pings: List[Dict[str, Any]] = []
    for sub in get_submessages(fields, field_num):
        pings.append({
            "idc": get_string(sub, 1),
            "ping": get_int32(sub, 2, 0),
        })
    return pings


def decode_proto_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.ProtoReq`: 1: uint32 cmd, 2: bytes data."""
    f = decode_proto(data)
    return {
        "cmd": get_varint(f, 1, 0),
        "data": get_bytes(f, 2, b""),
    }


def decode_group_create_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.GroupCreateReq`:
    dump.cs fields: 1: map_ids, 2: game_mode, 3: group_mode, 4: language, 5: difficulty, 6: tpsdk_str, 7: ping_list, 8: match_mode.
    Also handles 2..9 if tag 1 is omitted.
    """
    f = decode_proto(data)
    has_tag_1 = 1 in f
    return {
        "map_ids": get_packed_varints(f, 1 if has_tag_1 else 2),
        "game_mode": get_varint(f, 2 if has_tag_1 else 3, GameMode.BATTLE_ROYALE),
        "group_mode": get_varint(f, 3 if has_tag_1 else 4, GroupMode.QUAD),
        "language": get_string(f, 4 if has_tag_1 else 5, "en"),
        "difficulty": get_varint(f, 5 if has_tag_1 else 6, 0),
        "tpsdk_str": get_string(f, 6 if has_tag_1 else 7),
        "ping_list": _decode_ping_list(f, 7 if has_tag_1 else 8),
        "match_mode": get_varint(f, 8 if has_tag_1 else 9, MatchMode.CASUAL),
    }


def decode_group_invite_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.GroupInviteReq`: 1: uint64 invitee_id, 2: string invitee_region."""
    f = decode_proto(data)
    return {
        "invitee_id": get_varint(f, 1, 0),
        "invitee_region": get_string(f, 2),
    }


def decode_group_accept_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.GroupAcceptReq`: 1: group_id, 2: tpsdk_str, 3: inviter_account_id."""
    f = decode_proto(data)
    return {
        "group_id": get_varint(f, 1, 0),
        "tpsdk_str": get_string(f, 2),
        "inviter_account_id": get_varint(f, 3, 0),
    }


def decode_group_id_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `GroupRefuseReq` / `GroupLeaveReq` / `GroupStartReq` / `GroupStopReq` / `GroupInfoReq`.
    Tag 1: uint64 group_id.
    """
    f = decode_proto(data)
    return {"group_id": get_varint(f, 1, 0)}


def decode_group_ready_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.GroupReadyReq`: 1: uint64 group_id, 2: bool ready."""
    f = decode_proto(data)
    return {
        "group_id": get_varint(f, 1, 0),
        "ready": get_bool(f, 2, True),
    }


def decode_group_change_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.GroupChangeReq`:
    1: group_id, 2: auto_group, 3: group_mode, 4: game_mode,
    5: map_ids [PACKED], 6/7: difficulty, 7/8: match_mode.
    """
    f = decode_proto(data)
    has_diff_6 = 6 in f
    return {
        "group_id": get_varint(f, 1, 0),
        "has_auto_group": 2 in f,
        "auto_group": get_bool(f, 2, False),
        "has_group_mode": 3 in f,
        "group_mode": get_varint(f, 3, GroupMode.QUAD),
        "has_game_mode": 4 in f,
        "game_mode": get_varint(f, 4, GameMode.BATTLE_ROYALE),
        "has_map_ids": 5 in f,
        "map_ids": get_packed_varints(f, 5),
        "difficulty": get_varint(f, 6 if has_diff_6 else 7, 0),
        "has_match_mode": (7 in f and has_diff_6) or (8 in f),
        "match_mode": get_varint(f, 7 if has_diff_6 else 8, MatchMode.CASUAL),
    }


def decode_show_emote_req(data: bytes) -> Dict[str, Any]:
    """Decode tcp.ShowEmoteReq (tag 1: uint64 group_id, tag 2: uint32 emote_id)."""
    f = decode_proto(data) if data else {}
    return {
        "group_id": get_varint(f, 1, 0),
        "emote_id": get_varint(f, 2, 0),
    }


def encode_show_emote_ntf(account_id: int, emote_id: int) -> bytes:
    """Encode tcp.ShowEmoteNtf (tag 1: uint64 account_id, tag 2: uint32 emote_id)."""
    buf = bytearray()
    buf += encode_uint64(1, int(account_id))
    buf += encode_uint32(2, int(emote_id))
    return bytes(buf)


def decode_show_pet_action_req(data: bytes) -> Dict[str, Any]:
    """Decode tcp.ShowPetActionReq (tag 1: uint64 group_id, tag 2: uint32 action_id)."""
    f = decode_proto(data) if data else {}
    return {
        "group_id": get_varint(f, 1, 0),
        "action_id": get_varint(f, 2, 0),
    }


def encode_show_pet_action_ntf(account_id: int, action_id: int) -> bytes:
    """Encode tcp.ShowPetActionNtf (tag 1: uint64 account_id, tag 2: uint32 action_id)."""
    buf = bytearray()
    buf += encode_uint64(1, int(account_id))
    buf += encode_uint32(2, int(action_id))
    return bytes(buf)


def decode_matchmaking_start_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.MatchmakingStartReq`:
    1: map_ids [PACKED], 2: game_mode, 4: difficulty, 5: wta_currency_type,
    6: tpsdk_str, 7: ping_list, 8: match_mode (no tag 3).
    """
    f = decode_proto(data)
    return {
        "map_ids": get_packed_varints(f, 1),
        "game_mode": get_varint(f, 2, GameMode.BATTLE_ROYALE),
        "difficulty": get_varint(f, 4, 0),
        "wta_currency_type": get_varint(f, 5, 0),
        "tpsdk_str": get_string(f, 6),
        "ping_list": _decode_ping_list(f, 7),
        "match_mode": get_varint(f, 8, MatchMode.CASUAL),
    }


def decode_matchmaking_group_start_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.MatchmakingGroupStartReq`:
    1: map_ids [PACKED], 2: group_id, 3: group_mode, 4: players,
    6: game_mode, 7: difficulty, 8: auto_group, 9: group_members,
    10: auto_group_id, 11: group_idc, 12: match_mode (no tag 5).
    """
    f = decode_proto(data)
    group_members: List[List[int]] = []
    for sub in get_submessages(f, 9):
        group_members.append(get_packed_varints(sub, 1))
    return {
        "map_ids": get_packed_varints(f, 1),
        "group_id": get_varint(f, 2, 0),
        "group_mode": get_varint(f, 3, GroupMode.QUAD),
        "game_mode": get_varint(f, 6, GameMode.BATTLE_ROYALE),
        "difficulty": get_varint(f, 7, 0),
        "auto_group": get_bool(f, 8, False),
        "group_members": group_members,
        "auto_group_id": get_varint(f, 10, 0),
        "group_idc": get_string(f, 11),
        "match_mode": get_varint(f, 12, MatchMode.CASUAL),
    }


# ---------------------------------------------------------------------------
# HTTP Championship / Team Response Encoders (`proto.*`)
# ---------------------------------------------------------------------------

def encode_account_info_basic(
    profile: Dict[str, Any],
    team: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Encode `proto.AccountInfoBasic` (TypeDefIndex 5036).
    Used inside `AccountInfoBasicBundleRes` and `TeamMemberWithAccountInfo`.
    """
    buf = bytearray()
    buf += encode_uint64(1, int(profile.get("account_id", 10001)))
    buf += encode_uint32(2, int(profile.get("account_type", 1)))
    buf += encode_string(3, str(profile.get("nickname", "Player")))
    if profile.get("external_id"):
        buf += encode_string(4, str(profile["external_id"]))
    buf += encode_string(5, str(profile.get("region", "ID")))
    buf += encode_uint32(6, int(profile.get("level", 1)))
    buf += encode_uint32(7, int(profile.get("exp", 0)))
    buf += encode_uint32(8, int(profile.get("external_type", 0)))
    if profile.get("external_name"):
        buf += encode_string(9, str(profile["external_name"]))
    if profile.get("external_icon"):
        buf += encode_string(10, str(profile["external_icon"]))
    buf += encode_uint32(11, int(profile.get("banner_id", 0)))
    buf += encode_uint32(12, int(profile.get("head_pic", 0)))
    if profile.get("clan_name"):
        buf += encode_string(13, str(profile["clan_name"]))
    buf += encode_uint32(14, int(profile.get("rank", 1)))
    buf += encode_uint32(15, int(profile.get("ranking_points", 1000)))
    buf += encode_uint32(16, int(profile.get("role", 0)))
    buf += encode_bool(17, bool(profile.get("has_elite_pass", False)))
    buf += encode_uint32(18, int(profile.get("badge_cnt", 0)))
    buf += encode_uint32(19, int(profile.get("ep_event_id", 0)))
    buf += encode_uint32(20, int(profile.get("ep_badge", 0)))
    buf += encode_uint32(21, int(profile.get("liked", 0)))
    buf += encode_bool(22, bool(profile.get("is_deleted", False)))
    buf += encode_bool(23, bool(profile.get("show_rank", True)))
    buf += encode_int64(24, int(profile.get("last_login_at", int(time.time()))))
    buf += encode_uint64(25, int(profile.get("external_uid", 0)))
    buf += encode_int64(26, int(profile.get("return_at", 0)))
    if team:
        buf += encode_string(27, str(team.get("team_name", "Barbosa Squad")))
        buf += encode_uint32(28, len(team.get("members", [])))
        buf += encode_uint64(29, int(team.get("team_id", 0)))
    return bytes(buf)


def encode_account_info_basic_bundle_res(
    profiles: Sequence[Dict[str, Any]],
    team_lookup: Optional[Dict[int, Dict[str, Any]]] = None,
) -> bytes:
    """Encode `proto.AccountInfoBasicBundleRes`: 1: repeated AccountInfoBasic infos."""
    buf = bytearray()
    for prof in profiles:
        aid = int(prof.get("account_id", 0))
        team = team_lookup.get(aid) if team_lookup else None
        buf += encode_submessage(1, encode_account_info_basic(prof, team=team))
    return bytes(buf)


def encode_cs_team_id_res(team_id: int) -> bytes:
    """Encode `proto.CSTeamIDRes`: 1: uint64 team_id."""
    return encode_uint64(1, int(team_id))


def encode_team_info(team: Dict[str, Any]) -> bytes:
    """
    Encode `proto.TeamInfo`:
    1: team_id, 2: team_name, 3: create_at, 4: captain_id, 5: member_num,
    6: region, 7: banner_id, 8: contact_info, 9: country_or_area,
    10: head_pic, 11: uint64[] member_ids [PACKED].
    """
    members = team.get("members") or []
    member_ids = [int(m.get("account_id", 0)) for m in members]
    buf = bytearray()
    buf += encode_uint64(1, int(team.get("team_id", 0)))
    buf += encode_string(2, str(team.get("team_name", "Barbosa Squad")))
    buf += encode_uint64(3, int(team.get("created_at", int(time.time()))))
    buf += encode_uint64(4, int(team.get("leader_id", 10001)))
    buf += encode_uint32(5, len(member_ids))
    buf += encode_string(6, str(team.get("region", "ID")))
    buf += encode_uint32(7, int(team.get("banner_id", 901000001)))
    if team.get("contact_info"):
        buf += encode_string(8, str(team["contact_info"]))
    if team.get("country_or_area"):
        buf += encode_string(9, str(team["country_or_area"]))
    buf += encode_uint32(10, int(team.get("head_pic", 902000001)))
    buf += encode_packed_uint64(11, member_ids)
    return bytes(buf)


def encode_cs_team_info_bundle_res(teams: Sequence[Dict[str, Any]]) -> bytes:
    """Encode `proto.CSTeamInfoBundleRes`: 1: List<TeamInfo> infos."""
    return _encode_repeated_submessages(1, teams, encode_team_info)


def encode_team_member_with_account_info(item: Dict[str, Any]) -> bytes:
    """
    Encode `proto.TeamMemberWithAccountInfo`:
    1: AccountInfoBasic basic_info, 2: team_id, 3: member_type, 4: join_at, 5: region.
    """
    profile = item["profile"]
    team = item.get("team")
    buf = bytearray()
    buf += encode_submessage(1, encode_account_info_basic(profile, team=team))
    buf += encode_uint64(2, int(item.get("team_id", 0)))
    buf += encode_uint32(3, int(item.get("member_type", TeamMemberType.NORMAL)))
    buf += encode_uint64(4, int(item.get("join_at", int(time.time()))))
    buf += encode_string(5, str(profile.get("region", "ID")))
    return bytes(buf)


def encode_team_member_list_with_account_info(members: Sequence[Dict[str, Any]]) -> bytes:
    """Encode `proto.TeamMemberListWithAccountInfo`: 1: List<TeamMemberWithAccountInfo>."""
    return _encode_repeated_submessages(1, members, encode_team_member_with_account_info)


def encode_cs_team_member_res(
    team_id: int,
    member_id: int,
    member_type: int = TeamMemberType.NORMAL,
    join_at: int = 0,
    is_not_in_team: bool = False,
) -> bytes:
    """
    Encode `proto.CSTeamMemberRes`:
    1: team_id, 2: member_id, 3: member_type, 4: join_at, 5: is_not_in_team.
    """
    buf = bytearray()
    buf += encode_uint64(1, int(team_id))
    buf += encode_uint64(2, int(member_id))
    buf += encode_uint32(3, int(member_type))
    buf += encode_uint64(4, int(join_at or int(time.time())))
    buf += encode_bool(5, bool(is_not_in_team))
    return bytes(buf)


def encode_team_applicant_res(app: Dict[str, Any]) -> bytes:
    """Encode `proto.TeamApplicantRes`: 1: applicant_id, 2: team_id, 3: create_at."""
    buf = bytearray()
    buf += encode_uint64(1, int(app.get("applicant_id", 0)))
    buf += encode_uint64(2, int(app.get("team_id", 0)))
    buf += encode_uint64(3, int(app.get("create_at", int(time.time()))))
    return bytes(buf)


def encode_cs_team_applicant_list(applicants: Sequence[Dict[str, Any]]) -> bytes:
    """Encode `proto.CSTeamApplicantList`: 1: List<TeamApplicantRes>."""
    return _encode_repeated_submessages(1, applicants, encode_team_applicant_res)


def encode_team_invitation_res(inv: Dict[str, Any]) -> bytes:
    """Encode `proto.TeamInvitationRes`: 1: account_id, 2: team_id, 3: inviter_id, 4: create_at."""
    buf = bytearray()
    buf += encode_uint64(1, int(inv.get("target_id", inv.get("account_id", 0))))
    buf += encode_uint64(2, int(inv.get("team_id", 0)))
    buf += encode_uint64(3, int(inv.get("inviter_id", 0)))
    buf += encode_uint64(4, int(inv.get("created_at", inv.get("create_at", int(time.time())))))
    return bytes(buf)


def encode_cs_team_invitation_list(invitations: Sequence[Dict[str, Any]]) -> bytes:
    """Encode `proto.CSTeamInvitationList`: 1: List<TeamInvitationRes>."""
    return _encode_repeated_submessages(1, invitations, encode_team_invitation_res)


def encode_team_championship_info(info: Dict[str, Any]) -> bytes:
    """Encode `proto.TeamChampionshipInfo` (tags 1..15)."""
    buf = bytearray()
    buf += encode_uint64(1, int(info.get("team_id", 0)))
    buf += encode_uint32(2, int(info.get("championship_type", 1)))
    buf += encode_uint32(3, int(info.get("championship_id", 1)))
    buf += encode_uint32(4, int(info.get("tickets_num", 3)))
    buf += encode_uint32(5, int(info.get("trial_games_played", 0)))
    buf += encode_uint32(6, int(info.get("trial_kills", 0)))
    buf += encode_uint32(7, int(info.get("trial_valid_score", 0)))
    buf += encode_uint32(8, int(info.get("trial_total_score", 0)))
    buf += encode_uint32(9, int(info.get("trial_pos", 0)))
    buf += encode_bool(10, bool(info.get("is_enter_final", False)))
    buf += encode_uint32(11, int(info.get("final_games_played", 0)))
    buf += encode_uint32(12, int(info.get("final_kills", 0)))
    buf += encode_uint32(13, int(info.get("final_valid_score", 0)))
    buf += encode_uint32(14, int(info.get("final_total_score", 0)))
    buf += encode_uint32(15, int(info.get("final_pos", 0)))
    return bytes(buf)


def encode_account_championship_info(info: Dict[str, Any]) -> bytes:
    """Encode `proto.AccountChampionshipInfo` (tags 1..9)."""
    buf = bytearray()
    buf += encode_uint64(1, int(info.get("account_id", 10001)))
    buf += encode_uint32(2, int(info.get("championship_type", 1)))
    buf += encode_uint32(3, int(info.get("championship_id", 1)))
    buf += encode_uint32(4, int(info.get("trial_valid_score", 0)))
    buf += encode_uint32(5, int(info.get("trial_pos", 0)))
    buf += encode_bool(6, bool(info.get("can_get_trial_reward", False)))
    buf += encode_uint32(7, int(info.get("final_valid_score", 0)))
    buf += encode_uint32(8, int(info.get("final_pos", 0)))
    buf += encode_bool(9, bool(info.get("rewarded", False)))
    return bytes(buf)


def encode_championship_winner_info(info: Dict[str, Any]) -> bytes:
    """Encode `proto.ChampionshipWinnerInfo` (tags 1..4)."""
    buf = bytearray()
    buf += encode_uint32(1, int(info.get("championship_type", 1)))
    buf += encode_uint32(2, int(info.get("championship_id", 1)))
    buf += encode_string(3, str(info.get("region", "ID")))
    buf += encode_uint64(4, int(info.get("team_id", 0)))
    return bytes(buf)


def encode_championship_info(info: Dict[str, Any]) -> bytes:
    """Encode `proto.ChampionshipInfo` (tags 1..4)."""
    buf = bytearray()
    buf += encode_uint32(1, int(info.get("championship_type", 1)))
    if info.get("team_info"):
        buf += encode_submessage(2, encode_team_championship_info(info["team_info"]))
    if info.get("account_info"):
        buf += encode_submessage(3, encode_account_championship_info(info["account_info"]))
    for winner in info.get("winner_infos", []):
        buf += encode_submessage(4, encode_championship_winner_info(winner))
    return bytes(buf)


def encode_cs_team_championship_info_res(
    team_id: int,
    championship_infos: Sequence[Dict[str, Any]],
) -> bytes:
    """Encode `proto.CSTeamChampionshipInfoRes`: 1: team_id, 2: List<ChampionshipInfo>."""
    buf = bytearray()
    buf += encode_uint64(1, int(team_id))
    buf += _encode_repeated_submessages(2, championship_infos, encode_championship_info)
    return bytes(buf)


def encode_championship_open_info_desc(info: Dict[str, Any]) -> bytes:
    """Encode `proto.ChampionshipOpenInfoDesc` (tags 1..9)."""
    now = int(time.time())
    buf = bytearray()
    buf += encode_uint32(1, int(info.get("championship_type", 1)))
    buf += encode_uint32(2, int(info.get("championship_id", 1)))
    buf += encode_int64(3, int(info.get("season_start_time", now - 86400)))
    buf += encode_int64(4, int(info.get("season_end_time", now + 86400 * 30)))
    buf += encode_int64(5, int(info.get("trial_start_time", now - 3600)))
    buf += encode_int64(6, int(info.get("trial_end_time", now + 86400 * 7)))
    buf += encode_int64(7, int(info.get("final_start_time", now + 86400 * 8)))
    buf += encode_int64(8, int(info.get("final_end_time", now + 86400 * 14)))
    buf += encode_string(9, str(info.get("map_id", "1")))
    return bytes(buf)


def encode_championship_setting_desc(setting: Dict[str, Any]) -> bytes:
    """Encode `proto.ChampionshipSettingDesc` (tags 1..14)."""
    buf = bytearray()
    buf += encode_uint32(1, int(setting.get("championship_type", 1)))
    buf += encode_uint32(2, int(setting.get("championship_id", 1)))
    buf += encode_string(3, str(setting.get("trial_match_name", "Trial Match")))
    buf += encode_uint32(4, int(setting.get("trial_match_num", 8)))
    buf += encode_uint32(5, int(setting.get("trial_match_choose_num", 5)))
    buf += encode_string(6, str(setting.get("final_match_name", "Final Match")))
    buf += encode_uint32(7, int(setting.get("final_match_num", 6)))
    buf += encode_uint32(8, int(setting.get("final_match_choose_num", 6)))
    buf += encode_uint32(9, int(setting.get("min_match_num", 1)))
    buf += encode_uint32(10, int(setting.get("limited_item_type", 0)))
    buf += encode_uint32(11, int(setting.get("limited_item_id", 0)))
    buf += encode_uint32(12, int(setting.get("limited_item_num", 0)))
    buf += encode_uint32(13, int(setting.get("seniority_list", 100)))
    if setting.get("lobby_icon"):
        buf += encode_string(14, str(setting["lobby_icon"]))
    return bytes(buf)


def encode_cs_get_championship_config_res(
    open_info: Dict[str, Any],
    setting_info: Dict[str, Any],
) -> bytes:
    """
    Encode `proto.CSGetChampionshipConfigRes`:
    1: open_info, 2: reward_infos (optional), 3: setting_info.
    """
    buf = bytearray()
    buf += encode_submessage(1, encode_championship_open_info_desc(open_info))
    buf += encode_submessage(3, encode_championship_setting_desc(setting_info))
    return bytes(buf)


def encode_cs_team_championship_season_stats_res(
    team_id: int,
    championship_type: int,
    championship_id: int,
    member_profiles: Sequence[Dict[str, Any]],
    stats: Optional[Dict[str, Any]] = None,
    need_members_info: bool = False,
    team: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Encode `proto.CSTeamChampionshipSeasonStatsRes` (tags 1..17, 4=packed members)."""
    st = stats or {}
    member_ids = [int(p.get("account_id", 0)) for p in member_profiles]
    buf = bytearray()
    buf += encode_uint64(1, int(team_id))
    buf += encode_uint32(2, int(championship_type))
    buf += encode_uint32(3, int(championship_id))
    buf += encode_packed_uint64(4, member_ids)
    buf += encode_uint32(5, int(st.get("games_played", 0)))
    buf += encode_int32(6, int(st.get("max_score", 0)))
    buf += encode_uint32(7, int(st.get("wins", 0)))
    buf += encode_uint32(8, int(st.get("top_10_percent_times", 0)))
    buf += encode_uint32(9, int(st.get("top_50_percent_times", 0)))
    buf += encode_uint32(10, int(st.get("survival_time", 0)))
    buf += encode_uint32(11, int(st.get("moving_distance", 0)))
    buf += encode_uint32(12, int(st.get("kills", 0)))
    buf += encode_uint32(13, int(st.get("damage", 0)))
    buf += encode_uint32(14, int(st.get("one_game_most_kills", 0)))
    buf += encode_uint32(15, int(st.get("one_game_most_damage", 0)))
    buf += encode_uint32(16, int(st.get("headshot_kills", 0)))
    if need_members_info and member_profiles:
        team_map = {int(p.get("account_id", 0)): team for p in member_profiles} if team else None
        buf += encode_submessage(17, encode_account_info_basic_bundle_res(member_profiles, team_lookup=team_map))
    return bytes(buf)


def encode_cs_team_match_stats_history_res(match_stats: Sequence[Dict[str, Any]] = ()) -> bytes:
    """Encode `proto.CSTeamMatchStatsHistoryRes`: 1: List<TeamChampionshipMatchStats>."""
    buf = bytearray()
    for ms in match_stats:
        sub = bytearray()
        sub += encode_uint64(1, int(ms.get("team_id", 0)))
        sub += encode_uint32(2, int(ms.get("championship_type", 1)))
        sub += encode_uint32(3, int(ms.get("championship_id", 1)))
        sub += encode_uint64(4, int(ms.get("match_id", 0)))
        sub += encode_uint32(5, int(ms.get("create_time", 0)))
        sub += encode_uint32(6, int(ms.get("end_time", 0)))
        sub += encode_int32(7, int(ms.get("score", 0)))
        sub += encode_uint32(8, int(ms.get("phase", 0)))
        sub += encode_bool(9, bool(ms.get("is_invalid", False)))
        buf += encode_submessage(1, bytes(sub))
    return bytes(buf)


# ---------------------------------------------------------------------------
# TCP Lobby Group & Matchmaking Response Encoders (`tcp.*`)
# ---------------------------------------------------------------------------

def encode_group_member_pet_info(pet: Dict[str, Any]) -> bytes:
    """Encode `tcp.GroupMemberPetInfo`: 1: id, 2: name, 3: level, 4: skin_id."""
    buf = bytearray()
    buf += encode_uint32(1, int(pet.get("pet_id", pet.get("id", 0))))
    buf += encode_string(2, str(pet.get("name", "Pet")))
    buf += encode_uint32(3, int(pet.get("level", 1)))
    buf += encode_uint32(4, int(pet.get("skin_id", 0)))
    return bytes(buf)


def encode_group_member_info(
    member: Dict[str, Any],
    profile: Dict[str, Any],
    pet: Optional[Dict[str, Any]] = None,
    is_leader: Optional[bool] = None,
) -> bytes:
    """
    Encode `tcp.GroupMemberInfo`:
    1: account_id, 2: nickname, 3: region, 4: join_time, 5: level,
    6: avatar_id, 7: skin_color, 8: uint32[] clothes [PACKED], 9: ready,
    10: rank, 11: ranking_points, 12: banner_id, 13: head_pic, 14: role,
    15: uint32[] shows [PACKED], 16: GroupMemberPetInfo pet_info, 17: pve_weapon_id.

    Reversed from Free Fire 1.39 COW.UIModelGroup & COW.UIGroupMemberInfoController:
    - Leader must have role=1 (Captain) and ready=False. If the leader had ready=True,
      the client would show a yellow ready checkmark instead of the Captain Crown,
      and display CANCEL instead of the START button!
    - Non-leader members have role=0 (Normal Member) and ready=True/False depending on ready state.
    """
    clothes: List[int] = []
    for c in (profile.get("clothes") or []):
        if isinstance(c, dict):
            cid = c.get("id", c.get("item_id", 0))
            if cid:
                clothes.append(int(cid))
        else:
            try:
                clothes.append(int(c))
            except (ValueError, TypeError):
                pass
    if not clothes:
        clothes = [211000000, 208000000, 203000573, 204000345, 205000299]

    shows: List[int] = []
    raw_shows = profile.get("shows") or profile.get("equiped_skills") or []
    for s in raw_shows:
        if isinstance(s, dict):
            sid = s.get("skill_id", s.get("id", 0))
            if sid:
                shows.append(int(sid))
        else:
            try:
                shows.append(int(s))
            except (ValueError, TypeError):
                pass
    if not shows:
        shows = [907000001, 907000005, 907000010, 907000013, 907000014]

    aid = int(profile.get("account_id", member.get("account_id", 0)))
    if is_leader is None:
        is_leader = (int(member.get("role", 0)) == 1) or bool(member.get("is_leader", False))

    if is_leader:
        member_role = 1
        member_ready = False
    else:
        member_role = int(member.get("role", 0))
        if member_role == 1:
            member_role = 0
        member_ready = bool(member.get("ready", False))

    raw_avatar = int(profile.get("avatar_id", 102000004))
    avatar_id = raw_avatar if raw_avatar >= 101000000 else 102000004

    buf = bytearray()
    buf += encode_uint64(1, aid)
    buf += encode_string(2, str(profile.get("nickname", "Player")))
    buf += encode_string(3, str(profile.get("region", "ID")))
    buf += encode_uint64(4, int(member.get("joined_at", profile.get("create_at", int(time.time())))))
    buf += encode_uint32(5, int(profile.get("level", 1)))
    buf += encode_uint32(6, avatar_id)
    buf += encode_uint32(7, int(profile.get("skin_color", 0)))
    buf += encode_packed_uint32(8, clothes)
    buf += encode_bool(9, member_ready)
    buf += encode_uint32(10, int(profile.get("rank", 1)))
    buf += encode_uint32(11, int(profile.get("ranking_points", 1000)))
    buf += encode_uint32(12, int(profile.get("banner_id", 901000001)))
    buf += encode_uint32(13, int(profile.get("head_pic", 902000001)))
    buf += encode_uint32(14, member_role)
    buf += encode_packed_uint32(15, shows)
    if pet and int(pet.get("pet_id", pet.get("id", 0))) > 0:
        buf += encode_submessage(16, encode_group_member_pet_info(pet))
    if profile.get("pve_weapon_id"):
        buf += encode_uint32(17, int(profile["pve_weapon_id"]))
    return bytes(buf)


def encode_group_info(
    team: Dict[str, Any],
    member_profiles: Dict[int, Dict[str, Any]],
    pet_lookup: Optional[Dict[int, Dict[str, Any]]] = None,
) -> bytes:
    """
    Encode `tcp.GroupInfo`:
    1: group_id, 2: region, 3: auto_group, 4: group_mode, 5: is_ranking_match,
    6: List<GroupMemberInfo> members, 7: uint32[] map_ids [PACKED],
    8: game_mode, 9: difficulty, 10: match_mode.

    Reversed from Free Fire 1.39 COW.UIModelGroup:
    - group_id MUST equal the Leader's account_id. The client checks group_id == myId
      to determine IsGroupLeader.
    - Leader must be index 0 of members list.
    """
    game_mode = int(team.get("game_mode", GameMode.BATTLE_ROYALE))
    match_mode = int(team.get("match_mode", MatchMode.RANKING if game_mode == GameMode.BATTLE_ROYALE else MatchMode.CASUAL))
    is_ranking = bool(team.get("is_ranking_match", match_mode == MatchMode.RANKING))
    map_ids = [int(m) for m in (team.get("map_ids") or [int(team.get("map_id", 1))])]

    leader_id = int(team.get("leader_id") or team.get("group_id") or team.get("team_id", 0))
    group_id = leader_id if leader_id > 0 else int(team.get("team_id", 0))

    buf = bytearray()
    buf += encode_uint64(1, group_id)
    buf += encode_string(2, str(team.get("region", "ID")))
    buf += encode_bool(3, bool(team.get("auto_group", False)))
    buf += encode_uint32(4, group_mode_from_team(team))
    buf += encode_bool(5, is_ranking)

    raw_members = list(team.get("members") or [])
    leader_members = [m for m in raw_members if int(m.get("account_id", 0)) == leader_id]
    other_members = [m for m in raw_members if int(m.get("account_id", 0)) != leader_id]
    ordered_members = leader_members + other_members

    for m in ordered_members:
        aid = int(m.get("account_id", 0))
        prof = member_profiles.get(aid) or {"account_id": aid, "nickname": f"Player_{aid}"}
        pet = pet_lookup.get(aid) if pet_lookup else None
        is_lead = (aid == leader_id)
        buf += encode_submessage(6, encode_group_member_info(m, prof, pet=pet, is_leader=is_lead))
    buf += encode_packed_uint32(7, map_ids)
    buf += encode_uint32(8, game_mode)
    buf += encode_uint32(9, int(team.get("difficulty", 0)))
    buf += encode_uint32(10, match_mode)
    return bytes(buf)


def encode_group_invite_ntf(
    group_id: int,
    inviter_member: Dict[str, Any],
    inviter_profile: Dict[str, Any],
    team: Dict[str, Any],
    inviter_pet: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Encode `tcp.GroupInviteNtf`:
    1: group_id, 2: GroupMemberInfo inviter_info, 3: is_ranking_match,
    4: map_ids [PACKED], 5: game_mode, 6: group_mode.
    """
    game_mode = int(team.get("game_mode", GameMode.BATTLE_ROYALE))
    match_mode = int(team.get("match_mode", MatchMode.CASUAL))
    map_ids = [int(m) for m in (team.get("map_ids") or [int(team.get("map_id", 1))])]
    effective_group_id = int(team.get("leader_id") or team.get("group_id") or group_id)
    inv_aid = int(inviter_profile.get("account_id", inviter_member.get("account_id", 0)))
    is_lead = (inv_aid == int(team.get("leader_id", 0))) or (inv_aid == effective_group_id)
    buf = bytearray()
    buf += encode_uint64(1, effective_group_id)
    buf += encode_submessage(2, encode_group_member_info(inviter_member, inviter_profile, pet=inviter_pet, is_leader=is_lead))
    buf += encode_bool(3, bool(team.get("is_ranking_match", match_mode == MatchMode.RANKING)))
    buf += encode_packed_uint32(4, map_ids)
    buf += encode_uint32(5, game_mode)
    buf += encode_uint32(6, group_mode_from_team(team))
    return bytes(buf)


def encode_group_leave_ntf(
    leaver_id: int,
    reason: int,
    team: Dict[str, Any],
    member_profiles: Dict[int, Dict[str, Any]],
    pet_lookup: Optional[Dict[int, Dict[str, Any]]] = None,
) -> bytes:
    """Encode `tcp.GroupLeaveNtf`: 1: leaver_id, 2: reason, 3: GroupInfo group_info."""
    buf = bytearray()
    buf += encode_uint64(1, int(leaver_id))
    buf += encode_uint32(2, int(reason))
    buf += encode_submessage(3, encode_group_info(team, member_profiles, pet_lookup=pet_lookup))
    return bytes(buf)


def encode_group_stop_ntf(
    stopper_member: Dict[str, Any],
    stopper_profile: Dict[str, Any],
    team: Dict[str, Any],
    member_profiles: Dict[int, Dict[str, Any]],
    pet_lookup: Optional[Dict[int, Dict[str, Any]]] = None,
) -> bytes:
    """Encode `tcp.GroupStopNtf`: 1: stoper_info, 2: GroupInfo group_info."""
    stopper_aid = int(stopper_profile.get("account_id", stopper_member.get("account_id", 0)))
    stopper_pet = pet_lookup.get(stopper_aid) if pet_lookup else None
    buf = bytearray()
    buf += encode_submessage(1, encode_group_member_info(stopper_member, stopper_profile, pet=stopper_pet))
    buf += encode_submessage(2, encode_group_info(team, member_profiles, pet_lookup=pet_lookup))
    return bytes(buf)


def encode_group_dismiss_ntf(leaver_id: int, group_id: int, reason: int = EGroupLeaveReason.NORMAL) -> bytes:
    """Encode `tcp.GroupDismissNtf`: 1: leaver_id, 2: group_id, 3: reason."""
    buf = bytearray()
    buf += encode_uint64(1, int(leaver_id))
    buf += encode_uint64(2, int(group_id))
    buf += encode_uint32(3, int(reason))
    return bytes(buf)


def encode_matchmaking_suss_ntf(
    match_id: int,
    server_addr: str = "10.0.2.2:39800",
    secret: str = "0123456789abcdef0123456789abcdef",
    prepare_token: str = "0123456789abcdef0123456789abcdef",
    sleep_ms: int = 0,
    map_id: int = 1,
    game_mode: int = GameMode.BATTLE_ROYALE,
    match_mode: int = MatchMode.CASUAL,
    use_cache: bool = False,
    level_visual_style: int = 0,
    difficulty: int = 0,
    first_login: bool = False,
) -> bytes:
    """
    Encode `tcp.MatchmakingSussNtf`:
    1: match_id, 2: server_addr, 3: secret, 4: prepare_token, 5: sleep_ms,
    6: map_id, 7: game_mode, 8: match_mode, 9: use_cache,
    11: level_visual_style, 12: difficulty, 13: first_login (no tag 10).
    """
    buf = bytearray()
    buf += encode_uint64(1, int(match_id))
    buf += encode_string(2, str(server_addr))
    buf += encode_string(3, str(secret))
    buf += encode_string(4, str(prepare_token))
    buf += encode_uint32(5, int(sleep_ms))
    buf += encode_uint32(6, int(map_id))
    buf += encode_uint32(7, int(game_mode))
    buf += encode_uint32(8, int(match_mode))
    buf += encode_bool(9, bool(use_cache))
    buf += encode_uint32(11, int(level_visual_style))
    buf += encode_uint32(12, int(difficulty))
    buf += encode_bool(13, bool(first_login))
    return bytes(buf)


def encode_message_notify(
    account_id: int,
    protocol: int,
    ret: int,
    cmd: int,
    content: bytes = b"",
) -> bytes:
    """Encode `tcp.MessageNotify`: 1: account_id, 2: protocol, 3: ret, 4: cmd, 5: content."""
    buf = bytearray()
    buf += encode_uint64(1, int(account_id))
    buf += encode_uint32(2, int(protocol))
    buf += encode_uint32(3, int(ret))
    buf += encode_uint32(4, int(cmd))
    if content:
        buf += encode_bytes(5, content)
    return bytes(buf)
