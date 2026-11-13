"""
HTTP request handlers for Free Fire 1.39 Clan / Guild System.

Primary endpoints required by Free Fire 1.39 client (ServiceMessageTypeHTTP):
- /GetClanInfoByClanID         -> proto.ClanInfo
- /GetClanInfoByClanName       -> proto.ClanInfo
- /FuzzySearchClanByName       -> proto.CSClanInfoBundleRes
- /GetRandomClanList           -> proto.CSClanInfoBundleRes
- /GetClanMembers              -> proto.ClanMemberListWithAccountInfo
- /GetClanNews                 -> proto.CSClanNewsRes
- /GetClanSignInRewardsByLevel -> proto.CSClanSignInRes
- /ClanSignIn                  -> proto.CSClanSignInRes
- /ClaimSignInReward           -> proto.CSClanSignInRes
- /GetClanRaceInfo             -> proto.CSGetClanRaceInfoRes
- /ClaimClanRaceAward          -> proto.CSGetClanRaceInfoRes
- /ExchangeAwardWithRP         -> proto.CSGetClanRaceInfoRes
- /CreateClan                  -> proto.CSClanIDRes
- /RequestJoinClan             -> Empty (auto-joins when EntryType_AUTO)
- /QuitClan                    -> Empty
- /DismissClan                 -> Empty
- /ModifyClanInfo              -> Empty
- /ModifyClanName              -> Empty
- /ExtendClanScale             -> proto.CSExtendClanScaleRes
- /GetClanApplicantListByClanID -> proto.AccountInfoBasicBundleRes
- /ApproveJoinClanApplication  -> Empty
- /DeclineJoinClanApplication  -> Empty
- /InviteToClan                -> Empty
- /ApproveJoinClanInvitation   -> Empty
- /ChangeMemberTypeByCaptain   -> Empty
- /ReassignCaptain             -> Empty
- /RemoveClanMember            -> Empty
- /GetClanLuckyBagsInfo        -> proto.CSGetClanLuckyBagInfoRes
- /DrawClanLuckyBag            -> proto.CSDrawClanLuckyBagRes
- /GetClanWeekLeaderboardInfo  -> proto.CSGetClanWeekLeaderboardInfoRes

Integrates with core.state.state for player profiles, wallet, and unlocked items.
"""

from __future__ import annotations

import copy
import threading
import time
from typing import Any, Dict, List, Optional

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.clan_models import (
    AwardType,
    ClanMainType,
    ClanSignInRewardStatus,
    EntryType,
    MemberType,
    NewsType,
    decode_change_member_type_req,
    decode_claim_signin_reward_req,
    decode_clan_id_req,
    decode_clan_info_req,
    decode_clan_name_req,
    decode_create_clan_req,
    decode_draw_lucky_bag_req,
    decode_exchange_award_with_rp_req,
    decode_get_clan_signin_rewards_req,
    decode_invite_to_clan_req,
    decode_modify_clan_info_req,
    decode_modify_clan_name_req,
    decode_process_invite_req,
    decode_process_join_clan_req,
    decode_random_clan_list_req,
    decode_reassign_captain_req,
    decode_remove_clan_member_req,
    encode_account_info_basic_bundle_res,
    encode_clan_id_res,
    encode_clan_info,
    encode_clan_info_bundle_res,
    encode_clan_lucky_bag_info_res,
    encode_clan_member_list_with_account_info,
    encode_clan_news_res,
    encode_clan_race_info_res,
    encode_clan_signin_res,
    encode_clan_week_leaderboard_info_res,
    encode_draw_clan_lucky_bag_res,
    encode_extend_clan_scale_res,
)

CLAN_ENDPOINTS = {
    "CreateClan",
    "RequestJoinClan",
    "GetClanApplicantListByClanID",
    "ApproveJoinClanApplication",
    "DeclineJoinClanApplication",
    "InviteToClan",
    "ApproveJoinClanInvitation",
    "ChangeMemberTypeByCaptain",
    "ReassignCaptain",
    "RemoveClanMember",
    "QuitClan",
    "GetClanInfoByClanID",
    "GetClanInfoByClanName",
    "FuzzySearchClanByName",
    "GetClanMembers",
    "ModifyClanInfo",
    "ModifyClanName",
    "GetRandomClanList",
    "DismissClan",
    "ExtendClanScale",
    "ClanSignIn",
    "GetClanSignInRewardsByLevel",
    "ClaimSignInReward",
    "GetClanRaceInfo",
    "ClaimClanRaceAward",
    "ExchangeAwardWithRP",
    "GetClanLuckyBagsInfo",
    "DrawClanLuckyBag",
    "GetClanNews",
    "GetClanWeekLeaderboardInfo",
}


def _default_signin_rewards(clan_level: int = 4) -> List[Dict[str, Any]]:
    """Build 7-day weekday (1..7) guild sign-in rewards for the given clan level."""
    lvl = max(1, int(clan_level))
    return [
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": lvl,
                "weekday": 1,
                "award": {"award_type": AwardType.COINS, "award_id": 0, "award_num": 500 * lvl},
            },
            "status": ClanSignInRewardStatus.SIGNED,
        },
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": lvl,
                "weekday": 2,
                "award": {"award_type": AwardType.ITEM, "award_id": 200001, "award_num": 10},
            },
            "status": ClanSignInRewardStatus.SIGNED,
        },
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": lvl,
                "weekday": 3,
                "award": {"award_type": AwardType.COINS, "award_id": 0, "award_num": 1000 * lvl},
            },
            "status": ClanSignInRewardStatus.SIGNED,
        },
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": lvl,
                "weekday": 4,
                "award": {"award_type": AwardType.GEMS, "award_id": 0, "award_num": 25 * lvl},
            },
            "status": ClanSignInRewardStatus.SIGNED,
        },
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": lvl,
                "weekday": 5,
                "award": {"award_type": AwardType.ITEM, "award_id": 200001, "award_num": 25},
            },
            "status": ClanSignInRewardStatus.NOT_SIGNED,
        },
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": lvl,
                "weekday": 6,
                "award": {"award_type": AwardType.COINS, "award_id": 0, "award_num": 2000 * lvl},
            },
            "status": ClanSignInRewardStatus.NOT_SIGNED,
        },
        {
            "desc": {
                "sign_in_group": 1,
                "clan_level": lvl,
                "weekday": 7,
                "award": {"award_type": AwardType.GEMS, "award_id": 0, "award_num": 100},
            },
            "status": ClanSignInRewardStatus.NOT_SIGNED,
        },
    ]


def _default_race_rewards() -> List[Dict[str, Any]]:
    """Build 4 Guild Tournament / Dog-Tag race reward stages."""
    return [
        {
            "stage_id": 1,
            "min_race_point": 500,
            "race_point_cost": 100,
            "reward_honor": 500,
            "all_member_award": {"award_type": AwardType.COINS, "award_id": 0, "award_num": 1000},
            "unlock_award": {"award_type": AwardType.COINS, "award_id": 0, "award_num": 500},
        },
        {
            "stage_id": 2,
            "min_race_point": 1000,
            "race_point_cost": 200,
            "reward_honor": 1000,
            "all_member_award": {"award_type": AwardType.ITEM, "award_id": 200001, "award_num": 20},
            "unlock_award": {"award_type": AwardType.COINS, "award_id": 0, "award_num": 1000},
        },
        {
            "stage_id": 3,
            "min_race_point": 1500,
            "race_point_cost": 300,
            "reward_honor": 1500,
            "all_member_award": {"award_type": AwardType.GEMS, "award_id": 0, "award_num": 50},
            "unlock_award": {"award_type": AwardType.COINS, "award_id": 0, "award_num": 2000},
        },
        {
            "stage_id": 4,
            "min_race_point": 2000,
            "race_point_cost": 400,
            "reward_honor": 2500,
            "all_member_award": {"award_type": AwardType.GEMS, "award_id": 0, "award_num": 150},
            "unlock_award": {"award_type": AwardType.GEMS, "award_id": 0, "award_num": 100},
        },
    ]


class ClanService:
    """Thread-safe Clan / Guild state synchronized with core.state.state."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        now = int(time.time())
        self._next_clan_id = 50005
        self._clans: Dict[int, Dict[str, Any]] = {}
        self._members: Dict[int, Dict[int, Dict[str, Any]]] = {}
        self._news: Dict[int, List[Dict[str, Any]]] = {}
        self._applicants: Dict[int, List[int]] = {}
        self._lucky_bags: Dict[int, List[Dict[str, Any]]] = {}
        self._lucky_bag_draws: Dict[int, List[Dict[str, Any]]] = {}
        self._signin_rewards: Dict[int, List[Dict[str, Any]]] = {}
        self._race_exchanges: Dict[int, List[Dict[str, Any]]] = {}
        self._seed(now)

    def _seed(self, now: int) -> None:
        clans_seed = [
            {
                "clan_id": 50001,
                "clan_name": "INDIA V1",
                "create_at": 1570000000,
                "captain_id": 10001,
                "clan_level": 4,
                "capacity": 35,
                "entry_level": 1,
                "entry_type": EntryType.AUTO,
                "clan_logo": "",
                "announcement": "Welcome to INDIA V1! Daily Sign-In & Guild Race active.",
                "slogan": "India V1 1.39 - Play Fair & Win!",
                "region": "DEFAULT",
                "extended_times": 1,
                "vice_captains": [20001],
                "honor_point": 128500,
                "race_point": 1850,
                "last_gain_rp_at": now - 300,
                "claim_rp_award_at": 0,
                "area_id": 1,
                "play_style": 1,
                "members": [
                    (10001, MemberType.CAPTAIN, 42500, 650),
                    (20001, MemberType.VICE_CAPTAIN, 31200, 480),
                    (20002, MemberType.NORMAL_MEMBER, 22400, 320),
                    (20003, MemberType.NORMAL_MEMBER, 18900, 240),
                    (20005, MemberType.NORMAL_MEMBER, 13500, 160),
                ],
            },
            {
                "clan_id": 50002,
                "clan_name": "FF_LEGENDS",
                "create_at": 1571000000,
                "captain_id": 20004,
                "clan_level": 3,
                "capacity": 30,
                "entry_level": 10,
                "entry_type": EntryType.AUTO,
                "clan_logo": "",
                "announcement": "Active ranked squadrons every evening.",
                "slogan": "Push Heroic together!",
                "region": "DEFAULT",
                "extended_times": 0,
                "vice_captains": [20010],
                "honor_point": 84200,
                "race_point": 1200,
                "last_gain_rp_at": now - 900,
                "claim_rp_award_at": 0,
                "area_id": 2,
                "play_style": 2,
                "members": [
                    (20004, MemberType.CAPTAIN, 36000, 500),
                    (20010, MemberType.VICE_CAPTAIN, 28200, 420),
                    (20006, MemberType.NORMAL_MEMBER, 20000, 280),
                ],
            },
            {
                "clan_id": 50003,
                "clan_name": "HEADSHOT",
                "create_at": 1572000000,
                "captain_id": 20007,
                "clan_level": 2,
                "capacity": 25,
                "entry_level": 5,
                "entry_type": EntryType.MANUALLY,
                "clan_logo": "",
                "announcement": "Sniper & rushers welcome.",
                "slogan": "One tap, one Booyah.",
                "region": "DEFAULT",
                "extended_times": 0,
                "vice_captains": [],
                "honor_point": 45600,
                "race_point": 800,
                "last_gain_rp_at": now - 1800,
                "claim_rp_award_at": 0,
                "area_id": 1,
                "play_style": 3,
                "members": [
                    (20007, MemberType.CAPTAIN, 26000, 480),
                    (20008, MemberType.NORMAL_MEMBER, 19600, 320),
                ],
            },
            {
                "clan_id": 50004,
                "clan_name": "BOOYAH_CREW",
                "create_at": 1573000000,
                "captain_id": 20009,
                "clan_level": 4,
                "capacity": 35,
                "entry_level": 1,
                "entry_type": EntryType.AUTO,
                "clan_logo": "",
                "announcement": "Open guild for casual and ranked players!",
                "slogan": "Casual fun & Guild Wars",
                "region": "DEFAULT",
                "extended_times": 0,
                "vice_captains": [],
                "honor_point": 96400,
                "race_point": 1450,
                "last_gain_rp_at": now - 600,
                "claim_rp_award_at": 0,
                "area_id": 3,
                "play_style": 1,
                "members": [
                    (20009, MemberType.CAPTAIN, 96400, 1450),
                ],
            },
        ]

        for c in clans_seed:
            cid = c["clan_id"]
            members_spec = c.pop("members")
            c["member_num"] = len(members_spec)
            self._clans[cid] = c
            self._members[cid] = {}
            for idx, (aid, mtype, hp, rp) in enumerate(members_spec):
                self._members[cid][aid] = {
                    "account_id": aid,
                    "clan_id": cid,
                    "member_type": mtype,
                    "join_at": c["create_at"] + idx * 3600,
                    "region": c["region"],
                    "honor_point": hp,
                    "race_point": rp,
                    "last_gain_rp_at": now - (idx + 1) * 300,
                }
            self._news[cid] = [
                {
                    "type": NewsType.LEVEL_UP,
                    "content": {"account_id": c["captain_id"], "member_type": MemberType.CAPTAIN, "level": c["clan_level"]},
                    "update_time": now - 7200,
                },
                {
                    "type": NewsType.EP_BUNDLE,
                    "content": {"account_id": c["captain_id"], "member_type": MemberType.CAPTAIN, "level": c["clan_level"]},
                    "update_time": now - 3600,
                },
                {
                    "type": NewsType.JOIN,
                    "content": {"account_id": members_spec[-1][0], "member_type": members_spec[-1][1], "level": c["clan_level"]},
                    "update_time": now - 1200,
                },
            ]
            self._applicants[cid] = [20009] if cid == 50001 else []
            self._lucky_bags[cid] = [
                {
                    "clan_id": cid,
                    "bag_id": cid * 10 + 1,
                    "creater_id": c["captain_id"],
                    "created_at": now - 1800,
                    "total_num": 10,
                    "taken_num": 2,
                    "reason": 1,
                }
            ]
            self._lucky_bag_draws[cid] = []

    def _sync_player_clan(self, account_id: int, clan_id: int, clan_name: str) -> None:
        """Keep core.state player & profile clan_id/clan_name in sync."""
        if account_id == DEFAULT_ACCOUNT_ID:
            state.update_profile(account_id, clan_id=clan_id, clan_name=clan_name)
        else:
            if state.get_player(account_id) is not None:
                state.upsert_player(account_id, clan_id=clan_id, clan_name=clan_name)
            state.update_profile(account_id, clan_id=clan_id, clan_name=clan_name)

    def _get_basic_info(self, account_id: int) -> Dict[str, Any]:
        if account_id == DEFAULT_ACCOUNT_ID:
            return state.get_profile(account_id)
        player = state.get_player(account_id)
        if player is not None:
            return player
        return state.get_profile(account_id)

    def _refresh_clan_counts(self, clan_id: int) -> None:
        clan = self._clans.get(clan_id)
        if not clan:
            return
        members = self._members.get(clan_id, {})
        clan["member_num"] = len(members)
        clan["vice_captains"] = [
            aid for aid, m in members.items() if m["member_type"] == MemberType.VICE_CAPTAIN
        ]

    def _append_news(
        self, clan_id: int, news_type: int, account_id: int, member_type: int, level: int = 1
    ) -> None:
        news = self._news.setdefault(clan_id, [])
        news.insert(
            0,
            {
                "type": news_type,
                "content": {
                    "account_id": account_id,
                    "member_type": member_type,
                    "level": level,
                },
                "update_time": int(time.time()),
            },
        )
        if len(news) > 30:
            del news[30:]

    def get_clan_by_id(self, clan_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> Optional[Dict[str, Any]]:
        with self._lock:
            cid = int(clan_id)
            if cid == 0:
                prof = state.get_profile(account_id)
                cid = int(prof.get("clan_id", 0))
            if cid == 0:
                return None
            clan = self._clans.get(cid)
            if not clan:
                return None
            self._refresh_clan_counts(cid)
            return copy.deepcopy(clan)

    def get_clan_by_name(self, clan_name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            target = clan_name.strip().lower()
            for cid, clan in self._clans.items():
                if clan["clan_name"].lower() == target:
                    self._refresh_clan_counts(cid)
                    return copy.deepcopy(clan)
            return None

    def fuzzy_search_clans(self, keyword: str) -> List[Dict[str, Any]]:
        with self._lock:
            q = keyword.strip().lower()
            out: List[Dict[str, Any]] = []
            for cid, clan in self._clans.items():
                if not q or q in clan["clan_name"].lower() or q in clan.get("slogan", "").lower():
                    self._refresh_clan_counts(cid)
                    out.append(copy.deepcopy(clan))
            return out

    def get_random_clans(
        self,
        clan_list_type: int = ClanMainType.NONE,
        area_id: int = 0,
        play_style: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            matched: List[Dict[str, Any]] = []
            for cid, clan in self._clans.items():
                self._refresh_clan_counts(cid)
                if clan_list_type == ClanMainType.AREA and area_id and clan.get("area_id") != area_id:
                    continue
                if clan_list_type == ClanMainType.PLAY_STYLE and play_style and clan.get("play_style") != play_style:
                    continue
                matched.append(copy.deepcopy(clan))
            if not matched:
                for cid, clan in self._clans.items():
                    self._refresh_clan_counts(cid)
                    matched.append(copy.deepcopy(clan))
            return matched

    def get_clan_members(self, clan_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            cid = int(clan_id)
            if cid == 0:
                cid = int(state.get_profile(account_id).get("clan_id", 0))
            members = self._members.get(cid, {})
            result: List[Dict[str, Any]] = []
            for aid, m in members.items():
                entry = copy.deepcopy(m)
                entry["basic_info"] = self._get_basic_info(aid)
                result.append(entry)
            result.sort(key=lambda x: (-x["member_type"], -x["honor_point"], x["account_id"]))
            return result

    def get_clan_news(self, clan_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            cid = int(clan_id)
            if cid == 0:
                cid = int(state.get_profile(account_id).get("clan_id", 0))
            return copy.deepcopy(self._news.get(cid, []))

    def create_clan(
        self,
        account_id: int,
        clan_name: str,
        announcement: str = "",
        slogan: str = "",
        entry_type: int = EntryType.AUTO,
        area_id: int = 1,
        play_style: int = 1,
    ) -> int:
        with self._lock:
            now = int(time.time())
            # Remove from previous clan if any
            old_cid = int(state.get_profile(account_id).get("clan_id", 0))
            if old_cid and old_cid in self._members:
                self._members[old_cid].pop(account_id, None)
                self._refresh_clan_counts(old_cid)

            cid = self._next_clan_id
            self._next_clan_id += 1
            clean_name = clan_name.strip() or f"CLAN_{cid}"
            clan = {
                "clan_id": cid,
                "clan_name": clean_name,
                "create_at": now,
                "captain_id": account_id,
                "clan_level": 1,
                "capacity": 20,
                "member_num": 1,
                "entry_level": 1,
                "entry_type": entry_type or EntryType.AUTO,
                "clan_logo": "",
                "announcement": announcement or f"Welcome to {clean_name}!",
                "slogan": slogan or "Let's get that Booyah!",
                "region": "DEFAULT",
                "extended_times": 0,
                "vice_captains": [],
                "honor_point": 0,
                "race_point": 0,
                "last_gain_rp_at": 0,
                "claim_rp_award_at": 0,
                "area_id": area_id or 1,
                "play_style": play_style or 1,
            }
            self._clans[cid] = clan
            self._members[cid] = {
                account_id: {
                    "account_id": account_id,
                    "clan_id": cid,
                    "member_type": MemberType.CAPTAIN,
                    "join_at": now,
                    "region": "DEFAULT",
                    "honor_point": 0,
                    "race_point": 0,
                    "last_gain_rp_at": 0,
                }
            }
            self._news[cid] = []
            self._applicants[cid] = []
            self._lucky_bags[cid] = []
            self._lucky_bag_draws[cid] = []
            self._append_news(cid, NewsType.JOIN, account_id, MemberType.CAPTAIN, 1)
            self._sync_player_clan(account_id, cid, clean_name)
            return cid

    def join_clan(self, clan_id: int, account_id: int) -> bool:
        with self._lock:
            cid = int(clan_id)
            clan = self._clans.get(cid)
            if not clan:
                return False
            if clan.get("entry_type") == EntryType.MANUALLY:
                apps = self._applicants.setdefault(cid, [])
                if account_id not in apps:
                    apps.append(account_id)
                return True
            return self._add_member(cid, account_id)

    def _add_member(self, cid: int, account_id: int) -> bool:
        clan = self._clans.get(cid)
        if not clan:
            return False
        old_cid = int(state.get_profile(account_id).get("clan_id", 0))
        if old_cid and old_cid != cid and old_cid in self._members:
            self._members[old_cid].pop(account_id, None)
            self._refresh_clan_counts(old_cid)
        now = int(time.time())
        members = self._members.setdefault(cid, {})
        if account_id not in members:
            members[account_id] = {
                "account_id": account_id,
                "clan_id": cid,
                "member_type": MemberType.NORMAL_MEMBER,
                "join_at": now,
                "region": clan["region"],
                "honor_point": 0,
                "race_point": 0,
                "last_gain_rp_at": 0,
            }
            self._append_news(cid, NewsType.JOIN, account_id, MemberType.NORMAL_MEMBER, clan["clan_level"])
        self._refresh_clan_counts(cid)
        self._sync_player_clan(account_id, cid, clan["clan_name"])
        return True

    def quit_clan(self, clan_id: int, account_id: int) -> bool:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 0))
            if cid not in self._members:
                return False
            self._members[cid].pop(account_id, None)
            self._refresh_clan_counts(cid)
            self._sync_player_clan(account_id, 0, "")
            return True

    def dismiss_clan(self, clan_id: int, account_id: int) -> bool:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 0))
            clan = self._clans.pop(cid, None)
            if not clan:
                return False
            members = self._members.pop(cid, {})
            for aid in members:
                self._sync_player_clan(aid, 0, "")
            self._news.pop(cid, None)
            self._applicants.pop(cid, None)
            return True

    def modify_clan_info(
        self,
        clan_id: int,
        account_id: int,
        announcement: Optional[str] = None,
        slogan: Optional[str] = None,
        entry_type: Optional[int] = None,
        area_id: Optional[int] = None,
        play_style: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 0))
            clan = self._clans.get(cid)
            if not clan:
                return None
            if announcement is not None:
                clan["announcement"] = announcement
            if slogan is not None:
                clan["slogan"] = slogan
            if entry_type:
                clan["entry_type"] = int(entry_type)
            if area_id:
                clan["area_id"] = int(area_id)
            if play_style:
                clan["play_style"] = int(play_style)
            return copy.deepcopy(clan)

    def modify_clan_name(self, clan_id: int, account_id: int, clan_name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 0))
            clan = self._clans.get(cid)
            if not clan or not clan_name.strip():
                return None
            clan["clan_name"] = clan_name.strip()
            for aid in self._members.get(cid, {}):
                self._sync_player_clan(aid, cid, clan["clan_name"])
            return copy.deepcopy(clan)

    def extend_clan_scale(self, clan_id: int, account_id: int) -> Dict[str, int]:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 0))
            clan = self._clans.get(cid)
            if not clan:
                return {"clan_id": cid, "capacity": 20, "extended_times": 0}
            clan["capacity"] = int(clan.get("capacity", 20)) + 5
            clan["extended_times"] = int(clan.get("extended_times", 0)) + 1
            return {
                "clan_id": cid,
                "capacity": clan["capacity"],
                "extended_times": clan["extended_times"],
            }

    def list_applicants(self, clan_id: int, account_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 0))
            return [self._get_basic_info(aid) for aid in self._applicants.get(cid, [])]

    def process_application(self, clan_id: int, applicant_id: int, approve: bool) -> bool:
        with self._lock:
            cid = int(clan_id)
            apps = self._applicants.get(cid, [])
            if applicant_id in apps:
                apps.remove(applicant_id)
            if approve:
                return self._add_member(cid, applicant_id)
            return True

    def change_member_type(self, account_id: int, changee_id: int, target_type: int) -> bool:
        with self._lock:
            cid = int(state.get_profile(account_id).get("clan_id", 0))
            member = self._members.get(cid, {}).get(int(changee_id))
            if not member:
                return False
            member["member_type"] = int(target_type)
            self._refresh_clan_counts(cid)
            lvl = self._clans[cid]["clan_level"] if cid in self._clans else 1
            self._append_news(cid, NewsType.CHANGE_TYPE, int(changee_id), int(target_type), lvl)
            return True

    def reassign_captain(self, account_id: int, reassignee_id: int) -> bool:
        with self._lock:
            cid = int(state.get_profile(account_id).get("clan_id", 0))
            members = self._members.get(cid, {})
            if account_id not in members or reassignee_id not in members:
                return False
            members[account_id]["member_type"] = MemberType.NORMAL_MEMBER
            members[reassignee_id]["member_type"] = MemberType.CAPTAIN
            if cid in self._clans:
                self._clans[cid]["captain_id"] = reassignee_id
            self._refresh_clan_counts(cid)
            return True

    def remove_member(self, clan_id: int, removee_id: int) -> bool:
        with self._lock:
            cid = int(clan_id)
            if cid not in self._members:
                return False
            self._members[cid].pop(int(removee_id), None)
            self._refresh_clan_counts(cid)
            self._sync_player_clan(int(removee_id), 0, "")
            return True

    def _ensure_signin_rewards(self, account_id: int, clan_level: int) -> List[Dict[str, Any]]:
        if account_id not in self._signin_rewards:
            self._signin_rewards[account_id] = _default_signin_rewards(clan_level)
        return self._signin_rewards[account_id]

    def get_signin_rewards_by_level(
        self, clan_level: int, account_id: int = DEFAULT_ACCOUNT_ID
    ) -> List[Dict[str, Any]]:
        with self._lock:
            lvl = max(1, int(clan_level))
            rewards = self._ensure_signin_rewards(account_id, lvl)
            out = copy.deepcopy(rewards)
            for item in out:
                item["desc"]["clan_level"] = lvl
            return out

    def clan_signin(self, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            clan = self.get_clan_by_id(0, account_id=account_id)
            lvl = clan["clan_level"] if clan else 4
            rewards = self._ensure_signin_rewards(account_id, lvl)
            for item in rewards:
                if item["status"] == ClanSignInRewardStatus.NOT_SIGNED:
                    item["status"] = ClanSignInRewardStatus.SIGNED
                    break
            return copy.deepcopy(rewards)

    def claim_signin_reward(self, weekday: int, account_id: int = DEFAULT_ACCOUNT_ID) -> List[Dict[str, Any]]:
        with self._lock:
            clan = self.get_clan_by_id(0, account_id=account_id)
            lvl = clan["clan_level"] if clan else 4
            rewards = self._ensure_signin_rewards(account_id, lvl)
            for item in rewards:
                wd = item["desc"]["weekday"]
                if (weekday == 0 or wd == weekday) and item["status"] == ClanSignInRewardStatus.SIGNED:
                    item["status"] = ClanSignInRewardStatus.CLAIMED
                    award = item["desc"]["award"]
                    self._grant_award(award, account_id)
                    if weekday != 0:
                        break
            return copy.deepcopy(rewards)

    def _grant_award(self, award: Dict[str, Any], account_id: int) -> None:
        atype = int(award.get("award_type", AwardType.NONE))
        aid = int(award.get("award_id", 0))
        num = int(award.get("award_num", 0))
        if atype == AwardType.COINS and num > 0:
            state.grant_currency(coins=num, account_id=account_id)
        elif atype == AwardType.GEMS and num > 0:
            state.grant_currency(gems=num, account_id=account_id)
        elif atype == AwardType.ITEM and aid > 0 and num > 0:
            state.add_item(aid, num)

    def get_clan_race_info(
        self, clan_id: int = 0, account_id: int = DEFAULT_ACCOUNT_ID
    ) -> Dict[str, Any]:
        with self._lock:
            clan = self.get_clan_by_id(clan_id, account_id=account_id)
            cid = clan["clan_id"] if clan else 50001
            rp = clan["race_point"] if clan else 1850
            rewards = _default_race_rewards()
            stage = 0
            for r in rewards:
                if rp >= r["min_race_point"]:
                    stage = r["stage_id"]
            return {
                "opening_info": {
                    "region": clan["region"] if clan else "DEFAULT",
                    "start_week_day": 1,
                    "start_time": "00:00:00",
                    "end_week_day": 6,
                    "end_time": "23:59:59",
                },
                "stage": max(1, stage),
                "is_open": True,
                "rewards": rewards,
                "race_point": rp,
                "latest_race_week_id": 1,
                "exchange_info": copy.deepcopy(self._race_exchanges.get(cid, [])),
                "race_close_info": {
                    "region": clan["region"] if clan else "DEFAULT",
                    "start_time": "",
                    "end_time": "",
                },
                "timezone_offset_secs": 0,
            }

    def claim_clan_race_award(
        self, clan_id: int, account_id: int = DEFAULT_ACCOUNT_ID
    ) -> Dict[str, Any]:
        with self._lock:
            clan = self.get_clan_by_id(clan_id, account_id=account_id)
            if clan and clan["clan_id"] in self._clans:
                self._clans[clan["clan_id"]]["claim_rp_award_at"] = int(time.time())
            info = self.get_clan_race_info(clan_id, account_id=account_id)
            for rew in info["rewards"]:
                if info["race_point"] >= rew["min_race_point"]:
                    self._grant_award(rew["all_member_award"], account_id)
            return info

    def exchange_award_with_rp(
        self, clan_id: int, stage: int, account_id: int = DEFAULT_ACCOUNT_ID
    ) -> Dict[str, Any]:
        with self._lock:
            clan = self.get_clan_by_id(clan_id, account_id=account_id)
            cid = clan["clan_id"] if clan else 50001
            ex_list = self._race_exchanges.setdefault(cid, [])
            ex_list.append(
                {
                    "account_id": account_id,
                    "stage": int(stage),
                    "exchange_at": int(time.time()),
                }
            )
            for rew in _default_race_rewards():
                if rew["stage_id"] == int(stage):
                    self._grant_award(rew["all_member_award"], account_id)
                    break
            return self.get_clan_race_info(cid, account_id=account_id)

    def get_lucky_bags_info(
        self, clan_id: int, account_id: int = DEFAULT_ACCOUNT_ID
    ) -> Dict[str, Any]:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 50001))
            return {
                "lucky_bags": copy.deepcopy(self._lucky_bags.get(cid, [])),
                "draws": copy.deepcopy(self._lucky_bag_draws.get(cid, [])),
            }

    def draw_lucky_bag(
        self, clan_id: int, bag_id: int, account_id: int = DEFAULT_ACCOUNT_ID
    ) -> int:
        with self._lock:
            cid = int(clan_id) or int(state.get_profile(account_id).get("clan_id", 50001))
            for bag in self._lucky_bags.get(cid, []):
                if bag["bag_id"] == int(bag_id) and bag["taken_num"] < bag["total_num"]:
                    bag["taken_num"] += 1
            self._lucky_bag_draws.setdefault(cid, []).append(
                {
                    "account_id": account_id,
                    "bag_id": int(bag_id),
                    "opened_at": int(time.time()),
                }
            )
            tokens = 15
            state.add_item(200001, tokens)
            return tokens


clan_service = ClanService()


def handle_clan_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Clan / Guild HTTP endpoints. Returns True if path was handled.
    """
    endpoint = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    if endpoint not in CLAN_ENDPOINTS:
        return False

    if endpoint == "GetClanInfoByClanID":
        req = decode_clan_info_req(raw_body)
        clan = clan_service.get_clan_by_id(req["clan_id"], account_id=account_id)
        if not clan:
            handler.send_proto("ClanInfo (Empty)", b"")
        else:
            handler.send_proto("ClanInfo", encode_clan_info(clan))
        return True

    if endpoint == "GetClanInfoByClanName":
        req = decode_clan_name_req(raw_body)
        clan = clan_service.get_clan_by_name(req["clan_name"])
        handler.send_proto("ClanInfo", encode_clan_info(clan) if clan else b"")
        return True

    if endpoint == "FuzzySearchClanByName":
        req = decode_clan_name_req(raw_body)
        clans = clan_service.fuzzy_search_clans(req["clan_name"])
        handler.send_proto("CSClanInfoBundleRes", encode_clan_info_bundle_res(clans))
        return True

    if endpoint == "GetRandomClanList":
        req = decode_random_clan_list_req(raw_body)
        clans = clan_service.get_random_clans(
            clan_list_type=req["clan_list_type"],
            area_id=req["area_id"],
            play_style=req["play_style"],
        )
        handler.send_proto("CSClanInfoBundleRes", encode_clan_info_bundle_res(clans))
        return True

    if endpoint == "GetClanMembers":
        req = decode_clan_id_req(raw_body)
        members = clan_service.get_clan_members(req["clan_id"], account_id=account_id)
        handler.send_proto(
            "ClanMemberListWithAccountInfo",
            encode_clan_member_list_with_account_info(members),
        )
        return True

    if endpoint == "GetClanNews":
        req = decode_clan_id_req(raw_body)
        news = clan_service.get_clan_news(req["clan_id"], account_id=account_id)
        handler.send_proto("CSClanNewsRes", encode_clan_news_res(news))
        return True

    if endpoint == "CreateClan":
        req = decode_create_clan_req(raw_body)
        captain_id = req["captain_id"] or account_id
        cid = clan_service.create_clan(
            account_id=captain_id,
            clan_name=req["clan_name"],
            announcement=req["announcement"],
            slogan=req["slogan"],
            entry_type=req["entry_type"],
            area_id=req["area_id"],
            play_style=req["play_style"],
        )
        handler.send_proto("CSClanIDRes", encode_clan_id_res(cid))
        return True

    if endpoint == "GetClanSignInRewardsByLevel":
        req = decode_get_clan_signin_rewards_req(raw_body)
        rewards = clan_service.get_signin_rewards_by_level(
            req["clan_level"], account_id=account_id
        )
        handler.send_proto("CSClanSignInRes", encode_clan_signin_res(rewards, is_newcomer=False))
        return True

    if endpoint == "ClanSignIn":
        rewards = clan_service.clan_signin(account_id=account_id)
        handler.send_proto("CSClanSignInRes", encode_clan_signin_res(rewards, is_newcomer=False))
        return True

    if endpoint == "ClaimSignInReward":
        req = decode_claim_signin_reward_req(raw_body)
        rewards = clan_service.claim_signin_reward(req["weekday"], account_id=account_id)
        handler.send_proto("CSClanSignInRes", encode_clan_signin_res(rewards, is_newcomer=False))
        return True

    if endpoint == "GetClanRaceInfo":
        req = decode_clan_id_req(raw_body)
        info = clan_service.get_clan_race_info(req["clan_id"], account_id=account_id)
        handler.send_proto("CSGetClanRaceInfoRes", encode_clan_race_info_res(info))
        return True

    if endpoint == "ClaimClanRaceAward":
        req = decode_clan_id_req(raw_body)
        info = clan_service.claim_clan_race_award(req["clan_id"], account_id=account_id)
        handler.send_proto("CSGetClanRaceInfoRes", encode_clan_race_info_res(info))
        return True

    if endpoint == "ExchangeAwardWithRP":
        req = decode_exchange_award_with_rp_req(raw_body)
        info = clan_service.exchange_award_with_rp(
            req["clan_id"], req["stage"], account_id=account_id
        )
        handler.send_proto("CSGetClanRaceInfoRes", encode_clan_race_info_res(info))
        return True

    if endpoint == "RequestJoinClan":
        req = decode_clan_id_req(raw_body)
        clan_service.join_clan(req["clan_id"], account_id=account_id)
        handler.send_proto("Empty (RequestJoinClan)", b"")
        return True

    if endpoint == "QuitClan":
        req = decode_clan_id_req(raw_body)
        clan_service.quit_clan(req["clan_id"], account_id=account_id)
        handler.send_proto("Empty (QuitClan)", b"")
        return True

    if endpoint == "DismissClan":
        req = decode_clan_id_req(raw_body)
        clan_service.dismiss_clan(req["clan_id"], account_id=account_id)
        handler.send_proto("Empty (DismissClan)", b"")
        return True

    if endpoint == "ModifyClanInfo":
        req = decode_modify_clan_info_req(raw_body)
        clan_service.modify_clan_info(
            clan_id=req["clan_id"],
            account_id=account_id,
            announcement=req["announcement"],
            slogan=req["slogan"],
            entry_type=req["entry_type"],
            area_id=req["area_id"],
            play_style=req["play_style"],
        )
        handler.send_proto("Empty (ModifyClanInfo)", b"")
        return True

    if endpoint == "ModifyClanName":
        req = decode_modify_clan_name_req(raw_body)
        clan_service.modify_clan_name(req["clan_id"], account_id, req["clan_name"])
        handler.send_proto("Empty (ModifyClanName)", b"")
        return True

    if endpoint == "ExtendClanScale":
        req = decode_clan_id_req(raw_body)
        res = clan_service.extend_clan_scale(req["clan_id"], account_id=account_id)
        handler.send_proto(
            "CSExtendClanScaleRes",
            encode_extend_clan_scale_res(
                res["clan_id"], res["capacity"], res["extended_times"]
            ),
        )
        return True

    if endpoint == "GetClanApplicantListByClanID":
        req = decode_clan_id_req(raw_body)
        apps = clan_service.list_applicants(req["clan_id"], account_id=account_id)
        handler.send_proto(
            "AccountInfoBasicBundleRes", encode_account_info_basic_bundle_res(apps)
        )
        return True

    if endpoint == "ApproveJoinClanApplication":
        req = decode_process_join_clan_req(raw_body)
        clan_service.process_application(req["clan_id"], req["applicant_id"], approve=True)
        handler.send_proto("Empty (ApproveJoinClanApplication)", b"")
        return True

    if endpoint == "DeclineJoinClanApplication":
        req = decode_process_join_clan_req(raw_body)
        clan_service.process_application(req["clan_id"], req["applicant_id"], approve=False)
        handler.send_proto("Empty (DeclineJoinClanApplication)", b"")
        return True

    if endpoint == "InviteToClan":
        _ = decode_invite_to_clan_req(raw_body)
        handler.send_proto("Empty (InviteToClan)", b"")
        return True

    if endpoint == "ApproveJoinClanInvitation":
        req = decode_process_invite_req(raw_body)
        if req["clan_id"]:
            clan_service.join_clan(req["clan_id"], account_id=account_id)
        handler.send_proto("Empty (ApproveJoinClanInvitation)", b"")
        return True

    if endpoint == "ChangeMemberTypeByCaptain":
        req = decode_change_member_type_req(raw_body)
        clan_service.change_member_type(
            account_id, req["changee_id"], req["target_type"]
        )
        handler.send_proto("Empty (ChangeMemberTypeByCaptain)", b"")
        return True

    if endpoint == "ReassignCaptain":
        req = decode_reassign_captain_req(raw_body)
        clan_service.reassign_captain(account_id, req["reassignee_id"])
        handler.send_proto("Empty (ReassignCaptain)", b"")
        return True

    if endpoint == "RemoveClanMember":
        req = decode_remove_clan_member_req(raw_body)
        clan_service.remove_member(req["clan_id"], req["removee_id"])
        handler.send_proto("Empty (RemoveClanMember)", b"")
        return True

    if endpoint == "GetClanLuckyBagsInfo":
        req = decode_clan_id_req(raw_body)
        bags = clan_service.get_lucky_bags_info(req["clan_id"], account_id=account_id)
        handler.send_proto(
            "CSGetClanLuckyBagInfoRes",
            encode_clan_lucky_bag_info_res(bags["lucky_bags"], bags["draws"]),
        )
        return True

    if endpoint == "DrawClanLuckyBag":
        req = decode_draw_lucky_bag_req(raw_body)
        tokens = clan_service.draw_lucky_bag(
            req["clan_id"], req["bag_id"], account_id=account_id
        )
        handler.send_proto(
            "CSDrawClanLuckyBagRes",
            encode_draw_clan_lucky_bag_res(account_id, req["bag_id"], tokens),
        )
        return True

    if endpoint == "GetClanWeekLeaderboardInfo":
        now = int(time.time())
        handler.send_proto(
            "CSGetClanWeekLeaderboardInfoRes",
            encode_clan_week_leaderboard_info_res(main_key=1, next_refresh_time=now + 86400),
        )
        return True

    return False


handle_clan_post = handle_clan_request
