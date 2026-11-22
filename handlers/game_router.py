"""
Master HTTP game request router for Free Fire 1.39 emulation server.

Routes auth/core endpoints first, dispatches across all modular feature
handlers (already landed + optional in-flight handlers loaded safely via
_load_optional_handlers), preserves legacy auth_models fallbacks for modules
still under construction, and handles telemetry + safe empty fallbacks.
"""

from __future__ import annotations

import importlib
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from core.player import Player, player_manager
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
from proto.decoder import decode_proto, get_string, get_varint

HandlerFunc = Callable[..., bool]

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


def _resolve_request_account(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    is_login_endpoint: bool = False,
) -> Tuple[Player, bool]:
    """
    Extract account identity from query string, headers, protobuf body, or IP session,
    and authenticate against PlayerManager.
    Returns: (player: Player, is_new: bool)
    """
    parsed_aid: int = 0
    token: str = ""
    open_id: str = ""
    device_id: str = ""
    region: str = ""
    nickname: str = ""

    # 1. Parse URL query string
    try:
        raw_url = getattr(handler, "path", path)
        query_str = urlparse(raw_url).query
        if query_str:
            params = parse_qs(query_str)
            for k in ("account_id", "aid", "uid", "player_id", "id"):
                if k in params and params[k]:
                    val = params[k][0].strip()
                    if val.isdigit() and int(val) > 0:
                        parsed_aid = int(val)
                        break
            for k in ("token", "session_token", "login_token"):
                if k in params and params[k]:
                    token = params[k][0].strip()
                    break
            for k in ("open_id", "openid"):
                if k in params and params[k]:
                    open_id = params[k][0].strip()
                    break
            for k in ("device_id", "did"):
                if k in params and params[k]:
                    device_id = params[k][0].strip()
                    break
            if "region" in params and params["region"]:
                region = params["region"][0].strip().upper()
            if "nickname" in params and params["nickname"]:
                nickname = params["nickname"][0].strip()
    except Exception:
        pass

    # 2. Parse HTTP headers
    try:
        headers = getattr(handler, "headers", {})
        if not parsed_aid:
            for hk in ("X-Account-Id", "account_id", "aid"):
                val = headers.get(hk)
                if val and str(val).strip().isdigit():
                    parsed_aid = int(str(val).strip())
                    break
        if not token:
            auth_val = headers.get("Authorization", "") or headers.get("token", "") or headers.get("X-Session-Token", "")
            if auth_val:
                clean_auth = str(auth_val).replace("Bearer ", "").strip()
                if clean_auth:
                    token = clean_auth
        if not open_id:
            open_id = headers.get("X-Open-Id", "") or headers.get("open_id", "") or headers.get("X-GARENA-OPENID", "")
        if not device_id:
            device_id = headers.get("X-Device-Id", "") or headers.get("device_id", "")
    except Exception:
        pass

    # 3. Parse protobuf body if present
    if raw_body and len(raw_body) > 1:
        try:
            f = decode_proto(raw_body)
            if not parsed_aid and 1 in f:
                val1 = f[1][0]
                if isinstance(val1, int) and val1 >= 10000:
                    parsed_aid = int(val1)
            if not token:
                token = get_string(f, 29, "") or get_string(f, 8, "") or get_string(f, 2, "")
            if not open_id:
                open_id = get_string(f, 22, "")
            if not device_id:
                device_id = get_string(f, 19, "")
                if not device_id and 1 in f and isinstance(f[1][0], (bytes, bytearray, str)):
                    device_id = get_string(f, 1, "")
            if not region:
                region = get_string(f, 26, "") or get_string(f, 3, "")
            if not nickname:
                nickname = get_string(f, 34, "") or get_string(f, 2, "")
        except Exception:
            pass

    # 4. If we have credentials or it's a login endpoint, authenticate
    if parsed_aid > 0 or token or open_id or device_id:
        player, is_new = player_manager.authenticate(
            account_id=parsed_aid,
            open_id=open_id,
            device_id=device_id,
            token=token,
            client_ip=client_ip,
            nickname=nickname,
            region=region or "DEFAULT",
        )
        return player, is_new

    # 5. Check client_ip session
    if client_ip:
        sess_aid = player_manager.get_session_account_id(client_ip)
        if sess_aid:
            player = player_manager.get_player(sess_aid)
            if player:
                return player, False

    # 6. If it's a login/register endpoint without explicit credentials,
    # provision a new player if not localhost, or return default player
    if is_login_endpoint:
        player, is_new = player_manager.authenticate(
            open_id=open_id or (f"guest_{client_ip.replace('.', '_')}" if client_ip not in ("127.0.0.1", "::1") else ""),
            device_id=device_id,
            client_ip=client_ip,
            region=region or "DEFAULT",
        )
        return player, is_new

    # 7. Fallback to default player
    default_p = player_manager.get_or_create(DEFAULT_ACCOUNT_ID)
    return default_p, False


def _dispatch_feature_handlers(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
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

        try:
            if fn(handler, path, client_ip, raw_body, account_id=account_id):
                return True
        except TypeError:
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

    is_login = endpoint in ("MajorLogin", "MajorRegister", "Login", "GetLoginData", "ChooseRegion", "CreateRole", "FirstLogin")
    player, is_new = _resolve_request_account(handler, path, client_ip, raw_body, is_login_endpoint=is_login)
    account_id = player.account_id

    # 1. Exact Auth / Session endpoints
    if endpoint == "MajorLogin":
        player_manager.bind_session(client_ip, player.account_id, player.token)
        handler.send_proto(
            "MajorLoginRes",
            encode_major_login_res(
                account_id=player.account_id,
                region=player.region,
                token=player.token,
                ttl=86400,
                server_url=base_url,
            ),
        )
        return True

    if endpoint == "ChooseRegion":
        f = decode_proto(raw_body)
        chosen_reg = get_string(f, 1, "")
        if not chosen_reg:
            query_str = urlparse(getattr(handler, "path", path)).query
            if query_str:
                p_dict = parse_qs(query_str)
                if "region" in p_dict and p_dict["region"]:
                    chosen_reg = p_dict["region"][0]
        if chosen_reg:
            player_manager.change_region(player.account_id, chosen_reg)
        player_manager.bind_session(client_ip, player.account_id, player.token)
        handler.send_proto(
            "ChooseRegionRes",
            encode_major_login_res(
                account_id=player.account_id,
                region=player.region,
                token=player.token,
                ttl=86400,
                server_url=base_url,
            ),
        )
        return True

    if endpoint in ("MajorRegister", "CreateRole", "FirstLogin"):
        f = decode_proto(raw_body)
        new_nick = get_string(f, 1, "")
        if not new_nick or (2 in f and isinstance(f[2][0], (bytes, bytearray, str))):
            alt = get_string(f, 2, "")
            if alt and not isinstance(f[2][0], int):
                new_nick = alt
        reg = get_string(f, 3, "")
        if reg:
            player_manager.change_region(player.account_id, reg)
        if new_nick:
            player_manager.change_nickname(player.account_id, new_nick)
        player_manager.bind_session(client_ip, player.account_id, player.token)
        handler.send_proto(
            "LoginRes (Register)",
            encode_login_res(
                account_id=player.account_id,
                nickname=player.nickname,
                region=player.region,
                host=host_header,
                tcp_addr=tcp_addr,
                chat_server=1,
            ),
        )
        return True

    if endpoint in ("GetLoginData", "Login"):
        player_manager.bind_session(client_ip, player.account_id, player.token)
        handler.send_proto(
            f"LoginRes ({endpoint})",
            encode_login_res(
                account_id=player.account_id,
                nickname=player.nickname,
                region=player.region,
                host=host_header,
                tcp_addr=tcp_addr,
                chat_server=1,
            ),
        )
        return True

    if endpoint == "GetPlatformProfile":
        handler.send_proto(
            "PlatformProfileRes",
            encode_platform_profile_res(
                external_id=str(player.account_id),
                external_name=player.nickname,
                external_type=1,
            ),
        )
        return True

    if endpoint == "GetWallet":
        wallet = state.get_wallet(player.account_id)
        handler.send_proto(
            "CSGetWalletRes",
            encode_wallet_res(account_id=player.account_id, coins=wallet["coins"], gems=wallet["gems"]),
        )
        return True

    # 2. Modular feature handlers (Mail, Social, Team, Clan, Leaderboard,
    #    Elite Pass, Profile, Pet, Activity, Store + optional Character,
    #    Inventory, Gacha, Room, Misc as they land).
    if _dispatch_feature_handlers(handler, path, client_ip, raw_body, account_id=player.account_id):
        return True

    # 3. Temporary auth_models / stub fallbacks for in-flight modules
    if endpoint == "LoginGetProfile":
        handler.send_proto(
            "LoginProfileRes",
            encode_login_profile_res(account_id=player.account_id, avatar_id=player.avatar_id),
        )
        return True

    if endpoint == "GetProfiles":
        handler.send_proto("CSGetProfileListRes", encode_profile_list_res(avatar_id=player.avatar_id))
        return True

    if endpoint == "GetSkills":
        handler.send_proto("CSGetSkillListRes", encode_skill_list_res(account_id=player.account_id))
        return True

    if endpoint == "GetBackpack":
        from handlers.inventory_handler import inventory_service
        handler.send_proto(
            "CSGetBackpackRes",
            inventory_service.get_backpack(account_id=player.account_id),
        )
        return True

    if endpoint in ("HideAvatar", "GetHideAvatar"):
        handler.send_proto("CSGetHideAvatarRes", b"\x0a\x00")
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
