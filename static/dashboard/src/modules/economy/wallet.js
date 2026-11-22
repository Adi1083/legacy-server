/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Player Wallet Inspector & Transaction Ledger
 * Route: #/economy/wallet
 *
 * Capabilities:
 * - Reactive binding to PlayerContext (active account, live gold & diamonds)
 * - Standardized .page-container layout with UI.PageHeader & .grid-4 metric strip
 * - High-polish dark glass styling with active wallet tier gauges
 * - Symmetrical 50/50 split view: Financial Profile & Balances vs Voucher & Synthesis Matrix
 * - Live Economy Transaction Ledger & Audit Trail loaded from GET /api/admin/players/{id}
 * - Quick grant action triggers with UI.Confirm -> POST /api/dashboard/wallet/grant
 * - Zero consumer emojis
 */

(function () {
  'use strict';

  let ledgerSearchQuery = '';

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

  function formatTimestamp(ts) {
    if (!ts) return '—';
    try {
      const d = new Date(ts > 10000000000 ? ts : ts * 1000);
      return d.toISOString().replace('T', ' ').slice(0, 19);
    } catch (e) {
      return String(ts);
    }
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

  async function renderWallet(canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Loading('Loading wallet dossier & transaction ledger...');

    let p = window.playerContext.getCurrentPlayer();
    let dossierData = null;

    try {
      const [stateRes, playerDossierRes] = await Promise.all([
        window.apiClient.get('/api/dashboard/state', { account_id: aid }),
        window.apiClient.get(`/api/admin/players/${aid}`)
      ]);

      if (stateRes.ok && stateRes.data) p = stateRes.data;
      if (playerDossierRes.ok && playerDossierRes.data) {
        dossierData = playerDossierRes.data;
      }
    } catch (e) {
      console.error('State load error', e);
    }

    const wallet = (dossierData && dossierData.wallet) || (p && p.wallet) || { gold: 0, diamonds: 0, coins: 0, gems: 0 };
    const curGold = wallet.gold !== undefined ? wallet.gold : (wallet.coins || 0);
    const curDia = wallet.diamonds !== undefined ? wallet.diamonds : (wallet.gems || 0);

    const goldTier = getGoldTier(curGold);
    const diaTier = getDiamondTier(curDia);

    const nick = (dossierData && (dossierData.player && dossierData.player.nickname)) || (p && (p.nickname || (p.profile && p.profile.nickname))) || 'PushpaGG';
    const level = (dossierData && (dossierData.player && dossierData.player.level)) || (p && (p.level || (p.profile && p.profile.level))) || 60;
    const region = (dossierData && (dossierData.player && dossierData.player.region)) || (p && (p.region || (p.profile && p.profile.region))) || 'IND';

    // Compute voucher counts from inventory
    const inventory = (dossierData && dossierData.inventory) || (p && p.inventory) || [];
    function countItem(id) {
      const match = inventory.find(it => (it.item_id || it.id || it) === id);
      return match ? (match.amount || match.count || 1) : 0;
    }

    const goldVouchers = countItem(110100010);
    const diaVouchers = countItem(110100008);
    const weaponVouchers = countItem(110100009);
    const incubatorVouchers = countItem(110100018);
    const evoStones = countItem(808000003);
    const ffTokens = countItem(110200001);
    const totalVouchers = goldVouchers + diaVouchers + weaponVouchers + incubatorVouchers;

    // Gather transaction & audit log records
    const auditLogs = (dossierData && dossierData.audit_logs) || [];
    const gachaTransactions = (dossierData && dossierData.gacha_transactions) || [];

    // Unified economy ledger records
    const ledgerItems = [];

    auditLogs.forEach(log => {
      const isEconomyAction = log.action_type && (
        log.action_type.startsWith('WALLET_') ||
        log.action_type.startsWith('ITEM_') ||
        log.action_type.startsWith('CURRENCY_')
      );
      if (isEconomyAction || auditLogs.length <= 10) {
        ledgerItems.push({
          id: log.id || `LOG-${Math.random().toString(36).substr(2, 6)}`,
          timestamp: log.timestamp,
          actionType: log.action_type || 'AUDIT_LOG',
          summary: log.summary || 'Database state mutation',
          payload: log.payload || {},
          source: 'Admin REST API'
        });
      }
    });

    gachaTransactions.forEach(tx => {
      ledgerItems.push({
        id: tx.trans_id || `GTX-${Math.random().toString(36).substr(2, 6)}`,
        timestamp: tx.timestamp,
        actionType: 'GACHA_SPIN',
        summary: `Gacha pull chest #${tx.chest_id} (Cost: ${tx.cost_amount} ${tx.cost_type === 1 ? 'Gold' : 'Diamonds'})`,
        payload: { cost: tx.cost_amount, type: tx.cost_type },
        source: 'Lobby Daemon'
      });
    });

    // Sort descending by timestamp
    ledgerItems.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

    // Filter by search query
    const filteredLedger = ledgerItems.filter(item => {
      if (!ledgerSearchQuery) return true;
      const q = ledgerSearchQuery.toLowerCase();
      return (
        String(item.id).toLowerCase().includes(q) ||
        item.actionType.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q)
      );
    });

    const ledgerRowsHtml = filteredLedger.map(item => {
      const isGrant = item.actionType.includes('GRANT') || item.actionType.includes('ADD');
      const isSet = item.actionType.includes('SET');
      const isSpend = item.actionType.includes('SPIN') || item.actionType.includes('PURCHASE') || item.actionType.includes('SPEND');

      const badgeTone = isGrant ? 'emerald' : isSet ? 'amber' : isSpend ? 'cyan' : 'neutral';

      return `
        <tr>
          <td><code style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); font-weight: 600;">#${item.id}</code></td>
          <td><span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">${formatTimestamp(item.timestamp)}</span></td>
          <td>${window.UI.Badge(item.actionType, badgeTone)}</td>
          <td style="font-size: 11.5px; color: #fff;">${escapeHtml(item.summary)}</td>
          <td><code style="font-family: var(--font-mono); font-size: 10.5px; color: var(--text-tertiary);">${escapeHtml(item.source)}</code></td>
        </tr>
      `;
    }).join('');

    const pageActionsHtml = `
      <button class="btn btn-primary" onclick="window.location.hash='#/economy/currencies'">
        ${window.UI.Icon('sliders', 14)} <span>Adjust Currencies</span>
      </button>
      <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.WalletInspector.render(c);">
        ${window.UI.Icon('refresh', 14)} <span>Sync Balances</span>
      </button>
    `;

    canvas.innerHTML = `
      <div class="page-container">
        <!-- 1. Page Header -->
        ${window.UI.PageHeader(
          'Player Wallet & Financial Dossier',
          'Real-time account balances, voucher reserves, and transaction ledger',
          pageActionsHtml,
          'creditCard'
        )}

        <!-- 2. Exactly 4 Compact Metrics (.grid-4) -->
        <div class="grid-4" style="margin-bottom: var(--space-md);">
          ${window.UI.StatCard(
            'Gold Balance',
            formatNumber(curGold),
            goldTier.label,
            window.UI.Icon('coins', 16, '', 'var(--accent-amber)'),
            'amber'
          )}
          ${window.UI.StatCard(
            'Diamond Balance',
            formatNumber(curDia),
            diaTier.label,
            window.UI.Icon('diamond', 16, '', 'var(--accent-cyan)'),
            'cyan'
          )}
          ${window.UI.StatCard(
            'Total Vouchers Owned',
            `${totalVouchers} Tickets`,
            'Luck Royale & Forge',
            window.UI.Icon('ticket', 16, '', 'var(--accent-emerald)'),
            'emerald'
          )}
          ${window.UI.StatCard(
            'Active Context Profile',
            `Account ${aid}`,
            `${escapeHtml(nick)} • Lv.${level}`,
            window.UI.Icon('userCheck', 16, '', 'var(--accent-blue)'),
            'blue'
          )}
        </div>

        <!-- 3. Symmetrical 50/50 Split View -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <!-- Left Column: Active Player Identity & Financial Reserves -->
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <!-- Profile Identity Banner -->
            <div style="background: linear-gradient(135deg, rgba(14, 28, 54, 0.7), rgba(8, 14, 26, 0.85)); border: 1px solid var(--border-accent); border-radius: var(--radius-md); padding: 18px; display: flex; align-items: center; justify-content: space-between;">
              <div style="display: flex; align-items: center; gap: 14px;">
                <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #fbbf24, var(--accent-cyan)); display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                  ${window.UI.Icon('creditCard', 22, '', '#ffffff')}
                </div>
                <div>
                  <div style="font-size: 11px; color: var(--accent-cyan); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Financial Profile Identity</div>
                  <div style="font-size: 17px; font-weight: 700; color: #fff;">
                    Account ${aid} <span style="font-size: 12px; font-weight: 400; color: var(--text-tertiary);">(${escapeHtml(nick)})</span>
                  </div>
                  <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">
                    Combat Level: <b>${level}</b> • Regional Shard: <b>${region}</b>
                  </div>
                </div>
              </div>

              <div>
                <button class="btn btn-secondary" onclick="window.location.hash='#/economy/currencies'">
                  Adjust Funds
                </button>
              </div>
            </div>

            <!-- Gold Vault Card -->
            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(10, 16, 28, 0.55); border: 1px solid rgba(251, 191, 36, 0.35); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25); border-radius: var(--radius-md); padding: 18px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600;">Gold Currency Reserves</div>
                ${window.UI.Badge(goldTier.label, goldTier.badge)}
              </div>
              <div style="font-size: 26px; font-weight: 800; color: #fbbf24; letter-spacing: -0.02em; display: flex; align-items: center; gap: 8px;">
                ${window.UI.Icon('coins', 22, '', '#fbbf24')} <span>${formatNumber(curGold)}</span>
              </div>
              <div style="display: flex; gap: 6px; margin-top: 14px;">
                <button class="btn btn-secondary" style="flex: 1; padding: 5px 8px; font-size: 11px;" onclick="window.WalletInspector.quickGrantGold(25000)">
                  ${window.UI.Icon('plus', 12)} +25k Quick Grant
                </button>
                <button class="btn btn-secondary" style="flex: 1; padding: 5px 8px; font-size: 11px;" onclick="window.WalletInspector.quickGrantGold(100000)">
                  ${window.UI.Icon('plus', 12)} +100k Quick Grant
                </button>
              </div>
            </div>

            <!-- Diamond Vault Card -->
            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(10, 16, 28, 0.55); border: 1px solid rgba(56, 189, 248, 0.35); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25); border-radius: var(--radius-md); padding: 18px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600;">Diamond Currency Reserves</div>
                ${window.UI.Badge(diaTier.label, diaTier.badge)}
              </div>
              <div style="font-size: 26px; font-weight: 800; color: var(--accent-cyan); letter-spacing: -0.02em; display: flex; align-items: center; gap: 8px;">
                ${window.UI.Icon('diamond', 22, '', 'var(--accent-cyan)')} <span>${formatNumber(curDia)}</span>
              </div>
              <div style="display: flex; gap: 6px; margin-top: 14px;">
                <button class="btn btn-secondary" style="flex: 1; padding: 5px 8px; font-size: 11px;" onclick="window.WalletInspector.quickGrantDia(1000)">
                  ${window.UI.Icon('plus', 12)} +1k Quick Grant
                </button>
                <button class="btn btn-secondary" style="flex: 1; padding: 5px 8px; font-size: 11px;" onclick="window.WalletInspector.quickGrantDia(5000)">
                  ${window.UI.Icon('plus', 12)} +5k Quick Grant
                </button>
              </div>
            </div>
          </div>

          <!-- Right Column: Voucher & Synthesis Reserves Matrix -->
          <div style="background: rgba(10, 16, 28, 0.45); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 18px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
                <div>
                  <div style="font-size: 14px; font-weight: 700; color: #fff;">Luck Royale Vouchers & Synthesis Items</div>
                  <div style="font-size: 11px; color: var(--text-tertiary);">Tracked directly from player inventory table records</div>
                </div>
                <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="window.location.hash='#/luck-royale/overview'">
                  Luck Royale Studio
                </button>
              </div>

              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px;">
                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px;">
                  <div style="font-size: 10.5px; color: var(--text-tertiary); text-transform: uppercase;">Gold Royale</div>
                  <div style="font-size: 18px; font-weight: 700; color: #fbbf24; margin: 3px 0;">${goldVouchers} Tickets</div>
                  <div style="font-size: 9.5px; font-family: var(--font-mono); color: var(--text-muted);">ID: 110100010</div>
                </div>

                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px;">
                  <div style="font-size: 10.5px; color: var(--text-tertiary); text-transform: uppercase;">Diamond Royale</div>
                  <div style="font-size: 18px; font-weight: 700; color: var(--accent-cyan); margin: 3px 0;">${diaVouchers} Tickets</div>
                  <div style="font-size: 9.5px; font-family: var(--font-mono); color: var(--text-muted);">ID: 110100008</div>
                </div>

                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px;">
                  <div style="font-size: 10.5px; color: var(--text-tertiary); text-transform: uppercase;">Weapon Royale</div>
                  <div style="font-size: 18px; font-weight: 700; color: var(--accent-amber); margin: 3px 0;">${weaponVouchers} Tickets</div>
                  <div style="font-size: 9.5px; font-family: var(--font-mono); color: var(--text-muted);">ID: 110100009</div>
                </div>

                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px;">
                  <div style="font-size: 10.5px; color: var(--text-tertiary); text-transform: uppercase;">Incubator</div>
                  <div style="font-size: 18px; font-weight: 700; color: var(--accent-violet); margin: 3px 0;">${incubatorVouchers} Tickets</div>
                  <div style="font-size: 9.5px; font-family: var(--font-mono); color: var(--text-muted);">ID: 110100018</div>
                </div>

                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px;">
                  <div style="font-size: 10.5px; color: var(--text-tertiary); text-transform: uppercase;">Evolution Stone</div>
                  <div style="font-size: 18px; font-weight: 700; color: var(--accent-rose); margin: 3px 0;">${evoStones} Stones</div>
                  <div style="font-size: 9.5px; font-family: var(--font-mono); color: var(--text-muted);">ID: 808000003</div>
                </div>

                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px;">
                  <div style="font-size: 10.5px; color: var(--text-tertiary); text-transform: uppercase;">FF Tokens</div>
                  <div style="font-size: 18px; font-weight: 700; color: var(--accent-emerald); margin: 3px 0;">${ffTokens} Tokens</div>
                  <div style="font-size: 9.5px; font-family: var(--font-mono); color: var(--text-muted);">ID: 110200001</div>
                </div>
              </div>
            </div>

            <div style="margin-top: 14px; border-top: 1px solid var(--border-subtle); padding-top: 12px;">
              <button class="btn btn-secondary" style="width: 100%; font-size: 11px;" onclick="window.location.hash='#/inventory/manager'">
                ${window.UI.Icon('package', 14)} Open Complete Inventory Vault
              </button>
            </div>
          </div>
        </div>

        <!-- 4. Full-Width Bottom Section: Economy Transaction Ledger & Audit Trail -->
        <div style="background: rgba(10, 16, 28, 0.45); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 18px;">
          <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 14px;">
            <div>
              <div style="font-size: 14px; font-weight: 700; color: #fff;">Economy Transaction Ledger & Audit Trail</div>
              <div style="font-size: 11px; color: var(--text-tertiary);">Historical wallet modifications and gacha coin consumption in india_v1.db</div>
            </div>

            <div style="min-width: 240px; max-width: 320px;">
              <input type="text" class="form-input" placeholder="Filter transactions by keyword..."
                value="${escapeHtml(ledgerSearchQuery)}"
                oninput="window.WalletInspector.handleLedgerSearch(this.value)">
            </div>
          </div>

          <div class="glass-table-container" style="max-height: 440px; overflow-y: auto;">
            ${window.UI.Table(
              ['Record ID', 'Timestamp (UTC)', 'Category / Action', 'Summary & Mutation Details', 'Source Protocol'],
              ledgerRowsHtml,
              'No financial transactions or wallet modifications recorded for this account.'
            )}
          </div>
        </div>
      </div>
    `;
  }

  function handleLedgerSearch(val) {
    ledgerSearchQuery = val.trim();
    const canvas = document.getElementById('workspace-canvas');
    if (canvas) renderWallet(canvas);
  }

  function quickGrantGold(amount) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Quick Grant Gold',
      `Grant <b>+${formatNumber(amount)} Gold</b> to Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/wallet/grant', {
            account_id: aid,
            gold: amount,
            diamonds: 0,
            coins: amount,
            gems: 0
          });
          if (res.ok) {
            window.UI.Toast(`Granted ${formatNumber(amount)} Gold to Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderWallet(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to grant gold', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      }
    );
  }

  function quickGrantDia(amount) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Quick Grant Diamonds',
      `Grant <b>+${formatNumber(amount)} Diamonds</b> to Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/wallet/grant', {
            account_id: aid,
            gold: 0,
            diamonds: amount,
            coins: 0,
            gems: amount
          });
          if (res.ok) {
            window.UI.Toast(`Granted ${formatNumber(amount)} Diamonds to Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderWallet(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to grant diamonds', 'error');
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
      if (window.location.hash.startsWith('#/economy/wallet')) {
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) renderWallet(canvas);
      }
    });
  }

  // Export module interface
  window.Modules = window.Modules || {};
  window.Modules.WalletInspector = renderWallet;

  window.WalletInspector = {
    render: renderWallet,
    handleLedgerSearch,
    quickGrantGold,
    quickGrantDia
  };

  // Register SPA route
  function bindRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/economy/wallet', renderWallet);
    }
  }

  bindRoute();
  document.addEventListener('DOMContentLoaded', () => setTimeout(bindRoute, 0));
})();
