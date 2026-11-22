/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.1: Studio Overview & Machine Hub (overview.js)
 * Clean macOS dark glass design system, zero emojis, authentic backend metrics.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Overview = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Luck Royale telemetry & machines...');

  // Fetch live overview metrics and machine list in parallel
  const [overviewRes, machinesRes] = await Promise.all([
    window.apiClient.get('/api/admin/luck-royale/overview'),
    window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 })
  ]);

  const overview = (overviewRes.ok && overviewRes.data) ? overviewRes.data : {};
  const machines = (machinesRes.ok && machinesRes.data && machinesRes.data.machines) ? machinesRes.data.machines : [];

  const totalSpins = overview.total_spins || 0;
  const activeCount = machines.filter(m => m.enabled).length;
  const totalCount = machines.length;
  const diaBurn = overview.diamonds_burn || 0;
  const goldBurn = overview.gold_burn || 0;
  const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;

  // Build Machine Cards
  const machineCards = machines.map(m => {
    const isAct = Boolean(m.enabled);
    const coinSvg = m.coin_type === 2 ? window.UI.Icon('diamond', 13) : window.UI.Icon('coins', 13);
    const coinLabel = m.coin_type === 2 ? 'Diamonds' : 'Gold';
    const bannerUrl = (m.artwork && m.artwork.banner_url) || m.banner_url || '/banners/' + (m.banner_file || 'luck_royale_banner.png');
    const voucherName = m.exchange_item_name || (m.exchange_itemid ? `Voucher #${m.exchange_itemid}` : 'None');

    return `
      <div class="glass-card" style="display: flex; flex-direction: column; overflow: hidden; border-color: ${isAct ? 'var(--border-default)' : 'rgba(244, 63, 94, 0.2)'}; padding: 0;">
        <div style="position: relative; height: 130px; background: rgba(0,0,0,0.4); border-bottom: 1px solid var(--border-subtle); overflow: hidden; display: flex; align-items: center; justify-content: center;">
          <img src="${bannerUrl}" alt="${C.escapeHtml(m.display_name)}" style="width: 100%; height: 100%; object-fit: cover; opacity: ${isAct ? '0.85' : '0.4'}; transition: transform 0.3s ease;" onerror="this.onerror=null; this.src='/banners/luck_royale_banner.png';">
          <div style="position: absolute; top: 10px; left: 10px; display: flex; gap: 6px;">
            ${window.UI.Badge('ID: ' + m.chest_id, 'neutral')}
            ${m.chest_type_enum === 1 ? window.UI.Badge('TURNTABLE', 'indigo') : window.UI.Badge('ROYALE', 'cyan')}
          </div>
          <div style="position: absolute; top: 10px; right: 10px;">
            ${isAct ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('DISABLED', 'rose')}
          </div>
        </div>

        <div style="padding: 16px; flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 4px;">
              ${C.escapeHtml(m.display_name || m.chest_name)}
            </div>
            <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary); margin-bottom: 14px;">
              ${C.escapeHtml(m.chest_name)}
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; font-size: 11.5px; background: rgba(255, 255, 255, 0.02); padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <div>
                <span style="color: var(--text-tertiary); display: block; margin-bottom: 2px;">Cost per Spin</span>
                <span style="font-weight: 600; color: #fff; display: inline-flex; align-items: center; gap: 4px;">
                  ${coinSvg} ${m.once_price} / ${m.ten_price}
                </span>
              </div>
              <div>
                <span style="color: var(--text-tertiary); display: block; margin-bottom: 2px;">Pity Threshold</span>
                <span style="font-weight: 600; color: var(--accent-amber); font-family: var(--font-mono);">
                  ${m.rare_item_max || 100} Lucky
                </span>
              </div>
              <div>
                <span style="color: var(--text-tertiary); display: block; margin-bottom: 2px;">Voucher Item</span>
                <span style="font-weight: 500; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block;" title="${C.escapeHtml(voucherName)}">
                  ${C.escapeHtml(voucherName)}
                </span>
              </div>
              <div>
                <span style="color: var(--text-tertiary); display: block; margin-bottom: 2px;">Reward Pool</span>
                <span style="font-weight: 600; color: var(--accent-cyan); font-family: var(--font-mono);">
                  ${m.items_count || (m.items ? m.items.length : 0)} items
                </span>
              </div>
            </div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <button class="btn btn-primary" style="padding: 6px 10px; font-size: 11.5px;" onclick="window.LuckRoyale._selectedMachineCid=${m.chest_id}; window.location.hash='#/luck-royale/machines';">
                <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('sliders', 12)} Manage</span>
              </button>
              <button class="btn btn-secondary" style="padding: 6px 10px; font-size: 11.5px;" onclick="window.LuckRoyale._selectedPoolCid=${m.chest_id}; window.location.hash='#/luck-royale/pools';">
                <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('gift', 12)} Prize Pool</span>
              </button>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <button class="btn btn-secondary" style="padding: 5px 8px; font-size: 11px;" onclick="window.LuckRoyale._selectedBannerCid=${m.chest_id}; window.location.hash='#/luck-royale/banners';">
                <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('image', 11)} Artwork</span>
              </button>
              <button class="btn btn-secondary" style="padding: 5px 8px; font-size: 11px;" onclick="window.LuckRoyale.ToggleMachineFromOverview(${m.chest_id}, ${!isAct})">
                ${isAct ? 'Disable' : 'Enable'}
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Luck Royale Studio',
        'Administrative command center for Free Fire 1.39 OB17 turntables, prize pools, vouchers, and game economics',
        `
          <button class="btn btn-primary" onclick="window.LuckRoyale.OpenCreateMachineModal()">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('plus', 13)} Create Machine</span>
          </button>
        `,
        'sparkles'
      )}

      ${C.renderSubNav('overview')}

      <!-- Telemetry Strip -->
      <div class="grid-4" style="margin-bottom: 24px;">
        <div class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div class="stat-label">Total Rolls Executed</div>
              <div class="stat-value" style="color: var(--accent-cyan); font-family: var(--font-mono);">${C.formatNumber(totalSpins)}</div>
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Persisted in gacha_transactions</div>
            </div>
            <div style="color: var(--accent-cyan);">${window.UI.Icon('activity', 20)}</div>
          </div>
        </div>

        <div class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div class="stat-label">Active Turntables</div>
              <div class="stat-value" style="color: var(--accent-emerald); font-family: var(--font-mono);">${activeCount} / ${totalCount}</div>
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Online in Lobby Protocol</div>
            </div>
            <div style="color: var(--accent-emerald);">${window.UI.Icon('layers', 20)}</div>
          </div>
        </div>

        <div class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div class="stat-label">Economy Currency Burn</div>
              <div class="stat-value" style="color: var(--accent-amber); font-family: var(--font-mono); font-size: 18px; display: inline-flex; align-items: center; gap: 8px;">
                <span>${window.UI.Icon('diamond', 13)} ${C.formatNumber(diaBurn)}</span>
                <span style="color: var(--text-tertiary);">/</span>
                <span>${window.UI.Icon('coins', 13)} ${C.formatNumber(goldBurn)}</span>
              </div>
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Diamonds & Gold consumed</div>
            </div>
            <div style="color: var(--accent-amber);">${window.UI.Icon('trendingUp', 20)}</div>
          </div>
        </div>

        <div class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div class="stat-label">Active Context Profile</div>
              <div class="stat-value" style="color: #fff; font-family: var(--font-mono); font-size: 17px;">UID ${aid}</div>
              <div style="font-size: 11px; color: var(--accent-emerald); margin-top: 4px;">Synchronized with Session</div>
            </div>
            <div style="color: var(--text-tertiary);">${window.UI.Icon('user', 20)}</div>
          </div>
        </div>
      </div>

      <!-- Discovered Royale Machines Grid -->
      <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h2 style="font-size: 15px; font-weight: 600; color: #fff; margin: 0 0 4px 0;">Discovered Royale Machines (${machines.length})</h2>
          <div style="font-size: 12px; color: var(--text-secondary);">Direct access to individual machines, reward configurations, and artwork</div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary" onclick="window.location.hash='#/luck-royale/banners'">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('image', 12)} Asset Browser</span>
          </button>
          <button class="btn btn-secondary" onclick="window.location.hash='#/luck-royale/simulator'">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('cpu', 12)} Monte Carlo Simulator</span>
          </button>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
        ${machineCards}
      </div>
    </div>
  `;
};

window.LuckRoyale.ToggleMachineFromOverview = async function (chestId, newState) {
  const res = await window.apiClient.post('/api/admin/luck-royale/machines/toggle', { chest_id: chestId, enabled: newState });
  if (res.ok) {
    window.UI.Toast(`Machine ${chestId} ${newState ? 'enabled' : 'disabled'} successfully.`, 'success');
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to toggle machine.', 'danger');
  }
};
