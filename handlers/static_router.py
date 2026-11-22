import os
import re
import threading
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
LEGACY_ROOT = os.path.dirname(BASE_DIR)
BASE_APK_CANDIDATES = [
    os.path.join(LEGACY_ROOT, "apk", "IND_PROJECT_1.39_SingleBoot_Pushpa.apk"),
    os.path.join(LEGACY_ROOT, "India V1 1.39 base (fix-crash).apk"),
] + [p for p in ([os.path.join(LEGACY_ROOT, "apk", f) for f in os.listdir(os.path.join(LEGACY_ROOT, "apk"))] if os.path.isdir(os.path.join(LEGACY_ROOT, "apk")) else []) if p.endswith('.apk')]
BASE_APK_PATH = next((p for p in BASE_APK_CANDIDATES if os.path.isfile(p)), BASE_APK_CANDIDATES[0])

VERSION = "1.39.4"
SUB_VERSION = "35"

ver_path = os.path.join(STATIC_DIR, "versioninfo")
if os.path.exists(ver_path):
    with open(ver_path, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) >= 2:
            VERSION = lines[0]
            SUB_VERSION = lines[1]

_apk_lock = threading.Lock()
_apk_zip = None
_apk_entries = None


def _get_apk_asset(rel_asset_path: str):
    """Read an entry under assets/android/ from the base APK if present."""
    global _apk_zip, _apk_entries
    if not os.path.isfile(BASE_APK_PATH):
        return None
    clean = rel_asset_path.lstrip("/")
    if not clean.startswith("assets/"):
        clean = f"assets/android/{clean}"
    with _apk_lock:
        if _apk_zip is None:
            _apk_zip = zipfile.ZipFile(BASE_APK_PATH, "r")
            _apk_entries = set(_apk_zip.namelist())
        if clean not in _apk_entries:
            return None
        return _apk_zip.read(clean)


def _guess_content_type(path: str) -> str:
    low = path.lower()
    if low.endswith(".png"):
        return "image/png"
    if low.endswith(".jpg") or low.endswith(".jpeg"):
        return "image/jpeg"
    if low.endswith(".html") or low.endswith(".htm"):
        return "text/html; charset=utf-8"
    if low.endswith(".js"):
        return "application/javascript; charset=utf-8"
    if low.endswith(".css"):
        return "text/css; charset=utf-8"
    if low.endswith(".svg"):
        return "image/svg+xml"
    if low.endswith(".json"):
        return "application/json; charset=utf-8"
    if low.endswith(".csv"):
        return "text/csv; charset=utf-8"
    if low.endswith("fileinfo") or low.endswith("versioninfo"):
        return "text/plain; charset=utf-8"
    return "application/octet-stream"


def _send_bytes_with_range(handler, data: bytes, content_type: str):
    """Serve bytes honoring HTTP Range requests (206 Partial Content)."""
    total = len(data)
    range_hdr = handler.headers.get("Range") if getattr(handler, "headers", None) else None
    if range_hdr:
        m = re.match(r"bytes=(\d*)-(\d*)", range_hdr.strip())
        if m:
            start_s, end_s = m.groups()
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else total - 1
            if total == 0 or start >= total or end < start:
                handler.send_response(416)
                handler.send_header("Content-Range", f"bytes */{total}")
                handler.send_headers_common(0, content_type)
                return
            end = min(end, total - 1)
            chunk = data[start : end + 1]
            handler.send_response(206)
            handler.send_header("Accept-Ranges", "bytes")
            handler.send_header("Content-Range", f"bytes {start}-{end}/{total}")
            handler.send_headers_common(len(chunk), content_type)
            try:
                handler.wfile.write(chunk)
                handler.wfile.flush()
            except Exception:
                pass
            return

    handler.send_response(200)
    handler.send_header("Accept-Ranges", "bytes")
    handler.send_headers_common(total, content_type)
    try:
        handler.wfile.write(data)
        handler.wfile.flush()
    except Exception:
        pass


def _strip_cdn_prefixes(path: str) -> list[str]:
    """Generate candidate relative paths inside static/ or APK assets/android/."""
    raw = path.lstrip("/")
    candidates = [raw]
    for prefix in ("live/", "sbt/ABHotUpdates/", "static/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            candidates.append(raw)
    # Strip android/<ver>/ or android/optional/<subver>/
    m = re.match(r"^(?:android|ios|win)/(?:optional/[^/]+|[^/]+)/(.+)$", raw)
    if m:
        candidates.append(m.group(1))
    return list(dict.fromkeys(candidates))


def handle_static_get(handler, path, client_ip):
    host_header = handler.headers.get("Host", "127.0.0.1:8080")
    scheme = "https" if (handler.headers.get("X-Forwarded-Proto") == "https" or "onrender.com" in host_header) else "http"
    
    if "ver.php" in path:
        ver_info = {
            "code": 0,
            "is_server_open": True,
            "is_firewall_open": False,
            "need_track_hotupdate": False,
            "min_hint_size": 0.0,
            "cdn_msg": "",
            "billboard_msg": "",
            "remote_version": VERSION,
            "remote_option_version": SUB_VERSION,
            "cdn_url": f"{scheme}://{host_header}/live/",
            "server_url": f"{scheme}://{host_header}/",
            "is_review_server": False,
            "appstore_url": "",
            "force_to_restart_app": False,
            "country_code": "US",
            "gdpr_version": 0,
            "client_ip": client_ip,
            "maintenance_announcement": "",
            "maintenance_region": "",
            "need_check_ip_list": [],
            "network_log_server": "",
            "login_failed_count": 0
        }
        handler.send_json(ver_info)
        return True

    if path.endswith("versioninfo"):
        handler.send_text(f"{VERSION}\n{SUB_VERSION}\n")
        return True

    if path.endswith("fileinfo"):
        f_path = os.path.join(STATIC_DIR, "fileinfo")
        if os.path.exists(f_path):
            handler.send_file(f_path, "text/plain")
        else:
            handler.send_text("", 200)
        return True

    if path.endswith("serverList.json"):
        handler.send_json({
            "serverList": [{
                "serverName": "India V1 Localhost",
                "serverUrl": host_header,
                "garenaOverride": False,
                "garenaSandbox": False,
                "skipVersionCheck": True
            }]
        })
        return True

    if path.endswith("localConfig.json"):
        handler.send_json({})
        return True

    if path.endswith("Announcement.csv"):
        handler.send_text("id,title,content\n1,Welcome,India V1 1.39 Local Server\n", 200, "text/csv")
        return True

    if "app/info/get" in path or "app/feedback" in path:
        handler.send_json({"status": 0, "message": "success", "data": {}})
        return True

    ctype = _guess_content_type(path)
    for rel_path in _strip_cdn_prefixes(path):
        candidate = os.path.join(STATIC_DIR, rel_path)
        if os.path.isfile(candidate):
            with open(candidate, "rb") as f:
                _send_bytes_with_range(handler, f.read(), ctype)
            return True

        apk_bytes = _get_apk_asset(rel_path)
        if apk_bytes is not None:
            _send_bytes_with_range(handler, apk_bytes, ctype)
            return True

    # Do not fall through to 200 OK empty body on missing CDN/AssetBundle URLs
    if path.startswith("/live/") or path.startswith("/sbt/ABHotUpdates/") or "gameassetbundles/" in path:
        handler.send_text("Not Found", 404)
        return True

    return False
