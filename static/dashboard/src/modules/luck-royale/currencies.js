/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.5: Vouchers & Spin Costs (currencies.js)
 * Clean macOS dark glass design system, zero emojis, authentic voucher registry.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Currencies = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Vouchers & Spin Costs...');

  const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;

  // Fetch machines and active player wallet / inventory
  const [machRes, playerRes] = await Promise.all([
    window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 }),
    window.apiClient.get(`/api/admin/players/${aid}`)
  ]);

  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];
  const player = (playerRes.ok && playerRes.data && playerRes.data.player) ? playerRes.data.player : {};
  const inventory = player.inventory || [];

  function getVoucherCount(itemId) {
    const it = inventory.find(x => x.item_id === itemId);
    return it ? (it.quantity || it.item_num || 0) : 0;
  }

  // Canonical Voucher Data
  const voucherList = [
    { id: 110100010, name: 'Gold Royale Voucher', target: 'Gold Royale (#5)', count: getVoucherCount(110100010) },
    { id: 110100008, name: 'Diamond Royale Voucher', target: 'Diamond Royale (#3)', count: getVoucherCount(110100008) },
    { id: 110100009, name: 'Weapon Royale Voucher', target: 'Weapon Royale (#4)', count: getVoucherCount(110100009) },
    { id: 110100018, name: 'Incubator Voucher', target: 'Incubator (#6)', count: getVoucherCount(110100018) },
    { id: 808000003, name: 'Evolution Stone', target: 'Incubator Forge (#6)', count: getVoucherCount(808000003) },
    { id: 110200001, name: 'FF Token', target: 'Token Exchange Shop', count: getVoucherCount(110200001) },
  ];

  // 4-Card Voucher Metrics
  const metricCards = voucherList.slice(0, 4).map(v => `
    <div class="stat-card">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
        <div>
          <div class="stat-label">${C.escapeHtml(v.name)}</div>
          <div class="stat-value" style="color: var(--accent-cyan); font-family: var(--font-mono);">${C.formatNumber(v.count)} <span style="font-size: 11px; color: var(--text-tertiary);">Owned</span></div>
        </div>
        ${window.UI.Badge('ID: ' + v.id, 'neutral')}
      </div>
      <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 6px;">Target: ${v.target}</div>
    </div>
  `).join('');

  // Machine Pricing Rows
  const pricingRows = machines.map(m => {
    const coinSvg = m.coin_type === 2 ? window.UI.Icon('diamond', 12) : window.UI.Icon('coins', 12);
    return `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">${m.chest_id}</code></td>
        <td style="font-weight: 600; color: #fff;">${C.escapeHtml(m.display_name || m.chest_name)}</td>
        <td>${C.coinBadge(m.coin_type)}</td>
        <td>
          <span style="font-weight: 600; color: #fff; display: inline-flex; align-items: center; gap: 4px;">
            ${coinSvg} ${m.once_price}
          </span>
          ${m.discount_price_one ? `<span style="font-size: 10.5px; color: var(--accent-emerald); margin-left: 4px;">(${m.discount_price_one})</span>` : ''}
        </td>
        <td>
          <span style="font-weight: 600; color: #fff; display: inline-flex; align-items: center; gap: 4px;">
            ${coinSvg} ${m.ten_price}
          </span>
          ${m.discount_price_ten ? `<span style="font-size: 10.5px; color: var(--accent-emerald); margin-left: 4px;">(${m.discount_price_ten})</span>` : ''}
        </td>
        <td>
          <code style="font-family: var(--font-mono); font-size: 11px;">${m.exchange_itemid || '—'}</code>
        </td>
        <td>
          <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale._selectedMachineCid=${m.chest_id}; window.LuckRoyale._activeStudioTab='settings'; window.location.hash='#/luck-royale/machines';">
            Edit
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Voucher Registry Rows
  const voucherRows = voucherList.map(v => `
    <tr>
      <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">${v.id}</code></td>
      <td style="font-weight: 600; color: #fff;">${C.escapeHtml(v.name)}</td>
      <td style="font-size: 11.5px; color: var(--text-secondary);">${v.target}</td>
      <td>
        <span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-cyan);">${v.count}</span>
      </td>
      <td>
        <div style="display: flex; gap: 4px;">
          <button class="btn btn-secondary" style="padding: 3px 6px; font-size: 10.5px;" onclick="window.LuckRoyale.GrantVoucher(${aid}, ${v.id}, 5)">+5</button>
          <button class="btn btn-secondary" style="padding: 3px 6px; font-size: 10.5px;" onclick="window.LuckRoyale.GrantVoucher(${aid}, ${v.id}, 20)">+20</button>
          <button class="btn btn-primary" style="padding: 3px 6px; font-size: 10.5px;" onclick="window.LuckRoyale.GrantVoucher(${aid}, ${v.id}, 50)">+50</button>
        </div>
      </td>
    </tr>
  `).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Vouchers & Spin Costs',
        'Configure machine currency prices, voucher redemption rules, and live player token balances',
        null,
        'ticket'
      )}

      ${C.renderSubNav('currencies')}

      <!-- 4-Card Voucher Metrics -->
      <div class="grid-4" style="margin-bottom: 24px;">
        ${metricCards}
      </div>

      <!-- Symmetrical 50/50 Split -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <!-- Left: Spin Costs Matrix -->
        <div class="glass-card" style="padding: 0; overflow: hidden;">
          <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); font-weight: 600; font-size: 13px; color: #fff;">
            Machine Spin Pricing & Currency Rules
          </div>
          <div>
            ${window.UI.Table(['ID', 'Machine', 'Currency', '1x Spin', '10x Spin', 'Voucher ID', 'Action'], pricingRows)}
          </div>
        </div>

        <!-- Right: Canonical Voucher Registry -->
        <div class="glass-card" style="padding: 0; overflow: hidden;">
          <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; font-size: 13px; color: #fff;">Canonical Voucher Registry (UID ${aid})</span>
            ${window.UI.Badge('LIVE INVENTORY', 'emerald')}
          </div>
          <div>
            ${window.UI.Table(['Item ID', 'Token / Voucher', 'Associated Machine', 'Balance', 'Grant to Player'], voucherRows)}
          </div>
        </div>
      </div>
    </div>
  `;
};

window.LuckRoyale.GrantVoucher = async function (accountId, itemId, amount) {
  const res = await window.apiClient.post('/api/dashboard/items/grant', {
    account_id: accountId,
    item_id: itemId,
    quantity: amount
  });
  if (res.ok) {
    window.UI.Toast(`Granted +${amount} Item #${itemId} to UID ${accountId}.`, 'success');
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to grant voucher.', 'danger');
  }
};
