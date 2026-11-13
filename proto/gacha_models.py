"""Protobuf schemas, decoders, encoders, and OB17 Luck Royale catalogs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from proto.decoder import (
    decode_proto,
    get_string,
    get_varint,
)
from proto.encoder import (
    encode_bool,
    encode_float,
    encode_int32,
    encode_int64,
    encode_packed_uint32,
    encode_string,
    encode_submessage,
    encode_uint32,
)
from proto.store_models import (
    AwardType,
    TransReason,
    encode_award_data,
    encode_award_desc,
    encode_exchange_change_data,
    encode_exchanged_award,
)


# ---------------------------------------------------------------------------
# Enums (ELottery.* & UIModelGacha helpers verified against dump.cs / SO)
# ---------------------------------------------------------------------------

class LotteryType:
    """ELottery.LotteryType"""
    NONE = 0
    ONE = 1
    SOME = 2
    DROPUP_BUFF = 3


class CoinType:
    """ELottery.CoinType"""
    NONE = 0
    COINS = 1
    GEMS = 2


class ConsumeType:
    """ELottery.ConsumeType"""
    NONE = 0
    FREE = 1
    EXCHANGE_ITEM = 2
    MONEY = 3


class ChestTabType:
    """ELottery.Type"""
    NORMAL = 0
    TURNTABLE = 1
    ULTRAMATE = 2
    LEGENDARY = 3


class RareType:
    """ELottery.RareType"""
    NORMAL = 0
    RARE = 1
    SUPER_RARE = 2


# ---------------------------------------------------------------------------
# Real Free Fire 1.39 (OB17) Vouchers, Tokens & Item Constants (Item.csv)
# ---------------------------------------------------------------------------

VOUCHER_GOLD_ROYALE = 802000000
VOUCHER_DIAMOND_ROYALE = 802000001
VOUCHER_WEAPON_ROYALE = 802000008
VOUCHER_INCUBATOR = 802000009

ITEM_FF_TOKEN = 800000301
ITEM_MAGIC_CUBE = 800000304
ITEM_EVOLUTION_STONE = 808000001
ITEM_BLUEPRINT_YINYANG = 808000011
ITEM_BLUEPRINT_JOKER = 808000012

# Standard Luck Royale Chest IDs
CHEST_DIAMOND_ROYALE = 3
CHEST_WEAPON_ROYALE = 4
CHEST_GOLD_ROYALE = 5
CHEST_INCUBATOR = 6

FREE_COOLDOWN_SECONDS = 86400  # 24h free draw cycle


@dataclass(frozen=True)
class GachaShowItemConfig:
    item_id: int
    item_num: int = 1
    item_type: int = AwardType.ITEM
    is_show: bool = True
    reward_level: int = RareType.NORMAL
    repeated_item_id: int = ITEM_FF_TOKEN
    repeated_item_num: int = 5
    turntable_props_type: int = 0
    drop_up_ratio: float = 0.0
    weight: int = 100


@dataclass(frozen=True)
class ExtraRewardConfig:
    cdt_value: int
    reward_id: int
    reward_num: int = 1
    reward_type: int = AwardType.ITEM
    cdt_type: int = 1
    icon: str = ""
    special_reward: str = ""


@dataclass(frozen=True)
class ChestConfig:
    chest_id: int
    chest_sub_id: int
    priority: int
    coin_type: int
    chest_name: str
    exchange_itemid: int
    free_type: int
    once_price: int
    ten_price: int
    exchange_once_num: int
    exchange_ten_num: int
    color_id: int
    chest_model_id: int
    show_model_male: int
    show_model_female: int
    rare_item_max: int
    chest_type_enum: int = ChestTabType.NORMAL
    forge_tab_id: int = 0
    once_num: int = 1
    ten_num: int = 10
    discount_price_one: int = 0
    discount_price_ten: int = 0
    must_drop: bool = True
    extra_reward: bool = True
    first_reward_switch: bool = False
    first_reward_max: int = 3
    second_level_count: int = 40
    third_level_count: int = 90
    chest_activity: int = 2
    open_priority_switch: int = 0
    chest_model_id2: int = 0
    chest_model_id3: int = 0
    drop_probability_switch: bool = True
    extra_reward_icon: int = 2
    chest_hint_color: int = 0
    extra_reward_reset_day: tuple = (1,)
    items: tuple = field(default_factory=tuple)
    extra_rewards: tuple = field(default_factory=tuple)
    probabilities: tuple = ((RareType.SUPER_RARE, 2), (RareType.RARE, 18), (RareType.NORMAL, 80))


@dataclass(frozen=True)
class SpecialExchangeConfig:
    forge_tab_id: int
    tab_name: str
    item_id: int
    item_num: int
    sort_id: int
    limited_purchase_times: int
    exchange_items: tuple  # tuple of (award_id, award_num, award_type)
    reward_level: int = RareType.SUPER_RARE
    language: str = "en"
    image_url: str = ""
    real_image_url: str = ""
    is_show: bool = True


# ---------------------------------------------------------------------------
# Authentic OB17 Chest Catalogs (ChestType.csv + Item.csv)
# ---------------------------------------------------------------------------

CHEST_CONFIGS: Dict[int, ChestConfig] = {
    CHEST_DIAMOND_ROYALE: ChestConfig(
        chest_id=CHEST_DIAMOND_ROYALE,
        chest_sub_id=20,
        priority=100,
        coin_type=CoinType.GEMS,
        chest_name="TXT_CHEST_NAME_GEM",
        exchange_itemid=VOUCHER_DIAMOND_ROYALE,
        free_type=1,
        once_price=60,
        ten_price=600,
        exchange_once_num=1,
        exchange_ten_num=10,
        color_id=1,
        chest_model_id=203000374,
        show_model_male=102000010,
        show_model_female=101000010,
        rare_item_max=150,
        chest_type_enum=ChestTabType.NORMAL,
        once_num=1,
        ten_num=10,
        first_reward_switch=True,
        first_reward_max=3,
        chest_activity=2,
        items=(
            GachaShowItemConfig(ITEM_MAGIC_CUBE, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_MAGIC_CUBE, 1, weight=2),
            GachaShowItemConfig(710000401, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4),
            GachaShowItemConfig(710000400, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4),
            GachaShowItemConfig(710000403, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 8, weight=12),
            GachaShowItemConfig(710000404, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 8, weight=12),
            GachaShowItemConfig(710000405, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 5, weight=15),
            GachaShowItemConfig(710000406, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 5, weight=15),
            GachaShowItemConfig(203000505, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=60),
            GachaShowItemConfig(203000506, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=60),
            GachaShowItemConfig(204000304, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=60),
            GachaShowItemConfig(204000307, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=60),
            GachaShowItemConfig(ITEM_FF_TOKEN, 5, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 5, weight=80),
            GachaShowItemConfig(1101000002, 1, AwardType.ITEM, False, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=90),
            GachaShowItemConfig(1102000002, 1, AwardType.ITEM, False, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=90),
            GachaShowItemConfig(1307000001, 2, AwardType.ITEM, False, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=90),
        ),
        extra_rewards=(
            ExtraRewardConfig(5, VOUCHER_DIAMOND_ROYALE, 1),
            ExtraRewardConfig(15, VOUCHER_WEAPON_ROYALE, 1),
            ExtraRewardConfig(30, ITEM_FF_TOKEN, 15),
            ExtraRewardConfig(60, VOUCHER_INCUBATOR, 2),
            ExtraRewardConfig(100, ITEM_MAGIC_CUBE, 1),
        ),
        probabilities=((RareType.SUPER_RARE, 2), (RareType.RARE, 18), (RareType.NORMAL, 80)),
    ),
    CHEST_WEAPON_ROYALE: ChestConfig(
        chest_id=CHEST_WEAPON_ROYALE,
        chest_sub_id=12,
        priority=75,
        coin_type=CoinType.GEMS,
        chest_name="TXT_CHEST_NAME_GUN",
        exchange_itemid=VOUCHER_WEAPON_ROYALE,
        free_type=1,
        once_price=40,
        ten_price=400,
        exchange_once_num=1,
        exchange_ten_num=10,
        color_id=1,
        chest_model_id=907001611,
        show_model_male=102000010,
        show_model_female=101000010,
        rare_item_max=150,
        chest_type_enum=ChestTabType.NORMAL,
        once_num=1,
        ten_num=10,
        chest_activity=0,
        items=(
            GachaShowItemConfig(907001611, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4),
            GachaShowItemConfig(907001612, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4),
            GachaShowItemConfig(907001613, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 6, weight=14),
            GachaShowItemConfig(907001614, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 6, weight=14),
            GachaShowItemConfig(907001620, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 5, weight=20),
            GachaShowItemConfig(907001621, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 5, weight=20),
            GachaShowItemConfig(907001622, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=55),
            GachaShowItemConfig(907001623, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=55),
            GachaShowItemConfig(907001603, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=65),
            GachaShowItemConfig(907001604, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=65),
            GachaShowItemConfig(907001605, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=65),
            GachaShowItemConfig(907001607, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=65),
            GachaShowItemConfig(907001608, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=65),
            GachaShowItemConfig(ITEM_FF_TOKEN, 5, AwardType.ITEM, False, RareType.NORMAL, ITEM_FF_TOKEN, 5, weight=80),
        ),
        extra_rewards=(
            ExtraRewardConfig(5, VOUCHER_WEAPON_ROYALE, 1),
            ExtraRewardConfig(15, VOUCHER_DIAMOND_ROYALE, 1),
            ExtraRewardConfig(30, ITEM_FF_TOKEN, 15),
            ExtraRewardConfig(60, 907001620, 1),
            ExtraRewardConfig(100, 907001611, 1),
        ),
        probabilities=((RareType.SUPER_RARE, 3), (RareType.RARE, 22), (RareType.NORMAL, 75)),
    ),
    CHEST_GOLD_ROYALE: ChestConfig(
        chest_id=CHEST_GOLD_ROYALE,
        chest_sub_id=4,
        priority=50,
        coin_type=CoinType.COINS,
        chest_name="TXT_CHEST_NAME_GOLD",
        exchange_itemid=VOUCHER_GOLD_ROYALE,
        free_type=1,
        once_price=300,
        ten_price=3000,
        exchange_once_num=1,
        exchange_ten_num=10,
        color_id=2,
        chest_model_id=101000010,
        chest_model_id2=700000257,
        show_model_male=102000007,
        show_model_female=101000010,
        rare_item_max=300,
        chest_type_enum=ChestTabType.NORMAL,
        once_num=1,
        ten_num=10,
        open_priority_switch=1,
        chest_activity=0,
        items=(
            GachaShowItemConfig(710000422, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=3),
            GachaShowItemConfig(710000423, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=3),
            GachaShowItemConfig(710000303, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 5, weight=15),
            GachaShowItemConfig(710000304, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 5, weight=15),
            GachaShowItemConfig(710000305, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 5, weight=15),
            GachaShowItemConfig(203000500, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=60),
            GachaShowItemConfig(203000501, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=60),
            GachaShowItemConfig(204000300, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 3, weight=60),
            GachaShowItemConfig(800000001, 5, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=85),
            GachaShowItemConfig(800000002, 5, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=85),
            GachaShowItemConfig(1101000001, 1, AwardType.ITEM, False, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=95),
            GachaShowItemConfig(1102000001, 1, AwardType.ITEM, False, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=95),
            GachaShowItemConfig(1307000001, 1, AwardType.ITEM, False, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=95),
        ),
        extra_rewards=(
            ExtraRewardConfig(5, VOUCHER_GOLD_ROYALE, 2),
            ExtraRewardConfig(15, VOUCHER_DIAMOND_ROYALE, 1),
            ExtraRewardConfig(30, ITEM_FF_TOKEN, 10),
            ExtraRewardConfig(60, 710000304, 1),
            ExtraRewardConfig(100, 710000422, 1),
        ),
        probabilities=((RareType.SUPER_RARE, 1), (RareType.RARE, 14), (RareType.NORMAL, 85)),
    ),
    CHEST_INCUBATOR: ChestConfig(
        chest_id=CHEST_INCUBATOR,
        chest_sub_id=4,
        priority=1,
        coin_type=CoinType.GEMS,
        chest_name="T_12_Z_CHEST_WHEEL_HELP_TAB",
        exchange_itemid=VOUCHER_INCUBATOR,
        free_type=0,
        once_price=60,
        ten_price=270,
        exchange_once_num=1,
        exchange_ten_num=5,
        color_id=3,
        chest_model_id=203000395,
        chest_model_id2=203000396,
        show_model_male=102000009,
        show_model_female=101000010,
        rare_item_max=80,
        chest_type_enum=ChestTabType.TURNTABLE,
        forge_tab_id=1,
        once_num=1,
        ten_num=5,
        must_drop=False,
        chest_activity=2,
        items=(
            # 12 slots matching UIGachaTurntableContentView Reward0..Reward11
            GachaShowItemConfig(ITEM_BLUEPRINT_YINYANG, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_BLUEPRINT_YINYANG, 1, turntable_props_type=1, weight=6),
            GachaShowItemConfig(ITEM_EVOLUTION_STONE, 1, AwardType.ITEM, True, RareType.RARE, ITEM_EVOLUTION_STONE, 1, turntable_props_type=2, weight=14),
            GachaShowItemConfig(ITEM_BLUEPRINT_JOKER, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_BLUEPRINT_JOKER, 1, turntable_props_type=1, weight=6),
            GachaShowItemConfig(ITEM_EVOLUTION_STONE, 2, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_EVOLUTION_STONE, 2, turntable_props_type=2, weight=8),
            GachaShowItemConfig(907001615, 1, AwardType.ITEM, True, RareType.RARE, ITEM_FF_TOKEN, 10, weight=16),
            GachaShowItemConfig(ITEM_MAGIC_CUBE, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_MAGIC_CUBE, 1, weight=4),
            GachaShowItemConfig(VOUCHER_DIAMOND_ROYALE, 1, AwardType.ITEM, True, RareType.NORMAL, VOUCHER_DIAMOND_ROYALE, 1, weight=40),
            GachaShowItemConfig(VOUCHER_WEAPON_ROYALE, 1, AwardType.ITEM, True, RareType.NORMAL, VOUCHER_WEAPON_ROYALE, 1, weight=40),
            GachaShowItemConfig(ITEM_FF_TOKEN, 5, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 5, weight=55),
            GachaShowItemConfig(1307000001, 3, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=60),
            GachaShowItemConfig(1101000002, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=60),
            GachaShowItemConfig(1102000002, 1, AwardType.ITEM, True, RareType.NORMAL, ITEM_FF_TOKEN, 2, weight=60),
        ),
        extra_rewards=(
            ExtraRewardConfig(5, ITEM_EVOLUTION_STONE, 1),
            ExtraRewardConfig(15, ITEM_BLUEPRINT_YINYANG, 1),
            ExtraRewardConfig(30, ITEM_EVOLUTION_STONE, 2),
            ExtraRewardConfig(60, ITEM_BLUEPRINT_JOKER, 1),
        ),
        probabilities=((RareType.SUPER_RARE, 6), (RareType.RARE, 24), (RareType.NORMAL, 70)),
    ),
}


DEFAULT_SPECIAL_EXCHANGES: List[SpecialExchangeConfig] = [
    # Tab 1: OB17 YinYang Incubator Bundles (710000408..413)
    SpecialExchangeConfig(
        forge_tab_id=1,
        tab_name="T_17_R_CHEST_YINYANG_NAME",
        item_id=710000410,  # T_17_Y_BUNDLE_MALE_YINYANG_GOLD_NAME
        item_num=1,
        sort_id=1,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_YINYANG, 3, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 7, AwardType.ITEM)),
        reward_level=RareType.SUPER_RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=1,
        tab_name="T_17_R_CHEST_YINYANG_NAME",
        item_id=710000411,  # T_17_Y_BUNDLE_FEMALE_YINYANG_GOLD_NAME
        item_num=1,
        sort_id=2,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_YINYANG, 3, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 7, AwardType.ITEM)),
        reward_level=RareType.SUPER_RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=1,
        tab_name="T_17_R_CHEST_YINYANG_NAME",
        item_id=710000412,  # T_17_Y_BUNDLE_MALE_YINYANG_BLUE_NAME
        item_num=1,
        sort_id=3,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_YINYANG, 2, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 5, AwardType.ITEM)),
        reward_level=RareType.RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=1,
        tab_name="T_17_R_CHEST_YINYANG_NAME",
        item_id=710000413,  # T_17_Y_BUNDLE_FEMALE_YINYANG_BLUE_NAME
        item_num=1,
        sort_id=4,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_YINYANG, 2, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 5, AwardType.ITEM)),
        reward_level=RareType.RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=1,
        tab_name="T_17_R_CHEST_YINYANG_NAME",
        item_id=710000408,  # T_17_Y_BUNDLE_MALE_YINYANG_NAME
        item_num=1,
        sort_id=5,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_YINYANG, 1, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 3, AwardType.ITEM)),
        reward_level=RareType.NORMAL,
    ),
    SpecialExchangeConfig(
        forge_tab_id=1,
        tab_name="T_17_R_CHEST_YINYANG_NAME",
        item_id=710000409,  # T_17_Y_BUNDLE_FEMALE_YINYANG_NAME
        item_num=1,
        sort_id=6,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_YINYANG, 1, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 3, AwardType.ITEM)),
        reward_level=RareType.NORMAL,
    ),
    # Tab 2: OB17 Joker Incubator Bundles (710000414..419)
    SpecialExchangeConfig(
        forge_tab_id=2,
        tab_name="T_17_R_CHEST_JOKER_NAME",
        item_id=710000414,  # T_17_Y_BUNDLE_MALE_JOKER_ROYAL_NAME
        item_num=1,
        sort_id=1,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_JOKER, 3, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 7, AwardType.ITEM)),
        reward_level=RareType.SUPER_RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=2,
        tab_name="T_17_R_CHEST_JOKER_NAME",
        item_id=710000415,  # T_17_Y_BUNDLE_FEMALE_JOKER_ROYAL_NAME
        item_num=1,
        sort_id=2,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_JOKER, 3, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 7, AwardType.ITEM)),
        reward_level=RareType.SUPER_RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=2,
        tab_name="T_17_R_CHEST_JOKER_NAME",
        item_id=710000416,  # T_17_Y_BUNDLE_MALE_JOKER_REAPER_NAME
        item_num=1,
        sort_id=3,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_JOKER, 2, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 5, AwardType.ITEM)),
        reward_level=RareType.RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=2,
        tab_name="T_17_R_CHEST_JOKER_NAME",
        item_id=710000417,  # T_17_Y_BUNDLE_FEMALE_JOKER_REAPER_NAME
        item_num=1,
        sort_id=4,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_JOKER, 2, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 5, AwardType.ITEM)),
        reward_level=RareType.RARE,
    ),
    SpecialExchangeConfig(
        forge_tab_id=2,
        tab_name="T_17_R_CHEST_JOKER_NAME",
        item_id=710000418,  # T_17_Y_BUNDLE_MALE_JOKER_PENNYWISE_NAME
        item_num=1,
        sort_id=5,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_JOKER, 1, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 3, AwardType.ITEM)),
        reward_level=RareType.NORMAL,
    ),
    SpecialExchangeConfig(
        forge_tab_id=2,
        tab_name="T_17_R_CHEST_JOKER_NAME",
        item_id=710000419,  # T_17_Y_BUNDLE_FEMALE_JOKER_PENNYWISE_NAME
        item_num=1,
        sort_id=6,
        limited_purchase_times=1,
        exchange_items=((ITEM_BLUEPRINT_JOKER, 1, AwardType.ITEM), (ITEM_EVOLUTION_STONE, 3, AwardType.ITEM)),
        reward_level=RareType.NORMAL,
    ),
]


# ---------------------------------------------------------------------------
# Request Decoders (CS*Req)
# ---------------------------------------------------------------------------

def decode_get_gacha_special_exchange_desc_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSGetGachaSpecialExchangeDescReq"""
    fields = decode_proto(raw_body)
    return {"language": get_string(fields, 1, "en") or "en"}


def decode_get_lottery_probability_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSGetLotteryProbabilityReq"""
    fields = decode_proto(raw_body)
    return {
        "chest_id": get_varint(fields, 1, CHEST_DIAMOND_ROYALE),
        "chest_sub_id": get_varint(fields, 2, 0),
    }


def decode_lottery_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSLotteryReq"""
    fields = decode_proto(raw_body)
    return {
        "chest_id": get_varint(fields, 1, 0),
        "gacha_type": get_varint(fields, 2, LotteryType.ONE),
        "chest_sub_id": get_varint(fields, 3, 0),
        "consume_type": get_varint(fields, 4, ConsumeType.MONEY),
    }


def decode_lottery_extra_reward_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSLotteryExtraRewardReq"""
    fields = decode_proto(raw_body)
    return {
        "chest_id": get_varint(fields, 1, 0),
        "condition_num": get_varint(fields, 2, 0),
        "chest_sub_id": get_varint(fields, 3, 0),
    }


def decode_do_gacha_special_exchange_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSDoGachaSpecialExchangeReq"""
    fields = decode_proto(raw_body)
    return {
        "forge_tab_id": get_varint(fields, 1, 0),
        "item_id": get_varint(fields, 2, 0),
        "exchange_cnt": max(1, get_varint(fields, 3, 1)),
    }


# ---------------------------------------------------------------------------
# Response Encoders
# ---------------------------------------------------------------------------

def _active_window(now: Optional[int] = None) -> tuple[int, int, str, str]:
    base = int(now or time.time())
    start_ts = base - 86400 * 30
    end_ts = base + 86400 * 365
    start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(start_ts))
    end_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(end_ts))
    return start_ts, end_ts, start_str, end_str


def encode_client_chest_type(cfg: ChestConfig, now: Optional[int] = None) -> bytes:
    """proto.ClientChestType (tags 1..54 verified from IL2CPP)."""
    start_ts, end_ts, start_str, end_str = _active_window(now)
    buf = bytearray()
    buf += encode_uint32(1, cfg.chest_id)
    buf += encode_uint32(2, cfg.priority)
    buf += encode_uint32(3, cfg.coin_type)
    buf += encode_string(4, start_str)
    buf += encode_string(5, end_str)
    buf += encode_string(6, cfg.chest_name)
    buf += encode_uint32(7, cfg.exchange_itemid)
    buf += encode_uint32(8, cfg.free_type)
    buf += encode_uint32(9, cfg.chest_activity)
    buf += encode_uint32(10, cfg.chest_model_id)
    buf += encode_int64(11, start_ts)
    buf += encode_int64(12, end_ts)
    buf += encode_uint32(13, cfg.once_price)
    buf += encode_uint32(14, cfg.ten_price)
    buf += encode_uint32(15, cfg.exchange_once_num)
    buf += encode_uint32(16, cfg.exchange_ten_num)
    buf += encode_uint32(17, cfg.color_id)
    buf += encode_bool(18, cfg.must_drop)
    buf += encode_bool(19, cfg.extra_reward)
    buf += encode_uint32(20, cfg.once_num)
    buf += encode_uint32(21, cfg.ten_num)
    if cfg.discount_price_one:
        buf += encode_int64(28, start_ts)
        buf += encode_int64(29, end_ts)
        buf += encode_uint32(30, cfg.discount_price_one)
        buf += encode_uint32(31, cfg.discount_price_ten)
    buf += encode_uint32(32, cfg.show_model_male)
    buf += encode_uint32(33, cfg.show_model_female)
    buf += encode_uint32(34, cfg.rare_item_max)
    buf += encode_uint32(35, cfg.first_reward_max)
    buf += encode_uint32(36, cfg.second_level_count)
    buf += encode_uint32(37, cfg.third_level_count)
    if cfg.extra_reward_reset_day:
        buf += encode_packed_uint32(38, list(cfg.extra_reward_reset_day))
    buf += encode_uint32(39, cfg.chest_sub_id)
    buf += encode_bool(40, cfg.first_reward_switch)
    if cfg.chest_model_id2:
        buf += encode_uint32(41, cfg.chest_model_id2)
    buf += encode_bool(42, cfg.drop_probability_switch)
    buf += encode_uint32(43, cfg.open_priority_switch)
    if cfg.chest_model_id3:
        buf += encode_uint32(44, cfg.chest_model_id3)
    buf += encode_uint32(45, cfg.chest_type_enum)
    if cfg.forge_tab_id:
        buf += encode_uint32(46, cfg.forge_tab_id)
    buf += encode_uint32(47, cfg.extra_reward_icon)
    if cfg.chest_hint_color:
        buf += encode_uint32(48, cfg.chest_hint_color)
    return bytes(buf)


def encode_gacha_show_item(item: GachaShowItemConfig) -> bytes:
    """proto.GachaShowItem"""
    buf = bytearray()
    buf += encode_uint32(1, item.item_id)
    buf += encode_bool(2, item.is_show)
    buf += encode_uint32(3, item.repeated_item_id)
    buf += encode_uint32(4, item.repeated_item_num)
    buf += encode_uint32(5, item.item_type)
    buf += encode_uint32(6, item.item_num)
    buf += encode_uint32(7, item.reward_level)
    if item.turntable_props_type:
        buf += encode_uint32(8, item.turntable_props_type)
    if item.drop_up_ratio:
        buf += encode_float(9, item.drop_up_ratio)
    return bytes(buf)


def encode_extra_reward_desc(chest_id: int, chest_sub_id: int, er: ExtraRewardConfig) -> bytes:
    """proto.ExtraRewardDesc"""
    buf = bytearray()
    buf += encode_uint32(1, chest_id)
    if er.icon:
        buf += encode_string(2, er.icon)
    buf += encode_uint32(3, er.cdt_type)
    buf += encode_uint32(4, er.cdt_value)
    buf += encode_submessage(
        5,
        encode_award_desc(
            award_id=er.reward_id,
            award_num=er.reward_num,
            award_type=er.reward_type,
        ),
    )
    buf += encode_uint32(6, chest_sub_id)
    if er.special_reward:
        buf += encode_string(7, er.special_reward)
    return bytes(buf)


def encode_gacha_desc(cfg: ChestConfig, now: Optional[int] = None) -> bytes:
    """proto.GachaDesc"""
    buf = bytearray()
    buf += encode_uint32(1, cfg.chest_id)
    buf += encode_submessage(2, encode_client_chest_type(cfg, now=now))
    for item in cfg.items:
        buf += encode_submessage(3, encode_gacha_show_item(item))
    for er in cfg.extra_rewards:
        buf += encode_submessage(4, encode_extra_reward_desc(cfg.chest_id, cfg.chest_sub_id, er))
    return bytes(buf)


def encode_get_gacha_desc_res(
    configs: Optional[Sequence[ChestConfig]] = None,
    now: Optional[int] = None,
) -> bytes:
    """proto.CSGetGachaDescRes"""
    chests = list(configs) if configs is not None else sorted(
        CHEST_CONFIGS.values(), key=lambda c: (-c.priority, c.chest_id)
    )
    buf = bytearray()
    for cfg in chests:
        buf += encode_submessage(1, encode_gacha_desc(cfg, now=now))
    return bytes(buf)


def encode_gacha_info(
    chest_id: int,
    lottery_count_weekly: int = 0,
    exchanged_reward_list: Sequence[int] = (),
    next_free_time: int = 0,
    not_got_num: int = 0,
    limit_purchase_count_one: int = 0,
    limit_purchase_count_ten: int = 0,
    first_draw_reward_num: int = 0,
) -> bytes:
    """proto.GachaInfo"""
    buf = bytearray()
    buf += encode_uint32(1, chest_id)
    buf += encode_uint32(2, lottery_count_weekly)
    if exchanged_reward_list:
        buf += encode_packed_uint32(3, [int(x) for x in exchanged_reward_list])
    buf += encode_int64(4, next_free_time)
    buf += encode_uint32(5, not_got_num)
    if limit_purchase_count_one:
        buf += encode_uint32(6, limit_purchase_count_one)
    if limit_purchase_count_ten:
        buf += encode_uint32(7, limit_purchase_count_ten)
    if first_draw_reward_num:
        buf += encode_uint32(8, first_draw_reward_num)
    return bytes(buf)


def encode_get_gacha_info_res(infos: Sequence[Dict[str, Any]]) -> bytes:
    """proto.CSGetGachaInfoRes"""
    buf = bytearray()
    for info in infos:
        buf += encode_submessage(1, encode_gacha_info(**info))
    return bytes(buf)


def encode_chest_special_exchange_desc(
    cfg: SpecialExchangeConfig,
    purchase_times: int = 0,
    language: str = "en",
    now: Optional[int] = None,
) -> bytes:
    """proto.ChestSpecialExchangeDesc"""
    _, _, start_str, end_str = _active_window(now)
    buf = bytearray()
    buf += encode_uint32(1, cfg.forge_tab_id)
    buf += encode_string(2, cfg.tab_name)
    buf += encode_uint32(3, cfg.item_id)
    buf += encode_uint32(4, cfg.item_num)
    buf += encode_uint32(5, cfg.sort_id)
    buf += encode_string(6, start_str)
    buf += encode_string(7, end_str)
    buf += encode_uint32(8, cfg.limited_purchase_times)
    buf += encode_string(9, language or cfg.language)
    if cfg.image_url:
        buf += encode_string(10, cfg.image_url)
    buf += encode_bool(11, cfg.is_show)
    for award_id, award_num, award_type in cfg.exchange_items:
        buf += encode_submessage(
            12,
            encode_award_desc(
                award_id=award_id,
                award_num=award_num,
                award_type=award_type,
            ),
        )
    buf += encode_uint32(13, cfg.reward_level)
    if cfg.real_image_url:
        buf += encode_string(14, cfg.real_image_url)
    buf += encode_uint32(15, purchase_times)
    return bytes(buf)


def encode_get_gacha_special_exchange_desc_res(
    entries: Optional[Sequence[SpecialExchangeConfig]] = None,
    purchase_counts: Optional[Dict[tuple[int, int], int]] = None,
    language: str = "en",
    now: Optional[int] = None,
) -> bytes:
    """proto.CSGetGachaSpecialExchangeDescRes"""
    items = list(entries) if entries is not None else DEFAULT_SPECIAL_EXCHANGES
    counts = purchase_counts or {}
    buf = bytearray()
    for cfg in items:
        cnt = counts.get((cfg.forge_tab_id, cfg.item_id), 0)
        buf += encode_submessage(
            1,
            encode_chest_special_exchange_desc(
                cfg,
                purchase_times=cnt,
                language=language,
                now=now,
            ),
        )
    return bytes(buf)


def encode_rare_probability(rare: int, probability: int) -> bytes:
    """proto.CSGetLotteryProbabilityRes.RareProbability"""
    return encode_uint32(1, rare) + encode_uint32(2, probability)


def encode_get_lottery_probability_res(rare_pr: Sequence[tuple[int, int]]) -> bytes:
    """proto.CSGetLotteryProbabilityRes"""
    buf = bytearray()
    for rare, prob in rare_pr:
        buf += encode_submessage(1, encode_rare_probability(rare, prob))
    return bytes(buf)


def encode_lottery_res(
    lottery_goods: Sequence[Dict[str, int]],
    reward_goods: Sequence[Dict[str, int]] = (),
    extra_one_goods: Sequence[Dict[str, int]] = (),
    lottery_count_weekly: int = 0,
    next_free_time: int = 0,
    limit_purchase_count_one: int = 0,
    limit_purchase_count_ten: int = 0,
    not_got_num: int = 0,
    first_draw_reward_num: int = 0,
    exchange_item_num: int = 0,
    has_big_reward: bool = False,
) -> bytes:
    """proto.CSLotteryRes"""
    buf = bytearray()
    for g in lottery_goods:
        buf += encode_submessage(1, encode_exchanged_award(**g))
    for g in reward_goods:
        buf += encode_submessage(2, encode_exchanged_award(**g))
    for g in extra_one_goods:
        buf += encode_submessage(3, encode_exchanged_award(**g))
    buf += encode_uint32(4, lottery_count_weekly)
    buf += encode_int64(5, next_free_time)
    if limit_purchase_count_one:
        buf += encode_uint32(6, limit_purchase_count_one)
    if limit_purchase_count_ten:
        buf += encode_uint32(7, limit_purchase_count_ten)
    buf += encode_uint32(8, not_got_num)
    if first_draw_reward_num:
        buf += encode_uint32(9, first_draw_reward_num)
    buf += encode_int32(10, exchange_item_num)
    buf += encode_bool(11, has_big_reward)
    return bytes(buf)


def encode_exchange_gacha_extra_reward_res(
    items: Sequence[Dict[str, Any]] = (),
    coins: int = 0,
    gems: int = 0,
    exchanged_reward_list: Sequence[int] = (),
) -> bytes:
    """proto.CSExchangeGachaExtraRewardRes"""
    buf = bytearray()
    buf += encode_submessage(1, encode_award_data(items=items, coins=coins, gems=gems))
    if exchanged_reward_list:
        buf += encode_packed_uint32(2, [int(x) for x in exchanged_reward_list])
    return bytes(buf)


def encode_do_gacha_special_exchange_res(
    add_item_list: Sequence[Dict[str, Any]] = (),
    del_item_list: Sequence[Dict[str, Any]] = (),
    exchange_awards: Sequence[Dict[str, Any]] = (),
    purchase_times: int = 1,
    trans_id: int = 1,
) -> bytes:
    """proto.CSDoGachaSpecialExchangeRes"""
    change_data = encode_exchange_change_data(
        trans_id=trans_id,
        add_item_list=add_item_list,
        del_item_list=del_item_list,
        reason=TransReason.PURCHASE,
        exchange_awards=exchange_awards,
    )
    return encode_submessage(1, change_data) + encode_uint32(2, purchase_times)
