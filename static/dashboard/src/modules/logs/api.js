/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Real-time API Monitor & Telemetry Stream
 * Route: #/logs/api
 */

(function () {
  'use strict';

  let pollInterval = null;
  let isStreaming = true;
  let currentPollRate = 2000; // 2 seconds
  let activeFilterQuery = '';
  let activeMethodFilter = 'ALL';
  let activeStatusFilter = 'ALL';
  let capturedRequests = [];
  let unsubscribeApiActivity = null;

  /**
   * Main render function for #/logs/api
   */
  async function renderLogsApi(canvas) {
    // Clear any existing poll timer
    stopPolling();

    canvas.innerHTML = `
      <!-- Header & Quick Metrics -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 4px;">API Live Monitor</h2>
          <p style="color: var(--text-secondary); font-size: 12px;">Real-time IND PROJECT HTTP gateway telemetry, request stream & wire inspector</p>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <div id="stream-status-pill" class="badge badge-emerald" style="padding: 4px 10px; font-size: 11px;">
            <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--accent-emerald); box-shadow: 0 0 6px var(--accent-emerald); margin-right: 4px;"></span>
            LIVE STREAM
          </div>
          <button id="toggle-stream-btn" class="btn btn-secondary" onclick="window.LogsApiModule.toggleStream()">
            ⏸ Pause Stream
          </button>
          <button class="btn btn-secondary" onclick="window.LogsApiModule.refreshStream()" title="Manual refresh">
            🔄 Refresh
          </button>
          <button class="btn btn-danger" onclick="window.LogsApiModule.promptClearBuffer()">
            🗑 Clear Buffer
          </button>
          <button class="btn btn-secondary" onclick="window.LogsApiModule.exportLogs()">
            📥 Export JSON
          </button>
        </div>
      </div>

      <!-- Telemetry Stats Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px;">
        <div class="stat-card">
          <div class="stat-label">Total Tracked</div>
          <div class="stat-value" id="stat-total-reqs">—</div>
          <div class="stat-subtext">Buffered in memory (max 1000)</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">2xx Successful</div>
          <div class="stat-value" id="stat-success-reqs" style="color: var(--accent-emerald);">—</div>
          <div class="stat-subtext" id="stat-success-rate">100% success rate</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">4xx / 5xx Errors</div>
          <div class="stat-value" id="stat-error-reqs" style="color: var(--accent-rose);">0</div>
          <div class="stat-subtext">Rejected or invalid payloads</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Active Stream Interval</div>
          <div class="stat-value" style="font-size: 16px;">
            <select id="poll-rate-select" class="form-input" style="padding: 2px 6px; font-size: 13px; width: auto; display: inline-block; background: rgba(0,0,0,0.3);" onchange="window.LogsApiModule.setPollRate(this.value)">
              <option value="1000">1.0 sec (Fast)</option>
              <option value="2000" selected>2.0 sec (Normal)</option>
              <option value="5000">5.0 sec (Relaxed)</option>
              <option value="10000">10.0 sec (Low Overhead)</option>
            </select>
          </div>
          <div class="stat-subtext">Auto-poll <code>/api/dashboard/requests</code></div>
        </div>
      </div>

      <!-- Filter Bar -->
      <div class="glass-card" style="padding: 14px 18px; margin-bottom: 16px;">
        <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 240px;">
            <input type="text" id="api-search-input" class="form-input" placeholder="Filter by endpoint path, parameter, IP or summary (e.g. /MajorLogin, mail)..." oninput="window.LogsApiModule.onSearchChange(this.value)">
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase;">Method:</span>
            <select id="api-method-select" class="form-input" style="width: 100px; padding: 6px 10px;" onchange="window.LogsApiModule.onMethodChange(this.value)">
              <option value="ALL">ALL</option>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase;">Status:</span>
            <select id="api-status-select" class="form-input" style="width: 120px; padding: 6px 10px;" onchange="window.LogsApiModule.onStatusChange(this.value)">
              <option value="ALL">ALL Statuses</option>
              <option value="2xx">2xx (Success)</option>
              <option value="4xx">4xx (Client Err)</option>
              <option value="5xx">5xx (Server Err)</option>
            </select>
          </div>
          <button class="btn btn-secondary" onclick="window.LogsApiModule.resetFilters()">Reset</button>
        </div>
      </div>

      <!-- Request Table Card -->
      <div class="glass-card" style="padding: 0; overflow: hidden; margin-bottom: 24px;">
        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; color: #fff; font-size: 13px;">Live Ingestion Stream</div>
          <div id="table-record-count" style="font-size: 11px; color: var(--text-tertiary);">0 requests displayed</div>
        </div>
        <div class="glass-table-container" id="api-table-container">
          ${window.UI.Loading('Ingesting request telemetry stream...')}
        </div>
      </div>

      <!-- Protobuf Wire On-Demand Decoder Utility -->
      <div class="glass-card" style="margin-bottom: 30px;">
        <div class="glass-card-header">
          <div>
            <div class="glass-card-title">Wire-Level Protobuf Decoder</div>
            <div class="glass-card-subtitle">Decode raw client hex or base64 packets directly against Protobuf schema decoder</div>
          </div>
          <div class="glass-card-actions">
            <button class="btn btn-secondary" onclick="window.LogsApiModule.insertSampleHex()">Insert Sample Handshake</button>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          <div>
            <label style="display: block; font-size: 11px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase;">
              Raw Hex or Base64 Wire Payload
            </label>
            <textarea id="wire-hex-input" class="form-input" style="height: 140px; font-family: var(--font-mono); font-size: 11.5px; resize: vertical;" placeholder="Paste raw packet hex (e.g. 08 01 12 04 74 65 73 74) or base64..."></textarea>
            <div style="display: flex; gap: 8px; margin-top: 10px;">
              <button class="btn btn-primary" onclick="window.LogsApiModule.decodeWirePacket()">⚡ Decode Packet</button>
              <button class="btn btn-secondary" onclick="document.getElementById('wire-hex-input').value = ''; document.getElementById('wire-decoded-output').innerHTML = 'Awaiting input...';">Clear</button>
            </div>
          </div>
          <div>
            <label style="display: block; font-size: 11px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase;">
              Parsed Protobuf Structure (Monaco Syntax Highlighted)
            </label>
            <div class="monaco-viewer" style="background: #181c28; border: 1px solid var(--border-default); border-radius: var(--radius-sm); overflow: hidden; box-shadow: inset 0 2px 8px rgba(0,0,0,0.5);">
              <div style="background: rgba(10, 14, 22, 0.75); padding: 5px 12px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; font-size: 10.5px; font-family: var(--font-mono); color: var(--text-tertiary);">
                <div style="display: flex; gap: 6px; align-items: center;">
                  <span style="display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--accent-cyan);"></span>
                  <span style="color: #fff;">protobuf_wire.json</span>
                </div>
                <span>UTF-8 • Proto3 Wire • LF</span>
              </div>
              <pre id="wire-decoded-output" style="height: 140px; overflow: auto; padding: 12px; font-family: var(--font-mono); font-size: 11px; line-height: 1.5; color: #d4d4d4; margin: 0; white-space: pre-wrap;">Awaiting packet decode request...</pre>
            </div>
          </div>
        </div>
      </div>
    `;

    // Hook into client activity for immediate local telemetry
    if (window.apiClient && !unsubscribeApiActivity) {
      unsubscribeApiActivity = window.apiClient.onActivity((entry) => {
        // Prepend local entry to capturedRequests buffer
        capturedRequests.unshift({
          time: entry.timestamp,
          method: entry.method,
          path: entry.url,
          ip: '127.0.0.1 (Local UI)',
          status: entry.status,
          duration: entry.duration,
          decoded: { summary: entry.ok ? 'UI ApiClient Dispatched' : (entry.error || 'Request Failed') }
        });
        if (capturedRequests.length > 1000) capturedRequests.pop();
        renderFilteredTable();
        updateStats();
      });
    }

    // Initial fetch from backend
    await fetchRequestHistory();

    // Start live polling if active
    if (isStreaming) {
      startPolling();
    }
  }

  /**
   * Fetch request history from /api/dashboard/requests
   */
  async function fetchRequestHistory() {
    try {
      const res = await window.apiClient.get('/api/dashboard/requests', { limit: 200 });
      if (res.ok && res.data) {
        const serverItems = Array.isArray(res.data) ? res.data : (res.data.requests || []);
        
        // Merge without duplicating identical time+path+method
        const existingKeys = new Set(capturedRequests.map(r => `${r.time}_${r.method}_${r.path}`));
        for (const item of serverItems) {
          const key = `${item.time}_${item.method}_${item.path}`;
          if (!existingKeys.has(key)) {
            capturedRequests.push(item);
            existingKeys.add(key);
          }
        }

        // Sort descending by time
        capturedRequests.sort((a, b) => (b.time || '').localeCompare(a.time || ''));
        if (capturedRequests.length > 1000) capturedRequests.length = 1000;

        renderFilteredTable();
        updateStats();
      }
    } catch (err) {
      console.warn('API Monitor poll error:', err);
    }
  }

  function startPolling() {
    stopPolling();
    pollInterval = setInterval(async () => {
      // Check if user is still on this route
      if (window.location.hash !== '#/logs/api') {
        stopPolling();
        return;
      }
      await fetchRequestHistory();
    }, currentPollRate);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  function updateStats() {
    const total = capturedRequests.length;
    const errors = capturedRequests.filter(r => {
      const st = r.status || (r.decoded && r.decoded.status);
      return st >= 400 || (r.decoded && r.decoded.summary && r.decoded.summary.toLowerCase().includes('failed'));
    }).length;
    const successes = total - errors;
    const rate = total > 0 ? Math.round((successes / total) * 100) : 100;

    const elTotal = document.getElementById('stat-total-reqs');
    const elSuccess = document.getElementById('stat-success-reqs');
    const elRate = document.getElementById('stat-success-rate');
    const elErrors = document.getElementById('stat-error-reqs');

    if (elTotal) elTotal.textContent = total.toLocaleString();
    if (elSuccess) elSuccess.textContent = successes.toLocaleString();
    if (elRate) elRate.textContent = `${rate}% success rate`;
    if (elErrors) elErrors.textContent = errors.toLocaleString();
  }

  function renderFilteredTable() {
    const container = document.getElementById('api-table-container');
    if (!container) return;

    let filtered = capturedRequests;

    // Apply Method Filter
    if (activeMethodFilter !== 'ALL') {
      filtered = filtered.filter(r => (r.method || 'GET').toUpperCase() === activeMethodFilter);
    }

    // Apply Status Filter
    if (activeStatusFilter === '2xx') {
      filtered = filtered.filter(r => {
        const s = r.status || 200;
        return s >= 200 && s < 300;
      });
    } else if (activeStatusFilter === '4xx') {
      filtered = filtered.filter(r => {
        const s = r.status || 0;
        return s >= 400 && s < 500;
      });
    } else if (activeStatusFilter === '5xx') {
      filtered = filtered.filter(r => {
        const s = r.status || 0;
        return s >= 500;
      });
    }

    // Apply Search Query
    if (activeFilterQuery) {
      const q = activeFilterQuery.toLowerCase();
      filtered = filtered.filter(r => {
        const p = (r.path || '').toLowerCase();
        const ip = (r.ip || '').toLowerCase();
        const summ = ((r.decoded && r.decoded.summary) || '').toLowerCase();
        return p.includes(q) || ip.includes(q) || summ.includes(q);
      });
    }

    const countLabel = document.getElementById('table-record-count');
    if (countLabel) countLabel.textContent = `${filtered.length} of ${capturedRequests.length} requests displayed`;

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--text-tertiary); font-size: 12.5px;">
          No API requests match current filter criteria.
        </div>
      `;
      return;
    }

    const rowsHtml = filtered.map((req, idx) => {
      const status = req.status || 200;
      let badgeVariant = 'emerald';
      if (status >= 400 && status < 500) badgeVariant = 'amber';
      if (status >= 500) badgeVariant = 'rose';

      const methodBadge = req.method === 'GET' ? 'cyan' : (req.method === 'POST' ? 'emerald' : 'neutral');
      const summaryText = (req.decoded && req.decoded.summary) || '';

      return `
        <tr style="cursor: pointer;" onclick="window.LogsApiModule.inspectRequest(${idx})">
          <td><code style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 11px;">${req.time || '—'}</code></td>
          <td>${window.UI.Badge(req.method || 'GET', methodBadge)}</td>
          <td><span class="badge badge-${badgeVariant}">${status}</span></td>
          <td style="font-family: var(--font-mono); font-size: 12px; color: #fff; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${req.path || '/'}
            ${summaryText ? `<span style="color: var(--text-tertiary); font-size: 11px; margin-left: 6px;">(${summaryText})</span>` : ''}
          </td>
          <td><code style="font-family: var(--font-mono); color: var(--text-secondary); font-size: 11.5px;">${req.ip || '127.0.0.1'}</code></td>
          <td>
            <span style="color: var(--accent-cyan); font-size: 11.5px; font-family: var(--font-mono);">
              ${req.duration ? `${req.duration}ms` : '—'}
            </span>
          </td>
          <td style="text-align: right;">
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="event.stopPropagation(); window.LogsApiModule.inspectRequest(${idx})">Inspect</button>
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = window.UI.Table(
      ['Time', 'Method', 'Status', 'Request Path', 'Client IP', 'Latency', ''],
      rowsHtml
    );
  }

  // --- Exposed Global Handlers for DOM Interaction ---
  window.LogsApiModule = {
    render: renderLogsApi,

    toggleStream() {
      isStreaming = !isStreaming;
      const pill = document.getElementById('stream-status-pill');
      const btn = document.getElementById('toggle-stream-btn');

      if (isStreaming) {
        startPolling();
        if (pill) {
          pill.className = 'badge badge-emerald';
          pill.innerHTML = `<span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--accent-emerald); box-shadow: 0 0 6px var(--accent-emerald); margin-right: 4px;"></span>LIVE STREAM`;
        }
        if (btn) btn.textContent = '⏸ Pause Stream';
        window.UI.Toast('Live telemetry stream resumed', 'info');
      } else {
        stopPolling();
        if (pill) {
          pill.className = 'badge badge-amber';
          pill.innerHTML = `PAUSED`;
        }
        if (btn) btn.textContent = '▶ Resume Stream';
        window.UI.Toast('Live telemetry stream paused', 'warning');
      }
    },

    setPollRate(val) {
      currentPollRate = parseInt(val, 10) || 2000;
      if (isStreaming) {
        startPolling();
      }
      window.UI.Toast(`Stream rate set to ${currentPollRate / 1000}s`, 'info');
    },

    async refreshStream() {
      await fetchRequestHistory();
      window.UI.Toast('Telemetry stream refreshed', 'success');
    },

    onSearchChange(val) {
      activeFilterQuery = val.trim();
      renderFilteredTable();
    },

    onMethodChange(val) {
      activeMethodFilter = val;
      renderFilteredTable();
    },

    onStatusChange(val) {
      activeStatusFilter = val;
      renderFilteredTable();
    },

    resetFilters() {
      activeFilterQuery = '';
      activeMethodFilter = 'ALL';
      activeStatusFilter = 'ALL';
      const sInput = document.getElementById('api-search-input');
      const mSel = document.getElementById('api-method-select');
      const stSel = document.getElementById('api-status-select');
      if (sInput) sInput.value = '';
      if (mSel) mSel.value = 'ALL';
      if (stSel) stSel.value = 'ALL';
      renderFilteredTable();
    },

    promptClearBuffer() {
      window.UI.Confirm(
        'Clear Request Telemetry Buffer',
        'Are you sure you want to flush the Gateway in-memory request ring buffer? This action cannot be undone.',
        async () => {
          const res = await window.apiClient.post('/api/dashboard/requests/clear');
          if (res.ok) {
            capturedRequests = [];
            renderFilteredTable();
            updateStats();
            window.UI.Toast('Request telemetry buffer cleared successfully', 'success');
          } else {
            window.UI.Toast(res.error || 'Failed to clear buffer', 'error');
          }
        },
        true
      );
    },

    exportLogs() {
      if (capturedRequests.length === 0) {
        window.UI.Toast('No logs available to export', 'warning');
        return;
      }
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(capturedRequests, null, 2));
      const a = document.createElement('a');
      a.setAttribute('href', dataStr);
      a.setAttribute('download', `api_monitor_logs_${Date.now()}.json`);
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.UI.Toast('Logs exported as JSON', 'success');
    },

    inspectRequest(idx) {
      const req = capturedRequests[idx];
      if (!req) return;

      const bodyHtml = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: rgba(0,0,0,0.25); padding: 12px; border-radius: 6px; border: 1px solid var(--border-subtle);">
            <div><span style="color: var(--text-tertiary);">Timestamp:</span> <strong style="color: #fff;">${req.time || '—'}</strong></div>
            <div><span style="color: var(--text-tertiary);">Method:</span> <strong style="color: var(--accent-cyan);">${req.method || 'GET'}</strong></div>
            <div><span style="color: var(--text-tertiary);">Status:</span> <strong style="color: var(--accent-emerald);">${req.status || 200}</strong></div>
            <div><span style="color: var(--text-tertiary);">Duration:</span> <strong style="color: #fff;">${req.duration ? `${req.duration}ms` : '—'}</strong></div>
            <div><span style="color: var(--text-tertiary);">Client IP:</span> <code style="color: var(--accent-amber);">${req.ip || '127.0.0.1'}</code></div>
            <div><span style="color: var(--text-tertiary);">Path:</span> <code style="color: #fff;">${req.path || '/'}</code></div>
          </div>

          ${req.decoded ? `
            <div>
              <div style="font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; font-size: 11.5px; text-transform: uppercase;">Decoded Context</div>
              <pre style="background: rgba(0,0,0,0.35); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle); color: var(--accent-cyan); font-family: var(--font-mono); font-size: 11.5px; max-height: 180px; overflow-y: auto;">${JSON.stringify(req.decoded, null, 2)}</pre>
            </div>
          ` : ''}

          <div>
            <div style="font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; font-size: 11.5px; text-transform: uppercase;">Raw Record Object</div>
            <pre style="background: rgba(0,0,0,0.45); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle); color: var(--text-primary); font-family: var(--font-mono); font-size: 11px; max-height: 160px; overflow-y: auto;">${JSON.stringify(req, null, 2)}</pre>
          </div>
        </div>
      `;

      const actionsHtml = `
        <button class="btn btn-primary" onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(req).replace(/"/g, '&quot;')})); window.UI.Toast('Copied request payload', 'success');">Copy JSON</button>
        <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Close</button>
      `;

      window.UI.Modal(`API Request Inspector: ${req.method} ${req.path}`, bodyHtml, actionsHtml);
    },

    insertSampleHex() {
      const input = document.getElementById('wire-hex-input');
      if (input) {
        // Sample Free Fire OB17 Login Handshake Header Wire Hex
        input.value = '0801121031303030315f617574685f746f6b656e189601';
        window.UI.Toast('Inserted sample 1.39 auth wire hex', 'info');
      }
    },

    formatMonacoSyntax(data) {
      const jsonStr = JSON.stringify(data, null, 2);
      const escaped = jsonStr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return escaped.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
        let cls = 'color: #9cdcfe;'; // Monaco identifier
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'color: #4ec9b0; font-weight: 600;'; // Key / Tag name
          } else {
            cls = 'color: #ce9178;'; // String literal
          }
        } else if (/true|false/.test(match)) {
          cls = 'color: #569cd6; font-weight: 600;'; // Boolean
        } else if (/null/.test(match)) {
          cls = 'color: #808080;'; // Null
        } else {
          cls = 'color: #b5cea8;'; // Number / Varint
        }
        return `<span style="${cls}">${match}</span>`;
      });
    },

    async decodeWirePacket() {
      const input = document.getElementById('wire-hex-input');
      const output = document.getElementById('wire-decoded-output');
      if (!input || !output) return;

      const raw = input.value.trim();
      if (!raw) {
        window.UI.Toast('Please enter hex or base64 payload', 'warning');
        return;
      }

      output.innerHTML = '<span style="color: var(--text-tertiary);">Decoding against IND PROJECT Protobuf Wire decoder...</span>';

      try {
        const payload = raw.includes(' ') || /^[0-9a-fA-F]+$/.test(raw) ? { hex: raw } : { base64: raw };
        const res = await window.apiClient.post('/api/dashboard/decode', payload);
        if (res.ok && res.data) {
          output.innerHTML = window.LogsApiModule.formatMonacoSyntax(res.data);
          window.UI.Toast('Wire payload decoded successfully', 'success');
        } else {
          output.innerHTML = `<span style="color: var(--accent-rose);">Decode Failed: ${res.error || 'Invalid protobuf format'}</span>`;
          window.UI.Toast(res.error || 'Decode failed', 'error');
        }
      } catch (err) {
        output.innerHTML = `<span style="color: var(--accent-rose);">Error: ${err.message}</span>`;
      }
    }
  };

  // Register on window.Modules
  window.Modules = window.Modules || {};
  window.Modules.LogsApi = renderLogsApi;

  // Register in Router with resilient hook
  function hookRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/logs/api', renderLogsApi);
    }
  }
  hookRoute();
  document.addEventListener('DOMContentLoaded', () => { setTimeout(hookRoute, 0); });
  window.addEventListener('load', hookRoute);
})();
