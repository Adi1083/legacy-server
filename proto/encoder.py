# Protobuf Wire Encoder Helper
import struct

def encode_varint(value):
    value = int(value)
    if value < 0:
        value &= 0xFFFFFFFFFFFFFFFF
    b = bytearray()
    while value > 0x7F:
        b.append((value & 0x7F) | 0x80)
        value >>= 7
    b.append(value & 0x7F)
    return bytes(b)

def encode_tag(field_num, wire_type):
    return encode_varint((field_num << 3) | wire_type)

def encode_uint64(field_num, val):
    return encode_tag(field_num, 0) + encode_varint(int(val) & 0xFFFFFFFFFFFFFFFF)

def encode_int64(field_num, value):
    val = int(value)
    if val < 0:
        val = (val + (1 << 64)) & 0xFFFFFFFFFFFFFFFF
    return encode_tag(field_num, 0) + encode_varint(val)

def encode_int32(field_num, val):
    val = int(val)
    if val < 0:
        val = (val + (1 << 64)) & 0xFFFFFFFFFFFFFFFF
    return encode_tag(field_num, 0) + encode_varint(val)

def encode_uint32(field_num, val):
    return encode_tag(field_num, 0) + encode_varint(int(val) & 0xFFFFFFFF)

def encode_bool(field_num, val):
    return encode_tag(field_num, 0) + encode_varint(1 if val else 0)

def encode_string(field_num, s):
    raw = str(s).encode('utf-8')
    return encode_tag(field_num, 2) + encode_varint(len(raw)) + raw

def encode_bytes(field_num, data):
    raw = bytes(data)
    return encode_tag(field_num, 2) + encode_varint(len(raw)) + raw

def encode_submessage(field_num, content=b""):
    raw = bytes(content)
    return encode_tag(field_num, 2) + encode_varint(len(raw)) + raw

def encode_fixed64(field_num, val):
    return encode_tag(field_num, 1) + struct.pack('<d', float(val))

def encode_float(field_num, value):
    return encode_tag(field_num, 5) + struct.pack('<f', float(value))

def _encode_packed(field_num, values, mask=None):
    vals = list(values or ())
    if not vals:
        return b""
    buf = bytearray()
    for v in vals:
        iv = int(v)
        if mask is not None and iv < 0:
            iv = (iv + (1 << 64)) & 0xFFFFFFFFFFFFFFFF
        elif mask is not None:
            iv &= mask
        buf += encode_varint(iv)
    return encode_bytes(field_num, buf)

def encode_packed_uint32(field_num, values):
    return _encode_packed(field_num, values, mask=0xFFFFFFFF)

def encode_packed_uint64(field_num, values):
    return _encode_packed(field_num, values, mask=0xFFFFFFFFFFFFFFFF)
