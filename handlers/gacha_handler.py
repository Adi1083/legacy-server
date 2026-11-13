"""Luck Royale / Gacha HTTP endpoint handlers for Barbosa Project 1.39."""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.gacha_models import (
    CHEST_CONFIGS,
    DEFAULT_SPECIAL_EXCHANGES,
    FREE_COOLDOWN_SECONDS,
    ITEM_BLUEPRINT_JOKER,
    ITEM_BLUEPRINT_YINYANG,
    ITEM_EVOLUTION_STONE,
    ITEM_FF_TOKEN,
    VOUCHER_DIAMOND_ROYALE,
    VOUCHER_GOLD_ROYALE,
    VOUCHER_INCUBATOR,
    VOUCHER_WEAPON_ROYALE,
    ChestConfig,
    CoinType,
    ConsumeType,
    GachaShowItemConfig,
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
)
from proto.store_models import AwardType

logger = logging.getLogger("gacha_handler")

_STACKABLE_PREFIXES = (800, 802, 804, 808, 1101, 1102, 1307)

_INITIAL_GACHA_STOCK: Dict[int, int] = {
    VOUCHER_GOLD_ROYALE: 10,
    VOUCHER_DIAMOND_ROYALE: 10,
    VOUCHER_WEAPON_ROYALE: 10,
    VOUCHER_INCUBATOR: 10,
    ITEM_EVOLUTION_STONE: 10,
    ITEM_BLUEPRINT_YINYANG: 5,
    ITEM_BLUEPRINT_JOKER: 5,
}

_SPECIAL_EXCHANGE_INDEX: Dict[Tuple[int, int], SpecialExchangeConfig] = {
    (cfg.forge_tab_id, cfg.item_id): cfg for cfg in DEFAULT_SPECIAL_EXCHANGES
}


def _is_stackable_item(item_id: int) -> bool:
    return (int(item_id) // 1_000_000) in _STACKABLE_PREFIXES or (int(item_id) // 10_000) in (1101, 1102)


def _consume_inventory_items(requirements: Sequence[Tuple[int, int]]) -> Tuple[bool, List[Dict[str, int]]]:
    """Atomically verify and deduct required stackable items from core.state."""
    with state._lock:
        for item_id, need in requirements:
            iid = int(item_id)
            if state.get_item_count(iid) < int(need):
                return False, []

        consumed: List[Dict[str, int]] = []
        for item_id, need in requirements:
            iid = int(item_id)
            qty = max(1, int(need))
            cur = state.get_item_count(iid)
            rem = cur - qty
            if rem <= 0:
                state._unlocked_items.discard(iid)
                state._item_counts.pop(iid, None)
            else:
                state._item_counts[iid] = rem
            consumed.append({"item_id": iid, "cnt": qty})
        return True, consumed


class GachaService:
    """Thread-safe stateful Luck Royale / Gacha engine."""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._lock = threading.RLock()
        self._rng = rng or random.Random()
        self._seeded_accounts: set[int] = set()
        # account_id -> chest_id -> dict state
        self._chest_state: Dict[int, Dict[int, Dict[str, Any]]] = {}
        # account_id -> (forge_tab_id, item_id) -> purchase_times
        self._special_purchases: Dict[int, Dict[Tuple[int, int], int]] = {}
        self._trans_counter = 5000

    def _next_trans_id(self) -> int:
        self._trans_counter += 1
        return self._trans_counter

    def _ensure_seeded(self, account_id: int) -> None:
        if account_id in self._seeded_accounts:
            return
        for iid, qty in _INITIAL_GACHA_STOCK.items():
            if state.get_item_count(iid) == 0:
                state.add_item(iid, qty)
        self._seeded_accounts.add(account_id)

    def _get_chest_record(self, account_id: int, chest_id: int) -> Dict[str, Any]:
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

    def _deduct_cost(
        self,
        cfg: ChestConfig,
        gacha_type: int,
        consume_type: int,
        rec: Dict[str, Any],
        now: int,
        account_id: int,
    ) -> bool:
        is_multi = gacha_type == LotteryType.SOME
        if consume_type == ConsumeType.FREE:
            if cfg.free_type != 1 or is_multi or now < rec["next_free_time"]:
                return False
            rec["next_free_time"] = now + FREE_COOLDOWN_SECONDS
            return True

        if consume_type == ConsumeType.EXCHANGE_ITEM and cfg.exchange_itemid:
            need_vouchers = cfg.exchange_ten_num if is_multi else cfg.exchange_once_num
            ok, _ = _consume_inventory_items([(cfg.exchange_itemid, need_vouchers)])
            return ok

        # Default / ConsumeType.MONEY
        price = (
            (cfg.discount_price_ten or cfg.ten_price)
            if is_multi
            else (cfg.discount_price_one or cfg.once_price)
        )
        if cfg.coin_type == CoinType.COINS:
            ok, _ = state.spend_currency(coins=price, gems=0, account_id=account_id)
            return ok
        if cfg.coin_type == CoinType.GEMS:
            ok, _ = state.spend_currency(coins=0, gems=price, account_id=account_id)
            return ok
        return True

    def _pick_item(self, cfg: ChestConfig, rec: Dict[str, Any], force_rare: bool = False) -> GachaShowItemConfig:
        pool = cfg.items
        if force_rare or (cfg.rare_item_max > 0 and rec["not_got_num"] + 1 >= cfg.rare_item_max):
            rare_pool = [it for it in pool if it.reward_level >= RareType.SUPER_RARE]
            if not rare_pool:
                rare_pool = [it for it in pool if it.reward_level >= RareType.RARE]
            if rare_pool:
                pool = tuple(rare_pool)

        weights = [max(1, it.weight) for it in pool]
        chosen = self._rng.choices(pool, weights=weights, k=1)[0]
        if chosen.reward_level >= RareType.RARE:
            rec["not_got_num"] = 0
        else:
            rec["not_got_num"] += 1
        return chosen

    def purchase_gacha(
        self,
        req: Dict[str, Any],
        account_id: int = DEFAULT_ACCOUNT_ID,
    ) -> bytes:
        chest_id = int(req.get("chest_id", 0))
        gacha_type = int(req.get("gacha_type", LotteryType.ONE))
        consume_type = int(req.get("consume_type", ConsumeType.MONEY))

        with self._lock:
            self._ensure_seeded(account_id)
            cfg = CHEST_CONFIGS.get(chest_id)
            if cfg is None:
                logger.warning("PurchaseGacha unknown chest_id=%s", chest_id)
                return encode_lottery_res([])

            rec = self._get_chest_record(account_id, chest_id)
            now = int(time.time())
            if not self._deduct_cost(cfg, gacha_type, consume_type, rec, now, account_id):
                logger.warning(
                    "PurchaseGacha failed cost check chest=%s gacha_type=%s consume_type=%s",
                    chest_id,
                    gacha_type,
                    consume_type,
                )
                return encode_lottery_res(
                    [],
                    lottery_count_weekly=rec["lottery_count_weekly"],
                    next_free_time=rec["next_free_time"],
                    not_got_num=rec["not_got_num"],
                    exchange_item_num=state.get_item_count(cfg.exchange_itemid) if cfg.exchange_itemid else 0,
                )

            is_multi = gacha_type == LotteryType.SOME
            spin_count = cfg.ten_num if is_multi else cfg.once_num

            lottery_goods: List[Dict[str, int]] = []
            has_big_reward = False
            for idx in range(spin_count):
                force_rare = (
                    cfg.must_drop
                    and is_multi
                    and idx == spin_count - 1
                    and not has_big_reward
                )
                picked = self._pick_item(cfg, rec, force_rare=force_rare)
                if picked.reward_level >= RareType.RARE:
                    has_big_reward = True

                already_owned = (
                    not _is_stackable_item(picked.item_id)
                    and state.is_item_unlocked(picked.item_id)
                    and picked.repeated_item_id != picked.item_id
                )
                if already_owned:
                    dest_id = picked.repeated_item_id or ITEM_FF_TOKEN
                    dest_num = max(1, picked.repeated_item_num)
                else:
                    dest_id = picked.item_id
                    dest_num = max(1, picked.item_num)

                state.add_item(dest_id, dest_num)
                lottery_goods.append(
                    {
                        "origin_award_type": picked.item_type,
                        "origin_award_id": picked.item_id,
                        "origin_award_num": picked.item_num,
                        "dest_award_type": AwardType.ITEM,
                        "dest_award_id": dest_id,
                        "dest_award_num": dest_num,
                    }
                )

            rec["lottery_count_weekly"] += spin_count
            if cfg.first_reward_switch and rec["first_draw_reward_num"] < cfg.first_reward_max:
                rec["first_draw_reward_num"] += 1

            remaining_vouchers = state.get_item_count(cfg.exchange_itemid) if cfg.exchange_itemid else 0
            return encode_lottery_res(
                lottery_goods=lottery_goods,
                lottery_count_weekly=rec["lottery_count_weekly"],
                next_free_time=rec["next_free_time"],
                limit_purchase_count_one=rec["limit_purchase_count_one"],
                limit_purchase_count_ten=rec["limit_purchase_count_ten"],
                not_got_num=rec["not_got_num"],
                first_draw_reward_num=rec["first_draw_reward_num"],
                exchange_item_num=remaining_vouchers,
                has_big_reward=has_big_reward,
            )

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
                state.grant_currency(coins=coins, account_id=account_id)
            elif milestone.reward_type == AwardType.GEMS:
                gems = milestone.reward_num
                state.grant_currency(gems=gems, account_id=account_id)
            else:
                state.add_item(milestone.reward_id, milestone.reward_num)
                items.append({"item_id": milestone.reward_id, "cnt": milestone.reward_num})

            rec["exchanged_reward_list"].append(condition_num)
            rec["exchanged_reward_list"].sort()
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
            ok, del_list = _consume_inventory_items(reqs)
            if not ok:
                logger.warning(
                    "DoGachaSpecialExchange insufficient materials tab=%s item=%s",
                    tab_id,
                    item_id,
                )
                return encode_do_gacha_special_exchange_res(
                    purchase_times=cur_times,
                    trans_id=self._next_trans_id(),
                )

            grant_qty = cfg.item_num * exchange_cnt
            state.add_item(cfg.item_id, grant_qty)
            new_times = cur_times + exchange_cnt
            acct_counts[(tab_id, item_id)] = new_times
            return encode_do_gacha_special_exchange_res(
                add_item_list=[{"item_id": cfg.item_id, "cnt": grant_qty}],
                del_item_list=del_list,
                purchase_times=new_times,
                trans_id=self._next_trans_id(),
            )


gacha_service = GachaService()


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

    if endpoint == "GetGachaProbability":
        req = decode_get_lottery_probability_req(raw_body)
        handler.send_proto("CSGetLotteryProbabilityRes", gacha_service.get_probability(req["chest_id"]))
        return True

    if endpoint == "PurchaseGacha":
        req = decode_lottery_req(raw_body)
        handler.send_proto("CSLotteryRes", gacha_service.purchase_gacha(req, account_id=account_id))
        return True

    if endpoint == "ExchangeGachaExtraReward":
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
