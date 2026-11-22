# IND PROJECT Control Center — FF 2019 Restoration
# Swarm Task Assignments & File Ownership Matrix
**Version:** 2.0.0  
**Authority:** Agent 0 — Lead Architect / Technical Coordinator  

---

## 1. Multi-Agent Roster & Functional Ownership

```
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent ID | Role Title                             | Permitted File Boundaries                | Core Responsibilities              |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 0  | Lead Architect & Technical Coordinator | server/docs/dashboard/*                  | System architecture, integration,  |
|          |                                        |                                          | shared contracts, review & signoff |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 1  | Design System & UI/UX Architect        | server/static/dashboard/src/design/*     | Design tokens, CSS variables,      |
|          |                                        | server/static/dashboard/src/shared/ui.js | glassmorphism panels, UI widgets   |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 2  | App Shell & Navigation Engineer        | server/static/dashboard/src/app/*        | SPA shell, sidebar, topbar,        |
|          |                                        | server/static/dashboard/index.html       | breadcrumbs, router, modals/toasts |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 3  | Overview & Server Monitoring Engineer  | server/static/dashboard/src/modules/     | Main dashboard, server status,     |
|          |                                        |   overview/*                             | API telemetry, active stats        |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 4  | Player Management Engineer             | server/static/dashboard/src/modules/     | Player directory, player inspector,|
|          |                                        |   players/*                              | account manager, ban manager       |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 5  | Inventory, Characters & Economy Eng.   | server/static/dashboard/src/modules/     | Inventory vault, character skins,  |
|          |                                        |   inventory/*, economy/*                 | pets, wardrobe, wallet manager     |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 6  | Luck Royale Studio Engineer            | server/static/dashboard/src/modules/     | 12 gacha sub-workspaces, machines, |
|          |                                        |   luck-royale/*                          | pools, pity, forge, simulator      |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 7  | Game Management Engineer               | server/static/dashboard/src/modules/     | Game modes, maps, matchmaking,     |
|          |                                        |   game/*                                 | custom room server interfaces      |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 8  | Social & Communication Engineer        | server/static/dashboard/src/modules/     | Mail manager, mail composer,       |
|          |                                        |   social/*                               | friends manager, squad lobbies     |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 9  | Content Management Engineer            | server/static/dashboard/src/modules/     | Billboard banners, lobby CMS,      |
|          |                                        |   cms/*                                  | popups, announcements, marquee     |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 10 | Logs, Security & System Admin Engineer | server/static/dashboard/src/modules/     | API monitor, request logs,         |
|          |                                        |   logs/*, system/*                       | audit history, database stats      |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 11 | Backend API & Integration Engineer     | server/handlers/dashboard_api.py         | Missing endpoints, DB migrations,  |
|          |                                        | server/core/database.py, player.py       | authentication middleware          |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
| Agent 12 | QA, Integration & Regression Engineer  | server/tests/dashboard/*                 | E2E test scripts, verification,    |
|          |                                        | server/docs/dashboard/REGRESSION_*.md    | regression matrix, final signoff   |
+----------+----------------------------------------+------------------------------------------+------------------------------------+
```

---

## 2. Detailed Task Breakdown & Acceptance Criteria

### Agent 0 — Lead Architect & Coordinator
- **Deliverables:** `DASHBOARD_ARCHITECTURE.md`, `SWARM_TASK_ASSIGNMENTS.md`, `API_INTEGRATION_MAP.md`, `IMPLEMENTATION_STATUS.md`.
- **Acceptance Criteria:** Cohesive unified technical contracts established, zero conflicting file overlaps, strict governance of PRs/commits.

### Agent 1 — Design System & UI/UX Architect
- **Permitted Files:** `server/static/dashboard/src/design/tokens.css`, `server/static/dashboard/src/shared/ui.js`.
- **Deliverables:** Complete dark glassmorphism token set, `UIComponents` factory methods (`Card`, `Table`, `Badge`, `Button`, `Modal`, `Toast`, `EmptyState`, `UnavailableState`).
- **Acceptance Criteria:** Pure Apple-inspired aesthetic. No Bootstrap dependencies. Smooth transitions, responsive tables, zero horizontal page overflow.

### Agent 2 — Application Shell & Navigation Engineer
- **Permitted Files:** `server/static/dashboard/index.html`, `server/static/dashboard/src/app/shell.js`, `router.js`, `sidebar.js`, `topbar.js`.
- **Deliverables:** Hash-based SPA router (`#/module/view`), collapsible navigation sidebar with 10 expandable domain groups, topbar with breadcrumb trail, global search input, quick player selector, token configuration modal, and global toast container.
- **Acceptance Criteria:** Zero full-page refreshes. Navigating views updates breadcrumbs and retains state.

### Agent 3 — Overview & Server Monitoring Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/overview/main.js`, `monitoring.js`.
- **Deliverables:** Real-time server telemetry cards (HTTP 8080, TCP 8081, UDP 39800), active database player count, request throughput monitor, recent administrative audit log stream.
- **Acceptance Criteria:** Only genuine data displayed. No fake CPU/RAM mock gauges.

### Agent 4 — Player Management Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/players/directory.js`, `inspector.js`, `account.js`, `bans.js`, `sessions.js`.
- **Deliverables:** Searchable & paginated player directory (querying all 201 accounts), player inspector linking into `PlayerContext`, account creation and ban manager.
- **Acceptance Criteria:** Centralized player selection works dynamically. Selecting an account updates `PlayerContext` and broadcasts to all subscriber views.

### Agent 5 — Inventory, Characters & Economy Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/inventory/manager.js`, `characters.js`, `pets.js`, `wardrobe.js`, `server/static/dashboard/src/modules/economy/currencies.js`, `wallet.js`.
- **Deliverables:** Full inventory item browser with category filtering, item grant modal, character loadout picker, pet manager, and diamond/gold grant & set controls.
- **Acceptance Criteria:** Reacts instantly to active `PlayerContext` account ID. Destructive operations require confirmation.

### Agent 6 — Luck Royale Studio Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/luck-royale/*.js`.
- **Deliverables:** Integration of all 9 sub-routes (`/api/admin/luck-royale/*`) into 12 dedicated workspaces (Machine Manager, Reward Pool Editor, Lucky Meter & Pity, Currency/Voucher, Incubator Forge, Events, Banner overrides, Player Gacha Inspector, Audit Explorer, Probability Simulator).
- **Acceptance Criteria:** 100% preservation of verified gacha backend logic. Real vs Simulated spins clearly visually distinct.

### Agent 7 — Game Management Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/game/modes.js`, `maps.js`, `matchmaking.js`, `rooms.js`.
- **Deliverables:** Game mode toggles and unlock-all controls wired to `/api/dashboard/modes/*`. Matchmaking and custom room server management panels clearly marked with unavailable state where backend endpoints are pending.

### Agent 8 — Social & Communication Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/social/mail.js`, `friends.js`, `squads.js`.
- **Deliverables:** Mailbox reader with claim/delete action buttons, mail composer with gold/diamond attachment options, friends list inspector, squad lobby state monitor.

### Agent 9 — Content Management Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/cms/banners.js`, `lobby.js`, `events.js`, `announcements.js`.
- **Deliverables:** Billboard banner uploader and priority reorder list, startup splash image toggler, popup modal advert creator, marquee text ticker editor.

### Agent 10 — Logs, Security & System Administration Engineer
- **Permitted Files:** `server/static/dashboard/src/modules/logs/api.js`, `audit.js`, `transactions.js`, `server/static/dashboard/src/modules/system/settings.js`, `database.js`, `security.js`.
- **Deliverables:** Live API request monitor stream with clear and filter tools, gacha transaction roll history, database table row counts, security token inspector.

### Agent 11 — Backend API & Integration Engineer
- **Permitted Files:** `server/handlers/dashboard_api.py`, `server/core/player.py`, `server/core/database.py`.
- **Deliverables:** Implement missing endpoints: `GET /api/admin/players` (paginated), `GET /api/admin/players/{id}`, `POST /api/admin/players/create`, `POST /api/admin/players/{id}/ban`, `POST /api/admin/players/{id}/unban`, `DELETE /api/admin/players/{id}/items/{item_id}`.
- **Acceptance Criteria:** Zero disruption to existing lobby or combat servers. 100% backward compatibility.

### Agent 12 — QA, Integration & Regression Engineer
- **Permitted Files:** `server/tests/dashboard/*`, `server/docs/dashboard/REGRESSION_REPORT.md`.
- **Deliverables:** Comprehensive test suite validating all SPA routes, API client calls, player context switches, error boundaries, and backend regressions.
