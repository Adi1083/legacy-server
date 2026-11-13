"""
Protobuf serializers and deserializers for Free Fire 1.39 Mail System.

All ProtoMember tags, wire types, IsPacked flags, and enums verified against
D:\\LEGACY\\dump\\dump.cs, global-metadata.dat (v23), and x86 libil2cpp.so.

Schemas:
- proto.CSGetMailListReq  (1: string language)
- proto.CSGetMailListRes  (1: List<MailInfo> mails)
- proto.MailInfo          (1: uint64 mail_id, 2: uint32 type, 3: string title,
                           4: string content, 5: MailSenderInfo sender_info,
                           6: MailAttachment attachment, 7: int64 receive_time,
                           8: Status status, 9: Source source, 10: ActionType action_type)
- proto.MailSenderInfo    (1: uint64 sender_id, 2: string sender_nick, 3..19 optional)
- proto.MailGlobalDropInfo(1: uint32 item_id, 2: string url)
- proto.MailAttachment    (1: AwardData rewards)
- proto.AwardData         (1: List<Item> items, 2: uint32 coins, 3: uint32 gems,
                           4: uint32 exps, 5: uint32 activeness)
- proto.Item              (1: uint32 id, 2: uint32 cnt, 3: uint32 expire_time,
                           4: int32 left_use_times, 5: uint32 history_owned_cnt,
                           6: uint32 left_expire_time, 7: ItemStatus item_status,
                           8: ItemType item_type, 9: ItemSubType item_sub_type,
                           10: InstallmentStatus installment_status,
                           11..13: uint32 installment_term/create_time/next_pay_time)
- proto.ExchangedAward    (1..3: origin_award_type/id/num, 4..6: dest_award_type/id/num)
- proto.CSReadMailReq     (1: uint64[] mail_ids [IsPacked=true], 2: uint32 status)
- proto.CSReadMailRes     (1: AwardData rewards, 2: List<ExchangedAward> exchangedAwards)
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

from .decoder import (
    decode_proto,
    get_packed_varints,
    get_string,
    get_varint,
)
from .encoder import (
    encode_int32,
    encode_int64,
    encode_packed_uint64,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)


# ---------------------------------------------------------------------------
# Free Fire 1.39 Mail & Reward Enums (global-metadata.dat)
# ---------------------------------------------------------------------------
class MailSource:
    GAME = 0
    ADMIN = 1


class MailActionType:
    ATTACHMENT = 0
    NOTICE = 1
    CLAN_INVITE = 2


class MailStatus:
    INIT = 0
    PROCESSED = 1
    DELETED = 2


class MailType:
    NONE = 0
    CLAN_INVITE = 1
    CLAN_DISMISS = 2
    CLAN_KICKOUT = 3
    CLAN_REASSIGN_CAPTAIN = 4
    RANKING_SEASON_REWARDS = 5
    RANKING_RANK_LEVEL_REWARDS = 6
    EP_UNLOCK_REWARD = 7
    EP_CHALLENGE_REWARD = 8
    STORE_SEND_GIFT = 9
    GLOBAL_DROPS = 10
    CLAN_RACE_AWARD = 11
    SET_STREAMER = 14
    DEL_STREAMER = 15
    INSTANT_GAME_REWARD = 16
    SUBSCRIPTION_EP = 17
    CHAMPIONSHIP_TEAM_DISMISS = 18
    CHAMPIONSHIP_TEAM_KICKOUT = 19
    CHAMPIONSHIP_TRIAL_REWARDS = 20
    GOP_PURCHASE = 21


class ItemStatus:
    NONE = 0
    PERMANENT = 1
    INEXPIRE = 2
    OUTEXPIRE = 3


class ItemType:
    NONE = 0
    AVATAR = 1
    CLOTHES = 2
    LIMITEDCARD = 3
    TREASUREBOX = 4
    LOADOUTBOX = 5
    ROOMCARD = 6
    BUNDLE = 7
    DEBRIS = 8
    COLLECTION = 9
    VIRTUAL = 10
    BONUSCARD = 11
    STICKER = 12
    PET = 13


class AwardType:
    NONE = 0
    ITEM = 1
    COINS = 2
    GEMS = 3
    SKILL = 4
    EXP = 5
    ACTIVENESS = 6


def infer_item_type(item_id: int, explicit_type: Optional[int] = None) -> int:
    """Infer Free Fire 1.39 ItemType enum value from real item.csv ID prefixes."""
    if explicit_type is not None and int(explicit_type) > 0:
        return int(explicit_type)
    iid = int(item_id)
    if iid < 1000 or 100000000 <= iid < 200000000:
        return ItemType.AVATAR
    if 209000000 <= iid < 210000000:
        # Parachutes (209xxxxxx) have ItemType=9 (COLLECTION) in item.csv
        return ItemType.COLLECTION
    if 200000000 <= iid < 300000000:
        return ItemType.CLOTHES
    if 300000000 <= iid < 400000000:
        return ItemType.LIMITEDCARD
    if 400000000 <= iid < 500000000:
        return ItemType.TREASUREBOX
    if 500000000 <= iid < 600000000:
        return ItemType.LOADOUTBOX
    if 600000000 <= iid < 700000000:
        return ItemType.ROOMCARD
    if 700000000 <= iid < 800000000:
        return ItemType.BUNDLE
    if 800000000 <= iid < 900000000:
        return ItemType.DEBRIS
    if 900000000 <= iid < 1000000000:
        return ItemType.COLLECTION
    if 1000000000 <= iid < 1100000000:
        return ItemType.VIRTUAL
    if 1100000000 <= iid < 1200000000:
        return ItemType.BONUSCARD
    if 1200000000 <= iid < 1300000000:
        return ItemType.STICKER
    if 1300000000 <= iid < 1400000000:
        return ItemType.PET
    return ItemType.CLOTHES


# ---------------------------------------------------------------------------
# Protobuf Encoders
# ---------------------------------------------------------------------------
def encode_item(
    item_id: int,
    cnt: int = 1,
    expire_time: int = 0,
    left_use_times: int = 0,
    history_owned_cnt: Optional[int] = None,
    left_expire_time: int = 0,
    item_status: int = ItemStatus.PERMANENT,
    item_type: Optional[int] = None,
    item_sub_type: int = 0,
    installment_status: int = 0,
    installment_term: int = 0,
    installment_create_time: int = 0,
    installment_next_pay_time: int = 0,
) -> bytes:
    """Encode proto.Item (tags 1..13)."""
    count = max(1, int(cnt))
    resolved_type = infer_item_type(item_id, item_type)
    buf = bytearray()
    buf += encode_uint32(1, int(item_id))
    buf += encode_uint32(2, count)
    if expire_time:
        buf += encode_uint32(3, int(expire_time))
    if left_use_times:
        buf += encode_int32(4, int(left_use_times))
    buf += encode_uint32(5, count if history_owned_cnt is None else int(history_owned_cnt))
    if left_expire_time:
        buf += encode_uint32(6, int(left_expire_time))
    buf += encode_uint32(7, int(item_status))
    buf += encode_uint32(8, resolved_type)
    if item_sub_type:
        buf += encode_uint32(9, int(item_sub_type))
    if installment_status:
        buf += encode_uint32(10, int(installment_status))
    if installment_term:
        buf += encode_uint32(11, int(installment_term))
    if installment_create_time:
        buf += encode_uint32(12, int(installment_create_time))
    if installment_next_pay_time:
        buf += encode_uint32(13, int(installment_next_pay_time))
    return bytes(buf)


def encode_exchanged_award(
    origin_award_type: int,
    origin_award_id: int,
    origin_award_num: int,
    dest_award_type: int,
    dest_award_id: int,
    dest_award_num: int,
) -> bytes:
    """Encode proto.ExchangedAward (tags 1..6)."""
    buf = bytearray()
    buf += encode_uint32(1, int(origin_award_type))
    buf += encode_uint32(2, int(origin_award_id))
    buf += encode_uint32(3, int(origin_award_num))
    buf += encode_uint32(4, int(dest_award_type))
    buf += encode_uint32(5, int(dest_award_id))
    buf += encode_uint32(6, int(dest_award_num))
    return bytes(buf)


def _normalize_item_entry(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, dict):
        item_id = int(entry.get("item_id", entry.get("id", 0)))
        count = max(1, int(entry.get("count", entry.get("cnt", 1))))
        explicit_type = entry.get("item_type")
        return {
            "id": item_id,
            "cnt": count,
            "expire_time": int(entry.get("expire_time", 0)),
            "left_use_times": int(entry.get("left_use_times", 0)),
            "history_owned_cnt": entry.get("history_owned_cnt"),
            "left_expire_time": int(entry.get("left_expire_time", 0)),
            "item_status": int(entry.get("item_status", ItemStatus.PERMANENT)),
            "item_type": int(explicit_type) if explicit_type is not None else None,
            "item_sub_type": int(entry.get("item_sub_type", 0)),
        }
    return {
        "id": int(entry),
        "cnt": 1,
        "expire_time": 0,
        "left_use_times": 0,
        "history_owned_cnt": None,
        "left_expire_time": 0,
        "item_status": ItemStatus.PERMANENT,
        "item_type": None,
        "item_sub_type": 0,
    }


def encode_award_data(
    items: Optional[Iterable[Any]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
) -> bytes:
    """Encode proto.AwardData (1: items, 2: coins, 3: gems, 4: exps, 5: activeness)."""
    buf = bytearray()
    for entry in (items or ()):
        norm = _normalize_item_entry(entry)
        if norm["id"] > 0:
            buf += encode_submessage(1, encode_item(
                item_id=norm["id"],
                cnt=norm["cnt"],
                expire_time=norm["expire_time"],
                left_use_times=norm["left_use_times"],
                history_owned_cnt=norm["history_owned_cnt"],
                left_expire_time=norm["left_expire_time"],
                item_status=norm["item_status"],
                item_type=norm["item_type"],
                item_sub_type=norm["item_sub_type"],
            ))
    if coins > 0:
        buf += encode_uint32(2, int(coins))
    if gems > 0:
        buf += encode_uint32(3, int(gems))
    if exps > 0:
        buf += encode_uint32(4, int(exps))
    if activeness > 0:
        buf += encode_uint32(5, int(activeness))
    return bytes(buf)


def encode_mail_attachment(
    items: Optional[Iterable[Any]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
) -> bytes:
    """Encode proto.MailAttachment (1: AwardData rewards)."""
    rewards_bytes = encode_award_data(
        items=items,
        coins=coins,
        gems=gems,
        exps=exps,
        activeness=activeness,
    )
    return encode_submessage(1, rewards_bytes)


def encode_mail_global_drop_info(item_id: int, url: str = "") -> bytes:
    """Encode proto.MailGlobalDropInfo (1: uint32 item_id, 2: string url)."""
    buf = bytearray()
    buf += encode_uint32(1, int(item_id))
    if url:
        buf += encode_string(2, url)
    return bytes(buf)


def encode_mail_sender_info(
    sender_id: int = 0,
    sender_nick: str = "System",
    clan_id: int = 0,
    clan_name: str = "",
    clan_captain_id: int = 0,
    clan_captain_nick: str = "",
    season_id: int = 0,
    season_rank: int = 0,
    ep_unlock_id: int = 0,
    ep_challenge_id: int = 0,
    gift_message: str = "",
    global_drop: Optional[Dict[str, Any]] = None,
    honor_delta: int = 0,
    subscription_ep_id: int = 0,
    championship_team_id: int = 0,
    championship_team_name: str = "",
    championship_type: int = 0,
    championship_id: int = 0,
    championship_trial_pos: int = 0,
) -> bytes:
    """Encode proto.MailSenderInfo (tags 1..19)."""
    buf = bytearray()
    buf += encode_uint64(1, int(sender_id))
    buf += encode_string(2, str(sender_nick))
    if clan_id:
        buf += encode_uint64(3, int(clan_id))
    if clan_name:
        buf += encode_string(4, clan_name)
    if clan_captain_id:
        buf += encode_uint64(5, int(clan_captain_id))
    if clan_captain_nick:
        buf += encode_string(6, clan_captain_nick)
    if season_id:
        buf += encode_uint32(7, int(season_id))
    if season_rank:
        buf += encode_uint32(8, int(season_rank))
    if ep_unlock_id:
        buf += encode_uint32(9, int(ep_unlock_id))
    if ep_challenge_id:
        buf += encode_uint32(10, int(ep_challenge_id))
    if gift_message:
        buf += encode_string(11, gift_message)
    if global_drop:
        buf += encode_submessage(
            12,
            encode_mail_global_drop_info(
                item_id=int(global_drop.get("item_id", 0)),
                url=str(global_drop.get("url", "")),
            ),
        )
    if honor_delta:
        buf += encode_uint32(13, int(honor_delta))
    if subscription_ep_id:
        buf += encode_uint32(14, int(subscription_ep_id))
    if championship_team_id:
        buf += encode_uint64(15, int(championship_team_id))
    if championship_team_name:
        buf += encode_string(16, championship_team_name)
    if championship_type:
        buf += encode_uint32(17, int(championship_type))
    if championship_id:
        buf += encode_uint32(18, int(championship_id))
    if championship_trial_pos:
        buf += encode_uint32(19, int(championship_trial_pos))
    return bytes(buf)


def _resolve_proto_mail_status(mail: Dict[str, Any]) -> int:
    """
    Map ServerState mail flags to proto.EMail.Status:
      0 = Status_INIT (unclaimed -> Receive/Claim button enabled)
      1 = Status_PROCESSED (claimed -> Delete button enabled)
      2 = Status_DELETED
    Note: ServerState.read_mail sets internal status=1 for local read tracking,
    while ServerState.claim_mail sets is_claimed=True and internal status=2.
    Checking is_claimed prevents an unclaimed-but-read mail from hiding Claim,
    and prevents a claimed mail from being serialized as Status_DELETED.
    """
    if mail.get("is_deleted"):
        return MailStatus.DELETED
    if mail.get("is_claimed"):
        return MailStatus.PROCESSED
    return MailStatus.INIT


def encode_mail_info(mail: Dict[str, Any]) -> bytes:
    """Encode a ServerState mail dict into proto.MailInfo (tags 1..10)."""
    attachments = mail.get("attachments") or []
    coins = max(0, int(mail.get("coins", 0)))
    gems = max(0, int(mail.get("gems", 0)))
    exps = max(0, int(mail.get("exps", 0)))
    activeness = max(0, int(mail.get("activeness", 0)))
    has_rewards = bool(attachments or coins > 0 or gems > 0 or exps > 0 or activeness > 0)

    mail_type = int(mail.get("type", MailType.NONE))
    source = int(mail.get("source", MailSource.ADMIN))
    action_type = int(mail.get("action_type", MailActionType.ATTACHMENT))
    if not has_rewards and action_type == MailActionType.ATTACHMENT:
        # Pure text notices should expose Delete rather than an empty Claim button.
        action_type = MailActionType.NOTICE
        if mail_type == MailType.CLAN_INVITE:
            mail_type = MailType.NONE

    proto_status = _resolve_proto_mail_status(mail)
    sender_bytes = encode_mail_sender_info(
        sender_id=int(mail.get("sender_id", 0)),
        sender_nick=str(mail.get("sender_nick", "System")),
        gift_message=str(mail.get("gift_message", "")),
    )
    attachment_bytes = encode_mail_attachment(
        items=attachments,
        coins=coins,
        gems=gems,
        exps=exps,
        activeness=activeness,
    )

    buf = bytearray()
    buf += encode_uint64(1, int(mail["mail_id"]))
    buf += encode_uint32(2, mail_type)
    buf += encode_string(3, str(mail.get("title", "")))
    buf += encode_string(4, str(mail.get("content", "")))
    buf += encode_submessage(5, sender_bytes)
    buf += encode_submessage(6, attachment_bytes)
    buf += encode_int64(7, int(mail.get("receive_time", int(time.time()))))
    buf += encode_uint32(8, proto_status)
    buf += encode_uint32(9, source)
    buf += encode_uint32(10, action_type)
    return bytes(buf)


def encode_get_mail_list_res(mails: Iterable[Dict[str, Any]]) -> bytes:
    """Encode proto.CSGetMailListRes (1: repeated MailInfo mails)."""
    buf = bytearray()
    for mail in mails:
        if mail.get("is_deleted"):
            continue
        buf += encode_submessage(1, encode_mail_info(mail))
    return bytes(buf)


def encode_read_mail_req(mail_ids: Iterable[int], status: int = MailStatus.PROCESSED) -> bytes:
    """Encode proto.CSReadMailReq (1: packed uint64[] mail_ids, 2: uint32 status)."""
    buf = bytearray()
    buf += encode_packed_uint64(1, [int(mid) for mid in mail_ids])
    buf += encode_uint32(2, int(status))
    return bytes(buf)


def encode_read_mail_res(
    items: Optional[Iterable[Any]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
    exchanged_awards: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """Encode proto.CSReadMailRes (1: AwardData rewards, 2: List<ExchangedAward> exchangedAwards)."""
    buf = bytearray()
    has_rewards = bool(items) or coins > 0 or gems > 0 or exps > 0 or activeness > 0
    if has_rewards:
        buf += encode_submessage(
            1,
            encode_award_data(
                items=items,
                coins=coins,
                gems=gems,
                exps=exps,
                activeness=activeness,
            ),
        )
    for ex in (exchanged_awards or ()):
        buf += encode_submessage(
            2,
            encode_exchanged_award(
                origin_award_type=int(ex.get("origin_award_type", AwardType.ITEM)),
                origin_award_id=int(ex.get("origin_award_id", 0)),
                origin_award_num=int(ex.get("origin_award_num", 1)),
                dest_award_type=int(ex.get("dest_award_type", AwardType.COINS)),
                dest_award_id=int(ex.get("dest_award_id", 0)),
                dest_award_num=int(ex.get("dest_award_num", 0)),
            ),
        )
    return bytes(buf)


def encode_claim_mail_res(
    items: Optional[Iterable[Any]] = None,
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
    exchanged_awards: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """Alias for encode_read_mail_res (Free Fire 1.39 uses CSReadMailRes for mail claims)."""
    return encode_read_mail_res(
        items=items,
        coins=coins,
        gems=gems,
        exps=exps,
        activeness=activeness,
        exchanged_awards=exchanged_awards,
    )


# ---------------------------------------------------------------------------
# Protobuf Decoders
# ---------------------------------------------------------------------------
def decode_get_mail_list_req(raw_body: bytes) -> Dict[str, Any]:
    """Decode proto.CSGetMailListReq (1: string language)."""
    fields = decode_proto(raw_body)
    return {
        "language": get_string(fields, 1, "en"),
    }


def decode_read_mail_req(raw_body: bytes) -> Dict[str, Any]:
    """Decode proto.CSReadMailReq (1: packed uint64[] mail_ids, 2: uint32 status)."""
    fields = decode_proto(raw_body)
    return {
        "mail_ids": get_packed_varints(fields, 1),
        "status": get_varint(fields, 2, MailStatus.PROCESSED),
    }


def decode_claim_mail_req(raw_body: bytes) -> Dict[str, Any]:
    """Decode CSClaimMailReq / CSReadMailReq (accepts packed/unpacked/single mail_id on tag 1)."""
    fields = decode_proto(raw_body)
    mail_ids = get_packed_varints(fields, 1)
    return {
        "mail_ids": mail_ids,
        "status": get_varint(fields, 2, MailStatus.PROCESSED),
    }
