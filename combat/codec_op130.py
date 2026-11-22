"""
Opcode 130 (RUDP_JOIN_MATCH_FINISHED) codec, rebuilt from measurement.

Ground truth sources
--------------------
1. Disassembly of message.nSa~rX.UnSerialize (RVA 0x1ef36f5, TypeDef 4580) in
   tools/Il2CppDumper_official/libil2cpp_clean_memory.so.
2. A live Frida trace of every UDPClientMessageBase.Read* the client performed
   inside that method (scratch/measure_130.py -> dump/trace_130.json, captured
   against the real client at match entry).

Measured wire layout (in read order)
------------------------------------
    off  type     field (client store offset)                 bytes
      0  UInt32   err_code            [this+0x08]               4
      4  UInt64   account_id          [this+0x0c]               8
     12  UInt64   match_id            [this+0x14]               8
     20  Int32    server_time         [this+0x1c]               4
     24  Byte     map_id              [this+0x20]               1
     25  UInt32   waiting_seconds     [this+0x24]               4
     29  UInt16   weather_style       [this+0x28]               2
     31  UInt32   game_mode           [this+0x2c]               4
     35  UInt32   room_type           [this+0x30]               4
     39  struct   safe_zone           [this+0x34]              18   <-- was missing
     57  Int32    count1  (list<int>) [this+0x38]               4 + 4*count1
      ... Int32    count2  (list<uint>)[this+0x3c]               4 + 4*count2
      ... Int32    count3  (list<msg>)[this+0x40]               4 + items
      ... UInt32   trailing flag       [this+0x44]               4

The nested struct at +0x34 is message.j]\\x82VkzA (RVA 0x1ed8722), identified at
runtime by reading the virtual slot invoked at 0x1ef3907. Its measured layout is:

    off  type      field      bytes
      0  Int16     phase         2
      2  struct    current      12   message.My^x~\\x81o (RVA 0x1eec3e3): ReadInt32 x3
     14  struct    next         12   same type, same 3 x ReadInt32

Both circle methods were resolved from their live vtable slots (0x1ed8837 and
0x1ed88f6), and message.My^x~\\x81o.UnSerialize (0x1eec3e3) reads exactly three
Int32 values into +0x08, +0x0c and +0x10 before returning. An earlier model that
treated each circle as two ReadSingle floats (8 bytes) under-counted the block by
8 bytes; a live trace showed the client reading past the end of a 73-byte payload
at exactly that point (it picked up 600.0f left over from the opcode 100 buffer)
before raising EndOfStreamException.

Total with all collections empty: 39 + 26 + 4 + 4 + 4 + 4 = 81 bytes.

Why the earlier 55-byte payload aborted match entry
---------------------------------------------------
It omitted the 18-byte nested struct entirely, so the client parsed our first
collection count as the nested `phase` and kept reading inside
message.j]\\x82VkzA.UnSerialize. The reader ran off the end of the packet and
raised EndOfStreamException inside MatchGameClient.HandleRecvPacket, which the
client reports as a Bugly SIGABRT (Fatal signal 6).

The client `nSa~rX` message does NOT contain a 34-byte 3D circle block and it
does not read a radius here: those live in opcode 117 (RUDP_SAFE_ZONE_CHANGE).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


OPCODE_JOIN_MATCH_FINISHED: int = 130

#: Bytes of message.nSa~rX consumed before the nested safe-zone struct.
HEADER_BYTES: int = 39
#: Bytes of the nested message.j]\x82VkzA struct (Int16 + 2 x 3 Int32).
SAFE_ZONE_BYTES: int = 26
#: Correct serialized length when every collection is empty.
EMPTY_PAYLOAD_BYTES: int = HEADER_BYTES + SAFE_ZONE_BYTES + 4 + 4 + 4 + 4


@dataclass
class SafeZoneCircle:
    """TypeDef message.My^x~\\x81o (RVA 0x1eec3e3): three Int32 values.

    The obfuscated field names are not recoverable, so the three ints are kept in
    their measured order and populated from the match's authoritative safe-zone
    state (centre x/z and radius).
    """

    center_x: int = 0
    center_z: int = 0
    radius: int = 600

    def serialize(self) -> bytes:
        return struct.pack("<iii", int(self.center_x), int(self.center_z), int(self.radius))

    @classmethod
    def unserialize(cls, data: bytes, offset: int = 0) -> Tuple["SafeZoneCircle", int]:
        cx, cz, r = struct.unpack_from("<iii", data, offset)
        return cls(center_x=cx, center_z=cz, radius=r), offset + 12


@dataclass
class SafeZoneBlock:
    """TypeDef message.j]\\x82VkzA (RVA 0x1ed8722): phase + current + next zone."""

    phase: int = 0
    current: SafeZoneCircle = field(default_factory=SafeZoneCircle)
    next: SafeZoneCircle = field(default_factory=SafeZoneCircle)

    def serialize(self) -> bytes:
        return struct.pack("<h", int(self.phase)) + self.current.serialize() + self.next.serialize()

    @classmethod
    def unserialize(cls, data: bytes, offset: int = 0) -> Tuple["SafeZoneBlock", int]:
        phase = struct.unpack_from("<h", data, offset)[0]
        cur, offset = SafeZoneCircle.unserialize(data, offset + 2)
        nxt, offset = SafeZoneCircle.unserialize(data, offset)
        return cls(phase=phase, current=cur, next=nxt), offset


# Historical alias kept for existing imports.
SafeZoneData = SafeZoneBlock


@dataclass
class JoinMatchFinishedPacket:
    """TypeDef [4580]: message.nSa~rX (RUDP_JOIN_MATCH_FINISHED = 130)."""

    err_code: int = 0
    account_id: int = 10001
    match_id: int = 1000001
    server_time: int = 0
    map_id: int = 1
    waiting_seconds: int = 60
    weather_style: int = 1
    game_mode: int = 1
    room_type: int = 0
    safe_zone: SafeZoneBlock = field(default_factory=SafeZoneBlock)
    # list<int> at +0x38
    extra_ints: List[int] = field(default_factory=list)
    # list<uint> at +0x3c
    extra_uints: List[int] = field(default_factory=list)
    # list<message> at +0x40; the client only reads items when count3 > 0.
    extra_nest: List[bytes] = field(default_factory=list)
    # UInt32 at +0x44
    trailing_flag: int = 0

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
        assert len(buf) == HEADER_BYTES, len(buf)

        buf.extend(self.safe_zone.serialize())
        assert len(buf) == HEADER_BYTES + SAFE_ZONE_BYTES, len(buf)

        buf.extend(struct.pack("<i", len(self.extra_ints)))
        for v in self.extra_ints:
            buf.extend(struct.pack("<i", int(v)))

        buf.extend(struct.pack("<i", len(self.extra_uints)))
        for v in self.extra_uints:
            buf.extend(struct.pack("<I", int(v)))

        buf.extend(struct.pack("<i", len(self.extra_nest)))
        for item in self.extra_nest:
            buf.extend(item.serialize() if hasattr(item, "serialize") else bytes(item))

        buf.extend(struct.pack("<I", int(self.trailing_flag)))
        return bytes(buf)

    @classmethod
    def unserialize(cls, data: bytes, offset: int = 0) -> "JoinMatchFinishedPacket":
        header = struct.unpack_from("<IQQiBIHII", data, offset)
        pkt = cls(
            err_code=header[0],
            account_id=header[1],
            match_id=header[2],
            server_time=header[3],
            map_id=header[4],
            waiting_seconds=header[5],
            weather_style=header[6],
            game_mode=header[7],
            room_type=header[8],
        )
        cur = offset + HEADER_BYTES
        pkt.safe_zone, cur = SafeZoneBlock.unserialize(data, cur)

        count = struct.unpack_from("<i", data, cur)[0]
        cur += 4
        if count > 0:
            pkt.extra_ints = list(struct.unpack_from(f"<{count}i", data, cur))
            cur += 4 * count

        count = struct.unpack_from("<i", data, cur)[0]
        cur += 4
        if count > 0:
            pkt.extra_uints = list(struct.unpack_from(f"<{count}I", data, cur))
            cur += 4 * count

        count = struct.unpack_from("<i", data, cur)[0]
        cur += 4
        if count > 0:
            raise NotImplementedError("opcode 130 list3 items are never sent by this server")

        pkt.trailing_flag = struct.unpack_from("<I", data, cur)[0]
        return pkt


# Backward-compatible aliases
S2C_JoinMatchRes = JoinMatchFinishedPacket
RUDP_JoinMatchFinished = JoinMatchFinishedPacket


def serialize_op130(
    match_id: int,
    account_id: int = 10001,
    server_time: int = 0,
    err_code: int = 0,
    map_id: int = 1,
    waiting_seconds: int = 60,
    weather_style: int = 1,
    game_mode: int = 1,
    room_type: int = 0,
    safe_zone: Optional[SafeZoneBlock] = None,
) -> bytes:
    return JoinMatchFinishedPacket(
        err_code=err_code,
        account_id=account_id,
        match_id=match_id,
        server_time=server_time,
        map_id=map_id,
        waiting_seconds=waiting_seconds,
        weather_style=weather_style,
        game_mode=game_mode,
        room_type=room_type,
        safe_zone=safe_zone or SafeZoneBlock(),
    ).serialize()


if __name__ == "__main__":
    pkt = JoinMatchFinishedPacket(
        err_code=0, account_id=10001, match_id=51090121,
        server_time=1795000000, map_id=1, waiting_seconds=60,
        weather_style=1, game_mode=1, room_type=0,
        safe_zone=SafeZoneBlock(
            phase=0,
            current=SafeZoneCircle(center_x=0, center_z=0, radius=600),
            next=SafeZoneCircle(center_x=0, center_z=0, radius=600),
        ),
    )
    wire = pkt.serialize()
    assert len(wire) == EMPTY_PAYLOAD_BYTES == 81, len(wire)
    dec = JoinMatchFinishedPacket.unserialize(wire)
    assert dec.match_id == 51090121 and dec.account_id == 10001
    assert dec.safe_zone.phase == 0
    assert dec.safe_zone.current.radius == 600
    print(f"Opcode 130 codec OK: {len(wire)} bytes (39 header + 26 safe-zone + 16 collections)")
