"""
HTTP request handlers for the Free Fire 1.39 Friends & Social system.

Handles all verified Free Fire 1.39 client endpoints and compatibility aliases:
  - /GetFriend                  -> proto.AccountFriendRes
  - /GetFriendIDs               -> proto.AccountIDSlice (packed uint64[])
  - /GetFriendRequestList       -> proto.AccountInfoBasicBundleRes
  - /GetRecommendedFriend       -> proto.AccountFriendRes
  - /GetPlatformFriends         -> proto.AccountFriendRes
  - /GetPlatformFriendIDs       -> proto.AccountIDSlice
  - /GetFacebookFriend          -> proto.AccountFriendRes
  - /RequestAddingFriend        -> Empty (200 OK)
  - /AddFriend                  -> Empty (200 OK)
  - /ApplyFriend                -> Empty (200 OK)
  - /ConfirmFriendRequest       -> proto.AccountInfoWithPresence
  - /DeclineFriendRequest       -> Empty (200 OK)
  - /HandleFriendRequest        -> proto.AccountInfoWithPresence (accept) or Empty (decline)
  - /RemoveFriend               -> proto.CSRemoveFriendRes
  - /FuzzySearchAccountByName   -> proto.AccountInfoBasicBundleRes
  - /SearchAccount              -> proto.AccountInfoBasicBundleRes
  - /GetAccountInfoByAccountID  -> proto.AccountInfoBasic
  - /GetPresenceByAccountIds    -> AccountPresence bundle
  - /FriendInvite               -> Empty (200 OK)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from core.state import DEFAULT_ACCOUNT_ID, state
from proto.social_models import (
    decode_account_id_req,
    decode_account_id_slice,
    decode_cs_friend_invite_req,
    decode_cs_friend_req,
    decode_cs_get_friend_list_req,
    decode_cs_handle_friend_req,
    decode_cs_remove_friend_req,
    decode_search_account_req,
    encode_account_friend_res,
    encode_account_id_slice,
    encode_account_info_basic,
    encode_account_info_basic_bundle_res,
    encode_account_info_with_presence,
    encode_cs_remove_friend_res,
    encode_presence_bundle_res,
)


def _normalize_endpoint(path: str) -> str:
    clean = path.split("?", 1)[0].rstrip("/")
    return clean.rsplit("/", 1)[-1]


def _resolve_peer_id(primary: int, secondary: int, account_id: int) -> int:
    if primary and primary != account_id:
        return primary
    if secondary and secondary != account_id:
        return secondary
    return primary or secondary


def _handle_get_friend(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_get_friend_list_req(raw_body)
    friends = state.list_friends(account_id)
    payload = encode_account_friend_res(friends, need_stats=req["need_stats"])
    handler.send_proto("AccountFriendRes", payload)


def _handle_get_friend_ids(handler: Any, _ip: str, _raw_body: bytes, account_id: int) -> None:
    ids = state.list_friend_ids(account_id)
    handler.send_proto("AccountIDSlice", encode_account_id_slice(ids))


def _handle_get_friend_request_list(handler: Any, _ip: str, _raw_body: bytes, account_id: int) -> None:
    requests = state.list_friend_requests(account_id)
    players = [entry["player"] for entry in requests if entry.get("player")]
    handler.send_proto("AccountInfoBasicBundleRes", encode_account_info_basic_bundle_res(players))


def _handle_get_recommended_friend(handler: Any, _ip: str, _raw_body: bytes, account_id: int) -> None:
    recs = state.list_recommended_friends(account_id, limit=20)
    handler.send_proto("AccountFriendRes", encode_account_friend_res(recs))


def _handle_get_platform_friends(handler: Any, _ip: str, _raw_body: bytes, _account_id: int) -> None:
    handler.send_proto("AccountFriendRes", encode_account_friend_res([]))


def _handle_get_platform_friend_ids(handler: Any, _ip: str, _raw_body: bytes, _account_id: int) -> None:
    handler.send_proto("AccountIDSlice", encode_account_id_slice([]))


def _handle_add_friend(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_friend_req(raw_body)
    target_id = _resolve_peer_id(req["addee"], req["adder"], account_id)
    if target_id:
        target = state.get_player(target_id)
        auto_accept = bool(target and target.get("is_bot"))
        res = state.add_friend(target_id, account_id=account_id, auto_accept=auto_accept)
        print(f"  [+] Friend add/apply: {account_id} -> {target_id} ({res['status']})", flush=True)
    handler.send_bytes(b"", status=200)


def _accept_and_send_presence(handler: Any, friend_id: int, account_id: int) -> None:
    player = state.accept_friend(friend_id, account_id=account_id) if friend_id else None
    if player is None and friend_id:
        existing = state.get_player(friend_id)
        if existing:
            player = state.add_friend(friend_id, account_id=account_id, auto_accept=True).get("player")
    if player:
        handler.send_proto("AccountInfoWithPresence", encode_account_info_with_presence(player))
    else:
        handler.send_proto("AccountInfoWithPresence", b"")


def _handle_confirm_friend_request(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_friend_req(raw_body)
    friend_id = _resolve_peer_id(req["adder"], req["addee"], account_id)
    _accept_and_send_presence(handler, friend_id, account_id)


def _handle_decline_friend_request(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_friend_req(raw_body)
    friend_id = _resolve_peer_id(req["adder"], req["addee"], account_id)
    if friend_id:
        state.reject_friend(friend_id, account_id=account_id)
    handler.send_bytes(b"", status=200)


def _handle_friend_request_generic(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_handle_friend_req(raw_body)
    friend_id = _resolve_peer_id(req["adder"], req["addee"], account_id)
    action = req["action"]
    if action is not None and action in (0, 2):
        if friend_id:
            state.reject_friend(friend_id, account_id=account_id)
        handler.send_bytes(b"", status=200)
        return
    _accept_and_send_presence(handler, friend_id, account_id)


def _handle_remove_friend(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    req = decode_cs_remove_friend_req(raw_body)
    remover = req["remover"] or account_id
    removee = req["removee"]
    friend_id = _resolve_peer_id(removee, remover, account_id)
    if friend_id:
        state.remove_friend(friend_id, account_id=account_id)
    handler.send_proto(
        "CSRemoveFriendRes",
        encode_cs_remove_friend_res(remover=remover, removee=removee or friend_id),
    )


def _handle_search_account(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    req = decode_search_account_req(raw_body)
    query = req["query"]
    results: List[Dict[str, Any]] = []
    if query:
        results = state.search_players(query, limit=20, exclude_account_id=account_id)
    handler.send_proto("AccountInfoBasicBundleRes", encode_account_info_basic_bundle_res(results))


def _handle_get_account_info_by_id(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    target_id = decode_account_id_req(raw_body) or account_id
    player = state.get_player(target_id)
    if player is None and target_id == account_id:
        player = state.get_profile(account_id)
    payload = encode_account_info_basic(player) if player else b""
    handler.send_proto("AccountInfoBasic", payload)


def _handle_get_presence_by_ids(handler: Any, _ip: str, raw_body: bytes, account_id: int) -> None:
    ids = decode_account_id_slice(raw_body)
    if ids:
        players = [p for aid in ids if (p := state.get_player(aid)) is not None]
    else:
        players = state.list_friends(account_id)
    handler.send_proto("AccountPresenceBundleRes", encode_presence_bundle_res(players))


def _handle_friend_invite(handler: Any, _ip: str, raw_body: bytes, _account_id: int) -> None:
    req = decode_cs_friend_invite_req(raw_body)
    print(f"  [>] FriendInvite: inviter={req['inviter_id']} activity={req['activity_id']}", flush=True)
    handler.send_bytes(b"", status=200)


_SOCIAL_ROUTES: Dict[str, Callable[[Any, str, bytes, int], None]] = {
    "GetFriend": _handle_get_friend,
    "GetFriendIDs": _handle_get_friend_ids,
    "GetFriendRequestList": _handle_get_friend_request_list,
    "GetRecommendedFriend": _handle_get_recommended_friend,
    "GetPlatformFriends": _handle_get_platform_friends,
    "GetPlatformFriendIDs": _handle_get_platform_friend_ids,
    "GetFacebookFriend": _handle_get_platform_friends,
    "RequestAddingFriend": _handle_add_friend,
    "AddFriend": _handle_add_friend,
    "ApplyFriend": _handle_add_friend,
    "ConfirmFriendRequest": _handle_confirm_friend_request,
    "DeclineFriendRequest": _handle_decline_friend_request,
    "HandleFriendRequest": _handle_friend_request_generic,
    "RemoveFriend": _handle_remove_friend,
    "FuzzySearchAccountByName": _handle_search_account,
    "SearchAccount": _handle_search_account,
    "GetAccountInfoByAccountID": _handle_get_account_info_by_id,
    "GetPresenceByAccountIds": _handle_get_presence_by_ids,
    "FriendInvite": _handle_friend_invite,
}


def handle_social_request(
    handler: Any,
    path: str,
    client_ip: str,
    raw_body: bytes,
    account_id: int = DEFAULT_ACCOUNT_ID,
) -> bool:
    """Dispatch Friends & Social endpoints; returns True if path matched."""
    endpoint = _normalize_endpoint(path)
    fn = _SOCIAL_ROUTES.get(endpoint)
    if fn is None:
        return False
    fn(handler, client_ip, raw_body, account_id)
    return True


handle_social_post = handle_social_request
