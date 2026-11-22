/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.3: Reward Pool Editor (pools.js)
 * Clean macOS dark glass design system, zero emojis, authentic item metadata.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Pools = async function (canvas, targetChestId) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Reward Pools & Item Weights...');

  // 1. Fetch all machines to populate switcher
  const machRes = await window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 });
  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];

  let activeCid = targetChestId || window.LuckRoyale._selectedPoolCid || (machines[0] ? machines[0].chest_id : 3);
  const activeMachine = machines.find(m => m.chest_id === activeCid) || machines[0] || { chest_id: 3, display_name: 'Diamond Royale' };
  activeCid = activeMachine.chest_id;
  window.LuckRoyale._selectedPoolCid = activeCid;

  // 2. Fetch specific pool for activeCid
  const poolRes = await window.apiClient.get('/api/admin/luck-royale/reward-pools', { chest_id: activeCid });
  const poolData = (poolRes.ok && poolRes.data) ? poolRes.data : { items: [] };
  const items = poolData.items || [];

  // Calculate probability distribution
  const totalWeight = items.reduce((acc, it) => acc + (parseInt(it.weight, 10) || 0), 0) || 1;
  const superRareWeight = items.filter(it => it.reward_level >= 2).reduce((acc, it) => acc + (parseInt(it.weight, 10) || 0), 0);
  const rareWeight = items.filter(it => it.reward_level === 1).reduce((acc, it) => acc + (parseInt(it.weight, 10) || 0), 0);
  const normalWeight = items.filter(it => it.reward_level === 0).reduce((acc, it) => acc + (parseInt(it.weight, 10) || 0), 0);

  const superRarePct = ((superRareWeight / totalWeight) * 100).toFixed(2);
  const rarePct = ((rareWeight / totalWeight) * 100).toFixed(2);
  const normalPct = ((normalWeight / totalWeight) * 100).toFixed(2);

  // Machine Switcher Pills
  const machinePills = machines.map(m => {
    const isCur = m.chest_id === activeCid;
    return `
      <button class="btn ${isCur ? 'btn-primary' : 'btn-secondary'}" style="padding: 6px 14px; font-size: 12px; border-radius: var(--radius-full);" onclick="window.LuckRoyale._selectedPoolCid=${m.chest_id}; window.appRouter.handleRoute();">
        <span style="font-weight: ${isCur ? '600' : '500'};">${C.escapeHtml(m.display_name || m.chest_name)}</span>
        <span style="opacity: 0.7; font-family: var(--font-mono); font-size: 10.5px; margin-left: 4px;">(${m.items_count || 0})</span>
      </button>
    `;
  }).join('');

  // Item rows
  const itemRows = items.map((it, idx) => {
    const w = parseInt(it.weight, 10) || 0;
    const dropPct = ((w / totalWeight) * 100).toFixed(2);
    const meta = C.lookupItem(it.item_id);

    let repId = it.repeated_item_id;
    if (activeCid === 5 && (it.item_id >= 100000000 && it.item_id < 200000000)) {
      if (C.AVATAR_DEBRIS_MAP[it.item_id]) {
        repId = C.AVATAR_DEBRIS_MAP[it.item_id];
      }
    }
    const repMeta = C.lookupItem(repId || 110200001);
    const isCharDebris = repMeta.category === 'Character Fragment' || (repId >= 800000000 && repId < 900000000);

    return `
      <tr>
        <td>
          <div style="display: flex; align-items: center; gap: 10px;">
            ${C.renderItemImage(it.image_url, it.name || meta.name, 36)}
            <div>
              <div style="font-weight: 600; color: #fff;">${C.escapeHtml(it.name || meta.name)}</div>
              <div style="font-size: 10.5px; font-family: var(--font-mono); color: var(--accent-cyan);">ID: ${it.item_id}</div>
            </div>
          </div>
        </td>
        <td>${C.escapeHtml(it.category || meta.category)}</td>
        <td>${C.rarityBadge(it.reward_level)}</td>
        <td>
          <span style="font-family: var(--font-mono); font-weight: 600; color: #fff;">${w}</span>
          <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 4px;">(${dropPct}%)</span>
        </td>
        <td><code style="font-family: var(--font-mono);">${it.item_num || 1}</code></td>
        <td>
          <span style="font-size: 11px; color: ${isCharDebris ? 'var(--accent-amber)' : 'var(--text-secondary)'}; font-weight: ${isCharDebris ? '600' : '400'};">
            ${C.escapeHtml(repMeta.name)} x${it.repeated_item_num || 5}
          </span>
        </td>
        <td>
          <div style="display: flex; gap: 3px;">
            <button class="btn btn-secondary" style="padding: 3px 6px; font-size: 10px;" onclick="window.LuckRoyale.ReorderPoolItem(${activeCid}, ${it.item_id}, 'up')" ${idx === 0 ? 'disabled' : ''} title="Move Up">▲</button>
            <button class="btn btn-secondary" style="padding: 3px 6px; font-size: 10px;" onclick="window.LuckRoyale.ReorderPoolItem(${activeCid}, ${it.item_id}, 'down')" ${idx === items.length - 1 ? 'disabled' : ''} title="Move Down">▼</button>
          </div>
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.OpenEditPoolItemModal(${activeCid}, ${it.item_id})">Edit</button>
            <button class="btn btn-danger" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.RemovePoolItem(${activeCid}, ${it.item_id})">&times;</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Reward Pool Editor',
        `Drop weight distribution and reward catalogue for ${C.escapeHtml(activeMachine.display_name)} (ID: ${activeCid})`,
        `
          <button class="btn btn-primary" onclick="window.LuckRoyale.OpenAddPoolItemModal(${activeCid})">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('plus', 12)} Add Reward</span>
          </button>
        `,
        'gift'
      )}

      ${C.renderSubNav('pools')}

      <!-- Machine Selector Pills -->
      <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 16px; scrollbar-width: none;">
        ${machinePills}
      </div>

      <!-- Probability Stats Strip -->
      <div class="grid-4" style="margin-bottom: 20px;">
        <div class="stat-card">
          <div class="stat-label">Total Drop Weight</div>
          <div class="stat-value" style="color: var(--text-primary); font-family: var(--font-mono);">${C.formatNumber(totalWeight)}</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Denominator across ${items.length} items</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">Super Rare (Tier 2)</div>
          <div class="stat-value" style="color: var(--accent-amber); font-family: var(--font-mono);">${superRarePct}%</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Weight: ${superRareWeight}</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">Rare (Tier 1)</div>
          <div class="stat-value" style="color: var(--accent-cyan); font-family: var(--font-mono);">${rarePct}%</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Weight: ${rareWeight}</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">Normal (Tier 0)</div>
          <div class="stat-value" style="color: var(--text-secondary); font-family: var(--font-mono);">${normalPct}%</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Weight: ${normalWeight}</div>
        </div>
      </div>

      <!-- Reward Table -->
      <div class="glass-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; font-size: 13.5px; color: #fff;">
            Configured Rewards: ${C.escapeHtml(activeMachine.display_name)} (${items.length} items)
          </div>
          <div style="font-size: 11.5px; color: var(--text-tertiary);">
            Reordering items updates display sequence without altering random draw weights
          </div>
        </div>
        <div style="max-height: 520px; overflow-y: auto;">
          ${window.UI.Table(['Reward Item', 'Category', 'Rarity', 'Weight / Drop %', 'Qty', 'Duplicate Conversion', 'Order', 'Actions'], itemRows, 'No reward items configured in this pool.')}
        </div>
      </div>
    </div>
  `;
};

// Modals for Adding / Editing Pool Items
window.LuckRoyale.OpenAddPoolItemModal = function (chestId) {
  const modalHtml = `
    <div id="add-pool-item-modal" class="modal-backdrop active" style="z-index: 9999;">
      <div class="modal-content" style="max-width: 480px;">
        <div class="modal-header">
          <div class="modal-title">Add Reward to Machine #${chestId}</div>
          <button class="modal-close" onclick="document.getElementById('add-pool-item-modal').remove()">&times;</button>
        </div>
        <form id="add-pool-item-form" onsubmit="window.LuckRoyale.SubmitAddPoolItem(event, ${chestId}); return false;" style="padding: 16px;">
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Item ID (Numeric)</label>
            <input type="number" name="item_id" class="form-input" placeholder="e.g. 710000410" required>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Quantity (Num)</label>
              <input type="number" name="item_num" class="form-input" value="1" min="1" required>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Rarity Tier</label>
              <select name="reward_level" class="form-select">
                <option value="2">Super Rare (Grand Prize)</option>
                <option value="1">Rare</option>
                <option value="0" selected>Normal</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Drop Weight</label>
              <input type="number" name="weight" class="form-input" value="100" min="1" required>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Repeated / Debris Qty</label>
              <input type="number" name="repeated_item_num" class="form-input" value="5" min="1">
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('add-pool-item-modal').remove()">Cancel</button>
            <button type="submit" class="btn btn-primary">Add Item to Pool</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
};

window.LuckRoyale.SubmitAddPoolItem = async function (e, chestId) {
  const form = e.target;
  const payload = {
    chest_id: chestId,
    item_id: parseInt(form.item_id.value, 10),
    item_num: parseInt(form.item_num.value, 10),
    reward_level: parseInt(form.reward_level.value, 10),
    weight: parseInt(form.weight.value, 10),
    repeated_item_num: parseInt(form.repeated_item_num.value, 10),
  };

  const res = await window.apiClient.post('/api/admin/luck-royale/reward-pools', payload);
  if (res.ok) {
    window.UI.Toast('Item added to reward pool successfully.', 'success');
    const modal = document.getElementById('add-pool-item-modal');
    if (modal) modal.remove();
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to add item.', 'danger');
  }
};

window.LuckRoyale.OpenEditPoolItemModal = async function (chestId, itemId) {
  const poolRes = await window.apiClient.get('/api/admin/luck-royale/reward-pools', { chest_id: chestId });
  const items = (poolRes.ok && poolRes.data) ? poolRes.data.items : [];
  const it = items.find(x => x.item_id === itemId) || { item_id: itemId, weight: 100, item_num: 1, reward_level: 0 };

  const modalHtml = `
    <div id="edit-pool-item-modal" class="modal-backdrop active" style="z-index: 9999;">
      <div class="modal-content" style="max-width: 480px;">
        <div class="modal-header">
          <div class="modal-title">Edit Reward: ${it.name || 'Item #' + itemId}</div>
          <button class="modal-close" onclick="document.getElementById('edit-pool-item-modal').remove()">&times;</button>
        </div>
        <form id="edit-pool-item-form" onsubmit="window.LuckRoyale.SubmitEditPoolItem(event, ${chestId}, ${itemId}); return false;" style="padding: 16px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Drop Weight</label>
              <input type="number" name="weight" class="form-input" value="${it.weight || 100}" min="1" required>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Rarity Tier</label>
              <select name="reward_level" class="form-select">
                <option value="2" ${it.reward_level === 2 ? 'selected' : ''}>Super Rare</option>
                <option value="1" ${it.reward_level === 1 ? 'selected' : ''}>Rare</option>
                <option value="0" ${it.reward_level === 0 ? 'selected' : ''}>Normal</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Quantity</label>
              <input type="number" name="item_num" class="form-input" value="${it.item_num || 1}" min="1" required>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Repeated Qty</label>
              <input type="number" name="repeated_item_num" class="form-input" value="${it.repeated_item_num || 5}" min="1">
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('edit-pool-item-modal').remove()">Cancel</button>
            <button type="submit" class="btn btn-primary">Save Changes</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
};

window.LuckRoyale.SubmitEditPoolItem = async function (e, chestId, itemId) {
  const form = e.target;
  const payload = {
    chest_id: chestId,
    item_id: itemId,
    weight: parseInt(form.weight.value, 10),
    reward_level: parseInt(form.reward_level.value, 10),
    item_num: parseInt(form.item_num.value, 10),
    repeated_item_num: parseInt(form.repeated_item_num.value, 10),
  };

  const res = await window.apiClient.put('/api/admin/luck-royale/reward-pools', payload);
  if (res.ok) {
    window.UI.Toast('Reward updated successfully.', 'success');
    const modal = document.getElementById('edit-pool-item-modal');
    if (modal) modal.remove();
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to update reward.', 'danger');
  }
};
