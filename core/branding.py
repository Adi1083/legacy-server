    """
Barbosa Project 1.39 Branding & Visuals CMS Engine.
Enables 100% dynamic HTTP management of boot splash, launcher background,
login wallpaper, title logos, and lobby banners through the Admin Dashboard.
Zero APK repacking, zero ADB or emulator dependencies.
"""

from __future__ import annotations

import base64
import io
import json
import os
import threading
from typing import Any, Dict, List, Optional
from PIL import Image

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(SERVER_DIR, "static")
BANNERS_DIR = os.path.join(STATIC_DIR, "banners")
CMS_JSON_PATH = os.path.join(SERVER_DIR, "data", "lobby_cms.json")

os.makedirs(BANNERS_DIR, exist_ok=True)

BRANDING_SLOTS: Dict[str, Dict[str, Any]] = {
    "splash_logo": {
        "name": "Startup Splash Logo",
        "category": "boot",
        "desc": "Unity engine startup splash logo (4.0s boot screen)",
        "size": (512, 512),
        "format": "PNG",
        "default_url": "/banners/custom_splash.png",
    },
    "launcher_bg": {
        "name": "Launcher / Loading Screen Background",
        "category": "boot",
        "desc": "Hotupdate and version checking screen wallpaper (FF_fakeloading_img)",
        "size": (1024, 512),
        "format": "PNG",
        "default_url": "/banners/custom_launcher.png",
    },
    "login_bg": {
        "name": "OB17 Login Screen Background",
        "category": "login",
        "desc": "Main title and login screen background (dts_loading_img_0B17_BG)",
        "size": (1024, 512),
        "format": "PNG",
        "default_url": "/banners/custom_login.png",
    },
    "login_bg_pve": {
        "name": "PVE Login / Loading Screen Background",
        "category": "login",
        "desc": "Secondary PVE login & loading screen (dts_loading_img_PVE_BG)",
        "size": (1024, 512),
        "format": "PNG",
        "default_url": "/banners/custom_login.png",
    },
    "game_logo": {
        "name": "Title Screen Logo",
        "category": "boot",
        "desc": "Free Fire Header Logo on login screen (FF_UI_Logo)",
        "size": (512, 128),
        "format": "PNG",
        "default_url": "/banners/FF_UI_Logo.png",
    },
    "dts_logo": {
        "name": "DTS Brand Logo",
        "category": "boot",
        "desc": "DTS Studio RGB logo (DTS_UI_LOGO_rgb)",
        "size": (512, 256),
        "format": "PNG",
        "default_url": "/banners/DTS_UI_LOGO_rgb.png",
    },
    "lobby_banner_1": {
        "name": "Lobby Event Banner (Season 1)",
        "category": "lobby",
        "desc": "Primary lobby billboard banner on the left side",
        "size": (720, 360),
        "format": "PNG",
        "default_url": "/banners/splash_welcome.png",
        "cms_type": "splash",
        "cms_id": 1,
    },
    "lobby_banner_2": {
        "name": "Lobby Fire Pass Banner",
        "category": "lobby",
        "desc": "Secondary lobby event banner (Apocalyptic Order / Fire Pass)",
        "size": (720, 360),
        "format": "PNG",
        "default_url": "/banners/splash_elite.png",
        "cms_type": "splash",
        "cms_id": 2,
    },
    "lobby_ad_1": {
        "name": "Lobby News & Ad Card",
        "category": "lobby",
        "desc": "Small announcement card displayed in lobby carousel",
        "size": (360, 180),
        "format": "PNG",
        "default_url": "/banners/lobby_ad_1.png",
        "cms_type": "advert",
        "cms_id": 1,
    },
}

_LOCK = threading.RLock()


def get_all_slots() -> List[Dict[str, Any]]:
    """Return all configurable branding slots with current file status and preview URLs."""
    with _LOCK:
        results = []
        for slot_key, slot in BRANDING_SLOTS.items():
            filename = f"{slot_key}.png"
            filepath = os.path.join(BANNERS_DIR, filename)
            has_custom = os.path.isfile(filepath)
            
            mtime = int(os.path.getmtime(filepath)) if has_custom else 0
            preview_url = f"/banners/{filename}?t={mtime}" if has_custom else slot["default_url"]
            results.append({
                "key": slot_key,
                "name": slot["name"],
                "category": slot["category"],
                "desc": slot["desc"],
                "width": slot["size"][0],
                "height": slot["size"][1],
                "preview_url": preview_url,
                "is_custom": has_custom,
                "last_modified": mtime,
            })
        return results


def update_branding_slot(slot_key: str, image_raw_or_b64: str | bytes, push_to_emulator: bool = False) -> Dict[str, Any]:
    """
    Save an uploaded or selected image directly to static/banners/ and sync with Lobby CMS.
    Completely eliminates APK repacking and ADB dependencies.
    """
    if slot_key not in BRANDING_SLOTS:
        return {"ok": False, "error": f"Unknown branding slot: {slot_key}"}

    slot = BRANDING_SLOTS[slot_key]
    target_size = slot["size"]

    # Decode bytes
    if isinstance(image_raw_or_b64, str):
        if "," in image_raw_or_b64:
            image_raw_or_b64 = image_raw_or_b64.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(image_raw_or_b64)
        except Exception as ex:
            return {"ok": False, "error": f"Base64 decode failed: {ex}"}
    else:
        raw_bytes = image_raw_or_b64

    # Process and resize image with PIL
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
    except Exception as ex:
        return {"ok": False, "error": f"Invalid image format: {ex}"}

    out_filename = f"{slot_key}.png"
    out_path = os.path.join(BANNERS_DIR, out_filename)
    
    with _LOCK:
        img.save(out_path, format="PNG")

    mtime = int(os.path.getmtime(out_path))
    banner_url = f"/banners/{out_filename}"

    # If this is a lobby CMS item, update state and lobby_cms.json immediately
    if slot.get("cms_type") == "splash":
        _update_lobby_cms_splash(slot["cms_id"], banner_url)
    elif slot.get("cms_type") == "advert":
        _update_lobby_cms_advert(slot["cms_id"], banner_url)

    return {
        "ok": True,
        "slot": slot_key,
        "name": slot["name"],
        "preview_url": f"{banner_url}?t={mtime}",
        "url": banner_url,
        "version": mtime,
        "hot_swap": {"pushed": False, "note": "Served dynamically over HTTP from static/banners/"},
    }


def _update_lobby_cms_splash(splash_id: int, image_url: str) -> None:
    try:
        from core.state import state
        state.upsert_cms_item("splashes", {"id": splash_id, "image_url": image_url, "bg_img_url": image_url})
        return
    except Exception:
        pass

    if not os.path.exists(CMS_JSON_PATH):
        return
    try:
        with open(CMS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s in data.get("splashes", []):
            if s.get("id") == splash_id:
                s["image_url"] = image_url
                s["bg_img_url"] = image_url
                s["version"] = int(s.get("version", 1)) + 1
        with open(CMS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _update_lobby_cms_advert(advert_id: int, image_url: str) -> None:
    try:
        from core.state import state
        state.upsert_cms_item("adverts", {"id": advert_id, "advertisment_url": image_url})
        return
    except Exception:
        pass

    if not os.path.exists(CMS_JSON_PATH):
        return
    try:
        with open(CMS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for a in data.get("adverts", []):
            if a.get("id") == advert_id:
                a["advertisment_url"] = image_url
        with open(CMS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
