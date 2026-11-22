/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.9: Player Gacha State (player.js)
 * Clean macOS dark glass design system, zero emojis, active player context synchronization.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Player = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
  canvas.innerHTML = window.UI.Loading(`Loading Gacha dossier for Account UID ${aid}...`);

  // Fetch player details, meters, and personal gacha history
  const [playerRes, meterRes, txRes, machRes] = await Promise.all([
    window.apiClient.get(`/api/admin/players/${aid}`),
    window.apiClient.get('/api/admin/luck-royale/meters', { account_id: aid }),
    window.apiClient.get('/api/admin/luck-royale/transactions', { account_id: aid, limit: 30 }),
    window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 })
  ]);

  const player = (playerRes.ok && playerRes.data && playerRes.data.player) ? playerRes.data.player : {};
  const meters = (meterRes.ok && meterRes.data && meterRes.data.meters) ? meterRes.data.meters : {};
  const txs = (txRes.ok && txRes.data && txRes.data.transactions) ? txRes.data.transactions : [];
  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];

  // Meters Strip
  const meterCards = machines.map(m => {
    const cur = meters[m.chest_id] || 0;
    const max = m.rare_item_max || 100;
    const isPity = cur >= max;

    return `
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <div>
            <div class="stat-label">${C.escapeHtml(m.display_name || m.chest_name)}</div>
            <div class="stat-value" style="color: ${isPity ? 'var(--accent-amber)' : 'var(--accent-cyan)'}; font-family: var(--font-mono); font-size: 20px;">
              ${cur} <span style="font-size: 11px; color: var(--text-tertiary);">/ ${max}</span>
            </div>
          </div>
          ${isPity ? window.UI.Badge('PITY READY', 'amber') : window.UI.Badge('NORMAL', 'neutral')}
        </div>
        <div style="display: flex; gap: 4px; margin-top: 8px;">
          <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="window.LuckRoyale.AdjustMeter(${aid}, ${m.chest_id}, 0)">Reset</button>
          <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="window.LuckRoyale.AdjustMeter(${aid}, ${m.chest_id}, ${cur + 10})">+10</button>
          <button class="btn btn-primary" style="padding: 2px 6px; font-size: 10px;" onclick="window.LuckRoyale.AdjustMeter(${aid}, ${m.chest_id}, ${max - 1})">Max</button>
        </div>
      </div>
    `;
  }).join('');

  // Transaction Rows
  const txRows = txs.map(t => {
    const isJackpot = Boolean(t.has_big_reward);
    const rewardMeta = C.lookupItem(t.reward_item_id || 0);

    return `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--text-tertiary);">${C.formatTimestamp(t.timestamp)}</code></td>
        <td style="font-weight: 500; color: #fff;">Machine #${t.machine_id}</td>
        <td>${t.gacha_type === 1 ? window.UI.Badge('1x Single', 'neutral') : window.UI.Badge('10x Special', 'cyan')}</td>
        <td>
          <span style="font-family: var(--font-mono); font-weight: 600;">${t.cost_amount || 0}</span>
          <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 3px;">${t.cost_type === 2 ? 'Diamonds' : 'Gold'}</span>
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
          ${isJackpot ? window.UI.Badge('JACKPOT', 'amber') : window.UI.Badge('REGULAR', 'neutral')}
        </td>
      </tr>
    `;
  }).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Player Gacha State & Audit Dossier',
        `Live synchronized lucky meters, voucher balances, and roll audit history for Account UID ${aid}`,
        null,
        'user'
      )}

      ${C.renderSubNav('player')}

      <!-- Active Profile Banner -->
      <div class="glass-card" style="margin-bottom: 20px; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 14px;">
          <div style="width: 44px; height: 44px; border-radius: var(--radius-full); background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); display: flex; align-items: center; justify-content: center; color: var(--accent-cyan);">
            ${window.UI.Icon('user', 20)}
          </div>
          <div>
            <div style="font-size: 16px; font-weight: 600; color: #fff;">
              ${C.escapeHtml(player.nickname || 'Player')}
              <span style="font-size: 12px; font-family: var(--font-mono); color: var(--accent-cyan); font-weight: 400; margin-left: 6px;">UID: ${aid}</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-tertiary); margin-top: 2px;">
              Level: ${player.level || 1} • Rank: ${player.rank || 0} • Region: IND
            </div>
          </div>
        </div>

        <button class="btn btn-secondary" onclick="window.Topbar ? window.Topbar.promptSwitchPlayer() : null">
          Switch Context
        </button>
      </div>

      <!-- Meter Cards Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-bottom: 24px;">
        ${meterCards}
      </div>

      <!-- Roll History Table -->
      <div class="glass-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; font-size: 13.5px; color: #fff;">
            Recent Gacha Rolls for UID ${aid} (${txs.length} Recorded)
          </div>
          <div style="font-size: 11.5px; color: var(--text-tertiary);">
            Persisted in gacha_transactions table
          </div>
        </div>
        <div style="max-height: 440px; overflow-y: auto;">
          ${window.UI.Table(['Timestamp', 'Machine', 'Roll Type', 'Cost Paid', 'Reward Granted', 'Tier Status'], txRows, 'No gacha spins recorded for this account yet.')}
        </div>
      </div>
    </div>
  `;
};
