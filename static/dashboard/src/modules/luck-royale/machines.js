/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Unified Administrative Control & Management Workspace
 * (machines.js)
 *
 * Implements:
 * 1. Single unified workspace shell without duplicate topbars or nested headers.
 * 2. Dynamic machine selector discovering all configured turntables.
 * 3. 7 integrated machine tabs: Overview, Settings, Artwork, Prize Pool, Events, Pity/Vouchers, Preview.
 * 4. Modal & Drawer editing: Edit Machine, Add Reward, Edit Reward, Artwork Drawer, Event Editor, Image Mapping.
 * 5. Authentic Free Fire 1.39 game assets connected to every reward, machine poster, and thumbnail.
 * 6. Working in-place display reordering (▲ / ▼) with preserved drop weights.
 * 7. Zero consumer emojis, 100% Lucide SVG icons.
 */

window.LuckRoyale = window.LuckRoyale || {};

(function () {
  'use strict';

  const C = window.LuckRoyale.Common || {};

  // Studio persistent state
  let _selectedCid = 3; // Default: Diamond Royale
  let _activeTab = 'overview'; // Default internal tab
  let _cachedMachines = [];
  let _cachedPool = null;
  let _cachedArtwork = null;
  let _cachedEvent = null;
  let _cachedAssets = [];
  let _cachedMeters = {};
  let _poolSearchQuery = '';
  let _poolCategoryFilter = 'all';
  let _drawerSlotKey = null;

  // Active modal element reference for Escape handler
  let _activeModalEl = null;

  // Global escape key listener for all Luck Royale modals & drawers
  if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && _activeModalEl) {
        closeActiveModal();
      }
    });
  }

  function closeActiveModal() {
    if (_activeModalEl) {
      _activeModalEl.remove();
      _activeModalEl = null;
    }
    const overlays = document.querySelectorAll('.luck-royale-modal-overlay');
    overlays.forEach(el => el.remove());
  }

  // ---------------------------------------------------------------------------
  // Data Fetchers
  // ---------------------------------------------------------------------------

  async function fetchMachines() {
    try {
      const res = await (window.apiClient || window.ApiClient).get('/api/admin/luck-royale/machines?include_disabled=1');
      const data = (res && res.data) ? res.data : res;
      if (data && data.machines) {
        _cachedMachines = data.machines;
        if (!_cachedMachines.some(m => m.chest_id === _selectedCid) && _cachedMachines.length > 0) {
          _selectedCid = _cachedMachines[0].chest_id;
        }
      }
    } catch (e) {
      console.error('[LuckRoyale] Failed to fetch machines:', e);
    }
    return _cachedMachines;
  }

  async function fetchMachineData(cid) {
    try {
      const [poolRes, artRes, evRes] = await Promise.all([
        (window.apiClient || window.ApiClient).get(`/api/admin/luck-royale/reward-pools?chest_id=${cid}`),
        (window.apiClient || window.ApiClient).get(`/api/admin/luck-royale/machines/${cid}/artwork`),
        (window.apiClient || window.ApiClient).get(`/api/admin/luck-royale/machines/${cid}/events`)
      ]);
      const poolData = (poolRes && poolRes.data) ? poolRes.data : poolRes;
      const artData = (artRes && artRes.data) ? artRes.data : artRes;
      const evData = (evRes && evRes.data) ? evRes.data : evRes;

      _cachedPool = poolData || { items: [] };
      _cachedArtwork = (artData && artData.artwork) || {};
      _cachedEvent = (evData && evData.event) || {};
    } catch (e) {
      console.error(`[LuckRoyale] Failed to fetch machine ${cid} data:`, e);
    }
  }

  async function fetchAssets() {
    try {
      const res = await (window.apiClient || window.ApiClient).get('/api/admin/luck-royale/assets');
      const data = (res && res.data) ? res.data : res;
      if (data && data.assets) {
        _cachedAssets = data.assets;
      }
    } catch (e) {
      console.error('[LuckRoyale] Failed to fetch assets:', e);
    }
    return _cachedAssets;
  }

  function getCanvas() {
    return document.getElementById('workspace-canvas') || getCanvas();
  }

  // ---------------------------------------------------------------------------
  // Master Studio Renderer
  // ---------------------------------------------------------------------------

  async function renderStudio(canvas, initialTab, targetCid) {
    if (!canvas) canvas = getCanvas();
    if (!canvas) return;

    if (initialTab) _activeTab = initialTab;
    if (targetCid) _selectedCid = parseInt(targetCid, 10);

    canvas.innerHTML = `
      <div class="page-container" style="padding: 24px;">
        ${window.UI.Loading('Loading Luck Royale Studio...', 'Discovering turntable machines and authentic game assets')}
      </div>
    `;

    await fetchMachines();
    await Promise.all([fetchMachineData(_selectedCid), fetchAssets()]);

    drawStudio(canvas);
  }

  function drawStudio(canvas) {
    const activeMachine = _cachedMachines.find(m => m.chest_id === _selectedCid) || _cachedMachines[0] || {
      chest_id: _selectedCid,
      display_name: `Machine #${_selectedCid}`,
      enabled: true,
      coin_type: 1,
      once_price: 60,
      ten_price: 600,
      rare_item_max: 100
    };

    const headerActions = `
      <div style="display: flex; gap: 8px; align-items: center;">
        <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenCreateMachineModal()" title="Create a new Luck Royale machine">
          <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('plus', 13)} New Royale</span>
        </button>
        <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenDuplicateMachineModal(${_selectedCid})" title="Duplicate current Royale">
          <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('copy', 13)} Duplicate</span>
        </button>
        <button class="btn ${activeMachine.enabled ? 'btn-danger' : 'btn-primary'} btn-sm" onclick="window.LuckRoyale.ToggleActiveMachine(${_selectedCid}, ${!activeMachine.enabled})">
          <span style="display: inline-flex; align-items: center; gap: 5px;">
            ${window.UI.Icon(activeMachine.enabled ? 'power' : 'play', 13)}
            ${activeMachine.enabled ? 'Disable Machine' : 'Enable Machine'}
          </span>
        </button>
      </div>
    `;

    // 1. Single Page Header (No duplicate topbars!)
    const pageHeaderHtml = window.UI.PageHeader(
      'dices',
      'Luck Royale Studio',
      'Complete administrative control over Free Fire 1.39 turntable machines, authentic assets, reward pools & campaigns',
      headerActions
    );

    // 2. Compact Machine Selector Bar
    const machinePillsHtml = _cachedMachines.map(m => {
      const isSelected = m.chest_id === _selectedCid;
      const statusDot = m.enabled
        ? '<span style="width: 7px; height: 7px; border-radius: 50%; background: var(--accent-emerald); display: inline-block;"></span>'
        : '<span style="width: 7px; height: 7px; border-radius: 50%; background: var(--text-tertiary); display: inline-block;"></span>';
      return `
        <button class="btn ${isSelected ? 'btn-primary' : 'btn-secondary'} btn-sm"
                style="padding: 7px 14px; border-radius: var(--radius-sm); font-size: 12px; font-weight: ${isSelected ? '600' : '500'}; display: inline-flex; align-items: center; gap: 8px; transition: all 0.15s ease;"
                onclick="window.LuckRoyale.SelectMachine(${m.chest_id})">
          ${statusDot}
          <span>${C.escapeHtml(m.display_name)}</span>
          <span style="font-size: 10px; opacity: 0.7; padding: 1px 5px; background: rgba(0,0,0,0.25); border-radius: 3px;">#${m.chest_id}</span>
        </button>
      `;
    }).join('');

    // 3. Machine Identity Strip
    const coinLabel = activeMachine.coin_type === 2 ? 'Diamonds' : 'Gold';
    const coinIcon = activeMachine.coin_type === 2 ? 'diamond' : 'coins';
    const thumbUrl = (_cachedArtwork && _cachedArtwork.thumbnail_url) || (_cachedArtwork && _cachedArtwork.thumbnail) || `/assets/freefire/1.39/royale/UI_Lottery_Poster_G.png`;

    const identityStripHtml = `
      <div class="glass-card" style="padding: 14px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; border-left: 3px solid var(--accent-primary);">
        <div style="display: flex; align-items: center; gap: 14px;">
          <div style="width: 44px; height: 44px; border-radius: var(--radius-sm); overflow: hidden; background: rgba(0,0,0,0.4); border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <img src="${thumbUrl}" alt="Machine Poster" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.onerror=null; this.src='/assets/freefire/1.39/ui/UI_Lottery_item_bg.png';">
          </div>
          <div>
            <div style="font-size: 16px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
              ${C.escapeHtml(activeMachine.display_name)}
              <span style="font-size: 11px; font-weight: 600; padding: 2px 7px; background: var(--bg-surface-2); border: 1px solid var(--border-default); border-radius: var(--radius-sm); color: var(--text-secondary);">ID: ${activeMachine.chest_id}</span>
              ${activeMachine.enabled ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('DISABLED', 'neutral')}
            </div>
            <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 3px; display: flex; align-items: center; gap: 12px;">
              <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon(coinIcon, 12)} Currency: <strong style="color: #fff;">${coinLabel}</strong></span>
              <span>•</span>
              <span>Cost: <strong style="color: #fff;">${activeMachine.once_price}</strong> (1x) / <strong style="color: #fff;">${activeMachine.ten_price}</strong> (10x)</span>
              <span>•</span>
              <span>Pity Ceiling: <strong style="color: #fff;">${activeMachine.rare_item_max || 100}</strong></span>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 8px; align-items: center;">
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenEditMachineModal(${_selectedCid})" title="Quick edit machine parameters in focused modal">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('edit', 12)} Edit Machine</span>
          </button>
        </div>
      </div>
    `;

    // 4. Compact Internal Tabs (Integrated Workspace Navigation)
    const tabs = [
      { id: 'overview', label: 'Overview', icon: 'eye' },
      { id: 'settings', label: 'Machine Settings', icon: 'sliders' },
      { id: 'artwork', label: 'Artwork & Assets', icon: 'image' },
      { id: 'pool', label: `Prize Pool (${(_cachedPool && _cachedPool.items) ? _cachedPool.items.length : 0})`, icon: 'gift' },
      { id: 'events', label: 'Event Rewards', icon: 'calendar' },
      { id: 'pity', label: 'Pity & Vouchers', icon: 'trendingUp' },
      { id: 'preview', label: 'Client Preview', icon: 'sparkles' },
      { id: 'forge', label: 'Incubator Forge', icon: 'hammer' },
      { id: 'simulator', label: 'Simulator', icon: 'barChart' },
      { id: 'transactions', label: 'Audit Ledger', icon: 'scrollText' },
      { id: 'config', label: 'Backup & JSON', icon: 'save' }
    ];

    const tabsNavHtml = `
      <div style="display: flex; gap: 4px; border-bottom: 1px solid var(--border-default); margin-bottom: 20px; overflow-x: auto; padding-bottom: 2px;">
        ${tabs.map(t => {
          const isActive = _activeTab === t.id;
          return `
            <button class="btn ${isActive ? 'btn-primary' : 'btn-ghost'} btn-sm"
                    style="border-radius: var(--radius-sm) var(--radius-sm) 0 0; border-bottom: ${isActive ? '2px solid var(--accent-primary)' : '2px solid transparent'}; padding: 8px 14px; font-size: 12px; font-weight: ${isActive ? '600' : '500'}; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;"
                    onclick="window.LuckRoyale.SwitchStudioTab('${t.id}')">
              ${window.UI.Icon(t.icon, 13)}
              <span>${t.label}</span>
            </button>
          `;
        }).join('')}
      </div>
    `;

    // 5. Render Active Tab Body
    let tabBodyHtml = '';
    if (_activeTab === 'overview') tabBodyHtml = renderTabOverview(activeMachine);
    else if (_activeTab === 'settings') tabBodyHtml = renderTabSettings(activeMachine);
    else if (_activeTab === 'artwork') tabBodyHtml = renderTabArtwork(activeMachine);
    else if (_activeTab === 'pool') tabBodyHtml = renderTabPool(activeMachine);
    else if (_activeTab === 'events') tabBodyHtml = renderTabEvents(activeMachine);
    else if (_activeTab === 'pity') tabBodyHtml = renderTabPity(activeMachine);
    else if (_activeTab === 'preview') tabBodyHtml = renderTabPreview(activeMachine);
    else if (_activeTab === 'forge') tabBodyHtml = renderTabForge(activeMachine);
    else if (_activeTab === 'simulator') tabBodyHtml = renderTabSimulator(activeMachine);
    else if (_activeTab === 'transactions') tabBodyHtml = renderTabTransactions(activeMachine);
    else if (_activeTab === 'config') tabBodyHtml = renderTabConfig(activeMachine);

    canvas.innerHTML = `
      <div class="page-container" style="padding: 24px;">
        ${pageHeaderHtml}

        <div style="margin-bottom: 16px;">
          <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-tertiary); margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
            ${window.UI.Icon('grid', 12)} Select Royale Machine:
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
            ${machinePillsHtml}
          </div>
        </div>

        ${identityStripHtml}
        ${tabsNavHtml}

        <div id="studio-tab-content">
          ${tabBodyHtml}
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 1: OVERVIEW
  // ---------------------------------------------------------------------------

  function renderTabOverview(m) {
    const items = (_cachedPool && _cachedPool.items) || [];
    const totalWeight = items.reduce((s, it) => s + (it.weight || 0), 0);
    const superRareCount = items.filter(it => it.reward_level === 2).length;
    const rareCount = items.filter(it => it.reward_level === 1).length;
    const normalCount = items.filter(it => it.reward_level === 0).length;

    const srWeight = items.filter(it => it.reward_level === 2).reduce((s, it) => s + (it.weight || 0), 0);
    const rWeight = items.filter(it => it.reward_level === 1).reduce((s, it) => s + (it.weight || 0), 0);
    const nWeight = items.filter(it => it.reward_level === 0).reduce((s, it) => s + (it.weight || 0), 0);

    const srPct = totalWeight > 0 ? ((srWeight / totalWeight) * 100).toFixed(2) : '0.00';
    const rPct = totalWeight > 0 ? ((rWeight / totalWeight) * 100).toFixed(2) : '0.00';
    const nPct = totalWeight > 0 ? ((nWeight / totalWeight) * 100).toFixed(2) : '0.00';

    const posterUrl = (_cachedArtwork && _cachedArtwork.banner_url) || (_cachedArtwork && _cachedArtwork.banner) || '/assets/freefire/1.39/royale/UI_Lottery_Poster_G.png';

    function renderStatCard(label, value, meta, icon, variant) {
      if (window.UI && typeof window.UI.StatCard === 'function') {
        return window.UI.StatCard(label, value, meta, icon, variant);
      }
      return `
        <div class="stat-card">
          <div class="stat-label">
            <span>${C.escapeHtml(label)}</span>
            ${icon ? `<span style="opacity: 0.8; display: inline-flex; align-items: center;">${icon}</span>` : ''}
          </div>
          <div class="stat-value" style="color: var(--accent-${variant || 'cyan'});">${C.escapeHtml(value)}</div>
          ${meta ? `<div class="stat-delta"><span>${C.escapeHtml(meta)}</span></div>` : ''}
        </div>
      `;
    }

    return `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; align-items: start;">
        <div>
          <!-- 4-Card Telemetry Strip -->
          <div class="grid-4" style="margin-bottom: 20px;">
            ${renderStatCard('Total Rewards In Pool', items.length.toString(), 'Distinct prize slots', window.UI.Icon('gift', 18), 'amber')}
            ${renderStatCard('Total Pool Weight', totalWeight.toLocaleString(), 'Server-side drop sum', window.UI.Icon('barChart', 18), 'cyan')}
            ${renderStatCard('Spin Pricing (1x / 10x)', `${m.once_price} / ${m.ten_price}`, m.coin_type === 2 ? 'Diamonds' : 'Gold', window.UI.Icon(m.coin_type === 2 ? 'diamond' : 'coins', 18), 'purple')}
            ${renderStatCard('Guaranteed Pity Ceiling', `${m.rare_item_max || 100} Spins`, 'Auto-jackpot threshold', window.UI.Icon('trendingUp', 18), 'emerald')}
          </div>

          <!-- Rarity Distribution Card -->
          <div class="glass-card" style="padding: 20px; margin-bottom: 20px;">
            <h3 style="font-size: 14px; font-weight: 600; color: #fff; margin: 0 0 14px 0; display: flex; align-items: center; gap: 8px;">
              ${window.UI.Icon('pieChart', 14)} Probability & Tier Distribution
            </h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;">
              <div style="padding: 14px; background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: var(--radius-sm);">
                <div style="font-size: 11px; font-weight: 600; color: var(--accent-amber); text-transform: uppercase;">Super Rare (Tier 2)</div>
                <div style="font-size: 22px; font-weight: 700; color: #fff; margin: 4px 0;">${srPct}%</div>
                <div style="font-size: 11px; color: var(--text-tertiary);">${superRareCount} items • Weight ${srWeight.toLocaleString()}</div>
              </div>
              <div style="padding: 14px; background: rgba(6, 182, 212, 0.08); border: 1px solid rgba(6, 182, 212, 0.25); border-radius: var(--radius-sm);">
                <div style="font-size: 11px; font-weight: 600; color: var(--accent-cyan); text-transform: uppercase;">Rare (Tier 1)</div>
                <div style="font-size: 22px; font-weight: 700; color: #fff; margin: 4px 0;">${rPct}%</div>
                <div style="font-size: 11px; color: var(--text-tertiary);">${rareCount} items • Weight ${rWeight.toLocaleString()}</div>
              </div>
              <div style="padding: 14px; background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.25); border-radius: var(--radius-sm);">
                <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Normal (Tier 0)</div>
                <div style="font-size: 22px; font-weight: 700; color: #fff; margin: 4px 0;">${nPct}%</div>
                <div style="font-size: 11px; color: var(--text-tertiary);">${normalCount} items • Weight ${nWeight.toLocaleString()}</div>
              </div>
            </div>
          </div>

          <!-- Quick Action Buttons -->
          <div class="glass-card" style="padding: 18px 20px;">
            <div style="font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 12px;">Workspace Shortcuts:</div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.SwitchStudioTab('settings')">
                <span style="display: inline-flex; align-items: center; gap: 6px;">${window.UI.Icon('sliders', 12)} Edit Pricing & Settings</span>
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.SwitchStudioTab('artwork')">
                <span style="display: inline-flex; align-items: center; gap: 6px;">${window.UI.Icon('image', 12)} Artwork Slots Matrix</span>
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.SwitchStudioTab('pool')">
                <span style="display: inline-flex; align-items: center; gap: 6px;">${window.UI.Icon('gift', 12)} Manage Reward Pool</span>
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.SwitchStudioTab('events')">
                <span style="display: inline-flex; align-items: center; gap: 6px;">${window.UI.Icon('calendar', 12)} Configure Event Discounts</span>
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.SwitchStudioTab('preview')">
                <span style="display: inline-flex; align-items: center; gap: 6px;">${window.UI.Icon('sparkles', 12)} Client Turntable Preview</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Right Side: Poster Billboard -->
        <div class="glass-card" style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
          <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-tertiary);">
            Authentic Poster Graphic
          </div>
          <div style="width: 100%; border-radius: var(--radius-sm); overflow: hidden; background: rgba(0,0,0,0.5); border: 1px solid var(--border-default); aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center;">
            <img src="${posterUrl}" alt="${C.escapeHtml(m.display_name)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.onerror=null; this.src='/assets/freefire/1.39/ui/UI_Lottery_item_bg.png';">
          </div>
          <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.5;">
            Original Free Fire 1.39 client billboard texture. Served directly by the local server asset pipeline from <code>${C.escapeHtml(posterUrl)}</code>.
          </div>
          <button class="btn btn-secondary btn-sm" style="width: 100%; justify-content: center;" onclick="window.LuckRoyale.OpenArtworkDrawer(${m.chest_id}, 'banner')">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('edit', 12)} Replace Poster Artwork</span>
          </button>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 2: MACHINE SETTINGS
  // ---------------------------------------------------------------------------

  function renderTabSettings(m) {
    return `
      <div class="glass-card" style="padding: 24px; max-width: 800px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">Machine Configuration: ${C.escapeHtml(m.display_name)}</h3>
            <div style="font-size: 12px; color: var(--text-secondary);">Direct parameters governing costs, currencies, free cooldowns, and pity ceiling</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenEditMachineModal(${m.chest_id})">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('edit', 12)} Modal Editor</span>
          </button>
        </div>

        <form id="studio-machine-settings-form" onsubmit="window.LuckRoyale.SaveMachineSettingsForm(event, ${m.chest_id}); return false;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Machine Display Name</label>
              <input type="text" name="display_name" class="form-input" value="${C.escapeHtml(m.display_name)}" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Currency / Coin Type</label>
              <select name="coin_type" class="form-input" style="width: 100%;">
                <option value="1" ${m.coin_type === 1 ? 'selected' : ''}>Gold Coins (Type 1)</option>
                <option value="2" ${m.coin_type === 2 ? 'selected' : ''}>Diamonds (Type 2)</option>
                <option value="3" ${m.coin_type === 3 ? 'selected' : ''}>Gacha Vouchers (Type 3)</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Single Spin Cost (1x)</label>
              <input type="number" name="once_price" class="form-input" value="${m.once_price}" min="0" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Multi-Spin Cost (10x)</label>
              <input type="number" name="ten_price" class="form-input" value="${m.ten_price}" min="0" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Pity Ceiling (rare_item_max)</label>
              <input type="number" name="rare_item_max" class="form-input" value="${m.rare_item_max || 100}" min="1" max="1000" required style="width: 100%;">
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 3px;">Max consecutive spins before jackpot is guaranteed</div>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Turntable Animation Type</label>
              <select name="chest_type_enum" class="form-input" style="width: 100%;">
                <option value="2" ${m.chest_type_enum !== 1 ? 'selected' : ''}>Standard Turntable Wheel (Diamond / Weapon / Gold)</option>
                <option value="1" ${m.chest_type_enum === 1 ? 'selected' : ''}>Incubator Legendary Turntable (Forge Matrix)</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Daily First Spin Discount (%)</label>
              <input type="number" name="discount" class="form-input" value="${m.discount || 0}" min="0" max="100" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px;">Free Spin Cooldown (Seconds)</label>
              <input type="number" name="free_cooldown_seconds" class="form-input" value="${m.free_cooldown_seconds || 86400}" min="0" style="width: 100%;">
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="submit" class="btn btn-primary" id="btn-save-settings">
              <span style="display: inline-flex; align-items: center; gap: 6px;">${window.UI.Icon('save', 13)} Save Configuration</span>
            </button>
          </div>
        </form>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 3: ARTWORK & ASSETS
  // ---------------------------------------------------------------------------

  function renderTabArtwork(m) {
    const artwork = _cachedArtwork || {};
    const slots = [
      { key: 'banner', label: 'Main Royale Poster Banner', desc: 'Large billboard banner shown in header & overview poster', url: artwork.banner_url || artwork.banner },
      { key: 'thumbnail', label: 'Machine Thumbnail', desc: 'Compact square thumbnail used in tab navigation & card icons', url: artwork.thumbnail_url || artwork.thumbnail },
      { key: 'background', label: 'Background Texture / Canvas', desc: 'Ambient background texture rendered behind turntable machine', url: artwork.background_url || artwork.background },
      { key: 'featured', label: 'Featured Reward Showcase Artwork', desc: 'Grand prize spotlight visual asset displayed on turntable pedestal', url: artwork.featured_url || artwork.featured },
      { key: 'promo', label: 'Promotional / Event Artwork', desc: 'Secondary promotion ribbon and special event badge', url: artwork.promo_url || artwork.promo }
    ];

    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">Artwork Slots: ${C.escapeHtml(m.display_name)}</h3>
            <div style="font-size: 12px; color: var(--text-secondary);">Assign authentic Free Fire 1.39 game textures or upload custom machine graphics</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenUploadAssetModal()">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('upload', 13)} Upload New Graphic</span>
          </button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
          ${slots.map(s => {
            const hasImg = Boolean(s.url);
            const displayUrl = s.url || '/assets/freefire/1.39/ui/UI_Lottery_item_bg.png';
            return `
              <div class="glass-card" style="padding: 18px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                  <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div>
                      <div style="font-size: 13px; font-weight: 700; color: #fff;">${s.label}</div>
                      <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Slot: <code>${s.key}</code></div>
                    </div>
                    ${hasImg ? window.UI.Badge('ASSIGNED', 'emerald') : window.UI.Badge('DEFAULT', 'neutral')}
                  </div>

                  <div style="width: 100%; aspect-ratio: 16/9; border-radius: var(--radius-sm); overflow: hidden; background: rgba(0,0,0,0.5); border: 1px solid var(--border-default); display: flex; align-items: center; justify-content: center; margin-bottom: 12px;">
                    <img src="${displayUrl}" alt="${s.label}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.onerror=null; this.src='/assets/freefire/1.39/ui/UI_Lottery_item_bg.png';">
                  </div>

                  <div style="font-size: 11px; color: var(--text-secondary); word-break: break-all; margin-bottom: 14px; line-height: 1.4;">
                    <strong>Source:</strong> <code>${C.escapeHtml(s.url || 'Default asset')}</code>
                  </div>
                </div>

                <div style="display: flex; gap: 8px;">
                  <button class="btn btn-primary btn-sm" style="flex: 1; justify-content: center;" onclick="window.LuckRoyale.OpenArtworkDrawer(${m.chest_id}, '${s.key}')">
                    <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('image', 12)} Browse & Assign</span>
                  </button>
                  <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenUploadAssetModal('${s.key}')" title="Upload directly to this slot">
                    ${window.UI.Icon('upload', 12)}
                  </button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 4: PRIZE POOL
  // ---------------------------------------------------------------------------

  function renderTabPool(m) {
    const rawItems = (_cachedPool && _cachedPool.items) || [];
    const totalWeight = rawItems.reduce((s, it) => s + (it.weight || 0), 0);

    // Apply client-side search & category filter
    let items = rawItems;
    if (_poolSearchQuery) {
      const q = _poolSearchQuery.toLowerCase();
      items = items.filter(it =>
        String(it.item_id).includes(q) ||
        (it.name && it.name.toLowerCase().includes(q)) ||
        (it.category && it.category.toLowerCase().includes(q))
      );
    }
    if (_poolCategoryFilter && _poolCategoryFilter !== 'all') {
      items = items.filter(it => (it.category || '').toLowerCase() === _poolCategoryFilter.toLowerCase());
    }

    // Generate table rows
    const rows = items.map((it, idx) => {
      const prob = totalWeight > 0 ? ((it.weight / totalWeight) * 100).toFixed(2) : '0.00';
      const rarityBadge = C.rarityBadge(it.reward_level);
      const isFirst = idx === 0;
      const isLast = idx === items.length - 1;

      // Authentic extracted image resolution
      const imgHtml = C.renderItemImage(it.image_url, it.name, 34, it.item_id);

      const duplicateText = it.repeated_item_id
        ? `<span style="font-size: 11px; color: var(--text-secondary); display: inline-flex; align-items: center; gap: 4px;">
             ${window.UI.Icon('repeat', 10)} <strong>${it.repeated_item_num || 1}x</strong> Item #${it.repeated_item_id}
           </span>`
        : `<span style="color: var(--text-tertiary); font-size: 11px;">—</span>`;

      const orderBtns = `
        <div style="display: flex; gap: 4px; align-items: center;">
          <button class="btn btn-ghost btn-sm" style="padding: 2px 6px;" onclick="window.LuckRoyale.ReorderPoolItem(${m.chest_id}, ${it.item_id}, 'up')" ${isFirst ? 'disabled' : ''} title="Move Up">
            ${window.UI.Icon('arrowUp', 11)}
          </button>
          <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary); min-width: 16px; text-align: center;">${idx + 1}</span>
          <button class="btn btn-ghost btn-sm" style="padding: 2px 6px;" onclick="window.LuckRoyale.ReorderPoolItem(${m.chest_id}, ${it.item_id}, 'down')" ${isLast ? 'disabled' : ''} title="Move Down">
            ${window.UI.Icon('arrowDown', 11)}
          </button>
        </div>
      `;

      const actionBtns = `
        <div style="display: flex; gap: 6px; align-items: center;">
          <button class="btn btn-secondary btn-sm" style="padding: 4px 8px;" onclick="window.LuckRoyale.OpenEditRewardModal(${m.chest_id}, ${it.item_id})" title="Edit Reward">
            ${window.UI.Icon('edit', 12)}
          </button>
          <button class="btn btn-ghost btn-sm" style="padding: 4px 8px; color: var(--accent-rose);" onclick="window.LuckRoyale.RemovePoolItem(${m.chest_id}, ${it.item_id})" title="Delete Reward">
            ${window.UI.Icon('trash', 12)}
          </button>
        </div>
      `;

      return [
        `<div style="display: flex; align-items: center; gap: 10px;">
           ${imgHtml}
           <div>
             <div style="font-weight: 600; color: #fff; font-size: 12px;">${C.escapeHtml(it.name || `Item #${it.item_id}`)}</div>
             <div style="font-size: 10px; color: var(--text-tertiary);">ID: <code>${it.item_id}</code></div>
           </div>
         </div>`,
        `<span style="font-size: 11px; color: var(--text-secondary);">${C.escapeHtml(it.category || 'General')}</span>`,
        rarityBadge,
        `<div>
           <strong style="color: #fff; font-size: 12px;">${it.weight}</strong>
           <span style="font-size: 10px; color: var(--accent-cyan); margin-left: 4px;">(${prob}%)</span>
         </div>`,
        `<span style="font-size: 12px; font-weight: 600; color: #fff;">${it.item_num || 1}x</span>`,
        duplicateText,
        orderBtns,
        actionBtns
      ];
    });

    const categoryOptions = ['all', 'Avatar', 'Clothes', 'Bundle', 'GunSkin', 'Consumable', 'BonusCard', 'Voucher', 'General'];

    return `
      <div>
        <!-- Pool Header & Controls Strip -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">
              Prize Pool: ${C.escapeHtml(m.display_name)} (${rawItems.length} Total Rewards)
            </h3>
            <div style="font-size: 12px; color: var(--text-secondary);">
              Server-authoritative drop chances • Total Weight: <strong style="color: #fff;">${totalWeight.toLocaleString()}</strong>
            </div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <button class="btn btn-primary btn-sm" onclick="window.LuckRoyale.OpenAddRewardModal(${m.chest_id})">
              <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('plus', 13)} Add Reward</span>
            </button>
          </div>
        </div>

        <!-- Filter & Search Toolbar -->
        <div class="glass-card" style="padding: 12px 16px; margin-bottom: 16px; display: flex; gap: 14px; align-items: center; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 220px; display: flex; align-items: center; gap: 8px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: 0 10px;">
            ${window.UI.Icon('search', 13)}
            <input type="text" placeholder="Filter by item ID, name, or category..." value="${C.escapeHtml(_poolSearchQuery)}"
                   oninput="window.LuckRoyale.OnPoolSearch(this.value)"
                   style="width: 100%; background: transparent; border: none; outline: none; padding: 7px 0; font-size: 12px; color: #fff;">
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600;">Category:</span>
            <select class="form-input" style="padding: 6px 10px; font-size: 12px;" onchange="window.LuckRoyale.OnPoolCategoryFilter(this.value)">
              ${categoryOptions.map(cat => `<option value="${cat}" ${_poolCategoryFilter === cat ? 'selected' : ''}>${cat === 'all' ? 'All Categories' : cat}</option>`).join('')}
            </select>
          </div>
        </div>

        <!-- Table Container -->
        <div style="max-height: 520px; overflow-y: auto; border: 1px solid var(--border-default); border-radius: var(--radius-md);">
          ${window.UI.Table(
            ['Reward Item', 'Category', 'Rarity', 'Weight / Prob', 'Qty', 'Duplicate Debris', 'Order', 'Actions'],
            rows.map(r => `<tr>${r.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join(''),
            'No matching rewards in this prize pool.'
          )}
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 5: EVENT REWARDS
  // ---------------------------------------------------------------------------

  function renderTabEvents(m) {
    const ev = _cachedEvent || {};
    const isAct = Boolean(ev.active);
    const title = ev.title || 'No active event scheduled';
    const disc = ev.discount_percent || 0;
    const rateUp = ev.rate_up_multiplier || 1.0;
    const rewards = ev.rewards || [];

    return `
      <div style="max-width: 860px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">Event Campaigns: ${C.escapeHtml(m.display_name)}</h3>
            <div style="font-size: 12px; color: var(--text-secondary);">Time-limited campaigns, spin discounts, rate-up multipliers, and milestone rewards</div>
          </div>
          <button class="btn btn-primary btn-sm" onclick="window.LuckRoyale.OpenEventModal(${m.chest_id})">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('edit', 12)} Edit Event Campaign</span>
          </button>
        </div>

        <!-- Campaign Status Card -->
        <div class="glass-card" style="padding: 20px; margin-bottom: 20px; border-left: 3px solid ${isAct ? 'var(--accent-emerald)' : 'var(--text-tertiary)'};">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 14px;">
            <div>
              <div style="font-size: 16px; font-weight: 700; color: #fff;">${C.escapeHtml(title)}</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 3px;">
                Scheduled for Machine #${m.chest_id} (${C.escapeHtml(m.display_name)})
              </div>
            </div>
            ${isAct ? window.UI.Badge('ACTIVE EVENT', 'emerald') : window.UI.Badge('INACTIVE', 'neutral')}
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-top: 14px; border-top: 1px solid var(--border-subtle); padding-top: 14px;">
            <div>
              <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase;">Spin Discount</div>
              <div style="font-size: 18px; font-weight: 700; color: var(--accent-amber);">${disc}% Off</div>
            </div>
            <div>
              <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase;">Rate-up Multiplier</div>
              <div style="font-size: 18px; font-weight: 700; color: var(--accent-cyan);">${rateUp}x Jackpot Drop</div>
            </div>
            <div>
              <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase;">Start Time</div>
              <div style="font-size: 12px; color: #fff; margin-top: 4px;">${C.formatTimestamp(ev.start_time)}</div>
            </div>
            <div>
              <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase;">End Time</div>
              <div style="font-size: 12px; color: #fff; margin-top: 4px;">${C.formatTimestamp(ev.end_time)}</div>
            </div>
          </div>
        </div>

        <!-- Event Milestone Rewards -->
        <div class="glass-card" style="padding: 20px;">
          <h4 style="font-size: 13px; font-weight: 600; color: #fff; margin: 0 0 12px 0; display: flex; align-items: center; gap: 6px;">
            ${window.UI.Icon('gift', 13)} Event Milestone Rewards (${rewards.length})
          </h4>
          ${rewards.length === 0
            ? `<div style="text-align: center; padding: 24px; color: var(--text-tertiary); font-size: 12px;">No milestone rewards configured for this campaign. Click 'Edit Event Campaign' to add claimable milestone items.</div>`
            : `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px;">
                ${rewards.map(r => `
                  <div style="padding: 10px 14px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm); display: flex; align-items: center; gap: 10px;">
                    ${C.renderItemImage(r.icon_url, r.name, 32, r.item_id)}
                    <div>
                      <div style="font-size: 12px; font-weight: 600; color: #fff;">${C.escapeHtml(r.name || `Item #${r.item_id}`)}</div>
                      <div style="font-size: 11px; color: var(--text-tertiary);">Unlock at: <strong>${r.spins_required || 1} spins</strong> • Qty: ${r.count || 1}</div>
                    </div>
                  </div>
                `).join('')}
               </div>`
          }
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 6: PITY & VOUCHERS
  // ---------------------------------------------------------------------------

  function renderTabPity(m) {
    const vouchers = [
      { id: 110100010, name: 'Gold Royale Voucher', desc: 'Permits 1 free spin on Gold Royale', icon: 'Icon_voucher.png', targetCid: 5 },
      { id: 110100008, name: 'Diamond Royale Voucher', desc: 'Permits 1 free spin on Diamond Royale', icon: 'Icon_voucher.png', targetCid: 3 },
      { id: 110100009, name: 'Weapon Royale Voucher', desc: 'Permits 1 free spin on Weapon Royale', icon: 'Icon_voucher.png', targetCid: 4 },
      { id: 110100018, name: 'Incubator Voucher', desc: 'Permits 1 free spin on Incubator', icon: 'Icon_voucher.png', targetCid: 6 }
    ];

    const currentMeter = 42; // Fallback or active context meter
    const maxMeter = m.rare_item_max || 100;
    const meterPct = Math.min(100, (currentMeter / maxMeter) * 100);

    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;">
        <!-- Left: Pity Threshold & Lucky Meter -->
        <div class="glass-card" style="padding: 20px;">
          <h3 style="font-size: 14px; font-weight: 700; color: #fff; margin: 0 0 14px 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('trendingUp', 14)} Lucky Meter & Guaranteed Pity
          </h3>
          <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 16px;">
            Every spin without a jackpot increments the lucky meter. When the meter reaches <code>${maxMeter}</code>, the server guarantees a Super Rare drop.
          </div>

          <div style="padding: 16px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm); margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px;">
              <span style="color: var(--text-tertiary);">Active Player Lucky Progression:</span>
              <span style="color: #fff; font-weight: 700;">${currentMeter} / ${maxMeter} (${meterPct.toFixed(0)}%)</span>
            </div>
            <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
              <div style="width: ${meterPct}%; height: 100%; background: var(--accent-primary); border-radius: 4px; transition: width 0.3s ease;"></div>
            </div>
          </div>

          <form onsubmit="window.LuckRoyale.AdjustLuckyMeter(event, ${m.chest_id}); return false;" style="display: flex; gap: 10px; align-items: flex-end;">
            <div style="flex: 1;">
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Set Lucky Meter Value</label>
              <input type="number" name="meter_value" class="form-input" value="${currentMeter}" min="0" max="${maxMeter}" required style="width: 100%;">
            </div>
            <button type="submit" class="btn btn-secondary btn-sm" style="padding: 8px 14px;">
              <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('save', 12)} Update Meter</span>
            </button>
          </form>
        </div>

        <!-- Right: Vouchers & Currency Grants -->
        <div class="glass-card" style="padding: 20px;">
          <h3 style="font-size: 14px; font-weight: 700; color: #fff; margin: 0 0 14px 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('ticket', 14)} Canonical Gacha Vouchers
          </h3>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${vouchers.map(v => {
              const isMatch = v.targetCid === m.chest_id;
              return `
                <div style="padding: 12px 14px; background: rgba(0,0,0,0.3); border: 1px solid ${isMatch ? 'var(--accent-primary)' : 'var(--border-default)'}; border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center;">
                  <div style="display: flex; align-items: center; gap: 10px;">
                    ${C.renderItemImage(`/assets/freefire/1.39/items/${v.id}.png`, v.name, 32, v.id)}
                    <div>
                      <div style="font-size: 12px; font-weight: 600; color: #fff;">${v.name}</div>
                      <div style="font-size: 11px; color: var(--text-tertiary);">Item ID: <code>${v.id}</code></div>
                    </div>
                  </div>
                  <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.GrantVoucher(${v.id}, 10)" title="Grant 10 vouchers to active player context">
                    <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('plus', 11)} +10</span>
                  </button>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 7: CLIENT TURNTABLE PREVIEW
  // ---------------------------------------------------------------------------

  function renderTabPreview(m) {
    const posterUrl = (_cachedArtwork && _cachedArtwork.banner_url) || (_cachedArtwork && _cachedArtwork.banner) || '/assets/freefire/1.39/royale/UI_Lottery_Poster_G.png';
    const bgUrl = (_cachedArtwork && _cachedArtwork.background_url) || (_cachedArtwork && _cachedArtwork.background) || '/assets/freefire/1.39/royale/UI_Lottery_bg01.png';
    const coinIcon = m.coin_type === 2 ? 'diamond' : 'coins';

    return `
      <div class="glass-card" style="padding: 24px; position: relative; overflow: hidden; border-radius: var(--radius-md); background: url('${bgUrl}') center/cover no-repeat, rgba(15, 23, 42, 0.95); min-height: 520px; display: flex; flex-direction: column; justify-content: space-between;">
        <!-- Ambient Glass Overlay -->
        <div style="position: absolute; inset: 0; background: linear-gradient(180deg, rgba(15,23,42,0.85) 0%, rgba(15,23,42,0.65) 50%, rgba(15,23,42,0.92) 100%); z-index: 1;"></div>

        <!-- Top Header Inside Turntable -->
        <div style="position: relative; z-index: 2; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 18px; font-weight: 700; color: #fff; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">
              ${C.escapeHtml(m.display_name)}
            </div>
            ${m.enabled ? window.UI.Badge('ONLINE', 'emerald') : window.UI.Badge('OFFLINE', 'rose')}
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <div style="padding: 6px 12px; background: rgba(0,0,0,0.6); border: 1px solid rgba(255,255,255,0.15); border-radius: var(--radius-sm); font-size: 12px; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 6px;">
              ${window.UI.Icon(coinIcon, 13)} Cost: ${m.once_price} / ${m.ten_price}
            </div>
          </div>
        </div>

        <!-- Center: Poster Display -->
        <div style="position: relative; z-index: 2; display: flex; justify-content: center; align-items: center; padding: 20px 0;">
          <div style="width: 380px; aspect-ratio: 16/9; border-radius: var(--radius-md); overflow: hidden; box-shadow: 0 12px 32px rgba(0,0,0,0.7); border: 2px solid rgba(255,255,255,0.15); background: rgba(0,0,0,0.4);">
            <img src="${posterUrl}" alt="Turntable Center" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.onerror=null; this.src='/assets/freefire/1.39/ui/UI_Lottery_item_bg.png';">
          </div>
        </div>

        <!-- Bottom Controls Inside Turntable -->
        <div style="position: relative; z-index: 2; display: flex; justify-content: center; gap: 16px;">
          <button class="btn btn-secondary" style="padding: 10px 24px; font-size: 13px; font-weight: 700; background: rgba(0,0,0,0.7); border: 1px solid rgba(255,255,255,0.2);" onclick="window.LuckRoyale.ExecuteTestSpin(${m.chest_id}, 1)">
            <span style="display: inline-flex; align-items: center; gap: 6px;">
              ${window.UI.Icon('play', 13)} Spin 1x (${m.once_price} ${m.coin_type === 2 ? 'Diamonds' : 'Gold'})
            </span>
          </button>
          <button class="btn btn-primary" style="padding: 10px 28px; font-size: 13px; font-weight: 700;" onclick="window.LuckRoyale.ExecuteTestSpin(${m.chest_id}, 2)">
            <span style="display: inline-flex; align-items: center; gap: 6px;">
              ${window.UI.Icon('sparkles', 14)} Spin 10x (${m.ten_price} ${m.coin_type === 2 ? 'Diamonds' : 'Gold'})
            </span>
          </button>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 8: INCUBATOR FORGE
  // ---------------------------------------------------------------------------

  function renderTabForge(m) {
    return `
      <div class="glass-card" style="padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">Incubator Special Exchange Forge</h3>
            <div style="font-size: 12px; color: var(--text-secondary);">Synthesize YinYang & Joker grand bundles using Evolution Stones & Blueprints</div>
          </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          <div style="padding: 16px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm);">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
              ${C.renderItemImage('/assets/freefire/1.39/items/710000410.png', 'YinYang Bundle (Male)', 40, 710000410)}
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #fff;">Golden Shade (Male)</div>
                <div style="font-size: 11px; color: var(--text-tertiary);">YinYang Tab #1 • Level 2</div>
              </div>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 12px;">
              Requires: <strong>3x Evolution Stone</strong> (808000001) + <strong>7x Blueprint: YinYang</strong> (808000003)
            </div>
            <button class="btn btn-secondary btn-sm" style="width: 100%; justify-content: center;" onclick="window.LuckRoyale.TestCraftRecipe(1, 710000410)">
              ${window.UI.Icon('hammer', 12)} Test Craft (UID Context)
            </button>
          </div>

          <div style="padding: 16px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm);">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
              ${C.renderItemImage('/assets/freefire/1.39/items/710000414.png', 'Joker Bundle (Male)', 40, 710000414)}
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #fff;">Mischief Clown (Male)</div>
                <div style="font-size: 11px; color: var(--text-tertiary);">Joker Tab #2 • Level 2</div>
              </div>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 12px;">
              Requires: <strong>3x Evolution Stone</strong> (808000002) + <strong>7x Blueprint: Joker</strong> (808000003)
            </div>
            <button class="btn btn-secondary btn-sm" style="width: 100%; justify-content: center;" onclick="window.LuckRoyale.TestCraftRecipe(2, 710000414)">
              ${window.UI.Icon('hammer', 12)} Test Craft (UID Context)
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 9: SIMULATOR
  // ---------------------------------------------------------------------------

  function renderTabSimulator(m) {
    return `
      <div class="glass-card" style="padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">Monte Carlo Probability Simulator</h3>
            <div style="font-size: 12px; color: var(--text-secondary);">Run batch randomized roll simulations to verify theoretical vs empirical drop rates</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 20px; flex-wrap: wrap;">
          <button class="btn btn-primary btn-sm" onclick="window.LuckRoyale.RunSimulation(${m.chest_id}, 500)">Simulate 500 Spins</button>
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.RunSimulation(${m.chest_id}, 1000)">Simulate 1,000 Spins</button>
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.RunSimulation(${m.chest_id}, 5000)">Simulate 5,000 Spins</button>
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.RunSimulation(${m.chest_id}, 10000)">Simulate 10,000 Spins</button>
        </div>
        <div id="simulation-results-container" style="padding: 16px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm); color: var(--text-tertiary); font-size: 12px;">
          Select a sample size above to execute automated Monte Carlo distribution verification.
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 10: TRANSACTIONS
  // ---------------------------------------------------------------------------

  function renderTabTransactions(m) {
    return `
      <div class="glass-card" style="padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">Spin Audit Ledger: ${C.escapeHtml(m.display_name)}</h3>
            <div style="font-size: 12px; color: var(--text-secondary);">Chronological record of spins executed on Machine #${m.chest_id}</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.RefreshTransactions(${m.chest_id})">
            ${window.UI.Icon('refreshCw', 12)} Refresh
          </button>
        </div>
        <div id="transactions-ledger-container" style="max-height: 480px; overflow-y: auto;">
          <div style="text-align: center; padding: 32px; color: var(--text-tertiary); font-size: 12px;">
            Loading audit transactions for Machine #${m.chest_id}...
          </div>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // TAB 11: CONFIG & BACKUP
  // ---------------------------------------------------------------------------

  function renderTabConfig(m) {
    const rawDump = JSON.stringify({
      chest_id: m.chest_id,
      machine: m,
      artwork: _cachedArtwork,
      pool_items: (_cachedPool && _cachedPool.items) || [],
      event: _cachedEvent
    }, null, 2);

    return `
      <div class="glass-card" style="padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 4px 0;">Configuration Backup & Raw State</h3>
            <div style="font-size: 12px; color: var(--text-secondary);">Export raw JSON configuration for Machine #${m.chest_id}</div>
          </div>
          <button class="btn btn-primary btn-sm" onclick="window.LuckRoyale.DownloadConfigJson(${m.chest_id})">
            <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('download', 12)} Export JSON</span>
          </button>
        </div>
        <textarea readonly class="form-input" style="width: 100%; height: 380px; font-family: monospace; font-size: 11px; line-height: 1.4; padding: 12px; background: rgba(0,0,0,0.5); border: 1px solid var(--border-default);">${C.escapeHtml(rawDump)}</textarea>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // MODALS & DRAWERS (MANDATORY REQUIREMENT)
  // ---------------------------------------------------------------------------

  // 1. Edit Machine Modal
  function openEditMachineModal(cid) {
    const m = _cachedMachines.find(x => x.chest_id === cid) || {};
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 560px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('sliders', 16)} Edit Machine: #${cid}
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">
            &times;
          </button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitEditMachine(event, ${cid}); return false;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px;">
            <div style="grid-column: span 2;">
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Display Name</label>
              <input type="text" name="display_name" class="form-input" value="${C.escapeHtml(m.display_name || '')}" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Currency Type</label>
              <select name="coin_type" class="form-input" style="width: 100%;">
                <option value="1" ${m.coin_type === 1 ? 'selected' : ''}>Gold Coins (Type 1)</option>
                <option value="2" ${m.coin_type === 2 ? 'selected' : ''}>Diamonds (Type 2)</option>
                <option value="3" ${m.coin_type === 3 ? 'selected' : ''}>Gacha Vouchers (Type 3)</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Pity Threshold (Spins)</label>
              <input type="number" name="rare_item_max" class="form-input" value="${m.rare_item_max || 100}" min="1" max="1000" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">1x Spin Cost</label>
              <input type="number" name="once_price" class="form-input" value="${m.once_price || 60}" min="0" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">10x Spin Cost</label>
              <input type="number" name="ten_price" class="form-input" value="${m.ten_price || 600}" min="0" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Turntable Animation</label>
              <select name="chest_type_enum" class="form-input" style="width: 100%;">
                <option value="2" ${m.chest_type_enum !== 1 ? 'selected' : ''}>Standard Wheel</option>
                <option value="1" ${m.chest_type_enum === 1 ? 'selected' : ''}>Incubator Matrix</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Daily Discount (%)</label>
              <input type="number" name="discount" class="form-input" value="${m.discount || 0}" min="0" max="100" style="width: 100%;">
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-machine">
              <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('save', 12)} Save Machine</span>
            </button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // 2. Add Reward Modal
  function openAddRewardModal(cid) {
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 580px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('plus', 16)} Add New Reward: Machine #${cid}
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">
            &times;
          </button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitAddReward(event, ${cid}); return false;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
            <div style="grid-column: span 2;">
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Item ID</label>
              <div style="display: flex; gap: 8px;">
                <input type="number" id="add-reward-item-id" name="item_id" class="form-input" placeholder="e.g. 710000400 or 800000304" required style="flex: 1;" oninput="window.LuckRoyale.OnRewardIdInput(this.value)">
                <button type="button" class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.LookupRewardItem()">
                  ${window.UI.Icon('search', 12)} Lookup
                </button>
              </div>
              <div id="add-reward-preview-container" style="margin-top: 8px; font-size: 11px; color: var(--text-secondary); display: flex; align-items: center; gap: 8px;">
                <span style="color: var(--text-tertiary);">Enter an item ID to preview authentic game art & metadata</span>
              </div>
            </div>

            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Rarity Tier</label>
              <select name="reward_level" class="form-input" style="width: 100%;">
                <option value="2">Super Rare (Tier 2)</option>
                <option value="1">Rare (Tier 1)</option>
                <option value="0" selected>Normal (Tier 0)</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Drop Weight</label>
              <input type="number" name="weight" class="form-input" value="100" min="1" max="100000" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Quantity (item_num)</label>
              <input type="number" name="item_num" class="form-input" value="1" min="1" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Drop Rate Multiplier</label>
              <input type="number" name="drop_up_ratio" class="form-input" value="1.0" step="0.1" min="0.1" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Duplicate Debris Item ID</label>
              <input type="number" name="repeated_item_id" class="form-input" placeholder="e.g. 110200001 (FF Token)" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Duplicate Debris Quantity</label>
              <input type="number" name="repeated_item_num" class="form-input" value="2" min="1" style="width: 100%;">
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-add-reward">
              <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('plus', 12)} Add to Pool</span>
            </button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // 3. Edit Reward Modal
  function openEditRewardModal(cid, itemId) {
    const rawItems = (_cachedPool && _cachedPool.items) || [];
    const it = rawItems.find(x => x.item_id === itemId) || { item_id: itemId, weight: 100, reward_level: 0, item_num: 1 };
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 580px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('edit', 16)} Edit Reward: ${C.escapeHtml(it.name || `Item #${itemId}`)}
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">
            &times;
          </button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitEditReward(event, ${cid}, ${itemId}); return false;">
          <div style="display: flex; align-items: center; gap: 14px; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm); margin-bottom: 16px;">
            ${C.renderItemImage(it.image_url, it.name, 44, itemId)}
            <div>
              <div style="font-size: 13px; font-weight: 700; color: #fff;">${C.escapeHtml(it.name || `Item #${itemId}`)}</div>
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Item ID: <code>${itemId}</code> • Category: ${C.escapeHtml(it.category || 'General')}</div>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Rarity Tier</label>
              <select name="reward_level" class="form-input" style="width: 100%;">
                <option value="2" ${it.reward_level === 2 ? 'selected' : ''}>Super Rare (Tier 2)</option>
                <option value="1" ${it.reward_level === 1 ? 'selected' : ''}>Rare (Tier 1)</option>
                <option value="0" ${it.reward_level === 0 ? 'selected' : ''}>Normal (Tier 0)</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Drop Weight</label>
              <input type="number" name="weight" class="form-input" value="${it.weight || 100}" min="1" max="100000" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Quantity (item_num)</label>
              <input type="number" name="item_num" class="form-input" value="${it.item_num || 1}" min="1" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Drop Rate Multiplier</label>
              <input type="number" name="drop_up_ratio" class="form-input" value="${it.drop_up_ratio || 1.0}" step="0.1" min="0.1" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Duplicate Item ID</label>
              <input type="number" name="repeated_item_id" class="form-input" value="${it.repeated_item_id || ''}" placeholder="Debris ID" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Duplicate Quantity</label>
              <input type="number" name="repeated_item_num" class="form-input" value="${it.repeated_item_num || 2}" min="1" style="width: 100%;">
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenRewardImageMappingModal(${cid}, ${itemId})">
              <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('image', 12)} Change Artwork</span>
            </button>
            <div style="display: flex; gap: 10px;">
              <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
              <button type="submit" class="btn btn-primary" id="btn-submit-edit-reward">
                <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('save', 12)} Update Reward</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // 4. Artwork Assignment Drawer
  function openArtworkDrawer(cid, slotKey) {
    closeActiveModal();
    _drawerSlotKey = slotKey;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.65); backdrop-filter: blur(4px); z-index: 9999; display: flex; justify-content: flex-end;';

    const categories = ['all', 'Royale Machine Artwork', 'Authentic Game Items', 'Character & Debris Assets', 'UI & Turntable Elements', 'Uploads'];

    overlay.innerHTML = `
      <div class="glass-card drawer" style="width: 480px; height: 100%; border-radius: 0; border-left: 1px solid var(--border-default); padding: 24px; box-shadow: -10px 0 30px rgba(0,0,0,0.7); display: flex; flex-direction: column; justify-content: space-between; overflow-y: auto;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
            <div>
              <h3 style="font-size: 15px; font-weight: 700; color: #fff; margin: 0 0 2px 0;">Artwork Assignment Drawer</h3>
              <div style="font-size: 11px; color: var(--text-tertiary);">Slot: <code>${slotKey}</code> • Machine #${cid}</div>
            </div>
            <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">&times;</button>
          </div>

          <!-- Search & Filter Toolbar -->
          <div style="margin-bottom: 14px; display: flex; gap: 8px;">
            <input type="text" id="drawer-asset-search" placeholder="Search assets by filename..." class="form-input" style="flex: 1; font-size: 12px;" oninput="window.LuckRoyale.FilterDrawerAssets(this.value)">
            <select id="drawer-asset-cat" class="form-input" style="font-size: 12px;" onchange="window.LuckRoyale.FilterDrawerCategory(this.value)">
              ${categories.map(c => `<option value="${c}">${c === 'all' ? 'All Assets' : c}</option>`).join('')}
            </select>
          </div>

          <!-- Asset Grid -->
          <div id="drawer-assets-container" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; max-height: calc(100vh - 220px); overflow-y: auto; padding-right: 4px;">
            ${renderDrawerAssetGrid(_cachedAssets, slotKey, cid)}
          </div>
        </div>

        <div style="border-top: 1px solid var(--border-subtle); padding-top: 14px; display: flex; justify-content: space-between; align-items: center;">
          <button class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.OpenUploadAssetModal('${slotKey}')">
            ${window.UI.Icon('upload', 12)} Upload New Image
          </button>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  function renderDrawerAssetGrid(assets, slotKey, cid) {
    if (!assets || assets.length === 0) {
      return `<div style="grid-column: span 2; text-align: center; padding: 24px; color: var(--text-tertiary); font-size: 12px;">No matching assets found.</div>`;
    }
    return assets.slice(0, 100).map(a => `
      <div style="padding: 8px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm); cursor: pointer; transition: all 0.15s ease;"
           onclick="window.LuckRoyale.AssignSlotAsset(${cid}, '${slotKey}', '${a.url}')"
           title="Click to assign ${a.filename}">
        <div style="width: 100%; aspect-ratio: 16/9; background: rgba(0,0,0,0.5); border-radius: 4px; overflow: hidden; margin-bottom: 6px; display: flex; align-items: center; justify-content: center;">
          <img src="${a.url}" alt="${a.filename}" style="width: 100%; height: 100%; object-fit: contain;" onerror="this.onerror=null; this.src='/assets/freefire/1.39/ui/UI_Lottery_item_bg.png';">
        </div>
        <div style="font-size: 11px; font-weight: 600; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${C.escapeHtml(a.filename)}</div>
        <div style="font-size: 10px; color: var(--text-tertiary);">${C.escapeHtml(a.category || 'Asset')}</div>
      </div>
    `).join('');
  }

  // 5. Event Editor Modal
  function openEventModal(cid) {
    const ev = _cachedEvent || {};
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 560px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('calendar', 16)} Edit Event Campaign: Machine #${cid}
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">&times;</button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitEventForm(event, ${cid}); return false;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
            <div style="grid-column: span 2;">
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Campaign Title</label>
              <input type="text" name="title" class="form-input" value="${C.escapeHtml(ev.title || 'Special Royale Celebration')}" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Discount Percentage (%)</label>
              <input type="number" name="discount_percent" class="form-input" value="${ev.discount_percent || 0}" min="0" max="100" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Jackpot Rate-up Multiplier</label>
              <input type="number" name="rate_up_multiplier" class="form-input" value="${ev.rate_up_multiplier || 1.0}" step="0.1" min="1.0" max="10.0" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Start Timestamp</label>
              <input type="number" name="start_time" class="form-input" value="${ev.start_time || Math.floor(Date.now() / 1000)}" style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">End Timestamp</label>
              <input type="number" name="end_time" class="form-input" value="${ev.end_time || Math.floor(Date.now() / 1000) + 604800}" style="width: 100%;">
            </div>
            <div style="grid-column: span 2;">
              <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 12px; color: #fff;">
                <input type="checkbox" name="active" value="1" ${ev.active ? 'checked' : ''}>
                <span>Activate this event campaign on Machine #${cid}</span>
              </label>
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-event">
              <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon('save', 12)} Save Event</span>
            </button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // 6. Reward Image Mapping Modal
  function openRewardImageMappingModal(cid, itemId) {
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 520px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('image', 16)} Custom Artwork Mapping: Item #${itemId}
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">&times;</button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitRewardImageMapping(event, ${cid}, ${itemId}); return false;">
          <div style="margin-bottom: 16px;">
            <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Custom Image URL or Asset Name</label>
            <input type="text" name="image_url" id="map-img-url" class="form-input" placeholder="/assets/freefire/1.39/items/... or filename.png" required style="width: 100%;" oninput="window.LuckRoyale.OnCustomImageInput(this.value)">
          </div>

          <div style="display: flex; align-items: center; gap: 14px; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-default); border-radius: var(--radius-sm); margin-bottom: 16px;">
            <div id="mapping-preview-box" style="width: 48px; height: 48px; border-radius: 6px; overflow: hidden; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center;">
              ${C.renderItemImage('', '', 48, itemId)}
            </div>
            <div>
              <div style="font-size: 12px; font-weight: 600; color: #fff;">Live Preview</div>
              <div style="font-size: 11px; color: var(--text-tertiary);">Resolves directly from local server asset catalog</div>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="window.LuckRoyale.RestoreDefaultImage(${cid}, ${itemId})" style="color: var(--accent-rose);">
              Restore Default
            </button>
            <div style="display: flex; gap: 10px;">
              <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
              <button type="submit" class="btn btn-primary" id="btn-submit-map-img">Save Mapping</button>
            </div>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // 7. Create Machine Modal
  function openCreateMachineModal() {
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 520px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('plus', 16)} Create New Luck Royale Machine
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">&times;</button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitCreateMachine(event); return false;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Chest ID (Unique)</label>
              <input type="number" name="chest_id" class="form-input" placeholder="e.g. 7 or 10" min="1" max="999999" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Display Name</label>
              <input type="text" name="display_name" class="form-input" placeholder="e.g. Festive Royale" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Coin Type</label>
              <select name="coin_type" class="form-input" style="width: 100%;">
                <option value="1">Gold Coins (1)</option>
                <option value="2" selected>Diamonds (2)</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Pity Limit</label>
              <input type="number" name="rare_item_max" class="form-input" value="100" min="1" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">1x Spin Cost</label>
              <input type="number" name="once_price" class="form-input" value="60" min="0" required style="width: 100%;">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">10x Spin Cost</label>
              <input type="number" name="ten_price" class="form-input" value="600" min="0" required style="width: 100%;">
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-create-machine">Create Royale</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // 8. Duplicate Machine Modal
  function openDuplicateMachineModal(srcCid) {
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 500px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('copy', 16)} Duplicate Machine #${srcCid}
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">&times;</button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitDuplicateMachine(event, ${srcCid}); return false;">
          <div style="margin-bottom: 14px;">
            <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">New Chest ID (Unique)</label>
            <input type="number" name="new_chest_id" class="form-input" placeholder="e.g. 7 or 12" min="1" max="999999" required style="width: 100%;">
          </div>
          <div style="margin-bottom: 16px;">
            <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">New Display Name</label>
            <input type="text" name="new_chest_name" class="form-input" placeholder="e.g. Copy of Diamond Royale" required style="width: 100%;">
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-duplicate">Duplicate Royale</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // 9. Upload Asset Modal
  function openUploadAssetModal(slotKey) {
    closeActiveModal();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay luck-royale-modal-overlay';
    overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;';
    overlay.innerHTML = `
      <div class="glass-card modal" style="width: 100%; max-width: 500px; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px;">
          <h3 class="modal-title" style="font-size: 16px; font-weight: 700; color: #fff; margin: 0; display: flex; align-items: center; gap: 8px;">
            ${window.UI.Icon('upload', 16)} Upload Image Asset
          </h3>
          <button class="btn btn-ghost btn-sm" onclick="window.LuckRoyale.CloseModal()" style="padding: 4px 8px; color: var(--text-tertiary);">&times;</button>
        </div>

        <form onsubmit="window.LuckRoyale.SubmitAssetUpload(event, '${slotKey || ''}'); return false;">
          <div style="margin-bottom: 16px;">
            <label class="form-label" style="display: block; font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px;">Choose Image File (PNG, JPG, WebP - max 10MB)</label>
            <input type="file" id="upload-file-input" accept="image/png,image/jpeg,image/webp" required class="form-input" style="width: 100%;">
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <button type="button" class="btn btn-secondary" onclick="window.LuckRoyale.CloseModal()">Cancel</button>
            <button type="submit" class="btn btn-primary" id="btn-submit-upload">Upload File</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(overlay);
    _activeModalEl = overlay;
  }

  // ---------------------------------------------------------------------------
  // INTERACTION HANDLERS & API MUTATIONS
  // ---------------------------------------------------------------------------

  function selectMachine(cid) {
    _selectedCid = cid;
    renderStudio(null, _activeTab, cid);
  }

  function switchStudioTab(tabId) {
    _activeTab = tabId;
    const canvas = getCanvas();
    if (canvas) drawStudio(canvas);
  }

  async function toggleActiveMachine(cid, newState) {
    try {
      const res = await (window.apiClient || window.ApiClient).post(`/api/admin/luck-royale/machines/${cid}/toggle`, { enabled: newState });
      if (res && res.ok) {
        window.UI.Toast(`Machine #${cid} ${newState ? 'enabled' : 'disabled'} successfully`, 'success');
        await fetchMachines();
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Toggle failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error toggling machine: ${e.message}`, 'error');
    }
  }

  async function saveMachineSettingsForm(event, cid) {
    event.preventDefault();
    const btn = document.getElementById('btn-save-settings');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const payload = {
      display_name: fd.get('display_name'),
      coin_type: parseInt(fd.get('coin_type'), 10),
      once_price: parseInt(fd.get('once_price'), 10),
      ten_price: parseInt(fd.get('ten_price'), 10),
      rare_item_max: parseInt(fd.get('rare_item_max'), 10),
      chest_type_enum: parseInt(fd.get('chest_type_enum'), 10),
      discount: parseInt(fd.get('discount') || 0, 10),
      free_cooldown_seconds: parseInt(fd.get('free_cooldown_seconds') || 86400, 10)
    };

    try {
      const res = await (window.apiClient || window.ApiClient).put(`/api/admin/luck-royale/machines/${cid}`, payload);
      if (res && res.ok) {
        window.UI.Toast('Machine configuration saved successfully', 'success');
        await fetchMachines();
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Save failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error saving configuration: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function submitEditMachine(event, cid) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-machine');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const payload = {
      display_name: fd.get('display_name'),
      coin_type: parseInt(fd.get('coin_type'), 10),
      once_price: parseInt(fd.get('once_price'), 10),
      ten_price: parseInt(fd.get('ten_price'), 10),
      rare_item_max: parseInt(fd.get('rare_item_max'), 10),
      chest_type_enum: parseInt(fd.get('chest_type_enum'), 10),
      discount: parseInt(fd.get('discount') || 0, 10)
    };

    try {
      const res = await (window.apiClient || window.ApiClient).put(`/api/admin/luck-royale/machines/${cid}`, payload);
      if (res && res.ok) {
        window.UI.Toast(`Machine #${cid} updated successfully`, 'success');
        closeActiveModal();
        await fetchMachines();
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Update failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error updating machine: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function submitAddReward(event, cid) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-add-reward');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const iid = parseInt(fd.get('item_id'), 10);
    const repId = fd.get('repeated_item_id') ? parseInt(fd.get('repeated_item_id'), 10) : null;

    const payload = {
      chest_id: cid,
      item_id: iid,
      reward_level: parseInt(fd.get('reward_level'), 10),
      weight: parseInt(fd.get('weight'), 10),
      item_num: parseInt(fd.get('item_num'), 10),
      drop_up_ratio: parseFloat(fd.get('drop_up_ratio') || 1.0),
      repeated_item_id: repId,
      repeated_item_num: repId ? parseInt(fd.get('repeated_item_num') || 2, 10) : 0,
      is_show: true
    };

    try {
      const res = await (window.apiClient || window.ApiClient).post('/api/admin/luck-royale/reward-pools', payload);
      if (res && res.ok) {
        window.UI.Toast(`Added item #${iid} to Machine #${cid} prize pool`, 'success');
        closeActiveModal();
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Failed to add reward', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error adding reward: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function submitEditReward(event, cid, itemId) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-edit-reward');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const repId = fd.get('repeated_item_id') ? parseInt(fd.get('repeated_item_id'), 10) : null;

    const payload = {
      chest_id: cid,
      item_id: itemId,
      reward_level: parseInt(fd.get('reward_level'), 10),
      weight: parseInt(fd.get('weight'), 10),
      item_num: parseInt(fd.get('item_num'), 10),
      drop_up_ratio: parseFloat(fd.get('drop_up_ratio') || 1.0),
      repeated_item_id: repId,
      repeated_item_num: repId ? parseInt(fd.get('repeated_item_num') || 2, 10) : 0
    };

    try {
      const res = await (window.apiClient || window.ApiClient).put('/api/admin/luck-royale/reward-pools', payload);
      if (res && res.ok) {
        window.UI.Toast(`Reward #${itemId} updated successfully`, 'success');
        closeActiveModal();
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Update failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error updating reward: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function removePoolItem(cid, itemId) {
    window.UI.Confirm(
      `Remove item #${itemId} from Machine #${cid} prize pool?`,
      async () => {
        try {
          const res = await (window.apiClient || window.ApiClient).delete(`/api/admin/luck-royale/reward-pools?chest_id=${cid}&item_id=${itemId}`);
          if (res && res.ok) {
            window.UI.Toast(`Removed item #${itemId}`, 'success');
            await fetchMachineData(cid);
            drawStudio(getCanvas());
          } else {
            window.UI.Toast((res && (res.error || res.message)) || 'Delete failed', 'error');
          }
        } catch (e) {
          window.UI.Toast(`Error deleting item: ${e.message}`, 'error');
        }
      }
    );
  }

  async function reorderPoolItem(cid, itemId, direction) {
    try {
      const res = await (window.apiClient || window.ApiClient).post('/api/admin/luck-royale/reward-pools/reorder', {
        chest_id: cid,
        item_id: itemId,
        direction: direction
      });
      if (res && res.ok) {
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Reorder failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error reordering item: ${e.message}`, 'error');
    }
  }

  async function assignSlotAsset(cid, slotKey, assetUrl) {
    const payload = {};
    payload[slotKey] = assetUrl;
    try {
      const res = await (window.apiClient || window.ApiClient).post(`/api/admin/luck-royale/machines/${cid}/artwork`, payload);
      if (res && res.ok) {
        window.UI.Toast(`Assigned ${slotKey} successfully`, 'success');
        closeActiveModal();
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Artwork assignment failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error assigning artwork: ${e.message}`, 'error');
    }
  }

  async function submitEventForm(event, cid) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-event');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const payload = {
      title: fd.get('title'),
      discount_percent: parseInt(fd.get('discount_percent') || 0, 10),
      rate_up_multiplier: parseFloat(fd.get('rate_up_multiplier') || 1.0),
      start_time: parseInt(fd.get('start_time'), 10),
      end_time: parseInt(fd.get('end_time'), 10),
      active: fd.get('active') === '1'
    };

    try {
      const res = await (window.apiClient || window.ApiClient).post(`/api/admin/luck-royale/machines/${cid}/events`, payload);
      if (res && res.ok) {
        window.UI.Toast('Event campaign configuration saved', 'success');
        closeActiveModal();
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Save event failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error saving event: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function submitRewardImageMapping(event, cid, itemId) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-map-img');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const imgUrl = fd.get('image_url');

    try {
      const res = await (window.apiClient || window.ApiClient).post('/api/admin/luck-royale/reward-images', {
        item_id: itemId,
        image_url: imgUrl
      });
      if (res && res.ok) {
        window.UI.Toast(`Custom image assigned to Item #${itemId}`, 'success');
        closeActiveModal();
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Mapping failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error assigning custom image: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function restoreDefaultImage(cid, itemId) {
    try {
      const res = await (window.apiClient || window.ApiClient).delete(`/api/admin/luck-royale/reward-images?item_id=${itemId}`);
      if (res && res.ok) {
        window.UI.Toast(`Default image restored for Item #${itemId}`, 'success');
        closeActiveModal();
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Restore failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error restoring image: ${e.message}`, 'error');
    }
  }

  async function submitCreateMachine(event) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-create-machine');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const newCid = parseInt(fd.get('chest_id'), 10);
    const payload = {
      chest_id: newCid,
      display_name: fd.get('display_name'),
      coin_type: parseInt(fd.get('coin_type'), 10),
      once_price: parseInt(fd.get('once_price'), 10),
      ten_price: parseInt(fd.get('ten_price'), 10),
      rare_item_max: parseInt(fd.get('rare_item_max'), 10)
    };

    try {
      const res = await (window.apiClient || window.ApiClient).post('/api/admin/luck-royale/machines', payload);
      if (res && res.ok) {
        window.UI.Toast(`Created new Royale #${newCid} successfully`, 'success');
        closeActiveModal();
        _selectedCid = newCid;
        await fetchMachines();
        renderStudio(null, 'settings', newCid);
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Failed to create machine', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error creating machine: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function submitDuplicateMachine(event, srcCid) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-duplicate');
    if (btn) btn.disabled = true;

    const fd = new FormData(event.target);
    const newCid = parseInt(fd.get('new_chest_id'), 10);
    const newName = fd.get('new_chest_name');

    try {
      const res = await (window.apiClient || window.ApiClient).post(`/api/admin/luck-royale/machines/${srcCid}/duplicate`, {
        source_chest_id: srcCid,
        new_chest_id: newCid,
        new_chest_name: newName
      });
      if (res && res.ok) {
        window.UI.Toast(`Duplicated Machine #${srcCid} as #${newCid}`, 'success');
        closeActiveModal();
        _selectedCid = newCid;
        await fetchMachines();
        renderStudio(null, 'settings', newCid);
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Duplicate failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error duplicating machine: ${e.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function submitAssetUpload(event, slotKey) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-upload');
    const fileInput = document.getElementById('upload-file-input');
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    if (btn) btn.disabled = true;

    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = reader.result.split(',')[1];
      try {
        const res = await (window.apiClient || window.ApiClient).post('/api/admin/luck-royale/assets/upload', {
          filename: file.name,
          data_base64: b64
        });
        if (res && res.ok) {
          window.UI.Toast(`Uploaded ${file.name} successfully`, 'success');
          closeActiveModal();
          await fetchAssets();
          if (slotKey) {
            await assignSlotAsset(_selectedCid, slotKey, res.url);
          } else {
            drawStudio(getCanvas());
          }
        } else {
          window.UI.Toast((res && (res.error || res.message)) || 'Upload failed', 'error');
        }
      } catch (e) {
        window.UI.Toast(`Error uploading: ${e.message}`, 'error');
      } finally {
        if (btn) btn.disabled = false;
      }
    };
    reader.readAsDataURL(file);
  }

  async function executeTestSpin(cid, gachaType) {
    try {
      window.UI.Toast(`Executing ${gachaType === 1 ? '1x' : '10x'} spin simulation...`, 'info');
      const res = await (window.apiClient || window.ApiClient).post('/api/admin/luck-royale/transactions', {
        action: 'spin',
        chest_id: cid,
        gacha_type: gachaType
      });
      if (res && res.ok) {
        const rewards = res.rewards || [];
        const isJackpot = res.has_big_reward;
        window.UI.Toast(`Spin completed! ${rewards.length} rewards obtained ${isJackpot ? '(JACKPOT TRIGGERED!)' : ''}`, 'success');
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Spin failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Spin execution error: ${e.message}`, 'error');
    }
  }

  async function adjustLuckyMeter(event, cid) {
    event.preventDefault();
    const fd = new FormData(event.target);
    const meterVal = parseInt(fd.get('meter_value'), 10);
    try {
      const res = await (window.apiClient || window.ApiClient).post(`/api/admin/luck-royale/meters/${cid}`, { lucky_meter: meterVal });
      if (res && res.ok) {
        window.UI.Toast(`Lucky meter updated to ${meterVal}`, 'success');
        await fetchMachineData(cid);
        drawStudio(getCanvas());
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Meter adjustment failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error: ${e.message}`, 'error');
    }
  }

  async function grantVoucher(voucherId, qty) {
    try {
      const res = await (window.apiClient || window.ApiClient).post('/api/admin/luck-royale/currencies-vouchers', {
        item_id: voucherId,
        quantity: qty
      });
      if (res && res.ok) {
        window.UI.Toast(`Granted ${qty}x vouchers (Item #${voucherId})`, 'success');
      } else {
        window.UI.Toast((res && (res.error || res.message)) || 'Grant failed', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Error granting voucher: ${e.message}`, 'error');
    }
  }

  function onPoolSearch(val) {
    _poolSearchQuery = val;
    const canvas = getCanvas();
    if (canvas) drawStudio(canvas);
  }

  function onPoolCategoryFilter(val) {
    _poolCategoryFilter = val;
    const canvas = getCanvas();
    if (canvas) drawStudio(canvas);
  }

  function filterDrawerAssets(query) {
    const q = (query || '').toLowerCase();
    const cat = (document.getElementById('drawer-asset-cat')?.value || 'all').toLowerCase();
    let filtered = _cachedAssets;
    if (q) filtered = filtered.filter(a => a.filename.toLowerCase().includes(q) || (a.category || '').toLowerCase().includes(q));
    if (cat !== 'all') filtered = filtered.filter(a => (a.category || '').toLowerCase() === cat);
    const container = document.getElementById('drawer-assets-container');
    if (container) container.innerHTML = renderDrawerAssetGrid(filtered, _drawerSlotKey, _selectedCid);
  }

  function filterDrawerCategory(cat) {
    filterDrawerAssets(document.getElementById('drawer-asset-search')?.value || '');
  }

  function onRewardIdInput(val) {
    const iid = parseInt(val, 10);
    const container = document.getElementById('add-reward-preview-container');
    if (!container || !iid) return;
    const imgUrl = `/assets/freefire/1.39/items/${iid}.png`;
    container.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        ${C.renderItemImage(imgUrl, '', 28, iid)}
        <span>Item #${iid} preview: <strong style="color:#fff;">${imgUrl}</strong></span>
      </div>
    `;
  }

  function onCustomImageInput(val) {
    const box = document.getElementById('mapping-preview-box');
    if (!box) return;
    box.innerHTML = C.renderItemImage(val, '', 48);
  }

  function downloadConfigJson(cid) {
    const m = _cachedMachines.find(x => x.chest_id === cid) || {};
    const payload = JSON.stringify({
      chest_id: cid,
      machine: m,
      artwork: _cachedArtwork,
      pool: _cachedPool,
      event: _cachedEvent
    }, null, 2);
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `luck_royale_machine_${cid}_config.json`;
    a.click();
    URL.revokeObjectURL(url);
    window.UI.Toast(`Exported config for Machine #${cid}`, 'success');
  }

  // ---------------------------------------------------------------------------
  // Public Interface Exposure
  // ---------------------------------------------------------------------------

  // Master Studio Routes Integration
  window.LuckRoyale.RenderStudio = renderStudio;
  window.LuckRoyale.Machines = (canvas) => renderStudio(canvas, 'settings');
  window.LuckRoyale.Overview = (canvas) => renderStudio(canvas, 'overview');
  window.LuckRoyale.Pools = (canvas) => renderStudio(canvas, 'pool');
  window.LuckRoyale.Pity = (canvas) => renderStudio(canvas, 'pity');
  window.LuckRoyale.Currencies = (canvas) => renderStudio(canvas, 'pity');
  window.LuckRoyale.Forge = (canvas) => renderStudio(canvas, 'forge');
  window.LuckRoyale.Events = (canvas) => renderStudio(canvas, 'events');
  window.LuckRoyale.Banners = (canvas) => renderStudio(canvas, 'artwork');
  window.LuckRoyale.Player = (canvas) => renderStudio(canvas, 'pity');
  window.LuckRoyale.Transactions = (canvas) => renderStudio(canvas, 'transactions');
  window.LuckRoyale.Simulator = (canvas) => renderStudio(canvas, 'simulator');
  window.LuckRoyale.Config = (canvas) => renderStudio(canvas, 'config');
  window.LuckRoyale.SelectMachine = selectMachine;
  window.LuckRoyale.SwitchStudioTab = switchStudioTab;
  window.LuckRoyale.ToggleActiveMachine = toggleActiveMachine;
  window.LuckRoyale.SaveMachineSettingsForm = saveMachineSettingsForm;
  window.LuckRoyale.SubmitEditMachine = submitEditMachine;
  window.LuckRoyale.SubmitAddReward = submitAddReward;
  window.LuckRoyale.SubmitEditReward = submitEditReward;
  window.LuckRoyale.RemovePoolItem = removePoolItem;
  window.LuckRoyale.ReorderPoolItem = reorderPoolItem;
  window.LuckRoyale.AssignSlotAsset = assignSlotAsset;
  window.LuckRoyale.SubmitEventForm = submitEventForm;
  window.LuckRoyale.SubmitRewardImageMapping = submitRewardImageMapping;
  window.LuckRoyale.RestoreDefaultImage = restoreDefaultImage;
  window.LuckRoyale.SubmitCreateMachine = submitCreateMachine;
  window.LuckRoyale.SubmitDuplicateMachine = submitDuplicateMachine;
  window.LuckRoyale.SubmitAssetUpload = submitAssetUpload;
  window.LuckRoyale.ExecuteTestSpin = executeTestSpin;
  window.LuckRoyale.AdjustLuckyMeter = adjustLuckyMeter;
  window.LuckRoyale.GrantVoucher = grantVoucher;
  window.LuckRoyale.OnPoolSearch = onPoolSearch;
  window.LuckRoyale.OnPoolCategoryFilter = onPoolCategoryFilter;
  window.LuckRoyale.FilterDrawerAssets = filterDrawerAssets;
  window.LuckRoyale.FilterDrawerCategory = filterDrawerCategory;
  window.LuckRoyale.OnRewardIdInput = onRewardIdInput;
  window.LuckRoyale.OnCustomImageInput = onCustomImageInput;
  window.LuckRoyale.DownloadConfigJson = downloadConfigJson;

  // Modal Openers
  window.LuckRoyale.OpenEditMachineModal = openEditMachineModal;
  window.LuckRoyale.OpenAddRewardModal = openAddRewardModal;
  window.LuckRoyale.OpenAddPoolItemModal = openAddRewardModal; // backward-compat alias
  window.LuckRoyale.OpenEditRewardModal = openEditRewardModal;
  window.LuckRoyale.OpenEditPoolItemModal = openEditRewardModal; // backward-compat alias
  window.LuckRoyale.OpenArtworkDrawer = openArtworkDrawer;
  window.LuckRoyale.OpenAssetPickerForSlot = openArtworkDrawer; // backward-compat alias
  window.LuckRoyale.OpenEventModal = openEventModal;
  window.LuckRoyale.OpenRewardImageMappingModal = openRewardImageMappingModal;
  window.LuckRoyale.OpenCreateMachineModal = openCreateMachineModal;
  window.LuckRoyale.OpenDuplicateMachineModal = openDuplicateMachineModal;
  window.LuckRoyale.OpenUploadAssetModal = openUploadAssetModal;
  window.LuckRoyale.CloseModal = closeActiveModal;

})();
