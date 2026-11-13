"""
Web Admin Dashboard & Real-Time Control API for India V1 1.39.
Integrates with core.state.ServerState (Game State + Lobby CMS + Live Tracker)
and core.logger Protobuf inspection.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs

from core.logger import (
    clear_requests,
    decode_protobuf_wire,
    history_lock,
    request_history,
)
from core.state import DEFAULT_ACCOUNT_ID, state

_SERVER_START_TIME = time.time()
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANNERS_DIR = os.path.join(_BASE_DIR, "static", "banners")
_ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg")
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _parse_json_body(raw_body: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not raw_body:
        return {}, None
    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        return None, f"Invalid JSON body: {exc}"
    if not isinstance(data, dict):
        return None, "JSON body must be an object"
    return data, None


def _to_int(val: Any, default: int = 0) -> int:
    if val is None or val == "":
        return default
    return int(val)


def _parse_attachments(raw: Any) -> List[Dict[str, Any]]:
    """Accept list of dicts, list of ints, or comma-separated 'item_id' / 'item_id:count' string."""
    if not raw:
        return []
    result: List[Dict[str, Any]] = []
    if isinstance(raw, str):
        tokens = [t.strip() for t in raw.replace(";", ",").split(",") if t.strip()]
        for tok in tokens:
            if ":" in tok:
                id_part, cnt_part = tok.split(":", 1)
                result.append({
                    "item_id": int(id_part.strip()),
                    "count": max(1, int(cnt_part.strip() or 1)),
                    "type": 1,
                })
            else:
                result.append({"item_id": int(tok), "count": 1, "type": 1})
        return result

    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict) and entry.get("item_id") is not None:
                result.append({
                    "item_id": int(entry["item_id"]),
                    "count": max(1, int(entry.get("count", 1))),
                    "type": int(entry.get("type", 1)),
                })
            elif isinstance(entry, (int, str)) and str(entry).strip():
                result.append({"item_id": int(str(entry).strip()), "count": 1, "type": 1})
    return result


def _parse_item_ids(data: Dict[str, Any]) -> List[int]:
    ids: List[int] = []
    if data.get("item_id") is not None and str(data["item_id"]).strip() != "":
        ids.append(int(data["item_id"]))
    raw_many = data.get("item_ids")
    if isinstance(raw_many, list):
        for x in raw_many:
            if str(x).strip():
                ids.append(int(x))
    elif isinstance(raw_many, str):
        for tok in raw_many.replace(";", ",").split(","):
            tok = tok.strip()
            if tok:
                ids.append(int(tok))
    return ids


def _sanitize_banner_filename(raw_name: str) -> str:
    """Sanitize uploaded banner filename to safe basename with .png/.jpg/.jpeg extension."""
    base = os.path.basename(str(raw_name or "").replace("\\", "/")).strip()
    if not base:
        raise ValueError("Filename is required")
    stem, ext = os.path.splitext(base)
    ext_low = ext.lower()
    if ext_low not in _ALLOWED_IMAGE_EXTS:
        raise ValueError("Only .png, .jpg, and .jpeg files are allowed")
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
    if not safe_stem:
        safe_stem = f"banner_{int(time.time())}"
    return f"{safe_stem}{ext_low}"


def _is_valid_image_bytes(raw: bytes, ext: str) -> bool:
    if len(raw) < 8:
        return False
    if ext == ".png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return raw.startswith(b"\xff\xd8\xff")
    return False


def _list_banners() -> List[Dict[str, Any]]:
    os.makedirs(BANNERS_DIR, exist_ok=True)
    items: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(BANNERS_DIR)):
        if not name.lower().endswith(_ALLOWED_IMAGE_EXTS):
            continue
        full = os.path.join(BANNERS_DIR, name)
        if not os.path.isfile(full):
            continue
        st = os.stat(full)
        items.append({
            "name": name,
            "url": f"/banners/{name}",
            "size": int(st.st_size),
            "modified_at": int(st.st_mtime),
        })
    return items


def _save_banner_file(filename: str, b64_payload: str) -> Dict[str, Any]:
    safe_name = _sanitize_banner_filename(filename)
    _, ext = os.path.splitext(safe_name)
    encoded = str(b64_payload or "").strip()
    if not encoded:
        raise ValueError("Image data_base64 is required")
    if encoded.startswith("data:") and "," in encoded:
        encoded = encoded.split(",", 1)[1]
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception:
        raw = base64.b64decode(encoded)
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise ValueError(f"Image exceeds {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")
    if not _is_valid_image_bytes(raw, ext):
        raise ValueError(f"Invalid {ext} image header bytes")

    os.makedirs(BANNERS_DIR, exist_ok=True)
    dest = os.path.abspath(os.path.join(BANNERS_DIR, safe_name))
    banners_abs = os.path.abspath(BANNERS_DIR)
    if os.path.commonpath([dest, banners_abs]) != banners_abs:
        raise ValueError("Unsafe path")

    tmp = f"{dest}.tmp"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, dest)
    st = os.stat(dest)
    return {
        "name": safe_name,
        "url": f"/banners/{safe_name}",
        "size": int(st.st_size),
        "modified_at": int(st.st_mtime),
    }


def _delete_banner_file(filename: str) -> bool:
    safe_name = _sanitize_banner_filename(filename)
    dest = os.path.abspath(os.path.join(BANNERS_DIR, safe_name))
    banners_abs = os.path.abspath(BANNERS_DIR)
    if os.path.commonpath([dest, banners_abs]) != banners_abs:
        raise ValueError("Unsafe path")
    if not os.path.isfile(dest):
        return False
    os.remove(dest)
    return True


def _try_push_squad_invite_tcp(target_id: int, inviter_id: int, team: Dict[str, Any]) -> int:
    """Best-effort live TCP push of GroupInviteNtf if tcp_server has an active socket."""
    try:
        import tcp_server
        from proto.team_models import EGroupProto, EProtocolProto, encode_group_invite_ntf
    except Exception:
        return 0
    try:
        members = team.get("members") or []
        inviter_member = next((m for m in members if int(m.get("account_id", 0)) == int(inviter_id)), None)
        if not inviter_member:
            inviter_member = {"account_id": int(inviter_id), "role": 1, "ready": False}
        inviter_profile = state.get_player(int(inviter_id)) or state.get_profile(int(inviter_id))
        pet_id = int(inviter_profile.get("selected_pet_id", 0))
        inviter_pet = state.get_pet(pet_id) if pet_id > 0 else None
        eff_group_id = int(team.get("leader_id") or team.get("group_id") or team["team_id"])
        payload = encode_group_invite_ntf(
            group_id=eff_group_id,
            inviter_member=inviter_member,
            inviter_profile=inviter_profile,
            team=team,
            inviter_pet=inviter_pet,
        )
        return int(tcp_server.push_tcp_notify(
            int(target_id),
            EProtocolProto.GROUP,
            EGroupProto.INVITE_NTF,
            content=payload,
        ))
    except Exception:
        return 0


def _build_dashboard_payload(account_id: int = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
    snap = state.get_snapshot(account_id=account_id)
    with history_lock:
        req_count = len(request_history)
    snap["server"] = {
        "uptime_sec": int(time.time() - _SERVER_START_TIME),
        "request_count": req_count,
    }
    snap["all_players"] = state.search_players("", limit=100)
    snap["banners"] = _list_banners()
    return snap


def _query_int(query_params: Dict[str, List[str]], key: str, default: int) -> int:
    vals = query_params.get(key)
    if not vals:
        return default
    try:
        return int(vals[0])
    except ValueError:
        return default


def _query_str(query_params: Dict[str, List[str]], key: str, default: str = "") -> str:
    vals = query_params.get(key)
    return vals[0] if vals else default


def handle_dashboard_get(
    handler: Any,
    path: str,
    query_string: str = "",
    version: str = "1.39",
    sub_version: str = "1.39.4",
    port: int = 8080,
) -> bool:
    """Handle dashboard UI and GET /api/dashboard/* endpoints. Returns True if handled."""
    if path in ("/", "/dashboard"):
        handler.send_text(
            render_dashboard_html(version=version, sub_version=sub_version, port=port),
            status=200,
            content_type="text/html; charset=utf-8",
        )
        return True

    if path == "/api/requests":
        qp = parse_qs(query_string)
        limit = max(1, min(200, _query_int(qp, "limit", 200)))
        q_filter = _query_str(qp, "q").strip().lower()
        method_filter = _query_str(qp, "method").strip().upper()
        with history_lock:
            items = list(request_history)
        if q_filter:
            items = [i for i in items if q_filter in i["path"].lower()]
        if method_filter:
            items = [i for i in items if i["method"].upper() == method_filter]
        handler.send_json(items[:limit])
        return True

    if not path.startswith("/api/dashboard"):
        return False

    qp = parse_qs(query_string)
    account_id = _query_int(qp, "account_id", DEFAULT_ACCOUNT_ID)

    if path == "/api/dashboard/state":
        handler.send_json({"ok": True, **_build_dashboard_payload(account_id)})
        return True

    if path == "/api/dashboard/branding":
        from core.branding import get_all_slots
        handler.send_json({"ok": True, "slots": get_all_slots()})
        return True

    if path == "/api/dashboard/requests":
        limit = max(1, min(200, _query_int(qp, "limit", 100)))
        q_filter = _query_str(qp, "q").strip().lower()
        method_filter = _query_str(qp, "method").strip().upper()
        with history_lock:
            items = list(request_history)
        if q_filter:
            items = [
                i for i in items
                if q_filter in i["path"].lower()
                or q_filter in ((i.get("decoded") or {}).get("summary", "").lower())
            ]
        if method_filter:
            items = [i for i in items if i["method"].upper() == method_filter]
        handler.send_json({"ok": True, "requests": items[:limit], "total": len(items)})
        return True

    if path == "/api/dashboard/mail":
        handler.send_json({
            "ok": True,
            "mails": state.list_mails(account_id),
            "wallet": state.get_wallet(account_id),
        })
        return True

    if path == "/api/dashboard/friends":
        handler.send_json({
            "ok": True,
            "friends": state.list_friends(account_id),
            "friend_requests": state.list_friend_requests(account_id),
            "recommended_friends": state.list_recommended_friends(account_id),
            "all_players": state.search_players("", limit=100),
        })
        return True

    if path == "/api/dashboard/squad":
        handler.send_json({
            "ok": True,
            "team": state.get_team(account_id=account_id),
            "team_invitations": state.list_team_invitations(account_id),
            "invitable_friends": state.list_friends(account_id, online_only=True),
            "rooms": state.list_rooms(),
        })
        return True

    # ------------------------------------------------------------------
    # Lobby CMS & Banner Gallery & Startup Popup Tracker GET Routes
    # ------------------------------------------------------------------
    if path == "/api/dashboard/cms":
        cat = _query_str(qp, "category").strip()
        inc_dis = _query_str(qp, "include_disabled", "1") != "0"
        if cat:
            items = state.list_cms(cat, enabled_only=not inc_dis)
            handler.send_json({"ok": True, "category": cat, "items": items})
        else:
            handler.send_json({
                "ok": True,
                "cms": state.get_cms_snapshot(include_disabled=inc_dis),
                "banners": _list_banners(),
                "feed": state.get_lobby_event_feed(limit=100),
            })
        return True

    if path == "/api/dashboard/cms/banners":
        handler.send_json({"ok": True, "banners": _list_banners()})
        return True

    if path == "/api/dashboard/cms/feed":
        limit = max(1, min(300, _query_int(qp, "limit", 100)))
        cat = _query_str(qp, "category").strip() or None
        handler.send_json({
            "ok": True,
            "feed": state.get_lobby_event_feed(limit=limit, category=cat),
        })
        return True

    handler.send_json({"ok": False, "error": f"Unknown dashboard GET route: {path}"}, status=404)
    return True


def handle_dashboard_post(handler: Any, path: str, raw_body: bytes) -> bool:
    """Handle POST /api/dashboard/* control endpoints. Returns True if handled."""
    if not path.startswith("/api/dashboard"):
        return False

    data, err = _parse_json_body(raw_body)
    if err is not None or data is None:
        handler.send_json({"ok": False, "error": err or "Invalid request"}, status=400)
        return True

    try:
        account_id = _to_int(data.get("account_id"), DEFAULT_ACCOUNT_ID)

        # ------------------------------------------------------------------
        # 1. Mail Controls
        # ------------------------------------------------------------------
        if path == "/api/dashboard/mail/send":
            title = str(data.get("title") or "").strip()
            content = str(data.get("content") if data.get("content") is not None else (data.get("body") or "")).strip()
            if not title:
                handler.send_json({"ok": False, "error": "Mail title is required"}, status=400)
                return True
            coins = max(0, _to_int(data.get("coins") if data.get("coins") is not None else data.get("gold"), 0))
            gems = max(0, _to_int(data.get("gems") if data.get("gems") is not None else data.get("diamonds"), 0))
            attachments = _parse_attachments(data.get("attachments"))
            mail = state.add_mail(
                title=title,
                content=content,
                attachments=attachments,
                coins=coins,
                gems=gems,
                mail_type=_to_int(data.get("mail_type"), 1),
                sender_id=_to_int(data.get("sender_id"), 0),
                sender_nick=str(data.get("sender_nick") or "India V1 Admin"),
                source=_to_int(data.get("source"), 1),
                action_type=_to_int(data.get("action_type"), 0),
                account_id=account_id,
            )
            handler.send_json({
                "ok": True,
                "mail": mail,
                "mails": state.list_mails(account_id),
            })
            return True

        if path == "/api/dashboard/mail/claim":
            raw_mid = data.get("mail_id")
            if str(raw_mid).lower() == "all":
                res = state.claim_all_mails(account_id=account_id)
            else:
                res = state.claim_mail(_to_int(raw_mid), account_id=account_id)
            handler.send_json({
                **res,
                "mails": state.list_mails(account_id),
                "wallet": state.get_wallet(account_id),
            })
            return True

        if path == "/api/dashboard/mail/delete":
            mail_id = _to_int(data.get("mail_id"))
            deleted = state.delete_mail(mail_id, account_id=account_id)
            handler.send_json({
                "ok": deleted,
                "mails": state.list_mails(account_id),
            })
            return True

        # ------------------------------------------------------------------
        # 2. Friends & Friend Request Controls
        # ------------------------------------------------------------------
        if path == "/api/dashboard/friends/request":
            from_id = _to_int(data.get("from_id"))
            to_id = _to_int(data.get("to_id"), account_id)
            if from_id <= 0:
                handler.send_json({"ok": False, "error": "Valid from_id is required"}, status=400)
                return True
            if data.get("nickname") or not state.get_player(from_id):
                state.upsert_player(
                    from_id,
                    nickname=str(data.get("nickname") or f"Player_{from_id}"),
                    is_online=True,
                    online_status=1,
                    can_invite=True,
                )
            res = state.send_friend_request(
                from_id=from_id,
                to_id=to_id,
                message=str(data.get("message") or "Let's squad up!"),
            )
            handler.send_json({
                **res,
                "friends": state.list_friends(to_id),
                "friend_requests": state.list_friend_requests(to_id),
                "all_players": state.search_players("", limit=100),
            })
            return True

        if path == "/api/dashboard/friends/add":
            friend_id = _to_int(data.get("friend_id"))
            if friend_id <= 0:
                handler.send_json({"ok": False, "error": "Valid friend_id is required"}, status=400)
                return True
            if data.get("nickname") or not state.get_player(friend_id):
                state.upsert_player(
                    friend_id,
                    nickname=str(data.get("nickname") or f"Friend_{friend_id}"),
                    is_online=True,
                    online_status=1,
                    can_invite=True,
                )
            auto_accept = bool(data.get("auto_accept", True))
            res = state.add_friend(friend_id=friend_id, account_id=account_id, auto_accept=auto_accept)
            handler.send_json({
                **res,
                "friends": state.list_friends(account_id),
                "friend_requests": state.list_friend_requests(account_id),
                "all_players": state.search_players("", limit=100),
            })
            return True

        if path == "/api/dashboard/friends/accept":
            friend_id = _to_int(data.get("friend_id"))
            player = state.accept_friend(friend_id=friend_id, account_id=account_id)
            handler.send_json({
                "ok": player is not None,
                "player": player,
                "friends": state.list_friends(account_id),
                "friend_requests": state.list_friend_requests(account_id),
            })
            return True

        if path == "/api/dashboard/friends/reject":
            friend_id = _to_int(data.get("friend_id"))
            ok = state.reject_friend(friend_id=friend_id, account_id=account_id)
            handler.send_json({
                "ok": ok,
                "friends": state.list_friends(account_id),
                "friend_requests": state.list_friend_requests(account_id),
            })
            return True

        if path == "/api/dashboard/friends/remove":
            friend_id = _to_int(data.get("friend_id"))
            ok = state.remove_friend(friend_id=friend_id, account_id=account_id)
            handler.send_json({
                "ok": ok,
                "friends": state.list_friends(account_id),
                "friend_requests": state.list_friend_requests(account_id),
            })
            return True

        if path == "/api/dashboard/friends/online":
            pid = _to_int(data.get("player_id") or data.get("target_id") or data.get("account_id"))
            online_status = _to_int(data.get("online_status"), 1)
            player = state.set_player_online(pid, online_status=online_status)
            handler.send_json({
                "ok": player is not None,
                "player": player,
                "friends": state.list_friends(DEFAULT_ACCOUNT_ID),
                "all_players": state.search_players("", limit=100),
            })
            return True

        # ------------------------------------------------------------------
        # 3. Squad / Team Lobby & Invites Controls
        # ------------------------------------------------------------------
        if path == "/api/dashboard/squad/create":
            leader_id = _to_int(data.get("leader_id"), account_id)
            mode = str(data.get("mode") or "squad").lower()
            team_name = str(data.get("team_name") or "India V1 Squad")
            game_mode = _to_int(data.get("game_mode"), 1)
            map_id = _to_int(data.get("map_id"), 1)
            team = state.create_team(
                leader_id=leader_id,
                mode=mode,
                game_mode=game_mode,
                map_id=map_id,
                team_name=team_name,
            )
            handler.send_json({
                "ok": True,
                "team": team,
                "team_invitations": state.list_team_invitations(account_id),
            })
            return True

        if path == "/api/dashboard/squad/invite":
            direction = str(data.get("direction") or "").lower()
            mode = str(data.get("mode") or "squad").lower()
            game_mode = _to_int(data.get("game_mode"), 1)
            map_id = _to_int(data.get("map_id"), 1)

            if direction == "to_player" or (
                not direction and _to_int(data.get("target_id"), account_id) == account_id
                and _to_int(data.get("inviter_id"), 0) not in (0, account_id)
            ):
                inviter_id = _to_int(data.get("inviter_id"), 20001)
                if not state.get_player(inviter_id):
                    state.upsert_player(inviter_id, nickname=f"Bot_{inviter_id}", is_online=True, online_status=1, can_invite=True)
                inviter_team = state.get_team(account_id=inviter_id)
                if not inviter_team:
                    inviter_prof = state.get_player(inviter_id) or {}
                    inviter_team = state.create_team(
                        leader_id=inviter_id,
                        mode=mode,
                        game_mode=game_mode,
                        map_id=map_id,
                        team_name=f"{inviter_prof.get('nickname', 'Bot')}'s Squad",
                    )
                res = state.invite_player(
                    team_id=inviter_team["team_id"],
                    target_id=account_id,
                    inviter_id=inviter_id,
                    auto_join_bot=False,
                )
                if res.get("ok") and res.get("team"):
                    res["tcp_pushed"] = _try_push_squad_invite_tcp(account_id, inviter_id, res["team"])
            else:
                target_id = _to_int(data.get("target_id"))
                if target_id <= 0:
                    handler.send_json({"ok": False, "error": "target_id is required"}, status=400)
                    return True
                team = state.get_team(team_id=data.get("team_id"), account_id=account_id)
                if not team:
                    team = state.create_team(
                        leader_id=account_id,
                        mode=mode,
                        game_mode=game_mode,
                        map_id=map_id,
                    )
                res = state.invite_player(
                    team_id=team["team_id"],
                    target_id=target_id,
                    inviter_id=account_id,
                    auto_join_bot=bool(data.get("auto_join_bot", False)),
                )

            handler.send_json({
                **res,
                "player_team": state.get_team(account_id=account_id),
                "team_invitations": state.list_team_invitations(account_id),
            })
            return True

        if path == "/api/dashboard/squad/join":
            team_id = _to_int(data.get("team_id"))
            player_id = _to_int(data.get("player_id"), account_id)
            res = state.join_team(team_id=team_id, player_id=player_id)
            handler.send_json({
                **res,
                "team_invitations": state.list_team_invitations(account_id),
            })
            return True

        if path == "/api/dashboard/squad/leave":
            player_id = _to_int(data.get("player_id"), account_id)
            team_id = _to_int(data.get("team_id"), 0) or None
            ok = state.leave_team(player_id=player_id, team_id=team_id)
            handler.send_json({
                "ok": ok,
                "team": state.get_team(account_id=account_id),
                "team_invitations": state.list_team_invitations(account_id),
            })
            return True

        if path == "/api/dashboard/squad/kick":
            team_id = _to_int(data.get("team_id"))
            target_id = _to_int(data.get("target_id"))
            res = state.kick_player(team_id=team_id, target_id=target_id, requester_id=account_id)
            handler.send_json(res)
            return True

        if path == "/api/dashboard/squad/ready":
            team = state.get_team(team_id=data.get("team_id"), account_id=account_id)
            if not team:
                handler.send_json({"ok": False, "error": "Not in a squad"}, status=404)
                return True
            updated = state.set_team_ready(
                team_id=team["team_id"],
                player_id=_to_int(data.get("player_id"), account_id),
                ready=bool(data.get("ready", True)),
            )
            handler.send_json({"ok": updated is not None, "team": updated})
            return True

        if path == "/api/dashboard/squad/decline":
            invite_id = _to_int(data.get("invite_id"))
            ok = state.decline_team_invitation(invite_id=invite_id, account_id=account_id)
            handler.send_json({
                "ok": ok,
                "team_invitations": state.list_team_invitations(account_id),
            })
            return True

        # ------------------------------------------------------------------
        # 4. Live Wallet, Items, Profile, Character & Pet Controls
        # ------------------------------------------------------------------
        if path == "/api/dashboard/wallet/grant":
            coins = _to_int(data.get("coins") if data.get("coins") is not None else data.get("gold"), 0)
            gems = _to_int(data.get("gems") if data.get("gems") is not None else data.get("diamonds"), 0)
            wallet = state.grant_currency(coins=coins, gems=gems, account_id=account_id)
            handler.send_json({"ok": True, "wallet": wallet})
            return True

        if path == "/api/dashboard/wallet/set":
            coins_raw = data.get("coins") if "coins" in data else data.get("gold")
            gems_raw = data.get("gems") if "gems" in data else data.get("diamonds")
            coins = int(coins_raw) if coins_raw is not None and str(coins_raw) != "" else None
            gems = int(gems_raw) if gems_raw is not None and str(gems_raw) != "" else None
            wallet = state.set_wallet(coins=coins, gems=gems, account_id=account_id)
            handler.send_json({"ok": True, "wallet": wallet})
            return True

        if path == "/api/dashboard/items/grant":
            item_ids = _parse_item_ids(data)
            count = max(1, _to_int(data.get("count"), 1))
            if not item_ids:
                handler.send_json({"ok": False, "error": "Provide item_id or item_ids"}, status=400)
                return True
            granted = []
            for iid in item_ids:
                new_count = state.add_item(iid, count=count)
                granted.append({"item_id": iid, "count": new_count})
            handler.send_json({
                "ok": True,
                "granted": granted,
                "unlocked_items_count": len(state.get_unlocked_items()),
            })
            return True

        if path == "/api/dashboard/profile/update":
            allowed = {}
            for field in ("nickname", "signature", "region"):
                if data.get(field) is not None:
                    allowed[field] = str(data[field])
            for field in ("level", "exp", "rank", "ranking_points", "banner_id", "head_pic"):
                if data.get(field) is not None and str(data[field]) != "":
                    allowed[field] = int(data[field])
            prof = state.update_profile(account_id=account_id, **allowed)
            handler.send_json({"ok": True, "profile": prof})
            return True

        if path == "/api/dashboard/character/select":
            avatar_id = _to_int(data.get("avatar_id"))
            char = state.select_character(avatar_id=avatar_id, account_id=account_id)
            if not char:
                handler.send_json({"ok": False, "error": f"Unknown avatar_id {avatar_id}"}, status=404)
                return True
            handler.send_json({"ok": True, "character": char, "profile": state.get_profile(account_id)})
            return True

        if path == "/api/dashboard/character/equip":
            avatar_id = _to_int(data.get("avatar_id"), (state.get_profile(account_id) or {}).get("avatar_id", 102000004))
            clothes = _parse_item_ids(data)
            if not clothes and "clothes" in data and isinstance(data["clothes"], list):
                clothes = [int(x) for x in data["clothes"]]
            char = state.equip_character_clothes(avatar_id, clothes)
            handler.send_json({"ok": True, "character": char, "profile": state.get_profile(account_id)})
            return True

        if path == "/api/dashboard/pet/select":
            pet_id = _to_int(data.get("pet_id"))
            skin_raw = data.get("skin_id")
            skin_id = int(skin_raw) if skin_raw is not None and str(skin_raw) != "" else None
            pet = state.select_pet(pet_id=pet_id, skin_id=skin_id, account_id=account_id)
            if not pet:
                handler.send_json({"ok": False, "error": f"Unknown pet_id {pet_id}"}, status=404)
                return True
            handler.send_json({"ok": True, "pet": pet, "profile": state.get_profile(account_id)})
            return True

        # ------------------------------------------------------------------
        # 5. Request Stream & On-Demand Protobuf Decoder
        # ------------------------------------------------------------------
        if path == "/api/dashboard/requests/clear":
            cleared = clear_requests()
            handler.send_json({"ok": True, "cleared": cleared})
            return True

        if path == "/api/dashboard/decode":
            raw_bytes = b""
            if data.get("hex"):
                clean_hex = "".join(str(data["hex"]).split())
                raw_bytes = bytes.fromhex(clean_hex)
            elif data.get("base64"):
                raw_bytes = base64.b64decode(str(data["base64"]))
            else:
                handler.send_json({"ok": False, "error": "Provide 'hex' or 'base64' payload"}, status=400)
                return True
            decoded = decode_protobuf_wire(raw_bytes)
            handler.send_json({
                "ok": True,
                "byte_len": len(raw_bytes),
                "hex": raw_bytes.hex(),
                "decoded": decoded,
            })
            return True

        # ------------------------------------------------------------------
        # 6. Lobby CMS, Banner Upload & Live Startup Popup Tracker
        # ------------------------------------------------------------------
        if path == "/api/dashboard/cms/upload_banner":
            filename = str(data.get("filename") or data.get("name") or "")
            b64 = str(data.get("data_base64") or data.get("base64") or data.get("data") or "")
            banner = _save_banner_file(filename, b64)
            handler.send_json({
                "ok": True,
                "banner": banner,
                "banners": _list_banners(),
            })
            return True

        if path == "/api/dashboard/cms/delete_banner":
            filename = str(data.get("filename") or data.get("name") or "")
            deleted = _delete_banner_file(filename)
            handler.send_json({
                "ok": deleted,
                "deleted": os.path.basename(filename),
                "banners": _list_banners(),
                **({"error": "Banner file not found"} if not deleted else {}),
            }, status=200 if deleted else 404)
            return True

        if path == "/api/dashboard/cms/upsert":
            cat = str(data.get("category") or "").strip()
            item = data.get("item")
            if not isinstance(item, dict):
                item = {k: v for k, v in data.items() if k != "category"}
            if cat in ("events", "activities") and isinstance(item.get("awards"), list):
                norm_awards = []
                for aw in item["awards"]:
                    if isinstance(aw, dict):
                        norm_awards.append({
                            "award_type": _to_int(aw.get("award_type"), 1),
                            "award_id": _to_int(aw.get("award_id"), 0),
                            "award_num": max(1, _to_int(aw.get("award_num"), 1)),
                        })
                item = dict(item)
                item["awards"] = norm_awards
            saved = state.upsert_cms_item(cat, item)
            handler.send_json({
                "ok": True,
                "category": cat,
                "item": saved,
                "items": state.list_cms(cat),
                "cms": state.get_cms_snapshot(),
            })
            return True

        if path == "/api/dashboard/cms/delete":
            cat = str(data.get("category") or "").strip()
            raw_id = data.get("id") if data.get("id") is not None else data.get("item_id")
            if raw_id is None:
                handler.send_json({"ok": False, "error": "Item id is required"}, status=400)
                return True
            ok = state.delete_cms_item(cat, _to_int(raw_id))
            handler.send_json({
                "ok": ok,
                "category": cat,
                "items": state.list_cms(cat),
                "cms": state.get_cms_snapshot(),
            })
            return True

        if path == "/api/dashboard/cms/toggle":
            cat = str(data.get("category") or "").strip()
            raw_id = data.get("id") if data.get("id") is not None else data.get("item_id")
            if raw_id is None:
                handler.send_json({"ok": False, "error": "Item id is required"}, status=400)
                return True
            enabled = data.get("enabled") if "enabled" in data else (
                data.get("is_open") if "is_open" in data else None
            )
            toggled = state.toggle_cms_item(
                cat,
                _to_int(raw_id),
                enabled=(bool(enabled) if enabled is not None else None),
            )
            if toggled is None:
                handler.send_json({"ok": False, "error": "CMS item not found"}, status=404)
                return True
            handler.send_json({
                "ok": True,
                "category": cat,
                "item": toggled,
                "items": state.list_cms(cat),
                "cms": state.get_cms_snapshot(),
            })
            return True

        if path == "/api/dashboard/cms/reorder":
            cat = str(data.get("category") or "").strip()
            raw_ids = data.get("ordered_ids") or []
            ordered_ids = [int(x) for x in raw_ids]
            items = state.reorder_cms(cat, ordered_ids)
            handler.send_json({
                "ok": True,
                "category": cat,
                "items": items,
                "cms": state.get_cms_snapshot(),
            })
            return True

        if path == "/api/dashboard/cms/reset":
            cat = str(data.get("category") or "").strip() or None
            cms = state.reset_cms(cat)
            handler.send_json({"ok": True, "category": cat, "cms": cms})
            return True

        if path == "/api/dashboard/cms/bump_splashes":
            updated = []
            for sp in state.list_splashes():
                bumped = state.upsert_splash({"id": sp["id"], "enabled": sp.get("enabled", True)})
                updated.append(bumped)
            handler.send_json({
                "ok": True,
                "splashes": updated,
                "cms": state.get_cms_snapshot(),
            })
            return True

        if path == "/api/dashboard/cms/feed/clear":
            cleared = state.clear_lobby_event_feed()
            handler.send_json({"ok": True, "cleared": cleared, "feed": []})
            return True

        if path == "/api/dashboard/branding/update":
            from core.branding import update_branding_slot
            slot_key = str(data.get("slot") or "").strip()
            image_data = data.get("image_base64") or data.get("image_data")
            push_emu = bool(data.get("push_to_emulator", True))
            res = update_branding_slot(slot_key, image_data, push_to_emulator=push_emu)
            handler.send_json(res, status=200 if res.get("ok") else 400)
            return True

        handler.send_json({"ok": False, "error": f"Unknown dashboard POST route: {path}"}, status=404)
        return True
    except ValueError as exc:
        handler.send_json({"ok": False, "error": f"Invalid parameter: {exc}"}, status=400)
        return True
    except Exception as exc:
        handler.send_json({"ok": False, "error": str(exc)}, status=500)
        return True


def render_dashboard_html(version: str = "1.39", sub_version: str = "1.39.4", port: int = 8080) -> str:
    html = _DASHBOARD_HTML_TEMPLATE
    html = html.replace("__VERSION__", str(version))
    html = html.replace("__SUB_VERSION__", str(sub_version))
    html = html.replace("__PORT__", str(port))
    return html


_DASHBOARD_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>India V1 1.39 — Control Center</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-base: #06090f;
    --bg-surface: #0c121d;
    --bg-card: #121a29;
    --border: #1e293b;
    --border-subtle: #152033;
    --border-accent: #38bdf8;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-tertiary: #64748b;
    --accent: #38bdf8;
    --accent-glow: rgba(56, 189, 248, 0.15);
    --green: #10b981;
    --gold: #f59e0b;
    --radius-sm: 6px;
    --radius-md: 10px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    width: 100%;
    height: 100vh;
    overflow: hidden;
    background: var(--bg-base);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 13px;
  }

  /* Compact Header */
  .app-header {
    height: 52px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
    padding: 0 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }
  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .brand-badge {
    background: #0284c7;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: var(--radius-sm);
    letter-spacing: 0.05em;
  }
  .brand-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .brand-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-tertiary);
    border-left: 1px solid var(--border);
    padding-left: 10px;
  }
  .header-stats {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .chip {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 4px 10px;
    font-size: 11.5px;
    color: var(--text-secondary);
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .chip.online { border-color: rgba(16, 185, 129, 0.4); color: #34d399; }
  .chip.gold { color: #fbbf24; font-family: 'JetBrains Mono', monospace; }
  .chip.gems { color: #38bdf8; font-family: 'JetBrains Mono', monospace; }
  .indicator-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
  }

  /* Body Frame */
  .app-body {
    display: flex;
    height: calc(100vh - 52px);
    width: 100%;
    overflow: hidden;
  }

  /* Sidebar Navigation */
  .app-nav {
    width: 220px;
    flex-shrink: 0;
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 14px 10px;
    gap: 4px;
    overflow-y: auto;
  }
  .nav-group-title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--text-tertiary);
    text-transform: uppercase;
    padding: 8px 10px 4px;
  }
  .nav-item {
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-secondary);
    font-size: 12.5px;
    font-weight: 500;
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    text-align: left;
    transition: all 0.15s ease;
  }
  .nav-item:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.03);
    border-color: var(--border-subtle);
  }
  .nav-item.active {
    color: #fff;
    background: #1e293b;
    border-color: var(--accent);
    font-weight: 600;
  }
  .nav-bullet {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--text-tertiary);
  }
  .nav-item.active .nav-bullet {
    background: var(--accent);
    box-shadow: 0 0 6px var(--accent);
  }

  /* Viewport Hosting Swarm Modules */
  .view-viewport {
    flex: 1;
    height: 100%;
    background: var(--bg-base);
    position: relative;
    overflow: hidden;
  }
  .module-frame {
    width: 100%;
    height: 100%;
    border: none;
    display: none;
    background: var(--bg-base);
  }
  .module-frame.active {
    display: block;
  }
</style>
</head>
<body>

<!-- Header -->
<header class="app-header">
  <div class="header-left">
    <div class="brand-badge">INDIA V1</div>
    <div class="brand-title">Control Center</div>
    <div class="brand-sub">OB17 FF 1.39.4 — Localhost Engine</div>
  </div>
  <div class="header-stats">
    <div class="chip online"><span class="indicator-dot"></span> Port :__PORT__ &amp; :8081 Active</div>
    <div class="chip gold">Gold: <span id="hdr-coins">1,158,549</span></div>
    <div class="chip gems">Diamonds: <span id="hdr-gems">999,999</span></div>
    <div class="chip">Account: <span id="hdr-nick">Clack</span> (UID: 10000001)</div>
    <button class="chip" style="cursor:pointer; background:#1e293b; color:#fff;" onclick="reloadActiveFrame()">Reload View</button>
  </div>
</header>

<div class="app-body">
  <!-- Nav -->
  <aside class="app-nav">
    <div class="nav-group-title">Swarm Modules</div>
    <button class="nav-item active" onclick="switchModule('banners', this)">
      <span class="nav-bullet"></span> Banners &amp; Billboard Ads
    </button>
    <button class="nav-item" onclick="switchModule('events', this)">
      <span class="nav-bullet"></span> Events &amp; Quests Studio
    </button>
    <button class="nav-item" onclick="switchModule('tracker', this)">
      <span class="nav-bullet"></span> Popup &amp; Flow Tracker
    </button>
    <button class="nav-item" onclick="switchModule('social', this)">
      <span class="nav-bullet"></span> Mail &amp; Squad TCP Studio
    </button>
    <button class="nav-item" onclick="switchModule('vault', this)">
      <span class="nav-bullet"></span> Vault &amp; Character Catalog
    </button>
  </aside>

  <!-- Viewport -->
  <main class="view-viewport">
    <iframe id="frame-banners" class="module-frame active" src="/dashboard/banners.html"></iframe>
    <iframe id="frame-events" class="module-frame" src="about:blank"></iframe>
    <iframe id="frame-tracker" class="module-frame" src="about:blank"></iframe>
    <iframe id="frame-social" class="module-frame" src="about:blank"></iframe>
    <iframe id="frame-vault" class="module-frame" src="about:blank"></iframe>
  </main>
</div>

<script>
  const moduleUrls = {
    banners: '/dashboard/banners.html',
    events: '/dashboard/events.html',
    tracker: '/dashboard/tracker.html',
    social: '/dashboard/social.html',
    vault: '/dashboard/vault.html'
  };

  let activeModuleId = 'banners';

  function switchModule(modId, btn) {
    activeModuleId = modId;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.module-frame').forEach(f => f.classList.remove('active'));
    const frame = document.getElementById('frame-' + modId);
    if (frame) {
      if (frame.src === 'about:blank' || !frame.src) {
        frame.src = moduleUrls[modId];
      }
      frame.classList.add('active');
    }
  }

  function reloadActiveFrame() {
    const frame = document.getElementById('frame-' + activeModuleId);
    if (frame) {
      frame.src = moduleUrls[activeModuleId];
    }
  }

  // Sync wallet state periodically
  async function syncHeader() {
    try {
      const res = await fetch('/api/dashboard/state');
      if (!res.ok) return;
      const data = await res.json();
      if (data.profile) {
        if (data.profile.nickname) document.getElementById('hdr-nick').textContent = data.profile.nickname;
        if (data.profile.gold !== undefined) document.getElementById('hdr-coins').textContent = Number(data.profile.gold).toLocaleString();
        if (data.profile.diamonds !== undefined) document.getElementById('hdr-gems').textContent = Number(data.profile.diamonds).toLocaleString();
      }
    } catch (e) {}
  }
  syncHeader();
  setInterval(syncHeader, 5000);
</script>
</body>
</html>
"""
