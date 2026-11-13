"""
Activity, Attendance, Broadcast, Marquee, Splash, Advert, Bingo, Activeness,
Switches & GameBonus HTTP handlers for Barbosa Project (Free Fire 1.39).
"""

from __future__ import annotations

import copy
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.activity_models import (
    ActivityState,
    ActivityType,
    AdType,
    AwardType,
    EAttendanceSignState,
    EEventTag,
    EventTabType,
    NavigationType,
    SplashType,
    SwitchFunc,
    decode_activeness_reward_req,
    decode_activity_rewards_req,
    decode_finish_bingo_activity_req,
    decode_flip_bingo_req,
    decode_fresh_activity_rewards_req,
    decode_get_attendance_req,
    decode_get_bingo_rewards_req,
    decode_language_req,
    encode_activeness_and_reward_info_res,
    encode_activeness_desc_res,
    encode_activeness_reward_res,
    encode_activity_desc_res,
    encode_activity_info_res,
    encode_activity_rewards_res,
    encode_advert_res,
    encode_all_switchs_res,
    encode_announcement_res,
    encode_attendance_list_res,
    encode_broadcast_list_res,
    encode_clan_sign_in_res,
    encode_festival_attendance_info_res,
    encode_festival_attendance_signin_res,
    encode_festival_item_info_res,
    encode_flip_bingo_res,
    encode_fresh_activity_info_res,
    encode_fresh_activity_rewards_res,
    encode_game_bonus_event_desc_res,
    encode_get_attendance_res,
    encode_get_bingo_rewards_info_res,
    encode_get_bingo_rewards_res,
    encode_login_broadcast_res,
    encode_login_desc_res,
    encode_login_splash_res,
    encode_match_daily_bonus_res,
    encode_new_player_rewards_list_res,
    encode_scroll_marquee_res,
    encode_veteran_reward_list_res,
)
from proto.decoder import decode_proto, get_varint


ACTIVITY_ENDPOINTS = (
    "LoginGetDesc",
    "LoginGetSplash",
    "LoginGetBroadcast",
    "GetAnnouncement",
    "GetAttendance",
    "GetAttendanceList",
    "AttendanceSignin",
    "GetFestivalAttendanceInfo",
    "FestivalAttendanceSignin",
    "GetFestivalItemInfo",
    "GetNewPlayerRewardsList",
    "NewPlayerSignin",
    "GetVeteranRewardList",
    "VeteranClaimReward",
    "GetActivityDesc",
    "GetActivityInfo",
    "GetActivityRewards",
    "ActivityTrigger",
    "GetFreshActivityInfo",
    "GetFreshActivityRewards",
    "FreshActivityTrigger",
    "GetActivenessDesc",
    "GetActivenessAndRewardInfo",
    "GetActivenessReward",
    "GetBingoRewardsInfo",
    "FlipBingo",
    "GetBingoRewards",
    "FinishBingoActivity",
    "GetAdvert",
    "GetAds",
    "GetBroadcastList",
    "GetScrollMarquee",
    "GetAllSwitchs",
    "GetGameBonusEventDesc",
    "GetMatchDailyBonus",
)


def _extract_endpoint(path: str) -> str:
    clean = path.split("?", 1)[0].rstrip("/")
    return clean.rsplit("/", 1)[-1] if "/" in clean else clean


def _banners_base(handler: Any) -> str:
    host = "127.0.0.1:8080"
    headers = getattr(handler, "headers", None)
    if headers is not None:
        hdr_host = headers.get("Host")
        if hdr_host:
            host = str(hdr_host).strip()
    return f"http://{host}/banners"


def _host_root(base_url: str) -> str:
    root = str(base_url or "http://127.0.0.1:8080").strip().rstrip("/")
    if root.endswith("/banners"):
        root = root[: -len("/banners")]
    return root or "http://127.0.0.1:8080"


def _resolve_banner_url(base_url: str, raw_url: Any, version: Any = None) -> str:
    """Resolve relative `/banners/...` or bare filenames to `http://{host}...` and keep full URLs."""
    s = str(raw_url or "").strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        resolved = s
    elif s.startswith("/"):
        resolved = f"{_host_root(base_url)}{s}"
    else:
        resolved = f"{_host_root(base_url)}/banners/{s.lstrip('/')}"
    if version is not None:
        try:
            ver = int(version)
        except (TypeError, ValueError):
            ver = 1
        if ver > 1 and "?" not in resolved:
            resolved = f"{resolved}?v={ver}"
    return resolved


def _safe_record_lobby_event(
    endpoint: str,
    category: str,
    summary: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        state.record_lobby_event(endpoint, category, summary, detail)
    except Exception:
        pass


def _send_proto(handler: Any, name: str, payload: bytes) -> None:
    if hasattr(handler, "send_proto"):
        handler.send_proto(name, payload)
        return
    handler.send_response(200)
    handler.send_header("Content-Type", "application/octet-stream")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _award(award_type: int, award_id: int, award_num: int) -> Dict[str, int]:
    return {
        "award_type": int(award_type),
        "award_id": int(award_id),
        "award_num": int(award_num),
    }


def _default_attendance_items() -> List[Dict[str, Any]]:
    return [
        {
            "id": 1,
            "signed": EAttendanceSignState.NEED_SIGN,
            "awards": [_award(AwardType.COINS, 0, 1000), _award(AwardType.ITEM, 203000001, 1)],
        },
        {
            "id": 2,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 50)],
        },
        {
            "id": 3,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.ITEM, 204000001, 1), _award(AwardType.COINS, 0, 1500)],
        },
        {
            "id": 4,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 75), _award(AwardType.ITEM, 205000001, 1)],
        },
        {
            "id": 5,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.COINS, 0, 2500), _award(AwardType.ITEM, 211000001, 1)],
        },
        {
            "id": 6,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 100), _award(AwardType.ITEM, 901000001, 1)],
        },
        {
            "id": 7,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 200), _award(AwardType.ITEM, 902000001, 1)],
        },
    ]


def _default_new_player_items() -> List[Dict[str, Any]]:
    return [
        {
            "id": 1,
            "signed": EAttendanceSignState.NEED_SIGN,
            "awards": [_award(AwardType.COINS, 0, 2000), _award(AwardType.ITEM, 203000002, 1)],
        },
        {
            "id": 2,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 100), _award(AwardType.ITEM, 204000002, 1)],
        },
        {
            "id": 3,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.ITEM, 205000002, 1), _award(AwardType.COINS, 0, 3000)],
        },
        {
            "id": 4,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 150)],
        },
        {
            "id": 5,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.ITEM, 907100001, 1)],
        },
        {
            "id": 6,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.ITEM, 908000001, 1)],
        },
        {
            "id": 7,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 300), _award(AwardType.ITEM, 211000002, 1)],
        },
    ]


def _default_festival_items() -> List[Dict[str, Any]]:
    return [
        {
            "id": 1,
            "signed": EAttendanceSignState.NEED_SIGN,
            "awards": [_award(AwardType.ITEM, 203000003, 1), _award(AwardType.COINS, 0, 1200)],
            "drop_max_num": 1,
        },
        {
            "id": 2,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 80)],
            "drop_max_num": 1,
        },
        {
            "id": 3,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.ITEM, 909000001, 1)],
            "drop_max_num": 1,
        },
        {
            "id": 4,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.GEMS, 0, 120)],
            "drop_max_num": 1,
        },
        {
            "id": 5,
            "signed": EAttendanceSignState.UNSIGNED,
            "awards": [_award(AwardType.ITEM, 910000001, 1), _award(AwardType.GEMS, 0, 200)],
            "drop_max_num": 1,
        },
    ]


def _default_veteran_rewards() -> List[Dict[str, Any]]:
    return [
        {
            "desc": {
                "region": "DEFAULT",
                "id": 1,
                "award": _award(AwardType.GEMS, 0, 150),
                "cdn_url_key": "veteran_gem_pack",
            },
            "status": 0,
        },
        {
            "desc": {
                "region": "DEFAULT",
                "id": 2,
                "award": _award(AwardType.ITEM, 203000004, 1),
                "cdn_url_key": "veteran_bundle",
            },
            "status": 0,
        },
    ]


def _default_clan_sign_in_rewards() -> List[Dict[str, Any]]:
    return [
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": 1,
                "weekday": day,
                "award": _award(AwardType.COINS, 0, 300 * day),
            },
            "status": 1 if day == 1 else 0,
        }
        for day in range(1, 8)
    ]


def _default_activeness_rewards() -> List[Dict[str, Any]]:
    return [
        {
            "group_id": 1,
            "box_id": 1,
            "box": "Daily Box I (20)",
            "activeness": 20,
            "awards": [_award(AwardType.COINS, 0, 500)],
        },
        {
            "group_id": 1,
            "box_id": 2,
            "box": "Daily Box II (40)",
            "activeness": 40,
            "awards": [_award(AwardType.COINS, 0, 1000), _award(AwardType.ITEM, 901000003, 1)],
        },
        {
            "group_id": 1,
            "box_id": 3,
            "box": "Daily Box III (60)",
            "activeness": 60,
            "awards": [_award(AwardType.GEMS, 0, 50)],
        },
        {
            "group_id": 1,
            "box_id": 4,
            "box": "Weekly Grand Box (100)",
            "activeness": 100,
            "awards": [_award(AwardType.GEMS, 0, 150), _award(AwardType.ITEM, 203000005, 1)],
        },
    ]


def _default_activeness_box_states() -> List[Dict[str, int]]:
    # state: 0=locked, 1=claimable, 2=claimed
    return [
        {"group_id": 1, "box_id": 1, "state": 2},
        {"group_id": 1, "box_id": 2, "state": 1},
        {"group_id": 1, "box_id": 3, "state": 1},
        {"group_id": 1, "box_id": 4, "state": 0},
    ]


def _default_bingo_line_descs() -> List[Dict[str, Any]]:
    lines = [
        (1, [4001, 4002, 4003], [_award(AwardType.GEMS, 0, 60)]),
        (2, [4004, 4005, 4006], [_award(AwardType.COINS, 0, 2000)]),
        (3, [4007, 4008, 4009], [_award(AwardType.ITEM, 204000003, 1)]),
        (4, [4001, 4004, 4007], [_award(AwardType.GEMS, 0, 60)]),
        (5, [4002, 4005, 4008], [_award(AwardType.COINS, 0, 2500)]),
        (6, [4003, 4006, 4009], [_award(AwardType.ITEM, 205000003, 1)]),
        (7, [4001, 4005, 4009], [_award(AwardType.GEMS, 0, 100)]),
        (8, [4003, 4005, 4007], [_award(AwardType.GEMS, 0, 100), _award(AwardType.ITEM, 902000003, 1)]),
    ]
    return [
        {"id": rid, "level": 1, "activity_ids": cells, "awards": awards}
        for rid, cells, awards in lines
    ]


def _default_activity_states() -> Dict[int, Dict[str, int]]:
    states = {
        1001: {"id": 1001, "data": 1, "state": ActivityState.FINISHED},
        1002: {"id": 1002, "data": 0, "state": ActivityState.RECEIVED},
        1003: {"id": 1003, "data": 3, "state": ActivityState.FINISHED},
        2001: {"id": 2001, "data": 1, "state": ActivityState.FINISHED},
        2002: {"id": 2002, "data": 0, "state": ActivityState.RECEIVED},
        3001: {"id": 3001, "data": 1, "state": ActivityState.FINISHED},
        3002: {"id": 3002, "data": 0, "state": ActivityState.RECEIVED},
    }
    # 3x3 Bingo cells (4001..4009): first two already flipped, remaining 7 ready to flip
    for cid in range(4001, 4010):
        flipped = cid in (4001, 4002)
        states[cid] = {
            "id": cid,
            "data": 1 if flipped else 0,
            "state": ActivityState.AWARDED if flipped else ActivityState.RECEIVED,
        }
    return states


def _default_fresh_activities() -> Dict[int, Dict[str, Any]]:
    return {
        5001: {
            "id": 5001,
            "data": 1,
            "state": ActivityState.FINISHED,
            "awards": [_award(AwardType.COINS, 0, 1500), _award(AwardType.GEMS, 0, 50)],
        },
        5002: {
            "id": 5002,
            "data": 1,
            "state": ActivityState.FINISHED,
            "awards": [_award(AwardType.ITEM, 203000006, 1)],
        },
        5003: {
            "id": 5003,
            "data": 0,
            "state": ActivityState.RECEIVED,
            "awards": [_award(AwardType.COINS, 0, 2000), _award(AwardType.ACTIVENESS, 0, 20)],
        },
        5004: {
            "id": 5004,
            "data": 0,
            "state": ActivityState.RECEIVED,
            "awards": [_award(AwardType.GEMS, 0, 100)],
        },
    }


def _build_activity_descs(base_url: str) -> List[Dict[str, Any]]:
    now = int(time.time())
    start_ts = now - 86400
    end_ts = now + 30 * 86400
    rows = state.list_events(enabled_only=True)
    rows.sort(
        key=lambda ev: (
            int(ev.get("group_id", 1)),
            int(ev.get("sort_id", 1)),
            int(ev.get("activity_id", ev.get("id", 0))),
        )
    )
    descs: List[Dict[str, Any]] = []
    for ev in rows:
        item = copy.deepcopy(ev)
        aid = int(item.get("activity_id", item.get("id", 1001)))
        item["activity_id"] = aid
        item["id"] = int(item.get("id", aid))
        ver = item.get("version")
        img = _resolve_banner_url(base_url, item.get("image_url", ""), ver)
        lobby_img = _resolve_banner_url(base_url, item.get("image_url_for_lobby") or item.get("image_url", ""), ver)
        topup_img = _resolve_banner_url(base_url, item.get("image_url_for_top_up", ""), ver)
        item["image_url"] = img
        item["image_url_for_lobby"] = lobby_img
        if topup_img:
            item["image_url_for_top_up"] = topup_img
        item.setdefault("start_time", start_ts)
        item.setdefault("end_time", end_ts)
        descs.append(item)
    return descs


class _AccountActivityData:
    """Mutable per-account runtime state for events, attendance, bingo, activeness."""

    def __init__(self) -> None:
        self.attendance: List[Dict[str, Any]] = _default_attendance_items()
        self.is_signed_today: bool = False
        self.new_player: List[Dict[str, Any]] = _default_new_player_items()
        self.festival: List[Dict[str, Any]] = _default_festival_items()
        self.is_festival_signed_today: bool = False
        self.is_veteran: bool = True
        self.veteran_rewards: List[Dict[str, Any]] = _default_veteran_rewards()
        self.clan_sign_in_rewards: List[Dict[str, Any]] = _default_clan_sign_in_rewards()
        self.activity_states: Dict[int, Dict[str, int]] = _default_activity_states()
        self.fresh_day: int = 1
        self.fresh_activities: Dict[int, Dict[str, Any]] = _default_fresh_activities()
        self.daily_activeness: int = 60
        self.weekly_activeness: int = 240
        self.activeness_boxes: List[Dict[str, int]] = _default_activeness_box_states()
        self.bingo_rewards: List[Dict[str, Any]] = [
            {"rewards_id": r["id"], "awarded": False}
            for r in _default_bingo_line_descs()
        ]
        self.bingo_grid: Dict[int, Dict[str, Any]] = {
            cid: self.activity_states[cid]
            for cid in range(4001, 4010)
            if cid in self.activity_states
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attendance": self.attendance,
            "is_signed_today": self.is_signed_today,
            "new_player": self.new_player,
            "festival": self.festival,
            "is_festival_signed_today": self.is_festival_signed_today,
            "is_veteran": self.is_veteran,
            "veteran_rewards": self.veteran_rewards,
            "clan_sign_in_rewards": self.clan_sign_in_rewards,
            "activity_states": {str(k): v for k, v in self.activity_states.items()},
            "fresh_day": self.fresh_day,
            "fresh_activities": {str(k): v for k, v in self.fresh_activities.items()},
            "daily_activeness": self.daily_activeness,
            "weekly_activeness": self.weekly_activeness,
            "activeness_boxes": self.activeness_boxes,
            "bingo_rewards": self.bingo_rewards,
            "bingo_grid": {str(k): v for k, v in self.bingo_grid.items()},
        }

    def load_dict(self, data: Dict[str, Any]) -> None:
        if not data:
            return
        if "attendance" in data:
            self.attendance = data["attendance"]
        if "is_signed_today" in data:
            self.is_signed_today = bool(data["is_signed_today"])
        if "new_player" in data:
            self.new_player = data["new_player"]
        if "festival" in data:
            self.festival = data["festival"]
        if "is_festival_signed_today" in data:
            self.is_festival_signed_today = bool(data["is_festival_signed_today"])
        if "is_veteran" in data:
            self.is_veteran = bool(data["is_veteran"])
        if "veteran_rewards" in data:
            self.veteran_rewards = data["veteran_rewards"]
        if "clan_sign_in_rewards" in data:
            self.clan_sign_in_rewards = data["clan_sign_in_rewards"]
        if "activity_states" in data:
            raw_act = data["activity_states"]
            if isinstance(raw_act, dict):
                self.activity_states = {int(k): v for k, v in raw_act.items()}
            elif isinstance(raw_act, list):
                self.activity_states = {int(item["id"]): item for item in raw_act}
        if "fresh_day" in data:
            self.fresh_day = int(data["fresh_day"])
        if "fresh_activities" in data:
            raw_fresh = data["fresh_activities"]
            if isinstance(raw_fresh, dict):
                self.fresh_activities = {int(k): v for k, v in raw_fresh.items()}
            elif isinstance(raw_fresh, list):
                self.fresh_activities = {int(item["id"]): item for item in raw_fresh}
        if "daily_activeness" in data:
            self.daily_activeness = int(data["daily_activeness"])
        if "weekly_activeness" in data:
            self.weekly_activeness = int(data["weekly_activeness"])
        if "activeness_boxes" in data:
            self.activeness_boxes = data["activeness_boxes"]
        if "bingo_rewards" in data:
            self.bingo_rewards = data["bingo_rewards"]
        if "bingo_grid" in data:
            raw_bg = data["bingo_grid"]
            if isinstance(raw_bg, dict):
                self.bingo_grid = {int(k): v for k, v in raw_bg.items()}
            elif isinstance(raw_bg, list):
                self.bingo_grid = {int(item["id"]): item for item in raw_bg}
            for cid, cell in self.bingo_grid.items():
                self.activity_states[cid] = cell
        else:
            self.bingo_grid = {
                cid: self.activity_states[cid]
                for cid in range(4001, 4010)
                if cid in self.activity_states
            }


class ActivityService:
    """Thread-safe service managing activity configs, claims, attendance, and broadcasts."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._accounts: Dict[int, _AccountActivityData] = {}
        self._bingo_lines: List[Dict[str, Any]] = _default_bingo_line_descs()
        self._activeness_descs: List[Dict[str, Any]] = _default_activeness_rewards()

    def _get_acct(self, account_id: int) -> _AccountActivityData:
        account_id = int(account_id)
        acct = self._accounts.get(account_id)
        if acct is None:
            acct = _AccountActivityData()
            state_data = db.get_activity_state(account_id)
            if state_data:
                acct.load_dict(state_data)
            else:
                db.save_activity_state(account_id, acct.to_dict())
            self._accounts[account_id] = acct
        return acct

    def _save_acct_state(self, account_id: int, acct: Optional[_AccountActivityData] = None) -> None:
        account_id = int(account_id)
        if acct is None:
            acct = self._get_acct(account_id)
        db.save_activity_state(account_id, acct.to_dict())

    def _sync_account_activities(self, acct: _AccountActivityData) -> List[Dict[str, int]]:
        """Ensure newly added CMS events have claimable runtime state and filter to enabled CMS IDs."""
        rows = state.list_events(enabled_only=True)
        enabled_states: List[Dict[str, int]] = []
        seen: set[int] = set()
        for ev in rows:
            aid = int(ev.get("activity_id", ev.get("id", 0)))
            if aid <= 0 or aid in seen:
                continue
            seen.add(aid)
            st = acct.activity_states.get(aid)
            if st is None:
                st = {
                    "id": aid,
                    "data": max(1, int(ev.get("cdt_value", 1))),
                    "state": ActivityState.FINISHED,
                }
                acct.activity_states[aid] = st
            enabled_states.append(st)
        return enabled_states

    def _grant_awards(self, account_id: int, awards: List[Dict[str, Any]]) -> Dict[str, Any]:
        coins = 0
        gems = 0
        activeness = 0
        items: List[Dict[str, int]] = []

        for aw in awards:
            atype = int(aw.get("award_type", AwardType.ITEM))
            aid = int(aw.get("award_id", 0))
            anum = int(aw.get("award_num", 1))
            if atype == AwardType.COINS:
                coins += anum
            elif atype == AwardType.GEMS:
                gems += anum
            elif atype == AwardType.ACTIVENESS:
                activeness += anum
            elif atype == AwardType.ITEM and aid > 0:
                items.append({"id": aid, "cnt": anum})
                state.unlock_item(aid, count=anum)

        if coins or gems:
            state.grant_currency(coins=coins, gems=gems, account_id=account_id)

        if activeness:
            acct = self._get_acct(account_id)
            acct.daily_activeness += activeness
            acct.weekly_activeness += activeness
            desc_by_box = {int(r["box_id"]): int(r["activeness"]) for r in self._activeness_descs}
            for bs in acct.activeness_boxes:
                req_act = desc_by_box.get(int(bs["box_id"]), 9999)
                if bs["state"] == 0 and acct.daily_activeness >= req_act:
                    bs["state"] = 1
            self._save_acct_state(account_id, acct)

        return {"items": items, "coins": coins, "gems": gems, "activeness": activeness}

    # --- Attendance / Sign-In ---

    def build_attendance_list_res(self, account_id: int, base_url: str) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            end_ts = int(time.time()) + 30 * 86400
            return encode_attendance_list_res(
                items=copy.deepcopy(acct.attendance),
                end_time=end_ts,
                url=f"{base_url}/activity_banner.png",
                loc_key="TXT_SIGNIN_TITLE",
                is_signed_today=acct.is_signed_today,
            )

    def build_get_attendance_res(self, account_id: int, base_url: str, need_clan_info: bool = True) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            new_player_bytes = encode_new_player_rewards_list_res(copy.deepcopy(acct.new_player))
            att_bytes = self.build_attendance_list_res(account_id, base_url)
            vet_bytes = encode_veteran_reward_list_res(
                is_veteran=acct.is_veteran,
                rewards=copy.deepcopy(acct.veteran_rewards),
            )
            clan_bytes = (
                encode_clan_sign_in_res(copy.deepcopy(acct.clan_sign_in_rewards), is_newcomer=False)
                if need_clan_info
                else b""
            )
            return encode_get_attendance_res(
                new_player_res=new_player_bytes,
                attendance_res=att_bytes,
                veteran_res=vet_bytes,
                clan_sign_in_info=clan_bytes,
            )

    def sign_in_attendance(self, account_id: int) -> Dict[str, Any]:
        with self._lock:
            acct = self._get_acct(account_id)
            target = None
            for item in acct.attendance:
                if item["signed"] == EAttendanceSignState.NEED_SIGN:
                    target = item
                    break
            if target is None and not acct.is_signed_today:
                for item in acct.attendance:
                    if item["signed"] == EAttendanceSignState.UNSIGNED:
                        target = item
                        break
            if target is None:
                return {"items": [], "coins": 0, "gems": 0, "activeness": 0}
            target["signed"] = EAttendanceSignState.SIGNED
            acct.is_signed_today = True
            day_idx = int(target.get("id", 1))
            granted = self._grant_awards(account_id, target["awards"])
            db.record_claim(account_id, "attendance", day_idx, {"day": day_idx, "awards": target["awards"], "granted": granted})
            self._save_acct_state(account_id, acct)
            db.log_action(account_id, "ATTENDANCE_CLAIM", f"Claimed day {day_idx} attendance rewards", {"day": day_idx, "granted": granted})
            return granted

    def build_new_player_rewards_res(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            return encode_new_player_rewards_list_res(copy.deepcopy(acct.new_player))

    def sign_in_new_player(self, account_id: int, reward_id: int = 0) -> Dict[str, Any]:
        with self._lock:
            acct = self._get_acct(account_id)
            target = None
            for item in acct.new_player:
                if reward_id and item["id"] == reward_id and item["signed"] != EAttendanceSignState.SIGNED:
                    target = item
                    break
            if target is None and not reward_id:
                for item in acct.new_player:
                    if item["signed"] == EAttendanceSignState.NEED_SIGN:
                        target = item
                        break
                if target is None:
                    for item in acct.new_player:
                        if item["signed"] == EAttendanceSignState.UNSIGNED:
                            target = item
                            break
            if target is None:
                return {"items": [], "coins": 0, "gems": 0, "activeness": 0}
            target["signed"] = EAttendanceSignState.SIGNED
            rid = int(target.get("id", reward_id or 1))
            granted = self._grant_awards(account_id, target["awards"])
            db.record_claim(account_id, "7days_new_player", rid, {"reward_id": rid, "awards": target["awards"], "granted": granted})
            self._save_acct_state(account_id, acct)
            db.log_action(account_id, "NEW_PLAYER_CLAIM", f"Claimed 7-days new player reward {rid}", {"reward_id": rid, "granted": granted})
            return granted

    def build_veteran_reward_list_res(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            return encode_veteran_reward_list_res(
                is_veteran=acct.is_veteran,
                rewards=copy.deepcopy(acct.veteran_rewards),
            )

    def claim_veteran_reward(self, account_id: int, reward_id: int = 0) -> Dict[str, Any]:
        with self._lock:
            acct = self._get_acct(account_id)
            for rw in acct.veteran_rewards:
                if rw["status"] == 0 and (not reward_id or rw["desc"]["id"] == reward_id):
                    rw["status"] = 1
                    rid = int(rw["desc"]["id"])
                    granted = self._grant_awards(account_id, [rw["desc"]["award"]])
                    db.record_claim(account_id, "veteran", rid, {"reward_id": rid, "granted": granted})
                    self._save_acct_state(account_id, acct)
                    db.log_action(account_id, "VETERAN_CLAIM", f"Claimed veteran reward {rid}", {"reward_id": rid, "granted": granted})
                    return granted
            return {"items": [], "coins": 0, "gems": 0, "activeness": 0}

    def build_festival_attendance_info_res(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            return encode_festival_attendance_info_res(
                items=copy.deepcopy(acct.festival),
                is_signed_today=acct.is_festival_signed_today,
            )

    def sign_in_festival(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            target = None
            for item in acct.festival:
                if item["signed"] == EAttendanceSignState.NEED_SIGN:
                    target = item
                    break
            if target is None and not acct.is_festival_signed_today:
                for item in acct.festival:
                    if item["signed"] == EAttendanceSignState.UNSIGNED:
                        target = item
                        break
            if target is not None:
                target["signed"] = EAttendanceSignState.SIGNED
                acct.is_festival_signed_today = True
                day_idx = int(target.get("id", 1))
                granted = self._grant_awards(account_id, target["awards"])
                db.record_claim(account_id, "festival", day_idx, {"day": day_idx, "granted": granted})
                self._save_acct_state(account_id, acct)
                db.log_action(account_id, "FESTIVAL_CLAIM", f"Claimed festival check-in day {day_idx}", {"day": day_idx, "granted": granted})
            return encode_festival_attendance_signin_res("India V1 Festival Check-In Complete!")

    # --- Announcements, Splash, Adverts, Broadcasts, Marquee ---

    def _announcements(self, base_url: str, language: str) -> List[Dict[str, Any]]:
        now = int(time.time())
        rows = state.list_announcements(enabled_only=True)
        rows.sort(key=lambda a: (int(a.get("order_in_this_language", 1)), int(a.get("id", 1))))
        out: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            ver = row.get("version")
            img = _resolve_banner_url(base_url, row.get("image_url", ""), ver)
            lobby_img = _resolve_banner_url(base_url, row.get("image_url_for_lobby") or row.get("image_url", ""), ver)
            out.append(
                {
                    "id": int(row.get("id", idx)),
                    "language": str(row.get("language") or language),
                    "order_in_this_language": int(row.get("order_in_this_language", idx)),
                    "title": str(row.get("title", "Announcement")),
                    "desc": str(row.get("desc", "")),
                    "image_url": img,
                    "image_url_for_lobby": lobby_img,
                    "link_url": str(row.get("link_url", "")),
                    "fb_page_id": str(row.get("fb_page_id", "")),
                    "region": str(row.get("region", "DEFAULT")),
                    "start_time": int(row.get("start_time") or (now - 86400)),
                    "end_time": int(row.get("end_time") or (now + 365 * 86400)),
                    "use_embedded_browser": bool(row.get("use_embedded_browser", False)),
                }
            )
        return out

    def _splash_banners(self, base_url: str, language: str) -> List[Dict[str, Any]]:
        now = int(time.time())
        rows = state.list_splashes(enabled_only=True)
        rows.sort(key=lambda b: (int(b.get("sort_id", 1)), int(b.get("id", 1))))
        out: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            ver = row.get("version")
            img = _resolve_banner_url(base_url, row.get("image_url", ""), ver)
            bg_img = _resolve_banner_url(base_url, row.get("bg_img_url") or row.get("image_url", ""), ver)
            gos_url = str(row.get("gos_url") or row.get("link_url") or "")
            out.append(
                {
                    "id": int(row.get("id", idx)),
                    "region": str(row.get("region", "DEFAULT")),
                    "language": str(row.get("language") or language),
                    "name": str(row.get("name", "Banner")),
                    "sort_id": int(row.get("sort_id", idx)),
                    "start_time": int(row.get("start_time") or (now - 86400)),
                    "end_time": int(row.get("end_time") or (now + 365 * 86400)),
                    "image_url": img,
                    "bg_img_url": bg_img,
                    "gos_pos": int(row.get("gos_pos", NavigationType.ACTIVITY)),
                    "gos_url": gos_url,
                    "use_embedded_browser": bool(row.get("use_embedded_browser", bool(gos_url))),
                    "sub_go_pos": str(row.get("sub_go_pos", "")),
                    "video_url": str(row.get("video_url", "")),
                    "type": int(row.get("type", SplashType.NORMAL)),
                }
            )
        return out

    def build_announcement_res(
        self,
        base_url: str,
        language: str = "en",
        record_event: bool = True,
    ) -> bytes:
        anns = self._announcements(base_url, language)
        if record_event:
            _safe_record_lobby_event(
                "/GetAnnouncement",
                "announcement",
                f"Served {len(anns)} announcements",
                {
                    "language": language,
                    "count": len(anns),
                    "items": [{"id": a["id"], "title": a["title"], "image_url": a["image_url"]} for a in anns],
                },
            )
        return encode_announcement_res(anns)

    def build_login_splash_res(self, account_id: int, base_url: str, language: str = "en") -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            acts = self._sync_account_activities(acct)
            anns = self._announcements(base_url, language)
            splashes = self._splash_banners(base_url, language)
            _safe_record_lobby_event(
                "/LoginGetSplash",
                "splash",
                f"Served {len(splashes)} splashes, {len(anns)} news, {len(acts)} activities",
                {
                    "account_id": account_id,
                    "language": language,
                    "splashes": [{"id": s["id"], "name": s["name"], "image_url": s["image_url"]} for s in splashes],
                    "announcements": [{"id": a["id"], "title": a["title"], "image_url": a["image_url"]} for a in anns],
                    "activity_count": len(acts),
                },
            )
            return encode_login_splash_res(
                announcements=anns,
                splash_banners=splashes,
                activities=acts,
            )

    def _build_advert_items(self, base_url: str, language: str = "en") -> List[Dict[str, Any]]:
        now = int(time.time())
        rows = state.list_adverts(enabled_only=True)
        rows.sort(key=lambda a: (int(a.get("sort_id", 1)), int(a.get("id", 1))))
        ads: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            ver = row.get("version")
            ad_url = _resolve_banner_url(base_url, row.get("advertisment_url", ""), ver)
            sub_go = str(row.get("sub_go_pos") or row.get("link_url") or "")
            ads.append(
                {
                    "id": int(row.get("id", idx)),
                    "type": int(row.get("type", AdType.LOBBY_ADS)),
                    "sort_id": int(row.get("sort_id", idx)),
                    "language": str(row.get("language") or language),
                    "advertisment_url": ad_url,
                    "ad_start_time": int(row.get("ad_start_time") or (now - 86400)),
                    "ad_end_time": int(row.get("ad_end_time") or (now + 365 * 86400)),
                    "go_pos": int(row.get("go_pos", NavigationType.ACTIVITY)),
                    "sub_type": int(row.get("sub_type", 0)),
                    "sub_go_pos": sub_go,
                    "external_for_official_website": bool(row.get("external_for_official_website", False)),
                    "go_to_switch": bool(row.get("go_to_switch", True)),
                }
            )
        return ads

    def build_advert_res(
        self,
        base_url: str,
        language: str = "en",
        record_event: bool = True,
        endpoint: str = "/GetAdvert",
    ) -> bytes:
        ads = self._build_advert_items(base_url, language)
        if record_event:
            _safe_record_lobby_event(
                endpoint,
                "advert",
                f"Served {len(ads)} adverts",
                {
                    "language": language,
                    "count": len(ads),
                    "items": [
                        {"id": a["id"], "type": a["type"], "advertisment_url": a["advertisment_url"]}
                        for a in ads
                    ],
                },
            )
        return encode_advert_res(ads)

    def _broadcast_messages(self, account_id: int) -> List[Dict[str, Any]]:
        now = int(time.time())
        prof = state.get_profile(account_id)
        nick = str(prof.get("nickname", "Clack"))
        rows = state.list_broadcasts(enabled_only=True)
        out: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            out.append(
                {
                    "nickname": str(row.get("nickname") or nick),
                    "navigation_type": int(row.get("navigation_type", NavigationType.GACHA)),
                    "source": str(row.get("source", "Diamond Royale")),
                    "item_id": int(row.get("item_id", 203000001)),
                    "time_stamp": int(row.get("time_stamp") or now),
                    "source_id": int(row.get("source_id", row.get("id", idx))),
                }
            )
        return out

    def _scroll_marquees(self, language: str = "en") -> List[Dict[str, Any]]:
        now = int(time.time())
        rows = state.list_marquees(enabled_only=True)
        rows.sort(key=lambda m: (int(m.get("order_in_this_language", 1)), int(m.get("id", 1))))
        out: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            gos_url = str(row.get("gos_url") or row.get("link_url") or "")
            out.append(
                {
                    "language": str(row.get("language") or language),
                    "order_in_this_language": int(row.get("order_in_this_language", idx)),
                    "content": str(row.get("content", "")),
                    "start_time": int(row.get("start_time") or (now - 86400)),
                    "end_time": int(row.get("end_time") or (now + 365 * 86400)),
                    "region": str(row.get("region", "DEFAULT")),
                    "gos_pos": int(row.get("gos_pos", NavigationType.NONE)),
                    "gos_url": gos_url,
                    "use_embedded_browser": bool(row.get("use_embedded_browser", bool(gos_url))),
                    "sub_go_pos": str(row.get("sub_go_pos", "")),
                }
            )
        return out

    def build_broadcast_list_res(self, account_id: int, record_event: bool = True) -> bytes:
        msgs = self._broadcast_messages(account_id)
        if record_event:
            _safe_record_lobby_event(
                "/GetBroadcastList",
                "broadcast",
                f"Served {len(msgs)} lobby broadcasts",
                {"account_id": account_id, "count": len(msgs), "nicknames": [m["nickname"] for m in msgs]},
            )
        return encode_broadcast_list_res(msgs, silence_show_switch=False)

    def build_scroll_marquee_res(self, language: str = "en", record_event: bool = True) -> bytes:
        mqs = self._scroll_marquees(language)
        if record_event:
            _safe_record_lobby_event(
                "/GetScrollMarquee",
                "marquee",
                f"Served {len(mqs)} scroll marquees",
                {"language": language, "count": len(mqs), "contents": [m["content"] for m in mqs]},
            )
        return encode_scroll_marquee_res(mqs)

    def build_login_broadcast_res(self, account_id: int, language: str = "en") -> bytes:
        mqs = self._scroll_marquees(language)
        msgs = self._broadcast_messages(account_id)
        _safe_record_lobby_event(
            "/LoginGetBroadcast",
            "broadcast",
            f"Served {len(mqs)} marquees, {len(msgs)} broadcasts",
            {
                "account_id": account_id,
                "language": language,
                "marquees": [m["content"] for m in mqs],
                "broadcast_count": len(msgs),
            },
        )
        return encode_login_broadcast_res(
            marquees=mqs,
            messages=msgs,
            silence_show_switch=False,
        )

    # --- Activities, Bingo, Activeness ---

    def build_activity_desc_res(
        self,
        base_url: str,
        language: str = "en",
        record_event: bool = True,
    ) -> bytes:
        now = int(time.time())
        descs = _build_activity_descs(base_url)
        festivals = [
            {
                "event_id": 1,
                "table_type": EventTabType.FESTIVAL1,
                "table_sprite": "",
                "language": language,
                "event_title": "India V1 Festival",
                "event_lobby_icon": "",
                "start_time": "2026-01-01 00:00:00",
                "end_time": "2028-12-31 23:59:59",
                "festival_item_id": 203000001,
                "cdn_url": _resolve_banner_url(base_url, "/banners/announce_events.png"),
                "affiliate_table": 0,
                "group_id": 2,
            }
        ]
        entrances = [
            {
                "id": 1,
                "show_time": now - 86400,
                "start_time": now - 86400,
                "end_time": now + 30 * 86400,
                "go_url": "",
                "go_pos": NavigationType.ACTIVITY,
            },
            {
                "id": 2,
                "show_time": now - 86400,
                "start_time": now - 86400,
                "end_time": now + 30 * 86400,
                "go_url": "",
                "go_pos": NavigationType.GACHA,
            },
        ]
        bingo_info = [
            {
                "level": 1,
                "key_id": 203000001,
                "init_key_num": 5,
                "cost_key_num": 1,
                "cost_diamond": 10,
                "start_time": now - 86400,
                "end_time": now + 30 * 86400,
            }
        ]
        if record_event:
            _safe_record_lobby_event(
                "/GetActivityDesc",
                "event",
                f"Served {len(descs)} event descriptions",
                {
                    "language": language,
                    "count": len(descs),
                    "activity_ids": [d["activity_id"] for d in descs],
                    "titles": [d.get("act_title", "") for d in descs[:10]],
                },
            )
        return encode_activity_desc_res(
            activity_descs=descs,
            activity_festivals=festivals,
            entrance_list=entrances,
            bingo_info=bingo_info,
            bingo_rewards_info=self._bingo_lines,
        )

    def build_activity_info_res(self, account_id: int, record_event: bool = True) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            acts = self._sync_account_activities(acct)
            if record_event:
                _safe_record_lobby_event(
                    "/GetActivityInfo",
                    "event",
                    f"Served {len(acts)} account activity states",
                    {"account_id": account_id, "count": len(acts)},
                )
            return encode_activity_info_res(acts)

    def claim_activity_rewards(self, account_id: int, activity_ids: List[int], base_url: str) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            self._sync_account_activities(acct)
            desc_map = {int(d["activity_id"]): d for d in _build_activity_descs(base_url)}
            if not activity_ids:
                activity_ids = [
                    aid
                    for aid, st in acct.activity_states.items()
                    if st["state"] == ActivityState.FINISHED
                ]
            awards_to_grant: List[Dict[str, Any]] = []
            claimed_ids: List[int] = []
            for aid in activity_ids:
                st = acct.activity_states.get(aid)
                desc = desc_map.get(aid)
                if st is None and desc is not None:
                    st = {"id": aid, "data": int(desc.get("cdt_value", 1)), "state": ActivityState.FINISHED}
                    acct.activity_states[aid] = st
                if st is not None and st["state"] != ActivityState.AWARDED:
                    st["state"] = ActivityState.AWARDED
                    claimed_ids.append(aid)
                    if desc:
                        awards_to_grant.extend(desc.get("awards", ()))
            granted = self._grant_awards(account_id, awards_to_grant)
            if claimed_ids:
                for act_id in claimed_ids:
                    db.record_claim(account_id, "activity", act_id, {"activity_id": act_id, "granted": granted})
                self._save_acct_state(account_id, acct)
                _safe_record_lobby_event(
                    "/GetActivityRewards",
                    "event",
                    f"Claimed rewards for events {claimed_ids}",
                    {"account_id": account_id, "activity_ids": claimed_ids, "granted": granted},
                )
                db.log_action(account_id, "ACTIVITY_CLAIM", f"Claimed activity rewards {claimed_ids}", {"activity_ids": claimed_ids, "granted": granted})
            return encode_activity_rewards_res(
                items=granted["items"],
                coins=granted["coins"],
                gems=granted["gems"],
                activeness=granted["activeness"],
            )

    def trigger_activity(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            changed = False
            for aid in (1002, 3002):
                st = acct.activity_states.get(aid)
                if st and st["state"] == ActivityState.RECEIVED:
                    st["data"] = 1
                    st["state"] = ActivityState.FINISHED
                    changed = True
            if changed:
                self._save_acct_state(account_id, acct)
            return b""

    def build_fresh_activity_info_res(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            return encode_fresh_activity_info_res(
                day=acct.fresh_day,
                activities=acct.fresh_activities.values(),
            )

    def claim_fresh_activity_rewards(self, account_id: int, activity_ids: List[int]) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            if not activity_ids:
                activity_ids = [
                    aid
                    for aid, fa in acct.fresh_activities.items()
                    if fa["state"] == ActivityState.FINISHED
                ]
            awards_to_grant: List[Dict[str, Any]] = []
            claimed_ids: List[int] = []
            for aid in activity_ids:
                fa = acct.fresh_activities.get(aid)
                if fa is not None and fa["state"] != ActivityState.AWARDED:
                    fa["state"] = ActivityState.AWARDED
                    claimed_ids.append(aid)
                    awards_to_grant.extend(fa.get("awards", ()))
            granted = self._grant_awards(account_id, awards_to_grant)
            if claimed_ids:
                for act_id in claimed_ids:
                    db.record_claim(account_id, "activity", act_id, {"fresh_activity_id": act_id, "granted": granted})
                self._save_acct_state(account_id, acct)
                db.log_action(account_id, "FRESH_ACTIVITY_CLAIM", f"Claimed fresh activity rewards {claimed_ids}", {"activity_ids": claimed_ids, "granted": granted})
            return encode_fresh_activity_rewards_res(
                items=granted["items"],
                coins=granted["coins"],
                gems=granted["gems"],
                activeness=granted["activeness"],
            )

    def trigger_fresh_activity(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            changed = False
            for fa in acct.fresh_activities.values():
                if fa["state"] == ActivityState.RECEIVED:
                    fa["data"] = 1
                    fa["state"] = ActivityState.FINISHED
                    changed = True
            if changed:
                self._save_acct_state(account_id, acct)
            return b""

    def build_activeness_desc_res(self) -> bytes:
        return encode_activeness_desc_res(
            group_id=1,
            start_time="2026-01-01 00:00:00",
            end_time="2028-12-31 23:59:59",
            rewards=self._activeness_descs,
        )

    def build_activeness_info_res(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            return encode_activeness_and_reward_info_res(
                group_id=1,
                daily_activeness=acct.daily_activeness,
                weekly_activeness=acct.weekly_activeness,
                box_states=copy.deepcopy(acct.activeness_boxes),
            )

    def claim_activeness_reward(self, account_id: int, group_id: int, box_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            target_box = None
            for bs in acct.activeness_boxes:
                if bs["group_id"] == group_id and bs["box_id"] == box_id:
                    target_box = bs
                    break
            if target_box is None:
                for bs in acct.activeness_boxes:
                    if bs["box_id"] == box_id:
                        target_box = bs
                        break
            awards_to_grant: List[Dict[str, Any]] = []
            if target_box is not None and target_box["state"] != 2:
                target_box["state"] = 2
                for desc in self._activeness_descs:
                    if desc["box_id"] == target_box["box_id"]:
                        awards_to_grant.extend(desc.get("awards", ()))
                        break
                target_bid = int(target_box["box_id"])
                granted = self._grant_awards(account_id, awards_to_grant)
                db.record_claim(account_id, "activeness_box", target_bid, {"group_id": group_id, "box_id": target_bid, "granted": granted})
                self._save_acct_state(account_id, acct)
                db.log_action(account_id, "ACTIVENESS_CLAIM", f"Claimed activeness box {target_bid}", {"box_id": target_bid, "granted": granted})
            else:
                granted = self._grant_awards(account_id, awards_to_grant)
            return encode_activeness_reward_res(
                items=granted["items"],
                coins=granted["coins"],
                gems=granted["gems"],
            )

    def build_bingo_rewards_info_res(self, account_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            return encode_get_bingo_rewards_info_res(
                rewards=copy.deepcopy(acct.bingo_rewards),
                init_items=[{"id": 203000001, "cnt": 3}],
                init_coins=500,
            )

    def flip_bingo(self, account_id: int, activity_id: int, base_url: str) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            if not activity_id:
                for cid in range(4001, 4010):
                    cell = acct.activity_states.get(cid)
                    if cell and cell["state"] != ActivityState.AWARDED:
                        activity_id = cid
                        break
            st = acct.activity_states.get(activity_id)
            if st is not None and st["state"] != ActivityState.AWARDED:
                st["data"] = 1
                st["state"] = ActivityState.AWARDED
                if activity_id in acct.bingo_grid:
                    acct.bingo_grid[activity_id]["data"] = 1
                    acct.bingo_grid[activity_id]["state"] = ActivityState.AWARDED
                desc_map = {int(d["activity_id"]): d for d in _build_activity_descs(base_url)}
                desc = desc_map.get(activity_id)
                awards = desc.get("awards", ()) if desc else ()
                granted = self._grant_awards(account_id, awards)
                db.record_claim(account_id, "bingo_flip", activity_id, {"activity_id": activity_id, "granted": granted})
                self._save_acct_state(account_id, acct)
                db.log_action(account_id, "BINGO_FLIP", f"Flipped bingo cell {activity_id}", {"activity_id": activity_id, "granted": granted})
            return encode_flip_bingo_res(
                activity_id=activity_id,
                rewards=copy.deepcopy(acct.bingo_rewards),
            )

    def claim_bingo_line_reward(self, account_id: int, reward_id: int) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            awards_to_grant: List[Dict[str, Any]] = []
            claimed = False
            for br in acct.bingo_rewards:
                if br["rewards_id"] == reward_id and not br["awarded"]:
                    br["awarded"] = True
                    claimed = True
                    for line in self._bingo_lines:
                        if line["id"] == reward_id:
                            awards_to_grant.extend(line.get("awards", ()))
                            break
                    break
            granted = self._grant_awards(account_id, awards_to_grant)
            if claimed:
                db.record_claim(account_id, "bingo_line", reward_id, {"reward_id": reward_id, "granted": granted})
                self._save_acct_state(account_id, acct)
                db.log_action(account_id, "BINGO_LINE_CLAIM", f"Claimed bingo line {reward_id}", {"reward_id": reward_id, "granted": granted})
            return encode_get_bingo_rewards_res(
                reward_id=reward_id,
                items=granted["items"],
                coins=granted["coins"],
                gems=granted["gems"],
            )

    def finish_bingo_activity(self, account_id: int, activity_id: int, base_url: str) -> bytes:
        with self._lock:
            acct = self._get_acct(account_id)
            st = acct.activity_states.get(activity_id)
            if st is not None and st["state"] != ActivityState.AWARDED:
                st["data"] = 1
                st["state"] = ActivityState.AWARDED
                if activity_id in acct.bingo_grid:
                    acct.bingo_grid[activity_id]["data"] = 1
                    acct.bingo_grid[activity_id]["state"] = ActivityState.AWARDED
                desc_map = {int(d["activity_id"]): d for d in _build_activity_descs(base_url)}
                desc = desc_map.get(activity_id)
                awards = desc.get("awards", ()) if desc else ()
                granted = self._grant_awards(account_id, awards)
                db.record_claim(account_id, "bingo_finish", activity_id, {"activity_id": activity_id, "granted": granted})
                self._save_acct_state(account_id, acct)
                db.log_action(account_id, "BINGO_FINISH", f"Finished bingo cell {activity_id}", {"activity_id": activity_id, "granted": granted})
            return b""

    # --- Switches & GameBonus & LoginGetDesc ---

    def _feature_switches_list(self) -> List[Dict[str, Any]]:
        rows = state.list_feature_switches()
        if rows:
            switches = []
            for r in sorted(rows, key=lambda x: int(x.get("id", 0))):
                entry: Dict[str, Any] = {
                    "id": int(r["id"]),
                    "is_open": bool(r.get("is_open", True)),
                }
                if r.get("content"):
                    entry["content"] = str(r["content"])
                switches.append(entry)
            return switches
        switch_ids = sorted(
            val
            for name, val in vars(SwitchFunc).items()
            if not name.startswith("_") and isinstance(val, int) and val != SwitchFunc.NONE
        )
        return [
            {"id": sw_id, "is_open": sw_id != SwitchFunc.LEVEL_LIMITED_FOR_SPLASH_BANNER}
            for sw_id in switch_ids
        ]

    def build_all_switchs_res(self, record_event: bool = True) -> bytes:
        switches = self._feature_switches_list()
        if record_event:
            open_cnt = sum(1 for sw in switches if sw.get("is_open", True))
            _safe_record_lobby_event(
                "/GetAllSwitchs",
                "switch",
                f"Served {len(switches)} switches ({open_cnt} open)",
                {
                    "total": len(switches),
                    "open": open_cnt,
                    "closed_ids": [sw["id"] for sw in switches if not sw.get("is_open", True)],
                },
            )
        return encode_all_switchs_res(switches)

    def build_game_bonus_event_desc_res(self, record_event: bool = True) -> bytes:
        events = state.list_bonus_events(enabled_only=True)
        events.sort(key=lambda ev: int(ev.get("id", 1)))
        if record_event:
            _safe_record_lobby_event(
                "/GetGameBonusEventDesc",
                "bonus_event",
                f"Served {len(events)} 2x bonus events",
                {
                    "count": len(events),
                    "items": [
                        {
                            "id": ev.get("id"),
                            "exp_bonus": ev.get("exp_bonus"),
                            "gold_bonus": ev.get("gold_bonus"),
                        }
                        for ev in events
                    ],
                },
            )
        return encode_game_bonus_event_desc_res(events)

    def build_login_desc_res(self, base_url: str, language: str = "en") -> bytes:
        # Optional integration with other subsystems if they expose desc builders
        gacha_res = b""
        try:
            import proto.gacha_models as gm  # type: ignore

            if hasattr(gm, "encode_get_gacha_desc_res"):
                gacha_res = gm.encode_get_gacha_desc_res()
        except Exception:
            gacha_res = b""

        ranking_activity_config_res = b""
        try:
            import proto.leaderboard_models as lb  # type: ignore

            if hasattr(lb, "encode_ranking_activity_config_res"):
                ranking_activity_config_res = lb.encode_ranking_activity_config_res([])
        except Exception:
            ranking_activity_config_res = b""

        ads = self._build_advert_items(base_url, language)
        switches = self._feature_switches_list()
        descs = _build_activity_descs(base_url)
        bonuses = state.list_bonus_events(enabled_only=True)
        _safe_record_lobby_event(
            "/LoginGetDesc",
            "startup_desc",
            f"Served startup desc: {len(ads)} ads, {len(switches)} switches, {len(descs)} events, {len(bonuses)} bonus",
            {
                "language": language,
                "advert_count": len(ads),
                "switch_count": len(switches),
                "event_count": len(descs),
                "bonus_event_count": len(bonuses),
            },
        )

        return encode_login_desc_res(
            advert_res=self.build_advert_res(base_url, language, record_event=False),
            switchs_res=self.build_all_switchs_res(record_event=False),
            activity_res=self.build_activity_desc_res(base_url, language, record_event=False),
            gacha_res=gacha_res,
            ranking_activity_config_res=ranking_activity_config_res,
            game_bonus_event_res=self.build_game_bonus_event_desc_res(record_event=False),
        )


_service = ActivityService()


def get_activity_service() -> ActivityService:
    return _service


def handle_activity_request(
    handler: Any,
    path: str,
    client_ip: str = "",
    raw_body: bytes = b"",
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Activity, Attendance, Broadcast, Marquee, Splash, Advert, Bingo,
    Activeness, Switches, and GameBonus requests.
    Returns True if handled, False otherwise.
    """
    endpoint = _extract_endpoint(path)
    if endpoint not in ACTIVITY_ENDPOINTS:
        return False

    base_url = _banners_base(handler)
    language = decode_language_req(raw_body, field_num=1, default="en")

    if endpoint == "LoginGetDesc":
        res = _service.build_login_desc_res(base_url, language)
        _send_proto(handler, "LoginDescRes", res)
        return True

    if endpoint == "LoginGetSplash":
        res = _service.build_login_splash_res(account_id, base_url, language)
        _send_proto(handler, "LoginSplashRes", res)
        return True

    if endpoint == "LoginGetBroadcast":
        res = _service.build_login_broadcast_res(account_id, language)
        _send_proto(handler, "LoginBroadcastRes", res)
        return True

    if endpoint == "GetAnnouncement":
        res = _service.build_announcement_res(base_url, language)
        _send_proto(handler, "CSAnnouncementRes", res)
        return True

    if endpoint == "GetAttendance":
        need_clan = decode_get_attendance_req(raw_body) if raw_body else True
        res = _service.build_get_attendance_res(account_id, base_url, need_clan_info=need_clan)
        _send_proto(handler, "GetAttendanceRes", res)
        return True

    if endpoint == "GetAttendanceList":
        res = _service.build_attendance_list_res(account_id, base_url)
        _send_proto(handler, "CSGetAttendanceListRes", res)
        return True

    if endpoint == "AttendanceSignin":
        _service.sign_in_attendance(account_id)
        _send_proto(handler, "CSAttendanceSigninRes", b"")
        return True

    if endpoint == "GetNewPlayerRewardsList":
        res = _service.build_new_player_rewards_res(account_id)
        _send_proto(handler, "CSGetNewPlayerRewardsListRes", res)
        return True

    if endpoint == "NewPlayerSignin":
        fields = decode_proto(raw_body)
        reward_id = get_varint(fields, 1, 0)
        _service.sign_in_new_player(account_id, reward_id=reward_id)
        _send_proto(handler, "CSNewPlayerSigninRes", b"")
        return True

    if endpoint == "GetVeteranRewardList":
        res = _service.build_veteran_reward_list_res(account_id)
        _send_proto(handler, "CSGetVeteranRewardListRes", res)
        return True

    if endpoint == "VeteranClaimReward":
        fields = decode_proto(raw_body)
        reward_id = get_varint(fields, 1, 0)
        _service.claim_veteran_reward(account_id, reward_id=reward_id)
        _send_proto(handler, "CSVeteranClaimRewardRes", b"")
        return True

    if endpoint == "GetFestivalAttendanceInfo":
        res = _service.build_festival_attendance_info_res(account_id)
        _send_proto(handler, "CSGetFestivalAttendanceInfoRes", res)
        return True

    if endpoint == "FestivalAttendanceSignin":
        res = _service.sign_in_festival(account_id)
        _send_proto(handler, "CSFestivalAttendanceSigninRes", res)
        return True

    if endpoint == "GetFestivalItemInfo":
        _send_proto(handler, "CSGetFestivalItemInfoRes", encode_festival_item_info_res())
        return True

    if endpoint == "GetActivityDesc":
        res = _service.build_activity_desc_res(base_url, language)
        _send_proto(handler, "CSGetActivityDescRes", res)
        return True

    if endpoint == "GetActivityInfo":
        res = _service.build_activity_info_res(account_id)
        _send_proto(handler, "CSGetActivityInfoRes", res)
        return True

    if endpoint == "GetActivityRewards":
        req = decode_activity_rewards_req(raw_body)
        res = _service.claim_activity_rewards(account_id, req["activity_ids"], base_url)
        _send_proto(handler, "CSGetActivityRewardsRes", res)
        return True

    if endpoint == "ActivityTrigger":
        res = _service.trigger_activity(account_id)
        _send_proto(handler, "CSActivityTriggerRes", res)
        return True

    if endpoint == "GetFreshActivityInfo":
        res = _service.build_fresh_activity_info_res(account_id)
        _send_proto(handler, "CSGetFreshActivityInfoRes", res)
        return True

    if endpoint == "GetFreshActivityRewards":
        req = decode_fresh_activity_rewards_req(raw_body)
        res = _service.claim_fresh_activity_rewards(account_id, req["activity_ids"])
        _send_proto(handler, "CSGetFreshActivityRewardsRes", res)
        return True

    if endpoint == "FreshActivityTrigger":
        res = _service.trigger_fresh_activity(account_id)
        _send_proto(handler, "CSFreshActivityTriggerRes", res)
        return True

    if endpoint == "GetActivenessDesc":
        _send_proto(handler, "CSGetActivenessDescRes", _service.build_activeness_desc_res())
        return True

    if endpoint == "GetActivenessAndRewardInfo":
        res = _service.build_activeness_info_res(account_id)
        _send_proto(handler, "CSGetActivenessAndRewardInfoRes", res)
        return True

    if endpoint == "GetActivenessReward":
        req = decode_activeness_reward_req(raw_body)
        res = _service.claim_activeness_reward(account_id, req["group_id"], req["box_id"])
        _send_proto(handler, "CSGetActivenessRewardRes", res)
        return True

    if endpoint == "GetBingoRewardsInfo":
        res = _service.build_bingo_rewards_info_res(account_id)
        _send_proto(handler, "CSGetBingoRewardsInfoRes", res)
        return True

    if endpoint == "FlipBingo":
        req = decode_flip_bingo_req(raw_body)
        res = _service.flip_bingo(account_id, req["activity_id"], base_url)
        _send_proto(handler, "CSFlipBingoRes", res)
        return True

    if endpoint == "GetBingoRewards":
        reward_id = decode_get_bingo_rewards_req(raw_body)
        res = _service.claim_bingo_line_reward(account_id, reward_id)
        _send_proto(handler, "CSGetBingoRewardsRes", res)
        return True

    if endpoint == "FinishBingoActivity":
        req = decode_finish_bingo_activity_req(raw_body)
        res = _service.finish_bingo_activity(account_id, req["activity_id"], base_url)
        _send_proto(handler, "CSFinishBingoActivityRes", res)
        return True

    if endpoint in ("GetAdvert", "GetAds"):
        _send_proto(handler, "CSGetAdvertRes", _service.build_advert_res(base_url, language, endpoint=f"/{endpoint}"))
        return True

    if endpoint == "GetBroadcastList":
        _send_proto(handler, "CSGetBroadcastListRes", _service.build_broadcast_list_res(account_id))
        return True

    if endpoint == "GetScrollMarquee":
        _send_proto(handler, "CSScrollMarqueeRes", _service.build_scroll_marquee_res(language))
        return True

    if endpoint == "GetAllSwitchs":
        _send_proto(handler, "CSGetAllSwitchsRes", _service.build_all_switchs_res())
        return True

    if endpoint == "GetGameBonusEventDesc":
        _send_proto(handler, "CSGetGameBonusEventDescRes", _service.build_game_bonus_event_desc_res())
        return True

    if endpoint == "GetMatchDailyBonus":
        _send_proto(handler, "CSMatchDailyBonusRes", encode_match_daily_bonus_res())
        return True

    return False


handle_activity_post = handle_activity_request
