/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Player Fleet Directory
 * Route: #/players/directory
 * Domain: 02 Player Management
 *
 * Production Implementation: Apple macOS / iPadOS Dark Glassmorphism
 * Zero Emojis • Symmetrical Grid • Server-Side Pagination • Debounced Search • Context Synchronization
 */

window.Modules = window.Modules || {};

(function () {
    'use strict';

    const directoryState = {
      searchQuery: '',
      statusFilter: 'all', // all | active | banned
      sortBy: 'account_id_asc', // account_id_asc | account_id_desc | nickname_asc | level_desc | diamonds_desc | gold_desc
      currentPage: 1,
      pageSize: 15,
      cachedPlayers: [],
      totalCount: 0,
      onlineCount: 0,
      bannedCount: 0,
      isLoading: false,
    backendRouteLive: false,
      canvas: null
    };

    /**
     * Escape HTML entities to prevent injection
     */
    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

  /**
   * Fetch directory data with server-side pagination & filter fallback
   */
  async function loadDirectoryData(forceRefresh = false) {
  directoryState.isLoading = true;

  let sortByField = 'account_id';
  let sortOrder = 'asc';
  if (directoryState.sortBy === 'account_id_desc') { sortByField = 'account_id'; sortOrder = 'desc'; }
  else if (directoryState.sortBy === 'account_id_asc') { sortByField = 'account_id'; sortOrder = 'asc'; }
  else if (directoryState.sortBy === 'nickname_asc') { sortByField = 'nickname'; sortOrder = 'asc'; }
  else if (directoryState.sortBy === 'level_desc') { sortByField = 'level'; sortOrder = 'desc'; }
  else if (directoryState.sortBy === 'diamonds_desc') { sortByField = 'diamonds'; sortOrder = 'desc'; }
  else if (directoryState.sortBy === 'gold_desc') { sortByField = 'gold'; sortOrder = 'desc'; }

  // 1. Attempt admin paginated endpoint
  try {
    const queryParams = {
      search: directoryState.searchQuery,
      page: directoryState.currentPage,
      limit: directoryState.pageSize,
      sort: sortByField,
      order: sortOrder
    };

    if (directoryState.statusFilter === 'banned') {
      queryParams.is_banned = '1';
    } else if (directoryState.statusFilter === 'active') {
      queryParams.is_banned = '0';
    }

    const adminRes = await window.apiClient.get('/api/admin/players', queryParams);

    if (adminRes.ok && adminRes.data && (adminRes.data.players || Array.isArray(adminRes.data))) {
      directoryState.backendRouteLive = true;
      const players = adminRes.data.players || adminRes.data;
      directoryState.cachedPlayers = players;
      directoryState.totalCount = adminRes.data.total !== undefined ? adminRes.data.total : players.length;

      // Calculate counts
      directoryState.onlineCount = players.filter(p => p.is_online || p.online_status === 1).length;
      directoryState.bannedCount = players.filter(p => p.is_banned).length;
      directoryState.isLoading = false;
      return;
    }
  } catch (e) {
    // Admin route query fallback
  }

  // 2. Seamless Fallback: Query dashboard state
  try {
    directoryState.backendRouteLive = false;
    const currentAid = window.playerContext.getSelectedAccountId();
    const stateRes = await window.apiClient.get('/api/dashboard/state', { account_id: currentAid });

    let allPlayers = [];
    if (stateRes.ok && stateRes.data && stateRes.data.all_players) {
      allPlayers = stateRes.data.all_players;
    } else {
      const cur = window.playerContext.getCurrentPlayer();
      if (cur && cur.profile) allPlayers = [cur.profile];
    }

    // Compute total metrics across full dataset
    directoryState.onlineCount = allPlayers.filter(p => p.is_online || p.online_status === 1).length;
    directoryState.bannedCount = allPlayers.filter(p => p.is_banned).length;

    // Apply search
    let filtered = allPlayers;
    const query = (directoryState.searchQuery || '').trim().toLowerCase();
    if (query) {
      filtered = filtered.filter(p => {
        const aid = String(p.account_id || '');
        const nick = String(p.nickname || '').toLowerCase();
        return aid.includes(query) || nick.includes(query);
      });
    }

    // Apply status filter
    if (directoryState.statusFilter === 'active') {
      filtered = filtered.filter(p => !p.is_banned);
    } else if (directoryState.statusFilter === 'banned') {
      filtered = filtered.filter(p => p.is_banned);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (directoryState.sortBy) {
        case 'account_id_desc':
          return (b.account_id || 0) - (a.account_id || 0);
        case 'account_id_asc':
          return (a.account_id || 0) - (b.account_id || 0);
        case 'nickname_asc':
          return String(a.nickname || '').localeCompare(String(b.nickname || ''));
        case 'level_desc':
          return (b.level || 0) - (a.level || 0);
        case 'diamonds_desc':
          return (b.diamonds || b.gems || 0) - (a.diamonds || a.gems || 0);
        case 'gold_desc':
          return (b.gold || b.coins || 0) - (a.gold || a.coins || 0);
        default:
          return (a.account_id || 0) - (b.account_id || 0);
      }
    });

    directoryState.totalCount = filtered.length;

    // Slicing
    const start = (directoryState.currentPage - 1) * directoryState.pageSize;
    directoryState.cachedPlayers = filtered.slice(start, start + directoryState.pageSize);
  } catch (err) {
    console.error('Directory fetch error:', err);
    directoryState.cachedPlayers = [];
    directoryState.totalCount = 0;
  } finally {
    directoryState.isLoading = false;
  }
}

/**
 * Main Module Mount Function
 */
window.Modules.PlayersDirectory = async function (canvas) {
  directoryState.canvas = canvas;
  canvas.innerHTML = window.UI.Loading('Synchronizing player registry telemetry...');

  await loadDirectoryData();
  renderDirectoryView(canvas);

    // Listen to playerContext changes for reactive UI synchronization
    if (window.playerContext && typeof window.playerContext.onPlayerChange === 'function') {
      window.playerContext.onPlayerChange(() => {
        if (directoryState.canvas && window.location.hash.includes('directory')) {
          renderDirectoryView(directoryState.canvas);
        }
      });
    }
};

/**
 * Render the Directory view with macOS Glass styling
 */
function renderDirectoryView(canvas) {
  const currentActiveId = window.playerContext.getSelectedAccountId();
  const totalPages = Math.max(1, Math.ceil(directoryState.totalCount / directoryState.pageSize));
  if (directoryState.currentPage > totalPages) {
    directoryState.currentPage = totalPages;
  }

  const curPlayer = window.playerContext.getCurrentPlayer() || {};
  const curNick = (curPlayer.profile && curPlayer.profile.nickname) || 'Target Player';

  // 1. Page Header Actions
  const headerActionsHtml = `
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.04); padding: 3px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border-default);">
          <span style="font-size: 11px; color: var(--text-tertiary);">Direct Switch:</span>
          <input type="number" id="quick-aid-direct-input" class="form-input" style="padding: 2px 6px; font-size: 11px; width: 85px; height: 24px; background: transparent; border: 1px solid var(--border-subtle);" placeholder="Account ID" value="${currentActiveId}">
          <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 11px; height: 24px;" onclick="window.selectAndSetContextPlayer(document.getElementById('quick-aid-direct-input').value)">Switch</button>
        </div>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px; height: 30px;" onclick="window.refreshDirectoryView()" title="Refresh telemetry">
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('refresh', 13)} Refresh
          </span>
        </button>
        <button class="btn btn-primary" style="padding: 4px 12px; font-size: 11px; height: 30px;" onclick="window.location.hash='#/players/account'">
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('plus', 13)} Provision Account
          </span>
        </button>
      </div>
    `;

  // 2. Exactly 4 Compact Metrics (.grid-4)
  const metricCardsHtml = `
      <div class="grid-4" style="margin-bottom: var(--space-md);">
        ${window.UI.StatCard(
    'Total Accounts',
    directoryState.totalCount.toLocaleString(),
    directoryState.backendRouteLive ? 'Persistent in india_v1.db' : 'Synced from Server State',
    window.UI.Icon('users', 16, '', 'var(--accent-cyan)'),
    'cyan'
  )}
        ${window.UI.StatCard(
    'Active Fleet Context',
    `Account ${currentActiveId}`,
    escapeHtml(curNick),
    window.UI.Icon('userCheck', 16, '', 'var(--accent-amber)'),
    'amber'
  )}
        ${window.UI.StatCard(
    'Online Accounts',
    directoryState.onlineCount.toLocaleString(),
    'Lobby & Combat Sockets',
    window.UI.Icon('activity', 16, '', 'var(--accent-emerald)'),
    'emerald'
  )}
        ${window.UI.StatCard(
    'Sanctioned / Banned',
    directoryState.bannedCount.toLocaleString(),
    'Access Suspended',
    window.UI.Icon('ban', 16, '', 'var(--accent-rose)'),
    'rose'
  )}
      </div>
    `;

  // 3. Search, Filter & Controls Toolbar
  const filterToolbarHtml = `
      <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; margin-bottom: 14px; background: rgba(15, 23, 42, 0.45); padding: 10px 14px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
        <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; flex: 1; min-width: 280px;">
          <div style="position: relative; display: inline-flex; align-items: center;">
            <input
              type="text"
              id="player-search-input"
              class="form-input"
              placeholder="Search Nickname or ID..."
              value="${escapeHtml(directoryState.searchQuery)}"
              style="width: 240px; height: 30px; font-size: 11.5px; padding-left: 28px;"
              onkeydown="if (event.key === 'Enter') window.onDirectorySearch();"
            >
            <span style="position: absolute; left: 8px; pointer-events: none; opacity: 0.5;">
              ${window.UI.Icon('search', 13)}
            </span>
          </div>

          <button class="btn btn-secondary" style="height: 30px; padding: 2px 10px; font-size: 11px;" onclick="window.onDirectorySearch()">
            Search
          </button>

          ${directoryState.searchQuery ? `
            <button class="btn btn-secondary" style="height: 30px; padding: 2px 8px; font-size: 11px;" onclick="window.onClearDirectorySearch()" title="Clear search">
              ${window.UI.Icon('x', 12)}
            </button>
          ` : ''}

          <!-- Status Filter -->
          <select id="player-status-select" class="form-select" style="min-width: 155px; height: 30px; padding: 2px 24px 2px 8px; font-size: 11.5px;" onchange="window.onDirectoryFilterChange()">
            <option value="all" ${directoryState.statusFilter === 'all' ? 'selected' : ''}>Status: All Accounts</option>
            <option value="active" ${directoryState.statusFilter === 'active' ? 'selected' : ''}>Status: Active Only</option>
            <option value="banned" ${directoryState.statusFilter === 'banned' ? 'selected' : ''}>Status: Banned Only</option>
          </select>

          <!-- Sort Filter -->
          <select id="player-sort-select" class="form-select" style="min-width: 175px; height: 30px; padding: 2px 24px 2px 8px; font-size: 11.5px;" onchange="window.onDirectorySortChange()">
            <option value="account_id_asc" ${directoryState.sortBy === 'account_id_asc' ? 'selected' : ''}>Sort: Account ID (Asc)</option>
            <option value="account_id_desc" ${directoryState.sortBy === 'account_id_desc' ? 'selected' : ''}>Sort: Account ID (Desc)</option>
            <option value="nickname_asc" ${directoryState.sortBy === 'nickname_asc' ? 'selected' : ''}>Sort: Nickname (A-Z)</option>
            <option value="level_desc" ${directoryState.sortBy === 'level_desc' ? 'selected' : ''}>Sort: Level (Highest)</option>
            <option value="diamonds_desc" ${directoryState.sortBy === 'diamonds_desc' ? 'selected' : ''}>Sort: Diamonds (Highest)</option>
            <option value="gold_desc" ${directoryState.sortBy === 'gold_desc' ? 'selected' : ''}>Sort: Gold (Highest)</option>
          </select>
        </div>

        <div style="display: flex; gap: 8px; align-items: center;">
          <span style="font-size: 11px; color: var(--text-tertiary);">Show:</span>
          <select class="form-select" style="width: auto; height: 30px; padding: 2px 8px; font-size: 11.5px;" onchange="window.changeDirectoryPageSize(this.value)">
            <option value="15" ${directoryState.pageSize === 15 ? 'selected' : ''}>15</option>
            <option value="30" ${directoryState.pageSize === 30 ? 'selected' : ''}>30</option>
            <option value="50" ${directoryState.pageSize === 50 ? 'selected' : ''}>50</option>
            <option value="100" ${directoryState.pageSize === 100 ? 'selected' : ''}>100</option>
          </select>
        </div>
      </div>
    `;

  // 4. Player Table Rows
  const rowsHtml = directoryState.cachedPlayers.map(player => {
    const aid = player.account_id;
    const isActive = aid === currentActiveId;
    const isBanned = Boolean(player.is_banned);
    const isOnline = Boolean(player.is_online || player.online_status === 1);
    const activeWallet = (isActive && curPlayer && curPlayer.wallet) ? curPlayer.wallet : {};
    const diamonds = player.diamonds !== undefined ? player.diamonds : (player.gems !== undefined ? player.gems : (activeWallet.gems || activeWallet.diamonds || 0));
    const gold = player.gold !== undefined ? player.gold : (player.coins !== undefined ? player.coins : (activeWallet.coins || activeWallet.gold || 0));
    const level = player.level || 1;
    const rank = player.rank || 0;
    const nickname = player.nickname || 'Unknown Player';
    const region = player.region || 'IND';

    return `
        <tr style="${isActive ? 'background: rgba(56, 189, 248, 0.08); border-left: 3px solid var(--accent-cyan);' : ''}">
          <td style="text-align: center; width: 36px; padding: 8px 4px;">
            ${isActive ? window.UI.StatusDot('active', true) : window.UI.StatusDot('inactive')}
          </td>
          <td style="width: 100px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <code style="font-family: var(--font-mono); font-weight: 700; color: ${isActive ? 'var(--accent-cyan)' : 'var(--text-primary)'}; font-size: 12px;">${aid}</code>
              <button class="btn btn-secondary" style="padding: 1px 5px; font-size: 10px; border-radius: 4px; height: 20px;" onclick="navigator.clipboard.writeText('${aid}'); window.UI.Toast('Copied ID ${aid}', 'info');" title="Copy Account ID">
                ${window.UI.Icon('copy', 11)}
              </button>
            </div>
          </td>
          <td>
            <div style="display: flex; flex-direction: column;">
              <span style="font-weight: 600; color: #fff; font-size: 12.5px;">${escapeHtml(nickname)}</span>
              <span style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);">Region: ${escapeHtml(region)}</span>
            </div>
          </td>
          <td>
            <div style="display: flex; align-items: center; gap: 6px;">
              ${window.UI.Badge('Lv.' + level, 'neutral')}
              ${rank > 0 ? `<span style="font-size: 11px; color: var(--text-secondary); font-family: var(--font-mono);">${player.ranking_points || rank} RP</span>` : ''}
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
              ${window.UI.CurrencyChip('diamond', diamonds)}
              ${window.UI.CurrencyChip('gold', gold)}
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              ${isBanned ? window.UI.Badge('BANNED', 'rose') : window.UI.Badge('ACTIVE', 'emerald')}
              ${isOnline ? window.UI.Badge('ONLINE', 'cyan') : ''}
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 6px; align-items: center;">
              ${!isActive ? `
                <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px; height: 26px;" onclick="window.selectAndSetContextPlayer(${aid})">
                  Select
                </button>
              ` : `
                <span class="badge badge-cyan" style="font-size: 10px; padding: 3px 8px;">Active</span>
              `}
              <button class="btn btn-primary" style="padding: 3px 10px; font-size: 11px; height: 26px;" onclick="window.inspectPlayerAccount(${aid})">
                Inspect
              </button>
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px; height: 26px;" onclick="window.openPlayerQuickMenu(${aid}, '${escapeHtml(nickname)}')" title="More actions">
                ${window.UI.Icon('moreHorizontal', 12)}
              </button>
            </div>
          </td>
        </tr>
      `;
  }).join('');

    // 5. Pagination Bar
    const paginationHtml = `
    < div style = "display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); flex-wrap: wrap; gap: 10px;" >
        <div style="font-size: 12px; color: var(--text-tertiary);">
          Showing <b style="color: #fff;">${directoryState.cachedPlayers.length}</b> of <b style="color: #fff;">${directoryState.totalCount}</b> accounts (Page ${directoryState.currentPage} of ${totalPages})
        </div>

        <div style="display: flex; gap: 6px; align-items: center;">
          <button
            class="btn btn-secondary"
            style="padding: 3px 10px; font-size: 11px; height: 28px;"
            ${directoryState.currentPage <= 1 ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : ''}
            onclick="window.changeDirectoryPage(${directoryState.currentPage - 1})"
          >
            Previous
          </button>

          <span style="font-size: 11.5px; color: var(--text-secondary); padding: 0 6px;">
            Page <b style="color: #fff;">${directoryState.currentPage}</b> of ${totalPages}
          </span>

          <button
            class="btn btn-secondary"
            style="padding: 3px 10px; font-size: 11px; height: 28px;"
            ${directoryState.currentPage >= totalPages ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : ''}
            onclick="window.changeDirectoryPage(${directoryState.currentPage + 1})"
          >
            Next
          </button>
        </div>
      </div >
    `;

    // 6. Complete Card Assembly
    const directoryCardHtml = window.UI.Card(
      'Account Fleet Registry',
      'Manage global context, inspect individual dossiers, and monitor authentication status',
      `${ filterToolbarHtml }${
    window.UI.Table(
      ['', 'Account ID', 'Nickname & Region', 'Level & Rank', 'Currencies', 'Status', 'Actions'],
      rowsHtml,
      directoryState.searchQuery
        ? `No player accounts match search query "${escapeHtml(directoryState.searchQuery)}".`
        : 'No registered player accounts discovered in database.'
    )
  }${ paginationHtml } `
    );

    // 7. Full Page Container Layout
    canvas.innerHTML = `
    < div class="page-container" >
      ${
        window.UI.PageHeader(
          'Player Fleet Directory',
          'Browse, filter, inspect, and provision accounts across the India V1 database',
          headerActionsHtml,
          'users'
        )
  }
        ${ metricCardsHtml }
        ${ directoryCardHtml }
      </div >
    `;
  }

  // --- Global Window Helpers for Directory Interaction ---

  window.selectAndSetContextPlayer = async function (accountId) {
    const aid = parseInt(accountId, 10);
    if (!aid || isNaN(aid)) {
      window.UI.Toast('Invalid Account ID', 'warning');
      return;
    }

    try {
      await window.playerContext.setAccountId(aid);
      window.UI.Toast(`Switched active context to Account ${ aid } `, 'success');
      const canvas = document.getElementById('workspace-canvas');
      if (canvas && window.location.hash.includes('directory')) {
        renderDirectoryView(canvas);
      }
    } catch (e) {
      window.UI.Toast(`Failed to switch account: ${ e.message } `, 'error');
    }
  };

  window.inspectPlayerAccount = async function (accountId) {
    const aid = parseInt(accountId, 10);
    if (!aid || isNaN(aid)) return;

    await window.playerContext.setAccountId(aid);
    window.location.hash = '#/players/inspector';
  };

  window.openPlayerQuickMenu = function (accountId, nickname) {
    const modalBody = `
    < div style = "font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;" >
  Account: <b style="color: #fff;">${escapeHtml(nickname)}</b> (<code>${accountId}</code>)
      </div >
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <button class="btn btn-secondary" style="justify-content: flex-start; text-align: left; padding: 8px 12px;" onclick="window.selectAndSetContextPlayer(${accountId}); window.UI.CloseModal();">
            <span style="display: inline-flex; align-items: center; gap: 8px;">
              ${window.UI.Icon('userCheck', 14, '', 'var(--accent-amber)')} Set as Active Global Context
            </span>
          </button>
            <button class="btn btn-secondary" style="justify-content: flex-start; text-align: left; padding: 8px 12px;" onclick="window.inspectPlayerAccount(${accountId}); window.UI.CloseModal();">
              <span style="display: inline-flex; align-items: center; gap: 8px;">
                ${window.UI.Icon('user', 14, '', 'var(--accent-cyan)')} Inspect Full Dossier & Profile
              </span>
            </button>
              <button class="btn btn-secondary" style="justify-content: flex-start; text-align: left; padding: 8px 12px;" onclick="window.selectAndSetContextPlayer(${accountId}).then(() => { window.location.hash='#/inventory/manager'; window.UI.CloseModal(); });">
                <span style="display: inline-flex; align-items: center; gap: 8px;">
                  ${window.UI.Icon('package', 14, '', 'var(--accent-emerald)')} View Inventory Vault
                </span>
              </button>
                <button class="btn btn-secondary" style="justify-content: flex-start; text-align: left; padding: 8px 12px;" onclick="window.selectAndSetContextPlayer(${accountId}).then(() => { window.location.hash='#/economy/currencies'; window.UI.CloseModal(); });">
                  <span style="display: inline-flex; align-items: center; gap: 8px;">
                    ${window.UI.Icon('coins', 14, '', 'var(--accent-amber)')} Manage Economy & Currencies
                  </span>
                </button>
                  <button class="btn btn-danger" style="justify-content: flex-start; text-align: left; padding: 8px 12px;" onclick="window.selectAndSetContextPlayer(${accountId}).then(() => { window.location.hash='#/players/bans'; window.UI.CloseModal(); });">
                    <span style="display: inline-flex; align-items: center; gap: 8px;">
                      ${window.UI.Icon('ban', 14, '', 'var(--accent-rose)')} Sanctions & Ban Enforcement
                    </span>
                  </button>
                </div>
                `;

                window.UI.Modal(`Account Options: ${accountId}`, modalBody, `
                <button class="btn btn-secondary" onclick="window.UI.CloseModal()">Close</button>
                `);
  };

                window.onDirectorySearch = async function () {
    const input = document.getElementById('player-search-input');
                if (!input) return;
                directoryState.searchQuery = input.value.trim();
                directoryState.currentPage = 1;

                const canvas = document.getElementById('workspace-canvas');
                if (canvas) {
                  canvas.innerHTML = window.UI.Loading('Searching accounts...');
                await loadDirectoryData();
                renderDirectoryView(canvas);
    }
  };

                window.onClearDirectorySearch = async function () {
                  directoryState.searchQuery = '';
                directoryState.currentPage = 1;
                const canvas = document.getElementById('workspace-canvas');
                if (canvas) {
                  canvas.innerHTML = window.UI.Loading('Reloading accounts...');
                await loadDirectoryData();
                renderDirectoryView(canvas);
    }
  };

                window.onDirectoryFilterChange = async function () {
    const sel = document.getElementById('player-status-select');
                if (!sel) return;
                directoryState.statusFilter = sel.value;
                directoryState.currentPage = 1;

                const canvas = document.getElementById('workspace-canvas');
                if (canvas) {
                  canvas.innerHTML = window.UI.Loading('Filtering accounts...');
                await loadDirectoryData();
                renderDirectoryView(canvas);
    }
  };

                window.onDirectorySortChange = async function () {
    const sel = document.getElementById('player-sort-select');
                if (!sel) return;
                directoryState.sortBy = sel.value;

                const canvas = document.getElementById('workspace-canvas');
                if (canvas) {
                  canvas.innerHTML = window.UI.Loading('Sorting accounts...');
                await loadDirectoryData();
                renderDirectoryView(canvas);
    }
  };

                window.changeDirectoryPage = async function (newPage) {
    if (newPage < 1) return;
                directoryState.currentPage = newPage;
                const canvas = document.getElementById('workspace-canvas');
                if (canvas) {
                  await loadDirectoryData();
                renderDirectoryView(canvas);
    }
  };

                window.changeDirectoryPageSize = async function (newSize) {
                  directoryState.pageSize = parseInt(newSize, 10) || 15;
                directoryState.currentPage = 1;
                const canvas = document.getElementById('workspace-canvas');
                if (canvas) {
                  await loadDirectoryData();
                renderDirectoryView(canvas);
    }
  };

                window.refreshDirectoryView = async function () {
    const canvas = document.getElementById('workspace-canvas');
                if (canvas) {
                  canvas.innerHTML = window.UI.Loading('Refreshing player registry...');
                await loadDirectoryData(true);
                renderDirectoryView(canvas);
                window.UI.Toast('Player Directory updated', 'info');
    }
  };

              // Self-register with AppRouter if initialized
              if (window.appRouter) {
                window.appRouter.register('#/players/directory', window.Modules.PlayersDirectory);
  }
})();
