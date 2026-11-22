/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Server Monitoring & Wire Telemetry Stream
 * Route: #/overview/monitoring
 * Domain: 01 Overview & Server Monitoring
 *
 * Production Implementation: Apple macOS / iPadOS Dark Glassmorphism
 * Zero Emojis • Unified Service Telemetry Strip • Compact 4-Card Metrics • Interactive Wire Inspector Drawer
 * High-Performance Smooth Incremental DOM Updates • Zero-Flicker Polling • Static Asset Traffic Filter
 */

(function () {
  'use strict';

  // Module internal state
  const state = {
    canvas: null,
    requests: [],
    totalRequestsCount: 0,
    serverState: null,
    loading: false,
    inFlight: false,
    error: null,
    pollTimer: null,
    pollRate: 2000, // 2s default
    isStreaming: true,
    pingMs: 0,
    lastUpdated: null,
    searchQuery: '',
    methodFilter: 'ALL',
    trafficFilter: 'API', // 'API' (Gateway & Game Wire) or 'ALL' (Include Static Assets)
    limit: 100,
    selectedRequest: null,
    renderedRequestSignature: ''
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
   * Determine if request path is static asset noise (.js, .css, .ico, /dashboard/src/)
   */
  function isStaticAsset(path) {
    if (!path) return false;
    const p = path.toLowerCase();
    return p.includes('/dashboard/src/') ||
           p.endsWith('.js') ||
           p.endsWith('.css') ||
           p.includes('favicon.ico') ||
           p.startsWith('/banners/');
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
   * Format localized number
   */
  function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return Number(num).toLocaleString();
  }

  /**
   * Format bytes into readable units
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
   * Calculate Real Throughput & Network Telemetry Metrics
   */
  function calculateTelemetry(requests) {
    if (!requests || !Array.isArray(requests) || requests.length === 0) {
      return {
        totalBytes: 0,
        avgBytes: 0,
        rps: '0.00',
        getCount: 0,
        postCount: 0,
        otherCount: 0,
        protobufCount: 0
      };
    }

    let totalBytes = 0;
    let getCount = 0;
    let postCount = 0;
    let otherCount = 0;
    let protobufCount = 0;
    const nowSec = Date.now() / 1000;
    let reqsLast60Sec = 0;

    for (const r of requests) {
      const b = r.body_len || 0;
      totalBytes += b;

      const m = (r.method || 'GET').toUpperCase();
      if (m === 'GET') getCount++;
      else if (m === 'POST') postCount++;
      else otherCount++;

      if (r.decoded) protobufCount++;

      if (r.timestamp && (nowSec - r.timestamp) <= 60) {
        reqsLast60Sec++;
      }
    }

    const rps = (reqsLast60Sec / 60).toFixed(2);
    const avgBytes = requests.length > 0 ? Math.round(totalBytes / requests.length) : 0;

    return {
      totalBytes,
      avgBytes,
      rps,
      getCount,
      postCount,
      otherCount,
      protobufCount
    };
  }

  /**
   * Format Raw Hex String into standard 16-byte offset hex pairs
   */
  function formatHexPairs(hexStr) {
    if (!hexStr) return '';
    const clean = hexStr.replace(/\s+/g, '').toUpperCase();
    const pairs = [];
    for (let i = 0; i < clean.length; i += 2) {
      pairs.push(clean.substr(i, 2));
    }
    // Group into 16 bytes per line
    const lines = [];
    for (let i = 0; i < pairs.length; i += 16) {
      const linePairs = pairs.slice(i, i + 16);
      const offset = i.toString(16).padStart(4, '0').toUpperCase();
      lines.push(`${offset}: ${linePairs.join(' ')}`);
    }
    return lines.join('\n');
  }

  /**
   * Get filtered request list based on user search, method, and traffic filter
   */
  function getFilteredRequests() {
    let list = state.requests || [];

    // 1. Traffic scope filter: API & Wire only vs All
    if (state.trafficFilter === 'API') {
      list = list.filter(r => !isStaticAsset(r.path));
    }

    // 2. Method filter
    if (state.methodFilter !== 'ALL') {
      list = list.filter(r => (r.method || 'GET').toUpperCase() === state.methodFilter);
    }

    // 3. Search query filter
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      list = list.filter(r => {
        const pathMatch = (r.path || '').toLowerCase().includes(q);
        const clientMatch = (r.client || '').toLowerCase().includes(q);
        const summaryMatch = (r.decoded && r.decoded.summary ? r.decoded.summary.toLowerCase() : '').includes(q);
        return pathMatch || clientMatch || summaryMatch;
      });
    }

    return list;
  }

  /**
   * Fetch Live Telemetry Data from API
   */
  async function fetchData() {
    if (state.inFlight) return;
    state.inFlight = true;
    const t0 = performance.now();

    try {
      const [reqsRes, stateRes] = await Promise.all([
        window.apiClient.get('/api/dashboard/requests', {
          limit: state.limit
        }),
        window.apiClient.get('/api/dashboard/state')
      ]);

      state.pingMs = Math.round(performance.now() - t0);
      state.lastUpdated = new Date();

      if (reqsRes && reqsRes.ok && reqsRes.data) {
        state.requests = reqsRes.data.requests || [];
        state.totalRequestsCount = reqsRes.data.total !== undefined ? reqsRes.data.total : state.requests.length;
        state.error = null;
      } else {
        state.error = (reqsRes && reqsRes.error) || 'Failed to fetch telemetry request stream';
      }

      if (stateRes && stateRes.ok && stateRes.data) {
        state.serverState = stateRes.data;
      }
    } catch (err) {
      state.pingMs = Math.round(performance.now() - t0);
      state.error = err.message || 'Network communication error';
    } finally {
      state.inFlight = false;
    }
  }

  /**
   * Auto-refresh lifecycle timers
   */
  function startPolling() {
    stopPolling();
    if (state.isStreaming && state.pollRate > 0) {
      state.pollTimer = setInterval(async () => {
        if (!window.location.hash.startsWith('#/overview/monitoring')) {
          stopPolling();
          return;
        }
        await fetchData();
        updateDynamicElements();
      }, state.pollRate);
    }
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function onHashChange() {
    if (!window.location.hash.startsWith('#/overview/monitoring')) {
      stopPolling();
      if (typeof window.removeEventListener === 'function') {
        window.removeEventListener('hashchange', onHashChange);
      }
    }
  }

  /**
   * Generate Table Rows HTML
   */
  function renderTableRowsHtml(filteredRequests) {
    if (filteredRequests.length === 0) {
      if (state.searchQuery || state.methodFilter !== 'ALL' || state.trafficFilter === 'API') {
        return `
          <tr>
            <td colspan="8" style="padding: 0;">
              ${window.UI.EmptyState(
                'No Matching Packets',
                state.trafficFilter === 'API' && state.requests.length > 0
                  ? 'No gateway API/game packets in active buffer. Click "All Traffic" to view static assets, or trigger game actions.'
                  : 'No wire packets match the active search or method filter.',
                window.UI.Icon('search', 32, '', 'var(--text-tertiary)'),
                state.trafficFilter === 'API' && state.requests.length > 0
                  ? '<button class="btn btn-secondary" onclick="window.ServerMonitoringModule.setTrafficFilter(\'ALL\')">View All Traffic</button>'
                  : '<button class="btn btn-secondary" onclick="window.ServerMonitoringModule.clearFilters()">Clear Filters</button>'
              )}
            </td>
          </tr>
        `;
      }
      return `
        <tr>
          <td colspan="8" style="padding: 0;">
            ${window.UI.EmptyState(
              'Telemetry Buffer Empty',
              'All recorded HTTP requests have been purged from memory and requests.log. Waiting for incoming gateway traffic...',
              window.UI.Icon('terminal', 32, '', 'var(--accent-cyan)'),
              '<button class="btn btn-secondary" onclick="window.ServerMonitoringModule.refreshNow()">Refresh Stream</button>'
            )}
          </td>
        </tr>
      `;
    }

    return filteredRequests.map((r, idx) => {
      const method = (r.method || 'GET').toUpperCase();
      const badgeVariant = method === 'GET' ? 'cyan' : (method === 'POST' ? 'emerald' : (method === 'DELETE' ? 'rose' : 'amber'));
      const hasProto = !!r.decoded;
      const hasHex = !!r.body_hex;
      const isStatic = isStaticAsset(r.path);

      return `
        <tr style="cursor: pointer;" onclick="window.ServerMonitoringModule.inspectRequest(${idx})">
          <td style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 11px; width: 50px;">
            #${escapeHtml(r.id || idx + 1)}
          </td>
          <td style="width: 85px;">
            <code style="font-family: var(--font-mono); color: var(--accent-cyan); font-size: 11px;">${escapeHtml(r.time || '—')}</code>
          </td>
          <td style="width: 75px;">
            ${window.UI.Badge(escapeHtml(method), badgeVariant)}
          </td>
          <td style="font-family: var(--font-mono); font-size: 11.5px; word-break: break-all;">
            <span style="color: ${isStatic ? 'var(--text-secondary)' : '#fff'}; font-weight: 500;">${escapeHtml(r.path || '/')}</span>
            ${r.decoded && r.decoded.summary ? `
              <div style="font-size: 10.5px; color: var(--accent-emerald); font-family: var(--font-sans); margin-top: 2px; display: flex; align-items: center; gap: 4px;">
                ${window.UI.Icon('sparkles', 11, '', 'var(--accent-emerald)')}
                <span>${escapeHtml(r.decoded.summary)}</span>
              </div>
            ` : ''}
          </td>
          <td style="width: 115px;">
            <code style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 11px;">${escapeHtml(r.client || '127.0.0.1')}</code>
          </td>
          <td style="width: 90px; font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">
            ${r.body_len ? formatBytes(r.body_len) : '—'}
          </td>
          <td style="width: 115px;">
            ${hasProto ? `
              <span class="badge badge-emerald" style="font-size: 10px;">PROTOBUF</span>
            ` : (hasHex ? `
              <span class="badge badge-neutral" style="font-size: 10px;">RAW BYTES</span>
            ` : `
              <span style="color: var(--text-disabled); font-size: 11px;">${isStatic ? 'STATIC' : 'EMPTY'}</span>
            `)}
          </td>
          <td style="width: 80px; text-align: right;">
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;" onclick="event.stopPropagation(); window.ServerMonitoringModule.inspectRequest(${idx})">
              ${window.UI.Icon('eye', 12)}
              <span>Inspect</span>
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  /**
   * High-Performance Selective DOM Updater
   * Modifies only targeted elements on polling ticks without recreating canvas or disturbing user inputs/scroll
   */
  function updateDynamicElements() {
    if (!state.canvas || !window.location.hash.startsWith('#/overview/monitoring')) return;

    // If canvas structure is not yet rendered, execute initial mount
    const container = state.canvas.querySelector('.page-container');
    if (!container) {
      renderInitialLayout();
      return;
    }

    const snap = state.serverState || {};
    const serverInfo = snap.server || {};
    const rooms = snap.rooms || [];
    const uptimeStr = formatUptime(serverInfo.uptime_sec || 0);
    const totalRequestsCount = serverInfo.request_count || state.totalRequestsCount;
    const telemetry = calculateTelemetry(state.requests);
    const filteredRequests = getFilteredRequests();
    const lastUpdatedStr = formatTime(state.lastUpdated);

    // 1. Update Header Telemetry
    const updatedEl = document.getElementById('mon-last-updated');
    if (updatedEl) updatedEl.textContent = lastUpdatedStr;

    // 2. Update Service Strip
    const pingEl = document.getElementById('mon-ping-val');
    if (pingEl) pingEl.textContent = `${state.pingMs} ms`;

    const roomEl = document.getElementById('mon-room-count');
    if (roomEl) roomEl.textContent = rooms.length;

    // 3. Update Stat Cards
    const rpsEl = document.getElementById('mon-stat-rps');
    if (rpsEl) rpsEl.innerHTML = `${telemetry.rps} <span style="font-size: 12px; font-weight: 500; color: var(--text-tertiary);">req/s</span>`;

    const bytesEl = document.getElementById('mon-stat-bytes');
    if (bytesEl) bytesEl.textContent = formatBytes(telemetry.totalBytes);

    const bytesAvgEl = document.getElementById('mon-stat-bytes-avg');
    if (bytesAvgEl) bytesAvgEl.textContent = `Average ${telemetry.avgBytes} B / packet`;

    const uptimeEl = document.getElementById('mon-stat-uptime');
    if (uptimeEl) uptimeEl.textContent = uptimeStr;

    const totalReqsEl = document.getElementById('mon-stat-total-reqs');
    if (totalReqsEl) totalReqsEl.textContent = `${formatNumber(totalRequestsCount)} total gateway requests`;

    const protoEl = document.getElementById('mon-stat-proto');
    if (protoEl) protoEl.innerHTML = `${telemetry.protobufCount} <span style="font-size: 12px; font-weight: 500; color: var(--text-tertiary);">Protobuf</span>`;

    const satEl = document.getElementById('mon-stat-saturation');
    if (satEl) satEl.textContent = `${filteredRequests.length} displayed / ${state.requests.length} buffered`;

    // 4. Update Table Rows ONLY if signature changed
    const newSignature = `${filteredRequests.length}:${filteredRequests.slice(0, 5).map(r => r.id + '_' + r.time).join(',')}`;
    if (state.renderedRequestSignature !== newSignature) {
      state.renderedRequestSignature = newSignature;
      const tbody = document.getElementById('mon-table-body');
      if (tbody) {
        tbody.innerHTML = renderTableRowsHtml(filteredRequests);
      }
    }
  }

  /**
   * Render Master Layout Skeleton (Run once upon route entry)
   */
  function renderInitialLayout() {
    if (!state.canvas || !window.location.hash.startsWith('#/overview/monitoring')) return;

    const snap = state.serverState || {};
    const serverInfo = snap.server || {};
    const rooms = snap.rooms || [];
    const uptimeStr = formatUptime(serverInfo.uptime_sec || 0);
    const totalRequestsCount = serverInfo.request_count || state.totalRequestsCount;
    const telemetry = calculateTelemetry(state.requests);
    const filteredRequests = getFilteredRequests();
    const lastUpdatedStr = formatTime(state.lastUpdated);

    // 1. Page Header Actions Toolbar
    const headerActionsHtml = `
      <div class="toolbar-actions" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <!-- Stream State Pill -->
        <div id="mon-stream-pill" class="badge ${state.isStreaming ? 'badge-emerald' : 'badge-amber'}" style="padding: 4px 10px; font-size: 11px; display: inline-flex; align-items: center; gap: 6px;">
          ${window.UI.StatusDot(state.isStreaming ? 'active' : 'warning')}
          <span id="mon-stream-text">${state.isStreaming ? 'LIVE STREAM' : 'STREAM PAUSED'}</span>
        </div>

        <span style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); margin-right: 4px;">
          Updated: <span id="mon-last-updated" style="color: var(--text-secondary);">${lastUpdatedStr}</span>
        </span>

        <!-- Polling rate selector -->
        <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.04); padding: 3px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border-default);">
          <span style="font-size: 11px; color: var(--text-tertiary); display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('clock', 12, '', 'var(--text-tertiary)')} Polling:
          </span>
          <select id="mon-rate-select" class="form-select" style="padding: 2px 6px; font-size: 11px; width: auto; background: transparent; border: none; color: var(--accent-cyan); cursor: pointer;" onchange="window.ServerMonitoringModule.setPollRate(this.value)">
            <option value="1000" ${state.pollRate === 1000 ? 'selected' : ''}>1s Fast</option>
            <option value="2000" ${state.pollRate === 2000 ? 'selected' : ''}>2s Normal</option>
            <option value="5000" ${state.pollRate === 5000 ? 'selected' : ''}>5s Relaxed</option>
            <option value="0" ${state.pollRate === 0 ? 'selected' : ''}>Paused</option>
          </select>
        </div>

        <!-- Pause / Stream Toggle -->
        <button id="mon-toggle-btn" class="btn btn-secondary" onclick="window.ServerMonitoringModule.toggleStream()" title="${state.isStreaming ? 'Pause live streaming' : 'Resume live streaming'}">
          <span id="mon-toggle-icon" style="display: inline-flex; align-items: center;">${window.UI.Icon(state.isStreaming ? 'clock' : 'refresh', 13)}</span>
          <span id="mon-toggle-text">${state.isStreaming ? 'Pause' : 'Resume'}</span>
        </button>

        <!-- Refresh -->
        <button class="btn btn-secondary" onclick="window.ServerMonitoringModule.refreshNow()" title="Fetch latest packets">
          ${window.UI.Icon('refresh', 13)}
          <span>Refresh</span>
        </button>

        <!-- Clear Request History (UI.Confirm Guarded) -->
        <button class="btn btn-danger" onclick="window.ServerMonitoringModule.confirmClearBuffer()" title="Clear server-side requests.log buffer">
          ${window.UI.Icon('trash', 13)}
          <span>Clear Buffer</span>
        </button>

        <!-- Export JSON -->
        <button class="btn btn-secondary" onclick="window.ServerMonitoringModule.exportTelemetryJson()" title="Download telemetry dump">
          ${window.UI.Icon('download', 13)}
          <span>Export JSON</span>
        </button>
      </div>
    `;

    // Render PageHeader component with clean activity icon
    const pageHeaderHtml = window.UI.PageHeader(
      'Server Monitoring',
      'Barbosa Gateway wire telemetry, daemon telemetry, and Protobuf stream inspector',
      headerActionsHtml,
      'activity'
    );

    // 2. Alert Banner (if error present)
    const alertBannerHtml = state.error ? `
      <div id="mon-alert-banner" class="glass-card" style="border-left: 3px solid var(--accent-rose); background: rgba(244, 63, 94, 0.08); margin-bottom: var(--space-md); padding: 12px 16px;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
          <div style="display: flex; align-items: center; gap: 10px;">
            ${window.UI.Icon('alertTriangle', 18, '', 'var(--accent-rose)')}
            <div>
              <div style="color: var(--accent-rose); font-weight: 600; font-size: 12.5px;">Telemetry Stream Warning</div>
              <div style="color: var(--text-secondary); font-size: 11.5px;">${escapeHtml(state.error)}</div>
            </div>
          </div>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="window.ServerMonitoringModule.refreshNow()">
            Retry Connection
          </button>
        </div>
      </div>
    ` : '';

    // 3. Compact Unified Service Telemetry Strip
    const serviceStripHtml = `
      <div class="glass-card" style="padding: 10px 16px; margin-bottom: var(--space-md); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
        <!-- HTTP Gateway (Verified REST Probe) -->
        <div style="display: flex; align-items: center; gap: 8px;">
          ${window.UI.StatusDot(state.error ? 'danger' : 'active')}
          <span style="font-size: 12px; font-weight: 600; color: #fff;">HTTP Gateway</span>
          <span class="badge badge-emerald" style="font-family: var(--font-mono); font-size: 10px; padding: 2px 6px;">PORT 8080</span>
          ${window.UI.Badge(state.error ? 'OFFLINE' : 'ONLINE', state.error ? 'rose' : 'emerald')}
          <span style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); margin-left: 4px;">
            HTTP response time: <b id="mon-ping-val" style="color: var(--accent-emerald);">${state.pingMs} ms</b>
          </span>
        </div>

        <div style="width: 1px; height: 18px; background: var(--border-subtle); display: none; @media(min-width: 900px){ display: block; }"></div>

        <!-- TCP Lobby Socket (Configured Daemon) -->
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

        <!-- UDP Combat Engine (Configured Match Daemon) -->
        <div style="display: flex; align-items: center; gap: 8px;">
          ${window.UI.StatusDot('warning')}
          <span style="font-size: 12px; font-weight: 600; color: #fff;">UDP Combat</span>
          <span class="badge badge-indigo" style="font-family: var(--font-mono); font-size: 10px; padding: 2px 6px;">PORT 39800</span>
          ${window.UI.Badge('CONFIGURED', 'neutral')}
          <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 4px;">
            30 Hz Tick • <b id="mon-room-count" style="color: #fff;">${rooms.length}</b> Active Rooms
          </span>
        </div>
      </div>
    `;

    // 4. Compact Operational Metrics Grid (.grid-4, Zero Fake Gauges)
    const statCardsHtml = `
      <div class="grid-4" style="margin-bottom: var(--space-md);">
        ${window.UI.StatCard(
          'Throughput Rate',
          `<span id="mon-stat-rps">${telemetry.rps} <span style="font-size: 12px; font-weight: 500; color: var(--text-tertiary);">req/s</span></span>`,
          'Calculated over 60s sliding window',
          window.UI.Icon('zap', 16, '', 'var(--accent-cyan)'),
          'cyan'
        )}

        ${window.UI.StatCard(
          'Wire Payload Volume',
          `<span id="mon-stat-bytes">${formatBytes(telemetry.totalBytes)}</span>`,
          `<span id="mon-stat-bytes-avg">Average ${telemetry.avgBytes} B / packet</span>`,
          window.UI.Icon('package', 16, '', 'var(--accent-emerald)'),
          'emerald'
        )}

        ${window.UI.StatCard(
          'Gateway Uptime & Activity',
          `<span id="mon-stat-uptime">${uptimeStr}</span>`,
          `<span id="mon-stat-total-reqs">${formatNumber(totalRequestsCount)} total gateway requests</span>`,
          window.UI.Icon('clock', 16, '', 'var(--accent-violet)'),
          'violet'
        )}

        ${window.UI.StatCard(
          'Wire Protocol Stream',
          `<span id="mon-stat-proto">${telemetry.protobufCount} <span style="font-size: 12px; font-weight: 500; color: var(--text-tertiary);">Protobuf</span></span>`,
          `<span id="mon-stat-saturation">${filteredRequests.length} displayed / ${state.requests.length} buffered</span>`,
          window.UI.Icon('activity', 16, '', 'var(--accent-amber)'),
          'amber'
        )}
      </div>
    `;

    // 5. Interactive Request Stream & Wire Inspector Table
    const tableHeaderHtml = `
      <div class="glass-card-header" style="margin-bottom: var(--space-sm);">
        <div>
          <div class="glass-card-title">Wire Packet Stream & Inspection</div>
          <div class="glass-card-subtitle">Real-time HTTP wire packets processed by BarbosaHandler with Protobuf inspection</div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <span style="font-size: 11.5px; color: var(--text-tertiary);">Display:</span>
          <select class="form-select" style="padding: 2px 8px; font-size: 11.5px; width: auto;" onchange="window.ServerMonitoringModule.setLimit(this.value)">
            <option value="25" ${state.limit === 25 ? 'selected' : ''}>25 items</option>
            <option value="50" ${state.limit === 50 ? 'selected' : ''}>50 items</option>
            <option value="100" ${state.limit === 100 ? 'selected' : ''}>100 items</option>
            <option value="200" ${state.limit === 200 ? 'selected' : ''}>200 items</option>
          </select>
        </div>
      </div>
    `;

    // Filter Bar with Scope Toggle
    const filterBarHtml = `
      <div style="display: flex; gap: 12px; align-items: center; margin-bottom: var(--space-sm); flex-wrap: wrap;">
        <!-- Traffic Scope Filter (Noise Reducer) -->
        <div style="display: flex; gap: 4px; background: rgba(10, 16, 28, 0.4); padding: 3px; border-radius: var(--radius-sm); border: 1px solid var(--border-default);">
          <button class="btn ${state.trafficFilter === 'API' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 11px;" onclick="window.ServerMonitoringModule.setTrafficFilter('API')">
            API & Wire Only
          </button>
          <button class="btn ${state.trafficFilter === 'ALL' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 11px;" onclick="window.ServerMonitoringModule.setTrafficFilter('ALL')">
            All Traffic
          </button>
        </div>

        <!-- Search input -->
        <div style="flex: 1; min-width: 240px; position: relative;">
          <span style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); pointer-events: none; color: var(--text-tertiary);">
            ${window.UI.Icon('search', 13)}
          </span>
          <input type="text" id="mon-search-input" class="form-input" style="padding-left: 32px;" placeholder="Filter by path, IP, or decoded summary..." value="${escapeHtml(state.searchQuery)}" oninput="window.ServerMonitoringModule.onSearchChange(this.value)">
        </div>

        <!-- Method pills -->
        <div style="display: flex; gap: 4px;">
          ${['ALL', 'GET', 'POST', 'PUT', 'DELETE'].map(m => `
            <button class="btn ${state.methodFilter === m ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 11px;" onclick="window.ServerMonitoringModule.setMethodFilter('${m}')">
              ${m}
            </button>
          `).join('')}
        </div>

        ${state.searchQuery || state.methodFilter !== 'ALL' || state.trafficFilter !== 'API' ? `
          <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 8px;" onclick="window.ServerMonitoringModule.clearFilters()">
            Reset Filters
          </button>
        ` : ''}
      </div>
    `;

    // Table Content
    state.renderedRequestSignature = `${filteredRequests.length}:${filteredRequests.slice(0, 5).map(r => r.id + '_' + r.time).join(',')}`;
    const tableRowsHtml = renderTableRowsHtml(filteredRequests);

    const tableContainerHtml = `
      <div class="glass-table-container" style="max-height: 520px; overflow-y: auto;">
        <table class="glass-table">
          <thead>
            <tr>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2; width: 50px;">ID</th>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2; width: 85px;">Time</th>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2; width: 75px;">Method</th>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2;">Request Path & Decoded Summary</th>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2; width: 115px;">Client IP</th>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2; width: 90px;">Body Size</th>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2; width: 115px;">Wire Protocol</th>
              <th style="position: sticky; top: 0; background: rgba(10, 16, 28, 0.96); backdrop-filter: blur(10px); z-index: 2; width: 80px; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody id="mon-table-body">
            ${tableRowsHtml}
          </tbody>
        </table>
      </div>
    `;

    const streamCardHtml = `
      <div class="glass-card" style="margin-bottom: var(--space-md);">
        ${tableHeaderHtml}
        ${filterBarHtml}
        ${tableContainerHtml}
      </div>
    `;

    // Assembly inside master .page-container
    const html = `
      <div class="page-container">
        ${pageHeaderHtml}
        ${alertBannerHtml}
        ${serviceStripHtml}
        ${statCardsHtml}
        ${streamCardHtml}
      </div>
    `;

    state.canvas.innerHTML = html;
  }

  /**
   * Main Route Handler for #/overview/monitoring
   */
  async function renderOverviewMonitoring(canvas) {
    state.canvas = canvas;

    stopPolling();
    if (typeof window.removeEventListener === 'function') {
      window.removeEventListener('hashchange', onHashChange);
    }
    if (typeof window.addEventListener === 'function') {
      window.addEventListener('hashchange', onHashChange);
    }

    // Initial render loading state if no cached data exists
    if (!state.serverState && state.requests.length === 0) {
      canvas.innerHTML = window.UI.Loading('Establishing live telemetry connection...', 'Probing Barbosa HTTP Gateway and Daemon status');
    }

    await fetchData();
    renderInitialLayout();
    startPolling();
  }

  /**
   * Open Slide-Out Inspection Drawer for a given request
   */
  function inspectRequest(idx) {
    const filtered = getFilteredRequests();
    const req = filtered[idx] || state.requests[idx];
    if (!req) return;

    state.selectedRequest = req;
    const method = (req.method || 'GET').toUpperCase();
    const hasHex = !!req.body_hex;
    const hasProto = !!req.decoded;

    const drawerBody = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- Metadata Grid -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: rgba(10, 16, 28, 0.5); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-default); font-size: 12px;">
          <div><span style="color: var(--text-tertiary);">Request ID:</span> <b style="font-family: var(--font-mono); color: #fff;">#${escapeHtml(req.id || idx + 1)}</b></div>
          <div><span style="color: var(--text-tertiary);">Timestamp:</span> <b style="font-family: var(--font-mono); color: var(--accent-cyan);">${escapeHtml(req.time || '—')}</b></div>
          <div><span style="color: var(--text-tertiary);">Method:</span> <span>${window.UI.Badge(escapeHtml(method), method === 'GET' ? 'cyan' : (method === 'POST' ? 'emerald' : 'rose'))}</span></div>
          <div><span style="color: var(--text-tertiary);">Client IP:</span> <b style="font-family: var(--font-mono); color: #fff;">${escapeHtml(req.client || '127.0.0.1')}</b></div>
          <div style="grid-column: 1 / -1;"><span style="color: var(--text-tertiary);">Full Path:</span> <code style="font-family: var(--font-mono); color: var(--accent-cyan); word-break: break-all;">${escapeHtml(req.path || '/')}</code></div>
          <div><span style="color: var(--text-tertiary);">Payload Length:</span> <b style="font-family: var(--font-mono); color: #fff;">${req.body_len || 0} bytes</b></div>
          <div><span style="color: var(--text-tertiary);">Wire Protocol:</span> <b style="color: ${hasProto ? 'var(--accent-emerald)' : 'var(--text-secondary)'};">${hasProto ? 'Protobuf Wire' : (hasHex ? 'Raw Bytes' : 'Empty Body')}</b></div>
        </div>

        <!-- Decoded Protobuf Payload -->
        ${hasProto ? `
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--accent-emerald); display: flex; align-items: center; gap: 5px;">
                ${window.UI.Icon('sparkles', 12, '', 'var(--accent-emerald)')} Decoded Protobuf Wire Payload
              </span>
              <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10.5px;" onclick="navigator.clipboard.writeText(JSON.stringify(window.ServerMonitoringModule.getSelectedRequest().decoded, null, 2)).then(() => window.UI.Toast('JSON copied to clipboard', 'success'))">
                ${window.UI.Icon('copy', 11)} Copy JSON
              </button>
            </div>
            <pre style="background: rgba(0, 0, 0, 0.6); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(16, 185, 129, 0.3); font-family: var(--font-mono); font-size: 11px; color: #a7f3d0; max-height: 240px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; margin: 0;">${escapeHtml(JSON.stringify(req.decoded, null, 2))}</pre>
          </div>
        ` : ''}

        <!-- Raw Hex Dump -->
        ${hasHex ? `
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary); display: flex; align-items: center; gap: 5px;">
                ${window.UI.Icon('terminal', 12, '', 'var(--text-tertiary)')} Raw Payload Hex Dump (${req.body_len} bytes)
              </span>
              <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10.5px;" onclick="navigator.clipboard.writeText('${escapeHtml(req.body_hex || '')}').then(() => window.UI.Toast('Hex copied to clipboard', 'success'))">
                ${window.UI.Icon('copy', 11)} Copy Hex
              </button>
            </div>
            <pre style="background: rgba(0, 0, 0, 0.6); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-default); font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); max-height: 240px; overflow-y: auto; white-space: pre; line-height: 1.4; margin: 0;">${escapeHtml(formatHexPairs(req.body_hex))}</pre>
          </div>
        ` : `
          <div style="padding: 20px; background: rgba(10, 16, 28, 0.3); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); color: var(--text-tertiary); font-size: 12px; text-align: center;">
            No HTTP body payload attached to this request.
          </div>
        `}
      </div>
    `;

    const drawerFooter = `
      <button class="btn btn-secondary" onclick="window.UI.CloseDrawer()">Close Panel</button>
    `;

    window.UI.Drawer(`Wire Packet #${escapeHtml(req.id || idx + 1)}: ${escapeHtml(method)}`, drawerBody, drawerFooter, { width: '520px' });
  }

  // --- Public Interface ---
  const ServerMonitoring = {
    render: renderOverviewMonitoring,

    getSelectedRequest: function () {
      return state.selectedRequest;
    },

    refreshNow: async function () {
      await fetchData();
      updateDynamicElements();
      if (window.UI) window.UI.Toast('Telemetry stream refreshed', 'success');
    },

    toggleStream: function () {
      state.isStreaming = !state.isStreaming;
      if (state.isStreaming) {
        startPolling();
        if (window.UI) window.UI.Toast('Live telemetry stream resumed', 'info');
      } else {
        stopPolling();
        if (window.UI) window.UI.Toast('Live telemetry stream paused', 'warning');
      }
      // Update UI button and pill
      const pill = document.getElementById('mon-stream-pill');
      if (pill) {
        pill.className = `badge ${state.isStreaming ? 'badge-emerald' : 'badge-amber'}`;
      }
      const text = document.getElementById('mon-stream-text');
      if (text) text.textContent = state.isStreaming ? 'LIVE STREAM' : 'STREAM PAUSED';

      const toggleText = document.getElementById('mon-toggle-text');
      if (toggleText) toggleText.textContent = state.isStreaming ? 'Pause' : 'Resume';

      const toggleIcon = document.getElementById('mon-toggle-icon');
      if (toggleIcon) toggleIcon.innerHTML = window.UI.Icon(state.isStreaming ? 'clock' : 'refresh', 13);
    },

    setPollRate: function (rate) {
      state.pollRate = parseInt(rate, 10) || 0;
      if (state.pollRate > 0) {
        state.isStreaming = true;
        startPolling();
        if (window.UI) window.UI.Toast(`Telemetry polling set to ${state.pollRate / 1000}s`, 'info');
      } else {
        state.isStreaming = false;
        stopPolling();
        if (window.UI) window.UI.Toast('Telemetry polling paused', 'warning');
      }
      const text = document.getElementById('mon-stream-text');
      if (text) text.textContent = state.isStreaming ? 'LIVE STREAM' : 'STREAM PAUSED';
      const pill = document.getElementById('mon-stream-pill');
      if (pill) pill.className = `badge ${state.isStreaming ? 'badge-emerald' : 'badge-amber'}`;
    },

    setTrafficFilter: function (scope) {
      state.trafficFilter = scope || 'API';
      renderInitialLayout();
    },

    setLimit: function (limit) {
      state.limit = parseInt(limit, 10) || 100;
      fetchData().then(() => updateDynamicElements());
    },

    setMethodFilter: function (method) {
      state.methodFilter = method;
      renderInitialLayout();
    },

    onSearchChange: function (query) {
      state.searchQuery = query || '';
      const tbody = document.getElementById('mon-table-body');
      if (tbody) {
        tbody.innerHTML = renderTableRowsHtml(getFilteredRequests());
      }
    },

    clearFilters: function () {
      state.searchQuery = '';
      state.methodFilter = 'ALL';
      state.trafficFilter = 'API';
      renderInitialLayout();
    },

    confirmClearBuffer: function () {
      window.UI.Confirm(
        'Clear Telemetry Buffer',
        'Are you sure you want to purge all recorded HTTP requests from the in-memory buffer and requests.log?',
        async () => {
          try {
            const res = await window.apiClient.post('/api/dashboard/requests/clear');
            if (res && res.ok) {
              state.requests = [];
              state.totalRequestsCount = 0;
              window.UI.Toast('Telemetry buffer cleared', 'success');
              await fetchData();
              updateDynamicElements();
            } else {
              window.UI.Toast((res && res.error) || 'Failed to clear buffer', 'error');
            }
          } catch (e) {
            window.UI.Toast(e.message, 'error');
          }
        },
        true
      );
    },

    exportTelemetryJson: function () {
      const filtered = getFilteredRequests();
      if (!filtered || filtered.length === 0) {
        return window.UI.Toast('No telemetry data to export', 'warning');
      }
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(filtered, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `telemetry_stream_${new Date().toISOString().replace(/[:.]/g, '-')}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      window.UI.Toast('Telemetry exported to JSON', 'success');
    },

    inspectRequest: inspectRequest
  };

  // Global namespace registration
  window.ServerMonitoringModule = ServerMonitoring;
  window.Modules = window.Modules || {};
  window.Modules.OverviewMonitoring = renderOverviewMonitoring;

  // SPA Hash Router Registration
  if (window.appRouter) {
    window.appRouter.register('#/overview/monitoring', renderOverviewMonitoring);
  }
})();
