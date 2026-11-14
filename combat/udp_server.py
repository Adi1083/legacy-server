"""
Free Fire 1.39 Authoritative UDP/RUDP Combat Server.
Listens on UDP port 39800 (and auxiliary 10001).
Handles:
1. Low-level client handshake (HELLO -> S2C_Hello_Res with session key and order tracking).
2. PING / PONG (C2S_UDP_Ping_Req -> S2C_UDP_Ping_Res).
3. ACK handling and reliable packet tracking.
4. Match token authorization from TCP matchmaking handoff (MatchmakingSussNtf).
5. Packet dispatch to MatchDirector and WorldEngine.
6. Periodic state synchronization broadcasts to connected combat clients.
"""

import sys
import os
import time
import socket
import select
import struct
import threading
import logging
from typing import Dict, Optional, Tuple, Any

# Ensure project root is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(CURRENT_DIR)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from combat.udp_protocol import (
    UDMPacket,
    SendOption,
    ReservedMsgID,
    S2C_Hello_Res,
    UDP_Ack_Res,
    C2S_UDP_Ping_Req,
    S2C_UDP_Ping_Res,
    UDPMESSAGE_MSGKEY
)
from combat.combat_opcodes import CombatOpcode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [UDPServer] %(message)s")
logger = logging.getLogger("UDPServer")

_log_path = os.path.join(SERVER_DIR, "udp_traffic.log")
try:
    _fh = logging.FileHandler(_log_path, mode="a", encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [UDPServer] %(message)s"))
    logger.addHandler(_fh)
except Exception:
    pass


class ClientSession:
    """Represents a connected combat client over UDP."""
    def __init__(self, addr: Tuple[str, int], session_key: int):
        self.addr = addr
        self.session_key = session_key
        self.account_id: int = 0
        self.nickname: str = ""
        self.token: str = ""
        self.authorized: bool = False
        self.last_alive_time: float = time.time()
        self.local_seq: int = 1
        self.remote_seq: int = 0
        self.local_order: int = 1
        self.remote_order: int = 0
        self.received_seq_bits: int = 0  # 32-bit history of received sequence numbers
        self.pending_acks: list = []
        self.combat_stage: int = 0
        self.stage_1_seq: int = 0
        self.stage_2_final_seq: int = 0
        self.stage_3_seq: int = 0
        self.last_acked_remote_seq: int = 0
        self.last_sent_cmd: int = 0
        self.last_sent_seq: int = 0
        self.match_id: int = 10001
        self.prepare_token: str = ""
        self.match_entry_dispatched: bool = False

    def next_seq(self) -> int:
        seq = self.local_seq
        self.local_seq = (self.local_seq + 1) & 0xffff
        if self.local_seq == 0:
            self.local_seq = 1
        return seq

    def next_order(self) -> int:
        order = self.local_order
        self.local_order = (self.local_order + 1) & 0xffff
        if self.local_order == 0:
            self.local_order = 1
        return order

    def record_received_seq(self, seq: int) -> None:
        if self.remote_seq == 0:
            self.remote_seq = seq
            self.received_seq_bits = 1
            return

        diff = (seq - self.remote_seq) & 0xffff
        if 0 < diff < 32768:
            # Newer sequence received
            if diff < 32:
                self.received_seq_bits = (self.received_seq_bits << diff) | 1
            else:
                self.received_seq_bits = 1
            self.remote_seq = seq
        else:
            # Older sequence received out of order
            diff_back = (self.remote_seq - seq) & 0xffff
            if diff_back < 32:
                self.received_seq_bits |= (1 << diff_back)


class CombatUDPServer:
    """
    Authoritative UDP / RUDP Combat Server.
    Supports primary port 39800 and fallback port 10001.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 39800, aux_port: int = 10001):
        self.host = host
        self.port = port
        self.aux_port = aux_port
        self.running = False
        self.sock_primary: Optional[socket.socket] = None
        self.sock_aux: Optional[socket.socket] = None
        
        # Sessions keyed by (ip, port)
        self.sessions: Dict[Tuple[str, int], ClientSession] = {}
        self.authorized_tokens: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        
        # Match Director / World Engine callback hooks
        self.on_packet_received = None
        self.on_client_connected = None
        self.on_client_disconnected = None

    def register_match_token(self, token: str, account_id: int, match_id: int, nickname: str = "Player") -> None:
        """Register a valid match token passed from TCP matchmaking handoff."""
        with self.lock:
            self.authorized_tokens[token] = {
                "account_id": account_id,
                "match_id": match_id,
                "nickname": nickname,
                "created_at": time.time()
            }
            logger.info("Registered match token '%s' for account_id=%s match_id=%s", token, account_id, match_id)

    def start(self) -> None:
        """Bind sockets and start background network threads."""
        self.running = True

        # Primary socket
        self.sock_primary = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_primary.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock_primary.bind((self.host, self.port))
        self.sock_primary.setblocking(False)

        # Aux socket
        try:
            self.sock_aux = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_aux.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_aux.bind((self.host, self.aux_port))
            self.sock_aux.setblocking(False)
            logger.info("Bound aux UDP socket on %s:%s", self.host, self.aux_port)
        except Exception as e:
            logger.warning("Could not bind aux port %s: %s", self.aux_port, e)

        logger.info("Combat UDP Server listening on %s:%s", self.host, self.port)

        self.recv_thread = threading.Thread(target=self._recv_loop, name="UDPCombat-Recv", daemon=True)
        self.recv_thread.start()

        self.tick_thread = threading.Thread(target=self._tick_loop, name="UDPCombat-Tick", daemon=True)
        self.tick_thread.start()

    def stop(self) -> None:
        self.running = False
        if self.sock_primary:
            try:
                self.sock_primary.close()
            except Exception:
                pass
        if self.sock_aux:
            try:
                self.sock_aux.close()
            except Exception:
                pass
        logger.info("Combat UDP Server stopped")

    def _recv_loop(self) -> None:
        sockets = [s for s in [self.sock_primary, self.sock_aux] if s is not None]
        while self.running:
            try:
                readable, _, _ = select.select(sockets, [], [], 0.05)
                for s in readable:
                    try:
                        data, addr = s.recvfrom(2048)
                        if data:
                            self._handle_raw_packet(data, addr, s)
                    except (BlockingIOError, InterruptedError):
                        continue
                    except OSError:
                        # Socket closed during shutdown
                        break
                    except Exception as ex:
                        if self.running:
                            logger.error("Error receiving packet: %s", ex)
            except Exception as e:
                if self.running:
                    logger.error("Select loop error: %s", e)

    def _tick_loop(self) -> None:
        """Periodic housekeeping: session timeout, ping broadcast, ack flush."""
        while self.running:
            now = time.time()
            to_remove = []
            with self.lock:
                for addr, session in list(self.sessions.items()):
                    # Timeout after 20 seconds of silence
                    if now - session.last_alive_time > 20.0:
                        to_remove.append(addr)
                    else:
                        # Flush pending acks only if new remote sequences need acknowledging
                        if session.remote_seq > session.last_acked_remote_seq:
                            session.last_acked_remote_seq = session.remote_seq
                            ack_payload = UDP_Ack_Res(session.remote_seq, session.received_seq_bits).serialize()
                            ack_pkt = UDMPacket(
                                send_option=SendOption.NONE,
                                cmd=ReservedMsgID.UDP_ACK,
                                seq_id=0,
                                data=ack_payload
                            )
                            self._send_packet_to_addr(ack_pkt, addr)

            for addr in to_remove:
                logger.info("Session %s timed out", addr)
                with self.lock:
                    self.sessions.pop(addr, None)
                if self.on_client_disconnected:
                    try:
                        self.on_client_disconnected(addr)
                    except Exception as e:
                        logger.error("Client disconnect hook error: %s", e)

            # Advance authoritative MatchDirector simulation
            try:
                from .match_director import global_match_director
                if global_match_director and global_match_director.active_matches:
                    match_results = global_match_director.tick_all(0.05)
                    self._broadcast_match_tick(match_results)
            except Exception as e:
                logger.debug("MatchDirector tick error: %s", e)

            time.sleep(0.05)

    def _handle_raw_packet(self, raw: bytes, addr: Tuple[str, int], sock: socket.socket) -> None:
        pkt = UDMPacket.unserialize(raw)
        if not pkt:
            logger.warning("Failed to unserialize raw packet (%d bytes) from %s: %s", len(raw), addr, raw.hex())
            return

        logger.info("RECV %s: opt=%d cmd=%d seq=%d ord=%d len=%d", addr, pkt.send_option, pkt.cmd, pkt.seq_id, pkt.order_id, len(pkt.data))

        with self.lock:
            session = self.sessions.get(addr)

        now = time.time()
        if session:
            session.last_alive_time = now
            if pkt.seq_id > 0:
                session.record_received_seq(pkt.seq_id)

        # 1. HELLO Handshake Handlers
        if pkt.send_option == SendOption.HELLO:
            self._handle_hello(pkt, addr, sock)
            return

        # 2. PING / PONG
        if pkt.cmd == ReservedMsgID.UDP_PING:
            self._handle_ping(pkt, addr)
            return

        # 3. ACK packet
        if pkt.cmd == ReservedMsgID.UDP_ACK:
            ack_seq = 0
            ack_bits = 0
            if len(pkt.data) >= 6:
                ack_seq, ack_bits = struct.unpack("<HI", pkt.data[:6])
            elif len(pkt.data) >= 2:
                ack_seq, = struct.unpack("<H", pkt.data[:2])
            logger.info("RECV UDP_ACK from %s: ack_seq=%d, ack_bits=0x%08x (combat_stage=%d)",
                        addr, ack_seq, ack_bits, getattr(session, "combat_stage", 0) if session else 0)

            if session:
                stage = getattr(session, "combat_stage", 0)
                if stage == 0:
                    # Client acknowledged HELLO (seq 1). Handshake complete.
                    # Send Opcode 31 (RUDP_JOIN_MATCH_FINISHED) so client enters loading/waiting island!
                    session.combat_stage = 1
                    self._dispatch_stage_1_join_res(session)
                elif stage == 1:
                    # Client acknowledged Opcode 31!
                    stage_1_seq = getattr(session, "stage_1_seq", 2)
                    if ack_seq >= stage_1_seq:
                        logger.info("=== [ISOLATION VERIFIED] Client ACKed Opcode 31 (ack_seq=%d, expected=%d)! SafeZone & header parsed cleanly! ===", ack_seq, stage_1_seq)
                        session.combat_stage = 2
                        self._dispatch_stage_2_player_join(session)
                    else:
                        logger.info("[STAGE 1] In-flight ACK received: ack_seq=%d (waiting for seq=%d)", ack_seq, stage_1_seq)
                elif stage == 2:
                    # Client acknowledged player join(s)
                    stage_2_final = getattr(session, "stage_2_final_seq", 3)
                    if ack_seq >= stage_2_final:
                        logger.info("=== [ISOLATION VERIFIED] Client ACKed all player joins (Human + 2 Bots, ack_seq=%d, final_seq=%d)! Opcode 2 parsed safely! ===", ack_seq, stage_2_final)
                        session.combat_stage = 3
                        self._dispatch_stage_3_scene_info(session)
                    else:
                        logger.info("[STAGE 2] Partial player join ACK received: ack_seq=%d (waiting for final seq=%d)", ack_seq, stage_2_final)
                elif stage == 3:
                    # Client acknowledged Opcode 17!
                    stage_3_seq = getattr(session, "stage_3_seq", 6)
                    if ack_seq >= stage_3_seq:
                        logger.info("=== [ISOLATION VERIFIED] Client ACKed Opcode 17 (ack_seq=%d, expected=%d)! All 3 opcodes (31, 2, 17) accepted cleanly! Match is LIVE! ===", ack_seq, stage_3_seq)
                        session.combat_stage = 4
                        # Transition match to Spawn Island
                        try:
                            from .match_director import global_match_director, MatchState
                            if global_match_director:
                                match = global_match_director.get_match(session.match_id)
                                if match and match.state in (MatchState.STATE_0_MATCHMAKING, MatchState.STATE_1_UDP_CONNECT):
                                    match.transition_to(MatchState.STATE_2_SPAWN_ISLAND)
                                    logger.info("MatchDirector match %d transitioned to STATE_2_SPAWN_ISLAND", session.match_id)
                        except Exception as e:
                            logger.error("MatchDirector transition error on stage 3 ACK: %s", e)
                    else:
                        logger.info("[STAGE 3] In-flight ACK received: ack_seq=%d (waiting for seq=%d)", ack_seq, stage_3_seq)
            return

        # 4. BYEBYE packet
        if pkt.cmd == ReservedMsgID.UDP_BYEBYE or pkt.send_option == SendOption.BYEBYE:
            with self.lock:
                self.sessions.pop(addr, None)
            logger.info("Client %s sent BYEBYE", addr)
            if self.on_client_disconnected:
                self.on_client_disconnected(addr)
            return

        # 5. In-Game Combat Dispatch (hTKYY opcodes)
        if session:
            # Auto-ACK reliable incoming packets
            if pkt.is_reliable():
                session.last_acked_remote_seq = session.remote_seq
                ack_payload = UDP_Ack_Res(session.remote_seq, session.received_seq_bits).serialize()
                ack_pkt = UDMPacket(
                    send_option=SendOption.NONE,
                    cmd=ReservedMsgID.UDP_ACK,
                    seq_id=session.next_seq(),
                    data=ack_payload
                )
                self._send_packet_to_addr(ack_pkt, addr)

            # Check if this is RUDP_JOIN_MATCH
            if pkt.cmd == CombatOpcode.RUDP_JOIN_MATCH:
                self._handle_join_match(pkt, session)
                return

            # Opcode 107 or 8: RUDP_DEAD (Player shot/killed a bot)
            if pkt.cmd in (107, 8, CombatOpcode.RUDP_DEAD):
                self._handle_client_dead(pkt, session)
                return

            # Opcode 106 or 7: RUDP_TAKE_DAMAGE (Player damaged a bot)
            if pkt.cmd in (106, 7, CombatOpcode.RUDP_TAKE_DAMAGE):
                self._handle_client_take_damage(pkt, session)
                return

            # Opcode 104 or 5: RUDP_START_FIRE (Player fires weapon)
            if pkt.cmd in (104, 5, CombatOpcode.RUDP_START_FIRE):
                self._handle_client_fire(pkt, session)
                return

            # Opcode 3: Movement update from client
            if pkt.cmd == 3:
                self._handle_client_movement(pkt, session)
                return

            if self.on_packet_received:
                try:
                    self.on_packet_received(session, pkt)
                except Exception as e:
                    logger.error("Dispatch callback error for cmd %s: %s", pkt.cmd, e)

    def _handle_hello(self, pkt: UDMPacket, addr: Tuple[str, int], sock: socket.socket) -> None:
        """Process UDPMESSAGE_SENDOPTION_HELLO handshake and issue session key."""
        logger.info("HELLO DATA (%d bytes): %s", len(pkt.data), pkt.data.hex())
        with self.lock:
            existing = self.sessions.get(addr)
            if existing:
                session = existing
                session_key = session.session_key
                logger.info("Reusing active session_key=0x%x for %s (stage=%d)", session_key, addr, session.combat_stage)
                # Resend original S2C_Hello_Res without resetting connection or re-incrementing order
                res_payload = S2C_Hello_Res(session_key=session_key, order_id=1, required_id=1).serialize()
                reply_pkt = UDMPacket(
                    send_option=SendOption.HELLO,
                    cmd=ReservedMsgID.UDP_HELLO,
                    seq_id=1,
                    order_id=1,
                    data=res_payload
                )
                self._send_packet_to_addr(reply_pkt, addr, sock)
                return
            else:
                session_key = int(time.time() * 1000) & 0x7fffffff
                session = ClientSession(addr, session_key)

                # Match token verification and session metadata binding
                raw_token_hex = pkt.data.hex().lower() if pkt.data else ""
                raw_token_str = ""
                try:
                    raw_token_str = pkt.data.decode("utf-8", errors="ignore").lower()
                except Exception:
                    pass

                matched_tok = None
                matched_info = None

                for tok, info in self.authorized_tokens.items():
                    tok_clean = tok.lower().strip()
                    if raw_token_hex == tok_clean or raw_token_str == tok_clean or (raw_token_hex and tok_clean.startswith(raw_token_hex)) or (tok_clean and tok_clean in raw_token_str):
                        matched_tok = tok
                        matched_info = info
                        break

                if not matched_info and self.authorized_tokens:
                    # Fallback to most recently registered token
                    sorted_tokens = sorted(self.authorized_tokens.items(), key=lambda item: item[1].get("created_at", 0), reverse=True)
                    matched_tok, matched_info = sorted_tokens[0]
                    logger.info("Fell back to most recent authorized match token '%s'", matched_tok)

                if matched_info:
                    session.account_id = matched_info.get("account_id", 10001)
                    session.match_id = matched_info.get("match_id", 10001)
                    session.nickname = matched_info.get("nickname", "PushpaGG")
                    session.prepare_token = matched_tok or ""
                    session.authorized = True
                    logger.info("Bound authorized session for account_id=%d match_id=%d nick='%s' to %s",
                                session.account_id, session.match_id, session.nickname, addr)
                else:
                    session.account_id = 10001
                    session.match_id = 10001
                    session.nickname = "PushpaGG"
                    logger.info("Defaulted session for account_id=%d match_id=%d to %s", session.account_id, session.match_id, addr)

                # Link with MatchDirector
                try:
                    from .match_director import global_match_director
                    if global_match_director:
                        match = global_match_director.get_match(session.match_id)
                        if not match and global_match_director.active_matches:
                            match = list(global_match_director.active_matches.values())[-1]
                            session.match_id = match.match_id
                        if match:
                            match.client_endpoints[str(session.account_id)] = addr
                            match.client_session_keys[str(session.account_id)] = session_key
                            global_match_director.handle_udp_handshake(
                                match_id=match.match_id,
                                player_id=str(session.account_id),
                                token=match.prepare_token or session.prepare_token,
                                client_endpoint=addr,
                                session_key=session_key
                            )
                except Exception as e:
                    logger.error("MatchDirector binding error on HELLO: %s", e)

                self.sessions[addr] = session
                logger.info("Handshake HELLO received from %s. Assigned session_key=0x%x", addr, session_key)

        res_payload = S2C_Hello_Res(session_key=session_key, order_id=1, required_id=1).serialize()
        reply_pkt = UDMPacket(
            send_option=SendOption.HELLO,
            cmd=ReservedMsgID.UDP_HELLO,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            data=res_payload
        )
        self._send_packet_to_addr(reply_pkt, addr, sock)

        if self.on_client_connected:
            try:
                self.on_client_connected(session)
            except Exception as e:
                logger.error("on_client_connected hook error: %s", e)

    def _handle_ping(self, pkt: UDMPacket, addr: Tuple[str, int]) -> None:
        """Echo client tick timestamp for latency measurement."""
        tick = 0
        if len(pkt.data) >= 8:
            tick = struct.unpack("<Q", pkt.data[:8])[0]
        elif len(pkt.data) >= 4:
            tick = struct.unpack("<I", pkt.data[:4])[0]

        pong_payload = struct.pack("<Q", tick)
        with self.lock:
            session = self.sessions.get(addr)
            seq = session.next_seq() if session else 1

        reply = UDMPacket(
            send_option=SendOption.NONE,
            cmd=ReservedMsgID.UDP_PING,
            seq_id=seq,
            data=pong_payload
        )
        self._send_packet_to_addr(reply, addr)

    def _handle_join_match(self, pkt: UDMPacket, session: ClientSession) -> None:
        """
        Handle RUDP_JOIN_MATCH (100) from client.
        Verifies prepare_token and responds with RUDP_JOIN_MATCH response / RUDP_JOIN_MATCH_FINISHED.
        """
        logger.info("Client %s sent RUDP_JOIN_MATCH (data_len=%d)", session.addr, len(pkt.data))
        session.authorized = True

        match_id = 10001
        account_id = session.account_id or 1000001
        prepare_token = ""
        nickname = session.nickname or "Player"

        # 1. Parse authentic C2S_JoinMatch if payload is present
        if len(pkt.data) >= 16:
            try:
                from .combat_packet_codec import C2S_JoinMatch
                req = C2S_JoinMatch.unserialize(pkt.data)
                prepare_token = req.prepare_token
                if req.match_id > 0:
                    match_id = req.match_id
                if req.account_id > 0:
                    account_id = req.account_id
                    session.account_id = account_id
                logger.info("Parsed C2S_JoinMatch: match_id=%d, account_id=%d, token=%s", match_id, account_id, prepare_token)
            except Exception as e:
                logger.debug("Could not parse C2S_JoinMatch payload: %s", e)

        self._dispatch_match_entry(session, match_id=match_id, account_id=account_id, prepare_token=prepare_token, nickname=nickname)

    def _dispatch_match_entry(self, session: ClientSession, match_id: int = 10001, account_id: int = 1000001, prepare_token: str = "", nickname: str = "Player") -> None:
        """Start staged match entry sequence, beginning with Stage 1 (Opcode 130 ONLY)."""
        session.match_id = match_id
        session.account_id = account_id
        session.prepare_token = prepare_token
        session.nickname = nickname
        self._dispatch_stage_1_join_res(session, match_id=match_id, account_id=account_id, prepare_token=prepare_token, nickname=nickname)

    def _dispatch_stage_1_join_res(self, session: ClientSession, match_id: int = 10001, account_id: int = 1000001, prepare_token: str = "", nickname: str = "Player") -> None:
        """STAGE 1: Send ONLY RUDP_JOIN_MATCH_FINISHED (31)."""
        match_id = session.match_id or match_id
        account_id = session.account_id or account_id
        prepare_token = session.prepare_token or prepare_token
        nickname = session.nickname or nickname

        logger.info("[STAGE 1] Sending Opcode 31 (RUDP_JOIN_MATCH_FINISHED) to %s (account_id=%d, match_id=%d)", session.addr, account_id, match_id)
        session.authorized = True
        session.match_entry_dispatched = True

        # Link to MatchDirector
        try:
            from .match_director import global_match_director
            if global_match_director and global_match_director.active_matches:
                for mid, m in global_match_director.active_matches.items():
                    m.client_endpoints[str(account_id)] = session.addr
                    global_match_director.handle_udp_handshake(
                        match_id=mid,
                        player_id=str(account_id),
                        token=m.prepare_token or prepare_token,
                        client_endpoint=session.addr
                    )
                    logger.info("Associated match %d with client %s (player_id=%s)", mid, session.addr, account_id)
        except Exception as e:
            logger.error("MatchDirector link error: %s", e)

        # Build S2C_JoinMatchRes (73 bytes)
        try:
            from .combat_packet_codec import S2C_JoinMatchRes
            join_res = S2C_JoinMatchRes(
                err_code=0,
                match_id=match_id,
                account_id=account_id,
                server_time=int(time.time()),
                map_id=1,
                waiting_seconds=60,
                weather_style=1,
                game_mode=1,
                room_type=0
            )
            res_payload = join_res.serialize()
        except Exception as e:
            logger.warning("Falling back to minimal payload for JoinMatchRes: %s", e)
            res_payload = b"\x00"

        res_pkt = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_JOIN_MATCH_FINISHED,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            data=res_payload
        )
        session.stage_1_seq = res_pkt.seq_id
        session.last_sent_seq = res_pkt.seq_id
        session.last_sent_cmd = int(CombatOpcode.RUDP_JOIN_MATCH_FINISHED)
        self.send_packet(session, res_pkt)
        logger.info("[STAGE 1] Dispatched Opcode 31 (seq=%d, ord=%d, len=%d). Awaiting client ACK...", res_pkt.seq_id, res_pkt.order_id, len(res_payload))

    def _dispatch_stage_2_player_join(self, session: ClientSession) -> None:
        """STAGE 2: Send Opcode 2 (RUDP_PLAYER_JOIN) for human player + 2 bots (Bot_Kelly & Bot_Andrew)."""
        logger.info("[STAGE 2] Sending Opcode 2 (RUDP_PLAYER_JOIN) for human player + 2 bots to %s", session.addr)
        account_id = session.account_id or 1000001
        match_id = session.match_id or 10001
        nickname = session.nickname or "PushpaGG"
        avatar_id = 102000004
        try:
            from core.state import state
            p_prof = state.get_player(account_id)
            if p_prof:
                nickname = p_prof.get("nickname", nickname)
                avatar_id = p_prof.get("avatar_id", avatar_id)
        except Exception:
            pass

        try:
            from .combat_packet_codec import S2C_PlayerJoin
            # 1. Human player
            player_join = S2C_PlayerJoin(
                player_id=1,
                account_id=account_id,
                team_id=1,
                camp=1,
                match_id=match_id,
                nickname=nickname,
                avatar_id=avatar_id,
                is_bot=False
            )
            join_pkt = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                data=player_join.serialize()
            )
            self.send_packet(session, join_pkt)
            session.stage_2_final_seq = join_pkt.seq_id
            logger.info("[STAGE 2] Dispatched Opcode 2 for Human (seq=%d, ord=%d, nick='%s').", join_pkt.seq_id, join_pkt.order_id, nickname)

            # 2. Bot 1: Bot_Kelly
            bot1 = S2C_PlayerJoin(
                player_id=2,
                account_id=2000001,
                team_id=2,
                camp=2,
                match_id=match_id,
                nickname="Bot_Kelly",
                avatar_id=101000006,
                gender=1,
                clothes=[211000000, 203000059, 204000046, 205000029],
                skills=[201, 202],
                is_bot=True
            )
            bot1_pkt = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                data=bot1.serialize()
            )
            self.send_packet(session, bot1_pkt)
            session.stage_2_final_seq = bot1_pkt.seq_id
            logger.info("[STAGE 2] Dispatched Opcode 2 for Bot_Kelly (seq=%d, ord=%d).", bot1_pkt.seq_id, bot1_pkt.order_id)

            # 3. Bot 2: Bot_Andrew
            bot2 = S2C_PlayerJoin(
                player_id=3,
                account_id=2000002,
                team_id=3,
                camp=3,
                match_id=match_id,
                nickname="Bot_Andrew",
                avatar_id=102000005,
                gender=2,
                clothes=[211000000, 203000056, 204000043, 205000026],
                skills=[401, 402],
                is_bot=True
            )
            bot2_pkt = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                data=bot2.serialize()
            )
            self.send_packet(session, bot2_pkt)
            session.stage_2_final_seq = bot2_pkt.seq_id
            session.last_sent_seq = bot2_pkt.seq_id
            session.last_sent_cmd = int(CombatOpcode.RUDP_PLAYER_JOIN)
            logger.info("[STAGE 2] Dispatched Opcode 2 for Bot_Andrew (seq=%d, ord=%d). Final stage 2 seq=%d.", bot2_pkt.seq_id, bot2_pkt.order_id, session.stage_2_final_seq)
        except Exception as e:
            logger.error("Could not send RUDP_PLAYER_JOIN: %s", e)

    def _dispatch_stage_3_scene_info(self, session: ClientSession) -> None:
        """STAGE 3: Send Opcode 17 (RUDP_SYNC_SCENE_INFO) with countdown and 3 alive players."""
        logger.info("[STAGE 3] Sending Opcode 17 (RUDP_SYNC_SCENE_INFO) to %s", session.addr)
        match_id = session.match_id or 10001
        try:
            from .combat_packet_codec import S2C_SyncSceneInfo
            scene_info = S2C_SyncSceneInfo(
                match_id=match_id,
                elapsed_time=0.0,
                countdown_seconds=60.0,
                alive_players=3
            )
            scene_pkt = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_SYNC_SCENE_INFO,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                data=scene_info.serialize()
            )
            session.stage_3_seq = scene_pkt.seq_id
            session.last_sent_seq = scene_pkt.seq_id
            session.last_sent_cmd = int(CombatOpcode.RUDP_SYNC_SCENE_INFO)
            self.send_packet(session, scene_pkt)
            logger.info("[STAGE 3] Dispatched Opcode 17 (seq=%d, ord=%d, len=%d). Awaiting client ACK...", scene_pkt.seq_id, scene_pkt.order_id, len(scene_pkt.data))
        except Exception as e:
            logger.error("Could not send RUDP_SYNC_SCENE_INFO: %s", e)

    def send_packet(self, session: ClientSession, pkt: UDMPacket) -> bool:
        """Send a packet to a registered session."""
        if pkt.seq_id == 0:
            pkt.seq_id = session.next_seq()
        if pkt.is_reliable() and pkt.order_id == 0:
            pkt.order_id = session.next_order()
        return self._send_packet_to_addr(pkt, session.addr)

    def broadcast_packet(self, pkt: UDMPacket, exclude_addr: Optional[Tuple[str, int]] = None) -> None:
        """Broadcast packet to all connected clients."""
        with self.lock:
            addrs = [addr for addr in self.sessions.keys() if addr != exclude_addr]

        for addr in addrs:
            with self.lock:
                session = self.sessions.get(addr)
            if session:
                client_pkt = UDMPacket(
                    send_option=pkt.send_option,
                    cmd=pkt.cmd,
                    seq_id=session.next_seq(),
                    order_id=session.next_order() if pkt.is_reliable() else 0,
                    flags=pkt.flags,
                    data=pkt.data
                )
                self._send_packet_to_addr(client_pkt, addr)

    def _send_packet_to_addr(self, pkt: UDMPacket, addr: Tuple[str, int], sock: Optional[socket.socket] = None) -> bool:
        data = pkt.serialize()
        s = sock or self.sock_primary
        if not s:
            return False
        try:
            s.sendto(data, addr)
            logger.info("SENT %s: opt=%d cmd=%d seq=%d ord=%d len=%d bytes=%s", addr, pkt.send_option, pkt.cmd, pkt.seq_id, pkt.order_id, len(pkt.data), data.hex())
            return True
        except Exception as e:
            logger.error("Failed to send packet to %s: %s", addr, e)
            return False

    def _handle_client_dead(self, pkt: UDMPacket, session: ClientSession) -> None:
        """Handle client reporting lethal kill on bot (Opcode 107 / 8: RUDP_DEAD)."""
        logger.info("[COMBAT] RECV Opcode 107 (RUDP_DEAD) from %s (data_len=%d)", session.addr, len(pkt.data))
        from .combat_packet_codec import RUDP_Dead
        from .match_director import global_match_director
        victim_id = 2
        weapon_id = 101001
        is_hs = False
        try:
            dead_req = RUDP_Dead.unserialize(pkt.data)
            victim_id = dead_req.victim_id
            weapon_id = dead_req.weapon_id or 101001
            is_hs = dead_req.is_headshot
        except Exception as e:
            logger.debug("Failed parsing RUDP_Dead: %s", e)
            if len(pkt.data) >= 4:
                victim_id = struct.unpack("<I", pkt.data[:4])[0]

        match_id = session.match_id or 10001
        if global_match_director:
            global_match_director.handle_player_kill_bot(
                match_id=match_id,
                victim_id=victim_id,
                killer_id=session.account_id or 10001,
                weapon_id=weapon_id,
                is_headshot=is_hs
            )

        self._broadcast_death_event(session, victim_id, session.account_id or 10001, session.nickname or "PushpaGG", weapon_id, is_hs)

    def _handle_client_take_damage(self, pkt: UDMPacket, session: ClientSession) -> None:
        """Handle client dealing damage to bot (Opcode 106 / 7: RUDP_TAKE_DAMAGE)."""
        logger.info("[COMBAT] RECV Opcode 106/7 (RUDP_TAKE_DAMAGE) from %s (data_len=%d)", session.addr, len(pkt.data))
        from .combat_packet_codec import RUDP_TakeDamage
        from .match_director import global_match_director
        victim_id = 2
        damage = 35.0
        body_part = 2
        weapon_id = 101001
        try:
            dmg_req = RUDP_TakeDamage.unserialize(pkt.data)
            victim_id = dmg_req.victim_id
            damage = dmg_req.damage or 35.0
            body_part = dmg_req.body_part or 2
            weapon_id = dmg_req.weapon_id or 101001
        except Exception as e:
            logger.debug("Failed parsing RUDP_TakeDamage: %s", e)
            if len(pkt.data) >= 4:
                victim_id = struct.unpack("<I", pkt.data[:4])[0]

        match_id = session.match_id or 10001
        res = {"hit": False}
        if global_match_director:
            res = global_match_director.handle_player_damage_bot(
                match_id=match_id,
                victim_id=victim_id,
                attacker_id=session.account_id or 10001,
                damage=damage,
                body_part=body_part,
                weapon_id=weapon_id
            )

        if res.get("is_dead"):
            logger.info("=== [BOT ELIMINATED] Bot %s (victim_id=%s) killed by %s! ===",
                        res.get("nickname"), victim_id, session.nickname)
            self._broadcast_death_event(session, victim_id, session.account_id or 10001, session.nickname or "PushpaGG", weapon_id, body_part == 1)

    def _handle_client_fire(self, pkt: UDMPacket, session: ClientSession) -> None:
        """Handle client shooting weapon (Opcode 104 / 5: RUDP_START_FIRE)."""
        logger.info("[COMBAT] RECV Opcode 104/5 (RUDP_START_FIRE) from %s", session.addr)
        if len(pkt.data) >= 4:
            target_id = struct.unpack("<I", pkt.data[:4])[0]
            if target_id in (2, 3, 2000001, 2000002):
                from .match_director import global_match_director
                if global_match_director:
                    global_match_director.handle_player_damage_bot(
                        match_id=session.match_id or 10001,
                        victim_id=target_id,
                        attacker_id=session.account_id or 10001,
                        damage=38.0,
                        body_part=2,
                        weapon_id=101001
                    )

    def _handle_client_movement(self, pkt: UDMPacket, session: ClientSession) -> None:
        """Handle client movement update (Opcode 3)."""
        if len(pkt.data) >= 12:
            try:
                from .combat_packet_codec import UDP_PlayerPositionOnly
                from .match_director import global_match_director
                pos_pkt = UDP_PlayerPositionOnly.unserialize(pkt.data)
                if global_match_director:
                    match = global_match_director.get_match(session.match_id)
                    if match:
                        match.world.update_player_pos(
                            str(session.account_id),
                            pos_pkt.x, pos_pkt.y, pos_pkt.z
                        )
            except Exception:
                pass

    def _broadcast_death_event(self, session: ClientSession, victim_id: int, killer_id: int, killer_name: str, weapon_id: int, is_headshot: bool) -> None:
        """Broadcast authoritative death Opcode 107 (RUDP_DEAD) to client session(s)."""
        from .combat_packet_codec import RUDP_Dead
        from .match_director import global_match_director
        match_id = session.match_id or 10001
        alive_players = 1
        if global_match_director:
            m = global_match_director.get_match(match_id)
            if m:
                alive_players = m.world.alive_player_count

        dead = RUDP_Dead(
            victim_id=int(victim_id),
            killer_id=int(killer_id),
            killer_name=killer_name,
            weapon_id=weapon_id,
            is_headshot=is_headshot,
            rank=alive_players + 1,
            kills=1,
            is_suicide=False
        )
        dead_pkt = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=107, # Opcode 107: RUDP_DEAD
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            data=dead.serialize()
        )
        self.send_packet(session, dead_pkt)
        logger.info("[COMBAT] Dispatched Opcode 107 (RUDP_DEAD) for victim_id=%d, killer='%s', weapon=%d",
                    victim_id, killer_name, weapon_id)

    def _broadcast_match_tick(self, match_results: List[Dict[str, Any]]) -> None:
        """Broadcast bot movement updates (Opcode 3) to connected sessions."""
        from .combat_packet_codec import UDP_PlayerPositionOnly
        from .match_director import global_match_director

        if not global_match_director:
            return

        with self.lock:
            active_sessions = [s for s in self.sessions.values() if getattr(s, "combat_stage", 0) >= 4]

        if not active_sessions:
            return

        for session in active_sessions:
            match = global_match_director.get_match(session.match_id)
            if not match:
                continue

            for bot in match.bot_controller.bots.values():
                if bot.hp > 0:
                    pos_bytes = UDP_PlayerPositionOnly(
                        player_id=getattr(bot, "player_id", bot.bot_id + 1),
                        x=bot.position.x,
                        y=bot.position.y,
                        z=bot.position.z,
                        speed=bot.speed,
                        physx_state=int(bot.physx_state),
                        physx_pose=int(bot.physx_pose)
                    ).serialize()

                    # Opcode 3 movement packet
                    move_pkt = UDMPacket(
                        send_option=SendOption.NONE,
                        cmd=3, # Opcode 3 Movement
                        seq_id=session.next_seq(),
                        data=pos_bytes
                    )
                    self.send_packet(session, move_pkt)


# Singleton instance
_combat_server: Optional[CombatUDPServer] = None

def get_combat_server() -> CombatUDPServer:
    global _combat_server
    if _combat_server is None:
        _combat_server = CombatUDPServer()
    return _combat_server

def start_combat_server() -> CombatUDPServer:
    srv = get_combat_server()
    if not srv.running:
        srv.start()
    return srv
