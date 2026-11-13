/**
 * Free Fire 1.39 Events & Quests Section Controller
 * High-performance component logic for India V1 Modular Dashboard.
 * Strict compliance: Zero emojis, pure SVG icons, viewport-fitted structured layout.
 */

(function () {
  'use strict';

  // State
  let eventsState = {
    events: [],
    banners: [],
    activeFilter: 'all',
    statusFilter: 'all',
    searchQuery: '',
    sortBy: 'sort_id_asc',
    currentTab: 'list', // 'list' | 'builder' | 'bingo'
    editingEventId: null,
    bonusEvents: [],
    featureSwitches: []
  };

  // Known 1.39 Item Presets
  const ITEM_PRESETS = [
    { id: 203000003, name: 'Elite Pass Jacket (M)' },
    { id: 203000007, name: 'Sakura Demon Vest (F)' },
    { id: 203000573, name: 'Combat Tactical Hoodie' },
    { id: 204000345, name: 'Combat Cargo Pants' },
    { id: 205000299, name: 'Combat High Boots' },
    { id: 208000000, name: 'Standard Combat Mask' },
    { id: 211000000, name: 'Classic Officer Cap' },
    { id: 901000004, name: 'Season 1 Ranked Banner' },
    { id: 902000004, name: 'Master Avatar Frame' },
    { id: 911000001, name: 'Weapon Royale Crate' },
    { id: 911000002, name: 'Diamond Royale Crate' },
    { id: 911000003, name: 'Gold Royale Crate' }
  ];

  // Table Types Mapping (COW.EventTabType)
  const TABLE_TYPES = {
    1: { name: 'Daily Missions', badgeClass: 'badge-cyan', label: 'DAILY' },
    2: { name: 'Festival Launch', badgeClass: 'badge-amber', label: 'FESTIVAL' },
    3: { name: 'Festival Hub', badgeClass: 'badge-amber', label: 'FESTIVAL' },
    4: { name: 'Bingo Grid Cell', badgeClass: 'badge-purple', label: 'BINGO' },
    5: { name: 'Token Exchange', badgeClass: 'badge-emerald', label: 'EXCHANGE' },
    6: { name: 'Mega Season Preview', badgeClass: 'badge-rose', label: 'SEASON' },
    7: { name: 'Community Event', badgeClass: 'badge-blue', label: 'COMMUNITY' },
    9: { name: 'Activeness Progress', badgeClass: 'badge-emerald', label: 'ACTIVENESS' }
  };

  // Tag Types Mapping (COW.EEventTag)
  const TAG_TYPES = {
    0: { label: '', class: '' },
    1: { label: 'NEW', class: 'tag-new' },
    2: { label: 'HOT', class: 'tag-hot' },
    3: { label: 'LIMITED', class: 'tag-limited' },
    1000: { label: 'PREVIEW', class: 'tag-preview' }
  };

  // Navigation Jump Mapping
  const GOS_POS_LABELS = {
    0: 'None (In-Lobby)',
    1: 'Profile View',
    2: 'Squad Lobby',
    3: 'Store / Mall',
    4: 'Vault / Inventory',
    5: 'Clan Hub',
    6: 'Top-Up / Payment',
    7: 'Activity / Events',
    8: 'Friends List',
    14: 'Elite Pass Main',
    114: 'Fire Pass Controller',
    15: 'Luck Royale / Gacha'
  };

  // Clean SVG Icons
  const SVG_ICONS = {
    gem: `<svg class="svg-ico gem" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12l4 6-10 12L2 9z"></path><path d="M2 9h20"></path><path d="M10 3L6 9l6 12 6-12-4-6"></path></svg>`,
    gold: `<svg class="svg-ico gold" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"></circle><path d="M18.09 10.37A6 6 0 1 1 10.34 18"></path><path d="M7 6h2v4H7z"></path></svg>`,
    item: `<svg class="svg-ico item" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>`,
    activeness: `<svg class="svg-ico activeness" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>`,
    exp: `<svg class="svg-ico exp" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"></circle><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"></path></svg>`,
    plus: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`,
    trash: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`,
    edit: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>`,
    copy: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`,
    refresh: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>`,
    target: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>`,
    clock: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
    link: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`,
    check: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
    grid: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>`,
    search: `<svg class="svg-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`
  };

  // Toast Notification System
  function showToast(message, type = 'info') {
    const container = document.getElementById('events-toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `evt-toast evt-toast-${type}`;
    toast.innerHTML = `<span class="evt-toast-dot"></span><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('hide');
      setTimeout(() => toast.remove(), 260);
    }, 3200);
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Network Calls
  async function apiGet(endpoint) {
    try {
      const res = await fetch(endpoint, { method: 'GET', headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(`[Events] GET ${endpoint} error:`, err);
      showToast(`Request failed: ${err.message}`, 'error');
      return null;
    }
  }

  async function apiPost(endpoint, payload) {
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.error(`[Events] POST ${endpoint} error:`, err);
      showToast(`Action failed: ${err.message}`, 'error');
      return null;
    }
  }

  // Load all CMS data
  async function loadEventsData() {
    const data = await apiGet('/api/dashboard/cms');
    if (data && data.ok && data.cms) {
      eventsState.events = data.cms.events || [];
      eventsState.bonusEvents = data.cms.bonus_events || [];
      eventsState.featureSwitches = data.cms.feature_switches || [];
      renderActiveTab();
      updateHeaderCounts();
    }
    // Also load available banners for selector
    loadBanners();
  }

  async function loadBanners() {
    const bData = await apiGet('/api/dashboard/cms/banners');
    if (bData && bData.ok && Array.isArray(bData.banners)) {
      eventsState.banners = bData.banners;
      populateBannerDropdowns();
    }
  }

  function updateHeaderCounts() {
    const countEl = document.getElementById('evt-total-count');
    if (countEl) {
      const activeCount = eventsState.events.filter(e => e.enabled).length;
      countEl.textContent = `${activeCount} Active / ${eventsState.events.length} Total`;
    }
  }

  // Tab Switching (Sub-tabs within Events view)
  function switchEventsTab(tabName) {
    eventsState.currentTab = tabName;
    document.querySelectorAll('.evt-subnav-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.querySelectorAll('.evt-tab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === `pane-evt-${tabName}`);
    });
    renderActiveTab();
  }

  function renderActiveTab() {
    if (eventsState.currentTab === 'list') {
      renderEventsList();
    } else if (eventsState.currentTab === 'builder') {
      updateLivePreview();
    } else if (eventsState.currentTab === 'bingo') {
      renderBingoMatrix();
    }
  }

  // ---------------------------------------------------------------------------
  // TAB 1: Active Events & Quests Grid View
  // ---------------------------------------------------------------------------
  function renderEventsList() {
    const container = document.getElementById('events-grid-cards');
    if (!container) return;

    let filtered = [...eventsState.events];

    // Filter by category
    if (eventsState.activeFilter !== 'all') {
      const catNum = Number(eventsState.activeFilter);
      filtered = filtered.filter(e => {
        if (catNum === 1) return e.table_type === 1; // Daily
        if (catNum === 2) return e.table_type === 2 || e.table_type === 3; // Festival
        if (catNum === 4) return e.table_type === 4; // Bingo
        if (catNum === 5) return e.table_type === 5; // Token
        if (catNum === 6) return e.table_type === 6; // Mega
        if (catNum === 9) return e.table_type === 9; // Activeness
        return true;
      });
    }

    // Filter by status
    if (eventsState.statusFilter === 'enabled') {
      filtered = filtered.filter(e => e.enabled);
    } else if (eventsState.statusFilter === 'disabled') {
      filtered = filtered.filter(e => !e.enabled);
    }

    // Filter by search query
    if (eventsState.searchQuery) {
      const q = eventsState.searchQuery.toLowerCase();
      filtered = filtered.filter(e => {
        const title = (e.act_title || '').toLowerCase();
        const desc = (e.act_text || '').toLowerCase();
        const id = String(e.id || '');
        return title.includes(q) || desc.includes(q) || id.includes(q);
      });
    }

    // Sort
    filtered.sort((a, b) => {
      if (eventsState.sortBy === 'sort_id_asc') return (a.sort_id || 0) - (b.sort_id || 0);
      if (eventsState.sortBy === 'sort_id_desc') return (b.sort_id || 0) - (a.sort_id || 0);
      if (eventsState.sortBy === 'id_asc') return (a.id || 0) - (b.id || 0);
      if (eventsState.sortBy === 'id_desc') return (b.id || 0) - (a.id || 0);
      return 0;
    });

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="evt-empty-state">
          <div class="evt-empty-icon">${SVG_ICONS.target}</div>
          <div class="evt-empty-title">No events or quests match your criteria</div>
          <div class="evt-empty-desc">Adjust filters or create a new event using the builder.</div>
          <button class="evt-btn evt-btn-primary" onclick="window.eventsModule.createNewEvent()">
            ${SVG_ICONS.plus}<span>Create Custom Event</span>
          </button>
        </div>`;
      return;
    }

    container.innerHTML = filtered.map(evt => renderEventCard(evt)).join('');
  }

  function renderEventCard(evt) {
    const tableInfo = TABLE_TYPES[evt.table_type] || { name: 'Custom', badgeClass: 'badge-gray', label: 'EVENT' };
    const tagInfo = TAG_TYPES[evt.act_tag] || { label: '', class: '' };
    const awards = evt.awards || [];

    // Render rewards row
    const rewardsHtml = awards.map(a => renderRewardPill(a)).join('');

    // Navigation info
    const navText = evt.gos_pos > 0 ? (GOS_POS_LABELS[evt.gos_pos] || `Target #${evt.gos_pos}`) : null;

    // Time window
    const now = Math.floor(Date.now() / 1000);
    const isPermanent = !evt.end_time || evt.end_time > now + (200 * 86400);
    const timeLabel = isPermanent ? 'Permanent' : `Ends ${new Date((evt.end_time || 0) * 1000).toLocaleDateString()}`;

    return `
      <div class="evt-card ${evt.enabled ? 'is-enabled' : 'is-disabled'}" data-id="${evt.id}">
        <div class="evt-card-header">
          <div class="evt-card-badges">
            <span class="evt-pill ${tableInfo.badgeClass}">${tableInfo.label}</span>
            <span class="evt-pill badge-id">#${evt.id}</span>
            ${tagInfo.label ? `<span class="evt-pill ${tagInfo.class}">${tagInfo.label}</span>` : ''}
          </div>
          <label class="evt-switch" title="Toggle Active / Paused">
            <input type="checkbox" ${evt.enabled ? 'checked' : ''} onchange="window.eventsModule.toggleEvent(${evt.id}, this.checked)">
            <span class="evt-slider"></span>
          </label>
        </div>

        <div class="evt-card-body">
          <div class="evt-card-title-row">
            <h4 class="evt-card-title">${escapeHtml(evt.act_title || 'Untitled Event')}</h4>
            ${evt.award_context ? `<span class="evt-card-context">${escapeHtml(evt.award_context)}</span>` : ''}
          </div>
          <p class="evt-card-desc">${escapeHtml(evt.act_text || 'No objective description.')}</p>

          <div class="evt-card-condition-box">
            <div class="evt-cond-meta">
              <span class="evt-cond-label">${SVG_ICONS.target} Objective:</span>
              <span class="evt-cond-val">${evt.cdt_value ? `${evt.cdt_value} Required` : 'Instant / Login'}</span>
            </div>
            ${evt.is_process_show ? `
              <div class="evt-sim-progress">
                <div class="evt-sim-bar" style="width: 0%;"></div>
                <span class="evt-sim-text">0 / ${evt.cdt_value || 1}</span>
              </div>
            ` : ''}
          </div>

          <div class="evt-card-rewards-section">
            <div class="evt-rewards-label">Rewards &amp; Drops:</div>
            <div class="evt-rewards-row">
              ${rewardsHtml || '<span class="evt-no-rewards">No rewards configured</span>'}
            </div>
          </div>

          <div class="evt-card-footer-meta">
            <span class="evt-meta-item">${SVG_ICONS.clock} ${timeLabel}</span>
            ${navText ? `<span class="evt-meta-item evt-meta-nav">${SVG_ICONS.link} ${escapeHtml(navText)}</span>` : ''}
            <span class="evt-meta-item">Order: ${evt.sort_id || 1}</span>
          </div>
        </div>

        <div class="evt-card-actions">
          <button class="evt-btn evt-btn-sm evt-btn-secondary" onclick="window.eventsModule.editEvent(${evt.id})">
            ${SVG_ICONS.edit}<span>Edit</span>
          </button>
          <button class="evt-btn evt-btn-sm evt-btn-secondary" onclick="window.eventsModule.duplicateEvent(${evt.id})" title="Clone to new ID">
            ${SVG_ICONS.copy}<span>Duplicate</span>
          </button>
          <button class="evt-btn evt-btn-sm evt-btn-danger" onclick="window.eventsModule.deleteEvent(${evt.id})" title="Delete event">
            ${SVG_ICONS.trash}<span>Delete</span>
          </button>
        </div>
      </div>`;
  }

  function renderRewardPill(award) {
    const type = Number(award.award_type || 1);
    const count = Number(award.award_num || 1);
    const id = Number(award.award_id || 0);

    let icon = SVG_ICONS.item;
    let label = `Item #${id}`;
    let pillClass = 'reward-item';

    if (type === 3) { // Diamonds
      icon = SVG_ICONS.gem;
      label = `${count.toLocaleString()} Gems`;
      pillClass = 'reward-gem';
    } else if (type === 2) { // Gold
      icon = SVG_ICONS.gold;
      label = `${count.toLocaleString()} Gold`;
      pillClass = 'reward-gold';
    } else if (type === 6) { // Activeness
      icon = SVG_ICONS.activeness;
      label = `${count} Activeness`;
      pillClass = 'reward-activeness';
    } else if (type === 5) { // EXP
      icon = SVG_ICONS.exp;
      label = `${count} EXP`;
      pillClass = 'reward-exp';
    } else if (type === 1) { // Item
      const preset = ITEM_PRESETS.find(p => p.id === id);
      label = preset ? `${preset.name} (x${count})` : `Item #${id} (x${count})`;
    }

    return `
      <div class="evt-reward-pill ${pillClass}">
        <span class="evt-reward-ico">${icon}</span>
        <span class="evt-reward-text">${escapeHtml(label)}</span>
      </div>`;
  }

  // ---------------------------------------------------------------------------
  // TAB 2: Custom Event & Mission Builder
  // ---------------------------------------------------------------------------
  function openBuilderForNew() {
    eventsState.editingEventId = null;
    const nextId = getNextAvailableId();

    setFieldValue('bld-id', nextId);
    setFieldValue('bld-title', '');
    setFieldValue('bld-desc', '');
    setFieldValue('bld-context', 'Mission Pack');
    setFieldValue('bld-table-type', '1');
    setFieldValue('bld-tag', '1'); // NEW
    setFieldValue('bld-sort', '1');
    setFieldValue('bld-group', '1');
    setFieldChecked('bld-enabled', true);
    setFieldValue('bld-condition-val', '1');
    setFieldChecked('bld-show-progress', true);
    setFieldValue('bld-activity-type', '0');
    setFieldValue('bld-gos-pos', '0');
    setFieldValue('bld-banner-main', '/banners/activity_banner.png');
    setFieldValue('bld-banner-lobby', '/banners/lobby_ad_1.png');

    // Preset time: now to +30 days
    const now = Math.floor(Date.now() / 1000);
    setFieldValue('bld-start-time', now - 3600);
    setFieldValue('bld-end-time', now + (30 * 86400));

    // Clear rewards and add 2 starter rows
    const rewardsContainer = document.getElementById('bld-rewards-list');
    if (rewardsContainer) {
      rewardsContainer.innerHTML = '';
      addRewardRow({ award_type: 3, award_id: 0, award_num: 50 }); // 50 Gems
      addRewardRow({ award_type: 2, award_id: 0, award_num: 1000 }); // 1000 Gold
    }

    document.getElementById('bld-form-mode-title').textContent = 'Create New Event / Quest';
    document.getElementById('bld-badge-id-indicator').textContent = `#${nextId}`;

    switchEventsTab('builder');
    updateLivePreview();
  }

  function openBuilderForEdit(eventId) {
    const evt = eventsState.events.find(e => e.id === Number(eventId));
    if (!evt) {
      showToast(`Event #${eventId} not found`, 'error');
      return;
    }

    eventsState.editingEventId = evt.id;

    setFieldValue('bld-id', evt.id);
    setFieldValue('bld-title', evt.act_title || '');
    setFieldValue('bld-desc', evt.act_text || '');
    setFieldValue('bld-context', evt.award_context || '');
    setFieldValue('bld-table-type', String(evt.table_type || 1));
    setFieldValue('bld-tag', String(evt.act_tag || 0));
    setFieldValue('bld-sort', String(evt.sort_id || 1));
    setFieldValue('bld-group', String(evt.group_id || 1));
    setFieldChecked('bld-enabled', evt.enabled !== false);
    setFieldValue('bld-condition-val', String(evt.cdt_value || 1));
    setFieldChecked('bld-show-progress', evt.is_process_show === 1);
    setFieldValue('bld-activity-type', String(evt.activity_type || 0));
    setFieldValue('bld-gos-pos', String(evt.gos_pos || 0));
    setFieldValue('bld-banner-main', evt.image_url || '/banners/activity_banner.png');
    setFieldValue('bld-banner-lobby', evt.image_url_for_lobby || '/banners/lobby_ad_1.png');

    setFieldValue('bld-start-time', evt.start_time || Math.floor(Date.now() / 1000));
    setFieldValue('bld-end-time', evt.end_time || Math.floor(Date.now() / 1000) + (30 * 86400));

    // Populate rewards list
    const rewardsContainer = document.getElementById('bld-rewards-list');
    if (rewardsContainer) {
      rewardsContainer.innerHTML = '';
      const awards = evt.awards && evt.awards.length > 0 ? evt.awards : [{ award_type: 3, award_id: 0, award_num: 50 }];
      awards.forEach(a => addRewardRow(a));
    }

    document.getElementById('bld-form-mode-title').textContent = `Editing Event #${evt.id}`;
    document.getElementById('bld-badge-id-indicator').textContent = `#${evt.id}`;

    switchEventsTab('builder');
    updateLivePreview();
  }

  function getNextAvailableId() {
    const ids = eventsState.events.map(e => Number(e.id)).filter(n => !isNaN(n) && n < 4000);
    const max = ids.length > 0 ? Math.max(...ids) : 1000;
    return max + 1;
  }

  function addRewardRow(award = { award_type: 3, award_id: 0, award_num: 50 }) {
    const container = document.getElementById('bld-rewards-list');
    if (!container) return;

    const rowId = 'rew-row-' + Math.random().toString(36).substring(2, 9);
    const row = document.createElement('div');
    row.className = 'evt-reward-edit-row';
    row.id = rowId;

    const curType = Number(award.award_type || 3);
    const curNum = Number(award.award_num || 50);
    const curId = Number(award.award_id || 0);

    row.innerHTML = `
      <div class="evt-rew-icon-col">
        <span class="evt-rew-preview-ico">${getRewardIcon(curType)}</span>
      </div>
      <div class="evt-rew-type-col">
        <select class="evt-input evt-rew-type-select" onchange="window.eventsModule.onRewardTypeChange('${rowId}', this.value)">
          <option value="3" ${curType === 3 ? 'selected' : ''}>Diamonds (Gems)</option>
          <option value="2" ${curType === 2 ? 'selected' : ''}>Gold (Coins)</option>
          <option value="1" ${curType === 1 ? 'selected' : ''}>Item / Skin ID</option>
          <option value="6" ${curType === 6 ? 'selected' : ''}>Activeness Points</option>
          <option value="5" ${curType === 5 ? 'selected' : ''}>Account EXP</option>
        </select>
      </div>
      <div class="evt-rew-item-col" style="${curType === 1 ? '' : 'display:none;'}">
        <div class="evt-item-input-group">
          <input type="number" class="evt-input evt-rew-item-id" value="${curId}" placeholder="Item ID" oninput="window.eventsModule.updateLivePreview()">
          <select class="evt-input evt-item-preset-select" onchange="window.eventsModule.onPresetSelect('${rowId}', this.value)">
            <option value="">Presets...</option>
            ${ITEM_PRESETS.map(p => `<option value="${p.id}" ${p.id === curId ? 'selected' : ''}>${p.name}</option>`).join('')}
          </select>
        </div>
      </div>
      <div class="evt-rew-num-col">
        <input type="number" class="evt-input evt-rew-num" value="${curNum}" min="1" placeholder="Amount" oninput="window.eventsModule.updateLivePreview()">
        <div class="evt-quick-inc-btns">
          <button type="button" class="evt-btn-chip" onclick="window.eventsModule.incRewardAmount('${rowId}', 50)">+50</button>
          <button type="button" class="evt-btn-chip" onclick="window.eventsModule.incRewardAmount('${rowId}', 500)">+500</button>
        </div>
      </div>
      <div class="evt-rew-del-col">
        <button type="button" class="evt-btn-del-row" onclick="window.eventsModule.removeRewardRow('${rowId}')" title="Remove reward">
          ${SVG_ICONS.trash}
        </button>
      </div>`;

    container.appendChild(row);
    updateLivePreview();
  }

  function removeRewardRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
      row.remove();
      updateLivePreview();
    }
  }

  function incRewardAmount(rowId, delta) {
    const row = document.getElementById(rowId);
    if (!row) return;
    const numInput = row.querySelector('.evt-rew-num');
    if (numInput) {
      numInput.value = Math.max(1, (Number(numInput.value) || 0) + delta);
      updateLivePreview();
    }
  }

  function onRewardTypeChange(rowId, typeStr) {
    const row = document.getElementById(rowId);
    if (!row) return;
    const type = Number(typeStr);
    const itemCol = row.querySelector('.evt-rew-item-col');
    const icoSpan = row.querySelector('.evt-rew-preview-ico');
    if (itemCol) itemCol.style.display = type === 1 ? '' : 'none';
    if (icoSpan) icoSpan.innerHTML = getRewardIcon(type);
    updateLivePreview();
  }

  function onPresetSelect(rowId, presetVal) {
    if (!presetVal) return;
    const row = document.getElementById(rowId);
    if (!row) return;
    const idInput = row.querySelector('.evt-rew-item-id');
    if (idInput) {
      idInput.value = presetVal;
      updateLivePreview();
    }
  }

  function getRewardIcon(type) {
    if (type === 3) return SVG_ICONS.gem;
    if (type === 2) return SVG_ICONS.gold;
    if (type === 6) return SVG_ICONS.activeness;
    if (type === 5) return SVG_ICONS.exp;
    return SVG_ICONS.item;
  }

  function getCollectedRewards() {
    const list = [];
    document.querySelectorAll('.evt-reward-edit-row').forEach(row => {
      const typeSelect = row.querySelector('.evt-rew-type-select');
      const numInput = row.querySelector('.evt-rew-num');
      const itemInput = row.querySelector('.evt-rew-item-id');

      if (typeSelect && numInput) {
        const type = Number(typeSelect.value);
        const count = Math.max(1, Number(numInput.value) || 1);
        const itemId = type === 1 ? (Number(itemInput ? itemInput.value : 0) || 0) : 0;
        list.push({
          award_type: type,
          award_id: itemId,
          award_num: count
        });
      }
    });
    return list;
  }

  function updateLivePreview() {
    const previewContainer = document.getElementById('bld-card-preview-target');
    if (!previewContainer) return;

    const id = Number(getFieldValue('bld-id') || 1001);
    const title = getFieldValue('bld-title') || 'Play 1 Classic Match';
    const desc = getFieldValue('bld-desc') || 'Drop into Bermuda and survive in Classic or Ranked mode.';
    const context = getFieldValue('bld-context') || 'Match Bonus';
    const tableType = Number(getFieldValue('bld-table-type') || 1);
    const tag = Number(getFieldValue('bld-tag') || 0);
    const condVal = Number(getFieldValue('bld-condition-val') || 1);
    const showProgress = getFieldChecked('bld-show-progress');
    const bannerUrl = getFieldValue('bld-banner-main') || '/banners/activity_banner.png';
    const rewards = getCollectedRewards();

    const tableInfo = TABLE_TYPES[tableType] || { label: 'EVENT', badgeClass: 'badge-cyan' };
    const tagInfo = TAG_TYPES[tag] || { label: '', class: '' };

    const renderedRewards = rewards.map(r => renderRewardPill(r)).join('');

    previewContainer.innerHTML = `
      <div class="evt-game-preview-card">
        <div class="evt-preview-banner-wrap">
          <img src="${escapeHtml(bannerUrl)}" class="evt-preview-banner-img" alt="Banner" onerror="this.src='/banners/activity_banner.png'">
          <div class="evt-preview-badges-overlay">
            <span class="evt-pill ${tableInfo.badgeClass}">${tableInfo.label}</span>
            <span class="evt-pill badge-id">#${id}</span>
            ${tagInfo.label ? `<span class="evt-pill ${tagInfo.class}">${tagInfo.label}</span>` : ''}
          </div>
        </div>
        <div class="evt-preview-content">
          <div class="evt-preview-header">
            <h3 class="evt-preview-title">${escapeHtml(title)}</h3>
            ${context ? `<span class="evt-preview-context">${escapeHtml(context)}</span>` : ''}
          </div>
          <p class="evt-preview-desc">${escapeHtml(desc)}</p>

          <div class="evt-preview-progress-box">
            <div class="evt-preview-task">
              <span class="evt-task-name">${SVG_ICONS.target} Target Condition:</span>
              <span class="evt-task-stat">${condVal} Required</span>
            </div>
            ${showProgress ? `
              <div class="evt-sim-progress">
                <div class="evt-sim-bar" style="width: 25%;"></div>
                <span class="evt-sim-text">0 / ${condVal}</span>
              </div>
            ` : ''}
          </div>

          <div class="evt-preview-rewards-box">
            <div class="evt-preview-rew-heading">Rewards:</div>
            <div class="evt-preview-rew-list">
              ${renderedRewards || '<span class="evt-no-rewards">No rewards specified</span>'}
            </div>
          </div>

          <div class="evt-preview-btn-mock">
            <button class="evt-btn-claim-mock" disabled>CLAIM</button>
          </div>
        </div>
      </div>`;

    // Also update raw JSON viewer if open
    const jsonOutput = document.getElementById('bld-json-output');
    if (jsonOutput) {
      const payload = assembleEventPayload();
      jsonOutput.textContent = JSON.stringify(payload, null, 2);
    }
  }

  function assembleEventPayload() {
    return {
      id: Number(getFieldValue('bld-id')),
      activity_id: Number(getFieldValue('bld-id')),
      enabled: getFieldChecked('bld-enabled'),
      act_title: getFieldValue('bld-title').trim(),
      act_text: getFieldValue('bld-desc').trim(),
      award_context: getFieldValue('bld-context').trim(),
      table_type: Number(getFieldValue('bld-table-type')),
      act_tag: Number(getFieldValue('bld-tag')),
      sort_id: Number(getFieldValue('bld-sort') || 1),
      group_id: Number(getFieldValue('bld-group') || 1),
      cdt_value: Number(getFieldValue('bld-condition-val') || 1),
      is_process_show: getFieldChecked('bld-show-progress') ? 1 : 0,
      activity_type: Number(getFieldValue('bld-activity-type') || 0),
      gos_pos: Number(getFieldValue('bld-gos-pos') || 0),
      image_url: getFieldValue('bld-banner-main').trim(),
      image_url_for_lobby: getFieldValue('bld-banner-lobby').trim(),
      start_time: Number(getFieldValue('bld-start-time') || Math.floor(Date.now() / 1000)),
      end_time: Number(getFieldValue('bld-end-time') || Math.floor(Date.now() / 1000) + (30 * 86400)),
      awards: getCollectedRewards()
    };
  }

  async function saveEvent(saveAsNew = false) {
    const payload = assembleEventPayload();

    if (!payload.id || payload.id <= 0) {
      showToast('Event ID must be a positive integer', 'error');
      return;
    }
    if (!payload.act_title) {
      showToast('Event Title is required', 'error');
      return;
    }
    if (payload.awards.length === 0) {
      showToast('Please add at least one reward', 'error');
      return;
    }

    if (saveAsNew) {
      payload.id = getNextAvailableId();
      payload.activity_id = payload.id;
    }

    const res = await apiPost('/api/dashboard/cms/upsert', {
      category: 'events',
      item: payload
    });

    if (res && res.ok) {
      showToast(`Event #${payload.id} successfully saved & deployed`, 'success');
      await loadEventsData();
      switchEventsTab('list');
    }
  }

  // ---------------------------------------------------------------------------
  // TAB 3: Bingo & Bonus Matrix
  // ---------------------------------------------------------------------------
  function renderBingoMatrix() {
    const container = document.getElementById('bingo-matrix-grid');
    if (!container) return;

    // Bingo cells are IDs 4001..4009
    const bingoCells = [];
    for (let cid = 4001; cid <= 4009; cid++) {
      const found = eventsState.events.find(e => e.id === cid) || {
        id: cid,
        act_title: `Bingo Cell #${cid - 4000}`,
        act_text: 'Flip this card to complete a Bingo line!',
        cdt_value: 1,
        enabled: true,
        awards: [{ award_type: 2, award_id: 0, award_num: 500 }]
      };
      bingoCells.push(found);
    }

    container.innerHTML = bingoCells.map((cell, idx) => {
      const award = (cell.awards && cell.awards[0]) || { award_type: 2, award_num: 500 };
      const pill = renderRewardPill(award);
      return `
        <div class="evt-bingo-cell ${cell.enabled ? '' : 'is-disabled'}" data-cell-id="${cell.id}">
          <div class="evt-bingo-header">
            <span class="evt-bingo-num">${idx + 1}</span>
            <span class="evt-pill badge-id">#${cell.id}</span>
            <label class="evt-switch evt-switch-sm" title="Toggle Cell Active">
              <input type="checkbox" ${cell.enabled ? 'checked' : ''} onchange="window.eventsModule.toggleEvent(${cell.id}, this.checked)">
              <span class="evt-slider"></span>
            </label>
          </div>
          <div class="evt-bingo-title">${escapeHtml(cell.act_title)}</div>
          <div class="evt-bingo-reward-wrap">
            ${pill}
          </div>
          <button class="evt-btn evt-btn-sm evt-btn-secondary" style="margin-top:8px; width:100%;" onclick="window.eventsModule.editEvent(${cell.id})">
            ${SVG_ICONS.edit}<span>Edit Reward</span>
          </button>
        </div>`;
    }).join('');

    renderBonusEventsList();
  }

  function renderBonusEventsList() {
    const bonusContainer = document.getElementById('bonus-events-list');
    if (!bonusContainer) return;

    if (eventsState.bonusEvents.length === 0) {
      bonusContainer.innerHTML = '<div class="evt-empty-desc">No bonus multiplier events configured.</div>';
      return;
    }

    bonusContainer.innerHTML = eventsState.bonusEvents.map(b => `
      <div class="evt-bonus-row">
        <div class="evt-bonus-info">
          <span class="evt-bonus-name">${escapeHtml(b.name || 'Bonus Event')}</span>
          <span class="evt-bonus-sub">Type: ${b.bonus_type || 1} &bull; Mult: ${b.multiplier || '2x'}</span>
        </div>
        <label class="evt-switch">
          <input type="checkbox" ${b.enabled ? 'checked' : ''} onchange="window.eventsModule.toggleBonusEvent(${b.id}, this.checked)">
          <span class="evt-slider"></span>
        </label>
      </div>
    `).join('');
  }

  // ---------------------------------------------------------------------------
  // Action Handlers
  // ---------------------------------------------------------------------------
  async function toggleEvent(eventId, isChecked) {
    const res = await apiPost('/api/dashboard/cms/toggle', {
      category: 'events',
      id: eventId,
      enabled: isChecked
    });
    if (res && res.ok) {
      showToast(`Event #${eventId} ${isChecked ? 'activated' : 'paused'}`, 'info');
      // Update local state item
      const item = eventsState.events.find(e => e.id === Number(eventId));
      if (item) item.enabled = isChecked;
      updateHeaderCounts();
    }
  }

  async function toggleBonusEvent(bonusId, isChecked) {
    const res = await apiPost('/api/dashboard/cms/toggle', {
      category: 'bonus_events',
      id: bonusId,
      enabled: isChecked
    });
    if (res && res.ok) {
      showToast(`Bonus #${bonusId} updated`, 'info');
    }
  }

  async function deleteEvent(eventId) {
    if (!confirm(`Are you sure you want to delete Event #${eventId}? This cannot be undone.`)) {
      return;
    }
    const res = await apiPost('/api/dashboard/cms/delete', {
      category: 'events',
      id: eventId
    });
    if (res && res.ok) {
      showToast(`Event #${eventId} deleted`, 'info');
      await loadEventsData();
    }
  }

  async function duplicateEvent(eventId) {
    const orig = eventsState.events.find(e => e.id === Number(eventId));
    if (!orig) return;
    const newId = getNextAvailableId();
    const copy = JSON.parse(JSON.stringify(orig));
    copy.id = newId;
    copy.activity_id = newId;
    copy.act_title = `${copy.act_title || 'Event'} (Copy)`;

    const res = await apiPost('/api/dashboard/cms/upsert', {
      category: 'events',
      item: copy
    });
    if (res && res.ok) {
      showToast(`Duplicated to new Event #${newId}`, 'success');
      await loadEventsData();
      openBuilderForEdit(newId);
    }
  }

  async function resetEventsDefault() {
    if (!confirm('Reset all Events & Quests to factory seed? Custom events will be replaced.')) {
      return;
    }
    const res = await apiPost('/api/dashboard/cms/reset', { category: 'events' });
    if (res && res.ok) {
      showToast('Events successfully reset to default', 'success');
      await loadEventsData();
    }
  }

  function setPresetSchedule(days) {
    const now = Math.floor(Date.now() / 1000);
    setFieldValue('bld-start-time', now);
    setFieldValue('bld-end-time', now + (days * 86400));
    updateLivePreview();
    showToast(`Schedule set to ${days} days from now`, 'info');
  }

  function populateBannerDropdowns() {
    const pickerMain = document.getElementById('bld-banner-main-picker');
    const pickerLobby = document.getElementById('bld-banner-lobby-picker');
    if (!pickerMain && !pickerLobby) return;

    const options = eventsState.banners.map(b => `<option value="${b.url}">${b.name}</option>`).join('');

    if (pickerMain) {
      pickerMain.innerHTML = `<option value="">Choose server banner...</option>` + options;
      pickerMain.onchange = () => {
        if (pickerMain.value) {
          setFieldValue('bld-banner-main', pickerMain.value);
          updateLivePreview();
        }
      };
    }
    if (pickerLobby) {
      pickerLobby.innerHTML = `<option value="">Choose server banner...</option>` + options;
      pickerLobby.onchange = () => {
        if (pickerLobby.value) {
          setFieldValue('bld-banner-lobby', pickerLobby.value);
          updateLivePreview();
        }
      };
    }
  }

  // Helper field accessors
  function getFieldValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
  }
  function setFieldValue(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
  }
  function getFieldChecked(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
  }
  function setFieldChecked(id, val) {
    const el = document.getElementById(id);
    if (el) el.checked = Boolean(val);
  }

  // ---------------------------------------------------------------------------
  // Public Interface & Initializer
  // ---------------------------------------------------------------------------
  window.eventsModule = {
    init: function () {
      console.log('[Events] Initializing module...');
      loadEventsData();

      // Hook search and filters
      const searchInput = document.getElementById('evt-search-input');
      if (searchInput) {
        searchInput.oninput = (e) => {
          eventsState.searchQuery = e.target.value.trim();
          renderEventsList();
        };
      }

      const sortSelect = document.getElementById('evt-sort-select');
      if (sortSelect) {
        sortSelect.onchange = (e) => {
          eventsState.sortBy = e.target.value;
          renderEventsList();
        };
      }

      const statusSelect = document.getElementById('evt-status-filter');
      if (statusSelect) {
        statusSelect.onchange = (e) => {
          eventsState.statusFilter = e.target.value;
          renderEventsList();
        };
      }

      // Filter pills
      document.querySelectorAll('.evt-filter-pill').forEach(pill => {
        pill.onclick = () => {
          document.querySelectorAll('.evt-filter-pill').forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          eventsState.activeFilter = pill.dataset.cat;
          renderEventsList();
        };
      });

      // Hook builder live update inputs
      const builderInputs = [
        'bld-id', 'bld-title', 'bld-desc', 'bld-context', 'bld-table-type',
        'bld-tag', 'bld-condition-val', 'bld-show-progress', 'bld-banner-main'
      ];
      builderInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.addEventListener('input', updateLivePreview);
          el.addEventListener('change', updateLivePreview);
        }
      });
    },

    switchTab: switchEventsTab,
    createNewEvent: openBuilderForNew,
    editEvent: openBuilderForEdit,
    duplicateEvent: duplicateEvent,
    deleteEvent: deleteEvent,
    toggleEvent: toggleEvent,
    toggleBonusEvent: toggleBonusEvent,
    resetDefault: resetEventsDefault,
    saveEvent: saveEvent,
    addRewardRow: addRewardRow,
    removeRewardRow: removeRewardRow,
    incRewardAmount: incRewardAmount,
    onRewardTypeChange: onRewardTypeChange,
    onPresetSelect: onPresetSelect,
    setSchedule: setPresetSchedule,
    updateLivePreview: updateLivePreview,
    reload: loadEventsData,
    toggleJsonInspector: function () {
      const el = document.getElementById('bld-json-panel');
      if (el) el.classList.toggle('hide');
    }
  };

  // Auto-init if DOM is already parsed
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.eventsModule.init);
  } else {
    window.eventsModule.init();
  }

})();
