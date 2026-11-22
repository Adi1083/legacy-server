"""
Barbosa Project 1.39 Threaded Lobby TCP Server (`port 8081`).

Implements Free Fire 1.39's binary TCP framing (`TCPSession` / `TCPMsgPacket` /
`ServiceConnectionHandler`):
- Connect Handshake: Client sends `[1B cmd=0x01][1B flag][4B BE len][login_key]`,
  server responds with raw 1-byte `b"\\x02"`.
- C2S Packets (6-byte header): `[1B cmd][1B flag][4B BE length][payload]`
  where `cmd` is `tcp.EProtocol.Proto` (`2=HEARTBEAT`, `3=MATCHMAKING`, `5=GROUP`,
  `14=ROOM`, `15=PRESENCE`, `18=CHANNEL/CHAT`, etc.) and `payload` is
  `tcp.ProtoReq` (`1: uint32 cmd`, `2: bytes data`).
- S2C Packets (5-byte header, no flag byte): `[1B protocol][4B BE length][payload]`
  where `payload` is `proto.MessageNotify` (`1: account_id`, `2: protocol`,
  `3: ret`, `4: cmd`, `5: content`).
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import socket
import socketserver
import struct
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

logger = logging.getLogger("TCPServer")

from core.logger import log_request
from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.team_handler import handle_group_tcp_command
from proto.decoder import decode_proto, get_packed_varints, get_string, get_varint
from proto.encoder import (
    encode_bool,
    encode_int64,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)
from proto.social_models import encode_presence_list_res
from proto.team_models import (
    EMatchmakingProto,
    EProtocolProto,
    GameMode,
    MatchMode,
    decode_proto_req,
    encode_matchmaking_suss_ntf,
    encode_message_notify,
)

TCP_PORT = 8081
HANDSHAKE_ACK = b"\x02"
MAX_PACKET_SIZE = 4 * 1024 * 1024


class EProtocolExtra:
    """Authentic `tcp.EProtocol.Proto` IDs from Free Fire 1.39 IL2CPP TypeDef [5936]."""

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
    CHANNEL = 18  # Lobby / Squad / Global Chat
    STORE = 19
    PET = 20
    MANUAL = 21
    CHAMPIONSHIP = 22
    ANTIADDICTION = 23
    FRESH = 24


class EInventoryProto:
    """Authentic `tcp.EInventory.Proto` opcodes from IL2CPP TypeDef [5852]."""

    NONE = 0
    TOPUP_NTF = 1
    MONEY_UPDATE_NTF = 2
    NEW_ITEMS_NTF = 3
    REBATECARD_NTF = 4
    REBATECARD_REDEEM_NTF = 5
    ITEM_CHANGE = 6
    SELECTED_ITEMS_CHANGE = 7
    EP_CARD_NTF = 8
    INSTALLMENT_ITEMS_NEW_NTF = 9
    INSTALLMENT_ITEMS_CHANGE_NTF = 10
    INSTALLMENT_ITEMS_DELETE_NTF = 11
    INSTALLMENT_PAY_NTF = 12


class EProfileProto:
    """Authentic `tcp.EProfile.Proto` opcodes from IL2CPP TypeDef [5892]."""

    NONE = 0
    NEW_PROFILE_NTF = 1
    NEW_SKILL_NTF = 2
    PROFILE_CHANGE_NTF = 3


class EPresenceProto:
    NONE = 0
    PRESENCELIST = 1


class EChannelProto:
    NONE = 0
    TEXT_MSG = 1
    TEXT_MSG_NTF = 2
    JOIN_CHANNEL = 3
    LEAVE_CHANNEL = 4


# Active TCP socket registry indexed by `account_id` for unsolicited pushes
_SESS_LOCK = threading.RLock()
_ACTIVE_SESSIONS: Dict[int, List[Tuple[socket.socket, threading.Lock]]] = {}
_TCP_SERVER_INSTANCE: Optional["BarbosaTCPServer"] = None
_TCP_THREAD: Optional[threading.Thread] = None


def _register_session(account_id: int, sock: socket.socket, write_lock: threading.Lock) -> None:
    with _SESS_LOCK:
        _ACTIVE_SESSIONS.setdefault(int(account_id), []).append((sock, write_lock))


def _unregister_session(account_id: int, sock: socket.socket) -> None:
    with _SESS_LOCK:
        aid = int(account_id)
        entries = _ACTIVE_SESSIONS.get(aid)
        if not entries:
            return
        remaining = [(s, lk) for (s, lk) in entries if s is not sock]
        if remaining:
            _ACTIVE_SESSIONS[aid] = remaining
        else:
            _ACTIVE_SESSIONS.pop(aid, None)


def pack_s2c_packet(outer_cmd: int, payload: bytes) -> bytes:
    """Frame an S2C packet with the 5-byte header: `[1B cmd][4B BE len][payload]`."""
    raw = bytes(payload or b"")
    return struct.pack(">BI", int(outer_cmd) & 0xFF, len(raw)) + raw


def pack_message_notify_frame(
    account_id: int,
    protocol: int,
    cmd: int,
    content: bytes = b"",
    ret: int = 0,
) -> bytes:
    """Encode `proto.MessageNotify` and frame it with the 5-byte S2C header."""
    notify = encode_message_notify(
        account_id=int(account_id),
        protocol=int(protocol),
        ret=int(ret),
        cmd=int(cmd),
        content=bytes(content or b""),
    )
    return pack_s2c_packet(protocol, notify)


def push_tcp_notify(
    account_id: int,
    protocol: int,
    cmd: int,
    content: bytes = b"",
    ret: int = 0,
) -> int:
    """
    Push an unsolicited `MessageNotify` frame to all connected TCP sockets for `account_id`.
    Returns the number of sockets the frame was written to.
    """
    frame = pack_message_notify_frame(account_id, protocol, cmd, content=content, ret=ret)
    with _SESS_LOCK:
        targets = list(_ACTIVE_SESSIONS.get(int(account_id), ()))
    sent = 0
    for sock, write_lock in targets:
        try:
            with write_lock:
                sock.sendall(frame)
            sent += 1
        except OSError:
            _unregister_session(account_id, sock)
    return sent


def push_collection_sync(account_id: int) -> int:
    """
    Push real-time collection, profile, and lobby equipment sync packets to client socket:
    1. EProtocol.Proto.INVENTORY (8) cmd 7 (SELECTED_ITEMS_CHANGE):
       proto.SelectedItems & proto.CSGetSelectedItemsRes for collection badges/ticks.
    2. EProtocol.Proto.INVENTORY (8) cmd 6 (ITEM_CHANGE):
       Instant item state refresh.
    3. EProtocolExtra.PROFILE (13) cmd 3 (PROFILE_CHANGE_NTF):
       proto.AvatarProfile for wardrobe and character visuals.
    4. EProtocolProto.GROUP (5) cmd 18 (CHANGE_NTF) & cmd 8 (GROUP_CHANGE_NTF):
       tcp.GroupInfo for 3D lobby model on pedestal and weapon in hand.
    """
    aid = int(account_id)
    sent = 0
    try:
        from handlers.inventory_handler import inventory_service
        from proto.inventory_models import encode_selected_items, encode_avatar_profile
        from proto.encoder import encode_submessage

        sel = inventory_service.get_selected_items(aid)
        selected_bytes = encode_selected_items(
            avatar_id=sel["avatar_id"],
            skin_color=sel["skin_color"],
            clothes=sel["clothes"],
            loadouts=sel["loadouts"],
            banner_id=sel["banner_id"],
            head_pic=sel["head_pic"],
            slots=sel["slots"],
            emotes=sel["emotes"],
            shows=sel["shows"],
            pve_primary_weapon_skin=sel["pve_primary_weapon_skin"],
            ranking_cards=sel["ranking_cards"],
        )
        selected_res = encode_submessage(1, selected_bytes)

        # 1. Push INVENTORY SELECTED_ITEMS_CHANGE (7) and ITEM_CHANGE (6)
        sent += push_tcp_notify(aid, protocol=EProtocolExtra.INVENTORY, cmd=EInventoryProto.SELECTED_ITEMS_CHANGE, content=selected_res, ret=0)
        sent += push_tcp_notify(aid, protocol=EProtocolExtra.INVENTORY, cmd=EInventoryProto.SELECTED_ITEMS_CHANGE, content=selected_bytes, ret=0)
        sent += push_tcp_notify(aid, protocol=EProtocolExtra.INVENTORY, cmd=EInventoryProto.ITEM_CHANGE, content=selected_bytes, ret=0)

        # 2. Push PROFILE PROFILE_CHANGE_NTF (3)
        char = state.get_character(sel["avatar_id"]) or {}
        skills = char.get("equiped_skills") or []
        level = int(char.get("unlocked_level", 8))
        pve_w = int(char.get("pve_primary_weapon", 0))
        avatar_profile_bytes = encode_avatar_profile(
            avatar_id=sel["avatar_id"],
            unlocked_level=level,
            skin_color=sel["skin_color"],
            clothes=sel["clothes"],
            equiped_skills=skills,
            is_selected=True,
            pve_primary_weapon=pve_w,
        )
        sent += push_tcp_notify(aid, protocol=EProtocolExtra.PROFILE, cmd=EProfileProto.PROFILE_CHANGE_NTF, content=avatar_profile_bytes, ret=0)

        # 3. Push GROUP CHANGE_NTF (18) and GROUP_CHANGE_NTF (8) for lobby 3D pedestal character & weapon
        from handlers.team_handler import _get_or_create_team, _enrich_team, _encode_team_group_info
        team = state.get_team(account_id=aid) or _get_or_create_team(aid)
        if team:
            enriched = _enrich_team(team) or team
            group_payload = _encode_team_group_info(enriched)
            sent += push_tcp_notify(aid, protocol=EProtocolProto.GROUP, cmd=18, content=group_payload, ret=0)
            sent += push_tcp_notify(aid, protocol=EProtocolProto.GROUP, cmd=8, content=group_payload, ret=0)
    except Exception as e:
        logger.error("push_collection_sync error for account %d: %s", aid, e)
    return sent


def _recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
    """Read exactly `n` bytes from `sock`, returning `None` on clean EOF."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def _extract_account_id(login_blob: bytes, client_ip: str = "", default: int = DEFAULT_ACCOUNT_ID) -> int:
    """Attempt to extract an account ID from the handshake login key blob."""
    from core.player import player_manager
    if not login_blob:
        if client_ip:
            sess_aid = player_manager.get_session_account_id(client_ip)
            if sess_aid:
                return sess_aid
        return default

    # 1. Quick check: UTF-8 text digits or token
    try:
        text = login_blob.decode("utf-8", errors="ignore").strip()
        if text.isdigit() and int(text) > 0:
            return int(text)
        if text:
            p = player_manager.find_account_by_token(text)
            if p:
                return p.account_id
            m = re.search(r"\b(10\d{3,}|[1-9]\d{4,})\b", text)
            if m:
                val = int(m.group(1))
                if val > 0:
                    return val
    except Exception:
        pass

    # 2. Try raw binary integer (uint64 or uint32, LE / BE)
    if len(login_blob) == 8:
        try:
            val_le = struct.unpack("<Q", login_blob)[0]
            if 10000 <= val_le <= 999999999:
                return val_le
            val_be = struct.unpack(">Q", login_blob)[0]
            if 10000 <= val_be <= 999999999:
                return val_be
        except Exception:
            pass
    elif len(login_blob) == 4:
        try:
            val_le = struct.unpack("<I", login_blob)[0]
            if 10000 <= val_le <= 999999999:
                return val_le
            val_be = struct.unpack(">I", login_blob)[0]
            if 10000 <= val_be <= 999999999:
                return val_be
        except Exception:
            pass

    # 3. Try decoding protobuf
    try:
        f = decode_proto(login_blob)
        aid = get_varint(f, 1, 0)
        if aid > 0:
            return aid
        tok = get_string(f, 2, "") or get_string(f, 8, "") or get_string(f, 29, "")
        if tok:
            p = player_manager.find_account_by_token(tok)
            if p:
                return p.account_id
    except Exception:
        pass

    # 4. Fallback to client_ip bound session
    if client_ip:
        sess_aid = player_manager.get_session_account_id(client_ip)
        if sess_aid:
            return sess_aid

    return default


def encode_game_opening_info_res() -> bytes:
    """
    Encode `proto.GameOpeningInfoRes` [5602] for `MATCHMAKING (3)` cmd `GAMEOPENINGINFO (7)`.
    Schema reconstructed from Barbosa IL2CPP metadata v23:
    1: GameOpeningInfoDescList [5599] -> 1: repeated GameOpeningInfoDesc [5598]
       1: uint32 map_id (1: Bermuda, 2: Purgatory, 3: Kalahari)
       3: string name
       4: string language ("en")
       6: string start_time ("00:00:00")
       8: string end_time ("23:59:59")
       9: string tips ("")
       10: uint32 limited_rank (0)
       11: uint32 limited_count (0)
       12: bool enable (True)
       13: uint32 game_mode (1: BR/Classic, 2: SpeedRoyale, 8: Purge/RushHour, 11/15: CS)
       14: uint32 match_mode (1: Casual, 2: Ranking, 0: None)
       15: bool is_new (False)
       17: string config_start_time ("2020-01-01 00:00:00")
       18: string config_end_time ("2030-01-01 23:59:59")
       19: string player_count_limit ("0")
       20: uint32 level_visual_style (0)
       21: string difficulty ("0")
       22: bool pve_force_mm (False)
       23: string weekday ("0")
       24: uint32 sort_id
    2: int64 timezone_offset_secs
    3: GameModeNameList [5601] -> 1: repeated GameModeNameDesc [5600]
       1: uint32 mode_id
       2: string language ("en")
       3: string translation
    """
    from handlers.room_handler import _default_game_opening_descs, get_game_mode_names
    from proto.room_models import encode_game_opening_info_res as _proto_encode_res
    return _proto_encode_res(
        descs=_default_game_opening_descs(),
        timezone_offset_secs=0,
        mode_names=get_game_mode_names("en"),
    )


_encode_game_opening_info_res = encode_game_opening_info_res


def _handle_presence(sub_cmd: int, raw_body: bytes, account_id: int) -> Tuple[int, int, bytes]:
    """Handle `EProtocol.Proto.PRESENCE (15)` `PresenceListReq` -> `PresenceListRes`."""
    f = decode_proto(raw_body)
    account_ids = get_packed_varints(f, 1)
    list_type = get_varint(f, 2, 1)

    players: List[Dict[str, Any]] = []
    if account_ids:
        for aid in account_ids:
            p = state.get_player(int(aid))
            if p:
                players.append(p)
            else:
                players.append({"account_id": int(aid), "region": "DEFAULT", "is_online": True})
    else:
        players = state.list_friends(account_id=account_id)

    payload = encode_presence_list_res(players, account_list_type=list_type)
    resp_cmd = sub_cmd if sub_cmd else EPresenceProto.PRESENCELIST
    return resp_cmd, 0, payload


def _handle_channel_chat(sub_cmd: int, raw_body: bytes, account_id: int) -> Tuple[int, int, bytes]:
    """
    Handle `EProtocol.Proto.CHANNEL (18)` chat & channel actions:
    - `TEXT_MSG (1)` -> decodes `TextMsgReq` and echoes `TEXT_MSG_NTF (2)` payload.
    - `JOIN_CHANNEL (3)` / `LEAVE_CHANNEL (4)` -> returns success ack.
    """
    if sub_cmd == EChannelProto.TEXT_MSG:
        f = decode_proto(raw_body)
        sender_id = get_varint(f, 1, account_id) or account_id
        channel_id = get_varint(f, 2, 0)
        channel_type = get_varint(f, 3, 0)
        content = get_string(f, 4, "")
        send_at = get_varint(f, 5, int(time.time())) or int(time.time())
        group_id = get_varint(f, 6, 0)

        out = bytearray()
        out += encode_uint64(1, int(sender_id))
        out += encode_uint64(2, int(channel_id))
        out += encode_uint32(3, int(channel_type))
        if content:
            out += encode_string(4, content)
        out += encode_uint64(5, int(send_at))
        if group_id:
            out += encode_uint64(6, int(group_id))
        return EChannelProto.TEXT_MSG_NTF, 0, bytes(out)

    return sub_cmd, 0, b""


def _resolve_room_tcp_handler() -> Optional[Callable[..., Tuple[int, int, bytes]]]:
    """Optionally locate `handlers.room_handler.handle_room_tcp_command` when present."""
    try:
        mod = importlib.import_module("handlers.room_handler")
        for attr in ("handle_room_tcp_command", "handle_tcp_room_command"):
            fn = getattr(mod, attr, None)
            if callable(fn):
                return fn
    except ImportError:
        pass
    return None


def dispatch_tcp_packet(
    protocol: int,
    sub_cmd: int,
    data: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> Tuple[int, int, bytes]:
    """
    Dispatch a decoded `tcp.ProtoReq` `(protocol, sub_cmd, data)` and return
    `(response_cmd, ret_code, response_payload_bytes)`.
    """
    if protocol == EProtocolProto.MATCHMAKING:
        from handlers.room_handler import handle_matchmaking_tcp_command
        return handle_matchmaking_tcp_command(protocol, sub_cmd, data, account_id=account_id)

    if protocol == EProtocolProto.GROUP:
        return handle_group_tcp_command(protocol, sub_cmd, data, account_id=account_id)

    if protocol == EProtocolExtra.INVENTORY:
        from handlers.inventory_handler import inventory_service
        from proto.inventory_models import encode_selected_items
        sel = inventory_service.get_selected_items(account_id=account_id)
        selected_bytes = encode_selected_items(
            avatar_id=sel["avatar_id"],
            skin_color=sel["skin_color"],
            clothes=sel["clothes"],
            loadouts=sel["loadouts"],
            banner_id=sel["banner_id"],
            head_pic=sel["head_pic"],
            slots=sel["slots"],
            emotes=sel["emotes"],
            shows=sel["shows"],
            pve_primary_weapon_skin=sel["pve_primary_weapon_skin"],
            ranking_cards=sel["ranking_cards"],
        )
        res_bytes = encode_submessage(1, selected_bytes)
        resp_cmd = sub_cmd if sub_cmd else EInventoryProto.SELECTED_ITEMS_CHANGE
        return resp_cmd, 0, res_bytes

    if protocol == EProtocolExtra.PROFILE:
        from proto.inventory_models import encode_avatar_profile
        prof = state.get_profile(account_id) or {}
        aid = int(prof.get("avatar_id", 102000004))
        char = state.get_character(aid) or {}
        profile_bytes = encode_avatar_profile(
            avatar_id=aid,
            unlocked_level=int(char.get("unlocked_level", 8)),
            skin_color=int(prof.get("skin_color", 0)),
            clothes=list(prof.get("clothes") or []),
            equiped_skills=list(char.get("equiped_skills") or []),
            is_selected=True,
            pve_primary_weapon=int(prof.get("pve_primary_weapon_skin", 0)),
        )
        resp_cmd = sub_cmd if sub_cmd else EProfileProto.PROFILE_CHANGE_NTF
        return resp_cmd, 0, profile_bytes

    if protocol == EProtocolExtra.PRESENCE:
        return _handle_presence(sub_cmd, data, account_id=account_id)

    if protocol == EProtocolExtra.CHANNEL:
        return _handle_channel_chat(sub_cmd, data, account_id=account_id)

    if protocol == EProtocolExtra.ROOM:
        room_fn = _resolve_room_tcp_handler()
        if room_fn is not None:
            return room_fn(protocol, sub_cmd, data, account_id=account_id)
        return sub_cmd, 0, b""

    return sub_cmd, 0, b""


def _schedule_matchmaking_success(account_id: int, delay_secs: float = 1.0, client_ip: str = "127.0.0.1") -> None:
    """
    Schedule asynchronous dispatch of `MatchmakingSussNtf` after `delay_secs`.
    Allows the client UI to cleanly display the matchmaking radar/timer dialog first.
    If the player cancels matchmaking during this window, no notification is sent.
    """
    def _run() -> None:
        time.sleep(delay_secs)
        team = state.get_team(account_id=account_id)
        if not team or not team.get("matchmaking"):
            return

        map_ids = team.get("map_ids") or [int(team.get("map_id", 1))]
        map_id = int(map_ids[0])
        game_mode = int(team.get("game_mode", GameMode.BATTLE_ROYALE))
        match_mode = int(team.get("match_mode", MatchMode.CASUAL))
        difficulty = int(team.get("difficulty", 1))
        from core.state import generate_match_id
        match_id = generate_match_id()

        import hashlib
        sec_hex = hashlib.md5(f"sec_{match_id}".encode()).hexdigest()
        tok_hex = hashlib.md5(f"tok_{match_id}_{int(time.time())}".encode()).hexdigest()

        # Link match token and MatchDirector instance
        targets = {int(account_id)}
        if "members" in team and isinstance(team["members"], list):
            for m in team["members"]:
                mid = m.get("account_id") if isinstance(m, dict) else m
                if mid:
                    targets.add(int(mid))

        try:
            from combat.udp_server import get_combat_server
            from combat.match_director import global_match_director
            udp_srv = get_combat_server()
            player_nick = "Player"
            try:
                p_prof = state.get_profile(int(account_id))
                if p_prof and p_prof.get("nickname"):
                    player_nick = p_prof["nickname"]
            except Exception:
                pass

            for target_aid in targets:
                t_nick = player_nick if target_aid == int(account_id) else str(state.get_profile(target_aid).get("nickname", f"Player_{target_aid}"))
                udp_srv.register_match_token(token=tok_hex, account_id=target_aid, match_id=match_id, nickname=t_nick)

            if global_match_director:
                bot_cnt = 49 if game_mode == GameMode.BATTLE_ROYALE else 7
                global_match_director.create_match(
                    match_id=match_id,
                    map_id=map_id,
                    game_mode=game_mode,
                    match_mode=match_mode,
                    host_player_id=str(account_id),
                    host_nickname=player_nick,
                    bot_count=bot_cnt,
                    prepare_token=tok_hex,
                    secret=sec_hex
                )
        except Exception as e:
            logger.error("Failed to register combat match: %s", e)

        # For BlueStacks / Android emulator, the host machine is always 10.0.2.2
        server_ip = "10.0.2.2"
        suss_payload = encode_matchmaking_suss_ntf(
            match_id=match_id,
            server_addr=f"{server_ip}:39800",
            secret=sec_hex,
            prepare_token=tok_hex,
            sleep_ms=0,
            map_id=map_id,
            game_mode=game_mode,
            match_mode=match_mode,
            level_visual_style=1,
            difficulty=difficulty,
        )

        for target_aid in targets:
            push_tcp_notify(
                account_id=target_aid,
                protocol=EProtocolProto.MATCHMAKING,
                cmd=EMatchmakingProto.MATCHMAKINGSUSS_NTF,
                content=suss_payload,
                ret=0,
            )

    t = threading.Thread(target=_run, daemon=True)
    t.start()


class BarbosaTCPHandler(socketserver.BaseRequestHandler):
    """Per-connection threaded handler for Free Fire 1.39 TCP Lobby sessions."""

    def setup(self) -> None:
        self.request.settimeout(300.0)

    def handle(self) -> None:
        sock: socket.socket = self.request
        client_ip = str(self.client_address[0]).replace("::ffff:", "")
        from core.player import player_manager
        account_id = player_manager.get_session_account_id(client_ip) or DEFAULT_ACCOUNT_ID
        write_lock = threading.Lock()
        registered = False

        try:
            while True:
                header = _recv_exact(sock, 6)
                if header is None:
                    break
                cmd, _flag, length = struct.unpack(">BBI", header)
                if length > MAX_PACKET_SIZE:
                    break

                payload = _recv_exact(sock, length) if length > 0 else b""
                if payload is None:
                    break

                # Connect handshake: cmd=1 -> respond with single byte b"\x02"
                if cmd == EProtocolExtra.INIT:
                    parsed_aid = _extract_account_id(payload, client_ip=client_ip, default=account_id)
                    if not registered or parsed_aid != account_id:
                        if registered:
                            _unregister_session(account_id, sock)
                        account_id = parsed_aid
                        _register_session(account_id, sock, write_lock)
                        registered = True
                    player_manager.bind_session(client_ip, account_id)
                    state.set_player_online(account_id, online_status=1)
                    try:
                        log_request("TCP", f"tcp://INIT?aid={account_id}", client_ip, payload)
                    except Exception:
                        pass
                    with write_lock:
                        sock.sendall(HANDSHAKE_ACK)
                    continue

                if not registered:
                    _register_session(account_id, sock, write_lock)
                    registered = True
                    state.set_player_online(account_id, online_status=1)

                # Heartbeat ping
                if cmd == EProtocolExtra.HEARTBEAT:
                    if not payload:
                        with write_lock:
                            sock.sendall(pack_s2c_packet(EProtocolExtra.HEARTBEAT, b""))
                        continue
                    preq = decode_proto_req(payload)
                    frame = pack_message_notify_frame(account_id, EProtocolExtra.HEARTBEAT, preq["cmd"], b"", ret=0)
                    with write_lock:
                        sock.sendall(frame)
                    continue

                preq = decode_proto_req(payload)
                sub_cmd = preq["cmd"]
                inner_data = preq["data"]

                try:
                    log_request("TCP", f"tcp://proto_{cmd}/cmd_{sub_cmd}", client_ip, inner_data)
                except Exception:
                    pass

                resp_cmd, ret_code, resp_payload = dispatch_tcp_packet(
                    cmd, sub_cmd, inner_data, account_id=account_id
                )
                frame = pack_message_notify_frame(
                    account_id=account_id,
                    protocol=cmd,
                    cmd=resp_cmd,
                    content=resp_payload,
                    ret=ret_code,
                )
                with write_lock:
                    sock.sendall(frame)

                if (
                    cmd == EProtocolProto.MATCHMAKING
                    and sub_cmd in (EMatchmakingProto.START, EMatchmakingProto.GROUPSTART)
                    and ret_code == 0
                ):
                    _schedule_matchmaking_success(account_id, client_ip=client_ip)
        except (ConnectionResetError, BrokenPipeError, TimeoutError, OSError):
            pass
        except Exception as ex:
            import traceback
            err_file = os.path.join(_SERVER_DIR, "tcp_err.log")
            with open(err_file, "a", encoding="utf-8") as ef:
                ef.write(traceback.format_exc())
        finally:
            if registered:
                _unregister_session(account_id, sock)
                with _SESS_LOCK:
                    has_remaining = bool(_ACTIVE_SESSIONS.get(account_id))
                if not has_remaining:
                    state.set_player_online(account_id, online_status=0)


class BarbosaTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 256

    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass: Any, use_ipv6: bool = True):
        self.address_family = socket.AF_INET6 if use_ipv6 else socket.AF_INET
        super().__init__(server_address, RequestHandlerClass)

    def server_bind(self) -> None:
        if self.address_family == socket.AF_INET6:
            try:
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except Exception:
                pass
        super().server_bind()


def start_tcp_server(
    host: str = "::",
    port: int = TCP_PORT,
    background: bool = True,
) -> BarbosaTCPServer:
    """
    Start the threaded Lobby TCP server on `(host, port)`.
    When `background=True`, runs `serve_forever` in a daemon thread and returns
    the server instance cleanly for `server.py` startup integration.
    """
    global _TCP_SERVER_INSTANCE, _TCP_THREAD
    if _TCP_SERVER_INSTANCE is not None:
        return _TCP_SERVER_INSTANCE

    use_ipv6 = ":" in host
    try:
        srv = BarbosaTCPServer((host, int(port)), BarbosaTCPHandler, use_ipv6=use_ipv6)
    except OSError:
        srv = BarbosaTCPServer(("0.0.0.0", int(port)), BarbosaTCPHandler, use_ipv6=False)

    _TCP_SERVER_INSTANCE = srv
    if background:
        t = threading.Thread(target=srv.serve_forever, name="barbosa-tcp-lobby", daemon=True)
        t.start()
        _TCP_THREAD = t
    return srv


def stop_tcp_server() -> None:
    """Shut down the running Lobby TCP server if active."""
    global _TCP_SERVER_INSTANCE, _TCP_THREAD
    if _TCP_SERVER_INSTANCE is not None:
        try:
            _TCP_SERVER_INSTANCE.shutdown()
            _TCP_SERVER_INSTANCE.server_close()
        finally:
            _TCP_SERVER_INSTANCE = None
            _TCP_THREAD = None


if __name__ == "__main__":
    print("=" * 65, flush=True)
    print(f"[*] Barbosa Project 1.39 Lobby TCP Server listening on port {TCP_PORT}", flush=True)
    print("=" * 65, flush=True)
    srv = start_tcp_server(port=TCP_PORT, background=False)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] TCP Server stopped.", flush=True)
        stop_tcp_server()
