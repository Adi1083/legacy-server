/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.11: Monte Carlo Probability Simulator (simulator.js)
 * Clean macOS dark glass design system, zero emojis, verified offline probability model.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Simulator = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Probability Simulator...');

  // Fetch machines and active pool
  const machRes = await window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 });
  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];

  let activeCid = window.LuckRoyale._simCid || (machines[0] ? machines[0].chest_id : 3);
  const activeMachine = machines.find(m => m.chest_id === activeCid) || machines[0] || { chest_id: 3, display_name: 'Diamond Royale' };
  activeCid = activeMachine.chest_id;
  window.LuckRoyale._simCid = activeCid;

  const poolRes = await window.apiClient.get('/api/admin/luck-royale/reward-pools', { chest_id: activeCid });
  const items = (poolRes.ok && poolRes.data && poolRes.data.items) ? poolRes.data.items : [];

  const simResults = window.LuckRoyale._lastSimResults || null;

  // Machine Selector Options
  const machOptions = machines.map(m => `
    <option value="${m.chest_id}" ${m.chest_id === activeCid ? 'selected' : ''}>
      ${C.escapeHtml(m.display_name || m.chest_name)} (#${m.chest_id})
    </option>
  `).join('');

  let resultsHtml = '';
  if (simResults) {
    const totalSim = simResults.total;
    const srCount = simResults.superRare;
    const rCount = simResults.rare;
    const nCount = simResults.normal;

    const srPct = ((srCount / totalSim) * 100).toFixed(2);
    const rPct = ((rCount / totalSim) * 100).toFixed(2);
    const nPct = ((nCount / totalSim) * 100).toFixed(2);

    const rows = simResults.itemCounts.map(ic => {
      const dropPct = ((ic.count / totalSim) * 100).toFixed(2);
      return `
        <tr>
          <td>
            <div style="font-weight: 600; color: #fff;">${C.escapeHtml(ic.name)}</div>
            <div style="font-size: 10px; font-family: var(--font-mono); color: var(--accent-cyan);">ID: ${ic.item_id}</div>
          </td>
          <td>${C.rarityBadge(ic.reward_level)}</td>
          <td><span style="font-family: var(--font-mono); color: var(--text-tertiary);">${ic.theoreticalPct}%</span></td>
          <td>
            <span style="font-family: var(--font-mono); font-weight: 700; color: #fff;">${ic.count}</span>
            <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 4px;">(${dropPct}%)</span>
          </td>
        </tr>
      `;
    }).join('');

    resultsHtml = `
      <div class="grid-4" style="margin-bottom: 20px;">
        <div class="stat-card">
          <div class="stat-label">Total Simulated Rolls</div>
          <div class="stat-value" style="color: var(--accent-cyan); font-family: var(--font-mono);">${C.formatNumber(totalSim)}</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Executed offline in-memory</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Super Rare (Observed)</div>
          <div class="stat-value" style="color: var(--accent-amber); font-family: var(--font-mono);">${srPct}%</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Count: ${srCount} hits</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Rare (Observed)</div>
          <div class="stat-value" style="color: var(--accent-cyan); font-family: var(--font-mono);">${rPct}%</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Count: ${rCount} hits</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Normal (Observed)</div>
          <div class="stat-value" style="color: var(--text-secondary); font-family: var(--font-mono);">${nPct}%</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">Count: ${nCount} hits</div>
        </div>
      </div>

      <div class="glass-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); font-weight: 600; font-size: 13px; color: #fff;">
          Detailed Item Drop Frequency
        </div>
        <div style="max-height: 400px; overflow-y: auto;">
          ${window.UI.Table(['Reward Item', 'Rarity', 'Theoretical %', 'Observed Hits / %'], rows)}
        </div>
      </div>
    `;
  }

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Probability Simulator (Monte Carlo)',
        'Simulate thousands of offline gacha draws to statistically audit drop weights and guarantee convergence',
        null,
        'cpu'
      )}

      ${C.renderSubNav('simulator')}

      <!-- Simulation Setup Bar -->
      <div class="glass-card" style="padding: 18px; margin-bottom: 20px;">
        <div style="display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap;">
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Target Machine</label>
            <select id="sim-machine-select" class="form-select" style="min-width: 220px;" onchange="window.LuckRoyale._simCid=parseInt(this.value, 10); window.appRouter.handleRoute();">
              ${machOptions}
            </select>
          </div>

          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Iterations (Rolls)</label>
            <select id="sim-count-select" class="form-select" style="min-width: 140px;">
              <option value="500">500 Rolls</option>
              <option value="1000" selected>1,000 Rolls</option>
              <option value="5000">5,000 Rolls</option>
              <option value="10000">10,000 Rolls</option>
            </select>
          </div>

          <label style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); margin-bottom: 10px; cursor: pointer;">
            <input type="checkbox" id="sim-pity-check" checked>
            <span>Simulate Guaranteed Pity (${activeMachine.rare_item_max || 100} Lucky)</span>
          </label>

          <button class="btn btn-primary" style="margin-left: auto; padding: 7px 18px;" onclick="window.LuckRoyale.RunSimulation(${activeCid})">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('play', 12)} Run Simulation</span>
          </button>
        </div>
      </div>

      <!-- Results Display -->
      ${resultsHtml}
    </div>
  `;
};

window.LuckRoyale.RunSimulation = async function (chestId) {
  const countSelect = document.getElementById('sim-count-select');
  const pityCheck = document.getElementById('sim-pity-check');

  const rollsCount = countSelect ? parseInt(countSelect.value, 10) : 1000;
  const usePity = pityCheck ? pityCheck.checked : true;

  window.UI.Toast(`Simulating ${rollsCount} rolls for Machine #${chestId}...`, 'info');

  const poolRes = await window.apiClient.get('/api/admin/luck-royale/reward-pools', { chest_id: chestId });
  const items = (poolRes.ok && poolRes.data && poolRes.data.items) ? poolRes.data.items : [];
  if (items.length === 0) {
    window.UI.Toast('Pool is empty; cannot simulate.', 'warning');
    return;
  }

  const machRes = await window.apiClient.get('/api/admin/luck-royale/machines');
  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];
  const mach = machines.find(m => m.chest_id === chestId) || { rare_item_max: 100 };
  const pityMax = mach.rare_item_max || 100;

  const totalWeight = items.reduce((acc, it) => acc + (parseInt(it.weight, 10) || 0), 0) || 1;
  const superRareItems = items.filter(it => it.reward_level >= 2);

  const countsMap = {};
  items.forEach(it => { countsMap[it.item_id] = 0; });

  let curLucky = 0;
  let superRareHits = 0;
  let rareHits = 0;
  let normalHits = 0;

  for (let i = 0; i < rollsCount; i++) {
    let pickedItem = null;

    if (usePity && curLucky >= pityMax && superRareItems.length > 0) {
      pickedItem = superRareItems[Math.floor(Math.random() * superRareItems.length)];
      curLucky = 0;
    } else {
      let rand = Math.random() * totalWeight;
      for (const it of items) {
        rand -= (parseInt(it.weight, 10) || 0);
        if (rand <= 0) {
          pickedItem = it;
          break;
        }
      }
      if (!pickedItem) pickedItem = items[items.length - 1];

      if (pickedItem.reward_level >= 2) {
        curLucky = 0;
      } else {
        curLucky += 1;
      }
    }

    countsMap[pickedItem.item_id] = (countsMap[pickedItem.item_id] || 0) + 1;
    if (pickedItem.reward_level >= 2) superRareHits++;
    else if (pickedItem.reward_level === 1) rareHits++;
    else normalHits++;
  }

  const itemCountsList = items.map(it => ({
    item_id: it.item_id,
    name: it.name,
    reward_level: it.reward_level,
    theoreticalPct: (((parseInt(it.weight, 10) || 0) / totalWeight) * 100).toFixed(2),
    count: countsMap[it.item_id] || 0
  }));

  window.LuckRoyale._lastSimResults = {
    total: rollsCount,
    superRare: superRareHits,
    rare: rareHits,
    normal: normalHits,
    itemCounts: itemCountsList
  };

  window.LuckRoyale.Simulator(document.getElementById('app-canvas'));
};
