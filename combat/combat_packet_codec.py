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
        buf.extend(encode_dotnet_string(self.prepare_token))
        buf.extend(struct.pack("<QQ", self.match_id, self.account_id))
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes) -> "C2S_JoinMatch":
        token, offset = decode_dotnet_string(data, 0)
        match_id, account_id = struct.unpack("<QQ", data[offset:offset+16])
        return cls(token, match_id, account_id)


@dataclass
class S2C_JoinMatchRes:
    """TypeDef [4580]: message. nSa~rX (RUDP_JOIN_MATCH_FINISHED = 31)
    
    Wire layout (total 89 bytes):
    - [4B int32 err_code] (message.qLLZWho)
    - [8B uint64 match_id]
    - [8B uint64 account_id]
    - [4B uint32 server_time]
    - [1B uint8 map_id]
    - [4B int32 waiting_seconds]
    - [2B uint16 weather_style]
    - [4B int32 game_mode] (message.BuSs|~s)
    - [4B int32 room_type] (message.o[OXXhp)
    Total Header: 39 bytes (<iQQIBiHii)
    
    Nested SafeZone (TypeDef [4560]: message.j]‚VkzA):
    - [2B int16 phase]
    - [16B 4x float32 Circle 1 Current: x, y, z, radius]
    - [16B 4x float32 Circle 2 Next: x, y, z, radius]
    Total SafeZone: 34 bytes (<hffffffff)
    
    Trailing Barbosa Collection Fields (TypeDef [4580] fields 11..14):
    - [4B int32 field11_count = 0] (List<int>)
    - [4B int32 field12_count = 0] (List<uint>)
    - [4B int32 field13_count = 0] (List<Nested>)
    - [4B uint32 field14_val = 0]
    Total Trailing: 16 bytes (<iiii)
    Grand Total: 39 + 34 + 16 = 89 bytes
    """
    err_code: int = 0         # message.qLLZWho: 0 = ERR_NONE
    match_id: int = 10001
    account_id: int = 1000001
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
        buf = bytearray()
        # Header (39 bytes): [4B err_code][8B match_id][8B account_id][4B server_time][1B map_id][4B waiting_sec][2B weather][4B game_mode][4B room_type]
        buf.extend(struct.pack(
            "<iQQIBiHii",
            self.err_code,
            self.match_id,
            self.account_id,
            self.server_time,
            self.map_id,
            self.waiting_seconds,
            self.weather_style,
            self.game_mode,
            self.room_type,
        ))
        # Initial Safe Zone (TypeDef [4560]: message.j]‚VkzA)
        # Wire layout: [2B phase][16B Circle 1 Current: x, y, z, radius][16B Circle 2 Next: x, y, z, radius] = 34B
        buf.extend(struct.pack(
            "<hffffffff",
            self.phase,
            float(self.safe_zone_center[0]),
            float(self.safe_zone_center[1]),
            float(self.safe_zone_center[2]),
            float(self.safe_zone_radius),
            float(self.next_safe_zone_center[0]),
            float(self.next_safe_zone_center[1]),
            float(self.next_safe_zone_center[2]),
            float(self.next_safe_zone_radius)
        ))
        # Authentic Barbosa trailing fields (TypeDef [4580] fields 11..14):
        # Field 11: List<int> (count int32 = 0)
        # Field 12: List<uint> (count int32 = 0)
        # Field 13: List<Nested> (count int32 = 0)
        # Field 14: uint32 = 0
        buf.extend(struct.pack("<iiii", 0, 0, 0, 0))
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_JoinMatchRes":
        """Decodes exact 89-byte wire payload."""
        header = struct.unpack("<iQQIBiHii", data[:39])
        phase, cx, cy, cz, cr, nx, ny, nz, nr = struct.unpack("<hffffffff", data[39:73])
        # Trailing 16 bytes: f11_cnt, f12_cnt, f13_cnt, f14_val = struct.unpack("<iiii", data[73:89])
        return cls(
            err_code=header[0],
            match_id=header[1],
            account_id=header[2],
            server_time=header[3],
            map_id=header[4],
            waiting_seconds=header[5],
            weather_style=header[6],
            game_mode=header[7],
            room_type=header[8],
            safe_zone_center=(cx, cy, cz),
            safe_zone_radius=cr,
            next_safe_zone_center=(nx, ny, nz),
            next_safe_zone_radius=nr,
            phase=phase
        )


# ---------------------------------------------------------------------------
# 2. Player Join: S2C_RUDP_PlayerJoin (101)
# ---------------------------------------------------------------------------

@dataclass
class S2C_PlayerJoin:
    """TypeDef [4579]: message.ae zaPn (RUDP_PLAYER_JOIN = 101)"""
    player_id: int
    account_id: int
    team_id: int
    camp: int
    match_id: int
    nickname: str
    avatar_id: int
    is_bot: bool
    level: int = 25
    rank: int = 1800
    is_ready: bool = True
    clothes: List[int] = None
    gender: int = 1
    is_alive: bool = True
    skills: List[int] = None
    region: str = "NA"
    banner_id: int = 901001
    headpic: str = "avatar_01"

    def __post_init__(self):
        if self.clothes is None:
            self.clothes = [101001, 102001, 103001, 104001]
        if self.skills is None:
            self.skills = [1, 2]

    def serialize(self) -> bytes:
        buf = bytearray()
        buf.extend(struct.pack("<QQBBQ", self.player_id, self.account_id, self.team_id, self.camp, self.match_id))
        buf.extend(encode_dotnet_string(self.nickname))
        buf.extend(struct.pack("<IBIIB", self.avatar_id, 1 if self.is_bot else 0, self.level, self.rank, 1 if self.is_ready else 0))
        
        # Clothes array: [4B count int32] + [8B * count uint64] (TypeDef [4579] field 12)
        buf.extend(struct.pack("<i", len(self.clothes)))
        for c in self.clothes:
            buf.extend(struct.pack("<Q", c))

        buf.extend(struct.pack("<BB", self.gender, 1 if self.is_alive else 0))
        
        # Skills array: [4B count int32] + [4B * count uint32] (TypeDef [4579] field 15)
        buf.extend(struct.pack("<i", len(self.skills)))
        for s in self.skills:
            buf.extend(struct.pack("<I", s))

        buf.extend(encode_dotnet_string(self.region))
        buf.extend(struct.pack("<I", self.banner_id))
        buf.extend(encode_dotnet_string(self.headpic))
        return bytes(buf)


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
class UDP_PlayerPositionOnly:
    """UDP_PLAYER_POSITION_ONLY = 1014"""
    player_id: int
    x: float
    y: float
    z: float
    speed: float
    physx_state: int
    physx_pose: int

    def serialize(self) -> bytes:
        return struct.pack(
            "<I fff f BB",
            self.player_id,
            float(self.x), float(self.y), float(self.z),
            float(self.speed),
            self.physx_state,
            self.physx_pose
        )

    @classmethod
    def unserialize(cls, data: bytes) -> "UDP_PlayerPositionOnly":
        pid, x, y, z, speed, state, pose = struct.unpack("<I fff f BB", data[:26])
        return cls(pid, x, y, z, speed, state, pose)


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
    """TypeDef [4560]: message.j]‚VkzA (RUDP_SAFE_ZONE_CHANGE = 18)
    
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
