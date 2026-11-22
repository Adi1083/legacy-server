"""
UDP Game Combat Protocol Definitions and Packet Codec for Free Fire (Barbosa / OB17).
Extracted directly from Barbosa IL2CPP Metadata v23 (TypeDef [9777]: GCommon.UDPMsgPacket).
"""

import struct
from typing import Optional, Tuple, NamedTuple, Any

# Authentic Free Fire 1.39 CRC-7 Table (Polynomial 0x09: x^7 + x^3 + 1)
# Extracted directly from Barbosa IL2CPP Metadata v23 (Field [55626], offset 0x643DCB)
CRC7_TABLE = [
    0x00, 0x09, 0x12, 0x1b, 0x24, 0x2d, 0x36, 0x3f,
    0x48, 0x41, 0x5a, 0x53, 0x6c, 0x65, 0x7e, 0x77,
    0x19, 0x10, 0x0b, 0x02, 0x3d, 0x34, 0x2f, 0x26,
    0x51, 0x58, 0x43, 0x4a, 0x75, 0x7c, 0x67, 0x6e,
    0x32, 0x3b, 0x20, 0x29, 0x16, 0x1f, 0x04, 0x0d,
    0x7a, 0x73, 0x68, 0x61, 0x5e, 0x57, 0x4c, 0x45,
    0x2b, 0x22, 0x39, 0x30, 0x0f, 0x06, 0x1d, 0x14,
    0x63, 0x6a, 0x71, 0x78, 0x47, 0x4e, 0x55, 0x5c,
    0x64, 0x6d, 0x76, 0x7f, 0x40, 0x49, 0x52, 0x5b,
    0x2c, 0x25, 0x3e, 0x37, 0x08, 0x01, 0x1a, 0x13,
    0x7d, 0x74, 0x6f, 0x66, 0x59, 0x50, 0x4b, 0x42,
    0x35, 0x3c, 0x27, 0x2e, 0x11, 0x18, 0x03, 0x0a,
    0x56, 0x5f, 0x44, 0x4d, 0x72, 0x7b, 0x60, 0x69,
    0x1e, 0x17, 0x0c, 0x05, 0x3a, 0x33, 0x28, 0x21,
    0x4f, 0x46, 0x5d, 0x54, 0x6b, 0x62, 0x79, 0x70,
    0x07, 0x0e, 0x15, 0x1c, 0x23, 0x2a, 0x31, 0x38,
    0x41, 0x48, 0x53, 0x5a, 0x65, 0x6c, 0x77, 0x7e,
    0x09, 0x00, 0x1b, 0x12, 0x2d, 0x24, 0x3f, 0x36,
    0x58, 0x51, 0x4a, 0x43, 0x7c, 0x75, 0x6e, 0x67,
    0x10, 0x19, 0x02, 0x0b, 0x34, 0x3d, 0x26, 0x2f,
    0x73, 0x7a, 0x61, 0x68, 0x57, 0x5e, 0x45, 0x4c,
    0x3b, 0x32, 0x29, 0x20, 0x1f, 0x16, 0x0d, 0x04,
    0x6a, 0x63, 0x78, 0x71, 0x4e, 0x47, 0x5c, 0x55,
    0x22, 0x2b, 0x30, 0x39, 0x06, 0x0f, 0x14, 0x1d,
    0x25, 0x2c, 0x37, 0x3e, 0x01, 0x08, 0x13, 0x1a,
    0x6d, 0x64, 0x7f, 0x76, 0x49, 0x40, 0x5b, 0x52,
    0x3c, 0x35, 0x2e, 0x27, 0x18, 0x11, 0x0a, 0x03,
    0x74, 0x7d, 0x66, 0x6f, 0x50, 0x59, 0x42, 0x4b,
    0x17, 0x1e, 0x05, 0x0c, 0x33, 0x3a, 0x21, 0x28,
    0x5f, 0x56, 0x4d, 0x44, 0x7b, 0x72, 0x69, 0x60,
    0x0e, 0x07, 0x1c, 0x15, 0x2a, 0x23, 0x38, 0x31,
    0x46, 0x4f, 0x54, 0x5d, 0x62, 0x6b, 0x70, 0x79,
]

def calculate_crc7(data: bytes, initial: int = 0) -> int:
    crc = initial & 0x7f
    for b in data:
        idx = ((crc << 1) ^ b) & 0xff
        crc = CRC7_TABLE[idx] & 0x7f
    return crc


# Protocol Constants (TypeDef [9777]: GCommon.UDPMsgPacket)
UDPMESSAGE_MSGKEY = 0x6c
UDPMESSAGE_HEADER_MINI_SIZE = 5
UDPMESSAGE_HEADER_NONRELIABLE_SIZE = 8
UDPMESSAGE_HEADER_RELIABLE_SIZE = 12

class SendOption:
    NONE = 0
    HELLO = 1
    RELIABLE = 2
    BYEBYE = 3
    VAR = 4
    VAR_RELIABLE = 5

class ReservedMsgID:
    UDP_HELLO = 1
    UDP_ACK = 2
    UDP_PING = 3
    UDP_BYEBYE = 4
    UDP_LONGTIMENOSEE = 5

class PacketFlags:
    NONE = 0
    ENCRYPTION = 1
    ZIP = 2
    GAME_DISPATCH = 4  # (flags & 0xfe) == 4 required by MatchGameClient.HandleRecvPacket (0x0204053d / 0x19a466c)

class UDMPacket:
    def __init__(
        self,
        send_option: int,
        cmd: int,
        seq_id: int = 0,
        order_id: Optional[int] = None,
        flags: int = 0,
        data: bytes = b"",
        msg_key: int = UDPMESSAGE_MSGKEY,
        crc7: int = 0
    ):
        self.msg_key = msg_key
        self.crc7 = crc7
        self.send_option = send_option
        self.cmd = cmd
        self.seq_id = seq_id
        self.order_id = 0 if order_id is None else (order_id & 0xffff)
        self._order_id_explicit = (order_id is not None)
        self.flags = flags & 0xff
        self.data = data
        self.length = len(data)

    def is_reliable(self) -> bool:
        return self.send_option in (SendOption.HELLO, SendOption.RELIABLE, SendOption.VAR_RELIABLE)

    def is_var(self) -> bool:
        return self.send_option in (SendOption.VAR, SendOption.VAR_RELIABLE)

    def serialize(self) -> bytes:
        """
        Serializes packet into wire format matching TypeDef [9777]:
        Reliable (SendOption == 2 or 5, Header 12B):
            [1B MsgKey][1B CRC7][1B SendOption][2B Cmd][2B SeqID][2B OrderID][1B Flags][2B Length][Payload]
        Non-Reliable (Header 8B):
            [1B MsgKey][1B CRC7][1B SendOption][2B Cmd][2B SeqID][1B Flags][Payload]
        Mini (Header 5B):
            [1B MsgKey][1B CRC7][1B SendOption][2B Cmd][Payload]
        """
        buf = bytearray()
        buf.append(self.msg_key & 0xff)
        buf.append(0) # Placeholder for CRC7
        buf.append(self.send_option & 0xff)
        # Cmd is uint16 (2 bytes little-endian)
        buf.extend(struct.pack("<H", self.cmd & 0xffff))

        if self.is_reliable():
            buf.extend(struct.pack(
                "<HHBH",
                self.seq_id & 0xffff,
                self.order_id & 0xffff,
                self.flags & 0xff,
                len(self.data) & 0xffff
            ))
        else:
            buf.extend(struct.pack(
                "<BH",
                self.flags & 0xff,
                len(self.data) & 0xffff
            ))

        buf.extend(self.data)

        # Compute CRC7 over payload and header starting after CRC7 byte (buf[2:])
        crc = calculate_crc7(bytes(buf[2:]))
        self.crc7 = crc & 0x7f
        buf[1] = self.crc7
        return bytes(buf)

    @classmethod
    def unserialize(cls, raw: bytes) -> Optional["UDMPacket"]:
        if len(raw) < UDPMESSAGE_HEADER_MINI_SIZE:
            return None

        msg_key = raw[0]
        crc7 = raw[1]
        send_option = raw[2]
        cmd, = struct.unpack("<H", raw[3:5])

        if send_option in (SendOption.HELLO, SendOption.RELIABLE, SendOption.VAR_RELIABLE):
            if len(raw) < UDPMESSAGE_HEADER_RELIABLE_SIZE:
                return None
            seq_id, order_id, flags, length = struct.unpack("<HHBH", raw[5:12])
            payload = raw[12:12+length]
            return cls(
                send_option=send_option,
                cmd=cmd,
                seq_id=seq_id,
                order_id=order_id,
                flags=flags,
                data=payload,
                msg_key=msg_key,
                crc7=crc7
            )
        else:
            if len(raw) < UDPMESSAGE_HEADER_NONRELIABLE_SIZE:
                # Mini header (5 bytes)
                flags = 0
                payload = raw[5:]
            else:
                flags, length = struct.unpack("<BH", raw[5:8])
                payload = raw[8:8+length]

            return cls(
                send_option=send_option,
                cmd=cmd,
                seq_id=0,
                order_id=0,
                flags=flags,
                data=payload,
                msg_key=msg_key,
                crc7=crc7
            )


class S2C_Hello_Res:
    """
    S2C_Hello_Res (TypeDef [9771]):
    SessionKey: string (ReadString: 4-byte uint32 length + UTF-8 payload)
    5 bytes: 1B null/padding + uint16 order_id + uint16 required_id
    Total authentic wire payload = 28 bytes.
    """
    def __init__(self, session_key: Any = "mk-9d10bffc98767f2f", order_id: int = 0, required_id: int = 0):
        if isinstance(session_key, int):
            self.session_key = f"{session_key:08x}"
        else:
            self.session_key = str(session_key)
        self.order_id = order_id
        self.required_id = required_id

    def serialize(self) -> bytes:
        raw_key = self.session_key.encode("utf-8")
        # Format: 4B string len + raw_key + 1B null/padding + 2B order_id + 2B required_id
        res = struct.pack("<I", len(raw_key)) + raw_key + b"\x00" + struct.pack("<HH", self.order_id, self.required_id)
        if len(res) < 28:
            res = res + b"\x00" * (28 - len(res))
        return res[:28]

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_Hello_Res":
        str_len = struct.unpack("<I", data[:4])[0]
        session_key = data[4:4+str_len].decode("utf-8", errors="ignore")
        order_id, required_id = struct.unpack("<HH", data[4+str_len+1:8+str_len+1])
        return cls(session_key, order_id, required_id)


class UDP_Ack_Res:
    """
    UDP_Ack_Res (TypeDef [9772]):
    Ack: uint16 (SequenceID being acknowledged)
    AckBits: uint32 (Bitmask of previous 32 sequence IDs received)
    """
    def __init__(self, ack: int, ack_bits: int = 0):
        self.ack = ack
        self.ack_bits = ack_bits

    def serialize(self) -> bytes:
        return struct.pack("<HI", self.ack, self.ack_bits)

    @classmethod
    def unserialize(cls, data: bytes) -> "UDP_Ack_Res":
        ack, ack_bits = struct.unpack("<HI", data[:6])
        return cls(ack, ack_bits)


class C2S_UDP_Ping_Req:
    def __init__(self, send_tick_count: int):
        self.send_tick_count = send_tick_count

    def serialize(self) -> bytes:
        return struct.pack("<Q", self.send_tick_count)

    @classmethod
    def unserialize(cls, data: bytes) -> "C2S_UDP_Ping_Req":
        tick = struct.unpack("<Q", data[:8])[0]
        return cls(tick)


class S2C_UDP_Ping_Res:
    def __init__(self, send_tick_count: int):
        self.send_tick_count = send_tick_count

    def serialize(self) -> bytes:
        return struct.pack("<Q", self.send_tick_count)

    @classmethod
    def unserialize(cls, data: bytes) -> "S2C_UDP_Ping_Res":
        tick = struct.unpack("<Q", data[:8])[0]
        return cls(tick)
