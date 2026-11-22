/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.6: Incubator Special Exchange Forge (forge.js)
 * Clean macOS dark glass design system, zero emojis, authentic synthesis recipes.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Forge = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Incubator Special Exchange Recipes...');

  const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;

  // Fetch exchange recipes and player inventory
  const [exchangeRes, playerRes] = await Promise.all([
    window.apiClient.get('/api/admin/luck-royale/exchange'),
    window.apiClient.get(`/api/admin/players/${aid}`)
  ]);

  const exchanges = (exchangeRes.ok && exchangeRes.data && exchangeRes.data.exchanges) ? exchangeRes.data.exchanges : [];
  const player = (playerRes.ok && playerRes.data && playerRes.data.player) ? playerRes.data.player : {};
  const inventory = player.inventory || [];

  function getCount(id) {
    const it = inventory.find(x => x.item_id === id);
    return it ? (it.quantity || it.item_num || 0) : 0;
  }

  const evoCount = getCount(808000003);
  const yyBlueCount = getCount(808000011);
  const jkBlueCount = getCount(808000012);

  // Metric Strip
  const metricStrip = `
    <div class="grid-4" style="margin-bottom: 24px;">
      <div class="stat-card">
        <div class="stat-label">Active Forge Recipes</div>
        <div class="stat-value" style="color: var(--accent-cyan); font-family: var(--font-mono);">${exchanges.length}</div>
        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Configured in gacha_special_exchanges</div>
      </div>

      <div class="stat-card">
        <div class="stat-label">Player Evolution Stones</div>
        <div class="stat-value" style="color: var(--accent-amber); font-family: var(--font-mono);">${C.formatNumber(evoCount)}</div>
        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Item ID: 808000003</div>
      </div>

      <div class="stat-card">
        <div class="stat-label">Player YinYang Blueprints</div>
        <div class="stat-value" style="color: #fff; font-family: var(--font-mono);">${C.formatNumber(yyBlueCount)}</div>
        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Item ID: 808000011</div>
      </div>

      <div class="stat-card">
        <div class="stat-label">Player Joker Blueprints</div>
        <div class="stat-value" style="color: var(--accent-indigo); font-family: var(--font-mono);">${C.formatNumber(jkBlueCount)}</div>
        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Item ID: 808000012</div>
      </div>
    </div>
  `;

  // Recipe Rows
  const rows = exchanges.map(ex => {
    const meta = C.lookupItem(ex.item_id);
    const hasMaterials = evoCount >= (ex.evolution_stones || 0) && (yyBlueCount >= (ex.blueprints || 0) || jkBlueCount >= (ex.blueprints || 0));

    return `
      <tr>
        <td>
          <div style="display: flex; align-items: center; gap: 10px;">
            ${C.renderItemImage(null, ex.name || meta.name, 36)}
            <div>
              <div style="font-weight: 600; color: #fff;">${C.escapeHtml(ex.name || meta.name)}</div>
              <div style="font-size: 10.5px; font-family: var(--font-mono); color: var(--accent-cyan);">ID: ${ex.item_id}</div>
            </div>
          </div>
        </td>
        <td>${window.UI.Badge(ex.forge_tab_id === 1 ? 'YinYang' : 'Joker', ex.forge_tab_id === 1 ? 'cyan' : 'indigo')}</td>
        <td>
          <span style="font-family: var(--font-mono); font-weight: 600; color: var(--accent-amber);">
            ${ex.evolution_stones || ex.consume_stone || 3} Stones
          </span>
        </td>
        <td>
          <span style="font-family: var(--font-mono); font-weight: 600; color: #fff;">
            ${ex.blueprints || ex.consume_blueprint || 1} Blueprints
          </span>
        </td>
        <td>
          ${hasMaterials ? window.UI.Badge('CRAFT READY', 'emerald') : window.UI.Badge('INSUFFICIENT', 'neutral')}
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.TestCraftExchange(${aid}, ${ex.forge_tab_id || 1}, ${ex.item_id})">
              Test Craft
            </button>
            <button class="btn btn-danger" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.DeleteExchange(${ex.forge_tab_id || 1}, ${ex.item_id})">
              &times;
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Incubator Special Exchange Forge',
        'Manage high-tier bundle redemption formulas requiring Evolution Stones and Theme Blueprints',
        `
          <button class="btn btn-primary" onclick="window.LuckRoyale.OpenCreateExchangeModal()">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('plus', 12)} Add Recipe</span>
          </button>
        `,
        'hammer'
      )}

      ${C.renderSubNav('forge')}

      ${metricStrip}

      <!-- Recipes Card -->
      <div class="glass-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; font-size: 13.5px; color: #fff;">
            Registered Special Exchange Recipes (${exchanges.length})
          </div>
          <div style="font-size: 11.5px; color: var(--text-tertiary);">
            Redemption executed via DoGachaSpecialExchange protocol
          </div>
        </div>
        <div>
          ${window.UI.Table(['Grand Prize Bundle', 'Forge Tab', 'Required Stones', 'Required Blueprints', 'Player Craft Status', 'Actions'], rows, 'No recipes configured.')}
        </div>
      </div>
    </div>
  `;
};

window.LuckRoyale.TestCraftExchange = async function (accountId, tabId, itemId) {
  window.UI.Toast('Simulating craft exchange for player...', 'info');
  // Dispatches gacha exchange API or grants item
  const res = await window.apiClient.post('/api/dashboard/items/grant', {
    account_id: accountId,
    item_id: itemId,
    quantity: 1
  });
  if (res.ok) {
    window.UI.Toast(`Crafted bundle #${itemId} for UID ${accountId}!`, 'success');
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Craft failed.', 'danger');
  }
};

window.LuckRoyale.DeleteExchange = function (tabId, itemId) {
  window.UI.Confirm({
    title: 'Delete Forge Recipe',
    message: `Are you sure you want to delete the recipe for Item #${itemId}? Players will no longer be able to forge it.`,
    confirmText: 'Delete Recipe',
    confirmDanger: true,
    onConfirm: async () => {
      const res = await window.apiClient.delete('/api/admin/luck-royale/exchange', {
        forge_tab_id: tabId,
        item_id: itemId
      });
      if (res.ok) {
        window.UI.Toast(`Recipe for #${itemId} deleted.`, 'success');
        window.appRouter.handleRoute();
      } else {
        window.UI.Toast(res.error || 'Failed to delete recipe.', 'danger');
      }
    }
  });
};

window.LuckRoyale.OpenCreateExchangeModal = function () {
  const modalHtml = `
    <div id="create-forge-modal" class="modal-backdrop active" style="z-index: 9999;">
      <div class="modal-content" style="max-width: 440px;">
        <div class="modal-header">
          <div class="modal-title">Create Incubator Forge Recipe</div>
          <button class="modal-close" onclick="document.getElementById('create-forge-modal').remove()">&times;</button>
        </div>
        <form id="create-forge-form" onsubmit="window.LuckRoyale.SubmitCreateExchange(event); return false;" style="padding: 16px;">
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Target Bundle Item ID</label>
            <input type="number" name="item_id" class="form-input" placeholder="e.g. 710000410" required>
          </div>
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Forge Theme Tab</label>
            <select name="forge_tab_id" class="form-select">
              <option value="1">YinYang Theme (Tab 1)</option>
              <option value="2">Joker Theme (Tab 2)</option>
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Evolution Stones Required</label>
              <input type="number" name="evolution_stones" class="form-input" value="3" min="1" required>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Blueprints Required</label>
              <input type="number" name="blueprints" class="form-input" value="1" min="1" required>
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('create-forge-modal').remove()">Cancel</button>
            <button type="submit" class="btn btn-primary">Create Recipe</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
};

window.LuckRoyale.SubmitCreateExchange = async function (e) {
  const form = e.target;
  const payload = {
    item_id: parseInt(form.item_id.value, 10),
    forge_tab_id: parseInt(form.forge_tab_id.value, 10),
    evolution_stones: parseInt(form.evolution_stones.value, 10),
    blueprints: parseInt(form.blueprints.value, 10),
  };

  const res = await window.apiClient.post('/api/admin/luck-royale/exchange', payload);
  if (res.ok) {
    window.UI.Toast('Recipe created successfully.', 'success');
    const modal = document.getElementById('create-forge-modal');
    if (modal) modal.remove();
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to create recipe.', 'danger');
  }
};
