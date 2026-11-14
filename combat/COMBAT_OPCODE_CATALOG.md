# Free Fire 1.39 Complete Combat Opcode Catalog (message.hTKYY D, TypeDef [4464])

Total Opcodes / Fields: 266 (1 alue__ enum base + 265 combat opcodes).
Extracted directly from Barbosa IL2CPP Metadata v23 (global-metadata.dat).

## 1. Disambiguation: Wire Enum Value vs Relative Metadata Index
Previous crashes occurred due to confusion between the **1-based index** in CombatOpcode and the authentic **wire enum value** compiled into IL2CPP switch handlers:
- **Opcode 31**: RUDP_JOIN_MATCH_FINISHED (Relative Index 31, Wire Value 130)
- **Opcode 2**: RUDP_PLAYER_JOIN (Relative Index 2, Wire Value 101)
- **Opcode 17**: RUDP_SYNC_SCENE_INFO (Relative Index 17, Wire Value 116)
- **Opcode 11**: RUDP_BATTLE_START (Relative Index 11, Wire Value 110)
- **Opcode 443**: RUDP_TeamParachuteInfo (Relative Index 230, Wire Value 443)
- **Opcode 4**: RUDP_MATCH_END (Relative Index 4, Wire Value 103)
- **Opcode 107**: RUDP_DEAD (Relative Index 8, Wire Value 107) vs RUDP_SPECTATOR_REJOIN_DEADPLAYERINFO (Relative Index 107, Wire Value 206)

## 2. Complete 266 Field & Opcode Roster

| Index | Field ID | Wire Value | Opcode Name | Category |
|:---:|:---:|:---:|:---|:---|
| 0 | 23036 | None | value__ | Enum Definition |
| 1 | 23037 | 100 | RUDP_JOIN_MATCH | Lifecycle & Session |
| 2 | 23038 | 101 | RUDP_PLAYER_JOIN | General Combat |
| 3 | 23039 | 102 | RUDP_PLAYER_QUIT | General Combat |
| 4 | 23040 | 103 | RUDP_MATCH_END | Lifecycle & Session |
| 5 | 23041 | 104 | RUDP_START_FIRE | Weaponry & Combat |
| 6 | 23042 | 105 | RUDP_STOP_FIRE | Weaponry & Combat |
| 7 | 23043 | 106 | RUDP_TAKE_DAMAGE | Weaponry & Combat |
| 8 | 23044 | 107 | RUDP_DEAD | Weaponry & Combat |
| 9 | 23045 | 108 | RUDP_CHANGE_INVENTORY_ON_HAND | Inventory & Items |
| 10 | 23046 | 109 | RUDP_OPEN_DOOR | General Combat |
| 11 | 23047 | 110 | RUDP_BATTLE_START | Lifecycle & Session |
| 12 | 23048 | 111 | RUDP_PICKUP_INVENTORY | Inventory & Items |
| 13 | 23049 | 112 | RUDP_DROP_INVENTORY | Inventory & Items |
| 14 | 23050 | 113 | RUDP_USE_INVENTORY | Inventory & Items |
| 15 | 23051 | 114 | RUDP_ADD_PICKUP | Inventory & Items |
| 16 | 23052 | 115 | RUDP_DEL_PICKUP | Inventory & Items |
| 17 | 23053 | 116 | RUDP_SYNC_SCENE_INFO | Lifecycle & Session |
| 18 | 23054 | 117 | RUDP_SAFE_ZONE_CHANGE | World & Zones |
| 19 | 23055 | 118 | RUDP_BIND_PRI | General Combat |
| 20 | 23056 | 119 | RUDP_EQUIP | Inventory & Items |
| 21 | 23057 | 120 | RUDP_UNEQUIP | Inventory & Items |
| 22 | 23058 | 121 | RUDP_EQUIPMENT_CHANGED | Inventory & Items |
| 23 | 23059 | 122 | RUDP_EQUIP_ATTACHMENT | Inventory & Items |
| 24 | 23060 | 123 | RUDP_UNEQUIP_ATTACHMENT | Inventory & Items |
| 25 | 23061 | 124 | RUDP_ATTACHMENT_CHANGED | Inventory & Items |
| 26 | 23062 | 125 | RUDP_GETON_VEHICLE | Vehicles |
| 27 | 23063 | 126 | RUDP_GETOFF_VEHICLE | Vehicles |
| 28 | 23064 | 127 | RUDP_VEHICLE_TAKE_DAMAGE | Weaponry & Combat |
| 29 | 23065 | 128 | RUDP_VEHICLE_DEAD | Weaponry & Combat |
| 30 | 23066 | 129 | RUDP_FORCE_SYNC_VEHICLE_STATE | Vehicles |
| 31 | 23067 | 130 | RUDP_JOIN_MATCH_FINISHED | Lifecycle & Session |
| 32 | 23068 | 131 | RUDP_TRYUSE_INVENTORY | Inventory & Items |
| 33 | 23069 | 132 | RUDP_CANCELUSE_INVENTORY | Inventory & Items |
| 34 | 23070 | 133 | RUDP_START_RELOAD | Weaponry & Combat |
| 35 | 23071 | 134 | RUDP_STOP_RELOAD | Weaponry & Combat |
| 36 | 23072 | 135 | RUDP_SYNC_PLAYERS_VISIBILITY | General Combat |
| 37 | 23073 | 136 | RUDP_SYNC_VEHICLES_VISIBILITY | Vehicles |
| 38 | 23074 | 137 | RUDP_START_SNIPER | Weaponry & Combat |
| 39 | 23075 | 138 | RUDP_STOP_SNIPER | Weaponry & Combat |
| 40 | 23076 | 139 | RUDP_KNOCK_DOWN | General Combat |
| 41 | 23077 | 140 | RUDP_KNOCK_REVIVE | General Combat |
| 42 | 23078 | 141 | RUDP_START_RESCURE | General Combat |
| 43 | 23079 | 142 | RUDP_STOP_RESCURE | General Combat |
| 44 | 23080 | 143 | RUDP_FORCE_SYNC_PLAYER_STATE | General Combat |
| 45 | 23081 | 144 | RUDP_TELEPORT_PLAYER | General Combat |
| 46 | 23082 | 145 | RUDP_CONFIRM_SERVERFORCE_SYNC_PLAYER_STATE | General Combat |
| 47 | 23083 | 146 | RUDP_INIT_VEHICLE_STATE | Vehicles |
| 48 | 23084 | 147 | RUDP_MAPMARK_CHANGED | General Combat |
| 49 | 23085 | 148 | RUDP_SWITCH_OBSERVE | General Combat |
| 50 | 23086 | 149 | RUDP_NOTIFY_AI_INFO | General Combat |
| 51 | 23087 | 150 | RUDP_AIRDROP_START | World & Zones |
| 52 | 23088 | 151 | RUDP_AIRDRAGON_START | General Combat |
| 53 | 23089 | 152 | RUDP_BOMB | World & Zones |
| 54 | 23090 | 153 | RUDP_HITPROTECTION | General Combat |
| 55 | 23091 | 154 | RUDP_PROJECTILE_STATE_SYNC | Weaponry & Combat |
| 56 | 23092 | 155 | RUDP_PROJECTILE_THROW | Weaponry & Combat |
| 57 | 23093 | 156 | RUDP_PROJECTILE_EXPLODE | Weaponry & Combat |
| 58 | 23094 | 157 | RUDP_START_GRENADE | Weaponry & Combat |
| 59 | 23095 | 158 | RUDP_STOP_GRENADE | Weaponry & Combat |
| 60 | 23096 | 159 | RUDP_CUSTOM_ANIMATION | General Combat |
| 61 | 23097 | 160 | RUDP_UAV_REVEAL_PLAYERS | World & Zones |
| 62 | 23098 | 161 | RUDP_UAV_TAKE_DAMAGE | Weaponry & Combat |
| 63 | 23099 | 162 | RUDP_UAV_DEAD | Weaponry & Combat |
| 64 | 23100 | 163 | RUDP_SHOW_DAMAGE | Weaponry & Combat |
| 65 | 23101 | 164 | RUDP_UPDATE_BUFFBEHAVIOR | General Combat |
| 66 | 23102 | 165 | RUDP_VEHICLE_EXPLODE | Vehicles |
| 67 | 23103 | 166 | RUDP_AIRDROP_INWATER | World & Zones |
| 68 | 23104 | 167 | RUDP_SWITCH_ATTACHMENT | Inventory & Items |
| 69 | 23105 | 168 | RUDP_SYNC_INVENTORY_INFO | Inventory & Items |
| 70 | 23106 | 169 | RUDP_SYNC_OTHER_ATTACHMENT_INFO | Inventory & Items |
| 71 | 23107 | 170 | RUDP_SYNC_REGION_ACTIVITIES | General Combat |
| 72 | 23108 | 171 | RUDP_VEHICLE_CHANGE_SHAPE | Vehicles |
| 73 | 23109 | 172 | RUDP_VEHICLE_INIT_INVENTORY | Inventory & Items |
| 74 | 23110 | 173 | RUDP_VEHICLE_SYNC_INVENTORY | Inventory & Items |
| 75 | 23111 | 174 | RUDP_VEHICLE_PICKUP_INVENTORY | Inventory & Items |
| 76 | 23112 | 175 | RUDP_VEHICLE_DROP_INVENTORY | Inventory & Items |
| 77 | 23113 | 176 | RUDP_VEHICLE_EQUIPMENT_CHANGED | Inventory & Items |
| 78 | 23114 | 177 | RUDP_VEHICLE_USE_INVENTORY | Inventory & Items |
| 79 | 23115 | 178 | RUDP_VEHICLE_TRYUSE_INVENTORY | Inventory & Items |
| 80 | 23116 | 179 | RUDP_VEHICLE_CANCELUSE_INVENTORY | Inventory & Items |
| 81 | 23117 | 180 | RUDP_VEHICLE_CHANGE_AUTH | Vehicles |
| 82 | 23118 | 181 | RUDP_VEHICLE_CHANGE_SEAT | Vehicles |
| 83 | 23119 | 182 | RUDP_SPECTATOR_JOIN | General Combat |
| 84 | 23120 | 183 | RUDP_VEHICLE_ASK_CHANGE_SEAT | Vehicles |
| 85 | 23121 | 184 | RUDP_VEHICLE_CONFIRM_CHANGE_SEAT | Vehicles |
| 86 | 23122 | 185 | RUDP_PLAYER_QUIT_REQ | General Combat |
| 87 | 23123 | 186 | RUDP_PLAYER_QUIT_RES | General Combat |
| 88 | 23124 | 187 | RUDP_START_CLIMB | General Combat |
| 89 | 23125 | 188 | RUDP_VEHICLE_CHANGE_ParachuteState | Vehicles |
| 90 | 23126 | 189 | RUDP_TEAM_INFO | General Combat |
| 91 | 23127 | 190 | RUDP_AIRDROP_REENTER | World & Zones |
| 92 | 23128 | 191 | RUDP_SPECTATOR_PLAYERTAKEDAMAGE | Weaponry & Combat |
| 93 | 23129 | 192 | RUDP_GETON_STROP | General Combat |
| 94 | 23130 | 193 | RUDP_GETOFF_STROP | General Combat |
| 95 | 23131 | 194 | RUDP_DOOR_TAKE_DAMAGE | Weaponry & Combat |
| 96 | 23132 | 195 | RUDP_PLAYER_DO_ACTION | General Combat |
| 97 | 23133 | 196 | RUDP_OILDRUMS_TAKE_DAMAGE | Weaponry & Combat |
| 98 | 23134 | 197 | RUDP_OILDRUMS_USE | General Combat |
| 99 | 23135 | 198 | RUDP_OILDRUMS_BROKEN | General Combat |
| 100 | 23136 | 199 | RUDP_VEHICLE_PICKUP_SOUND | Inventory & Items |
| 101 | 23137 | 200 | RUDP_LOADOUT_CAMPFIRE_SYNCSTATE | Weaponry & Combat |
| 102 | 23138 | 201 | RUDP_LOADOUT_CAMPFIRE_REENTERSYNC | Weaponry & Combat |
| 103 | 23139 | 202 | RUDP_LOADOUT_TREASURE_SYNCSTATE | Clash Squad (CS) |
| 104 | 23140 | 203 | RUDP_LOADOUT_TREASURE_REENTERSYNC | General Combat |
| 105 | 23141 | 204 | RUDP_DIGOUTTREASURE_REQ | General Combat |
| 106 | 23142 | 205 | RUDP_Dynamic_ADD_VEHICLE | Vehicles |
| 107 | 23143 | 206 | RUDP_SPECTATOR_REJOIN_DEADPLAYERINFO | Weaponry & Combat |
| 108 | 23144 | 207 | RUDP_WEAPON_AMMO_IN_CLIP_SYNC | General Combat |
| 109 | 23145 | 208 | RUDP_PICKUP_INVENTORY_CHECK_TIME | Inventory & Items |
| 110 | 23146 | 209 | RUDP_MISSILE_FIRE | Weaponry & Combat |
| 111 | 23147 | 210 | RUDP_MISSILE_STATE_SYNC | General Combat |
| 112 | 23148 | 211 | RUDP_MISSILE_EXPLODE | General Combat |
| 113 | 23149 | 212 | RUDP_ADD_ICEWALL | General Combat |
| 114 | 23150 | 213 | RUDP_ICEWALL_TAKE_DAMAGE | Weaponry & Combat |
| 115 | 23151 | 214 | RUDP_RESYNC_ICEWALL | General Combat |
| 116 | 23152 | 215 | RUDP_REMOVE_ICEWALL | General Combat |
| 117 | 23153 | 216 | RUDP_LOADOUT_SYNCRUNTIMEVALUE | General Combat |
| 118 | 23154 | 217 | RUDP_SPECTATOR_ITEM_COUNT_SYNC | General Combat |
| 119 | 23155 | 218 | RUDP_SPECTATOR_JOIN_ITEM_COUNT_SYNC | General Combat |
| 120 | 23156 | 219 | RUDP_ADD_PICKUPLIST | Inventory & Items |
| 121 | 23157 | 220 | RUDP_UPDATE_PICKUPLIST | Inventory & Items |
| 122 | 23158 | 221 | RUDP_ADD_CONTAINER | General Combat |
| 123 | 23159 | 222 | RUDP_DEL_CONTAINER | General Combat |
| 124 | 23160 | 223 | RUDP_VEHICLE_MACHINEGUN_AMMO | Vehicles |
| 125 | 23161 | 224 | RUDP_OBSERVER_JOIN | General Combat |
| 126 | 23162 | 225 | RUDP_SWITCH_CERTAIN_OBSERVE | General Combat |
| 127 | 23163 | 226 | RUDP_TEAM_RANK_SCORE | General Combat |
| 128 | 23164 | 227 | RUDP_LANDMINE_ADD | General Combat |
| 129 | 23165 | 228 | RUDP_LANDMINE_DEL | General Combat |
| 130 | 23166 | 229 | RUDP_LANDMINE_RESYNC | General Combat |
| 131 | 23167 | 230 | RUDP_LANDMINE_TAKE_DAMAGE | Weaponry & Combat |
| 132 | 23168 | 231 | RUDP_USE_BOUNTY_SCANNER | General Combat |
| 133 | 23169 | 232 | RUDP_SYNC_AI_SKILL | General Combat |
| 134 | 23170 | 233 | RUDP_SYNC_AI_DEATHEXPLOSION | General Combat |
| 135 | 23171 | 234 | RUDP_PET_CREATE_BATCH | Pet System |
| 136 | 23172 | 235 | RUDP_PET_DELETE | Pet System |
| 137 | 23173 | 236 | RUDP_PET_ACTION | Pet System |
| 138 | 23174 | 237 | RUDP_PET_ACTION_RES | Pet System |
| 139 | 23175 | 238 | RUDP_USE_ACTIVE_SKILL | General Combat |
| 140 | 23176 | 239 | RUDP_STOP_ACTIVE_SKILL | General Combat |
| 141 | 23177 | 240 | RUDP_SYNC_ACTIVE_SKILL_STATE | General Combat |
| 142 | 23178 | 241 | RUDP_SPAWN_DAMAGE_ZONE | Weaponry & Combat |
| 143 | 23179 | 242 | RUDP_ZOMBIE_BOMB_SPAWN | World & Zones |
| 144 | 23180 | 243 | RUDP_ZOMBIE_BOMB_EXPLODE | World & Zones |
| 145 | 23181 | 244 | RUDP_SYNC_MARKED_ENERMIES | General Combat |
| 146 | 23182 | 245 | RUDP_NOTIFY_BE_HINTTED | General Combat |
| 147 | 23183 | 246 | RUDP_PLAYER_Notify_Enter_PENDING_REVIVE | General Combat |
| 148 | 23184 | 247 | RUDP_SYNC_GOD | General Combat |
| 149 | 23185 | 248 | RUDP_FULL_AMMO | General Combat |
| 150 | 23186 | 249 | RUDP_SYNC_CHAIRS | General Combat |
| 151 | 23187 | 250 | RUDP_GETON_CHAIR | General Combat |
| 152 | 23188 | 251 | RUDP_GETOFF_CHAIR | General Combat |
| 153 | 23189 | 252 | RUDP_FLASHBOMB_TIME | World & Zones |
| 154 | 23190 | 253 | RUDP_PVE_TAKE_DAMAGE | Weaponry & Combat |
| 155 | 23191 | 254 | RUDP_ZombieSurprised | General Combat |
| 156 | 23192 | 255 | RUDP_INFOBOX | General Combat |
| 157 | 23193 | 256 | RUDP_NOTIFY_EXTRALIFE_OBSOLETED | General Combat |
| 158 | 23194 | 257 | RUDP_INFOBOX_SPECTATOR | General Combat |
| 159 | 23195 | 258 | RUDP_AIM_TARGET_CHANGE | General Combat |
| 160 | 23196 | 259 | RUDP_BATTLEFLAG_SYNCSTATE | Lifecycle & Session |
| 161 | 23197 | 260 | RUDP_BATTLEFLAG_USE | Lifecycle & Session |
| 162 | 23198 | 261 | RUDP_BATTLEFLAG_REENTER | Lifecycle & Session |
| 163 | 23199 | 262 | RUDP_SPAWN_OBJECT | General Combat |
| 164 | 23200 | 263 | RUDP_DESTROY_OBJECT | General Combat |
| 165 | 23201 | 264 | RUDP_MANUAL_CHALLENGE | General Combat |
| 166 | 23202 | 265 | RUDP_MINISENTRY_FIRE | Weaponry & Combat |
| 167 | 23203 | 266 | RUDP_GRAPPLINGHOOK_SPAWN | General Combat |
| 168 | 23204 | 267 | RUDP_GRAPPLINGHOOK_HOOKED | General Combat |
| 169 | 23205 | 268 | RUDP_GRAPPLINGHOOK_DESTROY | General Combat |
| 170 | 23206 | 269 | RUDP_SP_ROOMGAMEACHIEVEMENT | Lifecycle & Session |
| 171 | 23207 | 270 | RUDP_GETON_STROP_BATCH | General Combat |
| 172 | 23208 | 271 | RUDP_GRAPPLINGHOOK_REENTER_SYNC | General Combat |
| 173 | 23209 | 272 | RUDP_PAUSE_GAME | General Combat |
| 174 | 23210 | 273 | RUDP_PAINTSPRAYER_USE | General Combat |
| 175 | 23211 | 274 | RUDP_PAINTSPRAYER_SYNC_STATE | General Combat |
| 176 | 23212 | 275 | RUDP_PAINTSPRAYER_REENTER | General Combat |
| 177 | 23213 | 276 | RUDP_PAINTSPRAYER_REMOVE | General Combat |
| 178 | 23214 | 277 | RUDP_SpawnLevelEmote | General Combat |
| 179 | 23215 | 278 | RUDP_SyncShowCase | General Combat |
| 180 | 23216 | 279 | RUDP_TriggerLevelEmote | General Combat |
| 181 | 23217 | 280 | RUDP_SPECTATOR_TEAMSCORE | General Combat |
| 182 | 23218 | 281 | RUDP_SPECTATOR_PLAYER_RANK | General Combat |
| 183 | 23219 | 282 | RUDP_PLAY_EPIC_CLOTHES_EFFECT | General Combat |
| 184 | 23220 | 283 | RUDP_SPECTATOR_INIT_TEAMSCORE | General Combat |
| 185 | 23221 | 284 | RUDP_LANDMINE_WARNING | General Combat |
| 186 | 23222 | 285 | RUDP_CLIENT_CLOTHES | General Combat |
| 187 | 23223 | 400 | RUDP_DEBUG_ADD_PICKUP | Inventory & Items |
| 188 | 23224 | 401 | RUDP_DEBUG_TURN_ZONE_DAMAGE_ONOFF | Weaponry & Combat |
| 189 | 23225 | 402 | RUDP_DEBUG_ADD_AIRDROP | World & Zones |
| 190 | 23226 | 403 | RUDP_DEBUG_TOGGLE_GOD | Debug / Dev |
| 191 | 23227 | 404 | RUDP_DEBUG_SPEED_HACK | Debug / Dev |
| 192 | 23228 | 405 | RUDP_DEBUG_ADD_BOT | Debug / Dev |
| 193 | 23229 | 406 | RUDP_DEBUG_ADD_AI | Debug / Dev |
| 194 | 23230 | 407 | RUDP_DEBUG_ADD_PROJECTILE | Weaponry & Combat |
| 195 | 23231 | 408 | RUDP_DEBUG_ADD_EP | Debug / Dev |
| 196 | 23232 | 409 | RUDP_DEBUG_AIMOVE | Debug / Dev |
| 197 | 23233 | 410 | RUDP_DEBUG_REMOVE_ZONE | Debug / Dev |
| 198 | 23234 | 411 | RUDP_DEBUG_ADD_VEHICLE | Vehicles |
| 199 | 23235 | 412 | RUDP_DEBUG_ADD_VEHICLE_ITEM | Vehicles |
| 200 | 23236 | 413 | RUDP_DEBUG_INFINITE_AMMO | Debug / Dev |
| 201 | 23237 | 414 | RUDP_PLAYER_GOALS | General Combat |
| 202 | 23238 | 415 | RUDP_OBSERVER_LIKE | General Combat |
| 203 | 23239 | 416 | RUDP_DEBUG_ADD_ICEWALL | Debug / Dev |
| 204 | 23240 | 417 | RUDP_AI_Create_Batch | General Combat |
| 205 | 23241 | 418 | RUDP_AI_Culling_Batch | General Combat |
| 206 | 23242 | 419 | RUDP_AI_DEAD | Weaponry & Combat |
| 207 | 23243 | 420 | RUDP_EMOTION_ANIMATION | General Combat |
| 208 | 23244 | 421 | RUDP_TAKE_HEALING | General Combat |
| 209 | 23245 | 422 | RUDP_ADD_REDENVELOPE | General Combat |
| 210 | 23246 | 423 | RUDP_SYNC_REDENVELOPE | General Combat |
| 211 | 23247 | 424 | RUDP_RECEIVE_REDENVELOPE | General Combat |
| 212 | 23248 | 425 | RUDP_DEBUG_FORCE_TAKE_DAMAGE | Weaponry & Combat |
| 213 | 23249 | 426 | RUDP_SYNC_MovePlatform_VISIBILITY | General Combat |
| 214 | 23250 | 427 | RUDP_DEBUG_ADD_PET | Debug / Dev |
| 215 | 23251 | 428 | RUDP_PLAYER_INROOM | Lifecycle & Session |
| 216 | 23252 | 429 | RUDP_PLAYER_UPDATE_JKPBUFF | General Combat |
| 217 | 23253 | 430 | RUDP_DEBUG_TOGGLE_IGNORE_BY_AI | Debug / Dev |
| 218 | 23254 | 431 | RUDP_PVE_ROUND_NOTIFY | PVE Mode |
| 219 | 23255 | 432 | RUDP_PVE_PLAYER_DAMAGE | Weaponry & Combat |
| 220 | 23256 | 433 | RUDP_REQUESTREVIVE | General Combat |
| 221 | 23257 | 434 | RUDP_REQUESTREVIVEWITHLOCATION | General Combat |
| 222 | 23258 | 435 | RUDP_NOTIFYREVIVE | General Combat |
| 223 | 23259 | 436 | RUDP_DEBUG_CHANGE_CLOTH | Debug / Dev |
| 224 | 23260 | 437 | RUDP_LEVELOBJECT_TAKE_DAMAGE | Weaponry & Combat |
| 225 | 23261 | 438 | RUDP_GETIN_CATAPULT | Drop & Movement |
| 226 | 23262 | 439 | RUDP_GETOUT_CATAPULT | Drop & Movement |
| 227 | 23263 | 440 | RUDP_START_CATAPULT_FALLING | Drop & Movement |
| 228 | 23264 | 441 | RUDP_NotifyPlayCutscene | General Combat |
| 229 | 23265 | 442 | RUDP_SPECTATOR_COMBAT_LEVEL | General Combat |
| 230 | 23266 | 443 | RUDP_TeamParachuteInfo | Drop & Movement |
| 231 | 23267 | 444 | RUDP_C2S_TransferParachuteLeader | Drop & Movement |
| 232 | 23268 | 445 | RUDP_C2S_ParachuteBecomeFree | Drop & Movement |
| 233 | 23269 | 446 | RUDP_S2C_TransferParachuteLeaderFail | Drop & Movement |
| 234 | 23270 | 447 | RUDP_CATAPULTS_SYNC | Drop & Movement |
| 235 | 23271 | 448 | RUDP_SYNC_HOTZONE_INFO | World & Zones |
| 236 | 23272 | 449 | RUDP_DISMISS_HOTZONES | World & Zones |
| 237 | 23273 | 450 | RUDP_DEBUG_ADD_HYPE | Debug / Dev |
| 238 | 23274 | 451 | RUDP_SHOW_MATCH_RESULT | Lifecycle & Session |
| 239 | 23275 | 452 | RUDP_PET_FINDMUSHROOM_MARK | Lifecycle & Session |
| 240 | 23276 | 453 | RUDP_PET_FINDMUSHROOM_REMOVE | Lifecycle & Session |
| 241 | 23277 | 454 | RUDP_SYNC_CSGAMEZONE_INFO | Clash Squad (CS) |
| 242 | 23278 | 455 | RUDP_SYNC_CSSHOPITEMS_LIST | Clash Squad (CS) |
| 243 | 23279 | 456 | RUDP_PURCHASE_CSITEMS | Clash Squad (CS) |
| 244 | 23280 | 457 | RUDP_CS_CURROUND_RESULT | Clash Squad (CS) |
| 245 | 23281 | 500 | RUDP_VAR_SYNC_PRI_DATA | General Combat |
| 246 | 23282 | 501 | RUDP_VAR_SYNC_GRI_DATA | General Combat |
| 247 | 23283 | 1000 | UDP_SYNC_SERVER_TIME | High-Freq Unreliable (1000+) |
| 248 | 23284 | 1001 | UDP_PLAYER_STATE_SYNC | High-Freq Unreliable (1000+) |
| 249 | 23285 | 1002 | UDP_VEHICLE_STATE_SYNC | High-Freq Unreliable (1000+) |
| 250 | 23286 | 1003 | UDP_AIRDROP_STATE_SYNC | High-Freq Unreliable (1000+) |
| 251 | 23287 | 1004 | UDP_SYNC_AI_MOVE | High-Freq Unreliable (1000+) |
| 252 | 23288 | 1005 | UDP_UAV_STATE_SYNC | High-Freq Unreliable (1000+) |
| 253 | 23289 | 1006 | UDP_PASSENGER_STATE_SYNC | High-Freq Unreliable (1000+) |
| 254 | 23290 | 1007 | UDP_LevelMovePlatform_STATE_SYNC | High-Freq Unreliable (1000+) |
| 255 | 23291 | 1008 | UDP_VEHICLE_MACHINEGUN_SYNC | High-Freq Unreliable (1000+) |
| 256 | 23292 | 1009 | UDP_AI_STATE_SYNC | High-Freq Unreliable (1000+) |
| 257 | 23293 | 1010 | UDP_PLAYER_HURT | High-Freq Unreliable (1000+) |
| 258 | 23294 | 1011 | UDP_PET_STATE_SYNC | High-Freq Unreliable (1000+) |
| 259 | 23295 | 1012 | UDP_PLAYER_STATE_SYNC_V2 | High-Freq Unreliable (1000+) |
| 260 | 23296 | 1013 | UDP_PLAYER_HEAL | High-Freq Unreliable (1000+) |
| 261 | 23297 | 1014 | UDP_PLAYER_POSITION_ONLY | High-Freq Unreliable (1000+) |
| 262 | 23298 | 1015 | UDP_SYNC_CATAPULT | High-Freq Unreliable (1000+) |
| 263 | 23299 | 1016 | UDP_SYNC_AIM_ROTATION | High-Freq Unreliable (1000+) |
| 264 | 23300 | 1017 | UDP_SYNC_ASSISTANT_INFO | High-Freq Unreliable (1000+) |
| 265 | 23301 | 1018 | UDP_SYNC_PROTECTED_HELMET_EVENT | High-Freq Unreliable (1000+) |

## 3. Verified Wire Layout Specifications for Key Opcodes

### 3.1 Opcode 31: `RUDP_JOIN_MATCH_FINISHED` (Wire Value: 130, Relative Index: 31)
- **TypeDef**: `message. nSa~rX` [4580], Disassembled live at RVA `0x1ef36f5`
- **Total Length**: **89 bytes**
- **Wire Layout**:
  * **Header (39 bytes, `<iQQIBiHii`)**:
    - `[4B int32 err_code]` (`message.qLLZWho`: 0 = ERR_NONE)
    - `[8B uint64 match_id]`
    - `[8B uint64 account_id]`
    - `[4B uint32 server_time]` (UNIX timestamp)
    - `[1B uint8 map_id]` (1 = Bermuda)
    - `[4B int32 waiting_seconds]` (60s countdown)
    - `[2B uint16 weather_style]` (1 = Normal)
    - `[4B int32 game_mode]` (1 = Battle Royale)
    - `[4B int32 room_type]` (0 = Casual)
  * **Nested SafeZone (`message.j]‚VkzA`, TypeDef [4560]) (34 bytes, `<hffffffff`)**:
    - `[2B int16 phase]`
    - `[16B 4x float32 Circle 1 Current: center_x, center_y, center_z, radius]`
    - `[16B 4x float32 Circle 2 Next: center_x, center_y, center_z, radius]`
  * **Trailing Barbosa Collections (16 bytes, `<iiii`)**:
    - `[4B int32 field11_count = 0]` (List<int>)
    - `[4B int32 field12_count = 0]` (List<uint>)
    - `[4B int32 field13_count = 0]` (List<Nested>)
    - `[4B uint32 field14_val = 0]`

---

### 3.2 Opcode 2: `RUDP_PLAYER_JOIN` (Wire Value: 101, Relative Index: 2)
- **TypeDef**: `message.ae zaPn` [4579], Disassembled live at RVA `0x1fafc18`
- **Wire Layout**: Variable Length (116B for standard bot, ~116-125B depending on strings)
  * `[8B uint64 player_id]`
  * `[8B uint64 account_id]`
  * `[1B uint8 team_id]`
  * `[1B uint8 camp]`
  * `[8B uint64 match_id]`
  * `[.NET String nickname]` (7-bit length prefix + UTF-8 bytes)
  * `[4B uint32 avatar_id]`
  * `[1B uint8 is_bot]` (1 = bot, 0 = human)
  * `[4B uint32 level]`
  * `[4B uint32 rank]`
  * `[1B uint8 is_ready]`
  * `[4B int32 clothes_count]` + `[8B * count uint64 clothes_ids]` (Field 12)
  * `[1B uint8 gender]`
  * `[1B uint8 is_alive]`
  * `[4B int32 skills_count]` + `[4B * count uint32 skill_ids]` (Field 15)
  * `[.NET String region]` (e.g. "NA")
  * `[4B uint32 banner_id]`
  * `[.NET String headpic]` (e.g. "avatar_01")

---

### 3.3 Opcode 17: `RUDP_SYNC_SCENE_INFO` (Wire Value: 116, Relative Index: 17)
- **TypeDef**: `message. nSa~rX` / `S2C_SyncSceneInfo`
- **Total Length**: **36 bytes**
- **Wire Layout (`<QffIffff`)**:
  * `[8B uint64 match_id]`
  * `[4B float32 elapsed_time]`
  * `[4B float32 countdown_seconds]` (60.0s for Spawn Island)
  * `[4B uint32 alive_players]`
  * `[4B float32 spawn_island_x]` (-500.0)
  * `[4B float32 spawn_island_y]` (10.0)
  * `[4B float32 spawn_island_z]` (800.0)
  * `[4B float32 spawn_island_radius]` (60.0)

---

### 3.4 Opcode 11: `RUDP_BATTLE_START` (Wire Value: 110, Relative Index: 11)
- **TypeDef**: `message.DtAJjUT` [4571]
- **Total Length**: **44 bytes**
- **Wire Layout (`<Qffffffff`)**:
  * `[8B uint64 match_id]`
  * `[12B 3x float32 start_pos (x, y, z)]`
  * `[12B 3x float32 end_pos (x, y, z)]`
  * `[4B float32 altitude]` (420.0)
  * `[4B float32 flight_speed]` (65.0)
  * `[4B float32 flight_duration]` (30.0)

---

### 3.5 Opcode 443: `RUDP_TeamParachuteInfo` (Wire Value: 443, Relative Index: 230)
- **TypeDef**: `message.]}CbXoA` [4584] / `S2C_ParachuteSync`
- **Total Length**: **33 bytes**
- **Wire Layout (`<IBfffffffI`)**:
  * `[4B uint32 player_id]`
  * `[1B uint8 phase]` (0=Airplane, 1=Freefall/Skydive, 2=Parachute Open, 3=Landed)
  * `[12B 3x float32 position (x, y, z)]`
  * `[4B float32 velocity_y]`
  * `[4B float32 forward_speed]`
  * `[4B float32 yaw]`
  * `[4B uint32 parachute_id]` (e.g. 902001)

---

### 3.6 Opcode 4: `RUDP_MATCH_END` (Wire Value: 103, Relative Index: 4)
- **TypeDef**: `message.~Hy{}`{` [4578]
- **Wire Layout**:
  * `[8B uint64 match_id]`
  * `[4B uint32 winner_team_id]`
  * `[1B uint8 reason]` (0 = Normal Victory, 1 = Timeout, 2 = Forfeit)
  * `[4B int32 survivor_count]`

---

### 3.7 Opcode 107 Disambiguation:
- **Wire Value 107 (`RUDP_DEAD`, Relative Index 8)**:
  * **TypeDef**: `message.K~|bywX` [4559]
  * **Wire Layout**:
    - `[8B uint64 victim_id]`
    - `[8B uint64 killer_id]`
    - `[.NET String killer_name]`
    - `[4B uint32 weapon_id]`
    - `[1B uint8 is_headshot]`
    - `[2B int16 rank]`
    - `[2B int16 kills]`
    - `[1B uint8 is_suicide]`
    - `[1B uint8 padding = 0]`
- **Relative Index 107 (`RUDP_SPECTATOR_REJOIN_DEADPLAYERINFO`, Wire Value 206)**:
  * **TypeDef**: Spectator Rejoin State
  * **Wire Layout**:
    - `[8B uint64 player_id]`
    - `[8B uint64 match_id]`
    - `[12B 3x float32 death_position]`
    - `[4B uint32 spectator_count]`
