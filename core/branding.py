"""
Barbosa Project 1.39 Branding & Visuals CMS Engine.
Enables real-time management of boot splash, launcher background,
login wallpaper, title logos, and lobby banners through the Admin Dashboard.
"""

from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import threading
from typing import Any, Dict, List, Optional
from PIL import Image

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_ROOT = os.path.dirname(SERVER_DIR)
STATIC_DIR = os.path.join(SERVER_DIR, "static")
BANNERS_DIR = os.path.join(STATIC_DIR, "banners")
CMS_JSON_PATH = os.path.join(SERVER_DIR, "data", "lobby_cms.json")
BASE_APK_PATH = os.path.join(LEGACY_ROOT, "apk", "Barbosa_1.39_LocalHost.apk")

ADB_PATH = r"C:\Program Files\BlueStacks_msi5\HD-Adb.exe"
DEVICE_SERIAL = "emulator-5554"

os.makedirs(BANNERS_DIR, exist_ok=True)

BRANDING_SLOTS: Dict[str, Dict[str, Any]] = {
    "splash_logo": {
        "name": "Startup Splash Logo",
        "category": "boot",
        "desc": "Unity engine startup splash logo (4.0s boot screen)",
        "size": (512, 512),
        "apk_path": "assets/bin/Data/globalgamemanagers.assets",
        "path_id": 3,
        "format": "PNG",
        "default_url": "/banners/custom_splash.png",
    },
    "launcher_bg": {
        "name": "Launcher / Loading Screen Background",
        "category": "boot",
        "desc": "Hotupdate and version checking screen wallpaper (FF_fakeloading_img)",
        "size": (1024, 512),
        "apk_path": "assets/bin/Data/a5d7b6bb7a57deb41a74f2a8197d39ea",
        "path_id": 1,
        "format": "PNG",
        "default_url": "/banners/custom_launcher.png",
    },
    "login_bg": {
        "name": "OB17 Login Screen Background",
        "category": "login",
        "desc": "Main title and login screen background (dts_loading_img_0B17_BG)",
        "size": (1024, 512),
        "apk_path": "assets/bin/Data/fbdb872a41bc0924abc8c5c0910f5e0e",
        "path_id": 1,
        "format": "PNG",
        "default_url": "/banners/custom_login.png",
    },
    "login_bg_pve": {
        "name": "PVE Login / Loading Screen Background",
        "category": "login",
        "desc": "Secondary PVE login & loading screen (dts_loading_img_PVE_BG)",
        "size": (1024, 512),
        "apk_path": "assets/bin/Data/71489e73ded47d64eb761135ba1b72c7",
        "path_id": 1,
        "format": "PNG",
        "default_url": "/banners/custom_login.png",
    },
    "game_logo": {
        "name": "Title Screen Logo",
        "category": "boot",
        "desc": "Free Fire Header Logo on login screen (FF_UI_Logo)",
        "size": (512, 128),
        "apk_path": "assets/bin/Data/8e570f01ef9b5414f80a8c1472f9274e",
        "path_id": 1,
        "format": "PNG",
        "default_url": "/banners/FF_UI_Logo.png",
    },
    "dts_logo": {
        "name": "DTS Brand Logo",
        "category": "boot",
        "desc": "DTS Studio RGB logo (DTS_UI_LOGO_rgb)",
        "size": (512, 256),
        "apk_path": "assets/bin/Data/e0380ceb8e6f8d1489ae0826d63c1090",
        "path_id": 1,
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
            
            preview_url = f"/banners/{filename}" if has_custom else slot["default_url"]
            results.append({
                "key": slot_key,
                "name": slot["name"],
                "category": slot["category"],
                "desc": slot["desc"],
                "width": slot["size"][0],
                "height": slot["size"][1],
                "preview_url": preview_url,
                "is_custom": has_custom,
                "last_modified": int(os.path.getmtime(filepath)) if has_custom else 0,
            })
        return results


def update_branding_slot(slot_key: str, image_raw_or_b64: str | bytes, push_to_emulator: bool = True) -> Dict[str, Any]:
    """
    Save an uploaded or selected image to the slot, update lobby CMS if applicable,
    and optionally hot-swap into the emulator without repacking.
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

    # If this is a lobby CMS item, update lobby_cms.json immediately
    if slot.get("cms_type") == "splash":
        _update_lobby_cms_splash(slot["cms_id"], f"/banners/{out_filename}")
    elif slot.get("cms_type") == "advert":
        _update_lobby_cms_advert(slot["cms_id"], f"/banners/{out_filename}")

    # If this is a boot/client asset, apply hot-swap or update APK
    hot_swap_result = None
    if slot.get("category") in ("boot", "login") and push_to_emulator:
        hot_swap_result = _apply_asset_to_emulator(slot_key, out_path)

    return {
        "ok": True,
        "slot": slot_key,
        "name": slot["name"],
        "preview_url": f"/banners/{out_filename}?t={int(os.path.getmtime(out_path))}",
        "hot_swap": hot_swap_result,
    }


def _update_lobby_cms_splash(splash_id: int, image_url: str) -> None:
    if not os.path.exists(CMS_JSON_PATH):
        return
    try:
        with open(CMS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s in data.get("splashes", []):
            if s.get("id") == splash_id:
                s["image_url"] = image_url
                s["bg_img_url"] = image_url
        with open(CMS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _update_lobby_cms_advert(advert_id: int, image_url: str) -> None:
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


def _apply_asset_to_emulator(slot_key: str, new_png_path: str) -> Dict[str, Any]:
    """Push the modified asset to emulator game storage via ADB without repacking."""
    if not os.path.exists(ADB_PATH):
        return {"pushed": False, "reason": "adb_not_found"}

    slot = BRANDING_SLOTS[slot_key]
    apk_rel_path = slot.get("apk_path")
    if not apk_rel_path:
        return {"pushed": False, "reason": "no_apk_path"}

    # Target path on Android device persistent data
    # /sdcard/Android/data/com.dts.freefireth/files/
    target_remote = f"/sdcard/Android/data/com.dts.freefireth/files/{apk_rel_path}"
    target_remote_dir = target_remote.rsplit("/", 1)[0]

    try:
        # Ensure remote directory exists
        cmd_mkdir = [ADB_PATH, "-s", DEVICE_SERIAL, "shell", "su", "-c", f"mkdir -p '{target_remote_dir}'"]
        subprocess.run(cmd_mkdir, capture_output=True, timeout=5)

        # Inject texture into the raw serialized Unity asset file locally
        import UnityPy
        import zipfile
        
        with zipfile.ZipFile(BASE_APK_PATH, "r") as z:
            raw_asset_bytes = z.read(apk_rel_path)

        env = UnityPy.load(raw_asset_bytes)
        img = Image.open(new_png_path).convert("RGBA")
        target_path_id = slot["path_id"]
        for obj in env.objects:
            if obj.path_id == target_path_id and obj.type.name == "Texture2D":
                d = obj.read()
                d.image = img
                d.save()
                break
        patched_bytes = env.file.save()

        # Write to temporary local file and push via ADB
        temp_local = os.path.join(LEGACY_ROOT, "dump", f"patched_{os.path.basename(apk_rel_path)}")
        with open(temp_local, "wb") as f:
            f.write(patched_bytes)

        cmd_push = [ADB_PATH, "-s", DEVICE_SERIAL, "push", temp_local, target_remote]
        res = subprocess.run(cmd_push, capture_output=True, text=True, timeout=10)
        
        # Also copy to root data directory if present
        subprocess.run(
            [ADB_PATH, "-s", DEVICE_SERIAL, "shell", "su", "-c", f"chmod 666 '{target_remote}'"],
            capture_output=True, timeout=5
        )

        return {"pushed": True, "remote_path": target_remote, "output": res.stdout.strip()}
    except Exception as ex:
        return {"pushed": False, "error": str(ex)}
