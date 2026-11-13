"""
Master HTTP game request router for Free Fire 1.39 emulation server.

Routes auth/core endpoints first, dispatches across all modular feature
handlers (already landed + optional in-flight handlers loaded safely via
_load_optional_handlers), preserves legacy auth_models fallbacks for modules
still under construction, and handles telemetry + safe empty fallbacks.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, List, Tuple

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.auth_models import (
    encode_backpack_res,
    encode_login_profile_res,
    encode_login_res,
    encode_major_login_res,
    encode_platform_profile_res,
    encode_profile_list_res,
    encode_skill_list_res,
    encode_wallet_res,
)

HandlerFunc = Callable[[Any, str, str, bytes], bool]

# Ordered handler modules: completed handlers first, optional in-flight modules guarded.
# Specific endpoint matching inside each module prevents substring collisions
# (e.g. /GetFriendRequestList vs /GetFriend, /MajorModifyNickname vs /MajorLogin).
_HANDLER_SPECS: Tuple[Tuple[str, str, bool], ...] = (
    ("handlers.mail_handler", "handle_mail_request", True),
    ("handlers.social_handler", "handle_social_request", True),
    ("handlers.team_handler", "handle_team_request", True),
    ("handlers.clan_handler", "handle_clan_request", True),
    ("handlers.leaderboard_handler", "handle_leaderboard_request", True),
    ("handlers.elitepass_handler", "handle_elitepass_request", True),
    ("handlers.profile_handler", "handle_profile_request", True),
    ("handlers.pet_handler", "handle_pet_request", True),
    ("handlers.activity_handler", "handle_activity_request", True),
    ("handlers.store_handler", "handle_store_request", True),
    ("handlers.character_handler", "handle_character_request", False),
    ("handlers.inventory_handler", "handle_inventory_request", False),
    ("handlers.gacha_handler", "handle_gacha_request", False),
    ("handlers.room_handler", "handle_room_request", False),
    ("handlers.misc_handler", "handle_misc_request", False),
)


_LOADED_CACHE: dict[str, HandlerFunc] = {}


def _load_required_handlers() -> None:
    """Validate and cache all required handler modules at import time."""
    for mod_name, fn_name, required in _HANDLER_SPECS:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name)
            _LOADED_CACHE[mod_name] = fn
        except ImportError:
            if required:
                raise


def _extract_endpoint(path: str) -> str:
    """Return final clean path segment without query string or trailing slash."""
    clean = path.split("?", 1)[0].rstrip("/")
    return clean.rsplit("/", 1)[-1] if "/" in clean else clean


def _dispatch_feature_handlers(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
) -> bool:
    """Try modular handlers, picking up newly landed optional modules automatically."""
    for mod_name, fn_name, required in _HANDLER_SPECS:
        fn = _LOADED_CACHE.get(mod_name)
        if fn is None:
            try:
                mod = importlib.import_module(mod_name)
                fn = getattr(mod, fn_name, None)
                if fn is None:
                    continue
                _LOADED_CACHE[mod_name] = fn
            except ImportError:
                if required:
                    raise
                continue

        if fn(handler, path, client_ip, raw_body):
            return True
    return False


# Eagerly validate required modules at import time
_load_required_handlers()


def handle_game_post(handler: Any, path: str, client_ip: str, raw_body: bytes) -> bool:
    """Route incoming Free Fire HTTP/POST & fallback-GET game requests."""
    host_header = handler.headers.get("Host", "127.0.0.1:8080")
    scheme = "https" if (handler.headers.get("X-Forwarded-Proto") == "https" or "onrender.com" in host_header) else "http"
    base_url = f"{scheme}://{host_header.rstrip('/')}"

    tcp_override = os.environ.get("TCP_PUBLIC_ADDR")
    if tcp_override:
        tcp_addr = tcp_override
    elif "onrender.com" in host_header:
        # Render free tier does not route raw TCP port 8081. Default to local gateway
        tcp_addr = "10.0.2.2:8081"
    else:
        tcp_host = host_header.split(":", 1)[0].strip() or "10.0.2.2"
        tcp_addr = f"{tcp_host}:8081"

    endpoint = _extract_endpoint(path)
    clean_path = path.split("?", 1)[0]

    # 1. Exact Auth / Session endpoints
    if endpoint == "MajorLogin":
        handler.send_proto(
            "MajorLoginRes",
            encode_major_login_res(
                account_id=DEFAULT_ACCOUNT_ID,
                region="DEFAULT",
                token="barbosa_session_token_12345",
                ttl=86400,
                server_url=base_url,
            ),
        )
        return True

    if endpoint == "MajorRegister":
        prof = state.get_profile(DEFAULT_ACCOUNT_ID)
        handler.send_proto(
            "LoginRes (Register)",
            encode_login_res(
                account_id=DEFAULT_ACCOUNT_ID,
                nickname=str(prof.get("nickname", "Clack")),
                region="DEFAULT",
                host=host_header,
                tcp_addr=tcp_addr,
                chat_server=1,
            ),
        )
        return True

    if endpoint == "GetLoginData":
        prof = state.get_profile(DEFAULT_ACCOUNT_ID)
        handler.send_proto(
            "LoginRes (GetLoginData)",
            encode_login_res(
                account_id=DEFAULT_ACCOUNT_ID,
                nickname=str(prof.get("nickname", "Clack")),
                region="DEFAULT",
                host=host_header,
                tcp_addr=tcp_addr,
                chat_server=1,
            ),
        )
        return True

    if endpoint == "ChooseRegion":
        handler.send_proto(
            "ChooseRegionRes",
            encode_major_login_res(
                account_id=DEFAULT_ACCOUNT_ID,
                region="DEFAULT",
                token="barbosa_session_token_12345",
                ttl=86400,
                server_url=base_url,
            ),
        )
        return True

    if endpoint == "Login":
        prof = state.get_profile(DEFAULT_ACCOUNT_ID)
        handler.send_proto(
            "LoginRes",
            encode_login_res(
                account_id=DEFAULT_ACCOUNT_ID,
                nickname=str(prof.get("nickname", "Clack")),
                region="DEFAULT",
                host=host_header,
                tcp_addr=tcp_addr,
                chat_server=1,
            ),
        )
        return True

    if endpoint == "GetPlatformProfile":
        handler.send_proto("PlatformProfileRes", encode_platform_profile_res())
        return True

    if endpoint == "GetWallet":
        wallet = state.get_wallet(DEFAULT_ACCOUNT_ID)
        handler.send_proto(
            "CSGetWalletRes",
            encode_wallet_res(coins=wallet["coins"], gems=wallet["gems"]),
        )
        return True

    # 2. Modular feature handlers (Mail, Social, Team, Clan, Leaderboard,
    #    Elite Pass, Profile, Pet, Activity, Store + optional Character,
    #    Inventory, Gacha, Room, Misc as they land).
    if _dispatch_feature_handlers(handler, path, client_ip, raw_body):
        return True

    # 3. Temporary auth_models / stub fallbacks for in-flight modules
    if endpoint == "LoginGetProfile":
        handler.send_proto(
            "LoginProfileRes",
            encode_login_profile_res(account_id=DEFAULT_ACCOUNT_ID, avatar_id=1),
        )
        return True

    if endpoint == "GetProfiles":
        handler.send_proto("CSGetProfileListRes", encode_profile_list_res(avatar_id=1))
        return True

    if endpoint == "GetSkills":
        handler.send_proto("CSGetSkillListRes", encode_skill_list_res(account_id=DEFAULT_ACCOUNT_ID))
        return True

    if endpoint == "GetBackpack":
        wallet = state.get_wallet(DEFAULT_ACCOUNT_ID)
        handler.send_proto(
            "CSGetBackpackRes",
            encode_backpack_res(coins=wallet["coins"], gems=wallet["gems"]),
        )
        return True

    if endpoint in ("HideAvatar", "GetHideAvatar"):
        handler.send_proto("CSGetHideAvatarRes", b"\x0a\x00")
        return True

    if endpoint == "GetGachaInfo":
        handler.send_proto("CSGetGachaInfoRes", b"")
        return True

    if endpoint in ("GetGachaDesc", "GetGachaSpecialExchangeDesc"):
        handler.send_proto("GachaDescRes", b"")
        return True

    if endpoint in ("GetGameOpeningInfo", "GetMapOpeningInfo", "GetOpeningInfo"):
        from tcp_server import encode_game_opening_info_res
        handler.send_proto("GameOpeningInfoRes", encode_game_opening_info_res())
        return True

    # 4. Telemetry / Logging (/eventLogEvent, /logNetworkLogEvent)
    lower_path = clean_path.lower()
    if endpoint in ("eventLogEvent", "logNetworkLogEvent") or any(
        k in lower_path for k in ("event", "telemetry", "report")
    ) or lower_path.startswith("/log"):
        handler.send_bytes(b"", status=200)
        return True

    # 5. Safe empty 200 fallback for unmapped endpoints (prevents connection drop)
    print(f"  [?] Default POST handler for unmapped endpoint: {path}", flush=True)
    handler.send_bytes(b"", status=200)
    return True
