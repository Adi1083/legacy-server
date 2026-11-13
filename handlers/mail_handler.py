"""
HTTP request handlers for Free Fire 1.39 Mail System.

Handles:
- /GetMailList  -> proto.CSGetMailListRes
- /ReadMail     -> proto.CSReadMailRes (status=1 claims/marks processed, status=2 deletes)
- /ClaimMail    -> proto.CSReadMailRes
- /ClaimAllMail -> proto.CSReadMailRes
- /DeleteMail   -> proto.CSReadMailRes

Integrates directly with core.state.ServerState so mails created via the Web
Dashboard appear immediately in-game with claimable coins, diamonds, and items.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.mail_models import (
    MailStatus,
    decode_claim_mail_req,
    decode_get_mail_list_req,
    decode_read_mail_req,
    encode_get_mail_list_res,
    encode_read_mail_res,
)


def _claim_mail_ids(mail_ids: List[int], account_id: int) -> Dict[str, Any]:
    """Claim rewards for a list of mail IDs and aggregate granted items/currency."""
    total_coins = 0
    total_gems = 0
    all_items: List[Dict[str, Any]] = []
    claimed_ids: List[int] = []

    for mid in mail_ids:
        mail = state.get_mail(mid, account_id=account_id)
        if not mail:
            continue
        if not mail.get("is_claimed"):
            res = state.claim_mail(mid, account_id=account_id)
            if res.get("ok"):
                claimed_ids.append(mid)
                total_coins += int(res.get("coins_added", 0))
                total_gems += int(res.get("gems_added", 0))
                all_items.extend(res.get("rewards") or [])
        else:
            state.read_mail(mid, account_id=account_id)

    return {
        "claimed_ids": claimed_ids,
        "coins": total_coins,
        "gems": total_gems,
        "items": all_items,
    }


def handle_mail_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """
    Dispatch Mail HTTP endpoints. Returns True if path was handled, False otherwise.
    """
    endpoint = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]

    if endpoint == "GetMailList":
        _ = decode_get_mail_list_req(raw_body)
        mails = state.list_mails(account_id=account_id)
        payload = encode_get_mail_list_res(mails)
        handler.send_proto("CSGetMailListRes", payload)
        return True

    if endpoint == "ReadMail":
        req = decode_read_mail_req(raw_body)
        mail_ids = req["mail_ids"]
        req_status = req["status"]

        if req_status == MailStatus.DELETED:
            for mid in mail_ids:
                state.delete_mail(mid, account_id=account_id)
            handler.send_proto("CSReadMailRes (Delete)", encode_read_mail_res())
            return True

        if req_status == MailStatus.INIT:
            for mid in mail_ids:
                state.read_mail(mid, account_id=account_id)
            handler.send_proto("CSReadMailRes (MarkRead)", encode_read_mail_res())
            return True

        # Status_PROCESSED (1): UIModelMail sends status=1 on Receive / Receive All / Open
        agg = _claim_mail_ids(mail_ids, account_id=account_id)
        payload = encode_read_mail_res(
            items=agg["items"],
            coins=agg["coins"],
            gems=agg["gems"],
        )
        handler.send_proto("CSReadMailRes (Claim)", payload)
        return True

    if endpoint == "ClaimMail":
        req = decode_claim_mail_req(raw_body)
        agg = _claim_mail_ids(req["mail_ids"], account_id=account_id)
        payload = encode_read_mail_res(
            items=agg["items"],
            coins=agg["coins"],
            gems=agg["gems"],
        )
        handler.send_proto("CSReadMailRes (ClaimMail)", payload)
        return True

    if endpoint == "ClaimAllMail":
        res = state.claim_all_mails(account_id=account_id)
        payload = encode_read_mail_res(
            items=res.get("rewards") or [],
            coins=int(res.get("coins_added", 0)),
            gems=int(res.get("gems_added", 0)),
        )
        handler.send_proto("CSReadMailRes (ClaimAllMail)", payload)
        return True

    if endpoint == "DeleteMail":
        req = decode_claim_mail_req(raw_body)
        for mid in req["mail_ids"]:
            state.delete_mail(mid, account_id=account_id)
        handler.send_proto("CSReadMailRes (DeleteMail)", encode_read_mail_res())
        return True

    return False


# Alias for router consistency
handle_mail_post = handle_mail_request
