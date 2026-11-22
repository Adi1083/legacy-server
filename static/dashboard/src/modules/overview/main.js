/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Main Command Dashboard (Overview)
 * Route: #/overview/main
 * Domain: 01 Overview & Server Monitoring
 * 
 * Production Implementation: Apple macOS / iPadOS Dark Glassmorphism
 * Zero Emojis • Unified Service Telemetry Strip • Compact 4-Card Metrics • Balanced 50/50 Split View
 */

(function () {
  'use strict';

  // Module internal state
  const state = {
    dashboardState: null,
    requestsData: null,
    loading: false,
    inFlight: false,
    error: null,
    pingMs: 0,
    lastUpdated: null,
    pollTimer: null,
    pollRate: 5000, // 5s default
    canvas: null,
    unsubscribeContext: null
  };

  /**
   * Safe HTML Escaper to prevent XSS in dynamic data injection
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
   * Format Seconds into readable uptime (e.g. "2h 45m 12s")
   */
  function formatUptime(seconds) {
    if (!seconds || isNaN(seconds) || seconds < 0) return '0s';
    const s = Math.floor(seconds);
    const days = Math.floor(s / 86400);
    const hours = Math.floor((s % 86400) / 3600);
    const minutes = Math.floor((s % 3600) / 60);
    const secs = s % 60;

    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0 || days > 0) parts.push(`${hours}h`);
    if (minutes > 0 || hours > 0 || days > 0) parts.push(`${minutes}m`);
    parts.push(`${secs}s`);
    return parts.join(' ');
  }

  /**
   * Format numbers with commas (e.g. 50000 -> 50,000)
   */
  function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return Number(num).toLocaleString();
  }

  /**
   * Format byte sizes into readable units (B, KB, MB, GB)
   */
  function formatBytes(bytes) {
    if (!bytes || isNaN(bytes) || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
  }

  /**
   * Format standard time string (HH:MM:SS)
   */
  function formatTime(date) {
    if (!date) return '—';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  /**
   * Calculate Real Throughput Telemetry from raw request history
   */
  function calculateTelemetry(requests) {
    if (!requests || !Array.isArray(requests) || requests.length === 0) {
      return {
        totalRequests: 0,
        totalBytes: 0,
        avgBytes: 0,
        reqsPerSec: '0.00',
        getMethodCount: 0,
        postMethodCount: 0,
        topEndpoints: []
      };
    }

    let totalBytes = 0;
    let getCount = 0;
    let postCount = 0;
    const pathCounts = {};
    const nowSec = Date.now() / 1000;
    let reqsLast60Sec = 0;

    for (const r of requests) {
      const bytes = r.body_len || 0;
      totalBytes += bytes;

      const method = (r.method || 'GET').toUpperCase();
      if (method === 'GET') getCount++;
      else if (method === 'POST') postCount++;

      const cleanPath = (r.path || '/').split('?')[0];
      pathCounts[cleanPath] = (pathCounts[cleanPath] || 0) + 1;

      if (r.timestamp && (nowSec - r.timestamp) <= 60) {
        reqsLast60Sec++;
      }
    }

    const rps = (reqsLast60Sec / 60).toFixed(2);
    const avgBytes = requests.length > 0 ? Math.round(totalBytes / requests.length) : 0;

    const topEndpoints = Object.entries(pathCounts)
      .map(([path, count]) => ({ path, count, pct: Math.round((count / requests.length) * 100) }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return {
      totalRequests: requests.length,
      totalBytes,
      avgBytes,
      reqsPerSec: rps,
      getMethodCount: getCount,
      postMethodCount: postCount,
      topEndpoints
    };
  }

  /**
   * Fetch Live Telemetry & Server State from Backend
   */
  async function loadData() {
    if (state.inFlight) return;
    state.inFlight = true;

    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const t0 = performance.now();

    try {
      const [stateRes, reqsRes] = await Promise.all([
        window.apiClient.get('/api/dashboard/state', { account_id: aid }),
        window.apiClient.get('/api/dashboard/requests', { limit: 100 })
      ]);

      state.pingMs = Math.round(performance.now() - t0);

      if (stateRes && stateRes.ok && stateRes.data) {
        state.dashboardState = stateRes.data;
        state.error = null;
      } else {
        state.error = (stateRes && stateRes.error) || 'Failed to connect to /api/dashboard/state';
      }

      if (reqsRes && reqsRes.ok && reqsRes.data) {
        state.requestsData = reqsRes.data;
      }

      state.lastUpdated = new Date();
    } catch (err) {
      state.pingMs = Math.round(performance.now() - t0);
      state.error = err.message || 'Network communication failure';
    } finally {
      state.loading = false;
      state.inFlight = false;
    }
  }

  /**
   * Main Render Entry Point for #/overview/main
   */
  async function renderOverviewMain(canvas) {
    state.canvas = canvas;

    // Halt any running polling interval to avoid timer leaks
    stopAutoRefresh();

    // Listen for hashchange to clean up timers when user navigates away
    if (typeof window.removeEventListener === 'function') {
      window.removeEventListener('hashchange', onHashChange);
    }
    if (typeof window.addEventListener === 'function') {
      window.addEventListener('hashchange', onHashChange);
    }

    // Initial loading skeleton if no state is cached
    if (!state.dashboardState) {
      state.loading = true;
      if (window.UI && typeof window.UI.Loading === 'function') {
        canvas.innerHTML = `
          <div class="page-container">
            ${window.UI.Loading('Connecting to IND PROJECT Server Telemetry & State Bus...')}
          </div>
        `;
      }
    }

    await loadData();
    renderContent();
    startAutoRefresh();

    // Subscribe to PlayerContext changes once
    if (window.playerContext && !state.unsubscribeContext) {
      state.unsubscribeContext = window.playerContext.subscribe((newAid) => {
        if (window.location.hash.startsWith('#/overview/main')) {
          loadData().then(() => renderContent());
        }
      });
    }
  }

  /**
   * Clean up on Route Exit
   */
  function onHashChange() {
    if (!window.location.hash.startsWith('#/overview/main')) {
      stopAutoRefresh();
      if (typeof window.removeEventListener === 'function') {
        window.removeEventListener('hashchange', onHashChange);
      }
    }
  }

  /**
   * Start Periodic Telemetry Auto-Refresh
   */
  function startAutoRefresh() {
    stopAutoRefresh();
    if (state.pollRate > 0) {
      state.pollTimer = setInterval(async () => {
        if (!window.location.hash.startsWith('#/overview/main')) {
          stopAutoRefresh();
          return;
        }
        await loadData();
        renderContent();
      }, state.pollRate);
    }
  }

  /**
   * Stop Periodic Auto-Refresh
   */
  function stopAutoRefresh() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  /**
   * Render the complete HTML structure into state.canvas
   */
  function renderContent() {
    if (!state.canvas) return;

    const snap = state.dashboardState || {};
    const serverInfo = snap.server || {};
    const profile = snap.profile || {};
    const wallet = snap.wallet || {};
    const allPlayers = snap.all_players || [];
    const rooms = snap.rooms || [];
    const requests = (state.requestsData && state.requestsData.requests) || [];
    const telemetry = calculateTelemetry(requests);

    const uptimeStr = formatUptime(serverInfo.uptime_sec || 0);
    const curAid = window.playerContext ? window.playerContext.getSelectedAccountId() : (profile.account_id || 10001);
    const totalRequestsCount = serverInfo.request_count || (state.requestsData ? state.requestsData.total : requests.length);
    const onlinePlayersCount = allPlayers.filter(p => p.is_online || p.online_status > 0).length;
    const lastUpdatedStr = formatTime(state.lastUpdated);

    // 1. Page Header Actions Toolbar
    const headerActionsHtml = `
      <div class="toolbar-actions" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <span style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); margin-right: 4px;">
          Updated: <span id="ov-last-updated" style="color: var(--text-secondary);">${lastUpdatedStr}</span>
        </span>

        <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.04); padding: 3px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border-default);">
          <span style="font-size: 11px; color: var(--text-tertiary); display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('clock', 12, '', 'var(--text-tertiary)')} Polling:
          </span>
          <select id="ov-poll-rate" class="form-select" style="padding: 2px 6px; font-size: 11px; width: auto; background: transparent; border: none; color: var(--accent-cyan); cursor: pointer;" onchange="window.OverviewMainModule.setPollRate(this.value)">
            <option value="2000" ${state.pollRate === 2000 ? 'selected' : ''}>2s Fast</option>
            <option value="5000" ${state.pollRate === 5000 ? 'selected' : ''}>5s Normal</option>
            <option value="10000" ${state.pollRate === 10000 ? 'selected' : ''}>10s Relaxed</option>
            <option value="0" ${state.pollRate === 0 ? 'selected' : ''}>Paused</option>
          </select>
        </div>

        <button class="btn btn-secondary" onclick="window.OverviewMainModule.manualRefresh()" title="Refresh telemetry state">
          ${window.UI.Icon('refresh', 13)}
          <span>Refresh</span>
        </button>

        <button class="btn btn-primary" onclick="window.location.hash='#/overview/monitoring'" title="Inspect live server monitoring metrics">
          ${window.UI.Icon('activity', 13)}
          <span>Monitoring</span>
        </button>
      </div>
    `;

    // Render PageHeader component with clean dashboard icon
    const pageHeaderHtml = window.UI.PageHeader(
      'Overview',
      'IND PROJECT Server Environment & Operational Overview • IND PROJECT Daemon Telemetry',
      headerActionsHtml,
      'dashboard'
    );

    // 2. Alert Banner (if error present)
    const alertBannerHtml = state.error ? `
      <div class="glass-card" style="border-left: 3px solid var(--accent-rose); background: rgba(244, 63, 94, 0.08); margin-bottom: var(--space-md); padding: 12px 16px;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
          <div style="display: flex; align-items: center; gap: 10px;">
            ${window.UI.Icon('alertTriangle', 18, '', 'var(--accent-rose)')}
            <div>
              <div style="color: var(--accent-rose); font-weight: 600; font-size: 12.5px;">Backend Communication Warning</div>
              <div style="color: var(--text-secondary); font-size: 11.5px;">${escapeHtml(state.error)}</div>
            </div>
          </div>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="window.OverviewMainModule.manualRefresh()">
            Retry Connection
          </button>
        </div>
      </div>
    ` : '';

    // 3. Compact Unified Service Telemetry Strip (Replacing the 3 oversized cards)
    const serviceStripHtml = `
      <div class="glass-card" style="padding: 10px 16px; margin-bottom: var(--space-md); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
        <!-- HTTP Gateway -->
        <div style="display: flex; align-items: center; gap: 8px;">
          ${window.UI.StatusDot(state.error ? 'danger' : 'active')}
          <span style="font-size: 12px; font-weight: 600; color: #fff;">HTTP Gateway</span>
          <span class="badge badge-emerald" style="font-family: var(--font-mono); font-size: 10px; padding: 2px 6px;">PORT 8080</span>
          ${window.UI.Badge(state.error ? 'OFFLINE' : 'ONLINE', state.error ? 'rose' : 'emerald')}
          <span style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); margin-left: 4px;">
            HTTP response time: <b style="color: var(--accent-emerald);">${state.pingMs} ms</b>
          </span>
        </div>

        <div style="width: 1px; height: 18px; background: var(--border-subtle); display: none; @media(min-width: 900px){ display: block; }"></div>

        <!-- TCP Lobby Gateway -->
        <div style="display: flex; align-items: center; gap: 8px;">
          ${window.UI.StatusDot('warning')}
          <span style="font-size: 12px; font-weight: 600; color: #fff;">TCP Lobby</span>
          <span class="badge badge-cyan" style="font-family: var(--font-mono); font-size: 10px; padding: 2px 6px;">PORT 8081</span>
          ${window.UI.Badge('CONFIGURED', 'neutral')}
          <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 4px;">
            ProtoWire v1.39 • Daemon Pool
          </span>
        </div>

        <div style="width: 1px; height: 18px; background: var(--border-subtle); display: none; @media(min-width: 900px){ display: block; }"></div>

        <!-- UDP Combat Engine -->
        <div style="display: flex; align-items: center; gap: 8px;">
          ${window.UI.StatusDot('warning')}
          <span style="font-size: 12px; font-weight: 600; color: #fff;">UDP Combat</span>
          <span class="badge badge-indigo" style="font-family: var(--font-mono); font-size: 10px; padding: 2px 6px;">PORT 39800</span>
          ${window.UI.Badge('CONFIGURED', 'neutral')}
          <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 4px;">
            30 Hz Tick • <b style="color: #fff;">${rooms.length}</b> Active Rooms
          </span>
        </div>
      </div>
    `;

    // 4. Exactly 4 Compact Operational Metrics (.grid-4)
    const statCardsHtml = `
      <div class="grid-4" style="margin-bottom: var(--space-md);">
        ${window.UI.StatCard(
          'Registered Accounts',
          formatNumber(allPlayers.length || 100),
          `<div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--accent-emerald);">● ${onlinePlayersCount} Online</span>
            <span style="color: var(--accent-cyan); cursor: pointer;" onclick="window.location.hash='#/players/directory'">Directory →</span>
          </div>`,
          window.UI.Icon('users', 16, '', 'var(--accent-cyan)'),
          'cyan'
        )}

        ${window.UI.StatCard(
          'Game Assets in Vault',
          formatNumber(snap.unlocked_items_count || 4525),
          `<div style="display: flex; justify-content: space-between; align-items: center;">
            <span>${snap.characters_count || 4} Heroes • ${snap.pets_count || 3} Pets</span>
            <span style="color: var(--accent-cyan); cursor: pointer;" onclick="window.location.hash='#/inventory/manager'">Vault →</span>
          </div>`,
          window.UI.Icon('package', 16, '', 'var(--accent-emerald)'),
          'emerald'
        )}

        ${window.UI.StatCard(
          'Request Throughput',
          `${telemetry.reqsPerSec} <span style="font-size: 12px; font-weight: 500; color: var(--text-tertiary);">req/s</span>`,
          `<div style="display: flex; justify-content: space-between; align-items: center;">
            <span>Volume: ${formatBytes(telemetry.totalBytes)}</span>
            <span style="color: var(--accent-cyan); cursor: pointer;" onclick="window.location.hash='#/logs/api'">Logs →</span>
          </div>`,
          window.UI.Icon('zap', 16, '', 'var(--accent-amber)'),
          'amber'
        )}

        ${window.UI.StatCard(
          'Gateway Uptime & Activity',
          `${uptimeStr}`,
          `<div style="display: flex; justify-content: space-between; align-items: center;">
            <span>${formatNumber(totalRequestsCount)} Total Requests</span>
            <span style="color: var(--accent-cyan); cursor: pointer;" onclick="window.location.hash='#/overview/monitoring'">Status →</span>
          </div>`,
          window.UI.Icon('server', 16, '', 'var(--accent-violet)'),
          'violet'
        )}
      </div>
    `;

    // 5. Balanced 50/50 Split View (Left: Request Stream Preview, Right: Active Player Dossier)
    const requestRowsHtml = requests.slice(0, 6).map(r => `
      <tr>
        <td style="font-family: var(--font-mono); color: var(--accent-cyan); width: 85px; white-space: nowrap;">${escapeHtml(r.time || '—')}</td>
        <td style="width: 70px;">${window.UI.Badge(escapeHtml(r.method || 'GET'), (r.method || 'GET') === 'GET' ? 'cyan' : 'emerald')}</td>
        <td style="font-family: var(--font-mono); font-size: 11px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(r.path || '/')}">
          ${escapeHtml(r.path || '/')}
        </td>
        <td style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 11px; width: 80px; white-space: nowrap;">
          ${escapeHtml(r.client || '::1')}
        </td>
        <td style="font-family: var(--font-mono); color: var(--text-secondary); font-size: 11px; width: 60px; text-align: right; white-space: nowrap;">
          ${formatBytes(r.body_len || 0)}
        </td>
      </tr>
    `).join('');

    const leftTableContent = requests.length === 0
      ? window.UI.EmptyState('Telemetry Buffer Cleared', 'No gateway requests currently buffered. Incoming traffic will display automatically.', window.UI.Icon('inbox', 32, '', 'var(--text-tertiary)'))
      : window.UI.Table(['Time', 'Method', 'Endpoint', 'Client', 'Size'], requestRowsHtml);

    const leftPaneHtml = window.UI.Card({
      title: 'Live Request Stream Preview',
      subtitle: 'Recent HTTP gateway traffic recorded in server request history',
      actions: `
        <div style="display: flex; gap: 8px; align-items: center;">
          <button class="btn btn-secondary btn-sm" onclick="window.OverviewMainModule.confirmClearRequests()" title="Clear telemetry buffer">
            ${window.UI.Icon('trash', 12)}
            <span>Clear</span>
          </button>
          <button class="btn btn-secondary btn-sm" onclick="window.location.hash='#/logs/api'" title="Open live API monitor">
            <span>Inspect All →</span>
          </button>
        </div>
      `,
      content: `
        ${leftTableContent}
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 11px; color: var(--text-tertiary);">
          <span>Buffered: <b style="color: #fff;">${requests.length}</b> records</span>
          <span>GET/POST Ratio: <b style="color: var(--accent-cyan);">${telemetry.getMethodCount}</b> / <b style="color: var(--accent-emerald);">${telemetry.postMethodCount}</b></span>
        </div>
      `
    });

    const diamonds = wallet.gems !== undefined ? wallet.gems : (profile.diamonds || 0);
    const coins = wallet.coins !== undefined ? wallet.coins : (profile.gold || 0);
    const badges = profile.badge_cnt || 0;

    const rightPaneHtml = window.UI.Card({
      title: `Active Player Context: ${escapeHtml(profile.nickname || 'Unknown')}`,
      subtitle: `Account ID: ${escapeHtml(curAid)} • Region: ${escapeHtml(profile.region || 'IND')}`,
      actions: `
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary btn-sm" onclick="window.location.hash='#/players/inspector'">
            Dossier →
          </button>
          <button class="btn btn-secondary btn-sm" onclick="window.location.hash='#/economy/currencies'">
            Currencies →
          </button>
        </div>
      `,
      content: `
        <!-- Luxury Currency Chips -->
        <div style="display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap;">
          ${window.UI.CurrencyChip('diamond', diamonds)}
          ${window.UI.CurrencyChip('gold', coins)}
          ${window.UI.CurrencyChip('badge', badges)}
        </div>

        <!-- Clean Player Details Grid -->
        <div style="background: rgba(10, 16, 28, 0.4); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-default); font-size: 12px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <span style="color: var(--text-tertiary);">Nickname:</span>
              <b style="color: #fff; margin-left: 6px;">${escapeHtml(profile.nickname || 'Unknown')}</b>
            </div>
            <div>
              <span style="color: var(--text-tertiary);">Level:</span>
              <b style="color: #fff; margin-left: 6px;">${profile.level || 1}</b>
              <span style="color: var(--text-tertiary); font-size: 11px;">(${formatNumber(profile.exp || 0)} EXP)</span>
            </div>
            <div>
              <span style="color: var(--text-tertiary);">Rank Rating:</span>
              <b style="color: var(--accent-amber); margin-left: 6px;">${formatNumber(profile.ranking_points || profile.rank || 0)} RP</b>
            </div>
            <div>
              <span style="color: var(--text-tertiary);">Elite Pass:</span>
              <span style="margin-left: 6px;">${profile.has_elite_pass ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('INACTIVE', 'neutral')}</span>
            </div>
            <div>
              <span style="color: var(--text-tertiary);">Account Status:</span>
              <span style="margin-left: 6px;">${profile.is_banned ? window.UI.Badge('BANNED', 'rose') : window.UI.Badge('ACTIVE', 'emerald')}</span>
            </div>
            <div>
              <span style="color: var(--text-tertiary);">Online Status:</span>
              <span style="margin-left: 6px;">${profile.is_online ? window.UI.Badge('ONLINE', 'emerald') : window.UI.Badge('OFFLINE', 'neutral')}</span>
            </div>
            <div style="grid-column: span 2; border-top: 1px solid var(--border-subtle); padding-top: 8px;">
              <span style="color: var(--text-tertiary);">Personal Signature:</span>
              <i style="color: var(--text-secondary); margin-left: 6px;">"${escapeHtml(profile.signature || 'None')}"</i>
            </div>
          </div>
        </div>
      `
    });

    const splitViewHtml = `
      <div class="split-view" style="margin-bottom: 0;">
        <div class="split-pane-left" style="flex: 1 1 0; min-width: 320px;">
          ${leftPaneHtml}
        </div>
        <div class="split-pane-right" style="flex: 1 1 0; min-width: 320px;">
          ${rightPaneHtml}
        </div>
      </div>
    `;

    // Assembly into .page-container with zero bottom shortcuts card
    state.canvas.innerHTML = `
      <div class="page-container" style="padding-bottom: var(--space-md);">
        ${pageHeaderHtml}
        ${alertBannerHtml}
        ${serviceStripHtml}
        ${statCardsHtml}
        ${splitViewHtml}
      </div>
    `;
  }

  // --- Public Interface ---
  const OverviewMain = {
    render: renderOverviewMain,

    manualRefresh: async function () {
      await loadData();
      renderContent();
      if (window.UI && typeof window.UI.Toast === 'function') {
        window.UI.Toast('Overview telemetry refreshed', 'success');
      }
    },

    setPollRate: function (rate) {
      state.pollRate = parseInt(rate, 10) || 0;
      startAutoRefresh();
      if (window.UI && typeof window.UI.Toast === 'function') {
        window.UI.Toast(state.pollRate > 0 ? `Polling set to ${state.pollRate / 1000}s` : 'Polling paused', 'info');
      }
    },

    confirmClearRequests: function () {
      if (window.UI && typeof window.UI.Confirm === 'function') {
        window.UI.Confirm(
          'Clear Telemetry Buffer?',
          'Are you sure you want to empty the recorded HTTP request history? This will clear the live stream preview.',
          async () => {
            try {
              const res = await window.apiClient.post('/api/dashboard/requests/clear', {});
              if (res && res.ok) {
                if (state.requestsData) state.requestsData.requests = [];
                await loadData();
                renderContent();
                if (window.UI && typeof window.UI.Toast === 'function') {
                  window.UI.Toast('Request telemetry buffer cleared', 'success');
                }
              }
            } catch (e) {
              if (window.UI && typeof window.UI.Toast === 'function') {
                window.UI.Toast('Failed to clear buffer: ' + e.message, 'danger');
              }
            }
          }
        );
      }
    }
  };

  // Global module registrations
  window.OverviewMainModule = OverviewMain;
  window.Modules = window.Modules || {};
  window.Modules.OverviewMain = renderOverviewMain;

  // SPA Hash Router Registration
  if (window.appRouter && typeof window.appRouter.register === 'function') {
    window.appRouter.register('#/overview/main', renderOverviewMain);
  }
})();
