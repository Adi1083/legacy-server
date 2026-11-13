"""
HTTP POST handlers for Free Fire 1.39 Player Profile, Stats, Personal Show,
Ranking Info, and Account Customization endpoints.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.profile_models import (
    DEFAULT_SEASON_ID,
    decode_account_id_req,
    decode_account_life_season_stats_req,
    decode_choose_banner_req,
    decode_choose_head_pic_req,
    decode_fuzzy_search_account_req,
    decode_get_player_stats_req,
    decode_modify_nickname_req,
    decode_player_ranking_info_req,
    decode_set_show_rank_req,
    encode_account_info_basic,
    encode_account_info_basic_bundle_res,
    encode_account_life_season_stats_res,
    encode_account_personal_show_info,
    encode_empty,
    encode_get_match_stats_list_res,
    encode_get_player_stats_res,
    encode_modify_nickname_res,
    encode_player_ranking_info_res,
)


def _resolve_target_account_id(parsed_id: int, fallback_id: int = DEFAULT_ACCOUNT_ID) -> int:
    return int(parsed_id) if parsed_id and int(parsed_id) > 0 else int(fallback_id)


def _build_enriched_profile(account_id: int) -> Dict[str, Any]:
    """Load profile from ServerState and enrich avatar clothes/skills if needed."""
    prof = state.get_profile(account_id)
    avatar_id = int(prof.get("avatar_id", 102000004))
    if avatar_id < 100000000:
        avatar_id = 102000004
        prof["avatar_id"] = avatar_id
    char = state.get_character(avatar_id)
    if char:
        if not prof.get("clothes"):
            prof["clothes"] = list(char.get("clothes") or [])
        if not prof.get("equiped_skills"):
            prof["equiped_skills"] = list(char.get("equiped_skills") or [])
        prof.setdefault("unlocked_level", int(char.get("unlocked_level", 8)))
        if not prof.get("pve_primary_weapon") and char.get("pve_primary_weapon"):
            prof["pve_primary_weapon"] = int(char["pve_primary_weapon"])
    if not prof.get("clothes"):
        prof["clothes"] = [211000000, 208000000, 203000573, 204000345, 205000299]
    return prof


def _build_pet_info(prof: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pet_id = int(prof.get("selected_pet_id", 0))
    if pet_id <= 0:
        return None
    pet = state.get_pet(pet_id)
    if pet:
        resolved_id = int(pet.get("id", pet.get("pet_id", pet_id)))
        skills = list(pet.get("skills") or [])
        if not skills and int(pet.get("skill_id", 0)) > 0:
            skills = [
                {
                    "pet_id": resolved_id,
                    "skill_id": int(pet["skill_id"]),
                    "skill_level": int(pet.get("skill_level", 3)),
                }
            ]
        return {
            "id": resolved_id,
            "name": str(pet.get("name", "Kitty")),
            "level": int(pet.get("level", 7)),
            "exp": int(pet.get("exp", 0)),
            "is_selected": True,
            "skin_id": int(prof.get("selected_pet_skin_id") or pet.get("skin_id", 0)),
            "actions": list(pet.get("actions") or [1, 2, 3, 4]),
            "skills": skills,
        }
    return {
        "id": pet_id,
        "name": "Kitty",
        "level": 7,
        "exp": 0,
        "is_selected": True,
        "skin_id": int(prof.get("selected_pet_skin_id", 0)),
        "actions": [],
        "skills": [],
    }


def _build_mode_stats(account_id: int, level: int, match_mode: int, group_scale: float) -> Dict[str, Any]:
    """Build consistent mode/group stats + DetailStats JSON from account profile."""
    seed = (account_id % 97) + (match_mode * 7)
    games = max(10, int((level * 3 + seed) * group_scale))
    wins = max(3, int(games * 0.28))
    kills = max(wins * 2, int(games * 3.4))
    deaths = max(1, games - wins)
    headshot_kills = max(1, int(kills * 0.34))
    headshots = headshot_kills + int(kills * 0.25)
    return {
        "account_id": account_id,
        "games_played": games,
        "wins": wins,
        "kills": kills,
        "detailed_stats": {
            "deaths": deaths,
            "top10_times": max(wins, int(games * 0.55)),
            "top_n_times": max(wins, int(games * 0.62)),
            "distance_travelled": games * 3150,
            "survival_time": games * 780,
            "revives": max(0, int(games * 0.45)),
            "highest_kills": min(28, 7 + (account_id % 11)),
            "damage": kills * 420,
            "road_kills": max(0, int(kills * 0.04)),
            "headshots": headshots,
            "headshot_kills": headshot_kills,
            "knock_down": int(kills * 1.15),
            "pick_ups": games * 26,
        },
    }


def _build_match_history(account_id: int, prof: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build recent MatchAccountStats entries for GetMatchStatsHistory."""
    now = int(time.time())
    teammates_raw = [
        p for p in (state.get_player(20001), state.get_player(20002), state.get_player(20003)) if p
    ]

    def _to_teammate(p: Dict[str, Any], kills: int, dmg: int) -> Dict[str, Any]:
        return {
            "account_id": int(p["account_id"]),
            "nickname": str(p["nickname"]),
            "kills": kills,
            "avatar_id": (int(p.get("avatar_id", 102000004)) if int(p.get("avatar_id", 102000004)) >= 100000000 else 102000004),
            "banner_id": int(p.get("banner_id", 901000001)),
            "head_pic": int(p.get("head_pic", 902000001)),
            "clan_name": str(p.get("clan_name", "")),
            "season_rank": int(p.get("rank", 310)),
            "level": int(p.get("level", 50)),
            "has_elite_pass": bool(p.get("has_elite_pass", True)),
            "badge_id": 1,
            "badge_cnt": int(p.get("badge_cnt", 50)),
            "is_friend": True,
            "show_rank": True,
            "role": 0,
            "damage": dmg,
        }

    templates = [
        # (offset_sec, rank, kills, dmg, group_mode, match_mode, game_mode, map_id, player_count, tm_count, rp_delta)
        (1800, 1, 11, 4180, 3, 2, 1, 1, 48, 3, 38),
        (5400, 2, 7, 2690, 1, 2, 1, 2, 50, 1, 21),
        (10800, 1, 9, 3420, 0, 1, 1, 1, 50, 0, 0),
        (19200, 3, 6, 2150, 3, 2, 1, 1, 48, 3, 14),
    ]

    matches: List[Dict[str, Any]] = []
    for idx, (offset, rank, kills, dmg, gmode, mmode, gamemode, map_id, pcount, tm_cnt, rp_delta) in enumerate(
        templates, start=1
    ):
        end_time = now - offset
        create_time = end_time - 960
        tms = [
            _to_teammate(p, max(2, kills - i - 1), max(650, dmg - (i + 1) * 450))
            for i, p in enumerate(teammates_raw[:tm_cnt])
        ]
        matches.append({
            "match_id": account_id * 1000 + idx,
            "account_id": account_id,
            "create_time": create_time,
            "end_time": end_time,
            "income": {
                "exp": 320 + kills * 25,
                "coins": 180 + kills * 15,
                "rank_points": max(0, rp_delta),
                "kill_points": kills * 5,
                "damage_points": dmg // 200,
                "level_before": int(prof.get("level", 60)),
                "level_after": int(prof.get("level", 60)),
                "ranking_points_delta": rp_delta,
                "ranking_points_before": max(0, int(prof.get("ranking_points", 3250)) - rp_delta),
                "ranking_points_after": int(prof.get("ranking_points", 3250)),
                "rank_before": int(prof.get("rank", 315)),
                "rank_after": int(prof.get("rank", 315)),
                "is_rank": mmode == 2,
            },
            "stats": {
                "account_id": account_id,
                "group_id": idx,
                "survival_time": 960 if rank == 1 else 780,
                "rank": rank,
                "kills": kills,
                "damage": dmg,
                "moving_distance": 3400,
                "revival_count": 2 if gmode > 0 else 0,
                "headshot_count": kills + 2,
                "headshot_kills": max(1, kills // 3),
                "knockdown_count": kills + 1,
                "pickup_count": 24,
                "assists": 2 if gmode > 0 else 0,
                "is_survive": rank == 1,
                "ranking_points": rp_delta,
                "achievements": [1, 2] if rank == 1 else [2],
                "enable_achievements": True,
                "avatar_id": (int(prof.get("avatar_id", 102000004)) if int(prof.get("avatar_id", 102000004)) >= 100000000 else 102000004),
                "teammates": tms,
                "group_mode": gmode,
                "match_mode": mmode,
                "player_count": pcount,
                "banner_id": int(prof.get("banner_id", 901000001)),
                "head_pic": int(prof.get("head_pic", 902000001)),
                "clan_name": str(prof.get("clan_name", "")),
                "level": int(prof.get("level", 60)),
                "season_rank": int(prof.get("rank", 315)),
                "game_mode": gamemode,
                "map_id": map_id,
                "has_elite_pass": bool(prof.get("has_elite_pass", True)),
                "badge_id": int(prof.get("ep_badge", 1)),
                "badge_cnt": int(prof.get("badge_cnt", 100)),
                "clothes_id": list(prof.get("clothes") or []),
                "liked": int(prof.get("liked", 9999)),
                "show_rank": bool(prof.get("show_rank", True)),
                "pet_id": int(prof.get("selected_pet_id", 0)),
                "pet_skin_id": int(prof.get("selected_pet_skin_id", 0)),
                "role": int(prof.get("role", 0)),
            },
        })
    return matches


# ---------------------------------------------------------------------------
# Endpoint Handlers
# ---------------------------------------------------------------------------

def _handle_get_player_personal_show(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    target_id = _resolve_target_account_id(decode_account_id_req(raw_body), default_account_id)
    prof = _build_enriched_profile(target_id)
    now = int(time.time())

    clan_id = int(prof.get("clan_id", 0))
    clan_name = str(prof.get("clan_name", ""))
    clan_basic = None
    captain_basic = None
    if clan_id > 0:
        clan_basic = {
            "clan_id": clan_id,
            "clan_name": clan_name or "INDIA V1",
            "captain_id": target_id,
            "clan_level": 4,
            "capacity": 35,
            "member_num": 12,
            "honor_point": 50000,
        }
        captain_basic = prof

    news = [
        {
            "type": 1,  # EAccount.NewsType.RANK
            "content": {"rank": int(prof.get("rank", 315)), "match_mode": 2},
            "update_time": now - 3600,
        },
        {
            "type": 5,  # EAccount.NewsType.ELITEPASS
            "content": {},
            "update_time": now - 86400,
        },
    ]
    history_ep = [
        {
            "ep_event_id": int(prof.get("ep_event_id", 1)),
            "owned_pass": bool(prof.get("has_elite_pass", True)),
            "ep_badge": int(prof.get("ep_badge", 1)),
            "badge_cnt": int(prof.get("badge_cnt", 100)),
        }
    ]
    payload = encode_account_personal_show_info(
        prof,
        ranking_leaderboard_pos=1 if target_id == DEFAULT_ACCOUNT_ID else max(2, target_id % 100),
        news=news,
        history_ep_info=history_ep,
        clan_basic_info=clan_basic,
        captain_basic_info=captain_basic,
        pet_info=_build_pet_info(prof),
    )
    handler.send_proto("AccountPersonalShowInfo", payload)


def _handle_get_account_info_by_id(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    target_id = _resolve_target_account_id(decode_account_id_req(raw_body), default_account_id)
    prof = _build_enriched_profile(target_id)
    handler.send_proto("AccountInfoBasic", encode_account_info_basic(prof))


def _handle_fuzzy_search_account(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    query = decode_fuzzy_search_account_req(raw_body)
    matches = state.search_players(query)
    if not matches and query:
        prof = _build_enriched_profile(default_account_id)
        if query.lower() in str(prof.get("nickname", "")).lower():
            matches = [prof]
    handler.send_proto("AccountInfoBasicBundleRes", encode_account_info_basic_bundle_res(matches))


def _handle_get_player_stats(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    parsed_id, match_mode = decode_get_player_stats_req(raw_body)
    target_id = _resolve_target_account_id(parsed_id, default_account_id)
    prof = state.get_profile(target_id)
    level = int(prof.get("level", 60))

    solo = _build_mode_stats(target_id, level, match_mode, 1.0)
    duo = _build_mode_stats(target_id, level, match_mode, 0.7)
    quad = _build_mode_stats(target_id, level, match_mode, 1.35)
    handler.send_proto(
        "CSGetPlayerStatsRes",
        encode_get_player_stats_res(target_id, solo, duo, quad),
    )


def _handle_get_match_stats_history(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    target_id = _resolve_target_account_id(decode_account_id_req(raw_body), default_account_id)
    prof = _build_enriched_profile(target_id)
    matches = _build_match_history(target_id, prof)
    handler.send_proto("CSGetMatchStatsListRes", encode_get_match_stats_list_res(matches))


def _handle_get_account_life_season_stats(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    parsed_id, champ_type = decode_account_life_season_stats_req(raw_body)
    target_id = _resolve_target_account_id(parsed_id, default_account_id)
    prof = state.get_profile(target_id)
    points = int(prof.get("ranking_points", 3250))

    stats_list = [
        {
            "account_id": target_id,
            "championship_type": champ_type,
            "championship_id": 1001 + i,
            "score": max(100, points - i * 150),
            "pos": i + 1,
        }
        for i in range(3)
    ]
    handler.send_proto(
        "CSAccountLifeSeasonStats",
        encode_account_life_season_stats_res(target_id, champ_type, stats_list),
    )


def _handle_get_player_ranking_info(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    season_id = decode_player_ranking_info_req(raw_body) or DEFAULT_SEASON_ID
    prof = state.get_profile(default_account_id)
    rank = int(prof.get("rank", 315))
    max_rank = int(prof.get("max_rank", max(rank, 315)))
    points = int(prof.get("ranking_points", 3250))
    show_rank = bool(prof.get("show_rank", True))

    payload = encode_player_ranking_info_res(
        account_id=int(prof.get("account_id", default_account_id)),
        season_id=season_id,
        rank=rank,
        max_rank=max_rank,
        ranking_points=points,
        show_rank=show_rank,
        last_season_info={
            "season_id": max(1, season_id - 1),
            "rank": rank,
            "max_rank": max_rank,
            "ranking_points": max(1000, points - 100),
        },
        match_token_num=int(prof.get("match_token_num", 500)),
    )
    handler.send_proto("CSPlayerRankingInfoRes", payload)


def _sync_profile_field(account_id: int, **updates: Any) -> Dict[str, Any]:
    prof = state.update_profile(account_id, **updates)
    if account_id != DEFAULT_ACCOUNT_ID and state.get_player(account_id) is not None:
        state.upsert_player(account_id, **updates)
    return prof


def _handle_change_nickname(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    new_nick, _use_card = decode_modify_nickname_req(raw_body)
    cleaned = new_nick.strip()[:32]
    if cleaned:
        prof = _sync_profile_field(default_account_id, nickname=cleaned)
        final_nick = str(prof.get("nickname", cleaned))
    else:
        final_nick = str(state.get_profile(default_account_id).get("nickname", "Clack"))
    handler.send_proto("CSModifyNicknameRes", encode_modify_nickname_res(final_nick))


def _handle_change_banner(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    banner_id = decode_choose_banner_req(raw_body)
    if banner_id > 0:
        _sync_profile_field(default_account_id, banner_id=banner_id)
    handler.send_proto("Empty", encode_empty())


def _handle_change_avatar_icon(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    head_pic = decode_choose_head_pic_req(raw_body)
    if head_pic > 0:
        _sync_profile_field(default_account_id, head_pic=head_pic)
    handler.send_proto("Empty", encode_empty())


def _handle_set_show_rank(
    handler: Any, raw_body: bytes, default_account_id: int
) -> None:
    show_rank = decode_set_show_rank_req(raw_body)
    _sync_profile_field(default_account_id, show_rank=show_rank)
    handler.send_proto("Empty", encode_empty())


_ROUTE_MAP: Dict[str, Callable[[Any, bytes, int], None]] = {
    "/GetPlayerPersonalShow": _handle_get_player_personal_show,
    "/GetAccountInfoByAccountID": _handle_get_account_info_by_id,
    "/FuzzySearchAccountByName": _handle_fuzzy_search_account,
    "/GetPlayerStats": _handle_get_player_stats,
    "/GetMatchStatsHistory": _handle_get_match_stats_history,
    "/GetAccountLifeSeasonStats": _handle_get_account_life_season_stats,
    "/GetPlayerRankingInfo": _handle_get_player_ranking_info,
    "/ChangeNickname": _handle_change_nickname,
    "/MajorModifyNickname": _handle_change_nickname,
    "/ChangeBanner": _handle_change_banner,
    "/ChooseBanner": _handle_change_banner,
    "/ChangeAvatarIcon": _handle_change_avatar_icon,
    "/ChooseHeadPic": _handle_change_avatar_icon,
    "/SetShowRank": _handle_set_show_rank,
}


def handle_profile_request(
    handler: Any,
    path: str,
    client_ip: str = "",
    raw_body: bytes = b"",
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """Dispatch profile/stats/customization HTTP POST requests. Returns True if handled."""
    fn = _ROUTE_MAP.get(path)
    if fn is None:
        return False
    fn(handler, raw_body, account_id)
    return True


handle_profile_post = handle_profile_request
