"""
Protobuf codecs and OB17 (Free Fire 1.39) data tables for Elite Pass & IAP/Cards.

All field tags, wire types, packed repeated flags, and enums are verified directly
against Free Fire 1.39 libil2cpp.so and decrypted client ConfigAsset CSVs
(EPEventSetting, EPUnlock, EPChallenge, EPDailyChallenge, EPMaxReward).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from proto.decoder import (
    decode_proto,
    get_bool,
    get_string,
    get_submessages,
    get_varint,
)
from proto.encoder import (
    encode_bool,
    encode_int64,
    encode_packed_uint32,
    encode_string,
    encode_submessage,
    encode_uint32,
)


class EPTargetStatus:
    """proto.EPTarget_Status enum."""

    ONGOING = 0
    REACHED = 1
    CLAIMED = 2


class ChallengeType:
    """COW.ChallengeType enum used in ChallengeStatus.challenge_type."""

    NONE = -1
    DAILY = 0
    ELITE = 1
    VETERAN = 2


class AwardType:
    """EInventory.AwardType enum."""

    NONE = 0
    ITEM = 1
    COINS = 2
    GEMS = 3
    SKILL = 4
    EXP = 5
    ACTIVENESS = 6


# Active OB17 (Free Fire 1.39) Elite Pass event constants from EPEventSetting / EPMaxReward
DEFAULT_EP_EVENT_ID = 16
DEFAULT_EP_BADGE_ITEM_ID = 1001000017
DEFAULT_FP_CHALLENGE_ITEM = 1002000017
DEFAULT_GOLD_LIMIT_IMPROVED = 100
DEFAULT_BADGE_COUNT = 250
EP_MAX_REWARD_STEP = 25

# (unlock_id, require_badges, fp_award=(type, id, num)|None, ep_award=(type, id, num)|None)
EP16_UNLOCKS: Tuple[
    Tuple[int, int, Optional[Tuple[int, int, int]], Optional[Tuple[int, int, int]]],
    ...,
] = (
    (1700, 0, None, (1, 203000556, 1)),
    (1701, 5, (1, 902000196, 1), (1, 802000001, 1)),
    (1702, 10, (1, 1002000017, 1), (1, 907001701, 1)),
    (1703, 15, None, (1, 905000058, 1)),
    (1704, 20, (1, 1307000001, 1), (1, 500000006, 5)),
    (1705, 25, None, (1, 301020933, 1)),
    (1706, 30, (1, 802000000, 1), (1, 901000178, 1)),
    (1707, 35, None, (2, 0, 500)),
    (1708, 40, (1, 1307000001, 1), (1, 902000194, 1)),
    (1709, 45, None, (1, 301022351, 1)),
    (1710, 50, (1, 802000001, 1), (1, 710000392, 1)),
    (1711, 55, None, (1, 1307000001, 3)),
    (1712, 60, (1, 430000042, 1), (1, 802000001, 1)),
    (1713, 65, None, (1, 301020449, 1)),
    (1714, 70, (1, 804000004, 1), (2, 0, 500)),
    (1715, 75, None, (1, 800000018, 100)),
    (1716, 80, (1, 1307000001, 1), (1, 907001702, 1)),
    (1717, 85, None, (1, 500000007, 5)),
    (1718, 90, (2, 0, 300), (1, 802000001, 1)),
    (1719, 95, None, (1, 1307000001, 3)),
    (1720, 100, (1, 500000004, 3), (1, 203000557, 1)),
    (1721, 105, None, (1, 301020930, 1)),
    (1722, 110, (1, 203000558, 1), (2, 0, 500)),
    (1723, 115, None, (1, 901000177, 1)),
    (1724, 120, (1, 500000006, 3), (1, 500000004, 3)),
    (1725, 125, None, (1, 906000064, 1)),
    (1726, 130, (1, 802000000, 1), (1, 800000017, 100)),
    (1727, 135, None, (1, 902000195, 1)),
    (1728, 140, (1, 500000007, 3), (1, 802000001, 1)),
    (1729, 145, None, (1, 301020447, 1)),
    (1730, 150, (1, 901000179, 1), (1, 903000035, 1)),
    (1731, 155, None, (1, 301020932, 1)),
    (1732, 160, (2, 0, 500), (1, 1307000001, 3)),
    (1733, 165, None, (1, 906000065, 1)),
    (1734, 170, (1, 430000045, 1), (1, 909000028, 1)),
    (1735, 175, None, (1, 301020931, 1)),
    (1736, 180, (1, 500000005, 3), (1, 808000001, 1)),
    (1737, 185, None, (1, 500000008, 5)),
    (1738, 190, (1, 802000000, 1), (1, 804000004, 1)),
    (1739, 195, None, (2, 0, 500)),
    (1740, 200, (1, 1307000001, 3), (1, 904000070, 1)),
    (1741, 205, None, (1, 812000001, 1)),
    (1742, 210, (1, 802000000, 3), (1, 1307000001, 3)),
    (1743, 215, None, (1, 800000019, 100)),
    (1744, 220, (1, 500000008, 3), (1, 500000005, 5)),
    (1799, 225, (1, 904000069, 1), (1, 710000391, 1)),
)

EP16_UNLOCK_MAP: Dict[int, Dict[str, Any]] = {
    uid: {
        "unlock_id": uid,
        "require_num": req_num,
        "fp_award": fp_award,
        "ep_award": ep_award,
    }
    for uid, req_num, fp_award, ep_award in EP16_UNLOCKS
}

# Exact OB17 daily (date=1) & EP/FP challenge definitions:
# (cid, ch_type, count_type, match_mode, game_mode, player_count, role_cond, cond_type, sub_cond, target, badges, special, date)
_RAW_EP16_CHALLENGES: Tuple[
    Tuple[int, int, int, int, int, int, Tuple[int, ...], int, Tuple[int, ...], int, int, int, int],
    ...,
] = (
    # Daily challenges (EPDailyChallenge.csv EPEventId=16 Date=1)
    (1, 0, 2, 0, 0, 0, (), 18, (), 25, 1, 0, 1),
    (2, 0, 2, 0, 0, 0, (), 18, (), 35, 1, 0, 1),
    (3, 0, 2, 0, 1, 0, (), 14, (), 3, 1, 0, 1),
    (4, 0, 2, 2, 0, 0, (), 17, (15,), 2, 1, 0, 1),
    (5, 0, 2, 0, 1, 0, (), 3, (), 5, 1, 0, 1),
    (36, 0, 2, 0, 0, 0, (), 6, (701, 702, 703, 707), 1, 1, 3, 1),
    # Elite & Veteran challenges (EPChallenge.csv EPEventId=16)
    (43, 1, 2, 2, 0, 0, (), 35, (0,), 8000, 8, 0, 0),
    (44, 1, 2, 0, 0, 0, (), 19, (), 16, 8, 0, 0),
    (45, 1, 2, 0, 0, 0, (), 25, (), 20, 8, 0, 0),
    (46, 1, 2, 0, 1, 0, (), 3, (), 60, 8, 0, 0),
    (47, 1, 2, 0, 1, 1, (), 24, (), 14, 8, 0, 0),
    (48, 1, 2, 0, 0, 0, (), 33, (), 1000, 8, 0, 0),
    (49, 1, 2, 0, 1, 0, (), 20, (300,), 11, 8, 0, 0),
    (50, 1, 2, 0, 1, 0, (), 41, (), 20, 8, 0, 0),
    (51, 1, 2, 0, 1, 0, (), 11, (), 36, 8, 0, 0),
    (52, 1, 2, 0, 1, 0, (), 13, (), 12, 8, 0, 0),
    (53, 1, 2, 2, 0, 0, (), 3, (), 30, 8, 0, 0),
    (54, 1, 2, 0, 1, 0, (), 16, (), 6, 8, 0, 0),
    (55, 2, 2, 0, 1, 0, (), 2, (), 12, 5, 0, 0),
    (56, 2, 1, 0, 0, 0, (), 6, (701, 702, 703, 707), 6, 5, 0, 0),
    (57, 2, 2, 0, 1, 0, (), 8, (), 22, 5, 0, 0),
    (58, 2, 2, 0, 1, 0, (), 4, (), 12000, 5, 0, 0),
    (59, 2, 2, 0, 1, 0, (), 1, (4,), 17, 5, 0, 0),
    (60, 2, 2, 2, 0, 4, (), 3, (), 30, 5, 0, 0),
    (61, 2, 2, 0, 1, 2, (), 31, (), 16, 5, 0, 0),
    (62, 2, 2, 0, 1, 0, (), 1, (601,), 15, 5, 0, 0),
    (63, 2, 2, 0, 1, 0, (), 17, (3,), 10, 5, 0, 0),
    (64, 2, 2, 0, 1, 0, (), 38, (10,), 3, 5, 0, 0),
    (65, 2, 1, 0, 1, 0, (), 3, (), 7, 5, 0, 0),
    (66, 2, 2, 2, 0, 0, (), 17, (15,), 15, 5, 0, 0),
    (67, 2, 2, 0, 1, 0, (), 34, (6,), 11, 5, 0, 0),
    (
        68,
        2,
        1,
        0,
        1,
        4,
        (
            102000001, 102000002, 102000003, 102000004, 102000005, 102000006, 102000007,
            102000008, 102000009, 102000010, 102000011, 102000012, 102000013, 102000014,
        ),
        31,
        (),
        4,
        5,
        0,
        0,
    ),
    (69, 2, 2, 0, 1, 0, (), 16, (), 10, 5, 0, 0),
    (70, 1, 2, 0, 1, 0, (), 4, (), 2000, 4, 3, 0),
    (71, 1, 2, 0, 1, 0, (), 11, (), 5, 4, 6, 0),
    (72, 1, 2, 2, 0, 0, (), 3, (), 5, 4, 9, 0),
    (73, 2, 2, 0, 1, 0, (), 3, (), 6, 3, 3, 0),
    (74, 2, 2, 0, 1, 1, (), 24, (), 1, 3, 6, 0),
    (75, 2, 2, 0, 0, 0, (), 6, (701, 702, 703, 707), 5, 3, 9, 0),
)

EP16_CHALLENGES: Tuple[Dict[str, Any], ...] = tuple(
    {
        "challenge_id": cid,
        "challenge_type": ch_type,
        "count_type": count_type,
        "match_mode": match_mode,
        "game_mode": game_mode,
        "player_count": player_count,
        "role_condition": list(role_cond),
        "condition_type": cond_type,
        "sub_condition": list(sub_cond),
        "target_value": target,
        "award_badges": badges,
        "special_challenge": special,
        "date": date,
    }
    for (
        cid,
        ch_type,
        count_type,
        match_mode,
        game_mode,
        player_count,
        role_cond,
        cond_type,
        sub_cond,
        target,
        badges,
        special,
        date,
    ) in _RAW_EP16_CHALLENGES
)

EP16_CHALLENGE_MAP: Dict[int, Dict[str, Any]] = {
    ch["challenge_id"]: ch for ch in EP16_CHALLENGES
}


def encode_reward_status(unlock_id: int, status: int, is_ep: int) -> bytes:
    """Encode proto.RewardStatus: 1=unlock_id, 2=status, 3=is_ep (0=FP, 1=EP)."""
    return b"".join((
        encode_uint32(1, unlock_id),
        encode_uint32(2, status),
        encode_uint32(3, is_ep),
    ))


def encode_challenge_cdt(
    condition_type: int,
    current_value: int,
    target_value: int,
    sub_condition: Sequence[int] = (),
) -> bytes:
    """Encode proto.ChallengeCdt: 1=condition_type, 2=current_value, 3=target_value, 4=packed sub_condition."""
    parts = [
        encode_uint32(1, condition_type),
        encode_uint32(2, current_value),
        encode_uint32(3, target_value),
    ]
    if sub_condition:
        parts.append(encode_packed_uint32(4, list(sub_condition)))
    return b"".join(parts)


def encode_challenge_status(ch: Dict[str, Any]) -> bytes:
    """Encode proto.ChallengeStatus (tags 1..12, tag 4 packed)."""
    parts = [
        encode_uint32(1, int(ch.get("challenge_id", 0))),
        encode_uint32(2, int(ch.get("status", EPTargetStatus.ONGOING))),
        encode_uint32(3, int(ch.get("update_time", int(time.time())))),
    ]
    role_cond = ch.get("role_condition") or ()
    if role_cond:
        parts.append(encode_packed_uint32(4, [int(x) for x in role_cond]))
    parts.extend((
        encode_uint32(5, int(ch.get("count_type", 2))),
        encode_uint32(6, int(ch.get("game_mode", 0))),
        encode_uint32(7, int(ch.get("player_count", 0))),
    ))
    conditions = ch.get("conditions")
    if conditions is None:
        conditions = [{
            "condition_type": int(ch.get("condition_type", 0)),
            "current_value": int(ch.get("current_value", 0)),
            "target_value": int(ch.get("target_value", 0)),
            "sub_condition": ch.get("sub_condition") or (),
        }]
    for cdt in conditions:
        parts.append(encode_submessage(8, encode_challenge_cdt(
            condition_type=int(cdt.get("condition_type", 0)),
            current_value=int(cdt.get("current_value", 0)),
            target_value=int(cdt.get("target_value", 0)),
            sub_condition=cdt.get("sub_condition") or (),
        )))
    parts.extend((
        encode_uint32(9, int(ch.get("match_mode", 0))),
        encode_uint32(10, int(ch.get("date", 0))),
        encode_uint32(11, int(ch.get("challenge_type", ChallengeType.ELITE))),
        encode_uint32(12, int(ch.get("special_challenge", 0))),
    ))
    return b"".join(parts)


def encode_get_ep_info_res(
    owned_pass: bool = True,
    rewards: Iterable[Tuple[int, int, int]] = (),
    challenges: Iterable[Dict[str, Any]] = (),
    ep_event_id: int = DEFAULT_EP_EVENT_ID,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    ep_badge: int = DEFAULT_EP_BADGE_ITEM_ID,
    gold_limit_improved: int = DEFAULT_GOLD_LIMIT_IMPROVED,
    fp_challenge_item: int = DEFAULT_FP_CHALLENGE_ITEM,
    owned_fp_challenge: bool = True,
    purchase_badge_count_today: int = 0,
    week: int = 4,
    daily_reset_time: Optional[int] = None,
    epid_preorder: int = 0,
    ep_preorder_start_time: int = 0,
    ep_preorder_end_time: int = 0,
    daily_challenge_completed_cnt: int = 0,
    elite_challenge_completed_cnt: int = 0,
    veteran_challenge_completed_cnt: int = 0,
    subscription_start_time: Optional[int] = None,
    subscription_end_time: Optional[int] = None,
    purchase_ep_count: int = 1,
    ep_max_reward_claimed_badge: int = 0,
) -> bytes:
    """Encode proto.CSGetEPInfoRes (tags 1..23)."""
    now = int(time.time())
    if start_time is None:
        start_time = now - 86400 * 7
    if end_time is None:
        end_time = now + 86400 * 30
    if daily_reset_time is None:
        daily_reset_time = now + 86400
    if subscription_start_time is None:
        subscription_start_time = now - 86400 * 7
    if subscription_end_time is None:
        subscription_end_time = now + 86400 * 30

    parts = [encode_bool(1, owned_pass)]
    for unlock_id, status, is_ep in rewards:
        parts.append(encode_submessage(2, encode_reward_status(unlock_id, status, is_ep)))
    for ch in challenges:
        parts.append(encode_submessage(3, encode_challenge_status(ch)))

    parts.extend((
        encode_uint32(4, ep_event_id),
        encode_int64(5, start_time),
        encode_int64(6, end_time),
        encode_uint32(7, ep_badge),
        encode_uint32(8, gold_limit_improved),
        encode_uint32(9, fp_challenge_item),
        encode_bool(10, owned_fp_challenge),
        encode_uint32(11, purchase_badge_count_today),
        encode_uint32(12, week),
        encode_int64(13, daily_reset_time),
        encode_uint32(14, epid_preorder),
        encode_int64(15, ep_preorder_start_time),
        encode_int64(16, ep_preorder_end_time),
        encode_uint32(17, daily_challenge_completed_cnt),
        encode_uint32(18, elite_challenge_completed_cnt),
        encode_uint32(19, veteran_challenge_completed_cnt),
        encode_int64(20, subscription_start_time),
        encode_int64(21, subscription_end_time),
        encode_uint32(22, purchase_ep_count),
        encode_uint32(23, ep_max_reward_claimed_badge),
    ))
    return b"".join(parts)


def encode_get_basic_ep_info_res(
    owned_pass: bool = True,
    ep_event_id: int = DEFAULT_EP_EVENT_ID,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    ep_badge: int = DEFAULT_EP_BADGE_ITEM_ID,
    gold_limit_improved: int = DEFAULT_GOLD_LIMIT_IMPROVED,
    owned_fp_challenge: bool = True,
    badge_cnt: int = DEFAULT_BADGE_COUNT,
) -> bytes:
    """Encode proto.GetBasicEPInfoRes (tags 1..8)."""
    now = int(time.time())
    return b"".join((
        encode_bool(1, owned_pass),
        encode_uint32(2, ep_event_id),
        encode_int64(3, now - 86400 * 7 if start_time is None else start_time),
        encode_int64(4, now + 86400 * 30 if end_time is None else end_time),
        encode_uint32(5, ep_badge),
        encode_uint32(6, gold_limit_improved),
        encode_bool(7, owned_fp_challenge),
        encode_uint32(8, badge_cnt),
    ))


def encode_basic_ep_info(
    ep_event_id: int = DEFAULT_EP_EVENT_ID,
    owned_pass: bool = True,
    ep_badge: int = DEFAULT_EP_BADGE_ITEM_ID,
    badge_cnt: int = DEFAULT_BADGE_COUNT,
) -> bytes:
    """Encode proto.BasicEPInfo (tags 1..4)."""
    return b"".join((
        encode_uint32(1, ep_event_id),
        encode_bool(2, owned_pass),
        encode_uint32(3, ep_badge),
        encode_uint32(4, badge_cnt),
    ))


def encode_card_price(card_num: int, single_price: int, all_price: int) -> bytes:
    """Encode proto.CardPrice: 1=card_num, 2=single_price, 3=all_price."""
    return b"".join((
        encode_uint32(1, card_num),
        encode_uint32(2, single_price),
        encode_uint32(3, all_price),
    ))


def encode_award_from_card(
    weight: int,
    award_type: int,
    award_id: int,
    award_num: int,
    award_level: int = 1,
    from_card_rank: int = 1,
) -> bytes:
    """Encode proto.AwardFromCard (tags 1..6)."""
    return b"".join((
        encode_uint32(1, weight),
        encode_uint32(2, award_type),
        encode_uint32(3, award_id),
        encode_uint32(4, award_num),
        encode_uint32(5, award_level),
        encode_uint32(6, from_card_rank),
    ))


def encode_card_image_desc(card_id: int, img_url: str = "") -> bytes:
    """Encode proto.CardImageDesc: 1=id, 2=img_url."""
    parts = [encode_uint32(1, card_id)]
    if img_url:
        parts.append(encode_string(2, img_url))
    return b"".join(parts)


def encode_pvp_card_info(
    enable_flip: bool = True,
    win_award: bool = True,
    card_prices: Optional[Sequence[Tuple[int, int, int]]] = None,
    awards: Optional[Sequence[Tuple[int, int, int, int, int, int]]] = None,
    flip_count_today: int = 0,
    flip_count_max: int = 4,
    back_image_url: str = "",
) -> bytes:
    """Encode proto.PVPCardInfo (tags 1..7)."""
    if card_prices is None:
        card_prices = ((1, 0, 0), (2, 10, 30), (3, 15, 45), (4, 20, 60))
    if awards is None:
        awards = (
            (100, AwardType.COINS, 0, 100, 1, 1),
            (50, AwardType.ITEM, 802000000, 1, 1, 2),
        )
    parts = [
        encode_bool(1, enable_flip),
        encode_bool(2, win_award),
    ]
    for card_num, single_p, all_p in card_prices:
        parts.append(encode_submessage(3, encode_card_price(card_num, single_p, all_p)))
    for w, atype, aid, anum, alvl, rank in awards:
        parts.append(encode_submessage(4, encode_award_from_card(w, atype, aid, anum, alvl, rank)))
    parts.append(encode_uint32(5, flip_count_today))
    parts.append(encode_uint32(6, flip_count_max))
    if back_image_url:
        parts.append(encode_string(7, back_image_url))
    return b"".join(parts)


def encode_pve_card_info(
    enable_flip: bool = True,
    card_prices: Optional[Sequence[Tuple[int, int, int]]] = None,
    awards: Optional[Sequence[Tuple[int, int, int, int, int, int]]] = None,
    flip_count_today: int = 0,
    flip_count_max: int = 4,
    back_images: Sequence[Tuple[int, str]] = (),
    match_rank: int = 1,
) -> bytes:
    """Encode proto.PVECardInfo (tags 1..7)."""
    if card_prices is None:
        card_prices = ((1, 0, 0), (2, 10, 30))
    if awards is None:
        awards = ((100, AwardType.COINS, 0, 100, 1, 1),)
    parts = [encode_bool(1, enable_flip)]
    for card_num, single_p, all_p in card_prices:
        parts.append(encode_submessage(2, encode_card_price(card_num, single_p, all_p)))
    for w, atype, aid, anum, alvl, rank in awards:
        parts.append(encode_submessage(3, encode_award_from_card(w, atype, aid, anum, alvl, rank)))
    parts.append(encode_uint32(4, flip_count_today))
    parts.append(encode_uint32(5, flip_count_max))
    for cid, url in back_images:
        parts.append(encode_submessage(6, encode_card_image_desc(cid, url)))
    parts.append(encode_uint32(7, match_rank))
    return b"".join(parts)


def encode_get_cards_res(
    pvp_cards: Optional[bytes] = None,
    pve_cards: Optional[bytes] = None,
) -> bytes:
    """Encode proto.CSGetCardsRes: 1=pvp_cards, 2=pve_cards."""
    return b"".join((
        encode_submessage(1, encode_pvp_card_info() if pvp_cards is None else pvp_cards),
        encode_submessage(2, encode_pve_card_info() if pve_cards is None else pve_cards),
    ))


def encode_account_iap_info_res(
    pool_id: int = 1,
    store_id: int = 1,
    create_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> bytes:
    """Encode proto.CSGetAccountIAPInfoRes: 1=pool_id, 2=store_id, 3=create_time, 4=end_time."""
    now = int(time.time())
    return b"".join((
        encode_uint32(1, pool_id),
        encode_uint32(2, store_id),
        encode_uint32(3, now - 86400 if create_time is None else create_time),
        encode_uint32(4, now + 86400 * 30 if end_time is None else end_time),
    ))


def encode_get_cards_and_iap_info_res(
    cards_res: Optional[bytes] = None,
    iap_info_res: Optional[bytes] = None,
) -> bytes:
    """Encode proto.GetCardsAndIAPInfoRes: 1=cards_res, 2=iap_info_res."""
    return b"".join((
        encode_submessage(1, encode_get_cards_res() if cards_res is None else cards_res),
        encode_submessage(2, encode_account_iap_info_res() if iap_info_res is None else iap_info_res),
    ))


def encode_ep_subscription_bonus_status_res(is_got: bool = False) -> bytes:
    """Encode proto.CSGetEPSubscriptionBonusStatusRes: 1=is_got."""
    return encode_bool(1, is_got)


def encode_ep_claim_reward_res() -> bytes:
    """Encode proto.CSEPClaimRewardRes (empty message)."""
    return b""


def encode_ep_claim_badge_res() -> bytes:
    """Encode proto.CSEPClaimBadgeRes (empty message)."""
    return b""


def encode_ep_purchase_res() -> bytes:
    """Encode proto.CSEPPurchaseRes (empty message)."""
    return b""


def encode_ep_purchase_badge_res() -> bytes:
    """Encode proto.CSEPPurchaseBadgeRes (empty message)."""
    return b""


def encode_ep_preorder_res() -> bytes:
    """Encode proto.CSEPPreorderRes (empty message)."""
    return b""


def encode_ep_video_ad_portal_res(video_url: str = "") -> bytes:
    """Encode proto.CSEPVideoAdPortalRes: 1=video_url."""
    return encode_string(1, video_url)


def decode_ep_claim_reward_req(data: bytes) -> Dict[str, Any]:
    """Decode proto.CSEPClaimRewardReq: 1=List<unlock>{1:id, 2:is_ep}, 2=nickname, 3=claim_max_reward."""
    fields = decode_proto(data)
    unlock_rewards: List[Dict[str, int]] = []
    for uf in get_submessages(fields, 1):
        unlock_rewards.append({
            "id": get_varint(uf, 1, 0),
            "is_ep": get_varint(uf, 2, 0),
        })
    return {
        "unlock_rewards": unlock_rewards,
        "nickname": get_string(fields, 2, ""),
        "claim_max_reward": get_bool(fields, 3, False),
    }


def decode_ep_claim_badge_req(data: bytes) -> Dict[str, int]:
    """Decode proto.CSEPClaimBadgeReq: 1=challenge_id."""
    fields = decode_proto(data)
    return {"challenge_id": get_varint(fields, 1, 0)}


def decode_ep_purchase_req(data: bytes) -> Dict[str, bool]:
    """Decode proto.CSEPPurchaseReq: 1=is_bundle."""
    fields = decode_proto(data)
    return {"is_bundle": get_bool(fields, 1, False)}


def decode_ep_purchase_badge_req(data: bytes) -> Dict[str, int]:
    """Decode proto.CSEPPurchaseBadgeReq: 1=count."""
    fields = decode_proto(data)
    return {"count": get_varint(fields, 1, 0)}


def decode_ep_video_ad_portal_req(data: bytes) -> Dict[str, str]:
    """Decode proto.CSEPVideoAdPortalReq: 1=language."""
    fields = decode_proto(data)
    return {"language": get_string(fields, 1, "")}
