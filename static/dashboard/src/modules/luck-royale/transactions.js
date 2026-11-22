/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.10: Spin Audit Ledger (transactions.js)
 * Clean macOS dark glass design system, zero emojis, internal scroll container.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Transactions = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Spin Audit Ledger...');

  const filterAid = window.LuckRoyale._txFilterAid || '';
  const filterCid = window.LuckRoyale._txFilterCid || '';
  const filterJackpot = Boolean(window.LuckRoyale._txFilterJackpot);

  const queryParams = { limit: 100 };
  if (filterAid) queryParams.account_id = filterAid;
  if (filterCid) queryParams.chest_id = filterCid;

  const res = await window.apiClient.get('/api/admin/luck-royale/transactions', queryParams);
  let txs = (res.ok && res.data && res.data.transactions) ? res.data.transactions : [];

  if (filterJackpot) {
    txs = txs.filter(t => t.has_big_reward);
  }

  const rows = txs.map(t => {
    const isJackpot = Boolean(t.has_big_reward);
    const rewardMeta = C.lookupItem(t.reward_item_id || 0);

    return `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--text-tertiary);">${C.formatTimestamp(t.timestamp)}</code></td>
        <td>
          <code style="font-family: var(--font-mono); font-weight: 600; color: var(--accent-cyan); cursor: pointer;" onclick="window.playerContext.setAccountId(${t.account_id}).then(() => window.appRouter.handleRoute())" title="Load Account Context">
            ${t.account_id}
          </code>
        </td>
        <td>
          <span style="font-weight: 500; color: #fff;">Machine #${t.machine_id}</span>
        </td>
        <td>
          ${t.gacha_type === 1 ? window.UI.Badge('1x Roll', 'neutral') : window.UI.Badge('10x Special', 'cyan')}
        </td>
        <td>
          <span style="font-family: var(--font-mono); font-weight: 600; color: #fff;">${t.cost_amount || 0}</span>
          <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 2px;">${t.cost_type === 2 ? 'Diamonds' : 'Gold'}</span>
        </td>
        <td>
          <div style="display: flex; align-items: center; gap: 8px;">
            ${C.renderItemImage(null, rewardMeta.name, 28)}
            <div>
              <div style="font-weight: 600; color: #fff; font-size: 12px;">${C.escapeHtml(rewardMeta.name)}</div>
              <div style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-cyan);">ID: ${t.reward_item_id || '—'}</div>
            </div>
          </div>
        </td>
        <td>
          ${isJackpot ? window.UI.Badge('JACKPOT', 'amber') : window.UI.Badge('NORMAL', 'neutral')}
        </td>
      </tr>
    `;
  }).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Spin Audit Ledger',
        'Authoritative immutable audit log of all Luck Royale turntable rolls, currency burn, and item grants',
        null,
        'scroll'
      )}

      ${C.renderSubNav('transactions')}

      <!-- Filter Controls -->
      <div class="glass-card" style="padding: 14px 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div style="display: flex; align-items: center; gap: 6px;">
          <label style="font-size: 11px; color: var(--text-tertiary);">Account UID:</label>
          <input type="number" id="tx-filter-aid" class="form-input" style="width: 140px; padding: 4px 8px; font-size: 12px;" placeholder="All Accounts" value="${filterAid}">
        </div>

        <div style="display: flex; align-items: center; gap: 6px;">
          <label style="font-size: 11px; color: var(--text-tertiary);">Machine:</label>
          <select id="tx-filter-cid" class="form-select" style="width: 150px; padding: 4px 8px; font-size: 12px;">
            <option value="">All Machines</option>
            <option value="3" ${filterCid === '3' ? 'selected' : ''}>Diamond (#3)</option>
            <option value="4" ${filterCid === '4' ? 'selected' : ''}>Weapon (#4)</option>
            <option value="5" ${filterCid === '5' ? 'selected' : ''}>Gold (#5)</option>
            <option value="6" ${filterCid === '6' ? 'selected' : ''}>Incubator (#6)</option>
          </select>
        </div>

        <label style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); cursor: pointer;">
          <input type="checkbox" id="tx-filter-jackpot" ${filterJackpot ? 'checked' : ''}>
          <span>Jackpots Only</span>
        </label>

        <button class="btn btn-primary" style="margin-left: auto; padding: 5px 14px; font-size: 11.5px;" onclick="window.LuckRoyale.ApplyTxFilters()">
          Filter Ledger
        </button>
      </div>

      <!-- Table Container with Internal Scroll -->
      <div class="glass-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; font-size: 13px; color: #fff;">
            Transaction Records (${txs.length} entries shown)
          </div>
          <div style="font-size: 11px; color: var(--text-tertiary);">
            Query limit: 100 rows
          </div>
        </div>
        <div style="max-height: 480px; overflow-y: auto;">
          ${window.UI.Table(['Timestamp', 'Account UID', 'Machine', 'Roll Type', 'Cost Paid', 'Reward Item Granted', 'Jackpot Status'], rows, 'No transactions matching query.')}
        </div>
      </div>
    </div>
  `;
};

window.LuckRoyale.ApplyTxFilters = function () {
  const aidInput = document.getElementById('tx-filter-aid');
  const cidInput = document.getElementById('tx-filter-cid');
  const jpInput = document.getElementById('tx-filter-jackpot');

  window.LuckRoyale._txFilterAid = aidInput ? aidInput.value.trim() : '';
  window.LuckRoyale._txFilterCid = cidInput ? cidInput.value : '';
  window.LuckRoyale._txFilterJackpot = jpInput ? jpInput.checked : false;

  window.appRouter.handleRoute();
};
