"""
HTTP & TCP Lobby handlers for Free Fire 1.39 Lobby Squad/Group, Matchmaking,
and Championship Team protocols.

Integrates directly with `core.state.state` (`ServerState`) and `proto.team_models`
so lobby squads, friend/bot invites, member ready states, mode/map selections,
matchmaking queue status, and Championship Teams all stay synchronized with the
Web Admin Dashboard and game client.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.state import DEFAULT_ACCOUNT_ID, DEFAULT_CLOTHES, state
from proto.decoder import decode_proto, get_string, get_varint
from proto.team_models import (
    EGroupLeaveReason,
    EGroupProto,
    EMatchmakingProto,
    EProtocolProto,
    GROUP_MODE_MAX_MEMBERS,
    GROUP_MODE_TO_STR,
    GameMode,
    GroupMode,
    MatchMode,
    TeamMemberType,
    decode_cs_add_team_contact_info_req,
    decode_cs_approve_invite_req,
    decode_cs_approve_join_req,
    decode_cs_create_team_req,
    decode_cs_decline_invite_req,
    decode_cs_decline_join_req,
    decode_cs_get_championship_req,
    decode_cs_init_championship_req,
    decode_cs_invite_to_team_req,
    decode_cs_modify_team_info_req,
    decode_cs_remove_member_req,
    decode_cs_team_info_req,
    decode_cs_team_match_stats_history_req,
    decode_cs_team_name_req,
    decode_cs_team_season_stats_req,
    decode_group_accept_req,
    decode_group_change_req,
    decode_group_create_req,
    decode_group_id_req,
    decode_group_invite_req,
    decode_group_ready_req,
    decode_show_emote_req,
    decode_show_pet_action_req,
    decode_matchmaking_group_start_req,
    decode_matchmaking_start_req,
    decode_proto_req,
    decode_team_id_req,
    encode_account_info_basic_bundle_res,
    encode_cs_get_championship_config_res,
    encode_cs_team_championship_info_res,
    encode_cs_team_championship_season_stats_res,
    encode_cs_team_id_res,
    encode_cs_team_info_bundle_res,
    encode_cs_team_match_stats_history_res,
    encode_group_dismiss_ntf,
    encode_group_info,
    encode_group_invite_ntf,
    encode_group_leave_ntf,
    encode_group_stop_ntf,
    encode_matchmaking_suss_ntf,
    encode_message_notify,
    encode_show_emote_ntf,
    encode_show_pet_action_ntf,
    encode_team_info,
    encode_team_member_list_with_account_info,
    group_mode_from_team,
)


# ---------------------------------------------------------------------------
# Thread-safe Championship / Extended Group Metadata Store
# ---------------------------------------------------------------------------

_META_LOCK = threading.RLock()
_TEAM_META: Dict[int, Dict[str, Any]] = {}
_TEAM_APPLICANTS: Dict[int, List[Dict[str, Any]]] = {}
_CHAMPIONSHIP_INFO: Dict[int, Dict[str, Any]] = {}


def _get_meta(team_id: int) -> Dict[str, Any]:
    with _META_LOCK:
        return dict(_TEAM_META.get(int(team_id), {}))


def _update_meta(team_id: int, **updates: Any) -> Dict[str, Any]:
    with _META_LOCK:
        entry = _TEAM_META.setdefault(int(team_id), {})
        for k, v in updates.items():
            if v is not None:
                entry[k] = v
        return dict(entry)


def _clear_meta(team_id: int) -> None:
    with _META_LOCK:
        _TEAM_META.pop(int(team_id), None)
        _TEAM_APPLICANTS.pop(int(team_id), None)
        _CHAMPIONSHIP_INFO.pop(int(team_id), None)


def _push_team_packet(
    team: Optional[Dict[str, Any]],
    cmd: int,
    payload: bytes,
    exclude_id: Optional[int] = None,
) -> None:
    """Push an unsolicited `MessageNotify` frame to all connected members of `team`."""
    if not team:
        return
    try:
        from tcp_server import push_tcp_notify
    except ImportError:
        return
    for m in team.get("members") or []:
        aid = int(m.get("account_id", 0))
        if aid > 0 and (exclude_id is None or aid != exclude_id):
            try:
                push_tcp_notify(aid, EProtocolProto.GROUP, cmd, payload)
            except Exception:
                pass


def _push_account_packet(account_id: int, cmd: int, payload: bytes) -> None:
    """Push an unsolicited `MessageNotify` frame to a specific connected account."""
    if not account_id or int(account_id) <= 0:
        return
    try:
        from tcp_server import push_tcp_notify
    except ImportError:
        return
    try:
        push_tcp_notify(int(account_id), EProtocolProto.GROUP, cmd, payload)
    except Exception:
        pass


def _resolve_profile(account_id: int) -> Dict[str, Any]:
    """Resolve full profile dict for either the local player or a bot/friend."""
    aid = int(account_id)
    if aid == DEFAULT_ACCOUNT_ID:
        prof = dict(state.get_profile(aid))
    else:
        player = state.get_player(aid)
        if player:
            prof = dict(player)
        else:
            prof = dict(state.get_profile(aid))
    # Guarantee clothes are populated so Unity renders the 3D model properly on pedestal
    if not prof.get("clothes"):
        prof["clothes"] = list(DEFAULT_CLOTHES)
    return prof


def _enrich_team(team: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Merge ServerState team dict with extended Group/Championship metadata."""
    if not team:
        return None
    tid = int(team["team_id"])
    merged = dict(team)
    meta = _get_meta(tid)
    prof = _resolve_profile(int(merged.get("leader_id", DEFAULT_ACCOUNT_ID)))
    merged.setdefault("region", prof.get("region", "ID"))
    merged.setdefault("banner_id", prof.get("banner_id", 901000001))
    merged.setdefault("head_pic", prof.get("head_pic", 902000001))
    merged["contact_info"] = meta.get("contact_info", "")
    merged["country_or_area"] = meta.get("country_or_area", prof.get("region", "ID"))
    merged["auto_group"] = bool(meta.get("auto_group", False))
    merged["difficulty"] = int(meta.get("difficulty", 0))
    map_ids = meta.get("map_ids")
    if not map_ids:
        map_ids = [int(merged.get("map_id", 1))]
    merged["map_ids"] = [int(m) for m in map_ids]
    game_mode = int(merged.get("game_mode", GameMode.BATTLE_ROYALE))
    default_mm = MatchMode.RANKING if game_mode == GameMode.BATTLE_ROYALE else MatchMode.CASUAL
    merged["match_mode"] = int(meta.get("match_mode", default_mm))
    merged["is_ranking_match"] = bool(
        meta.get("is_ranking_match", merged["match_mode"] == MatchMode.RANKING)
    )
    if "group_mode" in meta:
        merged["_explicit_group_mode"] = int(meta["group_mode"])
    leader_id = int(merged.get("leader_id", DEFAULT_ACCOUNT_ID))
    merged["group_id"] = leader_id
    for m in merged.get("members") or []:
        if int(m.get("account_id", 0)) == leader_id:
            m["role"] = 1
            m["ready"] = False
        else:
            if m.get("role") == 1:
                m["role"] = 0
    return merged


def _build_team_profiles(team: Dict[str, Any]) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Optional[Dict[str, Any]]]]:
    """Resolve profiles and active pet dicts for every member in `team`."""
    profiles: Dict[int, Dict[str, Any]] = {}
    pets: Dict[int, Optional[Dict[str, Any]]] = {}
    for m in team.get("members") or []:
        aid = int(m.get("account_id", 0))
        if aid <= 0:
            continue
        prof = _resolve_profile(aid)
        profiles[aid] = prof
        pet_id = int(prof.get("selected_pet_id", 0))
        if pet_id > 0:
            pet = state.get_pet(pet_id)
            if pet:
                pet = dict(pet)
                pet["skin_id"] = int(prof.get("selected_pet_skin_id", pet.get("skin_id", 0)))
                pets[aid] = pet
            else:
                pets[aid] = {
                    "pet_id": pet_id,
                    "name": f"Pet_{pet_id}",
                    "level": 1,
                    "skin_id": int(prof.get("selected_pet_skin_id", 0)),
                }
        else:
            pets[aid] = None
    return profiles, pets


def _encode_team_group_info(team: Dict[str, Any]) -> bytes:
    """Encode an enriched ServerState team dict as `tcp.GroupInfo`."""
    enriched = _enrich_team(team) or team
    profiles, pets = _build_team_profiles(enriched)
    return encode_group_info(enriched, profiles, pet_lookup=pets)


def _find_member_or_default(team: Dict[str, Any], account_id: int) -> Dict[str, Any]:
    leader_id = int(team.get("leader_id", 0))
    for m in team.get("members") or []:
        if int(m.get("account_id", 0)) == int(account_id):
            return m
    is_leader = (int(account_id) == leader_id)
    return {
        "account_id": int(account_id),
        "nickname": _resolve_profile(account_id).get("nickname", f"Player_{account_id}"),
        "role": 1 if is_leader else 0,
        "ready": False if is_leader else True,
        "joined_at": int(time.time()),
    }


def _get_or_create_team(account_id: int, default_mode: str = "squad") -> Dict[str, Any]:
    team = state.get_team(account_id=account_id)
    if not team:
        team = state.create_team(leader_id=account_id, mode=default_mode)
    return team


def _resolve_target_team(team_id: int, account_id: int) -> Optional[Dict[str, Any]]:
    if team_id and team_id > 0:
        team = state.get_team(team_id=team_id)
        if team:
            return team
        team = state.get_team(account_id=team_id)
        if team:
            return team
    return state.get_team(account_id=account_id)


def _ensure_championship_record(team_id: int, ctype: int = 1, cid: int = 1) -> Dict[str, Any]:
    with _META_LOCK:
        rec = _CHAMPIONSHIP_INFO.setdefault(int(team_id), {
            "team_id": int(team_id),
            "championship_type": int(ctype or 1),
            "championship_id": int(cid or 1),
            "tickets_num": 3,
            "trial_games_played": 0,
            "trial_kills": 0,
            "trial_valid_score": 0,
            "trial_total_score": 0,
            "trial_pos": 0,
            "is_enter_final": False,
            "final_games_played": 0,
            "final_kills": 0,
            "final_valid_score": 0,
            "final_total_score": 0,
            "final_pos": 0,
        })
        rec["championship_type"] = int(ctype or rec["championship_type"])
        rec["championship_id"] = int(cid or rec["championship_id"])
        return dict(rec)


def _is_bot_account(account_id: int) -> bool:
    """Offline sandbox bots (`20001..20010`) auto-join squads when invited."""
    p = state.get_player(int(account_id))
    return bool(p and p.get("is_bot"))


# ---------------------------------------------------------------------------
# Core Operations (shared by HTTP and TCP paths)
# ---------------------------------------------------------------------------

def _op_create_group(account_id: int, req: Dict[str, Any]) -> Tuple[Dict[str, Any], bytes]:
    gmode = int(req.get("group_mode", GroupMode.QUAD))
    mode_str = GROUP_MODE_TO_STR.get(gmode, "squad")
    max_members = GROUP_MODE_MAX_MEMBERS.get(gmode, 4)
    map_ids = req.get("map_ids") or [1]
    game_mode = int(req.get("game_mode", GameMode.BATTLE_ROYALE))
    match_mode = int(req.get("match_mode", MatchMode.CASUAL))
    difficulty = int(req.get("difficulty", 0))

    team = state.create_team(
        leader_id=account_id,
        mode=mode_str,
        max_members=max_members,
        game_mode=game_mode,
        map_id=int(map_ids[0]),
    )
    team["leader_id"] = int(account_id)
    team["group_id"] = int(account_id)
    for m in team.get("members", []):
        if int(m.get("account_id", 0)) == int(account_id):
            m["role"] = 1
            m["ready"] = False
    _update_meta(
        team["team_id"],
        map_ids=[int(m) for m in map_ids],
        match_mode=match_mode,
        difficulty=difficulty,
        group_mode=gmode,
        is_ranking_match=(match_mode == MatchMode.RANKING),
    )
    return team, _encode_team_group_info(team)


def _op_invite_to_group(account_id: int, team_id: int, invitee_id: int) -> Dict[str, Any]:
    team = _resolve_target_team(team_id, account_id) or _get_or_create_team(account_id)
    tid = int(team["team_id"])
    if team.get("max_members", 1) < 4:
        state.update_team_settings(tid, mode="squad", max_members=4)
        team = state.get_team(team_id=tid) or team
    res = state.invite_player(
        team["team_id"],
        invitee_id,
        inviter_id=account_id,
        auto_join_bot=_is_bot_account(invitee_id),
    )
    return {
        "result": res,
        "team": res.get("team") or state.get_team(team_id=team["team_id"]) or team,
    }


def _op_change_group(account_id: int, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    team = _resolve_target_team(req.get("group_id", 0), account_id)
    if not team:
        return None
    tid = int(team["team_id"])

    mode_str: Optional[str] = None
    max_members: Optional[int] = None
    if req.get("has_group_mode"):
        gm = int(req["group_mode"])
        mode_str = GROUP_MODE_TO_STR.get(gm, "squad")
        max_members = GROUP_MODE_MAX_MEMBERS.get(gm, 4)

    game_mode = int(req["game_mode"]) if req.get("has_game_mode") else None
    map_ids = req.get("map_ids") or []
    map_id = int(map_ids[0]) if (req.get("has_map_ids") and map_ids) else None
    auto_group = bool(req["auto_group"]) if req.get("has_auto_group") else None

    updated = state.update_team_settings(
        tid,
        mode=mode_str,
        game_mode=game_mode,
        map_id=map_id,
        max_members=max_members,
        auto_group=auto_group,
    )
    meta_updates: Dict[str, Any] = {}
    if req.get("has_auto_group"):
        meta_updates["auto_group"] = bool(req["auto_group"])
    if req.get("has_map_ids") and map_ids:
        meta_updates["map_ids"] = [int(m) for m in map_ids]
    if req.get("difficulty"):
        meta_updates["difficulty"] = int(req["difficulty"])
    if req.get("has_match_mode"):
        mm = int(req["match_mode"])
        meta_updates["match_mode"] = mm
        meta_updates["is_ranking_match"] = (mm == MatchMode.RANKING)
    if req.get("has_group_mode"):
        meta_updates["group_mode"] = int(req["group_mode"])
    if meta_updates:
        _update_meta(tid, **meta_updates)
    return updated or team


def _build_matchmaking_suss_ntf(enriched: Dict[str, Any]) -> bytes:
    """Build `tcp.MatchmakingSussNtf` from an enriched team dictionary."""
    tid = int(enriched.get("team_id", 0))
    match_id = int(enriched.get("match_id") or (tid * 100 + int(enriched.get("matchmaking_started_at") or time.time()) % 100))
    host = os.environ.get("INDIA V1_GAME_SERVER_HOST", "10.0.2.2")
    port = int(os.environ.get("INDIA V1_GAME_SERVER_PORT", "39800"))
    leader_id = int(enriched.get("leader_id") or 10001)

    import hashlib
    sec_hex = hashlib.md5(f"sec_{match_id}".encode()).hexdigest()
    tok_hex = hashlib.md5(f"prep_{match_id}_{int(time.time())}".encode()).hexdigest()

    try:
        from combat.udp_server import get_combat_server
        from combat.match_director import global_match_director
        from core.state import state
        udp_srv = get_combat_server()
        player_nick = "PushpaGG"
        try:
            p_prof = state.get_player(leader_id)
            if p_prof and p_prof.get("nickname"):
                player_nick = p_prof["nickname"]
        except Exception:
            pass

        udp_srv.register_match_token(token=tok_hex, account_id=leader_id, match_id=match_id, nickname=player_nick)
        if global_match_director:
            global_match_director.create_match(
                match_id=match_id,
                map_id=(enriched.get("map_ids") or [int(enriched.get("map_id", 1))])[0],
                game_mode=int(enriched.get("game_mode", GameMode.BATTLE_ROYALE)),
                match_mode=int(enriched.get("match_mode", MatchMode.CASUAL)),
                host_player_id=str(leader_id),
                host_nickname=player_nick,
                bot_count=2,
                prepare_token=tok_hex,
                secret=sec_hex
            )
    except Exception as e:
        logger.error("Failed to register combat match in team_handler: %s", e)

    return encode_matchmaking_suss_ntf(
        match_id=match_id,
        server_addr=f"{host}:{port}",
        secret=sec_hex,
        prepare_token=tok_hex,
        sleep_ms=500,
        map_id=(enriched.get("map_ids") or [int(enriched.get("map_id", 1))])[0],
        game_mode=int(enriched.get("game_mode", GameMode.BATTLE_ROYALE)),
        match_mode=int(enriched.get("match_mode", MatchMode.CASUAL)),
        difficulty=int(enriched.get("difficulty", 0)),
    )


def _op_start_matchmaking(
    account_id: int,
    team_id: int = 0,
    game_mode: Optional[int] = None,
    map_ids: Optional[List[int]] = None,
    match_mode: Optional[int] = None,
    difficulty: int = 0,
) -> Tuple[Dict[str, Any], bytes]:
    team = _resolve_target_team(team_id, account_id)
    if not team:
        team = _get_or_create_team(account_id, default_mode="solo")
    tid = int(team["team_id"])
    map_id = int(map_ids[0]) if map_ids else None
    mm_res = state.start_matchmaking(
        team_id=tid,
        account_id=account_id,
        game_mode=game_mode,
        map_id=map_id,
    )
    if map_ids or match_mode is not None or difficulty:
        _update_meta(
            tid,
            map_ids=[int(m) for m in map_ids] if map_ids else None,
            match_mode=match_mode,
            difficulty=difficulty or None,
        )
    mm_team = mm_res.get("team") if isinstance(mm_res, dict) and "team" in mm_res else (mm_res or team)
    enriched = _enrich_team(mm_team) or mm_team
    return mm_team, _build_matchmaking_suss_ntf(enriched)


# ---------------------------------------------------------------------------
# Championship / Team HTTP Endpoint Implementations (`proto.*`)
# ---------------------------------------------------------------------------

def _http_create_team(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_create_team_req(raw_body)
    name = req["team_name"] or "Barbosa Squad"
    team = state.create_team(leader_id=account_id, team_name=name)
    _update_meta(
        team["team_id"],
        contact_info=req["contact_info"],
        country_or_area=req["country_or_area"] or _resolve_profile(account_id).get("region", "ID"),
    )
    handler.send_proto("CSTeamIDRes", encode_cs_team_id_res(team["team_id"]))


def _http_request_join_team(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_team_id_req(raw_body)
    tid = int(req["team_id"])
    team = state.get_team(team_id=tid)
    if team:
        with _META_LOCK:
            apps = _TEAM_APPLICANTS.setdefault(tid, [])
            if not any(int(a["applicant_id"]) == int(account_id) for a in apps):
                apps.append({"applicant_id": int(account_id), "team_id": tid, "create_at": int(time.time())})
        state.join_team(tid, player_id=account_id)
    handler.send_proto("Empty (RequestJoinTeam)", b"")


def _http_modify_team_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_modify_team_info_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if team:
        tid = int(team["team_id"])
        if req["team_name"]:
            # Update team_name directly via state lock or re-apply metadata
            with state._lock:  # ServerState stores teams under `_teams` with `_lock`
                st_team = state._teams.get(tid)
                if st_team:
                    st_team["team_name"] = req["team_name"]
        if req["country_or_area"]:
            _update_meta(tid, country_or_area=req["country_or_area"])
    handler.send_proto("Empty (ModifyTeamInfo)", b"")


def _http_add_team_contact_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_add_team_contact_info_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if team:
        _update_meta(int(team["team_id"]), contact_info=req["contact_info"])
    handler.send_proto("Empty (AddTeamContactInfo)", b"")


def _http_get_team_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_team_info_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if not team:
        handler.send_proto("TeamInfo (empty)", encode_team_info({"team_id": 0, "team_name": "", "members": []}))
        return
    enriched = _enrich_team(team) or team
    handler.send_proto("TeamInfo", encode_team_info(enriched))


def _http_get_team_members(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_team_id_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if not team:
        handler.send_proto("TeamMemberListWithAccountInfo (empty)", encode_team_member_list_with_account_info([]))
        return
    enriched = _enrich_team(team) or team
    leader_id = int(enriched.get("leader_id", 0))
    items: List[Dict[str, Any]] = []
    for m in enriched.get("members") or []:
        aid = int(m.get("account_id", 0))
        items.append({
            "profile": _resolve_profile(aid),
            "team": enriched,
            "team_id": int(enriched["team_id"]),
            "member_type": TeamMemberType.CAPTAIN if aid == leader_id else TeamMemberType.NORMAL,
            "join_at": int(m.get("joined_at", int(time.time()))),
        })
    handler.send_proto("TeamMemberListWithAccountInfo", encode_team_member_list_with_account_info(items))


def _http_quit_team(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_team_id_req(raw_body)
    tid = int(req["team_id"])
    state.leave_team(player_id=account_id, team_id=tid or None)
    if tid and not state.get_team(team_id=tid):
        _clear_meta(tid)
    handler.send_proto("Empty (QuitTeam)", b"")


def _http_dismiss_team(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_team_id_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if team:
        tid = int(team["team_id"])
        for m in list(team.get("members") or []):
            aid = int(m.get("account_id", 0))
            if aid != account_id:
                state.leave_team(player_id=aid, team_id=tid)
        state.leave_team(player_id=account_id, team_id=tid)
        _clear_meta(tid)
    handler.send_proto("Empty (DismissTeam)", b"")


def _http_get_team_applicant_list(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_team_id_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if not team:
        handler.send_proto("AccountInfoBasicBundleRes (Applicants)", encode_account_info_basic_bundle_res([]))
        return
    tid = int(team["team_id"])
    with _META_LOCK:
        apps = list(_TEAM_APPLICANTS.get(tid, []))
    profiles = [_resolve_profile(int(a["applicant_id"])) for a in apps]
    handler.send_proto(
        "AccountInfoBasicBundleRes (Applicants)",
        encode_account_info_basic_bundle_res(profiles),
    )


def _http_approve_join_application(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_approve_join_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if team:
        tid = int(team["team_id"])
        app_id = int(req["applicant_id"])
        state.join_team(tid, player_id=app_id)
        with _META_LOCK:
            _TEAM_APPLICANTS[tid] = [
                a for a in _TEAM_APPLICANTS.get(tid, []) if int(a["applicant_id"]) != app_id
            ]
    handler.send_proto("Empty (ApproveJoinTeamApplication)", b"")


def _http_decline_join_application(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_decline_join_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if team:
        tid = int(team["team_id"])
        drop_ids = set(int(x) for x in req["applicant_ids"])
        with _META_LOCK:
            _TEAM_APPLICANTS[tid] = [
                a for a in _TEAM_APPLICANTS.get(tid, []) if int(a["applicant_id"]) not in drop_ids
            ]
    handler.send_proto("Empty (DeclineJoinTeamApplication)", b"")


def _http_invite_to_team(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_invite_to_team_req(raw_body)
    _op_invite_to_group(account_id, req["team_id"], req["invitee_id"])
    handler.send_proto("Empty (InviteToTeam)", b"")


def _http_approve_join_invitation(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_approve_invite_req(raw_body)
    tid = int(req["team_id"])
    if tid <= 0 and req["inviter_id"] > 0:
        inv_team = state.get_team(account_id=int(req["inviter_id"]))
        tid = int(inv_team["team_id"]) if inv_team else 0
    if tid > 0:
        state.join_team(tid, player_id=account_id)
    handler.send_proto("Empty (ApproveJoinTeamInvitation)", b"")


def _http_decline_join_invitation(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_decline_invite_req(raw_body)
    inviter_ids = set(int(x) for x in req["inviter_ids"])
    for inv in state.list_team_invitations(account_id=account_id):
        if not inviter_ids or int(inv.get("inviter_id", 0)) in inviter_ids:
            state.decline_team_invitation(int(inv["invite_id"]), account_id=account_id)
    handler.send_proto("Empty (DeclineJoinTeamInvitation)", b"")


def _http_get_team_invitation_list(handler: Any, _raw_body: bytes, account_id: int) -> None:
    invites = state.list_team_invitations(account_id=account_id)
    profiles: List[Dict[str, Any]] = []
    team_lookup: Dict[int, Dict[str, Any]] = {}
    for inv in invites:
        inviter_id = int(inv.get("inviter_id", 0))
        if inviter_id <= 0:
            continue
        prof = _resolve_profile(inviter_id)
        profiles.append(prof)
        tid = int(inv.get("team_id", 0))
        inv_team = state.get_team(team_id=tid) if tid > 0 else None
        if inv_team:
            team_lookup[inviter_id] = inv_team
        else:
            team_lookup[inviter_id] = {
                "team_id": tid,
                "team_name": inv.get("team_name", "Barbosa Squad"),
                "members": [{"account_id": inviter_id}],
            }
    handler.send_proto(
        "AccountInfoBasicBundleRes (Invitations)",
        encode_account_info_basic_bundle_res(profiles, team_lookup=team_lookup),
    )


def _http_fuzzy_search_team(handler: Any, raw_body: bytes, _account_id: int) -> None:
    req = decode_cs_team_name_req(raw_body)
    query = req["team_name"].strip().lower()
    matched: List[Dict[str, Any]] = []
    with state._lock:
        for team in state._teams.values():
            name = str(team.get("team_name", "")).lower()
            if not query or query in name:
                enriched = _enrich_team(dict(team))
                if enriched:
                    matched.append(enriched)
    handler.send_proto("CSTeamInfoBundleRes", encode_cs_team_info_bundle_res(matched))


def _http_remove_team_member(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_remove_member_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    if team and req["removee_id"] > 0:
        state.kick_player(int(team["team_id"]), int(req["removee_id"]), requester_id=account_id)
    handler.send_proto("Empty (RemoveTeamMember)", b"")


def _http_init_championship_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_init_championship_req(raw_body)
    team = state.get_team(account_id=account_id)
    tid = int(team["team_id"]) if team else 0
    rec = _ensure_championship_record(tid, ctype=req["championship_type"], cid=1)
    cinfo = {
        "championship_type": rec["championship_type"],
        "team_info": rec,
        "account_info": {"account_id": account_id, "championship_type": rec["championship_type"], "championship_id": 1},
    }
    handler.send_proto("CSTeamChampionshipInfoRes", encode_cs_team_championship_info_res(tid, [cinfo]))


def _http_get_championship_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_get_championship_req(raw_body)
    team = state.get_team(account_id=account_id)
    tid = int(team["team_id"]) if team else 0
    rec = _ensure_championship_record(tid, ctype=req["championship_type"], cid=req["championship_id"])
    cinfo = {
        "championship_type": rec["championship_type"],
        "team_info": rec,
        "account_info": {
            "account_id": account_id,
            "championship_type": rec["championship_type"],
            "championship_id": rec["championship_id"],
        },
    }
    handler.send_proto("CSTeamChampionshipInfoRes", encode_cs_team_championship_info_res(tid, [cinfo]))


def _http_get_championship_config(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    payload = encode_cs_get_championship_config_res(
        open_info={"championship_type": 1, "championship_id": 1, "map_id": "1"},
        setting_info={"championship_type": 1, "championship_id": 1},
    )
    handler.send_proto("CSGetChampionshipConfigRes", payload)


def _http_get_championship_season_stats(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_team_season_stats_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    tid = int(team["team_id"]) if team else int(req["team_id"])
    member_profiles = (
        [_resolve_profile(int(m["account_id"])) for m in team.get("members", [])]
        if team
        else [_resolve_profile(account_id)]
    )
    payload = encode_cs_team_championship_season_stats_res(
        team_id=tid,
        championship_type=req["championship_type"],
        championship_id=req["championship_id"],
        member_profiles=member_profiles,
        need_members_info=req["need_members_info"],
        team=team,
    )
    handler.send_proto("CSTeamChampionshipSeasonStatsRes", payload)


def _http_get_match_stats_history(handler: Any, raw_body: bytes, _account_id: int) -> None:
    _ = decode_cs_team_match_stats_history_req(raw_body)
    handler.send_proto("CSTeamMatchStatsHistoryRes", encode_cs_team_match_stats_history_res([]))


# ---------------------------------------------------------------------------
# Lobby Squad / Group / Matchmaking HTTP Endpoint Implementations
# ---------------------------------------------------------------------------

def _http_create_group(handler: Any, raw_body: bytes, account_id: int) -> None:
    f = decode_proto(raw_body)
    # Detect whether caller passed CSCreateTeamReq (tag 1 string) or tcp.GroupCreateReq (tags 2..9)
    if 1 in f and isinstance(f[1][0], (bytes, bytearray)) and 4 not in f:
        req = decode_cs_create_team_req(raw_body)
        team = state.create_team(leader_id=account_id, mode="squad", team_name=req["team_name"] or "Barbosa Squad")
        payload = _encode_team_group_info(team)
    else:
        req = decode_group_create_req(raw_body)
        _, payload = _op_create_group(account_id, req)
    handler.send_proto("GroupInfo (Create)", payload)


def _http_get_group_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_id_req(raw_body)
    team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
    handler.send_proto("GroupInfo", _encode_team_group_info(team))


def _http_invite_group(handler: Any, raw_body: bytes, account_id: int) -> None:
    # Works for both tcp.GroupInviteReq (1: invitee_id, 2: invitee_region)
    # and proto.CSInviteToTeamReq (1: invitee_id, 2: team_id).
    f = decode_proto(raw_body)
    invitee_id = get_varint(f, 1, 0)
    team_id = get_varint(f, 2, 0) if (2 in f and isinstance(f[2][0], int)) else 0
    out = _op_invite_to_group(account_id, team_id, invitee_id)
    team = _enrich_team(out["team"]) or out["team"]
    payload = _encode_team_group_info(team)
    if _is_bot_account(invitee_id):
        _push_team_packet(team, EGroupProto.JOIN_NTF, payload)
        _push_team_packet(team, EGroupProto.CHANGE_NTF, payload)
        _push_team_packet(team, EGroupProto.READY_NTF, payload)
    else:
        inv_member = _find_member_or_default(team, account_id)
        inv_prof = _resolve_profile(account_id)
        ntf = encode_group_invite_ntf(int(team["team_id"]), inv_member, inv_prof, team)
        _push_account_packet(invitee_id, EGroupProto.INVITE_NTF, ntf)
    handler.send_proto("GroupInfo (Invite)", payload)


def _http_join_group(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_accept_req(raw_body)
    gid = int(req["group_id"])
    inviter_id = int(req["inviter_account_id"])
    if gid <= 0 and inviter_id > 0:
        inv_team = state.get_team(account_id=inviter_id)
        gid = int(inv_team["team_id"]) if inv_team else 0
    res = state.join_team(gid, player_id=account_id) if gid > 0 else {"team": state.get_team(account_id=account_id)}
    team = res.get("team") or _resolve_target_team(gid, account_id) or _get_or_create_team(account_id)
    enriched = _enrich_team(team) or team
    payload = _encode_team_group_info(enriched)
    _push_team_packet(enriched, EGroupProto.JOIN_NTF, payload)
    _push_team_packet(enriched, EGroupProto.CHANGE_NTF, payload)
    handler.send_proto("GroupInfo (Join)", payload)


def _http_refuse_group(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_id_req(raw_body)
    gid = int(req["group_id"])
    for inv in state.list_team_invitations(account_id=account_id):
        if gid == 0 or int(inv.get("team_id", 0)) == gid:
            state.decline_team_invitation(int(inv["invite_id"]), account_id=account_id)
    handler.send_proto("Empty (RefuseGroupInvite)", b"")


def _http_leave_group(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_id_req(raw_body)
    gid = int(req["group_id"])
    team_before = _resolve_target_team(gid, account_id)
    tid = int(team_before["team_id"]) if team_before else gid
    state.leave_team(player_id=account_id, team_id=tid or None)
    remaining = state.get_team(team_id=tid) if tid > 0 else None
    human_members = [
        m for m in (remaining.get("members", []) if remaining else [])
        if not m.get("is_bot") and int(m.get("account_id", 0)) != account_id
    ]
    if not remaining or not human_members:
        if tid > 0:
            _clear_meta(tid)
            if remaining:
                for m in list(remaining.get("members", [])):
                    state.leave_team(player_id=int(m["account_id"]), team_id=tid)
        state.create_team(leader_id=account_id, mode="solo", max_members=1)
        dismiss_payload = encode_group_dismiss_ntf(account_id, tid, EGroupLeaveReason.NORMAL)
        _push_account_packet(account_id, EGroupProto.DISMISS_NTF, dismiss_payload)
        handler.send_proto("GroupDismissNtf", dismiss_payload)
        return
    enriched = _enrich_team(remaining) or remaining
    profiles, pets = _build_team_profiles(enriched)
    leave_payload = encode_group_leave_ntf(
        account_id,
        EGroupLeaveReason.NORMAL,
        enriched,
        profiles,
        pet_lookup=pets,
    )
    _push_team_packet(enriched, EGroupProto.LEAVE_NTF, leave_payload)
    handler.send_proto("GroupLeaveNtf", leave_payload)


def _http_kick_group_member(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_remove_member_req(raw_body)
    team = _resolve_target_team(req["team_id"], account_id)
    target_id = int(req["removee_id"])
    # Support callers passing only target_id in field 1 when team_id is omitted
    if target_id <= 0 and req["team_id"] > 0 and (not team or int(team["team_id"]) != int(req["team_id"])):
        target_id = int(req["team_id"])
        team = state.get_team(account_id=account_id)
    if team and target_id > 0:
        res = state.kick_player(int(team["team_id"]), target_id, requester_id=account_id)
        team = res.get("team") or state.get_team(team_id=int(team["team_id"])) or team
        enriched = _enrich_team(team) or team
        profiles, pets = _build_team_profiles(enriched)
        leave_ntf = encode_group_leave_ntf(target_id, EGroupLeaveReason.NORMAL, enriched, profiles, pet_lookup=pets)
        _push_team_packet(enriched, EGroupProto.LEAVE_NTF, leave_ntf)
        _push_team_packet(enriched, EGroupProto.CHANGE_NTF, _encode_team_group_info(enriched))
        dismiss_ntf = encode_group_dismiss_ntf(target_id, int(team["team_id"]), EGroupLeaveReason.NORMAL)
        _push_account_packet(target_id, EGroupProto.DISMISS_NTF, dismiss_ntf)
    team = team or _get_or_create_team(account_id)
    handler.send_proto("GroupInfo (Kick)", _encode_team_group_info(team))


def _http_team_ready(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_ready_req(raw_body)
    team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
    updated = state.set_team_ready(int(team["team_id"]), player_id=account_id, ready=req["ready"])
    enriched = _enrich_team(updated or team) or (updated or team)
    payload = _encode_team_group_info(enriched)
    _push_team_packet(enriched, EGroupProto.READY_NTF, payload)
    _push_team_packet(enriched, EGroupProto.READY, payload)
    handler.send_proto("GroupInfo (Ready)", payload)


def _http_change_group_mode(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_change_req(raw_body)
    updated = _op_change_group(account_id, req) or _get_or_create_team(account_id)
    enriched = _enrich_team(updated) or updated
    payload = _encode_team_group_info(enriched)
    _push_team_packet(enriched, EGroupProto.CHANGE_NTF, payload)
    handler.send_proto("GroupInfo (ChangeMode)", payload)


def _http_start_matchmaking(handler: Any, raw_body: bytes, account_id: int) -> None:
    f = decode_proto(raw_body)
    # MatchmakingGroupStartReq has tag 2 = group_id, tag 3 = group_mode, tag 6 = game_mode, tag 12 = match_mode
    if 2 in f and 3 in f:
        req = decode_matchmaking_group_start_req(raw_body)
        _, payload = _op_start_matchmaking(
            account_id,
            team_id=req["group_id"],
            game_mode=req["game_mode"] or None,
            map_ids=req["map_ids"] or None,
            match_mode=req["match_mode"] or None,
            difficulty=req["difficulty"],
        )
    elif (1 in f and isinstance(f[1][0], (bytes, bytearray))) or 8 in f or (2 in f and 1 not in f):
        req = decode_matchmaking_start_req(raw_body)
        _, payload = _op_start_matchmaking(
            account_id,
            game_mode=req["game_mode"] or None,
            map_ids=req["map_ids"] or None,
            match_mode=req["match_mode"] or None,
            difficulty=req["difficulty"],
        )
    else:
        req = decode_group_id_req(raw_body)
        _, payload = _op_start_matchmaking(account_id, team_id=req["group_id"])
    handler.send_proto("MatchmakingSussNtf", payload)


def _http_stop_matchmaking(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_id_req(raw_body)
    team = _resolve_target_team(req["group_id"], account_id)
    tid = int(team["team_id"]) if team else None
    cancelled = state.cancel_matchmaking(team_id=tid, account_id=account_id)
    final_team = cancelled or team
    if not final_team:
        handler.send_proto("Empty (CancelMatchMaking)", b"")
        return
    enriched = _enrich_team(final_team) or final_team
    profiles, pets = _build_team_profiles(enriched)
    stopper = _find_member_or_default(enriched, account_id)
    stopper_prof = profiles.get(account_id) or _resolve_profile(account_id)
    handler.send_proto(
        "GroupStopNtf",
        encode_group_stop_ntf(stopper, stopper_prof, enriched, profiles, pet_lookup=pets),
    )


def _http_get_matchmaking_status(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_group_id_req(raw_body)
    team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
    enriched = _enrich_team(team) or team
    status = str(enriched.get("matchmaking_status", "idle")).lower()
    if bool(enriched.get("matchmaking")) or status in ("searching", "matched", "in_match"):
        handler.send_proto("MatchmakingSussNtf (Status)", _build_matchmaking_suss_ntf(enriched))
        return
    handler.send_proto("GroupInfo (MatchmakingStatus)", _encode_team_group_info(enriched))


def _http_group_packet(handler: Any, raw_body: bytes, account_id: int) -> None:
    """Handle an HTTP-tunneled `tcp.ProtoReq` for `EProtocol.Proto.GROUP (5)`."""
    preq = decode_proto_req(raw_body)
    notify = handle_tcp_proto_req(EProtocolProto.GROUP, preq["cmd"], preq["data"], account_id=account_id)
    handler.send_proto(f"MessageNotify (GROUP cmd={preq['cmd']})", notify)


# ---------------------------------------------------------------------------
# TCP Lobby Packet Dispatch (`EProtocol.Proto.GROUP` & `MATCHMAKING`)
# ---------------------------------------------------------------------------

def handle_group_tcp_command(
    protocol: int,
    cmd: int,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> Tuple[int, int, bytes]:
    """
    Dispatch a Free Fire 1.39 TCP Lobby command for `GROUP` (5) or `MATCHMAKING` (3).
    Returns `(response_cmd, ret_code, encoded_protobuf_payload)`.
    """
    if protocol == EProtocolProto.MATCHMAKING:
        if cmd == EMatchmakingProto.START:
            req = decode_matchmaking_start_req(raw_body)
            _op_start_matchmaking(
                account_id,
                game_mode=req["game_mode"] or None,
                map_ids=req["map_ids"] or None,
                match_mode=req["match_mode"] or None,
                difficulty=req["difficulty"],
            )
            return EMatchmakingProto.START, 0, b""
        if cmd == EMatchmakingProto.GROUPSTART:
            req = decode_matchmaking_group_start_req(raw_body)
            _op_start_matchmaking(
                account_id,
                team_id=req["group_id"],
                game_mode=req["game_mode"] or None,
                map_ids=req["map_ids"] or None,
                match_mode=req["match_mode"] or None,
                difficulty=req["difficulty"],
            )
            return EMatchmakingProto.GROUPSTART, 0, b""
        if cmd in (EMatchmakingProto.CANCEL, EMatchmakingProto.GROUPCANCEL, EMatchmakingProto.DROPMATCH):
            req = decode_group_id_req(raw_body)
            state.cancel_matchmaking(team_id=req["group_id"] or None, account_id=account_id)
            return cmd, 0, b""
        return cmd, 0, b""

    if protocol != EProtocolProto.GROUP:
        return cmd, 1, b""

    if cmd == EGroupProto.CREATE:
        req = decode_group_create_req(raw_body)
        team, payload = _op_create_group(account_id, req)
        _push_team_packet(team, EGroupProto.CREATE, payload)
        return EGroupProto.CREATE, 0, payload

    if cmd == EGroupProto.INVITE:
        req = decode_group_invite_req(raw_body)
        invitee_id = int(req.get("invitee_id", 0))
        out = _op_invite_to_group(account_id, 0, invitee_id)
        team = _enrich_team(out["team"]) or out["team"]
        payload = _encode_team_group_info(team)
        if _is_bot_account(invitee_id):
            # Bot accepted & joined immediately -> return JOIN_NTF with updated GroupInfo
            # Push JOIN_NTF (cmd 6), CHANGE_NTF (cmd 18), and READY_NTF (cmd 16) to team
            _push_team_packet(team, EGroupProto.JOIN_NTF, payload)
            _push_team_packet(team, EGroupProto.CHANGE_NTF, payload)
            _push_team_packet(team, EGroupProto.READY_NTF, payload)
            return EGroupProto.JOIN_NTF, 0, payload
        inv_member = _find_member_or_default(team, account_id)
        inv_prof = _resolve_profile(account_id)
        ntf = encode_group_invite_ntf(int(team["team_id"]), inv_member, inv_prof, team)
        _push_account_packet(invitee_id, EGroupProto.INVITE_NTF, ntf)
        return EGroupProto.INVITE_NTF, 0, ntf

    if cmd == EGroupProto.ACCEPT:
        req = decode_group_accept_req(raw_body)
        gid = int(req["group_id"])
        if gid <= 0 and req["inviter_account_id"] > 0:
            inv_team = state.get_team(account_id=int(req["inviter_account_id"]))
            gid = int(inv_team["team_id"]) if inv_team else 0
        res = state.join_team(gid, player_id=account_id) if gid > 0 else {}
        team = res.get("team") or _resolve_target_team(gid, account_id) or _get_or_create_team(account_id)
        enriched = _enrich_team(team) or team
        payload = _encode_team_group_info(enriched)
        _push_team_packet(enriched, EGroupProto.JOIN_NTF, payload)
        _push_team_packet(enriched, EGroupProto.CHANGE_NTF, payload)
        return EGroupProto.JOIN_NTF, 0, payload

    if cmd == EGroupProto.REFUSE:
        req = decode_group_id_req(raw_body)
        for inv in state.list_team_invitations(account_id=account_id):
            if req["group_id"] == 0 or int(inv.get("team_id", 0)) == req["group_id"]:
                state.decline_team_invitation(int(inv["invite_id"]), account_id=account_id)
        return EGroupProto.REFUSE, 0, b""

    if cmd == EGroupProto.LEAVE:
        f = decode_proto(raw_body)
        param_id = get_varint(f, 1, 0) if 1 in f else 0
        target_id = get_varint(f, 2, 0) if 2 in f else 0

        team_before = state.get_team(account_id=account_id)
        if not team_before and param_id > 0:
            team_before = state.get_team(team_id=param_id)
        tid = int(team_before["team_id"]) if team_before else param_id

        # Determine if this is a kick or a self-leave
        members = list(team_before.get("members", [])) if team_before else []
        member_ids = [int(m.get("account_id", 0)) for m in members]
        is_leader = (team_before and int(team_before.get("leader_id", 0)) == int(account_id))

        kicked_id = 0
        if is_leader and target_id > 0 and target_id in member_ids and target_id != account_id:
            kicked_id = target_id
        elif is_leader and param_id > 0 and param_id in member_ids and param_id != account_id:
            kicked_id = param_id

        if kicked_id > 0:
            # Kick member flow
            state.kick_player(tid, kicked_id, requester_id=account_id)
            remaining_team = state.get_team(team_id=tid)
            if remaining_team:
                enriched = _enrich_team(remaining_team) or remaining_team
                profiles, pets = _build_team_profiles(enriched)
                leave_ntf = encode_group_leave_ntf(
                    kicked_id,
                    EGroupLeaveReason.NORMAL,
                    enriched,
                    profiles,
                    pet_lookup=pets,
                )
                _push_team_packet(enriched, EGroupProto.LEAVE_NTF, leave_ntf)
                _push_team_packet(enriched, EGroupProto.CHANGE_NTF, _encode_team_group_info(enriched))
                dismiss_ntf = encode_group_dismiss_ntf(kicked_id, tid, EGroupLeaveReason.NORMAL)
                _push_account_packet(kicked_id, EGroupProto.DISMISS_NTF, dismiss_ntf)
                return EGroupProto.LEAVE_NTF, 0, leave_ntf

        # Self-leave / Quit to Solo flow
        state.leave_team(player_id=account_id, team_id=tid or None)
        remaining = state.get_team(team_id=tid) if tid > 0 else None

        human_members = [
            m for m in (remaining.get("members", []) if remaining else [])
            if not m.get("is_bot") and int(m.get("account_id", 0)) != account_id
        ]

        if not remaining or not human_members:
            if tid > 0:
                _clear_meta(tid)
                if remaining:
                    for m in list(remaining.get("members", [])):
                        state.leave_team(player_id=int(m["account_id"]), team_id=tid)
            state.create_team(leader_id=account_id, mode="solo", max_members=1)
            dismiss_payload = encode_group_dismiss_ntf(account_id, tid, EGroupLeaveReason.NORMAL)
            _push_account_packet(account_id, EGroupProto.DISMISS_NTF, dismiss_payload)
            return EGroupProto.DISMISS_NTF, 0, dismiss_payload

        enriched = _enrich_team(remaining) or remaining
        profiles, pets = _build_team_profiles(enriched)
        leave_payload = encode_group_leave_ntf(
            account_id,
            EGroupLeaveReason.NORMAL,
            enriched,
            profiles,
            pet_lookup=pets,
        )
        _push_team_packet(enriched, EGroupProto.LEAVE_NTF, leave_payload)
        return EGroupProto.LEAVE_NTF, 0, leave_payload

    if cmd == EGroupProto.START:
        req = decode_group_id_req(raw_body)
        team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
        mm_res = state.start_matchmaking(team_id=int(team["team_id"]), account_id=account_id)
        enriched = _enrich_team(mm_res.get("team") or team) or (mm_res.get("team") or team)
        payload = _encode_team_group_info(enriched)
        _push_team_packet(enriched, EGroupProto.START_NTF, payload)
        return EGroupProto.START_NTF, 0, payload

    if cmd == EGroupProto.STOP:
        req = decode_group_id_req(raw_body)
        team = _resolve_target_team(req["group_id"], account_id)
        tid = int(team["team_id"]) if team else None
        cancelled = state.cancel_matchmaking(team_id=tid, account_id=account_id) or team
        if not cancelled:
            return EGroupProto.STOP_NTF, 0, b""
        enriched = _enrich_team(cancelled) or cancelled
        profiles, pets = _build_team_profiles(enriched)
        stopper = _find_member_or_default(enriched, account_id)
        payload = encode_group_stop_ntf(
            stopper,
            profiles.get(account_id) or _resolve_profile(account_id),
            enriched,
            profiles,
            pet_lookup=pets,
        )
        _push_team_packet(enriched, EGroupProto.STOP_NTF, payload)
        return EGroupProto.STOP_NTF, 0, payload

    if cmd == EGroupProto.GROUPINFO:
        req = decode_group_id_req(raw_body)
        team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
        enriched = _enrich_team(team) or team
        payload = _encode_team_group_info(enriched)
        return EGroupProto.GROUPINFO, 0, payload

    if cmd == EGroupProto.READY:
        req = decode_group_ready_req(raw_body)
        team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
        updated = state.set_team_ready(int(team["team_id"]), player_id=account_id, ready=req["ready"])
        enriched = _enrich_team(updated or team) or (updated or team)
        payload = _encode_team_group_info(enriched)
        _push_team_packet(enriched, EGroupProto.READY_NTF, payload)
        _push_team_packet(enriched, EGroupProto.READY, payload)
        return EGroupProto.READY_NTF, 0, payload

    if cmd == EGroupProto.CHANGE:
        req = decode_group_change_req(raw_body)
        updated = _op_change_group(account_id, req) or _get_or_create_team(account_id)
        enriched = _enrich_team(updated) or updated
        payload = _encode_team_group_info(enriched)
        _push_team_packet(enriched, EGroupProto.CHANGE_NTF, payload)
        return EGroupProto.CHANGE_NTF, 0, payload

    if cmd == EGroupProto.SHOWEMOTE:
        req = decode_show_emote_req(raw_body)
        team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
        emote_id = int(req.get("emote_id") or 0)
        ntf_payload = encode_show_emote_ntf(account_id, emote_id)
        _push_team_packet(team, EGroupProto.SHOWEMOTE_NTF, ntf_payload)
        return EGroupProto.SHOWEMOTE_NTF, 0, ntf_payload

    if cmd == EGroupProto.SHOWPETACTION:
        req = decode_show_pet_action_req(raw_body)
        team = _resolve_target_team(req["group_id"], account_id) or _get_or_create_team(account_id)
        action_id = int(req.get("action_id") or 0)
        ntf_payload = encode_show_pet_action_ntf(account_id, action_id)
        _push_team_packet(team, EGroupProto.SHOWPETACTION_NTF, ntf_payload)
        return EGroupProto.SHOWPETACTION_NTF, 0, ntf_payload

    return cmd, 0, b""


def broadcast_group_change(account_id: int) -> None:
    """Broadcast updated group info to all members after profile or collection changes."""
    team = state.get_team(account_id=account_id) or _get_or_create_team(account_id)
    if team:
        enriched = _enrich_team(team) or team
        payload = _encode_team_group_info(enriched)
        _push_team_packet(enriched, EGroupProto.CHANGE_NTF, payload)


def trigger_team_show_emote(account_id: int, emote_id: int) -> None:
    """Trigger real-time emote playback on 3D character in lobby squad."""
    team = state.get_team(account_id=account_id) or _get_or_create_team(account_id)
    if team:
        ntf_payload = encode_show_emote_ntf(account_id, emote_id)
        _push_team_packet(team, EGroupProto.SHOWEMOTE_NTF, ntf_payload)


def handle_tcp_proto_req(
    protocol: int,
    cmd: int,
    payload: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bytes:
    """Execute a TCP lobby command and wrap the response as `tcp.MessageNotify`."""
    resp_cmd, ret, resp_bytes = handle_group_tcp_command(protocol, cmd, payload, account_id=account_id)
    return encode_message_notify(account_id, protocol, ret, resp_cmd, resp_bytes)


# ---------------------------------------------------------------------------
# HTTP Dispatch Table & Entrypoint
# ---------------------------------------------------------------------------

_TEAM_ROUTES: Dict[str, Callable[[Any, bytes, int], None]] = {
    # Championship Team (`ServiceMessageTypeHTTP`)
    "CreateTeam": _http_create_team,
    "RequestJoinTeam": _http_request_join_team,
    "ModifyTeamInfo": _http_modify_team_info,
    "AddTeamContactInfo": _http_add_team_contact_info,
    "GetTeamInfoByTeamID": _http_get_team_info,
    "GetTeamMembers": _http_get_team_members,
    "QuitTeam": _http_quit_team,
    "DismissTeam": _http_dismiss_team,
    "GetTeamApplicantListByTeamID": _http_get_team_applicant_list,
    "ApproveJoinTeamApplication": _http_approve_join_application,
    "DeclineJoinTeamApplication": _http_decline_join_application,
    "InviteToTeam": _http_invite_to_team,
    "ApproveJoinTeamInvitation": _http_approve_join_invitation,
    "DeclineJoinTeamInvitation": _http_decline_join_invitation,
    "GetTeamInvitationList": _http_get_team_invitation_list,
    "FuzzySearchTeamByName": _http_fuzzy_search_team,
    "RemoveTeamMember": _http_remove_team_member,
    "InitTeamChampionshipInfo": _http_init_championship_info,
    "GetTeamChampionshipInfo": _http_get_championship_info,
    "GetChampionshipConfig": _http_get_championship_config,
    "GetTeamChampionshipSeasonStats": _http_get_championship_season_stats,
    "GetTeamMatchStatsHistory": _http_get_match_stats_history,
    # Lobby Squad / Group & Matchmaking HTTP Endpoints
    "CreateGroup": _http_create_group,
    "CreateSquad": _http_create_group,
    "GetGroupInfo": _http_get_group_info,
    "GetTeamStatus": _http_get_group_info,
    "InviteGroup": _http_invite_group,
    "InviteTeamMember": _http_invite_group,
    "JoinGroup": _http_join_group,
    "AcceptGroupInvite": _http_join_group,
    "RefuseGroupInvite": _http_refuse_group,
    "LeaveGroup": _http_leave_group,
    "KickTeamMember": _http_kick_group_member,
    "KickGroupMember": _http_kick_group_member,
    "TeamReady": _http_team_ready,
    "GroupReady": _http_team_ready,
    "ChangeGroupMode": _http_change_group_mode,
    "SetTeamMode": _http_change_group_mode,
    "StartGroupMatch": _http_start_matchmaking,
    "StartMatchMaking": _http_start_matchmaking,
    "StopGroupMatch": _http_stop_matchmaking,
    "CancelMatchMaking": _http_stop_matchmaking,
    "GetMatchmakingStatus": _http_get_matchmaking_status,
    "GroupPacket": _http_group_packet,
}


def handle_team_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Team/Squad/Matchmaking HTTP POST endpoints.
    Returns True if the endpoint was handled, False otherwise.
    """
    _ = client_ip
    endpoint = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    fn = _TEAM_ROUTES.get(endpoint)
    if fn is None:
        return False
    fn(handler, raw_body or b"", account_id)
    return True


handle_team_post = handle_team_request
