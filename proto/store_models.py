"""
Protobuf models and default Store catalogs for Free Fire 1.39 Store, Bundles,
Treasure Boxes / Weapon Crates, Gift Store, Exchange Store, Discount Store,
Installment Store, and PayBundle Windows.

All ProtoMember tags, wire types, packed flags, and enum constants are extracted
directly from Free Fire 1.39 global-metadata.dat + x86 libil2cpp.so.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .decoder import (
    decode_proto,
    get_bool,
    get_packed_varints,
    get_string,
    get_varint,
)
from .encoder import (
    encode_bool,
    encode_float,
    encode_int32,
    encode_int64,
    encode_packed_uint64,
    encode_string,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)


# ---------------------------------------------------------------------------
# Enums (verified from Free Fire 1.39 dump.cs)
# ---------------------------------------------------------------------------

class AwardType:
    """EInventory.AwardType [4935]"""
    NONE = 0
    ITEM = 1
    COINS = 2
    GEMS = 3
    SKILL = 4
    EXP = 5
    ACTIVENESS = 6


class CurrencyType:
    """EInventory.CurrencyType [4936]"""
    NONE = 0
    COINS = 1
    GEMS = 2


class StoreTag:
    """EInventory.StoreTag"""
    NONE = 0
    DISCOUNT = 1
    HOT = 2
    NEW = 3
    LIMITEDTIME = 4
    PURCHASELIMITED = 5
    EARLY_ACCESS = 6


class StorePromotionType:
    """EInventory.StorePromotionType"""
    NORMAL = 0
    DISCOUNT = 1


class ItemStatus:
    """EInventory.ItemStatus"""
    NONE = 0
    PERMANENT = 1
    EXPIRED = 2


class ItemType:
    """EInventory.ItemType [4930]"""
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


class ItemSubType:
    """EInventory.ItemSubType [4931]"""
    NONE = 0
    ELITEPASS = 3
    VOUCHER = 4
    RENAMECARD = 5
    REDENVELOPE = 6
    PETFOOD = 7
    PETACTION = 9
    PETSKIN = 10
    REVIVETOKEN = 11
    AVATARLEVELCARD = 12
    CHIP = 13
    GUILD_TOKEN = 14
    PETSKILL = 15
    CRATE = 16


class TransReason:
    """EInventory.TransReason [4941]"""
    NONE = 0
    USECARD = 1
    PURCHASE = 2
    TREASUREBOX = 3
    LOADOUT = 4
    BUNDLE = 15
    SEND_GIFT = 30
    EXCHANGESTORE_PURCHASE = 32


class MallType:
    """UINavigationUtil.UINavigationMallType [7019]"""
    NONE = 0
    NORMAL = 1
    WEAPON = 2
    BOX = 3
    GIFT = 4
    EXCHANGE = 5


class MallTabType:
    """UINavigationUtil.UINavigationMallTabType [7020]"""
    NONE = 0
    ALL = 1
    EXCLUSIVE = 2
    ADS = 3
    NEW_ITEM = 4
    TREASURE_BOX = 5
    BUNDLE = 6
    AVATAR = 7
    CLOTHES = 8
    WEAPON = 9
    PROPS = 10
    COLLECTION = 11
    PET = 12
    OTHER = 13
    DISCOUNT = 14
    INSTALLMENT = 15


class BoxType:
    """ETreasureBox.BoxType"""
    NONE = 0
    NORMAL = 1
    CRATE = 2


class BuddyType:
    """EGiftStore_BuddyType [5550]"""
    NONE = 0
    FRIEND = 1
    CLAN = 2
    TEAMMATE = 3


class InstallmentType:
    """EInventory.InstallmentType"""
    NONE = 0
    DAY_7 = 1
    DAY_15 = 2
    DAY_30 = 3


class InstallmentStatus:
    """EInventory.InstallmentStatus"""
    NONE = 0


# ---------------------------------------------------------------------------
# Item Classification Helper
# ---------------------------------------------------------------------------

def infer_item_type_and_subtype(item_id: int) -> Tuple[int, int]:
    """Infer Free Fire 1.39 ItemType & ItemSubType from real Item.csv ID prefixes."""
    iid = int(item_id)
    if 1 <= iid <= 99:
        return ItemType.AVATAR, ItemSubType.NONE
    prefix3 = iid // 1_000_000
    if prefix3 in (101, 102):
        return ItemType.AVATAR, ItemSubType.NONE
    if prefix3 == 209:
        return ItemType.COLLECTION, ItemSubType.NONE
    if prefix3 in (203, 204, 205, 206, 207, 208, 211, 212, 214):
        return ItemType.CLOTHES, ItemSubType.NONE
    if prefix3 in (301, 302, 303, 700, 710):
        return ItemType.BUNDLE, ItemSubType.NONE
    if prefix3 in (400, 401, 402, 403):
        return ItemType.TREASUREBOX, ItemSubType.CRATE
    if prefix3 == 500:
        return ItemType.LOADOUTBOX, ItemSubType.NONE
    if prefix3 == 501:
        return ItemType.VIRTUAL, ItemSubType.GUILD_TOKEN
    if prefix3 == 600:
        return ItemType.ROOMCARD, ItemSubType.NONE
    if 800 <= prefix3 <= 899:
        if prefix3 == 814:
            return ItemType.DEBRIS, ItemSubType.GUILD_TOKEN
        if prefix3 == 812:
            return ItemType.DEBRIS, ItemSubType.AVATARLEVELCARD
        return ItemType.DEBRIS, ItemSubType.NONE
    if 900 <= prefix3 <= 999:
        return ItemType.COLLECTION, ItemSubType.NONE
    if prefix3 == 1001:
        return ItemType.VIRTUAL, ItemSubType.NONE
    if prefix3 in (1101, 1102):
        return ItemType.BONUSCARD, ItemSubType.NONE
    if prefix3 == 1200:
        return ItemType.STICKER, ItemSubType.NONE
    if prefix3 == 130:
        return ItemType.PET, ItemSubType.NONE
    if prefix3 == 131:
        return ItemType.PET, ItemSubType.PETSKIN
    if prefix3 == 132:
        return ItemType.PET, ItemSubType.PETSKILL
    return ItemType.CLOTHES, ItemSubType.NONE


# ---------------------------------------------------------------------------
# Common Inventory / Award Proto Encoders
# ---------------------------------------------------------------------------

def encode_item(
    item_id: int,
    cnt: int = 1,
    expire_time: int = 0,
    left_use_times: int = -1,
    history_owned_cnt: Optional[int] = None,
    left_expire_time: int = 0,
    item_status: int = ItemStatus.PERMANENT,
    item_type: Optional[int] = None,
    item_sub_type: Optional[int] = None,
    installment_status: int = InstallmentStatus.NONE,
    installment_term: int = 0,
    installment_create_time: int = 0,
    installment_next_pay_time: int = 0,
) -> bytes:
    """proto.Item"""
    inferred_type, inferred_sub = infer_item_type_and_subtype(item_id)
    if item_type is None:
        item_type = inferred_type
    if item_sub_type is None:
        item_sub_type = inferred_sub
    if history_owned_cnt is None:
        history_owned_cnt = max(1, int(cnt))

    buf = bytearray()
    buf += encode_uint32(1, item_id)
    buf += encode_uint32(2, cnt)
    buf += encode_uint32(3, expire_time)
    buf += encode_int32(4, left_use_times)
    buf += encode_uint32(5, history_owned_cnt)
    buf += encode_uint32(6, left_expire_time)
    buf += encode_uint32(7, item_status)
    buf += encode_uint32(8, item_type)
    buf += encode_uint32(9, item_sub_type)
    if installment_status:
        buf += encode_uint32(10, installment_status)
    if installment_term:
        buf += encode_uint32(11, installment_term)
    if installment_create_time:
        buf += encode_uint32(12, installment_create_time)
    if installment_next_pay_time:
        buf += encode_uint32(13, installment_next_pay_time)
    return bytes(buf)


def encode_award_desc(
    award_id: int,
    award_num: int = 1,
    award_type: int = AwardType.ITEM,
    award_max_num: int = 0,
    award_expire_time: int = 0,
) -> bytes:
    """proto.AwardDesc"""
    buf = bytearray()
    buf += encode_uint32(1, award_type)
    buf += encode_uint32(2, award_id)
    buf += encode_uint32(3, award_num)
    if award_max_num:
        buf += encode_uint32(4, award_max_num)
    if award_expire_time:
        buf += encode_uint32(5, award_expire_time)
    return bytes(buf)


def encode_exchanged_award(
    origin_award_type: int,
    origin_award_id: int,
    origin_award_num: int,
    dest_award_type: int,
    dest_award_id: int,
    dest_award_num: int,
) -> bytes:
    """proto.ExchangedAward"""
    buf = bytearray()
    buf += encode_uint32(1, origin_award_type)
    buf += encode_uint32(2, origin_award_id)
    buf += encode_uint32(3, origin_award_num)
    buf += encode_uint32(4, dest_award_type)
    buf += encode_uint32(5, dest_award_id)
    buf += encode_uint32(6, dest_award_num)
    return bytes(buf)


def encode_award_data(
    items: Sequence[Dict[str, Any]] = (),
    coins: int = 0,
    gems: int = 0,
    exps: int = 0,
    activeness: int = 0,
) -> bytes:
    """proto.AwardData"""
    buf = bytearray()
    for it in items:
        buf += encode_submessage(1, encode_item(**it) if isinstance(it, dict) else bytes(it))
    buf += encode_uint32(2, coins)
    buf += encode_uint32(3, gems)
    if exps:
        buf += encode_uint32(4, exps)
    if activeness:
        buf += encode_uint32(5, activeness)
    return bytes(buf)


def encode_exchange_change_data(
    trans_id: int = 1,
    add_item_list: Sequence[Dict[str, Any]] = (),
    del_item_list: Sequence[Dict[str, Any]] = (),
    coins_delta: int = 0,
    gems_delta: int = 0,
    gop_gems_delta: int = 0,
    reason: int = TransReason.PURCHASE,
    sub_reason: int = 0,
    gop_gems: int = 0,
    gop_total_topup: int = 0,
    gop_total_free: int = 0,
    exchange_awards: Sequence[Dict[str, Any]] = (),
    check_bundle: bool = False,
) -> bytes:
    """proto.ExchangeChangeData"""
    buf = bytearray()
    buf += encode_uint64(1, trans_id)
    for it in add_item_list:
        buf += encode_submessage(2, encode_item(**it) if isinstance(it, dict) else bytes(it))
    for it in del_item_list:
        buf += encode_submessage(3, encode_item(**it) if isinstance(it, dict) else bytes(it))
    buf += encode_int32(4, coins_delta)
    buf += encode_int32(5, gems_delta)
    if gop_gems_delta:
        buf += encode_int32(6, gop_gems_delta)
    buf += encode_uint32(7, reason)
    if sub_reason:
        buf += encode_uint32(8, sub_reason)
    if gop_gems:
        buf += encode_uint32(9, gop_gems)
    if gop_total_topup:
        buf += encode_uint64(10, gop_total_topup)
    if gop_total_free:
        buf += encode_uint64(11, gop_total_free)
    for ex in exchange_awards:
        buf += encode_submessage(12, encode_exchanged_award(**ex) if isinstance(ex, dict) else bytes(ex))
    buf += encode_bool(13, check_bundle)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Store & Purchase Protos (CSGetStoreReq/Res, StoreDesc, CSPurchaseReq/Res)
# ---------------------------------------------------------------------------

def decode_get_store_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSGetStoreReq"""
    if not raw_body:
        return {"account_id": 0, "lock_region": "DEFAULT", "language": "en"}
    fields = decode_proto(raw_body)
    return {
        "account_id": get_varint(fields, 1, 0),
        "lock_region": get_string(fields, 2, "DEFAULT"),
        "language": get_string(fields, 3, "en"),
    }


def encode_store_desc(
    store_id: int,
    sort_id: int,
    item_id: int,
    name: str,
    desc: str = "",
    coins_price: int = 0,
    gems_price: int = 0,
    tag_type: int = StoreTag.NONE,
    tag_value: int = 0,
    limited_purchase_times: int = 0,
    purchase_times: int = 0,
    is_new: bool = False,
    type_override: str = "",
    is_original_type_remain: bool = True,
    is_recommended: bool = False,
    image_url: str = "",
    language: str = "en",
    is_vfx: bool = False,
    real_image_url: str = "",
    link_to_web_store: str = "",
    discount_price: int = 0,
    discount_start_time: int = 0,
    discount_end_time: int = 0,
    added_time: str = "2019-01-01 00:00:00",
    expire_time: str = "2030-12-31 23:59:59",
) -> bytes:
    """proto.StoreDesc"""
    buf = bytearray()
    buf += encode_uint32(1, store_id)
    buf += encode_uint32(2, sort_id)
    buf += encode_uint32(3, item_id)
    buf += encode_string(4, added_time)
    buf += encode_string(5, expire_time)
    buf += encode_string(6, name)
    buf += encode_string(7, desc)
    buf += encode_uint32(8, coins_price)
    buf += encode_uint32(9, gems_price)
    buf += encode_uint32(10, tag_type)
    buf += encode_uint32(11, tag_value)
    buf += encode_uint32(12, limited_purchase_times)
    buf += encode_uint32(13, purchase_times)
    buf += encode_bool(14, is_new)
    buf += encode_string(15, type_override)
    buf += encode_bool(16, is_original_type_remain)
    buf += encode_bool(17, is_recommended)
    buf += encode_string(18, image_url)
    buf += encode_string(19, language)
    buf += encode_bool(20, is_vfx)
    buf += encode_string(21, real_image_url)
    buf += encode_string(22, link_to_web_store)
    buf += encode_uint32(23, discount_price)
    buf += encode_int64(24, discount_start_time)
    buf += encode_int64(25, discount_end_time)
    return bytes(buf)


def encode_get_store_res(store_items: Sequence[Dict[str, Any]]) -> bytes:
    """proto.CSGetStoreRes"""
    buf = bytearray()
    for item in store_items:
        buf += encode_submessage(1, encode_store_desc(**item) if isinstance(item, dict) else bytes(item))
    return bytes(buf)


def decode_purchase_req(raw_body: bytes) -> Dict[str, Any]:
    """
    proto.CSPurchaseReq (also serves as CSBuyItemReq alias for /BuyItem):
      1: uint32 store_item_id
      2: uint64 trans_id
      3: uint32 cnt
      4: uint32 currency_type (1=COINS, 2=GEMS)
      5: uint32 price
      6: uint32 voucher_id
      7: StorePromotionType promotion_type
    """
    if not raw_body:
        return {
            "store_item_id": 0,
            "trans_id": 1,
            "cnt": 1,
            "currency_type": CurrencyType.COINS,
            "price": 0,
            "voucher_id": 0,
            "promotion_type": StorePromotionType.NORMAL,
        }
    fields = decode_proto(raw_body)
    return {
        "store_item_id": get_varint(fields, 1, 0),
        "trans_id": get_varint(fields, 2, 1),
        "cnt": max(1, get_varint(fields, 3, 1)),
        "currency_type": get_varint(fields, 4, CurrencyType.COINS),
        "price": get_varint(fields, 5, 0),
        "voucher_id": get_varint(fields, 6, 0),
        "promotion_type": get_varint(fields, 7, StorePromotionType.NORMAL),
    }


decode_buy_item_req = decode_purchase_req


def encode_purchase_res(
    change_data: bytes,
    coins: int = 999999,
    gems: int = 999999,
) -> bytes:
    """proto.CSPurchaseRes (also serves as CSBuyItemRes alias for /BuyItem)."""
    buf = bytearray()
    buf += encode_submessage(1, change_data)
    buf += encode_uint32(2, coins)
    buf += encode_int32(3, gems)
    return bytes(buf)


encode_buy_item_res = encode_purchase_res


# ---------------------------------------------------------------------------
# Store Tabs (CSGetStoreTabRes / StoreTableDesc)
# ---------------------------------------------------------------------------

def encode_store_table_desc(
    table_type: int,
    table_name: str,
    mall_type: int = MallType.NORMAL,
    sort_id: int = 1,
    language: str = "en",
) -> bytes:
    """proto.StoreTableDesc"""
    buf = bytearray()
    buf += encode_uint32(1, table_type)
    buf += encode_string(2, language)
    buf += encode_string(3, table_name)
    buf += encode_uint32(4, mall_type)
    buf += encode_uint32(5, sort_id)
    return bytes(buf)


def encode_get_store_tab_res(store_tables: Sequence[Dict[str, Any]]) -> bytes:
    """proto.CSGetStoreTabRes"""
    buf = bytearray()
    for t in store_tables:
        buf += encode_submessage(1, encode_store_table_desc(**t) if isinstance(t, dict) else bytes(t))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Bundle Protos (CSGetBundleRes, BundleShow, CSOpenBundleReq/Res)
# ---------------------------------------------------------------------------

def encode_bundle_show_data(
    award_id: int,
    award_num: int = 1,
    award_type: int = AwardType.ITEM,
    is_preview: bool = True,
    preview_avatar: int = 0,
    image_url: str = "",
    return_type: int = AwardType.NONE,
    return_id: int = 0,
    return_num: int = 0,
) -> bytes:
    """proto.BundleShowData"""
    buf = bytearray()
    buf += encode_uint32(1, award_id)
    buf += encode_bool(2, is_preview)
    buf += encode_uint32(3, preview_avatar)
    buf += encode_uint32(4, award_num)
    buf += encode_uint32(5, award_type)
    if image_url:
        buf += encode_string(6, image_url)
    if return_type:
        buf += encode_uint32(7, return_type)
    if return_id:
        buf += encode_uint32(8, return_id)
    if return_num:
        buf += encode_uint32(9, return_num)
    return bytes(buf)


def encode_bundle_show(bundle_id: int, bundles: Sequence[Dict[str, Any]]) -> bytes:
    """proto.BundleShow"""
    buf = bytearray()
    buf += encode_uint32(1, bundle_id)
    for b in bundles:
        buf += encode_submessage(2, encode_bundle_show_data(**b) if isinstance(b, dict) else bytes(b))
    return bytes(buf)


def encode_get_bundle_res(bundle_shows: Sequence[Dict[str, Any]]) -> bytes:
    """proto.CSGetBundleRes"""
    buf = bytearray()
    for bs in bundle_shows:
        buf += encode_submessage(
            1,
            encode_bundle_show(bs["id"], bs.get("bundles", ())) if isinstance(bs, dict) else bytes(bs),
        )
    return bytes(buf)


def decode_open_bundle_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSOpenBundleReq"""
    if not raw_body:
        return {"item_id": 0}
    fields = decode_proto(raw_body)
    return {"item_id": get_varint(fields, 1, 0)}


def encode_open_bundle_res(
    change_data: bytes,
    transfer_to_items: Sequence[Dict[str, Any]] = (),
) -> bytes:
    """proto.CSOpenBundleRes"""
    buf = bytearray()
    buf += encode_submessage(1, change_data)
    for aw in transfer_to_items:
        buf += encode_submessage(2, encode_award_desc(**aw) if isinstance(aw, dict) else bytes(aw))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Treasure Box / Weapon Crate Protos
# ---------------------------------------------------------------------------

def encode_treasure_box_show_data(
    award_id: int,
    award_num: int = 1,
    award_type: int = AwardType.ITEM,
    is_preview: bool = True,
    preview_avatar: int = 0,
    is_big_reward: bool = False,
    icon: str = "",
    reward_level: int = 1,
) -> bytes:
    """proto.TreasureBoxShowData"""
    buf = bytearray()
    buf += encode_uint32(1, award_id)
    buf += encode_bool(2, is_preview)
    buf += encode_uint32(3, preview_avatar)
    buf += encode_bool(4, is_big_reward)
    buf += encode_uint32(5, award_num)
    buf += encode_uint32(6, award_type)
    if icon:
        buf += encode_string(7, icon)
    buf += encode_uint32(8, reward_level)
    return bytes(buf)


def encode_treasure_box_show(box_id: int, treasure_boxes: Sequence[Dict[str, Any]]) -> bytes:
    """proto.TreasureBoxShow"""
    buf = bytearray()
    buf += encode_uint32(1, box_id)
    for tb in treasure_boxes:
        buf += encode_submessage(2, encode_treasure_box_show_data(**tb) if isinstance(tb, dict) else bytes(tb))
    return bytes(buf)


def encode_crate_treasure_group_desc(
    group_id: int,
    num_group: int = 1,
    is_repeatable: bool = False,
    icon: str = "",
) -> bytes:
    """proto.CrateTreasureGroupDesc"""
    buf = bytearray()
    buf += encode_uint32(1, group_id)
    buf += encode_uint32(2, num_group)
    buf += encode_bool(3, is_repeatable)
    if icon:
        buf += encode_string(4, icon)
    return bytes(buf)


def encode_crate_descs(crate_id: int, treasure_group: Sequence[Dict[str, Any]]) -> bytes:
    """proto.CrateDescs"""
    buf = bytearray()
    buf += encode_uint32(1, crate_id)
    for grp in treasure_group:
        buf += encode_submessage(
            2,
            encode_crate_treasure_group_desc(**grp) if isinstance(grp, dict) else bytes(grp),
        )
    return bytes(buf)


def encode_get_treasure_box_res(
    boxes: Sequence[Dict[str, Any]],
    crates: Sequence[Dict[str, Any]] = (),
) -> bytes:
    """proto.CSGetTreasureBoxRes"""
    buf = bytearray()
    for bx in boxes:
        buf += encode_submessage(
            1,
            encode_treasure_box_show(bx["id"], bx.get("treasure_boxes", ())) if isinstance(bx, dict) else bytes(bx),
        )
    for cr in crates:
        buf += encode_submessage(
            2,
            encode_crate_descs(cr["crate_id"], cr.get("treasure_group", ())) if isinstance(cr, dict) else bytes(cr),
        )
    return bytes(buf)


def decode_open_treasure_box_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSOpenTreasureBoxReq"""
    if not raw_body:
        return {
            "treasure_id": 0,
            "trans_id": 1,
            "box_type": BoxType.NORMAL,
            "can_get_unique": True,
            "item_cnt": 1,
            "is_crate_treasure": False,
        }
    fields = decode_proto(raw_body)
    return {
        "treasure_id": get_varint(fields, 1, 0),
        "trans_id": get_varint(fields, 2, 1),
        "box_type": get_varint(fields, 3, BoxType.NORMAL),
        "can_get_unique": get_bool(fields, 4, True),
        "item_cnt": max(1, get_varint(fields, 5, 1)),
        "is_crate_treasure": get_bool(fields, 6, False),
    }


def encode_open_treasure_box_res(
    awards: bytes,
    left_box_num: int = 0,
    exchanged_awards: Sequence[Dict[str, Any]] = (),
) -> bytes:
    """proto.CSOpenTreasureBoxRes"""
    buf = bytearray()
    buf += encode_submessage(1, awards)
    buf += encode_uint32(2, left_box_num)
    for ex in exchanged_awards:
        buf += encode_submessage(3, encode_exchanged_award(**ex) if isinstance(ex, dict) else bytes(ex))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Gift Store Protos
# ---------------------------------------------------------------------------

def encode_get_gift_store_res(
    store_id: int = 1,
    open_time: int = 1546300800,
    close_time: int = 1924991999,
    is_time_show: bool = False,
    giver_level: int = 1,
    receiver_level: int = 1,
    gift_time_limited: int = 99,
    gift_num_limited: int = 99,
) -> bytes:
    """proto.CSGetGiftStoreRes"""
    buf = bytearray()
    buf += encode_uint32(1, store_id)
    buf += encode_uint32(2, open_time)
    buf += encode_uint32(3, close_time)
    buf += encode_bool(4, is_time_show)
    buf += encode_uint32(5, giver_level)
    buf += encode_uint32(6, receiver_level)
    buf += encode_uint32(7, gift_time_limited)
    buf += encode_uint32(8, gift_num_limited)
    return bytes(buf)


def encode_gift_item(
    commodity_id: int,
    sort_id: int,
    item_id: int,
    coins_price: int = 0,
    gems_price: int = 0,
    tag_type: int = StoreTag.NONE,
    tag_value: int = 0,
    type_override: int = 0,
    is_original_type_remain: bool = True,
    is_exclusive: bool = False,
    image_url: str = "",
    is_quick_gift_recommended: bool = False,
) -> bytes:
    """proto.GiftItem"""
    buf = bytearray()
    buf += encode_uint32(1, commodity_id)
    buf += encode_uint32(2, sort_id)
    buf += encode_uint32(3, item_id)
    buf += encode_uint32(4, coins_price)
    buf += encode_uint32(5, gems_price)
    buf += encode_uint32(6, tag_type)
    buf += encode_uint32(7, tag_value)
    buf += encode_uint32(8, type_override)
    buf += encode_bool(9, is_original_type_remain)
    buf += encode_bool(10, is_exclusive)
    if image_url:
        buf += encode_string(11, image_url)
    buf += encode_bool(12, is_quick_gift_recommended)
    return bytes(buf)


def encode_get_gift_store_details_res(
    store_id: int = 1,
    items: Sequence[Dict[str, Any]] = (),
    send_gift_times_today: int = 0,
) -> bytes:
    """proto.CSGetGiftStoreDetailsRes"""
    buf = bytearray()
    buf += encode_uint32(1, store_id)
    for it in items:
        buf += encode_submessage(2, encode_gift_item(**it) if isinstance(it, dict) else bytes(it))
    buf += encode_uint32(3, send_gift_times_today)
    return bytes(buf)


def decode_send_gift_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSSendGiftReq (tag 1 is packed uint64[])."""
    if not raw_body:
        return {
            "receiver_account_ids": [],
            "buddy_type": BuddyType.FRIEND,
            "commodity_id": 0,
            "message_content": "",
            "currency_type": CurrencyType.GEMS,
            "clan_id": 0,
            "commodity_cnt": 1,
            "voucher_id": 0,
        }
    fields = decode_proto(raw_body)
    return {
        "receiver_account_ids": get_packed_varints(fields, 1),
        "buddy_type": get_varint(fields, 2, BuddyType.FRIEND),
        "commodity_id": get_varint(fields, 3, 0),
        "message_content": get_string(fields, 4, ""),
        "currency_type": get_varint(fields, 5, CurrencyType.GEMS),
        "clan_id": get_varint(fields, 6, 0),
        "commodity_cnt": max(1, get_varint(fields, 7, 1)),
        "voucher_id": get_varint(fields, 8, 0),
    }


def encode_send_gift_res(
    remove_ids: Iterable[int] = (),
    send_gift_times_today: int = 1,
) -> bytes:
    """proto.CSSendGiftRes (tag 1 is packed uint64[])."""
    buf = bytearray()
    rem = list(remove_ids or ())
    if rem:
        buf += encode_packed_uint64(1, rem)
    buf += encode_uint32(2, send_gift_times_today)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Exchange Store Protos
# ---------------------------------------------------------------------------

def decode_get_exchange_store_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSGetExchangeStoreReq"""
    if not raw_body:
        return {"language": "en"}
    fields = decode_proto(raw_body)
    return {"language": get_string(fields, 1, "en") or "en"}


def encode_exchange_store_desc(
    store_id: int,
    store_name: str,
    open_time: str = "2019-01-01 00:00:00",
    close_time: str = "2030-12-31 23:59:59",
    open_time_stamp: int = 1546300800,
    close_time_stamp: int = 1924991999,
    is_show_time: bool = False,
    check_bundle_switch: bool = False,
    need_clan: bool = False,
) -> bytes:
    """proto.ExchangeStoreDesc"""
    buf = bytearray()
    buf += encode_uint32(1, store_id)
    buf += encode_string(2, store_name)
    buf += encode_string(3, open_time)
    buf += encode_string(4, close_time)
    buf += encode_uint32(5, open_time_stamp)
    buf += encode_uint32(6, close_time_stamp)
    buf += encode_bool(7, is_show_time)
    buf += encode_bool(8, check_bundle_switch)
    buf += encode_bool(9, need_clan)
    return bytes(buf)


def encode_exchange_store_item_desc(
    store_id: int,
    commodity_id: int,
    sort_id: int,
    name: str,
    item_id: int,
    currency_id: int = 0,
    currency_name: str = "FF Token",
    currency_price: int = 10,
    tag_type: int = StoreTag.NONE,
    tag_value: int = 0,
    limited_purchase_times: int = 99,
    purchase_times: int = 0,
    added_time: str = "2019-01-01 00:00:00",
    expire_time: str = "2030-12-31 23:59:59",
    language: str = "en",
    image_url: str = "",
    real_image_url: str = "",
    gems_cost: int = 0,
    min_clan_level: int = 0,
) -> bytes:
    """proto.ExchangeStoreItemDesc"""
    buf = bytearray()
    buf += encode_uint32(1, store_id)
    buf += encode_uint32(2, commodity_id)
    buf += encode_uint32(3, sort_id)
    buf += encode_string(4, name)
    buf += encode_uint32(5, item_id)
    buf += encode_uint32(6, currency_id)
    buf += encode_string(7, currency_name)
    buf += encode_uint32(8, currency_price)
    buf += encode_uint32(9, tag_type)
    buf += encode_uint32(10, tag_value)
    buf += encode_uint32(11, limited_purchase_times)
    buf += encode_uint32(12, purchase_times)
    buf += encode_string(13, added_time)
    buf += encode_string(14, expire_time)
    buf += encode_string(15, language)
    if image_url:
        buf += encode_string(16, image_url)
    if real_image_url:
        buf += encode_string(17, real_image_url)
    buf += encode_uint32(18, gems_cost)
    if min_clan_level:
        buf += encode_uint32(19, min_clan_level)
    return bytes(buf)


def encode_exchange_store(
    exchange_store_desc: Dict[str, Any],
    exchange_store_items: Sequence[Dict[str, Any]],
) -> bytes:
    """proto.ExchangeStore"""
    buf = bytearray()
    desc_bytes = (
        encode_exchange_store_desc(**exchange_store_desc)
        if isinstance(exchange_store_desc, dict)
        else bytes(exchange_store_desc)
    )
    buf += encode_submessage(1, desc_bytes)
    for it in exchange_store_items:
        buf += encode_submessage(
            2,
            encode_exchange_store_item_desc(**it) if isinstance(it, dict) else bytes(it),
        )
    return bytes(buf)


def encode_get_exchange_store_res(exchange_stores: Sequence[Dict[str, Any]]) -> bytes:
    """proto.CSGetExchangeStoreRes"""
    buf = bytearray()
    for st in exchange_stores:
        if isinstance(st, dict):
            buf += encode_submessage(
                1,
                encode_exchange_store(
                    st["exchange_store_desc"],
                    st.get("exchange_store_items", ()),
                ),
            )
        else:
            buf += encode_submessage(1, bytes(st))
    return bytes(buf)


def decode_exchange_store_purchase_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSExchangeStorePurchaseReq"""
    if not raw_body:
        return {
            "store_id": 0,
            "commodity_id": 0,
            "trans_id": 1,
            "cnt": 1,
            "currency_id": 0,
            "currency_price": 0,
            "gems_cost": 0,
        }
    fields = decode_proto(raw_body)
    return {
        "store_id": get_varint(fields, 1, 0),
        "commodity_id": get_varint(fields, 2, 0),
        "trans_id": get_varint(fields, 3, 1),
        "cnt": max(1, get_varint(fields, 4, 1)),
        "currency_id": get_varint(fields, 5, 0),
        "currency_price": get_varint(fields, 6, 0),
        "gems_cost": get_varint(fields, 7, 0),
    }


def encode_exchange_store_purchase_res(
    change_data: bytes,
    purchase_times: int = 1,
) -> bytes:
    """proto.CSExchangeStorePurchaseRes"""
    buf = bytearray()
    buf += encode_submessage(1, change_data)
    buf += encode_uint32(2, purchase_times)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Discount Store Protos
# ---------------------------------------------------------------------------

def encode_discount_store_desc(
    store_id: int,
    loop_id: int,
    refresh_id: int,
    item_id: int,
    coins_price: int = 0,
    gems_price: int = 0,
    discount_value: float = 0.5,
    limited_purchase_times: int = 1,
    purchase_times: int = 0,
) -> bytes:
    """proto.DiscountStoreDesc"""
    buf = bytearray()
    buf += encode_uint32(1, store_id)
    buf += encode_uint32(2, loop_id)
    buf += encode_uint32(3, refresh_id)
    buf += encode_uint32(4, item_id)
    buf += encode_uint32(5, coins_price)
    buf += encode_uint32(6, gems_price)
    buf += encode_float(7, discount_value)
    buf += encode_uint32(8, limited_purchase_times)
    buf += encode_uint32(9, purchase_times)
    return bytes(buf)


def encode_get_discount_store_desc_res(discount_stores: Sequence[Dict[str, Any]]) -> bytes:
    """proto.CSGetDiscountStoreDescRes"""
    buf = bytearray()
    for ds in discount_stores:
        buf += encode_submessage(
            1,
            encode_discount_store_desc(**ds) if isinstance(ds, dict) else bytes(ds),
        )
    return bytes(buf)


def decode_discount_store_purchase_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSDiscountStorePurchaseReq"""
    if not raw_body:
        return {
            "store_id": 0,
            "item_id": 0,
            "cnt": 1,
            "currency_type": CurrencyType.GEMS,
            "price": 0,
            "voucher_id": 0,
        }
    fields = decode_proto(raw_body)
    return {
        "store_id": get_varint(fields, 1, 0),
        "item_id": get_varint(fields, 2, 0),
        "cnt": max(1, get_varint(fields, 3, 1)),
        "currency_type": get_varint(fields, 4, CurrencyType.GEMS),
        "price": get_varint(fields, 5, 0),
        "voucher_id": get_varint(fields, 6, 0),
    }


def encode_discount_store_purchase_res(
    change_data: bytes,
    purchase_count: int = 1,
) -> bytes:
    """proto.CSDiscountStorePurchaseRes"""
    buf = bytearray()
    buf += encode_submessage(1, change_data)
    buf += encode_uint32(2, purchase_count)
    return bytes(buf)


# ---------------------------------------------------------------------------
# PayBundleWindow & Installment Store Protos
# ---------------------------------------------------------------------------

def encode_pay_bundle_window_desc(
    id: int,
    index_id: int,
    price_item_id: int = 0,
    price: float = 0.99,
    discount_price_rebate_id: int = 0,
    discount_price_item_id: int = 0,
    discount_price: float = 0.0,
    rebate_percentage: int = 0,
    limited_purchase: int = 1,
    purchase_times: int = 0,
    awards: Sequence[Dict[str, Any]] = (),
) -> bytes:
    """proto.PayBundleWindowDesc"""
    buf = bytearray()
    buf += encode_uint32(1, id)
    buf += encode_uint32(2, index_id)
    buf += encode_uint32(3, price_item_id)
    buf += encode_float(4, price)
    buf += encode_uint32(5, discount_price_rebate_id)
    buf += encode_uint32(6, discount_price_item_id)
    buf += encode_float(7, discount_price)
    buf += encode_uint32(8, rebate_percentage)
    buf += encode_uint32(9, limited_purchase)
    buf += encode_uint32(10, purchase_times)
    for aw in awards:
        buf += encode_submessage(11, encode_award_desc(**aw) if isinstance(aw, dict) else bytes(aw))
    return bytes(buf)


def encode_get_pay_bundle_window_desc_res(
    pay_bundle_windows: Sequence[Dict[str, Any]] = (),
    next_refresh_time: Optional[int] = None,
) -> bytes:
    """proto.CSGetPayBundleWindowDescRes"""
    if next_refresh_time is None:
        next_refresh_time = int(time.time()) + 86400
    buf = bytearray()
    for w in pay_bundle_windows:
        buf += encode_submessage(1, encode_pay_bundle_window_desc(**w) if isinstance(w, dict) else bytes(w))
    buf += encode_uint32(2, next_refresh_time)
    return bytes(buf)


def decode_pay_bundle_window_purchase_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSPayBundleWindowPurchaseReq"""
    if not raw_body:
        return {"login_token": "", "rebate_card_id": 0}
    fields = decode_proto(raw_body)
    return {
        "login_token": get_string(fields, 1, ""),
        "rebate_card_id": get_varint(fields, 2, 0),
    }


def encode_pay_bundle_window_purchase_res(
    awards: Sequence[Dict[str, Any]] = (),
    purchase_times: int = 1,
) -> bytes:
    """proto.CSPayBundleWindowPurchaseRes"""
    buf = bytearray()
    for aw in awards:
        buf += encode_submessage(1, encode_award_desc(**aw) if isinstance(aw, dict) else bytes(aw))
    buf += encode_uint32(2, purchase_times)
    return bytes(buf)


def decode_get_installment_store_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSGetInstallmentStoreDescReq"""
    if not raw_body:
        return {"language": "en"}
    fields = decode_proto(raw_body)
    return {"language": get_string(fields, 1, "en") or "en"}


def encode_installment_store_desc(
    sort_id: int,
    item_id: int,
    added_time: int = 1546300800,
    expire_time: int = 1924991999,
    gems_price: int = 499,
    deposit_price: int = 99,
    installment_type: int = InstallmentType.DAY_7,
    installment_term: int = 4,
    promp_day: int = 7,
    language: str = "en",
    image_url: str = "",
) -> bytes:
    """proto.InstallmentStoreDesc"""
    buf = bytearray()
    buf += encode_uint32(1, sort_id)
    buf += encode_uint32(2, item_id)
    buf += encode_int64(3, added_time)
    buf += encode_int64(4, expire_time)
    buf += encode_uint32(5, gems_price)
    buf += encode_uint32(6, deposit_price)
    buf += encode_uint32(7, installment_type)
    buf += encode_uint32(8, installment_term)
    buf += encode_uint32(9, promp_day)
    buf += encode_string(10, language)
    if image_url:
        buf += encode_string(11, image_url)
    return bytes(buf)


def encode_get_installment_store_desc_res(
    installment_stores: Sequence[Dict[str, Any]] = (),
) -> bytes:
    """proto.CSGetInstallmentStoreDescRes"""
    buf = bytearray()
    for st in installment_stores:
        buf += encode_submessage(
            1,
            encode_installment_store_desc(**st) if isinstance(st, dict) else bytes(st),
        )
    return bytes(buf)


def decode_installment_purchase_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSInstallmentPurchaseReq"""
    if not raw_body:
        return {"item_id": 0, "price": 0, "is_one_time_payment": True}
    fields = decode_proto(raw_body)
    return {
        "item_id": get_varint(fields, 1, 0),
        "price": get_varint(fields, 2, 0),
        "is_one_time_payment": get_bool(fields, 3, True),
    }


def encode_installment_purchase_res(change_data: bytes) -> bytes:
    """proto.CSInstallmentPurchaseRes"""
    return encode_submessage(1, change_data)


def encode_get_installment_items_res(items: Sequence[Dict[str, Any]] = ()) -> bytes:
    """proto.CSGetInstallmentItemsRes"""
    buf = bytearray()
    for it in items:
        buf += encode_submessage(1, encode_item(**it) if isinstance(it, dict) else bytes(it))
    return bytes(buf)


# ---------------------------------------------------------------------------
# Default Free Fire 1.39 Store Catalogs (Bundles, Character Bundles,
# Weapon Crates, Fashion, Collections, Pets, Gift, Exchange, Discount)
# ---------------------------------------------------------------------------

def default_store_tabs() -> List[Dict[str, Any]]:
    """Default Store tabs for CSGetStoreTabRes / LoginDescRes tag 20."""
    return [
        {"table_type": MallTabType.NEW_ITEM, "table_name": "New", "mall_type": MallType.NORMAL, "sort_id": 1},
        {"table_type": MallTabType.BUNDLE, "table_name": "Bundles", "mall_type": MallType.NORMAL, "sort_id": 2},
        {"table_type": MallTabType.AVATAR, "table_name": "Characters", "mall_type": MallType.NORMAL, "sort_id": 3},
        {"table_type": MallTabType.CLOTHES, "table_name": "Fashion", "mall_type": MallType.NORMAL, "sort_id": 4},
        {"table_type": MallTabType.COLLECTION, "table_name": "Collections", "mall_type": MallType.NORMAL, "sort_id": 5},
        {"table_type": MallTabType.PET, "table_name": "Pets", "mall_type": MallType.NORMAL, "sort_id": 6},
        {"table_type": MallTabType.TREASURE_BOX, "table_name": "Crates", "mall_type": MallType.BOX, "sort_id": 7},
        {"table_type": MallTabType.WEAPON, "table_name": "Armory", "mall_type": MallType.WEAPON, "sort_id": 8},
        {"table_type": MallTabType.DISCOUNT, "table_name": "Daily Special", "mall_type": MallType.NORMAL, "sort_id": 9},
    ]


# Bundle definitions: real Bundle.csv item_id -> list of contained award items + optional character avatar_id
BUNDLE_DEFINITIONS: Dict[int, Dict[str, Any]] = {
    # Featured Outfit Bundles (real Item.csv / Bundle.csv 700xxxxxx)
    700000001: {
        "name": "Streetwear Legend Bundle",
        "items": [500000001, 203000060, 205000035, 209000012, 400000002],
        "preview_avatar": 102000004,
    },
    700000002: {
        "name": "Crimson Samurai Bundle",
        "items": [203000096, 204000068, 205000051],
        "preview_avatar": 102000004,
    },
    700000003: {
        "name": "Cyber Recon Bundle",
        "items": [203000056, 204000043, 205000026],
        "preview_avatar": 101000001,
    },
    700000004: {
        "name": "Shadow Strike Bundle",
        "items": [203000058, 204000045, 205000028],
        "preview_avatar": 102000004,
    },
    # Character Bundles (real Bundle.csv 700/710xxxxxx + real Avatar.csv 101/102xxxxxx)
    700000270: {
        "name": "Moco Hacker Bundle",
        "avatar_id": 101000011,
        "preview_avatar": 101000011,
        "items": [211000056, 203000251, 204000143, 205000119, 812000001],
    },
    700000271: {
        "name": "Hayato Bushido Bundle",
        "avatar_id": 102000012,
        "preview_avatar": 102000012,
        "items": [211000081, 203000274, 204000157, 205000126, 812000001],
    },
    710000162: {
        "name": "Wukong Monkey King Bundle",
        "avatar_id": 102000011,
        "preview_avatar": 102000011,
        "items": [203000353, 204000200, 205000167],
    },
    710000309: {
        "name": "Laura Sharp Shooter Bundle",
        "avatar_id": 101000012,
        "preview_avatar": 101000012,
        "items": [203000455, 204000263, 205000221],
    },
    710000347: {
        "name": "Rafael Dead Silent Bundle",
        "avatar_id": 102000013,
        "preview_avatar": 102000013,
        "items": [203000528, 204000310, 205000266, 812000001],
    },
    710000386: {
        "name": "A124 Thrill of Battle Bundle",
        "avatar_id": 101000013,
        "preview_avatar": 101000013,
        "items": [203000566, 204000340, 205000294, 812000001],
    },
}


# Treasure Box / Weapon Crate definitions: real Item.csv 400xxxxxx -> real CollectionWeapon.csv 907xxxxxx
TREASURE_BOX_DEFINITIONS: Dict[int, Dict[str, Any]] = {
    400000053: {
        "name": "AK Weapon Loot Crate",
        "is_crate": True,
        "rewards": [
            {"award_id": 907000013, "is_big_reward": True, "reward_level": 4},
            {"award_id": 907000001, "is_big_reward": True, "reward_level": 3},
            {"award_id": 907000002, "is_big_reward": False, "reward_level": 2},
            {"award_id": 907000005, "is_big_reward": False, "reward_level": 1},
        ],
    },
    400000054: {
        "name": "M4A1 Weapon Loot Crate",
        "is_crate": True,
        "rewards": [
            {"award_id": 907000010, "is_big_reward": True, "reward_level": 4},
            {"award_id": 907000014, "is_big_reward": True, "reward_level": 3},
            {"award_id": 907000005, "is_big_reward": False, "reward_level": 2},
            {"award_id": 907000002, "is_big_reward": False, "reward_level": 1},
        ],
    },
    400000025: {
        "name": "Camo Weapon Loot Crate",
        "is_crate": True,
        "rewards": [
            {"award_id": 907000001, "is_big_reward": True, "reward_level": 4},
            {"award_id": 907000002, "is_big_reward": True, "reward_level": 3},
            {"award_id": 907000010, "is_big_reward": False, "reward_level": 2},
            {"award_id": 907000013, "is_big_reward": False, "reward_level": 1},
        ],
    },
    400000044: {
        "name": "Power Weapon Loot Crate",
        "is_crate": True,
        "rewards": [
            {"award_id": 907000014, "is_big_reward": True, "reward_level": 4},
            {"award_id": 907000013, "is_big_reward": True, "reward_level": 3},
            {"award_id": 907000005, "is_big_reward": False, "reward_level": 2},
            {"award_id": 907000001, "is_big_reward": False, "reward_level": 1},
        ],
    },
    400000001: {
        "name": "Booyah Fashion Supply Box",
        "is_crate": False,
        "rewards": [
            {"award_id": 203000060, "is_big_reward": True, "reward_level": 4},
            {"award_id": 204000068, "is_big_reward": False, "reward_level": 3},
            {"award_id": 205000035, "is_big_reward": False, "reward_level": 2},
            {"award_id": 904000001, "is_big_reward": False, "reward_level": 2},
        ],
    },
}


def default_bundle_shows() -> List[Dict[str, Any]]:
    """Build CSGetBundleRes entries matching BUNDLE_DEFINITIONS."""
    shows: List[Dict[str, Any]] = []
    for bid, meta in BUNDLE_DEFINITIONS.items():
        shows.append({
            "id": bid,
            "bundles": [
                {
                    "award_id": item_id,
                    "is_preview": True,
                    "preview_avatar": meta.get("preview_avatar", 0),
                    "award_num": 1,
                    "award_type": AwardType.ITEM,
                }
                for item_id in meta["items"]
            ],
        })
    return shows


def default_treasure_boxes() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build CSGetTreasureBoxRes (boxes, crates) matching TREASURE_BOX_DEFINITIONS."""
    boxes: List[Dict[str, Any]] = []
    crates: List[Dict[str, Any]] = []
    for box_id, meta in TREASURE_BOX_DEFINITIONS.items():
        boxes.append({
            "id": box_id,
            "treasure_boxes": [
                {
                    "award_id": r["award_id"],
                    "is_preview": True,
                    "preview_avatar": 0,
                    "is_big_reward": r["is_big_reward"],
                    "award_num": 1,
                    "award_type": AwardType.ITEM,
                    "reward_level": r["reward_level"],
                }
                for r in meta["rewards"]
            ],
        })
        if meta.get("is_crate"):
            crates.append({
                "crate_id": box_id,
                "treasure_group": [
                    {"group_id": 1, "num_group": 1, "is_repeatable": True},
                ],
            })
    return boxes, crates


def default_store_catalog() -> List[Dict[str, Any]]:
    """
    Rich catalog of StoreDesc entries covering:
    - Featured Bundles
    - Character Bundles
    - Weapon Crates & Weapon Skins
    - Fashion / Clothes (Tops, Bottoms, Shoes, Hats/Masks)
    - Collections (Backpacks, Parachutes, Surfboards, Loot Boxes, Banners, Avatars)
    - Pets & Pet Skins
    """
    now = int(time.time())
    disc_start = now - 3600
    disc_end = now + 86400 * 30
    items: List[Dict[str, Any]] = []
    sid = 1001
    sort = 1

    def add(
        item_id: int,
        name: str,
        desc: str,
        *,
        coins_price: int = 0,
        gems_price: int = 0,
        tag_type: int = StoreTag.NONE,
        tag_value: int = 0,
        type_override: str = "",
        is_new: bool = False,
        is_recommended: bool = False,
        discount_price: int = 0,
    ) -> None:
        nonlocal sid, sort
        items.append({
            "store_id": sid,
            "sort_id": sort,
            "item_id": item_id,
            "name": name,
            "desc": desc,
            "coins_price": coins_price,
            "gems_price": gems_price,
            "tag_type": tag_type,
            "tag_value": tag_value,
            "limited_purchase_times": 0,
            "purchase_times": 0,
            "is_new": is_new,
            "type_override": type_override,
            "is_original_type_remain": True,
            "is_recommended": is_recommended,
            "discount_price": discount_price,
            "discount_start_time": disc_start if discount_price else 0,
            "discount_end_time": disc_end if discount_price else 0,
        })
        sid += 1
        sort += 1

    # 1. Featured Bundles (Tab: BUNDLE=6, NEW_ITEM=4, EXCLUSIVE=2) — real Bundle.csv IDs
    add(700000001, "Streetwear Legend Bundle", "Full featured hip-hop outfit set",
        gems_price=899, coins_price=15000, tag_type=StoreTag.HOT,
        type_override=f"{MallTabType.BUNDLE},{MallTabType.NEW_ITEM}", is_new=True, is_recommended=True)
    add(700000002, "Crimson Samurai Bundle", "Elite red samurai armor bundle",
        gems_price=1199, tag_type=StoreTag.HOT,
        type_override=f"{MallTabType.BUNDLE},{MallTabType.EXCLUSIVE}", is_new=True, is_recommended=True)
    add(700000003, "Cyber Recon Bundle", "Tactical cybernetic combat set",
        gems_price=999, tag_type=StoreTag.DISCOUNT, tag_value=20, discount_price=799,
        type_override=f"{MallTabType.BUNDLE},{MallTabType.DISCOUNT}", is_recommended=True)
    add(700000004, "Shadow Strike Bundle", "Stealth assassin outfit pack",
        gems_price=799, coins_price=12000, tag_type=StoreTag.NEW,
        type_override=f"{MallTabType.BUNDLE},{MallTabType.NEW_ITEM}", is_new=True)

    # 2. Character Bundles (Tab: AVATAR=7, BUNDLE=6) — real Bundle.csv IDs
    char_bundles = [
        (700000270, "Moco Hacker Bundle", "Unlocks Moco + Cybernetic Set", 499, 8000),
        (700000271, "Hayato Bushido Bundle", "Unlocks Hayato + Bushido Outfit", 499, 8000),
        (710000162, "Wukong Monkey King Bundle", "Unlocks Wukong + Royal Armor", 599, 10000),
        (710000309, "Laura Sharp Shooter Bundle", "Unlocks Laura + Special Agent Set", 499, 8000),
        (710000347, "Rafael Dead Silent Bundle", "Unlocks Rafael + Assassin Set", 599, 10000),
        (710000386, "A124 Thrill of Battle Bundle", "Unlocks A124 + Android Set", 599, 10000),
    ]
    for bid, cname, cdesc, gprice, cprice in char_bundles:
        add(bid, cname, cdesc, coins_price=cprice, gems_price=gprice,
            tag_type=StoreTag.HOT, type_override=f"{MallTabType.AVATAR},{MallTabType.BUNDLE}",
            is_recommended=True)

    # 3. Weapon Crates & Treasure Boxes (Tab: TREASURE_BOX=5, WEAPON=9) — real Item.csv 400xxxxxx IDs
    add(400000053, "AK Weapon Loot Crate", "Chance to drop AK weapon skins",
        gems_price=40, coins_price=1000, tag_type=StoreTag.HOT,
        type_override=f"{MallTabType.TREASURE_BOX},{MallTabType.WEAPON}", is_recommended=True)
    add(400000054, "M4A1 Weapon Loot Crate", "Chance to drop M4A1 weapon skins",
        gems_price=40, coins_price=1000, tag_type=StoreTag.NEW,
        type_override=f"{MallTabType.TREASURE_BOX},{MallTabType.WEAPON}", is_new=True)
    add(400000025, "Camo Weapon Loot Crate", "Chance to drop Camo weapon finishes",
        gems_price=35, coins_price=900, tag_type=StoreTag.HOT,
        type_override=f"{MallTabType.TREASURE_BOX},{MallTabType.WEAPON}")
    add(400000044, "Power Weapon Loot Crate", "Chance to drop Power weapon skins",
        gems_price=35, coins_price=900, tag_type=StoreTag.DISCOUNT, tag_value=25, discount_price=26,
        type_override=f"{MallTabType.TREASURE_BOX},{MallTabType.WEAPON}")
    add(400000001, "Booyah Fashion Supply Box", "Contains rare tops, bottoms, and backpacks",
        gems_price=25, coins_price=500, tag_type=StoreTag.NEW,
        type_override=f"{MallTabType.TREASURE_BOX}")

    # 4. Direct Weapon Skins (Tab: WEAPON=9) — real CollectionWeapon.csv 907000xxx IDs
    weapon_skins = [
        (907000013, "AK - Flaming Dragon", 499, 9000),
        (907000014, "SCAR - Titan", 499, 9000),
        (907000010, "M4A1 - Scorching Sands", 399, 7500),
        (907000005, "AWM - Cheetah", 399, 7500),
        (907000001, "USP - Urban Camo", 299, 6000),
    ]
    for wid, wname, wg, wc in weapon_skins:
        add(wid, wname, "Permanent weapon finish",
            coins_price=wc, gems_price=wg, tag_type=StoreTag.HOT,
            type_override=f"{MallTabType.WEAPON}")

    # 5. Fashion / Clothes (Tab: CLOTHES=8) — real Item.csv / Clothes.csv IDs
    fashion_defs = [
        (203000001, "Booyah Varsity Jacket", "Classic survivor top", 1500, 199),
        (203000060, "Tactical Hooded Top", "Lightweight combat hoodie", 2000, 249),
        (204000001, "Urban Cargo Pants", "Durable battleground trousers", 1200, 149),
        (204000043, "Neon Runner Jeans", "Stylish slim-fit pants", 1500, 199),
        (205000001, "Air Dash Sneakers", "High-traction combat kicks", 900, 99),
        (205000035, "Shadow Combat Boots", "Reinforced tactical boots", 1100, 129),
        (211000001, "Skull Bandana Mask", "Signature survivor face mask", 2500, 299),
        (211000056, "Cyber Visor Cap", "Futuristic street headwear", 1800, 199),
    ]
    for fid, fname, fdesc, fc, fg in fashion_defs:
        add(fid, fname, fdesc, coins_price=fc, gems_price=fg,
            type_override=f"{MallTabType.CLOTHES}")

    # 6. Collections (Tab: COLLECTION=11) — real Item.csv 90x / 209 IDs
    collection_defs = [
        (904000001, "Dragon Scale Backpack", "Level 1-3 themed backpack skin", 2500, 299),
        (904000002, "Cyber Wing Pack", "Futuristic combat backpack", 2500, 299),
        (209000002, "Phoenix Parachute", "Drop in style", 1800, 199),
        (906000001, "Lightning Surfboard", "High-speed skyboard", 1800, 199),
        (903000001, "Golden Trophy Loot Box", "Custom elimination crate", 1500, 149),
        (909000001, "Booyah Victory Emote", "Lobby & in-game emote", 1500, 149),
        (908000001, "Sports Car Finish", "Custom vehicle finish", 2000, 199),
        (901000010, "Barbosa Elite Banner", "Profile banner", 500, 49),
        (902000010, "Legend Emblem Avatar", "Profile avatar", 500, 49),
    ]
    for cid, cname, cdesc, cc, cg in collection_defs:
        add(cid, cname, cdesc, coins_price=cc, gems_price=cg,
            type_override=f"{MallTabType.COLLECTION}")

    # 7. Pets & Pet Skins (Tab: PET=12) — real Pet.csv & PetSkin.csv IDs
    pet_defs = [
        (1300000001, "Kitty", "Loyal feline companion", 3000, 299),
        (1300000011, "Mechanical Pup", "Robotic guard dog", 3500, 349),
        (1300000021, "Night Panther", "Weight training panther pet", 5000, 499),
        (1300000031, "Detective Panda", "HP-on-kill panda pet", 5999, 599),
        (1300000041, "Shiba", "Mushroom tracker Shiba", 4500, 449),
        (1310000002, "Ocelot Kitty Skin", "Skin for Kitty", 1500, 149),
        (1310000024, "Golden Panther Skin", "Skin for Night Panther", 2000, 199),
    ]
    for pid, pname, pdesc, pc, pg in pet_defs:
        add(pid, pname, pdesc, coins_price=pc, gems_price=pg,
            type_override=f"{MallTabType.PET}")

    return items


def default_gift_store_items() -> List[Dict[str, Any]]:
    """Default GiftItem entries for CSGetGiftStoreDetailsRes using real Item.csv IDs."""
    return [
        {"commodity_id": 2001, "sort_id": 1, "item_id": 700000001, "coins_price": 0, "gems_price": 899,
         "tag_type": StoreTag.HOT, "is_exclusive": False, "is_quick_gift_recommended": True},
        {"commodity_id": 2002, "sort_id": 2, "item_id": 700000271, "coins_price": 0, "gems_price": 499,
         "tag_type": StoreTag.HOT, "is_exclusive": False, "is_quick_gift_recommended": True},
        {"commodity_id": 2003, "sort_id": 3, "item_id": 400000053, "coins_price": 1000, "gems_price": 40,
         "tag_type": StoreTag.NEW, "is_exclusive": False, "is_quick_gift_recommended": True},
        {"commodity_id": 2004, "sort_id": 4, "item_id": 203000001, "coins_price": 1500, "gems_price": 199,
         "tag_type": StoreTag.NONE, "is_exclusive": False, "is_quick_gift_recommended": False},
        {"commodity_id": 2005, "sort_id": 5, "item_id": 907000013, "coins_price": 0, "gems_price": 499,
         "tag_type": StoreTag.HOT, "is_exclusive": False, "is_quick_gift_recommended": False},
        {"commodity_id": 2006, "sort_id": 6, "item_id": 1300000031, "coins_price": 0, "gems_price": 599,
         "tag_type": StoreTag.NONE, "is_exclusive": False, "is_quick_gift_recommended": False},
    ]


def default_exchange_stores() -> List[Dict[str, Any]]:
    """Default ExchangeStore tabs & items for CSGetExchangeStoreRes using real Item.csv IDs."""
    return [
        {
            "exchange_store_desc": {
                "store_id": 1,
                "store_name": "FF Token Redeem",
                "need_clan": False,
            },
            "exchange_store_items": [
                {"store_id": 1, "commodity_id": 3001, "sort_id": 1, "name": "Streetwear Legend Bundle",
                 "item_id": 700000001, "currency_id": 801000001, "currency_name": "FF Token",
                 "currency_price": 40, "tag_type": StoreTag.HOT},
                {"store_id": 1, "commodity_id": 3002, "sort_id": 2, "name": "AK Weapon Loot Crate",
                 "item_id": 400000053, "currency_id": 801000001, "currency_name": "FF Token",
                 "currency_price": 5, "tag_type": StoreTag.NEW},
                {"store_id": 1, "commodity_id": 3003, "sort_id": 3, "name": "Skull Bandana Mask",
                 "item_id": 211000001, "currency_id": 801000001, "currency_name": "FF Token",
                 "currency_price": 15, "tag_type": StoreTag.NONE},
            ],
        },
        {
            "exchange_store_desc": {
                "store_id": 2,
                "store_name": "Rank Token Redeem",
                "need_clan": False,
            },
            "exchange_store_items": [
                {"store_id": 2, "commodity_id": 3101, "sort_id": 1, "name": "Crimson Samurai Bundle",
                 "item_id": 700000002, "currency_id": 800000001, "currency_name": "Rank Token",
                 "currency_price": 100, "tag_type": StoreTag.HOT},
                {"store_id": 2, "commodity_id": 3102, "sort_id": 2, "name": "SCAR - Titan",
                 "item_id": 907000014, "currency_id": 800000001, "currency_name": "Rank Token",
                 "currency_price": 50, "tag_type": StoreTag.NONE},
            ],
        },
        {
            "exchange_store_desc": {
                "store_id": 3,
                "store_name": "Guild Token Redeem",
                "need_clan": True,
            },
            "exchange_store_items": [
                {"store_id": 3, "commodity_id": 3201, "sort_id": 1, "name": "M4A1 Weapon Loot Crate",
                 "item_id": 400000054, "currency_id": 814000001, "currency_name": "Guild Token",
                 "currency_price": 10, "min_clan_level": 1},
            ],
        },
    ]


def default_discount_stores() -> List[Dict[str, Any]]:
    """Default DiscountStoreDesc entries for CSGetDiscountStoreDescRes / LoginDescRes tag 14."""
    return [
        {"store_id": 1, "loop_id": 1, "refresh_id": 1, "item_id": 700000003,
         "coins_price": 0, "gems_price": 999, "discount_value": 0.5, "limited_purchase_times": 3, "purchase_times": 0},
        {"store_id": 1, "loop_id": 1, "refresh_id": 2, "item_id": 400000044,
         "coins_price": 900, "gems_price": 35, "discount_value": 0.3, "limited_purchase_times": 10, "purchase_times": 0},
        {"store_id": 1, "loop_id": 1, "refresh_id": 3, "item_id": 907000010,
         "coins_price": 7500, "gems_price": 399, "discount_value": 0.4, "limited_purchase_times": 1, "purchase_times": 0},
        {"store_id": 1, "loop_id": 1, "refresh_id": 4, "item_id": 904000001,
         "coins_price": 2500, "gems_price": 299, "discount_value": 0.5, "limited_purchase_times": 1, "purchase_times": 0},
    ]


def build_default_login_desc_store_parts() -> Dict[str, bytes]:
    """
    Helper returning pre-encoded LoginDescRes submessages for Store-related tags:
      - tag 9  treasure_res
      - tag 10 bundle_res
      - tag 11 gift_store_res
      - tag 14 discount_store_res
      - tag 20 store_tab_res
    """
    boxes, crates = default_treasure_boxes()
    return {
        "treasure_res": encode_get_treasure_box_res(boxes, crates),
        "bundle_res": encode_get_bundle_res(default_bundle_shows()),
        "gift_store_res": encode_get_gift_store_res(),
        "discount_store_res": encode_get_discount_store_desc_res(default_discount_stores()),
        "store_tab_res": encode_get_store_tab_res(default_store_tabs()),
    }
