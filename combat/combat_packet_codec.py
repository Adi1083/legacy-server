"""
Free Fire 1.39 Authoritative In-Game Combat Packet Codec.
Implements exact binary serialization matching Barbosa IL2CPP Metadata v23 (TypeDefs [4464]..[4587]).

Wire encoding rules:
- Primitives: Little-Endian (<)
- Strings: 7-bit variable-length integer encoded length prefix followed by UTF-8 bytes (.NET BinaryWriter standard)
- Vectors: 3x 32-bit float (x, y, z)
- Rotations: float yaw, float pitch
"""

import struct
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

from .combat_opcodes import CombatOpcode


# ---------------------------------------------------------------------------
# String & Varint Helpers (.NET BinaryReader / BinaryWriter format)
# ---------------------------------------------------------------------------

def encode_dotnet_string(s: str) -> bytes:
    """Encodes a string with .NET BinaryWriter 7-bit length prefix."""
    raw = s.encode("utf-8")
    buf = bytearray()
    length = len(raw)
    while length >= 0x80:
        buf.append((length | 0x80) & 0xff)
        length >>= 7
    buf.append(length & 0x7f)
    buf.extend(raw)
    return bytes(buf)


def decode_dotnet_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """Decodes a string with .NET BinaryReader 7-bit length prefix. Returns (string, new_offset)."""
    length = 0
    shift = 0
    pos = offset
    while pos < len(data):
        b = data[pos]
        pos += 1
        length |= (b & 0x7f) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    s = data[pos:pos+length].decode("utf-8", errors="replace")
    return s, pos + length


def encode_udp_string(s: str) -> bytes:
    """Encodes a string for GCommon.UDPClientMessageBase.ReadString:
    4-byte Int32 length prefix (Little-Endian) followed by UTF-8 bytes."""
    raw = (s or "").encode("utf-8")
    return struct.pack("<i", len(raw)) + raw


def decode_udp_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """Decodes a string for GCommon.UDPClientMessageBase.ReadString:
    4-byte Int32 length prefix (Little-Endian) followed by UTF-8 bytes."""
    if len(data) < offset + 4:
        return "", offset
    length, = struct.unpack("<i", data[offset:offset+4])
    offset += 4
    if length <= 0:
        return "", offset
    if len(data) < offset + length:
        raw = data[offset:]
        return raw.decode("utf-8", errors="replace"), len(data)
    s = data[offset:offset+length].decode("utf-8", errors="replace")
    return s, offset + length


# ---------------------------------------------------------------------------
# 1. Match Join Handshake: C2S_RUDP_JoinMatch (100) & S2C_RUDP_JoinMatchRes
# ---------------------------------------------------------------------------

@dataclass
class C2S_JoinMatch:
    """TypeDef [4587]: message.B}vNjXD (RUDP_JOIN_MATCH = 100)"""
    prepare_token: str
    match_id: int
    account_id: int

    def serialize(self) -> bytes:
        buf = bytearray()
        tok_bytes = self.prepare_token.encode("utf-8")
        buf.extend(struct.pack("<I", len(tok_bytes)))
        buf.extend(tok_bytes)
        buf.extend(struct.pack("<QQ", self.match_id, self.account_id))
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes) -> "C2S_JoinMatch":
        if not data or len(data) < 4:
            return cls("", 0, 0)
        tok_len = struct.unpack("<I", data[:4])[0]
        if tok_len <= len(data) - 4:
            token = data[4:4+tok_len].decode("utf-8", errors="ignore")
            offset = 4 + tok_len
        else:
            token, offset = decode_dotnet_string(data, 0)
        if len(data) >= offset + 16:
            match_id, account_id = struct.unpack("<QQ", data[offset:offset+16])
        else:
            match_id, account_id = 0, 0
        return cls(token, match_id, account_id)


@dataclass
class S2C_JoinMatchRes:
    """TypeDef [4580]: message.nSa~rX (RUDP_JOIN_MATCH = 100).

    Layout measured on the real client (Frida read trace + live vtable slot
    resolution), not inferred from metadata:

    Header, 39B (<IQQiBIHII>): err_code, account_id, match_id, server_time,
        map_id, waiting_seconds, weather_style, game_mode, room_type

    Nested message.j]VkzA, 26B:
        phase    Int16                                        2B
        current  message.My^x~o (0x1eec3e3: ReadInt32 x3) 12B
        next     same class                                  12B

    Collections + trailer, 16B:
        list<int> count | list<uint> count | list<msg> count | trailing UInt32

    Total: 39 + 26 + 16 = 81 bytes.

    The earlier 34B block of four float32 per circle (2 + 16 + 16) was the
    match-entry abort: the client reads three Int32 per circle, so our radius
    600.0f landed on the second circle's first field and again on the second
    collection count, producing a multi-million element list read that ran off
    the packet and raised EndOfStreamException in
    MatchClient.HandleRecvPacket (logcat: Fatal signal 6 in UnityMain).
    """
    err_code: int = 0         # message.qLLZWho: 0 = ERR_NONE
    account_id: int = 10001
    match_id: int = 1000001
    server_time: int = 0      # UNIX timestamp
    map_id: int = 1           # 1 = Bermuda
    waiting_seconds: int = 60 # 60s Spawn Island countdown
    weather_style: int = 1    # Visual style
    game_mode: int = 1        # 1 = Battle Royale
    room_type: int = 0        # 0 = Casual
    safe_zone_center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    safe_zone_radius: float = 600.0
    next_safe_zone_center: Optional[Tuple[float, float, float]] = None
    next_safe_zone_radius: Optional[float] = None
    phase: int = 0

    def __post_init__(self):
        if self.next_safe_zone_center is None:
            self.next_safe_zone_center = self.safe_zone_center
        if self.next_safe_zone_radius is None:
            self.next_safe_zone_radius = self.safe_zone_radius

    def serialize(self) -> bytes:
        buf = bytearray(struct.pack(
            "<IQQiBIHII",
            int(self.err_code),
            int(self.account_id),
            int(self.match_id),
            int(self.server_time),
            int(self.map_id),
            int(self.waiting_seconds),
            int(self.weather_style),
            int(self.game_mode),
            int(self.room_type),
        ))
        # Nested message.j]\x82VkzA: Int16 phase + two message.My^x~\x81o circles,
        # each exactly three Int32 (live vtable target 0x1eec3e3).
        buf.extend(struct.pack(
            "<hiiiiii",
            int(self.phase),
            int(self.safe_zone_center[0]),
            int(self.safe_zone_center[2]),
            int(self.safe_zone_radius),
            int(self.next_safe_zone_center[0]),
            int(self.next_safe_zone_center[2]),
            int(self.next_safe_zone_radius),
        ))
        # list<int> count, list<uint> count, list<message> count, trailing UInt32
        buf.extend(struct.pack("<III", 0, 0, 0))
        buf.extend(struct.pack("<I", 0))
        return bytes(buf)

    def serialize_compact(self) -> bytes:
        """Authentic 16-byte wire payload as captured from live Barbosa combat server."""
        return struct.pack("<IQI", self.err_code, self.match_id, self.server_time)

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_JoinMatchRes":
        """Decodes the measured 81-byte wire payload."""
        header = struct.unpack("<IQQiBIHII", data[:39])
        phase, cx, cz, cr, nx, nz, nr = struct.unpack("<hiiiiii", data[39:65])
        return cls(
            err_code=header[0],
            account_id=header[1],
            match_id=header[2],
            server_time=header[3],
            map_id=header[4],
            waiting_seconds=header[5],
            weather_style=header[6],
            game_mode=header[7],
            room_type=header[8],
            safe_zone_center=(float(cx), 0.0, float(cz)),
            safe_zone_radius=float(cr),
            next_safe_zone_center=(float(nx), 0.0, float(nz)),
            next_safe_zone_radius=float(nr),
            phase=phase
        )


# ---------------------------------------------------------------------------
# 2. Player Join: S2C_RUDP_PlayerJoin (101)
# ---------------------------------------------------------------------------

@dataclass
class S2C_PlayerJoin:
    """TypeDef [4579]: message.ae zaPn (RUDP_PLAYER_JOIN = 101)
    
    18 sequential fields established by IL2CPP disassembly of
    message.ae zaPn.UnSerialize (RVA 0x01fafc18) and Serialize (RVA 0x1fb07e9):
      1. UInt64  account_id
      2. UInt64  match_id
      3. Byte    camp
      4. Byte    is_bot (0=human, 1=bot)
      5. UInt64  team_id
      6. String  nickname (Int32 len + UTF-8)
      7. UInt32  avatar_id
      8. Boolean is_ready
      9. UInt32  level
     10. UInt32  rank
     11. Boolean is_alive
     12. List    clothes (Int32 count + count * UInt64)
     13. Byte    gender
     14. Boolean flag
     15. List    skills (Int32 count + count * UInt32)
     16. String  region (Int32 len + UTF-8)
     17. UInt32  banner_id
     18. String  headpic (Int32 len + UTF-8)
    """
    account_id: int
    match_id: int
    camp: int = 1
    is_bot: bool = False
    team_id: int = 1
    nickname: str = ""
    avatar_id: int = 1010001
    is_ready: bool = True
    level: int = 25
    rank: int = 1800
    is_alive: bool = True
    clothes: List[int] = None
    gender: int = 1
    flag: bool = False
    skills: List[int] = None
    region: str = "IND"
    banner_id: int = 901000001
    headpic: str = ""
    player_id: int = 1  # Compatibility alias for server tracking (not serialized on wire)

    def __post_init__(self):
        if self.clothes is None:
            self.clothes = []
        if self.skills is None:
            self.skills = []

    def serialize(self) -> bytes:
        buf = bytearray()
        # 1. account_id (UInt64)
        # 2. match_id (UInt64)
        # 3. camp (Byte)
        # 4. is_bot (Byte)
        # 5. team_id (UInt64)
        buf.extend(struct.pack(
            "<QQBBQ",
            int(self.account_id) & 0xFFFFFFFFFFFFFFFF,
            int(self.match_id) & 0xFFFFFFFFFFFFFFFF,
            int(self.camp) & 0xFF,
            1 if self.is_bot else 0,
            int(self.team_id) & 0xFFFFFFFFFFFFFFFF
        ))
        # 6. nickname (String: Int32 len + UTF-8 bytes)
        buf.extend(encode_udp_string(self.nickname))
        # 7. avatar_id (UInt32)
        # 8. is_ready (Boolean)
        # 9. level (UInt32)
        # 10. rank (UInt32)
        # 11. is_alive (Boolean)
        buf.extend(struct.pack(
            "<I?II?",
            int(self.avatar_id) & 0xFFFFFFFF,
            bool(self.is_ready),
            int(self.level) & 0xFFFFFFFF,
            int(self.rank) & 0xFFFFFFFF,
            bool(self.is_alive)
        ))
        # 12. clothes (Int32 count + count * UInt64)
        clothes_list = self.clothes or []
        buf.extend(struct.pack("<i", len(clothes_list)))
        for cid in clothes_list:
            buf.extend(struct.pack("<Q", int(cid) & 0xFFFFFFFFFFFFFFFF))
        # 13. gender (Byte)
        # 14. flag (Boolean)
        buf.extend(struct.pack(
            "<B?",
            int(self.gender) & 0xFF,
            bool(self.flag)
        ))
        # 15. skills (Int32 count + count * UInt32)
        skills_list = self.skills or []
        buf.extend(struct.pack("<i", len(skills_list)))
        for sid in skills_list:
            buf.extend(struct.pack("<I", int(sid) & 0xFFFFFFFF))
        # 16. region (String: Int32 len + UTF-8 bytes)
        buf.extend(encode_udp_string(self.region))
        # 17. banner_id (UInt32)
        buf.extend(struct.pack("<I", int(self.banner_id) & 0xFFFFFFFF))
        # 18. headpic (String: Int32 len + UTF-8 bytes)
        buf.extend(encode_udp_string(self.headpic))
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_PlayerJoin":
        offset = 0
        account_id, match_id, camp, is_bot_raw, team_id = struct.unpack("<QQBBQ", data[offset:offset+26])
        offset += 26
        nickname, offset = decode_udp_string(data, offset)
        avatar_id, is_ready, level, rank, is_alive = struct.unpack("<I?II?", data[offset:offset+14])
        offset += 14
        clothes_count, = struct.unpack("<i", data[offset:offset+4])
        offset += 4
        clothes = []
        for _ in range(max(0, clothes_count)):
            cid, = struct.unpack("<Q", data[offset:offset+8])
            clothes.append(cid)
            offset += 8
        gender, flag = struct.unpack("<B?", data[offset:offset+2])
        offset += 2
        skills_count, = struct.unpack("<i", data[offset:offset+4])
        offset += 4
        skills = []
        for _ in range(max(0, skills_count)):
            sid, = struct.unpack("<I", data[offset:offset+4])
            skills.append(sid)
            offset += 4
        region, offset = decode_udp_string(data, offset)
        banner_id, = struct.unpack("<I", data[offset:offset+4])
        offset += 4
        headpic, offset = decode_udp_string(data, offset)
        return cls(
            account_id=account_id,
            match_id=match_id,
            camp=camp,
            is_bot=bool(is_bot_raw),
            team_id=team_id,
            nickname=nickname,
            avatar_id=avatar_id,
            is_ready=is_ready,
            level=level,
            rank=rank,
            is_alive=is_alive,
            clothes=clothes,
            gender=gender,
            flag=flag,
            skills=skills,
            region=region,
            banner_id=banner_id,
            headpic=headpic,
            player_id=1
        )


# ---------------------------------------------------------------------------
# 3. Scene State & Countdown Sync: S2C_RUDP_SyncSceneInfo (116)
# ---------------------------------------------------------------------------

@dataclass
class S2C_SyncSceneInfo:
    """TypeDef [4580] variation: (RUDP_SYNC_SCENE_INFO = 116)"""
    match_id: int
    elapsed_time: float
    countdown_seconds: float
    alive_players: int
    spawn_island_x: float = -500.0
    spawn_island_y: float = 10.0
    spawn_island_z: float = 800.0
    spawn_island_radius: float = 60.0

    def serialize(self) -> bytes:
        return struct.pack(
            "<QffI ffff",
            self.match_id,
            float(self.elapsed_time),
            float(self.countdown_seconds),
            int(self.alive_players),
            float(self.spawn_island_x),
            float(self.spawn_island_y),
            float(self.spawn_island_z),
            float(self.spawn_island_radius)
        )

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_SyncSceneInfo":
        mid, elapsed, countdown, alive, x, y, z, r = struct.unpack("<QffIffff", data[:36])
        return cls(
            match_id=mid,
            elapsed_time=elapsed,
            countdown_seconds=countdown,
            alive_players=alive,
            spawn_island_x=x,
            spawn_island_y=y,
            spawn_island_z=z,
            spawn_island_radius=r
        )


# ---------------------------------------------------------------------------
# 4. Airplane & Battle Start: S2C_RUDP_BattleStart (110)
# ---------------------------------------------------------------------------

@dataclass
class S2C_BattleStart:
    """TypeDef [4571]: message.DtAJjUT (RUDP_BATTLE_START = 110)"""
    match_id: int
    start_pos: Tuple[float, float, float]
    end_pos: Tuple[float, float, float]
    altitude: float = 420.0
    flight_speed: float = 65.0
    flight_duration: float = 30.0

    def serialize(self) -> bytes:
        return struct.pack(
            "<Q fff fff fff",
            self.match_id,
            float(self.start_pos[0]), float(self.start_pos[1]), float(self.start_pos[2]),
            float(self.end_pos[0]), float(self.end_pos[1]), float(self.end_pos[2]),
            float(self.altitude),
            float(self.flight_speed),
            float(self.flight_duration)
        )

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_BattleStart":
        vals = struct.unpack("<Qfffffffff", data[:44])
        return cls(
            match_id=vals[0],
            start_pos=(vals[1], vals[2], vals[3]),
            end_pos=(vals[4], vals[5], vals[6]),
            altitude=vals[7],
            flight_speed=vals[8],
            flight_duration=vals[9]
        )


# ---------------------------------------------------------------------------
# 5. Parachute Deployment: S2C_RUDP_TeamParachuteInfo (443)
# ---------------------------------------------------------------------------

@dataclass
class S2C_ParachuteSync:
    """TypeDef [4464] opcode 443 (RUDP_TeamParachuteInfo)"""
    player_id: int
    phase: int           # 0=Plane, 1=Skydiving, 2=Parachute Open, 3=Landed
    x: float
    y: float
    z: float
    velocity_y: float
    forward_speed: float
    yaw: float
    parachute_id: int = 902001

    def serialize(self) -> bytes:
        return struct.pack(
            "<IB fff fff I",
            self.player_id,
            self.phase,
            float(self.x), float(self.y), float(self.z),
            float(self.velocity_y), float(self.forward_speed), float(self.yaw),
            self.parachute_id
        )


# ---------------------------------------------------------------------------
# 6. High-Frequency Movement: UDP_PLAYER_POSITION_ONLY (1014) & UDP_SYNC_AIM_ROTATION (1016)
# ---------------------------------------------------------------------------

@dataclass
class PlayerPosItem:
    """TypeDef [4537]: message. jqCaJw (15 bytes)
    Used within message.Ctdp€Ud (Opcode 1014: UDP_PLAYER_POSITION_ONLY)
    - player_id: uint8 (1 byte, e.g. 1 for human, 2 for bot1, 3 for bot2)
    - pos: message.My^x~ o (12 bytes, 3x int32 scaled in millimeters: int(coord * 1000))
    - physx_state: uint8 (1 byte)
    - physx_pose: uint8 (1 byte)
    """
    player_id: int
    x: float
    y: float
    z: float
    physx_state: int = 0
    physx_pose: int = 0

    def serialize(self) -> bytes:
        ix = int(self.x * 1000)
        iy = int(self.y * 1000)
        iz = int(self.z * 1000)
        return struct.pack(
            "<B iii BB",
            self.player_id & 0xFF,
            ix, iy, iz,
            self.physx_state & 0xFF,
            self.physx_pose & 0xFF
        )

    @classmethod
    def unserialize(cls, data: bytes, offset: int = 0) -> Tuple["PlayerPosItem", int]:
        if len(data) < offset + 15:
            return cls(0, 0.0, 0.0, 0.0, 0, 0), offset
        pid, ix, iy, iz, state, pose = struct.unpack("<B iii BB", data[offset:offset+15])
        return cls(pid, ix / 1000.0, iy / 1000.0, iz / 1000.0, state, pose), offset + 15


@dataclass
class UDP_PlayerPositionBatch:
    """TypeDef [4607]: message.Ctdp€Ud (UDP_PLAYER_POSITION_ONLY = 1014)
    Wire Layout:
    - [4B int32 count1] (number of PlayerPosItem elements)
    - [count1 * 15B PlayerPosItem elements]
    - [4B int32 count2] (secondary list count, always 0)
    - [4B int32 timestamp] (tick timestamp / seq)
    """
    players: List[PlayerPosItem]
    timestamp: int = 0

    def serialize(self) -> bytes:
        buf = bytearray(struct.pack("<i", len(self.players)))
        for p in self.players:
            buf.extend(p.serialize())
        buf.extend(struct.pack("<ii", 0, self.timestamp))
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes) -> "UDP_PlayerPositionBatch":
        if len(data) < 8:
            return cls([], 0)
        count, = struct.unpack("<i", data[:4])
        players = []
        offset = 4
        for _ in range(count):
            if offset + 15 > len(data):
                break
            item, offset = PlayerPosItem.unserialize(data, offset)
            players.append(item)
        ts = 0
        if offset + 8 <= len(data):
            _, ts = struct.unpack("<ii", data[offset:offset+8])
        return cls(players, ts)


@dataclass
class UDP_SyncServerTime:
    """TypeDef [23283]: Opcode 1000 (UDP_SYNC_SERVER_TIME) - 4 bytes uint32 server time / tick."""
    server_time: int = 0

    def serialize(self) -> bytes:
        return struct.pack("<I", self.server_time & 0xFFFFFFFF)

    @classmethod
    def unserialize(cls, data: bytes) -> "UDP_SyncServerTime":
        val = struct.unpack("<I", data[:4])[0] if len(data) >= 4 else 0
        return cls(val)


@dataclass
class UDP_PlayerStateSync:
    """TypeDef [23284]: Opcode 1001 (UDP_PLAYER_STATE_SYNC) - High frequency player sync.
    Wire Layout:
    - [4B uint32 server_time_ms]
    - [4B uint32 flags / tick]
    - [4B uint32 count]
    - [count * 15B PlayerPosItem elements]
    """
    server_time_ms: int = 0
    flags: int = 0
    players: List[PlayerPosItem] = None

    def __post_init__(self):
        if self.players is None:
            self.players = []

    def serialize(self) -> bytes:
        buf = bytearray(struct.pack("<III", self.server_time_ms & 0xFFFFFFFF, self.flags & 0xFFFFFFFF, len(self.players)))
        for p in self.players:
            buf.extend(p.serialize())
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes) -> "UDP_PlayerStateSync":
        if len(data) < 12:
            return cls(0, 0, [])
        ts, flags, count = struct.unpack("<III", data[:12])
        players = []
        offset = 12
        for _ in range(count):
            if offset + 15 > len(data):
                break
            item, offset = PlayerPosItem.unserialize(data, offset)
            players.append(item)
        return cls(ts, flags, players)


@dataclass
class UDP_PlayerPositionOnly:
    """Compatibility wrapper for UDP_PLAYER_POSITION_ONLY = 1014.
    Serializes a single entity as a valid 1-item message.Ctdp€Ud batch packet (27 bytes).
    """
    player_id: int
    x: float
    y: float
    z: float
    speed: float = 0.0
    physx_state: int = 0
    physx_pose: int = 0

    def serialize(self) -> bytes:
        item = PlayerPosItem(
            player_id=self.player_id,
            x=self.x,
            y=self.y,
            z=self.z,
            physx_state=self.physx_state,
            physx_pose=self.physx_pose
        )
        batch = UDP_PlayerPositionBatch(players=[item], timestamp=0)
        return batch.serialize()

    @classmethod
    def unserialize(cls, data: bytes) -> "UDP_PlayerPositionOnly":
        batch = UDP_PlayerPositionBatch.unserialize(data)
        if batch.players:
            p = batch.players[0]
            return cls(p.player_id, p.x, p.y, p.z, 0.0, p.physx_state, p.physx_pose)
        if len(data) >= 22:
            try:
                pid, x, y, z = struct.unpack("<Ifff", data[:16])
                return cls(pid, x, y, z, 0.0, 0, 0)
            except Exception:
                pass
        return cls(0, 0.0, 0.0, 0.0, 0.0, 0, 0)


@dataclass
class UDP_SyncAimRotation:
    """TypeDef [4563]: message.^M `Enj (UDP_SYNC_AIM_ROTATION = 1016)"""
    player_id: int
    yaw: float
    pitch: float

    def serialize(self) -> bytes:
        return struct.pack("<Hff", self.player_id & 0xffff, float(self.yaw), float(self.pitch))

    @classmethod
    def unserialize(cls, data: bytes) -> "UDP_SyncAimRotation":
        pid, yaw, pitch = struct.unpack("<Hff", data[:10])
        return cls(pid, yaw, pitch)


# ---------------------------------------------------------------------------
# 7. Weapon Fire, Damage, Death, Safe Zone
# ---------------------------------------------------------------------------

@dataclass
class RUDP_StartFire:
    """TypeDef [4535]: message.b^GQwPC (RUDP_START_FIRE = 104)"""
    shooter_id: int
    weapon_id: int
    origin_x: float
    origin_y: float
    origin_z: float
    dir_x: float
    dir_y: float
    dir_z: float
    fire_mode: int = 1

    def serialize(self) -> bytes:
        return struct.pack(
            "<II fff fff B",
            self.shooter_id,
            self.weapon_id,
            float(self.origin_x), float(self.origin_y), float(self.origin_z),
            float(self.dir_x), float(self.dir_y), float(self.dir_z),
            self.fire_mode
        )


@dataclass
class RUDP_TakeDamage:
    """TypeDef [4544]: message.RfRyewp (RUDP_TAKE_DAMAGE = 106)"""
    victim_id: int
    attacker_id: int
    damage: float
    body_part: int       # 1=Head, 2=Body, 3=Limb
    weapon_id: int
    remaining_hp: int
    remaining_armor: int
    hit_pos: Tuple[float, float, float]

    def serialize(self) -> bytes:
        return struct.pack(
            "<IIfBIBHHfff",
            self.victim_id,
            self.attacker_id,
            float(self.damage),
            self.body_part,
            self.weapon_id,
            1 if self.remaining_hp <= 0 else 0, # is_fatal
            self.remaining_hp,
            self.remaining_armor,
            float(self.hit_pos[0]), float(self.hit_pos[1]), float(self.hit_pos[2])
        )

    @classmethod
    def unserialize(cls, data: bytes) -> "RUDP_TakeDamage":
        if len(data) >= 34:
            v_id, a_id, dmg, part, wid, fatal, rem_hp, rem_arm, hx, hy, hz = struct.unpack("<IIfBIBHHfff", data[:34])
            return cls(v_id, a_id, dmg, part, wid, rem_hp, rem_arm, (hx, hy, hz))
        elif len(data) >= 8:
            v_id, a_id = struct.unpack("<II", data[:8])
            return cls(v_id, a_id, 35.0, 2, 101001, 100, 50, (0.0, 0.0, 0.0))
        elif len(data) >= 4:
            v_id, = struct.unpack("<I", data[:4])
            return cls(v_id, 1, 35.0, 2, 101001, 100, 50, (0.0, 0.0, 0.0))
        return cls(0, 0, 35.0, 2, 101001, 0, 0, (0.0, 0.0, 0.0))


@dataclass
class RUDP_Dead:
    """TypeDef [4559]: message.K~|bywX (RUDP_DEAD = 107)"""
    victim_id: int
    killer_id: int
    killer_name: str
    weapon_id: int
    is_headshot: bool
    rank: int
    kills: int
    is_suicide: bool = False

    def serialize(self) -> bytes:
        buf = bytearray()
        buf.extend(struct.pack("<QQ", self.victim_id, self.killer_id))
        buf.extend(encode_dotnet_string(self.killer_name))
        buf.extend(struct.pack(
            "<IBhhBB",
            self.weapon_id,
            1 if self.is_headshot else 0,
            self.rank,
            self.kills,
            1 if self.is_suicide else 0,
            0
        ))
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes) -> "RUDP_Dead":
        if len(data) >= 16:
            victim_id, killer_id = struct.unpack("<QQ", data[:16])
            killer_name, offset = decode_dotnet_string(data, 16)
            if len(data) >= offset + 11:
                weapon_id, hs, rank, kills, sui, _ = struct.unpack("<IBhhBB", data[offset:offset+11])
                return cls(victim_id, killer_id, killer_name, weapon_id, bool(hs), rank, kills, bool(sui))
            return cls(victim_id, killer_id, killer_name, 101001, False, 1, 1, False)
        elif len(data) >= 8:
            victim_id, killer_id = struct.unpack("<II", data[:8])
            return cls(victim_id, killer_id, "Player", 101001, False, 1, 1, False)
        elif len(data) >= 4:
            victim_id, = struct.unpack("<I", data[:4])
            return cls(victim_id, 1, "Player", 101001, False, 1, 1, False)
        return cls(0, 0, "Player", 101001, False, 1, 1, False)


@dataclass
class RUDP_SafeZoneChange:
    """TypeDef [4560]: message.j]‚VkzA (RUDP_SAFE_ZONE_CHANGE = 117)
    
    Wire layout (total 34 bytes):
    - [2B int16 phase] (Field [24017]: pc}wE]‚)
    - [16B 4x float32 Circle 1 Current: x, y, z, radius] (Field [24018]: tmixIrA -> message.My^x~ o)
    - [16B 4x float32 Circle 2 Next: x, y, z, radius] (Field [24019]: ~zmrkpb -> message.My^x~ o)
    Total SafeZone Wire Format: 2 + 16 + 16 = 34 bytes (<hffffffff)
    """
    phase: int
    current_x: float
    current_y: float
    current_z: float
    current_radius: float
    next_x: float
    next_y: float
    next_z: float
    next_radius: float
    shrink_duration: float = 0.0      # Optional metadata (simulation-side)
    damage_per_second: float = 0.0    # Optional metadata (simulation-side)

    def serialize(self) -> bytes:
        return struct.pack(
            "<hffffffff",
            self.phase,
            float(self.current_x), float(self.current_y), float(self.current_z), float(self.current_radius),
            float(self.next_x), float(self.next_y), float(self.next_z), float(self.next_radius),
        )

    @classmethod
    def unserialize(cls, data: bytes) -> "RUDP_SafeZoneChange":
        phase, cx, cy, cz, cr, nx, ny, nz, nr = struct.unpack("<hffffffff", data[:34])
        return cls(phase, cx, cy, cz, cr, nx, ny, nz, nr)


@dataclass
class RUDP_BindPRI:
    """TypeDef [23055]: Opcode 118 (RUDP_BIND_PRI) - Priority Channel / Replication Binding.
    
    Wire layout (total 24 bytes):
    - [8B uint64 account_id]
    - [4B uint32 entity_id]
    - [4B uint32 pri_id = 0]
    - [8B uint64 reserved = 0]
    Total Wire Format: 8 + 4 + 4 + 8 = 24 bytes (<QIIQ)
    """
    account_id: int
    entity_id: int = 1
    pri_id: int = 0
    reserved: int = 0

    def serialize(self) -> bytes:
        return struct.pack("<QIIQ", self.account_id, self.entity_id, self.pri_id, self.reserved)

    @classmethod
    def unserialize(cls, data: bytes) -> "RUDP_BindPRI":
        acc, eid, pid, res = struct.unpack("<QIIQ", data[:24])
        return cls(account_id=acc, entity_id=eid, pri_id=pid, reserved=res)


# ---------------------------------------------------------------------------
# Opcode 170: RUDP_SYNC_REGION_ACTIVITIES
# ---------------------------------------------------------------------------
from .codec_op170 import RegionActivityItem, S2C_SyncRegionActivities, RUDP_SyncRegionActivities

# ---------------------------------------------------------------------------
# Opcode 130: RUDP_JOIN_MATCH_FINISHED
# ---------------------------------------------------------------------------
from .codec_op130 import JoinMatchFinishedPacket, RUDP_JoinMatchFinished

# ---------------------------------------------------------------------------
# Opcode 278: RUDP_SyncShowCase
# ---------------------------------------------------------------------------
from .codec_op278 import ShowCaseItem, S2C_SyncShowCase, RUDP_SyncShowCase

# ---------------------------------------------------------------------------
# Opcode 135: RUDP_SYNC_PLAYERS_VISIBILITY
# ---------------------------------------------------------------------------
from .codec_op135 import PlayerVisibilityItem, S2C_SyncPlayersVisibility, RUDP_SyncPlayersVisibility

# ---------------------------------------------------------------------------
# Opcode 501: RUDP_VAR_SYNC_GRI_DATA
# ---------------------------------------------------------------------------
from .codec_op501 import ReplicationItem, S2C_VarSyncGRIData, RUDP_VarSyncGRIData


