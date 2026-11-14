import time
from .encoder import (
    encode_uint64, encode_uint32, encode_int32,
    encode_string, encode_bool, encode_submessage, encode_fixed64
)

def encode_major_login_res(account_id=10001, region="DEFAULT", token="barbosa_session_token_12345", ttl=86400, server_url="http://10.0.2.2:8080/"):
    buf = bytearray()
    buf += encode_uint64(1, account_id)
    buf += encode_string(2, region)
    buf += encode_string(3, region)
    buf += encode_string(4, region)
    buf += encode_string(5, "")
    buf += encode_string(6, region)
    buf += encode_string(7, region)
    buf += encode_string(8, token)
    buf += encode_uint32(9, ttl)
    buf += encode_string(10, server_url)
    return bytes(buf)

def encode_basic_ep_info():
    buf = bytearray()
    buf += encode_uint32(1, 1)    # ep_event_id
    buf += encode_bool(2, True)   # owned_pass
    buf += encode_uint32(3, 1)    # ep_badge
    buf += encode_uint32(4, 100)  # badge_cnt
    return bytes(buf)

def encode_ranking_info():
    buf = bytearray()
    buf += encode_uint32(1, 1)    # season_id
    buf += encode_uint32(2, 1)    # rank
    buf += encode_uint32(3, 1)    # max_rank
    buf += encode_uint32(4, 1000) # ranking_points
    return bytes(buf)

def encode_login_res(
    account_id=10001,
    nickname="Clack",
    region="DEFAULT",
    host="10.0.2.2:8080",
    tcp_addr=None,
    chat_server=1,
):
    if not tcp_addr:
        tcp_host = host.split(":", 1)[0].strip() or "10.0.2.2"
        tcp_addr = f"{tcp_host}:8081"

    buf = bytearray()
    buf += encode_uint64(1, account_id)
    buf += encode_uint32(2, 1)
    buf += encode_string(3, region)
    buf += encode_string(4, nickname)
    buf += encode_uint64(5, 1570000000)
    buf += encode_uint32(6, 60)
    buf += encode_uint32(7, 99999)
    buf += encode_uint32(8, chat_server)      # chat_server <= 9998 required by IsChatServerValid
    buf += encode_uint32(9, 999999)
    buf += encode_int32(10, 999999)
    buf += encode_string(14, tcp_addr)        # notification_channel -> Lobby TCP host:port
    buf += encode_uint32(15, 0)
    buf += encode_string(16, f"http://{host}/event")
    buf += encode_uint64(20, 0)
    buf += encode_uint64(23, int(time.time()))
    buf += encode_string(24, region)
    buf += encode_uint32(25, 0)
    buf += encode_bool(26, False)
    buf += encode_uint32(27, 0)
    buf += encode_uint32(28, 0) # MUST be 0
    buf += encode_bool(29, True)
    buf += encode_uint32(30, 1)
    buf += encode_uint32(31, 100)
    buf += encode_string(32, tcp_addr)        # chat_addr -> Chat TCP host:port
    buf += encode_bool(33, True)
    buf += encode_submessage(34, encode_basic_ep_info())
    buf += encode_submessage(35, encode_ranking_info())
    buf += encode_uint64(36, 0)
    buf += encode_uint32(37, 0)
    buf += encode_string(39, f"http://{host}/log")
    buf += encode_string(40, "10.0.2.2")
    buf += encode_string(42, region)
    buf += encode_fixed64(43, 0.0)
    return bytes(buf)

def encode_avatar_profile(avatar_id=1, unlocked_level=1, skin_color=0, is_selected=True):
    buf = bytearray()
    buf += encode_uint32(1, avatar_id)
    buf += encode_uint32(2, unlocked_level)
    buf += encode_uint32(3, skin_color)
    buf += encode_bool(6, is_selected)
    buf += encode_uint32(7, 0)
    return bytes(buf)

def encode_profile_list_res(avatar_id=1):
    buf = bytearray()
    buf += encode_submessage(1, encode_avatar_profile(avatar_id, 1, 0, True))
    return bytes(buf)

def encode_skill_list_res(account_id=10001):
    buf = bytearray()
    buf += encode_uint64(1, account_id)
    return bytes(buf)

def encode_login_profile_res(account_id=10001, avatar_id=1):
    buf = bytearray()
    buf += encode_submessage(1, encode_profile_list_res(avatar_id))
    buf += encode_submessage(2, encode_skill_list_res(account_id))
    return bytes(buf)

def encode_login_desc_res():
    buf = bytearray()
    for tag in range(1, 21):
        buf += encode_submessage(tag, b"")
    return bytes(buf)

def encode_login_splash_res():
    buf = bytearray()
    for tag in range(1, 4):
        buf += encode_submessage(tag, b"")
    return bytes(buf)

def encode_account_info_basic(account_id=10001, nickname="Clack", level=60, banner_id=1):
    buf = bytearray()
    buf += encode_uint64(1, account_id)
    buf += encode_uint32(2, 1)
    buf += encode_string(3, nickname)
    buf += encode_string(4, str(account_id))
    buf += encode_string(5, "DEFAULT")
    buf += encode_uint32(6, level)
    buf += encode_uint32(7, 99999)
    buf += encode_uint32(8, 1)
    buf += encode_string(9, nickname)
    buf += encode_string(10, "")
    buf += encode_uint32(11, banner_id)
    return bytes(buf)

def encode_personal_show_info(account_id=10001, nickname="Clack", avatar_id=1):
    buf = bytearray()
    buf += encode_submessage(1, encode_account_info_basic(account_id, nickname))
    buf += encode_submessage(2, encode_avatar_profile(avatar_id, 1, 0, True))
    return bytes(buf)

def encode_platform_profile_res(external_id="10001", external_name="Clack", external_type=1):
    buf = bytearray()
    buf += encode_string(1, external_id)
    buf += encode_uint32(2, external_type)
    buf += encode_string(3, external_name)
    buf += encode_string(4, "")
    return bytes(buf)

def encode_account_wallet(coins=999999, gems=999999, gop_gems=0, total_topup=0, last_topup_time=0):
    buf = bytearray()
    buf += encode_uint32(1, coins)
    buf += encode_int32(2, gems)
    if gop_gems:
        buf += encode_uint32(3, gop_gems)
    if total_topup:
        buf += encode_uint64(4, total_topup)
    if last_topup_time:
        buf += encode_int64(5, last_topup_time)
    return bytes(buf)

def encode_wallet_res(account_id=10001, coins=999999, gems=999999):
    buf = bytearray()
    buf += encode_uint64(1, account_id)
    buf += encode_submessage(2, encode_account_wallet(coins=coins, gems=gems))
    return bytes(buf)

def encode_backpack_res(coins=999999, gems=999999):
    buf = bytearray()
    buf += encode_submessage(1, encode_account_wallet(coins=coins, gems=gems))
    return bytes(buf)
