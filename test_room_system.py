"""Comprehensive unittest suite for Free Fire 1.39 Custom Rooms & Matchmaking."""

import struct
import sys
import unittest
from pathlib import Path

SERVER_DIR = str(Path(__file__).resolve().parent)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.game_router import handle_game_post
from handlers.room_handler import (
    handle_room_request,
    handle_room_tcp_command,
    handle_tcp_frame,
)
from proto.decoder import (
    decode_proto,
    get_bool,
    get_bytes,
    get_float,
    get_int64,
    get_string,
    get_submessage,
    get_submessages,
    get_varint,
)
from proto.encoder import (
    encode_bool,
    encode_bytes,
    encode_packed_uint32,
    encode_string,
    encode_uint32,
    encode_uint64,
)
from proto.room_models import (
    ECustomRoomSetting,
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
    MatchMode,
    TCP_HANDSHAKE_ACK,
    encode_room_card_info,
)
from tcp_server import dispatch_tcp_packet


class _MockHandler:
    def __init__(self) -> None:
        self.calls = []
        self.headers = {"Host": "127.0.0.1:8080"}

    def send_proto(self, name: str, data: bytes) -> None:
        self.calls.append((name, data))


def _make_c2s_frame(cmd: int, flag: int, payload: bytes) -> bytes:
    return struct.pack(">BBi", cmd, flag, len(payload)) + payload


def _parse_s2c_frame(raw: bytes):
    cmd, length = struct.unpack_from(">Bi", raw, 0)
    return cmd, raw[5 : 5 + length]


def _make_proto_req(cmd: int, inner: bytes) -> bytes:
    return encode_uint32(1, cmd) + encode_bytes(2, inner)


class TestRoomAndMatchmaking(unittest.TestCase):
    def setUp(self) -> None:
        with state._lock:
            state._rooms.clear()
        self.h = _MockHandler()

    def test_http_room_lifecycle_and_game_router_pickup(self) -> None:
        # 1. /GetRoomList via game_router.handle_game_post -> proto.GetAllRoomsRes
        handled = handle_game_post(self.h, "/GetRoomList", "127.0.0.1", b"")
        self.assertTrue(handled)
        name, body = self.h.calls[-1]
        self.assertEqual(name, "GetAllRoomsRes")
        room_msgs = get_submessages(decode_proto(body), 1)
        self.assertEqual(len(room_msgs), 3)
        self.assertEqual(get_string(room_msgs[0], 2), "Bermuda Classic Public")
        self.assertEqual(get_varint(room_msgs[0], 15), ERoomType.CASUAL)
        self.assertTrue(get_bool(room_msgs[2], 11))
        self.assertEqual(get_string(room_msgs[2], 17), "139")

        # 2. /CreateRoom via game_router
        create_req = (
            encode_uint32(1, 2)
            + encode_uint32(2, GameMode.CS)
            + encode_uint32(3, GroupMode.QUAD)
            + encode_string(4, "Cook45 Scrims")
            + encode_string(5, "7788")
            + encode_uint32(6, 2)
            + encode_uint32(7, 4)
            + encode_bool(8, True)
            + encode_uint32(9, ERoomType.LEAGUE_NORMAL)
            + encode_uint32(14, ECustomRoomSetting.UNLIMITED_AMMO | ECustomRoomSetting.NO_FALLING_DAMAGE)
        )
        self.assertTrue(handle_game_post(self.h, "/CreateRoom", "127.0.0.1", create_req))
        ri = decode_proto(self.h.calls[-1][1])
        rid = get_varint(ri, 1)
        self.assertGreaterEqual(rid, 90001)
        self.assertEqual(get_string(ri, 2), "Cook45 Scrims")
        self.assertEqual(get_varint(ri, 3), DEFAULT_ACCOUNT_ID)
        self.assertEqual(get_string(ri, 10), "7788")
        self.assertTrue(get_bool(ri, 13))
        self.assertEqual(
            get_varint(ri, 18),
            ECustomRoomSetting.UNLIMITED_AMMO | ECustomRoomSetting.NO_FALLING_DAMAGE,
        )

        # 3. /JoinRoom wrong password vs right password vs room full
        bad_join = encode_uint64(1, rid) + encode_string(2, "0000")
        self.assertTrue(handle_room_request(self.h, "/JoinRoom", "127.0.0.1", bad_join, 1000000099))
        self.assertEqual(self.h.calls[-1], ("RoomJoinErr", b""))

        good_join = encode_uint64(1, rid) + encode_string(2, "7788") + encode_uint64(3, 1) + encode_bool(4, True)
        self.assertTrue(handle_room_request(self.h, "/JoinRoom", "127.0.0.1", good_join, 1000000099))
        jri = decode_proto(self.h.calls[-1][1])
        members = get_submessages(get_submessages(jri, 11)[0], 3)
        member_ids = [get_varint(m, 2) for m in members]
        self.assertEqual(set(member_ids), {DEFAULT_ACCOUNT_ID, 1000000099})

        # Full check
        _, err_full, _ = handle_room_tcp_command(
            EProtocolProto.ROOM, ERoomProto.JOIN, good_join, account_id=1000000077
        )
        self.assertEqual(err_full, ERoomErrCode.REACHMAXMEMBERS)

        # 4. /ChangeRoom + /SwitchRoomSeat + /SetRoomReady + /SpectateRoom + /StartRoom + /Kick + /Leave
        change_req = encode_uint64(1, rid) + encode_string(2, "Cook45 Finals") + encode_uint32(6, 12)
        self.assertTrue(handle_room_request(self.h, "/ChangeRoom", "127.0.0.1", change_req, DEFAULT_ACCOUNT_ID))
        self.assertEqual(get_string(decode_proto(self.h.calls[-1][1]), 2), "Cook45 Finals")
        self.assertEqual(get_varint(decode_proto(self.h.calls[-1][1]), 7), 12)

        seat_req = (
            encode_uint64(1, rid)
            + encode_uint64(2, 1000000099)
            + encode_uint32(3, ERoomPlayerRole.MEMBER)
            + encode_uint32(4, 2)
            + encode_uint32(5, 1)
        )
        self.assertTrue(handle_room_request(self.h, "/SwitchRoomSeat", "127.0.0.1", seat_req, 1000000099))
        self.assertEqual(len(get_submessages(decode_proto(self.h.calls[-1][1]), 11)), 2)

        # Seat collision check
        _, err_seat, _ = handle_room_tcp_command(
            EProtocolProto.ROOM,
            ERoomProto.SWITCHSEAT,
            encode_uint64(1, rid) + encode_uint64(2, DEFAULT_ACCOUNT_ID) + encode_uint32(3, 1) + encode_uint32(4, 2) + encode_uint32(5, 1),
            account_id=DEFAULT_ACCOUNT_ID,
        )
        self.assertEqual(err_seat, ERoomErrCode.SEATOCCUPIED)

        self.assertTrue(handle_room_request(self.h, "/SetRoomReady", "127.0.0.1", encode_bool(1, True), 1000000099))
        ready_ntf = decode_proto(self.h.calls[-1][1])
        self.assertTrue(get_bool(get_submessages(ready_ntf, 2)[0], 6))

        self.assertTrue(
            handle_room_request(self.h, "/SpectateRoom", "127.0.0.1", encode_uint64(1, rid) + encode_string(2, "7788"), 1000000088)
        )
        self.assertEqual(len(get_submessages(decode_proto(self.h.calls[-1][1]), 12)), 1)

        self.assertTrue(handle_room_request(self.h, "/StartRoom", "127.0.0.1", encode_uint64(1, rid), DEFAULT_ACCOUNT_ID))
        suss = decode_proto(self.h.calls[-1][1])
        self.assertGreater(get_varint(suss, 1), 700000)
        self.assertEqual(get_varint(suss, 8), MatchMode.ROOM)
        self.assertNotIn(10, suss)

        # Non-owner kick fails with NOTOWNER
        _, err_not_owner, _ = handle_room_tcp_command(
            EProtocolProto.ROOM, ERoomProto.KICK, encode_uint64(1, DEFAULT_ACCOUNT_ID), account_id=1000000099
        )
        self.assertEqual(err_not_owner, ERoomErrCode.NOTOWNER)

        self.assertTrue(handle_room_request(self.h, "/KickRoomPlayer", "127.0.0.1", encode_uint64(1, 1000000099), DEFAULT_ACCOUNT_ID))
        kick_ntf = decode_proto(self.h.calls[-1][1])
        self.assertEqual(get_varint(get_submessage(kick_ntf, 1), 2), 1000000099)

        self.assertTrue(handle_room_request(self.h, "/LeaveRoom", "127.0.0.1", encode_uint64(1, rid), DEFAULT_ACCOUNT_ID))
        dismiss_ntf = decode_proto(self.h.calls[-1][1])
        self.assertEqual(get_varint(dismiss_ntf, 2), rid)
        self.assertEqual(get_varint(dismiss_ntf, 3), ERoomDismissReason.NORMAL)

    def test_matchmaking_and_game_server_endpoints(self) -> None:
        mm_req = (
            encode_packed_uint32(1, [1, 2])
            + encode_uint32(2, GameMode.BATTLE_ROYALE)
            + encode_uint32(4, 0)
            + encode_uint32(8, MatchMode.RANKING)
        )
        self.assertTrue(handle_room_request(self.h, "/StartMatchMaking", "127.0.0.1", mm_req, DEFAULT_ACCOUNT_ID))
        mm_suss = decode_proto(self.h.calls[-1][1])
        self.assertEqual(get_varint(mm_suss, 6), 1)
        self.assertEqual(get_varint(mm_suss, 8), MatchMode.RANKING)
        self.assertTrue(state.get_team(account_id=DEFAULT_ACCOUNT_ID)["matchmaking"])

        self.assertTrue(handle_room_request(self.h, "/GetMatchmakingStatus", "127.0.0.1", b"", DEFAULT_ACCOUNT_ID))
        self.assertEqual(self.h.calls[-1][0], "MatchmakingSussNtf (Status)")

        self.assertTrue(handle_room_request(self.h, "/CancelMatchMaking", "127.0.0.1", b"", DEFAULT_ACCOUNT_ID))
        self.assertFalse(state.get_team(account_id=DEFAULT_ACCOUNT_ID)["matchmaking"])

        # /GetGameServerList & /GetGameOpeningInfo
        self.assertTrue(handle_game_post(self.h, "/GetGameServerList", "127.0.0.1", b""))
        gs = decode_proto(self.h.calls[-1][1])
        self.assertEqual(len(get_submessages(gs, 1)), 2)
        self.assertAlmostEqual(get_float(get_submessages(gs, 2)[0], 5), 1.0, places=4)

        self.assertTrue(handle_room_request(self.h, "/GetGameOpeningInfo", "127.0.0.1", encode_string(1, "IND") + encode_string(2, "en"), DEFAULT_ACCOUNT_ID))
        goi = decode_proto(self.h.calls[-1][1])
        descs = get_submessages(get_submessage(goi, 1), 1)
        self.assertEqual(len(descs), 21)
        self.assertEqual(get_string(descs[0], 2), "Bermuda")
        self.assertEqual(get_string(descs[0], 4), "00:00:00")
        self.assertEqual(get_string(descs[0], 13), "2020-01-01 00:00:00")
        self.assertEqual(get_int64(goi, 2), 0)

    def test_tcp_server_dispatch_and_framing(self) -> None:
        # 1. Handshake ACK
        init_frame = _make_c2s_frame(EProtocolProto.INIT, 0, b"login_key_123")
        self.assertEqual(handle_tcp_frame(init_frame, DEFAULT_ACCOUNT_ID), TCP_HANDSHAKE_ACK)

        # 2. Live tcp_server.dispatch_tcp_packet integration for ROOM (14)
        resp_cmd, ret_code, resp_payload = dispatch_tcp_packet(
            EProtocolProto.ROOM, ERoomProto.ROOMLIST, b"", account_id=DEFAULT_ACCOUNT_ID
        )
        self.assertEqual(resp_cmd, ERoomProto.ROOMLIST)
        self.assertEqual(ret_code, ERoomErrCode.SUSS)
        tcp_rooms = get_submessages(decode_proto(resp_payload), 1)
        self.assertEqual(len(tcp_rooms), 3)
        self.assertNotIn(17, tcp_rooms[0])  # tcp.RoomBasicInfo stops at tag 16

        # 3. Full 6B C2S -> 5B S2C MessageNotify round-trip for ROOMLIST & GAMEOPENINGINFO
        roomlist_frame = _make_c2s_frame(EProtocolProto.ROOM, 0, _make_proto_req(ERoomProto.ROOMLIST, b""))
        s2c_cmd, s2c_payload = _parse_s2c_frame(handle_tcp_frame(roomlist_frame, DEFAULT_ACCOUNT_ID))
        self.assertEqual(s2c_cmd, EProtocolProto.ROOM)
        ntf = decode_proto(s2c_payload)
        self.assertEqual(get_varint(ntf, 1), DEFAULT_ACCOUNT_ID)
        self.assertEqual(get_varint(ntf, 2), EProtocolProto.ROOM)
        self.assertEqual(get_varint(ntf, 3), ERoomErrCode.SUSS)
        self.assertEqual(get_varint(ntf, 4), ERoomProto.ROOMLIST)

        mm_goi_frame = _make_c2s_frame(
            EProtocolProto.MATCHMAKING, 0, _make_proto_req(EMatchmakingProto.GAMEOPENINGINFO, encode_string(1, "IND"))
        )
        s2c_cmd2, s2c_payload2 = _parse_s2c_frame(handle_tcp_frame(mm_goi_frame, DEFAULT_ACCOUNT_ID))
        self.assertEqual(s2c_cmd2, EProtocolProto.MATCHMAKING)
        ntf2 = decode_proto(s2c_payload2)
        self.assertEqual(get_varint(ntf2, 4), EMatchmakingProto.GAMEOPENINGINFO)

        # 4. Invite self error & RoomCardInfo check
        resp_cmd_inv, ret_inv, _ = dispatch_tcp_packet(
            EProtocolProto.ROOM, ERoomProto.INVITE, encode_uint64(1, DEFAULT_ACCOUNT_ID), account_id=DEFAULT_ACCOUNT_ID
        )
        self.assertEqual(resp_cmd_inv, ERoomProto.INVITE)
        self.assertEqual(ret_inv, ERoomErrCode.CANNOTINVITESELF)

        rc = decode_proto(encode_room_card_info(600000001, 5, 0))
        self.assertEqual(get_varint(rc, 1), 600000001)
        self.assertEqual(get_varint(rc, 2), 5)

        self.assertFalse(handle_room_request(self.h, "/UnknownEndpoint", "127.0.0.1", b"", DEFAULT_ACCOUNT_ID))


if __name__ == "__main__":
    unittest.main(verbosity=2)
