"""
HTTP request handlers for Free Fire 1.39 Store, Gift Store, Exchange Store,
Discount Store, Bundles, Treasure Boxes / Weapon Crates, Installment Store,
and /Purchase + /BuyItem.

Supported HTTP endpoints (ServiceMessageTypeHTTP + /BuyItem alias):
- /GetStore                  -> proto.CSGetStoreRes
- /GetStoreTab               -> proto.CSGetStoreTabRes
- /Purchase                  -> proto.CSPurchaseRes
- /BuyItem                   -> proto.CSPurchaseRes (alias for /Purchase)
- /GetBundle                 -> proto.CSGetBundleRes
- /OpenBundle                -> proto.CSOpenBundleRes
- /GetTreasureBox            -> proto.CSGetTreasureBoxRes
- /OpenTreasureBox           -> proto.CSOpenTreasureBoxRes
- /GetTreasureBoxPR          -> Empty
- /GetGiftStore              -> proto.CSGetGiftStoreRes
- /GetGiftStoreDetails       -> proto.CSGetGiftStoreDetailsRes
- /SendGift                  -> proto.CSSendGiftRes
- /GetExchangeStore          -> proto.CSGetExchangeStoreRes
- /ExchangeStorePurchase     -> proto.CSExchangeStorePurchaseRes
- /GetDiscountStore          -> proto.CSGetDiscountStoreDescRes
- /DiscountStorePurchase     -> proto.CSDiscountStorePurchaseRes
- /GetPayBundleWindowDesc    -> proto.CSGetPayBundleWindowDescRes
- /PayBundleWindowPurchase   -> proto.CSPayBundleWindowPurchaseRes
- /GetInstallmentStore       -> proto.CSGetInstallmentStoreDescRes
- /InstallmentPurchase       -> proto.CSInstallmentPurchaseRes
- /GetInstallmentItems       -> proto.CSGetInstallmentItemsRes

Integrates with core.state.state for infinite coins/gems (999999) and persistent
item, character, pet, and mail unlocks.
"""

from __future__ import annotations

import copy
import random
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.store_models import (
    BUNDLE_DEFINITIONS,
    TREASURE_BOX_DEFINITIONS,
    AwardType,
    CurrencyType,
    ItemStatus,
    TransReason,
    decode_discount_store_purchase_req,
    decode_exchange_store_purchase_req,
    decode_get_exchange_store_req,
    decode_get_installment_store_req,
    decode_get_store_req,
    decode_installment_purchase_req,
    decode_open_bundle_req,
    decode_open_treasure_box_req,
    decode_pay_bundle_window_purchase_req,
    decode_purchase_req,
    decode_send_gift_req,
    default_bundle_shows,
    default_discount_stores,
    default_exchange_stores,
    default_gift_store_items,
    default_store_catalog,
    default_store_tabs,
    default_treasure_boxes,
    encode_award_data,
    encode_discount_store_purchase_res,
    encode_exchange_change_data,
    encode_exchange_store_purchase_res,
    encode_get_bundle_res,
    encode_get_discount_store_desc_res,
    encode_get_exchange_store_res,
    encode_get_gift_store_details_res,
    encode_get_gift_store_res,
    encode_get_installment_items_res,
    encode_get_installment_store_desc_res,
    encode_get_pay_bundle_window_desc_res,
    encode_get_store_res,
    encode_get_store_tab_res,
    encode_get_treasure_box_res,
    encode_installment_purchase_res,
    encode_open_bundle_res,
    encode_open_treasure_box_res,
    encode_pay_bundle_window_purchase_res,
    encode_purchase_res,
    encode_send_gift_res,
)

INFINITE_COINS = 999999
INFINITE_GEMS = 999999


class StoreService:
    """Thread-safe Store, Bundle, Crate, Gift, Exchange & Discount service."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._catalog: List[Dict[str, Any]] = default_store_catalog()
        self._by_store_id: Dict[int, Dict[str, Any]] = {
            int(it["store_id"]): it for it in self._catalog
        }
        self._by_item_id: Dict[int, Dict[str, Any]] = {
            int(it["item_id"]): it for it in self._catalog
        }
        self._gift_items: List[Dict[str, Any]] = default_gift_store_items()
        self._gift_by_commodity: Dict[int, Dict[str, Any]] = {
            int(it["commodity_id"]): it for it in self._gift_items
        }
        self._exchange_stores: List[Dict[str, Any]] = default_exchange_stores()
        self._discount_stores: List[Dict[str, Any]] = default_discount_stores()

        # Per-account purchase counters
        self._store_purchases: Dict[int, Dict[int, int]] = {}
        self._exchange_purchases: Dict[int, Dict[Tuple[int, int], int]] = {}
        self._discount_purchases: Dict[int, Dict[Tuple[int, int], int]] = {}
        self._gift_count_today: Dict[int, int] = {}
        self._next_trans_id = int(time.time()) * 1000

    def _alloc_trans_id(self, requested_trans_id: int) -> int:
        if requested_trans_id and int(requested_trans_id) > 0:
            return int(requested_trans_id)
        with self._lock:
            self._next_trans_id += 1
            return self._next_trans_id

    @staticmethod
    def _ensure_infinite_wallet(account_id: int) -> Dict[str, int]:
        """Keep player wallet topped up to infinite coins & gems."""
        wallet = state.get_wallet(account_id)
        coins = max(INFINITE_COINS, int(wallet.get("coins", 0)))
        gems = max(INFINITE_GEMS, int(wallet.get("gems", 0)))
        if coins != wallet.get("coins") or gems != wallet.get("gems"):
            return state.set_wallet(coins=coins, gems=gems, account_id=account_id)
        return wallet

    @staticmethod
    def _grant_unlocked_item(item_id: int, count: int = 1) -> Dict[str, Any]:
        """Grant item_id in core.state.state and unlock associated character/pet if applicable."""
        iid = int(item_id)
        cnt = max(1, int(count))
        new_total = state.add_item(iid, cnt)

        # Unlock pet or pet skin if item belongs to pet prefix (130xxxxxxx / 131xxxxxxx)
        prefix3 = iid // 1_000_000
        if prefix3 == 130:
            state.unlock_pet(pet_id=iid)
        elif prefix3 == 131:
            # Map skin 1310000XY -> pet 13000000(X*10 + 1) matching Pet.csv (1300000001, 11, 21, 31, 41)
            pet_offset = ((iid % 100) // 10) * 10
            if pet_offset in (0, 10, 20, 30, 40):
                state.unlock_pet(pet_id=1300000001 + pet_offset, skins=[iid])

        # Character bundles / direct character avatars unlock their corresponding character too
        if prefix3 in (101, 102):
            state.unlock_character(avatar_id=iid)
        bundle_meta = BUNDLE_DEFINITIONS.get(iid)
        if bundle_meta and bundle_meta.get("avatar_id"):
            state.unlock_character(avatar_id=int(bundle_meta["avatar_id"]))

        return {
            "item_id": iid,
            "cnt": cnt,
            "history_owned_cnt": new_total,
            "item_status": ItemStatus.PERMANENT,
        }

    # ------------------------------------------------------------------
    # Catalog Builders
    # ------------------------------------------------------------------
    def get_store_items(self, account_id: int, language: str = "en") -> List[Dict[str, Any]]:
        with self._lock:
            counts = self._store_purchases.get(account_id, {})
            out: List[Dict[str, Any]] = []
            for entry in self._catalog:
                item = copy.deepcopy(entry)
                item["language"] = language or "en"
                item["purchase_times"] = counts.get(int(item["store_id"]), 0)
                out.append(item)
            return out

    def get_gift_details(self, account_id: int) -> Dict[str, Any]:
        with self._lock:
            return {
                "store_id": 1,
                "items": copy.deepcopy(self._gift_items),
                "send_gift_times_today": self._gift_count_today.get(account_id, 0),
            }

    def get_exchange_stores(self, account_id: int, language: str = "en") -> List[Dict[str, Any]]:
        with self._lock:
            counts = self._exchange_purchases.get(account_id, {})
            stores = copy.deepcopy(self._exchange_stores)
            for st in stores:
                sid = int(st["exchange_store_desc"]["store_id"])
                for it in st.get("exchange_store_items", []):
                    cid = int(it["commodity_id"])
                    it["language"] = language or "en"
                    it["purchase_times"] = counts.get((sid, cid), 0)
            return stores

    def get_discount_stores(self, account_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            counts = self._discount_purchases.get(account_id, {})
            out = copy.deepcopy(self._discount_stores)
            for ds in out:
                key = (int(ds["store_id"]), int(ds["item_id"]))
                ds["purchase_times"] = counts.get(key, 0)
            return out

    # ------------------------------------------------------------------
    # Purchase / Open / Gift Actions
    # ------------------------------------------------------------------
    def purchase_item(self, req: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        """
        Handle both /Purchase (CSPurchaseReq) and /BuyItem.
        Resolves store_item_id as store_id or item_id, grants item(s) to state,
        keeps wallet infinite (999999 coins/gems), and returns CSPurchaseRes.
        """
        store_item_id = int(req.get("store_item_id", 0))
        cnt = max(1, int(req.get("cnt", 1)))
        trans_id = self._alloc_trans_id(int(req.get("trans_id", 0)))

        with self._lock:
            entry = self._by_store_id.get(store_item_id) or self._by_item_id.get(store_item_id)
            if entry:
                item_id = int(entry["item_id"])
                store_id = int(entry["store_id"])
                acc_counts = self._store_purchases.setdefault(account_id, {})
                acc_counts[store_id] = acc_counts.get(store_id, 0) + cnt
            else:
                # Direct item_id purchase fallback (if /BuyItem passes raw item_id)
                item_id = store_item_id if store_item_id > 0 else 203000001

            granted = self._grant_unlocked_item(item_id, cnt)
            wallet = self._ensure_infinite_wallet(account_id)

        change_data = encode_exchange_change_data(
            trans_id=trans_id,
            add_item_list=[granted],
            coins_delta=0,
            gems_delta=0,
            reason=TransReason.PURCHASE,
            check_bundle=item_id in BUNDLE_DEFINITIONS,
        )
        return encode_purchase_res(
            change_data=change_data,
            coins=int(wallet["coins"]),
            gems=int(wallet["gems"]),
        )

    def open_bundle(self, req: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        """Handle /OpenBundle -> unpacks bundle contents into core.state.state."""
        bundle_id = int(req.get("item_id", 0))
        trans_id = self._alloc_trans_id(0)

        with self._lock:
            meta = BUNDLE_DEFINITIONS.get(bundle_id)
            reward_ids = list(meta["items"]) if meta else [203000001, 204000001, 205000001, 211000001]
            if meta and meta.get("avatar_id"):
                state.unlock_character(avatar_id=int(meta["avatar_id"]))

            add_items = [self._grant_unlocked_item(rid, 1) for rid in reward_ids]
            del_items = [{"item_id": bundle_id, "cnt": 1, "history_owned_cnt": max(1, state.get_item_count(bundle_id))}] if bundle_id else []
            transfer_awards = [
                {"award_id": rid, "award_num": 1, "award_type": AwardType.ITEM}
                for rid in reward_ids
            ]
            self._ensure_infinite_wallet(account_id)

        change_data = encode_exchange_change_data(
            trans_id=trans_id,
            add_item_list=add_items,
            del_item_list=del_items,
            coins_delta=0,
            gems_delta=0,
            reason=TransReason.BUNDLE,
            check_bundle=True,
        )
        return encode_open_bundle_res(change_data=change_data, transfer_to_items=transfer_awards)

    def open_treasure_box(self, req: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        """Handle /OpenTreasureBox -> awards crate/box weapon skins or gear to state."""
        box_id = int(req.get("treasure_id", 0))
        item_cnt = max(1, int(req.get("item_cnt", 1)))

        with self._lock:
            meta = TREASURE_BOX_DEFINITIONS.get(box_id)
            if meta and meta.get("rewards"):
                pool = [int(r["award_id"]) for r in meta["rewards"]]
            else:
                pool = [907000001, 907000002, 907000005, 907000010]

            granted_items: List[Dict[str, Any]] = []
            for idx in range(item_cnt):
                chosen_id = pool[idx % len(pool)] if idx == 0 else random.choice(pool)
                granted_items.append(self._grant_unlocked_item(chosen_id, 1))

            left_num = max(0, state.get_item_count(box_id) - item_cnt) if box_id else 0
            self._ensure_infinite_wallet(account_id)

        awards_bytes = encode_award_data(items=granted_items, coins=0, gems=0)
        return encode_open_treasure_box_res(awards=awards_bytes, left_box_num=left_num)

    def send_gift(self, req: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        """Handle /SendGift -> delivers gift mail to receivers and keeps infinite wallet."""
        receivers = [int(r) for r in req.get("receiver_account_ids", [])]
        commodity_id = int(req.get("commodity_id", 0))
        cnt = max(1, int(req.get("commodity_cnt", 1)))
        message = str(req.get("message_content", "") or "Enjoy your gift!")

        with self._lock:
            gift_meta = self._gift_by_commodity.get(commodity_id)
            item_id = int(gift_meta["item_id"]) if gift_meta else (commodity_id or 700000001)
            sender_prof = state.get_profile(account_id) or {}
            sender_nick = str(sender_prof.get("nickname", "Clack"))

            for rid in receivers:
                state.add_mail(
                    title="Gift Received!",
                    content=message,
                    attachments=[{"item_id": item_id, "count": cnt, "type": AwardType.ITEM}],
                    sender_id=account_id,
                    sender_nick=sender_nick,
                    account_id=rid,
                )

            today = self._gift_count_today.get(account_id, 0) + max(1, len(receivers))
            self._gift_count_today[account_id] = today
            self._ensure_infinite_wallet(account_id)

        return encode_send_gift_res(remove_ids=receivers, send_gift_times_today=today)

    def exchange_purchase(self, req: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        """Handle /ExchangeStorePurchase -> grants redeemed item and keeps wallet infinite."""
        store_id = int(req.get("store_id", 1))
        commodity_id = int(req.get("commodity_id", 0))
        cnt = max(1, int(req.get("cnt", 1)))
        trans_id = self._alloc_trans_id(int(req.get("trans_id", 0)))

        with self._lock:
            item_id = 700000001
            for st in self._exchange_stores:
                if int(st["exchange_store_desc"]["store_id"]) == store_id or store_id == 0:
                    for it in st.get("exchange_store_items", []):
                        if int(it["commodity_id"]) == commodity_id:
                            item_id = int(it["item_id"])
                            break

            granted = self._grant_unlocked_item(item_id, cnt)
            acc_counts = self._exchange_purchases.setdefault(account_id, {})
            key = (store_id, commodity_id)
            acc_counts[key] = acc_counts.get(key, 0) + cnt
            ptimes = acc_counts[key]
            self._ensure_infinite_wallet(account_id)

        change_data = encode_exchange_change_data(
            trans_id=trans_id,
            add_item_list=[granted],
            coins_delta=0,
            gems_delta=0,
            reason=TransReason.EXCHANGESTORE_PURCHASE,
            check_bundle=item_id in BUNDLE_DEFINITIONS,
        )
        return encode_exchange_store_purchase_res(change_data=change_data, purchase_times=ptimes)

    def discount_purchase(self, req: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        """Handle /DiscountStorePurchase -> grants discounted item and keeps wallet infinite."""
        store_id = int(req.get("store_id", 1))
        item_id = int(req.get("item_id", 0)) or 700000003
        cnt = max(1, int(req.get("cnt", 1)))
        trans_id = self._alloc_trans_id(0)

        with self._lock:
            granted = self._grant_unlocked_item(item_id, cnt)
            acc_counts = self._discount_purchases.setdefault(account_id, {})
            key = (store_id, item_id)
            acc_counts[key] = acc_counts.get(key, 0) + cnt
            pcount = acc_counts[key]
            self._ensure_infinite_wallet(account_id)

        change_data = encode_exchange_change_data(
            trans_id=trans_id,
            add_item_list=[granted],
            coins_delta=0,
            gems_delta=0,
            reason=TransReason.PURCHASE,
            check_bundle=item_id in BUNDLE_DEFINITIONS,
        )
        return encode_discount_store_purchase_res(change_data=change_data, purchase_count=pcount)

    def installment_purchase(self, req: Dict[str, Any], account_id: int = DEFAULT_ACCOUNT_ID) -> bytes:
        """Handle /InstallmentPurchase -> unlocks item cleanly with infinite wallet."""
        item_id = int(req.get("item_id", 0)) or 203000001
        trans_id = self._alloc_trans_id(0)
        with self._lock:
            granted = self._grant_unlocked_item(item_id, 1)
            self._ensure_infinite_wallet(account_id)
        change_data = encode_exchange_change_data(
            trans_id=trans_id,
            add_item_list=[granted],
            reason=TransReason.PURCHASE,
        )
        return encode_installment_purchase_res(change_data=change_data)


store_service = StoreService()


# ------------------------------------------------------------------
# HTTP Request Dispatcher
# ------------------------------------------------------------------
def _normalize_endpoint(path: str) -> str:
    clean = path.split("?", 1)[0].strip()
    return clean.rsplit("/", 1)[-1]


def handle_store_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Free Fire 1.39 Store / Gift / Bundle / Crate / Exchange / Discount
    HTTP requests. Returns True if handled, False otherwise.
    """
    endpoint = _normalize_endpoint(path)

    if endpoint == "GetStore":
        req = decode_get_store_req(raw_body)
        aid = int(req.get("account_id") or account_id)
        items = store_service.get_store_items(aid, language=req.get("language", "en"))
        handler.send_proto("CSGetStoreRes", encode_get_store_res(items))
        return True

    if endpoint == "GetStoreTab":
        handler.send_proto("CSGetStoreTabRes", encode_get_store_tab_res(default_store_tabs()))
        return True

    if endpoint in ("Purchase", "BuyItem"):
        req = decode_purchase_req(raw_body)
        proto_name = "CSBuyItemRes" if endpoint == "BuyItem" else "CSPurchaseRes"
        handler.send_proto(proto_name, store_service.purchase_item(req, account_id=account_id))
        return True

    if endpoint == "GetBundle":
        handler.send_proto("CSGetBundleRes", encode_get_bundle_res(default_bundle_shows()))
        return True

    if endpoint == "OpenBundle":
        req = decode_open_bundle_req(raw_body)
        handler.send_proto("CSOpenBundleRes", store_service.open_bundle(req, account_id=account_id))
        return True

    if endpoint == "GetTreasureBox":
        boxes, crates = default_treasure_boxes()
        handler.send_proto("CSGetTreasureBoxRes", encode_get_treasure_box_res(boxes, crates))
        return True

    if endpoint == "OpenTreasureBox":
        req = decode_open_treasure_box_req(raw_body)
        handler.send_proto("CSOpenTreasureBoxRes", store_service.open_treasure_box(req, account_id=account_id))
        return True

    if endpoint == "GetTreasureBoxPR":
        handler.send_proto("Empty (GetTreasureBoxPR)", b"")
        return True

    if endpoint == "GetGiftStore":
        handler.send_proto("CSGetGiftStoreRes", encode_get_gift_store_res())
        return True

    if endpoint == "GetGiftStoreDetails":
        details = store_service.get_gift_details(account_id=account_id)
        handler.send_proto(
            "CSGetGiftStoreDetailsRes",
            encode_get_gift_store_details_res(
                store_id=details["store_id"],
                items=details["items"],
                send_gift_times_today=details["send_gift_times_today"],
            ),
        )
        return True

    if endpoint == "SendGift":
        req = decode_send_gift_req(raw_body)
        handler.send_proto("CSSendGiftRes", store_service.send_gift(req, account_id=account_id))
        return True

    if endpoint == "GetExchangeStore":
        req = decode_get_exchange_store_req(raw_body)
        stores = store_service.get_exchange_stores(account_id=account_id, language=req.get("language", "en"))
        handler.send_proto("CSGetExchangeStoreRes", encode_get_exchange_store_res(stores))
        return True

    if endpoint == "ExchangeStorePurchase":
        req = decode_exchange_store_purchase_req(raw_body)
        handler.send_proto(
            "CSExchangeStorePurchaseRes",
            store_service.exchange_purchase(req, account_id=account_id),
        )
        return True

    if endpoint == "GetDiscountStore":
        discounts = store_service.get_discount_stores(account_id=account_id)
        handler.send_proto("CSGetDiscountStoreDescRes", encode_get_discount_store_desc_res(discounts))
        return True

    if endpoint == "DiscountStorePurchase":
        req = decode_discount_store_purchase_req(raw_body)
        handler.send_proto(
            "CSDiscountStorePurchaseRes",
            store_service.discount_purchase(req, account_id=account_id),
        )
        return True

    if endpoint == "GetPayBundleWindowDesc":
        handler.send_proto("CSGetPayBundleWindowDescRes", encode_get_pay_bundle_window_desc_res())
        return True

    if endpoint == "PayBundleWindowPurchase":
        _ = decode_pay_bundle_window_purchase_req(raw_body)
        handler.send_proto("CSPayBundleWindowPurchaseRes", encode_pay_bundle_window_purchase_res())
        return True

    if endpoint == "GetInstallmentStore":
        _ = decode_get_installment_store_req(raw_body)
        handler.send_proto("CSGetInstallmentStoreDescRes", encode_get_installment_store_desc_res())
        return True

    if endpoint == "InstallmentPurchase":
        req = decode_installment_purchase_req(raw_body)
        handler.send_proto(
            "CSInstallmentPurchaseRes",
            store_service.installment_purchase(req, account_id=account_id),
        )
        return True

    if endpoint == "GetInstallmentItems":
        handler.send_proto("CSGetInstallmentItemsRes", encode_get_installment_items_res())
        return True

    return False


handle_store_post = handle_store_request
