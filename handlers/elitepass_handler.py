"""
HTTP request handlers for Free Fire 1.39 Elite Pass & IAP/Cards.

Handles:
- /GetEPInfo                     -> proto.CSGetEPInfoRes
- /GetCardsAndIAPInfo            -> proto.GetCardsAndIAPInfoRes
- /GetEPSubscriptionBonusStatus  -> proto.CSGetEPSubscriptionBonusStatusRes
- /ClaimEPReward & /EPClaimReward -> proto.CSEPClaimRewardRes
- /EPClaimBadge                  -> proto.CSEPClaimBadgeRes
- /EPPurchaseBadge               -> proto.CSEPPurchaseBadgeRes
- /EPPurchase                    -> proto.CSEPPurchaseRes
- /EPPreorder                    -> proto.CSEPPreorderRes
- /EPVideoAdPortal               -> proto.CSEPVideoAdPortalRes

Integrates with core.state.state for persistent Elite Pass unlock state,
badge counts, currency/item grants, and claimed reward tracking.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.elitepass_models import (
    AwardType,
    ChallengeType,
    DEFAULT_BADGE_COUNT,
    DEFAULT_EP_BADGE_ITEM_ID,
    DEFAULT_EP_EVENT_ID,
    DEFAULT_FP_CHALLENGE_ITEM,
    DEFAULT_GOLD_LIMIT_IMPROVED,
    EP16_CHALLENGE_MAP,
    EP16_CHALLENGES,
    EP16_UNLOCKS,
    EP16_UNLOCK_MAP,
    EPTargetStatus,
    EP_MAX_REWARD_STEP,
    decode_ep_claim_badge_req,
    decode_ep_claim_reward_req,
    decode_ep_purchase_badge_req,
    decode_ep_purchase_req,
    decode_ep_video_ad_portal_req,
    encode_ep_claim_badge_res,
    encode_ep_claim_reward_res,
    encode_ep_preorder_res,
    encode_ep_purchase_badge_res,
    encode_ep_purchase_res,
    encode_ep_subscription_bonus_status_res,
    encode_ep_video_ad_portal_res,
    encode_get_cards_and_iap_info_res,
    encode_get_ep_info_res,
)

ELITEPASS_ENDPOINTS = frozenset({
    "GetEPInfo",
    "GetCardsAndIAPInfo",
    "GetEPSubscriptionBonusStatus",
    "ClaimEPReward",
    "EPClaimReward",
    "EPClaimBadge",
    "EPPurchaseBadge",
    "EPPurchase",
    "EPPreorder",
    "EPVideoAdPortal",
})

_EP_MAX_REWARD_ITEM_ID = 400000466

_ep_lock = threading.RLock()
_ep_accounts: Dict[int, Dict[str, Any]] = {}


def _reward_claim_key(unlock_id: int, is_ep: int) -> int:
    """Encode (unlock_id, is_ep) into a unique positive integer key for state.claim_ep_reward."""
    return int(unlock_id) * 10 + (1 if is_ep else 0)


def _grant_award(award: Optional[Tuple[int, int, int]], account_id: int) -> None:
    """Apply an (award_type, award_id, award_num) tuple into core.state."""
    if not award:
        return
    atype, aid, anum = award
    if anum <= 0:
        return
    if atype == AwardType.ITEM and aid > 0:
        state.add_item(aid, anum)
    elif atype == AwardType.COINS:
        state.grant_currency(coins=anum, account_id=account_id)
    elif atype == AwardType.GEMS:
        state.grant_currency(gems=anum, account_id=account_id)
    elif atype == AwardType.EXP:
        prof = state.get_profile(account_id)
        state.update_profile(account_id, exp=int(prof.get("exp", 0)) + anum)


def _sync_badge_count(account_id: int, target_count: int) -> int:
    """Ensure profile badge_cnt and inventory badge item count match at least target_count."""
    item_cnt = state.get_item_count(DEFAULT_EP_BADGE_ITEM_ID)
    prof = state.get_profile(account_id)
    prof_cnt = int(prof.get("badge_cnt", 0))
    final_cnt = max(target_count, item_cnt, prof_cnt)
    if item_cnt < final_cnt:
        state.add_item(DEFAULT_EP_BADGE_ITEM_ID, final_cnt - item_cnt)
    if (
        not prof.get("has_elite_pass", False)
        or prof.get("ep_event_id") in (None, 0, 1)
        or prof.get("ep_badge") in (None, 0, 1)
        or prof_cnt != final_cnt
    ):
        state.update_profile(
            account_id,
            has_elite_pass=True,
            ep_event_id=DEFAULT_EP_EVENT_ID,
            ep_badge=DEFAULT_EP_BADGE_ITEM_ID,
            badge_cnt=final_cnt,
        )
    return final_cnt


def _init_challenges() -> Dict[int, Dict[str, Any]]:
    """Build initial challenge statuses using real OB17 challenges (mix of REACHED and ONGOING)."""
    now = int(time.time())
    statuses: Dict[int, Dict[str, Any]] = {}
    for ch in EP16_CHALLENGES:
        cid = ch["challenge_id"]
        target = ch["target_value"]
        # Keep daily challenges and most seasonal challenges claimable (REACHED),
        # while leaving the final 3 special challenges ONGOING at partial progress.
        if ch.get("special_challenge", 0) > 0 and cid in (73, 74, 75):
            status = EPTargetStatus.ONGOING
            current = max(1, target // 2)
        else:
            status = EPTargetStatus.REACHED
            current = target
        entry = dict(ch)
        entry["status"] = status
        entry["current_value"] = current
        entry["update_time"] = now
        statuses[cid] = entry
    return statuses


def _ensure_ep_account(account_id: int) -> Dict[str, Any]:
    """Return (creating if needed) runtime Elite Pass state for account_id."""
    with _ep_lock:
        ep = _ep_accounts.get(account_id)
        if ep is None:
            _sync_badge_count(account_id, DEFAULT_BADGE_COUNT)
            ep = {
                "challenges": _init_challenges(),
                "owned_fp_challenge": True,
                "purchase_badge_count_today": 0,
                "purchase_ep_count": 1,
                "ep_max_reward_claimed_badge": 0,
                "subscription_bonus_got": False,
                "daily_completed": 0,
                "elite_completed": 0,
                "veteran_completed": 0,
            }
            _ep_accounts[account_id] = ep
        return ep


def _build_rewards(account_id: int, badge_cnt: int, owned_pass: bool) -> List[Tuple[int, int, int]]:
    """Build list of (unlock_id, EPTarget_Status, is_ep) for all 46 OB17 tiers."""
    claimed = set(state.get_claimed_ep_rewards(account_id))
    out: List[Tuple[int, int, int]] = []
    for unlock_id, req_badges, fp_award, ep_award in EP16_UNLOCKS:
        if fp_award is not None:
            if _reward_claim_key(unlock_id, 0) in claimed or unlock_id in claimed:
                fp_status = EPTargetStatus.CLAIMED
            elif badge_cnt >= req_badges:
                fp_status = EPTargetStatus.REACHED
            else:
                fp_status = EPTargetStatus.ONGOING
            out.append((unlock_id, fp_status, 0))

        if ep_award is not None:
            if _reward_claim_key(unlock_id, 1) in claimed or unlock_id in claimed:
                ep_status = EPTargetStatus.CLAIMED
            elif owned_pass and badge_cnt >= req_badges:
                ep_status = EPTargetStatus.REACHED
            else:
                ep_status = EPTargetStatus.ONGOING
            out.append((unlock_id, ep_status, 1))
    return out


def _get_ep_info_payload(account_id: int) -> bytes:
    """Assemble and encode CSGetEPInfoRes from current core.state and EP runtime state."""
    with _ep_lock:
        ep = _ensure_ep_account(account_id)
        prof = state.get_profile(account_id)
        owned_pass = bool(prof.get("has_elite_pass", True))
        badge_cnt = _sync_badge_count(account_id, DEFAULT_BADGE_COUNT)
        rewards = _build_rewards(account_id, badge_cnt, owned_pass)
        challenges = [dict(ep["challenges"][cid]) for cid in sorted(ep["challenges"])]
        return encode_get_ep_info_res(
            owned_pass=owned_pass,
            rewards=rewards,
            challenges=challenges,
            ep_event_id=int(prof.get("ep_event_id", DEFAULT_EP_EVENT_ID)),
            ep_badge=int(prof.get("ep_badge", DEFAULT_EP_BADGE_ITEM_ID)),
            gold_limit_improved=DEFAULT_GOLD_LIMIT_IMPROVED,
            fp_challenge_item=DEFAULT_FP_CHALLENGE_ITEM,
            owned_fp_challenge=bool(ep["owned_fp_challenge"]),
            purchase_badge_count_today=int(ep["purchase_badge_count_today"]),
            daily_challenge_completed_cnt=int(ep["daily_completed"]),
            elite_challenge_completed_cnt=int(ep["elite_completed"]),
            veteran_challenge_completed_cnt=int(ep["veteran_completed"]),
            purchase_ep_count=int(ep["purchase_ep_count"]),
            ep_max_reward_claimed_badge=int(ep["ep_max_reward_claimed_badge"]),
        )


def _claim_rewards(req: Dict[str, Any], account_id: int) -> List[Tuple[int, int]]:
    """Mark requested EP/FP tier rewards and optional max-reward chest as claimed."""
    claimed_now: List[Tuple[int, int]] = []
    with _ep_lock:
        ep = _ensure_ep_account(account_id)
        prof = state.get_profile(account_id)
        badge_cnt = int(prof.get("badge_cnt", DEFAULT_BADGE_COUNT))
        owned_pass = bool(prof.get("has_elite_pass", True))

        if req.get("claim_max_reward"):
            cur_max = int(ep["ep_max_reward_claimed_badge"])
            next_step = max(225, cur_max) + EP_MAX_REWARD_STEP
            if badge_cnt >= next_step:
                ep["ep_max_reward_claimed_badge"] = next_step
                state.add_item(_EP_MAX_REWARD_ITEM_ID, 1)

        for item in req.get("unlock_rewards", ()):
            uid = int(item.get("id", 0))
            is_ep = 1 if int(item.get("is_ep", 0)) else 0
            if uid <= 0:
                continue
            row = EP16_UNLOCK_MAP.get(uid)
            if row is not None:
                if badge_cnt < row["require_num"]:
                    continue
                if is_ep and not owned_pass:
                    continue
            if state.claim_ep_reward(_reward_claim_key(uid, is_ep), account_id=account_id):
                claimed_now.append((uid, is_ep))
                if row is not None:
                    award = row["ep_award"] if is_ep else row["fp_award"]
                    _grant_award(award, account_id)
    return claimed_now


def _claim_challenge_badge(challenge_id: int, account_id: int) -> int:
    """Claim badge reward for a completed/ongoing challenge and update badge count."""
    with _ep_lock:
        ep = _ensure_ep_account(account_id)
        ch = ep["challenges"].get(challenge_id)
        if ch is None:
            tpl = EP16_CHALLENGE_MAP.get(challenge_id)
            if tpl is None:
                return 0
            ch = dict(tpl)
            ch["status"] = EPTargetStatus.REACHED
            ch["current_value"] = ch["target_value"]
            ep["challenges"][challenge_id] = ch

        if ch["status"] == EPTargetStatus.CLAIMED:
            return 0

        ch["status"] = EPTargetStatus.CLAIMED
        ch["current_value"] = ch["target_value"]
        ch["update_time"] = int(time.time())

        ctype = int(ch.get("challenge_type", ChallengeType.ELITE))
        if ctype == ChallengeType.DAILY:
            ep["daily_completed"] += 1
        elif ctype == ChallengeType.ELITE:
            ep["elite_completed"] += 1
        elif ctype == ChallengeType.VETERAN:
            ep["veteran_completed"] += 1

        badges = max(1, int(ch.get("award_badges", 1)))
        state.add_item(DEFAULT_EP_BADGE_ITEM_ID, badges)
        prof = state.get_profile(account_id)
        new_cnt = max(int(prof.get("badge_cnt", 0)) + badges, state.get_item_count(DEFAULT_EP_BADGE_ITEM_ID))
        state.update_profile(account_id, badge_cnt=new_cnt)
        return badges


def _add_badges(count: int, account_id: int, is_purchase: bool = False) -> int:
    """Add badges to inventory and profile badge_cnt."""
    if count <= 0:
        return 0
    with _ep_lock:
        ep = _ensure_ep_account(account_id)
        state.add_item(DEFAULT_EP_BADGE_ITEM_ID, count)
        prof = state.get_profile(account_id)
        new_cnt = max(int(prof.get("badge_cnt", 0)) + count, state.get_item_count(DEFAULT_EP_BADGE_ITEM_ID))
        state.update_profile(account_id, badge_cnt=new_cnt)
        if is_purchase:
            ep["purchase_badge_count_today"] += count
        return new_cnt


def reset_ep_state(account_id: Optional[int] = None) -> None:
    """Reset runtime EP challenge/subscription state (useful in tests)."""
    with _ep_lock:
        if account_id is None:
            _ep_accounts.clear()
        else:
            _ep_accounts.pop(account_id, None)


def handle_elitepass_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """Dispatch Elite Pass & IAP HTTP endpoints. Returns True if handled."""
    endpoint = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    if endpoint not in ELITEPASS_ENDPOINTS:
        return False

    if endpoint == "GetEPInfo":
        handler.send_proto("CSGetEPInfoRes", _get_ep_info_payload(account_id))
        return True

    if endpoint == "GetCardsAndIAPInfo":
        handler.send_proto("GetCardsAndIAPInfoRes", encode_get_cards_and_iap_info_res())
        return True

    if endpoint in ("GetEPSubscriptionBonusStatus", "GetRebateSubscriptionBonusStatus"):
        with _ep_lock:
            ep = _ensure_ep_account(account_id)
            is_got = bool(ep["subscription_bonus_got"])
        res_name = "CSGetRebateSubscriptionBonusStatusRes" if endpoint == "GetRebateSubscriptionBonusStatus" else "CSGetEPSubscriptionBonusStatusRes"
        handler.send_proto(
            res_name,
            encode_ep_subscription_bonus_status_res(is_got=is_got),
        )
        return True

    if endpoint in ("ClaimEPReward", "EPClaimReward"):
        req = decode_ep_claim_reward_req(raw_body)
        claimed = _claim_rewards(req, account_id)
        print(f"  [EP] Claimed rewards: {claimed}, max={req['claim_max_reward']}", flush=True)
        handler.send_proto("CSEPClaimRewardRes", encode_ep_claim_reward_res())
        return True

    if endpoint == "EPClaimBadge":
        req = decode_ep_claim_badge_req(raw_body)
        added = _claim_challenge_badge(req["challenge_id"], account_id)
        print(f"  [EP] Claimed challenge {req['challenge_id']} (+{added} badges)", flush=True)
        handler.send_proto("CSEPClaimBadgeRes", encode_ep_claim_badge_res())
        return True

    if endpoint == "EPPurchaseBadge":
        req = decode_ep_purchase_badge_req(raw_body)
        count = max(1, req["count"])
        new_cnt = _add_badges(count, account_id, is_purchase=True)
        print(f"  [EP] Purchased {count} badges -> total {new_cnt}", flush=True)
        handler.send_proto("CSEPPurchaseBadgeRes", encode_ep_purchase_badge_res())
        return True

    if endpoint == "EPPurchase":
        req = decode_ep_purchase_req(raw_body)
        with _ep_lock:
            ep = _ensure_ep_account(account_id)
            ep["purchase_ep_count"] += 1
            ep["owned_fp_challenge"] = True
            state.update_profile(
                account_id,
                has_elite_pass=True,
                ep_event_id=DEFAULT_EP_EVENT_ID,
                ep_badge=DEFAULT_EP_BADGE_ITEM_ID,
            )
            if req["is_bundle"]:
                _add_badges(50, account_id)
        handler.send_proto("CSEPPurchaseRes", encode_ep_purchase_res())
        return True

    if endpoint == "EPPreorder":
        _ensure_ep_account(account_id)
        handler.send_proto("CSEPPreorderRes", encode_ep_preorder_res())
        return True

    if endpoint == "EPVideoAdPortal":
        _ = decode_ep_video_ad_portal_req(raw_body)
        handler.send_proto("CSEPVideoAdPortalRes", encode_ep_video_ad_portal_res(""))
        return True

    return False


handle_elitepass_post = handle_elitepass_request
