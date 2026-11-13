import os
import struct
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

request_history: List[Dict[str, Any]] = []
history_lock = threading.Lock()
_request_seq = 0
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requests.log")

WIRE_TYPE_NAMES = {
    0: "varint",
    1: "fixed64",
    2: "length_delimited",
    5: "fixed32",
}


def _read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    result = 0
    shift = 0
    length = len(data)
    while pos < length:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift > 70:
            raise ValueError("varint too long")
    raise ValueError("truncated varint")


def _is_printable_utf8(raw: bytes) -> Optional[str]:
    if not raw:
        return ""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    for ch in text:
        code = ord(ch)
        if code < 32 and ch not in ("\t", "\n", "\r"):
            return None
        if code == 127:
            return None
    return text


def _try_decode_packed_varints(raw: bytes, max_items: int = 128) -> Optional[List[int]]:
    if len(raw) < 2:
        return None
    pos = 0
    vals: List[int] = []
    try:
        while pos < len(raw):
            v, pos = _read_varint(raw, pos)
            vals.append(v)
            if len(vals) > max_items:
                return None
    except ValueError:
        return None
    return vals if len(vals) >= 2 else None


def decode_protobuf_wire(
    data: bytes,
    depth: int = 0,
    max_depth: int = 5,
    max_fields: int = 200,
) -> Dict[str, Any]:
    """Best-effort recursive Protobuf wire decoder for live request inspection."""
    if not data:
        return {"is_protobuf": False, "fields": [], "summary": "empty"}

    pos = 0
    total = len(data)
    fields: List[Dict[str, Any]] = []

    try:
        while pos < total:
            if len(fields) >= max_fields:
                break
            tag, pos = _read_varint(data, pos)
            field_num = tag >> 3
            wire_type = tag & 0x07
            if field_num <= 0 or field_num > 100000 or wire_type not in WIRE_TYPE_NAMES:
                return {
                    "is_protobuf": False,
                    "fields": [],
                    "error": f"invalid tag/wire at offset {pos - 1} (field={field_num}, wire={wire_type})",
                }

            entry: Dict[str, Any] = {
                "field": field_num,
                "wire_type": WIRE_TYPE_NAMES[wire_type],
            }

            if wire_type == 0:
                val, pos = _read_varint(data, pos)
                entry["type"] = "varint"
                entry["value"] = val
                if val >= (1 << 63):
                    entry["signed"] = val - (1 << 64)
            elif wire_type == 1:
                if pos + 8 > total:
                    return {"is_protobuf": False, "fields": [], "error": "truncated fixed64"}
                chunk = data[pos : pos + 8]
                pos += 8
                u64 = struct.unpack("<Q", chunk)[0]
                f64 = struct.unpack("<d", chunk)[0]
                entry["type"] = "fixed64"
                entry["value"] = u64
                entry["double"] = f64 if (f64 == f64 and abs(f64) < 1e300) else None
                entry["hex"] = chunk.hex()
            elif wire_type == 5:
                if pos + 4 > total:
                    return {"is_protobuf": False, "fields": [], "error": "truncated fixed32"}
                chunk = data[pos : pos + 4]
                pos += 4
                u32 = struct.unpack("<I", chunk)[0]
                f32 = struct.unpack("<f", chunk)[0]
                entry["type"] = "fixed32"
                entry["value"] = u32
                entry["float"] = round(f32, 6) if (f32 == f32 and abs(f32) < 1e30) else None
                entry["hex"] = chunk.hex()
            elif wire_type == 2:
                length, pos = _read_varint(data, pos)
                if length < 0 or pos + length > total:
                    return {"is_protobuf": False, "fields": [], "error": "truncated length_delimited"}
                chunk = data[pos : pos + length]
                pos += length

                if length == 0:
                    entry["type"] = "bytes"
                    entry["value"] = ""
                    entry["length"] = 0
                else:
                    text = _is_printable_utf8(chunk)
                    sub_decoded = None
                    if depth < max_depth and length >= 2:
                        candidate = decode_protobuf_wire(chunk, depth + 1, max_depth, max_fields)
                        if candidate.get("is_protobuf") and candidate.get("fields"):
                            # Ensure plausible field numbers for embedded submessages
                            if all(f["field"] <= 500 for f in candidate["fields"]):
                                sub_decoded = candidate["fields"]

                    if text is not None and (sub_decoded is None or any(ch.isalnum() for ch in text)):
                        entry["type"] = "string"
                        entry["value"] = text
                        entry["length"] = length
                    elif sub_decoded is not None:
                        entry["type"] = "message"
                        entry["fields"] = sub_decoded
                        entry["length"] = length
                    else:
                        entry["type"] = "bytes"
                        entry["length"] = length
                        entry["hex"] = chunk[:256].hex()
                        packed = _try_decode_packed_varints(chunk)
                        if packed is not None:
                            entry["packed_varints"] = packed

            fields.append(entry)
    except ValueError as exc:
        return {"is_protobuf": False, "fields": [], "error": str(exc)}

    preview_parts = []
    for f in fields[:5]:
        if f["type"] == "string":
            s = f["value"]
            if len(s) > 24:
                s = s[:21] + "..."
            preview_parts.append(f"f{f['field']}=\"{s}\"")
        elif f["type"] == "message":
            preview_parts.append(f"f{f['field']}={{...{len(f['fields'])}f}}")
        elif "value" in f:
            preview_parts.append(f"f{f['field']}={f['value']}")
        else:
            preview_parts.append(f"f{f['field']}=<{f.get('length', 0)}B>")

    return {
        "is_protobuf": True,
        "fields": fields,
        "field_count": len(fields),
        "summary": ", ".join(preview_parts) if preview_parts else "empty",
    }


def log_request(method: str, path: str, client_ip: str, body: Optional[bytes] = None) -> Dict[str, Any]:
    global _request_seq
    decoded = decode_protobuf_wire(body) if body else None
    with history_lock:
        _request_seq += 1
        entry = {
            "id": _request_seq,
            "time": time.strftime("%H:%M:%S"),
            "timestamp": time.time(),
            "method": method,
            "path": path,
            "client": client_ip,
            "body_hex": body[:4096].hex() if body else None,
            "body_len": len(body) if body else 0,
            "decoded": decoded,
        }
        request_history.insert(0, entry)
        if len(request_history) > 200:
            request_history.pop()

    line = f"[{entry['time']}] {method} {path} from {client_ip} ({entry['body_len']} bytes)"
    print(line, flush=True)

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

    if method == "GET" and "/banners/" in path and "preview=1" not in path:
        try:
            from core.state import state

            clean_path = path.split("?", 1)[0]
            state.record_lobby_event(
                endpoint=clean_path,
                category="banner_fetch",
                summary=f"Client fetched banner {os.path.basename(clean_path)}",
                detail={"client": client_ip, "path": clean_path},
            )
        except Exception:
            pass

    return entry


def clear_requests() -> int:
    with history_lock:
        count = len(request_history)
        request_history.clear()
        return count
