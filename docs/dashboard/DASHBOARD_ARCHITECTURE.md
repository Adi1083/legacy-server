# IND PROJECT Control Center — FF 2019 Restoration
# Architecture & Technical Design Specification
**Version:** 2.0.0 (Phase 1 Baseline)  
**Author:** Lead Architect / Technical Coordinator (Agent 0)  
**Target:** Unified Single-Page Application (SPA) Administration Platform  

---

## 1. System Overview & Core Philosophy

The **IND PROJECT Control Center** is the unified administrative and live-operations command interface for the **FF 2019 Restoration** (Barbosa private server platform).

### The Core Problem Solved
Prior to this architecture, the dashboard was fractured across 7 disconnected multi-page HTML documents (`index.html`, `vault.html`, `social.html`, `luck_royale.html`, `banners.html`, `modes.html`, `tracker.html`). Each page maintained its own isolated styling, made direct unstructured `fetch` calls, and fatally hardcoded target player account IDs to `10001`.

### The Architectural Solution
1. **Single-Page Application (SPA):** Seamless view switching without page reloads, eliminating flicker and preserving state.
2. **Apple-Inspired Dark Glassmorphism:** Restrained, ultra-premium interface adhering to macOS/iPadOS design guidelines (deep navy backgrounds, frosted blur panels, fine borders, San Francisco font stack).
3. **Centralized Player Context (`PlayerContext`):** A shared singleton state holding the currently active player account ID. Changing the selected player in the Player Directory instantly updates all player-bound workspaces (Vault, Wardrobe, Economy, Mail, Gacha Inspector).
4. **Centralized API Client (`ApiClient`):** Unified HTTP transport with timeout protection, error normalization, standard CORS handling, and authentication token injection.
5. **Real-Data Guarantee:** No simulated CPU/RAM gauges, no mock online counts, and no fake transactions. When an operation lacks backend support, the UI explicitly renders an informative **"Requires Backend Support"** state.

---

## 2. Information Architecture & Navigation Hierarchy

The control center organizes all 10 core functional domains into an expandable, keyboard-navigable sidebar:

```
[01] OVERVIEW
  ├── Main Dashboard            (#/overview/main)
  └── Server Monitoring         (#/overview/monitoring)

[02] PLAYER MANAGEMENT
  ├── Player Directory          (#/players/directory)
  ├── Player Inspector          (#/players/inspector)
  ├── Account Manager           (#/players/account)
  ├── Ban Manager               (#/players/bans)
  └── Live Sessions             (#/players/sessions)

[03] INVENTORY & COLLECTION
  ├── Inventory Manager         (#/inventory/manager)
  ├── Character Manager         (#/inventory/characters)
  ├── Pet Manager               (#/inventory/pets)
  └── Cosmetics & Wardrobe      (#/inventory/wardrobe)

[04] ECONOMY
  ├── Currency Manager          (#/economy/currencies)
  └── Player Wallet Inspector   (#/economy/wallet)

[05] LUCK ROYALE STUDIO
  ├── Overview                  (#/luck-royale/overview)
  ├── Machine Manager           (#/luck-royale/machines)
  ├── Reward Pool Editor        (#/luck-royale/pools)
  ├── Lucky Meter & Pity        (#/luck-royale/pity)
  ├── Currency & Vouchers       (#/luck-royale/currencies)
  ├── Incubator Forge           (#/luck-royale/forge)
  ├── Events & Discounts        (#/luck-royale/events)
  ├── Banner Configuration      (#/luck-royale/banners)
  ├── Player Gacha Inspector    (#/luck-royale/player)
  ├── Transaction Explorer      (#/luck-royale/transactions)
  └── Probability Simulator     (#/luck-royale/simulator)

[06] GAME MANAGEMENT
  ├── Game Modes                (#/game/modes)
  ├── Maps                      (#/game/maps)
  ├── Matchmaking               (#/game/matchmaking)
  └── Custom Rooms              (#/game/rooms)

[07] SOCIAL & COMMUNICATION
  ├── Mail Manager              (#/social/mail)
  ├── Friends Manager           (#/social/friends)
  └── Squad Manager             (#/social/squads)

[08] CONTENT MANAGEMENT
  ├── Banner Manager            (#/cms/banners)
  ├── Lobby CMS                 (#/cms/lobby)
  ├── Event Manager             (#/cms/events)
  └── Announcements             (#/cms/announcements)

[09] LOGS & MONITORING
  ├── API Monitor               (#/logs/api)
  ├── Audit Logs                (#/logs/audit)
  └── Transaction Explorer      (#/logs/transactions)

[10] SYSTEM ADMINISTRATION
  ├── Server Settings           (#/system/settings)
  ├── Database                  (#/system/database)
  ├── System Tools              (#/system/tools)
  └── Security                  (#/system/security)
```

---

## 3. Visual Design System: Apple Dark Glassmorphism

The interface strictly avoids garish gaming neon tropes, excessive glow effects, and oversized Bootstrap cards. It implements authentic macOS Sonoma / visionOS dark translucent visual hierarchy.

### Design Tokens (CSS Variables)

```css
:root {
  /* Surface Layers */
  --bg-desktop: #040711;
  --bg-sidebar: rgba(12, 18, 30, 0.72);
  --bg-topbar: rgba(12, 18, 30, 0.65);
  --bg-card: rgba(18, 26, 42, 0.58);
  --bg-card-hover: rgba(26, 38, 62, 0.65);
  --bg-input: rgba(8, 13, 24, 0.70);
  
  /* Glassmorphism Blur Filters */
  --glass-blur-sm: blur(12px);
  --glass-blur-md: blur(20px);
  --glass-blur-lg: blur(32px);
  
  /* Borders & Dividers */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-focused: rgba(56, 189, 248, 0.45);
  
  /* Restrained Accents */
  --accent-cyan: #38bdf8;
  --accent-blue: #3b82f6;
  --accent-indigo: #6366f1;
  --accent-violet: #8b5cf6;
  --accent-emerald: #10b981;
  --accent-amber: #f59e0b;
  --accent-rose: #f43f5e;
  
  /* Text Hierarchy */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-tertiary: #64748b;
  --text-disabled: #334155;
  
  /* Typography */
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: "SF Mono", "JetBrains Mono", Menlo, Monaco, Consolas, monospace;
}
```

---

## 4. Shared Technical Contracts & Interfaces

### A. Centralized API Client (`ApiClient`)
The application uses a centralized API client instance exposed on `window.ApiClient` to eliminate scattered `fetch` logic:

```typescript
interface ApiResponse<T = any> {
  ok: boolean;
  data?: T;
  error?: string;
  code?: number;
  status: number;
}

class ApiClient {
  private baseUrl: string = '';
  private adminToken: string = '';

  public async get<T>(endpoint: string, params?: Record<string, any>): Promise<ApiResponse<T>>;
  public async post<T>(endpoint: string, body?: any): Promise<ApiResponse<T>>;
  public async put<T>(endpoint: string, body?: any): Promise<ApiResponse<T>>;
  public async delete<T>(endpoint: string, body?: any): Promise<ApiResponse<T>>;
  public async upload(endpoint: string, formData: FormData): Promise<ApiResponse<any>>;
}
```

### B. Centralized Player Context (`PlayerContext`)
Manages the globally active player across all views:

```typescript
interface PlayerSummary {
  account_id: number;
  nickname: string;
  level: number;
  diamonds: number;
  gold: number;
  is_banned?: boolean;
}

class PlayerContext {
  private currentAccountId: number = 10001; // default initial account
  private playerCache: Map<number, any> = new Map();
  private subscribers: Set<(accountId: number, player: any) => void> = new Set();

  public getSelectedAccountId(): number;
  public setSelectedAccountId(accountId: number): Promise<void>;
  public subscribe(callback: (accountId: number, player: any) => void): () => void;
  public refreshCurrentPlayer(): Promise<void>;
}
```

### C. Reusable UI Components
All workspace views must instantiate standard components from `window.UIComponents`:
1. `UI.Card(title, subtitle, actions, content)`
2. `UI.Table(columns, rows, options)`
3. `UI.Pagination(currentPage, totalPages, onPageChange)`
4. `UI.Badge(text, variant)` (variants: `cyan`, `green`, `amber`, `rose`, `neutral`)
5. `UI.Button(label, variant, onClick, options)`
6. `UI.Input(type, label, value, onChange, options)`
7. `UI.Modal(title, body, actions)`
8. `UI.Confirm(title, message, onConfirm, isDestructive)`
9. `UI.Toast(message, type)` (`success`, `error`, `warning`, `info`)
10. `UI.EmptyState(icon, title, message, actionButton)`
11. `UI.UnavailableState(featureName, requiredBackendEndpoint, notes)`

---

## 5. Security & Verification Requirements
- All administrative destructive actions (account wiping, banning, inventory deletion, machine configuration purge) require a modal confirmation prompt.
- Endpoints requiring tokens pass `Authorization: Bearer <token>` and `X-Admin-Token: <token>` automatically when configured in Topbar settings.
- All requests are logged in the API Monitor view for complete operational traceability.
