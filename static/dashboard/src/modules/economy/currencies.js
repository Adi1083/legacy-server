/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Currency Manager & Wallet Adjustments
 * Route: #/economy/currencies
 *
 * Capabilities:
 * - Reactive binding to PlayerContext (active account, live gold & diamonds)
 * - Standardized .page-container layout with UI.PageHeader & .grid-4 metric strip
 * - High-polish dark glass styling with active wallet tier gauges
 * - Operation 1: Grant / Increment Currency (POST /api/dashboard/wallet/grant) with UI.Confirm & live balance preview
 * - Operation 2: Set Absolute Wallet Balance (POST /api/dashboard/wallet/set) with destructive UI.Confirm & presets
 * - Operation 3: Voucher Management & Quick Grant (POST /api/dashboard/items/grant) with UI.Confirm
 * - Server Currency & Voucher Registry reference table
 * - Zero consumer emojis
 */

(function () {
  'use strict';

  let activeTab = 'adjustments'; // 'adjustments' | 'vouchers' | 'registry'

  function formatNumber(num) {
    return Number(num || 0).toLocaleString();
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function getGoldTier(amount) {
    if (amount >= 5000000) return { label: 'Sovereign Treasury', badge: 'rose' };
    if (amount >= 1000000) return { label: 'Tycoon Reserve', badge: 'amber' };
    if (amount >= 250000) return { label: 'Veteran Merchant', badge: 'cyan' };
    if (amount >= 50000) return { label: 'Active Raider', badge: 'emerald' };
    return { label: 'Recruit Baseline', badge: 'neutral' };
  }

  function getDiamondTier(amount) {
    if (amount >= 100000) return { label: 'Imperial Whale', badge: 'rose' };
    if (amount >= 25000) return { label: 'Apex Collector', badge: 'amber' };
    if (amount >= 5000) return { label: 'Elite Sponsor', badge: 'cyan' };
    if (amount >= 1000) return { label: 'Active Patron', badge: 'emerald' };
    return { label: 'Standard Operative', badge: 'neutral' };
  }

  const VOUCHERS_REGISTRY = [
    {
      id: 110100010,
      name: 'Gold Royale Voucher',
      domain: 'Gold Royale Wheel',
      desc: 'Free single spin voucher for the Gold Royale cosmetic wheel.',
      tone: 'amber',
      icon: 'ticket'
    },
    {
      id: 110100008,
      name: 'Diamond Royale Voucher',
      domain: 'Diamond Royale Machine',
      desc: 'Premier spin token for exclusive seasonal cosmetic costumes.',
      tone: 'cyan',
      icon: 'diamond'
    },
    {
      id: 110100009,
      name: 'Weapon Royale Voucher',
      domain: 'Weapon Royale Armory',
      desc: 'Free spin ticket for legendary firearms and rare weapon skins.',
      tone: 'amber',
      icon: 'crosshair'
    },
    {
      id: 110100018,
      name: 'Incubator Voucher',
      domain: 'Incubator Machine',
      desc: 'Evolution voucher for blueprint synthesis and incubator spins.',
      tone: 'cyan',
      icon: 'sparkles'
    },
    {
      id: 808000003,
      name: 'Evolution Stone',
      domain: 'Incubator Forge',
      desc: 'Crucial synthesis catalyst required to assemble incubator blueprints.',
      tone: 'rose',
      icon: 'shield'
    },
    {
      id: 110200001,
      name: 'FF Tokens',
      domain: 'Exchange Store',
      desc: 'Universal exchange currency awarded from duplicate gacha rewards.',
      tone: 'emerald',
      icon: 'coins'
    }
  ];

  async function renderCurrencies(canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Loading('Loading account wallet & currencies...');

    let p = window.playerContext.getCurrentPlayer();
    let totalAccounts = 1;

    try {
      const [stateRes, playersRes] = await Promise.all([
        window.apiClient.get('/api/dashboard/state', { account_id: aid }),
        window.apiClient.get('/api/admin/players', { limit: 1 })
      ]);

      if (stateRes.ok && stateRes.data) p = stateRes.data;
      if (playersRes.ok && playersRes.data) {
        totalAccounts = playersRes.data.total || (playersRes.data.players ? playersRes.data.players.length : 1);
      }
    } catch (e) {
      console.error('State load error', e);
    }

    const wallet = (p && p.wallet) || { gold: 0, diamonds: 0, coins: 0, gems: 0 };
    const curGold = wallet.gold !== undefined ? wallet.gold : (wallet.coins || 0);
    const curDia = wallet.diamonds !== undefined ? wallet.diamonds : (wallet.gems || 0);

    const goldTier = getGoldTier(curGold);
    const diaTier = getDiamondTier(curDia);

    const nick = (p && (p.nickname || (p.profile && p.profile.nickname))) || 'PushpaGG';
    const level = (p && (p.level || (p.profile && p.profile.level))) || 60;

    // Inventory voucher counts
    const inventory = (p && p.inventory) || [];
    function countItem(id) {
      const match = inventory.find(it => (it.item_id || it.id || it) === id);
      return match ? (match.amount || match.count || 1) : 0;
    }

    const vouchersCardsHtml = VOUCHERS_REGISTRY.map(v => {
      const count = countItem(v.id);
      return `
        <div class="glass-card voucher-card" style="
          background: rgba(10, 16, 28, 0.45);
          border: 1px solid var(--border-default);
          border-radius: var(--radius-md);
          padding: 16px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          transition: all var(--transition-fast);
        ">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <code style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); font-weight: 600;">ID: ${v.id}</code>
              ${window.UI.Badge(v.domain, v.tone)}
            </div>

            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
              <div style="
                width: 32px;
                height: 32px;
                border-radius: var(--radius-sm);
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                justify-content: center;
              ">
                ${window.UI.Icon(v.icon, 16, '', `var(--accent-${v.tone})`)}
              </div>
              <div>
                <div style="font-size: 14px; font-weight: 700; color: #fff;">${escapeHtml(v.name)}</div>
                <div style="font-size: 12px; font-family: var(--font-mono); font-weight: 700; color: var(--accent-${v.tone});">
                  ${formatNumber(count)} Owned
                </div>
              </div>
            </div>

            <div style="font-size: 11px; color: var(--text-tertiary); line-height: 1.4; margin-bottom: 12px; min-height: 30px;">
              ${escapeHtml(v.desc)}
            </div>
          </div>

          <div style="border-top: 1px solid var(--border-subtle); padding-top: 12px; display: flex; gap: 6px;">
            <button class="btn btn-secondary" style="flex: 1; padding: 4px 6px; font-size: 11px;"
              onclick="window.CurrencyManager.promptGrantVoucher(${v.id}, '${escapeHtml(v.name).replace(/'/g, "\\'")}', 1)">
              ${window.UI.Icon('plus', 12)} +1
            </button>
            <button class="btn btn-secondary" style="flex: 1; padding: 4px 6px; font-size: 11px;"
              onclick="window.CurrencyManager.promptGrantVoucher(${v.id}, '${escapeHtml(v.name).replace(/'/g, "\\'")}', 5)">
              +5
            </button>
            <button class="btn btn-primary" style="flex: 1; padding: 4px 6px; font-size: 11px;"
              onclick="window.CurrencyManager.promptGrantVoucher(${v.id}, '${escapeHtml(v.name).replace(/'/g, "\\'")}', 10)">
              +10
            </button>
          </div>
        </div>
      `;
    }).join('');

    const pageActionsHtml = `
      <button class="btn btn-primary" onclick="window.location.hash='#/economy/wallet'">
        ${window.UI.Icon('creditCard', 14)} <span>Player Wallet Dossier</span>
      </button>
      <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.CurrencyManager.render(c);">
        ${window.UI.Icon('refresh', 14)} <span>Sync Balances</span>
      </button>
    `;

    canvas.innerHTML = `
      <div class="page-container">
        <!-- 1. Page Header -->
        ${window.UI.PageHeader(
          'Currency Manager & Adjustments',
          'Adjust account balances, grant currency, and audit economy rules',
          pageActionsHtml,
          'diamond'
        )}

        <!-- 2. Exactly 4 Compact Metrics (.grid-4) -->
        <div class="grid-4" style="margin-bottom: var(--space-md);">
          ${window.UI.StatCard(
            'Gold Reserves',
            formatNumber(curGold),
            goldTier.label,
            window.UI.Icon('coins', 16, '', 'var(--accent-amber)'),
            'amber'
          )}
          ${window.UI.StatCard(
            'Diamond Reserves',
            formatNumber(curDia),
            diaTier.label,
            window.UI.Icon('diamond', 16, '', 'var(--accent-cyan)'),
            'cyan'
          )}
          ${window.UI.StatCard(
            'Tracked Accounts',
            `${totalAccounts} Accounts`,
            'Persistent in india_v1.db',
            window.UI.Icon('users', 16, '', 'var(--accent-emerald)'),
            'emerald'
          )}
          ${window.UI.StatCard(
            'Active Context Account',
            `Account ${aid}`,
            `${escapeHtml(nick)} • Lv.${level}`,
            window.UI.Icon('user', 16, '', 'var(--accent-blue)'),
            'blue'
          )}
        </div>

        <!-- 3. Navigation View Switcher Tabs -->
        <div style="display: flex; gap: 8px; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 10px;">
          <button class="btn ${activeTab === 'adjustments' ? 'btn-primary' : 'btn-secondary'}" onclick="window.CurrencyManager.switchTab('adjustments')">
            ${window.UI.Icon('sliders', 14)} Currency Adjustments & Grants
          </button>
          <button class="btn ${activeTab === 'vouchers' ? 'btn-primary' : 'btn-secondary'}" onclick="window.CurrencyManager.switchTab('vouchers')">
            ${window.UI.Icon('ticket', 14)} Voucher Management & Grants
          </button>
          <button class="btn ${activeTab === 'registry' ? 'btn-primary' : 'btn-secondary'}" onclick="window.CurrencyManager.switchTab('registry')">
            ${window.UI.Icon('fileText', 14)} Economy Architecture & Token Registry
          </button>
        </div>

        ${activeTab === 'adjustments' ? `
          <!-- Live Balances Display -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px;">
            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(10, 16, 28, 0.55); border: 1px solid rgba(251, 191, 36, 0.35); box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12); border-radius: var(--radius-md); padding: 18px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Gold Coins Balance</div>
                ${window.UI.Badge('COIN_TYPE: GOLD', 'amber')}
              </div>
              <div style="font-size: 26px; font-weight: 800; color: #fbbf24; letter-spacing: -0.02em; display: flex; align-items: center; gap: 8px;">
                ${window.UI.Icon('coins', 24, '', '#fbbf24')} <span>${formatNumber(curGold)}</span>
              </div>
              <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">
                Used for Gold Royale spins, standard store weapons, and operative level upgrades.
              </div>
            </div>

            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(10, 16, 28, 0.55); border: 1px solid rgba(56, 189, 248, 0.35); box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12); border-radius: var(--radius-md); padding: 18px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Diamonds (Gems) Balance</div>
                ${window.UI.Badge('COIN_TYPE: DIAMOND', 'cyan')}
              </div>
              <div style="font-size: 26px; font-weight: 800; color: var(--accent-cyan); letter-spacing: -0.02em; display: flex; align-items: center; gap: 8px;">
                ${window.UI.Icon('diamond', 24, '', 'var(--accent-cyan)')} <span>${formatNumber(curDia)}</span>
              </div>
              <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">
                Premium currency for Diamond Royale, Weapon Royale, Elite Pass, and exclusive bundles.
              </div>
            </div>
          </div>

          <!-- Dual Adjustment Engine -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 24px;">
            <!-- Card 1: Grant / Delta Increment -->
            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(10, 16, 28, 0.45); border: 1px solid var(--border-default); box-shadow: 0 4px 16px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08); border-radius: var(--radius-md); padding: 18px; display: flex; flex-direction: column; justify-content: space-between;">
              <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
                  <div>
                    <div style="font-size: 14px; font-weight: 700; color: #fff;">Grant Currency (Increment)</div>
                    <div style="font-size: 11px; color: var(--text-tertiary);">Adds specified amounts on top of current balance</div>
                  </div>
                  ${window.UI.Badge('ADDITIVE', 'emerald')}
                </div>

                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div>
                    <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; text-transform: uppercase;">Add Gold (+)</label>
                    <input type="number" id="grant-gold-input" class="form-input" value="50000" min="0" oninput="window.CurrencyManager.updatePreview(${curGold}, ${curDia})">
                    <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-gold-input').value = 10000; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+10k</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-gold-input').value = 50000; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+50k</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-gold-input').value = 250000; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+250k</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-gold-input').value = 1000000; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+1M</button>
                    </div>
                  </div>

                  <div>
                    <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; text-transform: uppercase;">Add Diamonds (+)</label>
                    <input type="number" id="grant-dia-input" class="form-input" value="2500" min="0" oninput="window.CurrencyManager.updatePreview(${curGold}, ${curDia})">
                    <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-dia-input').value = 500; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+500</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-dia-input').value = 2500; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+2.5k</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-dia-input').value = 10000; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+10k</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="document.getElementById('grant-dia-input').value = 50000; window.CurrencyManager.updatePreview(${curGold}, ${curDia})">+50k</button>
                    </div>
                  </div>

                  <!-- Live Calculation Preview -->
                  <div id="grant-preview-box" style="background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px; font-size: 11px; margin-top: 4px;">
                    <div style="color: var(--text-tertiary); margin-bottom: 4px; font-weight: 600;">Resulting Balance Preview:</div>
                    <div style="display: flex; justify-content: space-between; font-family: var(--font-mono);">
                      <span>Gold: <b style="color: #fbbf24;" id="preview-gold-val">${formatNumber(curGold + 50000)}</b></span>
                      <span>Diamonds: <b style="color: var(--accent-cyan);" id="preview-dia-val">${formatNumber(curDia + 2500)}</b></span>
                    </div>
                  </div>
                </div>
              </div>

              <button class="btn btn-primary" style="margin-top: 14px; padding: 8px 16px;" onclick="window.CurrencyManager.promptGrant()">
                ${window.UI.Icon('plus', 14)} Grant Currency Funds
              </button>
            </div>

            <!-- Card 2: Set Absolute Wallet Balance -->
            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(10, 16, 28, 0.45); border: 1px solid var(--border-default); box-shadow: 0 4px 16px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08); border-radius: var(--radius-md); padding: 18px; display: flex; flex-direction: column; justify-content: space-between;">
              <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
                  <div>
                    <div style="font-size: 14px; font-weight: 700; color: #fff;">Set Absolute Balance</div>
                    <div style="font-size: 11px; color: var(--text-tertiary);">Overwrites wallet with exact specified values</div>
                  </div>
                  ${window.UI.Badge('DESTRUCTIVE', 'rose')}
                </div>

                <div style="display: flex; flex-direction: column; gap: 12px;">
                  <div>
                    <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; text-transform: uppercase;">Exact Gold Balance</label>
                    <input type="number" id="set-gold-input" class="form-input" value="${curGold}">
                  </div>

                  <div>
                    <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; text-transform: uppercase;">Exact Diamond Balance</label>
                    <input type="number" id="set-dia-input" class="form-input" value="${curDia}">
                  </div>

                  <div>
                    <div style="font-size: 10.5px; color: var(--text-tertiary); margin-bottom: 6px; font-weight: 600;">Quick Balance Presets:</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10.5px;" onclick="window.CurrencyManager.fillPreset(10000, 500)">Starter (10k / 500)</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10.5px;" onclick="window.CurrencyManager.fillPreset(500000, 15000)">Whale (500k / 15k)</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10.5px;" onclick="window.CurrencyManager.fillPreset(9999999, 999999)">Max (9.9M / 999k)</button>
                      <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10.5px; color: var(--accent-rose);" onclick="window.CurrencyManager.fillPreset(0, 0)">Zero Out (0 / 0)</button>
                    </div>
                  </div>
                </div>
              </div>

              <button class="btn btn-danger" style="margin-top: 14px; padding: 8px 16px;" onclick="window.CurrencyManager.promptSetBalance()">
                ${window.UI.Icon('alertTriangle', 14)} Overwrite Wallet Balance
              </button>
            </div>
          </div>
        ` : activeTab === 'vouchers' ? `
          <!-- Voucher Management Grid -->
          <div style="margin-bottom: 16px;">
            <div style="font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 4px;">Luck Royale Vouchers & Synthesis Items</div>
            <div style="font-size: 11.5px; color: var(--text-secondary);">Direct item grants into active player inventory database table</div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-bottom: 24px;">
            ${vouchersCardsHtml}
          </div>
        ` : `
          <!-- Currency & Voucher Registry Reference Table inside responsive container -->
          <div style="background: rgba(10, 16, 28, 0.45); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 18px;">
            <div style="font-weight: 700; color: #fff; margin-bottom: 4px; font-size: 13.5px;">Server Currency & Voucher Architecture</div>
            <p style="color: var(--text-secondary); font-size: 11.5px; margin-bottom: 14px;">
              Canonical economy tokens, voucher item IDs, and internal coin identifiers defined across server/proto/:
            </p>
            <div class="glass-table-container" style="overflow-x: auto; width: 100%;">
              ${window.UI.Table(
                ['Token / Currency', 'Item / Proto ID', 'Domain Usage', 'Storage Location'],
                `
                  <tr>
                    <td style="font-weight: 600; color: #fbbf24;">${window.UI.Icon('coins', 14, '', '#fbbf24')} Gold Coins</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">CoinType.GOLD (1/2)</code></td>
                    <td>Free Royale, shop items, level-up costs</td>
                    <td>accounts table (gold column)</td>
                  </tr>
                  <tr>
                    <td style="font-weight: 600; color: var(--accent-cyan);">${window.UI.Icon('diamond', 14, '', 'var(--accent-cyan)')} Diamonds (Gems)</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">CoinType.DIAMOND (2/1)</code></td>
                    <td>Diamond/Weapon Royale, Incubator, Bundles</td>
                    <td>accounts table (diamonds column)</td>
                  </tr>
                  <tr>
                    <td style="font-weight: 600; color: #fff;">${window.UI.Icon('ticket', 14)} Gold Royale Voucher</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-amber);">110100010</code></td>
                    <td>Free single spin on Gold Royale wheel</td>
                    <td>inventory table</td>
                  </tr>
                  <tr>
                    <td style="font-weight: 600; color: #fff;">${window.UI.Icon('ticket', 14)} Diamond Royale Voucher</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-amber);">110100008</code></td>
                    <td>Free single spin on Diamond Royale wheel</td>
                    <td>inventory table</td>
                  </tr>
                  <tr>
                    <td style="font-weight: 600; color: #fff;">${window.UI.Icon('ticket', 14)} Weapon Royale Voucher</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-amber);">110100009</code></td>
                    <td>Free single spin on Weapon Royale wheel</td>
                    <td>inventory table</td>
                  </tr>
                  <tr>
                    <td style="font-weight: 600; color: #fff;">${window.UI.Icon('ticket', 14)} Incubator Voucher</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-amber);">110100018</code></td>
                    <td>Free single spin on Incubator machine</td>
                    <td>inventory table</td>
                  </tr>
                  <tr>
                    <td style="font-weight: 600; color: var(--accent-rose);">${window.UI.Icon('shield', 14, '', 'var(--accent-rose)')} Evolution Stone</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-amber);">808000003</code></td>
                    <td>Synthesis catalyst for Incubator Forge</td>
                    <td>inventory table</td>
                  </tr>
                  <tr>
                    <td style="font-weight: 600; color: var(--accent-emerald);">${window.UI.Icon('coins', 14, '', 'var(--accent-emerald)')} FF Tokens</td>
                    <td><code style="font-family: var(--font-mono); color: var(--accent-amber);">110200001</code></td>
                    <td>Duplicate item exchange currency</td>
                    <td>inventory table</td>
                  </tr>
                `
              )}
            </div>
          </div>
        `}
      </div>
    `;
  }

  function switchTab(tab) {
    activeTab = tab;
    const canvas = document.getElementById('workspace-canvas');
    if (canvas) renderCurrencies(canvas);
  }

  function updatePreview(baseGold, baseDia) {
    const gInput = document.getElementById('grant-gold-input');
    const dInput = document.getElementById('grant-dia-input');
    const gAdd = parseInt(gInput ? gInput.value : 0, 10) || 0;
    const dAdd = parseInt(dInput ? dInput.value : 0, 10) || 0;

    const gEl = document.getElementById('preview-gold-val');
    const dEl = document.getElementById('preview-dia-val');
    if (gEl) gEl.innerText = formatNumber(baseGold + gAdd);
    if (dEl) dEl.innerText = formatNumber(baseDia + dAdd);
  }

  function fillPreset(gold, dia) {
    const gInput = document.getElementById('set-gold-input');
    const dInput = document.getElementById('set-dia-input');
    if (gInput) gInput.value = gold;
    if (dInput) dInput.value = dia;
  }

  function promptGrant() {
    const aid = window.playerContext.getSelectedAccountId();
    const gold = parseInt(document.getElementById('grant-gold-input').value, 10) || 0;
    const dia = parseInt(document.getElementById('grant-dia-input').value, 10) || 0;

    if (gold <= 0 && dia <= 0) {
      window.UI.Toast('Please enter an amount greater than 0 for Gold or Diamonds', 'warning');
      return;
    }

    window.UI.Confirm(
      'Grant Currency',
      `Grant <b>+${formatNumber(gold)} Gold</b> and <b>+${formatNumber(dia)} Diamonds</b> to Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/wallet/grant', {
            account_id: aid,
            gold: gold,
            diamonds: dia,
            coins: gold,
            gems: dia
          });
          if (res.ok) {
            window.UI.Toast(`Granted funds to Account ${aid} successfully`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderCurrencies(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to grant funds', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      }
    );
  }

  function promptSetBalance() {
    const aid = window.playerContext.getSelectedAccountId();
    const gold = parseInt(document.getElementById('set-gold-input').value, 10);
    const dia = parseInt(document.getElementById('set-dia-input').value, 10);

    if (isNaN(gold) || isNaN(dia) || gold < 0 || dia < 0) {
      window.UI.Toast('Please enter non-negative integer values for Gold and Diamonds', 'warning');
      return;
    }

    window.UI.Confirm(
      'Overwrite Wallet Balance',
      `<b>CAUTION:</b> Overwrite Account <b>${aid}</b>'s balance to exact <b>${formatNumber(gold)} Gold</b> and <b>${formatNumber(dia)} Diamonds</b>? This permanently modifies database records.`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/wallet/set', {
            account_id: aid,
            gold: gold,
            diamonds: dia,
            coins: gold,
            gems: dia
          });
          if (res.ok) {
            window.UI.Toast(`Wallet balance updated for Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderCurrencies(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to update balance', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      },
      true
    );
  }

  function promptGrantVoucher(itemId, voucherName, qty) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Grant Voucher / Token',
      `Grant <b>${qty}x ${voucherName}</b> (Item ID: <code>${itemId}</code>) to Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/items/grant', {
            account_id: aid,
            item_ids: [itemId],
            count: qty
          });
          if (res.ok) {
            window.UI.Toast(`Granted ${qty}x ${voucherName} to Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderCurrencies(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to grant voucher', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      }
    );
  }

  // Reactive listener to playerContext account switches
  if (window.playerContext && typeof window.playerContext.onPlayerChange === 'function') {
    window.playerContext.onPlayerChange(() => {
      if (window.location.hash.startsWith('#/economy/currencies')) {
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) renderCurrencies(canvas);
      }
    });
  }

  // Export module interface
  window.Modules = window.Modules || {};
  window.Modules.CurrencyManager = renderCurrencies;

  window.CurrencyManager = {
    render: renderCurrencies,
    switchTab,
    updatePreview,
    fillPreset,
    promptGrant,
    promptSetBalance,
    promptGrantVoucher
  };

  // Register SPA route
  function bindRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/economy/currencies', renderCurrencies);
    }
  }

  bindRoute();
  document.addEventListener('DOMContentLoaded', () => setTimeout(bindRoute, 0));
})();
