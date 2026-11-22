/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Topbar Navigation & Global Context Bar
 * Dynamic Breadcrumbs, Player Context Pill, Auth Modal, Refresh Actions
 */

const Topbar = {
  // Breadcrumb dictionary mapping section and view keys to canonical labels
  breadcrumbsMap: {
    'overview': { title: 'Overview', root: '#/overview/main' },
    'players': { title: 'Player Management', root: '#/players/directory' },
    'inventory': { title: 'Inventory & Collection', root: '#/inventory/manager' },
    'economy': { title: 'Economy', root: '#/economy/currencies' },
    'luck-royale': { title: 'Luck Royale Studio', root: '#/luck-royale/overview' },
    'game': { title: 'Game Management', root: '#/game/modes' },
    'social': { title: 'Social & Communication', root: '#/social/mail' },
    'cms': { title: 'Content Management', root: '#/cms/banners' },
    'logs': { title: 'Logs & Monitoring', root: '#/logs/api' },
    'system': { title: 'System Administration', root: '#/system/settings' }
  },

  viewTitles: {
    'main': 'Main Dashboard',
    'monitoring': 'Server Monitoring',
    'directory': 'Player Directory',
    'inspector': 'Player Inspector',
    'account': 'Account Manager',
    'bans': 'Ban & Sanction Manager',
    'sessions': 'Live TCP/UDP Sessions',
    'manager': 'Inventory Manager',
    'characters': 'Character Manager',
    'pets': 'Pet Manager',
    'wardrobe': 'Cosmetics & Wardrobe',
    'currencies': 'Currency Manager',
    'wallet': 'Player Wallet',
    'overview': 'Studio Overview',
    'machines': 'Machine Manager',
    'pools': 'Reward Pool Editor',
    'pity': 'Lucky Meter & Pity',
    'forge': 'Incubator Forge',
    'events': 'Events & Discounts',
    'banners': 'Banner Overrides / Billboard',
    'player': 'Player Gacha State',
    'transactions': 'Spin Audit Ledger',
    'simulator': 'Probability Simulator',
    'modes': 'Game Modes',
    'maps': 'Map Rotation',
    'matchmaking': 'Matchmaking Queue',
    'rooms': 'Custom Rooms',
    'mail': 'Mailbox Manager',
    'mail-compose': 'Compose Mail',
    'friends': 'Friends Manager',
    'squads': 'Squad Manager',
    'lobby': 'Lobby CMS & Splash',
    'announcements': 'Announcements & Marquee',
    'api': 'API Live Monitor',
    'audit': 'Administrative Audit Log',
    'settings': 'Server Settings',
    'database': 'Database Status',
    'security': 'Security & Auth Controls'
  },

  _icon(name) {
    return (window.Icons && window.Icons[name]) || '';
  },

  render() {
    return `
      <div class="app-topbar">
        <div class="topbar-left">
          <!-- Mobile Sidebar Drawer Toggle (hidden on desktop) -->
          <button class="btn btn-secondary topbar-mobile-toggle" onclick="Sidebar.toggleMobile()" title="Open Navigation">
            ${this._icon('menu')}
          </button>

          <!-- Dynamic Breadcrumbs -->
          <div class="breadcrumbs" id="topbar-breadcrumbs">
            <span class="breadcrumb-segment" onclick="window.location.hash='#/overview/main'">OVERVIEW</span>
            <span class="breadcrumb-sep">/</span>
            <span class="breadcrumb-active">MAIN DASHBOARD</span>
          </div>
        </div>

        <div class="topbar-right">
          <!-- Active Player Context Indicator Pill -->
          <div class="player-context-pill" id="player-pill" title="Active Player Context — Click to switch player" onclick="Topbar.openPlayerSwitcherModal()">
            <div class="player-dot"></div>
            <span id="player-pill-label" style="font-weight: 500;">Account: 10001</span>
          </div>

          <!-- Admin Auth Token Configuration -->
          <button class="btn btn-secondary" style="padding: 5px 10px; font-size: 11.5px;" onclick="Topbar.openAuthModal()" title="Configure Administrative Auth Token">
            ${this._icon('authLock')} <span>Auth</span>
          </button>

          <!-- Refresh Current State -->
          <button class="btn btn-secondary" id="topbar-refresh-btn" style="padding: 5px 10px; font-size: 11.5px;" onclick="Topbar.refreshCurrentState()" title="Refresh Player Context & Workspace">
            <span id="topbar-refresh-icon">${this._icon('refresh')}</span>
          </button>
        </div>
      </div>
    `;
  },

  init() {
    // Subscribe to PlayerContext changes
    window.playerContext.subscribe((accountId, playerData, isLoading) => {
      const pill = document.getElementById('player-pill');
      const label = document.getElementById('player-pill-label');
      if (pill) {
        if (isLoading) {
          pill.classList.add('loading');
        } else {
          pill.classList.remove('loading');
        }
      }

      if (label) {
        if (playerData && playerData.nickname) {
          label.textContent = `${playerData.nickname} (${accountId})`;
        } else {
          label.textContent = `Account: ${accountId}`;
        }
      }
    });
  },

  updateBreadcrumbs(hash) {
    const breadcrumbs = document.getElementById('topbar-breadcrumbs');
    if (!breadcrumbs) return;

    const cleanHash = hash.replace('#/', '').split('?')[0];
    const parts = cleanHash.split('/');
    const sectionKey = parts[0] || 'overview';
    const viewKey = parts[1] || 'main';

    const secMeta = this.breadcrumbsMap[sectionKey] || {
      title: sectionKey.toUpperCase(),
      root: `#/${sectionKey}/main`
    };

    const viewName = this.viewTitles[viewKey] || viewKey.replace(/-/g, ' ').toUpperCase();

    breadcrumbs.innerHTML = `
      <span class="breadcrumb-segment" onclick="window.location.hash='${secMeta.root}'">${secMeta.title.toUpperCase()}</span>
      <span class="breadcrumb-sep">/</span>
      <span class="breadcrumb-active">${viewName.toUpperCase()}</span>
    `;
  },

  async refreshCurrentState() {
    const icon = document.getElementById('topbar-refresh-icon');
    if (icon) icon.classList.add('spin-anim');

    try {
      await window.playerContext.refresh();
      await window.appRouter.handleRoute();
      if (window.UI && window.UI.Toast) {
        window.UI.Toast('Workspace & player state refreshed', 'success');
      }
    } catch (e) {
      if (window.UI && window.UI.Toast) {
        window.UI.Toast('Refresh completed with warnings', 'info');
      }
    } finally {
      setTimeout(() => {
        if (icon) icon.classList.remove('spin-anim');
      }, 700);
    }
  },

  openPlayerSwitcherModal() {
    const currentId = window.playerContext.getSelectedAccountId();
    const curPlayer = window.playerContext.getCurrentPlayer() || {};
    const nick = curPlayer.nickname || 'Unknown';
    const gold = curPlayer.wallet ? curPlayer.wallet.gold : 0;
    const dia = curPlayer.wallet ? curPlayer.wallet.diamonds : 0;

    const body = `
      <div style="background: rgba(10, 16, 28, 0.45); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 14px; margin-bottom: 16px;">
        <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Currently Active Dossier</div>
        <div style="font-size: 15px; font-weight: 700; color: #fff;">${nick} <code style="font-size: 12px; color: var(--accent-cyan); font-family: var(--font-mono); font-weight: normal;">(ID: ${currentId})</code></div>
        <div style="display: flex; gap: 16px; margin-top: 8px; font-size: 12px;">
          <div>Diamonds: <b style="color: var(--accent-cyan);">${dia}</b></div>
          <div>Gold: <b style="color: #fbbf24;">${gold}</b></div>
        </div>
      </div>

      <div style="margin-bottom: 14px;">
        <label style="display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">Enter Account ID:</label>
        <div style="display: flex; gap: 8px;">
          <input type="number" id="switcher-aid-input" class="form-input" placeholder="e.g. 10001" value="${currentId}">
          <button class="btn btn-primary" onclick="Topbar.switchPlayerSubmit()">Switch Context</button>
        </div>
      </div>

      <div>
        <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 6px;">Quick Presets:</label>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px;" onclick="Topbar.setQuickPlayer(10001)">10001 (PushpaGG)</button>
          <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px;" onclick="Topbar.setQuickPlayer(10002)">10002 (Test2)</button>
          <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px;" onclick="Topbar.setQuickPlayer(10003)">10003 (Test3)</button>
          <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px;" onclick="Topbar.setQuickPlayer(10004)">10004 (Test4)</button>
        </div>
      </div>
    `;

    const footer = `
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Close</button>
    `;

    window.UI.Modal('Player Context Switcher', body, footer);
  },

  async setQuickPlayer(id) {
    const input = document.getElementById('switcher-aid-input');
    if (input) input.value = id;
    await this.switchPlayerSubmit();
  },

  async switchPlayerSubmit() {
    const input = document.getElementById('switcher-aid-input');
    if (!input) return;

    const val = parseInt(input.value.trim(), 10);
    if (isNaN(val) || val <= 0) {
      window.UI.Toast('Please enter a valid numeric Account ID', 'warning');
      return;
    }

    const modal = document.getElementById('global-modal-overlay');
    if (modal) modal.remove();

    window.UI.Toast(`Switching context to Account ${val}...`, 'info');
    await window.playerContext.setAccountId(val);
    await window.appRouter.handleRoute();
    window.UI.Toast(`Active context: Account ${val}`, 'success');
  },

  openAuthModal() {
    const currentToken = window.apiClient.getToken();
    const body = `
      <div style="margin-bottom: 12px; color: var(--text-secondary); font-size: 12px; line-height: 1.5;">
        Configure an administrative token to authorize protected operations (banning accounts, currency adjustments, gacha pool overrides):
      </div>

      <div style="margin-bottom: 14px;">
        <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Admin Bearer Token</label>
        <div style="position: relative;">
          <input type="password" id="auth-token-input" class="form-input" placeholder="e.g. secret_admin_key" value="${currentToken}">
          <button type="button" style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 12px;" onclick="
            const inp = document.getElementById('auth-token-input');
            inp.type = inp.type === 'password' ? 'text' : 'password';
          ">Show</button>
        </div>
      </div>

      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px;" onclick="document.getElementById('auth-token-input').value='secret_admin_key'">Preset: secret_admin_key</button>
        <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px;" onclick="document.getElementById('auth-token-input').value=''">Clear</button>
      </div>
    `;

    const actions = `
      <button class="btn btn-primary" onclick="Topbar.saveAuthToken()">Save Token</button>
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Cancel</button>
    `;

    window.UI.Modal('Admin Authentication', body, actions);
  },

  saveAuthToken() {
    const input = document.getElementById('auth-token-input');
    if (input) {
      const val = input.value.trim();
      window.apiClient.setToken(val);
      const modal = document.getElementById('global-modal-overlay');
      if (modal) modal.remove();
      window.UI.Toast(val ? 'Admin token saved' : 'Admin token cleared (Permissive Mode)', 'success');
    }
  }
};

window.Topbar = Topbar;
