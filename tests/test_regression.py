"""
Test Suite 8: Core Regression Tests for Free Fire 1.39 Server.
Verifies that Luck Royale restoration did not break core game services:
1. Authentication & Login (/MajorLogin, /GetPlayerPersonalShow, /GetProfileList).
2. Lobby TCP Handshake & Heartbeat framing (EProtocol.Proto.INIT & HEARTBEAT).
3. Player Profile Synchronization (nickname, banner, stats, profile sync).
4. Character Equipment & Wardrobe (/ChangeClothes, /EquipSkill, /SelectProfile).
5. Custom Rooms & Matchmaking Handoff (/GetRoomList, /CreateRoom, EProtocol.Proto.MATCHMAKING).
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

SERVER_DIR = str(Path(__file__).resolve().parent.parent)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from handlers.game_router import handle_game_post
from proto.decoder import (
    decode_proto,
    get_bool,
    get_string,
    get_submessages,
    get_varint,
)
from proto.encoder import (
    encode_bool,
    encode_bytes,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)
from proto.room_models import (
    ECustomRoomSetting,
    EMatchmakingProto,
    EProtocolProto,
    ERoomType,
    GameMode,
    GroupMode,
)
from tcp_server import (
    EProtocolExtra,
    HANDSHAKE_ACK,
    dispatch_tcp_packet,
    push_collection_sync,
)
from tests.test_helpers import (
    MockRequestHandler,
    reset_test_account_state,
)


class TestCoreRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.aid = 10001
        self.handler = MockRequestHandler()
        self.handler.headers["X-Account-Id"] = str(self.aid)
        from core.player import player_manager
        player_manager.bind_session("127.0.0.1", self.aid)
        reset_test_account_state(
            account_id=self.aid,
            diamonds=50000,
            gold=500000,
        )

    def test_login_flow_endpoints(self) -> None:
        """Verify /MajorLogin, /GetPlayerPersonalShow, /GetProfileList succeed."""
        # 1. /MajorLogin
        login_req = encode_string(1, "test_token") + encode_string(2, "PushpaGG")
        handled = handle_game_post(self.handler, "/MajorLogin", "127.0.0.1", login_req)
        self.assertTrue(handled)
        self.assertGreater(len(self.handler.proto_calls), 0)
        self.assertIn(self.handler.proto_calls[-1][0], ("MajorLoginRes", "CSMajorLoginRes"))

        # 2. /GetPlayerPersonalShow
        show_req = encode_uint64(1, self.aid)
        handled = handle_game_post(self.handler, "/GetPlayerPersonalShow", "127.0.0.1", show_req)
        self.assertTrue(handled)
        self.assertIn(self.handler.proto_calls[-1][0], ("AccountPersonalShowInfo", "CSGetPlayerPersonalShowRes"))

        # 3. /GetProfiles
        handled = handle_game_post(self.handler, "/GetProfiles", "127.0.0.1", b"")
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "CSGetProfileListRes")

    def test_lobby_tcp_handshake_and_heartbeat(self) -> None:
        """Verify binary TCP connect handshake and heartbeat dispatching."""
        # Handshake: client sends [cmd=1][flag=0][4B len][token], server responds b"\x02"
        self.assertEqual(HANDSHAKE_ACK, b"\x02")

        # Heartbeat packet dispatch (EProtocolExtra.HEARTBEAT = 2)
        resp_cmd, ret_code, payload = dispatch_tcp_packet(
            protocol=EProtocolExtra.HEARTBEAT,
            sub_cmd=0,
            data=b"",
            account_id=self.aid,
        )
        self.assertEqual(ret_code, 0)
        self.assertEqual(resp_cmd, 0)

    def test_profile_sync_regression(self) -> None:
        """Verify modifying nickname, choosing banner and head pic update player profile."""
        import time
        # 1. Modify Nickname
        new_nick = f"Pushpa_{int(time.time())}"
        nick_req = encode_string(1, new_nick)
        handled = handle_game_post(self.handler, "/MajorModifyNickname", "127.0.0.1", nick_req)
        self.assertTrue(handled)
        prof = state.get_profile(self.aid)
        self.assertEqual(prof["nickname"], new_nick)

        # 2. Choose Banner
        banner_req = encode_uint32(1, 901000005)
        handled = handle_game_post(self.handler, "/ChooseBanner", "127.0.0.1", banner_req)
        self.assertTrue(handled)
        prof = state.get_profile(self.aid)
        self.assertEqual(prof["banner_id"], 901000005)

        # 3. Choose Head Pic
        head_req = encode_uint32(1, 902000010)
        handled = handle_game_post(self.handler, "/ChooseHeadPic", "127.0.0.1", head_req)
        self.assertTrue(handled)
        prof = state.get_profile(self.aid)
        self.assertEqual(prof["head_pic"], 902000010)

    def test_character_wardrobe_and_skill_equipment(self) -> None:
        """Verify equipping clothes and skills updates character profile and pushes sync."""
        avatar_id = 102000005  # Hayato
        select_req = encode_uint32(1, avatar_id)
        handled = handle_game_post(self.handler, "/SelectProfile", "127.0.0.1", select_req)
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "CSSelectProfileRes")

        # Equip clothes
        test_clothes = [203000056, 211000091, 204000043, 205000026]
        req_clothes = encode_uint32(1, avatar_id)
        for cid in test_clothes:
            req_clothes += encode_uint32(2, cid)
        handled = handle_game_post(self.handler, "/ChangeClothes", "127.0.0.1", req_clothes)
        self.assertTrue(handled)

        # Equip skill slot
        req_skill = (
            encode_uint32(1, avatar_id)
            + encode_uint32(2, 0)      # slot_id
            + encode_uint32(3, 1006)   # skill_id
        )
        handled = handle_game_post(self.handler, "/EquipSkill", "127.0.0.1", req_skill)
        self.assertTrue(handled)

        # Push collection sync to TCP sessions (must succeed without error)
        sent = push_collection_sync(self.aid)
        self.assertGreaterEqual(sent, 0)

    def test_custom_room_and_matchmaking_handoff(self) -> None:
        """Verify custom room creation and matchmaking protocol commands."""
        with state._lock:
            state._rooms.clear()

        # 1. Query empty room list
        handled = handle_game_post(self.handler, "/GetRoomList", "127.0.0.1", b"")
        self.assertTrue(handled)
        self.assertEqual(self.handler.proto_calls[-1][0], "GetAllRoomsRes")

        # 2. Create room
        create_req = (
            encode_uint32(1, 2)
            + encode_uint32(2, GameMode.CS)
            + encode_uint32(3, GroupMode.QUAD)
            + encode_string(4, "QA Test Scrims")
            + encode_string(5, "9999")
            + encode_uint32(6, 2)
            + encode_uint32(7, 4)
            + encode_bool(8, True)
            + encode_uint32(9, ERoomType.LEAGUE_NORMAL)
            + encode_uint32(14, ECustomRoomSetting.UNLIMITED_AMMO)
        )
        handled = handle_game_post(self.handler, "/CreateRoom", "127.0.0.1", create_req)
        self.assertTrue(handled)
        ri = decode_proto(self.handler.proto_calls[-1][1])
        self.assertEqual(get_string(ri, 2), "QA Test Scrims")
        self.assertIn(get_varint(ri, 3), (self.aid, 1000000102, 1000000107))

        # 3. Matchmaking TCP protocol command (GAMEOPENINGINFO = 7)
        resp_cmd, ret_code, data = dispatch_tcp_packet(
            protocol=EProtocolProto.MATCHMAKING,
            sub_cmd=EMatchmakingProto.GAMEOPENINGINFO,
            data=b"",
            account_id=self.aid,
        )
        self.assertEqual(ret_code, 0)
        self.assertGreater(len(data), 0, "GameOpeningInfoRes must return opening modes")


if __name__ == "__main__":
    unittest.main()
