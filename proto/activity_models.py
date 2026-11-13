"""
Protobuf models for Free Fire 1.39 Events, Activities, Attendance, Broadcasts,
Announcements, Login Splash, Marquee, Adverts, Bingo, Activeness, and LoginDesc.

All ProtoMember tags, wire types, packed flags, and enum constants are extracted
directly from Free Fire 1.39 global-metadata.dat + x86 libil2cpp.so.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

from .decoder import (
    decode_proto,
    get_bool,
    get_packed_varints,
    get_string,
    get_submessage,
    get_varint,
)
from .encoder import (
    encode_bool,
    encode_int32,
    encode_int64,
    encode_packed_uint32,
    encode_string,
    encode_submessage,
    encode_uint32,
)


# ---------------------------------------------------------------------------
# Enums (exact values from global-metadata.dat)
# ---------------------------------------------------------------------------

class AwardType:
    NONE = 0
    ITEM = 1
    COINS = 2
    GEMS = 3
    SKILL = 4
    EXP = 5
    ACTIVENESS = 6


class ActivityState:
    """proto.ActivityInfo+State [TypeDef 4966]"""
    RECEIVED = 0
    FINISHED = 1
    AWARDED = 2


class ActivityType:
    """proto.ActivityType [TypeDef 4967]"""
    NORMAL = 0
    FIRSTRECHARGE = 1
    EXCHANGE = 2
    SHARE = 3
    BIND = 4
    FESTIVAL = 5
    RETURNER = 6
    RETURN_INVITER = 7
    WATCH_AD = 8
    OPTIONAL_HOTFIX = 9
    CDN_SHOW = 10
    ANNOUNCE_SHOW = 11
    PRELOGIN = 12
    LIMITED_TIME_RECHARGE = 13
    MONTHLY_RECHARGE = 14
    MONTHLY_REBATE = 15
    WEEKLY_REBATE = 16
    GOOGLE_ENGAGEMENT_REWARDS = 17
    WATCH_AD_AFTER_MATCH = 18
    SECOND_RECHARGE = 19
    OVERVIEW = 20
    NAVIGATION = 21
    ACTIVENESS = 22


class EventTabType:
    """COW.EventTabType [TypeDef 7483]"""
    NONE = 0
    DAILY = 1
    FESTIVAL1 = 2
    FESTIVAL2 = 3
    GWBINGO = 4
    GWTOKEN = 5
    MEGA_EVENT = 6
    GWCommon_EVENT = 7
    GWAD = 8
    ACTIVENESS = 9
    ALL = 999


class EEventTag:
    """COW.EEventTag [TypeDef 7484]"""
    NONE = 0
    NEW = 1
    HOT = 2
    LIMIT = 3
    PREVIEW = 1000


class EAttendanceSignState:
    """EAttendanceSignState [TypeDef 7508]"""
    UNSIGNED = 0
    SIGNED = 1
    NEED_SIGN = 2


class NavigationType:
    """NavigationType [TypeDef 5368]"""
    NONE = 0
    PROFILE = 1
    GROUP = 2
    MALL = 3
    VAULT = 4
    CLAN = 5
    RECHARGE = 6
    ACTIVITY = 7
    FRIENDS = 8
    LOADOUTS = 9
    SETTING = 10
    TUTORIAL = 11
    MONTHCARD = 12
    AVATARPROFILE = 13
    GACHA = 15
    INGAME_DROP = 23
    ELITEPASS_MAIN = 114
    ELITEPASS_CHALLENGE = 214


class AdType:
    """COW.AdType [TypeDef 7547]"""
    NONE = 0
    MALL = 1
    TOKEN = 2
    GACHA = 3
    EP = 4
    MALLBG = 5
    GIFTBG = 6
    REBATE_CARD = 7
    PAYMENT_WINDOW_UNPAID = 8
    PAYMENT_WINDOW_PAID = 9
    LOBBY_ACTIVITY = 10
    LOBBY_ADS = 11
    MALL_WEAPON_BG = 12
    LOADING = 13
    GACHA_ACTIVITY_BG1 = 14
    GACHA_ACTIVITY_BG2 = 15
    FLIPCARD_PRIZEHINT = 16
    ACTIVITY_MAX = 17
    PRELOGIN = 18
    ACTIVITY_INTRODUCTION = 19
    GACHA_SPLASHBANNER = 20
    FULLSCREENCG = 21
    FORGEBG = 22
    PAYMENT_BONUS = 23
    PAYMENT_SHOP = 24
    INSTALLMENT_TUTORIAL = 25
    EP_MAINBG = 26
    ACTIVITY_MAINBG = 27
    AVATAR_SPLASHBANNER = 29
    SECOND_CHARGE = 30
    ACTIVITY_OVERVIEW = 31
    ACTIVITY_OVERVIEW_NAVIGATION = 32


class SwitchFunc:
    """SwitchFunc [TypeDef 5005]"""
    NONE = 0
    LOTTERY_PR = 1
    TREASURE_BOX_PR = 2
    SPECIAL_STORE_ICON = 3
    GIFT_STORE_IOS = 4
    EXCHANGE_STORE_IOS = 5
    LEVEL_LIMITED_FOR_SPLASH_BANNER = 6
    AD_REWARDED_VIDEO_ENTRANCE = 7
    PRELOAD_REWARDED_VIDEO_UNDER_WIFI = 8
    UNFINISHED_TOPUP_ICON_SHOW = 9
    FINISHED_TOPUP_ICON_SHOW = 10
    TP_TICK = 11
    PVE_WEAPON_INFO_SHOW = 12
    CATAPULT_USING = 13
    LIVE_SHOW = 14
    TP_INFO = 15
    SP_UNITY = 16
    MYSTERY_BONUS = 18
    AFTER_MATCH_REWARD_AD = 20
    CHAMPIONSHIP_ENTRANCE = 21
    NATIONAL_FLAG = 22
    ACTIVENESS_LEVEL = 23
    SECOND_RECHARGE_ICON = 24


class SplashType:
    """SplashBannerDesc.type"""
    NORMAL = 0
    VIDEO = 1
    LIVE = 2


# ---------------------------------------------------------------------------
# Shared Award / Item Encoders
# ---------------------------------------------------------------------------

def encode_award_desc(
    award_type: int = AwardType.ITEM,
    award_id: int = 0,
    award_num: int = 1,
    award_max_num: int = 0,
    award_expire_time: int = 0,
) -> bytes:
    """proto.AwardDesc [5570]"""
    buf = bytearray()
    buf += encode_uint32(1, award_type)
    buf += encode_uint32(2, award_id)
    buf += encode_uint32(3, award_num)
    if award_max_num:
        buf += encode_uint32(4, award_max_num)
    if award_expire_time:
        buf += encode_uint32(5, award_expire_time)
    return bytes(buf)


def encode_item(
    item_id: int,
    cnt: int = 1,
    expire_time: int = 0,
    left_use_times: int = -1,
    history_owned_cnt: int = 1,
    left_expire_time: int = 0,
    item_status: int = 1,  # PERMANENT
    item_type: int = 0,
    item_sub_type: int = 0,
) -> bytes:
    """proto.Item [5020]"""
    buf = bytearray()
    buf += encode_uint32(1, item_id)
    buf += encode_uint32(2, cnt)
    buf += encode_uint32(3, expire_time)
    buf += encode_int32(4, left_use_times)
    buf += encode_uint32(5, history_owned_cnt)
    buf += encode_uint32(6, left_expire_time)
    buf += encode_uint32(7, item_status)
    if item_type:
        buf += encode_uint32(8, item_type)
    if item_sub_type:
        buf += encode_uint32(9, item_sub_type)
    return bytes(buf)


def encode_award_data(
    items: Optional[Iterable[Dict[str, Any]]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
) -> bytes:
    """proto.AwardData [5024]"""
    buf = bytearray()
    for it in items or ():
        if isinstance(it, bytes):
            buf += encode_submessage(1, it)
        else:
            buf += encode_submessage(
                1,
                encode_item(
                    item_id=int(it.get("id", it.get("item_id", 0))),
                    cnt=int(it.get("cnt", it.get("count", 1))),
                    expire_time=int(it.get("expire_time", 0)),
                    item_status=int(it.get("item_status", 1)),
                    item_type=int(it.get("item_type", 0)),
                    item_sub_type=int(it.get("item_sub_type", 0)),
                ),
            )
    if coins:
        buf += encode_uint32(2, coins)
    if gems:
        buf += encode_uint32(3, gems)
    if exps:
        buf += encode_uint32(4, exps)
    if activeness:
        buf += encode_uint32(5, activeness)
    return bytes(buf)


def encode_exchanged_award(
    origin_award_type: int,
    origin_award_id: int,
    origin_award_num: int,
    dest_award_type: int,
    dest_award_id: int,
    dest_award_num: int,
) -> bytes:
    """proto.ExchangedAward [5022]"""
    buf = bytearray()
    buf += encode_uint32(1, origin_award_type)
    buf += encode_uint32(2, origin_award_id)
    buf += encode_uint32(3, origin_award_num)
    buf += encode_uint32(4, dest_award_type)
    buf += encode_uint32(5, dest_award_id)
    buf += encode_uint32(6, dest_award_num)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Attendance Models
# ---------------------------------------------------------------------------

def encode_attendance_item(
    item_id: int,
    signed: int = EAttendanceSignState.UNSIGNED,
    awards: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.AttendanceItem [5268]"""
    buf = bytearray()
    buf += encode_uint32(1, item_id)
    buf += encode_uint32(2, signed)
    for aw in awards or ():
        buf += encode_submessage(
            3,
            encode_award_desc(
                award_type=int(aw.get("award_type", AwardType.ITEM)),
                award_id=int(aw.get("award_id", 0)),
                award_num=int(aw.get("award_num", 1)),
                award_max_num=int(aw.get("award_max_num", 0)),
                award_expire_time=int(aw.get("award_expire_time", 0)),
            ),
        )
    return bytes(buf)


def encode_attendance_list_res(
    items: Iterable[Dict[str, Any]],
    end_time: int,
    url: str = "",
    loc_key: str = "TXT_SIGNIN_TITLE",
    is_signed_today: bool = False,
) -> bytes:
    """proto.CSGetAttendanceListRes [5253]"""
    buf = bytearray()
    for it in items:
        buf += encode_submessage(
            1,
            encode_attendance_item(
                item_id=int(it["id"]),
                signed=int(it.get("signed", EAttendanceSignState.UNSIGNED)),
                awards=it.get("awards", ()),
            ),
        )
    buf += encode_int64(2, end_time)
    if url:
        buf += encode_string(3, url)
    if loc_key:
        buf += encode_string(4, loc_key)
    buf += encode_bool(5, is_signed_today)
    return bytes(buf)


def encode_new_player_rewards_list_res(items: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSGetNewPlayerRewardsListRes [5257] (NewPlayerRewardItem [5267])"""
    buf = bytearray()
    for it in items:
        sub = encode_attendance_item(
            item_id=int(it["id"]),
            signed=int(it.get("signed", EAttendanceSignState.UNSIGNED)),
            awards=it.get("awards", ()),
        )
        buf += encode_submessage(1, sub)
    return bytes(buf)


def encode_veteran_reward_desc(
    region: str,
    reward_id: int,
    award: Dict[str, Any],
    cdn_url_key: str = "",
) -> bytes:
    """proto.VeteranRewardDesc [5620]"""
    buf = bytearray()
    buf += encode_string(1, region)
    buf += encode_uint32(2, reward_id)
    buf += encode_submessage(
        3,
        encode_award_desc(
            award_type=int(award.get("award_type", AwardType.ITEM)),
            award_id=int(award.get("award_id", 0)),
            award_num=int(award.get("award_num", 1)),
        ),
    )
    if cdn_url_key:
        buf += encode_string(4, cdn_url_key)
    return bytes(buf)


def encode_veteran_reward_list_res(
    is_veteran: bool = False,
    rewards: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.CSGetVeteranRewardListRes [5260]"""
    buf = bytearray()
    buf += encode_bool(1, is_veteran)
    for rw in rewards or ():
        item_buf = bytearray()
        desc = rw.get("desc", {})
        item_buf += encode_submessage(
            1,
            encode_veteran_reward_desc(
                region=str(desc.get("region", "DEFAULT")),
                reward_id=int(desc.get("id", 1)),
                award=desc.get("award", {"award_type": AwardType.COINS, "award_id": 0, "award_num": 1000}),
                cdn_url_key=str(desc.get("cdn_url_key", "")),
            ),
        )
        item_buf += encode_uint32(2, int(rw.get("status", 0)))
        buf += encode_submessage(2, bytes(item_buf))
    return bytes(buf)


def encode_clan_sign_in_res(
    rewards: Optional[Iterable[Dict[str, Any]]] = None,
    is_newcomer: bool = False,
) -> bytes:
    """proto.CSClanSignInRes [5316]"""
    buf = bytearray()
    for rw in rewards or ():
        desc = rw.get("desc", {})
        desc_buf = bytearray()
        desc_buf += encode_uint32(1, int(desc.get("sign_in_group", 1)))
        desc_buf += encode_uint32(2, int(desc.get("clan_level", 1)))
        desc_buf += encode_uint32(3, int(desc.get("weekday", 1)))
        aw = desc.get("award", {"award_type": AwardType.COINS, "award_id": 0, "award_num": 500})
        desc_buf += encode_submessage(
            4,
            encode_award_desc(
                award_type=int(aw.get("award_type", AwardType.COINS)),
                award_id=int(aw.get("award_id", 0)),
                award_num=int(aw.get("award_num", 500)),
            ),
        )
        item_buf = bytearray()
        item_buf += encode_submessage(1, bytes(desc_buf))
        item_buf += encode_uint32(2, int(rw.get("status", 0)))
        buf += encode_submessage(1, bytes(item_buf))
    buf += encode_bool(2, is_newcomer)
    return bytes(buf)


def encode_get_attendance_res(
    new_player_res: bytes = b"",
    attendance_res: bytes = b"",
    veteran_res: bytes = b"",
    clan_sign_in_info: bytes = b"",
) -> bytes:
    """proto.GetAttendanceRes [5418]"""
    buf = bytearray()
    buf += encode_submessage(1, new_player_res)
    buf += encode_submessage(2, attendance_res)
    buf += encode_submessage(3, veteran_res)
    buf += encode_submessage(4, clan_sign_in_info)
    return bytes(buf)


def encode_festival_attendance_info_res(
    items: Iterable[Dict[str, Any]],
    is_signed_today: bool = False,
    festival_item_id: int = 203000001,
    act_text1: str = "Barbosa Festival Calendar",
    act_text2: str = "Sign in daily for exclusive skins & diamonds!",
    act_text3: str = "Limited Time Event",
    start_time: int = 0,
    end_time: int = 0,
    is_in_attendance_time: bool = True,
) -> bytes:
    """proto.CSGetFestivalAttendanceInfoRes [5263]"""
    now = int(time.time())
    if not start_time:
        start_time = now - 86400
    if not end_time:
        end_time = now + 30 * 86400

    buf = bytearray()
    for it in items:
        sub = bytearray()
        sub += encode_uint32(1, int(it["id"]))
        sub += encode_uint32(2, int(it.get("signed", EAttendanceSignState.UNSIGNED)))
        for aw in it.get("awards", ()):
            sub += encode_submessage(
                3,
                encode_award_desc(
                    award_type=int(aw.get("award_type", AwardType.ITEM)),
                    award_id=int(aw.get("award_id", 0)),
                    award_num=int(aw.get("award_num", 1)),
                ),
            )
        sub += encode_uint32(4, int(it.get("drop_max_num", 1)))
        buf += encode_submessage(1, bytes(sub))
    buf += encode_bool(2, is_signed_today)
    buf += encode_uint32(3, festival_item_id)
    buf += encode_string(4, act_text1)
    buf += encode_string(5, act_text2)
    buf += encode_string(6, act_text3)
    buf += encode_int64(7, start_time)
    buf += encode_int64(8, end_time)
    buf += encode_bool(9, is_in_attendance_time)
    return bytes(buf)


def encode_festival_attendance_signin_res(act_text1: str = "Signed in successfully!") -> bytes:
    """proto.CSFestivalAttendanceSigninRes [5265]"""
    return encode_string(1, act_text1)


def encode_festival_item_info_res(
    festival_item_id: int = 203000001,
    act_text1: str = "Barbosa Festival",
    act_text2: str = "Collect tokens and claim rewards!",
    act_text3: str = "Active Now",
) -> bytes:
    """proto.CSGetFestivalItemInfoRes [5264]"""
    buf = bytearray()
    buf += encode_uint32(1, festival_item_id)
    buf += encode_string(2, act_text1)
    buf += encode_string(3, act_text2)
    buf += encode_string(4, act_text3)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Announcements & Login Splash Models
# ---------------------------------------------------------------------------

def encode_announcement_desc(
    ann_id: int,
    title: str,
    desc: str,
    image_url: str = "",
    image_url_for_lobby: str = "",
    link_url: str = "",
    fb_page_id: str = "",
    language: str = "en",
    region: str = "DEFAULT",
    order: int = 1,
    start_time: int = 0,
    end_time: int = 0,
    use_embedded_browser: bool = False,
) -> bytes:
    """proto.AnnouncementDesc [5363] — 13 fields confirmed in IL2CPP / dump.cs"""
    now = int(time.time())
    if not start_time:
        start_time = now - 86400
    if not end_time:
        end_time = now + 365 * 86400

    buf = bytearray()
    buf += encode_string(1, language)
    buf += encode_uint32(2, order)
    buf += encode_string(3, title)
    buf += encode_string(4, image_url)
    buf += encode_string(5, fb_page_id)
    buf += encode_string(6, image_url_for_lobby or image_url)
    buf += encode_string(7, link_url)
    buf += encode_string(8, desc)
    buf += encode_uint32(9, start_time)
    buf += encode_uint32(10, end_time)
    buf += encode_string(11, region)
    buf += encode_uint32(12, ann_id)
    buf += encode_bool(13, use_embedded_browser)
    return bytes(buf)


def encode_announcement_res(announcements: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSAnnouncementRes [5359]"""
    buf = bytearray()
    for a in announcements:
        buf += encode_submessage(
            1,
            encode_announcement_desc(
                ann_id=int(a.get("id", 1)),
                title=str(a.get("title", "Announcement")),
                desc=str(a.get("desc", "")),
                image_url=str(a.get("image_url", "")),
                image_url_for_lobby=str(a.get("image_url_for_lobby", "")),
                link_url=str(a.get("link_url", "")),
                fb_page_id=str(a.get("fb_page_id", "")),
                language=str(a.get("language", "en")),
                region=str(a.get("region", "DEFAULT")),
                order=int(a.get("order_in_this_language", 1)),
                start_time=int(a.get("start_time", 0)),
                end_time=int(a.get("end_time", 0)),
                use_embedded_browser=bool(a.get("use_embedded_browser", False)),
            ),
        )
    return bytes(buf)


def encode_splash_banner_desc(
    banner_id: int,
    name: str,
    image_url: str,
    sort_id: int = 1,
    gos_pos: int = NavigationType.ACTIVITY,
    gos_url: str = "",
    use_embedded_browser: bool = False,
    sub_go_pos: str = "",
    video_url: str = "",
    bg_img_url: str = "",
    banner_type: int = SplashType.NORMAL,
    region: str = "DEFAULT",
    language: str = "en",
    start_time: int = 0,
    end_time: int = 0,
) -> bytes:
    """proto.SplashBannerDesc [5364]"""
    now = int(time.time())
    if not start_time:
        start_time = now - 86400
    if not end_time:
        end_time = now + 365 * 86400

    buf = bytearray()
    buf += encode_string(1, region)
    buf += encode_string(2, language)
    buf += encode_uint32(3, banner_id)
    buf += encode_string(4, name)
    buf += encode_uint32(5, sort_id)
    buf += encode_int64(6, start_time)
    buf += encode_int64(7, end_time)
    buf += encode_string(8, image_url)
    buf += encode_uint32(9, gos_pos)
    buf += encode_string(10, gos_url)
    buf += encode_bool(11, use_embedded_browser)
    buf += encode_string(12, sub_go_pos)
    buf += encode_string(13, video_url)
    buf += encode_string(14, bg_img_url or image_url)
    buf += encode_uint32(15, banner_type)
    return bytes(buf)


def encode_splash_banner_desc_list(banners: Iterable[Dict[str, Any]]) -> bytes:
    """proto.SplashBannerDescList [5454]"""
    buf = bytearray()
    for b in banners:
        buf += encode_submessage(
            1,
            encode_splash_banner_desc(
                banner_id=int(b.get("id", 1)),
                name=str(b.get("name", "Banner")),
                image_url=str(b.get("image_url", "")),
                sort_id=int(b.get("sort_id", 1)),
                gos_pos=int(b.get("gos_pos", NavigationType.ACTIVITY)),
                gos_url=str(b.get("gos_url", "")),
                use_embedded_browser=bool(b.get("use_embedded_browser", False)),
                sub_go_pos=str(b.get("sub_go_pos", "")),
                video_url=str(b.get("video_url", "")),
                bg_img_url=str(b.get("bg_img_url", "")),
                banner_type=int(b.get("type", SplashType.NORMAL)),
                region=str(b.get("region", "DEFAULT")),
                language=str(b.get("language", "en")),
                start_time=int(b.get("start_time", 0)),
                end_time=int(b.get("end_time", 0)),
            ),
        )
    return bytes(buf)


def encode_activity_info(act_id: int, data: int = 0, state: int = ActivityState.RECEIVED) -> bytes:
    """proto.ActivityInfo [5283]"""
    buf = bytearray()
    buf += encode_uint32(1, act_id)
    buf += encode_uint32(2, data)
    buf += encode_uint32(3, state)
    return bytes(buf)


def encode_activity_info_res(activities: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSGetActivityInfoRes [5272]"""
    buf = bytearray()
    for a in activities:
        buf += encode_submessage(
            1,
            encode_activity_info(
                act_id=int(a.get("id", a.get("activity_id", 0))),
                data=int(a.get("data", 0)),
                state=int(a.get("state", ActivityState.RECEIVED)),
            ),
        )
    return bytes(buf)


def encode_login_splash_res(
    announcements: Optional[Iterable[Dict[str, Any]]] = None,
    splash_banners: Optional[Iterable[Dict[str, Any]]] = None,
    activities: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.LoginSplashRes [5419]"""
    buf = bytearray()
    buf += encode_submessage(1, encode_announcement_res(announcements or ()))
    buf += encode_submessage(2, encode_splash_banner_desc_list(splash_banners or ()))
    buf += encode_submessage(3, encode_activity_info_res(activities or ()))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Activity Desc, Festival, Entrance, Bingo, Activeness, Fresh Activity
# ---------------------------------------------------------------------------

def encode_client_activity_desc(act: Dict[str, Any]) -> bytes:
    """proto.ClientActivityDesc [5287]"""
    now = int(time.time())
    start_ts = int(act.get("start_time", now - 86400))
    end_ts = int(act.get("end_time", now + 30 * 86400))
    show_ts = int(act.get("show_time", start_ts))

    buf = bytearray()
    buf += encode_uint32(1, int(act.get("group_id", 1)))
    buf += encode_uint32(2, int(act.get("activity_id", 1001)))
    buf += encode_string(3, str(act.get("act_title", "Event")))
    buf += encode_string(4, str(act.get("act_text", "")))
    buf += encode_string(5, str(act.get("award_context", "")))
    buf += encode_string(6, str(act.get("image_url", "")))
    buf += encode_string(7, str(act.get("image_url_for_lobby", "")))
    buf += encode_uint32(8, int(act.get("activity_type", ActivityType.NORMAL)))
    buf += encode_uint32(9, int(act.get("sort_id", 1)))
    buf += encode_uint32(10, int(act.get("is_process_show", 1)))
    buf += encode_uint32(11, int(act.get("act_tag", EEventTag.NEW)))
    buf += encode_uint32(12, int(act.get("gos_pos", NavigationType.NONE)))
    buf += encode_int64(13, start_ts)
    buf += encode_int64(14, end_ts)
    buf += encode_uint32(15, int(act.get("cdt_value", 1)))
    for aw in act.get("awards", ()):
        buf += encode_submessage(
            16,
            encode_award_desc(
                award_type=int(aw.get("award_type", AwardType.ITEM)),
                award_id=int(aw.get("award_id", 0)),
                award_num=int(aw.get("award_num", 1)),
                award_max_num=int(aw.get("award_max_num", 0)),
                award_expire_time=int(aw.get("award_expire_time", 0)),
            ),
        )
    for ex in act.get("exchange_items", ()):
        buf += encode_submessage(
            17,
            encode_item(
                item_id=int(ex.get("id", ex.get("item_id", 0))),
                cnt=int(ex.get("cnt", ex.get("count", 1))),
            ),
        )
    buf += encode_int64(18, show_ts)
    buf += encode_uint32(19, int(act.get("table_type", EventTabType.DAILY)))
    buf += encode_string(20, str(act.get("original_start_time", "2026-01-01 00:00:00")))
    buf += encode_string(21, str(act.get("original_end_time", "2028-12-31 23:59:59")))
    buf += encode_string(22, str(act.get("image_url_for_top_up", "")))
    buf += encode_uint32(23, int(act.get("affiliate_table", 0)))
    buf += encode_uint32(24, int(act.get("activity_class", 0)))
    return bytes(buf)


def encode_activity_festival_desc(fest: Dict[str, Any]) -> bytes:
    """proto.ActivityFestivalDesc [5588]"""
    buf = bytearray()
    buf += encode_uint32(1, int(fest.get("event_id", 1)))
    buf += encode_uint32(2, int(fest.get("table_type", EventTabType.FESTIVAL1)))
    buf += encode_string(3, str(fest.get("table_sprite", "")))
    buf += encode_string(4, str(fest.get("language", "en")))
    buf += encode_string(5, str(fest.get("event_title", "Barbosa Festival")))
    buf += encode_string(6, str(fest.get("event_lobby_icon", "")))
    buf += encode_string(7, str(fest.get("start_time", "2026-01-01 00:00:00")))
    buf += encode_string(8, str(fest.get("end_time", "2028-12-31 23:59:59")))
    buf += encode_uint32(9, int(fest.get("festival_item_id", 203000001)))
    buf += encode_string(10, str(fest.get("cdn_url", "")))
    buf += encode_uint32(11, int(fest.get("affiliate_table", 0)))
    buf += encode_uint32(12, int(fest.get("group_id", 1)))
    return bytes(buf)


def encode_activity_entrance_switch_desc(ent: Dict[str, Any]) -> bytes:
    """proto.ClientActivityEntranceSwitchDesc [5285]"""
    now = int(time.time())
    buf = bytearray()
    buf += encode_uint32(1, int(ent.get("id", 1)))
    buf += encode_int64(2, int(ent.get("show_time", now - 86400)))
    buf += encode_int64(3, int(ent.get("start_time", now - 86400)))
    buf += encode_int64(4, int(ent.get("end_time", now + 30 * 86400)))
    buf += encode_string(5, str(ent.get("go_url", "")))
    buf += encode_uint32(6, int(ent.get("go_pos", NavigationType.ACTIVITY)))
    return bytes(buf)


def encode_client_activity_bingo_info_desc(binfo: Dict[str, Any]) -> bytes:
    """proto.ClientActivityBingoInfoDesc [5286]"""
    now = int(time.time())
    buf = bytearray()
    buf += encode_uint32(1, int(binfo.get("level", 1)))
    buf += encode_uint32(2, int(binfo.get("key_id", 203000001)))
    buf += encode_uint32(3, int(binfo.get("init_key_num", 3)))
    buf += encode_uint32(4, int(binfo.get("cost_key_num", 1)))
    buf += encode_uint32(5, int(binfo.get("cost_diamond", 10)))
    buf += encode_int64(6, int(binfo.get("start_time", now - 86400)))
    buf += encode_int64(7, int(binfo.get("end_time", now + 30 * 86400)))
    return bytes(buf)


def encode_activity_bingo_rewards_desc(rdesc: Dict[str, Any]) -> bytes:
    """proto.ActivityBingoRewardsDesc [5590]"""
    buf = bytearray()
    buf += encode_uint32(1, int(rdesc.get("id", 1)))
    buf += encode_uint32(2, int(rdesc.get("level", 1)))
    buf += encode_packed_uint32(3, rdesc.get("activity_ids", ()))
    for aw in rdesc.get("awards", ()):
        buf += encode_submessage(
            4,
            encode_award_desc(
                award_type=int(aw.get("award_type", AwardType.ITEM)),
                award_id=int(aw.get("award_id", 0)),
                award_num=int(aw.get("award_num", 1)),
            ),
        )
    return bytes(buf)


def encode_activity_desc_res(
    activity_descs: Optional[Iterable[Dict[str, Any]]] = None,
    activity_festivals: Optional[Iterable[Dict[str, Any]]] = None,
    entrance_list: Optional[Iterable[Dict[str, Any]]] = None,
    bingo_info: Optional[Iterable[Dict[str, Any]]] = None,
    bingo_rewards_info: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.CSGetActivityDescRes [5271]"""
    buf = bytearray()
    for a in activity_descs or ():
        buf += encode_submessage(1, encode_client_activity_desc(a))
    for f in activity_festivals or ():
        buf += encode_submessage(2, encode_activity_festival_desc(f))
    for e in entrance_list or ():
        buf += encode_submessage(3, encode_activity_entrance_switch_desc(e))
    for b in bingo_info or ():
        buf += encode_submessage(4, encode_client_activity_bingo_info_desc(b))
    for br in bingo_rewards_info or ():
        buf += encode_submessage(5, encode_activity_bingo_rewards_desc(br))
    return bytes(buf)


def encode_activity_rewards_res(
    items: Optional[Iterable[Dict[str, Any]]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
) -> bytes:
    """proto.CSGetActivityRewardsRes [5274]"""
    return encode_submessage(1, encode_award_data(items=items, coins=coins, gems=gems, exps=exps, activeness=activeness))


def encode_fresh_activity_info_res(
    day: int = 1,
    activities: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.CSGetFreshActivityInfoRes [5543]"""
    buf = bytearray()
    buf += encode_uint32(1, day)
    for a in activities or ():
        buf += encode_submessage(
            2,
            encode_activity_info(
                act_id=int(a.get("id", 0)),
                data=int(a.get("data", 0)),
                state=int(a.get("state", ActivityState.RECEIVED)),
            ),
        )
    return bytes(buf)


def encode_fresh_activity_rewards_res(
    items: Optional[Iterable[Dict[str, Any]]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
    exchange_awards: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.CSGetFreshActivityRewardsRes [5545]"""
    buf = bytearray()
    buf += encode_submessage(1, encode_award_data(items=items, coins=coins, gems=gems, exps=exps, activeness=activeness))
    for ex in exchange_awards or ():
        buf += encode_submessage(
            2,
            encode_exchanged_award(
                origin_award_type=int(ex.get("origin_award_type", AwardType.ITEM)),
                origin_award_id=int(ex.get("origin_award_id", 0)),
                origin_award_num=int(ex.get("origin_award_num", 1)),
                dest_award_type=int(ex.get("dest_award_type", AwardType.ITEM)),
                dest_award_id=int(ex.get("dest_award_id", 0)),
                dest_award_num=int(ex.get("dest_award_num", 1)),
            ),
        )
    return bytes(buf)


# ---------------------------------------------------------------------------
# Activeness Models
# ---------------------------------------------------------------------------

def encode_activeness_desc_res(
    group_id: int = 1,
    start_time: str = "2026-01-01 00:00:00",
    end_time: str = "2028-12-31 23:59:59",
    rewards: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.CSGetActivenessDescRes [5540]"""
    time_buf = bytearray()
    time_buf += encode_uint32(1, group_id)
    time_buf += encode_string(2, start_time)
    time_buf += encode_string(3, end_time)

    buf = bytearray()
    buf += encode_submessage(1, bytes(time_buf))
    for rw in rewards or ():
        rb = bytearray()
        rb += encode_uint32(1, int(rw.get("group_id", group_id)))
        rb += encode_uint32(2, int(rw.get("box_id", 1)))
        rb += encode_string(3, str(rw.get("box", "Chest")))
        rb += encode_string(4, str(rw.get("box_icon1", "")))
        rb += encode_string(5, str(rw.get("box_icon2", "")))
        rb += encode_string(6, str(rw.get("VFX", "")))
        rb += encode_uint32(7, int(rw.get("activeness", 20)))
        for aw in rw.get("awards", ()):
            rb += encode_submessage(
                8,
                encode_award_desc(
                    award_type=int(aw.get("award_type", AwardType.COINS)),
                    award_id=int(aw.get("award_id", 0)),
                    award_num=int(aw.get("award_num", 100)),
                ),
            )
        buf += encode_submessage(2, bytes(rb))
    return bytes(buf)


def encode_activeness_and_reward_info_res(
    group_id: int = 1,
    daily_activeness: int = 60,
    weekly_activeness: int = 240,
    box_states: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """proto.CSGetActivenessAndRewardInfoRes [5539]"""
    info_buf = bytearray()
    info_buf += encode_uint32(1, group_id)
    info_buf += encode_uint32(2, daily_activeness)
    info_buf += encode_uint32(3, weekly_activeness)

    rew_info_buf = bytearray()
    for bs in box_states or ():
        bb = bytearray()
        bb += encode_uint32(1, int(bs.get("group_id", group_id)))
        bb += encode_uint32(2, int(bs.get("box_id", 1)))
        bb += encode_uint32(3, int(bs.get("state", 0)))
        rew_info_buf += encode_submessage(1, bytes(bb))

    buf = bytearray()
    buf += encode_submessage(1, bytes(info_buf))
    buf += encode_submessage(2, bytes(rew_info_buf))
    return bytes(buf)


def encode_activeness_reward_res(
    items: Optional[Iterable[Dict[str, Any]]] = None,
    coins: int = 0,
    gems: int = 0,
) -> bytes:
    """proto.CSGetActivenessRewardRes [5542]"""
    return encode_submessage(1, encode_award_data(items=items, coins=coins, gems=gems))


# ---------------------------------------------------------------------------
# Bingo Models
# ---------------------------------------------------------------------------

def encode_bingo_reward_info(rewards_id: int, awarded: bool) -> bytes:
    """proto.ActivityBingoRewardsInfo [5284]"""
    buf = bytearray()
    buf += encode_uint32(1, rewards_id)
    buf += encode_bool(2, awarded)
    return bytes(buf)


def encode_get_bingo_rewards_info_res(
    rewards: Iterable[Dict[str, Any]],
    init_items: Optional[Iterable[Dict[str, Any]]] = None,
    init_coins: int = 0,
    init_gems: int = 0,
) -> bytes:
    """proto.CSGetBingoRewardsInfoRes [5277]"""
    buf = bytearray()
    for r in rewards:
        buf += encode_submessage(
            1,
            encode_bingo_reward_info(
                rewards_id=int(r["rewards_id"]),
                awarded=bool(r.get("awarded", False)),
            ),
        )
    if init_items or init_coins or init_gems:
        buf += encode_submessage(
            2,
            encode_award_data(items=init_items, coins=init_coins, gems=init_gems),
        )
    else:
        buf += encode_submessage(2, b"")
    return bytes(buf)


def encode_flip_bingo_res(
    activity_id: int,
    rewards: Iterable[Dict[str, Any]],
) -> bytes:
    """proto.CSFlipBingoRes [5279]"""
    buf = bytearray()
    buf += encode_uint32(1, activity_id)
    for r in rewards:
        buf += encode_submessage(
            2,
            encode_bingo_reward_info(
                rewards_id=int(r["rewards_id"]),
                awarded=bool(r.get("awarded", False)),
            ),
        )
    return bytes(buf)


def encode_get_bingo_rewards_res(
    reward_id: int,
    items: Optional[Iterable[Dict[str, Any]]] = None,
    coins: int = 0,
    gems: int = 0,
) -> bytes:
    """proto.CSGetBingoRewardsRes [5281]"""
    buf = bytearray()
    buf += encode_uint32(1, reward_id)
    buf += encode_submessage(2, encode_award_data(items=items, coins=coins, gems=gems))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Adverts, Broadcasts, Scroll Marquee, Switches, GameBonus
# ---------------------------------------------------------------------------

def encode_advert_desc(ad: Dict[str, Any]) -> bytes:
    """proto.AdvertDesc [5696]"""
    now = int(time.time())
    buf = bytearray()
    buf += encode_uint32(1, int(ad.get("id", 1)))
    buf += encode_uint32(2, int(ad.get("type", AdType.LOBBY_ADS)))
    buf += encode_uint32(3, int(ad.get("sort_id", 1)))
    buf += encode_string(4, str(ad.get("language", "en")))
    buf += encode_string(5, str(ad.get("advertisment_url", "")))
    buf += encode_uint32(6, int(ad.get("ad_start_time", now - 86400)))
    buf += encode_uint32(7, int(ad.get("ad_end_time", now + 365 * 86400)))
    buf += encode_uint32(8, int(ad.get("go_pos", NavigationType.ACTIVITY)))
    buf += encode_uint32(9, int(ad.get("sub_type", 0)))
    buf += encode_string(10, str(ad.get("sub_go_pos", "")))
    buf += encode_bool(11, bool(ad.get("external_for_official_website", False)))
    buf += encode_bool(12, bool(ad.get("go_to_switch", True)))
    return bytes(buf)


def encode_advert_res(adverts: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSGetAdvertRes [5371]"""
    buf = bytearray()
    for ad in adverts:
        buf += encode_submessage(1, encode_advert_desc(ad))
    return bytes(buf)


def encode_broadcast_message(msg: Dict[str, Any]) -> bytes:
    """proto.BroadcastMessage [5366]"""
    buf = bytearray()
    buf += encode_string(1, str(msg.get("nickname", "Clack")))
    buf += encode_uint32(2, int(msg.get("navigation_type", NavigationType.GACHA)))
    buf += encode_string(3, str(msg.get("source", "Diamond Royale")))
    buf += encode_uint32(4, int(msg.get("item_id", 203000001)))
    buf += encode_int64(5, int(msg.get("time_stamp", int(time.time()))))
    buf += encode_uint32(6, int(msg.get("source_id", 1)))
    return bytes(buf)


def encode_broadcast_list_res(
    messages: Iterable[Dict[str, Any]],
    silence_show_switch: bool = False,
) -> bytes:
    """proto.CSGetBroadcastListRes [5362]"""
    buf = bytearray()
    for m in messages:
        buf += encode_submessage(1, encode_broadcast_message(m))
    buf += encode_bool(2, silence_show_switch)
    return bytes(buf)


def encode_scroll_marquee_desc(mq: Dict[str, Any]) -> bytes:
    """proto.ScrollMarqueeDesc [5365]"""
    now = int(time.time())
    buf = bytearray()
    buf += encode_string(1, str(mq.get("language", "en")))
    buf += encode_uint32(2, int(mq.get("order_in_this_language", 1)))
    buf += encode_string(3, str(mq.get("content", "")))
    buf += encode_int64(4, int(mq.get("start_time", now - 86400)))
    buf += encode_int64(5, int(mq.get("end_time", now + 365 * 86400)))
    buf += encode_string(6, str(mq.get("region", "DEFAULT")))
    buf += encode_uint32(7, int(mq.get("gos_pos", NavigationType.NONE)))
    buf += encode_string(8, str(mq.get("gos_url", "")))
    buf += encode_bool(9, bool(mq.get("use_embedded_browser", False)))
    buf += encode_string(10, str(mq.get("sub_go_pos", "")))
    return bytes(buf)


def encode_scroll_marquee_res(marquees: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSScrollMarqueeRes [5361]"""
    buf = bytearray()
    for mq in marquees:
        buf += encode_submessage(1, encode_scroll_marquee_desc(mq))
    return bytes(buf)


def encode_login_broadcast_res(
    marquees: Iterable[Dict[str, Any]],
    messages: Iterable[Dict[str, Any]],
    silence_show_switch: bool = False,
) -> bytes:
    """proto.LoginBroadcastRes [5455]"""
    buf = bytearray()
    buf += encode_submessage(1, encode_scroll_marquee_res(marquees))
    buf += encode_submessage(2, encode_broadcast_list_res(messages, silence_show_switch))
    return bytes(buf)


def encode_all_switchs_res(switches: Iterable[Dict[str, Any]]) -> bytes:
    """proto.CSGetAllSwitchsRes [5413] (SwitchDesc [5741])"""
    buf = bytearray()
    for sw in switches:
        sb = bytearray()
        sb += encode_uint32(1, int(sw["id"]))
        sb += encode_bool(2, bool(sw.get("is_open", True)))
        if sw.get("content"):
            sb += encode_string(3, str(sw["content"]))
        buf += encode_submessage(1, bytes(sb))
    return bytes(buf)


def encode_game_bonus_event_desc_res(events: Optional[Iterable[Dict[str, Any]]] = None) -> bytes:
    """proto.CSGetGameBonusEventDescRes [5169] (GameBonusEventDesc [5674])"""
    now = int(time.time())
    buf = bytearray()
    for ev in events or ():
        eb = bytearray()
        eb += encode_string(1, str(ev.get("region", "DEFAULT")))
        eb += encode_uint32(2, int(ev.get("id", 1)))
        eb += encode_string(3, str(ev.get("start_day", "2026-01-01")))
        eb += encode_string(4, str(ev.get("end_day", "2028-12-31")))
        eb += encode_string(5, str(ev.get("daily_start_time", "00:00:00")))
        eb += encode_string(6, str(ev.get("daily_end_time", "23:59:59")))
        eb += encode_uint32(7, int(ev.get("match_mode", 0)))
        eb += encode_uint32(8, int(ev.get("game_mode", 0)))
        eb += encode_uint32(9, int(ev.get("map_id", 0)))
        eb += encode_int32(10, int(ev.get("group_mode", 0)))
        eb += encode_uint32(11, int(ev.get("exp_bonus", 100)))
        eb += encode_uint32(12, int(ev.get("gold_bonus", 100)))
        eb += encode_uint32(13, int(ev.get("gold_limit", 5000)))
        eb += encode_uint32(14, int(ev.get("debris_limit", 50)))
        ts_start = int(ev.get("today_start_timestamp", now - 3600))
        ts_end = int(ev.get("today_end_timestamp", now + 82800))
        ts_tm_start = int(ev.get("tomorrow_start_timestamp", now + 82800))
        ts_tm_end = int(ev.get("tomorrow_end_timestamp", now + 169200))
        eb += encode_int64(15, ts_start)
        eb += encode_int64(16, ts_end)
        eb += encode_int64(17, ts_tm_start)
        eb += encode_int64(18, ts_tm_end)
        eb += encode_int64(101, ts_start)
        eb += encode_int64(102, ts_end)
        eb += encode_int64(103, ts_tm_start)
        eb += encode_int64(104, ts_tm_end)
        buf += encode_submessage(1, bytes(eb))
    return bytes(buf)


def encode_match_daily_bonus_res(
    has_exp_achieved: bool = False,
    exp_bonus: int = 100,
    has_gold_achieved: bool = False,
    gold_bonus: int = 100,
) -> bytes:
    """proto.CSMatchDailyBonusRes [5165]"""
    buf = bytearray()
    buf += encode_bool(1, has_exp_achieved)
    buf += encode_uint32(2, exp_bonus)
    buf += encode_bool(3, has_gold_achieved)
    buf += encode_uint32(4, gold_bonus)
    return bytes(buf)


def encode_login_desc_res(
    advert_res: bytes = b"",
    switchs_res: bytes = b"",
    activity_res: bytes = b"",
    gacha_res: bytes = b"",
    ranking_res: bytes = b"",
    profile_res: bytes = b"",
    avatar_res: bytes = b"",
    hide_res: bytes = b"",
    treasure_res: bytes = b"",
    bundle_res: bytes = b"",
    gift_store_res: bytes = b"",
    ranking_match_param: bytes = b"",
    ranking_item_rank: bytes = b"",
    discount_store_res: bytes = b"",
    ranking_activity_config_res: bytes = b"",
    google_rewards_desc: bytes = b"",
    fullscreen_cg_res: bytes = b"",
    game_bonus_event_res: bytes = b"",
    championship_basic_info_res: bytes = b"",
    store_tab_res: bytes = b"",
) -> bytes:
    """proto.LoginDescRes [5420] — all 20 static desc submessages."""
    parts = [
        (1, advert_res),
        (2, switchs_res),
        (3, activity_res),
        (4, gacha_res),
        (5, ranking_res),
        (6, profile_res),
        (7, avatar_res),
        (8, hide_res),
        (9, treasure_res),
        (10, bundle_res),
        (11, gift_store_res),
        (12, ranking_match_param),
        (13, ranking_item_rank),
        (14, discount_store_res),
        (15, ranking_activity_config_res),
        (16, google_rewards_desc),
        (17, fullscreen_cg_res),
        (18, game_bonus_event_res),
        (19, championship_basic_info_res),
        (20, store_tab_res),
    ]
    buf = bytearray()
    for tag, sub in parts:
        buf += encode_submessage(tag, sub)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Request Decoders (CS*Req)
# ---------------------------------------------------------------------------

def decode_language_req(raw_body: bytes, field_num: int = 1, default: str = "en") -> str:
    if not raw_body:
        return default
    fields = decode_proto(raw_body)
    lang = get_string(fields, field_num, default)
    return lang or default


def decode_activity_rewards_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSGetActivityRewardsReq [5273]"""
    fields = decode_proto(raw_body)
    return {
        "activity_ids": get_packed_varints(fields, 1),
        "language": get_string(fields, 2, "en"),
    }


def decode_fresh_activity_rewards_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSGetFreshActivityRewardsReq [5544]"""
    fields = decode_proto(raw_body)
    return {
        "activity_ids": get_packed_varints(fields, 1),
        "is_daily": get_bool(fields, 2, True),
    }


def decode_flip_bingo_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSFlipBingoReq [5278]"""
    fields = decode_proto(raw_body)
    return {
        "activity_id": get_varint(fields, 1, 0),
        "language": get_string(fields, 2, "en"),
    }


def decode_get_bingo_rewards_req(raw_body: bytes) -> int:
    """proto.CSGetBingoRewardsReq [5280]"""
    fields = decode_proto(raw_body)
    return get_varint(fields, 1, 0)


def decode_finish_bingo_activity_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSFinishBingoActivityReq [5282]"""
    fields = decode_proto(raw_body)
    return {
        "activity_id": get_varint(fields, 1, 0),
        "key_id": get_varint(fields, 2, 0),
        "language": get_string(fields, 3, "en"),
    }


def decode_activeness_reward_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSGetActivenessRewardReq [5541]"""
    fields = decode_proto(raw_body)
    box = get_submessage(fields, 1)
    return {
        "group_id": get_varint(box, 1, 1),
        "box_id": get_varint(box, 2, 1),
    }


def decode_get_attendance_req(raw_body: bytes) -> bool:
    """proto.CSGetAttendanceReq [5262]"""
    fields = decode_proto(raw_body)
    return get_bool(fields, 1, False)
