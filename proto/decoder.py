"""
Generic Protobuf wire-format parser for Free Fire 1.39 request payloads.
Never raises on unknown tags or truncated payloads.
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Tuple


def _read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    """Read a base-128 varint starting at pos. Returns (value, new_pos)."""
    result = 0
    shift = 0
    length = len(data)
    while pos < length:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos
        shift += 7
        if shift >= 70:
            raise ValueError("Varint too long")
    raise ValueError("Truncated varint")


def decode_proto(data: bytes) -> Dict[int, List[Any]]:
    """
    Parse raw Protobuf wire bytes into {field_num: [values...]}.
    - Wire type 0 (varint) -> int
    - Wire type 1 (64-bit) -> bytes (8 bytes)
    - Wire type 2 (length-delimited) -> bytes
    - Wire type 5 (32-bit) -> bytes (4 bytes)
    Stops gracefully if data is empty, truncated, or malformed.
    """
    fields: Dict[int, List[Any]] = {}
    if not data:
        return fields

    raw = bytes(data)
    pos = 0
    length = len(raw)

    while pos < length:
        try:
            tag, pos = _read_varint(raw, pos)
        except ValueError:
            break

        field_num = tag >> 3
        wire_type = tag & 0x07
        if field_num == 0:
            break

        if wire_type == 0:
            try:
                val, pos = _read_varint(raw, pos)
            except ValueError:
                break
            fields.setdefault(field_num, []).append(val)
        elif wire_type == 1:
            if pos + 8 > length:
                break
            fields.setdefault(field_num, []).append(raw[pos : pos + 8])
            pos += 8
        elif wire_type == 2:
            try:
                size, pos = _read_varint(raw, pos)
            except ValueError:
                break
            if size < 0 or pos + size > length:
                break
            fields.setdefault(field_num, []).append(raw[pos : pos + size])
            pos += size
        elif wire_type == 3:
            # Legacy start-group: skip until matching end-group (wire_type 4) or stop
            continue
        elif wire_type == 4:
            continue
        elif wire_type == 5:
            if pos + 4 > length:
                break
            fields.setdefault(field_num, []).append(raw[pos : pos + 4])
            pos += 4
        else:
            # Unknown wire type: stop safely
            break

    return fields


def get_varint(fields: Dict[int, List[Any]], field_num: int, default: int = 0) -> int:
    """Return the first integer varint for field_num, or default."""
    vals = fields.get(field_num)
    if not vals:
        return default
    v = vals[0]
    if isinstance(v, int):
        return v
    return default


def get_int64(fields: Dict[int, List[Any]], field_num: int, default: int = 0) -> int:
    """Return a signed 64-bit varint for field_num, or default."""
    vals = fields.get(field_num)
    if not vals or not isinstance(vals[0], int):
        return default
    v = vals[0] & 0xFFFFFFFFFFFFFFFF
    return v - (1 << 64) if v >= (1 << 63) else v


def get_int32(fields: Dict[int, List[Any]], field_num: int, default: int = 0) -> int:
    """Return a signed 32-bit varint for field_num, or default."""
    vals = fields.get(field_num)
    if not vals or not isinstance(vals[0], int):
        return default
    v = vals[0] & 0xFFFFFFFF
    return v - (1 << 32) if v >= (1 << 31) else v


def get_bool(fields: Dict[int, List[Any]], field_num: int, default: bool = False) -> bool:
    """Return boolean value for field_num, or default."""
    vals = fields.get(field_num)
    if not vals or not isinstance(vals[0], int):
        return default
    return vals[0] != 0


def get_bytes(fields: Dict[int, List[Any]], field_num: int, default: bytes = b"") -> bytes:
    """Return the first length-delimited/fixed byte blob for field_num, or default."""
    vals = fields.get(field_num)
    if not vals:
        return default
    v = vals[0]
    if isinstance(v, (bytes, bytearray)):
        return bytes(v)
    return default


def get_string(fields: Dict[int, List[Any]], field_num: int, default: str = "") -> str:
    """Return the first UTF-8 string for field_num, or default."""
    vals = fields.get(field_num)
    if not vals:
        return default
    v = vals[0]
    if isinstance(v, (bytes, bytearray)):
        return bytes(v).decode("utf-8", errors="replace")
    return default


def get_packed_varints(fields: Dict[int, List[Any]], field_num: int) -> List[int]:
    """
    Decode packed repeated varints (wire type 2) AND fallback unpacked repeated varints (wire type 0).
    """
    vals = fields.get(field_num)
    if not vals:
        return []
    out: List[int] = []
    for item in vals:
        if isinstance(item, int):
            out.append(item)
        elif isinstance(item, (bytes, bytearray)):
            raw = bytes(item)
            pos = 0
            length = len(raw)
            while pos < length:
                try:
                    v, pos = _read_varint(raw, pos)
                    out.append(v)
                except ValueError:
                    break
    return out


def get_float(fields: Dict[int, List[Any]], field_num: int, default: float = 0.0) -> float:
    """Return 32-bit IEEE float (wire type 5) for field_num, or default."""
    vals = fields.get(field_num)
    if not vals or not isinstance(vals[0], (bytes, bytearray)) or len(vals[0]) != 4:
        return default
    return struct.unpack("<f", bytes(vals[0]))[0]


def get_double(fields: Dict[int, List[Any]], field_num: int, default: float = 0.0) -> float:
    """Return 64-bit IEEE double (wire type 1) for field_num, or default."""
    vals = fields.get(field_num)
    if not vals or not isinstance(vals[0], (bytes, bytearray)) or len(vals[0]) != 8:
        return default
    return struct.unpack("<d", bytes(vals[0]))[0]


def get_submessage(fields: Dict[int, List[Any]], field_num: int) -> Dict[int, List[Any]]:
    """Parse and return the first nested submessage for field_num (empty dict if missing)."""
    raw = get_bytes(fields, field_num)
    return decode_proto(raw) if raw else {}


def get_submessages(fields: Dict[int, List[Any]], field_num: int) -> List[Dict[int, List[Any]]]:
    """Parse and return all repeated nested submessages for field_num."""
    vals = fields.get(field_num)
    if not vals:
        return []
    return [decode_proto(bytes(v)) for v in vals if isinstance(v, (bytes, bytearray))]
