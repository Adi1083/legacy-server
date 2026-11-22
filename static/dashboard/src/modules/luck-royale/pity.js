/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.4: Lucky Meter & Pity Management (pity.js)
 * Clean macOS dark glass design system, zero emojis, authentic backend meter APIs.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Pity = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Lucky Meter & Pity configurations...');

  const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;

  // Fetch machines and player meter state
  const [machRes, meterRes] = await Promise.all([
    window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 }),
    window.apiClient.get('/api/admin/luck-royale/meters', { account_id: aid })
  ]);

  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];
  const playerMeters = (meterRes.ok && meterRes.data && meterRes.data.meters) ? meterRes.data.meters : {};

  // Build 4-card metric strip
  const metricCards = machines.slice(0, 4).map(m => {
    const curMeter = playerMeters[m.chest_id] || 0;
    const ceiling = m.rare_item_max || 100;
    const pct = Math.min(100, Math.floor((curMeter / ceiling) * 100));

    return `
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <div>
            <div class="stat-label">${C.escapeHtml(m.display_name || m.chest_name)}</div>
            <div class="stat-value" style="color: var(--accent-amber); font-family: var(--font-mono);">${ceiling} <span style="font-size: 11px; color: var(--text-tertiary);">Ceiling</span></div>
          </div>
          ${curMeter >= ceiling ? window.UI.Badge('READY', 'amber') : window.UI.Badge(curMeter + ' pts', 'cyan')}
        </div>
        <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; margin-top: 8px;">
          <div style="width: ${pct}%; height: 100%; background: ${pct >= 100 ? 'var(--accent-amber)' : 'var(--accent-cyan)'};"></div>
        </div>
      </div>
    `;
  }).join('');

  // Machine Configuration Table Rows
  const configRows = machines.map(m => {
    const ceiling = m.rare_item_max || 100;
    return `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">${m.chest_id}</code></td>
        <td style="font-weight: 600; color: #fff;">${C.escapeHtml(m.display_name || m.chest_name)}</td>
        <td>${C.coinBadge(m.coin_type)}</td>
        <td>
          <input type="number" id="pity-input-${m.chest_id}" class="form-input" style="width: 110px; padding: 4px 8px; font-size: 12px; font-family: var(--font-mono);" value="${ceiling}" min="1">
        </td>
        <td>
          <span style="font-size: 11.5px; color: var(--text-secondary);">
            Guarantees Super Rare on roll ${ceiling + 1}
          </span>
        </td>
        <td>
          <button class="btn btn-primary" style="padding: 4px 10px; font-size: 11px;" onclick="window.LuckRoyale.UpdatePityCeiling(${m.chest_id})">
            Save
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Player State Rows
  const playerRows = machines.map(m => {
    const curMeter = playerMeters[m.chest_id] || 0;
    const ceiling = m.rare_item_max || 100;
    const isGuaranteed = curMeter >= ceiling;

    return `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">${m.chest_id}</code></td>
        <td style="font-weight: 600; color: #fff;">${C.escapeHtml(m.display_name || m.chest_name)}</td>
        <td>
          <span style="font-family: var(--font-mono); font-weight: 700; color: ${isGuaranteed ? 'var(--accent-amber)' : 'var(--text-primary)'}; font-size: 13px;">
            ${curMeter}
          </span>
          <span style="font-size: 11px; color: var(--text-tertiary);">/ ${ceiling}</span>
        </td>
        <td>
          ${isGuaranteed ? window.UI.Badge('GUARANTEED NEXT ROLL', 'amber') : window.UI.Badge('ACCUMULATING', 'cyan')}
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.AdjustMeter(${aid}, ${m.chest_id}, 0)">Reset 0</button>
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.AdjustMeter(${aid}, ${m.chest_id}, ${curMeter + 10})">+10</button>
            <button class="btn btn-primary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.AdjustMeter(${aid}, ${m.chest_id}, ${ceiling - 1})">Force Pity Ready</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Lucky Meter & Guaranteed Pity',
        'Configure jackpot thresholds and inspect real-time lucky accumulation counters per account',
        null,
        'activity'
      )}

      ${C.renderSubNav('pity')}

      <!-- 4-Card Pity Metrics -->
      <div class="grid-4" style="margin-bottom: 24px;">
        ${metricCards}
      </div>

      <!-- Symmetrical 50/50 Split View -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <!-- Left: Pity Ceilings Table -->
        <div class="glass-card" style="padding: 0; overflow: hidden;">
          <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); font-weight: 600; font-size: 13px; color: #fff;">
            Machine Pity Ceilings (System Wide)
          </div>
          <div style="padding: 0;">
            ${window.UI.Table(['ID', 'Machine', 'Currency', 'Pity Ceiling', 'Mechanic', 'Action'], configRows)}
          </div>
        </div>

        <!-- Right: Active Player Meter Dossier -->
        <div class="glass-card" style="padding: 0; overflow: hidden;">
          <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; font-size: 13px; color: #fff;">Active Player Meters (UID ${aid})</span>
            ${window.UI.Badge('SYNCHRONIZED', 'emerald')}
          </div>
          <div style="padding: 0;">
            ${window.UI.Table(['ID', 'Machine', 'Current Lucky', 'Pity Status', 'Adjust State'], playerRows)}
          </div>
        </div>
      </div>
    </div>
  `;
};

window.LuckRoyale.UpdatePityCeiling = async function (chestId) {
  const input = document.getElementById(`pity-input-${chestId}`);
  if (!input) return;
  const val = parseInt(input.value, 10);
  if (isNaN(val) || val <= 0) {
    window.UI.Toast('Please enter a valid positive number.', 'warning');
    return;
  }
  const res = await window.apiClient.put('/api/admin/luck-royale/machines', {
    chest_id: chestId,
    rare_item_max: val
  });
  if (res.ok) {
    window.UI.Toast(`Machine #${chestId} pity ceiling updated to ${val}.`, 'success');
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to update pity ceiling.', 'danger');
  }
};
