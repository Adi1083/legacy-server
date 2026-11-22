# IND PROJECT Control Center — FF 2019 Restoration
# Exhaustive API Integration Map & Data Contract
**Version:** 2.0.0  
**Authority:** Agent 0 — Lead Architect & Agent 11 — Backend Integration Engineer  

---

## 1. Existing Endpoints: Verified Active & Reused

### A. GET Endpoints

| HTTP Method | Route | Description | Params / Query | Response Structure | Persistence | Handler Location |
|---|---|---|---|---|---|---|
| `GET` | `/api/dashboard/state` | Returns player profile, wallet, characters, pets, inventory | `account_id` (int) | `{"ok": true, "account_id": ..., "nickname": ..., "wallet": {"gold": N, "diamonds": N}, "characters": [...], "pets": [...], "inventory": [...]}` | Read-only | `dashboard_api.py:292` |
| `GET` | `/api/dashboard/branding` | Server brand slots, MOTD, subtitle | None | `{"ok": true, "slots": {...}}` | JSON file | `dashboard_api.py:296` |
| `GET` | `/api/dashboard/requests` | Filtered HTTP request logs | `limit`, `q`, `method` | `[{"time": "...", "method": "...", "path": "...", "ip": "..."}]` | In-memory ring buffer (1000 items) | `dashboard_api.py:301` |
| `GET` | `/api/dashboard/mail` | Player mailbox messages | `account_id` (int) | `{"ok": true, "mails": [{"id": N, "title": "...", "content": "...", "attachments": [...]}]}` | SQLite `mails` table | `dashboard_api.py:313` |
| `GET` | `/api/dashboard/friends` | Player friends list & requests | `account_id` (int) | `{"ok": true, "friends": [...], "pending": [...]}` | SQLite `friends` table | `dashboard_api.py:321` |
| `GET` | `/api/dashboard/squad` | Current squad lobby status | `account_id` (int) | `{"ok": true, "squad": {...}}` | In-memory squad state | `dashboard_api.py:329` |
| `GET` | `/api/dashboard/cms` | Full CMS configuration | None | `{"ok": true, "banners": [...], "splashes": [...], "popups": [...], "announcements": [...], "marquee": "..."}` | SQLite & JSON | `dashboard_api.py:334` |
| `GET` | `/api/dashboard/cms/banners`| Active billboard banners list | None | `{"ok": true, "banners": [{"id": "...", "filename": "...", "active": true, "order": 0}]}` | SQLite / Disk | `dashboard_api.py:339` |
| `GET` | `/api/dashboard/modes` | Game modes & map availability | None | `{"ok": true, "modes": {...}}` | JSON `game_modes.json` | `dashboard_api.py:344` |
| `GET` | `/api/admin/luck-royale/machines` | All gacha machines | None | `{"ok": true, "machines": [...]}` | SQLite `gacha_states` | `admin_luck_royale_api.py:84` |
| `GET` | `/api/admin/luck-royale/pools/{id}` | Machine reward items & weights | Machine ID | `{"ok": true, "pool": [...]}` | SQLite / Registry | `admin_luck_royale_api.py:112` |
| `GET` | `/api/admin/luck-royale/lucky/{id}` | Pity thresholds & lucky meter | Machine ID | `{"ok": true, "lucky": {...}}` | SQLite `gacha_states` | `admin_luck_royale_api.py:140` |
| `GET` | `/api/admin/luck-royale/currencies` | Ticket IDs and currency costs | None | `{"ok": true, "currencies": {...}}` | Config / Registry | `admin_luck_royale_api.py:168` |
| `GET` | `/api/admin/luck-royale/forge/{id}` | Incubator exchange recipes | Machine ID | `{"ok": true, "recipes": [...]}` | SQLite `gacha_special_exchanges` | `admin_luck_royale_api.py:196` |
| `GET` | `/api/admin/luck-royale/events` | Active discount events | None | `{"ok": true, "events": [...]}` | Config / Registry | `admin_luck_royale_api.py:224` |
| `GET` | `/api/admin/luck-royale/audit` | Roll transaction logs | `limit`, `account_id` | `{"ok": true, "transactions": [...]}` | SQLite `gacha_transactions` | `admin_luck_royale_api.py:252` |
| `GET` | `/api/admin/luck-royale/config`| Complete gacha JSON backup | None | `{"ok": true, "config": {...}}` | Registry dump | `admin_luck_royale_api.py:280` |
| `GET` | `/api/admin/luck-royale/preview`| Client packet structure view | None | `{"ok": true, "preview": {...}}` | Registry client payload | `admin_luck_royale_api.py:308` |

---

### B. POST / Mutation Endpoints

| HTTP Method | Route | Required Body (JSON) | Response Structure | Persistence | Handler Location |
|---|---|---|---|---|---|
| `POST` | `/api/dashboard/wallet/grant` | `{"account_id": N, "gold": N, "diamonds": N}` | `{"ok": true, "wallet": {...}}` | SQLite `accounts` table | `dashboard_api.py:465` |
| `POST` | `/api/dashboard/wallet/set` | `{"account_id": N, "gold": N, "diamonds": N}` | `{"ok": true, "wallet": {...}}` | SQLite `accounts` table | `dashboard_api.py:488` |
| `POST` | `/api/dashboard/items/grant` | `{"account_id": N, "item_ids": [N], "amount": N}` | `{"ok": true, "granted": [...]}` | SQLite `inventory` table | `dashboard_api.py:510` |
| `POST` | `/api/dashboard/character/select` | `{"account_id": N, "character_id": N}` | `{"ok": true, "selected_character": N}`| SQLite `characters` table | `dashboard_api.py:435` |
| `POST` | `/api/dashboard/character/equip` | `{"account_id": N, "character_id": N, "item_ids": [N]}` | `{"ok": true, "equipped": [...]}` | SQLite `characters` table | `dashboard_api.py:448` |
| `POST` | `/api/dashboard/pet/select` | `{"account_id": N, "pet_id": N}` | `{"ok": true, "selected_pet": N}` | SQLite `pets` table | `dashboard_api.py:458` |
| `POST` | `/api/dashboard/profile/update` | `{"account_id": N, "nickname": "...", "level": N, "exp": N, "rank": N, "signature": "..."}` | `{"ok": true, "profile": {...}}` | SQLite `accounts` table | `dashboard_api.py:415` |
| `POST` | `/api/dashboard/branding/update`| `{"key": "...", "value": "..."}` | `{"ok": true}` | JSON file | `dashboard_api.py:405` |
| `POST` | `/api/dashboard/mail/send` | `{"account_id": N, "title": "...", "content": "...", "gold": N, "diamonds": N, "items": [...]}` | `{"ok": true, "mail_id": N}` | SQLite `mails` table | `dashboard_api.py:530` |
| `POST` | `/api/dashboard/mail/claim` | `{"account_id": N, "mail_id": N}` | `{"ok": true, "claimed": {...}}` | SQLite `mails` & `accounts` | `dashboard_api.py:555` |
| `POST` | `/api/dashboard/mail/delete` | `{"account_id": N, "mail_id": N}` | `{"ok": true}` | SQLite `mails` table | `dashboard_api.py:575` |
| `POST` | `/api/dashboard/friends/request`| `{"account_id": N, "target_id": N}` | `{"ok": true}` | SQLite `friends` table | `dashboard_api.py:590` |
| `POST` | `/api/dashboard/friends/accept` | `{"account_id": N, "target_id": N}` | `{"ok": true}` | SQLite `friends` table | `dashboard_api.py:605` |
| `POST` | `/api/dashboard/friends/reject` | `{"account_id": N, "target_id": N}` | `{"ok": true}` | SQLite `friends` table | `dashboard_api.py:620` |
| `POST` | `/api/dashboard/friends/remove` | `{"account_id": N, "target_id": N}` | `{"ok": true}` | SQLite `friends` table | `dashboard_api.py:635` |
| `POST` | `/api/dashboard/squad/create` | `{"account_id": N}` | `{"ok": true, "squad_id": N}` | In-memory | `dashboard_api.py:650` |
| `POST` | `/api/dashboard/squad/invite` | `{"account_id": N, "target_id": N}` | `{"ok": true}` | In-memory | `dashboard_api.py:665` |
| `POST` | `/api/dashboard/squad/join` | `{"account_id": N, "squad_id": N}` | `{"ok": true}` | In-memory | `dashboard_api.py:680` |
| `POST` | `/api/dashboard/squad/leave` | `{"account_id": N}` | `{"ok": true}` | In-memory | `dashboard_api.py:695` |
| `POST` | `/api/dashboard/squad/kick` | `{"account_id": N, "target_id": N}` | `{"ok": true}` | In-memory | `dashboard_api.py:710` |
| `POST` | `/api/dashboard/squad/ready` | `{"account_id": N, "ready": bool}` | `{"ok": true}` | In-memory | `dashboard_api.py:725` |
| `POST` | `/api/dashboard/cms/banner/upload` | Multipart form: `file`, `name`, `order` | `{"ok": true, "banner": {...}}` | Disk & SQLite | `dashboard_api.py:740` |
| `POST` | `/api/dashboard/cms/banner/delete` | `{"banner_id": "..."}` | `{"ok": true}` | Disk & SQLite | `dashboard_api.py:765` |
| `POST` | `/api/dashboard/cms/banner/reorder`| `{"order": ["id1", "id2"]}` | `{"ok": true}` | SQLite | `dashboard_api.py:785` |
| `POST` | `/api/dashboard/cms/splash/upload` | Multipart form: `file` | `{"ok": true, "splash": {...}}` | Disk & JSON | `dashboard_api.py:800` |
| `POST` | `/api/dashboard/cms/splash/toggle` | `{"active": bool}` | `{"ok": true}` | JSON | `dashboard_api.py:820` |
| `POST` | `/api/dashboard/cms/popup/create` | `{"title": "...", "content": "...", "image": "..."}` | `{"ok": true, "popup_id": N}` | SQLite | `dashboard_api.py:835` |
| `POST` | `/api/dashboard/cms/popup/delete` | `{"popup_id": N}` | `{"ok": true}` | SQLite | `dashboard_api.py:855` |
| `POST` | `/api/dashboard/cms/popup/toggle` | `{"popup_id": N, "active": bool}` | `{"ok": true}` | SQLite | `dashboard_api.py:870` |
| `POST` | `/api/dashboard/cms/announcement/create` | `{"title": "...", "content": "..."}` | `{"ok": true, "announcement_id": N}` | SQLite | `dashboard_api.py:885` |
| `POST` | `/api/dashboard/cms/announcement/delete` | `{"announcement_id": N}` | `{"ok": true}` | SQLite | `dashboard_api.py:905` |
| `POST` | `/api/dashboard/cms/announcement/toggle` | `{"announcement_id": N, "active": bool}`| `{"ok": true}` | SQLite | `dashboard_api.py:920` |
| `POST` | `/api/dashboard/cms/marquee/update`| `{"text": "..."}` | `{"ok": true}` | JSON | `dashboard_api.py:935` |
| `POST` | `/api/dashboard/modes/update` | `{"mode_id": "...", "enabled": bool}` | `{"ok": true}` | JSON `game_modes.json` | `dashboard_api.py:950` |
| `POST` | `/api/dashboard/modes/unlock-all`| None | `{"ok": true}` | JSON `game_modes.json` | `dashboard_api.py:965` |
| `POST` | `/api/dashboard/modes/lock-optional`| None | `{"ok": true}` | JSON `game_modes.json` | `dashboard_api.py:980` |
| `POST` | `/api/dashboard/requests/clear`| None | `{"ok": true}` | In-memory buffer flush | `dashboard_api.py:990` |
| `POST` | `/api/admin/luck-royale/machines` | `{"machine_id": "...", ...}` | `{"ok": true, "machine": {...}}` | SQLite `gacha_states` | `admin_luck_royale_api.py:95` |
| `PUT` | `/api/admin/luck-royale/machines/{id}`| `{"name": "...", "active": bool, ...}` | `{"ok": true}` | SQLite `gacha_states` | `admin_luck_royale_api.py:100` |
| `DELETE`| `/api/admin/luck-royale/machines/{id}`| None | `{"ok": true}` | SQLite `gacha_states` | `admin_luck_royale_api.py:105` |
| `PUT` | `/api/admin/luck-royale/pools/{id}` | `{"items": [{"item_id": N, "weight": N}]}`| `{"ok": true}` | SQLite / Registry | `admin_luck_royale_api.py:125` |
| `POST` | `/api/admin/luck-royale/spin` | `{"machine_id": "...", "account_id": N, "count": N}` | `{"ok": true, "rewards": [...]}` | SQLite `gacha_transactions` | `admin_luck_royale_api.py:320` |

---

## 2. Phase 4 Target Backend API Contracts (To Be Implemented)

### `GET /api/admin/players`
- **Purpose:** Enumerate all registered players with server-side pagination, searching, and sorting.
- **Query Parameters:**
  - `page` (int, default: 1)
  - `limit` (int, default: 25, max: 100)
  - `q` (string, optional: search nickname or account ID substring)
  - `sort` (string, optional: `account_id`, `nickname`, `level`, `diamonds`, `gold`)
  - `order` (string: `asc` or `desc`)
- **Response Shape:**
```json
{
  "ok": true,
  "total": 201,
  "page": 1,
  "limit": 25,
  "players": [
    {
      "account_id": 10001,
      "nickname": "PushpaGG",
      "level": 35,
      "exp": 12450,
      "rank": 2100,
      "gold": 500000,
      "diamonds": 12500,
      "is_banned": false,
      "created_at": "2026-11-12 18:00:00"
    }
  ]
}
```

### `POST /api/admin/players/create`
- **Purpose:** Create a fresh player account with specified initial attributes.
- **Body:** `{"nickname": "Hero_01", "region": "IND", "level": 1, "gold": 1000, "diamonds": 100}`
- **Response Shape:** `{"ok": true, "account_id": 10202, "nickname": "Hero_01"}`

### `DELETE /api/admin/players/{account_id}`
- **Purpose:** Permanently wipe an account and cascade delete inventory, claims, gacha states, and mails.
- **Response Shape:** `{"ok": true, "deleted_account_id": 10202}`

### `POST /api/admin/players/{account_id}/ban` & `/unban`
- **Purpose:** Mark account as suspended or restored.
- **Body:** `{"reason": "Testing sanction flow"}`
- **Response Shape:** `{"ok": true, "account_id": 10001, "is_banned": true}`

### `DELETE /api/admin/players/{account_id}/items/{item_id}`
- **Purpose:** Remove an exploited or unwanted item from player inventory.
- **Response Shape:** `{"ok": true, "removed_item_id": 9999}`

### `GET /api/admin/sessions` & `POST /api/admin/sessions/{account_id}/kick`
- **Purpose:** Enumerate active TCP/UDP lobby sessions and force socket termination.
- **Response Shape:** `{"ok": true, "sessions": [{"account_id": 10001, "ip": "127.0.0.1", "connected_seconds": 340}]}`
