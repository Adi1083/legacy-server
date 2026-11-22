"""
Free Fire 1.39 Opcode 170 (RUDP_SYNC_REGION_ACTIVITIES) Codec.

Ground truth (client disassembly, tools/Il2CppDumper_official/libil2cpp_clean_memory.so):
- Container Class: message.UCqGsjv (TypeDefIndex 4712)
    * UnSerialize RVA: 0x200f702
    * Serialize   RVA: 0x200f1db
- Helpers: UDPClientMessageBase.ReadInt32 (0x19a3551), ReadString (0x199cdfd)

UnSerialize (0x200f702) read order:
    1. count   = ReadInt32()
    2. first   = ReadString()                <- ALWAYS read, even when count <= 0
    3. count * ReadString() appended to the list
    4. last    = ReadString()  -> stored in the title field

So the wire format is:
    [4B int32 count] [count x String] [String title]

Each String is [4B int32 byte-length][UTF-8 bytes] (UDPClientMessageBase.ReadString).

The earlier "dEa^CT / 7-byte int16 items" model in this module was wrong: the client routes
opcode 170 to message.UCqGsjv and calls ReadString() unconditionally, so a 4-byte "empty"
payload starved the reader and raised EndOfStreamException inside
MatchGameClient.HandleRecvPacket (observed as a Bugly SIGABRT).

Minimal valid payload (no region activities): count=0 + empty title -> 8 zero bytes.
"""

import io
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

try:
    from .combat_opcodes import CombatOpcode
    OPCODE_SYNC_REGION_ACTIVITIES = CombatOpcode.RUDP_SYNC_REGION_ACTIVITIES
except (ImportError, ValueError):
    OPCODE_SYNC_REGION_ACTIVITIES = 170


def read_string(stream: io.BytesIO) -> str:
    """Reads a string prefixed by a 4-byte Int32 length (UDPClientMessageBase.ReadString)."""
    raw_len = stream.read(4)
    if len(raw_len) < 4:
        raise EOFError("Unexpected EOF while reading string length")
    str_len, = struct.unpack("<i", raw_len)
    if str_len <= 0:
        return ""
    raw = stream.read(str_len)
    if len(raw) < str_len:
        raise EOFError("Unexpected EOF while reading string body")
    return raw.decode("utf-8", errors="replace")


def write_string(s: Optional[str]) -> bytes:
    """Writes a string prefixed by a 4-byte Int32 length (UDPClientMessageBase.WriteString)."""
    if not s:
        return struct.pack("<i", 0)
    encoded = s.encode("utf-8")
    return struct.pack("<i", len(encoded)) + encoded


@dataclass
class RegionActivityItem:
    """Region activity entry. Encoded on the wire as a single string field."""
    region_id: int = 0
    activity_type: int = 0
    state: int = 0
    param: int = 0

    def to_wire_string(self) -> str:
        return f"{self.region_id}:{self.activity_type}:{self.state}:{self.param}"


@dataclass
class S2C_SyncRegionActivities:
    """TypeDef [4712]: message.UCqGsjv (RUDP_SYNC_REGION_ACTIVITIES = 170).

    Wire layout:
        [4B int32 count] [count x String] [String title]
    """
    activities: List[Union[str, RegionActivityItem]] = field(default_factory=list)
    title: str = ""

    OPCODE: int = OPCODE_SYNC_REGION_ACTIVITIES

    def serialize(self) -> bytes:
        buf = bytearray(struct.pack("<i", len(self.activities)))
        for item in self.activities:
            buf.extend(write_string(item if isinstance(item, str) else item.to_wire_string()))
        buf.extend(write_string(self.title))
        return bytes(buf)

    def serialize_padded(self, target_len: int = 64) -> bytes:
        raw = self.serialize()
        return raw.ljust(target_len, b"\x00") if len(raw) < target_len else raw

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_SyncRegionActivities":
        if not data or len(data) < 4:
            return cls([], "")
        stream = io.BytesIO(data)
        count = struct.unpack("<i", stream.read(4))[0]
        if count < 0:
            return cls([], "")
        items: List[str] = []
        try:
            items.append(read_string(stream))
            for _ in range(count):
                items.append(read_string(stream))
            title = read_string(stream)
        except EOFError:
            title = ""
        return cls(activities=items, title=title)


# Convenient aliases
RUDP_SyncRegionActivities = S2C_SyncRegionActivities
Opcode170Codec = S2C_SyncRegionActivities


if __name__ == "__main__":
    print("Testing Opcode 170 (RUDP_SYNC_REGION_ACTIVITIES / message.UCqGsjv) codec...")

    empty_pkt = S2C_SyncRegionActivities()
    empty_bytes = empty_pkt.serialize()
    assert empty_bytes == b"\x00" * 8, f"Empty payload must be 8 bytes, got {empty_bytes.hex()}"
    print(f"  [OK] Empty serialization: {empty_bytes.hex()} (len={len(empty_bytes)})")

    dec = S2C_SyncRegionActivities.unserialize(empty_bytes)
    assert dec.activities == [""] and dec.title == ""
    print("  [OK] Empty roundtrip")

    pkt = S2C_SyncRegionActivities(activities=[RegionActivityItem(101, 2, 1, 300)], title="region")
    wire = pkt.serialize()
    dec = S2C_SyncRegionActivities.unserialize(wire)
    assert dec.activities == ["101:2:1:300", "region"], dec
    print(f"  [OK] Single activity roundtrip: {wire.hex()} (len={len(wire)})")
