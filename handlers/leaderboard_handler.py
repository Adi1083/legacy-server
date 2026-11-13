"""HTTP endpoint handlers for Free Fire 1.39 leaderboards & ranking endpoints."""

from __future__ import annotations

import logging
from typing import Any

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.leaderboard_models import (
    RankingActivityType,
    build_account_leaderboard_response,
    build_clan_week_leaderboard_info_response,
    build_leaderboard_dispatch,
    build_player_ranking_info_response,
    build_player_ranking_season_stats_response,
    build_ranking_season_config_response,
    decode_leaderboard_req,
    decode_ranking_info_req,
    decode_ranking_season_stats_req,
    decode_set_show_rank_req,
    encode_daily_ranking_reward_res,
    encode_ranking_activity_config_res,
    encode_set_show_rank_res,
)

logger = logging.getLogger("barbosa.leaderboard")


def _extract_endpoint(path: str) -> str:
    return path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]


def handle_leaderboard_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """Dispatch Free Fire 1.39 leaderboard & ranking endpoints. Returns True if handled."""
    endpoint = _extract_endpoint(path)

    if endpoint == "Leaderboard":
        proto_name, payload = build_leaderboard_dispatch(account_id, raw_body)
        handler.send_proto(proto_name, payload)
        return True

    if endpoint in ("MajorGetGlobalLeaderboard", "GetTopNDailyLeaderboard", "GetDailyLeaderboardByAccountID", "GetLeaderboardPeakItem"):
        req = decode_leaderboard_req(raw_body)
        if endpoint == "GetTopNDailyLeaderboard" and not raw_body:
            req["page_size"] = 20
        payload = build_account_leaderboard_response(account_id, req)
        handler.send_proto("AccountLeaderboardRes", payload)
        return True

    if endpoint == "GetClanWeekLeaderboardInfo":
        payload = build_clan_week_leaderboard_info_response()
        handler.send_proto("CSGetClanWeekLeaderboardInfoRes", payload)
        return True

    if endpoint == "GetCurOrRecentRankingConfig":
        req = decode_ranking_info_req(raw_body)
        payload = build_ranking_season_config_response(season_id=req["season_id"] or 1)
        handler.send_proto("CSGetCurrentOrRecentRankingSeasonConfigRes", payload)
        return True

    if endpoint == "GetPlayerRankingSeasonStats":
        req = decode_ranking_season_stats_req(raw_body)
        payload = build_player_ranking_season_stats_response(
            account_id=account_id,
            season_id=req["season_id"] or 1,
        )
        handler.send_proto("CSPlayerRankingSeasonStatsRes", payload)
        return True

    if endpoint == "GetPlayerRankingInfo":
        req = decode_ranking_info_req(raw_body)
        payload = build_player_ranking_info_response(
            account_id=account_id,
            season_id=req["season_id"] or 1,
        )
        handler.send_proto("CSPlayerRankingInfoRes", payload)
        return True

    if endpoint == "GetDailyRankingReward":
        payload = encode_daily_ranking_reward_res(has_first_win=True)
        handler.send_proto("CSGetDailyRankingRewardRes", payload)
        return True

    if endpoint == "SetShowRank":
        req = decode_set_show_rank_req(raw_body)
        show_rank = bool(req["show_rank"])
        state.update_profile(account_id, show_rank=show_rank)
        payload = encode_set_show_rank_res(show_rank)
        handler.send_proto("CSSetShowRankRes", payload)
        return True

    if endpoint == "GetRankingActivityConfig":
        payload = encode_ranking_activity_config_res([
            {
                "region": "BR",
                "start_time": "2020-01-01 00:00:00",
                "end_time": "2030-01-01 00:00:00",
                "activity_type": RankingActivityType.DOUBLE_RANKING_POINT,
                "start_timestamp": 1577836800,
                "end_timestamp": 1893456000,
            }
        ])
        handler.send_proto("CSGetRankingActivityConfigRes", payload)
        return True

    if endpoint in ("ResetNeedLastSeasonInfo", "ChooseRankingCards"):
        handler.send_proto(f"{endpoint}Res", b"")
        return True

    return False


handle_leaderboard_post = handle_leaderboard_request
