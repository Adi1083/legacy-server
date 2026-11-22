"""
HTTP and TCP handlers for Free Fire 1.39 Custom Rooms, Matchmaking,
Game Opening Info, and Game Server List endpoints.

HTTP endpoints handled:
  /GetRoomList          -> proto.GetAllRoomsRes
  /CreateRoom           -> tcp.RoomInfo
  /JoinRoom             -> tcp.RoomInfo
  /SpectateRoom         -> tcp.RoomInfo
  /LeaveRoom            -> tcp.RoomLeaveNtf | tcp.RoomDismissNtf
  /KickRoomPlayer       -> tcp.RoomKickNtf
  /RoomInfo             -> tcp.RoomInfo
  /GetRoomInfo          -> tcp.RoomInfo
  /ChangeRoom           -> tcp.RoomInfo
  /SetRoomReady         -> tcp.RoomSetReadyNtf
  /SwitchRoomSeat       -> tcp.RoomInfo
  /InviteRoom           -> tcp.RoomInviteNtf
  /StartRoom            -> tcp.MatchmakingSussNtf
  /DropRoomMatch        -> tcp.RoomStateNtf
  /StartMatchMaking     -> tcp.MatchmakingSussNtf
  /CancelMatchMaking    -> b""
  /GetMatchmakingStatus -> tcp.MatchmakingSussNtf | b""
  /GetGameServerList    -> GameServerNodeManagerDesc + PingServerDesc list
  /GetGameOpeningInfo   -> proto.GameOpeningInfoRes
  /RoomPacket           -> proto.MessageNotify (dispatches tcp.ProtoReq for ROOM)
  /MatchmakingPacket    -> proto.MessageNotify (dispatches tcp.ProtoReq for MATCHMAKING)

TCP dispatchers exported:
  handle_room_tcp_command(cmd, payload, account_id) -> (ret, reply_cmd, reply_bytes)
  handle_matchmaking_tcp_command(cmd, payload, account_id) -> (ret, reply_cmd, reply_bytes)
  handle_tcp_proto_req(protocol, raw_proto_req, account_id) -> bytes (MessageNotify)
  handle_tcp_frame(raw_frame, account_id) -> bytes (5-byte S2C TCP frame or ACK)
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.decoder import decode_proto, get_varint
from proto.room_models import (
    ECustomRoomSetting,
    EMatchmakingErrCode,
    EMatchmakingProto,
    EProtocolProto,
    ERoomDismissReason,
    ERoomErrCode,
    ERoomPlayerRole,
    ERoomProto,
    ERoomState,
    ERoomType,
    GameMode,
    GroupMode,
    LevelVisualStyle,
    MapID,
    MatchMode,
    TCP_HANDSHAKE_ACK,
    decode_game_opening_info_req,
    decode_group_join_room_req,
    decode_matchmaking_group_start_req,
    decode_matchmaking_start_req,
    decode_proto_req,
    decode_room_change_req,
    decode_room_create_req,
    decode_room_id_req,
    decode_room_invite_req,
    decode_room_join_req,
    decode_room_kick_req,
    decode_room_list_req,
    decode_room_set_ready_req,
    decode_room_spectate_req,
    decode_room_switch_seat_req,
    decode_tcp_packet_c2s,
    encode_game_opening_info_res,
    encode_game_server_list_res,
    encode_get_all_rooms_res,
    encode_matchmaking_suss_ntf,
    encode_message_notify,
    encode_room_dismiss_ntf,
    encode_room_info,
    encode_room_invite_ntf,
    encode_room_join_ntf,
    encode_room_kick_ntf,
    encode_room_leave_ntf,
    encode_room_set_ready_ntf,
    encode_room_state_ntf,
    encode_tcp_packet_s2c,
    encode_tcp_room_list_res,
)


# ---------------------------------------------------------------------------
# Runtime Configuration & Extended Room Metadata Store
# ---------------------------------------------------------------------------

_GAME_SERVER_HOST = os.environ.get("INDIA V1_GAME_SERVER_HOST", "10.0.2.2")
_GAME_SERVER_PORT = int(os.environ.get("INDIA V1_GAME_SERVER_PORT", "39800"))
_GAME_SERVER_ADDR = f"{_GAME_SERVER_HOST}:{_GAME_SERVER_PORT}"

_META_LOCK = threading.RLock()
_ROOM_META: Dict[int, Dict[str, Any]] = {}
_MATCH_COUNTER = 700001
_SEEDED = False

_GROUP_MODE_SQUAD_SIZE = {
    GroupMode.SOLO: 1,
    GroupMode.DUAL: 2,
    GroupMode.TRIPLE: 3,
    GroupMode.QUAD: 4,
}


def _next_match_id() -> int:
    from core.state import generate_match_id
    return generate_match_id()


def _default_room_meta(room: Dict[str, Any]) -> Dict[str, Any]:
    owner_id = int(room.get("owner_id", DEFAULT_ACCOUNT_ID))
    return {
        "group_mode": int(room.get("group_mode", GroupMode.QUAD)),
        "max_spectator_num": int(room.get("max_spectator_num", 16)),
        "state": int(room.get("state", ERoomState.IDLE)),
        "enable_death_spectate": bool(room.get("enable_death_spectate", False)),
        "room_type": int(room.get("room_type", ERoomType.CASUAL)),
        "enable_group_icon": bool(room.get("enable_group_icon", False)),
        "match_times": int(room.get("match_times", 0)),
        "level_visual_style": int(room.get("level_visual_style", LevelVisualStyle.NORMAL)),
        "room_setting": int(room.get("room_setting", 0)),
        "banner": int(room.get("banner", 901000001)),
        "color": int(room.get("color", 0)),
        "icon": int(room.get("icon", 0)),
        "spectators": list(room.get("spectators", [])),
        "ready_map": {owner_id: True},
        "seat_map": {owner_id: (1, 1)},  # account_id -> (group_id, pos)
        "emulator_scores": {owner_id: 0},
    }


def _get_or_init_meta(room: Dict[str, Any]) -> Dict[str, Any]:
    rid = int(room["room_id"])
    with _META_LOCK:
        meta = _ROOM_META.get(rid)
        if meta is None:
            meta = _default_room_meta(room)
            _ROOM_META[rid] = meta
        return meta


def _ensure_seeded_rooms() -> None:
    """Populate initial custom rooms in core.state when the room list is empty."""
    global _SEEDED
    with _META_LOCK:
        if _SEEDED and state.list_rooms():
            return
        if not state.list_rooms():
            defaults = [
                {
                    "owner_id": 1000000002,
                    "name": "Bermuda Classic Public",
                    "map_id": 1,
                    "game_mode": GameMode.BATTLE_ROYALE,
                    "group_mode": GroupMode.QUAD,
                    "max_players": 48,
                    "max_spectator_num": 16,
                    "password": "",
                    "room_type": ERoomType.CASUAL,
                    "room_setting": 0,
                },
                {
                    "owner_id": 1000000003,
                    "name": "Clash Squad 4v4 Unlimited",
                    "map_id": 1,
                    "game_mode": GameMode.CS,
                    "group_mode": GroupMode.QUAD,
                    "max_players": 8,
                    "max_spectator_num": 8,
                    "password": "",
                    "room_type": ERoomType.CASUAL,
                    "room_setting": ECustomRoomSetting.UNLIMITED_AMMO,
                },
                {
                    "owner_id": 1000000004,
                    "name": "Scrims Tournament Room",
                    "map_id": 2,
                    "game_mode": GameMode.BATTLE_ROYALE,
                    "group_mode": GroupMode.QUAD,
                    "max_players": 48,
                    "max_spectator_num": 16,
                    "password": "139",
                    "room_type": ERoomType.LEAGUE_NORMAL,
                    "room_setting": ECustomRoomSetting.HIDE_KILL_INFO,
                },
            ]
            for cfg in defaults:
                created = state.create_room(
                    owner_id=cfg["owner_id"],
                    name=cfg["name"],
                    map_id=cfg["map_id"],
                    game_mode=cfg["game_mode"],
                    max_players=cfg["max_players"],
                    password=cfg["password"],
                )
                rid = int(created["room_id"])
                meta = _default_room_meta(created)
                meta["group_mode"] = cfg["group_mode"]
                meta["max_spectator_num"] = cfg["max_spectator_num"]
                meta["room_type"] = cfg["room_type"]
                meta["room_setting"] = cfg["room_setting"]
                _ROOM_META[rid] = meta
        _SEEDED = True


def _resolve_profile(account_id: int) -> Dict[str, Any]:
    prof = state.get_profile(account_id)
    if prof:
        return prof
    return {
        "account_id": int(account_id),
        "nickname": f"Player_{account_id}",
        "head_pic": 902000001,
        "banner_id": 901000001,
    }


def _build_player_entry(
    account_id: int,
    meta: Dict[str, Any],
    role: int = ERoomPlayerRole.MEMBER,
    group_id: Optional[int] = None,
) -> Dict[str, Any]:
    prof = _resolve_profile(account_id)
    seat = meta.get("seat_map", {}).get(account_id, (1, 1))
    gid = int(group_id if group_id is not None else seat[0])
    return {
        "group_id": gid,
        "account_id": int(account_id),
        "nickname": str(prof.get("nickname", f"Player_{account_id}")),
        "emulator_score": int(meta.get("emulator_scores", {}).get(account_id, 0)),
        "head_pic": int(prof.get("head_pic", 902000001)),
        "ready": bool(meta.get("ready_map", {}).get(account_id, False)),
        "banner_id": int(prof.get("banner_id", 901000001)),
        "role": int(role),
    }


def _build_full_room_dict(room: Dict[str, Any]) -> Dict[str, Any]:
    meta = _get_or_init_meta(room)
    with _META_LOCK:
        group_mode = int(meta["group_mode"])
        squad_size = max(1, _GROUP_MODE_SQUAD_SIZE.get(group_mode, 4))
        members = [int(m) for m in room.get("members", [])]
        spectators = [int(s) for s in meta.get("spectators", [])]

        groups_by_id: Dict[int, List[Dict[str, Any]]] = {}
        for idx, aid in enumerate(members):
            seat = meta["seat_map"].get(aid)
            if seat is None:
                gid = (idx // squad_size) + 1
                pos = (idx % squad_size) + 1
                meta["seat_map"][aid] = (gid, pos)
            else:
                gid = int(seat[0])
            entry = _build_player_entry(aid, meta, role=ERoomPlayerRole.MEMBER, group_id=gid)
            groups_by_id.setdefault(gid, []).append(entry)

        groups = [
            {"id": gid, "name": f"Team {gid}", "members": plist}
            for gid, plist in sorted(groups_by_id.items())
        ]
        spectators_info = [
            _build_player_entry(sid, meta, role=ERoomPlayerRole.SPECTATOR, group_id=0)
            for sid in spectators
        ]

        return {
            **room,
            "group_mode": group_mode,
            "cur_member_num": len(members),
            "max_member_num": int(room.get("max_players", 48)),
            "cur_spectator_num": len(spectators),
            "max_spectator_num": int(meta["max_spectator_num"]),
            "state": int(meta["state"]),
            "enable_death_spectate": bool(meta["enable_death_spectate"]),
            "room_type": int(meta["room_type"]),
            "enable_group_icon": bool(meta["enable_group_icon"]),
            "match_times": int(meta["match_times"]),
            "level_visual_style": int(meta["level_visual_style"]),
            "room_setting": int(meta["room_setting"]),
            "banner": int(meta["banner"]),
            "color": int(meta["color"]),
            "icon": int(meta["icon"]),
            "spectators": spectators,
            "spectators_info": spectators_info,
            "groups": groups,
        }


def _find_room(room_id: int = 0, account_id: int = 0) -> Optional[Dict[str, Any]]:
    _ensure_seeded_rooms()
    rooms = state.list_rooms()
    if room_id > 0:
        for r in rooms:
            if int(r["room_id"]) == int(room_id):
                return r
    if account_id > 0:
        for r in rooms:
            rid = int(r["room_id"])
            meta = _get_or_init_meta(r)
            if account_id in r.get("members", []) or account_id in meta.get("spectators", []):
                return r
            if int(r.get("owner_id", 0)) == int(account_id):
                return r
    return None


def _build_matchmaking_suss(
    map_id: int = 1,
    game_mode: int = GameMode.BATTLE_ROYALE,
    match_mode: int = MatchMode.CASUAL,
    difficulty: int = 0,
    level_visual_style: int = LevelVisualStyle.NORMAL,
    match_id: int = 0,
) -> bytes:
    mid = match_id or _next_match_id()
    import hashlib
    sec_hex = hashlib.md5(f"sec_{mid}".encode()).hexdigest()
    tok_hex = hashlib.md5(f"prep_{mid}_{int(time.time())}".encode()).hexdigest()

    try:
        from combat.udp_server import get_combat_server
        from combat.match_director import global_match_director
        udp_srv = get_combat_server()
        udp_srv.register_match_token(token=tok_hex, account_id=DEFAULT_ACCOUNT_ID, match_id=mid, nickname="PushpaGG")
        if global_match_director:
            global_match_director.create_match(
                match_id=mid,
                map_id=int(map_id),
                game_mode=int(game_mode),
                match_mode=int(match_mode),
                host_player_id=str(DEFAULT_ACCOUNT_ID),
                host_nickname="PushpaGG",
                bot_count=49,
                prepare_token=tok_hex,
                secret=sec_hex
            )
    except Exception:
        pass

    return encode_matchmaking_suss_ntf(
        match_id=mid,
        server_addr=_GAME_SERVER_ADDR,
        secret=sec_hex,
        prepare_token=tok_hex,
        sleep_ms=0,
        map_id=int(map_id),
        game_mode=int(game_mode),
        match_mode=int(match_mode),
        use_cache=False,
        level_visual_style=int(level_visual_style or 1),
        difficulty=int(difficulty),
        first_login=False,
    )


# ---------------------------------------------------------------------------
# Dynamic Game Modes & Map Registry (Free Fire 1.39 Authentic Reversal)
# ---------------------------------------------------------------------------

_MODE_REGISTRY_LOCK = threading.RLock()
_GAME_MODES_REGISTRY: Dict[str, Dict[str, Any]] = {}
_MODES_SEEDED: bool = False

# Canonical list of all 16 authentic 1.39 modes and map definitions:
AUTHENTIC_139_GAME_MODES: List[Dict[str, Any]] = [
    # --- Bermuda (Map ID 1) ---
    {
        "key": "1_1_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Classic Bermuda",
        "game_mode": GameMode.BATTLE_ROYALE,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 1,
    },
    {
        "key": "1_1_2",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Ranked Bermuda",
        "game_mode": GameMode.BATTLE_ROYALE,
        "match_mode": MatchMode.RANKING,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "",
        "limited_rank": 10,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 2,
    },
    {
        "key": "1_15_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Clash Squad 4v4",
        "game_mode": GameMode.CS,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": True,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 3,
    },
    {
        "key": "1_2_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Speed Royale (Rush Hour)",
        "game_mode": GameMode.SPEED_ROYALE,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Fast-paced 20-player intense battle royale in a high-density zone.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 4,
    },
    {
        "key": "1_16_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Big Head Deathmatch",
        "game_mode": GameMode.BIG_HEAD,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Heads enlarge with consecutive kills! Fast respawns enabled.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": True,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 5,
    },
    {
        "key": "1_3_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Fatal Blade (Fate Royale)",
        "game_mode": GameMode.FATE_ROYALE,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Special arms weapon progression and fast-paced combat.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 6,
    },
    {
        "key": "1_12_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Purge Night (Kill Feast)",
        "game_mode": GameMode.PURGE,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Aggressive night combat with hype juice levels and high tier loot.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 7,
    },
    {
        "key": "1_13_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Cold Dead (Die Twice / Reborn)",
        "game_mode": GameMode.REBORN,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Fall once, rise again! Players resurrect upon their first death.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 8,
    },
    {
        "key": "1_4_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Death Race (Zombie Speed Royale)",
        "game_mode": GameMode.ZOMBIE_SPEED_ROYALE,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Armed amphibious vehicles vs waves of infected runners.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "2",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 9,
    },
    {
        "key": "1_7_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Zombie Panic Ground",
        "game_mode": GameMode.ZOMBIE_GROUND,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Defend the safe zone from mutating horde bosses and undead hordes.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 10,
    },
    {
        "key": "1_14_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Hook & Brick (Grappling Hook)",
        "game_mode": GameMode.HOOK_BRICK,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Vertical rooftops combat with high-velocity grappling hooks.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 11,
    },
    {
        "key": "1_11_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Winner Takes All (Token War)",
        "game_mode": GameMode.WINNER_TAKES_ALL,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Chip stake high-roller battle royale arena.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 12,
    },

    # --- Purgatory / Azores (Map ID 2) ---
    {
        "key": "2_1_1",
        "map_id": MapID.PURGATORY,
        "name": "Purgatory",
        "mode_title": "Classic Purgatory",
        "game_mode": GameMode.BATTLE_ROYALE,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 13,
    },
    {
        "key": "2_1_2",
        "map_id": MapID.PURGATORY,
        "name": "Purgatory",
        "mode_title": "Ranked Purgatory",
        "game_mode": GameMode.BATTLE_ROYALE,
        "match_mode": MatchMode.RANKING,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "",
        "limited_rank": 10,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "1;2;4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1",
        "pve_force_mm": False,
        "weekday": "0",
        "sort_id": 14,
    },

    # --- PVE Death Uprising & Survival (Map ID 3 / 1) ---
    {
        "key": "3_101_1",
        "map_id": MapID.HYAKKI,
        "name": "Death Uprising",
        "mode_title": "Death Uprising (Hyakki Boss)",
        "game_mode": GameMode.PVE_HYAKKI,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "4-player co-op raid boss battle against the Butcher boss.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": True,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1;2;3",
        "pve_force_mm": True,
        "weekday": "0",
        "sort_id": 15,
    },
    {
        "key": "1_102_1",
        "map_id": MapID.BERMUDA,
        "name": "Bermuda",
        "mode_title": "Zombie Survival (PVE SVZombie)",
        "game_mode": GameMode.PVE_SV_ZOMBIE,
        "match_mode": MatchMode.CASUAL,
        "language": "en",
        "start_time": "00:00:00",
        "end_time": "23:59:59",
        "tips": "Survive endless waves of undead mutants and extraction rescue.",
        "limited_rank": 0,
        "limited_count": 0,
        "enable": True,
        "is_new": False,
        "config_start_time": "2020-01-01 00:00:00",
        "config_end_time": "2030-01-01 23:59:59",
        "player_count_limit": "4",
        "level_visual_style": LevelVisualStyle.NORMAL,
        "difficulty": "1;2",
        "pve_force_mm": True,
        "weekday": "0",
        "sort_id": 16,
    },
]


def _ensure_seeded_game_modes() -> None:
    global _MODES_SEEDED
    with _MODE_REGISTRY_LOCK:
        if _MODES_SEEDED and _GAME_MODES_REGISTRY:
            return
        for mode in AUTHENTIC_139_GAME_MODES:
            key = str(mode.get("key") or f"{mode['map_id']}_{mode['game_mode']}_{mode['match_mode']}")
            _GAME_MODES_REGISTRY[key] = dict(mode)
        _MODES_SEEDED = True


def get_game_opening_descriptors(only_enabled: bool = False) -> List[Dict[str, Any]]:
    """Return list of game opening descriptors for GameOpeningInfoRes."""
    _ensure_seeded_game_modes()
    with _MODE_REGISTRY_LOCK:
        descs: List[Dict[str, Any]] = []
        for m in sorted(_GAME_MODES_REGISTRY.values(), key=lambda x: int(x.get("sort_id", 99))):
            if only_enabled and not m.get("enable", True):
                continue
            desc = dict(m)
            desc.pop("key", None)
            desc.pop("mode_title", None)
            descs.append(desc)
        return descs


def get_game_mode_names(lang: str = "en") -> List[Tuple[int, str, str]]:
    """Return authentic mode translations for GameModeNameList."""
    return [
        (GameMode.BATTLE_ROYALE, lang, "Classic"),
        (GameMode.SPEED_ROYALE, lang, "Speed Royal"),
        (GameMode.FATE_ROYALE, lang, "Fatal Blade"),
        (GameMode.ZOMBIE_SPEED_ROYALE, lang, "Death Race"),
        (GameMode.ZOMBIE_GROUND, lang, "Zombie Panic"),
        (GameMode.JANKENPON, lang, "Jan-Ken-Pon"),
        (GameMode.WINNER_TAKES_ALL, lang, "Winner Takes All"),
        (GameMode.PURGE, lang, "Rush Hour"),
        (GameMode.PURGE_LEGACY, lang, "Rush Hour"),
        (GameMode.REBORN, lang, "Cold Dead"),
        (GameMode.HOOK_BRICK, lang, "Hook & Brick"),
        (GameMode.CS, lang, "Clash Squad"),
        (GameMode.CS_LEGACY, lang, "Clash Squad"),
        (GameMode.BIG_HEAD, lang, "Big Head"),
        (GameMode.PVE_HYAKKI, lang, "Death Uprising"),
        (GameMode.PVE_SV_ZOMBIE, lang, "Zombie Survival"),
    ]


def _default_game_opening_descs() -> List[Dict[str, Any]]:
    return get_game_opening_descriptors(only_enabled=False)


def list_modes_admin() -> List[Dict[str, Any]]:
    """Return JSON-serializable list of all authentic modes with status for admin control."""
    _ensure_seeded_game_modes()
    with _MODE_REGISTRY_LOCK:
        return [dict(m) for m in sorted(_GAME_MODES_REGISTRY.values(), key=lambda x: int(x.get("sort_id", 99)))]


def toggle_game_mode(
    map_id: int,
    game_mode: int,
    match_mode: int = 1,
    enable: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Dynamically unlock, enable, or close a specific map/mode combination in real time."""
    _ensure_seeded_game_modes()
    key = f"{int(map_id)}_{int(game_mode)}_{int(match_mode)}"
    with _MODE_REGISTRY_LOCK:
        mode = _GAME_MODES_REGISTRY.get(key)
        if not mode:
            for k, m in _GAME_MODES_REGISTRY.items():
                if int(m["map_id"]) == int(map_id) and int(m["game_mode"]) == int(game_mode):
                    key = k
                    mode = m
                    break
        if not mode:
            return None
        if enable is None:
            mode["enable"] = not bool(mode.get("enable", True))
        else:
            mode["enable"] = bool(enable)
        return dict(mode)


def unlock_all_modes() -> int:
    """Dynamically unlock and enable all 16 authentic 1.39 game modes."""
    _ensure_seeded_game_modes()
    with _MODE_REGISTRY_LOCK:
        for m in _GAME_MODES_REGISTRY.values():
            m["enable"] = True
        return len(_GAME_MODES_REGISTRY)


def lock_optional_modes() -> int:
    """Lock optional experimental modes, leaving core modes active."""
    _ensure_seeded_game_modes()
    core_keys = {"1_1_1", "1_1_2", "2_1_1", "1_15_1"}
    with _MODE_REGISTRY_LOCK:
        locked_cnt = 0
        for k, m in _GAME_MODES_REGISTRY.items():
            if k in core_keys:
                m["enable"] = True
            else:
                m["enable"] = False
                locked_cnt += 1
        return locked_cnt


def update_game_mode(
    map_id: int,
    game_mode: int,
    match_mode: int = 1,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """Update dynamic configuration of a mode (tips, sort_id, is_new, player_count_limit, etc.)."""
    _ensure_seeded_game_modes()
    key = f"{int(map_id)}_{int(game_mode)}_{int(match_mode)}"
    with _MODE_REGISTRY_LOCK:
        mode = _GAME_MODES_REGISTRY.get(key)
        if not mode:
            for k, m in _GAME_MODES_REGISTRY.items():
                if int(m["map_id"]) == int(map_id) and int(m["game_mode"]) == int(game_mode):
                    key = k
                    mode = m
                    break
        if not mode:
            return None
        allowed_fields = {
            "name", "mode_title", "tips", "enable", "is_new", "start_time",
            "end_time", "player_count_limit", "level_visual_style", "difficulty",
            "weekday", "sort_id", "limited_rank", "limited_count", "pve_force_mm",
        }
        for k, v in kwargs.items():
            if k in allowed_fields:
                mode[k] = v
        return dict(mode)


def reset_game_modes() -> None:
    """Reset all game modes back to their authentic initial state."""
    with _MODE_REGISTRY_LOCK:
        _GAME_MODES_REGISTRY.clear()
        for mode in AUTHENTIC_139_GAME_MODES:
            key = str(mode.get("key") or f"{mode['map_id']}_{mode['game_mode']}_{mode['match_mode']}")
            _GAME_MODES_REGISTRY[key] = dict(mode)


def is_mode_enabled(map_id: int, game_mode: int, match_mode: int = 1) -> bool:
    """Check if a specific map/mode combination is enabled."""
    _ensure_seeded_game_modes()
    key = f"{int(map_id)}_{int(game_mode)}_{int(match_mode)}"
    with _MODE_REGISTRY_LOCK:
        mode = _GAME_MODES_REGISTRY.get(key)
        if mode:
            return bool(mode.get("enable", True))
        for m in _GAME_MODES_REGISTRY.values():
            if int(m["map_id"]) == int(map_id) and int(m["game_mode"]) == int(game_mode):
                return bool(m.get("enable", True))
        return True


def _default_game_servers() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    nodes = [
        {
            "region": "IND",
            "node_name": "IND-Local-01",
            "server_ip": _GAME_SERVER_ADDR,
            "is_default": True,
            "warn_capacity": 1000,
        },
        {
            "region": "SG",
            "node_name": "SG-Node-01",
            "server_ip": _GAME_SERVER_ADDR,
            "is_default": False,
            "warn_capacity": 1000,
        },
    ]
    pings = [
        {
            "region": "IND",
            "ip": _GAME_SERVER_ADDR,
            "start_time": "2020-01-01 00:00:00",
            "end_time": "2099-12-31 23:59:59",
            "ping_random": 1.0,
        },
        {
            "region": "SG",
            "ip": _GAME_SERVER_ADDR,
            "start_time": "2020-01-01 00:00:00",
            "end_time": "2099-12-31 23:59:59",
            "ping_random": 1.0,
        },
    ]
    return nodes, pings


# ---------------------------------------------------------------------------
# Core Room Operations (shared by HTTP & TCP)
# ---------------------------------------------------------------------------

def _op_get_room_list(room_id: int = 0, room_type: int = ERoomType.NONE) -> List[Dict[str, Any]]:
    _ensure_seeded_rooms()
    full_rooms = [_build_full_room_dict(r) for r in state.list_rooms()]
    if room_id > 0:
        full_rooms = [r for r in full_rooms if int(r["room_id"]) == int(room_id)]
    if room_type not in (ERoomType.NONE, 0):
        full_rooms = [r for r in full_rooms if int(r["room_type"]) == int(room_type)]
    return full_rooms


def _op_create_room(account_id: int, req: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    _ensure_seeded_rooms()
    prof = _resolve_profile(account_id)
    room_name = str(req.get("room_name") or f"{prof['nickname']}'s Room")
    password = str(req.get("code", req.get("password", "")))
    map_id = int(req.get("map_id", 1) or 1)
    game_mode = int(req.get("game_mode", GameMode.BATTLE_ROYALE) or GameMode.BATTLE_ROYALE)
    max_players = int(req.get("max_member_num", req.get("max_players", 48)) or 48)
    max_players = max(2, min(max_players, 50))

    created = state.create_room(
        owner_id=account_id,
        name=room_name,
        map_id=map_id,
        game_mode=game_mode,
        max_players=max_players,
        password=password,
    )
    rid = int(created["room_id"])
    with _META_LOCK:
        meta = _default_room_meta(created)
        meta["group_mode"] = int(req.get("group_mode", GroupMode.QUAD))
        meta["max_spectator_num"] = int(req.get("max_spectator_num", 16) or 16)
        meta["enable_death_spectate"] = bool(req.get("enable_death_spectate", False))
        meta["room_type"] = int(req.get("room_type", ERoomType.CASUAL) or ERoomType.CASUAL)
        meta["enable_group_icon"] = bool(req.get("enable_group_icon", False))
        meta["level_visual_style"] = int(req.get("level_visual_style", LevelVisualStyle.NORMAL))
        meta["room_setting"] = int(req.get("room_setting", 0))
        meta["banner"] = int(prof.get("banner_id", 901000001))
        _ROOM_META[rid] = meta

    return ERoomErrCode.SUSS, _build_full_room_dict(created)


def _op_join_room(
    account_id: int,
    room_id: int,
    password: str = "",
    group_id: int = 0,
    players: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[int, Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    _ensure_seeded_rooms()
    if room_id <= 0:
        return ERoomErrCode.NOROOM, None, []

    join_ids: List[int] = []
    if players:
        for p in players:
            aid = int(p.get("account_id", 0))
            if aid > 0:
                join_ids.append(aid)
    if not join_ids:
        join_ids = [account_id]

    res: Dict[str, Any] = {"ok": False, "reason": "room_not_found", "room": None}
    for pid in join_ids:
        res = state.join_room(room_id=room_id, player_id=pid, password=password)
        if not res.get("ok"):
            reason = res.get("reason")
            if reason == "wrong_password":
                return ERoomErrCode.INVALIDCODE, None, []
            if reason == "room_full":
                return ERoomErrCode.REACHMAXMEMBERS, None, []
            return ERoomErrCode.NOROOM, None, []

    room = res.get("room")
    if not room:
        return ERoomErrCode.NOROOM, None, []

    meta = _get_or_init_meta(room)
    with _META_LOCK:
        for p in players or []:
            pid = int(p.get("account_id", 0))
            if pid > 0:
                meta["emulator_scores"][pid] = int(p.get("emulator_score", 0))
        for pid in join_ids:
            if pid in meta["spectators"]:
                meta["spectators"].remove(pid)
            meta["ready_map"].setdefault(pid, False)
            if group_id > 0:
                existing_in_grp = sum(
                    1 for s_gid, _ in meta["seat_map"].values() if s_gid == group_id
                )
                meta["seat_map"][pid] = (group_id, existing_in_grp + 1)

    full = _build_full_room_dict(room)
    joined_entries = [
        _build_player_entry(pid, meta, role=ERoomPlayerRole.MEMBER) for pid in join_ids
    ]
    return ERoomErrCode.SUSS, full, joined_entries


def _op_spectate_room(
    account_id: int,
    room_id: int,
    password: str = "",
) -> Tuple[int, Optional[Dict[str, Any]]]:
    room = _find_room(room_id=room_id)
    if not room:
        return ERoomErrCode.NOROOM, None
    if room.get("has_password") and room.get("password", "") != password:
        return ERoomErrCode.INVALIDCODE, None

    meta = _get_or_init_meta(room)
    with _META_LOCK:
        with state._lock:
            raw_room = state._rooms.get(int(room["room_id"]))
            if raw_room and account_id in raw_room["members"]:
                raw_room["members"].remove(account_id)
                meta["seat_map"].pop(account_id, None)
        if account_id not in meta["spectators"]:
            if len(meta["spectators"]) >= int(meta["max_spectator_num"]):
                return ERoomErrCode.REACHMAXSPECTATORS, None
            meta["spectators"].append(account_id)
    updated = _find_room(room_id=int(room["room_id"])) or room
    return ERoomErrCode.SUSS, _build_full_room_dict(updated)


def _op_leave_room(
    account_id: int,
    room_id: int = 0,
) -> Tuple[int, bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Returns (err_code, dismissed, leaver_entry, updated_room_or_none)."""
    room = _find_room(room_id=room_id, account_id=account_id)
    if not room:
        return ERoomErrCode.NOTINROOM, False, None, None

    rid = int(room["room_id"])
    meta = _get_or_init_meta(room)
    was_spectator = account_id in meta.get("spectators", [])
    leaver_entry = _build_player_entry(
        account_id,
        meta,
        role=ERoomPlayerRole.SPECTATOR if was_spectator else ERoomPlayerRole.MEMBER,
    )

    dismissed = False
    remaining_room: Optional[Dict[str, Any]] = None
    with _META_LOCK:
        with state._lock:
            raw = state._rooms.get(rid)
            if not raw:
                return ERoomErrCode.NOROOM, False, None, None
            if account_id in raw["members"]:
                raw["members"].remove(account_id)
            if account_id in meta["spectators"]:
                meta["spectators"].remove(account_id)
            meta["seat_map"].pop(account_id, None)
            meta["ready_map"].pop(account_id, None)

            if not raw["members"]:
                state._rooms.pop(rid, None)
                _ROOM_META.pop(rid, None)
                dismissed = True
            else:
                if int(raw["owner_id"]) == int(account_id):
                    new_owner = int(raw["members"][0])
                    raw["owner_id"] = new_owner
                    raw["owner_nick"] = str(_resolve_profile(new_owner).get("nickname", raw["owner_nick"]))
                    meta["ready_map"][new_owner] = True
                remaining_room = dict(raw)
                remaining_room["members"] = list(raw["members"])

    if dismissed:
        return ERoomErrCode.SUSS, True, leaver_entry, {"room_id": rid}
    assert remaining_room is not None
    return ERoomErrCode.SUSS, False, leaver_entry, _build_full_room_dict(remaining_room)


def _op_kick_player(
    account_id: int,
    kick_id: int,
    room_id: int = 0,
) -> Tuple[int, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    room = _find_room(room_id=room_id, account_id=account_id)
    if not room:
        return ERoomErrCode.NOTINROOM, None, None
    if int(room["owner_id"]) != int(account_id):
        return ERoomErrCode.NOTOWNER, None, None
    if int(kick_id) == int(account_id) or kick_id <= 0:
        return ERoomErrCode.CANNOTKICK, None, None

    rid = int(room["room_id"])
    meta = _get_or_init_meta(room)
    was_spec = kick_id in meta.get("spectators", [])
    if kick_id not in room.get("members", []) and not was_spec:
        return ERoomErrCode.NOTINROOM, None, None

    kicked_entry = _build_player_entry(
        kick_id,
        meta,
        role=ERoomPlayerRole.SPECTATOR if was_spec else ERoomPlayerRole.MEMBER,
    )
    with _META_LOCK:
        with state._lock:
            raw = state._rooms.get(rid)
            if not raw:
                return ERoomErrCode.NOROOM, None, None
            if kick_id in raw["members"]:
                raw["members"].remove(kick_id)
            if kick_id in meta["spectators"]:
                meta["spectators"].remove(kick_id)
            meta["seat_map"].pop(kick_id, None)
            meta["ready_map"].pop(kick_id, None)
            updated = dict(raw)
            updated["members"] = list(raw["members"])

    return ERoomErrCode.SUSS, kicked_entry, _build_full_room_dict(updated)


def _op_change_room(account_id: int, req: Dict[str, Any]) -> Tuple[int, Optional[Dict[str, Any]]]:
    room = _find_room(room_id=int(req.get("room_id", 0)), account_id=account_id)
    if not room:
        return ERoomErrCode.NOROOM, None
    if int(room["owner_id"]) != int(account_id):
        return ERoomErrCode.NOTOWNER, None

    rid = int(room["room_id"])
    meta = _get_or_init_meta(room)
    with _META_LOCK:
        with state._lock:
            raw = state._rooms.get(rid)
            if not raw:
                return ERoomErrCode.NOROOM, None
            if req.get("has_room_name") and req.get("room_name"):
                raw["name"] = str(req["room_name"])
            if req.get("has_code"):
                pw = str(req.get("code", ""))
                raw["password"] = pw
                raw["has_password"] = bool(pw)
            if req.get("has_map_id") and int(req["map_id"]) > 0:
                raw["map_id"] = int(req["map_id"])
            if req.get("has_game_mode") and int(req["game_mode"]) > 0:
                raw["game_mode"] = int(req["game_mode"])
            if req.get("has_max_member_num") and int(req["max_member_num"]) >= 2:
                raw["max_players"] = min(50, int(req["max_member_num"]))
            updated = dict(raw)
            updated["members"] = list(raw["members"])

        if req.get("has_max_spectator_num"):
            meta["max_spectator_num"] = int(req["max_spectator_num"])
        if req.get("has_enable_death_spectate"):
            meta["enable_death_spectate"] = bool(req["enable_death_spectate"])
        if req.get("has_enable_group_icon"):
            meta["enable_group_icon"] = bool(req["enable_group_icon"])
        if req.get("has_level_visual_style"):
            meta["level_visual_style"] = int(req["level_visual_style"])
        if req.get("has_room_setting"):
            meta["room_setting"] = int(req["room_setting"])

    return ERoomErrCode.SUSS, _build_full_room_dict(updated)


def _op_switch_seat(account_id: int, req: Dict[str, Any]) -> Tuple[int, Optional[Dict[str, Any]]]:
    room = _find_room(room_id=int(req.get("room_id", 0)), account_id=account_id)
    if not room:
        return ERoomErrCode.NOROOM, None

    rid = int(room["room_id"])
    target_id = int(req.get("account_id") or account_id)
    to_role = int(req.get("to_role", ERoomPlayerRole.MEMBER))
    to_group = max(1, int(req.get("to_room_pos", 1) or 1))
    to_pos = max(1, int(req.get("to_group_pos", 1) or 1))
    meta = _get_or_init_meta(room)

    with _META_LOCK:
        with state._lock:
            raw = state._rooms.get(rid)
            if not raw:
                return ERoomErrCode.NOROOM, None
            if to_role == ERoomPlayerRole.SPECTATOR:
                if target_id in raw["members"]:
                    raw["members"].remove(target_id)
                if target_id not in meta["spectators"]:
                    if len(meta["spectators"]) >= int(meta["max_spectator_num"]):
                        return ERoomErrCode.REACHMAXSPECTATORS, None
                    meta["spectators"].append(target_id)
                meta["seat_map"].pop(target_id, None)
            else:
                # Prevent colliding onto an occupied group/slot
                for other_id, seat in meta["seat_map"].items():
                    if other_id != target_id and seat == (to_group, to_pos):
                        return ERoomErrCode.SEATOCCUPIED, None
                if target_id in meta["spectators"]:
                    meta["spectators"].remove(target_id)
                if target_id not in raw["members"]:
                    if len(raw["members"]) >= int(raw["max_players"]):
                        return ERoomErrCode.REACHMAXMEMBERS, None
                    raw["members"].append(target_id)
                meta["seat_map"][target_id] = (to_group, to_pos)

            updated = dict(raw)
            updated["members"] = list(raw["members"])

    return ERoomErrCode.SUSS, _build_full_room_dict(updated)


def _op_set_ready(account_id: int, ready: bool) -> Tuple[int, Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    room = _find_room(account_id=account_id)
    if not room:
        return ERoomErrCode.NOTINROOM, None, []
    meta = _get_or_init_meta(room)
    with _META_LOCK:
        meta["ready_map"][account_id] = bool(ready)
        entry = _build_player_entry(account_id, meta, role=ERoomPlayerRole.MEMBER)
    return ERoomErrCode.SUSS, _build_full_room_dict(room), [entry]


def _op_start_room(account_id: int, room_id: int = 0) -> Tuple[int, Optional[bytes], Optional[Dict[str, Any]]]:
    room = _find_room(room_id=room_id, account_id=account_id)
    if not room:
        return ERoomErrCode.NOROOM, None, None
    if int(room["owner_id"]) != int(account_id):
        return ERoomErrCode.NOTOWNER, None, None

    meta = _get_or_init_meta(room)
    with _META_LOCK:
        meta["state"] = ERoomState.INGAME
        meta["match_times"] = int(meta["match_times"]) + 1
        lvl_style = int(meta["level_visual_style"])

    suss_bytes = _build_matchmaking_suss(
        map_id=int(room.get("map_id", 1)),
        game_mode=int(room.get("game_mode", GameMode.BATTLE_ROYALE)),
        match_mode=MatchMode.ROOM,
        difficulty=0,
        level_visual_style=lvl_style,
    )
    return ERoomErrCode.SUSS, suss_bytes, _build_full_room_dict(room)


def _op_drop_room_match(account_id: int, room_id: int = 0) -> Tuple[int, Optional[Dict[str, Any]]]:
    room = _find_room(room_id=room_id, account_id=account_id)
    if not room:
        return ERoomErrCode.NOROOM, None
    meta = _get_or_init_meta(room)
    with _META_LOCK:
        meta["state"] = ERoomState.IDLE
    return ERoomErrCode.SUSS, _build_full_room_dict(room)


# ---------------------------------------------------------------------------
# Matchmaking Operations (shared by HTTP & TCP)
# ---------------------------------------------------------------------------

def _decode_any_matchmaking_req(raw_body: bytes) -> Dict[str, Any]:
    if not raw_body:
        return {"map_ids": [1], "game_mode": GameMode.BATTLE_ROYALE, "match_mode": MatchMode.CASUAL, "difficulty": 0}
    f = decode_proto(raw_body)
    # MatchmakingGroupStartReq carries group_mode (tag 3) or players (tag 4 submessage) or group_mode/game_mode tag 6
    if 3 in f or 6 in f and isinstance(f[6][0], int) or 12 in f:
        grp = decode_matchmaking_group_start_req(raw_body)
        return {
            "map_ids": grp["map_ids"] or [1],
            "game_mode": grp["game_mode"],
            "match_mode": grp["match_mode"],
            "difficulty": grp["difficulty"],
            "group_id": grp["group_id"],
        }
    solo = decode_matchmaking_start_req(raw_body)
    return {
        "map_ids": solo["map_ids"] or [1],
        "game_mode": solo["game_mode"],
        "match_mode": solo["match_mode"],
        "difficulty": solo["difficulty"],
        "group_id": 0,
    }


def _op_start_matchmaking(account_id: int, raw_body: bytes) -> Tuple[int, bytes]:
    req = _decode_any_matchmaking_req(raw_body)
    map_id = int((req.get("map_ids") or [1])[0])
    game_mode = int(req.get("game_mode", GameMode.BATTLE_ROYALE))
    match_mode = int(req.get("match_mode", MatchMode.CASUAL))
    difficulty = int(req.get("difficulty", 1))
    group_id = int(req.get("group_id", 0)) or None

    if not is_mode_enabled(map_id, game_mode, match_mode):
        return EMatchmakingErrCode.MAPNOTOPEN, b""

    team = state.start_matchmaking(
        team_id=group_id,
        account_id=account_id,
        game_mode=game_mode,
        map_id=map_id,
    )
    # Ensure match_mode and difficulty are persisted for TCP notification
    if team and "team_id" in team:
        raw_t = state._teams.get(team["team_id"])
        if raw_t is not None:
            raw_t["match_mode"] = match_mode
            raw_t["difficulty"] = difficulty
    suss = _build_matchmaking_suss(
        map_id=int(team.get("map_id", map_id)),
        game_mode=int(team.get("game_mode", game_mode)),
        match_mode=match_mode,
        difficulty=difficulty,
    )
    return EMatchmakingErrCode.SUSS, suss


def _op_cancel_matchmaking(account_id: int, raw_body: bytes) -> Tuple[int, bytes]:
    team_id: Optional[int] = None
    if raw_body:
        f = decode_proto(raw_body)
        gid = get_varint(f, 1, 0)
        if gid > 0:
            team_id = gid
    state.cancel_matchmaking(team_id=team_id, account_id=account_id)
    return EMatchmakingErrCode.SUSS, b""


# ---------------------------------------------------------------------------
# TCP Dispatchers (ROOM=14, MATCHMAKING=3)
# ---------------------------------------------------------------------------

def _dispatch_room_sub_cmd(
    cmd: int,
    payload: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> Tuple[int, int, bytes]:
    """
    Dispatch a `tcp.ERoom.Proto` command (`EProtocol.Proto.ROOM = 14`).
    Returns `(reply_cmd, ret_code, reply_bytes)` matching `tcp_server.dispatch_tcp_packet`.
    """
    if cmd == ERoomProto.ROOMLIST:
        req = decode_room_list_req(payload) if payload else {"room_id": 0, "room_type": ERoomType.NONE}
        rooms = _op_get_room_list(req["room_id"], req["room_type"])
        return ERoomProto.ROOMLIST, ERoomErrCode.SUSS, encode_tcp_room_list_res(rooms)

    if cmd in (ERoomProto.CREATE, ERoomProto.REAL_CREATE):
        req = decode_room_create_req(payload) if payload else {}
        err, room = _op_create_room(account_id, req)
        return cmd, err, encode_room_info(room)

    if cmd == ERoomProto.JOIN:
        req = decode_room_join_req(payload) if payload else {"room_id": 0, "code": ""}
        err, room, _ = _op_join_room(
            account_id=account_id,
            room_id=int(req.get("room_id", 0)),
            password=str(req.get("code", "")),
            group_id=int(req.get("group_id", 0)),
            players=req.get("players"),
        )
        if err != ERoomErrCode.SUSS or not room:
            return ERoomProto.JOIN, err, b""
        return ERoomProto.JOIN, ERoomErrCode.SUSS, encode_room_info(room)

    if cmd == ERoomProto.SPECTATE:
        req = decode_room_spectate_req(payload) if payload else {"room_id": 0, "code": ""}
        err, room = _op_spectate_room(account_id, int(req.get("room_id", 0)), str(req.get("code", "")))
        return ERoomProto.SPECTATE, err, encode_room_info(room) if room else b""

    if cmd == ERoomProto.LEAVE:
        req = decode_room_id_req(payload) if payload else {"room_id": 0}
        err, dismissed, leaver, room = _op_leave_room(account_id, int(req.get("room_id", 0)))
        if err != ERoomErrCode.SUSS or not room:
            return ERoomProto.LEAVE, err, b""
        if dismissed:
            return ERoomProto.DISMISS_NTF, ERoomErrCode.SUSS, encode_room_dismiss_ntf(
                account_id, int(room["room_id"]), ERoomDismissReason.NORMAL
            )
        assert leaver is not None
        return ERoomProto.LEAVE_NTF, ERoomErrCode.SUSS, encode_room_leave_ntf(leaver, room)

    if cmd == ERoomProto.KICK:
        req = decode_room_kick_req(payload) if payload else {"kick_account_id": 0}
        err, kicked, room = _op_kick_player(account_id, int(req.get("kick_account_id", 0)))
        if err != ERoomErrCode.SUSS or not kicked or not room:
            return ERoomProto.KICK, err, b""
        return ERoomProto.KICK_NTF, ERoomErrCode.SUSS, encode_room_kick_ntf(kicked, room)

    if cmd == ERoomProto.ROOMINFO:
        req = decode_room_id_req(payload) if payload else {"room_id": 0}
        room = _find_room(room_id=int(req.get("room_id", 0)), account_id=account_id)
        if not room:
            return ERoomProto.ROOMINFO, ERoomErrCode.NOROOM, b""
        return ERoomProto.ROOMINFO, ERoomErrCode.SUSS, encode_room_info(_build_full_room_dict(room))

    if cmd == ERoomProto.CHANGE:
        req = decode_room_change_req(payload) if payload else {}
        err, room = _op_change_room(account_id, req)
        return ERoomProto.CHANGE_NTF, err, encode_room_info(room) if room else b""

    if cmd == ERoomProto.SWITCHSEAT:
        req = decode_room_switch_seat_req(payload) if payload else {}
        err, room = _op_switch_seat(account_id, req)
        return ERoomProto.SWITCHSEAT_NTF, err, encode_room_info(room) if room else b""

    if cmd == ERoomProto.SETREADY:
        req = decode_room_set_ready_req(payload) if payload else {"ready": True}
        err, room, entries = _op_set_ready(account_id, bool(req.get("ready", True)))
        if err != ERoomErrCode.SUSS or not room:
            return ERoomProto.SETREADY, err, b""
        return ERoomProto.SETREADY_NTF, ERoomErrCode.SUSS, encode_room_set_ready_ntf(int(room["room_id"]), entries)

    if cmd == ERoomProto.INVITE:
        req = decode_room_invite_req(payload) if payload else {"invitee_id": 0}
        invitee_id = int(req.get("invitee_id", 0))
        if invitee_id == account_id:
            return ERoomProto.INVITE, ERoomErrCode.CANNOTINVITESELF, b""
        room = _find_room(account_id=account_id)
        if not room:
            return ERoomProto.INVITE, ERoomErrCode.NOTINROOM, b""
        meta = _get_or_init_meta(room)
        inviter = _build_player_entry(account_id, meta, role=ERoomPlayerRole.MEMBER)
        ntf = encode_room_invite_ntf(
            room_id=int(room["room_id"]),
            inviter=inviter,
            map_id=int(room.get("map_id", 1)),
            game_mode=int(room.get("game_mode", GameMode.BATTLE_ROYALE)),
            group_mode=int(meta["group_mode"]),
            owner_id=int(room["owner_id"]),
        )
        return ERoomProto.INVITE_NTF, ERoomErrCode.SUSS, ntf

    if cmd == ERoomProto.START:
        req = decode_room_id_req(payload) if payload else {"room_id": 0}
        err, suss, _ = _op_start_room(account_id, int(req.get("room_id", 0)))
        if err != ERoomErrCode.SUSS or not suss:
            return ERoomProto.START, err, b""
        return ERoomProto.MATCHMAKINGSUSS_NTF, ERoomErrCode.SUSS, suss

    if cmd == ERoomProto.DROPOMATCH:
        req = decode_room_id_req(payload) if payload else {"room_id": 0}
        err, room = _op_drop_room_match(account_id, int(req.get("room_id", 0)))
        if err != ERoomErrCode.SUSS or not room:
            return ERoomProto.DROPOMATCH, err, b""
        return ERoomProto.ROOMSTATE_NTF, ERoomErrCode.SUSS, encode_room_state_ntf(
            int(room["room_id"]), int(room["state"])
        )

    return cmd, ERoomErrCode.SUSS, b""


def handle_room_tcp_command(
    protocol: int,
    sub_cmd: int,
    data: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> Tuple[int, int, bytes]:
    """
    TCP entrypoint compatible with `tcp_server.dispatch_tcp_packet`.
    Returns `(response_cmd, ret_code, response_payload_bytes)`.
    """
    if protocol == EProtocolProto.MATCHMAKING:
        return handle_matchmaking_tcp_command(protocol, sub_cmd, data, account_id=account_id)
    if protocol == EProtocolProto.GROUP and sub_cmd == 19:  # EGroup.Proto_JOINROOM
        req = decode_group_join_room_req(data)
        err, room, _ = _op_join_room(
            account_id=account_id,
            room_id=int(req["room_id"]),
            password=str(req["code"]),
            group_id=int(req["group_id"]),
        )
        return ERoomProto.JOIN, err, encode_room_info(room) if (err == ERoomErrCode.SUSS and room) else b""
    return _dispatch_room_sub_cmd(sub_cmd, data, account_id=account_id)


handle_tcp_room_command = handle_room_tcp_command


def handle_matchmaking_tcp_command(
    protocol: int,
    sub_cmd: int,
    data: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> Tuple[int, int, bytes]:
    """
    Dispatch a `tcp.EMatchmaking.Proto` command (`EProtocol.Proto.MATCHMAKING = 3`).
    Returns `(response_cmd, ret_code, response_payload_bytes)`.
    """
    del protocol
    if sub_cmd in (EMatchmakingProto.START, EMatchmakingProto.GROUPSTART):
        err, suss = _op_start_matchmaking(account_id, data)
        if err == EMatchmakingErrCode.SUSS and suss:
            return EMatchmakingProto.MATCHMAKINGSUSS_NTF, err, suss
        return sub_cmd, err, b""

    if sub_cmd in (EMatchmakingProto.CANCEL, EMatchmakingProto.GROUPCANCEL, EMatchmakingProto.DROPMATCH):
        err, _ = _op_cancel_matchmaking(account_id, data)
        return sub_cmd, err, b""

    if sub_cmd == EMatchmakingProto.GAMEOPENINGINFO:
        req = decode_game_opening_info_req(data) if data else {"region": "IND", "language": "en"}
        lang = req.get("language") or "en"
        res = encode_game_opening_info_res(
            descs=get_game_opening_descriptors(only_enabled=False),
            timezone_offset_secs=0,
            mode_names=get_game_mode_names(lang),
        )
        return EMatchmakingProto.GAMEOPENINGINFO, EMatchmakingErrCode.SUSS, res

    return sub_cmd, EMatchmakingErrCode.SUSS, b""


def handle_tcp_proto_req(
    protocol: int,
    raw_proto_req: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bytes:
    """
    Unwrap `tcp.ProtoReq` (`1: cmd, 2: data`) for ROOM (14) / MATCHMAKING (3) /
    GROUP JOINROOM (5, cmd=19) and return encoded `proto.MessageNotify`.
    """
    proto_req = decode_proto_req(raw_proto_req) if raw_proto_req else {"cmd": 0, "data": b""}
    cmd = int(proto_req["cmd"])
    data = proto_req["data"]

    if protocol in (EProtocolProto.ROOM, EProtocolProto.MATCHMAKING) or (
        protocol == EProtocolProto.GROUP and cmd == 19
    ):
        reply_cmd, ret, reply_bytes = handle_room_tcp_command(protocol, cmd, data, account_id=account_id)
        out_proto = EProtocolProto.ROOM if (protocol == EProtocolProto.GROUP and cmd == 19) else protocol
        return encode_message_notify(account_id, out_proto, ret, reply_cmd, reply_bytes)

    return encode_message_notify(account_id, protocol, 0, cmd, b"")


def handle_tcp_frame(raw_frame: bytes, account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
    """
    Process a complete C2S TCP frame (`[1B cmd][1B flag][4B BE len][payload]`)
    and return the exact S2C wire response (`b"\\x02"` for init, or 5-byte frame).
    """
    cmd, _flag, payload = decode_tcp_packet_c2s(raw_frame)
    if cmd == EProtocolProto.INIT:
        return TCP_HANDSHAKE_ACK
    if cmd == EProtocolProto.HEARTBEAT:
        return encode_tcp_packet_s2c(EProtocolProto.HEARTBEAT, b"")
    notify = handle_tcp_proto_req(cmd, payload, account_id=account_id)
    return encode_tcp_packet_s2c(cmd, notify)


# ---------------------------------------------------------------------------
# HTTP Handlers
# ---------------------------------------------------------------------------

def _http_get_room_list(handler: Any, raw_body: bytes, _account_id: int) -> None:
    req = decode_room_list_req(raw_body) if raw_body else {"room_id": 0, "room_type": ERoomType.NONE}
    rooms = _op_get_room_list(req["room_id"], req["room_type"])
    handler.send_proto("GetAllRoomsRes", encode_get_all_rooms_res(rooms))


def _http_create_room(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_create_req(raw_body) if raw_body else {}
    _, room = _op_create_room(account_id, req)
    handler.send_proto("RoomInfo (Create)", encode_room_info(room))


def _http_join_room(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_join_req(raw_body) if raw_body else {"room_id": 0, "code": ""}
    err, room, _ = _op_join_room(
        account_id=account_id,
        room_id=int(req.get("room_id", 0)),
        password=str(req.get("code", "")),
        group_id=int(req.get("group_id", 0)),
        players=req.get("players"),
    )
    if err != ERoomErrCode.SUSS or not room:
        handler.send_proto("RoomJoinErr", b"")
        return
    handler.send_proto("RoomInfo (Join)", encode_room_info(room))


def _http_spectate_room(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_spectate_req(raw_body) if raw_body else {"room_id": 0, "code": ""}
    err, room = _op_spectate_room(account_id, int(req.get("room_id", 0)), str(req.get("code", "")))
    if err != ERoomErrCode.SUSS or not room:
        handler.send_proto("RoomSpectateErr", b"")
        return
    handler.send_proto("RoomInfo (Spectate)", encode_room_info(room))


def _http_leave_room(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_id_req(raw_body) if raw_body else {"room_id": 0}
    err, dismissed, leaver, room = _op_leave_room(account_id, int(req.get("room_id", 0)))
    if err != ERoomErrCode.SUSS or not room:
        handler.send_proto("RoomLeaveEmpty", b"")
        return
    if dismissed:
        handler.send_proto(
            "RoomDismissNtf",
            encode_room_dismiss_ntf(account_id, int(room["room_id"]), ERoomDismissReason.NORMAL),
        )
        return
    assert leaver is not None
    handler.send_proto("RoomLeaveNtf", encode_room_leave_ntf(leaver, room))


def _http_kick_room_player(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_kick_req(raw_body) if raw_body else {"kick_account_id": 0}
    err, kicked, room = _op_kick_player(account_id, int(req.get("kick_account_id", 0)))
    if err != ERoomErrCode.SUSS or not kicked or not room:
        handler.send_proto("RoomKickEmpty", b"")
        return
    handler.send_proto("RoomKickNtf", encode_room_kick_ntf(kicked, room))


def _http_get_room_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_id_req(raw_body) if raw_body else {"room_id": 0}
    room = _find_room(room_id=int(req.get("room_id", 0)), account_id=account_id)
    if not room:
        handler.send_proto("RoomInfoEmpty", b"")
        return
    handler.send_proto("RoomInfo", encode_room_info(_build_full_room_dict(room)))


def _http_change_room(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_change_req(raw_body) if raw_body else {}
    err, room = _op_change_room(account_id, req)
    if err != ERoomErrCode.SUSS or not room:
        handler.send_proto("RoomChangeEmpty", b"")
        return
    handler.send_proto("RoomInfo (Change)", encode_room_info(room))


def _http_set_room_ready(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_set_ready_req(raw_body) if raw_body else {"ready": True}
    err, room, entries = _op_set_ready(account_id, bool(req.get("ready", True)))
    if err != ERoomErrCode.SUSS or not room:
        handler.send_proto("RoomSetReadyEmpty", b"")
        return
    handler.send_proto("RoomSetReadyNtf", encode_room_set_ready_ntf(int(room["room_id"]), entries))


def _http_switch_room_seat(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_switch_seat_req(raw_body) if raw_body else {}
    err, room = _op_switch_seat(account_id, req)
    if err != ERoomErrCode.SUSS or not room:
        handler.send_proto("RoomSwitchSeatEmpty", b"")
        return
    handler.send_proto("RoomInfo (SwitchSeat)", encode_room_info(room))


def _http_invite_room(handler: Any, raw_body: bytes, account_id: int) -> None:
    _ = decode_room_invite_req(raw_body) if raw_body else {"invitee_id": 0}
    room = _find_room(account_id=account_id)
    if not room:
        handler.send_proto("RoomInviteEmpty", b"")
        return
    meta = _get_or_init_meta(room)
    inviter = _build_player_entry(account_id, meta, role=ERoomPlayerRole.MEMBER)
    payload = encode_room_invite_ntf(
        room_id=int(room["room_id"]),
        inviter=inviter,
        map_id=int(room.get("map_id", 1)),
        game_mode=int(room.get("game_mode", GameMode.BATTLE_ROYALE)),
        group_mode=int(meta["group_mode"]),
        owner_id=int(room["owner_id"]),
    )
    handler.send_proto("RoomInviteNtf", payload)


def _http_start_room(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_id_req(raw_body) if raw_body else {"room_id": 0}
    err, suss, _ = _op_start_room(account_id, int(req.get("room_id", 0)))
    if err != ERoomErrCode.SUSS or not suss:
        handler.send_proto("RoomStartEmpty", b"")
        return
    handler.send_proto("MatchmakingSussNtf (Room)", suss)


def _http_drop_room_match(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_room_id_req(raw_body) if raw_body else {"room_id": 0}
    err, room = _op_drop_room_match(account_id, int(req.get("room_id", 0)))
    if err != ERoomErrCode.SUSS or not room:
        handler.send_proto("RoomDropMatchEmpty", b"")
        return
    handler.send_proto(
        "RoomStateNtf",
        encode_room_state_ntf(int(room["room_id"]), int(room["state"])),
    )


def _http_start_matchmaking(handler: Any, raw_body: bytes, account_id: int) -> None:
    _, suss = _op_start_matchmaking(account_id, raw_body)
    handler.send_proto("MatchmakingSussNtf", suss)


def _http_cancel_matchmaking(handler: Any, raw_body: bytes, account_id: int) -> None:
    _op_cancel_matchmaking(account_id, raw_body)
    handler.send_proto("Empty (CancelMatchMaking)", b"")


def _http_get_matchmaking_status(handler: Any, _raw_body: bytes, account_id: int) -> None:
    team = state.get_team(account_id=account_id)
    if team and team.get("matchmaking"):
        suss = _build_matchmaking_suss(
            map_id=int(team.get("map_id", 1)),
            game_mode=int(team.get("game_mode", GameMode.BATTLE_ROYALE)),
            match_mode=MatchMode.CASUAL,
        )
        handler.send_proto("MatchmakingSussNtf (Status)", suss)
        return
    handler.send_proto("Empty (MatchmakingStatus)", b"")


def _http_get_game_server_list(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    nodes, pings = _default_game_servers()
    handler.send_proto("GameServerListRes", encode_game_server_list_res(nodes, pings))


def _http_get_game_opening_info(handler: Any, raw_body: bytes, _account_id: int) -> None:
    req = decode_game_opening_info_req(raw_body) if raw_body else {"region": "IND", "language": "en"}
    lang = req.get("language") or "en"
    res = encode_game_opening_info_res(
        descs=get_game_opening_descriptors(only_enabled=False),
        timezone_offset_secs=0,
        mode_names=get_game_mode_names(lang),
    )
    handler.send_proto("GameOpeningInfoRes", res)


def _http_admin_list_modes(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    handler.send_json({"ok": True, "modes": list_modes_admin()})


def _http_admin_toggle_mode(handler: Any, raw_body: bytes, _account_id: int) -> None:
    try:
        data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        data = {}
    map_id = int(data.get("map_id", 1))
    game_mode = int(data.get("game_mode", 1))
    match_mode = int(data.get("match_mode", 1))
    enable = data.get("enable")
    if enable is not None:
        enable = bool(enable)
    toggled = toggle_game_mode(map_id, game_mode, match_mode, enable=enable)
    handler.send_json({"ok": toggled is not None, "mode": toggled, "modes": list_modes_admin()})


def _http_admin_unlock_all_modes(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    cnt = unlock_all_modes()
    handler.send_json({"ok": True, "unlocked_count": cnt, "modes": list_modes_admin()})


def _http_admin_lock_optional_modes(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    cnt = lock_optional_modes()
    handler.send_json({"ok": True, "locked_count": cnt, "modes": list_modes_admin()})


def _http_admin_update_mode(handler: Any, raw_body: bytes, _account_id: int) -> None:
    try:
        data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        data = {}
    map_id = int(data.get("map_id", 1))
    game_mode = int(data.get("game_mode", 1))
    match_mode = int(data.get("match_mode", 1))
    kwargs = {k: v for k, v in data.items() if k not in ("map_id", "game_mode", "match_mode", "account_id")}
    updated = update_game_mode(map_id, game_mode, match_mode, **kwargs)
    handler.send_json({"ok": updated is not None, "mode": updated, "modes": list_modes_admin()})


def _http_admin_reset_modes(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    reset_game_modes()
    handler.send_json({"ok": True, "modes": list_modes_admin()})


def _http_room_packet(handler: Any, raw_body: bytes, account_id: int) -> None:
    notify = handle_tcp_proto_req(EProtocolProto.ROOM, raw_body, account_id=account_id)
    handler.send_proto("MessageNotify (Room)", notify)


def _http_matchmaking_packet(handler: Any, raw_body: bytes, account_id: int) -> None:
    notify = handle_tcp_proto_req(EProtocolProto.MATCHMAKING, raw_body, account_id=account_id)
    handler.send_proto("MessageNotify (Matchmaking)", notify)


_RouteFn = Callable[[Any, bytes, int], None]

_ROOM_ROUTES: Dict[str, _RouteFn] = {
    "GetRoomList": _http_get_room_list,
    "CreateRoom": _http_create_room,
    "JoinRoom": _http_join_room,
    "SpectateRoom": _http_spectate_room,
    "LeaveRoom": _http_leave_room,
    "KickRoomPlayer": _http_kick_room_player,
    "RoomInfo": _http_get_room_info,
    "GetRoomInfo": _http_get_room_info,
    "ChangeRoom": _http_change_room,
    "SetRoomReady": _http_set_room_ready,
    "SwitchRoomSeat": _http_switch_room_seat,
    "InviteRoom": _http_invite_room,
    "StartRoom": _http_start_room,
    "DropRoomMatch": _http_drop_room_match,
    "StartMatchMaking": _http_start_matchmaking,
    "CancelMatchMaking": _http_cancel_matchmaking,
    "GetMatchmakingStatus": _http_get_matchmaking_status,
    "GetGameServerList": _http_get_game_server_list,
    "GetGameOpeningInfo": _http_get_game_opening_info,
    "RoomPacket": _http_room_packet,
    "MatchmakingPacket": _http_matchmaking_packet,
    "AdminListModes": _http_admin_list_modes,
    "AdminToggleMode": _http_admin_toggle_mode,
    "AdminUnlockAllModes": _http_admin_unlock_all_modes,
    "AdminLockOptionalModes": _http_admin_lock_optional_modes,
    "AdminUpdateMode": _http_admin_update_mode,
    "AdminResetModes": _http_admin_reset_modes,
    "api/dashboard/modes": _http_admin_list_modes,
    "api/modes": _http_admin_list_modes,
}


def handle_room_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """Route Custom Room, Matchmaking, and Game Server HTTP endpoints."""
    del client_ip
    clean_path = path.split("?", 1)[0].strip("/")
    route_fn = _ROOM_ROUTES.get(clean_path)
    if route_fn is None:
        return False
    route_fn(handler, raw_body, account_id)
    return True


handle_room_post = handle_room_request
