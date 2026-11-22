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

# Opcode 101 (RUDP_PLAYER_JOIN) makes this 1.39 client SIGSEGV inside its own
# message parser: message.<cls>.UnSerialize allocates a List<T> whose element
# class is null in this build, so the array store writes through null on
# UnityMain. Off by default so the match itself can run; set PLAYER_JOIN=1 to
# re-enable the player-entity burst and the stage-2 player dispatch.
PLAYER_JOIN_ENABLED = os.environ.get("PLAYER_JOIN", "0") == "1"
ISOLATED_OP101_TEST = os.environ.get("ISOLATED_OP101_TEST", "0") == "1"
STAGE_3_ENABLED = os.environ.get("STAGE_3", "0") == "1"
STAGE_4_ENABLED = os.environ.get("STAGE_4", "0") == "1"
import socket
import select
import struct
import threading
import logging
from typing import Dict, Optional, Tuple, Any, List

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
from core.state import DEFAULT_ACCOUNT_ID, generate_match_id

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
        self.local_order: int = 0  # Authentic Barbosa order ID counter starts at 0
        self.remote_order: int = 0
        self.received_seq_bits: int = 0  # 32-bit history of received sequence numbers
        self.pending_acks: list = []
        self.unacked_reliable_packets: Dict[int, Tuple[UDMPacket, float, int]] = {}  # seq -> (pkt, send_time, retries)
        self.combat_stage: int = 0
        self.stage_1_seq: int = -1
        self.stage_2_final_seq: int = -1
        self.stage_3_seq: int = -1
        self.last_acked_remote_seq: int = 0
        self.last_sent_cmd: int = 0
        self.last_sent_seq: int = 0
        self.match_id: int = 0
        self.prepare_token: str = ""
        self.match_entry_dispatched: bool = False
        # Scene-load synchronization: tracks when Opcode 130 was ACK'd (= client started LoadSceneAsync)
        self.scene_load_start_time: float = 0.0
        # Set True once the server has confirmed the scene is loaded (via C2S_SCENE_LOADED or adaptive timeout)
        self.scene_loaded_confirmed: bool = False
        self.stage_2_scheduled: bool = False
        # Wall-clock time of the 12-step match-entry burst; used to re-dispatch the
        # entity/player-join stage once the client has finished loading the match scene.
        self.match_entry_time: float = 0.0
        # Probe: lightweight pings sent during scene load to detect when client starts responding from loaded scene
        self.scene_probe_count: int = 0
        self.scene_probe_start_time: float = 0.0

    def next_seq(self) -> int:
        seq = self.local_seq
        self.local_seq = (self.local_seq + 1) & 0xffff
        if self.local_seq == 0:
            self.local_seq = 1
        return seq

    def next_order(self) -> int:
        order = self.local_order
        self.local_order = (self.local_order + 1) & 0xffff
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

    def acknowledge_reliable_packets(self, ack_seq: int, ack_bits: int = 0) -> None:
        """Removes acknowledged packets from the reliable retransmission queue."""
        if not self.unacked_reliable_packets:
            return
        to_remove = []
        for seq in self.unacked_reliable_packets.keys():
            if seq == ack_seq:
                to_remove.append(seq)
            elif 0 < (ack_seq - seq) <= 32:
                bit_idx = ack_seq - seq - 1
                if (ack_bits >> bit_idx) & 1:
                    to_remove.append(seq)
            elif (ack_seq - seq) > 32:
                to_remove.append(seq)
        for s in to_remove:
            self.unacked_reliable_packets.pop(s, None)


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
        logger.info("[COMBAT CONFIG] PLAYER_JOIN_ENABLED=%s, ISOLATED_OP101_TEST=%s, STAGE_3_ENABLED=%s, STAGE_4_ENABLED=%s",
                    PLAYER_JOIN_ENABLED, ISOLATED_OP101_TEST, STAGE_3_ENABLED, STAGE_4_ENABLED)

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
            stage_2_targets: List[ClientSession] = []
            with self.lock:
                for addr, session in list(self.sessions.items()):
                    # Timeout after 20 seconds of silence
                    if now - session.last_alive_time > 20.0:
                        to_remove.append(addr)
                    else:
                        # CRITICAL FIX: Suppress unsolicited ACKs during handshake & early stage dispatch.
                        # The client's internal state machine expects HELLO_RES -> scene load -> Opcode 130
                        # in strict order. Firing unsolicited ACKs during stages 0-3 corrupts UnityMain's
                        # packet dispatcher and triggers SIGSEGV fault addr 0x0 at libil2cpp +0xa0.
                        # Only flush background ACKs once combat_stage >= 4 (match is LIVE).
                        if session.combat_stage >= 4 and session.remote_seq > session.last_acked_remote_seq:
                            session.last_acked_remote_seq = session.remote_seq
                            ack_payload = UDP_Ack_Res(session.remote_seq, session.received_seq_bits).serialize()
                            ack_pkt = UDMPacket(
                                send_option=SendOption.NONE,
                                cmd=ReservedMsgID.UDP_ACK,
                                seq_id=0,
                                data=ack_payload
                            )
                            self._send_packet_to_addr(ack_pkt, addr)

                        # Post-scene-load entity dispatch: the 12-step match-entry burst is sent while the
                        # client is still loading PVP_WaitingIsland, so its in-match message handlers are not
                        # registered yet and the player-join entities are discarded. Re-dispatch them once the
                        # client is inside the loaded match scene (observed ~3s after the burst).
                        if ISOLATED_OP101_TEST:
                            # Hard-gate: during isolated Opcode 101 test, suppress all post-scene entity dispatch
                            pass
                        elif (session.combat_stage >= 4 and not session.stage_2_scheduled
                              and session.match_entry_time
                              and now - session.match_entry_time >= 4.0):
                            session.stage_2_scheduled = True
                            stage_2_targets.append(session)

                        # Retransmit unacknowledged reliable packets after 1.0s timeout (max 3 retries)
                        if getattr(session, "unacked_reliable_packets", None):
                            for seq, (unack_pkt, send_time, retries) in list(session.unacked_reliable_packets.items()):
                                if ISOLATED_OP101_TEST and unack_pkt.cmd == CombatOpcode.RUDP_PLAYER_JOIN:
                                    # Never auto-retransmit Opcode 101 in isolated test mode
                                    continue
                                if now - send_time >= 1.0 and retries < 3:
                                    logger.debug("Resending unacked reliable packet seq=%d (cmd=%d, retry=%d) to %s", seq, unack_pkt.cmd, retries + 1, addr)
                                    session.unacked_reliable_packets[seq] = (unack_pkt, now, retries + 1)
                                    self._send_packet_to_addr(unack_pkt, addr)

            for stage2_session in stage_2_targets:
                try:
                    logger.info("[STAGE 2] Match scene ready (%.1fs after burst) - dispatching player-join entities to %s",
                                now - stage2_session.match_entry_time, stage2_session.addr)
                    if ISOLATED_OP101_TEST:
                        logger.info("[ISOLATED_GUARD] Stage 2 re-dispatch blocked by ISOLATED_OP101_TEST.")
                    elif PLAYER_JOIN_ENABLED:
                        self._dispatch_stage_2_player_join(stage2_session)
                    else:
                        logger.info("[STAGE 2] Player-join dispatch disabled (PLAYER_JOIN=0); %s scene kept alive", stage2_session.addr)
                except Exception as e:
                    logger.error("Stage 2 post-scene dispatch failed for %s: %s", stage2_session.addr, e)

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

        if pkt.cmd not in (CombatOpcode.UDP_PLAYER_POSITION_ONLY, 1014, 3, ReservedMsgID.UDP_PING):
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

        # 2. PING / PONG (Payload is 4B or 8B tick timestamp)
        if pkt.cmd == ReservedMsgID.UDP_PING and len(pkt.data) <= 8:
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
                session.acknowledge_reliable_packets(ack_seq, ack_bits)
                stage = getattr(session, "combat_stage", 0)
                if stage == 0:
                    logger.info("[STAGE 0] Handshake complete. Standing by for client RUDP_JOIN_MATCH (Opcode 100)...")
                else:
                    logger.info("[STAGE %d] ACK received: ack_seq=%d, ack_bits=0x%08x", stage, ack_seq, ack_bits)
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
            # CRITICAL: Use seq_id=0 for ACK packets — ACKs are non-reliable control messages.
            # Using session.next_seq() here pollutes the server's sequence counter, causing the
            # client to expect data for those sequences and stalling its reliable packet pipeline.
            if pkt.is_reliable():
                session.last_acked_remote_seq = session.remote_seq
                ack_payload = UDP_Ack_Res(session.remote_seq, session.received_seq_bits).serialize()
                ack_pkt = UDMPacket(
                    send_option=SendOption.NONE,
                    cmd=ReservedMsgID.UDP_ACK,
                    seq_id=0,
                    data=ack_payload
                )
                self._send_packet_to_addr(ack_pkt, session.addr)

            # Check if this is RUDP_JOIN_MATCH
            if pkt.cmd == CombatOpcode.RUDP_JOIN_MATCH:
                threading.Thread(target=self._handle_join_match, args=(pkt, session), daemon=True).start()
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

            # Opcode 1014 or 3: Movement update from client
            if pkt.cmd in (CombatOpcode.UDP_PLAYER_POSITION_ONLY, 1014, 3):
                self._handle_client_movement(pkt, session)
                return

            # Opcode 443 or 445: Client parachute / eject action
            if pkt.cmd in (CombatOpcode.RUDP_TeamParachuteInfo, CombatOpcode.RUDP_C2S_ParachuteBecomeFree, 443, 445):
                from .match_director import global_match_director, MatchState
                if global_match_director:
                    m = global_match_director.get_match(session.match_id)
                    if m and m.state == MatchState.STATE_3_AIRPLANE_FLIGHT:
                        m.eject_player(str(session.account_id))
                        m.transition_to(MatchState.STATE_4_EJECT_PARACHUTE)
                        logger.info("[MATCH] Client %s initiated manual airplane eject (cmd=%d)", session.addr, pkt.cmd)
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
                # Resend authentic S2C_Hello_Res (40B wire format)
                res_payload = S2C_Hello_Res(session_key="mk-9d10bffc98767f2f", order_id=0, required_id=0).serialize()
                reply_pkt = UDMPacket(
                    send_option=SendOption.HELLO,
                    cmd=ReservedMsgID.UDP_HELLO,
                    seq_id=0,
                    order_id=0,
                    flags=0,
                    data=res_payload
                )
                self._send_packet_to_addr(reply_pkt, addr, sock)

                # Acknowledge the client's incoming HELLO seq so client resend queue ceases retries
                ack_payload = struct.pack("<HI", pkt.seq_id, 0)
                ack_pkt = UDMPacket(
                    send_option=SendOption.NONE,
                    cmd=ReservedMsgID.UDP_ACK,
                    seq_id=0,
                    order_id=0,
                    data=ack_payload
                )
                self._send_packet_to_addr(ack_pkt, addr, sock)
                logger.info("Dispatched UDP_ACK for client HELLO seq=%d to %s", pkt.seq_id, addr)
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

                import hashlib
                matched_tok = None
                matched_info = None

                for tok, info in self.authorized_tokens.items():
                    tok_clean = tok.lower().strip()
                    tok_md5_bytes = hashlib.md5(tok.encode()).digest()
                    tok_raw_bytes = b""
                    try:
                        if len(tok_clean) == 32:
                            tok_raw_bytes = bytes.fromhex(tok_clean)
                    except Exception:
                        pass

                    if (
                        pkt.data == tok_md5_bytes
                        or (tok_raw_bytes and pkt.data == tok_raw_bytes)
                        or raw_token_hex == tok_clean
                        or raw_token_str == tok_clean
                        or (raw_token_hex and tok_clean.startswith(raw_token_hex))
                        or (tok_clean and tok_clean in raw_token_str)
                    ):
                        matched_tok = tok
                        matched_info = info
                        break

                if not matched_info and self.authorized_tokens:
                    # Fallback to most recently registered token
                    sorted_tokens = sorted(self.authorized_tokens.items(), key=lambda item: item[1].get("created_at", 0), reverse=True)
                    matched_tok, matched_info = sorted_tokens[0]
                    logger.info("Fell back to most recent authorized match token '%s'", matched_tok)

                if matched_info:
                    session.account_id = matched_info.get("account_id", DEFAULT_ACCOUNT_ID)
                    session.match_id = matched_info.get("match_id", 0)
                    session.nickname = matched_info.get("nickname", "PushpaGG")
                    session.prepare_token = matched_tok or ""
                    session.authorized = True
                    logger.info("Bound authorized session for account_id=%d match_id=%d nick='%s' to %s",
                                session.account_id, session.match_id, session.nickname, addr)
                else:
                    from core.state import generate_match_id
                    session.account_id = DEFAULT_ACCOUNT_ID
                    session.match_id = generate_match_id()
                    session.nickname = "PushpaGG"
                    logger.info("Defaulted session for account_id=%d match_id=%d to %s", session.account_id, session.match_id, addr)

                # Link with MatchDirector
                try:
                    from .match_director import global_match_director
                    if global_match_director:
                        match = global_match_director.get_match(session.match_id)
                        if not match:
                            match = global_match_director.get_match_for_player(str(session.account_id))
                        if not match and global_match_director.active_matches:
                            match = list(global_match_director.active_matches.values())[-1]
                        if match:
                            session.match_id = match.match_id
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

        res_payload = S2C_Hello_Res(session_key="mk-9d10bffc98767f2f", order_id=0, required_id=0).serialize()
        reply_pkt = UDMPacket(
            send_option=SendOption.HELLO,
            cmd=ReservedMsgID.UDP_HELLO,
            seq_id=0,
            order_id=0,
            flags=0,
            data=res_payload
        )
        self._send_packet_to_addr(reply_pkt, addr, sock)

        # Acknowledge the client's incoming HELLO seq so client resend queue ceases retries
        ack_payload = struct.pack("<HI", pkt.seq_id, 0)
        ack_pkt = UDMPacket(
            send_option=SendOption.NONE,
            cmd=ReservedMsgID.UDP_ACK,
            seq_id=0,
            order_id=0,
            data=ack_payload
        )
        self._send_packet_to_addr(ack_pkt, addr, sock)
        logger.info("Dispatched UDP_ACK for client HELLO seq=%d to %s", pkt.seq_id, addr)

        if self.on_client_connected:
            try:
                self.on_client_connected(session)
            except Exception as e:
                logger.error("on_client_connected hook error: %s", e)

    def _handle_ping(self, pkt: UDMPacket, addr: Tuple[str, int]) -> None:
        """Echo client tick timestamp for latency measurement."""
        # Preserve exact payload length (4B uint32 or 8B uint64) to maintain client stream framing
        pong_payload = pkt.data

        reply = UDMPacket(
            send_option=SendOption.NONE,
            cmd=ReservedMsgID.UDP_PING,
            seq_id=0,
            data=pong_payload
        )
        self._send_packet_to_addr(reply, addr)

    def _handle_join_match(self, pkt: UDMPacket, session: ClientSession) -> None:
        """
        Handle RUDP_JOIN_MATCH (100) from client.
        Authentic Barbosa OB17 Protocol Ground-Truth Burst:
        1. UDP_ACK (cmd=2, ack=client_seq, bits=1, 6B payload / 14B wire)
        2. S2C_JoinMatchRes (cmd=100, opt=2, seq=1, ord=0, 81B payload / 93B wire)
        3. RUDP_SYNC_REGION_ACTIVITIES (cmd=170, opt=2, seq=2, ord=1, 64B payload / 76B wire)
        4. RUDP_SYNC_REGION_ACTIVITIES (cmd=170, opt=2, seq=3, ord=2, 64B payload / 76B wire)
        5. RUDP_SyncShowCase (cmd=278, opt=2, seq=4, ord=3, 96B payload / 108B wire)
        6. RUDP_PLAYER_JOIN (cmd=101, opt=2, seq=5, ord=4) -> Local player entity (ID 1, 32B payload). MUST happen before cmd=130!
        7. RUDP_SYNC_PLAYERS_VISIBILITY (cmd=135, opt=2, seq=6, ord=5, 24B payload / 36B wire)
        8. RUDP_JOIN_MATCH_FINISHED (cmd=130, opt=2, seq=7, ord=6, 81B payload / 93B wire)
        9. RUDP_BIND_PRI (cmd=118, opt=2, seq=8, ord=7, 24B payload / 36B wire)
        10. RUDP_VAR_SYNC_GRI_DATA (cmd=501, opt=5, seq=9, ord=8, 16B payload / 28B wire)
        11. RUDP_PLAYER_JOIN (cmd=101, opt=2, seq=10..32, ord=9..31) -> Bot entities (gated by PLAYER_JOIN)
            Followed by bots seq 33..58, priority binds seq 59..98, visibility sync seq 99.
        12. RUDP_SAFE_ZONE_CHANGE (cmd=117, opt=2, seq=100, ord=99, 48B payload / 60B wire)
            Followed by GRI data (cmd=501, seq=101, ord=100) and 10 Hz position sync (Opcode 1014).
        """
        logger.info("Client %s sent RUDP_JOIN_MATCH (seq=%d, len=%d). Firing ground-truth Barbosa 12-step burst!",
                    session.addr, pkt.seq_id, len(pkt.data))
        # Bot entity messages are gated by PLAYER_JOIN: every opcode 101 packet makes
        # the 1.39 client SIGSEGV inside its own message parser, so they stay off
        # unless PLAYER_JOIN=1.
        session.authorized = True
        session.combat_stage = 2

        match_id = session.match_id or 1000001
        account_id = session.account_id or DEFAULT_ACCOUNT_ID
        nickname = session.nickname or "PushpaGG"
        prepare_token = session.prepare_token or ""

        # Parse token/match_id if client provided it
        if len(pkt.data) >= 16:
            try:
                from .combat_packet_codec import C2S_JoinMatch
                req = C2S_JoinMatch.unserialize(pkt.data)
                if req.match_id > 0:
                    match_id = req.match_id
                    session.match_id = match_id
                if req.prepare_token:
                    prepare_token = req.prepare_token
                    session.prepare_token = prepare_token
            except Exception as e:
                logger.debug("C2S_JoinMatch parse note: %s", e)

        # 1. Immediate UDP_ACK for client seq (cmd=2, ack=client_seq, bits=1, 6B payload / 14B wire)
        ack_payload = struct.pack("<HI", pkt.seq_id, 1)
        ack_pkt = UDMPacket(
            send_option=SendOption.NONE,
            cmd=ReservedMsgID.UDP_ACK,
            seq_id=0,
            order_id=0,
            flags=0,
            data=ack_payload
        )
        self._send_packet_to_addr(ack_pkt, session.addr)

        # Reset session sequence and order counters for strictly monotonic burst
        session.local_seq = 1
        session.local_order = 0

        # 2. S2C_JoinMatchRes (cmd=100, opt=2, seq=1, ord=0, 81B payload / 93B wire)
        # Authentic Barbosa protobuf/binary structure initializing MatchGame.m_Match,
        # game mode, map ID, room settings, and initial safe zone.
        from .combat_packet_codec import S2C_JoinMatchRes, RUDP_BindPRI
        join_res = S2C_JoinMatchRes(
            err_code=0,
            account_id=account_id,
            match_id=match_id,
            server_time=int(time.time()),
            map_id=1,
            waiting_seconds=60,
            weather_style=1,
            game_mode=1,
            room_type=0,
            safe_zone_center=(0.0, 0.0, 0.0),
            safe_zone_radius=600.0,
            next_safe_zone_center=(0.0, 0.0, 0.0),
            next_safe_zone_radius=600.0,
            phase=0,
        )
        payload_100 = join_res.serialize()
        assert len(payload_100) == 81, f"opcode 100 payload must be 81B, got {len(payload_100)}"
        pkt_100 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_JOIN_MATCH,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=1,
            data=payload_100
        )
        self.send_packet(session, pkt_100)
        time.sleep(0.005)

        # 3. RUDP_SYNC_REGION_ACTIVITIES (cmd=170, opt=2, seq=2, ord=1, 4B wire)
        from .codec_op170 import S2C_SyncRegionActivities
        payload_170 = S2C_SyncRegionActivities(activities=[]).serialize()
        pkt_170 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_SYNC_REGION_ACTIVITIES,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_170
        )
        self.send_packet(session, pkt_170)
        time.sleep(0.005)

        # 4. RUDP_SyncShowCase (cmd=278, opt=2, seq=3, ord=2, 4B wire)
        from .codec_op278 import S2C_SyncShowCase
        payload_278 = S2C_SyncShowCase(items=[]).serialize()
        pkt_278 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_SyncShowCase,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_278
        )
        self.send_packet(session, pkt_278)
        time.sleep(0.005)

        # 6. RUDP_PLAYER_JOIN (cmd=101, opt=2, seq=5, ord=4) -> Local human player entity (ID 1, 320B payload / 332B wire). MUST happen before cmd=130!
        from .combat_packet_codec import S2C_PlayerJoin
        avatar_id = 101000006
        clothes = [211000000, 208000000, 203000573, 204000345, 205000299]
        skills = [106, 206]
        try:
            from core.state import state
            p_prof = state.get_player(account_id)
            if p_prof:
                nickname = p_prof.get("nickname", nickname)
                avatar_id = int(p_prof.get("avatar_id", avatar_id))
            char = state.get_character(avatar_id, account_id)
            if char and char.get("clothes"):
                clothes = [int(c) for c in char["clothes"]]
        except Exception:
            pass

        if ISOLATED_OP101_TEST:
            # Step 4 (Isolated Test Mode): Send single minimal 66-byte Opcode 101 Human Join
            min_pjoin = S2C_PlayerJoin(
                account_id=account_id,
                match_id=match_id,
                camp=1,
                is_bot=False,
                team_id=1,
                nickname="",
                avatar_id=1010001,
                is_ready=True,
                level=1,
                rank=100,
                is_alive=True,
                clothes=[],
                gender=1,
                flag=False,
                skills=[],
                region="",
                banner_id=901000001,
                headpic=""
            )
            payload_101_min = min_pjoin.serialize()
            assert len(payload_101_min) == 66, f"minimal payload must be 66B, got {len(payload_101_min)}"
            pkt_101_min = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                flags=1,  # Verified reliable flag 0x01
                data=payload_101_min
            )
            self.send_packet(session, pkt_101_min)
            logger.info("[ISOLATED_TEST] Dispatched single minimal Opcode 101 (seq=%d, ord=%d, len=%d, crc7=0x%02x, flags=0x%02x) to %s",
                        pkt_101_min.seq_id, pkt_101_min.order_id, len(pkt_101_min.data), pkt_101_min.crc7, pkt_101_min.flags, session.addr)
            time.sleep(0.005)

            # Step 5 (Isolated Test Mode): Send Opcode 130 to confirm match loading parameters (without Opcode 135, 118, or bots)
            from .codec_op130 import JoinMatchFinishedPacket, SafeZoneBlock, SafeZoneCircle
            payload_130 = JoinMatchFinishedPacket(
                err_code=0,
                account_id=account_id,
                match_id=match_id,
                server_time=int(time.time()),
                map_id=1,
                waiting_seconds=60,
                weather_style=1,
                game_mode=1,
                room_type=0,
                safe_zone=SafeZoneBlock(
                    phase=int(join_res.phase),
                    current=SafeZoneCircle(
                        center_x=int(join_res.safe_zone_center[0]),
                        center_z=int(join_res.safe_zone_center[2]),
                        radius=int(join_res.safe_zone_radius),
                    ),
                    next=SafeZoneCircle(
                        center_x=int(join_res.next_safe_zone_center[0]),
                        center_z=int(join_res.next_safe_zone_center[2]),
                        radius=int(join_res.next_safe_zone_radius),
                    ),
                ),
            ).serialize()
            assert len(payload_130) == 81, f"opcode 130 payload must be 81B, got {len(payload_130)}"
            pkt_130 = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_JOIN_MATCH_FINISHED,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                flags=1,  # Verified reliable flag 0x01
                data=payload_130
            )
            self.send_packet(session, pkt_130)
            logger.info("[ISOLATED_TEST] Dispatched Opcode 130 (seq=%d, ord=%d). All bots and unverified replication messages hard-gated.",
                        pkt_130.seq_id, pkt_130.order_id)

            session.stage_2_scheduled = True
            session.combat_stage = 4
            session.match_entry_dispatched = True
            session.match_entry_time = time.time()
            return  # HARD-GATE: Exit immediately to ensure 0 bots, 0 PRI binds, 0 visibility packets!

        local_pjoin = S2C_PlayerJoin(
            player_id=1,
            account_id=account_id,
            team_id=1,
            camp=1,
            match_id=match_id,
            nickname=nickname,
            avatar_id=avatar_id,
            is_bot=False,
            level=25,
            rank=1800,
            is_ready=True,
            clothes=clothes,
            gender=2 if str(avatar_id).startswith("101") else 1,
            is_alive=True,
            skills=skills,
            region="IND",
            banner_id=901000001,
            headpic="avatar_01"
        )
        payload_101_local = local_pjoin.serialize()
        pkt_101_local = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_PLAYER_JOIN,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_101_local
        )
        if PLAYER_JOIN_ENABLED:
            self.send_packet(session, pkt_101_local)
        else:
            logger.info("Opcode 101 (human player join) skipped: PLAYER_JOIN=0")
        time.sleep(0.005)

        # 7. RUDP_SYNC_PLAYERS_VISIBILITY (cmd=135, opt=2, seq=6, ord=5, 8B UInt64 bitmask)
        from .codec_op135 import S2C_SyncPlayersVisibility
        payload_135 = S2C_SyncPlayersVisibility(visibility_mask=0xFFFFFFFFFFFFFFFF).serialize()
        pkt_135 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_SYNC_PLAYERS_VISIBILITY,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_135
        )
        self.send_packet(session, pkt_135)
        time.sleep(0.005)

        # 8. RUDP_JOIN_MATCH_FINISHED (cmd=130, opt=2, seq=7, ord=6, 81B payload / 93B wire)
        # TypeDef [4580] message.nSa~rX, measured (not inferred): 39B header
        # (UInt32, UInt64, UInt64, Int32, Byte, UInt32, UInt16, UInt32, UInt32) +
        # 26B nested message.j]\x82VkzA (Int16 phase + 2 x message.My^x~\x81o, each
        # 3 x Int32) + list<int> + list<uint> + list<msg> + UInt32 = 81B with empty
        # collections.
        # The safe-zone centres are the same authoritative values sent in
        # S2C_JoinMatchRes for this match (x/z of the 3D centres).
        from .codec_op130 import JoinMatchFinishedPacket, SafeZoneBlock, SafeZoneCircle
        payload_130 = JoinMatchFinishedPacket(
            err_code=0,
            account_id=account_id,
            match_id=match_id,
            server_time=int(time.time()),
            map_id=1,
            waiting_seconds=60,
            weather_style=1,
            game_mode=1,
            room_type=0,
            safe_zone=SafeZoneBlock(
                phase=int(join_res.phase),
                current=SafeZoneCircle(
                    center_x=int(join_res.safe_zone_center[0]),
                    center_z=int(join_res.safe_zone_center[2]),
                    radius=int(join_res.safe_zone_radius),
                ),
                next=SafeZoneCircle(
                    center_x=int(join_res.next_safe_zone_center[0]),
                    center_z=int(join_res.next_safe_zone_center[2]),
                    radius=int(join_res.next_safe_zone_radius),
                ),
            ),
        ).serialize()
        assert len(payload_130) == 81, f"opcode 130 payload must be 81B, got {len(payload_130)}"
        pkt_130 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_JOIN_MATCH_FINISHED,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_130
        )
        self.send_packet(session, pkt_130)
        time.sleep(0.005)

        # 9. RUDP_BIND_PRI (cmd=118, opt=2, seq=8, ord=7, 24B payload / 36B wire)
        # Authentic Barbosa PRI binding: <account_id: uint64><entity_id: uint32><pri_id: uint32><reserved: uint64>
        local_bind = RUDP_BindPRI(account_id=account_id, entity_id=1, pri_id=0, reserved=0)
        pkt_118 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_BIND_PRI,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=local_bind.serialize()
        )
        self.send_packet(session, pkt_118)
        time.sleep(0.005)

        # 10. RUDP_VAR_SYNC_GRI_DATA (cmd=501, opt=5, seq=9, ord=8, 2B wire)
        from .codec_op501 import S2C_VarSyncGRIData
        payload_501 = S2C_VarSyncGRIData(items=[]).serialize()
        pkt_501 = UDMPacket(
            send_option=SendOption.VAR_RELIABLE,
            cmd=CombatOpcode.RUDP_VAR_SYNC_GRI_DATA,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_501
        )
        self.send_packet(session, pkt_501)
        time.sleep(0.005)

        # 11. RUDP_PLAYER_JOIN (cmd=101, opt=2, seq=10..32, ord=9..31) -> Bot entities (gated by PLAYER_JOIN)
        bot_names = [
            "Kelly", "Andrew", "Ford", "Olivia", "Alok", "Kla", "Maxim", "Misha",
            "Nikita", "Paloma", "Antonio", "Caroline", "Hayato", "Laura", "Rafael",
            "A124", "Jota", "Kapella", "Wolfrahh", "Luqueta", "Chrono", "Dasha",
            "Shirou", "Maro", "Xayne", "D-Bee", "Thiva", "Dimitri", "Otho", "Leon",
            "Nairi", "Kenta", "Homer", "Iris", "J.Biebs", "Tatsuya", "Luna", "Santino",
            "Orion", "Alvaro", "Wukong", "Steffie", "Notora", "Shani", "Joseph",
            "Clu", "Skyler", "Ignis", "Suzy"
        ]
        # Bots 2..24 (seq 10..32, ord 9..31)
        for idx in range(2, 25):
            bname = bot_names[(idx - 2) % len(bot_names)]
            bot_gender = 1 if (idx % 2 == 0) else 2
            bot_avatar = 102000004 if bot_gender == 1 else 101000006
            bot_join = S2C_PlayerJoin(
                player_id=idx,
                account_id=2000000 + idx,
                team_id=(idx % 12) + 1,
                camp=1,
                match_id=match_id,
                nickname=bname,
                avatar_id=bot_avatar,
                is_bot=True,
                level=15 + (idx % 15),
                rank=1200 + (idx * 20),
                is_ready=True,
                clothes=[211000000, 203000056, 204000043, 205000026],
                gender=bot_gender,
                is_alive=True,
                skills=[106],
                region="IND",
                banner_id=901000001,
                headpic="avatar_02"
            )
            pkt_bot = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                flags=0,
                data=bot_join.serialize()
            )
            if PLAYER_JOIN_ENABLED:
                self.send_packet(session, pkt_bot)
            time.sleep(0.002)

        # Remaining Bots 25..50 (seq 33..58, ord 32..57)
        for idx in range(25, 51):
            bname = bot_names[(idx - 2) % len(bot_names)]
            bot_gender = 1 if (idx % 2 == 0) else 2
            bot_avatar = 102000004 if bot_gender == 1 else 101000006
            bot_join = S2C_PlayerJoin(
                player_id=idx,
                account_id=2000000 + idx,
                team_id=(idx % 12) + 1,
                camp=1,
                match_id=match_id,
                nickname=bname,
                avatar_id=bot_avatar,
                is_bot=True,
                level=15 + (idx % 15),
                rank=1200 + (idx * 20),
                is_ready=True,
                clothes=[211000000, 203000056, 204000043, 205000026],
                gender=bot_gender,
                is_alive=True,
                skills=[106],
                region="IND",
                banner_id=901000001,
                headpic="avatar_02"
            )
            pkt_bot = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                flags=0,
                data=bot_join.serialize()
            )
            if PLAYER_JOIN_ENABLED:
                self.send_packet(session, pkt_bot)
            time.sleep(0.002)

        # Priority channel binds (cmd=118, seq 59..98, ord 58..97, 24B payload / 36B wire)
        for bot_idx in range(40):
            bot_eid = bot_idx + 2
            bot_acc = 1000000000 + bot_eid
            bot_bind = RUDP_BindPRI(account_id=bot_acc, entity_id=bot_eid, pri_id=0, reserved=0)
            pkt_bind = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_BIND_PRI,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                flags=0,
                data=bot_bind.serialize()
            )
            self.send_packet(session, pkt_bind)
            time.sleep(0.002)

        # Secondary Visibility Sync (cmd=135, seq 99, ord 98, 24B payload / 36B wire)
        pkt_135_2 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_SYNC_PLAYERS_VISIBILITY,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_135
        )
        self.send_packet(session, pkt_135_2)

        # Non-reliable Opcode 1000 (clock sync) + Opcode 1001 (position sync)
        import math
        from .combat_packet_codec import PlayerPosItem, UDP_PlayerPositionBatch, UDP_SyncServerTime, UDP_PlayerStateSync, RUDP_SafeZoneChange
        sx, sy, sz = -500.0, 10.0, 800.0
        spawn_items = [
            PlayerPosItem(player_id=1, x=sx, y=sy, z=sz, physx_state=0, physx_pose=0)
        ]
        for idx in range(2, 51):
            angle = (idx - 2) * (2.0 * math.pi / 49.0)
            radius = 5.0 + (idx % 7) * 3.0
            bx = sx + math.cos(angle) * radius
            bz = sz + math.sin(angle) * radius
            spawn_items.append(PlayerPosItem(player_id=idx, x=bx, y=sy, z=bz, physx_state=0, physx_pose=0))

        # Opcode 1000 (clock sync) intentionally not sent: the client parses opcode 1000 with
        # message.dEa^CT (Int32 count + count*7B items), so the 4-byte timestamp we produced
        # was read as a huge element count and raised EndOfStreamException in
        # MatchGameClient.HandleRecvPacket (Bugly SIGABRT). The match does not require it.
        # pkt_1000 = UDMPacket(
        #     send_option=SendOption.NONE,
        #     cmd=CombatOpcode.UDP_SYNC_SERVER_TIME,
        #     seq_id=0,
        #     order_id=0,
        #     flags=0,
        #     data=UDP_SyncServerTime(server_time=0).serialize()
        # )
        # self.send_packet(session, pkt_1000)

        pkt_1001 = UDMPacket(
            send_option=SendOption.NONE,
            cmd=CombatOpcode.UDP_PLAYER_STATE_SYNC,
            seq_id=0,
            order_id=0,
            flags=0,
            data=UDP_PlayerStateSync(server_time_ms=int(time.time() * 1000) & 0xFFFFFFFF, flags=0, players=spawn_items).serialize()
        )
        self.send_packet(session, pkt_1001)

        # 12. RUDP_SAFE_ZONE_CHANGE (cmd=117, opt=2, seq=100, ord=99, 48B payload / 60B wire)
        safezone = RUDP_SafeZoneChange(
            phase=0,
            current_x=sx,
            current_y=sy,
            current_z=sz,
            current_radius=450.0,
            next_x=sx,
            next_y=sy,
            next_z=sz,
            next_radius=450.0
        )
        payload_117 = safezone.serialize().ljust(48, b"\x00")
        pkt_117 = UDMPacket(
            send_option=SendOption.RELIABLE,
            cmd=CombatOpcode.RUDP_SAFE_ZONE_CHANGE,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_117
        )
        self.send_packet(session, pkt_117)

        # Post-100: GRI Data Sync (cmd=501, 2B wire)
        pkt_501_2 = UDMPacket(
            send_option=SendOption.VAR_RELIABLE,
            cmd=CombatOpcode.RUDP_VAR_SYNC_GRI_DATA,
            seq_id=session.next_seq(),
            order_id=session.next_order(),
            flags=0,
            data=payload_501
        )
        self.send_packet(session, pkt_501_2)

        # Opcode 1014 (batch compatibility)
        batch = UDP_PlayerPositionBatch(players=spawn_items, timestamp=int(time.time() * 1000) & 0x7FFFFFFF)
        pkt_1014 = UDMPacket(
            send_option=SendOption.NONE,
            cmd=CombatOpcode.UDP_PLAYER_POSITION_ONLY,
            seq_id=0,
            order_id=0,
            flags=0,
            data=batch.serialize()
        )
        self.send_packet(session, pkt_1014)

        session.combat_stage = 4
        session.match_entry_dispatched = True
        session.match_entry_time = time.time()
        logger.info("[MATCH-ENTRY] Complete 12-step authentic Barbosa burst (final seq=%d, ord=%d) sent to %s! Match is LIVE on Bermuda Spawn Island.",
                    session.local_seq - 1, session.local_order - 1, session.addr)

    def _dispatch_stage_2_player_join(self, session: ClientSession) -> None:
        """STAGE 2: Send Opcode 101 (RUDP_PLAYER_JOIN) for human player + 49 bots (total 50 players for Battle Royale)."""
        if ISOLATED_OP101_TEST:
            logger.info("[ISOLATED_GUARD] Stage 2 re-dispatch blocked by ISOLATED_OP101_TEST.")
            return
        logger.info("[STAGE 2] Sending Opcode 101 (RUDP_PLAYER_JOIN) for human player + 49 bots to %s", session.addr)
        account_id = session.account_id or DEFAULT_ACCOUNT_ID
        match_id = session.match_id or generate_match_id()
        nickname = session.nickname or "PushpaGG"
        avatar_id = 102000004
        level = 25
        rank = 1800
        region = "DEFAULT"
        banner_id = 901000001
        headpic = "avatar_01"
        clothes = [211000000, 208000000, 203000573, 204000345, 205000299]
        skills = [106, 206]
        gender = 1

        try:
            from core.state import state
            p_prof = state.get_player(account_id)
            if p_prof:
                nickname = p_prof.get("nickname", nickname)
                avatar_id = int(p_prof.get("avatar_id", avatar_id))
                level = int(p_prof.get("level", level))
                rank = int(p_prof.get("ranking_points") or p_prof.get("rank") or rank)
                region = str(p_prof.get("region", region))
                banner_id = int(p_prof.get("banner_id", banner_id))
                headpic = str(p_prof.get("head_pic") or p_prof.get("headpic") or headpic)

            char = state.get_character(avatar_id, account_id)
            if char:
                char_clothes = char.get("clothes")
                if char_clothes:
                    clothes = [int(c) for c in char_clothes]
                char_skills = char.get("equiped_skills")
                if char_skills:
                    s_list = []
                    for s in char_skills:
                        if isinstance(s, dict):
                            sid = s.get("skill_id", 0)
                        else:
                            sid = int(s)
                        if sid > 0:
                            s_list.append(sid)
                    if s_list:
                        skills = s_list
                elif char.get("skill_id"):
                    skills = [int(char["skill_id"])]

            gender = 2 if str(avatar_id).startswith("101") else 1
        except Exception as e:
            logger.warning("Error populating player/character state for account %s: %s", account_id, e)

        try:
            from .combat_packet_codec import S2C_PlayerJoin
            # 1. Human player (player_id=1)
            player_join = S2C_PlayerJoin(
                player_id=1,
                account_id=account_id,
                team_id=1,
                camp=1,
                match_id=match_id,
                nickname=nickname,
                avatar_id=avatar_id,
                is_bot=False,
                level=level,
                rank=rank,
                is_ready=True,
                clothes=clothes,
                gender=gender,
                is_alive=True,
                skills=skills,
                region=region,
                banner_id=banner_id,
                headpic=headpic
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
            time.sleep(0.001)  # Micro-pacing between entity allocations
            logger.info("[STAGE 2] Dispatched Opcode 101 for Human (seq=%d, ord=%d, nick='%s', aid=%d, clothes=%d, skills=%d).",
                        join_pkt.seq_id, join_pkt.order_id, nickname, account_id, len(clothes), len(skills))

            # Predefined bot archetypes & names
            bot_names = [
                "Bot_Kelly", "Bot_Andrew", "Bot_Ford", "Bot_Olivia", "Bot_Nikita",
                "Bot_Misha", "Bot_Kla", "Bot_Paloma", "Bot_Maxim", "Bot_Caroline",
                "Bot_Antonio", "Bot_Wukong", "Bot_Shimada", "Bot_Laura", "Bot_Rafael",
                "Bot_Hayato", "Bot_A124", "Bot_Joseph", "Bot_Shani", "Bot_Notora",
                "Bot_Alvaro", "Bot_Steffie", "Bot_Jota", "Bot_Kapella", "Bot_Wolfrahh",
                "Bot_Luqueta", "Bot_HayatoFire", "Bot_Jai", "Bot_K", "Bot_Dasha",
                "Bot_Chrono", "Bot_Shirou", "Bot_Skyler", "Bot_Xayne", "Bot_Maro",
                "Bot_D-Bee", "Bot_Thiva", "Bot_Dimitri", "Bot_Leon", "Bot_Otho",
                "Bot_Nairi", "Bot_Kenta", "Bot_J-Biebs", "Bot_Iris", "Bot_Luna",
                "Bot_Tatsuya", "Bot_Santino", "Bot_Orion", "Bot_Alok"
            ]

            # 2. 49 Bots (player_id=2 through 50)
            for idx in range(2, 51):
                b_name = bot_names[(idx - 2) % len(bot_names)]
                bot_gender = 1 if (idx % 2 == 0) else 2
                bot_avatar = 102000004 if bot_gender == 1 else 101000006
                bot_obj = S2C_PlayerJoin(
                    player_id=idx,
                    account_id=2000000 + idx,
                    team_id=idx,
                    camp=idx,
                    match_id=match_id,
                    nickname=b_name,
                    avatar_id=bot_avatar,
                    gender=bot_gender,
                    clothes=[211000000, 203000056, 204000043, 205000026],
                    skills=[201, 202],
                    is_bot=True
                )
                bot_pkt = UDMPacket(
                    send_option=SendOption.RELIABLE,
                    cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                    seq_id=session.next_seq(),
                    order_id=session.next_order(),
                    data=bot_obj.serialize()
                )
                self.send_packet(session, bot_pkt)
                session.stage_2_final_seq = bot_pkt.seq_id
                time.sleep(0.001)  # Micro-pacing: 1ms per bot entity

            session.last_sent_seq = session.stage_2_final_seq
            session.last_sent_cmd = int(CombatOpcode.RUDP_PLAYER_JOIN)
            logger.info("[STAGE 2] Dispatched Opcode 101 for all 49 bots (total 50 entities). Final stage 2 seq=%d.", session.stage_2_final_seq)
        except Exception as e:
            logger.error("Could not send RUDP_PLAYER_JOIN: %s", e)

    def _dispatch_stage_3_scene_info(self, session: ClientSession) -> None:
        """STAGE 3: Send Opcode 116 (RUDP_SYNC_SCENE_INFO) with countdown and 50 alive players."""
        if ISOLATED_OP101_TEST or not STAGE_3_ENABLED:
            logger.info("[ISOLATED_GUARD] Stage 3 (Opcode 116) hard-gated: call blocked.")
            return
        logger.info("[STAGE 3] Sending Opcode 116 (RUDP_SYNC_SCENE_INFO) to %s", session.addr)
        match_id = session.match_id or generate_match_id()
        try:
            from .combat_packet_codec import S2C_SyncSceneInfo
            scene_info = S2C_SyncSceneInfo(
                match_id=match_id,
                elapsed_time=0.0,
                countdown_seconds=60.0,
                alive_players=50,
                spawn_island_x=-500.0,
                spawn_island_y=10.0,
                spawn_island_z=800.0,
                spawn_island_radius=60.0
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
            logger.info("[STAGE 3] Dispatched Opcode 116 (seq=%d, ord=%d, len=%d). Awaiting client ACK...", scene_pkt.seq_id, scene_pkt.order_id, len(scene_pkt.data))
            logger.info("[STAGE 3] Dispatched Opcode 116 (seq=%d, ord=%d, len=%d).", scene_pkt.seq_id, scene_pkt.order_id, len(scene_pkt.data))
        except Exception as e:
            logger.error("Could not send RUDP_SYNC_SCENE_INFO: %s", e)

        # Immediate Opcode 1014 position batch for all 50 sorted entities right after Opcode 116 (without waiting for ACK)
        try:
            from .match_director import global_match_director
            match = global_match_director.get_match(match_id) if global_match_director else None
            if not match and global_match_director:
                match = global_match_director.get_match_for_player(str(session.account_id))
            if not match and global_match_director and global_match_director.active_matches:
                match = list(global_match_director.active_matches.values())[-1]
            if match:
                session.match_id = match.match_id
                batch_bytes = match.build_waiting_island_position_batch_bytes()
            else:
                import math
                from .combat_packet_codec import PlayerPosItem, UDP_PlayerPositionBatch
                sx, sy, sz = -500.0, 10.0, 800.0
                spawn_items = [PlayerPosItem(player_id=1, x=sx, y=sy, z=sz, physx_state=0, physx_pose=0)]
                pedestals = [(-502.5, 10.3, 799.0), (-497.5, 10.3, 799.0), (-505.0, 10.1, 797.5), (-495.0, 10.1, 797.5)]
                for i, (px, py, pz) in enumerate(pedestals, start=2):
                    spawn_items.append(PlayerPosItem(player_id=i, x=px, y=py, z=pz, physx_state=0, physx_pose=0))
                for idx in range(6, 51):
                    k = (idx - 6) % 15
                    ring = (idx - 6) // 15
                    radius = 12.0 if ring == 0 else (24.0 if ring == 1 else 38.0)
                    angle = k * (2.0 * math.pi / 15.0) + (math.pi / 15.0 if ring == 1 else 0.0)
                    bx = sx + radius * math.cos(angle)
                    bz = sz + radius * math.sin(angle)
                    spawn_items.append(PlayerPosItem(player_id=idx, x=bx, y=sy, z=bz, physx_state=0, physx_pose=0))
                spawn_items.sort(key=lambda it: it.player_id)
                batch = UDP_PlayerPositionBatch(players=spawn_items, timestamp=int(time.time() * 1000) & 0x7FFFFFFF)
                batch_bytes = batch.serialize()

            pkt_1014 = UDMPacket(
                send_option=SendOption.NONE,
                cmd=CombatOpcode.UDP_PLAYER_POSITION_ONLY,
                seq_id=0,
                order_id=0,
                data=batch_bytes
            )
            self.send_packet(session, pkt_1014)
            logger.info("[STAGE 3] Dispatched immediate Opcode 1014 batch (50 sorted entities, len=%d) right after Opcode 116 without waiting for ACK.", len(batch_bytes))
        except Exception as e:
            logger.error("[STAGE 3] Error sending immediate Opcode 1014 batch: %s", e)

    def _dispatch_stage_4_spawn_island(self, session: ClientSession) -> None:
        """
        STAGE 4: Dispatches immediate Bermuda Spawn Island synchronization:
        1. Immediate S2C_SyncSceneInfo (Opcode 116) with countdown=60.0s, alive=50, and Spawn Island coordinates.
        2. Immediate UDP_PlayerPositionOnly (Opcode 1014) for all 50 players on Bermuda Spawn Island.
        """
        if ISOLATED_OP101_TEST or not STAGE_4_ENABLED:
            logger.info("[ISOLATED_GUARD] Stage 4 hard-gated: call blocked.")
            return
        logger.info("[STAGE 4] Dispatching immediate Spawn Island state and entity positions to %s", session.addr)
        match_id = session.match_id or generate_match_id()

        # Re-affirm local human player avatar in the active scene
        try:
            from .combat_packet_codec import S2C_PlayerJoin
            p_join = S2C_PlayerJoin(
                player_id=1,
                account_id=session.account_id or DEFAULT_ACCOUNT_ID,
                team_id=1,
                camp=1,
                match_id=match_id,
                nickname=session.nickname or "PushpaGG",
                avatar_id=102000004,
                is_bot=False,
                level=25,
                rank=1800,
                is_ready=True,
                clothes=[211000000, 208000000, 203000573, 204000345, 205000299],
                gender=1,
                is_alive=True,
                skills=[106, 206]
            )
            re_pkt = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_PLAYER_JOIN,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                data=p_join.serialize()
            )
            self.send_packet(session, re_pkt)
            logger.info("[STAGE 4] Re-affirmed Human Player Opcode 101 for active scene binding (seq=%d)", re_pkt.seq_id)
        except Exception as e:
            logger.debug("[STAGE 4] Re-affirm player error: %s", e)

        # 1. Send immediate S2C_SyncSceneInfo (Opcode 116)
        try:
            from .combat_packet_codec import S2C_SyncSceneInfo, UDP_PlayerPositionOnly
            scene_info = S2C_SyncSceneInfo(
                match_id=match_id,
                elapsed_time=0.0,
                countdown_seconds=60.0,
                alive_players=50,
                spawn_island_x=-500.0,
                spawn_island_y=10.0,
                spawn_island_z=800.0,
                spawn_island_radius=60.0
            )
            scene_pkt = UDMPacket(
                send_option=SendOption.RELIABLE,
                cmd=CombatOpcode.RUDP_SYNC_SCENE_INFO,
                seq_id=session.next_seq(),
                order_id=session.next_order(),
                data=scene_info.serialize()
            )
            self.send_packet(session, scene_pkt)
            logger.info("[STAGE 4] Dispatched immediate Opcode 116 Spawn Island sync (seq=%d, ord=%d)", scene_pkt.seq_id, scene_pkt.order_id)
            time.sleep(0.005)  # 5ms pacing between stage transition scene info and entity position batch
        except Exception as e:
            logger.error("[STAGE 4] Error sending immediate Opcode 116: %s", e)

        # 2. Dispatch initial entity positions for all 50 players around Spawn Island center (-500.0, 10.0, 800.0)
        try:
            from .match_director import global_match_director
            match = global_match_director.get_match(match_id) if global_match_director else None
            if not match and global_match_director:
                match = global_match_director.get_match_for_player(str(session.account_id))
            if not match and global_match_director and global_match_director.active_matches:
                match = list(global_match_director.active_matches.values())[-1]
            if match:
                session.match_id = match.match_id
                batch_bytes = match.build_waiting_island_position_batch_bytes()
            else:
                import math
                from .combat_packet_codec import PlayerPosItem, UDP_PlayerPositionBatch
                spawn_entities = [(1, -500.0, 10.0, 800.0)]
                for idx in range(2, 51):
                    angle = (idx - 2) * (2.0 * math.pi / 49.0)
                    radius = 5.0 + (idx % 7) * 3.0
                    bx = -500.0 + math.cos(angle) * radius
                    bz = 800.0 + math.sin(angle) * radius
                    spawn_entities.append((idx, bx, 10.0, bz))

                pos_items = [
                    PlayerPosItem(
                        player_id=pid,
                        x=x,
                        y=y,
                        z=z,
                        physx_state=0, # WALKING / IDLE
                        physx_pose=0   # STANDING
                    )
                    for pid, x, y, z in spawn_entities
                ]
                batch = UDP_PlayerPositionBatch(
                    players=pos_items,
                    timestamp=int(time.time() * 1000) & 0x7FFFFFFF
                )
                batch_bytes = batch.serialize()

            # Dispatch with primary CombatOpcode (1014)
            pkt_1014 = UDMPacket(
                send_option=SendOption.NONE,
                cmd=CombatOpcode.UDP_PLAYER_POSITION_ONLY,
                seq_id=0,
                order_id=0,
                data=batch_bytes
            )
            self.send_packet(session, pkt_1014)

            logger.info("[STAGE 4] Dispatched initial Spawn Island batch entity positions for all 50 entities (len=%d)", len(batch_bytes))
        except Exception as e:
            logger.error("[STAGE 4] Error sending initial player positions: %s", e)

    def send_packet(self, session: ClientSession, pkt: UDMPacket) -> bool:
        """Send a packet to a registered session."""
        if pkt.is_reliable():
            # Reliable game messages carry flags=1 (or existing flags if explicitly set)
            if pkt.flags == 0:
                pkt.flags = 1
            if pkt.seq_id == 0:
                pkt.seq_id = session.next_seq()
            if not getattr(pkt, "_order_id_explicit", False) and pkt.order_id == 0:
                pkt.order_id = session.next_order()
            if hasattr(session, "unacked_reliable_packets"):
                session.unacked_reliable_packets[pkt.seq_id] = (pkt, time.time(), 0)
        else:
            pkt.seq_id = 0
            pkt.order_id = 0

        ok = self._send_packet_to_addr(pkt, session.addr)
        return ok

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
            if pkt.cmd not in (CombatOpcode.UDP_PLAYER_POSITION_ONLY, 1014, 3, ReservedMsgID.UDP_PING):
                logger.info("SENT %s: opt=%d cmd=%d seq=%d ord=%d flags=0x%02x crc7=0x%02x payload_len=%d wire_len=%d",
                            addr, pkt.send_option, pkt.cmd, pkt.seq_id, pkt.order_id, pkt.flags, pkt.crc7, len(pkt.data), len(data))
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

        match_id = session.match_id or generate_match_id()
        if global_match_director:
            global_match_director.handle_player_kill_bot(
                match_id=match_id,
                victim_id=victim_id,
                killer_id=session.account_id or DEFAULT_ACCOUNT_ID,
                weapon_id=weapon_id,
                is_headshot=is_hs
            )

        self._broadcast_death_event(session, victim_id, session.account_id or DEFAULT_ACCOUNT_ID, session.nickname or "PushpaGG", weapon_id, is_hs)

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

        match_id = session.match_id or generate_match_id()
        res = {"hit": False}
        if global_match_director:
            res = global_match_director.handle_player_damage_bot(
                match_id=match_id,
                victim_id=victim_id,
                attacker_id=session.account_id or DEFAULT_ACCOUNT_ID,
                damage=damage,
                body_part=body_part,
                weapon_id=weapon_id
            )

        if res.get("is_dead"):
            logger.info("=== [BOT ELIMINATED] Bot %s (victim_id=%s) killed by %s! ===",
                        res.get("nickname"), victim_id, session.nickname)
            self._broadcast_death_event(session, victim_id, session.account_id or DEFAULT_ACCOUNT_ID, session.nickname or "PushpaGG", weapon_id, body_part == 1)

    def _handle_client_fire(self, pkt: UDMPacket, session: ClientSession) -> None:
        """Handle client shooting weapon (Opcode 104 / 5: RUDP_START_FIRE)."""
        logger.info("[COMBAT] RECV Opcode 104/5 (RUDP_START_FIRE) from %s", session.addr)
        if len(pkt.data) >= 4:
            target_id = struct.unpack("<I", pkt.data[:4])[0]
            if target_id in (2, 3, 2000001, 2000002):
                from .match_director import global_match_director
                if global_match_director:
                    global_match_director.handle_player_damage_bot(
                        match_id=session.match_id or generate_match_id(),
                        victim_id=target_id,
                        attacker_id=session.account_id or DEFAULT_ACCOUNT_ID,
                        damage=38.0,
                        body_part=2,
                        weapon_id=101001
                    )

    def _handle_client_movement(self, pkt: UDMPacket, session: ClientSession) -> None:
        """Handle client movement update (Opcode 3 / 1014)."""
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
                            pos_pkt.x, pos_pkt.y, pos_pkt.z,
                            speed=pos_pkt.speed,
                            physx_state=pos_pkt.physx_state,
                            physx_pose=pos_pkt.physx_pose
                        )
                        match.world.update_player_pos(
                            "1",
                            pos_pkt.x, pos_pkt.y, pos_pkt.z,
                            speed=pos_pkt.speed,
                            physx_state=pos_pkt.physx_state,
                            physx_pose=pos_pkt.physx_pose
                        )
                        from .match_director import MatchState
                        if pos_pkt.physx_state in (4, 5) and match.state == MatchState.STATE_3_AIRPLANE_FLIGHT:
                            match.eject_player(str(session.account_id))
                            match.transition_to(MatchState.STATE_4_EJECT_PARACHUTE)
                            logger.info("[MATCH] Player %s transitioned to SKYDIVING via movement physx_state=%d", session.account_id, pos_pkt.physx_state)
            except Exception:
                pass

    def _broadcast_death_event(self, session: ClientSession, victim_id: int, killer_id: int, killer_name: str, weapon_id: int, is_headshot: bool) -> None:
        """Broadcast authoritative death Opcode 107 (RUDP_DEAD) to client session(s)."""
        from .combat_packet_codec import RUDP_Dead
        from .match_director import global_match_director
        match_id = session.match_id or generate_match_id()
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
        """
        Broadcast authoritative match state updates to connected combat sessions.
        
        Handles:
        - STATE_CHANGE events → dispatches Opcode 110 (BattleStart), 443 (Parachute), 117 (SafeZone)
        - Bot position sync → Opcode 3 (Movement) during active combat
        - Scene countdown sync → Opcode 116 (SyncSceneInfo) during Spawn Island
        """
        if ISOLATED_OP101_TEST:
            return
        from .combat_packet_codec import (
            UDP_PlayerPositionOnly, S2C_BattleStart, S2C_ParachuteSync,
            S2C_SyncSceneInfo, RUDP_SafeZoneChange
        )
        from .match_director import global_match_director, MatchState

        if not global_match_director:
            return

        with self.lock:
            active_sessions = [s for s in self.sessions.values() if getattr(s, "combat_stage", 0) >= 4]

        if not active_sessions:
            return

        for session in active_sessions:
            match = global_match_director.get_match(session.match_id)
            if not match:
                match = global_match_director.get_match_for_player(str(session.account_id))
            if not match and global_match_director.active_matches:
                match = list(global_match_director.active_matches.values())[-1]
            if not match:
                continue
            session.match_id = match.match_id

            # Process match events (state transitions, airdrops, zone changes, etc.)
            for result in match_results:
                if result.get("match_id") != session.match_id:
                    continue
                for event in result.get("events", []):
                    ev_type = event.get("type", "")

                    # ── STATE_CHANGE: Dispatch lifecycle opcodes ──
                    if ev_type == "STATE_CHANGE":
                        new_state = event.get("new_state", -1)

                        if new_state == int(MatchState.STATE_3_AIRPLANE_FLIGHT):
                            # Opcode 110: RUDP_BATTLE_START — send airplane flight trajectory
                            battle_bytes = match.build_battle_start_bytes()
                            if battle_bytes:
                                battle_pkt = UDMPacket(
                                    send_option=SendOption.RELIABLE,
                                    cmd=CombatOpcode.RUDP_BATTLE_START,
                                    seq_id=session.next_seq(),
                                    order_id=session.next_order(),
                                    data=battle_bytes
                                )
                                self.send_packet(session, battle_pkt)
                                logger.info("[MATCH] Dispatched Opcode 110 (RUDP_BATTLE_START) to %s", session.addr)

                        elif new_state == int(MatchState.STATE_4_EJECT_PARACHUTE):
                            # Opcode 443: RUDP_TeamParachuteInfo — notify client of eject / skydiving transition
                            for pid in match.human_player_ids:
                                para_bytes = match.build_parachute_sync_bytes(pid)
                                if para_bytes:
                                    para_pkt = UDMPacket(
                                        send_option=SendOption.RELIABLE,
                                        cmd=CombatOpcode.RUDP_TeamParachuteInfo,
                                        seq_id=session.next_seq(),
                                        order_id=session.next_order(),
                                        data=para_bytes
                                    )
                                    self.send_packet(session, para_pkt)
                                    logger.info("[MATCH] Dispatched Opcode 443 (RUDP_TeamParachuteInfo) skydiving for player %s", pid)

                        elif new_state == int(MatchState.STATE_5_COMBAT_LOOTING):
                            # Safe zone initial state on combat start
                            sz_bytes = match.build_safe_zone_bytes()
                            if sz_bytes:
                                sz_pkt = UDMPacket(
                                    send_option=SendOption.RELIABLE,
                                    cmd=CombatOpcode.RUDP_SAFE_ZONE_CHANGE,
                                    seq_id=session.next_seq(),
                                    order_id=session.next_order(),
                                    data=sz_bytes
                                )
                                self.send_packet(session, sz_pkt)
                                logger.info("[MATCH] Dispatched Opcode 117 (RUDP_SAFE_ZONE_CHANGE) to %s", session.addr)

                        elif new_state == int(MatchState.STATE_6_GAME_OVER):
                            # Opcode 451: RUDP_SHOW_MATCH_RESULT — Booyah! / game over
                            # For now just log; payload TBD from further disassembly
                            logger.info("[MATCH] === BOOYAH! Match %d game over for %s ===", session.match_id, session.addr)

                    # ── WAITING_COUNTDOWN: Periodic scene info during Spawn Island ──
                    elif ev_type == "WAITING_COUNTDOWN":
                        if ISOLATED_OP101_TEST or not STAGE_3_ENABLED:
                            continue
                        remaining = event.get("remaining_seconds", 60)
                        last_rem = getattr(session, "_last_broadcast_remaining", -1)
                        # Broadcast every second as countdown ticks down
                        if remaining != last_rem:
                            session._last_broadcast_remaining = remaining
                            scene_bytes = match.build_sync_scene_info_bytes()
                            scene_pkt = UDMPacket(
                                send_option=SendOption.NONE,
                                cmd=CombatOpcode.RUDP_SYNC_SCENE_INFO,
                                seq_id=0,
                                order_id=0,
                                data=scene_bytes
                            )
                            self.send_packet(session, scene_pkt)



                    # ── PLAYER_LANDED: Parachute landing event ──
                    elif ev_type == "PLAYER_LANDED":
                        pid = event.get("player_id", "")
                        para_bytes = match.build_parachute_sync_bytes(pid)
                        if para_bytes:
                            para_pkt = UDMPacket(
                                send_option=SendOption.RELIABLE,
                                cmd=CombatOpcode.RUDP_TeamParachuteInfo,
                                seq_id=session.next_seq(),
                                order_id=session.next_order(),
                                data=para_bytes
                            )
                            self.send_packet(session, para_pkt)
                            logger.info("[MATCH] Dispatched Opcode 443 (RUDP_TeamParachuteInfo) landed for player %s", pid)

                    # ── INITIAL_SPAWN_POSITION / PLAYER_POSITION_SYNC: Opcode 1014 ──
                    elif ev_type in ("INITIAL_SPAWN_POSITION", "PLAYER_POSITION_SYNC"):
                        pos_bytes = event.get("data")
                        if pos_bytes:
                            pos_pkt = UDMPacket(
                                send_option=SendOption.NONE,
                                cmd=CombatOpcode.UDP_PLAYER_POSITION_ONLY,
                                seq_id=0,
                                data=pos_bytes
                            )
                            self.send_packet(session, pos_pkt)
                            session._last_pos_sync_ts = time.time()

            # Continuously sync clock (Opcode 1000) and active entity positions (Opcode 1001 & 1014) at 10 Hz
            now_ts = time.time()
            last_pos_sync = getattr(session, "_last_pos_sync_ts", 0.0)
            if now_ts - last_pos_sync >= 0.1:
                session._last_pos_sync_ts = now_ts
                try:
                    # 1. Opcode 1000: clock sync
                    server_time_val = int((now_ts - getattr(session, "created_time", now_ts)) * 1000) & 0xFFFFFFFF
                    # Opcode 1000 (clock sync) intentionally not sent: the client parses opcode 1000 with
        # message.dEa^CT (Int32 count + count*7B items), so the 4-byte timestamp we produced
        # was read as a huge element count and raised EndOfStreamException in
        # MatchGameClient.HandleRecvPacket (Bugly SIGABRT). The match does not require it.
                    # pkt_1000 = UDMPacket(
                    #     send_option=SendOption.NONE,
                    #     cmd=CombatOpcode.UDP_SYNC_SERVER_TIME,
                    #     seq_id=0,
                    #     order_id=0,
                    #     flags=0,
                    #     data=struct.pack("<I", server_time_val)
                    # )
                    # self.send_packet(session, pkt_1000)

                    # 2. Position updates
                    batch_bytes = match.build_player_position_batch_bytes()
                    if batch_bytes:
                        # Opcode 1014
                        pos_pkt = UDMPacket(
                            send_option=SendOption.NONE,
                            cmd=CombatOpcode.UDP_PLAYER_POSITION_ONLY,
                            seq_id=0,
                            data=batch_bytes
                        )
                        self.send_packet(session, pos_pkt)

                        # Opcode 1001: player state sync
                        from .combat_packet_codec import UDP_PlayerPositionBatch, UDP_PlayerStateSync
                        p_batch = UDP_PlayerPositionBatch.unserialize(batch_bytes)
                        if p_batch and p_batch.players:
                            state_pkt = UDMPacket(
                                send_option=SendOption.NONE,
                                cmd=CombatOpcode.UDP_PLAYER_STATE_SYNC,
                                seq_id=0,
                                data=UDP_PlayerStateSync(server_time_ms=server_time_val, flags=0, players=p_batch.players).serialize()
                            )
                            self.send_packet(session, state_pkt)
                except Exception as e:
                    logger.debug("Player & bot position sync error: %s", e)


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
