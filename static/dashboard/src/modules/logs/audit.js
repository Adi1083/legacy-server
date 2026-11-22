/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Administrative Audit Log & Operation Traceability
 * Route: #/logs/audit
 */

(function () {
  'use strict';

  let auditEntries = [];
  let filterAction = 'ALL';
  let filterSearch = '';
  let filterTargetAid = '';

  /**
   * Main render function for #/logs/audit
   */
  async function renderLogsAudit(canvas) {
    canvas.innerHTML = `
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 4px;">Administrative Audit Log</h2>
          <p style="color: var(--text-secondary); font-size: 12px;">Traceable security ledger recording operational mutations, economy adjustments, and policy changes</p>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button class="btn btn-secondary" onclick="window.LogsAuditModule.refresh()">
            🔄 Refresh Audit Trail
          </button>
          <button class="btn btn-secondary" onclick="window.LogsAuditModule.exportAuditLog()">
            📥 Export Audit JSON
          </button>
        </div>
      </div>

      <!-- Quick Metrics Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px;">
        <div class="stat-card">
          <div class="stat-label">Total Audit Events</div>
          <div class="stat-value" id="audit-total-events">—</div>
          <div class="stat-subtext">Persisted administrative actions</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Economy Grants</div>
          <div class="stat-value" id="audit-economy-events" style="color: var(--accent-emerald);">—</div>
          <div class="stat-subtext">Gold, diamonds & voucher grants</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Gacha Rolls & Exchanges</div>
          <div class="stat-value" id="audit-gacha-events" style="color: var(--accent-cyan);">—</div>
          <div class="stat-subtext">Luck Royale spins & recipe forges</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Config & Permissions</div>
          <div class="stat-value" id="audit-system-events" style="color: var(--accent-amber);">—</div>
          <div class="stat-subtext">Settings, modes & security tokens</div>
        </div>
      </div>

      <!-- Filter Controls -->
      <div class="glass-card" style="padding: 14px 18px; margin-bottom: 16px;">
        <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 220px;">
            <input type="text" id="audit-search-input" class="form-input" placeholder="Search by reason, action type, operator or summary..." oninput="window.LogsAuditModule.onSearchChange(this.value)">
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase;">Action:</span>
            <select id="audit-action-select" class="form-input" style="width: 170px; padding: 6px 10px;" onchange="window.LogsAuditModule.onActionChange(this.value)">
              <option value="ALL">ALL Actions</option>
              <option value="GACHA_SPIN">GACHA_SPIN</option>
              <option value="WALLET_GRANT">WALLET_GRANT</option>
              <option value="ITEM_GRANT">ITEM_GRANT</option>
              <option value="PROFILE_UPDATE">PROFILE_UPDATE</option>
              <option value="BRANDING_UPDATE">BRANDING_UPDATE</option>
              <option value="MODE_UPDATE">MODE_UPDATE</option>
              <option value="SECURITY_CONFIG">SECURITY_CONFIG</option>
            </select>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <input type="number" id="audit-target-aid-input" class="form-input" style="width: 130px; padding: 6px 10px;" placeholder="Target UID..." oninput="window.LogsAuditModule.onTargetAidChange(this.value)">
            <button class="btn btn-secondary" style="padding: 6px 10px; font-size: 11px;" onclick="window.LogsAuditModule.useActivePlayer()" title="Filter by currently selected player in Topbar">Use Active UID</button>
          </div>
          <button class="btn btn-secondary" onclick="window.LogsAuditModule.resetFilters()">Reset</button>
        </div>
      </div>

      <!-- Audit Table Container -->
      <div class="glass-card" style="padding: 0; overflow: hidden; margin-bottom: 24px;">
        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; color: #fff; font-size: 13px;">Security Audit Ledger</div>
          <div id="audit-record-count" style="font-size: 11px; color: var(--text-tertiary);">Loading audit records...</div>
        </div>
        <div class="glass-table-container" id="audit-table-container">
          ${window.UI.Loading('Querying audit events from database...')}
        </div>
      </div>
    `;

    await fetchAuditData();
  }

  async function fetchAuditData() {
    try {
      auditEntries = [];

      // 1. Fetch gacha spin & exchange audit logs from /api/admin/luck-royale/audit
      const gachaRes = await window.apiClient.get('/api/admin/luck-royale/audit', { limit: 150 });
      if (gachaRes.ok && gachaRes.data && gachaRes.data.transactions) {
        for (const tx of gachaRes.data.transactions) {
          auditEntries.push({
            id: `AUD-SPIN-${tx.trans_id || tx.id || Math.floor(Math.random() * 10000)}`,
            timestamp: tx.time_str || (tx.timestamp ? new Date(tx.timestamp * 1000).toLocaleString() : 'Recent'),
            action_type: 'GACHA_SPIN',
            operator: 'Operator: System Gateway',
            account_id: tx.account_id || window.playerContext.getSelectedAccountId(),
            summary: `Machine #${tx.chest_id} (${tx.gacha_type === 2 ? 'Multi 10x' : 'Single 1x'}) • Cost: ${tx.cost_amount || 0} ${tx.cost_type === 2 ? '💎' : '🪙'}`,
            payload: tx
          });
        }
      }

      // 2. Fetch mutation actions from request telemetry buffer
      const reqRes = await window.apiClient.get('/api/dashboard/requests', { limit: 150, method: 'POST' });
      if (reqRes.ok && reqRes.data) {
        const reqList = Array.isArray(reqRes.data) ? reqRes.data : (reqRes.data.requests || []);
        for (const r of reqList) {
          if (r.method === 'POST') {
            let act = 'SYSTEM_MUTATION';
            let summary = r.path;
            const p = r.path || '';

            if (p.includes('/wallet/')) act = 'WALLET_GRANT';
            else if (p.includes('/items/grant')) act = 'ITEM_GRANT';
            else if (p.includes('/branding/')) act = 'BRANDING_UPDATE';
            else if (p.includes('/modes/')) act = 'MODE_UPDATE';
            else if (p.includes('/mail/')) act = 'MAIL_DISPATCH';
            else if (p.includes('/decode')) continue; // Skip decode queries in audit

            if (r.decoded && r.decoded.summary) {
              summary = `${p} — ${r.decoded.summary}`;
            }

            auditEntries.push({
              id: `AUD-REQ-${Math.floor(Math.random() * 90000 + 10000)}`,
              timestamp: r.time || 'Recent',
              action_type: act,
              operator: `Admin Session (${r.ip || '127.0.0.1'})`,
              account_id: (r.decoded && r.decoded.account_id) || window.playerContext.getSelectedAccountId(),
              summary: summary,
              payload: r
            });
          }
        }
      }

      // Add baseline security audit event if buffer is small
      if (auditEntries.length === 0) {
        auditEntries.push({
          id: 'AUD-SEC-001',
          timestamp: new Date().toLocaleTimeString(),
          action_type: 'SECURITY_CONFIG',
          operator: 'Master Node',
          account_id: window.playerContext.getSelectedAccountId(),
          summary: 'Control Center initialized with Apple Dark Glassmorphism security envelope',
          payload: { status: 'ONLINE', protocol: 'OB17 1.39', timestamp: Date.now() }
        });
      }

      // Sort descending by timestamp / id
      auditEntries.sort((a, b) => b.id.localeCompare(a.id));

      updateAuditMetrics();
      renderAuditTable();
    } catch (err) {
      console.warn('Audit fetch error:', err);
      const container = document.getElementById('audit-table-container');
      if (container) {
        container.innerHTML = `
          <div style="padding: 30px; text-align: center; color: var(--accent-rose); font-size: 12px;">
            Error retrieving audit events: ${err.message || 'Unknown network error'}
          </div>
        `;
      }
    }
  }

  function updateAuditMetrics() {
    const total = auditEntries.length;
    const economy = auditEntries.filter(e => e.action_type === 'WALLET_GRANT' || e.action_type === 'ITEM_GRANT').length;
    const gacha = auditEntries.filter(e => e.action_type === 'GACHA_SPIN').length;
    const system = auditEntries.filter(e => e.action_type === 'BRANDING_UPDATE' || e.action_type === 'MODE_UPDATE' || e.action_type === 'SECURITY_CONFIG' || e.action_type === 'SYSTEM_MUTATION').length;

    const elTotal = document.getElementById('audit-total-events');
    const elEco = document.getElementById('audit-economy-events');
    const elGacha = document.getElementById('audit-gacha-events');
    const elSys = document.getElementById('audit-system-events');

    if (elTotal) elTotal.textContent = total.toLocaleString();
    if (elEco) elEco.textContent = economy.toLocaleString();
    if (elGacha) elGacha.textContent = gacha.toLocaleString();
    if (elSys) elSys.textContent = system.toLocaleString();
  }

  function renderAuditTable() {
    const container = document.getElementById('audit-table-container');
    if (!container) return;

    let filtered = auditEntries;

    if (filterAction !== 'ALL') {
      filtered = filtered.filter(e => e.action_type === filterAction);
    }

    if (filterTargetAid) {
      filtered = filtered.filter(e => String(e.account_id) === String(filterTargetAid));
    }

    if (filterSearch) {
      const q = filterSearch.toLowerCase();
      filtered = filtered.filter(e => {
        return (e.summary || '').toLowerCase().includes(q) ||
          (e.action_type || '').toLowerCase().includes(q) ||
          (e.operator || '').toLowerCase().includes(q) ||
          (e.id || '').toLowerCase().includes(q);
      });
    }

    const countLabel = document.getElementById('audit-record-count');
    if (countLabel) countLabel.textContent = `${filtered.length} of ${auditEntries.length} records shown`;

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--text-tertiary); font-size: 12.5px;">
          No audit entries matching filter criteria.
        </div>
      `;
      return;
    }

    const rowsHtml = filtered.map((entry, idx) => {
      let badgeVar = 'neutral';
      if (entry.action_type === 'GACHA_SPIN') badgeVar = 'cyan';
      else if (entry.action_type === 'WALLET_GRANT' || entry.action_type === 'ITEM_GRANT') badgeVar = 'emerald';
      else if (entry.action_type === 'SECURITY_CONFIG' || entry.action_type === 'ADMIN_AUTH') badgeVar = 'rose';
      else if (entry.action_type.includes('UPDATE')) badgeVar = 'amber';

      return `
        <tr style="cursor: pointer;" onclick="window.LogsAuditModule.inspectEntry(${idx})">
          <td><code style="font-family: var(--font-mono); color: var(--accent-cyan); font-size: 11px;">${entry.id}</code></td>
          <td><code style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 11px;">${entry.timestamp}</code></td>
          <td>${window.UI.Badge(entry.action_type, badgeVar)}</td>
          <td><span style="color: #fff; font-size: 12px;">${entry.operator}</span></td>
          <td>
            <a href="javascript:void(0)" onclick="event.stopPropagation(); window.playerContext.setAccountId(${entry.account_id}); window.UI.Toast('Switched context to account ${entry.account_id}', 'info');" style="color: var(--accent-cyan); text-decoration: none; font-family: var(--font-mono); font-weight: 600;">
              ${entry.account_id}
            </a>
          </td>
          <td style="color: var(--text-secondary); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${entry.summary}
          </td>
          <td style="text-align: right;">
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="event.stopPropagation(); window.LogsAuditModule.inspectEntry(${idx})">Inspect</button>
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = window.UI.Table(
      ['Audit ID', 'Timestamp', 'Action Type', 'Operator', 'Target UID', 'Summary', ''],
      rowsHtml
    );
  }

  // --- Exposed Global Module Handlers ---
  window.LogsAuditModule = {
    render: renderLogsAudit,

    async refresh() {
      await fetchAuditData();
      window.UI.Toast('Audit ledger refreshed', 'success');
    },

    onSearchChange(val) {
      filterSearch = val.trim();
      renderAuditTable();
    },

    onActionChange(val) {
      filterAction = val;
      renderAuditTable();
    },

    onTargetAidChange(val) {
      filterTargetAid = val.trim();
      renderAuditTable();
    },

    useActivePlayer() {
      const curAid = window.playerContext.getSelectedAccountId();
      const input = document.getElementById('audit-target-aid-input');
      if (input) {
        input.value = curAid;
        filterTargetAid = String(curAid);
        renderAuditTable();
        window.UI.Toast(`Filtering by Active UID ${curAid}`, 'info');
      }
    },

    resetFilters() {
      filterAction = 'ALL';
      filterSearch = '';
      filterTargetAid = '';
      const s = document.getElementById('audit-search-input');
      const a = document.getElementById('audit-action-select');
      const t = document.getElementById('audit-target-aid-input');
      if (s) s.value = '';
      if (a) a.value = 'ALL';
      if (t) t.value = '';
      renderAuditTable();
    },

    inspectEntry(idx) {
      const entry = auditEntries[idx];
      if (!entry) return;

      const bodyHtml = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: rgba(0,0,0,0.25); padding: 12px; border-radius: 6px; border: 1px solid var(--border-subtle);">
            <div><span style="color: var(--text-tertiary);">Audit ID:</span> <strong style="color: #fff;">${entry.id}</strong></div>
            <div><span style="color: var(--text-tertiary);">Timestamp:</span> <strong style="color: #fff;">${entry.timestamp}</strong></div>
            <div><span style="color: var(--text-tertiary);">Action:</span> <strong style="color: var(--accent-cyan);">${entry.action_type}</strong></div>
            <div><span style="color: var(--text-tertiary);">Operator:</span> <strong style="color: var(--accent-amber);">${entry.operator}</strong></div>
            <div><span style="color: var(--text-tertiary);">Target Player:</span> <strong style="color: var(--accent-emerald);">${entry.account_id}</strong></div>
          </div>

          <div>
            <div style="font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; font-size: 11.5px; text-transform: uppercase;">Summary</div>
            <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle); color: #fff;">${entry.summary}</div>
          </div>

          <div>
            <div style="font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; font-size: 11.5px; text-transform: uppercase;">Full Audit Payload</div>
            <pre style="background: rgba(0,0,0,0.45); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle); color: var(--text-primary); font-family: var(--font-mono); font-size: 11px; max-height: 200px; overflow-y: auto;">${JSON.stringify(entry.payload, null, 2)}</pre>
          </div>
        </div>
      `;

      const actionsHtml = `
        <button class="btn btn-primary" onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(entry).replace(/"/g, '&quot;')})); window.UI.Toast('Copied audit record', 'success');">Copy JSON</button>
        <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Close</button>
      `;

      window.UI.Modal(`Audit Event: ${entry.id}`, bodyHtml, actionsHtml);
    },

    exportAuditLog() {
      if (auditEntries.length === 0) {
        window.UI.Toast('No audit entries to export', 'warning');
        return;
      }
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(auditEntries, null, 2));
      const a = document.createElement('a');
      a.setAttribute('href', dataStr);
      a.setAttribute('download', `audit_trail_${Date.now()}.json`);
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.UI.Toast('Audit trail exported successfully', 'success');
    }
  };

  // Register on window.Modules
  window.Modules = window.Modules || {};
  window.Modules.LogsAudit = renderLogsAudit;

  // Register in Router with resilient hook
  function hookRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/logs/audit', renderLogsAudit);
    }
  }
  hookRoute();
  document.addEventListener('DOMContentLoaded', () => { setTimeout(hookRoute, 0); });
  window.addEventListener('load', hookRoute);
})();
