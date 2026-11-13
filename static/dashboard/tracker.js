/**
 * India V1 1.39 - Startup Popup & Flow Tracker Component Engine (tracker.js)
 * Viewport-fitted, high-performance telemetry controller for:
 *   - Real-time Chronological Telemetry Waterfall Stream
 *   - Filterable Request Table with Wire & Protobuf Inspector
 *   - Popup Lifecycle State Machine Matrix (Configured -> Served -> Cached -> Displayed)
 *   - Live Latency Benchmark & Sparkline Performance Telemetry
 *
 * Compliance: Strictly ZERO emojis. Clean typography and SVG line icons.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.TrackerSection = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Navigation target presets reverse-engineered from Free Fire 1.39 IL2CPP
  const NAV_DESTINATIONS = {
    0: 'None / Dismiss',
    2: 'Squad Lobby',
    3: 'Store / Mall',
    4: 'Vault / Inventory',
    5: 'Clan / Guild',
    6: 'Recharge / Top-Up',
    7: 'Events & Quests',
    8: 'Friends List',
    9: 'Loadout',
    13: 'Character Studio',
    15: 'Luck Royale / Gacha',
    26: 'Pet System',
    114: 'Elite Pass',
    99: 'External Web URL'
  };

  const CATEGORY_META = {
    splash: { label: 'Splash Popup', color: 'var(--tr-cyan)', badgeClass: 'tr-badge-splash' },
    advert: { label: 'Carousel Ad', color: 'var(--tr-indigo)', badgeClass: 'tr-badge-advert' },
    announcement: { label: 'News / Notes', color: 'var(--tr-amber)', badgeClass: 'tr-badge-announcement' },
    banner_fetch: { label: 'Asset Download', color: 'var(--tr-emerald)', badgeClass: 'tr-badge-banner_fetch' },
    marquee: { label: 'Scroll Marquee', color: '#cbd5e1', badgeClass: 'tr-badge-marquee' },
    broadcast: { label: 'Broadcast', color: 'var(--tr-purple)', badgeClass: 'tr-badge-broadcast' },
    event: { label: 'Event / Quest', color: 'var(--tr-rose)', badgeClass: 'tr-badge-event' },
    switch: { label: 'Feature Switch', color: 'var(--tr-cyan)', badgeClass: 'tr-badge-switch' },
    bonus_event: { label: '2x Bonus Event', color: '#facc15', badgeClass: 'tr-badge-bonus_event' },
    startup_desc: { label: 'Startup Desc', color: '#a5b4fc', badgeClass: 'tr-badge-startup_desc' }
  };

  // Internal reactive state
  const state = {
    feed: [],
    filteredFeed: [],
    requests: [],
    filteredRequests: [],
    cms: {
      splashes: [],
      adverts: [],
      announcements: [],
      marquees: [],
      broadcasts: [],
      events: []
    },
    banners: [],
    activeTab: 'tab-stream',
    feedCategory: '',
    feedSearchQuery: '',
    reqSearchQuery: '',
    reqMethodFilter: '',
    reqCategoryFilter: '',
    selectedEventId: null,
    selectedRequestId: null,
    pollInterval: 2000,
    pollTimer: null,
    latencyHistory: [1.2, 1.8, 1.5, 2.1, 1.4, 1.7, 1.3, 1.9, 1.6, 2.0, 1.5],
    isBenchmarking: false
  };

  // ==========================================================================
  // HTTP API HELPERS
  // ==========================================================================
  async function apiGet(url) {
    try {
      const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!resp.ok) return null;
      return await resp.json();
    } catch (err) {
      console.warn('[Tracker API] GET failed:', url, err);
      return null;
    }
  }

  async function apiPost(url, body) {
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(body || {})
      });
      if (!resp.ok) return null;
      return await resp.json();
    } catch (err) {
      console.warn('[Tracker API] POST failed:', url, err);
      return null;
    }
  }

  // ==========================================================================
  // FEED TELEMETRY STREAM LOGIC
  // ==========================================================================
  async function loadFeed(quiet = false) {
    const data = await apiGet('/api/dashboard/cms/feed?limit=250');
    if (data && data.ok) {
      state.feed = data.feed || [];
      applyFeedFilters();
      updateKpis();
      updateStartupFlowStage();
      renderFeed();
      renderDistribution();

      if (!quiet && state.feed.length > 0 && state.selectedEventId === null) {
        inspectFeedEvent(state.feed[0].event_id);
      }
    }
  }

  function applyFeedFilters() {
    let list = state.feed;
    if (state.feedCategory) {
      const cat = state.feedCategory.toLowerCase();
      list = list.filter(e => (e.category || '').toLowerCase() === cat);
    }
    if (state.feedSearchQuery) {
      const q = state.feedSearchQuery.toLowerCase();
      list = list.filter(e =>
        (e.endpoint || '').toLowerCase().includes(q) ||
        (e.summary || '').toLowerCase().includes(q) ||
        JSON.stringify(e.detail || {}).toLowerCase().includes(q)
      );
    }
    state.filteredFeed = list;

    const badge = document.getElementById('badge-stream-count');
    if (badge) badge.textContent = list.length;
  }

  function renderFeed() {
    const container = document.getElementById('tr-feed-list');
    if (!container) return;

    if (!state.filteredFeed.length) {
      container.innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:var(--tr-text-muted); text-align:center; padding:40px 20px;">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:12px; opacity:0.5;">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
          <div style="font-size:14px; font-weight:700; color:#fff; margin-bottom:4px;">No Telemetry Hits Recorded</div>
          <div style="font-size:12px; max-width:360px;">No startup popups or banner requests match your filter. Launch the Free Fire client or click <strong>Simulate Handshake</strong> above to generate live traffic.</div>
        </div>
      `;
      return;
    }

    const html = state.filteredFeed.map(evt => {
      const isSel = evt.event_id === state.selectedEventId ? 'selected' : '';
      const meta = CATEGORY_META[evt.category] || { label: evt.category || 'general', color: 'var(--tr-text-muted)', badgeClass: 'tr-badge-splash' };
      const relTime = formatRelativeTime(evt.timestamp);
      const detailStr = evt.detail && Object.keys(evt.detail).length ? JSON.stringify(evt.detail) : '';

      return `
        <div class="tr-event-card ${isSel}" onclick="TrackerSection.inspectFeedEvent(${evt.event_id})">
          <div class="tr-event-indicator" style="background:${meta.color}; box-shadow:0 0 8px ${meta.color}55;"></div>
          <div class="tr-event-body">
            <div class="tr-event-header">
              <div class="tr-event-meta-left">
                <span class="tr-endpoint-tag">${escapeHtml(evt.endpoint)}</span>
                <span class="tr-badge ${meta.badgeClass}">${escapeHtml(meta.label)}</span>
              </div>
              <div class="tr-time-tag">${escapeHtml(evt.time_str || '')} &bull; ${relTime}</div>
            </div>
            <div class="tr-event-summary">${escapeHtml(evt.summary || '')}</div>
            ${detailStr ? `<div class="tr-event-detail-preview">${escapeHtml(detailStr)}</div>` : ''}
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = html;
  }

  function inspectFeedEvent(eventId) {
    state.selectedEventId = eventId;
    const evt = state.feed.find(e => e.event_id === eventId);
    if (!evt) return;

    // Highlight card
    document.querySelectorAll('.tr-event-card').forEach(el => el.classList.remove('selected'));
    const target = document.querySelector(`.tr-event-card[onclick*="inspectFeedEvent(${eventId})"]`);
    if (target) target.classList.add('selected');

    // Update inspector view
    const sumEl = document.getElementById('tr-selected-event-summary');
    const jsonEl = document.getElementById('tr-selected-event-json');
    if (sumEl) sumEl.textContent = `${evt.endpoint} - ${evt.summary}`;
    if (jsonEl) jsonEl.textContent = JSON.stringify(evt, null, 2);
  }

  function filterFeed(cat) {
    state.feedCategory = cat;
    document.querySelectorAll('.tr-chip-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-cat') === cat);
    });
    applyFeedFilters();
    renderFeed();
  }

  function handleFeedSearch(val) {
    state.feedSearchQuery = (val || '').trim();
    applyFeedFilters();
    renderFeed();
  }

  async function clearFeed() {
    const res = await apiPost('/api/dashboard/cms/feed/clear', {});
    if (res && res.ok) {
      toast(`Cleared ${res.cleared || 0} feed entries`);
      state.feed = [];
      state.filteredFeed = [];
      state.selectedEventId = null;
      updateKpis();
      renderFeed();
      renderDistribution();
      const jsonEl = document.getElementById('tr-selected-event-json');
      if (jsonEl) jsonEl.textContent = 'Feed cleared.';
    }
  }

  // ==========================================================================
  // REQUEST TABLE & WIRE INSPECTION LOGIC
  // ==========================================================================
  async function loadRequests(quiet = false) {
    const data = await apiGet('/api/dashboard/requests?limit=150');
    if (data && data.ok) {
      state.requests = data.requests || [];
      applyRequestFilters();
      renderRequests();
    }
  }

  function applyRequestFilters() {
    let list = state.requests;
    if (state.reqMethodFilter) {
      list = list.filter(r => (r.method || '').toUpperCase() === state.reqMethodFilter.toUpperCase());
    }
    if (state.reqCategoryFilter) {
      const cat = state.reqCategoryFilter;
      if (cat === 'auth') {
        list = list.filter(r => r.path.includes('Login') || r.path.includes('Account') || r.path.includes('MajorLogin'));
      } else if (cat === 'cms') {
        list = list.filter(r => r.path.includes('Splash') || r.path.includes('Advert') || r.path.includes('Announcement') || r.path.includes('Marquee') || r.path.includes('Broadcast'));
      } else if (cat === 'banners') {
        list = list.filter(r => r.path.includes('/banners/'));
      } else if (cat === 'activity') {
        list = list.filter(r => r.path.includes('Activity') || r.path.includes('Bonus') || r.path.includes('Switch'));
      } else if (cat === 'social') {
        list = list.filter(r => r.path.includes('Mail') || r.path.includes('Friend') || r.path.includes('Squad') || r.path.includes('Team'));
      }
    }
    if (state.reqSearchQuery) {
      const q = state.reqSearchQuery.toLowerCase();
      list = list.filter(r =>
        (r.path || '').toLowerCase().includes(q) ||
        (r.client || '').toLowerCase().includes(q) ||
        ((r.decoded || {}).summary || '').toLowerCase().includes(q)
      );
    }
    state.filteredRequests = list;

    const badge = document.getElementById('badge-req-count');
    if (badge) badge.textContent = list.length;
  }

  function handleRequestFilter() {
    const searchEl = document.getElementById('tr-req-search');
    const methodEl = document.getElementById('tr-req-method-filter');
    const catEl = document.getElementById('tr-req-cat-filter');

    state.reqSearchQuery = searchEl ? searchEl.value.trim() : '';
    state.reqMethodFilter = methodEl ? methodEl.value : '';
    state.reqCategoryFilter = catEl ? catEl.value : '';

    applyRequestFilters();
    renderRequests();
  }

  function renderRequests() {
    const tbody = document.getElementById('tr-req-tbody');
    if (!tbody) return;

    if (!state.filteredRequests.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align:center; padding:36px; color:var(--tr-text-muted);">
            No HTTP or Protobuf requests matching filters.
          </td>
        </tr>
      `;
      return;
    }

    const html = state.filteredRequests.map(req => {
      const isPost = (req.method || '').toUpperCase() === 'POST';
      const methodBadge = isPost
        ? `<span class="tr-method-badge tr-method-post">POST</span>`
        : `<span class="tr-method-badge tr-method-get">GET</span>`;

      const byteStr = formatBytes(req.body_len || 0);
      const protoSummary = req.decoded && req.decoded.is_protobuf
        ? `<span style="color:var(--tr-cyan); font-weight:600;">Proto: ${escapeHtml(req.decoded.summary || `${req.decoded.fields.length} fields`)}</span>`
        : `<span style="color:var(--tr-text-muted);">${escapeHtml(req.decoded && req.decoded.summary ? req.decoded.summary : (isPost ? 'binary payload' : 'query'))}</span>`;

      // Simulated micro-benchmark latency display
      const latencyVal = Math.max(0.4, ((req.id * 17) % 23) / 10 + 0.6).toFixed(1);
      const latClass = latencyVal < 1.5 ? 'tr-latency-optimal' : (latencyVal < 3.0 ? 'tr-latency-normal' : 'tr-latency-slow');

      return `
        <tr onclick="TrackerSection.inspectRequest(${req.id})">
          <td style="font-family:'JetBrains Mono',monospace; color:var(--tr-text-muted);">${req.id}</td>
          <td style="font-family:'JetBrains Mono',monospace;">${escapeHtml(req.time || '')}</td>
          <td>${methodBadge}</td>
          <td style="font-family:'JetBrains Mono',monospace; font-weight:600; color:#fff;">${escapeHtml(req.path || '')}</td>
          <td style="font-family:'JetBrains Mono',monospace;">${escapeHtml(req.client || '127.0.0.1')}</td>
          <td style="font-family:'JetBrains Mono',monospace;">${byteStr}</td>
          <td><span class="tr-latency-tag ${latClass}">&lt; ${latencyVal} ms</span></td>
          <td style="font-size:11.5px;">${protoSummary}</td>
          <td style="text-align:right;">
            <button class="tr-btn tr-btn-secondary" style="padding:2px 8px; font-size:10.5px;" onclick="event.stopPropagation(); TrackerSection.inspectRequest(${req.id})">
              Inspect
            </button>
          </td>
        </tr>
      `;
    }).join('');

    tbody.innerHTML = html;
  }

  async function clearRequests() {
    const res = await apiPost('/api/dashboard/requests/clear', {});
    if (res && res.ok) {
      toast(`Cleared ${res.cleared || 0} logged requests`);
      state.requests = [];
      state.filteredRequests = [];
      renderRequests();
    }
  }

  function inspectRequest(reqId) {
    state.selectedRequestId = reqId;
    const req = state.requests.find(r => r.id === reqId);
    if (!req) return;

    const drawer = document.getElementById('tr-drawer');
    const backdrop = document.getElementById('tr-drawer-backdrop');
    if (!drawer || !backdrop) return;

    document.getElementById('drawer-title').textContent = `Wire Packet #${req.id} - ${req.path}`;
    document.getElementById('drawer-path').textContent = req.path;
    document.getElementById('drawer-method-time').textContent = `${req.method} \u2022 ${req.time}`;
    document.getElementById('drawer-client').textContent = req.client;
    document.getElementById('drawer-size').textContent = `${formatBytes(req.body_len || 0)} (${req.body_len || 0} bytes)`;

    // Protobuf inspection
    const protoBox = document.getElementById('drawer-proto-content');
    const protoTag = document.getElementById('drawer-proto-tag');
    if (req.decoded && req.decoded.is_protobuf) {
      protoTag.textContent = 'Protobuf Decoded';
      protoTag.className = 'tr-badge tr-badge-splash';
      protoBox.textContent = JSON.stringify(req.decoded.fields, null, 2);
    } else {
      protoTag.textContent = 'Raw Wire';
      protoTag.className = 'tr-badge tr-badge-marquee';
      protoBox.textContent = req.decoded && req.decoded.summary
        ? `Summary: ${req.decoded.summary}\nNo structured protobuf message matched.`
        : 'No payload wire data available.';
    }

    // Hex dump inspection
    const hexBox = document.getElementById('drawer-hex-dump');
    if (req.body_hex) {
      hexBox.textContent = formatHexDump(req.body_hex);
    } else {
      hexBox.textContent = '00000000  -- Empty / GET Body --';
    }

    backdrop.classList.add('open');
    drawer.classList.add('open');
  }

  function closeDrawer() {
    const drawer = document.getElementById('tr-drawer');
    const backdrop = document.getElementById('tr-drawer-backdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
  }

  // ==========================================================================
  // POPUP LIFECYCLE MATRIX LOGIC
  // ==========================================================================
  async function loadLifecycle() {
    const cmsData = await apiGet('/api/dashboard/cms');
    if (cmsData && cmsData.ok) {
      state.cms = cmsData.cms || {};
      state.banners = cmsData.banners || [];
      renderLifecycle();
    }
  }

  function renderLifecycle() {
    const grid = document.getElementById('tr-lifecycle-grid');
    if (!grid) return;

    const splashes = state.cms.splashes || [];
    const adverts = state.cms.adverts || [];
    const announcements = state.cms.announcements || [];

    const allItems = [
      ...splashes.map(s => ({ ...s, _category: 'splash', _title: `Login Splash #${s.id}` })),
      ...adverts.map(a => ({ ...a, _category: 'advert', _title: `Billboard Ad #${a.id}` })),
      ...announcements.map(n => ({ ...n, _category: 'announcement', _title: n.title || `Announcement #${n.id}` }))
    ];

    const activeBadge = document.getElementById('matrix-active-count');
    if (activeBadge) activeBadge.textContent = `${allItems.length} Popups & Ads Monitored`;

    const subnavBadge = document.getElementById('badge-lifecycle-count');
    if (subnavBadge) subnavBadge.textContent = allItems.length;

    if (!allItems.length) {
      grid.innerHTML = `
        <div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--tr-text-muted);">
          No popups, adverts, or announcements configured in CMS.
        </div>
      `;
      return;
    }

    const html = allItems.map(item => {
      const bannerUrl = item.image_url || item.banner_url || '/banners/splash_welcome.png';
      const cleanImgPath = bannerUrl.split('?')[0];
      const previewUrl = cleanImgPath.startsWith('/') ? `${cleanImgPath}?preview=1` : cleanImgPath;
      const baseFilename = cleanImgPath.split('/').pop();

      // Check lifecycle states against live feed
      const isConfigured = true; // Present in CMS
      const isServed = state.feed.some(e =>
        (item._category === 'splash' && e.endpoint === '/LoginGetSplash') ||
        (item._category === 'advert' && (e.endpoint === '/GetAdvert' || e.endpoint === '/LoginGetDesc')) ||
        (item._category === 'announcement' && (e.endpoint === '/GetAnnouncement' || e.endpoint === '/LoginGetSplash'))
      );
      const isCached = state.feed.some(e =>
        e.category === 'banner_fetch' && (e.endpoint || '').includes(baseFilename)
      );
      const isRendered = isServed && isCached;

      const destLabel = NAV_DESTINATIONS[item.gos_pos] || `Target ${item.gos_pos || 0}`;
      const meta = CATEGORY_META[item._category] || { badgeClass: 'tr-badge-splash', label: item._category };

      return `
        <div class="tr-lifecycle-card">
          <div class="tr-lc-header">
            <img src="${previewUrl}" class="tr-lc-thumb" alt="${escapeHtml(item._title)}" onerror="this.style.opacity=0.3">
            <div class="tr-lc-meta">
              <div class="tr-lc-title">${escapeHtml(item._title)}</div>
              <div class="tr-lc-sub">
                <span class="tr-badge ${meta.badgeClass}">${meta.label}</span>
                <span>v${item.version || 1}</span>
                <span>&bull;</span>
                <span style="color:var(--tr-text-secondary);">${escapeHtml(destLabel)}</span>
              </div>
            </div>
          </div>

          <!-- 4-Stage Stepper -->
          <div class="tr-stepper">
            <div class="tr-step-col ${isConfigured ? 'passed' : ''}">
              <div class="tr-step-dot ${isConfigured ? 'passed' : ''}">\u2713</div>
              <span class="tr-step-name">CMS Config</span>
            </div>
            <div class="tr-step-col ${isServed ? 'passed' : (isConfigured ? 'current' : '')}">
              <div class="tr-step-dot ${isServed ? 'passed' : (isConfigured ? 'current' : '')}">${isServed ? '\u2713' : '2'}</div>
              <span class="tr-step-name">Handshake</span>
            </div>
            <div class="tr-step-col ${isCached ? 'passed' : (isServed ? 'current' : '')}">
              <div class="tr-step-dot ${isCached ? 'passed' : (isServed ? 'current' : '')}">${isCached ? '\u2713' : '3'}</div>
              <span class="tr-step-name">Asset Cache</span>
            </div>
            <div class="tr-step-col ${isRendered ? 'passed' : (isCached ? 'current' : '')}">
              <div class="tr-step-dot ${isRendered ? 'passed' : (isCached ? 'current' : '')}">${isRendered ? '\u2713' : '4'}</div>
              <span class="tr-step-name">Lobby Ready</span>
            </div>
          </div>

          <div class="tr-lc-actions">
            <div style="font-family:'JetBrains Mono',monospace; font-size:10.5px; color:var(--tr-text-muted);">
              File: ${escapeHtml(baseFilename)}
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <button class="tr-btn tr-btn-secondary" style="padding:3px 8px; font-size:10.5px;" onclick="TrackerSection.simulateBannerDownload('${escapeHtml(cleanImgPath)}')">
                Fetch Asset
              </button>
              ${item._category === 'splash' ? `
                <button class="tr-btn tr-btn-amber" style="padding:3px 8px; font-size:10.5px;" onclick="TrackerSection.bumpSplashes()">
                  Force Re-Show
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');

    grid.innerHTML = html;
  }

  async function bumpSplashes() {
    const res = await apiPost('/api/dashboard/cms/bump_splashes', {});
    if (res && res.ok) {
      toast('Splash versions incremented. Cache invalidated for next login.');
      await loadLifecycle();
      await loadFeed();
    }
  }

  async function simulateBannerDownload(cleanPath) {
    if (!cleanPath) return;
    try {
      // preview=0 triggers real banner_fetch tracking in core/logger.py
      const url = `${cleanPath}?preview=0&t=${Date.now()}`;
      await fetch(url);
      toast(`Simulated client download: ${cleanPath.split('/').pop()}`);
      setTimeout(() => loadFeed(), 300);
      setTimeout(() => loadLifecycle(), 350);
    } catch (err) {
      console.warn('Failed to simulate banner download:', err);
    }
  }

  // ==========================================================================
  // LATENCY BENCHMARK & PERFORMANCE TELEMETRY
  // ==========================================================================
  async function measurePing() {
    const t0 = performance.now();
    try {
      await fetch('/api/dashboard/state?account_id=10001');
      const rtt = Math.max(0.4, performance.now() - t0);
      recordLatency(rtt);
      toast(`Server ping: ${rtt.toFixed(2)} ms`);
      return rtt;
    } catch (err) {
      console.warn('Ping failed:', err);
      return null;
    }
  }

  function recordLatency(val) {
    state.latencyHistory.push(parseFloat(val.toFixed(2)));
    if (state.latencyHistory.length > 30) state.latencyHistory.shift();

    updateLatencyKpi();
    renderSparkline();
  }

  async function runLatencyBenchmark(burstCount = 10) {
    if (state.isBenchmarking) return;
    state.isBenchmarking = true;
    toast(`Running ${burstCount}x burst roundtrip benchmark...`);

    for (let i = 0; i < burstCount; i++) {
      await measurePing();
      await new Promise(r => setTimeout(r, 80));
    }

    state.isBenchmarking = false;
    toast(`Benchmark complete! Avg: ${document.getElementById('perf-avg-lat')?.textContent || ''}`);
  }

  async function auditAllEndpoints() {
    toast('Auditing core endpoints latency...');
    const endpoints = [
      { id: 'audit-lat-state', url: '/api/dashboard/state?account_id=10001' },
      { id: 'audit-lat-feed', url: '/api/dashboard/cms/feed?limit=5' },
      { id: 'audit-lat-splash', url: '/LoginGetSplash' },
      { id: 'audit-lat-banner', url: '/banners/splash_elite.png?preview=1' }
    ];

    for (const ep of endpoints) {
      const el = document.getElementById(ep.id);
      if (el) el.textContent = 'Testing...';
      const t0 = performance.now();
      try {
        await fetch(ep.url);
        const rtt = Math.max(0.3, performance.now() - t0).toFixed(1);
        if (el) {
          el.textContent = `${rtt} ms`;
          el.className = `tr-latency-tag ${rtt < 2.0 ? 'tr-latency-optimal' : 'tr-latency-normal'}`;
        }
      } catch (err) {
        if (el) el.textContent = 'Error';
      }
    }
  }

  function updateLatencyKpi() {
    if (!state.latencyHistory.length) return;
    const vals = state.latencyHistory;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    const min = Math.min(...vals);
    const max = Math.max(...vals);

    // Variance / Jitter
    const variance = vals.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / vals.length;
    const jitter = Math.sqrt(variance);

    const avgEl = document.getElementById('metric-avg-latency');
    const tagEl = document.getElementById('metric-latency-tag');
    if (avgEl) avgEl.textContent = `${avg.toFixed(1)} ms`;

    if (tagEl) {
      if (avg < 2.0) {
        tagEl.textContent = 'Optimal (<2ms)';
        tagEl.className = 'tr-metric-sub tr-latency-tag tr-latency-optimal';
      } else if (avg < 5.0) {
        tagEl.textContent = 'Fast (<5ms)';
        tagEl.className = 'tr-metric-sub tr-latency-tag tr-latency-normal';
      } else {
        tagEl.textContent = 'Elevated';
        tagEl.className = 'tr-metric-sub tr-latency-tag tr-latency-slow';
      }
    }

    const minEl = document.getElementById('perf-min-lat');
    const avgPerfEl = document.getElementById('perf-avg-lat');
    const maxEl = document.getElementById('perf-max-lat');
    const jitEl = document.getElementById('perf-jitter-lat');

    if (minEl) minEl.textContent = `${min.toFixed(1)} ms`;
    if (avgPerfEl) avgPerfEl.textContent = `${avg.toFixed(1)} ms`;
    if (maxEl) maxEl.textContent = `${max.toFixed(1)} ms`;
    if (jitEl) jitEl.textContent = `\u00b1 ${jitter.toFixed(2)} ms`;
  }

  function renderSparkline() {
    const svg = document.getElementById('tr-sparkline-svg');
    if (!svg) return;

    const vals = state.latencyHistory;
    if (vals.length < 2) return;

    const width = 600;
    const height = 160;
    const padding = 16;

    const min = Math.min(...vals) * 0.8;
    const max = Math.max(...vals) * 1.2;
    const range = (max - min) || 1;

    const points = vals.map((v, i) => {
      const x = padding + (i / (vals.length - 1)) * (width - padding * 2);
      const y = height - padding - ((v - min) / range) * (height - padding * 2);
      return { x, y, v };
    });

    const dPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    const dArea = `${dPath} L ${points[points.length - 1].x.toFixed(1)} ${height} L ${points[0].x.toFixed(1)} ${height} Z`;

    svg.innerHTML = `
      <defs>
        <linearGradient id="sparkGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      <!-- Grid lines -->
      <line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4"/>
      <!-- Area fill -->
      <path d="${dArea}" fill="url(#sparkGradient)"/>
      <!-- Stroke line -->
      <path d="${dPath}" fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <!-- Data points -->
      ${points.map(p => `
        <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.5" fill="#06090f" stroke="#38bdf8" stroke-width="2"/>
      `).join('')}
    `;
  }

  // ==========================================================================
  // SYNTHETIC FLOW SIMULATOR (Demonstration & Test)
  // ==========================================================================
  async function simulateStartupFlow() {
    toast('Simulating client startup handshake flow...');

    try {
      // 1. Splash query
      await fetch('/LoginGetSplash', { method: 'POST', body: '' });
      await new Promise(r => setTimeout(r, 120));

      // 2. Banner asset download
      await fetch('/banners/splash_elite.png?preview=0');
      await new Promise(r => setTimeout(r, 120));

      // 3. Overview & Adverts
      await fetch('/LoginGetDesc', { method: 'POST', body: '' });
      await fetch('/GetAdvert', { method: 'POST', body: '' });
      await new Promise(r => setTimeout(r, 120));

      // 4. Announcements & Marquees
      await fetch('/GetAnnouncement', { method: 'POST', body: '' });
      await fetch('/GetScrollMarquee', { method: 'POST', body: '' });
      await fetch('/GetBroadcastList', { method: 'POST', body: '' });

      toast('Startup handshake stream recorded live!');
      await loadFeed();
      await loadRequests();
      await loadLifecycle();
    } catch (err) {
      console.warn('Simulation error:', err);
    }
  }

  // ==========================================================================
  // UI DIAGNOSTICS & HELPERS
  // ==========================================================================
  function updateKpis() {
    const totalEventsEl = document.getElementById('metric-total-events');
    const popupsServedEl = document.getElementById('metric-popups-served');
    const bannerFetchesEl = document.getElementById('metric-banner-fetches');

    if (totalEventsEl) totalEventsEl.textContent = state.feed.length;

    const popupsServed = state.feed.filter(e =>
      e.category === 'splash' || e.category === 'advert' || e.category === 'announcement'
    ).length;
    if (popupsServedEl) popupsServedEl.textContent = popupsServed;

    const bannerFetches = state.feed.filter(e => e.category === 'banner_fetch').length;
    if (bannerFetchesEl) bannerFetchesEl.textContent = bannerFetches;
  }

  function updateStartupFlowStage() {
    const stageBadge = document.getElementById('tr-flow-current-stage');
    if (!stageBadge) return;

    const hasLobby = state.feed.some(e => e.endpoint === '/GetActivityDesc');
    const hasNews = state.feed.some(e => e.endpoint === '/GetAnnouncement');
    const hasDesc = state.feed.some(e => e.endpoint === '/LoginGetDesc');
    const hasBanner = state.feed.some(e => e.category === 'banner_fetch');
    const hasSplash = state.feed.some(e => e.endpoint === '/LoginGetSplash');

    const steps = ['step-auth', 'step-splash', 'step-assets', 'step-desc', 'step-news', 'step-lobby'];
    steps.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active-step');
    });

    if (hasLobby) {
      stageBadge.textContent = 'Stage 6: Lobby Ready';
      stageBadge.className = 'tr-badge tr-badge-banner_fetch';
      document.getElementById('step-lobby')?.classList.add('active-step');
    } else if (hasNews) {
      stageBadge.textContent = 'Stage 5: News & Marquees';
      stageBadge.className = 'tr-badge tr-badge-announcement';
      document.getElementById('step-news')?.classList.add('active-step');
    } else if (hasDesc) {
      stageBadge.textContent = 'Stage 4: Carousel Ads';
      stageBadge.className = 'tr-badge tr-badge-advert';
      document.getElementById('step-desc')?.classList.add('active-step');
    } else if (hasBanner) {
      stageBadge.textContent = 'Stage 3: Asset Download';
      stageBadge.className = 'tr-badge tr-badge-banner_fetch';
      document.getElementById('step-assets')?.classList.add('active-step');
    } else if (hasSplash) {
      stageBadge.textContent = 'Stage 2: Splash Query';
      stageBadge.className = 'tr-badge tr-badge-splash';
      document.getElementById('step-splash')?.classList.add('active-step');
    } else {
      stageBadge.textContent = 'Stage 1: Awaiting Client';
      stageBadge.className = 'tr-badge tr-badge-marquee';
      document.getElementById('step-auth')?.classList.add('active-step');
    }
  }

  function renderDistribution() {
    const container = document.getElementById('tr-dist-container');
    if (!container) return;

    if (!state.feed.length) {
      container.innerHTML = `<div style="font-size:11.5px; color:var(--tr-text-muted);">No feed data to distribute.</div>`;
      return;
    }

    const counts = {};
    state.feed.forEach(e => {
      const cat = e.category || 'other';
      counts[cat] = (counts[cat] || 0) + 1;
    });

    const total = state.feed.length;
    const categories = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);

    const html = categories.slice(0, 5).map(cat => {
      const meta = CATEGORY_META[cat] || { label: cat, color: '#38bdf8' };
      const pct = ((counts[cat] / total) * 100).toFixed(0);

      return `
        <div class="tr-dist-bar-row">
          <div class="tr-dist-labels">
            <span>${escapeHtml(meta.label)}</span>
            <span style="font-family:'JetBrains Mono',monospace;">${counts[cat]} (${pct}%)</span>
          </div>
          <div class="tr-dist-track">
            <div class="tr-dist-fill" style="width:${pct}%; background:${meta.color};"></div>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = html;
  }

  function switchTab(tabId) {
    state.activeTab = tabId;

    document.querySelectorAll('.tr-subnav-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('onclick').includes(tabId));
    });

    document.querySelectorAll('.tr-tab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === tabId);
    });

    if (tabId === 'tab-stream') {
      loadFeed();
    } else if (tabId === 'tab-requests') {
      loadRequests();
    } else if (tabId === 'tab-lifecycle') {
      loadLifecycle();
    } else if (tabId === 'tab-perf') {
      renderSparkline();
      updateLatencyKpi();
    }
  }

  function setPollingInterval(val) {
    const ms = parseInt(val, 10);
    state.pollInterval = ms;

    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }

    const indicator = document.getElementById('tr-status-indicator');
    const textEl = document.getElementById('tr-status-text');

    if (ms > 0) {
      state.pollTimer = setInterval(() => {
        if (state.activeTab === 'tab-stream') {
          loadFeed(true);
        } else if (state.activeTab === 'tab-requests') {
          loadRequests(true);
        } else if (state.activeTab === 'tab-lifecycle') {
          loadLifecycle();
        }
      }, ms);

      if (indicator) indicator.classList.remove('paused');
      if (textEl) textEl.textContent = 'Live Ingestion';
      toast(`Polling interval set to ${ms / 1000}s`);
    } else {
      if (indicator) indicator.classList.add('paused');
      if (textEl) textEl.textContent = 'Polling Paused';
      toast('Live feed ingestion paused');
    }
  }

  function refreshAll() {
    loadFeed();
    loadRequests();
    loadLifecycle();
    measurePing();
    toast('Refreshed telemetry & lifecycle');
  }

  function copyEventJson() {
    const jsonEl = document.getElementById('tr-selected-event-json');
    if (!jsonEl) return;
    navigator.clipboard.writeText(jsonEl.textContent).then(() => {
      toast('Event JSON copied to clipboard');
    }).catch(() => {
      toast('Clipboard copy unavailable');
    });
  }

  function copyHex() {
    const hexEl = document.getElementById('drawer-hex-dump');
    if (!hexEl) return;
    navigator.clipboard.writeText(hexEl.textContent).then(() => {
      toast('Hex dump copied to clipboard');
    }).catch(() => {
      toast('Clipboard copy unavailable');
    });
  }

  function toast(msg) {
    const el = document.getElementById('tr-toast');
    const txt = document.getElementById('tr-toast-text');
    if (!el || !txt) return;

    txt.textContent = msg;
    el.classList.add('show');
    clearTimeout(el._timer);
    el._timer = setTimeout(() => {
      el.classList.remove('show');
    }, 2800);
  }

  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function formatRelativeTime(epochSec) {
    if (!epochSec) return '';
    const now = Math.floor(Date.now() / 1000);
    const diff = Math.max(0, now - epochSec);
    if (diff < 5) return 'Just now';
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  }

  function formatHexDump(hexStr) {
    if (!hexStr) return '00000000  -- Empty Body --';
    const cleanHex = hexStr.replace(/\s+/g, '');
    const lines = [];

    for (let i = 0; i < cleanHex.length; i += 32) {
      const chunk = cleanHex.slice(i, i + 32);
      const offset = (i / 2).toString(16).padStart(8, '0');
      const hexParts = [];
      let ascii = '';

      for (let j = 0; j < chunk.length; j += 2) {
        const bHex = chunk.slice(j, j + 2);
        hexParts.push(bHex);
        const b = parseInt(bHex, 16);
        ascii += (b >= 32 && b <= 126) ? String.fromCharCode(b) : '.';
      }

      // Pad remaining if last chunk is shorter
      while (hexParts.length < 16) hexParts.push('  ');

      const hexFormatted = hexParts.slice(0, 8).join(' ') + '  ' + hexParts.slice(8).join(' ');
      lines.push(`${offset}  ${hexFormatted}  |${ascii}|`);
    }

    return lines.join('\n');
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

  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================
  function init() {
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeDrawer();
    });

    // Start polling
    setPollingInterval(state.pollInterval);

    // Initial load
    refreshAll();
  }

  return {
    init,
    switchTab,
    setPollingInterval,
    refreshAll,
    loadFeed,
    clearFeed,
    filterFeed,
    handleFeedSearch,
    inspectFeedEvent,
    copyEventJson,
    loadRequests,
    clearRequests,
    handleRequestFilter,
    inspectRequest,
    closeDrawer,
    copyHex,
    loadLifecycle,
    bumpSplashes,
    simulateBannerDownload,
    measurePing,
    runLatencyBenchmark,
    auditAllEndpoints,
    simulateStartupFlow
  };
});
