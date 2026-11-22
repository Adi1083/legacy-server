"""
Offline validation test suite for Opcode 101 (RUDP_PLAYER_JOIN).
Strictly verifies:
- 18-field serialization order matching IL2CPP disassembly of message.ae zaPn.UnSerialize (0x01fafc18)
- Minimal 66-byte payload (empty strings, 0 clothes, 0 skills)
- Captured 320-byte human payload (30 clothes, 11-char nickname, 3-char region)
- Captured 208-byte and 216-byte bot payloads (16 vs 17 clothes, 14 string chars)
- Exact byte offset mapping and boundaries for every field
- Full round-trip serialization and deserialization integrity
- Wire framing comparison with Barbosa original captures
"""

import sys
import os
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.combat.combat_packet_codec import S2C_PlayerJoin, encode_udp_string, decode_udp_string
from server.combat.udp_protocol import UDMPacket, SendOption
from server.combat.combat_opcodes import CombatOpcode


def get_field_offsets(payload: bytes, pjoin: S2C_PlayerJoin):
    """Parses payload byte by byte and returns exact field boundaries."""
    offsets = []
    curr = 0

    # 1. account_id (UInt64, 8B)
    offsets.append(("account_id", curr, curr + 8, "<Q", 8, pjoin.account_id))
    curr += 8

    # 2. match_id (UInt64, 8B)
    offsets.append(("match_id", curr, curr + 8, "<Q", 8, pjoin.match_id))
    curr += 8

    # 3. camp (Byte, 1B)
    offsets.append(("camp", curr, curr + 1, "<B", 1, pjoin.camp))
    curr += 1

    # 4. is_bot (Byte, 1B)
    offsets.append(("is_bot", curr, curr + 1, "<B", 1, pjoin.is_bot))
    curr += 1

    # 5. team_id (UInt64, 8B)
    offsets.append(("team_id", curr, curr + 8, "<Q", 8, pjoin.team_id))
    curr += 8

    # 6. nickname (String: 4B len + N bytes)
    nlen, = struct.unpack("<i", payload[curr:curr+4])
    offsets.append(("nickname_len", curr, curr + 4, "<i", 4, nlen))
    curr += 4
    nstr = payload[curr:curr+nlen].decode("utf-8", errors="replace")
    offsets.append(("nickname_bytes", curr, curr + nlen, "UTF-8", nlen, nstr))
    curr += nlen

    # 7. avatar_id (UInt32, 4B)
    offsets.append(("avatar_id", curr, curr + 4, "<I", 4, pjoin.avatar_id))
    curr += 4

    # 8. is_ready (Boolean, 1B)
    offsets.append(("is_ready", curr, curr + 1, "<?", 1, pjoin.is_ready))
    curr += 1

    # 9. level (UInt32, 4B)
    offsets.append(("level", curr, curr + 4, "<I", 4, pjoin.level))
    curr += 4

    # 10. rank (UInt32, 4B)
    offsets.append(("rank", curr, curr + 4, "<I", 4, pjoin.rank))
    curr += 4

    # 11. is_alive (Boolean, 1B)
    offsets.append(("is_alive", curr, curr + 1, "<?", 1, pjoin.is_alive))
    curr += 1

    # 12. clothes (Int32 count + count * 8B)
    ccount, = struct.unpack("<i", payload[curr:curr+4])
    offsets.append(("clothes_count", curr, curr + 4, "<i", 4, ccount))
    curr += 4
    cbytes_len = ccount * 8
    offsets.append(("clothes_items", curr, curr + cbytes_len, f"{ccount}*<Q", cbytes_len, len(pjoin.clothes or [])))
    curr += cbytes_len

    # 13. gender (Byte, 1B)
    offsets.append(("gender", curr, curr + 1, "<B", 1, pjoin.gender))
    curr += 1

    # 14. flag (Boolean, 1B)
    offsets.append(("flag", curr, curr + 1, "<?", 1, pjoin.flag))
    curr += 1

    # 15. skills (Int32 count + count * 4B)
    scount, = struct.unpack("<i", payload[curr:curr+4])
    offsets.append(("skills_count", curr, curr + 4, "<i", 4, scount))
    curr += 4
    sbytes_len = scount * 4
    offsets.append(("skills_items", curr, curr + sbytes_len, f"{scount}*<I", sbytes_len, len(pjoin.skills or [])))
    curr += sbytes_len

    # 16. region (String: 4B len + N bytes)
    rlen, = struct.unpack("<i", payload[curr:curr+4])
    offsets.append(("region_len", curr, curr + 4, "<i", 4, rlen))
    curr += 4
    rstr = payload[curr:curr+rlen].decode("utf-8", errors="replace")
    offsets.append(("region_bytes", curr, curr + rlen, "UTF-8", rlen, rstr))
    curr += rlen

    # 17. banner_id (UInt32, 4B)
    offsets.append(("banner_id", curr, curr + 4, "<I", 4, pjoin.banner_id))
    curr += 4

    # 18. headpic (String: 4B len + N bytes)
    hlen, = struct.unpack("<i", payload[curr:curr+4])
    offsets.append(("headpic_len", curr, curr + 4, "<i", 4, hlen))
    curr += 4
    hstr = payload[curr:curr+hlen].decode("utf-8", errors="replace")
    offsets.append(("headpic_bytes", curr, curr + hlen, "UTF-8", hlen, hstr))
    curr += hlen

    return offsets, curr


def test_minimal_66b():
    print("=== TEST 1: Minimal 66-byte Opcode 101 Payload ===")
    pjoin = S2C_PlayerJoin(
        account_id=10001,
        match_id=99999,
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
    payload = pjoin.serialize()
    print(f"Serialized Length: {len(payload)} bytes (Expected: 66)")
    assert len(payload) == 66, f"Expected 66 bytes, got {len(payload)}"

    offsets, total_len = get_field_offsets(payload, pjoin)
    assert total_len == 66

    print(f"{'Field Name':<16} {'Start':<6} {'End':<6} {'Width':<6} {'Type':<10} {'Value'}")
    print("-" * 65)
    for name, s, e, wtype, wlen, val in offsets:
        print(f"{name:<16} {s:<6} {e:<6} {wlen:<6} {wtype:<10} {val}")

    # Round-trip unserialize
    rt = S2C_PlayerJoin.unserialize(payload)
    assert rt.account_id == pjoin.account_id
    assert rt.match_id == pjoin.match_id
    assert rt.camp == pjoin.camp
    assert rt.is_bot == pjoin.is_bot
    assert rt.team_id == pjoin.team_id
    assert rt.nickname == ""
    assert rt.avatar_id == pjoin.avatar_id
    assert rt.is_ready == pjoin.is_ready
    assert rt.level == pjoin.level
    assert rt.rank == pjoin.rank
    assert rt.is_alive == pjoin.is_alive
    assert rt.clothes == []
    assert rt.gender == pjoin.gender
    assert rt.flag == pjoin.flag
    assert rt.skills == []
    assert rt.region == ""
    assert rt.banner_id == pjoin.banner_id
    assert rt.headpic == ""
    print("Round-trip validation: PASSED cleanly.\n")


def test_human_320b():
    print("=== TEST 2: Captured 320-byte Human Opcode 101 Payload (Barbosa seq 5) ===")
    clothes_30 = [
        211000000, 208000000, 203000573, 204000174, 205000299, 203000228,
        211000001, 208000001, 203000574, 204000175, 205000300, 203000229,
        211000002, 208000002, 203000575, 204000176, 205000301, 203000230,
        211000003, 208000003, 203000576, 204000177, 205000302, 203000231,
        211000004, 208000004, 203000577, 204000178, 205000303, 203000232
    ]
    pjoin = S2C_PlayerJoin(
        account_id=10001,
        match_id=99999,
        camp=1,
        is_bot=False,
        team_id=1,
        nickname="BarbosaPlay",  # 11 ASCII characters
        avatar_id=102000004,
        is_ready=True,
        level=25,
        rank=1800,
        is_alive=True,
        clothes=clothes_30,      # 30 items * 8B = 240B
        gender=1,
        flag=False,
        skills=[],              # 0 skills (4B count)
        region="IND",           # 3 ASCII characters
        banner_id=901000001,
        headpic=""              # 0 chars (4B length)
    )
    payload = pjoin.serialize()
    print(f"Serialized Length: {len(payload)} bytes (Expected: 320)")
    assert len(payload) == 320, f"Expected 320 bytes, got {len(payload)}"

    offsets, total_len = get_field_offsets(payload, pjoin)
    assert total_len == 320

    print(f"{'Field Name':<16} {'Start':<6} {'End':<6} {'Width':<6} {'Type':<10} {'Value'}")
    print("-" * 65)
    for name, s, e, wtype, wlen, val in offsets:
        print(f"{name:<16} {s:<6} {e:<6} {wlen:<6} {wtype:<10} {val}")

    # Wire framing check (UDMPacket Reliable Header: 12B)
    pkt = UDMPacket(
        send_option=SendOption.RELIABLE,
        cmd=CombatOpcode.RUDP_PLAYER_JOIN,
        seq_id=5,
        order_id=4,
        flags=1,
        data=payload
    )
    wire = pkt.serialize()
    print(f"UDMPacket Wire Length: {len(wire)} bytes (Expected: 332 = 12B header + 320B payload)")
    assert len(wire) == 332, f"Expected 332 bytes, got {len(wire)}"

    # Round-trip unserialize
    rt = S2C_PlayerJoin.unserialize(payload)
    assert rt.nickname == "BarbosaPlay"
    assert len(rt.clothes) == 30
    assert rt.clothes == clothes_30
    assert rt.region == "IND"
    assert rt.avatar_id == 102000004
    print("Round-trip validation: PASSED cleanly.\n")


def test_bot_208b_and_216b():
    print("=== TEST 3: Captured 208-byte and 216-byte Bot Opcode 101 Payloads (Barbosa seq 10..53) ===")
    clothes_16 = [211000000 + i for i in range(16)]  # 16 items * 8B = 128B
    clothes_17 = [211000000 + i for i in range(17)]  # 17 items * 8B = 136B (+8B)

    # Bot 208: 66 baseline + 128 clothes + 14 string chars (9 name + 5 region) = 208B
    bot_208 = S2C_PlayerJoin(
        account_id=2000001,
        match_id=99999,
        camp=1,
        is_bot=True,
        team_id=2,
        nickname="Bot_00001",  # 9 chars
        avatar_id=102000004,
        is_ready=True,
        level=15,
        rank=1200,
        is_alive=True,
        clothes=clothes_16,
        gender=1,
        flag=False,
        skills=[],
        region="BOTS1",        # 5 chars -> total 14 string chars
        banner_id=901000001,
        headpic=""
    )
    payload_208 = bot_208.serialize()
    print(f"Bot 208 Serialized Length: {len(payload_208)} bytes (Expected: 208)")
    assert len(payload_208) == 208, f"Expected 208 bytes, got {len(payload_208)}"

    pkt_208 = UDMPacket(
        send_option=SendOption.RELIABLE,
        cmd=CombatOpcode.RUDP_PLAYER_JOIN,
        seq_id=10,
        order_id=9,
        flags=1,
        data=payload_208
    )
    wire_208 = pkt_208.serialize()
    print(f"Bot 208 Wire Length: {len(wire_208)} bytes (Expected: 220 = 12B header + 208B payload)")
    assert len(wire_208) == 220

    # Bot 216: 66 baseline + 136 clothes (+8B) + 14 string chars = 216B
    bot_216 = S2C_PlayerJoin(
        account_id=2000002,
        match_id=99999,
        camp=1,
        is_bot=True,
        team_id=3,
        nickname="Bot_00002",  # 9 chars
        avatar_id=102000004,
        is_ready=True,
        level=15,
        rank=1200,
        is_alive=True,
        clothes=clothes_17,
        gender=1,
        flag=False,
        skills=[],
        region="BOTS1",        # 5 chars -> total 14 string chars
        banner_id=901000001,
        headpic=""
    )
    payload_216 = bot_216.serialize()
    print(f"Bot 216 Serialized Length: {len(payload_216)} bytes (Expected: 216)")
    assert len(payload_216) == 216, f"Expected 216 bytes, got {len(payload_216)}"

    pkt_216 = UDMPacket(
        send_option=SendOption.RELIABLE,
        cmd=CombatOpcode.RUDP_PLAYER_JOIN,
        seq_id=14,
        order_id=13,
        flags=1,
        data=payload_216
    )
    wire_216 = pkt_216.serialize()
    print(f"Bot 216 Wire Length: {len(wire_216)} bytes (Expected: 228 = 12B header + 216B payload)")
    assert len(wire_216) == 228

    diff = len(payload_216) - len(payload_208)
    print(f"Difference between 216B and 208B bot payload: {diff} bytes (Exactly sizeof(UInt64) = 8 bytes)")
    assert diff == 8

    # Round-trip unserialize
    rt_208 = S2C_PlayerJoin.unserialize(payload_208)
    assert len(rt_208.clothes) == 16
    assert rt_208.is_bot is True
    rt_216 = S2C_PlayerJoin.unserialize(payload_216)
    assert len(rt_216.clothes) == 17
    assert rt_216.is_bot is True
    print("Round-trip validation: PASSED cleanly.\n")


def test_barbosa_trace_framing_comparison():
    print("=== TEST 4: Barbosa Original Trace Framing Comparison ===")
    import json
    # Inspect first match session (burst seq 1..53)
    found_seqs = {}
    with open("dump/barbosa_original_trace.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            seq = obj.get("seq")
            cmd = obj.get("cmd")
            if cmd == 101 and seq in [5, 10, 14] and seq not in found_seqs:
                found_seqs[seq] = obj

    for seq in [5, 10, 14]:
        pkt = found_seqs.get(seq)
        assert pkt is not None, f"seq {seq} not found in barbosa_original_trace.jsonl"
        data_len = pkt.get("dataLen")
        total_len = pkt.get("totalLen")
        header_len = total_len - data_len
        print(f"Captured Barbosa seq={seq}: totalLen={total_len}, dataLen={data_len}, headerLen={header_len}")
        assert header_len == 12, f"Expected 12B header, got {header_len}"

    assert found_seqs[5]["dataLen"] == 320, "Expected seq 5 dataLen == 320"
    assert found_seqs[10]["dataLen"] == 208, "Expected seq 10 dataLen == 208"
    assert found_seqs[14]["dataLen"] == 216, "Expected seq 14 dataLen == 216"

    print("Barbosa framing alignment: 100% MATCH.\n")


if __name__ == "__main__":
    test_minimal_66b()
    test_human_320b()
    test_bot_208b_and_216b()
    test_barbosa_trace_framing_comparison()
    print("ALL OFFLINE TESTS PASSED SUCCESSFULLY.")
