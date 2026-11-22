"""
Protobuf models and full real APK item catalog for Free Fire 1.39 Vault,
Backpack, Clothes, Loadouts, Collections, Armory/Shows, Emotes & Stickers.

Item IDs and (ItemType, ItemSubType, CollectionType) metadata are extracted
directly from IND PROJECT 1.39 APK DES-decrypted Config CSVs
(Item.csv, Clothes.csv, CollectionWeapon.csv, Loadout.csv, Bundle.csv, Pet.csv).

All ProtoMember tags, wire types, and IsPacked flags are verified from
Free Fire 1.39 global-metadata.dat + x86 libil2cpp.so.
"""

from __future__ import annotations

import base64
import json
import zlib
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .decoder import decode_proto, get_packed_varints, get_varint
from .encoder import (
    encode_bool,
    encode_int32,
    encode_int64,
    encode_packed_uint32,
    encode_submessage,
    encode_uint32,
    encode_uint64,
)
from .store_models import ItemStatus, ItemSubType, ItemType, encode_item


# ---------------------------------------------------------------------------
# Default Equipped IDs (verified from Avatar.csv / Clothes.csv / Item.csv)
# ---------------------------------------------------------------------------

DEFAULT_AVATAR_ID = 102000004  # Adam (Male default)
DEFAULT_FEMALE_AVATAR_ID = 101000001  # Eve (Female default)
DEFAULT_CLOTHES: List[int] = [
    211000000,  # Hair (Type=11)
    208000000,  # Face (Type=8)
    203000573,  # Top (Type=3)
    204000345,  # Pants (Type=4)
    205000299,  # Shoes (Type=5)
]
DEFAULT_LOADOUTS: List[int] = [500000001, 500000005]  # Bullets + Bonfire
DEFAULT_COLLECTION_SLOTS: List[int] = [
    904000001,  # Backpack
    209000001,  # Parachute
    906000001,  # Skyboard
    903000001,  # Lootbox
    908000001,  # Vehicle skin
]
DEFAULT_WEAPON_SHOWS: List[int] = [
    907000001,  # USP Camo
    907000005,  # AWM
    907000010,  # M4A1
    907000013,  # AK
    907000014,  # SCAR
]
DEFAULT_EMOTES: List[Tuple[int, int]] = [
    (1, 909000001),
    (2, 909000002),
    (3, 909000003),
    (4, 909000004),
]

# Stackable item types/subtypes granted at x99 by default
_STACKABLE_TYPES: Set[int] = {
    ItemType.TREASUREBOX,
    ItemType.LOADOUTBOX,
    ItemType.ROOMCARD,
    ItemType.BUNDLE,
    ItemType.DEBRIS,
    ItemType.VIRTUAL,
    ItemType.BONUSCARD,
}

# Compressed (item_id, item_type, item_sub_type, collection_type) for all
# 4,462 permanent items from APK DES-decrypted Item.csv / Clothes.csv / CollectionWeapon.csv
_CATALOG_B64 = (
    "eNpt3Vt2G0mSRdEJ1YeuPTwixlKr5z+N1oMlgdjoT1sq8hAMaDfMPTP/+9/60T9+/V/+U//58Z8f//efv5Ni0kyGyT"
    "I5TC4mN5PnfZIfTGgOzaE5NIfm0ByaQ3NoLpqL5qK5aC6ai+aiuWgumovmprlpbpqb5qa5aW6am+amuWkemofmoXlo"
    "HpqH5qF5aB6ah+aleWlempfmpXlpXpqX5qV5aT40H5oPzYfmQ/Oh+dB8aD40H5ovmi+aL5ovmi+aL5ovmi+aL5ovmm"
    "+ab5pvmm+ab5pvmm+ab5pvmm+aH5ofmh+aH5ofmh+aH5ofmh+an/fm/PjBJEyKSTMZJsvkMLmY3ExoxsHgYHAwOBgc"
    "DA4GB4ODwcHgYHAwOBgcDA4GB4ODwcHgYHAwOBgcDA4GB4ODwcHgYHAwOBgcDA4GB4ODwcHgYHAwOBgcDA4GB4ODwc"
    "HgYHAwOBgcDA4GB4ODwcHgYHAwOBgcDMYF44JxwbggWvAr+BX8Cn4Fv4Jfuezh9cGv4FfwK/gV/Ap+Bb+CX8Gv4Ffw"
    "K/gV/Ap+Bb+CX8Gv4FfwK/hV+FX4VfhV+FX4VfhV+FX4VfhV+FX4VfhV+FX4VfhV+FX4VfhV+FX4VfhV+FX4VfhV+F"
    "X4VfhV+FX4VfhV+FX4VfhV+FXYVNhU2FTYVNhU2FTYVNhU2FTYVNhU2FTYVNhU2FTYVNhU2FTYVNhU2FTYVNhU2FTY"
    "VNhU2FR8Ris+oxV+FX4VfhV+FZ/RCtGKz2iFcYVxhXGFcYVxhXGFcYVxhXGFcYVxhXGFcYVxhXGFcYVxhXGFcYVxhX"
    "GFcYVxhXGFcYVxhXGFcY1xjXGNcY1xjXGNcY1xjXGNcY1xjXGNcY1xjXGNcY1xjXGNcY1xjXGNcY1xjXGNcY1xjXGN"
    "cY1xjXGNcY1xjXGNcY1xzWe05jNa42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYO"
    "Ng42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg"
    "42DjYONg42DjYONg4+Dg4ODg4ODg4ODg4ODg4ODgoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN"
    "6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g3qDeoN6g"
    "3qDeYNxg3GDcYNxg3GDcYNxg3GDcYNxg3GDcYNxg3GDcYNxg3GDcYNxg3GDcYNxg3GDcYNxg3GDcYNxg3GDcYNxg3G"
    "DcYNxg3GDcYtxi3GLcYtxi3GLcYtxi3PJZb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9R"
    "b1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb1FvUW9Rb/"
    "mstzi4OLg4uDi4OLg4uDi4OLg4uDi4OLg4uDi43xwcbgAONwCHG4DDDcDhBuBwA3C4ATjcABxuAA43AIcbgMMNwOEG"
    "4HADcLgBONwAHG4ADjcAhxuAww3A4QbgcANwuAE43AAcbgAONwCHG4DDDcDhBuBwA3C4ATjcABxuAA43AIcbgMMNwO"
    "EG4HADcLgBONwAHG4ADjcAhxuAww3A4QbgcANwuAE43AAcbgAONwCHG4DDDcDhBuBwA3C4ATjcABxuAA43AIcbgMMN"
    "wOEG4HADcLgBONwAHG4ADjcAhxuAww3A4QbgcANwuAE43AAcbgAONwCHG4DDDcDhBuBwA3C4ATjcABxuAA43AIcbgM"
    "MNwOEG4HADcLgBONwAHG4ADjcAhxuAww3A4QbgcANwuAE43AAcbgAO9/2G+37Dfb/hvt9w32+47zfc9xvu+w33/Yb7"
    "fsN9v+G+33Dfb7jvN9z3G+77Dff9hvt+w32/4b7fcN9vuO833Pcb7vsN9/2G+37Dfb/hvt9w32+47zfc9xvu+w33/Y"
    "b7fsN9v+G+33Dfb7jvN9z3G+77Dff9hvt+w32/4b7fcN9vuO833Pcb7vsN9/2G+37Dfb/hvt9w32+47zfc9xvu+w33"
    "/Yb7fsN9v+G+33Dfb7jvN9z3G+77/ZnQjHpBvaBeUC+oF9QL6gX1gnpBvaBeUC+oF9QL6gX1gnpBvaBeUC+oF9QL6g"
    "X1gnpBvaBeUC+oF9QL6gX1gnpBve/3Bod7g8O9weHe4HBvcLg3ONwbHO4NDvcGh3uDw73B4d7gcG9wuDc43Bsc7g0O"
    "9waHe4PDvcHh3uBwb3C4NzjcGxzuDQ73Bod7g8O9weHe4HBvcLg3ONwbHO4NDvcGh3uDw73B4d7gnwnNOFg4WDhYOF"
    "g4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4"
    "WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg42DjYONg42DjYONg42D"
    "jYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjY"
    "ONg42DjYONg42DjYONg42Dj4/W7hcu6wnDss5w7LucNy7rCcOyznDsu5w3LusJw7LOcOy7nDcu6wnDss5w7LucNy7r"
    "CcOyznDsu5w3LusJw7LOcOy7nDcu6wnDss5w7LucNy7rCcOyznDsu5w3LusJw7LOcOy7nDcu6wnDss5w7LucNy7rCc"
    "OyznDsu5w3LusJw7LOcOy7nDcu6wnDss5w7LucNy7rCcOyznDsu5w3LusJw7LOcOy7nDcu6wnDss5w7LucNy7rCcOy"
    "znDsu5w3LusJw7LOcOy7nDcu6wnDss5w7LKcNyXrCcFyznBct5wXJesJwXLOcFy3nBcl6wnBcs5wXLecFyXrCcFyzn"
    "Bct5wXJesPwbA5YThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4"
    "TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4Tl"
    "BGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBG"
    "E5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5"
    "QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QV"
    "hOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhO"
    "EJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJ"
    "YThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYT"
    "hOUEYTlBWE4QlhOE5QRhOUFYThCWE4TlBGE5QVhOEJYThPv31vH16zxfk+fnZF8m+T15/TPFn2kmw2SZHCYXk5vJ8z"
    "4JzQkTmkNzaA7NoTk0h+bQXDQXzUVz0Vw0F81Fc9FcNBfNTXO/NP/8wP/2RH1NwqSYNJNhskwOk4vJzeR5n4Tm0Bya"
    "Q0/oCT2hp/juxfcqXp/i9Sl6ip6ip+zh9WkKm9enaW6am+amuWlumpvmpnloHpqH5qF5aB6ah+aheWgempfmpXlpXn"
    "qWnqVn6Vl6Dj2HnkPP4TU8vIaH5kPzofnQfGi+aL5ovmi+aL5ovmi+aL5ovmi+aL5pvmm+KbwpvCm8KbwpvCm8KXwo"
    "fCh8eFUfmh+aH5ofmh+aH5qf9+YgUZAoSBQkChIFiYJEQaIgUZAoSBQkChJ925l/TWhGq6BV0Cpo9W1n/meCX9925l"
    "8TmhEtiBZEC6IF0YJoQbQgWhAtiBZEC6IF0YJoQbQgWhAtiBZEC6IF0YJoQbQgWvAr+BX8Cn4Fv75tyL8mFGJcMC6I"
    "FkQLogXRgmhBtCBaEC2IFkQLogXRgmhBtCBaEC2IFkQLogXRgmhBtCBaEO3bPvxrQjPGBeOCccG4YFwwLhgXjAvGBe"
    "OCccG4YFwwLhgXjCuMK4wrjCuMK4wrjCuMK4wrjCuMK4wrjCuMK4wrjCuMK4wrjCuMK4wrjCuMK4wrjCtEK0QrRCtE"
    "K0QrRCtEK0QrRCtEK0QrRCtEK0QrRCtEK0QrRCtEK0QrRCtEKz6jFcYVxhXGFcYVxhXGFcYVxhXGFZ/jCvUK9Qr1Cv"
    "UK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK9Qr1CvUK"
    "9Qr1CvUK9Qr1GvUa9Rr1GvUa9Rr1GvUa9Rr1GvUa9Rr1GvUa9Rr1GvUa9Rr1GvUa9Rr1GvUa9Rr1mk92jYONg42DjY"
    "ONg42DjYONg42DjYONg42DjYONg42DjYONg6/35//8e2p+7dXnbVJMmskwWSaHycXkZvK8T34+8+8TmkNzaA7NoTk0"
    "h+bQHJqL5qK5aC6ai+aiuWgumovmorlpbpqb5qa5aW6am+amuWlumofmoXloHpqH5qF5aB6ah+aheWlempfmpXlpXp"
    "qX5qV5aV6aD4WHwkPhofBQeCg8FB4KD4UXr+pF80XzRfNF80XzRfNF80XzRfNN803zTfNN803zTfNN803zTfNN80Pz"
    "Q/ND80PzQ/ND80PzQ/ND8/Pe/GuH/z4Jk2LSTIbJMjlMLiY3E5pRL6gX1AvqBfWCekG9oF5QL6gX1AvqBfWCekG9oF"
    "5QL6gX1AvqBfWCekG9oF5QL6gX1AvqBfWCekG9oF5QL6gX1AvqBfWCekG9oF5QL6gX1AvqBfWCekG9oF5QL6j3a8//"
    "PqEZB4ODwcHgYHAwOBgcDA4GB4ODwcHgYHAwOBgcDA4GB4ODwcHgYHAwOBgcDA4GB4ODwcHgYHAwOBgcDA4GB4ODwc"
    "HgYHAwOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4"
    "WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WD"
    "hYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhYOFg4WDhY"
    "OFg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYON"
    "g42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg4"
    "2DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42D"
    "g4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4"
    "ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4OD"
    "g4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4OLg4"
    "uDi4OLg4uDi4OLg4uDi4OLg4uDi4OLg4uDi4OLg4uDi43xzM+fNP7M5/fv7B36NwbShcGwpXgsKVoHABKFwAqq97Q/"
    "8mzbWP5krHvP+v9u91qH2bFJNmMkyWyWFyMbmZPO+T8L3C9wrfK3yvvHyv8LPn/Wc/f1+f8zapv5Pr75+53ibFpJkM"
    "k2VymFxMbibP++TnE/U+oTk0h+bQHJpDc2gOzaG5aC6ai+aiuWgumovmorloLpqb5qa5aW6am+amuWlumpvmpnloHp"
    "qH5qF5aB6ah+aheWgempfmpXlpXpqX5qV5aV6al+al+dB8aD40H5oPzYfmQ/Oh+dB8aL5ovmi+aL5ovmi+aL5ovmi+"
    "aL5ovmm+ab5pvmm+ab5pvmm+ab5pvml+aH5ofmh+aH5ofmh+aH5ofmh+3pt/XTJ7n4RJMWkmw2SZHCYXk5sJzTgYHA"
    "wOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB"
    "4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHA"
    "wOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwc"
    "LBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLB"
    "wsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcLBws"
    "HCwcLBwsHCwcLBwsHCwcLBwsHCwcLBwsHCwcbBxsHGwcbBxsHGwc7FcHww427GDDDjbsYMMONuxgww427GDDDjbsYM"
    "MONuxgww427GDDDjbsYMMONuxgww427GDDDjbsYMMONuxgww427GDDDjbsYMMONuxgww427GDDDjbsYMMONuxgww42"
    "7GDDDjbsYMMONuxgww427GDDDjbsYMMONuxgww427GDDDjbsYMMONuxgww427GDDDjbsYMMONuxgww427GDDDjbsYM"
    "MONuxgww427GDDDjbsYMMONuxgww427GDDDjbsYMMONuxgwxY0bEHDFjRsQcMWNGxBwxY0bEHDFjRsQcMWNGxBwxY0"
    "bEHDFjTsD8P+MOwPw/4w7A/D/jDsD8P+MOwPw/4w7A/D/jDsD8P+MOwPw/4w7A/D/jDsD8P+MOwPw/4w7A/D/jDsD8"
    "P+MOwPw/4w7A/D/jDsD8P+MOwPw/4w7A/D/jDs68K+Luzrwr4u7OvCvi7s68K+Luzrwr4u7OvCvi7s68K+Luzrwr4u"
    "7OvCvi7s68K+Luzrwr4u7OvCvi7s68K+Luzrwr4u7OvC/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8"
    "L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n"
    "7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8"
    "L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n7H/C/ifsf8L+J+x/wv4n"
    "7H/C/ief9z/NTqbZyTQONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42Dj"
    "YONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYO"
    "Ng42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYONg42DjYODg4ODg4ODg"
    "4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODuoN6g3qDeoN6g3qDeoN6g3qDeoN6s2ren//"
    "CZHvk287mWInU2xF6n0rcv/95x3ut0kxaSbDZJkcJheTm8nzPvn5PL9PaA7NoTk0h+bQHJpDc96bm1e1eVWbV7V5Vf"
    "v7q5pf/x7kfJ8Uk36b/P7vFH6f5AeTMCkmfOXM90l4osITFZ6o8ESFJyo8UeGJCk9UeKLCExWeqPBEhScqPFHhiQpP"
    "VHiiwhMVnqj//ScS3yc0F81Fc9FcNBfNRXPRXDQ3zU1z09w0N81Nc9PcNDfNTfPQPDQPzUPz0Dw0D81D89A8NC/NS/"
    "PSvDQvzUvz0rw0L81L86H50HxoPjQfmg/Nh+ZD86H50HzRfNF80XzRfNF80XzRfNF80XzRfNN803zTfNN803zTfNN8"
    "03zTfNP80PzQ/ND80PzQ/ND80PzQ/ND8vDf/Ojt+n4RJMWkmw2SZHCYXk5sJzTgYHAwOBgeDg8HB4GBwMDgYHAwOBg"
    "eDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBw"
    "MDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMDgYHAwOBgeDg8HB4GBwMO8OLp9lDpOLyc3keZ+8f/76+pDPxD"
    "9TTJrJMFkmh8nF5GbyvE/y1rw0HyYXk7dXrP++Gv1t8vpn5u+fmW+TMCkmzWSYLJPD5GJyM3neJ6E5NIfm0ByaQ3No"
    "Ds2hOTQXzUVz0Vw0F8312rx/f6f7NTl/f4Pn26RfJvff3/v9bVJMmskwWSaHycXkZvK8T37/3r9PaM5Lc/7tUn7+wT"
    "+jf38p/PyTr6Ny1K+jf++NfL3Y9fLl/7zLnr/bm+fnuywvk2LSTIbJMjlMLiY3k+d98vOVfJ/QHJpDc2gOzaE5NIfm"
    "0Fw0F81Fc9FcNBfNRXPRXDQXzU1z09w0N81Nc9PcNDfNTXPTPDQPzUPz0Dw0D81D89A8NA/NS/PSvDQvzUvz0rw0L8"
    "1L89J8aD40H5oPzYfmQ/Oh+dB8aD40XzRfNF80XzRfNF80XzRfNF80XzTfNN803zTfNN803zTfNN803zTfND80PzQ/"
    "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"
    "803zQ/ND80PzQ/ND80PzQ/ND80Pz896cHz+YhEkxaSbDZJkcJheTt+b3LUTYQoQtRNhChC1E2EKELUTYQoQtRNhChC"
    "1E2EKELUTYQoQtRNhChC1E2EKELUTYQoQtRNhC/J7QXDQXzUXzu8vv+42w3wj7jbDfCPuNsN8I+42w3wj7jbDfCPuN"
    "sN8I+42w3wj7jbDfCPuNsN8I+42w3wj7jbDfCPuNsN8I+42w3wj7jbDfCPuNsN8I+43fE5qb5qa5aW6am+amuWkemo"
    "fmoXloHpqH5vf/7+t9JxN2MmEnE3YyYScTdjJhJxN2MmEnE3YyYScTdjJhJxN2MmEnE3YyYScTdjJhJxN2MmEn83tC"
    "M++d5b2zvHeWJ3x5wpcnfHnCt/3KvBo84csTvjzhyxO+POHLE7484csTvjzh6xM+NA/NQ/PSvDQvPe+fHd53aGGHFn"
    "ZoYYcWdmhhhxZ2aGGHFnZoYYcWdmhhhxZ2aGGHFnZoYYcWdmhhhxZ2aGGHFnZoYYcWdmhhhxZ2aGGHFnZoYYcWdmhh"
    "hxZ2aGGHFnZoYYcWdmhhhxZ2aGGHFnZoYYcWdmhhhxZ2aGGHFnZoYYcWdmhhhxZ2aGGHFnZoYYcWdmhhhxZ2aGGHVr"
    "zfi/d78X4v3u/F+714vxfv9+L9Xrzfi/d78X4v3u/F+714vxfv9+L9Xrzfi/d78X4v3u/F+714vxfv9+L9Xrzfi/d7"
    "8X4v3u/F+714vxfv9+L9Xrzfi/d78X4v3u/F+714vxfv9+L9Xrzfi/d78X4v3u/F+714vxfv9+L9Xrzfi/d78X4v3u"
    "/F+714vxfv93p/v98vN+7ul0kxaSbDZJkcJheTm8nzPvn6Db5OaA7NoTk057X5eXk1npdJMWkmw2SZHCYXk5vJ8z75"
    "ejVeJzSH5tAcmkNzaA7NoTk0F81Fc9FcNBfNRXPRXDQXzfWv+c9i8Pej8PO1/vNv+/47qw+z/jCbD7P9MDsfZteH2f"
    "1h9jj7OXD24efIh58jH36OfPg58uHnyIefI/4cvxaur7P68DrXh9e5PrzO9eF1rg+vc314nevD61wfXuf68DrXh9e5"
    "PrzO9eF1rg+vc314nevD61wfXufidc6/Zzfvs/o2qw9/rvhz9fc/0ffr3+T9fVYvs/735/ptlg+z+jDrD7P5Prv+fY"
    "/rf7Pn3+z5PqsPs/4wmw+z/TA7zvLh++bD982H75sP3zcfvm8+fN/68H3rw/etD9+3Pnzf/vD1+sPX6w9frz98vfnw"
    "9ebD15sPX2++fb28PFf58X1Yn4b9aTifhvthmE/fKJ++UT59o3z6RvXpa9anr1mfvmZ9+pr96Wv2p6/Zn75mf/qa8+"
    "lrzqevOZ++5rx9zX35xe33YX0a9t/h//0/+jaeCQ=="
)


def _load_catalog() -> Dict[int, Tuple[int, int, int]]:
    raw = zlib.decompress(base64.b64decode(_CATALOG_B64))
    rows = json.loads(raw.decode("utf-8"))
    catalog = {int(r[0]): (int(r[1]), int(r[2]), int(r[3])) for r in rows}
    # Ensure default parachute 209000001 has collection_type = 5 (CollectionType.PARACHUTE)
    if 209000001 in catalog and catalog[209000001][2] == 0:
        catalog[209000001] = (catalog[209000001][0], catalog[209000001][1], 5)
    return catalog


# item_id -> (item_type, item_sub_type, collection_type)
UNLOCKED_ITEM_DEFS: Dict[int, Tuple[int, int, int]] = _load_catalog()
ALL_PERMANENT_ITEM_IDS: Tuple[int, ...] = tuple(sorted(UNLOCKED_ITEM_DEFS.keys()))

# Category ID lists (directly extracted from APK CSVs)
CLOTHES_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.CLOTHES
)
WEAPON_SKIN_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 7
)
BANNER_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 1
)
HEADPIC_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 2
)
LOOTBOX_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 3
)
BACKPACK_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 4
)
PARACHUTE_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 5
)
SKYBOARD_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 6
)
VEHICLE_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 8
)
EMOTE_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, ct) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.COLLECTION and ct == 9
)
CRATE_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, _) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.TREASUREBOX
)
LOADOUT_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, _) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.LOADOUTBOX
)
ROOM_CARD_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, _) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.ROOMCARD
)
BUNDLE_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, _, _) in sorted(UNLOCKED_ITEM_DEFS.items()) if t == ItemType.BUNDLE
)
VOUCHER_IDS: Tuple[int, ...] = tuple(
    iid for iid, (t, st, _) in sorted(UNLOCKED_ITEM_DEFS.items())
    if t == ItemType.DEBRIS and st == ItemSubType.VOUCHER
)


def default_item_count(item_id: int) -> int:
    """Return initial stack count (99 for stackables/consumables, 1 for permanent gear)."""
    meta = UNLOCKED_ITEM_DEFS.get(int(item_id))
    if meta and meta[0] in _STACKABLE_TYPES:
        return 99
    return 1


def unlock_all_inventory_in_state(target_state: Any = None) -> int:
    """
    Register all 4,462 real APK permanent items into core.state.state as unlocked
    with stack counts set appropriately. Returns count of newly unlocked items.
    """
    if target_state is None:
        from core.state import state as target_state

    newly_added = target_state.unlock_items(ALL_PERMANENT_ITEM_IDS)
    with target_state._lock:
        for iid, (itype, _, _) in UNLOCKED_ITEM_DEFS.items():
            if itype in _STACKABLE_TYPES:
                if target_state._item_counts.get(iid, 0) < 99:
                    target_state._item_counts[iid] = 99
            else:
                target_state._item_counts.setdefault(iid, 1)
    return newly_added


# ---------------------------------------------------------------------------
# Proto Encoders (verified tags & IsPacked flags)
# ---------------------------------------------------------------------------

def encode_account_wallet(
    coins: int = 999999,
    gems: int = 999999,
    gop_gems: int = 0,
    total_topup: int = 0,
    last_topup_time: int = 0,
) -> bytes:
    """proto.AccountWallet (tag 2 gems is signed int32)."""
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


def encode_loadout_info(
    loadout_id: int,
    loadout_num: int = 99,
    is_free_play: bool = True,
) -> bytes:
    """proto.LoadoutInfo"""
    buf = bytearray()
    buf += encode_uint32(1, loadout_id)
    buf += encode_uint32(2, loadout_num)
    buf += encode_bool(3, is_free_play)
    return bytes(buf)


def encode_choosed_emote(slot_id: int, emote_id: int) -> bytes:
    """proto.ChoosedEmote"""
    return encode_uint32(1, slot_id) + encode_uint32(2, emote_id)


def encode_choosed_emotes(emotes: Sequence[Tuple[int, int]]) -> bytes:
    """proto.ChoosedEmotes"""
    buf = bytearray()
    for slot_id, emote_id in emotes:
        buf += encode_submessage(1, encode_choosed_emote(slot_id, emote_id))
    return bytes(buf)


def encode_selected_items(
    avatar_id: int = DEFAULT_AVATAR_ID,
    skin_color: int = 0,
    clothes: Sequence[int] = DEFAULT_CLOTHES,
    loadouts: Sequence[Dict[str, Any]] = (),
    banner_id: int = 901000001,
    head_pic: int = 902000001,
    slots: Sequence[int] = DEFAULT_COLLECTION_SLOTS,
    emotes: Sequence[Tuple[int, int]] = DEFAULT_EMOTES,
    shows: Sequence[int] = DEFAULT_WEAPON_SHOWS,
    pve_primary_weapon_skin: int = 907000001,
    ranking_cards: Sequence[int] = (),
) -> bytes:
    """proto.SelectedItems (tags 3, 7, 9, 11 are packed uint32[])."""
    buf = bytearray()
    buf += encode_uint32(1, avatar_id)
    buf += encode_uint32(2, skin_color)
    if clothes:
        buf += encode_packed_uint32(3, clothes)
    for lo in loadouts:
        if isinstance(lo, dict):
            buf += encode_submessage(
                4,
                encode_loadout_info(
                    lo["loadout_id"],
                    lo.get("loadout_num", 99),
                    lo.get("is_free_play", True),
                ),
            )
        else:
            buf += encode_submessage(4, encode_loadout_info(int(lo), 99, True))
    buf += encode_uint32(5, banner_id)
    buf += encode_uint32(6, head_pic)
    if slots:
        buf += encode_packed_uint32(7, slots)
    if emotes:
        buf += encode_submessage(8, encode_choosed_emotes(emotes))
    if shows:
        buf += encode_packed_uint32(9, shows)
    if pve_primary_weapon_skin:
        buf += encode_uint32(10, pve_primary_weapon_skin)
    if ranking_cards:
        buf += encode_packed_uint32(11, ranking_cards)
    return bytes(buf)


def encode_avatar_skill_slot(slot_id: int, skill_id: int) -> bytes:
    """proto.AvatarSkillSlot"""
    return encode_uint32(1, slot_id) + encode_uint32(2, skill_id)


def encode_avatar_profile(
    avatar_id: int = DEFAULT_AVATAR_ID,
    unlocked_level: int = 8,
    skin_color: int = 0,
    clothes: Sequence[int] = DEFAULT_CLOTHES,
    equiped_skills: Sequence[Dict[str, int]] = (),
    is_selected: bool = True,
    pve_primary_weapon: int = 0,
) -> bytes:
    """proto.AvatarProfile (tag 4 clothes is packed uint32[])."""
    buf = bytearray()
    buf += encode_uint32(1, avatar_id)
    buf += encode_uint32(2, unlocked_level)
    buf += encode_uint32(3, skin_color)
    if clothes:
        buf += encode_packed_uint32(4, clothes)
    for sk in equiped_skills:
        buf += encode_submessage(
            5,
            encode_avatar_skill_slot(int(sk.get("slot_id", 1)), int(sk.get("skill_id", 0))),
        )
    buf += encode_bool(6, is_selected)
    if pve_primary_weapon:
        buf += encode_uint32(7, pve_primary_weapon)
    return bytes(buf)


def encode_get_backpack_res(
    wallet: Dict[str, int],
    selected_items: Dict[str, Any],
    item_counts: Dict[int, int],
) -> bytes:
    """proto.CSGetBackpackRes"""
    buf = bytearray()
    wallet_bytes = encode_account_wallet(
        coins=int(wallet.get("coins", 999999)),
        gems=int(wallet.get("gems", 999999)),
    )
    buf += encode_submessage(1, wallet_bytes)
    buf += encode_submessage(
        2,
        encode_selected_items(
            avatar_id=int(selected_items.get("avatar_id", DEFAULT_AVATAR_ID)),
            skin_color=int(selected_items.get("skin_color", 0)),
            clothes=selected_items.get("clothes", DEFAULT_CLOTHES),
            loadouts=selected_items.get("loadouts", DEFAULT_LOADOUTS),
            banner_id=int(selected_items.get("banner_id", 901000001)),
            head_pic=int(selected_items.get("head_pic", 902000001)),
            slots=selected_items.get("slots", DEFAULT_COLLECTION_SLOTS),
            emotes=selected_items.get("emotes", DEFAULT_EMOTES),
            shows=selected_items.get("shows", DEFAULT_WEAPON_SHOWS),
            pve_primary_weapon_skin=int(selected_items.get("pve_primary_weapon_skin", 907000001)),
            ranking_cards=selected_items.get("ranking_cards", ()),
        ),
    )
    for iid in sorted(item_counts.keys()):
        cnt = max(1, int(item_counts[iid]))
        meta = UNLOCKED_ITEM_DEFS.get(int(iid))
        itype = meta[0] if meta else None
        isub = meta[1] if meta else None
        if itype == ItemType.COLLECTION and meta and meta[2]:
            isub = meta[2]
        buf += encode_submessage(
            3,
            encode_item(
                item_id=int(iid),
                cnt=cnt,
                history_owned_cnt=cnt,
                item_status=ItemStatus.PERMANENT,
                item_type=itype,
                item_sub_type=isub,
            ),
        )
    return bytes(buf)


def encode_change_clothes_res(profile_bytes: bytes) -> bytes:
    """proto.CSChangeClothesRes"""
    return encode_submessage(1, profile_bytes)


def encode_get_hide_collections_res(item_ids: Iterable[int] = ()) -> bytes:
    """proto.CSGetHideCollectionsRes (tag 1 is packed uint32[]). Returns b'\x0a\x00' if empty to prevent client NRE."""
    ids = [int(x) for x in item_ids]
    return encode_packed_uint32(1, ids) if ids else b"\x0a\x00"


# ---------------------------------------------------------------------------
# Request Decoders
# ---------------------------------------------------------------------------

def decode_change_clothes_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSChangeClothesReq"""
    if not raw_body:
        return {"avatar_id": 0, "clothes": [], "skin_color": 0}
    fields = decode_proto(raw_body)
    return {
        "avatar_id": get_varint(fields, 1, 0),
        "clothes": get_packed_varints(fields, 2),
        "skin_color": get_varint(fields, 3, 0),
    }


def decode_choose_loadout_req(raw_body: bytes) -> Dict[str, Any]:
    """proto.CSChooseLoadoutReq"""
    if not raw_body:
        return {"loadouts": [], "group_id": 0}
    fields = decode_proto(raw_body)
    return {
        "loadouts": get_packed_varints(fields, 1),
        "group_id": get_varint(fields, 2, 0),
    }


def decode_choose_slots_req(raw_body: bytes) -> List[int]:
    """proto.CSChooseSlotsReq"""
    if not raw_body:
        return []
    return get_packed_varints(decode_proto(raw_body), 1)


def decode_choose_show_req(raw_body: bytes) -> List[int]:
    """proto.CSChooseShowReq"""
    if not raw_body:
        return []
    return get_packed_varints(decode_proto(raw_body), 1)


def decode_choose_emote_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSChooseEmoteReq"""
    if not raw_body:
        return {"slot_id": 1, "emote_id": 0, "group_id": 0}
    fields = decode_proto(raw_body)
    return {
        "slot_id": get_varint(fields, 1, 1),
        "emote_id": get_varint(fields, 2, 0),
        "group_id": get_varint(fields, 3, 0),
    }


def decode_choose_banner_req(raw_body: bytes) -> int:
    """proto.CSChooseBannerReq"""
    return get_varint(decode_proto(raw_body), 1, 0) if raw_body else 0


def decode_choose_head_pic_req(raw_body: bytes) -> int:
    """proto.CSChooseHeadPicReq"""
    return get_varint(decode_proto(raw_body), 1, 0) if raw_body else 0


def decode_choose_ranking_cards_req(raw_body: bytes) -> int:
    """proto.CSChooseRankingCardsReq"""
    return get_varint(decode_proto(raw_body), 1, 0) if raw_body else 0


def decode_choose_pve_primary_weapon_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSChoosePVEPrimaryWeaponReq"""
    if not raw_body:
        return {"primary_weapon_id": 0, "group_id": 0}
    fields = decode_proto(raw_body)
    return {
        "primary_weapon_id": get_varint(fields, 1, 0),
        "group_id": get_varint(fields, 2, 0),
    }


def decode_buy_sticker_req(raw_body: bytes) -> Dict[str, int]:
    """proto.CSBuyStickerReq"""
    if not raw_body:
        return {"currency_type": 2, "item_id": 0}
    fields = decode_proto(raw_body)
    return {
        "currency_type": get_varint(fields, 1, 2),
        "item_id": get_varint(fields, 2, 0),
    }


def decode_hide_collections_req(raw_body: bytes) -> List[int]:
    """Optional CSGetHideCollectionsRes-shaped payload for /SetCollectionHide."""
    if not raw_body:
        return []
    return get_packed_varints(decode_proto(raw_body), 1)
