"""
HTTP request handlers for Manual, Live/Streamer/Video, GiftRank, MysteryBonus,
WinnerTakesAll, CollectionHide, Loadout, and Entitlement endpoints in Free Fire 1.39.

Exposes `handle_misc_request(handler, path, client_ip, raw_body, account_id=10001) -> bool`
(alias `handle_misc_post`) for automatic pickup by `handlers/game_router.py`.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Set

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.activity_models import AwardType
from proto.decoder import decode_proto, get_packed_varints, get_varint
from proto.encoder import encode_uint32
from proto.misc_models import (
    EManualState,
    FollowerType,
    GiftRankType,
    VideoType,
    decode_all_video_list_by_type_req,
    decode_choose_loadout_req,
    decode_follow_streamer_list_req,
    decode_get_gift_rank_reward_req,
    decode_gift_rank_reward_info_req,
    decode_live_table_names_req,
    decode_manual_map_reward_req,
    decode_manual_weapon_reward_req,
    decode_other_live_info_req,
    decode_personal_video_zone_req,
    decode_recommended_video_list_req,
    decode_update_account_follow_stat_req,
    decode_update_video_hit_count_req,
    encode_all_video_list_by_type_res,
    encode_follow_streamer_list_res,
    encode_get_gift_rank_desc_res,
    encode_get_hide_collections_res,
    encode_get_live_info_res,
    encode_get_manual_all_map_reward_states_res,
    encode_get_manual_all_weapon_reward_states_res,
    encode_get_manual_collect_info_res,
    encode_get_winner_takes_all_info_res,
    encode_gift_rank_reward_info_res,
    encode_get_gift_rank_reward_res,
    encode_live_table_names_res,
    encode_manual_map_reward_res,
    encode_manual_weapon_reward_res,
    encode_mystery_bonus_res,
    encode_mystery_bonus_spin_res,
    encode_personal_video_zone_res,
    encode_recommended_video_list_res,
)


# ---------------------------------------------------------------------------
# Thread-safe Per-Account Misc Feature State
# ---------------------------------------------------------------------------

_MISC_LOCK = threading.RLock()
_MANUAL_COLLECT_EVENTS = [1, 2, 3, 4, 5]

_WEAPON_REWARDS: Dict[int, Dict[int, int]] = {}
_MAP_REWARDS: Dict[int, Dict[int, int]] = {}
_FOLLOWED_STREAMERS: Dict[int, Set[int]] = {}
_GIFT_RECEIVER_REWARDED: Dict[int, List[int]] = {}
_GIFT_GIVER_REWARDED: Dict[int, List[int]] = {}
_HIDDEN_COLLECTIONS: Dict[int, List[int]] = {}
_EQUIPPED_LOADOUTS: Dict[int, List[int]] = {}
_EQUIPPED_ENTITLEMENT: Dict[int, int] = {}

_VIDEOS: List[Dict[str, Any]] = [
    {
        "video_id": 1,
        "video_url": "",
        "video_type": VideoType.HOTEST,
        "video_name": "India V1 Booyah Highlight",
        "video_sort_id": 1,
        "thumbnail_url": "",
        "hit_count": 250,
        "streamer_account_id": 20001,
        "streamer_nickname": "IndiaV1_Bot",
    },
    {
        "video_id": 2,
        "video_url": "",
        "video_type": VideoType.LIVE_NOW,
        "video_name": "Bermuda Ranked Squad Rush",
        "video_sort_id": 2,
        "thumbnail_url": "",
        "hit_count": 180,
        "streamer_account_id": 20002,
        "streamer_nickname": "Clack_Shadow",
    },
    {
        "video_id": 3,
        "video_url": "",
        "video_type": VideoType.EXPLORE,
        "video_name": "Clash Squad Ace Play",
        "video_sort_id": 3,
        "thumbnail_url": "",
        "hit_count": 120,
        "streamer_account_id": 20003,
        "streamer_nickname": "Purgatory_Pro",
    },
    {
        "video_id": 4,
        "video_url": "",
        "video_type": VideoType.TUTORIAL,
        "video_name": "One-Tap Headshot Guide",
        "video_sort_id": 4,
        "thumbnail_url": "",
        "hit_count": 95,
        "streamer_account_id": 20004,
        "streamer_nickname": "Booyah_Queen",
    },
]


def _get_weapon_states(account_id: int) -> Dict[int, int]:
    with _MISC_LOCK:
        return _WEAPON_REWARDS.setdefault(
            int(account_id),
            {
                1: EManualState.FINISHED,
                2: EManualState.FINISHED,
                3: EManualState.COLLECTING,
                5: EManualState.COLLECTING,
            },
        )


def _get_map_states(account_id: int) -> Dict[int, int]:
    with _MISC_LOCK:
        return _MAP_REWARDS.setdefault(
            int(account_id),
            {
                1: EManualState.FINISHED,
                2: EManualState.FINISHED,
                3: EManualState.COLLECTING,
            },
        )


def _get_followed_set(account_id: int) -> Set[int]:
    with _MISC_LOCK:
        return _FOLLOWED_STREAMERS.setdefault(int(account_id), {20001, 20002})


def _streamer_entry(aid: int) -> Dict[str, Any]:
    prof = state.get_player(int(aid)) or state.get_profile(int(aid))
    return {
        "account_id": int(prof.get("account_id", aid)),
        "nickname": str(prof.get("nickname", f"Player_{aid}")),
        "head_pic": int(prof.get("head_pic", 902000001)),
        "banner_id": int(prof.get("banner_id", 901000001)),
    }


def _claim_manual_reward(
    state_map: Dict[int, int],
    key: int,
    coins_reward: int,
    account_id: int,
) -> bool:
    """Transition a manual reward milestone to AWARDED once and credit coins."""
    with _MISC_LOCK:
        current = state_map.get(int(key), EManualState.FINISHED)
        if current == EManualState.AWARDED:
            return False
        state_map[int(key)] = EManualState.AWARDED
    state.grant_currency(coins=coins_reward, account_id=account_id)
    try:
        db.record_claim(account_id, "manual_reward", int(key), {"coins": coins_reward})
        db.log_action(
            account_id,
            "MANUAL_REWARD_CLAIM",
            f"Claimed manual reward #{key}: {coins_reward} coins",
            {"reward_key": key, "coins": coins_reward},
        )
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# Manual Endpoints
# ---------------------------------------------------------------------------

def _http_get_manual_collect_info(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    handler.send_proto(
        "CSGetManualCollectInfoRes",
        encode_get_manual_collect_info_res(_MANUAL_COLLECT_EVENTS),
    )


def _http_get_manual_weapon_states(handler: Any, _raw_body: bytes, account_id: int) -> None:
    wstates = _get_weapon_states(account_id)
    rows = [{"quantity_period": k, "state": v} for k, v in sorted(wstates.items())]
    handler.send_proto(
        "CSGetManualAllWeaponRewardStatesRes",
        encode_get_manual_all_weapon_reward_states_res(rows),
    )


def _http_get_manual_map_states(handler: Any, _raw_body: bytes, account_id: int) -> None:
    mstates = _get_map_states(account_id)
    rows = [{"map_id": k, "state": v} for k, v in sorted(mstates.items())]
    handler.send_proto(
        "CSGetManualAllMapRewardStatesRes",
        encode_get_manual_all_map_reward_states_res(rows),
    )


def _http_get_manual_weapon_reward(handler: Any, raw_body: bytes, account_id: int) -> None:
    period = decode_manual_weapon_reward_req(raw_body) or 1
    granted = _claim_manual_reward(_get_weapon_states(account_id), period, 500, account_id)
    payload = encode_manual_weapon_reward_res(coins=500 if granted else 0)
    handler.send_proto("CSGetManualWeaponRewardRes", payload)


def _http_get_manual_map_reward(handler: Any, raw_body: bytes, account_id: int) -> None:
    map_id = decode_manual_map_reward_req(raw_body) or 1
    granted = _claim_manual_reward(_get_map_states(account_id), map_id, 500, account_id)
    payload = encode_manual_map_reward_res(coins=500 if granted else 0)
    handler.send_proto("CSGetManualMapRewardRes", payload)


# ---------------------------------------------------------------------------
# Live / Streamer / Video Endpoints
# ---------------------------------------------------------------------------

def _http_get_follow_streamer_list(handler: Any, raw_body: bytes, account_id: int) -> None:
    _ = decode_follow_streamer_list_req(raw_body)
    followed_ids = sorted(_get_followed_set(account_id))
    rec_ids = [aid for aid in (20001, 20002, 20003, 20004, 20005, 20006) if aid not in followed_ids]
    payload = encode_follow_streamer_list_res(
        [_streamer_entry(aid) for aid in followed_ids],
        [_streamer_entry(aid) for aid in rec_ids],
    )
    handler.send_proto("CSGetFollowStreamerListRes", payload)


def _http_get_own_live_info(handler: Any, _raw_body: bytes, account_id: int) -> None:
    prof = state.get_profile(account_id)
    info = {
        "is_streamer": True,
        "nickname": prof.get("nickname", "Clack"),
        "head_pic": prof.get("head_pic", 902000001),
        "banner_id": prof.get("banner_id", 901000001),
        "fan_count": len(_get_followed_set(account_id)),
    }
    handler.send_proto("CSGetLiveInfoRes (Own)", encode_get_live_info_res(info))


def _http_get_other_live_info(handler: Any, raw_body: bytes, _account_id: int) -> None:
    target_id = decode_other_live_info_req(raw_body) or 20001
    prof = state.get_player(target_id) or state.get_profile(target_id)
    info = {
        "is_streamer": True,
        "nickname": prof.get("nickname", f"Player_{target_id}"),
        "head_pic": prof.get("head_pic", 902000001),
        "banner_id": prof.get("banner_id", 901000001),
        "fan_count": 1250,
    }
    handler.send_proto("CSGetLiveInfoRes (Other)", encode_get_live_info_res(info))


def _http_get_personal_video_zone(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_personal_video_zone_req(raw_body)
    target_id = req["other_account_id"] or 20001
    vtype = req["video_type"]
    prof = state.get_player(target_id) or state.get_profile(target_id)
    followed = target_id in _get_followed_set(account_id)

    with _MISC_LOCK:
        vids = [
            dict(v)
            for v in _VIDEOS
            if (target_id == 0 or int(v["streamer_account_id"]) == target_id)
            and (vtype in (VideoType.NONE, VideoType.ALL) or int(v["video_type"]) == vtype)
        ]
        if not vids:
            vids = [dict(v) for v in _VIDEOS[:2]]

    zone = {
        "nickname": prof.get("nickname", f"Player_{target_id}"),
        "head_pic": prof.get("head_pic", 902000001),
        "fan_count": 1250,
        "follower_type": FollowerType.YES if followed else FollowerType.NO,
        "video_list": vids,
    }
    handler.send_proto("CSGetPersonalVideoZoneRes", encode_personal_video_zone_res(zone))


def _http_get_recommended_video_list(handler: Any, raw_body: bytes, _account_id: int) -> None:
    _ = decode_recommended_video_list_req(raw_body)
    with _MISC_LOCK:
        vids = [dict(v) for v in _VIDEOS]
    handler.send_proto("CSGetRecommendedVideoListRes", encode_recommended_video_list_res(vids))


def _http_get_all_video_list_by_type(handler: Any, raw_body: bytes, _account_id: int) -> None:
    req = decode_all_video_list_by_type_req(raw_body)
    vtype = req["video_type"]
    with _MISC_LOCK:
        if vtype in (VideoType.NONE, VideoType.ALL, VideoType.NEWEST, VideoType.POPULAR):
            vids = [dict(v) for v in _VIDEOS]
        else:
            vids = [dict(v) for v in _VIDEOS if int(v["video_type"]) == vtype]
    handler.send_proto("CSGetAllVideoListByVideoTypeRes", encode_all_video_list_by_type_res(vids))


def _http_update_video_hit_count(handler: Any, raw_body: bytes, _account_id: int) -> None:
    req = decode_update_video_hit_count_req(raw_body)
    vid_id = int(req["video_id"])
    with _MISC_LOCK:
        for v in _VIDEOS:
            if int(v["video_id"]) == vid_id:
                v["hit_count"] = int(v.get("hit_count", 0)) + 1
                break
    handler.send_proto("Empty (UpdateVideoHitCount)", b"")


def _http_get_live_table_names(handler: Any, raw_body: bytes, _account_id: int) -> None:
    lang = decode_live_table_names_req(raw_body)
    tabs = [
        {"id": VideoType.HOTEST, "content": "Hottest", "language": lang},
        {"id": VideoType.LIVE_NOW, "content": "Live Now", "language": lang},
        {"id": VideoType.EXPLORE, "content": "Explore", "language": lang},
        {"id": VideoType.TUTORIAL, "content": "Tutorial", "language": lang},
    ]
    handler.send_proto("CSGetLiveTableNamesRes", encode_live_table_names_res(tabs))


def _http_update_account_follow_stat(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_update_account_follow_stat_req(raw_body)
    sid = int(req["streamer_id"])
    if sid > 0:
        followed = _get_followed_set(account_id)
        with _MISC_LOCK:
            if req["follower_type"] == FollowerType.YES:
                followed.add(sid)
            else:
                followed.discard(sid)
    handler.send_proto("Empty (UpdateAccountFollowStat)", b"")


def _http_get_single_follow_type(handler: Any, raw_body: bytes, account_id: int) -> None:
    streamer_id = get_varint(decode_proto(raw_body), 1, 0)
    is_followed = streamer_id in _get_followed_set(account_id)
    ftype = FollowerType.YES if is_followed else FollowerType.NO
    handler.send_proto("CSGetSingleFollowTypeRes", encode_uint32(1, ftype))


# ---------------------------------------------------------------------------
# GiftRank Endpoints
# ---------------------------------------------------------------------------

def _http_get_gift_rank_desc(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    desc = {
        "rank_id": 1,
        "rank_name": "India V1 Gift Ranking",
        "is_time_show": True,
        "giver_item_id": 203000001,
        "receiver_item_id": 204000001,
        "gift_ratio": 10,
    }
    details = [
        {
            "gift_rank_type": GiftRankType.RECEIVER,
            "gift_rewards": [
                {
                    "rank_tab_id": GiftRankType.RECEIVER,
                    "gift_item_num": 10,
                    "reward_item_type": AwardType.GEMS,
                    "reward_item_name": "50 Diamonds",
                    "reward_item_id": 0,
                    "reward_item_num": 50,
                }
            ],
        },
        {
            "gift_rank_type": GiftRankType.GIVER,
            "gift_rewards": [
                {
                    "rank_tab_id": GiftRankType.GIVER,
                    "gift_item_num": 10,
                    "reward_item_type": AwardType.GEMS,
                    "reward_item_name": "50 Diamonds",
                    "reward_item_id": 0,
                    "reward_item_num": 50,
                }
            ],
        },
    ]
    handler.send_proto("CSGetGiftRankDescRes", encode_get_gift_rank_desc_res(desc, details))


def _http_get_gift_rank_reward_info(handler: Any, raw_body: bytes, account_id: int) -> None:
    _ = decode_gift_rank_reward_info_req(raw_body)
    aid = int(account_id)
    with _MISC_LOCK:
        recv = list(_GIFT_RECEIVER_REWARDED.get(aid, []))
        give = list(_GIFT_GIVER_REWARDED.get(aid, []))
    handler.send_proto("CSGetGiftRankRewardInfoRes", encode_gift_rank_reward_info_res(recv, give))


def _http_get_gift_rank_reward(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_get_gift_rank_reward_req(raw_body)
    aid = int(account_id)
    milestone = int(req["gift_item_num"])
    is_giver = int(req["gift_rank_type"]) == GiftRankType.GIVER

    with _MISC_LOCK:
        store = _GIFT_GIVER_REWARDED if is_giver else _GIFT_RECEIVER_REWARDED
        rewarded = store.setdefault(aid, [])
        newly_claimed = milestone not in rewarded
        if newly_claimed:
            rewarded.append(milestone)
        snapshot = list(rewarded)

    if newly_claimed:
        state.grant_currency(gems=50, account_id=aid)
        try:
            claim_type = "gift_rank_giver" if is_giver else "gift_rank_receiver"
            db.record_claim(aid, claim_type, milestone, {"gems": 50})
            db.log_action(
                aid,
                "GIFT_RANK_CLAIM",
                f"Claimed gift rank milestone #{milestone}",
                {"milestone": milestone, "is_giver": is_giver, "gems": 50},
            )
        except Exception:
            pass

    award = {"award_type": AwardType.GEMS, "award_id": 0, "award_num": 50 if newly_claimed else 0}
    handler.send_proto("CSGetGiftRankRewardRes", encode_get_gift_rank_reward_res(award, snapshot))


# ---------------------------------------------------------------------------
# MysteryBonus & WinnerTakesAll Endpoints
# ---------------------------------------------------------------------------

def _http_get_mystery_bonus(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    handler.send_proto("CSMysteryBonusRes", encode_mystery_bonus_res())


def _http_mystery_bonus_spin(handler: Any, _raw_body: bytes, _account_id: int) -> None:
    handler.send_proto("CSMysteryBonusSpinRes", encode_mystery_bonus_spin_res(bonus_percent=100))


def _http_get_wta_info(handler: Any, _raw_body: bytes, account_id: int) -> None:
    prof = state.get_profile(account_id)
    payload = encode_get_winner_takes_all_info_res(
        account_id=account_id,
        wta_desc={"region": prof.get("region", "DEFAULT"), "chip_cost": 100, "diamond_cost": 10},
    )
    handler.send_proto("CSGetWinnerTakesAllInfoRes", payload)


# ---------------------------------------------------------------------------
# CollectionHide, Loadout & Entitlement Endpoints
# ---------------------------------------------------------------------------

def _http_get_collection_hide(handler: Any, _raw_body: bytes, account_id: int) -> None:
    with _MISC_LOCK:
        hidden = list(_HIDDEN_COLLECTIONS.get(int(account_id), []))
    handler.send_proto("CSGetHideCollectionsRes", encode_get_hide_collections_res(hidden))


def _http_set_collection_hide(handler: Any, raw_body: bytes, account_id: int) -> None:
    ids = get_packed_varints(decode_proto(raw_body), 1)
    with _MISC_LOCK:
        _HIDDEN_COLLECTIONS[int(account_id)] = [int(x) for x in ids]
        hidden = list(_HIDDEN_COLLECTIONS[int(account_id)])
    handler.send_proto("CSGetHideCollectionsRes", encode_get_hide_collections_res(hidden))


def _http_choose_loadout(handler: Any, raw_body: bytes, account_id: int) -> None:
    req = decode_choose_loadout_req(raw_body)
    loadouts = [int(x) for x in req["loadouts"]]
    with _MISC_LOCK:
        _EQUIPPED_LOADOUTS[int(account_id)] = loadouts
    for lid in loadouts:
        if lid > 0:
            state.unlock_item(lid)
    handler.send_proto("Empty (ChooseLoadout)", b"")


def _http_choose_entitlement(handler: Any, raw_body: bytes, account_id: int) -> None:
    ent_id = get_varint(decode_proto(raw_body), 1, 0)
    with _MISC_LOCK:
        _EQUIPPED_ENTITLEMENT[int(account_id)] = int(ent_id)
    handler.send_proto("Empty (ChooseEntitlement)", b"")


# ---------------------------------------------------------------------------
# Dispatch Table & Entrypoint
# ---------------------------------------------------------------------------

_MISC_ROUTES: Dict[str, Callable[[Any, bytes, int], None]] = {
    # Manual
    "GetManualCollectInfo": _http_get_manual_collect_info,
    "GetManualAllWeaponRewardStates": _http_get_manual_weapon_states,
    "GetManualAllMapRewardStates": _http_get_manual_map_states,
    "GetManualWeaponReward": _http_get_manual_weapon_reward,
    "GetManualMapReward": _http_get_manual_map_reward,
    # Live / Streamer / Video
    "GetFollowStreamerList": _http_get_follow_streamer_list,
    "GetOwnLiveInfo": _http_get_own_live_info,
    "GetOtherLiveInfo": _http_get_other_live_info,
    "GetPersonalVideoZone": _http_get_personal_video_zone,
    "GetRecommendedVideoList": _http_get_recommended_video_list,
    "GetAllVideoListByVideoType": _http_get_all_video_list_by_type,
    "UpdateVideoHitCount": _http_update_video_hit_count,
    "GetLiveTableNames": _http_get_live_table_names,
    "UpdateAccountFollowStat": _http_update_account_follow_stat,
    "GetSingleFollowType": _http_get_single_follow_type,
    # GiftRank
    "GetGiftRankDesc": _http_get_gift_rank_desc,
    "GetGiftRankRewardInfo": _http_get_gift_rank_reward_info,
    "GetGiftRankReward": _http_get_gift_rank_reward,
    # MysteryBonus & WinnerTakesAll
    "GetMysteryBonus": _http_get_mystery_bonus,
    "MysteryBonusSpin": _http_mystery_bonus_spin,
    "GetWinnerTakesAllInfo": _http_get_wta_info,
    # CollectionHide, Loadout, Entitlement
    "GetCollectionHide": _http_get_collection_hide,
    "SetCollectionHide": _http_set_collection_hide,
    "ChooseLoadout": _http_choose_loadout,
    "ChooseEntitlement": _http_choose_entitlement,
}

MISC_ENDPOINTS = tuple(_MISC_ROUTES.keys())


def handle_misc_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Manual, Live/Video, GiftRank, MysteryBonus, WTA, CollectionHide,
    Loadout, and Entitlement HTTP endpoints. Returns True if handled.
    """
    _ = client_ip
    endpoint = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    fn = _MISC_ROUTES.get(endpoint)
    if fn is None:
        return False
    fn(handler, raw_body or b"", account_id)
    return True


handle_misc_post = handle_misc_request
