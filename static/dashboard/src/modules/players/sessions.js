/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Live Sessions & Network Telemetry
 * Route: #/players/sessions
 * Domain: 02 Player Management
 *
 * Production Implementation: Apple macOS / iPadOS Dark Glassmorphism
 * Zero Emojis • Live Sockets & Daemon Telemetry • Real-time HTTP Wire Stream • Context Synchronization
 */

window.Modules = window.Modules || {};

(function () {
  'use strict';

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatBytes(bytes) {
    if (!bytes || isNaN(bytes) || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
  }

  window.Modules.PlayersSessions = async function (canvas) {
    canvas.innerHTML = window.UI.Loading('Scanning active socket descriptors and telemetry...');

    // 1. Fetch dashboard state for online players & server info
    let allPlayers = [];
    let onlinePlayers = [];
    try {
        const stateRes = await window.apiClient.get('/api/dashboard/state');
        if (stateRes.ok && stateRes.data) {
          allPlayers = stateRes.data.all_players || [];
          onlinePlayers = allPlayers.filter(p => p.is_online || p.online_status === 1);
        }
    } catch (e) { }

    // 2. Fetch recent request telemetry
    let recentRequests = [];
    try {
      const reqRes = await window.apiClient.get('/api/dashboard/requests', { limit: 30 });
      if (reqRes.ok && reqRes.data) {
        recentRequests = reqRes.data.requests || (Array.isArray(reqRes.data) ? reqRes.data : []);
      }
    } catch (e) { }

    renderSessionsView(canvas, onlinePlayers, recentRequests);
  };

  function renderSessionsView(canvas, onlinePlayers, recentRequests) {
    const aid = window.playerContext.getSelectedAccountId();

    // 1. Header Actions
    const headerActionsHtml = `
      < div style = "display: flex; gap: 8px; align-items: center;" >
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px; height: 30px;" onclick="window.Modules.PlayersSessions(document.getElementById('workspace-canvas'))">
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('refresh', 13)} Refresh Telemetry
          </span>
        </button>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px; height: 30px;" onclick="window.apiClient.post('/api/dashboard/requests/clear').then(() => window.Modules.PlayersSessions(document.getElementById('workspace-canvas')))">
          Clear Log
        </button>
        <button class="btn btn-secondary" style="padding: 4px 12px; font-size: 11px; height: 30px;" onclick="window.location.hash='#/players/directory'">
          Directory
        </button>
      </div >
      `;

    // 2. Exactly 4 Compact Metrics (.grid-4)
    const metricCardsHtml = `
      <div class="grid-4" style="margin-bottom: var(--space-md);">
        ${window.UI.StatCard(
      'HTTP REST Gateway',
      'PORT 8080',
      'Verified Live / Barbosa REST',
      window.UI.Icon('server', 16, '', 'var(--accent-emerald)'),
      'emerald'
    )}
        ${window.UI.StatCard(
      'TCP Lobby Gateway',
      'PORT 8081',
      'Configured / Daemon Sockets',
      window.UI.Icon('terminal', 16, '', 'var(--accent-cyan)'),
      'cyan'
    )}
        ${window.UI.StatCard(
      'UDP Combat Engine',
      'PORT 39800',
      '30 Hz Dedicated Tick',
      window.UI.Icon('crosshair', 16, '', 'var(--accent-indigo)'),
      'indigo'
    )}
        ${window.UI.StatCard(
      'Online Fleet Accounts',
      onlinePlayers.length.toString(),
      'Active Authenticated Sessions',
      window.UI.Icon('users', 16, '', 'var(--accent-amber)'),
      'amber'
    )}
      </div>
    `;

    // 3. Online Players & Socket Telemetry Section
    let onlineTableHtml = '';
    if (onlinePlayers.length > 0) {
      const rows = onlinePlayers.map(p => `
        < tr >
          <td><code style="font-family: var(--font-mono); color: var(--accent-cyan); font-weight: 700;">${p.account_id}</code></td>
          <td style="font-weight: 600; color: #fff;">${escapeHtml(p.nickname || 'Unknown')}</td>
          <td>${window.UI.Badge('Lv.' + (p.level || 1), 'neutral')}</td>
          <td><span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">${escapeHtml(p.region || 'IND')}</span></td>
          <td>${window.UI.Badge('ONLINE', 'emerald')}</td>
          <td>
            <button class="btn btn-primary" style="padding: 2px 8px; font-size: 10px;" onclick="window.playerContext.setAccountId(${p.account_id}).then(() => window.location.hash='#/players/inspector')">
              Inspect
            </button>
          </td>
        </tr >
        `).join('');

      onlineTableHtml = `
        <div style="max-height: 380px; overflow-y: auto; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          ${window.UI.Table(['Account ID', 'Nickname', 'Level', 'Region', 'Status', 'Action'], rows)}
        </div>
      `;
    } else {
      onlineTableHtml = window.UI.EmptyState(
        'No Active Online Players',
        'No client game connections are currently connected to the Barbosa TCP lobby server. When players connect from the Free Fire 1.39 game client, active session descriptors will appear here.',
        window.UI.Icon('activity', 32, '', 'var(--text-tertiary)')
      );
    }

    const socketCardHtml = window.UI.Card(
      'Active Client Socket Telemetry',
      'Real-time authenticated client connections across Barbosa TCP Lobby (8081)',
      `
      < div style = "background: rgba(15, 23, 42, 0.45); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-bottom: 14px; font-size: 12px; color: var(--text-secondary); line-height: 1.5;" >
      <b>Daemon Architecture Note:</b> Raw socket handles are managed directly by < code > server / tcp_server.py</code >.Connected client handshakes and keep - alives are synchronized in memory and updated in the server state.
        </div >
      ${ onlineTableHtml }
    `
    );

    // 4. Wire Traffic Stream Section
    const reqRows = recentRequests.slice(0, 30).map(r => `
      < tr >
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); width: 85px; white-space: nowrap;">${escapeHtml(r.time || '—')}</td>
        <td style="width: 70px;">${window.UI.Badge(escapeHtml(r.method || 'GET'), (r.method || 'GET') === 'GET' ? 'cyan' : 'emerald')}</td>
        <td style="font-family: var(--font-mono); font-size: 11.5px; color: #fff; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(r.path || '')}</td>
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary); width: 110px;">${escapeHtml(r.ip || '127.0.0.1')}</td>
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); text-align: right; width: 80px;">${formatBytes(r.body_len || 0)}</td>
      </tr >
      `).join('');

        const trafficCardHtml = window.UI.Card(
        'Live HTTP Wire Traffic Stream',
        'Recent wire packets and API invocations processed by the HTTP Gateway',
        `
        <div style="max-height: 380px; overflow-y: auto; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          ${window.UI.Table(['Timestamp', 'Method', 'Path & Summary', 'Client IP', 'Payload Size'], reqRows, 'No recent network traffic logged.')}
        </div>
        `,
        `<div style="font-size: 11px; color: var(--text-tertiary);">Real-time stream buffer holds up to 100 recent transactions</div>`
        );

        // 5. Mount Page Container
        canvas.innerHTML = `
        <div class="page-container">
          ${window.UI.PageHeader(
            'Fleet Sessions & Network Telemetry',
            'Real-time client connections, socket telemetry, and live HTTP/TCP wire activity',
            headerActionsHtml,
            'activity'
          )}
          ${metricCardsHtml}
          <div style="display: flex; flex-direction: column; gap: var(--space-md);">
            ${socketCardHtml}
            ${trafficCardHtml}
          </div>
        </div>
        `;
  }

  // Self-register with AppRouter if initialized
  if (window.appRouter) {
    window.appRouter.register('#/players/sessions', window.Modules.PlayersSessions);
  }
})();
