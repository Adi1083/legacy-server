"""
Free Fire 1.39 Opcode 135 (RUDP_SYNC_PLAYERS_VISIBILITY) Codec.

Reverse Engineering Evidence:
- Assembly: Assembly-CSharp.dll
- IL2CPP Metadata TypeDef: TypeDefIndex [4695]
- Type Name: message.HIFZsBP
- Base Class: GCommon.UDPClientMessageBase (TypeDefIndex [9773])
- Method RVAs:
    * UnSerialize: RVA 0x208b84e (VA 0xba6d884e)
    * Serialize:   RVA 0x208b6ce (VA 0xba6d86ce)
    * .ctor:       RVA 0x208b725 (VA 0xba6d8725)
    * Recycle:     RVA 0x208b6c4 (VA 0xba6d86c4)
- Network Dispatcher & Client Handler:
    * Interface: COW.GamePlay.u}NfIjE (TypeDefIndex [4254]), Method [34278] SyncPlayersVisibility
    * Handler: COW.GamePlay.PlayerNetwork$$SyncPlayersVisibility (RVA 0x956dba, VA 0xb8fa3dba)
    * Parameter Type: System.UInt64 (metadata v23 typeIndex 24, 8-byte unsigned integer)
- Related Sibling Type:
    * Opcode 136 (RUDP_SYNC_VEHICLES_VISIBILITY): message.X|pEzcO (TypeDefIndex [4696], UnSerialize RVA 0x2019683)

Exact Binary Wire Layout:
-----------------------------------------------------------------------------
Offset | Size | Format | Field Name        | Type / Description
-------|------|--------|-------------------|---------------------------------
0x00   | 8    | <Q     | visibility_mask   | UInt64 (64-bit player visibility bitmask)
-----------------------------------------------------------------------------
Total Wire Size: 8 bytes minimal (<Q).
Padded Wire Size: 24 bytes (in authentic 1.39 burst capture seq=6, seq=99, seq=153, 
                 the payload is 24 bytes with trailing zero padding for TEA block alignment).

Wire Semantics:
- Bit `i` (from 0 to 49 for up to 50 players in match) controls visibility of Player entity index `i`.
- If bit `i` is set (1), Player entity `i` is rendered / visible.
- If bit `i` is clear (0), Player entity `i` is culled / hidden.
- Bitwise test in PlayerNetwork (RVA 0x957265):
    `is_visible = (player_bitmask & visibility_mask) != 0`
- Default / All players visible: 0xFFFFFFFFFFFFFFFF (all 64 bits set).
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    from .combat_opcodes import CombatOpcode
    OPCODE_SYNC_PLAYERS_VISIBILITY = CombatOpcode.RUDP_SYNC_PLAYERS_VISIBILITY
except (ImportError, ValueError):
    OPCODE_SYNC_PLAYERS_VISIBILITY = 135

# Default mask: all 64 bits set (all players visible)
ALL_PLAYERS_VISIBLE_MASK: int = 0xFFFFFFFFFFFFFFFF
NO_PLAYERS_VISIBLE_MASK: int = 0x0000000000000000


@dataclass
class PlayerVisibilityItem:
    """Helper / compatibility representation of a single player's visibility flag."""
    entity_id: int
    is_visible: bool = True

    def serialize(self) -> bytes:
        return struct.pack("<iB", self.entity_id, 1 if self.is_visible else 0)


@dataclass
class S2C_SyncPlayersVisibility:
    """TypeDef [4695]: message.HIFZsBP (RUDP_SYNC_PLAYERS_VISIBILITY = 135).
    
    Wire layout:
    - [8B uint64 visibility_mask] (<Q)
    
    In authentic IND PROJECT network captures (seq=6, seq=99, seq=153 in burst_summary_350.txt),
    the packet payload length is 24 bytes (8B uint64 + 16B zero padding for TEA block alignment).
    Both 8-byte raw and 24-byte padded payloads are supported transparently.
    """
    visibility_mask: int = ALL_PLAYERS_VISIBLE_MASK
    _players: Optional[List[PlayerVisibilityItem]] = field(default=None, repr=False)

    OPCODE: int = OPCODE_SYNC_PLAYERS_VISIBILITY

    def __init__(
        self,
        visibility_mask: Optional[int] = None,
        players: Optional[List[PlayerVisibilityItem]] = None
    ):
        if players is not None:
            self._players = players
            mask = 0
            for p in players:
                if p.is_visible:
                    bit = p.entity_id if p.entity_id < 64 else (p.entity_id % 64)
                    mask |= (1 << bit)
            self.visibility_mask = mask if mask != 0 else (visibility_mask if visibility_mask is not None else ALL_PLAYERS_VISIBLE_MASK)
        elif visibility_mask is not None:
            self.visibility_mask = visibility_mask
            self._players = None
        else:
            self.visibility_mask = ALL_PLAYERS_VISIBLE_MASK
            self._players = None

    @property
    def players(self) -> List[PlayerVisibilityItem]:
        """Backward compatibility property returning PlayerVisibilityItem list."""
        if self._players is not None:
            return self._players
        items = []
        for i in range(50):
            if self.visibility_mask & (1 << i):
                items.append(PlayerVisibilityItem(entity_id=i, is_visible=True))
        return items

    def set_player_visible(self, player_index: int, visible: bool = True) -> None:
        """Sets visibility bit for player_index (0..63)."""
        if 0 <= player_index < 64:
            if visible:
                self.visibility_mask |= (1 << player_index)
            else:
                self.visibility_mask &= ~(1 << player_index)

    def is_player_visible(self, player_index: int) -> bool:
        """Checks visibility bit for player_index (0..63)."""
        if 0 <= player_index < 64:
            return bool(self.visibility_mask & (1 << player_index))
        return False

    def serialize(self, target_len: int = 24) -> bytes:
        """Serializes exact IL2CPP wire representation (<Q, 8 bytes).
        
        Args:
            target_len: Target wire length (default 24 to match authentic 1.39 burst).
                        Pass 8 for minimal unpadded 8-byte payload.
        """
        raw = struct.pack("<Q", self.visibility_mask & 0xFFFFFFFFFFFFFFFF)
        if target_len > 8:
            return raw.ljust(target_len, b"\x00")
        return raw

    def serialize_raw(self) -> bytes:
        """Serializes minimal unpadded 8-byte payload (<Q)."""
        return struct.pack("<Q", self.visibility_mask & 0xFFFFFFFFFFFFFFFF)

    def serialize_padded(self, target_len: int = 24) -> bytes:
        """Serializes payload padded with zeros to target_len (default 24B)."""
        return self.serialize(target_len=target_len)

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_SyncPlayersVisibility":
        """Decodes wire bytes into S2C_SyncPlayersVisibility.
        
        Reads 8-byte unsigned integer (<Q) matching message.HIFZsBP.UnSerialize (RVA 0x208b84e).
        Also handles legacy/fallback formats gracefully.
        """
        if not data:
            return cls(visibility_mask=ALL_PLAYERS_VISIBLE_MASK)

        # Authentic IL2CPP wire layout: 8 bytes uint64 (<Q)
        if len(data) >= 8:
            # Check if this could be legacy format: count (4B) + count * 5B
            # If len == 4 + count * 5 and count in 1..20, handle as legacy
            if len(data) >= 9:
                possible_count = struct.unpack_from("<i", data, 0)[0]
                if 0 < possible_count <= 20 and len(data) == 4 + possible_count * 5:
                    players = []
                    offset = 4
                    mask = 0
                    for _ in range(possible_count):
                        eid, vis = struct.unpack_from("<iB", data, offset)
                        offset += 5
                        players.append(PlayerVisibilityItem(entity_id=eid, is_visible=bool(vis)))
                        if vis:
                            mask |= (1 << (eid % 64))
                    return cls(visibility_mask=mask, players=players)

            mask = struct.unpack_from("<Q", data, 0)[0]
            return cls(visibility_mask=mask)

        # Partial / 4-byte format
        if len(data) >= 4:
            mask32 = struct.unpack_from("<I", data, 0)[0]
            return cls(visibility_mask=mask32)

        return cls(visibility_mask=ALL_PLAYERS_VISIBLE_MASK)


# Aliases for convenient importing across server modules
RUDP_SyncPlayersVisibility = S2C_SyncPlayersVisibility
Opcode135Codec = S2C_SyncPlayersVisibility


if __name__ == "__main__":
    print("Testing Opcode 135 (RUDP_SYNC_PLAYERS_VISIBILITY) codec...")

    # Test 1: Default all players visible
    pkt_all = S2C_SyncPlayersVisibility()
    assert pkt_all.visibility_mask == 0xFFFFFFFFFFFFFFFF
    assert pkt_all.is_player_visible(0) is True
    assert pkt_all.is_player_visible(49) is True
    wire_raw = pkt_all.serialize_raw()
    assert len(wire_raw) == 8, f"Expected 8 bytes, got {len(wire_raw)}"
    assert wire_raw == b"\xff\xff\xff\xff\xff\xff\xff\xff"
    dec_all = S2C_SyncPlayersVisibility.unserialize(wire_raw)
    assert dec_all.visibility_mask == 0xFFFFFFFFFFFFFFFF
    print(f"  [OK] Default all-visible (8B raw): {wire_raw.hex()}")

    # Test 2: Authentic 24-byte burst payload format
    wire_padded = pkt_all.serialize(target_len=24)
    assert len(wire_padded) == 24, f"Expected 24 bytes, got {len(wire_padded)}"
    assert wire_padded[:8] == b"\xff\xff\xff\xff\xff\xff\xff\xff"
    assert wire_padded[8:] == b"\x00" * 16
    dec_padded = S2C_SyncPlayersVisibility.unserialize(wire_padded)
    assert dec_padded.visibility_mask == 0xFFFFFFFFFFFFFFFF
    print(f"  [OK] Authentic 24B padded burst wire: {wire_padded.hex()}")

    # Test 3: Specific player visibility bitmask manipulation
    pkt_custom = S2C_SyncPlayersVisibility(visibility_mask=0)
    pkt_custom.set_player_visible(1, True)
    pkt_custom.set_player_visible(5, True)
    pkt_custom.set_player_visible(10, True)
    expected_mask = (1 << 1) | (1 << 5) | (1 << 10)
    assert pkt_custom.visibility_mask == expected_mask
    assert pkt_custom.is_player_visible(1) is True
    assert pkt_custom.is_player_visible(2) is False
    assert pkt_custom.is_player_visible(5) is True
    assert pkt_custom.is_player_visible(10) is True
    wire_custom = pkt_custom.serialize_raw()
    dec_custom = S2C_SyncPlayersVisibility.unserialize(wire_custom)
    assert dec_custom.visibility_mask == expected_mask
    assert dec_custom.is_player_visible(1) is True
    assert dec_custom.is_player_visible(5) is True
    print(f"  [OK] Custom bitmask (players 1, 5, 10): mask={hex(expected_mask)}, wire={wire_custom.hex()}")

    # Test 4: Compatibility with legacy PlayerVisibilityItem constructor
    vis_items = [PlayerVisibilityItem(entity_id=1, is_visible=True), PlayerVisibilityItem(entity_id=2, is_visible=False)]
    pkt_compat = S2C_SyncPlayersVisibility(players=vis_items)
    assert pkt_compat.is_player_visible(1) is True
    assert pkt_compat.is_player_visible(2) is False
    wire_compat = pkt_compat.serialize(target_len=24)
    assert len(wire_compat) == 24
    dec_compat = S2C_SyncPlayersVisibility.unserialize(wire_compat)
    assert dec_compat.is_player_visible(1) is True
    print(f"  [OK] Backward compatibility constructor: mask={hex(pkt_compat.visibility_mask)}")

    print("All Opcode 135 codec tests passed successfully!")
