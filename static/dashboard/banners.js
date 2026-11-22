/**
 * India V1 1.39 - Banners & Ads Component Engine (banners.js)
 * High-performance, viewport-fitted UI controller for:
 *   - Lobby Billboard Carousel Ads (with live 1.39 simulator)
 *   - Login Splash Popups (with cache-busting force-show & preview)
 *   - Drag-and-drop Image Asset Uploader & Gallery
 *   - Top Marquee Ticker (live animated strip)
 *   - In-game News & Announcements (modal viewer preview)
 *
 * Compliance: Strictly ZERO emojis. Clean typography and SVG line icons.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.BannersSection = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Navigation types reverse-engineered from Free Fire 1.39 IL2CPP
  const NAV_DESTINATIONS = [
    { id: 0, label: '0 - None / Dismiss', desc: 'Closes dialog or does nothing' },
    { id: 3, label: '3 - Store / Mall', desc: 'Mall tab via sub_go_pos (e.g. 1,6 Bundles)' },
    { id: 7, label: '7 - Events & Activities', desc: 'Event tab (Daily, Festival, Bingo, Tokens)' },
    { id: 15, label: '15 - Luck Royale / Gacha', desc: 'Gold, Diamond & Weapon Royale spins' },
    { id: 114, label: '114 - Elite Pass', desc: 'Elite Pass controller & missions' },
    { id: 13, label: '13 - Character Profile', desc: 'Character selection & skills' },
    { id: 4, label: '4 - Vault / Inventory', desc: 'Costumes, skins & fashion items' },
    { id: 26, label: '26 - Pet System', desc: 'Pet selection & abilities' },
    { id: 2, label: '2 - Squad Lobby', desc: 'Duo or Squad group matchmaking' },
    { id: 5, label: '5 - Clan / Guild', desc: 'Clan lobby & leaderboards' },
    { id: 6, label: '6 - Recharge / Top-Up', desc: 'Diamond purchase & rebate offers' },
    { id: 8, label: '8 - Friends List', desc: 'Friend requests & online status' },
    { id: 9, label: '9 - Loadout', desc: 'Battle item loadout & airdrops' },
    { id: 99, label: '99 - External Web URL', desc: 'Opens gos_url in embedded or native browser' },
  ];

  // Internal state
  const state = {
    cms: {
      adverts: [],
      splashes: [],
      marquees: [],
      announcements: [],
      events: []
    },
    banners: [],
    activeTab: 'billboard',
    activeAdIndex: 0,
    carouselTimer: null,
    carouselPlaying: true,
    editingAdId: null,
    editingSplashId: null,
    editingMqId: null,
    editingNewsId: null,
    activeNewsPreviewId: null,
    activeSplashPreviewId: null,
    searchBannerQuery: '',
    sortBannersBy: 'name',
    isLoading: false,
    brandingSlots: [],
    brandingFilter: 'all'
  };

  // SVG Icons helper (Strictly no emojis)
  const ICONS = {
    check: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    x: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    plus: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    edit: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
    trash: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    bolt: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    link: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    copy: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    refresh: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
    upload: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    chevronLeft: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>',
    chevronRight: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
    play: '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    pause: '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',
    image: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
    external: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'
  };

  // Toast Notification
  function showToast(message, type = 'info') {
    let toast = document.getElementById('b-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'b-toast';
      toast.className = 'b-toast';
      document.body.appendChild(toast);
    }
    toast.className = `b-toast b-toast-${type} show`;
    toast.innerHTML = `<span class="b-toast-icon">${type === 'success' ? ICONS.check : (type === 'error' ? ICONS.x : ICONS.bolt)}</span><span class="b-toast-msg">${escapeHtml(message)}</span>`;
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.remove('show');
    }, 2800);
  }

  // Escape HTML string
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // HTTP API Helpers
  async function apiGet(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      console.error('[Banners] apiGet error:', path, err);
      showToast(`Network error: ${err.message}`, 'error');
      return null;
    }
  }

  async function apiPost(path, body) {
    try {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      });
      const data = await res.json();
      if (!res.ok || (data && data.ok === false)) {
        throw new Error((data && data.error) || `HTTP ${res.status}`);
      }
      return data;
    } catch (err) {
      console.error('[Banners] apiPost error:', path, err);
      showToast(`Action failed: ${err.message}`, 'error');
      return null;
    }
  }

  // Format bytes
  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // Format timestamp to date string
  function formatTimestamp(ts) {
    if (!ts) return '-';
    try {
      const d = new Date(ts * 1000);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return String(ts);
    }
  }

  // Lookup destination name
  function getDestLabel(goPos) {
    const dest = NAV_DESTINATIONS.find(d => d.id === Number(goPos));
    return dest ? dest.label : `Custom [${goPos}]`;
  }

  // Tab switching
  function switchSubTab(tabName) {
    state.activeTab = tabName;
    document.querySelectorAll('.b-subtab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
    });
    document.querySelectorAll('.b-subtab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === `b-pane-${tabName}`);
    });

    if (tabName === 'billboard') {
      startCarousel();
      renderAdverts();
    } else {
      stopCarousel();
    }

    if (tabName === 'splashes') {
      renderSplashes();
    } else if (tabName === 'assets') {
      renderAssets();
    } else if (tabName === 'marquee-news') {
      renderMarquees();
      renderAnnouncements();
    } else if (tabName === 'boot-branding') {
      loadBranding();
    }
  }

  // =========================================================================
  // SUB-TAB 1: LOBBY BILLBOARD CAROUSEL ADS
  // =========================================================================

  function renderAdverts() {
    renderAdvertsTable();
    renderBillboardSimulator();
  }

  function renderAdvertsTable() {
    const container = document.getElementById('b-adverts-table-body');
    if (!container) return;

    const ads = state.cms.adverts || [];
    if (!ads.length) {
      container.innerHTML = `<tr><td colspan="6" class="b-empty-row">No billboard ad spots configured. Click "+ New Ad Spot" to create one.</td></tr>`;
      return;
    }

    // Sort by sort_id or id
    const sorted = [...ads].sort((a, b) => (a.sort_id || a.id) - (b.sort_id || b.id));

    container.innerHTML = sorted.map((ad, idx) => {
      const destName = getDestLabel(ad.go_pos);
      const isSelected = state.editingAdId === ad.id;
      const cleanImg = (ad.advertisment_url || '').split('?')[0];

      return `
        <tr class="b-table-row ${isSelected ? 'row-selected' : ''}" data-ad-id="${ad.id}">
          <td class="col-rank">#${ad.sort_id || (idx + 1)}</td>
          <td class="col-thumb">
            <div class="b-thumb-box">
              <img src="${escapeHtml(ad.advertisment_url || '/banners/lobby_ad_1.png')}" alt="Ad" onerror="this.src='/banners/lobby_ad_1.png'">
            </div>
          </td>
          <td class="col-details">
            <div class="b-item-primary">Ad Spot #${ad.id}</div>
            <div class="b-item-secondary monospace" title="${escapeHtml(cleanImg)}">${escapeHtml(cleanImg || 'None')}</div>
          </td>
          <td class="col-dest">
            <span class="b-badge b-badge-cyan" title="Jump Target: go_pos=${ad.go_pos}">${escapeHtml(destName)}</span>
            ${ad.sub_go_pos ? `<span class="b-badge b-badge-dim" title="sub_go_pos">${escapeHtml(ad.sub_go_pos)}</span>` : ''}
          </td>
          <td class="col-status">
            <button class="b-toggle-btn ${ad.enabled ? 'active' : ''}" onclick="BannersSection.toggleAd(${ad.id})" title="Click to toggle active state">
              <span class="b-toggle-knob"></span>
              <span class="b-toggle-text">${ad.enabled ? 'Active' : 'Disabled'}</span>
            </button>
          </td>
          <td class="col-actions">
            <div class="b-actions-cluster">
              <button class="b-btn-icon" onclick="BannersSection.editAd(${ad.id})" title="Edit Ad Spot">${ICONS.edit}</button>
              <button class="b-btn-icon text-danger" onclick="BannersSection.deleteAd(${ad.id})" title="Delete Ad Spot">${ICONS.trash}</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  function renderBillboardSimulator() {
    const simContainer = document.getElementById('b-billboard-screen');
    const dotsContainer = document.getElementById('b-billboard-dots');
    if (!simContainer || !dotsContainer) return;

    const ads = (state.cms.adverts || []).filter(a => a.enabled);
    if (!ads.length) {
      simContainer.innerHTML = `
        <div class="b-billboard-empty">
          <div class="b-billboard-empty-icon">${ICONS.image}</div>
          <div>No active billboard ads in rotation</div>
        </div>
      `;
      dotsContainer.innerHTML = '';
      return;
    }

    if (state.activeAdIndex >= ads.length) {
      state.activeAdIndex = 0;
    }

    const currentAd = ads[state.activeAdIndex];
    const destName = getDestLabel(currentAd.go_pos);

    simContainer.innerHTML = `
      <div class="b-billboard-slide" onclick="BannersSection.simulateAdClick(${currentAd.id})">
        <img src="${escapeHtml(currentAd.advertisment_url)}" class="b-billboard-img" alt="Billboard Ad #${currentAd.id}">
        <div class="b-billboard-overlay">
          <div class="b-billboard-tag">Ad Spot #${currentAd.id}</div>
          <div class="b-billboard-jump-pill">${escapeHtml(destName)} ${ICONS.external}</div>
        </div>
      </div>
    `;

    dotsContainer.innerHTML = ads.map((ad, idx) => `
      <button class="b-dot ${idx === state.activeAdIndex ? 'active' : ''}" onclick="BannersSection.setAdIndex(${idx})" title="Ad #${ad.id}"></button>
    `).join('');
  }

  function startCarousel() {
    stopCarousel();
    if (!state.carouselPlaying) return;
    state.carouselTimer = setInterval(() => {
      const activeAds = (state.cms.adverts || []).filter(a => a.enabled);
      if (activeAds.length > 1) {
        state.activeAdIndex = (state.activeAdIndex + 1) % activeAds.length;
        renderBillboardSimulator();
      }
    }, 4000);
  }

  function stopCarousel() {
    if (state.carouselTimer) {
      clearInterval(state.carouselTimer);
      state.carouselTimer = null;
    }
  }

  function toggleCarouselPlay() {
    state.carouselPlaying = !state.carouselPlaying;
    const btn = document.getElementById('b-carousel-play-btn');
    if (btn) {
      btn.innerHTML = state.carouselPlaying ? ICONS.pause : ICONS.play;
      btn.setAttribute('title', state.carouselPlaying ? 'Pause Carousel' : 'Play Carousel');
    }
    if (state.carouselPlaying) {
      startCarousel();
    } else {
      stopCarousel();
    }
  }

  function nextAd() {
    const activeAds = (state.cms.adverts || []).filter(a => a.enabled);
    if (!activeAds.length) return;
    state.activeAdIndex = (state.activeAdIndex + 1) % activeAds.length;
    renderBillboardSimulator();
  }

  function prevAd() {
    const activeAds = (state.cms.adverts || []).filter(a => a.enabled);
    if (!activeAds.length) return;
    state.activeAdIndex = (state.activeAdIndex - 1 + activeAds.length) % activeAds.length;
    renderBillboardSimulator();
  }

  function setAdIndex(idx) {
    state.activeAdIndex = idx;
    renderBillboardSimulator();
  }

  function simulateAdClick(adId) {
    const ad = (state.cms.adverts || []).find(a => a.id === adId);
    if (!ad) return;
    const dest = NAV_DESTINATIONS.find(d => d.id === Number(ad.go_pos));
    const label = dest ? dest.label : `Destination ${ad.go_pos}`;
    showToast(`Simulation: Player tapped Ad #${ad.id} -> Navigates to: ${label} (sub: "${ad.sub_go_pos || 'default'}")`, 'info');
  }

  function openAdDrawer(ad = null) {
    const drawer = document.getElementById('b-ad-drawer');
    const form = document.getElementById('b-ad-form');
    if (!drawer || !form) return;

    state.editingAdId = ad ? ad.id : null;
    const titleEl = document.getElementById('b-ad-drawer-title');
    if (titleEl) {
      titleEl.textContent = ad ? `Edit Billboard Ad #${ad.id}` : 'Create New Billboard Ad';
    }

    document.getElementById('b-ad-input-id').value = ad ? ad.id : (getNextId(state.cms.adverts));
    document.getElementById('b-ad-input-url').value = ad ? (ad.advertisment_url || '') : '';
    document.getElementById('b-ad-input-sort').value = ad ? (ad.sort_id || 1) : ((state.cms.adverts || []).length + 1);
    document.getElementById('b-ad-input-sub').value = ad ? (ad.sub_go_pos || '') : '';
    document.getElementById('b-ad-input-enabled').checked = ad ? !!ad.enabled : true;

    // Populate destination dropdown
    const select = document.getElementById('b-ad-select-pos');
    select.innerHTML = NAV_DESTINATIONS.map(d => `
      <option value="${d.id}" ${ad && Number(ad.go_pos) === d.id ? 'selected' : ''}>${escapeHtml(d.label)}</option>
    `).join('');

    // Populate banner picker dropdown
    populateBannerPicker('b-ad-picker', ad ? ad.advertisment_url : '');

    updateAdImgPreview();
    drawer.classList.add('open');
    renderAdvertsTable();
  }

  function closeAdDrawer() {
    const drawer = document.getElementById('b-ad-drawer');
    if (drawer) drawer.classList.remove('open');
    state.editingAdId = null;
    renderAdvertsTable();
  }

  function updateAdImgPreview() {
    const input = document.getElementById('b-ad-input-url');
    const preview = document.getElementById('b-ad-img-preview');
    if (input && preview) {
      preview.src = input.value || '/banners/lobby_ad_1.png';
    }
  }

  async function saveAd(event) {
    if (event) event.preventDefault();
    const id = Number(document.getElementById('b-ad-input-id').value);
    const url = document.getElementById('b-ad-input-url').value.trim();
    const goPos = Number(document.getElementById('b-ad-select-pos').value);
    const subGoPos = document.getElementById('b-ad-input-sub').value.trim();
    const sortId = Number(document.getElementById('b-ad-input-sort').value) || 1;
    const enabled = document.getElementById('b-ad-input-enabled').checked;

    if (!url) {
      showToast('Please specify a banner image URL', 'error');
      return;
    }

    const existing = (state.cms.adverts || []).find(a => a.id === id) || {};
    const item = {
      ...existing,
      id,
      advertisment_url: url,
      go_pos: goPos,
      sub_go_pos: subGoPos,
      sort_id: sortId,
      enabled,
      type: 11, // Lobby Ad Type
      language: existing.language || 'en'
    };

    const res = await apiPost('/api/dashboard/cms/upsert', {
      category: 'adverts',
      item
    });

    if (res && res.ok) {
      showToast(`Ad spot #${id} saved successfully!`, 'success');
      closeAdDrawer();
      await loadCms();
      renderAdverts();
    }
  }

  async function toggleAd(adId) {
    const ad = (state.cms.adverts || []).find(a => a.id === adId);
    if (!ad) return;
    const newStatus = !ad.enabled;

    const res = await apiPost('/api/dashboard/cms/toggle', {
      category: 'adverts',
      id: adId,
      enabled: newStatus
    });

    if (res && res.ok) {
      ad.enabled = newStatus;
      showToast(`Ad spot #${adId} is now ${newStatus ? 'active' : 'disabled'}`, 'success');
      renderAdverts();
    }
  }

  async function deleteAd(adId) {
    if (!confirm(`Are you sure you want to delete Billboard Ad spot #${adId}?`)) return;
    const res = await apiPost('/api/dashboard/cms/delete', {
      category: 'adverts',
      id: adId
    });

    if (res && res.ok) {
      showToast(`Deleted Ad spot #${adId}`, 'success');
      if (state.editingAdId === adId) closeAdDrawer();
      await loadCms();
      renderAdverts();
    }
  }

  // =========================================================================
  // SUB-TAB 2: LOGIN SPLASH POPUPS WITH FORCE-SHOW
  // =========================================================================

  function renderSplashes() {
    renderSplashesList();
    renderSplashSimulator();
  }

  function renderSplashesList() {
    const container = document.getElementById('b-splashes-list');
    if (!container) return;

    const splashes = state.cms.splashes || [];
    if (!splashes.length) {
      container.innerHTML = `<div class="b-empty-card">No login splash popups registered. Click "+ New Splash" to add one.</div>`;
      return;
    }

    container.innerHTML = splashes.map(sp => {
      const isSelected = state.activeSplashPreviewId === sp.id || (state.activeSplashPreviewId === null && sp === splashes[0]);
      const destName = getDestLabel(sp.gos_pos);
      const cleanImg = (sp.image_url || '').split('?')[0];

      return `
        <div class="b-splash-card ${isSelected ? 'selected' : ''}" onclick="BannersSection.selectSplashPreview(${sp.id})">
          <div class="b-splash-card-left">
            <div class="b-splash-thumb">
              <img src="${escapeHtml(sp.image_url || '/banners/splash_welcome.png')}" alt="Splash" onerror="this.src='/banners/splash_welcome.png'">
            </div>
            <div class="b-splash-info">
              <div class="b-splash-header-row">
                <span class="b-splash-title">${escapeHtml(sp.name || `Splash #${sp.id}`)}</span>
                <span class="b-badge b-badge-gold">v${sp.version || 1}</span>
              </div>
              <div class="b-splash-sub monospace">${escapeHtml(cleanImg)}</div>
              <div class="b-splash-meta">
                <span class="b-badge b-badge-cyan">${escapeHtml(destName)}</span>
                ${sp.gos_url ? `<span class="b-badge b-badge-dim monospace" title="${escapeHtml(sp.gos_url)}">URL</span>` : ''}
              </div>
            </div>
          </div>
          <div class="b-splash-card-right" onclick="event.stopPropagation()">
            <button class="b-toggle-btn ${sp.enabled ? 'active' : ''}" onclick="BannersSection.toggleSplash(${sp.id})" title="Toggle Splash Popup">
              <span class="b-toggle-knob"></span>
              <span class="b-toggle-text">${sp.enabled ? 'Active' : 'Disabled'}</span>
            </button>
            <div class="b-actions-cluster">
              <button class="b-btn-secondary b-btn-xs" onclick="BannersSection.bumpSingleSplash(${sp.id})" title="Increment version counter to force client re-download and re-popup">
                ${ICONS.bolt} Bump v${(sp.version || 1) + 1}
              </button>
              <button class="b-btn-icon" onclick="BannersSection.editSplash(${sp.id})" title="Edit Splash">${ICONS.edit}</button>
              <button class="b-btn-icon text-danger" onclick="BannersSection.deleteSplash(${sp.id})" title="Delete Splash">${ICONS.trash}</button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderSplashSimulator() {
    const frame = document.getElementById('b-splash-sim-frame');
    if (!frame) return;

    const splashes = state.cms.splashes || [];
    if (!splashes.length) {
      frame.innerHTML = `<div class="b-empty-screen">No splashes to preview</div>`;
      return;
    }

    let current = splashes.find(s => s.id === state.activeSplashPreviewId);
    if (!current) {
      current = splashes[0];
      state.activeSplashPreviewId = current.id;
    }

    const destName = getDestLabel(current.gos_pos);

    frame.innerHTML = `
      <div class="b-splash-modal-overlay">
        <div class="b-splash-modal-box">
          <div class="b-splash-modal-header">
            <span class="b-splash-modal-tag">${escapeHtml(current.name || 'Special Announcement')}</span>
            <button class="b-splash-modal-close" onclick="BannersSection.simulateSplashClose()">${ICONS.x}</button>
          </div>
          <div class="b-splash-modal-body">
            <img src="${escapeHtml(current.image_url || '/banners/splash_welcome.png')}" alt="Splash Banner" class="b-splash-modal-img">
          </div>
          <div class="b-splash-modal-footer">
            <label class="b-splash-modal-chk">
              <input type="checkbox" checked disabled>
              <span>Do not show again today (Unity Cache-Key: hash+v${current.version || 1})</span>
            </label>
            <button class="b-btn-primary b-btn-sm" onclick="BannersSection.simulateSplashAction(${current.id})">
              <span>View Now</span> ${ICONS.external}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function selectSplashPreview(id) {
    state.activeSplashPreviewId = id;
    renderSplashes();
  }

  function simulateSplashClose() {
    showToast('Simulation: Player dismissed splash popup dialog', 'info');
  }

  function simulateSplashAction(id) {
    const sp = (state.cms.splashes || []).find(s => s.id === id);
    if (!sp) return;
    const dest = getDestLabel(sp.gos_pos);
    showToast(`Simulation: Player tapped splash action -> Navigates to ${dest}`, 'info');
  }

  async function bumpAllSplashes() {
    const res = await apiPost('/api/dashboard/cms/bump_splashes', {});
    if (res && res.ok) {
      showToast('Force-Show triggered! Incremented cache versions on all splash popups.', 'success');
      await loadCms();
      renderSplashes();
    }
  }

  async function bumpSingleSplash(id) {
    const sp = (state.cms.splashes || []).find(s => s.id === id);
    if (!sp) return;

    const item = {
      ...sp,
      id,
      enabled: sp.enabled
      // Server state.upsert_splash auto-increments version
    };

    const res = await apiPost('/api/dashboard/cms/upsert', {
      category: 'splashes',
      item
    });

    if (res && res.ok) {
      showToast(`Splash #${id} bumped to v${(sp.version || 1) + 1}! Will force display on next login.`, 'success');
      await loadCms();
      renderSplashes();
    }
  }

  function openSplashDrawer(splash = null) {
    const drawer = document.getElementById('b-splash-drawer');
    if (!drawer) return;

    state.editingSplashId = splash ? splash.id : null;
    const titleEl = document.getElementById('b-splash-drawer-title');
    if (titleEl) {
      titleEl.textContent = splash ? `Edit Login Splash #${splash.id}` : 'Create New Login Splash';
    }

    document.getElementById('b-splash-input-id').value = splash ? splash.id : (getNextId(state.cms.splashes));
    document.getElementById('b-splash-input-name').value = splash ? (splash.name || '') : '';
    document.getElementById('b-splash-input-url').value = splash ? (splash.image_url || '') : '';
    document.getElementById('b-splash-input-web').value = splash ? (splash.gos_url || '') : '';
    document.getElementById('b-splash-input-sub').value = splash ? (splash.sub_go_pos || '') : '';
    document.getElementById('b-splash-input-sort').value = splash ? (splash.sort_id || 1) : 1;
    document.getElementById('b-splash-input-browser').checked = splash ? !!splash.use_embedded_browser : true;
    document.getElementById('b-splash-input-enabled').checked = splash ? !!splash.enabled : true;

    // Populate destination dropdown
    const select = document.getElementById('b-splash-select-pos');
    select.innerHTML = NAV_DESTINATIONS.map(d => `
      <option value="${d.id}" ${splash && Number(splash.gos_pos) === d.id ? 'selected' : ''}>${escapeHtml(d.label)}</option>
    `).join('');

    // Populate banner picker
    populateBannerPicker('b-splash-picker', splash ? splash.image_url : '');

    updateSplashImgPreview();
    drawer.classList.add('open');
  }

  function closeSplashDrawer() {
    const drawer = document.getElementById('b-splash-drawer');
    if (drawer) drawer.classList.remove('open');
    state.editingSplashId = null;
  }

  function updateSplashImgPreview() {
    const input = document.getElementById('b-splash-input-url');
    const preview = document.getElementById('b-splash-img-preview');
    if (input && preview) {
      preview.src = input.value || '/banners/splash_welcome.png';
    }
  }

  async function saveSplash(event) {
    if (event) event.preventDefault();
    const id = Number(document.getElementById('b-splash-input-id').value);
    const name = document.getElementById('b-splash-input-name').value.trim() || `Splash #${id}`;
    const url = document.getElementById('b-splash-input-url').value.trim();
    const gosPos = Number(document.getElementById('b-splash-select-pos').value);
    const gosUrl = document.getElementById('b-splash-input-web').value.trim();
    const subGoPos = document.getElementById('b-splash-input-sub').value.trim();
    const sortId = Number(document.getElementById('b-splash-input-sort').value) || 1;
    const useBrowser = document.getElementById('b-splash-input-browser').checked;
    const enabled = document.getElementById('b-splash-input-enabled').checked;

    if (!url) {
      showToast('Please specify a banner image URL', 'error');
      return;
    }

    const existing = (state.cms.splashes || []).find(s => s.id === id) || {};
    const item = {
      ...existing,
      id,
      name,
      image_url: url,
      bg_img_url: url,
      gos_pos: gosPos,
      gos_url: gosUrl,
      sub_go_pos: subGoPos,
      sort_id: sortId,
      use_embedded_browser: useBrowser,
      enabled,
      language: existing.language || 'en',
      region: existing.region || 'DEFAULT'
    };

    const res = await apiPost('/api/dashboard/cms/upsert', {
      category: 'splashes',
      item
    });

    if (res && res.ok) {
      showToast(`Splash #${id} saved successfully!`, 'success');
      closeSplashDrawer();
      await loadCms();
      renderSplashes();
    }
  }

  async function toggleSplash(splashId) {
    const sp = (state.cms.splashes || []).find(s => s.id === splashId);
    if (!sp) return;
    const newStatus = !sp.enabled;

    const res = await apiPost('/api/dashboard/cms/toggle', {
      category: 'splashes',
      id: splashId,
      enabled: newStatus
    });

    if (res && res.ok) {
      sp.enabled = newStatus;
      showToast(`Splash #${splashId} is now ${newStatus ? 'active' : 'disabled'}`, 'success');
      renderSplashes();
    }
  }

  async function deleteSplash(splashId) {
    if (!confirm(`Are you sure you want to delete Splash popup #${splashId}?`)) return;
    const res = await apiPost('/api/dashboard/cms/delete', {
      category: 'splashes',
      id: splashId
    });

    if (res && res.ok) {
      showToast(`Deleted Splash #${splashId}`, 'success');
      if (state.editingSplashId === splashId) closeSplashDrawer();
      await loadCms();
      renderSplashes();
    }
  }

  // =========================================================================
  // SUB-TAB 3: BANNER ASSET MANAGER & DRAG-AND-DROP UPLOADER
  // =========================================================================

  function renderAssets() {
    renderBannersGallery();
  }

  function renderBannersGallery() {
    const container = document.getElementById('b-gallery-grid');
    const badge = document.getElementById('b-gallery-count-badge');
    if (!container) return;

    let list = [...(state.banners || [])];

    // Search filter
    if (state.searchBannerQuery) {
      const q = state.searchBannerQuery.toLowerCase();
      list = list.filter(b => b.name.toLowerCase().includes(q));
    }

    // Sort
    if (state.sortBannersBy === 'name') {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else if (state.sortBannersBy === 'size') {
      list.sort((a, b) => (b.size || 0) - (a.size || 0));
    } else if (state.sortBannersBy === 'date') {
      list.sort((a, b) => (b.modified_at || 0) - (a.modified_at || 0));
    }

    if (badge) {
      badge.textContent = `${list.length} / ${state.banners.length} Files`;
    }

    if (!list.length) {
      container.innerHTML = `
        <div class="b-gallery-empty">
          <div class="b-gallery-empty-icon">${ICONS.image}</div>
          <div class="b-gallery-empty-text">No banner image files match your query.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = list.map(b => {
      return `
        <div class="b-gallery-card">
          <div class="b-gallery-thumb-wrap" onclick="BannersSection.openPreviewModal('${escapeHtml(b.url)}', '${escapeHtml(b.name)}')">
            <img src="${escapeHtml(b.url)}" alt="${escapeHtml(b.name)}" class="b-gallery-thumb" onerror="this.src='/banners/splash_welcome.png'">
            <div class="b-gallery-thumb-overlay">Click to inspect full image</div>
          </div>
          <div class="b-gallery-info">
            <div class="b-gallery-filename monospace" title="${escapeHtml(b.name)}">${escapeHtml(b.name)}</div>
            <div class="b-gallery-sub">
              <span>${formatBytes(b.size)}</span>
              <span>${formatTimestamp(b.modified_at)}</span>
            </div>
            <div class="b-gallery-assign-row">
              <span class="b-assign-lbl">Quick Assign:</span>
              <button class="b-btn-assign" onclick="BannersSection.assignBanner('${escapeHtml(b.url)}', 'ad1')" title="Assign to Billboard Ad Spot #1">Ad 1</button>
              <button class="b-btn-assign" onclick="BannersSection.assignBanner('${escapeHtml(b.url)}', 'ad2')" title="Assign to Billboard Ad Spot #2">Ad 2</button>
              <button class="b-btn-assign" onclick="BannersSection.assignBanner('${escapeHtml(b.url)}', 'splash')" title="Assign to Login Splash Popup">Splash</button>
              <button class="b-btn-assign" onclick="BannersSection.assignBanner('${escapeHtml(b.url)}', 'news')" title="Assign to News Announcement">News</button>
            </div>
            <div class="b-gallery-card-footer">
              <button class="b-btn-secondary b-btn-xs" onclick="BannersSection.copyUrl('${escapeHtml(b.url)}')">
                ${ICONS.copy} <span>Copy URL</span>
              </button>
              <button class="b-btn-icon text-danger" onclick="BannersSection.deleteBannerFile('${escapeHtml(b.name)}')" title="Delete Asset">
                ${ICONS.trash}
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // Setup Drag-and-drop Dropzone
  function initDropzone() {
    const dropzone = document.getElementById('b-upload-dropzone');
    const fileInput = document.getElementById('b-upload-file-input');
    if (!dropzone || !fileInput) return;

    ['dragenter', 'dragover'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      }, false);
    });

    dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length) {
        uploadFiles(dt.files);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length) {
        uploadFiles(fileInput.files);
      }
    });
  }

  async function uploadFiles(fileList) {
    if (!fileList || !fileList.length) return;
    const progressEl = document.getElementById('b-upload-progress');
    const barEl = document.getElementById('b-upload-progress-bar');
    const textEl = document.getElementById('b-upload-progress-text');

    if (progressEl) progressEl.classList.add('show');

    let uploadedCount = 0;
    const total = fileList.length;

    for (let i = 0; i < total; i++) {
      const file = fileList[i];
      if (textEl) textEl.textContent = `Uploading ${file.name} (${i + 1}/${total})...`;
      if (barEl) barEl.style.width = `${Math.round(((i) / total) * 100)}%`;

      try {
        const base64 = await readFileAsBase64(file);
        const res = await apiPost('/api/dashboard/cms/upload_banner', {
          filename: file.name,
          data_base64: base64
        });

        if (res && res.ok) {
          uploadedCount++;
        }
      } catch (err) {
        console.error('Upload error for', file.name, err);
        showToast(`Failed uploading ${file.name}: ${err.message}`, 'error');
      }
    }

    if (barEl) barEl.style.width = '100%';
    if (textEl) textEl.textContent = `Completed ${uploadedCount} of ${total} files`;

    setTimeout(() => {
      if (progressEl) progressEl.classList.remove('show');
    }, 1500);

    showToast(`Successfully uploaded ${uploadedCount} image asset(s)`, 'success');
    await loadBanners();
    renderAssets();
  }

  function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result;
        const b64 = result.includes(',') ? result.split(',')[1] : result;
        resolve(b64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  async function deleteBannerFile(filename) {
    if (!confirm(`Delete image asset "${filename}" from server?`)) return;
    const res = await apiPost('/api/dashboard/cms/delete_banner', { filename });
    if (res && res.ok) {
      showToast(`Deleted ${filename}`, 'success');
      await loadBanners();
      renderAssets();
    }
  }

  function copyUrl(url) {
    navigator.clipboard.writeText(url).then(() => {
      showToast(`Copied URL: ${url}`, 'success');
    }).catch(() => {
      showToast(`URL: ${url}`, 'info');
    });
  }

  async function assignBanner(url, target) {
    if (target === 'ad1') {
      const ad = (state.cms.adverts || []).find(a => a.id === 1) || { id: 1, sort_id: 1, go_pos: 7, enabled: true };
      ad.advertisment_url = url;
      await apiPost('/api/dashboard/cms/upsert', { category: 'adverts', item: ad });
      showToast(`Assigned ${url} to Billboard Ad #1`, 'success');
      await loadCms();
      renderAdverts();
    } else if (target === 'ad2') {
      const ad = (state.cms.adverts || []).find(a => a.id === 2) || { id: 2, sort_id: 2, go_pos: 15, enabled: true };
      ad.advertisment_url = url;
      await apiPost('/api/dashboard/cms/upsert', { category: 'adverts', item: ad });
      showToast(`Assigned ${url} to Billboard Ad #2`, 'success');
      await loadCms();
      renderAdverts();
    } else if (target === 'splash') {
      const sp = (state.cms.splashes || [])[0] || { id: 1, name: 'Login Splash', gos_pos: 7, enabled: true };
      sp.image_url = url;
      sp.bg_img_url = url;
      await apiPost('/api/dashboard/cms/upsert', { category: 'splashes', item: sp });
      showToast(`Assigned ${url} to Splash Popup #${sp.id}`, 'success');
      await loadCms();
      renderSplashes();
    } else if (target === 'news') {
      const an = (state.cms.announcements || [])[0] || { id: 1, title: 'Notice', enabled: true };
      an.image_url = url;
      an.image_url_for_lobby = url;
      await apiPost('/api/dashboard/cms/upsert', { category: 'announcements', item: an });
      showToast(`Assigned ${url} to News Announcement #${an.id}`, 'success');
      await loadCms();
      renderAnnouncements();
    }
  }

  function openPreviewModal(url, name) {
    let modal = document.getElementById('b-preview-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'b-preview-modal';
      modal.className = 'b-modal-overlay';
      modal.innerHTML = `
        <div class="b-modal-card">
          <div class="b-modal-header">
            <span id="b-modal-title" class="b-modal-title"></span>
            <button class="b-btn-icon" onclick="document.getElementById('b-preview-modal').classList.remove('show')">${ICONS.x}</button>
          </div>
          <div class="b-modal-body">
            <img id="b-modal-img" src="" alt="Preview" class="b-modal-img">
          </div>
          <div class="b-modal-footer">
            <button class="b-btn-secondary b-btn-sm" onclick="BannersSection.copyUrl(document.getElementById('b-modal-img').src)">${ICONS.copy} Copy URL</button>
            <button class="b-btn-primary b-btn-sm" onclick="document.getElementById('b-preview-modal').classList.remove('show')">Done</button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    document.getElementById('b-modal-title').textContent = name || 'Image Preview';
    document.getElementById('b-modal-img').src = url;
    modal.classList.add('show');
  }

  // =========================================================================
  // SUB-TAB 4: TOP MARQUEE TICKER & NEWS ANNOUNCEMENTS
  // =========================================================================

  function renderMarquees() {
    renderMarqueeList();
    renderLiveTickerStrip();
  }

  function renderLiveTickerStrip() {
    const stripText = document.getElementById('b-ticker-stream');
    if (!stripText) return;

    const mqs = (state.cms.marquees || []).filter(m => m.enabled);
    if (!mqs.length) {
      stripText.textContent = 'NO ACTIVE MARQUEE TICKER BROADCASTS AT THIS TIME';
      return;
    }

    const merged = mqs.map(m => `[#${m.id}] ${m.content}`).join('   * * *   ');
    stripText.textContent = merged;
  }

  function renderMarqueeList() {
    const container = document.getElementById('b-marquee-list');
    if (!container) return;

    const mqs = state.cms.marquees || [];
    if (!mqs.length) {
      container.innerHTML = `<div class="b-empty-card">No marquee tickers configured.</div>`;
      return;
    }

    container.innerHTML = mqs.map(m => `
      <div class="b-mq-card">
        <div class="b-mq-info">
          <div class="b-mq-header">
            <span class="b-mq-id">Ticker #${m.id}</span>
            <span class="b-badge b-badge-cyan">${escapeHtml(getDestLabel(m.gos_pos))}</span>
          </div>
          <div class="b-mq-text">${escapeHtml(m.content || '')}</div>
        </div>
        <div class="b-mq-actions">
          <button class="b-toggle-btn ${m.enabled ? 'active' : ''}" onclick="BannersSection.toggleMarquee(${m.id})">
            <span class="b-toggle-knob"></span>
            <span class="b-toggle-text">${m.enabled ? 'Active' : 'Disabled'}</span>
          </button>
          <button class="b-btn-icon" onclick="BannersSection.editMarquee(${m.id})">${ICONS.edit}</button>
          <button class="b-btn-icon text-danger" onclick="BannersSection.deleteMarquee(${m.id})">${ICONS.trash}</button>
        </div>
      </div>
    `).join('');
  }

  function openMarqueeDrawer(mq = null) {
    const drawer = document.getElementById('b-marquee-drawer');
    if (!drawer) return;

    state.editingMqId = mq ? mq.id : null;
    document.getElementById('b-mq-input-id').value = mq ? mq.id : getNextId(state.cms.marquees);
    document.getElementById('b-mq-input-content').value = mq ? (mq.content || '') : '';
    document.getElementById('b-mq-input-enabled').checked = mq ? !!mq.enabled : true;

    const select = document.getElementById('b-mq-select-pos');
    select.innerHTML = NAV_DESTINATIONS.map(d => `
      <option value="${d.id}" ${mq && Number(mq.gos_pos) === d.id ? 'selected' : ''}>${escapeHtml(d.label)}</option>
    `).join('');

    drawer.classList.add('open');
  }

  function closeMarqueeDrawer() {
    const drawer = document.getElementById('b-marquee-drawer');
    if (drawer) drawer.classList.remove('open');
    state.editingMqId = null;
  }

  async function saveMarquee(event) {
    if (event) event.preventDefault();
    const id = Number(document.getElementById('b-mq-input-id').value);
    const content = document.getElementById('b-mq-input-content').value.trim();
    const gosPos = Number(document.getElementById('b-mq-select-pos').value);
    const enabled = document.getElementById('b-mq-input-enabled').checked;

    if (!content) {
      showToast('Ticker content text is required', 'error');
      return;
    }

    const existing = (state.cms.marquees || []).find(m => m.id === id) || {};
    const item = {
      ...existing,
      id,
      content,
      gos_pos: gosPos,
      enabled,
      language: existing.language || 'en',
      order_in_this_language: existing.order_in_this_language || id
    };

    const res = await apiPost('/api/dashboard/cms/upsert', {
      category: 'marquees',
      item
    });

    if (res && res.ok) {
      showToast(`Marquee #${id} updated!`, 'success');
      closeMarqueeDrawer();
      await loadCms();
      renderMarquees();
    }
  }

  async function toggleMarquee(mqId) {
    const mq = (state.cms.marquees || []).find(m => m.id === mqId);
    if (!mq) return;
    const newStatus = !mq.enabled;

    const res = await apiPost('/api/dashboard/cms/toggle', {
      category: 'marquees',
      id: mqId,
      enabled: newStatus
    });

    if (res && res.ok) {
      mq.enabled = newStatus;
      showToast(`Marquee #${mqId} ${newStatus ? 'activated' : 'disabled'}`, 'success');
      renderMarquees();
    }
  }

  async function deleteMarquee(mqId) {
    if (!confirm(`Delete Marquee ticker #${mqId}?`)) return;
    const res = await apiPost('/api/dashboard/cms/delete', {
      category: 'marquees',
      id: mqId
    });

    if (res && res.ok) {
      showToast(`Deleted Marquee #${mqId}`, 'success');
      if (state.editingMqId === mqId) closeMarqueeDrawer();
      await loadCms();
      renderMarquees();
    }
  }

  // --- Announcements / News Sub-Section ---

  function renderAnnouncements() {
    renderAnnouncementsList();
    renderNewsViewerSimulator();
  }

  function renderAnnouncementsList() {
    const container = document.getElementById('b-news-list');
    if (!container) return;

    const news = state.cms.announcements || [];
    if (!news.length) {
      container.innerHTML = `<div class="b-empty-card">No news notices configured.</div>`;
      return;
    }

    container.innerHTML = news.map(an => {
      const isSelected = state.activeNewsPreviewId === an.id || (state.activeNewsPreviewId === null && an === news[0]);
      return `
        <div class="b-news-row ${isSelected ? 'selected' : ''}" onclick="BannersSection.selectNewsPreview(${an.id})">
          <div class="b-news-row-left">
            <span class="b-news-title">${escapeHtml(an.title || `Notice #${an.id}`)}</span>
            <span class="b-news-desc-snippet">${escapeHtml((an.desc || '').slice(0, 75))}...</span>
          </div>
          <div class="b-news-row-right" onclick="event.stopPropagation()">
            <button class="b-toggle-btn ${an.enabled ? 'active' : ''}" onclick="BannersSection.toggleNews(${an.id})">
              <span class="b-toggle-knob"></span>
              <span class="b-toggle-text">${an.enabled ? 'Active' : 'Disabled'}</span>
            </button>
            <button class="b-btn-icon" onclick="BannersSection.editNews(${an.id})">${ICONS.edit}</button>
            <button class="b-btn-icon text-danger" onclick="BannersSection.deleteNews(${an.id})">${ICONS.trash}</button>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderNewsViewerSimulator() {
    const viewer = document.getElementById('b-news-viewer');
    if (!viewer) return;

    const news = state.cms.announcements || [];
    if (!news.length) {
      viewer.innerHTML = `<div class="b-empty-screen">No announcements to display</div>`;
      return;
    }

    let current = news.find(n => n.id === state.activeNewsPreviewId);
    if (!current) {
      current = news[0];
      state.activeNewsPreviewId = current.id;
    }

    viewer.innerHTML = `
      <div class="b-news-sim-card">
        <div class="b-news-sim-header">
          <div class="b-news-sim-tabs">
            ${news.map(n => `
              <button class="b-news-sim-tab ${n.id === current.id ? 'active' : ''}" onclick="BannersSection.selectNewsPreview(${n.id})">
                ${escapeHtml(n.title || `Notice #${n.id}`)}
              </button>
            `).join('')}
          </div>
        </div>
        <div class="b-news-sim-body">
          ${current.image_url ? `
            <img src="${escapeHtml(current.image_url)}" class="b-news-sim-banner" alt="Announcement Banner" onerror="this.style.display='none'">
          ` : ''}
          <div class="b-news-sim-title">${escapeHtml(current.title || 'Notice')}</div>
          <div class="b-news-sim-text">${escapeHtml(current.desc || '')}</div>
          ${current.link_url ? `
            <div class="b-news-sim-link-box">
              <span class="monospace">${escapeHtml(current.link_url)}</span>
              <button class="b-btn-primary b-btn-xs" onclick="window.open('${escapeHtml(current.link_url)}', '_blank')">
                <span>Visit Link</span> ${ICONS.external}
              </button>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  function selectNewsPreview(id) {
    state.activeNewsPreviewId = id;
    renderAnnouncements();
  }

  function openNewsDrawer(news = null) {
    const drawer = document.getElementById('b-news-drawer');
    if (!drawer) return;

    state.editingNewsId = news ? news.id : null;
    document.getElementById('b-news-input-id').value = news ? news.id : getNextId(state.cms.announcements);
    document.getElementById('b-news-input-title').value = news ? (news.title || '') : '';
    document.getElementById('b-news-input-url').value = news ? (news.image_url || '') : '';
    document.getElementById('b-news-input-link').value = news ? (news.link_url || '') : '';
    document.getElementById('b-news-input-desc').value = news ? (news.desc || '') : '';
    document.getElementById('b-news-input-enabled').checked = news ? !!news.enabled : true;

    populateBannerPicker('b-news-picker', news ? news.image_url : '');
    drawer.classList.add('open');
  }

  function closeNewsDrawer() {
    const drawer = document.getElementById('b-news-drawer');
    if (drawer) drawer.classList.remove('open');
    state.editingNewsId = null;
  }

  async function saveNews(event) {
    if (event) event.preventDefault();
    const id = Number(document.getElementById('b-news-input-id').value);
    const title = document.getElementById('b-news-input-title').value.trim();
    const url = document.getElementById('b-news-input-url').value.trim();
    const link = document.getElementById('b-news-input-link').value.trim();
    const desc = document.getElementById('b-news-input-desc').value.trim();
    const enabled = document.getElementById('b-news-input-enabled').checked;

    if (!title) {
      showToast('Announcement title is required', 'error');
      return;
    }

    const existing = (state.cms.announcements || []).find(n => n.id === id) || {};
    const item = {
      ...existing,
      id,
      title,
      image_url: url,
      image_url_for_lobby: url,
      link_url: link,
      desc,
      enabled,
      language: existing.language || 'en',
      order_in_this_language: existing.order_in_this_language || id,
      gos_pos: existing.gos_pos || 7
    };

    const res = await apiPost('/api/dashboard/cms/upsert', {
      category: 'announcements',
      item
    });

    if (res && res.ok) {
      showToast(`Announcement #${id} saved!`, 'success');
      closeNewsDrawer();
      await loadCms();
      renderAnnouncements();
    }
  }

  async function toggleNews(id) {
    const an = (state.cms.announcements || []).find(n => n.id === id);
    if (!an) return;
    const newStatus = !an.enabled;

    const res = await apiPost('/api/dashboard/cms/toggle', {
      category: 'announcements',
      id,
      enabled: newStatus
    });

    if (res && res.ok) {
      an.enabled = newStatus;
      showToast(`Announcement #${id} ${newStatus ? 'active' : 'disabled'}`, 'success');
      renderAnnouncements();
    }
  }

  async function deleteNews(id) {
    if (!confirm(`Delete Announcement notice #${id}?`)) return;
    const res = await apiPost('/api/dashboard/cms/delete', {
      category: 'announcements',
      id
    });

    if (res && res.ok) {
      showToast(`Deleted Announcement #${id}`, 'success');
      if (state.editingNewsId === id) closeNewsDrawer();
      await loadCms();
      renderAnnouncements();
    }
  }

  // =========================================================================
  // SHARED UTILITIES & DATA LOADING
  // =========================================================================

  function getNextId(list = []) {
    if (!list || !list.length) return 1;
    const maxId = Math.max(...list.map(item => Number(item.id) || 0));
    return maxId + 1;
  }

  function populateBannerPicker(selectId, currentUrl) {
    const sel = document.getElementById(selectId);
    if (!sel) return;

    sel.innerHTML = `<option value="">-- Choose from uploaded banners --</option>` +
      (state.banners || []).map(b => `
        <option value="${escapeHtml(b.url)}" ${b.url === currentUrl ? 'selected' : ''}>${escapeHtml(b.name)} (${formatBytes(b.size)})</option>
      `).join('');
  }

  async function loadCms() {
    const data = await apiGet('/api/dashboard/cms');
    if (data && data.ok) {
      state.cms = data.cms || {};
      if (data.banners) {
        state.banners = data.banners;
      }
    }
  }

  async function loadBanners() {
    const data = await apiGet('/api/dashboard/cms/banners');
    if (data && data.ok) {
      state.banners = data.banners || [];
    }
  }

  async function refreshAll() {
    const btn = document.getElementById('b-refresh-btn');
    if (btn) btn.classList.add('spinning');
    await Promise.all([loadCms(), loadBanners()]);
    switchSubTab(state.activeTab);
    if (btn) btn.classList.remove('spinning');
    showToast('Banners and CMS configuration refreshed', 'info');
  }

  async function resetCategory(category) {
    if (!confirm(`Reset ${category} to initial factory defaults?`)) return;
    const res = await apiPost('/api/dashboard/cms/reset', { category });
    if (res && res.ok) {
      showToast(`Reset ${category} to defaults`, 'success');
      await loadCms();
      switchSubTab(state.activeTab);
    }
  }

  // =========================================================================
  // SUB-TAB 5: BOOT, SPLASH & LOGIN VISUALS (REALTIME CMS ENGINE)
  // =========================================================================

  async function loadBranding() {
    const grid = document.getElementById('b-branding-grid');
    if (!grid) return;
    try {
      const res = await apiGet('/api/dashboard/branding');
      if (res && res.ok && Array.isArray(res.slots)) {
        state.brandingSlots = res.slots;
        renderBranding();
      } else {
        grid.innerHTML = '<div style="grid-column:1/-1; padding:30px; text-align:center; color:var(--b-rose);">Failed to load branding slots from server.</div>';
      }
    } catch (e) {
      grid.innerHTML = `<div style="grid-column:1/-1; padding:30px; text-align:center; color:var(--b-rose);">Error: ${escapeHtml(e.message)}</div>`;
    }
  }

  function filterBranding(category) {
    state.brandingFilter = category;
    document.querySelectorAll('[data-bfilter]').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-bfilter') === category);
    });
    renderBranding();
  }

  function renderBranding() {
    const grid = document.getElementById('b-branding-grid');
    if (!grid) return;
    const filter = state.brandingFilter || 'all';
    const slots = (state.brandingSlots || []).filter(s => filter === 'all' || s.category === filter);

    if (slots.length === 0) {
      grid.innerHTML = '<div style="grid-column:1/-1; padding:40px; text-align:center; color:var(--b-text-dim);">No branding slots in this category.</div>';
      return;
    }

    grid.innerHTML = slots.map(slot => {
      const isCustomBadge = slot.is_custom 
        ? '<span class="b-badge b-badge-success" style="font-size:10px;">Custom Active</span>'
        : '<span class="b-badge b-badge-default" style="font-size:10px;">APK Default</span>';
      
      const catBadge = `<span class="b-badge b-badge-cyan" style="font-size:10px; text-transform:uppercase;">${escapeHtml(slot.category)}</span>`;

      return `
        <div class="b-card" style="display:flex; flex-direction:column; justify-content:space-between; background:var(--b-bg-surface-elevated); border:1px solid var(--b-border);">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
              <div>
                <h3 style="font-size:14px; font-weight:700; color:var(--b-text-main);">${escapeHtml(slot.name)}</h3>
                <span style="font-size:11px; color:var(--b-text-dim); font-family:'JetBrains Mono', monospace;">${escapeHtml(slot.key)} (${slot.width}x${slot.height})</span>
              </div>
              <div style="display:flex; gap:4px; align-items:center;">
                ${catBadge}
                ${isCustomBadge}
              </div>
            </div>
            <p style="font-size:12px; color:var(--b-text-muted); margin-bottom:12px; line-height:1.4;">${escapeHtml(slot.desc)}</p>

            <!-- Preview Frame -->
            <div style="background:#05070d; border-radius:var(--b-radius-sm); border:1px solid rgba(255,255,255,0.06); padding:8px; display:flex; align-items:center; justify-content:center; min-height:140px; max-height:180px; overflow:hidden; margin-bottom:12px; position:relative;">
              <img id="branding-preview-${slot.key}" src="${slot.preview_url}" alt="${escapeHtml(slot.name)}" style="max-width:100%; max-height:160px; object-fit:contain; border-radius:4px; box-shadow:0 4px 12px rgba(0,0,0,0.5);">
            </div>
          </div>

          <!-- Controls -->
          <div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
            <div style="display:flex; gap:6px;">
              <input type="text" id="branding-url-${slot.key}" class="b-input" style="font-size:12px; padding:6px 10px;" placeholder="Image URL (/banners/...)" value="${escapeHtml(slot.preview_url.split('?')[0])}">
              <button class="b-btn-primary" style="padding:6px 12px; font-size:12px; white-space:nowrap;" onclick="BannersSection.applyBrandingUrl('${slot.key}')">Apply URL</button>
            </div>
            <div style="display:flex; gap:8px; justify-content:space-between; align-items:center;">
              <label class="b-btn-secondary" style="padding:6px 10px; font-size:12px; cursor:pointer; display:inline-flex; align-items:center; gap:5px;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                <span>Upload New</span>
                <input type="file" accept="image/*" style="display:none;" onchange="BannersSection.uploadBrandingFile('${slot.key}', this)">
              </label>
              <button class="b-btn-secondary" style="padding:6px 10px; font-size:12px; color:var(--b-text-dim);" onclick="BannersSection.resetBrandingSlot('${slot.key}')">Reset Default</button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  async function uploadBrandingFile(slotKey, input) {
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    const reader = new FileReader();
    reader.onload = async function (e) {
      const b64 = e.target.result;
      showToast(`Uploading ${file.name} for ${slotKey}...`, 'info');
      const res = await apiPost('/api/dashboard/branding/update', {
        slot_key: slotKey,
        image_b64: b64
      });
      if (res && res.ok) {
        showToast(`Successfully updated visual for ${slotKey}!`, 'success');
        await loadBranding();
      } else {
        showToast(`Update failed: ${res ? res.error : 'Network error'}`, 'error');
      }
    };
    reader.readAsDataURL(file);
  }

  async function applyBrandingUrl(slotKey) {
    const input = document.getElementById(`branding-url-${slotKey}`);
    if (!input) return;
    const url = input.value.trim();
    if (!url) {
      showToast('Please enter an image URL', 'error');
      return;
    }
    showToast(`Applying URL to ${slotKey}...`, 'info');
    const res = await apiPost('/api/dashboard/branding/update', {
      slot_key: slotKey,
      image_url: url
    });
    if (res && res.ok) {
      showToast(`Visual for ${slotKey} updated!`, 'success');
      await loadBranding();
    } else {
      showToast(`Update failed: ${res ? res.error : 'Network error'}`, 'error');
    }
  }

  async function resetBrandingSlot(slotKey) {
    if (!confirm(`Reset ${slotKey} visual to APK default?`)) return;
    const res = await apiPost('/api/dashboard/branding/reset', { slot_key: slotKey });
    if (res && res.ok) {
      showToast(`Reset ${slotKey} to default`, 'success');
      await loadBranding();
    } else {
      showToast('Reset failed', 'error');
    }
  }

  function refreshBranding() {
    loadBranding();
    showToast('Reloaded visuals from server', 'info');
  }

  // Initial Boot
  async function init() {
    initDropzone();

    // Search input listener
    const searchInput = document.getElementById('b-gallery-search');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        state.searchBannerQuery = e.target.value.trim();
        renderBannersGallery();
      });
    }

    // Sort select listener
    const sortSelect = document.getElementById('b-gallery-sort');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        state.sortBannersBy = e.target.value;
        renderBannersGallery();
      });
    }

    await Promise.all([loadCms(), loadBanners()]);
    switchSubTab('billboard');
  }

  // Public Interface
  return {
    init,
    refreshAll,
    switchSubTab,
    resetCategory,

    // Billboard Carousel
    nextAd,
    prevAd,
    setAdIndex,
    toggleCarouselPlay,
    simulateAdClick,
    editAd: (id) => {
      const ad = (state.cms.adverts || []).find(a => a.id === id);
      openAdDrawer(ad);
    },
    newAd: () => openAdDrawer(null),
    closeAdDrawer,
    saveAd,
    toggleAd,
    deleteAd,
    updateAdImgPreview,

    // Login Splash
    selectSplashPreview,
    simulateSplashClose,
    simulateSplashAction,
    bumpAllSplashes,
    bumpSingleSplash,
    editSplash: (id) => {
      const sp = (state.cms.splashes || []).find(s => s.id === id);
      openSplashDrawer(sp);
    },
    newSplash: () => openSplashDrawer(null),
    closeSplashDrawer,
    saveSplash,
    toggleSplash,
    deleteSplash,
    updateSplashImgPreview,

    // Asset Gallery & Upload
    deleteBannerFile,
    copyUrl,
    assignBanner,
    openPreviewModal,

    // Marquee & News
    editMarquee: (id) => {
      const mq = (state.cms.marquees || []).find(m => m.id === id);
      openMarqueeDrawer(mq);
    },
    newMarquee: () => openMarqueeDrawer(null),
    closeMarqueeDrawer,
    saveMarquee,
    toggleMarquee,
    deleteMarquee,

    selectNewsPreview,
    editNews: (id) => {
      const an = (state.cms.announcements || []).find(n => n.id === id);
      openNewsDrawer(an);
    },
    newNews: () => openNewsDrawer(null),
    closeNewsDrawer,
    saveNews,
    toggleNews,
    deleteNews,

    // Boot & Login Visuals CMS
    loadBranding,
    filterBranding,
    uploadBrandingFile,
    applyBrandingUrl,
    resetBrandingSlot,
    refreshBranding,

    // Accessors
    getState: () => state
  };
});
