# Free Fire 1.39 (Barbosa / OB17) In-Match Combat & UDP Network Protocol Specification

Deconstructed and verified against Free Fire 1.39 IL2CPP Metadata v23 (`global-metadata.dat`), `libil2cpp.so` memory dump from runtime process (PID 4252), and `dump/dump.cs`.

---

## 1. Protocol Architecture & Header Layouts

The Free Fire 1.39 combat network layer is implemented in `GCommon.UDPSession` (TypeDef [9784]) and packetized via `GCommon.UDPMsgPacket` (TypeDef [9777]).

### 1.1 Header Constants
- `UDPMESSAGE_MSGKEY = 0x6C` (108 decimal)
- `UDPMESSAGE_HEADER_MINI_SIZE = 5` bytes
- `UDPMESSAGE_HEADER_NONRELIABLE_SIZE = 8` bytes
- `UDPMESSAGE_HEADER_RELIABLE_SIZE = 12` bytes

### 1.2 Send Options (`SendOption`)
| ID | Constant | Reliability | Description |
|:---|:---|:---|:---|
| 0 | `NONE` | Non-Reliable | Unreliable one-off packets (ACK, fast sync) |
| 1 | `HELLO` | Reliable | Handshake connection request / response |
| 2 | `RELIABLE` | Reliable | In-order reliable combat packets (Join, Shoot, Damage, Death, Loot) |
| 3 | `BYEBYE` | Non-Reliable | Disconnect notification |
| 4 | `VAR` | Non-Reliable | Variable uncompressed packet |
| 5 | `VAR_RELIABLE` | Reliable | Variable reliable compressed packet |

*Note on Reliability Rule (from `GCommon.UDPMsgPacket.IsReliable` at `0xc447b5db`)*:
If `Cmd == 2` (`UDP_ACK`), the packet is **always treated as non-reliable** (8-byte header), regardless of SendOption. Otherwise, SendOptions `HELLO (1)`, `RELIABLE (2)`, and `VAR_RELIABLE (5)` use the 12-byte reliable header.

---

### 1.3 Wire Frame Layouts

#### Reliable Packet Header (12 Bytes Total)
```
+--------------+-------------+-----------------+-------------------+
| MsgKey (1B)  |  CRC7 (1B)  | SendOption (1B) |     Cmd (2B)      |
|    [0x6C]    |  [0..127]   |    [1, 2, 5]    |    [uint16_le]    |
+--------------+-------------+-----------------+-------------------+
|  SeqID (2B)  | OrderID (2B)|    Flags (1B)   |    Length (2B)    |
| [uint16_le]  | [uint16_le] | [0x01/0x02/etc] |    [uint16_le]    |
+--------------+-------------+-----------------+-------------------+
| Payload Data (Length Bytes)...                                   |
+------------------------------------------------------------------+
```

#### Non-Reliable Packet Header (8 Bytes Total)
```
+--------------+-------------+-----------------+-------------------+
| MsgKey (1B)  |  CRC7 (1B)  | SendOption (1B) |     Cmd (2B)      |
|    [0x6C]    |  [0..127]   |   [0, 3, 4]     |    [uint16_le]    |
+--------------+-------------+-----------------+-------------------+
|  Flags (1B)  | Length (2B) |
| [uint8]      | [uint16_le] |
+--------------+-------------+-------------------------------------+
| Payload Data (Length Bytes)...                                   |
+------------------------------------------------------------------+
```

#### Mini Header (5 Bytes Total)
```
+--------------+-------------+-----------------+-------------------+
| MsgKey (1B)  |  CRC7 (1B)  | SendOption (1B) |     Cmd (2B)      |
|    [0x6C]    |  [0..127]   |    [uint8]      |    [uint16_le]    |
+--------------+-------------+-----------------+-------------------+
```

---

## 2. Checksum Algorithm: Free Fire CRC-7

Checksum calculation is handled by `GCommon.UDPChecksum` (TypeDef [9765]).

- **Polynomial**: `x^7 + x^3 + 1 = 0x09` (ITU-T CRC-7 variant)
- **Table**: 256 bytes extracted from metadata Field [55626]:
  `[0, 9, 18, 27, 36, 45, 54, 63, 72, 65, 90, 83, 108, 101, 126, 119, ...]`
- **Calculation Step** (from disassembled `0xc4479f0e`):
  ```python
  def calculate_crc7(data: bytes, initial: int = 0) -> int:
      crc = initial & 0x7f
      for b in data:
          idx = ((crc << 1) ^ b) & 0xff
          crc = CRC7_TABLE[idx] & 0x7f
      return crc
  ```
- **Checksum Span**: CRC7 is computed over all bytes starting at offset 2 (`SendOption`) through the end of the packet payload. Offsets 0 (`MsgKey`) and 1 (`CRC7` placeholder) are excluded.

---

## 3. Session Handshake & Lifecycle Sequence

```
Client (Port random)                                Server (Port 39800 / 10001)
  |                                                          |
  | -------- 1. HELLO (SendOption=1, Cmd=1, Seq=1) --------->|
  |                                                          | [Assigns session_key]
  |<-------- 2. S2C_Hello_Res (SessionKey, Order=1) ---------|
  |                                                          |
  | -------- 3. RUDP_JOIN_MATCH (Cmd=100, prepare_token) ---->|
  |                                                          | [Validates token & assigns slot]
  |<-------- 4. UDP_ACK (Ack=ClientSeq, AckBits=mask) -------|
  |<-------- 5. RUDP_JOIN_MATCH_FINISHED (Cmd=130) ----------|
  |<-------- 6. RUDP_SYNC_SCENE_INFO (Cmd=116, 60s timer) ---| [Spawn Island 60s countdown]
  |                                                          |
  |<-------> 7. Periodic PING / PONG (Cmd=3, tick uint64) <->|
  |<-------> 8. High-frequency state sync (Cmd=1000..1018) ->| [Airplane flight, skydive, combat]
  |                                                          |
  | -------- 9. BYEBYE (SendOption=3, Cmd=4) --------------->|
```

### 3.1 Reserved System Messages (`UDPMessageIDReserved`)
1. `UDP_HELLO = 1`: Handshake initialization.
   - S2C payload: `<IHH` (SessionKey uint32 4B, OrderID uint16 2B, RequiredID uint16 2B = 8 bytes).
2. `UDP_ACK = 2`: Reliable packet acknowledgement.
   - Payload: `<HI` (AckSequence uint16 2B, AckHistoryBits uint32 4B = 6 bytes).
3. `UDP_PING = 3`: Latency tracking probe.
   - Payload: `<Q` (SendTickCount uint64 8B).
4. `UDP_BYEBYE = 4`: Clean session termination.
5. `UDP_LONGTIMENOSEE = 5`: Keepalive heartbeat probe for dormant sessions.
   - Payload: `<I` (SessionKey uint32 4B).

---

## 4. Complete Combat Packet Opcode Map (`message.hTKYY`)

All 265 authentic combat opcodes from TypeDef [4464]:

### Core Match Lifecycle
- `100: RUDP_JOIN_MATCH`
- `101: RUDP_PLAYER_JOIN`
- `102: RUDP_PLAYER_QUIT`
- `103: RUDP_MATCH_END`
- `110: RUDP_BATTLE_START`
- `116: RUDP_SYNC_SCENE_INFO`
- `117: RUDP_SAFE_ZONE_CHANGE`
- `130: RUDP_JOIN_MATCH_FINISHED`
- `143: RUDP_FORCE_SYNC_PLAYER_STATE`
- `144: RUDP_TELEPORT_PLAYER`
- `145: RUDP_CONFIRM_SERVERFORCE_SYNC_PLAYER_STATE`
- `274: RUDP_SHOW_MATCH_RESULT`

### Weaponry, Ballistics & Combat
- `104: RUDP_START_FIRE`
- `105: RUDP_STOP_FIRE`
- `106: RUDP_TAKE_DAMAGE`
- `107: RUDP_DEAD`
- `108: RUDP_CHANGE_INVENTORY_ON_HAND`
- `133: RUDP_START_RELOAD`
- `134: RUDP_STOP_RELOAD`
- `137: RUDP_START_SNIPER`
- `138: RUDP_STOP_SNIPER`
- `139: RUDP_KNOCK_DOWN`
- `140: RUDP_KNOCK_REVIVE`
- `141: RUDP_START_RESCURE`
- `142: RUDP_STOP_RESCURE`
- `153: RUDP_HITPROTECTION`
- `154: RUDP_PROJECTILE_STATE_SYNC`
- `155: RUDP_PROJECTILE_THROW`
- `156: RUDP_PROJECTILE_EXPLODE`
- `157: RUDP_START_GRENADE`
- `158: RUDP_STOP_GRENADE`
- `163: RUDP_SHOW_DAMAGE`
- `164: RUDP_UPDATE_BUFFBEHAVIOR`
- `207: RUDP_WEAPON_AMMO_IN_CLIP_SYNC`
- `212: RUDP_ADD_ICEWALL`
- `213: RUDP_ICEWALL_TAKE_DAMAGE`
- `214: RUDP_RESYNC_ICEWALL`

### Inventory & Ground Loot
- `111: RUDP_PICKUP_INVENTORY`
- `112: RUDP_DROP_INVENTORY`
- `113: RUDP_USE_INVENTORY`
- `114: RUDP_ADD_PICKUP`
- `115: RUDP_DEL_PICKUP`
- `119: RUDP_EQUIP`
- `120: RUDP_UNEQUIP`
- `121: RUDP_EQUIPMENT_CHANGED`
- `122: RUDP_EQUIP_ATTACHMENT`
- `123: RUDP_UNEQUIP_ATTACHMENT`
- `124: RUDP_ATTACHMENT_CHANGED`
- `131: RUDP_TRYUSE_INVENTORY`
- `132: RUDP_CANCELUSE_INVENTORY`
- `168: RUDP_SYNC_INVENTORY_INFO`
- `208: RUDP_PICKUP_INVENTORY_CHECK_TIME`

### Vehicles & World Platform
- `125: RUDP_GETON_VEHICLE`
- `126: RUDP_GETOFF_VEHICLE`
- `127: RUDP_VEHICLE_TAKE_DAMAGE`
- `128: RUDP_VEHICLE_DEAD`
- `129: RUDP_FORCE_SYNC_VEHICLE_STATE`
- `146: RUDP_INIT_VEHICLE_STATE`
- `165: RUDP_VEHICLE_EXPLODE`
- `171: RUDP_VEHICLE_CHANGE_SHAPE`
- `180: RUDP_VEHICLE_CHANGE_AUTH`
- `181: RUDP_VEHICLE_CHANGE_SEAT`
- `188: RUDP_VEHICLE_CHANGE_ParachuteState`

### Airdrop, UAV & Environment
- `150: RUDP_AIRDROP_START`
- `151: RUDP_AIRDRAGON_START`
- `152: RUDP_BOMB`
- `160: RUDP_UAV_REVEAL_PLAYERS`
- `161: RUDP_UAV_TAKE_DAMAGE`
- `162: RUDP_UAV_DEAD`
- `166: RUDP_AIRDROP_INWATER`
- `190: RUDP_AIRDROP_REENTER`

### Parachute & Catapult
- `224: RUDP_GETIN_CATAPULT`
- `225: RUDP_GETOUT_CATAPULT`
- `226: RUDP_START_CATAPULT_FALLING`
- `229: RUDP_TeamParachuteInfo`
- `230: RUDP_C2S_TransferParachuteLeader`
- `231: RUDP_C2S_ParachuteBecomeFree`
- `232: RUDP_S2C_TransferParachuteLeaderFail`
- `233: RUDP_CATAPULTS_SYNC`

### High-Frequency Unreliable Sync (1000..1018)
- `1000: UDP_SYNC_SERVER_TIME`
- `1001: UDP_PLAYER_STATE_SYNC`
- `1002: UDP_VEHICLE_STATE_SYNC`
- `1003: UDP_AIRDROP_STATE_SYNC`
- `1004: UDP_SYNC_AI_MOVE`
- `1005: UDP_UAV_STATE_SYNC`
- `1006: UDP_PASSENGER_STATE_SYNC`
- `1007: UDP_LevelMovePlatform_STATE_SYNC`
- `1008: UDP_VEHICLE_MACHINEGUN_SYNC`
- `1009: UDP_AI_STATE_SYNC`
- `1010: UDP_PLAYER_HURT`
- `1011: UDP_PET_STATE_SYNC`
- `1012: UDP_PLAYER_STATE_SYNC_V2`
- `1013: UDP_PLAYER_HEAL`
- `1014: UDP_PLAYER_POSITION_ONLY`
- `1015: UDP_SYNC_CATAPULT`
- `1016: UDP_SYNC_AIM_ROTATION`
- `1017: UDP_SYNC_ASSISTANT_INFO`
- `1018: UDP_SYNC_PROTECTED_HELMET_EVENT`
