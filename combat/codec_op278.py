"""
Free Fire 1.39 Opcode 278 (RUDP_SyncShowCase) Codec.

Reverse Engineering Evidence:
- Assembly: Assembly-CSharp.dll
- IL2CPP Metadata TypeDef: TypeDefIndex [4712]
- Type Name: message.UCqGsjv
- Base Class: GCommon.UDPClientMessageBase (TypeDefIndex [26738] / [9773])
- Method RVAs (x86 32-bit):
    * UnSerialize: RVA 0x200f702 (VA 0xba65b702)
    * Serialize:   RVA 0x200f1db (VA 0xba65b1db)
    * Helper ReadString:  RVA 0x199cdfd (VA 0xb9fe4dfd)
    * Helper WriteString: RVA 0x19a3395 (VA 0xb9feb395)
    * Helper ReadInt32:   RVA 0x19a3551 (VA 0xb9feb551)
- Fields:
    * Field [24489] at offset +0x08: }GqDRyP (System.Collections.Generic.List<string> items)
    * Field [24490] at offset +0x0C: ‚S[y^ED (System.String title / introduction string)
- Associated Client Subsystem:
    * COW.GamePlay.LevelShowCase (TypeDefIndex [3890])
    * COW.ArenaShowCaseData (TypeDefIndex [3181])
    * UIHudShowCaseIntroductionController (TypeDefIndex [6813])

Wire Binary Layout (Little-Endian '<'):
---------------------------------------------------------------------------------------
Field Name   | Type   | Size (Bytes) | Description
-------------|--------|--------------|-------------------------------------------------
count        | Int32  | 4 (<i)       | Number of showcase items in the list
items[0]     | String | 4 + len      | [4B int32 length] + [UTF-8 bytes] (if count > 0)
...          | String | 4 + len      | ...
items[N-1]   | String | 4 + len      | [4B int32 length] + [UTF-8 bytes]
title        | String | 4 + len      | [4B int32 length] + [UTF-8 bytes] (Always read!)
---------------------------------------------------------------------------------------

Empty / Minimal Wire Layout (count = 0, title = ""):
- count:      0 (4 bytes: struct.pack("<i", 0) -> b"\\x00\\x00\\x00\\x00")
- title_len:  0 (4 bytes: struct.pack("<i", 0) -> b"\\x00\\x00\\x00\\x00")
- Total Minimal Payload: Exactly 8 bytes (b"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00").
- Ground-Truth Burst Wire Size: 96 bytes (8 bytes minimal + 88 bytes zero padding).

Root Cause of Client Crash (EndOfStreamException):
- At 0x200f75f: client reads 4-byte count.
- At 0x200f7d0: client unconditionally calls ReadString() BEFORE checking count <= 0.
- ReadString() begins with ReadInt32() to get string byte length.
- If server sends only 4 bytes (count=0), ReadString() starves for the 4-byte string length,
  raising System.IO.EndOfStreamException at System.IO.BinaryReader.ReadInt32().
- Sending at least 8 bytes (count=0, title_len=0) satisfies ReadString() cleanly.
"""

import io
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any

try:
    from .combat_opcodes import CombatOpcode
    OPCODE_SYNC_SHOW_CASE = CombatOpcode.RUDP_SyncShowCase
except (ImportError, ValueError, AttributeError):
    OPCODE_SYNC_SHOW_CASE = 278


def _read_string(stream: io.BytesIO) -> str:
    """Reads a string prefixed by 4-byte Int32 length (matching UDPClientMessageBase.ReadString)."""
    raw_len = stream.read(4)
    if len(raw_len) < 4:
        raise EOFError("Unexpected EOF while reading string length")
    str_len, = struct.unpack("<i", raw_len)
    if str_len < 0:
        return ""
    if str_len == 0:
        return ""
    str_bytes = stream.read(str_len)
    if len(str_bytes) < str_len:
        raise EOFError(f"Unexpected EOF while reading string body (expected {str_len}, got {len(str_bytes)})")
    return str_bytes.decode("utf-8", errors="replace")


def _write_string(s: Optional[str]) -> bytes:
    """Writes a string prefixed by 4-byte Int32 length (matching UDPClientMessageBase.WriteString)."""
    if s is None or len(s) == 0:
        return struct.pack("<i", 0)
    encoded = s.encode("utf-8")
    return struct.pack("<i", len(encoded)) + encoded


@dataclass
class ShowCaseItem:
    """Backward compatibility item wrapper for showcase items."""
    item_id: Union[int, str] = 0
    slot_id: int = 0

    def serialize(self) -> bytes:
        return _write_string(str(self.item_id))

    def __str__(self) -> str:
        return str(self.item_id)


@dataclass
class S2C_SyncShowCase:
    """Opcode 278 (RUDP_SyncShowCase) message container (message.UCqGsjv)."""
    items: List[Union[str, ShowCaseItem]] = field(default_factory=list)
    title: str = ""

    def serialize(self) -> bytes:
        """Serializes the message into the exact binary wire layout expected by message.UCqGsjv."""
        # Convert items to list of strings
        str_items = [item.item_id if isinstance(item, ShowCaseItem) else str(item) for item in self.items]
        count = len(str_items)

        # 1. Write count (4 bytes Int32)
        buf = bytearray(struct.pack("<i", count))

        # 2. Write item strings
        for item_str in str_items:
            buf.extend(_write_string(item_str))

        # 3. Write title string (always present)
        buf.extend(_write_string(self.title))

        return bytes(buf)

    def serialize_padded(self, target_len: int = 96) -> bytes:
        """Serializes and zero-pads to the authentic Barbosa ground-truth capture length (96 bytes)."""
        payload = self.serialize()
        if len(payload) < target_len:
            payload = payload.ljust(target_len, b"\x00")
        return payload

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_SyncShowCase":
        """Deserializes raw binary payload exactly matching message.UCqGsjv.UnSerialize (RVA 0x200f702)."""
        if len(data) < 4:
            raise ValueError(f"Payload too short for Opcode 278 header: {len(data)} bytes (minimum 4)")

        stream = io.BytesIO(data)
        raw_count = stream.read(4)
        count, = struct.unpack("<i", raw_count)

        # At RVA 0x200f7d0: ReadString is called BEFORE checking count <= 0
        first_string = _read_string(stream)

        if count <= 0:
            # If count <= 0: branch 0x200f7d9 -> 0x200f826 stores first_string into title
            return cls(items=[], title=first_string)

        # If count > 0:
        # first_string is added as items[0]
        items: List[str] = [first_string]

        # Then loop reads remaining count - 1 items
        for _ in range(1, count):
            items.append(_read_string(stream))

        # The final string read at loop termination is stored into title
        title = _read_string(stream)

        return cls(items=items, title=title)

    def to_dict(self) -> dict:
        return {
            "cmd": OPCODE_SYNC_SHOW_CASE,
            "count": len(self.items),
            "items": [str(x) for x in self.items],
            "title": self.title,
        }


# Aliases for architecture and backward compatibility
RUDP_SyncShowCase = S2C_SyncShowCase
Opcode278Codec = S2C_SyncShowCase


if __name__ == "__main__":
    print("Testing Opcode 278 (RUDP_SyncShowCase / message.UCqGsjv) Codec...")

    # Test 1: Empty showcase (count=0, title="")
    msg_empty = S2C_SyncShowCase()
    raw_empty = msg_empty.serialize()
    assert raw_empty == b"\x00\x00\x00\x00\x00\x00\x00\x00", f"Empty serialize mismatch: {raw_empty.hex()}"
    assert len(raw_empty) == 8, f"Expected exactly 8 bytes for minimal wire, got {len(raw_empty)}"

    decoded_empty = S2C_SyncShowCase.unserialize(raw_empty)
    assert decoded_empty.items == []
    assert decoded_empty.title == ""
    print("[PASS] Test 1: Empty showcase minimal 8-byte wire roundtrip")

    # Test 2: Padded empty showcase (96 bytes ground-truth burst)
    raw_padded = msg_empty.serialize_padded(96)
    assert len(raw_padded) == 96, f"Expected 96 bytes, got {len(raw_padded)}"
    assert raw_padded[:8] == b"\x00\x00\x00\x00\x00\x00\x00\x00"
    decoded_padded = S2C_SyncShowCase.unserialize(raw_padded)
    assert decoded_padded.items == []
    assert decoded_padded.title == ""
    print("[PASS] Test 2: 96-byte padded showcase roundtrip")

    # Test 3: Empty items with a title
    msg_title_only = S2C_SyncShowCase(items=[], title="SpawnIslandShowcase")
    raw_title_only = msg_title_only.serialize()
    decoded_title_only = S2C_SyncShowCase.unserialize(raw_title_only)
    assert decoded_title_only.items == []
    assert decoded_title_only.title == "SpawnIslandShowcase"
    print("[PASS] Test 3: Empty items with title roundtrip")

    # Test 4: Multiple items with title
    items_test = ["item_pedestal_1", "item_pedestal_2", "special_gacha_box"]
    msg_items = S2C_SyncShowCase(items=items_test, title="ArenaShowcaseMain")
    raw_items = msg_items.serialize()
    decoded_items = S2C_SyncShowCase.unserialize(raw_items)
    assert decoded_items.items == items_test
    assert decoded_items.title == "ArenaShowcaseMain"
    print("[PASS] Test 4: Multiple items with title roundtrip")

    # Test 5: EndOfStreamException starvation check (4 bytes only should raise EOFError)
    try:
        S2C_SyncShowCase.unserialize(b"\x00\x00\x00\x00")
        assert False, "Should have raised EOFError on 4-byte starved payload"
    except EOFError as e:
        print(f"[PASS] Test 5: 4-byte starved payload correctly caught: {e}")

    # Test 6: ShowCaseItem backward compatibility
    msg_compat = S2C_SyncShowCase(items=[ShowCaseItem(item_id="item_101", slot_id=0)], title="CompatTitle")
    raw_compat = msg_compat.serialize()
    decoded_compat = S2C_SyncShowCase.unserialize(raw_compat)
    assert decoded_compat.items == ["item_101"]
    assert decoded_compat.title == "CompatTitle"
    print("[PASS] Test 6: ShowCaseItem backward compatibility roundtrip")

    print("\nAll Opcode 278 codec tests passed successfully!")
