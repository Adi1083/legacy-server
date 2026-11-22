"""
Free Fire 1.39 Opcode 501 (RUDP_VAR_SYNC_GRI_DATA) Packet Codec.

Reverse Engineered Ground-Truth:
- IL2CPP Target: Free Fire Barbosa v1.39 (libil2cpp_decrypted.so / dump.cs)
- Class Mapping:
    * TypeDefIndex [9754]: `GCommon.GRIDataPool` (Game Replication Info Data Pool)
    * Inherits from TypeDefIndex [9751]: `GCommon.ReplicationDataPool`
- Handler Method:
    * `GCommon.ReplicationDataPool.SyncReplicationData` (RVA 0x197fca0)
    * Dispatched via `GCommon.MatchGameClient.HandleRecvPacket` (RVA 0x2040352)
    * `GCommon.NetworkMessageDispatcher.Invoke` (RVA 0x2040c1b) for Opcode 501
- Transport:
    * Protocol: RUDP / UDP
    * SendOption: 5 (VAR_RELIABLE)
    * Endianness: Little-Endian (<)

Binary Wire Format:
- [2B uint16 total_len] (<H)
    * Specifies the total byte count of variable replication items that follow.
    * Empty Sync: If `total_len == 0`, wire payload is strictly 2 bytes (b"\\x00\\x00").
      The client loop condition `(current_stream_pos - start_pos) >= total_len` terminates
      immediately with zero exceptions and zero items parsed.
- [Sequence of Variable Entries]:
    * Processed sequentially while `bytes_read < total_len`:
        - [1B uint8 data_type] (<B):
            0: Int8   (sbyte, 1B, <b)
            1: UInt8  (byte,  1B, <B)
            2: Int16  (short, 2B, <h)
            3: UInt16 (ushort,2B, <H)
            4: Int32  (int,   4B, <i)
            5: UInt32 (uint,  4B, <I)
            6: Bool   (bool,  1B, <?)
            7: Float  (float, 4B, <f)
            8: UInt64 (ulong, 8B, <Q)
            9: Int64  (long,  8B, <q)
        - [1B uint8 key_id] (<B):
            The GRI property index / variable replication identifier.
        - [Value Bytes]:
            Primitive value encoded according to `data_type` in little-endian.
"""

import struct
from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Tuple

try:
    from .combat_opcodes import CombatOpcode
    OPCODE_VAR_SYNC_GRI_DATA = CombatOpcode.RUDP_VAR_SYNC_GRI_DATA
except (ImportError, ValueError):
    OPCODE_VAR_SYNC_GRI_DATA = 501


class ReplicationDataType(IntEnum):
    """Replication variable primitive data types recognized by SyncReplicationData."""
    INT8 = 0
    UINT8 = 1
    INT16 = 2
    UINT16 = 3
    INT32 = 4
    UINT32 = 5
    BOOL = 6
    FLOAT = 7
    UINT64 = 8
    INT64 = 9


# Format strings and sizes for each type
_TYPE_SPECS: Dict[int, Tuple[str, int]] = {
    ReplicationDataType.INT8: ("<b", 1),
    ReplicationDataType.UINT8: ("<B", 1),
    ReplicationDataType.INT16: ("<h", 2),
    ReplicationDataType.UINT16: ("<H", 2),
    ReplicationDataType.INT32: ("<i", 4),
    ReplicationDataType.UINT32: ("<I", 4),
    ReplicationDataType.BOOL: ("<?", 1),
    ReplicationDataType.FLOAT: ("<f", 4),
    ReplicationDataType.UINT64: ("<Q", 8),
    ReplicationDataType.INT64: ("<q", 8),
}


@dataclass
class ReplicationItem:
    """A single variable replication property entry."""
    data_type: int
    key_id: int
    value: Any

    def serialize(self) -> bytes:
        """Serializes entry to binary wire: [1B data_type][1B key_id][value]."""
        header = struct.pack("<BB", int(self.data_type), int(self.key_id))
        spec = _TYPE_SPECS.get(int(self.data_type))
        if spec is None:
            return header

        fmt, _ = spec
        if self.data_type == ReplicationDataType.BOOL:
            val_bytes = struct.pack(fmt, bool(self.value))
        elif self.data_type == ReplicationDataType.FLOAT:
            val_bytes = struct.pack(fmt, float(self.value))
        else:
            val_bytes = struct.pack(fmt, int(self.value))
        return header + val_bytes

    @classmethod
    def unserialize_from(cls, data: bytes, offset: int = 0) -> Tuple["ReplicationItem", int]:
        """Deserializes one entry starting at offset. Returns (item, new_offset)."""
        if offset + 2 > len(data):
            raise ValueError(f"Insufficient bytes for ReplicationItem header at {offset}")
        dtype, key = struct.unpack_from("<BB", data, offset)
        offset += 2

        spec = _TYPE_SPECS.get(dtype)
        if spec is None:
            raise ValueError(f"Unsupported ReplicationItem data_type {dtype} at {offset-2}")

        fmt, size = spec
        if offset + size > len(data):
            raise ValueError(f"Insufficient bytes for data_type {dtype} (needed {size}B) at {offset}")

        val, = struct.unpack_from(fmt, data, offset)
        offset += size
        return cls(data_type=dtype, key_id=key, value=val), offset


@dataclass
class S2C_VarSyncGRIData:
    """
    Opcode 501 (RUDP_VAR_SYNC_GRI_DATA) packet implementation.
    Maps to GCommon.GRIDataPool / GCommon.ReplicationDataPool.SyncReplicationData.
    """
    items: List[ReplicationItem] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[ReplicationItem]:
        return iter(self.items)

    def __getitem__(self, index: int) -> ReplicationItem:
        return self.items[index]

    def add_item(self, key_id: int, value: Any, data_type: Optional[int] = None) -> "S2C_VarSyncGRIData":
        """Convenience method to add an item, auto-detecting data_type if omitted."""
        if data_type is None:
            if isinstance(value, bool):
                data_type = ReplicationDataType.BOOL
            elif isinstance(value, float):
                data_type = ReplicationDataType.FLOAT
            elif isinstance(value, int):
                if value < 0:
                    data_type = ReplicationDataType.INT32
                elif value <= 0xFF:
                    data_type = ReplicationDataType.UINT8
                elif value <= 0xFFFF:
                    data_type = ReplicationDataType.UINT16
                elif value <= 0xFFFFFFFF:
                    data_type = ReplicationDataType.UINT32
                else:
                    data_type = ReplicationDataType.UINT64
            else:
                raise TypeError(f"Cannot auto-detect replication data_type for {type(value)}")
        self.items.append(ReplicationItem(data_type=int(data_type), key_id=int(key_id), value=value))
        return self

    def serialize(self) -> bytes:
        """
        Serializes packet to wire bytes.
        Empty items list produces authoritative 2-byte header struct.pack('<H', 0).
        """
        if not self.items:
            return struct.pack("<H", 0)

        body = b"".join(item.serialize() for item in self.items)
        return struct.pack("<H", len(body)) + body

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_VarSyncGRIData":
        """
        Deserializes binary wire bytes into S2C_VarSyncGRIData packet.
        Follows client logic: reads uint16 total_len, then loops until total_len consumed.
        """
        if len(data) < 2:
            return cls(items=[])

        total_len, = struct.unpack_from("<H", data, 0)
        if total_len == 0:
            return cls(items=[])

        available = len(data) - 2
        payload_end = 2 + min(total_len, available)

        items: List[ReplicationItem] = []
        offset = 2
        while offset < payload_end:
            if offset + 2 > payload_end:
                break
            dtype, key = struct.unpack_from("<BB", data, offset)
            spec = _TYPE_SPECS.get(dtype)
            if spec is None:
                # Client skips or breaks on unknown type
                break
            fmt, size = spec
            if offset + 2 + size > payload_end:
                break
            offset += 2
            val, = struct.unpack_from(fmt, data, offset)
            offset += size
            items.append(ReplicationItem(data_type=dtype, key_id=key, value=val))

        return cls(items=items)

    def to_dict(self) -> Dict[int, Any]:
        """Returns dict of key_id -> value."""
        return {item.key_id: item.value for item in self.items}


# Aliases for backward compatibility and swarm conventions
RUDP_VarSyncGRIData = S2C_VarSyncGRIData
Opcode501Codec = S2C_VarSyncGRIData
