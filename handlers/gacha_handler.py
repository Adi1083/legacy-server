"""Luck Royale / Gacha HTTP endpoint handlers and server-authoritative engine for Free Fire 1.39 (IND PROJECT).

Owns:
1. Server-side spin execution and reward pipeline.
2. Single spins (1x) and multi-spins (5x, 10x, 11x depending on machine config).
3. Server-authoritative random reward selection (never trust client-supplied IDs).
4. Machine-specific reward pool isolation (prevent cross-machine reward contamination).
5. Lucky meter progression, reset upon grand prize drop, and guaranteed jackpot triggering.
6. Duplicate reward detection and automatic FF Token conversion (configured token rates per rarity).
7. Atomic inventory injection into core.state with failure rollback and concurrency protection (RLock).
8. Transaction idempotency, spin history logging, and admin API helpers.
"""

from __future__ import annotations

import collections
import copy
import json
import logging
import random
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.database import db
from core.state import DEFAULT_ACCOUNT_ID, state
from proto.character_models import (
    AVATAR_CATALOG,
    AVATAR_TO_DEBRIS_MAP,
    STARTER_AVATAR_IDS,
    get_character_debris_id,
)
from proto.gacha_models import (
    CHEST_CONFIGS,
    CHEST_DIAMOND_ROYALE,
    CHEST_GOLD_ROYALE,
    CHEST_INCUBATOR,
    CHEST_WEAPON_ROYALE,
    DEFAULT_SPECIAL_EXCHANGES,
    FREE_COOLDOWN_SECONDS,
    IEconomyService,
    ITEM_BLUEPRINT_JOKER,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
    ITEM_MAGIC_CUBE,
    VOUCHER_ALIASES,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
    ChestConfig,
    ChestTabType,
    CoinType,
    ConsumeType,
    CostDeductionResult,
    CostType,
    ExtraRewardConfig,
    ForgeExchangeResult,
    GachaShowItemConfig,
    IEconomyService,
    LotteryType,
    RareType,
    SpecialExchangeConfig,
    decode_do_gacha_special_exchange_req,
    decode_get_gacha_special_exchange_desc_req,
    decode_get_lottery_probability_req,
    decode_lottery_extra_reward_req,
    decode_lottery_req,
    encode_do_gacha_special_exchange_res,
    encode_exchange_gacha_extra_reward_res,
    encode_get_gacha_desc_res,
    encode_get_gacha_info_res,
    encode_get_gacha_special_exchange_desc_res,
    encode_get_lottery_probability_res,
    encode_lottery_res,
    resolve_canonical_item_id,
)
from proto.store_models import AwardType

logger = logging.getLogger("gacha_handler")

# ---------------------------------------------------------------------------
# Stackable Prefixes & Item Aliases (OB17 CSV & Coordinator Contract Support)
# ---------------------------------------------------------------------------

_STACKABLE_PREFIXES = (800, 802, 804, 808, 1101, 1102, 1307)

# Configured default FF Token conversion rates by rarity
DEFAULT_DUPLICATE_TOKEN_RATES: Dict[int, int] = {
    RareType.SUPER_RARE: 10,
    RareType.RARE: 5,
    RareType.NORMAL: 2,
}

_INITIAL_GACHA_STOCK: Dict[int, int] = {
    VOUCHER_GOLD_ROYALE: 10,
    VOUCHER_DIAMOND_ROYALE: 10,
    VOUCHER_WEAPON_ROYALE: 10,
    VOUCHER_INCUBATOR: 10,
    ITEM_EVOLUTION_STONE: 10,
    ITEM_BLUEPRINT_YINYANG: 5,
    ITEM_BLUEPRINT_JOKER: 5,
    # Also seed legacy aliases so both catalog conventions are fulfilled
    802000000: 10,
    802000001: 10,
    802000008: 10,
    802000009: 10,
    808000001: 10,
    808000011: 5,
    808000012: 5,
    800000301: 20,
}

_SPECIAL_EXCHANGE_INDEX: Dict[Tuple[int, int], SpecialExchangeConfig] = {
    (cfg.forge_tab_id, cfg.item_id): cfg for cfg in DEFAULT_SPECIAL_EXCHANGES
}


def _is_stackable_item(item_id: int) -> bool:
    """Return True if item_id is stackable/consumable (never converts to duplicates)."""
    iid = int(item_id)
    if (iid // 1_000_000) in _STACKABLE_PREFIXES:
        return True
    if (iid // 10_000) in (1101, 1102):
        return True
    if iid in (
        ITEM_FF_TOKEN,
        ITEM_EVOLUTION_STONE,
        ITEM_BLUEPRINT_YINYANG,
        ITEM_BLUEPRINT_JOKER,
        808000001,
        808000002,
        808000003,
        800000301,
        110200001,
    ):
        return True
    return False


def _get_item_count_with_alias(item_id: int, account_id: int = DEFAULT_ACCOUNT_ID) -> int:
    """Retrieve item count for an account, checking both the ID and any registered alias."""
    iid = int(item_id)
    cnt = state.get_item_count(iid, account_id=account_id)
    if cnt > 0:
        return cnt
    alias = VOUCHER_ALIASES.get(iid)
    if alias is not None:
        cnt = state.get_item_count(alias, account_id=account_id)
        if cnt > 0:
            return cnt
    # Fallback to default account if testing with an unsynced transient account
    if account_id != DEFAULT_ACCOUNT_ID:
        cnt_def = state.get_item_count(iid, account_id=DEFAULT_ACCOUNT_ID)
        if cnt_def > 0:
            return cnt_def
        if alias is not None:
            cnt_def_alias = state.get_item_count(alias, account_id=DEFAULT_ACCOUNT_ID)
            if cnt_def_alias > 0:
                return cnt_def_alias
    return 0


def _consume_inventory_items(
    requirements: Sequence[Tuple[int, int]],
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> Tuple[bool, List[Dict[str, int]]]:
    """Atomically verify and deduct required stackable items from core.state for account_id."""
    with state._lock:
        resolved_reqs: List[Tuple[int, int]] = []
        for item_id, need in requirements:
            iid = int(item_id)
            req_qty = int(need)
            if state.get_item_count(iid, account_id=account_id) >= req_qty:
                resolved_reqs.append((iid, req_qty))
            else:
                alias = VOUCHER_ALIASES.get(iid)
                if alias and state.get_item_count(alias, account_id=account_id) >= req_qty:
                    resolved_reqs.append((alias, req_qty))
                elif (
                    account_id != DEFAULT_ACCOUNT_ID
                    and state.get_item_count(iid, account_id=DEFAULT_ACCOUNT_ID) >= req_qty
                ):
                    resolved_reqs.append((iid, req_qty))
                else:
                    return False, []

        consumed: List[Dict[str, int]] = []
        for iid, qty in resolved_reqs:
            cur = state.get_item_count(iid, account_id=account_id)
            rem = cur - qty
            if rem <= 0:
                state.lock_item(iid, account_id=account_id)
                if account_id == DEFAULT_ACCOUNT_ID:
                    state._unlocked_items.discard(iid)
                    state._item_counts.pop(iid, None)
            else:
                state._item_counts[iid] = rem
                try:
                    from core.player import player_manager

                    p = player_manager.get_player(account_id)
                    if p:
                        p._inventory[iid] = rem
                except Exception:
                    pass
                try:
                    db.save_inventory_item(account_id, iid, rem)
                except Exception:
                    pass

            # Sync fallback state if applicable
            if account_id != DEFAULT_ACCOUNT_ID and state.get_item_count(iid, account_id=DEFAULT_ACCOUNT_ID) > 0:
                cur_def = state.get_item_count(iid, account_id=DEFAULT_ACCOUNT_ID)
                rem_def = max(0, cur_def - qty)
                if rem_def <= 0:
                    state._unlocked_items.discard(iid)
                    state._item_counts.pop(iid, None)
                else:
                    state._item_counts[iid] = rem_def

            consumed.append({"item_id": iid, "cnt": qty})
        return True, consumed


# ---------------------------------------------------------------------------
# Rollback Journal for Atomic State & Inventory Injection
# ---------------------------------------------------------------------------

class SpinRollbackJournal:
    """Tracks state mutations within a spin transaction to rollback atomically if an error occurs."""

    def __init__(self, account_id: int) -> None:
        self.account_id = account_id
        self.coins_spent: int = 0
        self.gems_spent: int = 0
        self.vouchers_consumed: List[Tuple[int, int]] = []
        self.items_added: List[Tuple[int, int, bool]] = []  # (item_id, count, was_new_unlock)
        self.chest_record_backup: Optional[Dict[str, Any]] = None

    def rollback(self, chest_record: Optional[Dict[str, Any]] = None) -> None:
        """Rollback all recorded in-memory mutations across state and chest record."""
        try:
            with state._lock:
                # 1. Refund spent currencies using state modify helpers
                if self.coins_spent > 0:
                    state.modify_gold(self.account_id, self.coins_spent)
                if self.gems_spent > 0:
                    state.modify_diamond(self.account_id, self.gems_spent)

                # 2. Refund consumed vouchers
                for iid, qty in self.vouchers_consumed:
                    state.add_item(iid, qty, account_id=self.account_id)

                # 3. Rollback granted items
                for iid, qty, was_new in self.items_added:
                    if was_new:
                        state.lock_item(iid, account_id=self.account_id)
                    else:
                        cur = state.get_item_count(iid, account_id=self.account_id)
                        rem = max(0, cur - qty)
                        if rem <= 0:
                            state.lock_item(iid, account_id=self.account_id)
                        else:
                            state._item_counts[iid] = rem

                # 4. Restore chest state record
                if self.chest_record_backup is not None and chest_record is not None:
                    chest_record.clear()
                    chest_record.update(self.chest_record_backup)

            logger.info("Spin rollback completed successfully for account %s", self.account_id)
        except Exception as ex:
            logger.error("Error during spin rollback for account %s: %s", self.account_id, ex)


# ---------------------------------------------------------------------------
# Gacha Service Engine
# ---------------------------------------------------------------------------

class GachaService:
    """Thread-safe, server-authoritative Luck Royale and Gacha engine."""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._lock = threading.RLock()
        self._rng = rng or random.Random()
        self._seeded_accounts: Set[int] = set()
        # account_id -> chest_id -> dict state
        self._chest_state: Dict[int, Dict[int, Dict[str, Any]]] = {}
        # account_id -> (forge_tab_id, item_id) -> purchase_times
        self._special_purchases: Dict[int, Dict[Tuple[int, int], int]] = {}
        self._trans_counter = int(time.time() * 1000) % 90000000 + 10000000
        # In-memory transaction idempotency cache: key -> res_bytes
        self._idempotency_cache: Dict[str, bytes] = {}
        # In-memory spin history ring buffer for rapid admin API querying
        self._spin_history: collections.deque[Dict[str, Any]] = collections.deque(maxlen=1000)

    def _next_trans_id(self) -> int:
        self._trans_counter += 1
        return self._trans_counter

    def _ensure_seeded(self, account_id: int) -> None:
        """Seed account inventory and restore persisted gacha state from SQLite."""
        if account_id in self._seeded_accounts:
            return
        saved_states = db.get_all_gacha_states(account_id)
        if saved_states:
            acct_state = self._chest_state.setdefault(account_id, {})
            for cid, sdict in saved_states.items():
                acct_state[cid] = {
                    "lottery_count_weekly": int(sdict.get("lottery_count_weekly", 0)),
                    "exchanged_reward_list": list(sdict.get("exchanged_reward_list", [])),
                    "next_free_time": int(sdict.get("next_free_time", 0)),
                    "not_got_num": int(sdict.get("not_got_num", 0)),
                    "limit_purchase_count_one": int(sdict.get("limit_purchase_count_one", 0)),
                    "limit_purchase_count_ten": int(sdict.get("limit_purchase_count_ten", 0)),
                    "first_draw_reward_num": int(sdict.get("first_draw_reward_num", 0)),
                }

        # Seed initial vouchers and materials for this account
        for iid, qty in _INITIAL_GACHA_STOCK.items():
            if state.get_item_count(iid, account_id=account_id) == 0:
                state.add_item(iid, qty, account_id=account_id)
            if state.get_item_count(iid, account_id=DEFAULT_ACCOUNT_ID) == 0:
                state.add_item(iid, qty, account_id=DEFAULT_ACCOUNT_ID)

        self._seeded_accounts.add(account_id)

    def _get_chest_record(self, account_id: int, chest_id: int) -> Dict[str, Any]:
        """Get or initialize thread-safe chest record for (account_id, chest_id)."""
        acct = self._chest_state.setdefault(account_id, {})
        rec = acct.get(chest_id)
        if rec is None:
            rec = {
                "lottery_count_weekly": 0,
                "exchanged_reward_list": [],
                "next_free_time": 0,
                "not_got_num": 0,
                "limit_purchase_count_one": 0,
                "limit_purchase_count_ten": 0,
                "first_draw_reward_num": 0,
            }
            acct[chest_id] = rec
        return rec

    def get_chest_state(self, account_id: int, chest_id: int) -> Dict[str, Any]:
        with self._lock:
            self._ensure_seeded(account_id)
            return copy.deepcopy(self._get_chest_record(account_id, chest_id))

    def set_chest_state(self, account_id: int, chest_id: int, state_dict: Dict[str, Any]) -> None:
        with self._lock:
            self._ensure_seeded(account_id)
            rec = self._get_chest_record(account_id, chest_id)
            for k in (
                "lottery_count_weekly",
                "exchanged_reward_list",
                "next_free_time",
                "not_got_num",
                "limit_purchase_count_one",
                "limit_purchase_count_ten",
                "first_draw_reward_num",
            ):
                if k in state_dict:
                    rec[k] = state_dict[k]
            db.save_gacha_state(account_id, chest_id, rec)

    def get_meter(self, account_id: int, chest_id: int) -> int:
        with self._lock:
            self._ensure_seeded(account_id)
            return int(self._get_chest_record(account_id, chest_id).get("not_got_num", 0))

    def set_meter(self, account_id: int, chest_id: int, value: int) -> None:
        with self._lock:
            self._ensure_seeded(account_id)
            rec = self._get_chest_record(account_id, chest_id)
            rec["not_got_num"] = max(0, int(value))
            db.save_gacha_state(account_id, chest_id, rec)

    def reset_meter(self, account_id: int, chest_id: int) -> None:
        self.set_meter(account_id, chest_id, 0)

    def get_gacha_desc(self) -> bytes:
        return encode_get_gacha_desc_res()

    def get_gacha_info(self, account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        with self._lock:
            self._ensure_seeded(account_id)
            infos: List[Dict[str, Any]] = []
            for chest_id in sorted(CHEST_CONFIGS):
                rec = self._get_chest_record(account_id, chest_id)
                infos.append(
                    {
                        "chest_id": chest_id,
                        "lottery_count_weekly": rec["lottery_count_weekly"],
                        "exchanged_reward_list": list(rec["exchanged_reward_list"]),
                        "next_free_time": rec["next_free_time"],
                        "not_got_num": rec["not_got_num"],
                        "limit_purchase_count_one": rec["limit_purchase_count_one"],
                        "limit_purchase_count_ten": rec["limit_purchase_count_ten"],
                        "first_draw_reward_num": rec["first_draw_reward_num"],
                    }
                )
            return encode_get_gacha_info_res(infos)

    def get_special_exchange_desc(
        self,
        language: str = "en",
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> bytes:
        with self._lock:
            self._ensure_seeded(account_id)
            counts = dict(self._special_purchases.get(account_id, {}))
            return encode_get_gacha_special_exchange_desc_res(
                purchase_counts=counts,
                language=language,
            )

    def get_probability(self, chest_id: int) -> bytes:
        cfg = CHEST_CONFIGS.get(int(chest_id))
        if cfg is None:
            return encode_get_lottery_probability_res(())
        return encode_get_lottery_probability_res(cfg.probabilities)

    # -----------------------------------------------------------------------
    # Economy Deduction Subsystem
    # -----------------------------------------------------------------------

    def _deduct_cost(
        self,
        cfg: ChestConfig,
        gacha_type: int,
        consume_type: int,
        rec: Dict[str, Any],
        now: int,
        account_id: int,
        journal: SpinRollbackJournal,
    ) -> bool:
        """Validate and deduct currency/vouchers with full rollback logging."""
        is_multi = gacha_type == LotteryType.SOME
        need_vouchers = cfg.exchange_ten_num if is_multi else cfg.exchange_once_num

        # Smart fallback if consume_type is NONE (0)
        if consume_type == ConsumeType.NONE:
            v_cnt = _get_item_count_with_alias(cfg.exchange_itemid, account_id=account_id) if cfg.exchange_itemid else 0
            if cfg.exchange_itemid and v_cnt >= need_vouchers:
                consume_type = ConsumeType.EXCHANGE_ITEM
            elif cfg.free_type == 1 and not is_multi and now >= rec["next_free_time"]:
                consume_type = ConsumeType.FREE
            else:
                consume_type = ConsumeType.MONEY

        # 1. Daily Free Spin
        if consume_type == ConsumeType.FREE:
            if cfg.free_type != 1 or is_multi or now < rec["next_free_time"]:
                return False
            rec["next_free_time"] = now + FREE_COOLDOWN_SECONDS
            return True

        # 2. Voucher Consumption
        if consume_type == ConsumeType.EXCHANGE_ITEM and cfg.exchange_itemid:
            ok, consumed = _consume_inventory_items([(cfg.exchange_itemid, need_vouchers)], account_id=account_id)
            if not ok:
                return False
            for c in consumed:
                journal.vouchers_consumed.append((c["item_id"], c["cnt"]))
            return True

        # 3. Currency (Diamonds / Gold) Deduction via state.modify_gold / modify_diamond
        price = (
            (cfg.discount_price_ten or cfg.ten_price)
            if is_multi
            else (cfg.discount_price_one or cfg.once_price)
        )

        if cfg.coin_type == CoinType.COINS:
            res = state.modify_gold(account_id, -price)
            if res.success:
                journal.coins_spent = price
                return True
            return False

        if cfg.coin_type == CoinType.GEMS:
            res = state.modify_diamond(account_id, -price)
            if res.success:
                journal.gems_spent = price
                return True
            return False

        return True

    # -----------------------------------------------------------------------
    # Server-Authoritative Reward Selection & Pity / Lucky Meter Subsystem
    # -----------------------------------------------------------------------

    def _pick_item(
        self,
        cfg: ChestConfig,
        rec: Dict[str, Any],
        force_grand_prize: bool = False,
        force_rare: bool = False,
    ) -> Tuple[GachaShowItemConfig, bool]:
        """Server-authoritative random reward selection with machine pool isolation and pity logic.

        Returns (chosen_item, is_grand_prize).
        """
        pool: Sequence[GachaShowItemConfig] = cfg.items
        if not pool:
            raise ValueError(f"Machine {cfg.chest_id} has empty reward pool")

        # Determine grand prize tier (top rarity tier available in this machine)
        max_tier = max(it.reward_level for it in pool)

        # Trigger guaranteed jackpot pity when not_got_num reaches threshold
        is_jackpot_pity = (cfg.rare_item_max > 0) and (rec["not_got_num"] + 1 >= cfg.rare_item_max)

        if force_grand_prize or is_jackpot_pity:
            # Jackpot guarantee: select exclusively from Grand Prize (SUPER_RARE) pool
            grand_pool = [it for it in pool if it.reward_level >= RareType.SUPER_RARE]
            if not grand_pool:
                grand_pool = [it for it in pool if it.reward_level >= max_tier]
            if grand_pool:
                pool = grand_pool
        elif force_rare:
            # Multi-spin must_drop guarantee: select from Rare or higher
            rare_pool = [it for it in pool if it.reward_level >= RareType.RARE]
            if rare_pool:
                pool = rare_pool

        # Server-authoritative weighted random selection
        weights = [max(1, it.weight) for it in pool]
        chosen = self._rng.choices(pool, weights=weights, k=1)[0]

        # Lucky Meter Progression:
        # A Grand Prize (SUPER_RARE or top machine tier) resets the lucky meter to 0!
        is_grand_prize = (chosen.reward_level >= RareType.SUPER_RARE) or (chosen.reward_level >= max_tier and max_tier >= RareType.RARE)

        if is_grand_prize:
            rec["not_got_num"] = 0
        else:
            rec["not_got_num"] += 1

        return chosen, is_grand_prize

    # -----------------------------------------------------------------------
    # Main Spin Execution Pipeline
    # -----------------------------------------------------------------------

    def purchase_gacha(
        self,
        req: Dict[str, Any],
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> bytes:
        """Execute server-authoritative single or multi-spin draw."""
        chest_id = int(req.get("chest_id", 0))
        gacha_type = int(req.get("gacha_type", LotteryType.ONE))
        consume_type = int(req.get("consume_type", ConsumeType.MONEY))
        client_trans_id = req.get("trans_id") or req.get("client_trans_id")

        # Idempotency check: if client sent an idempotency key or repeat transaction, return cached result
        idempotency_key = f"{account_id}:{chest_id}:{client_trans_id}" if client_trans_id else None
        if idempotency_key and idempotency_key in self._idempotency_cache:
            logger.info("Returning idempotent response for key %s", idempotency_key)
            return self._idempotency_cache[idempotency_key]

        with self._lock:
            self._ensure_seeded(account_id)
            cfg = CHEST_CONFIGS.get(chest_id)
            if cfg is None:
                logger.warning("PurchaseGacha unknown chest_id=%s", chest_id)
                return encode_lottery_res([])

            rec = self._get_chest_record(account_id, chest_id)
            journal = SpinRollbackJournal(account_id)
            journal.chest_record_backup = dict(rec)
            lucky_before = int(rec["not_got_num"])
            now = int(time.time())

            # Validate and deduct spin cost
            if not self._deduct_cost(cfg, gacha_type, consume_type, rec, now, account_id, journal):
                logger.warning(
                    "PurchaseGacha failed cost check chest=%s gacha_type=%s consume_type=%s account=%s",
                    chest_id,
                    gacha_type,
                    consume_type,
                    account_id,
                )
                rem_vouchers = _get_item_count_with_alias(cfg.exchange_itemid, account_id) if cfg.exchange_itemid else 0
                return encode_lottery_res(
                    [],
                    lottery_count_weekly=rec["lottery_count_weekly"],
                    next_free_time=rec["next_free_time"],
                    not_got_num=rec["not_got_num"],
                    exchange_item_num=rem_vouchers,
                )

            # Spin Configuration:
            # - Multi-spin: 10 spins (+1 bonus for non-turntables) = 11 items
            # - Multi-spin for Turntable (Incubator): 5 spins (no bonus) = 5 items
            # - Single spin: 1 item
            is_multi = (gacha_type == LotteryType.SOME)
            is_ten_plus_one = is_multi and (cfg.ten_num == 10) and (cfg.chest_type_enum != ChestTabType.TURNTABLE)
            spin_count = cfg.ten_num if is_multi else cfg.once_num

            lottery_goods: List[Dict[str, int]] = []
            extra_one_goods: List[Dict[str, int]] = []
            has_big_reward = False
            batch_granted_items: Set[int] = set()

            try:
                # 1. Base Spin Batch Execution
                for idx in range(spin_count):
                    force_rare = (
                        cfg.must_drop
                        and is_multi
                        and (idx == spin_count - 1)
                        and not has_big_reward
                        and not is_ten_plus_one
                    )
                    picked, is_jackpot = self._pick_item(cfg, rec, force_rare=force_rare)
                    if is_jackpot or picked.reward_level >= RareType.SUPER_RARE:
                        has_big_reward = True

                    # Duplicate Reward Detection & Automatic Token Conversion
                    is_stackable = _is_stackable_item(picked.item_id)
                    if is_stackable:
                        dest_id = picked.item_id
                        dest_num = max(1, picked.item_num)
                        was_new = False
                    else:
                        is_owned = (
                            state.is_item_unlocked(picked.item_id, account_id=account_id)
                            or (picked.item_id in batch_granted_items)
                        )
                        if is_owned:
                            # Automatic Duplicate Conversion to FF Tokens or Character Debris
                            if cfg.chest_id == CHEST_GOLD_ROYALE and (100000000 <= picked.item_id < 200000000 or picked.item_id in AVATAR_CATALOG):
                                # ABSOLUTE RULE: Gold Royale duplicate character rewards must produce character-specific fragments (debris 800000000+), NEVER generic FF Tokens
                                debris_id = get_character_debris_id(picked.item_id)
                                if debris_id is None:
                                    logger.error(
                                        "Gold Royale duplicate character %s has no authoritative debris mapping (or is starter avatar); rolling back spin atomically",
                                        picked.item_id,
                                    )
                                    raise ValueError(
                                        f"Gold Royale unmapped duplicate character {picked.item_id} - atomic rollback triggered"
                                    )
                                dest_id = debris_id
                                dest_num = max(5, picked.repeated_item_num)
                            elif picked.repeated_item_id and picked.repeated_item_id != picked.item_id:
                                dest_id = picked.repeated_item_id
                                dest_num = max(1, picked.repeated_item_num)
                            else:
                                dest_id = ITEM_FF_TOKEN
                                dest_num = DEFAULT_DUPLICATE_TOKEN_RATES.get(picked.reward_level, 2)
                            was_new = False
                        else:
                            dest_id = picked.item_id
                            dest_num = max(1, picked.item_num)
                            was_new = True
                            batch_granted_items.add(picked.item_id)
                            state.unlock_item(dest_id, count=dest_num, account_id=account_id)

                    state.add_item(dest_id, dest_num, account_id=account_id)
                    journal.items_added.append((dest_id, dest_num, was_new))

                    # Stage 5 Duplicate Presentation Correction:
                    # Gold Royale duplicate character rewards must present the authoritative debris item (800000000+)
                    # as the primary reward (Origin) so CSSharedItemData resolves the item sprite, name, and count,
                    # while avoiding matching wheel grand-prize IDs which triggers unwanted 3D feature showcase.
                    origin_type = picked.item_type
                    origin_id = picked.item_id
                    origin_num = picked.item_num

                    if (
                        not is_stackable
                        and is_owned
                        and cfg.chest_id == CHEST_GOLD_ROYALE
                        and (100000000 <= picked.item_id < 200000000 or picked.item_id in AVATAR_CATALOG)
                    ):
                        origin_type = AwardType.ITEM
                        origin_id = dest_id
                        origin_num = dest_num

                    lottery_goods.append(
                        {
                            "origin_award_type": origin_type,
                            "origin_award_id": origin_id,
                            "origin_award_num": origin_num,
                            "dest_award_type": AwardType.ITEM,
                            "dest_award_id": dest_id,
                            "dest_award_num": dest_num,
                        }
                    )

                # 2. Bonus +1 Draw for 10+1 Draw Machines (Gold, Diamond, Weapon Royale)
                if is_ten_plus_one:
                    force_rare = cfg.must_drop and not has_big_reward
                    picked_extra, is_jackpot_extra = self._pick_item(cfg, rec, force_rare=force_rare)
                    if is_jackpot_extra or picked_extra.reward_level >= RareType.SUPER_RARE:
                        has_big_reward = True

                    is_stackable = _is_stackable_item(picked_extra.item_id)
                    if is_stackable:
                        dest_id = picked_extra.item_id
                        dest_num = max(1, picked_extra.item_num)
                        was_new = False
                    else:
                        is_owned = (
                            state.is_item_unlocked(picked_extra.item_id, account_id=account_id)
                            or (picked_extra.item_id in batch_granted_items)
                        )
                        if is_owned:
                            if cfg.chest_id == CHEST_GOLD_ROYALE and (100000000 <= picked_extra.item_id < 200000000 or picked_extra.item_id in AVATAR_CATALOG):
                                # ABSOLUTE RULE: Gold Royale duplicate character rewards must produce character-specific fragments (debris 800000000+), NEVER generic FF Tokens
                                debris_id = get_character_debris_id(picked_extra.item_id)
                                if debris_id is None:
                                    logger.error(
                                        "Gold Royale bonus draw duplicate character %s has no authoritative debris mapping (or is starter avatar); rolling back spin atomically",
                                        picked_extra.item_id,
                                    )
                                    raise ValueError(
                                        f"Gold Royale unmapped duplicate character {picked_extra.item_id} in bonus draw - atomic rollback triggered"
                                    )
                                dest_id = debris_id
                                dest_num = max(5, picked_extra.repeated_item_num)
                            elif picked_extra.repeated_item_id and picked_extra.repeated_item_id != picked_extra.item_id:
                                dest_id = picked_extra.repeated_item_id
                                dest_num = max(1, picked_extra.repeated_item_num)
                            else:
                                dest_id = ITEM_FF_TOKEN
                                dest_num = DEFAULT_DUPLICATE_TOKEN_RATES.get(picked_extra.reward_level, 2)
                            was_new = False
                        else:
                            dest_id = picked_extra.item_id
                            dest_num = max(1, picked_extra.item_num)
                            was_new = True
                            batch_granted_items.add(picked_extra.item_id)
                            state.unlock_item(dest_id, count=dest_num, account_id=account_id)

                    state.add_item(dest_id, dest_num, account_id=account_id)
                    journal.items_added.append((dest_id, dest_num, was_new))

                    origin_extra_type = picked_extra.item_type
                    origin_extra_id = picked_extra.item_id
                    origin_extra_num = picked_extra.item_num

                    if (
                        not is_stackable
                        and is_owned
                        and cfg.chest_id == CHEST_GOLD_ROYALE
                        and (100000000 <= picked_extra.item_id < 200000000 or picked_extra.item_id in AVATAR_CATALOG)
                    ):
                        origin_extra_type = AwardType.ITEM
                        origin_extra_id = dest_id
                        origin_extra_num = dest_num

                    extra_one_goods.append(
                        {
                            "origin_award_type": origin_extra_type,
                            "origin_award_id": origin_extra_id,
                            "origin_award_num": origin_extra_num,
                            "dest_award_type": AwardType.ITEM,
                            "dest_award_id": dest_id,
                            "dest_award_num": dest_num,
                        }
                    )

                # Update weekly count and first draw counter
                total_drawn = spin_count + (1 if is_ten_plus_one else 0)
                rec["lottery_count_weekly"] += total_drawn
                if cfg.first_reward_switch and rec["first_draw_reward_num"] < cfg.first_reward_max:
                    rec["first_draw_reward_num"] += 1

                # 3. Durable Persistence & Idempotency / History Logging
                db.save_gacha_state(account_id, chest_id, rec)

                # Cost type and amount determination
                cost_type = cfg.coin_type
                cost_amount = journal.coins_spent or journal.gems_spent or (len(journal.vouchers_consumed) * (cfg.exchange_ten_num if is_multi else cfg.exchange_once_num))

                reward_list = lottery_goods + extra_one_goods
                try:
                    trans_id = db.record_gacha_transaction(
                        account_id=account_id,
                        chest_id=chest_id,
                        gacha_type=gacha_type,
                        consume_type=consume_type,
                        cost_type=cost_type,
                        cost_amount=cost_amount,
                        reward_list=reward_list,
                        lucky_before=lucky_before,
                        lucky_after=rec["not_got_num"],
                        has_big_reward=has_big_reward,
                        timestamp=now,
                    )
                except Exception as ex:
                    logger.warning("record_gacha_transaction fallback to next_trans_id: %s", ex)
                    trans_id = self._next_trans_id()

                tx_record = {
                    "trans_id": trans_id,
                    "account_id": account_id,
                    "chest_id": chest_id,
                    "gacha_type": gacha_type,
                    "consume_type": consume_type,
                    "cost_type": cost_type,
                    "cost_amount": cost_amount,
                    "total_drawn": total_drawn,
                    "has_big_reward": 1 if has_big_reward else 0,
                    "luck_before": lucky_before,
                    "luck_after": rec["not_got_num"],
                    "reward_list_json": json.dumps(reward_list),
                    "timestamp": now,
                }
                self._spin_history.append(tx_record)

                db.log_action(
                    account_id,
                    "GACHA_SPIN",
                    f"Spun chest {chest_id} ({gacha_type=}, {consume_type=}), awarded {total_drawn} items, luck={rec['not_got_num']}",
                    {
                        "trans_id": trans_id,
                        "chest_id": chest_id,
                        "gacha_type": gacha_type,
                        "total_drawn": total_drawn,
                        "luck": rec["not_got_num"],
                        "has_big_reward": has_big_reward,
                    },
                )

                remaining_vouchers = (
                    _get_item_count_with_alias(cfg.exchange_itemid, account_id) if cfg.exchange_itemid else 0
                )
                res_bytes = encode_lottery_res(
                    lottery_goods=lottery_goods,
                    extra_one_goods=extra_one_goods,
                    lottery_count_weekly=rec["lottery_count_weekly"],
                    next_free_time=rec["next_free_time"],
                    limit_purchase_count_one=rec["limit_purchase_count_one"],
                    limit_purchase_count_ten=rec["limit_purchase_count_ten"],
                    not_got_num=rec["not_got_num"],
                    first_draw_reward_num=rec["first_draw_reward_num"],
                    exchange_item_num=remaining_vouchers,
                    has_big_reward=has_big_reward,
                )

                if idempotency_key:
                    self._idempotency_cache[idempotency_key] = res_bytes

                return res_bytes

            except Exception as e:
                logger.error("PurchaseGacha exception during draw: %s; rolling back atomically", e, exc_info=True)
                journal.rollback(rec)
                rem_vouchers = (
                    _get_item_count_with_alias(cfg.exchange_itemid, account_id) if cfg.exchange_itemid else 0
                )
                return encode_lottery_res(
                    [],
                    lottery_count_weekly=rec["lottery_count_weekly"],
                    next_free_time=rec["next_free_time"],
                    not_got_num=rec["not_got_num"],
                    exchange_item_num=rem_vouchers,
                )

    # -----------------------------------------------------------------------
    # Milestone Claims & Special Exchange Forge
    # -----------------------------------------------------------------------

    def exchange_extra_reward(
        self,
        req: Dict[str, Any],
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> bytes:
        chest_id = int(req.get("chest_id", 0))
        condition_num = int(req.get("condition_num", 0))

        with self._lock:
            self._ensure_seeded(account_id)
            cfg = CHEST_CONFIGS.get(chest_id)
            rec = self._get_chest_record(account_id, chest_id)
            if cfg is None:
                return encode_exchange_gacha_extra_reward_res(exchanged_reward_list=rec["exchanged_reward_list"])

            milestone = next((er for er in cfg.extra_rewards if er.cdt_value == condition_num), None)
            if (
                milestone is None
                or condition_num in rec["exchanged_reward_list"]
                or rec["lottery_count_weekly"] < condition_num
            ):
                return encode_exchange_gacha_extra_reward_res(exchanged_reward_list=rec["exchanged_reward_list"])

            items: List[Dict[str, Any]] = []
            coins = 0
            gems = 0
            if milestone.reward_type == AwardType.COINS:
                coins = milestone.reward_num
                state.modify_gold(account_id, coins)
            elif milestone.reward_type == AwardType.GEMS:
                gems = milestone.reward_num
                state.modify_diamond(account_id, gems)
            else:
                state.add_item(milestone.reward_id, milestone.reward_num, account_id=account_id)
                items.append({"item_id": milestone.reward_id, "cnt": milestone.reward_num})

            rec["exchanged_reward_list"].append(condition_num)
            rec["exchanged_reward_list"].sort()

            # Durable state persistence
            db.save_gacha_state(account_id, chest_id, rec)
            db.log_action(
                account_id,
                "GACHA_MILESTONE",
                f"Claimed milestone {condition_num} for chest {chest_id}",
                {"chest_id": chest_id, "condition_num": condition_num},
            )

            return encode_exchange_gacha_extra_reward_res(
                items=items,
                coins=coins,
                gems=gems,
                exchanged_reward_list=rec["exchanged_reward_list"],
            )

    def do_special_exchange(
        self,
        req: Dict[str, Any],
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> bytes:
        tab_id = int(req.get("forge_tab_id", 0))
        item_id = int(req.get("item_id", 0))
        exchange_cnt = max(1, int(req.get("exchange_cnt", 1)))

        with self._lock:
            self._ensure_seeded(account_id)
            cfg = _SPECIAL_EXCHANGE_INDEX.get((tab_id, item_id))
            if cfg is None:
                return encode_do_gacha_special_exchange_res(purchase_times=0, trans_id=self._next_trans_id())

            acct_counts = self._special_purchases.setdefault(account_id, {})
            cur_times = acct_counts.get((tab_id, item_id), 0)
            if cfg.limited_purchase_times > 0 and cur_times + exchange_cnt > cfg.limited_purchase_times:
                return encode_do_gacha_special_exchange_res(
                    purchase_times=cur_times,
                    trans_id=self._next_trans_id(),
                )

            reqs = [(award_id, award_num * exchange_cnt) for award_id, award_num, _ in cfg.exchange_items]
            ok, del_list = _consume_inventory_items(reqs, account_id=account_id)
            if not ok:
                logger.warning(
                    "DoGachaSpecialExchange insufficient materials tab=%s item=%s account=%s",
                    tab_id,
                    item_id,
                    account_id,
                )
                return encode_do_gacha_special_exchange_res(
                    purchase_times=cur_times,
                    trans_id=self._next_trans_id(),
                )

            grant_qty = cfg.item_num * exchange_cnt
            state.unlock_item(cfg.item_id, count=grant_qty, account_id=account_id)
            state.add_item(cfg.item_id, grant_qty, account_id=account_id)
            new_times = cur_times + exchange_cnt
            acct_counts[(tab_id, item_id)] = new_times
            trans_id = self._next_trans_id()

            try:
                db.record_special_exchange(
                    account_id=account_id,
                    tab_id=tab_id,
                    item_id=item_id,
                    exchange_cnt=exchange_cnt,
                    trans_id=trans_id,
                    details={"del_items": del_list},
                )
            except Exception:
                pass

            return encode_do_gacha_special_exchange_res(
                add_item_list=[{"item_id": cfg.item_id, "cnt": grant_qty}],
                del_item_list=del_list,
                purchase_times=new_times,
                trans_id=trans_id,
            )

    # -----------------------------------------------------------------------
    # Admin API & Analytics Query Helpers
    # -----------------------------------------------------------------------

    def get_spin_history(
        self,
        account_id: Optional[int] = None,
        chest_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query recent spin transactions with optional account/machine filters."""
        with self._lock:
            # Query database first using core_arch method
            try:
                rows = db.get_gacha_transactions(account_id=account_id, chest_id=chest_id, limit=limit)
                if rows:
                    return rows
            except Exception as e:
                logger.warning("get_gacha_transactions DB fallback: %s", e)

            # Fallback to in-memory history ring buffer
            res: List[Dict[str, Any]] = []
            for item in reversed(self._spin_history):
                if account_id and item["account_id"] != int(account_id):
                    continue
                if chest_id and item["chest_id"] != int(chest_id):
                    continue
                d = dict(item)
                try:
                    d["reward_list"] = json.loads(d.get("reward_list_json", "[]"))
                except Exception:
                    d["reward_list"] = []
                res.append(d)
                if len(res) >= limit:
                    break
            return res

    def get_transaction(self, trans_id: int) -> Optional[Dict[str, Any]]:
        """Lookup single transaction by ID."""
        with self._lock:
            for item in self._spin_history:
                if item["trans_id"] == int(trans_id):
                    d = dict(item)
                    try:
                        d["reward_list"] = json.loads(d.get("reward_list_json", "[]"))
                    except Exception:
                        d["reward_list"] = []
                    return d
            try:
                rows = db.get_gacha_transactions(limit=100)
                for r in rows:
                    if r["trans_id"] == int(trans_id):
                        return r
            except Exception:
                pass
            return None


class EconomyService(IEconomyService):
    """Authoritative Economy Subsystem for Luck Royale (Agent 5: currency, vouchers, incubator forge)."""

    def __init__(self, service: Optional[GachaService] = None) -> None:
        self._service = service

    def get_voucher_balance(self, account_id: int, chest_id: int) -> int:
        """Get player's current voucher count for a specific machine."""
        cfg = CHEST_CONFIGS.get(int(chest_id))
        if cfg is None or not cfg.exchange_itemid:
            return 0
        return _get_item_count_with_alias(cfg.exchange_itemid, account_id=account_id)

    def validate_and_deduct_cost(
        self,
        account_id: int,
        cfg: ChestConfig,
        gacha_type: int,
        consume_type: int,
        rec: Dict[str, Any],
        now: int,
    ) -> CostDeductionResult:
        """
        Atomically validate balance and deduct appropriate currency or voucher.
        1. Currency deduction: Diamonds (CoinType.DIAMOND=1 / GEMS) and Gold (CoinType.GOLD=2 / COINS)
           with balance validation and zero-negative prevention.
        2. Machine-compatible voucher deduction (Gold Royale Voucher 110100010, Diamond Voucher 110100008,
           Weapon Voucher 110100009, Incubator Voucher 110100018) prioritizing vouchers over raw currency when selected.
        3. Daily free spin cooldown tracking per machine.
        """
        is_multi = (gacha_type == LotteryType.SOME)
        need_vouchers = cfg.exchange_ten_num if is_multi else cfg.exchange_once_num

        # Smart fallback if consume_type is NONE (0)
        if consume_type == ConsumeType.NONE:
            v_cnt = self.get_voucher_balance(account_id, cfg.chest_id)
            if cfg.free_type == 1 and not is_multi and now >= rec.get("next_free_time", 0):
                consume_type = ConsumeType.FREE
            elif cfg.exchange_itemid and v_cnt >= need_vouchers:
                consume_type = ConsumeType.EXCHANGE_ITEM
            else:
                consume_type = ConsumeType.MONEY

        # 1. Daily Free Spin
        if consume_type == ConsumeType.FREE:
            if cfg.free_type != 1 or is_multi or now < rec.get("next_free_time", 0):
                return CostDeductionResult(
                    success=False,
                    cost_type=CostType.FREE,
                    amount_deducted=0,
                    message="Free spin cooldown active or multi-spin requested",
                )
            rec["next_free_time"] = now + FREE_COOLDOWN_SECONDS
            db.log_action(
                account_id,
                "GACHA_FREE_SPIN",
                f"Used daily free spin for chest {cfg.chest_id}; next free: {rec['next_free_time']}",
                {"chest_id": cfg.chest_id, "next_free_time": rec["next_free_time"]},
            )
            return CostDeductionResult(
                success=True,
                cost_type=CostType.FREE,
                amount_deducted=0,
                message="Free spin authorized",
            )

        # 2. Voucher Consumption
        if consume_type == ConsumeType.EXCHANGE_ITEM:
            if not cfg.exchange_itemid:
                return CostDeductionResult(
                    success=False,
                    cost_type=CostType.VOUCHER,
                    amount_deducted=0,
                    message="Machine does not accept vouchers",
                )
            ok, consumed = _consume_inventory_items([(cfg.exchange_itemid, need_vouchers)], account_id=account_id)
            if not ok:
                return CostDeductionResult(
                    success=False,
                    cost_type=CostType.VOUCHER,
                    amount_deducted=0,
                    voucher_id_used=cfg.exchange_itemid,
                    message="Insufficient vouchers",
                )
            rem_v = self.get_voucher_balance(account_id, cfg.chest_id)
            db.log_action(
                account_id,
                "GACHA_VOUCHER_SPEND",
                f"Spent {need_vouchers} voucher(s) for chest {cfg.chest_id}; remaining: {rem_v}",
                {"chest_id": cfg.chest_id, "voucher_id": cfg.exchange_itemid, "consumed": consumed, "remaining": rem_v},
            )
            return CostDeductionResult(
                success=True,
                cost_type=CostType.VOUCHER,
                amount_deducted=need_vouchers,
                voucher_id_used=cfg.exchange_itemid,
                message="Vouchers deducted",
            )

        # 3. Currency (Diamonds / Gold) Deduction
        price = (
            (cfg.discount_price_ten or cfg.ten_price)
            if is_multi
            else (cfg.discount_price_one or cfg.once_price)
        )
        if price < 0:
            return CostDeductionResult(
                success=False,
                cost_type=CostType.GOLD,
                amount_deducted=0,
                message="Invalid price configuration",
            )
        if price == 0:
            return CostDeductionResult(
                success=True,
                cost_type=CostType.FREE,
                amount_deducted=0,
                message="Zero cost authorized",
            )

        is_gold_chest = (cfg.chest_id == CHEST_GOLD_ROYALE) or (cfg.coin_type in (CoinType.COINS, 2))
        if is_gold_chest and cfg.chest_id not in (CHEST_DIAMOND_ROYALE, CHEST_WEAPON_ROYALE, CHEST_INCUBATOR):
            ok, new_bal = state.modify_gold(account_id, -price)
            if not ok:
                return CostDeductionResult(
                    success=False,
                    cost_type=CostType.GOLD,
                    amount_deducted=0,
                    message="Insufficient gold balance",
                )
            db.log_action(
                account_id,
                "GACHA_CURRENCY_SPEND",
                f"Spent {price} Gold for chest {cfg.chest_id}; new balance: {new_bal}",
                {"chest_id": cfg.chest_id, "currency": "GOLD", "price": price, "balance": new_bal},
            )
            return CostDeductionResult(
                success=True,
                cost_type=CostType.GOLD,
                amount_deducted=price,
                message="Gold deducted",
            )

        ok, new_bal = state.modify_diamond(account_id, -price)
        if not ok:
            return CostDeductionResult(
                success=False,
                cost_type=CostType.DIAMOND,
                amount_deducted=0,
                message="Insufficient diamond balance",
            )
        db.log_action(
            account_id,
            "GACHA_CURRENCY_SPEND",
            f"Spent {price} Diamonds for chest {cfg.chest_id}; new balance: {new_bal}",
            {"chest_id": cfg.chest_id, "currency": "DIAMOND", "price": price, "balance": new_bal},
        )
        return CostDeductionResult(
            success=True,
            cost_type=CostType.DIAMOND,
            amount_deducted=price,
            message="Diamonds deducted",
        )

    def execute_special_exchange(
        self,
        account_id: int,
        forge_tab_id: int,
        item_id: int,
        count: int = 1,
    ) -> ForgeExchangeResult:
        """Incubator Special Exchange Forge craft execution."""
        cfg = _SPECIAL_EXCHANGE_INDEX.get((forge_tab_id, item_id))
        if cfg is None:
            return ForgeExchangeResult(
                success=False,
                forge_tab_id=forge_tab_id,
                item_id=item_id,
                count=count,
                consumed_materials=[],
                purchase_times=0,
                trans_id=0,
                error_message="Unknown forge recipe",
            )

        exchange_cnt = max(1, int(count))
        purchases = db.get_special_exchange_purchases(account_id)
        cur_times = purchases.get((forge_tab_id, item_id), 0)
        if cfg.limited_purchase_times > 0 and cur_times + exchange_cnt > cfg.limited_purchase_times:
            return ForgeExchangeResult(
                success=False,
                forge_tab_id=forge_tab_id,
                item_id=item_id,
                count=exchange_cnt,
                consumed_materials=[],
                purchase_times=cur_times,
                trans_id=0,
                error_message="Purchase limit exceeded",
            )

        reqs = [(award_id, award_num * exchange_cnt) for award_id, award_num, _ in cfg.exchange_items]
        ok, del_list = _consume_inventory_items(reqs, account_id=account_id)
        if not ok:
            return ForgeExchangeResult(
                success=False,
                forge_tab_id=forge_tab_id,
                item_id=item_id,
                count=exchange_cnt,
                consumed_materials=[],
                purchase_times=cur_times,
                trans_id=0,
                error_message="Insufficient blueprint or evolution stone materials",
            )

        grant_qty = cfg.item_num * exchange_cnt
        state.unlock_item(cfg.item_id, count=grant_qty, account_id=account_id)
        state.add_item(cfg.item_id, grant_qty, account_id=account_id)
        trans_id = db.record_special_exchange(
            account_id=account_id,
            forge_tab_id=forge_tab_id,
            item_id=cfg.item_id,
            count=exchange_cnt,
            consumed_items=del_list,
        )
        new_times = cur_times + exchange_cnt

        db.log_action(
            account_id,
            "GACHA_SPECIAL_EXCHANGE",
            f"Crafted Incubator item {cfg.item_id} x{grant_qty} (tab={forge_tab_id})",
            {
                "trans_id": trans_id,
                "forge_tab_id": forge_tab_id,
                "item_id": cfg.item_id,
                "grant_qty": grant_qty,
                "del_items": del_list,
                "purchase_times": new_times,
            },
        )

        return ForgeExchangeResult(
            success=True,
            forge_tab_id=forge_tab_id,
            item_id=cfg.item_id,
            count=grant_qty,
            consumed_materials=del_list,
            purchase_times=new_times,
            trans_id=trans_id,
            error_message="",
        )

    def exchange_token_store(
        self,
        commodity_id: int,
        store_id: int = 1,
        cnt: int = 1,
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Token store exchange (FF Tokens 110200001) for cosmetic rewards."""
        from handlers.store_handler import store_service
        req = {
            "store_id": store_id,
            "commodity_id": commodity_id,
            "cnt": cnt,
            "trans_id": int(time.time() * 1000) % 90000000 + 10000000,
        }
        res_bytes = store_service.exchange_purchase(req, account_id=account_id)
        return True, "Token exchange processed", {"res_len": len(res_bytes)}


gacha_service = GachaService()
economy_service = EconomyService(gacha_service)
gacha_service.economy_service = economy_service


def handle_gacha_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """Route Luck Royale / Gacha endpoints for FF 1.39."""
    endpoint = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]

    if endpoint == "GetGachaDesc":
        handler.send_proto("CSGetGachaDescRes", gacha_service.get_gacha_desc())
        return True

    if endpoint == "GetGachaInfo":
        handler.send_proto("CSGetGachaInfoRes", gacha_service.get_gacha_info(account_id=account_id))
        return True

    if endpoint == "GetGachaSpecialExchangeDesc":
        req = decode_get_gacha_special_exchange_desc_req(raw_body)
        handler.send_proto(
            "CSGetGachaSpecialExchangeDescRes",
            gacha_service.get_special_exchange_desc(language=req["language"], account_id=account_id),
        )
        return True

    if endpoint in ("GetGachaProbability", "GetLotteryProbability"):
        req = decode_get_lottery_probability_req(raw_body)
        handler.send_proto("CSGetLotteryProbabilityRes", gacha_service.get_probability(req["chest_id"]))
        return True

    if endpoint in ("PurchaseGacha", "Lottery"):
        req = decode_lottery_req(raw_body)
        handler.send_proto("CSLotteryRes", gacha_service.purchase_gacha(req, account_id=account_id))
        return True

    if endpoint in ("ExchangeGachaExtraReward", "LotteryExtraReward"):
        req = decode_lottery_extra_reward_req(raw_body)
        handler.send_proto(
            "CSExchangeGachaExtraRewardRes",
            gacha_service.exchange_extra_reward(req, account_id=account_id),
        )
        return True

    if endpoint == "DoGachaSpecialExchange":
        req = decode_do_gacha_special_exchange_req(raw_body)
        handler.send_proto(
            "CSDoGachaSpecialExchangeRes",
            gacha_service.do_special_exchange(req, account_id=account_id),
        )
        return True

    return False


handle_gacha_post = handle_gacha_request
