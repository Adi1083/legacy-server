"""
Protobuf encoders and request decoders for Free Fire 1.39 Profile, Stats,
Personal Show, Ranking Info, and Account Customization endpoints.

All ProtoMember tags, wire types, and IsPacked flags are verified directly from
Free Fire 1.39 metadata and x86 libil2cpp.so custom attribute generators.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from proto.decoder import (
    decode_proto,
    get_bool,
    get_string,
    get_varint,
)
from proto.encoder import (
    encode_bool,
    encode_int32,
    encode_int64,
    encode_packed_uint32,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)

DEFAULT_SEASON_ID = 10


# ---------------------------------------------------------------------------
# Request Decoders
# ---------------------------------------------------------------------------

def decode_account_id_req(data: bytes, default_account_id: int = 0) -> int:
    """Decode proto.AccountIDReq / proto.CSMatchHistoryReq (1: ulong account_id)."""
    fields = decode_proto(data)
    return get_varint(fields, 1, default_account_id)


def decode_get_account_info_req(data: bytes) -> Tuple[int, str]:
    """Decode proto.CSGetAccountInfoReq (1: int input_type, 2: string input_value)."""
    fields = decode_proto(data)
    return get_varint(fields, 1, 0), get_string(fields, 2, "")


def decode_fuzzy_search_account_req(data: bytes) -> str:
    """Decode proto.CSFuzzySearchAccountByNameReq (1: string nickname)."""
    fields = decode_proto(data)
    return get_string(fields, 1, "")


def decode_get_player_stats_req(data: bytes, default_account_id: int = 0) -> Tuple[int, int]:
    """Decode proto.CSGetPlayerStatsReq (1: ulong account_id, 2: uint match_mode)."""
    fields = decode_proto(data)
    return get_varint(fields, 1, default_account_id), get_varint(fields, 2, 0)


def decode_account_life_season_stats_req(
    data: bytes, default_account_id: int = 0
) -> Tuple[int, int]:
    """Decode proto.CSAccountLifeSeasonStatsReq (1: ulong account_id, 2: uint championship_type)."""
    fields = decode_proto(data)
    return get_varint(fields, 1, default_account_id), get_varint(fields, 2, 0)


def decode_player_ranking_info_req(data: bytes) -> int:
    """Decode proto.CSPlayerRankingInfoReq (1: uint season_id)."""
    fields = decode_proto(data)
    return get_varint(fields, 1, DEFAULT_SEASON_ID)


def decode_modify_nickname_req(data: bytes) -> Tuple[str, bool]:
    """Decode proto.CSModifyNicknameReq (1: string nickname, 2: bool use_card)."""
    fields = decode_proto(data)
    return get_string(fields, 1, ""), get_bool(fields, 2, False)


def decode_choose_banner_req(data: bytes) -> int:
    """Decode proto.CSChooseBannerReq (1: uint banner_id)."""
    fields = decode_proto(data)
    return get_varint(fields, 1, 0)


def decode_choose_head_pic_req(data: bytes) -> int:
    """Decode proto.CSChooseHeadPicReq (1: uint head_pic)."""
    fields = decode_proto(data)
    return get_varint(fields, 1, 0)


def decode_set_show_rank_req(data: bytes) -> bool:
    """Decode proto.CSSetShowRankReq / toggle (1: bool show_rank)."""
    fields = decode_proto(data)
    return get_bool(fields, 1, True)


# ---------------------------------------------------------------------------
# Basic Account & Avatar Encoders
# ---------------------------------------------------------------------------

def encode_account_info_basic(profile: Dict[str, Any]) -> bytes:
    """
    Encode proto.AccountInfoBasic:
      1: ulong account_id            16: uint role
      2: uint account_type           17: bool has_elite_pass
      3: string nickname             18: uint badge_cnt
      4: string external_id          19: uint badge_id
      5: string region               20: uint season_id
      6: uint level                  21: uint liked
      7: uint exp                    22: bool is_deleted
      8: uint external_type          23: bool show_rank
      9: string external_name        24: long last_login_at
     10: string external_icon        25: ulong external_uid
     11: uint banner_id              26: long return_at
     12: uint head_pic               27: string championship_team_name
     13: string clan_name            28: uint championship_team_member_num
     14: uint rank                   29: ulong championship_team_id
     15: uint ranking_points
    """
    account_id = int(profile.get("account_id", 10001))
    nickname = str(profile.get("nickname", f"Player_{account_id}"))
    now = int(time.time())
    last_login_at = int(profile.get("last_login_at", now) or now)
    badge_id = int(profile.get("badge_id", profile.get("ep_badge", 1)))
    season_id = int(profile.get("season_id", DEFAULT_SEASON_ID))
    external_id = str(profile.get("external_id", str(account_id)))
    external_name = str(profile.get("external_name", nickname))
    external_icon = str(profile.get("external_icon", ""))
    clan_name = str(profile.get("clan_name", ""))
    external_uid = int(profile.get("external_uid", account_id))
    return_at = int(profile.get("return_at", 0))
    champ_team_name = str(profile.get("championship_team_name", ""))
    champ_team_members = int(profile.get("championship_team_member_num", 0))
    champ_team_id = int(profile.get("championship_team_id", 0))

    parts = [
        encode_uint64(1, account_id),
        encode_uint32(2, int(profile.get("account_type", 1))),
        encode_string(3, nickname),
        encode_string(4, external_id),
        encode_string(5, str(profile.get("region", "DEFAULT"))),
        encode_uint32(6, int(profile.get("level", 60))),
        encode_uint32(7, int(profile.get("exp", 99999))),
        encode_uint32(8, int(profile.get("external_type", 1))),
        encode_string(9, external_name),
        encode_string(10, external_icon) if external_icon else b"",
        encode_uint32(11, int(profile.get("banner_id", 901000001))),
        encode_uint32(12, int(profile.get("head_pic", 902000001))),
        encode_string(13, clan_name) if clan_name else b"",
        encode_uint32(14, int(profile.get("rank", 315))),
        encode_uint32(15, int(profile.get("ranking_points", 3250))),
        encode_uint32(16, int(profile.get("role", 0))),
        encode_bool(17, bool(profile.get("has_elite_pass", True))),
        encode_uint32(18, int(profile.get("badge_cnt", 100))),
        encode_uint32(19, badge_id),
        encode_uint32(20, season_id),
        encode_uint32(21, int(profile.get("liked", 9999))),
        encode_bool(22, bool(profile.get("is_deleted", False))),
        encode_bool(23, bool(profile.get("show_rank", True))),
        encode_int64(24, last_login_at),
        encode_uint64(25, external_uid),
        encode_int64(26, return_at) if return_at else b"",
        encode_string(27, champ_team_name) if champ_team_name else b"",
        encode_uint32(28, champ_team_members) if champ_team_members else b"",
        encode_uint64(29, champ_team_id) if champ_team_id else b"",
    ]
    return b"".join(parts)


def encode_account_info_basic_bundle_res(profiles: Sequence[Dict[str, Any]]) -> bytes:
    """Encode proto.AccountInfoBasicBundleRes (1: List<AccountInfoBasic> infos)."""
    return b"".join(encode_submessage(1, encode_account_info_basic(p)) for p in profiles)


def encode_avatar_skill_slot(slot_id: int, skill_id: int) -> bytes:
    """Encode proto.AvatarSkillSlot (1: uint slot_id, 2: uint skill_id)."""
    return encode_uint32(1, int(slot_id)) + encode_uint32(2, int(skill_id))


def encode_avatar_profile(
    profile: Dict[str, Any],
    unlocked_level: int = 8,
    is_selected: bool = True,
) -> bytes:
    """
    Encode proto.AvatarProfile:
      1: uint avatar_id
      2: uint unlocked_level
      3: uint skin_color
      4: uint[] clothes [PACKED]
      5: List<AvatarSkillSlot> equiped_skills
      6: bool is_selected
      7: uint pve_primary_weapon
    """
    clothes = [int(c) for c in (profile.get("clothes") or []) if int(c) > 0]
    raw_skills = profile.get("equiped_skills") or []
    skill_bytes = bytearray()
    for idx, entry in enumerate(raw_skills, start=1):
        if isinstance(entry, dict):
            slot_id = int(entry.get("slot_id", idx))
            skill_id = int(entry.get("skill_id", 0))
        elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
            slot_id = int(entry[0])
            skill_id = int(entry[1])
        else:
            slot_id = idx
            skill_id = int(entry)
        if skill_id > 0:
            skill_bytes += encode_submessage(5, encode_avatar_skill_slot(slot_id, skill_id))

    pve_weapon = int(profile.get("pve_primary_weapon", 0))
    return b"".join([
        encode_uint32(1, int(profile.get("avatar_id", 102000004))),
        encode_uint32(2, int(profile.get("unlocked_level", unlocked_level))),
        encode_uint32(3, int(profile.get("skin_color", 0))),
        encode_packed_uint32(4, clothes),
        bytes(skill_bytes),
        encode_bool(6, bool(profile.get("is_selected", is_selected))),
        encode_uint32(7, pve_weapon) if pve_weapon else b"",
    ])


# ---------------------------------------------------------------------------
# Personal Show Encoders (Clan, Pet, EP History, News)
# ---------------------------------------------------------------------------

def encode_account_news_content(content: Dict[str, Any]) -> bytes:
    """
    Encode proto.AccountNewsContent:
      1: uint[] item_ids [PACKED]  6: uint group_mode
      2: uint rank                 7: uint treasurebox_id
      3: uint match_mode           8: uint commodity_id
      4: uint map_id               9: uint store_id
      5: uint game_mode
    """
    item_ids = [int(i) for i in (content.get("item_ids") or []) if int(i) > 0]
    parts = [encode_packed_uint32(1, item_ids)]
    for tag, key in (
        (2, "rank"),
        (3, "match_mode"),
        (4, "map_id"),
        (5, "game_mode"),
        (6, "group_mode"),
        (7, "treasurebox_id"),
        (8, "commodity_id"),
        (9, "store_id"),
    ):
        val = int(content.get(key, 0))
        if val:
            parts.append(encode_uint32(tag, val))
    return b"".join(parts)


def encode_account_news(news: Dict[str, Any]) -> bytes:
    """Encode proto.AccountNews (1: int type, 2: AccountNewsContent content, 3: long update_time)."""
    news_type = int(news.get("type", 1))
    content = news.get("content") or {}
    update_time = int(news.get("update_time", int(time.time())))
    return b"".join([
        encode_int32(1, news_type),
        encode_submessage(2, encode_account_news_content(content)),
        encode_int64(3, update_time),
    ])


def encode_basic_ep_info(ep: Dict[str, Any]) -> bytes:
    """Encode proto.BasicEPInfo (1: ep_event_id, 2: owned_pass, 3: ep_badge, 4: badge_cnt)."""
    return b"".join([
        encode_uint32(1, int(ep.get("ep_event_id", 1))),
        encode_bool(2, bool(ep.get("owned_pass", True))),
        encode_uint32(3, int(ep.get("ep_badge", 1))),
        encode_uint32(4, int(ep.get("badge_cnt", 100))),
    ])


def encode_clan_info_basic(clan: Dict[str, Any]) -> bytes:
    """
    Encode proto.ClanInfoBasic:
      1: ulong clan_id      5: uint capacity
      2: string clan_name   6: uint member_num
      3: ulong captain_id   7: uint honor_point
      4: uint clan_level
    """
    return b"".join([
        encode_uint64(1, int(clan.get("clan_id", 0))),
        encode_string(2, str(clan.get("clan_name", ""))),
        encode_uint64(3, int(clan.get("captain_id", 0))),
        encode_uint32(4, int(clan.get("clan_level", 4))),
        encode_uint32(5, int(clan.get("capacity", 35))),
        encode_uint32(6, int(clan.get("member_num", 12))),
        encode_uint32(7, int(clan.get("honor_point", 50000))),
    ])


def encode_pet_skill_info(pet_id: int, skill_id: int, skill_level: int = 3) -> bytes:
    """Encode proto.PetSkillInfo (1: uint pet_id, 2: uint skill_id, 3: uint skill_level)."""
    return b"".join([
        encode_uint32(1, int(pet_id)),
        encode_uint32(2, int(skill_id)),
        encode_uint32(3, int(skill_level)),
    ])


def encode_pet_info(pet: Dict[str, Any]) -> bytes:
    """
    Encode proto.PetInfo:
      1: uint id                     5: bool is_selected
      2: string name                 6: uint skin_id
      3: uint level                  7: uint[] actions [PACKED]
      4: uint exp                    8: List<PetSkillInfo> skills
    """
    pet_id = int(pet.get("id", pet.get("pet_id", 1300000001)))
    actions = [int(a) for a in (pet.get("actions") or []) if int(a) > 0]
    skills = pet.get("skills") or []
    skill_bytes = bytearray()
    for sk in skills:
        if isinstance(sk, dict):
            s_id = int(sk.get("skill_id", 0))
            s_lv = int(sk.get("skill_level", 3))
            s_pet = int(sk.get("pet_id", pet_id))
        else:
            s_id = int(sk)
            s_lv = 3
            s_pet = pet_id
        if s_id > 0:
            skill_bytes += encode_submessage(8, encode_pet_skill_info(s_pet, s_id, s_lv))

    return b"".join([
        encode_uint32(1, pet_id),
        encode_string(2, str(pet.get("name", "Kitty"))),
        encode_uint32(3, int(pet.get("level", 7))),
        encode_uint32(4, int(pet.get("exp", 0))),
        encode_bool(5, bool(pet.get("is_selected", True))),
        encode_uint32(6, int(pet.get("skin_id", 0))),
        encode_packed_uint32(7, actions),
        bytes(skill_bytes),
    ])


def encode_account_personal_show_info(
    profile: Dict[str, Any],
    *,
    ranking_leaderboard_pos: int = 1,
    news: Optional[Sequence[Dict[str, Any]]] = None,
    history_ep_info: Optional[Sequence[Dict[str, Any]]] = None,
    clan_basic_info: Optional[Dict[str, Any]] = None,
    captain_basic_info: Optional[Dict[str, Any]] = None,
    pet_info: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Encode proto.AccountPersonalShowInfo:
      1: AccountInfoBasic basic_info
      2: AvatarProfile profile_info
      3: int ranking_leaderboard_pos
      4: List<AccountNews> news
      5: List<BasicEPInfo> history_ep_info
      6: ClanInfoBasic clan_basic_info
      7: AccountInfoBasic captain_basic_info
      8: PetInfo pet_info
    """
    parts = [
        encode_submessage(1, encode_account_info_basic(profile)),
        encode_submessage(2, encode_avatar_profile(profile)),
        encode_int32(3, int(ranking_leaderboard_pos)),
    ]
    for item in (news or ()):
        parts.append(encode_submessage(4, encode_account_news(item)))
    for ep in (history_ep_info or ()):
        parts.append(encode_submessage(5, encode_basic_ep_info(ep)))
    if clan_basic_info and int(clan_basic_info.get("clan_id", 0)) > 0:
        parts.append(encode_submessage(6, encode_clan_info_basic(clan_basic_info)))
    if captain_basic_info:
        parts.append(encode_submessage(7, encode_account_info_basic(captain_basic_info)))
    if pet_info and int(pet_info.get("id", pet_info.get("pet_id", 0))) > 0:
        parts.append(encode_submessage(8, encode_pet_info(pet_info)))
    return b"".join(parts)


# ---------------------------------------------------------------------------
# Player Stats Encoders (CSGetPlayerStatsRes & DetailStats)
# ---------------------------------------------------------------------------

DETAIL_STATS_KEYS = (
    "deaths",
    "top10_times",
    "top_n_times",
    "distance_travelled",
    "survival_time",
    "revives",
    "highest_kills",
    "damage",
    "road_kills",
    "headshots",
    "headshot_kills",
    "knock_down",
    "pick_ups",
)


def encode_detail_stats_json(detail: Optional[Dict[str, Any]]) -> str:
    """Serialize DetailStats JSON parsed by LitJson.JsonMapper.ToObject<DetailStats>."""
    src = detail or {}
    payload = {k: max(0, int(src.get(k, 0))) for k in DETAIL_STATS_KEYS}
    return json.dumps(payload, separators=(",", ":"))


def encode_account_info_with_stats(account_id: int, stats: Optional[Dict[str, Any]]) -> bytes:
    """
    Encode proto.AccountInfoWithStats:
      1: ulong account_id
      2: uint games_played
      3: uint wins
      4: uint kills
      5: string detailed_stats
    """
    st = stats or {}
    detail_raw = st.get("detailed_stats")
    if isinstance(detail_raw, str) and detail_raw:
        detail_json = detail_raw
    else:
        detail_json = encode_detail_stats_json(
            detail_raw if isinstance(detail_raw, dict) else st.get("detail")
        )
    return b"".join([
        encode_uint64(1, int(st.get("account_id", account_id))),
        encode_uint32(2, int(st.get("games_played", 0))),
        encode_uint32(3, int(st.get("wins", 0))),
        encode_uint32(4, int(st.get("kills", 0))),
        encode_string(5, detail_json),
    ])


def encode_get_player_stats_res(
    account_id: int,
    solo_stats: Optional[Dict[str, Any]] = None,
    duo_stats: Optional[Dict[str, Any]] = None,
    quad_stats: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Encode proto.CSGetPlayerStatsRes:
      1: AccountInfoWithStats solo_stats
      2: AccountInfoWithStats duo_stats
      3: AccountInfoWithStats quad_stats
    """
    return b"".join([
        encode_submessage(1, encode_account_info_with_stats(account_id, solo_stats)),
        encode_submessage(2, encode_account_info_with_stats(account_id, duo_stats)),
        encode_submessage(3, encode_account_info_with_stats(account_id, quad_stats)),
    ])


# ---------------------------------------------------------------------------
# Match History Encoders (CSGetMatchStatsListRes, MatchAccountStats, MatchStats)
# ---------------------------------------------------------------------------

def encode_teammate_stats(tm: Dict[str, Any]) -> bytes:
    """
    Encode proto.TeammateStats (tags 1..19):
      1: ulong account_id       11: uint badge_id
      2: string nickname        12: uint badge_cnt
      3: uint kills             13: bool is_friend
      4: uint avatar_id         14: bool show_rank
      5: uint banner_id         15: string lock_region
      6: uint head_pic          16: uint pve_damage
      7: string clan_name       17: uint pve_primary_weapon_skin
      8: uint season_rank       18: uint role
      9: uint level             19: uint damage
     10: bool has_elite_pass
    """
    clan_name = str(tm.get("clan_name", ""))
    lock_region = str(tm.get("lock_region", ""))
    return b"".join([
        encode_uint64(1, int(tm.get("account_id", 0))),
        encode_string(2, str(tm.get("nickname", "Player"))),
        encode_uint32(3, int(tm.get("kills", 0))),
        encode_uint32(4, int(tm.get("avatar_id", 102000004))),
        encode_uint32(5, int(tm.get("banner_id", 901000001))),
        encode_uint32(6, int(tm.get("head_pic", 902000001))),
        encode_string(7, clan_name) if clan_name else b"",
        encode_uint32(8, int(tm.get("season_rank", 310))),
        encode_uint32(9, int(tm.get("level", 50))),
        encode_bool(10, bool(tm.get("has_elite_pass", True))),
        encode_uint32(11, int(tm.get("badge_id", 1))),
        encode_uint32(12, int(tm.get("badge_cnt", 50))),
        encode_bool(13, bool(tm.get("is_friend", True))),
        encode_bool(14, bool(tm.get("show_rank", True))),
        encode_string(15, lock_region) if lock_region else b"",
        encode_uint32(16, int(tm.get("pve_damage", 0))) if tm.get("pve_damage") else b"",
        encode_uint32(17, int(tm.get("pve_primary_weapon_skin", 0)))
        if tm.get("pve_primary_weapon_skin")
        else b"",
        encode_uint32(18, int(tm.get("role", 0))),
        encode_uint32(19, int(tm.get("damage", 0))),
    ])


def encode_match_income(inc: Dict[str, Any]) -> bytes:
    """
    Encode proto.MatchIncome (selected core reward tags verified in MatchIncome):
      1: uint exp                     15: int ranking_points_delta
      2: uint coins                   16: int ranking_points_before
      3: uint rank_points             17: int ranking_points_after
      4: uint kill_points             24: uint rank_before
      5: uint damage_points           25: uint rank_after
      6: uint level_before            27: bool is_rank
      7: uint level_after
    """
    return b"".join([
        encode_uint32(1, int(inc.get("exp", 0))),
        encode_uint32(2, int(inc.get("coins", 0))),
        encode_uint32(3, int(inc.get("rank_points", 0))),
        encode_uint32(4, int(inc.get("kill_points", 0))),
        encode_uint32(5, int(inc.get("damage_points", 0))),
        encode_uint32(6, int(inc.get("level_before", 60))),
        encode_uint32(7, int(inc.get("level_after", 60))),
        encode_int32(15, int(inc.get("ranking_points_delta", 0))),
        encode_int32(16, int(inc.get("ranking_points_before", 3200))),
        encode_int32(17, int(inc.get("ranking_points_after", 3250))),
        encode_uint32(24, int(inc.get("rank_before", 315))),
        encode_uint32(25, int(inc.get("rank_after", 315))),
        encode_bool(27, bool(inc.get("is_rank", True))),
    ])


def encode_match_stats(st: Dict[str, Any]) -> bytes:
    """
    Encode proto.MatchStats (verified tags 1..65; achievements=21 & clothes_id=42 packed).
    """
    achievements = [int(a) for a in (st.get("achievements") or []) if int(a) > 0]
    clothes_id = [int(c) for c in (st.get("clothes_id") or []) if int(c) > 0]
    clan_name = str(st.get("clan_name", ""))
    pet_name = str(st.get("pet_name", ""))
    pet_id = int(st.get("pet_id", 0))
    pet_skin_id = int(st.get("pet_skin_id", 0))

    parts = [
        encode_uint64(1, int(st.get("account_id", 10001))),
        encode_uint64(2, int(st.get("group_id", 1))),
        encode_uint32(3, int(st.get("survival_time", 900))),
        encode_uint32(4, int(st.get("rank", 1))),
        encode_uint32(5, int(st.get("kills", 0))),
        encode_uint32(6, int(st.get("damage", 0))),
        encode_uint32(7, int(st.get("moving_distance", 0))),
        encode_uint32(8, int(st.get("revival_count", 0))),
        encode_uint32(9, int(st.get("vehicle_kills", 0))),
        encode_uint32(10, int(st.get("headshot_count", 0))),
        encode_uint32(11, int(st.get("headshot_kills", 0))),
        encode_uint32(12, int(st.get("knockdown_count", 0))),
        encode_uint32(13, int(st.get("pickup_count", 0))),
        encode_uint32(14, int(st.get("assists", 0))),
        encode_bool(15, bool(st.get("is_survive", int(st.get("rank", 1)) == 1))),
        encode_uint32(16, int(st.get("out_index", 0))),
        encode_int32(17, int(st.get("ranking_points", 0))),
        encode_uint32(20, int(st.get("down_count", 0))),
        encode_packed_uint32(21, achievements),
        encode_uint32(22, int(st.get("kill_bots", 0))),
        encode_bool(23, bool(st.get("enable_achievements", True))),
        encode_uint32(24, int(st.get("avatar_id", 102000004))),
    ]
    for tm in (st.get("teammates") or ()):
        parts.append(encode_submessage(25, encode_teammate_stats(tm)))
    parts.extend([
        encode_uint32(29, int(st.get("group_mode", 1))),
        encode_uint32(30, int(st.get("match_mode", 1))),
        encode_uint32(31, int(st.get("player_count", 50))),
        encode_uint32(32, int(st.get("banner_id", 901000001))),
        encode_uint32(33, int(st.get("head_pic", 902000001))),
        encode_string(34, clan_name) if clan_name else b"",
        encode_uint32(35, int(st.get("level", 60))),
        encode_uint32(36, int(st.get("season_rank", 315))),
        encode_uint32(37, int(st.get("game_mode", 1))),
        encode_uint32(38, int(st.get("map_id", 1))),
        encode_bool(39, bool(st.get("has_elite_pass", True))),
        encode_uint32(40, int(st.get("badge_id", 1))),
        encode_uint32(41, int(st.get("badge_cnt", 100))),
        encode_packed_uint32(42, clothes_id),
        encode_uint32(45, int(st.get("liked", 0))),
        encode_bool(48, bool(st.get("show_rank", True))),
        encode_uint32(52, pet_id) if pet_id else b"",
        encode_string(53, pet_name) if pet_name else b"",
        encode_uint32(58, pet_skin_id) if pet_skin_id else b"",
        encode_uint32(64, int(st.get("role", 0))),
    ])
    return b"".join(parts)


def encode_match_account_stats(entry: Dict[str, Any]) -> bytes:
    """
    Encode proto.MatchAccountStats:
      1: ulong match_id
      2: ulong account_id
      3: uint create_time
      4: uint end_time
      7: MatchIncome income
      8: MatchStats stats
    """
    now = int(time.time())
    end_time = int(entry.get("end_time", now))
    create_time = int(entry.get("create_time", max(0, end_time - 900)))
    income = entry.get("income")
    stats = entry.get("stats") or {}

    parts = [
        encode_uint64(1, int(entry.get("match_id", 1))),
        encode_uint64(2, int(entry.get("account_id", stats.get("account_id", 10001)))),
        encode_uint32(3, create_time),
        encode_uint32(4, end_time),
    ]
    if income:
        parts.append(encode_submessage(7, encode_match_income(income)))
    parts.append(encode_submessage(8, encode_match_stats(stats)))
    return b"".join(parts)


def encode_get_match_stats_list_res(matches: Sequence[Dict[str, Any]]) -> bytes:
    """Encode proto.CSGetMatchStatsListRes (1: List<MatchAccountStats> match_stats_list)."""
    return b"".join(encode_submessage(1, encode_match_account_stats(m)) for m in matches)


# ---------------------------------------------------------------------------
# Championship Life Season Stats Encoders
# ---------------------------------------------------------------------------

def encode_account_season_stats(entry: Dict[str, Any]) -> bytes:
    """
    Encode proto.AccountSeasonStats:
      1: ulong account_id
      2: uint championship_type
      3: uint championship_id
      4: uint score
      5: uint pos
    """
    return b"".join([
        encode_uint64(1, int(entry.get("account_id", 10001))),
        encode_uint32(2, int(entry.get("championship_type", 0))),
        encode_uint32(3, int(entry.get("championship_id", 1))),
        encode_uint32(4, int(entry.get("score", 0))),
        encode_uint32(5, int(entry.get("pos", 1))),
    ])


def encode_account_life_season_stats_res(
    account_id: int,
    championship_type: int,
    stats_list: Sequence[Dict[str, Any]],
) -> bytes:
    """
    Encode proto.CSAccountLifeSeasonStats:
      1: ulong account_id
      2: uint championship_type
      3: List<AccountSeasonStats> stats
    """
    parts = [
        encode_uint64(1, int(account_id)),
        encode_uint32(2, int(championship_type)),
    ]
    for st in stats_list:
        parts.append(encode_submessage(3, encode_account_season_stats(st)))
    return b"".join(parts)


# ---------------------------------------------------------------------------
# Ranking Info & Customization Encoders
# ---------------------------------------------------------------------------

def encode_ranking_info(
    season_id: int,
    rank: int,
    max_rank: int,
    ranking_points: int,
) -> bytes:
    """Encode proto.RankingInfo (1: season_id, 2: rank, 3: max_rank, 4: ranking_points)."""
    return b"".join([
        encode_uint32(1, int(season_id)),
        encode_uint32(2, int(rank)),
        encode_uint32(3, int(max_rank)),
        encode_uint32(4, int(ranking_points)),
    ])


def encode_player_ranking_info_res(
    account_id: int,
    season_id: int,
    rank: int,
    max_rank: int,
    ranking_points: int,
    show_rank: bool = True,
    last_season_info: Optional[Dict[str, Any]] = None,
    match_token_num: int = 500,
) -> bytes:
    """
    Encode proto.CSPlayerRankingInfoRes:
      1: ulong account_id          5: uint ranking_points
      2: uint season_id            6: bool show_rank
      3: uint rank                 7: RankingInfo last_season_info
      4: uint max_rank             8: uint match_token_num
    """
    last = last_season_info or {
        "season_id": max(1, int(season_id) - 1),
        "rank": int(rank),
        "max_rank": int(max_rank),
        "ranking_points": int(ranking_points),
    }
    return b"".join([
        encode_uint64(1, int(account_id)),
        encode_uint32(2, int(season_id)),
        encode_uint32(3, int(rank)),
        encode_uint32(4, int(max_rank)),
        encode_uint32(5, int(ranking_points)),
        encode_bool(6, bool(show_rank)),
        encode_submessage(
            7,
            encode_ranking_info(
                last.get("season_id", max(1, int(season_id) - 1)),
                last.get("rank", rank),
                last.get("max_rank", max_rank),
                last.get("ranking_points", ranking_points),
            ),
        ),
        encode_uint32(8, int(match_token_num)),
    ])


def encode_modify_nickname_res(nickname: str) -> bytes:
    """
    Encode proto.CSModifyNicknameRes / proto.CSModifyNicknameReq (1: string nickname).
    Client UIModelUser.<UserRename>m__1 casts response to CSModifyNicknameReq and reads tag 1.
    """
    return encode_string(1, str(nickname))


def encode_empty() -> bytes:
    """Encode proto.Empty."""
    return b""
