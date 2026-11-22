/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Transaction Explorer & Gacha Ledger
 * Route: #/logs/transactions (also aliased to #/luck-royale/transactions)
 */

(function () {
  'use strict';

  let transactionsList = [];
  let filterAid = '';
  let filterChestId = 'ALL';
  let filterType = 'ALL';
  let filterJackpotOnly = false;
  let filterLimit = 50;

  const MACHINE_NAMES = {
    3: 'Diamond Royale',
    4: 'Weapon Royale',
    5: 'Gold Royale',
    6: 'Incubator Forge'
  };

  /**
   * Main render function for #/logs/transactions
   */
  async function renderTransactions(canvas) {
    canvas.innerHTML = `
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 4px;">Transaction Explorer</h2>
          <p style="color: var(--text-secondary); font-size: 12px;">Complete audit ledger of Luck Royale spins, economy burns, item awards & lucky meters</p>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button class="btn btn-primary" onclick="window.LogsTransactionsModule.openManualTxModal()">
            ➕ Record Transaction
          </button>
          <button class="btn btn-secondary" onclick="window.LogsTransactionsModule.refresh()">
            🔄 Refresh Ledger
          </button>
          <button class="btn btn-secondary" onclick="window.LogsTransactionsModule.exportCSV()">
            📥 Export CSV
          </button>
          <button class="btn btn-secondary" onclick="window.LogsTransactionsModule.exportJSON()">
            📥 Export JSON
          </button>
        </div>
      </div>

      <!-- Analytics Stats Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px;">
        <div class="stat-card">
          <div class="stat-label">Total Transactions</div>
          <div class="stat-value" id="tx-stat-total">—</div>
          <div class="stat-subtext">Recorded in gacha_transactions</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Diamonds Burned</div>
          <div class="stat-value" id="tx-stat-diamonds" style="color: var(--accent-cyan);">—</div>
          <div class="stat-subtext">Premium currency sunk</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Gold Burned</div>
          <div class="stat-value" id="tx-stat-gold" style="color: var(--accent-amber);">—</div>
          <div class="stat-subtext">Free currency sunk</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Grand Prize Jackpots</div>
          <div class="stat-value" id="tx-stat-jackpots" style="color: var(--accent-emerald);">—</div>
          <div class="stat-subtext">Jackpot drops triggered</div>
        </div>
      </div>

      <!-- Filter Bar -->
      <div class="glass-card" style="padding: 14px 18px; margin-bottom: 16px;">
        <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
          <div style="display: flex; gap: 6px; align-items: center;">
            <input type="number" id="tx-filter-aid" class="form-input" style="width: 140px; padding: 6px 10px;" placeholder="Filter Account UID..." oninput="window.LogsTransactionsModule.onAidChange(this.value)">
            <button class="btn btn-secondary" style="padding: 6px 10px; font-size: 11px;" onclick="window.LogsTransactionsModule.useActivePlayer()">Use Active</button>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase;">Machine:</span>
            <select id="tx-filter-chest" class="form-input" style="width: 170px; padding: 6px 10px;" onchange="window.LogsTransactionsModule.onChestChange(this.value)">
              <option value="ALL">All Machines</option>
              <option value="3">Diamond Royale (#3)</option>
              <option value="4">Weapon Royale (#4)</option>
              <option value="5">Gold Royale (#5)</option>
              <option value="6">Incubator Forge (#6)</option>
            </select>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase;">Type:</span>
            <select id="tx-filter-type" class="form-input" style="width: 120px; padding: 6px 10px;" onchange="window.LogsTransactionsModule.onTypeChange(this.value)">
              <option value="ALL">All Spins</option>
              <option value="1">Single (1x)</option>
              <option value="2">Multi (10x / 5x)</option>
            </select>
          </div>
          <div style="display: flex; gap: 6px; align-items: center;">
            <label style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); cursor: pointer;">
              <input type="checkbox" id="tx-filter-jackpot" onchange="window.LogsTransactionsModule.onJackpotToggle(this.checked)">
              <span>Jackpot Only</span>
            </label>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase;">Limit:</span>
            <select id="tx-filter-limit" class="form-input" style="width: 90px; padding: 6px 10px;" onchange="window.LogsTransactionsModule.onLimitChange(this.value)">
              <option value="25">25</option>
              <option value="50" selected>50</option>
              <option value="100">100</option>
              <option value="200">200</option>
            </select>
          </div>
          <button class="btn btn-secondary" onclick="window.LogsTransactionsModule.resetFilters()">Reset</button>
        </div>
      </div>

      <!-- Transaction Ledger Table Card -->
      <div class="glass-card" style="padding: 0; overflow: hidden; margin-bottom: 24px;">
        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; color: #fff; font-size: 13px;">Gacha Transaction Audit Trail</div>
          <div id="tx-record-count" style="font-size: 11px; color: var(--text-tertiary);">Loading transactions...</div>
        </div>
        <div class="glass-table-container" id="tx-table-container">
          ${window.UI.Loading('Loading gacha transactions from database...')}
        </div>
      </div>
    `;

    await fetchTransactions();
  }

  async function fetchTransactions() {
    try {
      const params = { limit: filterLimit };
      if (filterAid) params.account_id = filterAid;
      if (filterChestId !== 'ALL') params.chest_id = filterChestId;

      const res = await window.apiClient.get('/api/admin/luck-royale/transactions', params);
      if (res.ok && res.data && res.data.transactions) {
        transactionsList = res.data.transactions;
      } else {
        // Fallback to overview recent transactions if /transactions returned empty
        const ovRes = await window.apiClient.get('/api/admin/luck-royale/overview');
        if (ovRes.ok && ovRes.data && ovRes.data.recent_transactions) {
          transactionsList = ovRes.data.recent_transactions;
        } else {
          transactionsList = [];
        }
      }

      updateAnalytics();
      renderTable();
    } catch (err) {
      console.warn('Failed to fetch transactions:', err);
      const container = document.getElementById('tx-table-container');
      if (container) {
        container.innerHTML = `
          <div style="padding: 30px; text-align: center; color: var(--accent-rose); font-size: 12px;">
            Failed to query transactions: ${err.message || 'Unknown network error'}
          </div>
        `;
      }
    }
  }

  function updateAnalytics() {
    const total = transactionsList.length;
    let diamonds = 0;
    let gold = 0;
    let jackpots = 0;

    for (const tx of transactionsList) {
      const costType = tx.cost_type; // 2 = diamond, 1 = gold
      const costAmt = parseInt(tx.cost_amount || 0, 10);
      if (costType === 2) diamonds += costAmt;
      else if (costType === 1) gold += costAmt;

      if (tx.has_big_reward || tx.jackpot) jackpots++;
    }

    const elTotal = document.getElementById('tx-stat-total');
    const elDia = document.getElementById('tx-stat-diamonds');
    const elGold = document.getElementById('tx-stat-gold');
    const elJack = document.getElementById('tx-stat-jackpots');

    if (elTotal) elTotal.textContent = total.toLocaleString();
    if (elDia) elDia.textContent = `💎 ${diamonds.toLocaleString()}`;
    if (elGold) elGold.textContent = `🪙 ${gold.toLocaleString()}`;
    if (elJack) elJack.textContent = jackpots.toLocaleString();
  }

  function renderTable() {
    const container = document.getElementById('tx-table-container');
    if (!container) return;

    let filtered = transactionsList;

    if (filterChestId !== 'ALL') {
      filtered = filtered.filter(t => String(t.chest_id) === String(filterChestId));
    }

    if (filterType !== 'ALL') {
      filtered = filtered.filter(t => String(t.gacha_type) === String(filterType));
    }

    if (filterJackpotOnly) {
      filtered = filtered.filter(t => t.has_big_reward || t.jackpot);
    }

    if (filterAid) {
      filtered = filtered.filter(t => String(t.account_id) === String(filterAid));
    }

    const countLabel = document.getElementById('tx-record-count');
    if (countLabel) countLabel.textContent = `${filtered.length} of ${transactionsList.length} transactions shown`;

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--text-tertiary); font-size: 12.5px;">
          No transactions match current filters. Try resetting filter criteria.
        </div>
      `;
      return;
    }

    const rowsHtml = filtered.map((tx, idx) => {
      const machineName = MACHINE_NAMES[tx.chest_id] || `Machine #${tx.chest_id}`;
      let machineBadgeVariant = 'cyan';
      if (tx.chest_id === 3) machineBadgeVariant = 'cyan';
      else if (tx.chest_id === 4) machineBadgeVariant = 'rose';
      else if (tx.chest_id === 5) machineBadgeVariant = 'amber';
      else if (tx.chest_id === 6) machineBadgeVariant = 'emerald';

      const isJackpot = tx.has_big_reward || tx.jackpot;
      const spinTypeStr = tx.gacha_type === 2 ? 'Multi (10x)' : (tx.gacha_type === 1 ? 'Single (1x)' : 'Special');
      const timeStr = tx.time_str || (tx.timestamp ? new Date(tx.timestamp * 1000).toLocaleTimeString() : 'Recent');

      // Cost format
      let costStr = 'Free';
      if (tx.cost_amount > 0) {
        costStr = tx.cost_type === 2 ? `💎 ${tx.cost_amount}` : (tx.cost_type === 1 ? `🪙 ${tx.cost_amount}` : `🎟️ ${tx.cost_amount}`);
      }

      // Rewards summary
      let rewardsSummary = '—';
      if (Array.isArray(tx.reward_item_ids) && tx.reward_item_ids.length > 0) {
        rewardsSummary = tx.reward_item_ids.map(id => `<code style="font-family: var(--font-mono); color: var(--accent-cyan); font-size: 11px;">${id}</code>`).join(' ');
      } else if (tx.rewards_summary) {
        rewardsSummary = tx.rewards_summary;
      }

      return `
        <tr style="cursor: pointer;" onclick="window.LogsTransactionsModule.inspectTx(${idx})">
          <td><code style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 11px;">#${tx.trans_id || tx.id || idx + 1}</code></td>
          <td><code style="font-family: var(--font-mono); color: var(--text-tertiary); font-size: 11px;">${timeStr}</code></td>
          <td>
            <a href="javascript:void(0)" onclick="event.stopPropagation(); window.playerContext.setAccountId(${tx.account_id}); window.UI.Toast('Switched context to account ${tx.account_id}', 'info');" style="color: var(--accent-cyan); text-decoration: none; font-family: var(--font-mono); font-weight: 600;">
              ${tx.account_id}
            </a>
          </td>
          <td>${window.UI.Badge(machineName, machineBadgeVariant)}</td>
          <td><span style="font-size: 12px; color: #fff;">${spinTypeStr}</span></td>
          <td><span style="font-weight: 600; font-size: 12px; color: ${tx.cost_type === 2 ? 'var(--accent-cyan)' : 'var(--accent-amber)'};">${costStr}</span></td>
          <td style="max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${rewardsSummary}
          </td>
          <td>
            <span style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-secondary);">
              ${tx.lucky_before !== undefined ? `${tx.lucky_before} → ${tx.lucky_after}` : (tx.lucky_after || '—')}
            </span>
          </td>
          <td>
            ${isJackpot ? window.UI.Badge('JACKPOT ⭐', 'emerald') : window.UI.Badge('Standard', 'neutral')}
          </td>
          <td style="text-align: right;">
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="event.stopPropagation(); window.LogsTransactionsModule.inspectTx(${idx})">Inspect</button>
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = window.UI.Table(
      ['Tx ID', 'Time', 'UID', 'Machine', 'Type', 'Cost Spent', 'Rewards Awarded', 'Lucky Meter', 'Status', ''],
      rowsHtml
    );
  }

  // --- Exposed Handlers for DOM Interaction ---
  window.LogsTransactionsModule = {
    render: renderTransactions,

    async refresh() {
      await fetchTransactions();
      window.UI.Toast('Transaction ledger refreshed', 'success');
    },

    onAidChange(val) {
      filterAid = val.trim();
      renderTable();
    },

    onChestChange(val) {
      filterChestId = val;
      renderTable();
    },

    onTypeChange(val) {
      filterType = val;
      renderTable();
    },

    onJackpotToggle(checked) {
      filterJackpotOnly = checked;
      renderTable();
    },

    onLimitChange(val) {
      filterLimit = parseInt(val, 10) || 50;
      fetchTransactions();
    },

    useActivePlayer() {
      const curAid = window.playerContext.getSelectedAccountId();
      const input = document.getElementById('tx-filter-aid');
      if (input) {
        input.value = curAid;
        filterAid = String(curAid);
        renderTable();
        window.UI.Toast(`Filtering by Active UID ${curAid}`, 'info');
      }
    },

    resetFilters() {
      filterAid = '';
      filterChestId = 'ALL';
      filterType = 'ALL';
      filterJackpotOnly = false;
      const fAid = document.getElementById('tx-filter-aid');
      const fChest = document.getElementById('tx-filter-chest');
      const fType = document.getElementById('tx-filter-type');
      const fJack = document.getElementById('tx-filter-jackpot');
      if (fAid) fAid.value = '';
      if (fChest) fChest.value = 'ALL';
      if (fType) fType.value = 'ALL';
      if (fJack) fJack.checked = false;
      renderTable();
    },

    inspectTx(idx) {
      const tx = transactionsList[idx];
      if (!tx) return;

      const bodyHtml = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: rgba(0,0,0,0.25); padding: 12px; border-radius: 6px; border: 1px solid var(--border-subtle);">
            <div><span style="color: var(--text-tertiary);">Transaction ID:</span> <strong style="color: #fff;">#${tx.trans_id || tx.id || idx + 1}</strong></div>
            <div><span style="color: var(--text-tertiary);">Timestamp:</span> <strong style="color: #fff;">${tx.time_str || (tx.timestamp ? new Date(tx.timestamp * 1000).toLocaleString() : 'Recent')}</strong></div>
            <div><span style="color: var(--text-tertiary);">Account ID:</span> <strong style="color: var(--accent-cyan);">${tx.account_id}</strong></div>
            <div><span style="color: var(--text-tertiary);">Machine:</span> <strong style="color: var(--accent-amber);">${MACHINE_NAMES[tx.chest_id] || tx.chest_id}</strong></div>
            <div><span style="color: var(--text-tertiary);">Spin Type:</span> <strong style="color: #fff;">${tx.gacha_type === 2 ? 'Multi 10x' : 'Single 1x'}</strong></div>
            <div><span style="color: var(--text-tertiary);">Cost Spent:</span> <strong style="color: var(--accent-emerald);">${tx.cost_amount || 0} (Type: ${tx.cost_type})</strong></div>
            <div><span style="color: var(--text-tertiary);">Lucky Meter Before:</span> <strong style="color: #fff;">${tx.lucky_before || 0}</strong></div>
            <div><span style="color: var(--text-tertiary);">Lucky Meter After:</span> <strong style="color: var(--accent-cyan);">${tx.lucky_after || 0}</strong></div>
          </div>

          <div>
            <div style="font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; font-size: 11.5px; text-transform: uppercase;">Raw Transaction Record</div>
            <pre style="background: rgba(0,0,0,0.45); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle); color: var(--text-primary); font-family: var(--font-mono); font-size: 11px; max-height: 200px; overflow-y: auto;">${JSON.stringify(tx, null, 2)}</pre>
          </div>
        </div>
      `;

      const actionsHtml = `
        <button class="btn btn-primary" onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(tx).replace(/"/g, '&quot;')})); window.UI.Toast('Copied transaction record', 'success');">Copy JSON</button>
        <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Close</button>
      `;

      window.UI.Modal(`Transaction #${tx.trans_id || tx.id || idx + 1}`, bodyHtml, actionsHtml);
    },

    openManualTxModal() {
      const curAid = window.playerContext.getSelectedAccountId();
      const bodyHtml = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div>
            <label style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 4px;">Target Account ID</label>
            <input type="number" id="manual-tx-aid" class="form-input" value="${curAid}">
          </div>
          <div>
            <label style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 4px;">Target Machine</label>
            <select id="manual-tx-chest" class="form-input">
              <option value="3">Diamond Royale (#3)</option>
              <option value="4">Weapon Royale (#4)</option>
              <option value="5">Gold Royale (#5)</option>
              <option value="6">Incubator Forge (#6)</option>
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 4px;">Spin Type</label>
              <select id="manual-tx-type" class="form-input">
                <option value="1">Single (1x)</option>
                <option value="2">Multi (10x)</option>
              </select>
            </div>
            <div>
              <label style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 4px;">Cost Amount</label>
              <input type="number" id="manual-tx-cost" class="form-input" value="60">
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 4px;">Lucky Meter After</label>
              <input type="number" id="manual-tx-lucky" class="form-input" value="10">
            </div>
            <div style="display: flex; align-items: center; margin-top: 18px;">
              <label style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #fff; cursor: pointer;">
                <input type="checkbox" id="manual-tx-jackpot">
                <span>Grand Prize Jackpot?</span>
              </label>
            </div>
          </div>
        </div>
      `;

      const actionsHtml = `
        <button class="btn btn-primary" onclick="window.LogsTransactionsModule.submitManualTx()">Submit Transaction</button>
        <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Cancel</button>
      `;

      window.UI.Modal('Record Manual Gacha Transaction', bodyHtml, actionsHtml);
    },

    async submitManualTx() {
      const aid = parseInt(document.getElementById('manual-tx-aid').value, 10) || window.playerContext.getSelectedAccountId();
      const cid = parseInt(document.getElementById('manual-tx-chest').value, 10) || 3;
      const gtype = parseInt(document.getElementById('manual-tx-type').value, 10) || 1;
      const cost = parseInt(document.getElementById('manual-tx-cost').value, 10) || 0;
      const lucky = parseInt(document.getElementById('manual-tx-lucky').value, 10) || 0;
      const isJackpot = document.getElementById('manual-tx-jackpot').checked;

      const payload = {
        account_id: aid,
        chest_id: cid,
        gacha_type: gtype,
        cost_type: cid === 5 ? 1 : 2,
        cost_amount: cost,
        lucky_before: Math.max(0, lucky - 1),
        lucky_after: lucky,
        has_big_reward: isJackpot,
        reward_item_ids: [cid === 3 ? 101000001 : 102000001]
      };

      const res = await window.apiClient.post('/api/admin/luck-royale/transactions', payload);
      document.getElementById('global-modal-overlay').remove();

      if (res.ok) {
        window.UI.Toast('Transaction recorded successfully', 'success');
        await fetchTransactions();
      } else {
        window.UI.Toast(res.error || 'Failed to record transaction', 'error');
      }
    },

    exportCSV() {
      if (transactionsList.length === 0) {
        window.UI.Toast('No transactions to export', 'warning');
        return;
      }

      const headers = ['Tx ID', 'Timestamp', 'Account ID', 'Machine ID', 'Machine Name', 'Spin Type', 'Cost Type', 'Cost Amount', 'Lucky Before', 'Lucky After', 'Is Jackpot'];
      const rows = transactionsList.map(tx => [
        tx.trans_id || tx.id || '',
        tx.time_str || tx.timestamp || '',
        tx.account_id || '',
        tx.chest_id || '',
        MACHINE_NAMES[tx.chest_id] || '',
        tx.gacha_type || 1,
        tx.cost_type || '',
        tx.cost_amount || 0,
        tx.lucky_before || 0,
        tx.lucky_after || 0,
        tx.has_big_reward ? '1' : '0'
      ]);

      const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
      const a = document.createElement('a');
      a.setAttribute('href', encodeURI(csvContent));
      a.setAttribute('download', `gacha_transactions_${Date.now()}.csv`);
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.UI.Toast('Transactions exported to CSV', 'success');
    },

    exportJSON() {
      if (transactionsList.length === 0) {
        window.UI.Toast('No transactions to export', 'warning');
        return;
      }
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(transactionsList, null, 2));
      const a = document.createElement('a');
      a.setAttribute('href', dataStr);
      a.setAttribute('download', `gacha_transactions_${Date.now()}.json`);
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.UI.Toast('Transactions exported to JSON', 'success');
    }
  };

  // Register on window.Modules
  window.Modules = window.Modules || {};
  window.Modules.LogsTransactions = renderTransactions;

  // Register in Router with resilient hook
  function hookRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/logs/transactions', renderTransactions);
      window.appRouter.register('#/luck-royale/transactions', renderTransactions);
    }
  }
  hookRoute();
  document.addEventListener('DOMContentLoaded', () => { setTimeout(hookRoute, 0); });
  window.addEventListener('load', hookRoute);
})();
