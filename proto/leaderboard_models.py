"""Protobuf schemas, request decoders, and response builders for Free Fire 1.39 leaderboards & rankings."""

from __future__ import annotations

import json
import time
from enum import IntEnum
from typing import Any

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.decoder import (
    decode_proto,
    get_bool,
    get_int32,
    get_string,
    get_varint,
)
from proto.encoder import (
    encode_bool,
    encode_fixed64,
    encode_int32,
    encode_int64,
    encode_packed_uint64,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)


class LeaderboardMainType(IntEnum):
    REGULAR = 0
    RANKING_SCORE = 1
    RANKING_KILLS = 2
    RANKING_WIN_COUNT = 3
    CASUAL_KILLS = 4
    CASUAL_WIN_COUNT = 5
    ELITEPASS_BADGE = 6
    GIFT_STORE = 7
    CHAMPIONSHIP_TRIAL_SCORE = 8
    CHAMPIONSHIP_TRIAL_KILLS = 9
    CLAN_HONOR = 1001
    CLAN_HONOR_WEEK = 1002
    CLAN_RACE = 1003


class RankingActivityType(IntEnum):
    NONE = 0
    NO_DEDUCT = 1
    DOUBLE_RANKING_POINT = 2
    DOUBLE_TOKEN = 3


class AwardType(IntEnum):
    NONE = 0
    ITEM = 1
    COINS = 2
    GEMS = 3
    SKILL = 4
    EXP = 5
    ACTIVENESS = 6


# ---------------------------------------------------------------------------
# Request Decoders
# ---------------------------------------------------------------------------

def decode_leaderboard_req(raw_body: bytes) -> dict[str, Any]:
    """Decode CSLeaderboardReq (tags 1..9)."""
    fields = decode_proto(raw_body) if raw_body else {}
    return {
        "main_type": get_int32(fields, 1, LeaderboardMainType.RANKING_SCORE),
        "sub_type": get_int32(fields, 2, 0),
        "main_key": get_varint(fields, 3, 0),
        "sub_key": get_varint(fields, 4, 0),
        "page_index": get_varint(fields, 5, 0),
        "page_size": get_varint(fields, 6, 50),
        "get_self": get_bool(fields, 7, True),
        "region": get_string(fields, 8, ""),
        "lock_region": get_string(fields, 9, ""),
    }


def decode_ranking_info_req(raw_body: bytes) -> dict[str, int]:
    """Decode CSPlayerRankingInfoReq (tag 1: season_id)."""
    fields = decode_proto(raw_body) if raw_body else {}
    return {"season_id": get_varint(fields, 1, 1)}


def decode_ranking_season_stats_req(raw_body: bytes) -> dict[str, int]:
    """Decode CSPlayerRankingSeasonStatsReq (tag 1: season_id)."""
    fields = decode_proto(raw_body) if raw_body else {}
    return {"season_id": get_varint(fields, 1, 1)}


def decode_set_show_rank_req(raw_body: bytes) -> dict[str, Any]:
    """Decode CSSetShowRankReq (tag 1: season_id, tag 2: show_rank)."""
    fields = decode_proto(raw_body) if raw_body else {}
    return {
        "season_id": get_varint(fields, 1, 1),
        "show_rank": get_bool(fields, 2, True),
    }


# ---------------------------------------------------------------------------
# Low-level Protobuf Encoders
# ---------------------------------------------------------------------------

def encode_account_info_basic(p: dict[str, Any]) -> bytes:
    """Encode proto.AccountInfoBasic (tags 1..29)."""
    now = int(time.time())
    parts = [
        encode_uint64(1, int(p.get("account_id", DEFAULT_ACCOUNT_ID))),
        encode_uint32(2, int(p.get("account_type", 1))),
        encode_string(3, str(p.get("nickname", "Player"))),
        encode_string(4, str(p.get("external_id", ""))),
        encode_string(5, str(p.get("region", "BR"))),
        encode_uint32(6, int(p.get("level", 1))),
        encode_uint32(7, int(p.get("exp", 0))),
        encode_uint32(8, int(p.get("external_type", 0))),
        encode_string(9, str(p.get("external_name", ""))),
        encode_string(10, str(p.get("external_icon", ""))),
        encode_uint32(11, int(p.get("banner_id", 901000001))),
        encode_uint32(12, int(p.get("head_pic", 902000001))),
        encode_string(13, str(p.get("clan_name", ""))),
        encode_uint32(14, int(p.get("rank", 301))),
        encode_uint32(15, int(p.get("ranking_points", 1000))),
        encode_uint32(16, int(p.get("role", 0))),
        encode_bool(17, bool(p.get("has_elite_pass", False))),
        encode_uint32(18, int(p.get("badge_cnt", 0))),
        encode_uint32(19, int(p.get("badge_id", 100000001))),
        encode_uint32(20, int(p.get("season_id", 1))),
        encode_uint32(21, int(p.get("liked", 0))),
        encode_bool(22, bool(p.get("is_deleted", False))),
        encode_bool(23, bool(p.get("show_rank", True))),
        encode_int64(24, int(p.get("last_login_at", now))),
        encode_uint64(25, int(p.get("external_uid", 0))),
        encode_int64(26, int(p.get("return_at", 0))),
        encode_string(27, str(p.get("championship_team_name", ""))),
        encode_uint32(28, int(p.get("championship_team_member_num", 0))),
        encode_uint64(29, int(p.get("championship_team_id", 0))),
    ]
    return b"".join(parts)


def encode_detail_stats_json(stats: dict[str, Any]) -> str:
    """Build JSON matching client message.DetailStats fields."""
    games = max(1, int(stats.get("games_played", 1)))
    wins = int(stats.get("wins", 0))
    kills = int(stats.get("kills", 0))
    payload = {
        "deaths": int(stats.get("deaths", max(0, games - wins))),
        "top10_times": int(stats.get("top10_times", max(wins, int(games * 0.45)))),
        "top_n_times": int(stats.get("top_n_times", max(wins, int(games * 0.6)))),
        "distance_travelled": int(stats.get("distance_travelled", games * 2450)),
        "survival_time": int(stats.get("survival_time", games * 720)),
        "revives": int(stats.get("revives", max(1, kills // 6))),
        "highest_kills": int(stats.get("highest_kills", min(24, max(4, kills // max(1, games // 2))))),
        "damage": int(stats.get("damage", kills * 310)),
        "road_kills": int(stats.get("road_kills", max(0, kills // 25))),
        "headshots": int(stats.get("headshots", max(1, kills // 3))),
        "headshot_kills": int(stats.get("headshot_kills", max(1, kills // 4))),
        "knock_down": int(stats.get("knock_down", int(kills * 1.15))),
        "pick_ups": int(stats.get("pick_ups", games * 18)),
    }
    return json.dumps(payload, separators=(",", ":"))


def encode_account_info_with_stats(account_id: int, stats: dict[str, Any]) -> bytes:
    """Encode proto.AccountInfoWithStats (tags 1..5)."""
    detailed = stats.get("detailed_stats")
    if not isinstance(detailed, str):
        detailed = encode_detail_stats_json(stats)
    return b"".join([
        encode_uint64(1, int(account_id)),
        encode_uint32(2, int(stats.get("games_played", 0))),
        encode_uint32(3, int(stats.get("wins", 0))),
        encode_uint32(4, int(stats.get("kills", 0))),
        encode_string(5, detailed),
    ])


def encode_account_leaderboard_profile(player: dict[str, Any]) -> bytes:
    """Encode proto.AccountLeaderboardProfile (tags 1..4)."""
    account_id = int(player.get("account_id", DEFAULT_ACCOUNT_ID))
    stats = player.get("stats") or {
        "games_played": int(player.get("games_played", 120)),
        "wins": int(player.get("wins", 35)),
        "kills": int(player.get("kills", 420)),
    }
    return b"".join([
        encode_submessage(1, encode_account_info_basic(player)),
        encode_submessage(2, encode_account_info_with_stats(account_id, stats)),
        encode_uint32(3, int(player.get("rank", 301))),
        encode_uint32(4, int(player.get("ranking_points", 1000))),
    ])


def encode_account_leaderboard_item(item: dict[str, Any]) -> bytes:
    """Encode proto.AccountLeaderboardItem (tags 1..4)."""
    profile_data = item["account_profile"]
    return b"".join([
        encode_uint64(1, int(item["account_id"])),
        encode_fixed64(2, float(item["score"])),
        encode_submessage(3, encode_account_leaderboard_profile(profile_data)),
        encode_int32(4, int(item["pos"])),
    ])


def encode_account_leaderboard_res(items: list[dict[str, Any]], self_item: dict[str, Any] | None = None) -> bytes:
    """Encode proto.AccountLeaderboardRes (tag 1: items, tag 2: self)."""
    parts = [encode_submessage(1, encode_account_leaderboard_item(it)) for it in items]
    if self_item is not None:
        parts.append(encode_submessage(2, encode_account_leaderboard_item(self_item)))
    return b"".join(parts)


def encode_clan_info(clan: dict[str, Any]) -> bytes:
    """Encode proto.ClanInfo (tags 1..21)."""
    now = int(time.time())
    return b"".join([
        encode_uint64(1, int(clan["clan_id"])),
        encode_string(2, str(clan["clan_name"])),
        encode_uint64(3, int(clan.get("create_at", now - 86400 * 120))),
        encode_uint64(4, int(clan.get("captain_id", DEFAULT_ACCOUNT_ID))),
        encode_uint32(5, int(clan.get("clan_level", 4))),
        encode_uint32(6, int(clan.get("capacity", 50))),
        encode_uint32(7, int(clan.get("member_num", 32))),
        encode_uint32(8, int(clan.get("entry_level", 10))),
        encode_uint32(9, int(clan.get("entry_type", 0))),
        encode_string(10, str(clan.get("clan_logo", ""))),
        encode_string(11, str(clan.get("announcement", "Booyah!"))),
        encode_string(12, str(clan.get("slogan", "Play hard, win smart"))),
        encode_string(13, str(clan.get("region", "BR"))),
        encode_string(14, str(clan.get("misc", "{}"))),
        encode_string(15, str(clan.get("vice_captains", "[]"))),
        encode_uint32(16, int(clan.get("honor_point", 50000))),
        encode_uint32(17, int(clan.get("race_point", 12000))),
        encode_uint64(18, int(clan.get("last_gain_rp_at", now - 600))),
        encode_uint64(19, int(clan.get("claim_rp_award_at", now - 3600))),
        encode_uint32(20, int(clan.get("area_id", 1))),
        encode_uint32(21, int(clan.get("play_style", 1))),
    ])


def encode_clan_leaderboard_profile(clan: dict[str, Any]) -> bytes:
    """Encode proto.ClanLeaderboardProfile (tag 1: clan_info)."""
    return encode_submessage(1, encode_clan_info(clan))


def encode_clan_leaderboard_item(item: dict[str, Any]) -> bytes:
    """Encode proto.ClanLeaderboardItem (tags 1..4)."""
    return b"".join([
        encode_uint64(1, int(item["clan_id"])),
        encode_fixed64(2, float(item["score"])),
        encode_submessage(3, encode_clan_leaderboard_profile(item["clan_profile"])),
        encode_int32(4, int(item["pos"])),
    ])


def encode_clan_leaderboard_res(items: list[dict[str, Any]], self_item: dict[str, Any] | None = None) -> bytes:
    """Encode proto.ClanLeaderboardRes (tag 1: items, tag 2: self)."""
    parts = [encode_submessage(1, encode_clan_leaderboard_item(it)) for it in items]
    if self_item is not None:
        parts.append(encode_submessage(2, encode_clan_leaderboard_item(self_item)))
    return b"".join(parts)


def encode_clan_week_leaderboard_info_res(main_key: int, next_refresh_time: int) -> bytes:
    """Encode proto.CSGetClanWeekLeaderboardInfoRes (tags 1..2)."""
    return b"".join([
        encode_int64(1, int(main_key)),
        encode_uint32(2, int(next_refresh_time)),
    ])


def encode_team_info(team: dict[str, Any]) -> bytes:
    """Encode proto.TeamInfo (tags 1..11, tag 11 member_ids packed)."""
    member_ids = [int(m) for m in team.get("member_ids", [])]
    parts = [
        encode_uint64(1, int(team["team_id"])),
        encode_string(2, str(team["team_name"])),
        encode_uint64(3, int(team.get("create_at", int(time.time()) - 86400 * 30))),
        encode_uint64(4, int(team.get("captain_id", member_ids[0] if member_ids else DEFAULT_ACCOUNT_ID))),
        encode_uint32(5, int(team.get("member_num", len(member_ids)))),
        encode_string(6, str(team.get("region", "BR"))),
        encode_uint32(7, int(team.get("banner_id", 901000001))),
        encode_string(8, str(team.get("contact_info", ""))),
        encode_string(9, str(team.get("country_or_area", "BR"))),
        encode_uint32(10, int(team.get("head_pic", 902000001))),
    ]
    if member_ids:
        parts.append(encode_packed_uint64(11, member_ids))
    return b"".join(parts)


def encode_team_championship_info(champ: dict[str, Any]) -> bytes:
    """Encode proto.TeamChampionshipInfo (tags 1..15)."""
    return b"".join([
        encode_uint64(1, int(champ["team_id"])),
        encode_uint32(2, int(champ.get("championship_type", 1))),
        encode_uint32(3, int(champ.get("championship_id", 1))),
        encode_uint32(4, int(champ.get("tickets_num", 5))),
        encode_uint32(5, int(champ.get("trial_games_played", 12))),
        encode_uint32(6, int(champ.get("trial_kills", 95))),
        encode_uint32(7, int(champ.get("trial_valid_score", 2400))),
        encode_uint32(8, int(champ.get("trial_total_score", 2800))),
        encode_uint32(9, int(champ.get("trial_pos", 1))),
        encode_bool(10, bool(champ.get("is_enter_final", True))),
        encode_uint32(11, int(champ.get("final_games_played", 6))),
        encode_uint32(12, int(champ.get("final_kills", 42))),
        encode_uint32(13, int(champ.get("final_valid_score", 1400))),
        encode_uint32(14, int(champ.get("final_total_score", 1400))),
        encode_uint32(15, int(champ.get("final_pos", 1))),
    ])


def encode_account_info_basic_bundle_res(infos: list[dict[str, Any]]) -> bytes:
    """Encode proto.AccountInfoBasicBundleRes (tag 1: repeated infos)."""
    return b"".join(encode_submessage(1, encode_account_info_basic(info)) for info in infos)


def encode_team_championship_season_stats_res(stats: dict[str, Any]) -> bytes:
    """Encode proto.CSTeamChampionshipSeasonStatsRes (tags 1..17, tag 4 members packed)."""
    members = [int(m) for m in stats.get("members", [])]
    parts = [
        encode_uint64(1, int(stats["team_id"])),
        encode_uint32(2, int(stats.get("championship_type", 1))),
        encode_uint32(3, int(stats.get("championship_id", 1))),
    ]
    if members:
        parts.append(encode_packed_uint64(4, members))
    parts.extend([
        encode_uint32(5, int(stats.get("games_played", 18))),
        encode_int32(6, int(stats.get("max_score", 2800))),
        encode_uint32(7, int(stats.get("wins", 7))),
        encode_uint32(8, int(stats.get("top_10_percent_times", 12))),
        encode_uint32(9, int(stats.get("top_50_percent_times", 16))),
        encode_uint32(10, int(stats.get("survival_time", 15400))),
        encode_uint32(11, int(stats.get("moving_distance", 48000))),
        encode_uint32(12, int(stats.get("kills", 137))),
        encode_uint32(13, int(stats.get("damage", 41200))),
        encode_uint32(14, int(stats.get("one_game_most_kills", 16))),
        encode_uint32(15, int(stats.get("one_game_most_damage", 4650))),
        encode_uint32(16, int(stats.get("headshot_kills", 39))),
        encode_submessage(17, encode_account_info_basic_bundle_res(stats.get("members_info", []))),
    ])
    return b"".join(parts)


def encode_team_leaderboard_profile(entry: dict[str, Any]) -> bytes:
    """Encode proto.TeamLeaderboardProfile (tags 1..3)."""
    return b"".join([
        encode_submessage(1, encode_team_info(entry["team_info"])),
        encode_submessage(2, encode_team_championship_info(entry["team_championship_info"])),
        encode_submessage(3, encode_team_championship_season_stats_res(entry["team_stats"])),
    ])


def encode_team_leaderboard_item(item: dict[str, Any]) -> bytes:
    """Encode proto.TeamLeaderboardItem (tags 1..4)."""
    return b"".join([
        encode_uint64(1, int(item["team_id"])),
        encode_fixed64(2, float(item["score"])),
        encode_submessage(3, encode_team_leaderboard_profile(item["team_profile"])),
        encode_int32(4, int(item["pos"])),
    ])


def encode_team_leaderboard_res(items: list[dict[str, Any]], self_item: dict[str, Any] | None = None) -> bytes:
    """Encode proto.TeamLeaderboardRes (tag 1: items, tag 2: self)."""
    parts = [encode_submessage(1, encode_team_leaderboard_item(it)) for it in items]
    if self_item is not None:
        parts.append(encode_submessage(2, encode_team_leaderboard_item(self_item)))
    return b"".join(parts)


def encode_leaderboard_profile(
    account_profile: dict[str, Any] | None = None,
    clan_profile: dict[str, Any] | None = None,
    team_profile: dict[str, Any] | None = None,
) -> bytes:
    """Encode proto.LeaderboardProfile (tags 1..4)."""
    has_data = bool(account_profile or clan_profile or team_profile)
    parts = [encode_bool(1, has_data)]
    if account_profile is not None:
        parts.append(encode_submessage(2, encode_account_leaderboard_profile(account_profile)))
    if clan_profile is not None:
        parts.append(encode_submessage(3, encode_clan_leaderboard_profile(clan_profile)))
    if team_profile is not None:
        parts.append(encode_submessage(4, encode_team_leaderboard_profile(team_profile)))
    return b"".join(parts)


def encode_leaderboard_item(item: dict[str, Any]) -> bytes:
    """Encode proto.LeaderboardItem (tag 5: unique_id, tag 2: score, tag 3: profile, tag 4: pos)."""
    return b"".join([
        encode_uint64(5, int(item["unique_id"])),
        encode_fixed64(2, float(item["score"])),
        encode_submessage(3, encode_leaderboard_profile(**item["profile"])),
        encode_int32(4, int(item["pos"])),
    ])


def encode_cs_leaderboard_res(items: list[dict[str, Any]], self_item: dict[str, Any] | None = None) -> bytes:
    """Encode proto.CSLeaderboardRes (tag 1: items, tag 2: self)."""
    parts = [encode_submessage(1, encode_leaderboard_item(it)) for it in items]
    if self_item is not None:
        parts.append(encode_submessage(2, encode_leaderboard_item(self_item)))
    return b"".join(parts)


def encode_ranking_season_info(season: dict[str, Any]) -> bytes:
    """Encode proto.RankingSeasonInfo (tags 1..6)."""
    return b"".join([
        encode_uint32(1, int(season["id"])),
        encode_int64(2, int(season["open_time"])),
        encode_int64(3, int(season["end_time"])),
        encode_string(4, str(season["season_name"])),
        encode_uint32(5, int(season.get("starting_ranking_points", 1000))),
        encode_string(6, str(season.get("map_id", "Bermuda"))),
    ])


def encode_award_desc(award: dict[str, Any]) -> bytes:
    """Encode proto.AwardDesc (tags 1..5)."""
    return b"".join([
        encode_int32(1, int(award.get("award_type", AwardType.COINS))),
        encode_uint32(2, int(award.get("award_id", 0))),
        encode_uint32(3, int(award.get("award_num", 0))),
        encode_uint32(4, int(award.get("award_max_num", award.get("award_num", 0)))),
        encode_uint32(5, int(award.get("award_expire_time", 0))),
    ])


def encode_rank_awards_desc(rank_award: dict[str, Any]) -> bytes:
    """Encode proto.RankAwardsDesc (tags 1..3)."""
    parts = [encode_uint32(1, int(rank_award["rank"]))]
    for award in rank_award.get("level_awards", []):
        parts.append(encode_submessage(2, encode_award_desc(award)))
    for award in rank_award.get("season_awards", []):
        parts.append(encode_submessage(3, encode_award_desc(award)))
    return b"".join(parts)


def encode_ranking_season_config_res(season: dict[str, Any], awards: list[dict[str, Any]]) -> bytes:
    """Encode proto.CSGetCurrentOrRecentRankingSeasonConfigRes (tags 1..2)."""
    parts = [encode_submessage(1, encode_ranking_season_info(season))]
    for rank_award in awards:
        parts.append(encode_submessage(2, encode_rank_awards_desc(rank_award)))
    return b"".join(parts)


def encode_player_ranking_season_stats_res(stats: dict[str, Any]) -> bytes:
    """Encode proto.CSPlayerRankingSeasonStatsRes (tags 1..16)."""
    return b"".join([
        encode_uint64(1, int(stats["account_id"])),
        encode_uint32(2, int(stats.get("season_id", 1))),
        encode_uint32(3, int(stats.get("games_played", 0))),
        encode_uint32(4, int(stats.get("max_rank", 301))),
        encode_uint32(5, int(stats.get("max_ranking_points", 1000))),
        encode_uint32(6, int(stats.get("wins", 0))),
        encode_uint32(7, int(stats.get("top_10_percent_times", 0))),
        encode_uint32(8, int(stats.get("top_50_percent_times", 0))),
        encode_uint32(9, int(stats.get("survival_time", 0))),
        encode_uint32(10, int(stats.get("moving_distance", 0))),
        encode_uint32(11, int(stats.get("kills", 0))),
        encode_uint32(12, int(stats.get("damage", 0))),
        encode_uint32(13, int(stats.get("one_game_most_kills", 0))),
        encode_uint32(14, int(stats.get("one_game_most_damage", 0))),
        encode_uint32(15, int(stats.get("head_shot_kills", 0))),
        encode_uint32(16, int(stats.get("revivals", 0))),
    ])


def encode_ranking_info(info: dict[str, Any]) -> bytes:
    """Encode proto.RankingInfo (tags 1..4)."""
    return b"".join([
        encode_uint32(1, int(info.get("season_id", 1))),
        encode_uint32(2, int(info.get("rank", 301))),
        encode_uint32(3, int(info.get("max_rank", 301))),
        encode_uint32(4, int(info.get("ranking_points", 1000))),
    ])


def encode_player_ranking_info_res(info: dict[str, Any]) -> bytes:
    """Encode proto.CSPlayerRankingInfoRes (tags 1..8)."""
    last_season = info.get("last_season_info") or {
        "season_id": max(1, int(info.get("season_id", 1))),
        "rank": int(info.get("rank", 301)),
        "max_rank": int(info.get("max_rank", 301)),
        "ranking_points": int(info.get("ranking_points", 1000)),
    }
    return b"".join([
        encode_uint64(1, int(info["account_id"])),
        encode_uint32(2, int(info.get("season_id", 1))),
        encode_uint32(3, int(info.get("rank", 301))),
        encode_uint32(4, int(info.get("max_rank", 301))),
        encode_uint32(5, int(info.get("ranking_points", 1000))),
        encode_bool(6, bool(info.get("show_rank", True))),
        encode_submessage(7, encode_ranking_info(last_season)),
        encode_uint32(8, int(info.get("match_token_num", 40))),
    ])


def encode_daily_ranking_reward_res(has_first_win: bool) -> bytes:
    """Encode proto.CSGetDailyRankingRewardRes (tag 1: has_first_win)."""
    return encode_bool(1, bool(has_first_win))


def encode_set_show_rank_res(show_rank: bool) -> bytes:
    """Encode proto.CSSetShowRankRes (tag 1: show_rank)."""
    return encode_bool(1, bool(show_rank))


def encode_ranking_activity_config(cfg: dict[str, Any]) -> bytes:
    """Encode proto.RankingActivityConfig (tags 1..4, 101, 102)."""
    return b"".join([
        encode_string(1, str(cfg.get("region", "BR"))),
        encode_string(2, str(cfg.get("start_time", "2020-01-01 00:00:00"))),
        encode_string(3, str(cfg.get("end_time", "2030-01-01 00:00:00"))),
        encode_int32(4, int(cfg.get("activity_type", RankingActivityType.NONE))),
        encode_uint32(101, int(cfg.get("start_timestamp", 1577836800))),
        encode_uint32(102, int(cfg.get("end_timestamp", 1893456000))),
    ])


def encode_ranking_activity_config_res(configs: list[dict[str, Any]]) -> bytes:
    """Encode proto.CSGetRankingActivityConfigRes (tag 1: repeated activity_configs)."""
    return b"".join(encode_submessage(1, encode_ranking_activity_config(c)) for c in configs)


# ---------------------------------------------------------------------------
# Seeded Datasets & High-Level Response Builders
# ---------------------------------------------------------------------------

_EXTRA_GLOBAL_PLAYERS: list[dict[str, Any]] = [
    {
        "account_id": 30001,
        "nickname": "Nobru_FF",
        "level": 78,
        "exp": 985000,
        "rank": 320,
        "ranking_points": 5420,
        "clan_name": "CORINTHIANS",
        "has_elite_pass": True,
        "badge_cnt": 380,
        "liked": 45120,
        "banner_id": 901000015,
        "head_pic": 902000015,
        "region": "BR",
        "games_played": 412,
        "wins": 164,
        "kills": 1985,
        "gift_score": 14800,
    },
    {
        "account_id": 30002,
        "nickname": "Cerol_BR",
        "level": 76,
        "exp": 920000,
        "rank": 320,
        "ranking_points": 5190,
        "clan_name": "FLUXO_GG",
        "has_elite_pass": True,
        "badge_cnt": 355,
        "liked": 39400,
        "banner_id": 901000014,
        "head_pic": 902000014,
        "region": "BR",
        "games_played": 390,
        "wins": 149,
        "kills": 1820,
        "gift_score": 12600,
    },
    {
        "account_id": 30003,
        "nickname": "B4K_Legend",
        "level": 75,
        "exp": 890000,
        "rank": 319,
        "ranking_points": 4890,
        "clan_name": "BASTARDOS",
        "has_elite_pass": True,
        "badge_cnt": 310,
        "liked": 32800,
        "banner_id": 901000012,
        "head_pic": 902000012,
        "region": "BR",
        "games_played": 365,
        "wins": 132,
        "kills": 1645,
        "gift_score": 9800,
    },
    {
        "account_id": 30004,
        "nickname": "LevelUp007",
        "level": 73,
        "exp": 845000,
        "rank": 318,
        "ranking_points": 4520,
        "clan_name": "BARBOSA",
        "has_elite_pass": True,
        "badge_cnt": 295,
        "liked": 28450,
        "banner_id": 901000011,
        "head_pic": 902000011,
        "region": "BR",
        "games_played": 340,
        "wins": 118,
        "kills": 1480,
        "gift_score": 8200,
    },
    {
        "account_id": 30005,
        "nickname": "Raistar99",
        "level": 72,
        "exp": 810000,
        "rank": 318,
        "ranking_points": 4210,
        "clan_name": "HEADSHOT",
        "has_elite_pass": True,
        "badge_cnt": 275,
        "liked": 26100,
        "banner_id": 901000010,
        "head_pic": 902000010,
        "region": "BR",
        "games_played": 315,
        "wins": 108,
        "kills": 1590,
        "gift_score": 7400,
    },
]

_SEEDED_CLANS: list[dict[str, Any]] = [
    {
        "clan_id": 50001,
        "clan_name": "BARBOSA",
        "captain_id": 10001,
        "clan_level": 5,
        "capacity": 50,
        "member_num": 38,
        "honor_point": 184500,
        "week_honor": 42800,
        "race_point": 26400,
        "slogan": "LEGACY 1.39 - Always Booyah",
    },
    {
        "clan_id": 50002,
        "clan_name": "FF_LEGENDS",
        "captain_id": 20003,
        "clan_level": 5,
        "capacity": 50,
        "member_num": 44,
        "honor_point": 176200,
        "week_honor": 39500,
        "race_point": 24100,
        "slogan": "Top Squads Only",
    },
    {
        "clan_id": 50003,
        "clan_name": "HEADSHOT",
        "captain_id": 20004,
        "clan_level": 4,
        "capacity": 45,
        "member_num": 36,
        "honor_point": 154800,
        "week_honor": 34200,
        "race_point": 19800,
        "slogan": "One Tap Precision",
    },
    {
        "clan_id": 50004,
        "clan_name": "CORINTHIANS",
        "captain_id": 30001,
        "clan_level": 5,
        "capacity": 50,
        "member_num": 49,
        "honor_point": 212400,
        "week_honor": 51600,
        "race_point": 31200,
        "slogan": "Champions League",
    },
    {
        "clan_id": 50005,
        "clan_name": "FLUXO_GG",
        "captain_id": 30002,
        "clan_level": 5,
        "capacity": 50,
        "member_num": 47,
        "honor_point": 198900,
        "week_honor": 46900,
        "race_point": 28750,
        "slogan": "Bermuda Rushers",
    },
]

_SEEDED_CHAMPIONSHIP_TEAMS: list[dict[str, Any]] = [
    {
        "team_id": 70001,
        "team_name": "BARBOSA_SQUAD",
        "captain_id": 10001,
        "member_ids": [10001, 20001, 20002, 20003],
        "trial_valid_score": 3250,
        "trial_total_score": 3680,
        "trial_kills": 148,
        "wins": 9,
    },
    {
        "team_id": 70002,
        "team_name": "FLUXO_PRO",
        "captain_id": 30002,
        "member_ids": [30002, 30003, 20004, 20005],
        "trial_valid_score": 3580,
        "trial_total_score": 3920,
        "trial_kills": 164,
        "wins": 11,
    },
    {
        "team_id": 70003,
        "team_name": "TIMAO_FF",
        "captain_id": 30001,
        "member_ids": [30001, 30004, 30005, 20006],
        "trial_valid_score": 3710,
        "trial_total_score": 4150,
        "trial_kills": 176,
        "wins": 12,
    },
    {
        "team_id": 70004,
        "team_name": "NIGHT_HUNTERS",
        "captain_id": 20007,
        "member_ids": [20007, 20008, 20009, 20010],
        "trial_valid_score": 2690,
        "trial_total_score": 2940,
        "trial_kills": 112,
        "wins": 6,
    },
]

_RANK_AWARDS_SEED: list[dict[str, Any]] = [
    {
        "rank": 301,
        "level_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 500}],
        "season_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 1000}],
    },
    {
        "rank": 306,
        "level_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 1000}],
        "season_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 1500}],
    },
    {
        "rank": 310,
        "level_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 1500}],
        "season_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 2500}],
    },
    {
        "rank": 314,
        "level_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 2500}],
        "season_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 4000}],
    },
    {
        "rank": 318,
        "level_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 4000}],
        "season_awards": [
            {"award_type": AwardType.COINS, "award_id": 0, "award_num": 6000},
            {"award_type": AwardType.ITEM, "award_id": 901000001, "award_num": 1},
        ],
    },
    {
        "rank": 319,
        "level_awards": [{"award_type": AwardType.COINS, "award_id": 0, "award_num": 5000}],
        "season_awards": [
            {"award_type": AwardType.COINS, "award_id": 0, "award_num": 8000},
            {"award_type": AwardType.ITEM, "award_id": 902000001, "award_num": 1},
        ],
    },
]


def _normalize_player(raw: dict[str, Any]) -> dict[str, Any]:
    """Ensure every player record has complete stats and profile defaults."""
    rp = int(raw.get("ranking_points", 2000))
    level = int(raw.get("level", 40))
    games = int(raw.get("games_played", max(30, rp // 14)))
    wins = int(raw.get("wins", max(5, games // 4)))
    kills = int(raw.get("kills", max(40, int(games * 3.8))))
    p = dict(raw)
    p.setdefault("account_type", 1)
    p.setdefault("region", "BR")
    p.setdefault("exp", level * 12000)
    p.setdefault("banner_id", 901000001)
    p.setdefault("head_pic", 902000001)
    p.setdefault("clan_name", "")
    p.setdefault("rank", 315)
    p.setdefault("ranking_points", rp)
    p.setdefault("has_elite_pass", level >= 45)
    p.setdefault("badge_cnt", max(10, level * 3))
    p.setdefault("badge_id", 100000001)
    p.setdefault("season_id", 1)
    p.setdefault("liked", max(100, level * 150))
    p.setdefault("show_rank", True)
    p.setdefault("games_played", games)
    p.setdefault("wins", wins)
    p.setdefault("kills", kills)
    p.setdefault("gift_score", max(500, rp * 2))
    p["stats"] = {
        "games_played": p["games_played"],
        "wins": p["wins"],
        "kills": p["kills"],
    }
    return p


def _collect_players(account_id: int, friends_only: bool = False) -> list[dict[str, Any]]:
    """Collect active profile, friends/bots, and global leaderboard entrants."""
    by_id: dict[int, dict[str, Any]] = {}

    self_profile = state.get_profile(account_id)
    if self_profile:
        by_id[int(self_profile.get("account_id", account_id))] = _normalize_player(self_profile)

    for friend in state.list_friends(account_id, online_only=False):
        fid = int(friend.get("account_id", 0))
        if fid:
            by_id.setdefault(fid, _normalize_player(friend))

    if not friends_only:
        for bot in state.list_recommended_friends(account_id, limit=50):
            bid = int(bot.get("account_id", 0))
            if bid:
                by_id.setdefault(bid, _normalize_player(bot))
        for bot_id in range(20001, 20015):
            bot = state.get_player(bot_id)
            if bot:
                by_id.setdefault(int(bot["account_id"]), _normalize_player(bot))
        for gp in _EXTRA_GLOBAL_PLAYERS:
            by_id.setdefault(int(gp["account_id"]), _normalize_player(gp))

    return list(by_id.values())


def _score_for_player(player: dict[str, Any], main_type: int) -> float:
    if main_type in (LeaderboardMainType.RANKING_KILLS, LeaderboardMainType.CASUAL_KILLS):
        return float(player.get("kills", 0))
    if main_type in (LeaderboardMainType.RANKING_WIN_COUNT, LeaderboardMainType.CASUAL_WIN_COUNT):
        return float(player.get("wins", 0))
    if main_type == LeaderboardMainType.ELITEPASS_BADGE:
        return float(player.get("badge_cnt", 0))
    if main_type == LeaderboardMainType.GIFT_STORE:
        return float(player.get("gift_score", 0))
    return float(player.get("ranking_points", 0))


def _paginate(items: list[dict[str, Any]], page_index: int, page_size: int) -> list[dict[str, Any]]:
    if page_size <= 0:
        return items
    start = max(0, page_index) * page_size
    return items[start : start + page_size]


def build_account_leaderboard_response(
    account_id: int = DEFAULT_ACCOUNT_ID,
    req: dict[str, Any] | None = None,
) -> bytes:
    """Build AccountLeaderboardRes sorted by main_type with pagination and self entry."""
    req = req or {}
    main_type = int(req.get("main_type", LeaderboardMainType.RANKING_SCORE))
    sub_type = int(req.get("sub_type", 0))
    friends_only = sub_type == 1
    page_index = int(req.get("page_index", 0))
    page_size = int(req.get("page_size", 50))
    get_self = bool(req.get("get_self", True))

    players = _collect_players(account_id, friends_only=friends_only)
    players.sort(key=lambda p: (-_score_for_player(p, main_type), int(p["account_id"])))

    ranked_items: list[dict[str, Any]] = []
    self_item: dict[str, Any] | None = None
    for idx, p in enumerate(players, start=1):
        entry = {
            "account_id": int(p["account_id"]),
            "score": _score_for_player(p, main_type),
            "account_profile": p,
            "pos": idx,
        }
        ranked_items.append(entry)
        if int(p["account_id"]) == int(account_id):
            self_item = entry

    paged = _paginate(ranked_items, page_index, page_size)
    return encode_account_leaderboard_res(paged, self_item if get_self else None)


def build_clan_leaderboard_response(
    account_id: int = DEFAULT_ACCOUNT_ID,
    req: dict[str, Any] | None = None,
) -> bytes:
    """Build ClanLeaderboardRes sorted by clan honor/week honor/race points."""
    req = req or {}
    main_type = int(req.get("main_type", LeaderboardMainType.CLAN_HONOR))
    page_index = int(req.get("page_index", 0))
    page_size = int(req.get("page_size", 50))
    get_self = bool(req.get("get_self", True))

    profile = state.get_profile(account_id) or {}
    self_clan_id = int(profile.get("clan_id", 50001) or 50001)

    def _clan_score(c: dict[str, Any]) -> float:
        if main_type == LeaderboardMainType.CLAN_HONOR_WEEK:
            return float(c.get("week_honor", c.get("honor_point", 0)))
        if main_type == LeaderboardMainType.CLAN_RACE:
            return float(c.get("race_point", 0))
        return float(c.get("honor_point", 0))

    clans = sorted(_SEEDED_CLANS, key=lambda c: (-_clan_score(c), int(c["clan_id"])))
    ranked_items: list[dict[str, Any]] = []
    self_item: dict[str, Any] | None = None
    for idx, c in enumerate(clans, start=1):
        entry = {
            "clan_id": int(c["clan_id"]),
            "score": _clan_score(c),
            "clan_profile": c,
            "pos": idx,
        }
        ranked_items.append(entry)
        if int(c["clan_id"]) == self_clan_id:
            self_item = entry

    paged = _paginate(ranked_items, page_index, page_size)
    return encode_clan_leaderboard_res(paged, self_item if get_self else None)


def build_team_leaderboard_response(
    account_id: int = DEFAULT_ACCOUNT_ID,
    req: dict[str, Any] | None = None,
) -> bytes:
    """Build TeamLeaderboardRes for championship trial score/kills leaderboards."""
    req = req or {}
    main_type = int(req.get("main_type", LeaderboardMainType.CHAMPIONSHIP_TRIAL_SCORE))
    page_index = int(req.get("page_index", 0))
    page_size = int(req.get("page_size", 50))
    get_self = bool(req.get("get_self", True))

    def _team_score(t: dict[str, Any]) -> float:
        if main_type == LeaderboardMainType.CHAMPIONSHIP_TRIAL_KILLS:
            return float(t.get("trial_kills", 0))
        return float(t.get("trial_valid_score", 0))

    players_by_id = {int(p["account_id"]): p for p in _collect_players(account_id, friends_only=False)}
    teams = sorted(_SEEDED_CHAMPIONSHIP_TEAMS, key=lambda t: (-_team_score(t), int(t["team_id"])))
    ranked_items: list[dict[str, Any]] = []
    self_item: dict[str, Any] | None = None

    for idx, t in enumerate(teams, start=1):
        tid = int(t["team_id"])
        member_ids = [int(m) for m in t["member_ids"]]
        member_infos = []
        for mid in member_ids:
            p = players_by_id.get(mid) or state.get_player(mid)
            if p is None and mid == account_id:
                p = state.get_profile(mid)
            if p is not None:
                member_infos.append(_normalize_player(p))

        team_profile = {
            "team_info": {
                "team_id": tid,
                "team_name": t["team_name"],
                "captain_id": t["captain_id"],
                "member_num": len(member_ids),
                "member_ids": member_ids,
                "region": "BR",
            },
            "team_championship_info": {
                "team_id": tid,
                "championship_type": 1,
                "championship_id": 1,
                "trial_games_played": 12,
                "trial_kills": t["trial_kills"],
                "trial_valid_score": t["trial_valid_score"],
                "trial_total_score": t["trial_total_score"],
                "trial_pos": idx,
                "final_pos": idx,
            },
            "team_stats": {
                "team_id": tid,
                "championship_type": 1,
                "championship_id": 1,
                "members": member_ids,
                "games_played": 18,
                "max_score": t["trial_total_score"],
                "wins": t["wins"],
                "kills": t["trial_kills"],
                "members_info": member_infos,
            },
        }
        entry = {
            "team_id": tid,
            "score": _team_score(t),
            "team_profile": team_profile,
            "pos": idx,
        }
        ranked_items.append(entry)
        if int(account_id) in member_ids:
            self_item = entry

    paged = _paginate(ranked_items, page_index, page_size)
    return encode_team_leaderboard_res(paged, self_item if get_self else None)


def build_leaderboard_dispatch(
    account_id: int = DEFAULT_ACCOUNT_ID,
    raw_body: bytes = b"",
) -> tuple[str, bytes]:
    """Decode CSLeaderboardReq and return (proto_name, encoded_bytes) per UIModelLeaderBoard dispatch."""
    req = decode_leaderboard_req(raw_body)
    main_type = int(req["main_type"])
    if main_type in (
        LeaderboardMainType.CLAN_HONOR,
        LeaderboardMainType.CLAN_HONOR_WEEK,
        LeaderboardMainType.CLAN_RACE,
    ):
        return "ClanLeaderboardRes", build_clan_leaderboard_response(account_id, req)
    if main_type in (
        LeaderboardMainType.CHAMPIONSHIP_TRIAL_SCORE,
        LeaderboardMainType.CHAMPIONSHIP_TRIAL_KILLS,
    ):
        return "TeamLeaderboardRes", build_team_leaderboard_response(account_id, req)
    return "AccountLeaderboardRes", build_account_leaderboard_response(account_id, req)


def build_ranking_season_config_response(season_id: int = 1) -> bytes:
    """Build CSGetCurrentOrRecentRankingSeasonConfigRes."""
    now = int(time.time())
    season = {
        "id": max(1, int(season_id)),
        "open_time": now - 86400 * 30,
        "end_time": now + 86400 * 45,
        "season_name": f"Ranked Season {max(1, int(season_id))}",
        "starting_ranking_points": 1000,
        "map_id": "Bermuda",
    }
    return encode_ranking_season_config_res(season, _RANK_AWARDS_SEED)


def build_player_ranking_season_stats_response(
    account_id: int = DEFAULT_ACCOUNT_ID,
    season_id: int = 1,
) -> bytes:
    """Build CSPlayerRankingSeasonStatsRes from profile state."""
    p = _normalize_player(state.get_profile(account_id) or {"account_id": account_id})
    games = max(1, int(p["games_played"]))
    wins = int(p["wins"])
    kills = int(p["kills"])
    rank = int(p["rank"])
    rp = int(p["ranking_points"])
    return encode_player_ranking_season_stats_res({
        "account_id": account_id,
        "season_id": max(1, int(season_id)),
        "games_played": games,
        "max_rank": max(rank, 315),
        "max_ranking_points": max(rp, 3250),
        "wins": wins,
        "top_10_percent_times": max(wins, int(games * 0.45)),
        "top_50_percent_times": max(wins, int(games * 0.72)),
        "survival_time": games * 740,
        "moving_distance": games * 2600,
        "kills": kills,
        "damage": kills * 320,
        "one_game_most_kills": 18,
        "one_game_most_damage": 5400,
        "head_shot_kills": max(1, kills // 3),
        "revivals": max(1, wins * 2),
    })


def build_player_ranking_info_response(
    account_id: int = DEFAULT_ACCOUNT_ID,
    season_id: int = 1,
) -> bytes:
    """Build CSPlayerRankingInfoRes from profile state."""
    p = _normalize_player(state.get_profile(account_id) or {"account_id": account_id})
    sid = max(1, int(season_id))
    rank = int(p["rank"])
    rp = int(p["ranking_points"])
    return encode_player_ranking_info_res({
        "account_id": account_id,
        "season_id": sid,
        "rank": rank,
        "max_rank": max(rank, int(p.get("max_rank", rank))),
        "ranking_points": rp,
        "show_rank": bool(p.get("show_rank", True)),
        "last_season_info": {
            "season_id": max(1, sid - 1) if sid > 1 else 1,
            "rank": rank,
            "max_rank": max(rank, int(p.get("max_rank", rank))),
            "ranking_points": rp,
        },
        "match_token_num": int(p.get("rank_tokens", 120)),
    })


def build_clan_week_leaderboard_info_response() -> bytes:
    """Build CSGetClanWeekLeaderboardInfoRes with current ISO-week key and next Monday reset."""
    now = int(time.time())
    tm = time.gmtime(now)
    iso_year, iso_week, iso_wday = time.strftime("%G %V %u", tm).split()
    main_key = int(f"{iso_year}{iso_week}")
    days_until_monday = 8 - int(iso_wday)
    seconds_today = tm.tm_hour * 3600 + tm.tm_min * 60 + tm.tm_sec
    next_refresh = now + days_until_monday * 86400 - seconds_today
    return encode_clan_week_leaderboard_info_res(main_key, next_refresh)
