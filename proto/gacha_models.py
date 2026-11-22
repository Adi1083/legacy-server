"""
Centralized Backend Architecture & Data Models for Free Fire 1.39 (OB17) Luck Royale.
Provides:
1. Machine registry and configuration schema (separating existence, visibility, availability, eligibility, and spin authorization).
2. Reward pool models with weighted probability, rarity tiers (Gold, Purple, Blue), guaranteed drop rules, and isolated pools per machine.
3. Voucher, token, and special exchange (Incubator forge) definition models.
4. File/database persistence layer (JSON with atomic write, versioning, and validation schemas).
5. Shared interface contracts and abstract services for gacha_eng, economy_spec, and admin_api.
6. Protobuf request decoders and wire response encoders for FF 1.39 IL2CPP client.
"""

from __future__ import annotations

import abc
import copy
from dataclasses import asdict, dataclass, field
from enum import IntEnum
import json
import logging
import os
import random
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

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
from proto.character_models import (
    AVATAR_TO_DEBRIS_MAP,
    STARTER_AVATAR_IDS,
    get_character_debris_id,
)
from proto.store_models import (
    AwardType,
    TransReason,
    encode_award_data,
    encode_award_desc,
    encode_exchange_change_data,
    encode_exchanged_award,
)

logger = logging.getLogger("gacha_models")

# ---------------------------------------------------------------------------
# Enums (ELottery.* & UIModelGacha helpers verified against dump.cs / SO)
# ---------------------------------------------------------------------------

class LotteryType(IntEnum):
    """ELottery.LotteryType"""
    NONE = 0
    ONE = 1            # Single draw (1x)
    SOME = 2           # Multi-draw (10x or 5x)
    DROPUP_BUFF = 3    # Special rate-up draw


class CoinType(IntEnum):
    """ELottery.CoinType"""
    NONE = 0
    COINS = 1          # Gold Coins (Client Wire)
    GEMS = 2           # Diamonds (Client Wire)


# Semantic aliases for prompt & economy spec:
# Diamonds (CoinType.DIAMOND=1) and Gold (CoinType.GOLD=2)
CoinType.DIAMOND = 1
CoinType.GOLD = 2


class ConsumeType(IntEnum):
    """ELottery.ConsumeType"""
    NONE = 0
    FREE = 1           # Daily free spin
    EXCHANGE_ITEM = 2  # Royale Voucher
    MONEY = 3          # Gold or Diamonds


class ChestTabType(IntEnum):
    """ELottery.Type (Client display tab style)"""
    NORMAL = 0         # Standard card view (Diamond, Weapon, Gold)
    TURNTABLE = 1      # 12-slot roulette wheel (Incubator)
    ULTRAMATE = 2      # Special event royale
    LEGENDARY = 3      # High tier royale


class RareType(IntEnum):
    """ELottery.RareType (Rarity tier glow in UI)"""
    NORMAL = 0         # Blue tier (Common / Consumables / Standard skins)
    RARE = 1           # Purple tier (Epic / Stones / High tier weapons)
    SUPER_RARE = 2     # Gold tier (Jackpot / Blueprints / Magic Cube / Legendary)


class DropRarityTier(IntEnum):
    """Semantic aliases for visual reward rarity tiers."""
    BLUE = RareType.NORMAL
    PURPLE = RareType.RARE
    GOLD = RareType.SUPER_RARE


class MachineState(IntEnum):
    """Operational lifecycle state of a Luck Royale machine."""
    DISABLED = 0       # Machine is shut down / inaccessible
    ACTIVE = 1         # Machine is fully active and accepting spins
    MAINTENANCE = 2    # Visible but spin actions rejected with maintenance flag
    SCHEDULED = 3      # Machine awaiting start_time trigger


class CostType(IntEnum):
    """Type of currency/item expended in a spin transaction."""
    FREE = 0
    GOLD = 1
    DIAMOND = 2
    VOUCHER = 3


# ---------------------------------------------------------------------------
# Free Fire 1.39 (OB17) Authoritative Constants (Lead Architect Baseline #49)
# ---------------------------------------------------------------------------

# Canonical Vouchers (Item IDs)
VOUCHER_GOLD_ROYALE = 110100010
VOUCHER_DIAMOND_ROYALE = 110100008
VOUCHER_WEAPON_ROYALE = 110100009
VOUCHER_INCUBATOR = 110100018

# Legacy Voucher IDs (kept for backward compatibility and alias resolution)
LEGACY_VOUCHER_GOLD_ROYALE = 802000000
LEGACY_VOUCHER_DIAMOND_ROYALE = 802000001
LEGACY_VOUCHER_WEAPON_ROYALE = 802000008
LEGACY_VOUCHER_INCUBATOR = 802000009

# Canonical Tokens & Special Items
ITEM_FF_TOKEN = 110200001
LEGACY_ITEM_FF_TOKEN = 800000301
ITEM_MAGIC_CUBE = 800000304

# Incubator Materials
ITEM_EVOLUTION_STONE = 808000003
LEGACY_ITEM_EVOLUTION_STONE = 808000001
ITEM_BLUEPRINT_YINYANG = 808000001
LEGACY_ITEM_BLUEPRINT_YINYANG = 808000011
ITEM_BLUEPRINT_JOKER = 808000002
LEGACY_ITEM_BLUEPRINT_JOKER = 808000012

# Standard Luck Royale Chest IDs
CHEST_DIAMOND_ROYALE = 3
CHEST_WEAPON_ROYALE = 4
CHEST_GOLD_ROYALE = 5
CHEST_INCUBATOR = 6

# Free Spin Cooldown
FREE_COOLDOWN_SECONDS = 86400  # 24 hours

# Voucher Mapping: Maps canonical voucher to machine chest_id
VOUCHER_TO_CHEST_MAP: Dict[int, int] = {
    VOUCHER_DIAMOND_ROYALE: CHEST_DIAMOND_ROYALE,
    LEGACY_VOUCHER_DIAMOND_ROYALE: CHEST_DIAMOND_ROYALE,
    VOUCHER_WEAPON_ROYALE: CHEST_WEAPON_ROYALE,
    LEGACY_VOUCHER_WEAPON_ROYALE: CHEST_WEAPON_ROYALE,
    VOUCHER_GOLD_ROYALE: CHEST_GOLD_ROYALE,
    LEGACY_VOUCHER_GOLD_ROYALE: CHEST_GOLD_ROYALE,
    VOUCHER_INCUBATOR: CHEST_INCUBATOR,
    LEGACY_VOUCHER_INCUBATOR: CHEST_INCUBATOR,
}

# Alias Map: Maps legacy IDs to canonical IDs
VOUCHER_ALIASES: Dict[int, int] = {
    LEGACY_VOUCHER_GOLD_ROYALE: VOUCHER_GOLD_ROYALE,
    LEGACY_VOUCHER_DIAMOND_ROYALE: VOUCHER_DIAMOND_ROYALE,
    LEGACY_VOUCHER_WEAPON_ROYALE: VOUCHER_WEAPON_ROYALE,
    LEGACY_VOUCHER_INCUBATOR: VOUCHER_INCUBATOR,
    LEGACY_ITEM_FF_TOKEN: ITEM_FF_TOKEN,
    LEGACY_ITEM_EVOLUTION_STONE: ITEM_EVOLUTION_STONE,
    LEGACY_ITEM_BLUEPRINT_YINYANG: ITEM_BLUEPRINT_YINYANG,
    LEGACY_ITEM_BLUEPRINT_JOKER: ITEM_BLUEPRINT_JOKER,
}

# Reverse Alias Map: Maps canonical ID to list of valid acceptable IDs
VALID_ITEM_ID_ALIASES: Dict[int, Tuple[int, ...]] = {
    VOUCHER_GOLD_ROYALE: (VOUCHER_GOLD_ROYALE, LEGACY_VOUCHER_GOLD_ROYALE),
    VOUCHER_DIAMOND_ROYALE: (VOUCHER_DIAMOND_ROYALE, LEGACY_VOUCHER_DIAMOND_ROYALE),
    VOUCHER_WEAPON_ROYALE: (VOUCHER_WEAPON_ROYALE, LEGACY_VOUCHER_WEAPON_ROYALE),
    VOUCHER_INCUBATOR: (VOUCHER_INCUBATOR, LEGACY_VOUCHER_INCUBATOR),
    ITEM_FF_TOKEN: (ITEM_FF_TOKEN, LEGACY_ITEM_FF_TOKEN),
    ITEM_EVOLUTION_STONE: (ITEM_EVOLUTION_STONE, LEGACY_ITEM_EVOLUTION_STONE),
    ITEM_BLUEPRINT_YINYANG: (ITEM_BLUEPRINT_YINYANG, LEGACY_ITEM_BLUEPRINT_YINYANG),
    ITEM_BLUEPRINT_JOKER: (ITEM_BLUEPRINT_JOKER, LEGACY_ITEM_BLUEPRINT_JOKER),
}

# Default duplicate conversion rates (into FF Tokens)
DEFAULT_DUPLICATE_CONVERSION: Dict[int, int] = {
    RareType.SUPER_RARE: 10,  # Gold tier duplicate -> 10 FF tokens
    RareType.RARE: 5,        # Purple tier duplicate -> 5 FF tokens
    RareType.NORMAL: 2,      # Blue tier duplicate -> 2 FF tokens
}

# Stackable item prefixes in Free Fire inventory
STACKABLE_PREFIXES: Tuple[int, ...] = (800, 802, 804, 808, 1101, 1102, 1307)


def resolve_canonical_item_id(item_id: int) -> int:
    """Resolve an item ID (including legacy ID) to its canonical representation."""
    return VOUCHER_ALIASES.get(int(item_id), int(item_id))


def is_stackable_item(item_id: int) -> bool:
    """Determine whether an item stacks in inventory or represents a unique unlock."""
    iid = int(item_id)
    return (iid // 1_000_000) in STACKABLE_PREFIXES or (iid // 10_000) in (1101, 1102)


# ---------------------------------------------------------------------------
# Data Models: Reward Pool Item, Milestones, Recipes
# ---------------------------------------------------------------------------

@dataclass
class GachaShowItemConfig:
    """Individual reward item in a Luck Royale machine's isolated pool."""
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
    is_jackpot: bool = False

    @property
    def rarity_name(self) -> str:
        if self.reward_level == RareType.SUPER_RARE:
            return "Gold (Super Rare)"
        elif self.reward_level == RareType.RARE:
            return "Purple (Rare)"
        return "Blue (Normal)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_num": self.item_num,
            "item_type": self.item_type,
            "is_show": self.is_show,
            "reward_level": self.reward_level,
            "repeated_item_id": self.repeated_item_id,
            "repeated_item_num": self.repeated_item_num,
            "turntable_props_type": self.turntable_props_type,
            "drop_up_ratio": self.drop_up_ratio,
            "weight": self.weight,
            "is_jackpot": self.is_jackpot,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GachaShowItemConfig:
        return cls(
            item_id=int(data["item_id"]),
            item_num=int(data.get("item_num", 1)),
            item_type=int(data.get("item_type", AwardType.ITEM)),
            is_show=bool(data.get("is_show", True)),
            reward_level=int(data.get("reward_level", RareType.NORMAL)),
            repeated_item_id=int(data.get("repeated_item_id", ITEM_FF_TOKEN)),
            repeated_item_num=int(data.get("repeated_item_num", 5)),
            turntable_props_type=int(data.get("turntable_props_type", 0)),
            drop_up_ratio=float(data.get("drop_up_ratio", 0.0)),
            weight=max(1, int(data.get("weight", 100))),
            is_jackpot=bool(data.get("is_jackpot", False)),
        )


# Semantic alias
RewardPoolItem = GachaShowItemConfig


@dataclass
class ExtraRewardConfig:
    """Milestone extra reward based on weekly spin count."""
    cdt_value: int
    reward_id: int
    reward_num: int = 1
    reward_type: int = AwardType.ITEM
    cdt_type: int = 1
    icon: str = ""
    special_reward: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cdt_value": self.cdt_value,
            "reward_id": self.reward_id,
            "reward_num": self.reward_num,
            "reward_type": self.reward_type,
            "cdt_type": self.cdt_type,
            "icon": self.icon,
            "special_reward": self.special_reward,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExtraRewardConfig:
        return cls(
            cdt_value=int(data["cdt_value"]),
            reward_id=int(data["reward_id"]),
            reward_num=int(data.get("reward_num", 1)),
            reward_type=int(data.get("reward_type", AwardType.ITEM)),
            cdt_type=int(data.get("cdt_type", 1)),
            icon=str(data.get("icon", "")),
            special_reward=str(data.get("special_reward", "")),
        )


@dataclass
class LuckyMeterConfig:
    """Configuration for machine lucky meter and jackpot threshold."""
    threshold: int = 150
    rate_increment: int = 1
    reset_on_jackpot: bool = True
    reset_on_rare: bool = True
    jackpot_tier: int = RareType.SUPER_RARE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LuckyMeterConfig:
        return cls(
            threshold=int(data.get("threshold", 150)),
            rate_increment=int(data.get("rate_increment", 1)),
            reset_on_jackpot=bool(data.get("reset_on_jackpot", True)),
            reset_on_rare=bool(data.get("reset_on_rare", True)),
            jackpot_tier=int(data.get("jackpot_tier", RareType.SUPER_RARE)),
        )


@dataclass
class VoucherDefinition:
    """Definition of a Royale Voucher and its relation to machines."""
    voucher_id: int
    chest_id: int
    name: str
    single_cost: int = 1
    multi_cost: int = 10
    alias_ids: Tuple[int, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voucher_id": self.voucher_id,
            "chest_id": self.chest_id,
            "name": self.name,
            "single_cost": self.single_cost,
            "multi_cost": self.multi_cost,
            "alias_ids": list(self.alias_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VoucherDefinition:
        return cls(
            voucher_id=int(data["voucher_id"]),
            chest_id=int(data["chest_id"]),
            name=str(data.get("name", "")),
            single_cost=int(data.get("single_cost", 1)),
            multi_cost=int(data.get("multi_cost", 10)),
            alias_ids=tuple(data.get("alias_ids", ())),
        )


@dataclass
class SpecialExchangeConfig:
    """Incubator forge crafting recipe (Evolution Stones + Blueprints)."""
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forge_tab_id": self.forge_tab_id,
            "tab_name": self.tab_name,
            "item_id": self.item_id,
            "item_num": self.item_num,
            "sort_id": self.sort_id,
            "limited_purchase_times": self.limited_purchase_times,
            "exchange_items": [list(x) for x in self.exchange_items],
            "reward_level": self.reward_level,
            "language": self.language,
            "image_url": self.image_url,
            "real_image_url": self.real_image_url,
            "is_show": self.is_show,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SpecialExchangeConfig:
        return cls(
            forge_tab_id=int(data["forge_tab_id"]),
            tab_name=str(data.get("tab_name", "")),
            item_id=int(data["item_id"]),
            item_num=int(data.get("item_num", 1)),
            sort_id=int(data.get("sort_id", 1)),
            limited_purchase_times=int(data.get("limited_purchase_times", 1)),
            exchange_items=tuple(tuple(x) for x in data.get("exchange_items", ())),
            reward_level=int(data.get("reward_level", RareType.SUPER_RARE)),
            language=str(data.get("language", "en")),
            image_url=str(data.get("image_url", "")),
            real_image_url=str(data.get("real_image_url", "")),
            is_show=bool(data.get("is_show", True)),
        )


# Semantic alias
SpecialExchangeRecipe = SpecialExchangeConfig


# ---------------------------------------------------------------------------
# Machine Configuration Schema (Separating Concerns)
# ---------------------------------------------------------------------------

@dataclass
class ChestConfig:
    """
    Centralized Luck Royale Machine Configuration Schema.
    Separates:
      1. Existence: Registered machine metadata and asset identifiers.
      2. Visibility: Whether machine is shown in client UI tabs.
      3. Availability: Whether machine is active, in maintenance, or scheduled.
      4. Eligibility: Player qualifications (level, VIP, passes).
      5. Spin Authorization: Rules, pricing, limits, and cooldowns.
    """
    # 1. Existence / Core Identifiers
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

    # 2. Visibility Controls
    is_visible: bool = True
    banner_image: str = ""

    # 3. Availability Controls
    is_enabled: bool = True
    state_enum: int = MachineState.ACTIVE
    start_time: int = 0  # 0 = always active
    end_time: int = 0    # 0 = no expiration

    # 4. Eligibility Controls
    min_player_level: int = 1
    requires_elite_pass: bool = False
    min_vip_level: int = 0

    # 5. Spin Authorization Rules
    allow_single_spin: bool = True
    allow_multi_spin: bool = True
    daily_spin_limit: int = 0  # 0 = unlimited

    # -----------------------------------------------------------------------
    # Separation of Concerns: Evaluation Methods
    # -----------------------------------------------------------------------

    def is_available(self, now: Optional[int] = None) -> bool:
        """Check operational availability (active flag and active time window)."""
        if not self.is_enabled or self.state_enum == MachineState.DISABLED:
            return False
        if self.state_enum == MachineState.MAINTENANCE:
            return False
        current = int(now or time.time())
        if self.start_time > 0 and current < self.start_time:
            return False
        if self.end_time > 0 and current > self.end_time:
            return False
        return True

    def is_visible_to(self, player_info: Optional[Dict[str, Any]] = None, now: Optional[int] = None) -> bool:
        """Check client UI visibility condition."""
        if not self.is_visible:
            return False
        current = int(now or time.time())
        if self.end_time > 0 and current > self.end_time:
            return False
        return True

    def check_eligibility(self, player_info: Dict[str, Any]) -> Tuple[bool, str]:
        """Verify whether player meets eligibility requirements to spin."""
        level = int(player_info.get("level", 1))
        if level < self.min_player_level:
            return False, f"Requires player level {self.min_player_level} (current: {level})"
        if self.requires_elite_pass and not bool(player_info.get("has_elite_pass", False)):
            return False, "Requires active Elite Pass"
        return True, "Eligible"

    def authorize_spin(
        self,
        account_id: int,
        gacha_type: int,
        consume_type: int,
        player_state: Dict[str, Any],
        wallet: Dict[str, int],
        inventory: Dict[int, int],
        now: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Authorize whether a spin action is permitted based on availability,
        limits, cooldowns, and player resource balances.
        """
        current = int(now or time.time())
        if not self.is_available(current):
            return False, f"Machine {self.chest_id} is currently unavailable or under maintenance"

        is_multi = gacha_type == LotteryType.SOME
        if is_multi and not self.allow_multi_spin:
            return False, "Multi-spin is not permitted on this machine"
        if not is_multi and not self.allow_single_spin:
            return False, "Single-spin is not permitted on this machine"

        # Check daily spin limit
        if self.daily_spin_limit > 0:
            weekly_spins = int(player_state.get("lottery_count_weekly", 0))
            draws_to_add = self.ten_num if is_multi else self.once_num
            if weekly_spins + draws_to_add > self.daily_spin_limit:
                return False, f"Exceeds daily spin limit of {self.daily_spin_limit}"

        # Check free spin authorization
        if consume_type == ConsumeType.FREE:
            if self.free_type != 1 or is_multi:
                return False, "Free spin not permitted for multi-spin or disabled free type"
            next_free = int(player_state.get("next_free_time", 0))
            if current < next_free:
                return False, f"Free spin on cooldown until {next_free}"
            return True, "Authorized (Free)"

        # Check voucher authorization
        if consume_type == ConsumeType.EXCHANGE_ITEM:
            if not self.exchange_itemid:
                return False, "No voucher configured for this machine"
            need_vouchers = self.exchange_ten_num if is_multi else self.exchange_once_num
            # Check voucher and any aliases
            avail = 0
            for vid in VALID_ITEM_ID_ALIASES.get(self.exchange_itemid, (self.exchange_itemid,)):
                avail += inventory.get(vid, 0)
            if avail < need_vouchers:
                return False, f"Insufficient vouchers: need {need_vouchers}, have {avail}"
            return True, "Authorized (Voucher)"

        # Check currency authorization (MONEY)
        price = (self.discount_price_ten or self.ten_price) if is_multi else (self.discount_price_one or self.once_price)
        if self.coin_type == CoinType.COINS:
            coins = wallet.get("coins", 0)
            if coins < price:
                return False, f"Insufficient Gold: need {price}, have {coins}"
            return True, "Authorized (Gold)"
        elif self.coin_type == CoinType.GEMS:
            gems = wallet.get("gems", 0)
            if gems < price:
                return False, f"Insufficient Diamonds: need {price}, have {gems}"
            return True, "Authorized (Diamonds)"

        return True, "Authorized"

    # -----------------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chest_id": self.chest_id,
            "chest_sub_id": self.chest_sub_id,
            "priority": self.priority,
            "coin_type": self.coin_type,
            "chest_name": self.chest_name,
            "exchange_itemid": self.exchange_itemid,
            "free_type": self.free_type,
            "once_price": self.once_price,
            "ten_price": self.ten_price,
            "exchange_once_num": self.exchange_once_num,
            "exchange_ten_num": self.exchange_ten_num,
            "color_id": self.color_id,
            "chest_model_id": self.chest_model_id,
            "show_model_male": self.show_model_male,
            "show_model_female": self.show_model_female,
            "rare_item_max": self.rare_item_max,
            "chest_type_enum": self.chest_type_enum,
            "forge_tab_id": self.forge_tab_id,
            "once_num": self.once_num,
            "ten_num": self.ten_num,
            "discount_price_one": self.discount_price_one,
            "discount_price_ten": self.discount_price_ten,
            "must_drop": self.must_drop,
            "extra_reward": self.extra_reward,
            "first_reward_switch": self.first_reward_switch,
            "first_reward_max": self.first_reward_max,
            "second_level_count": self.second_level_count,
            "third_level_count": self.third_level_count,
            "chest_activity": self.chest_activity,
            "open_priority_switch": self.open_priority_switch,
            "chest_model_id2": self.chest_model_id2,
            "chest_model_id3": self.chest_model_id3,
            "drop_probability_switch": self.drop_probability_switch,
            "extra_reward_icon": self.extra_reward_icon,
            "chest_hint_color": self.chest_hint_color,
            "extra_reward_reset_day": list(self.extra_reward_reset_day),
            "probabilities": [list(p) for p in self.probabilities],
            "items": [it.to_dict() if hasattr(it, "to_dict") else asdict(it) for it in self.items],
            "extra_rewards": [er.to_dict() if hasattr(er, "to_dict") else asdict(er) for er in self.extra_rewards],
            "is_visible": self.is_visible,
            "banner_image": self.banner_image,
            "is_enabled": self.is_enabled,
            "state_enum": self.state_enum,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "min_player_level": self.min_player_level,
            "requires_elite_pass": self.requires_elite_pass,
            "min_vip_level": self.min_vip_level,
            "allow_single_spin": self.allow_single_spin,
            "allow_multi_spin": self.allow_multi_spin,
            "daily_spin_limit": self.daily_spin_limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChestConfig:
        items = tuple(
            GachaShowItemConfig.from_dict(it) if isinstance(it, dict) else it
            for it in data.get("items", ())
        )
        extra_rewards = tuple(
            ExtraRewardConfig.from_dict(er) if isinstance(er, dict) else er
            for er in data.get("extra_rewards", ())
        )
        probabilities = tuple(
            tuple(p) for p in data.get("probabilities", ((RareType.SUPER_RARE, 2), (RareType.RARE, 18), (RareType.NORMAL, 80)))
        )
        reset_days = tuple(data.get("extra_reward_reset_day", (1,)))

        return cls(
            chest_id=int(data["chest_id"]),
            chest_sub_id=int(data.get("chest_sub_id", 0)),
            priority=int(data.get("priority", 100)),
            coin_type=int(data.get("coin_type", CoinType.GEMS)),
            chest_name=str(data.get("chest_name", "")),
            exchange_itemid=int(data.get("exchange_itemid", 0)),
            free_type=int(data.get("free_type", 0)),
            once_price=int(data.get("once_price", 0)),
            ten_price=int(data.get("ten_price", 0)),
            exchange_once_num=int(data.get("exchange_once_num", 1)),
            exchange_ten_num=int(data.get("exchange_ten_num", 10)),
            color_id=int(data.get("color_id", 1)),
            chest_model_id=int(data.get("chest_model_id", 0)),
            show_model_male=int(data.get("show_model_male", 0)),
            show_model_female=int(data.get("show_model_female", 0)),
            rare_item_max=int(data.get("rare_item_max", 150)),
            chest_type_enum=int(data.get("chest_type_enum", ChestTabType.NORMAL)),
            forge_tab_id=int(data.get("forge_tab_id", 0)),
            once_num=int(data.get("once_num", 1)),
            ten_num=int(data.get("ten_num", 10)),
            discount_price_one=int(data.get("discount_price_one", 0)),
            discount_price_ten=int(data.get("discount_price_ten", 0)),
            must_drop=bool(data.get("must_drop", True)),
            extra_reward=bool(data.get("extra_reward", True)),
            first_reward_switch=bool(data.get("first_reward_switch", False)),
            first_reward_max=int(data.get("first_reward_max", 3)),
            second_level_count=int(data.get("second_level_count", 40)),
            third_level_count=int(data.get("third_level_count", 90)),
            chest_activity=int(data.get("chest_activity", 2)),
            open_priority_switch=int(data.get("open_priority_switch", 0)),
            chest_model_id2=int(data.get("chest_model_id2", 0)),
            chest_model_id3=int(data.get("chest_model_id3", 0)),
            drop_probability_switch=bool(data.get("drop_probability_switch", True)),
            extra_reward_icon=int(data.get("extra_reward_icon", 2)),
            chest_hint_color=int(data.get("chest_hint_color", 0)),
            extra_reward_reset_day=reset_days,
            items=items,
            extra_rewards=extra_rewards,
            probabilities=probabilities,
            is_visible=bool(data.get("is_visible", True)),
            banner_image=str(data.get("banner_image", "")),
            is_enabled=bool(data.get("is_enabled", True)),
            state_enum=int(data.get("state_enum", MachineState.ACTIVE)),
            start_time=int(data.get("start_time", 0)),
            end_time=int(data.get("end_time", 0)),
            min_player_level=int(data.get("min_player_level", 1)),
            requires_elite_pass=bool(data.get("requires_elite_pass", False)),
            min_vip_level=int(data.get("min_vip_level", 0)),
            allow_single_spin=bool(data.get("allow_single_spin", True)),
            allow_multi_spin=bool(data.get("allow_multi_spin", True)),
            daily_spin_limit=int(data.get("daily_spin_limit", 0)),
        )


# Semantic alias
MachineConfig = ChestConfig


# ---------------------------------------------------------------------------
# Reward Pool Wrapper (Machine Isolation & Weighted Drops)
# ---------------------------------------------------------------------------

class RewardPool:
    """Isolated reward pool for a single machine with weighted probability math."""

    def __init__(self, chest_id: int, items: Sequence[GachaShowItemConfig]) -> None:
        self.chest_id = chest_id
        self._items = tuple(items)

    @property
    def items(self) -> Tuple[GachaShowItemConfig, ...]:
        return self._items

    def get_items_by_tier(self, tier: int) -> List[GachaShowItemConfig]:
        return [it for it in self._items if it.reward_level == tier]

    def get_super_rare_items(self) -> List[GachaShowItemConfig]:
        return self.get_items_by_tier(RareType.SUPER_RARE)

    def get_rare_items(self) -> List[GachaShowItemConfig]:
        return self.get_items_by_tier(RareType.RARE)

    def get_normal_items(self) -> List[GachaShowItemConfig]:
        return self.get_items_by_tier(RareType.NORMAL)

    def calculate_tier_probabilities(self) -> List[Tuple[int, int]]:
        """Calculate percentage probabilities per rarity tier based on item weights."""
        total_weight = sum(it.weight for it in self._items)
        if total_weight <= 0:
            return [(RareType.SUPER_RARE, 2), (RareType.RARE, 18), (RareType.NORMAL, 80)]

        tier_weights: Dict[int, int] = {
            RareType.SUPER_RARE: sum(it.weight for it in self.get_super_rare_items()),
            RareType.RARE: sum(it.weight for it in self.get_rare_items()),
            RareType.NORMAL: sum(it.weight for it in self.get_normal_items()),
        }
        res: List[Tuple[int, int]] = []
        for tier in (RareType.SUPER_RARE, RareType.RARE, RareType.NORMAL):
            pct = round((tier_weights[tier] / total_weight) * 100)
            res.append((tier, max(1, pct) if tier_weights[tier] > 0 else 0))
        return res

    def roll_item(
        self,
        rng: Optional[random.Random] = None,
        force_tier: Optional[int] = None,
    ) -> GachaShowItemConfig:
        """Roll a reward from this isolated pool according to item weights."""
        r = rng or random
        pool = list(self._items)
        if force_tier is not None:
            filtered = [it for it in pool if it.reward_level >= force_tier]
            if filtered:
                pool = filtered

        weights = [max(1, it.weight) for it in pool]
        return r.choices(pool, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Player Gacha State Model
# ---------------------------------------------------------------------------

@dataclass
class GachaPlayerState:
    """Per-account, per-chest runtime and persistent state."""
    account_id: int
    chest_id: int
    lottery_count_weekly: int = 0
    exchanged_reward_list: List[int] = field(default_factory=list)
    next_free_time: int = 0
    not_got_num: int = 0  # Lucky meter
    limit_purchase_count_one: int = 0
    limit_purchase_count_ten: int = 0
    first_draw_reward_num: int = 0
    updated_at: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "chest_id": self.chest_id,
            "lottery_count_weekly": self.lottery_count_weekly,
            "exchanged_reward_list": list(self.exchanged_reward_list),
            "next_free_time": self.next_free_time,
            "not_got_num": self.not_got_num,
            "limit_purchase_count_one": self.limit_purchase_count_one,
            "limit_purchase_count_ten": self.limit_purchase_count_ten,
            "first_draw_reward_num": self.first_draw_reward_num,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], account_id: int = 0, chest_id: int = 0) -> GachaPlayerState:
        return cls(
            account_id=int(data.get("account_id", account_id)),
            chest_id=int(data.get("chest_id", chest_id)),
            lottery_count_weekly=int(data.get("lottery_count_weekly", 0)),
            exchanged_reward_list=list(data.get("exchanged_reward_list", [])),
            next_free_time=int(data.get("next_free_time", 0)),
            not_got_num=int(data.get("not_got_num", 0)),
            limit_purchase_count_one=int(data.get("limit_purchase_count_one", 0)),
            limit_purchase_count_ten=int(data.get("limit_purchase_count_ten", 0)),
            first_draw_reward_num=int(data.get("first_draw_reward_num", 0)),
            updated_at=int(data.get("updated_at", 0)),
        )


# ---------------------------------------------------------------------------
# Shared DTOs and Result Contracts
# ---------------------------------------------------------------------------

@dataclass
class SpinRequest:
    account_id: int
    chest_id: int
    gacha_type: int = LotteryType.ONE
    consume_type: int = ConsumeType.MONEY


@dataclass
class DropItem:
    origin_award_type: int
    origin_award_id: int
    origin_award_num: int
    dest_award_type: int
    dest_award_id: int
    dest_award_num: int
    reward_level: int
    is_duplicate: bool = False


@dataclass
class SpinResult:
    chest_id: int
    lottery_goods: List[DropItem]
    extra_one_goods: List[DropItem]
    lottery_count_weekly: int
    next_free_time: int
    not_got_num: int
    has_big_reward: bool
    cost_paid: Dict[str, Any]
    exchange_item_num: int = 0


@dataclass
class CostDeductionResult:
    success: bool
    cost_type: CostType
    amount_deducted: int
    voucher_id_used: int = 0
    message: str = ""


@dataclass
class ForgeExchangeResult:
    success: bool
    forge_tab_id: int
    item_id: int
    count: int
    consumed_materials: List[Dict[str, int]]
    purchase_times: int
    trans_id: int
    error_message: str = ""


@dataclass
class OverviewStatsDTO:
    active_machines: int
    total_spins: int
    diamonds_spent: int
    gold_spent: int
    vouchers_consumed: int
    jackpots_awarded: int


# ---------------------------------------------------------------------------
# Abstract Service Contracts (ABCs for Swarm Collaboration)
# ---------------------------------------------------------------------------

class IGachaEngine(abc.ABC):
    """Abstract contract for server-authoritative gacha spin execution."""

    @abc.abstractmethod
    def spin(self, req: SpinRequest) -> SpinResult:
        """Execute server-authoritative single or multi-spin."""
        ...

    @abc.abstractmethod
    def calculate_drop(
        self,
        cfg: ChestConfig,
        state: GachaPlayerState,
        force_rare: bool = False,
    ) -> GachaShowItemConfig:
        """Authoritatively roll a reward from the machine's isolated pool."""
        ...

    @abc.abstractmethod
    def process_duplicate(
        self,
        item: GachaShowItemConfig,
        account_id: int,
    ) -> Tuple[int, int, bool]:
        """Convert duplicate owned item to FF tokens according to rarity rate."""
        ...


class IEconomyService(abc.ABC):
    """Abstract contract for currency, voucher deduction, and Incubator forge."""

    @abc.abstractmethod
    def validate_and_deduct_cost(
        self,
        account_id: int,
        cfg: ChestConfig,
        gacha_type: int,
        consume_type: int,
        rec: Dict[str, Any],
        now: int,
    ) -> CostDeductionResult:
        """Atomically validate balance and deduct appropriate currency or voucher."""
        ...

    @abc.abstractmethod
    def execute_special_exchange(
        self,
        account_id: int,
        forge_tab_id: int,
        item_id: int,
        count: int,
    ) -> ForgeExchangeResult:
        """Verify blueprint + stone materials and craft Incubator bundles."""
        ...

    @abc.abstractmethod
    def get_voucher_balance(self, account_id: int, chest_id: int) -> int:
        """Get player's current voucher count for a specific machine."""
        ...


class ILuckRoyaleAdminService(abc.ABC):
    """Abstract contract for administrative dashboard management."""

    @abc.abstractmethod
    def get_overview(self) -> Dict[str, Any]:
        """Get summary statistics of Luck Royale operation."""
        ...

    @abc.abstractmethod
    def list_machines(self) -> List[Dict[str, Any]]:
        """List all machines with active/disabled statuses and pricing."""
        ...

    @abc.abstractmethod
    def update_machine(self, machine_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create or update a machine configuration."""
        ...

    @abc.abstractmethod
    def update_reward_pool(self, chest_id: int, items_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Update items and probabilities for a machine's reward pool."""
        ...

    @abc.abstractmethod
    def adjust_lucky_meter(self, account_id: int, chest_id: int, value: int) -> Tuple[bool, str]:
        """Manually adjust a player's lucky meter value."""
        ...

    @abc.abstractmethod
    def get_transactions(
        self,
        account_id: Optional[int] = None,
        chest_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query gacha transaction audit history."""
        ...


class ILuckRoyaleRegistry(abc.ABC):
    """Abstract contract for centralized machine registry."""

    @abc.abstractmethod
    def get_machine(self, chest_id: int) -> Optional[ChestConfig]:
        """Retrieve a machine configuration by ID."""
        ...

    @abc.abstractmethod
    def get_all_machines(self) -> List[ChestConfig]:
        """Get all registered machines."""
        ...

    @abc.abstractmethod
    def get_visible_machines(self, account_id: int = 0) -> List[ChestConfig]:
        """Get all machines currently visible to players."""
        ...

    @abc.abstractmethod
    def register_machine(self, cfg: ChestConfig) -> None:
        """Register or overwrite a machine configuration."""
        ...


# ---------------------------------------------------------------------------
# Default Authentic OB17 Catalogs
# ---------------------------------------------------------------------------

def build_default_chest_configs() -> Dict[int, ChestConfig]:
    """Build the authentic OB17 Luck Royale machine catalog."""
    return {
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
                GachaShowItemConfig(ITEM_MAGIC_CUBE, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_MAGIC_CUBE, 1, weight=2, is_jackpot=True),
                GachaShowItemConfig(710000401, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4, is_jackpot=True),
                GachaShowItemConfig(710000400, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4, is_jackpot=True),
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
                GachaShowItemConfig(907001611, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4, is_jackpot=True),
                GachaShowItemConfig(907001612, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=4, is_jackpot=True),
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
                GachaShowItemConfig(710000422, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=3, is_jackpot=True),
                GachaShowItemConfig(710000423, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_FF_TOKEN, 10, weight=3, is_jackpot=True),
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
                GachaShowItemConfig(ITEM_BLUEPRINT_YINYANG, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_BLUEPRINT_YINYANG, 1, turntable_props_type=1, weight=6, is_jackpot=True),
                GachaShowItemConfig(ITEM_EVOLUTION_STONE, 1, AwardType.ITEM, True, RareType.RARE, ITEM_EVOLUTION_STONE, 1, turntable_props_type=2, weight=14),
                GachaShowItemConfig(ITEM_BLUEPRINT_JOKER, 1, AwardType.ITEM, True, RareType.SUPER_RARE, ITEM_BLUEPRINT_JOKER, 1, turntable_props_type=1, weight=6, is_jackpot=True),
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


def build_default_special_exchanges() -> List[SpecialExchangeConfig]:
    """Build authentic Incubator forge crafting recipes."""
    return [
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
# Schema Validation
# ---------------------------------------------------------------------------

def validate_machine_config(cfg: ChestConfig) -> Tuple[bool, List[str]]:
    """Validate a machine configuration for consistency and completeness."""
    errors: List[str] = []
    if cfg.chest_id <= 0:
        errors.append("chest_id must be a positive integer")
    if not cfg.chest_name:
        errors.append("chest_name cannot be empty")
    if cfg.coin_type not in (CoinType.NONE, CoinType.COINS, CoinType.GEMS):
        errors.append(f"Invalid coin_type: {cfg.coin_type}")
    if cfg.once_price < 0 or cfg.ten_price < 0:
        errors.append("Prices cannot be negative")
    if not cfg.items:
        errors.append("Machine must have at least one reward in its reward pool")
    for idx, item in enumerate(cfg.items):
        if item.item_id <= 0:
            errors.append(f"Item #{idx}: item_id must be a positive integer")
        if item.weight <= 0:
            errors.append(f"Item #{idx} ({item.item_id}): weight must be positive")
    return len(errors) == 0, errors


def validate_catalog_dict(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate raw JSON dictionary before loading or saving to file."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return False, ["Root configuration must be a JSON object"]
    if "machines" not in data or not isinstance(data["machines"], list):
        errors.append("Configuration must contain a 'machines' list")
    else:
        for m_data in data["machines"]:
            if not isinstance(m_data, dict) or "chest_id" not in m_data:
                errors.append("Each machine entry must be an object with 'chest_id'")
    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Centralized Persistence Manager: JSON File Layer (Atomic & Versioned)
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "luck_royale_config.json",
)


class LuckRoyaleConfigManager:
    """
    Thread-safe, atomic file persistence manager for Luck Royale configurations.
    Features:
      - Atomic write via temporary file and replace (crash/corruption proof).
      - Strict schema validation on save and load.
      - Schema versioning and modification tracking.
      - Hot reload support.
    """

    SCHEMA_VERSION = "1.39.0"

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = os.path.abspath(config_path)
        self._lock = threading.RLock()
        self._version = 1
        self._last_modified = int(time.time())
        self._machines: Dict[int, ChestConfig] = {}
        self._special_exchanges: List[SpecialExchangeConfig] = []
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        with self._lock:
            if os.path.exists(self.config_path):
                ok = self.load_config(self.config_path)
                if not ok:
                    logger.warning("Failed to load %s; initializing default catalog", self.config_path)
                    self._initialize_defaults()
                    self.save_config()
            else:
                self._initialize_defaults()
                self.save_config()

    def _initialize_defaults(self) -> None:
        self._machines = build_default_chest_configs()
        self._special_exchanges = build_default_special_exchanges()
        self._version = 1
        self._last_modified = int(time.time())

    def load_config(self, path: Optional[str] = None) -> bool:
        """Load configuration from JSON file with validation."""
        target_path = path or self.config_path
        with self._lock:
            try:
                if not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
                    return False
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                ok, errors = validate_catalog_dict(data)
                if not ok:
                    logger.error("Config validation errors in %s: %s", target_path, errors)
                    return False

                new_machines: Dict[int, ChestConfig] = {}
                for m_dict in data.get("machines", []):
                    cfg = ChestConfig.from_dict(m_dict)
                    new_machines[cfg.chest_id] = cfg

                new_exchanges: List[SpecialExchangeConfig] = []
                for ex_dict in data.get("special_exchanges", []):
                    new_exchanges.append(SpecialExchangeConfig.from_dict(ex_dict))

                self._machines = new_machines
                self._special_exchanges = new_exchanges
                self._version = int(data.get("version", 1))
                self._last_modified = int(data.get("last_modified", int(time.time())))
                logger.info("Successfully loaded Luck Royale config v%s (%d machines)", self._version, len(self._machines))
                return True
            except Exception as e:
                logger.exception("Error loading Luck Royale config from %s: %s", target_path, e)
                return False

    def save_config(self, path: Optional[str] = None) -> bool:
        """Atomically save configuration to JSON file with atomic rename."""
        target_path = path or self.config_path
        with self._lock:
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                self._version += 1
                self._last_modified = int(time.time())

                catalog_dict = self.to_dict()
                ok, errors = validate_catalog_dict(catalog_dict)
                if not ok:
                    logger.error("Cannot save invalid catalog dict: %s", errors)
                    return False

                # Atomic write using temp file in same directory
                dir_name = os.path.dirname(target_path)
                with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                    json.dump(catalog_dict, tf, indent=2, ensure_ascii=False)
                    temp_name = tf.name

                os.replace(temp_name, target_path)
                logger.info("Atomically saved Luck Royale config v%d to %s", self._version, target_path)
                return True
            except Exception as e:
                logger.exception("Error saving Luck Royale config to %s: %s", target_path, e)
                return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete Luck Royale catalog to dictionary."""
        with self._lock:
            return {
                "schema_version": self.SCHEMA_VERSION,
                "version": self._version,
                "last_modified": self._last_modified,
                "machines": [cfg.to_dict() for cfg in sorted(self._machines.values(), key=lambda c: (-c.priority, c.chest_id))],
                "special_exchanges": [ex.to_dict() for ex in self._special_exchanges],
            }

    # Machine Accessors
    def get_machine(self, chest_id: int) -> Optional[ChestConfig]:
        with self._lock:
            return self._machines.get(int(chest_id))

    def get_all_machines(self) -> Dict[int, ChestConfig]:
        with self._lock:
            return dict(self._machines)

    def set_machine(self, cfg: ChestConfig) -> None:
        with self._lock:
            self._machines[cfg.chest_id] = cfg
            self.save_config()

    def remove_machine(self, chest_id: int) -> bool:
        with self._lock:
            if int(chest_id) in self._machines:
                del self._machines[int(chest_id)]
                self.save_config()
                return True
            return False

    # Special Exchange Accessors
    def get_special_exchanges(self) -> List[SpecialExchangeConfig]:
        with self._lock:
            return list(self._special_exchanges)

    def set_special_exchanges(self, exchanges: Sequence[SpecialExchangeConfig]) -> None:
        with self._lock:
            self._special_exchanges = list(exchanges)
            self.save_config()


# Global Singleton Persistence Manager
config_manager = LuckRoyaleConfigManager()


# ---------------------------------------------------------------------------
# Centralized In-Memory Registry (Thread-Safe)
# ---------------------------------------------------------------------------

class LuckRoyaleRegistry(ILuckRoyaleRegistry):
    """
    Centralized in-memory registry for Luck Royale machines,
    reward pools, vouchers, and Incubator forge recipes.
    """

    def __init__(self, manager: Optional[LuckRoyaleConfigManager] = None) -> None:
        self._manager = manager or config_manager
        self._lock = threading.RLock()

    def get_machine(self, chest_id: int) -> Optional[ChestConfig]:
        return self._manager.get_machine(int(chest_id))

    def get_all_machines(self) -> List[ChestConfig]:
        return list(self._manager.get_all_machines().values())

    def get_visible_machines(self, account_id: int = 0) -> List[ChestConfig]:
        now = int(time.time())
        with self._lock:
            return [
                cfg for cfg in self._manager.get_all_machines().values()
                if cfg.is_visible_to(now=now)
            ]

    def get_active_machines(self) -> List[ChestConfig]:
        now = int(time.time())
        with self._lock:
            return [
                cfg for cfg in self._manager.get_all_machines().values()
                if cfg.is_available(now=now)
            ]

    def register_machine(self, cfg: ChestConfig) -> None:
        self._manager.set_machine(cfg)

    def unregister_machine(self, chest_id: int) -> bool:
        return self._manager.remove_machine(int(chest_id))

    def get_reward_pool(self, chest_id: int) -> Optional[RewardPool]:
        cfg = self.get_machine(chest_id)
        if cfg is None:
            return None
        return RewardPool(cfg.chest_id, cfg.items)

    def get_special_exchanges(self) -> List[SpecialExchangeConfig]:
        return self._manager.get_special_exchanges()

    def get_special_exchange_by_tab_item(self, forge_tab_id: int, item_id: int) -> Optional[SpecialExchangeConfig]:
        for ex in self.get_special_exchanges():
            if ex.forge_tab_id == int(forge_tab_id) and ex.item_id == int(item_id):
                return ex
        return None


# Global Singleton Registry
registry = LuckRoyaleRegistry(config_manager)


# ---------------------------------------------------------------------------
# Backward-Compatible Dynamic Accessors (CHEST_CONFIGS & DEFAULT_SPECIAL_EXCHANGES)
# ---------------------------------------------------------------------------

class _DynamicChestConfigs(dict):
    """
    Transparent dictionary proxy exposing active registry machines.
    Guarantees full backward compatibility with any legacy code importing CHEST_CONFIGS.
    """
    def __getitem__(self, key: Any) -> ChestConfig:
        cfg = registry.get_machine(int(key))
        if cfg is None:
            raise KeyError(key)
        return cfg

    def get(self, key: Any, default: Any = None) -> Any:
        cfg = registry.get_machine(int(key))
        return cfg if cfg is not None else default

    def __contains__(self, key: Any) -> bool:
        return registry.get_machine(int(key)) is not None

    def __iter__(self):
        return iter(registry.get_all_machines()[i].chest_id for i in range(len(registry.get_all_machines())))

    def __len__(self) -> int:
        return len(registry.get_all_machines())

    def keys(self):
        return [c.chest_id for c in registry.get_all_machines()]

    def values(self):
        return registry.get_all_machines()

    def items(self):
        return [(c.chest_id, c) for c in registry.get_all_machines()]


CHEST_CONFIGS = _DynamicChestConfigs()


class _DynamicSpecialExchanges(list):
    """
    Transparent list proxy exposing active registry forge recipes.
    Guarantees full backward compatibility with any legacy code importing DEFAULT_SPECIAL_EXCHANGES.
    """
    def __iter__(self):
        return iter(registry.get_special_exchanges())

    def __len__(self) -> int:
        return len(registry.get_special_exchanges())

    def __getitem__(self, idx: Any) -> Any:
        return registry.get_special_exchanges()[idx]


DEFAULT_SPECIAL_EXCHANGES = _DynamicSpecialExchanges()


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
# Response Encoders (CS*Res)
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
    chests = list(configs) if configs is not None else registry.get_visible_machines()
    chests.sort(key=lambda c: (-c.priority, c.chest_id))
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
    items = list(entries) if entries is not None else registry.get_special_exchanges()
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
