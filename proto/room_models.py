"""
Protobuf models and TCP framing helpers for Free Fire 1.39 Custom Rooms,
Matchmaking, Game Opening Info, and Game Server descriptors.

All ProtoMember tags, wire types, packed flags, and enum constants are verified
against Free Fire 1.39 global-metadata.dat + x86 libil2cpp.so.
"""

from __future__ import annotations

import struct
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .decoder import (
    decode_proto,
    get_bool,
    get_bytes,
    get_int32,
    get_int64,
    get_packed_varints,
    get_string,
    get_submessage,
    get_submessages,
    get_varint,
)
from .encoder import (
    encode_bool,
    encode_bytes,
    encode_float,
    encode_int32,
    encode_int64,
    encode_packed_uint32,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)
from .team_models import (
    GameMode,
    GroupMode,
    MapID,
    MatchMode,
    decode_matchmaking_group_start_req,
    decode_matchmaking_start_req,
    decode_proto_req,
    encode_matchmaking_suss_ntf,
    encode_message_notify,
)


# ---------------------------------------------------------------------------
# Constants & Enums (exact values from global-metadata.dat)
# ---------------------------------------------------------------------------

TCP_HANDSHAKE_ACK = b"\x02"
TCP_KICK_CMD = 0x0B


class EProtocolProto:
    """tcp.EProtocol+Proto [TypeDef 5936]"""
    NONE = 0
    INIT = 1
    HEARTBEAT = 2
    MATCHMAKING = 3
    STATS = 4
    GROUP = 5
    FRIEND = 6
    MAIL = 7
    INVENTORY = 8
    BACKPACK = 9
    ACTIVITY = 10
    ACCOUNT = 11
    CLAN = 12
    PROFILE = 13
    ROOM = 14
    PRESENCE = 15
    ELITEPASS = 16
    RECONNECTION = 17
    CHANNEL = 18
    STORE = 19
    PET = 21
    MANUAL = 22
    CHAMPIONSHIP = 23
    ANTIADDICTION = 24
    FRESH = 25


class ERoomProto:
    """tcp.ERoom+Proto [TypeDef 5896]"""
    NONE = 0
    ROOMLIST = 1
    CREATE = 2
    JOIN = 3
    SPECTATE = 4
    JOIN_NTF = 5
    LEAVE = 6
    LEAVE_NTF = 7
    DISMISS_NTF = 8
    KICK = 9
    KICK_NTF = 10
    START = 11
    ROOMINFO = 12
    CHANGE = 13
    CHANGE_NTF = 14
    DROPOMATCH = 15
    MATCHMAKINGSUSS_NTF = 16
    ROOMSTATE_NTF = 17
    CHECKINGAMEPLAYER = 18
    CLEARINGAMEPLAYER = 19
    SWITCHSEAT = 20
    SWITCHSEAT_NTF = 21
    INVITE = 22
    INVITE_NTF = 23
    SETREADY = 24
    SETREADY_NTF = 25
    REAL_CREATE = 26
    ADMIN_SET_ICON = 27
    ADMIN_DISMISS_ROOM = 28
    ANTIADDICTION_NFT = 29
    TEAMMATEHEATING_NFT = 30
    ADMIN_GET_CUSTOMROOM_MATCHSTATS = 31


class ERoomErrCode:
    """tcp.ERoom+ErrCode [TypeDef 5897]"""
    SUSS = 0
    NOROOM = 1
    REACHMAXMEMBERS = 2
    REACHMAXSPECTATORS = 3
    ALREADYINROOM = 4
    NOTINROOM = 5
    ROOMINGAME = 6
    ROOMNOTINGAME = 7
    CANNOTCREATEROOM = 8
    NOGAMESERVERAVAILABLE = 9
    INVALIDCODE = 10
    CANNOTKICK = 11
    NOTOWNER = 12
    GENMATCHIDFAIL = 13
    LOGINGAMESERVERTIMEOUT = 14
    CREATEROOMFAIL = 15
    JOININVALIDPLAYERCNT = 16
    DIRTYWORD = 17
    SEATOCCUPIED = 18
    CANNOTSWITCHSEAT = 19
    INVALIDMEMBERNUM = 20
    NOTENOUGHROOMCARD = 21
    INVALIDOPTIONS = 22
    CANNOTINVITESELF = 23
    INVALIDROOMTYPE = 24
    INVITEEALREADYINGROUP = 25
    INVITEEALREADYINROOM = 26
    INVITEEALREADYINGAME = 27
    INVITEEALREADYOFFLINE = 28
    NOTENOUGHMEMEBERS = 29
    REACHMAXINGAMEROOMNUMLIMIT = 30
    NEGATIVEGEMS = 31
    ANTIADDICTIONBAN = 32
    ROOMCENTERNOTREADY = 33


class ERoomType:
    """tcp.ERoom+Type [TypeDef 5898]"""
    NONE = 0
    CASUAL = 1
    LEAGUE_NORMAL = 2
    LEAGUE_OFFICIAL = 3
    CHAMPIONSHIP = 4


class ERoomPlayerRole:
    """tcp.ERoom+PlayerRole"""
    NONE = 0
    MEMBER = 1
    SPECTATOR = 2


class ERoomPlayerState:
    """tcp.ERoom+PlayerState"""
    IDLE = 0
    LOADING = 1
    INGAME = 2
    INGAME_CAN_RECONNECT = 3


class ERoomState:
    """tcp.ERoom+State"""
    IDLE = 0
    INGAME = 1


class ERoomDismissReason:
    """tcp.ERoom+DismissReason"""
    NONE = 0
    NORMAL = 1
    OFFLINE = 2
    TIMEOUT = 3
    ADMIN = 4


class UpdateRoomEvent:
    """tcp.ERoom+UpdateRoomEvent [TypeDef 5903]"""
    NONE = 0
    INIT = 1
    SEND_ALL_ROOMS = 2
    STATE = 3
    OPTIONS = 4
    MEMBER_NUM = 5
    DISMISS_ROOM = 6
    CREATE_ROOM = 7
    EMPTY = 8


class ProtoERoomCmd:
    """proto.ERoom+Cmd"""
    NONE = 0
    SEND_ALL_ROOMS = 1
    OK = 2


class EMatchmakingProto:
    """tcp.EMatchmaking+Proto"""
    START = 1
    CANCEL = 2
    GROUPSTART = 3
    GROUPCANCEL = 4
    MATCHMAKINGSUSS_NTF = 5
    DROPMATCH = 6
    GAMEOPENINGINFO = 7
    CHECKINGAMEPLAYER = 8
    CLEARINGAMEPLAYER = 9
    ANTIADDICTION_NFT = 10


class EMatchmakingErrCode:
    """tcp.EMatchmaking+ErrCode"""
    SUSS = 0
    ALREADYINMATCHMAKING = 1
    CREATEPLAYERFAIL = 2
    JOINSINGLEPOOLFAIL = 3
    JOINMULTIPOOLFAIL = 4
    NOGAMESERVERAVAILABLE = 5
    INITMATCHFAIL = 6
    LOGINGAMESERVERTIMEOUT = 7
    MMTIMEOUT = 8
    NOSUCHPOOL = 9
    MAPNOTOPEN = 10
    INVALIDRANDOMMAPCONFIG = 11
    RANKINGMATCHLEVELLIMIT = 12
    NOTQUALIFIEDFORFREEWTA = 13
    INVALIDWTACURRENCYTYPE = 14
    NOTENOUGHMONEYFORWTA = 15
    NEGATIVEGEMS = 16
    ANTIADDICTIONBAN = 17


class EMatchmakingPlayerState:
    """tcp.EMatchmaking+PlayerState"""
    MATCHMAKING = 0
    LOADING = 1
    INGAME = 2
    INGAME_CAN_RECONNECT = 3


class LevelVisualStyle:
    """tcp.EMatchmaking+LevelVisualStyle"""
    NORMAL = 0
    NIGHT = 1
    SNOW = 2


class ServerStatus:
    """proto.EGameServer+ServerStatus"""
    NONE = 0
    RUNNING = 1
    SOFTCLOSED = 2
    DOWN = 3


class ECustomRoomSetting:
    """COW.ECustomRoomSetting [TypeDef 7658] bitflags"""
    HIDE_KILL_INFO = 1
    UNLIMITED_AMMO = 2
    NO_FALLING_DAMAGE = 4
    NO_LOADOUT = 8
    NO_AIRDROP = 16
    NO_SKILL = 32
    NO_VEHICLE = 64
    PLAYER_HP_START = 256
    PLAYER_HP_END = 1024
    PLAYER_EP_START = 2048
    PLAYER_EP_END = 8192
    PLAYER_SPEED_START = 16384
    PLAYER_SPEED_END = 65536
    DROP_LIST_START = 131072
    DROP_LIST_END = 1048576
    PLAYER_JUMP_HEIGHT_START = 2097152
    PLAYER_JUMP_HEIGHT_END = 8388608
    ACCTATALSTATS = 16777216


# ---------------------------------------------------------------------------
# TCP Wire Framing Helpers
# ---------------------------------------------------------------------------

def encode_tcp_packet_s2c(cmd: int, payload: bytes) -> bytes:
    """
    Encode S2C TCP frame (5-byte header, NO flag byte):
    [1B cmd][4B BE int32 length][payload]
    """
    return struct.pack(">Bi", int(cmd) & 0xFF, len(payload)) + payload


def decode_tcp_packet_c2s(raw: bytes) -> Tuple[int, int, bytes]:
    """
    Decode C2S TCP frame (6-byte header):
    [1B cmd][1B flag][4B BE int32 length][payload]
    Returns (cmd, flag, payload).
    """
    if len(raw) < 6:
        raise ValueError(f"C2S TCP frame too short: {len(raw)} bytes")
    cmd, flag, length = struct.unpack_from(">BBi", raw, 0)
    payload = raw[6 : 6 + max(0, length)]
    return cmd, flag, payload


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _encode_repeated(tag: int, items: Iterable[Any], encoder_fn) -> bytes:
    buf = bytearray()
    for item in items:
        buf += encode_submessage(tag, encoder_fn(item))
    return bytes(buf)


def _as_fields(data: Any) -> Dict[int, List[Any]]:
    return data if isinstance(data, dict) else decode_proto(data)


def _decode_ping_list(fields: Dict[int, List[Any]], tag: int) -> List[Dict[str, Any]]:
    return [decode_account_idc_ping_info(sub) for sub in get_submessages(fields, tag)]


def _decode_join_players(fields: Dict[int, List[Any]], tag: int) -> List[Dict[str, Any]]:
    return [decode_join_room_player_info(sub) for sub in get_submessages(fields, tag)]


# ---------------------------------------------------------------------------
# Request Decoders
# ---------------------------------------------------------------------------

def decode_account_idc_ping_info(data: Any) -> Dict[str, Any]:
    """Decode `tcp.AccountIDCPingInfo`: 1: string idc, 2: int32 ping."""
    f = _as_fields(data)
    return {
        "idc": get_string(f, 1, ""),
        "ping": get_int32(f, 2, 0),
    }


def decode_join_room_player_info(data: Any) -> Dict[str, Any]:
    """Decode `tcp.JoinRoomPlayerInfo`: 1: conn_id, 2: emulator_score, 3: AccountMatchInfo."""
    f = _as_fields(data)
    bf = get_submessage(f, 3)
    account_id = get_varint(bf, 1, 0) if bf else 0
    nickname = get_string(bf, 2, "") if bf else ""
    banner_id = get_varint(bf, 9, 901000001) if bf else 901000001
    head_pic = get_varint(bf, 10, 902000001) if bf else 902000001
    return {
        "conn_id": get_varint(f, 1, 0),
        "emulator_score": get_varint(f, 2, 0),
        "account_id": account_id,
        "nickname": nickname,
        "banner_id": banner_id,
        "head_pic": head_pic,
        "basic_info_fields": bf,
    }


def decode_room_list_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.RoomListReq`: 1: uint64 room_id, 2: tcp.ERoom.Type room_type."""
    f = decode_proto(data)
    return {
        "room_id": get_varint(f, 1, 0),
        "room_type": get_varint(f, 2, ERoomType.NONE),
    }


def decode_room_create_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.RoomCreateReq`:
    1: map_id, 2: game_mode, 3: group_mode, 4: room_name, 5: code,
    6: max_member_num, 7: max_spectator_num, 8: enable_death_spectate,
    9: room_type, 10: group_id, 11: enable_group_icon, 12: level_visual_style,
    13: room_id, 14: room_setting, 15: List<AccountIDCPingInfo> ping_list.
    """
    f = decode_proto(data)
    return {
        "map_id": get_varint(f, 1, 1),
        "game_mode": get_varint(f, 2, GameMode.BATTLE_ROYALE),
        "group_mode": get_varint(f, 3, GroupMode.QUAD),
        "room_name": get_string(f, 4, ""),
        "code": get_string(f, 5, ""),
        "max_member_num": get_varint(f, 6, 48),
        "max_spectator_num": get_varint(f, 7, 16),
        "enable_death_spectate": get_bool(f, 8, False),
        "room_type": get_varint(f, 9, ERoomType.CASUAL),
        "group_id": get_varint(f, 10, 0),
        "enable_group_icon": get_bool(f, 11, False),
        "level_visual_style": get_varint(f, 12, LevelVisualStyle.NORMAL),
        "room_id": get_varint(f, 13, 0),
        "room_setting": get_varint(f, 14, 0),
        "ping_list": _decode_ping_list(f, 15),
    }


def decode_room_join_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.RoomJoinReq`:
    1: room_id, 2: code, 3: group_id, 4: is_solo, 5: List<JoinRoomPlayerInfo>,
    6: group_name, 7: inviter_account_id, 8: List<AccountIDCPingInfo>.
    """
    f = decode_proto(data)
    return {
        "room_id": get_varint(f, 1, 0),
        "code": get_string(f, 2, ""),
        "group_id": get_varint(f, 3, 0),
        "is_solo": get_bool(f, 4, True),
        "players": _decode_join_players(f, 5),
        "group_name": get_string(f, 6, ""),
        "inviter_account_id": get_varint(f, 7, 0),
        "ping_list": _decode_ping_list(f, 8),
    }


def decode_room_spectate_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.RoomSpectateReq`:
    1: room_id, 2: code, 3: group_id, 4: is_solo, 5: List<JoinRoomPlayerInfo>,
    6: List<AccountIDCPingInfo>.
    """
    f = decode_proto(data)
    return {
        "room_id": get_varint(f, 1, 0),
        "code": get_string(f, 2, ""),
        "group_id": get_varint(f, 3, 0),
        "is_solo": get_bool(f, 4, True),
        "players": _decode_join_players(f, 5),
        "ping_list": _decode_ping_list(f, 6),
    }


def decode_room_id_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.RoomIDReq` / `tcp.RoomInfoReq`: 1: uint64 room_id."""
    f = decode_proto(data)
    return {"room_id": get_varint(f, 1, 0)}


def decode_room_change_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.RoomChangeReq`:
    1: room_id, 2: room_name, 3: code, 4: map_id, 5: game_mode,
    6: max_member_num, 7: max_spectator_num, 8: enable_death_spectate,
    9: enable_group_icon, 10: level_visual_style, 11: room_setting.
    """
    f = decode_proto(data)
    return {
        "room_id": get_varint(f, 1, 0),
        "room_name": get_string(f, 2, ""),
        "has_room_name": 2 in f,
        "code": get_string(f, 3, ""),
        "has_code": 3 in f,
        "map_id": get_varint(f, 4, 1),
        "has_map_id": 4 in f,
        "game_mode": get_varint(f, 5, GameMode.BATTLE_ROYALE),
        "has_game_mode": 5 in f,
        "max_member_num": get_varint(f, 6, 48),
        "has_max_member_num": 6 in f,
        "max_spectator_num": get_varint(f, 7, 16),
        "has_max_spectator_num": 7 in f,
        "enable_death_spectate": get_bool(f, 8, False),
        "has_enable_death_spectate": 8 in f,
        "enable_group_icon": get_bool(f, 9, False),
        "has_enable_group_icon": 9 in f,
        "level_visual_style": get_varint(f, 10, LevelVisualStyle.NORMAL),
        "has_level_visual_style": 10 in f,
        "room_setting": get_varint(f, 11, 0),
        "has_room_setting": 11 in f,
    }


def decode_room_switch_seat_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.RoomSwitchSeatReq`:
    1: room_id, 2: account_id, 3: to_role, 4: to_room_pos, 5: to_group_pos.
    """
    f = decode_proto(data)
    return {
        "room_id": get_varint(f, 1, 0),
        "account_id": get_varint(f, 2, 0),
        "to_role": get_varint(f, 3, ERoomPlayerRole.MEMBER),
        "to_room_pos": get_varint(f, 4, 0),
        "to_group_pos": get_varint(f, 5, 0),
    }


def decode_room_kick_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.RoomKickReq`: 1: uint64 kick_account_id."""
    f = decode_proto(data)
    return {"kick_account_id": get_varint(f, 1, 0)}


def decode_room_invite_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.RoomInviteReq`: 1: uint64 invitee_id."""
    f = decode_proto(data)
    return {"invitee_id": get_varint(f, 1, 0)}


def decode_room_set_ready_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.RoomSetReadyReq`: 1: bool ready, 2: bool set_group."""
    f = decode_proto(data)
    return {
        "ready": get_bool(f, 1, True),
        "set_group": get_bool(f, 2, False),
    }


def decode_group_join_room_req(data: bytes) -> Dict[str, Any]:
    """
    Decode `tcp.GroupJoinRoomReq`:
    1: room_id, 2: code, 3: group_id, 4: is_solo, 5: group_name.
    """
    f = decode_proto(data)
    return {
        "room_id": get_varint(f, 1, 0),
        "code": get_string(f, 2, ""),
        "group_id": get_varint(f, 3, 0),
        "is_solo": get_bool(f, 4, False),
        "group_name": get_string(f, 5, ""),
    }


def decode_game_opening_info_req(data: bytes) -> Dict[str, Any]:
    """Decode `tcp.GameOpeningInfoReq`: 1: string region, 2: string language."""
    f = decode_proto(data)
    return {
        "region": get_string(f, 1, "IND"),
        "language": get_string(f, 2, "en"),
    }


# ---------------------------------------------------------------------------
# Room Encoders
# ---------------------------------------------------------------------------

def _encode_room_basic_fields(room: Dict[str, Any], include_code: bool = False) -> bytes:
    """
    Shared encoder for `tcp.RoomBasicInfo` (tags 1..16) and
    `proto.RoomBasicInfo` (tags 1..16 + tag 17 `code`).
    """
    password = str(room.get("password", room.get("code", "")))
    has_password = bool(room.get("has_password", bool(password)))
    members = room.get("members", [])
    spectators = room.get("spectators", [])

    buf = bytearray()
    buf += encode_uint64(1, int(room.get("room_id", room.get("id", 0))))
    buf += encode_string(2, str(room.get("name", "IND Custom Room")))
    buf += encode_uint32(3, int(room.get("map_id", 1)))
    buf += encode_uint32(4, int(room.get("game_mode", GameMode.BATTLE_ROYALE)))
    buf += encode_uint32(5, int(room.get("group_mode", GroupMode.QUAD)))
    buf += encode_uint32(6, int(room.get("cur_member_num", len(members))))
    buf += encode_uint32(7, int(room.get("max_players", room.get("max_member_num", 48))))
    buf += encode_uint32(8, int(room.get("cur_spectator_num", len(spectators))))
    buf += encode_uint32(9, int(room.get("max_spectator_num", 16)))
    buf += encode_uint32(10, int(room.get("state", ERoomState.IDLE)))
    buf += encode_bool(11, has_password)
    buf += encode_uint32(12, int(room.get("banner", 901000001)))
    buf += encode_uint32(13, int(room.get("color", 0)))
    buf += encode_uint32(14, int(room.get("icon", 0)))
    buf += encode_uint32(15, int(room.get("room_type", ERoomType.CASUAL)))
    buf += encode_uint32(16, int(room.get("level_visual_style", LevelVisualStyle.NORMAL)))
    if include_code and password:
        buf += encode_string(17, password)
    return bytes(buf)


def encode_tcp_room_basic_info(room: Dict[str, Any]) -> bytes:
    """Encode `tcp.RoomBasicInfo` (tags 1..16)."""
    return _encode_room_basic_fields(room, include_code=False)


def encode_tcp_room_list_res(rooms: Sequence[Dict[str, Any]]) -> bytes:
    """Encode `tcp.RoomListRes`: 1: List<tcp.RoomBasicInfo>."""
    return _encode_repeated(1, rooms, encode_tcp_room_basic_info)


def encode_proto_room_basic_info(room: Dict[str, Any]) -> bytes:
    """Encode `proto.RoomBasicInfo` (tags 1..16 + 17: string code)."""
    return _encode_room_basic_fields(room, include_code=True)


def encode_get_all_rooms_res(rooms: Sequence[Dict[str, Any]]) -> bytes:
    """Encode `proto.GetAllRoomsRes`: 1: List<proto.RoomBasicInfo> rooms."""
    return _encode_repeated(1, rooms, encode_proto_room_basic_info)


def encode_room_player_info(player: Dict[str, Any]) -> bytes:
    """
    Encode `tcp.RoomPlayerInfo`:
    1: group_id, 2: account_id, 3: nickname, 4: emulator_score,
    5: head_pic, 6: ready, 7: banner_id, 8: role.
    """
    buf = bytearray()
    buf += encode_uint64(1, int(player.get("group_id", 0)))
    buf += encode_uint64(2, int(player.get("account_id", 0)))
    buf += encode_string(3, str(player.get("nickname", "Player")))
    buf += encode_uint32(4, int(player.get("emulator_score", 0)))
    buf += encode_uint32(5, int(player.get("head_pic", 902000001)))
    buf += encode_bool(6, bool(player.get("ready", False)))
    buf += encode_uint32(7, int(player.get("banner_id", 901000001)))
    buf += encode_uint32(8, int(player.get("role", ERoomPlayerRole.MEMBER)))
    return bytes(buf)


def encode_room_group_info(group: Dict[str, Any]) -> bytes:
    """
    Encode `tcp.RoomGroupInfo`:
    1: uint64 id, 2: string name, 3: List<tcp.RoomPlayerInfo> members.
    """
    buf = bytearray()
    buf += encode_uint64(1, int(group.get("id", 0)))
    if group.get("name"):
        buf += encode_string(2, str(group["name"]))
    buf += _encode_repeated(3, group.get("members", []), encode_room_player_info)
    return bytes(buf)


def encode_room_info(room: Dict[str, Any]) -> bytes:
    """
    Encode `tcp.RoomInfo` (exact tags 1..18):
    1: id, 2: name, 3: owner, 4: map_id, 5: game_mode, 6: group_mode,
    7: max_member_num, 8: max_spectator_num, 9: state, 10: code,
    11: List<RoomGroupInfo> groups, 12: List<RoomPlayerInfo> spectators,
    13: enable_death_spectate, 14: room_type, 15: enable_group_icon,
    16: match_times, 17: level_visual_style, 18: room_setting.
    """
    password = str(room.get("password", room.get("code", "")))
    buf = bytearray()
    buf += encode_uint64(1, int(room.get("room_id", room.get("id", 0))))
    buf += encode_string(2, str(room.get("name", "IND Custom Room")))
    buf += encode_uint64(3, int(room.get("owner_id", room.get("owner", 0))))
    buf += encode_uint32(4, int(room.get("map_id", 1)))
    buf += encode_uint32(5, int(room.get("game_mode", GameMode.BATTLE_ROYALE)))
    buf += encode_uint32(6, int(room.get("group_mode", GroupMode.QUAD)))
    buf += encode_uint32(7, int(room.get("max_players", room.get("max_member_num", 48))))
    buf += encode_uint32(8, int(room.get("max_spectator_num", 16)))
    buf += encode_uint32(9, int(room.get("state", ERoomState.IDLE)))
    if password:
        buf += encode_string(10, password)
    buf += _encode_repeated(11, room.get("groups", []), encode_room_group_info)
    buf += _encode_repeated(12, room.get("spectators_info", []), encode_room_player_info)
    buf += encode_bool(13, bool(room.get("enable_death_spectate", False)))
    buf += encode_uint32(14, int(room.get("room_type", ERoomType.CASUAL)))
    buf += encode_bool(15, bool(room.get("enable_group_icon", False)))
    buf += encode_uint32(16, int(room.get("match_times", 0)))
    buf += encode_uint32(17, int(room.get("level_visual_style", LevelVisualStyle.NORMAL)))
    buf += encode_uint32(18, int(room.get("room_setting", 0)))
    return bytes(buf)


def encode_room_join_ntf(join_players: Sequence[Dict[str, Any]], room: Dict[str, Any]) -> bytes:
    """Encode `tcp.RoomJoinNtf`: 1: List<RoomPlayerInfo> join_player_list, 2: RoomInfo room_info."""
    buf = bytearray()
    buf += _encode_repeated(1, join_players, encode_room_player_info)
    buf += encode_submessage(2, encode_room_info(room))
    return bytes(buf)


def encode_room_leave_ntf(leaver: Dict[str, Any], room: Dict[str, Any]) -> bytes:
    """Encode `tcp.RoomLeaveNtf`: 1: RoomPlayerInfo leaver_info, 2: RoomInfo room_info."""
    buf = bytearray()
    buf += encode_submessage(1, encode_room_player_info(leaver))
    buf += encode_submessage(2, encode_room_info(room))
    return bytes(buf)


def encode_room_dismiss_ntf(
    leaver_id: int,
    room_id: int,
    reason: int = ERoomDismissReason.NORMAL,
) -> bytes:
    """Encode `tcp.RoomDismissNtf`: 1: leaver_id, 2: room_id, 3: DismissReason."""
    buf = bytearray()
    buf += encode_uint64(1, int(leaver_id))
    buf += encode_uint64(2, int(room_id))
    buf += encode_uint32(3, int(reason))
    return bytes(buf)


def encode_room_kick_ntf(kicked_player: Dict[str, Any], room: Dict[str, Any]) -> bytes:
    """Encode `tcp.RoomKickNtf`: 1: RoomPlayerInfo kick_player_info, 2: RoomInfo room_info."""
    buf = bytearray()
    buf += encode_submessage(1, encode_room_player_info(kicked_player))
    buf += encode_submessage(2, encode_room_info(room))
    return bytes(buf)


def encode_room_state_ntf(room_id: int, room_state: int) -> bytes:
    """Encode `tcp.RoomStateNtf`: 1: uint64 room_id, 2: uint32 state."""
    return encode_uint64(1, int(room_id)) + encode_uint32(2, int(room_state))


def encode_room_invite_ntf(
    room_id: int,
    inviter: Dict[str, Any],
    map_id: int = 1,
    game_mode: int = GameMode.BATTLE_ROYALE,
    group_mode: int = GroupMode.QUAD,
    owner_id: int = 0,
) -> bytes:
    """
    Encode `tcp.RoomInviteNtf`:
    1: room_id, 2: inviter_info, 3: map_id, 4: game_mode, 5: group_mode, 6: owner_id.
    """
    buf = bytearray()
    buf += encode_uint64(1, int(room_id))
    buf += encode_submessage(2, encode_room_player_info(inviter))
    buf += encode_uint32(3, int(map_id))
    buf += encode_uint32(4, int(game_mode))
    buf += encode_uint32(5, int(group_mode))
    buf += encode_uint64(6, int(owner_id))
    return bytes(buf)


def encode_room_set_ready_ntf(room_id: int, players: Sequence[Dict[str, Any]]) -> bytes:
    """Encode `tcp.RoomSetReadyNtf`: 1: uint64 room_id, 2: List<RoomPlayerInfo> players."""
    buf = bytearray()
    buf += encode_uint64(1, int(room_id))
    buf += _encode_repeated(2, players, encode_room_player_info)
    return bytes(buf)


def encode_room_card_info(card_id: int = 600000001, cnt: int = 10, expire_time: int = 0) -> bytes:
    """Encode `tcp.RoomCardInfo`: 1: uint32 id, 2: uint32 cnt, 3: uint32 expire_time."""
    buf = bytearray()
    buf += encode_uint32(1, int(card_id))
    buf += encode_uint32(2, int(cnt))
    if expire_time:
        buf += encode_uint32(3, int(expire_time))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Game Opening Info & Game Server List Encoders
# ---------------------------------------------------------------------------

def encode_game_opening_info_desc(desc: Dict[str, Any]) -> bytes:
    """
    Encode `proto.GameOpeningInfoDesc` (exact IL2CPP tags skipping 2, 5, 7, 16):
    1: uint32 map_id
    3: string name
    4: string language
    6: string start_time
    8: string end_time
    9: string tips
    10: uint32 limited_rank
    11: uint32 limited_count
    12: bool enable
    13: uint32 game_mode
    14: uint32 match_mode
    15: bool is_new
    17: string config_start_time
    18: string config_end_time
    19: string player_count_limit
    20: uint32 level_visual_style
    21: string difficulty
    22: bool pve_force_mm
    23: string weekday
    24: uint32 sort_id
    """
    buf = bytearray()
    buf += encode_uint32(1, int(desc.get("map_id", 1)))
    buf += encode_string(3, str(desc.get("name", "")))
    buf += encode_string(4, str(desc.get("language", "en")))
    buf += encode_string(6, str(desc.get("start_time", "00:00:00")))
    buf += encode_string(8, str(desc.get("end_time", "23:59:59")))
    buf += encode_string(9, str(desc.get("tips", "")))
    buf += encode_uint32(10, int(desc.get("limited_rank", 0)))
    buf += encode_uint32(11, int(desc.get("limited_count", 0)))
    buf += encode_bool(12, bool(desc.get("enable", True)))
    buf += encode_uint32(13, int(desc.get("game_mode", GameMode.BATTLE_ROYALE)))
    buf += encode_uint32(14, int(desc.get("match_mode", MatchMode.CASUAL)))
    buf += encode_bool(15, bool(desc.get("is_new", False)))
    buf += encode_string(17, str(desc.get("config_start_time", "2020-01-01 00:00:00")))
    buf += encode_string(18, str(desc.get("config_end_time", "2030-01-01 23:59:59")))
    buf += encode_string(19, str(desc.get("player_count_limit", "1;2;4")))
    buf += encode_uint32(20, int(desc.get("level_visual_style", LevelVisualStyle.NORMAL)))
    buf += encode_string(21, str(desc.get("difficulty", "1")))
    buf += encode_bool(22, bool(desc.get("pve_force_mm", False)))
    buf += encode_string(23, str(desc.get("weekday", "0")))
    buf += encode_uint32(24, int(desc.get("sort_id", 1)))
    return bytes(buf)


def encode_game_mode_name_desc(mode_id: int, language: str, translation: str) -> bytes:
    """Encode `proto.GameModeNameDesc`: 1: uint32 mode_id, 2: string language, 3: string translation."""
    buf = bytearray()
    buf += encode_uint32(1, int(mode_id))
    buf += encode_string(2, str(language))
    buf += encode_string(3, str(translation))
    return bytes(buf)


def encode_game_opening_info_res(
    descs: Sequence[Dict[str, Any]],
    timezone_offset_secs: int = 0,
    mode_names: Sequence[Tuple[int, str, str]] = (),
) -> bytes:
    """
    Encode `proto.GameOpeningInfoRes`:
    1: GameOpeningInfoDescList (1: List<GameOpeningInfoDesc>),
    2: int64 timezone_offset_secs,
    3: GameModeNameList (1: List<GameModeNameDesc>).
    """
    desc_list = _encode_repeated(1, descs, encode_game_opening_info_desc)
    name_list = bytearray()
    for mode_id, lang, trans in mode_names:
        name_list += encode_submessage(1, encode_game_mode_name_desc(mode_id, lang, trans))

    buf = bytearray()
    buf += encode_submessage(1, desc_list)
    buf += encode_int64(2, int(timezone_offset_secs))
    if name_list:
        buf += encode_submessage(3, bytes(name_list))
    return bytes(buf)


def encode_ping_server_desc(desc: Dict[str, Any]) -> bytes:
    """
    Encode `proto.PingServerDesc`:
    1: string region, 2: string ip, 3: string start_time, 4: string end_time, 5: float ping_random.
    """
    buf = bytearray()
    buf += encode_string(1, str(desc.get("region", "IND")))
    buf += encode_string(2, str(desc.get("ip", "127.0.0.1:39800")))
    if desc.get("start_time"):
        buf += encode_string(3, str(desc["start_time"]))
    if desc.get("end_time"):
        buf += encode_string(4, str(desc["end_time"]))
    buf += encode_float(5, float(desc.get("ping_random", 0.0)))
    return bytes(buf)


def encode_game_server_node_manager_desc(desc: Dict[str, Any]) -> bytes:
    """
    Encode `proto.GameServerNodeManagerDesc`:
    1: string region, 2: string node_name, 3: string server_ip,
    4: bool is_default, 5: uint32 warn_capacity.
    """
    buf = bytearray()
    buf += encode_string(1, str(desc.get("region", "IND")))
    buf += encode_string(2, str(desc.get("node_name", "IND-Primary-01")))
    buf += encode_string(3, str(desc.get("server_ip", "127.0.0.1:39800")))
    buf += encode_bool(4, bool(desc.get("is_default", True)))
    buf += encode_uint32(5, int(desc.get("warn_capacity", 1000)))
    return bytes(buf)


def encode_game_server_list_res(
    nodes: Sequence[Dict[str, Any]],
    ping_servers: Sequence[Dict[str, Any]] = (),
) -> bytes:
    """
    Encode game server node + ping server list for `/GetGameServerList`:
    1: List<proto.GameServerNodeManagerDesc> nodes,
    2: List<proto.PingServerDesc> ping_servers.
    """
    buf = bytearray()
    buf += _encode_repeated(1, nodes, encode_game_server_node_manager_desc)
    buf += _encode_repeated(2, ping_servers, encode_ping_server_desc)
    return bytes(buf)
