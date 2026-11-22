/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: 08.3 Announcements & Marquee Manager (#/cms/announcements)
 * 
 * Features:
 * - Real-Time Animated Marquee Scrolling Ticker Simulator & Controller
 * - Quick Ticker Broadcast Bar (POST /api/dashboard/cms/marquee/update & upsert)
 * - Free Fire 1.39 In-Game Bulletin Board & News Center Simulator (Responsive 1366x768+)
 * - Announcement CRUD with rich content descriptions and jump actions
 * - Priority Reordering (Move Up / Down) via /api/dashboard/cms/reorder
 * - Instant Active Toggling via /api/dashboard/cms/toggle
 * - Responsive .glass-table-container Horizontal Containment
 * - Apple macOS/iPadOS Dark Glassmorphism Design
 */

(function () {
  'use strict';

  // Navigation targets reverse-engineered from Free Fire 1.39 IL2CPP
  const NAV_DESTINATIONS = [
    { id: 0, label: '0 — Dismiss / None', desc: 'Closes dialog or does nothing' },
    { id: 3, label: '3 — Store / Mall', desc: 'Mall tab via sub_go_pos (e.g. Bundles)' },
    { id: 7, label: '7 — Events & Quests', desc: 'Event tab (Daily, Festival, Tokens)' },
    { id: 15, label: '15 — Luck Royale / Gacha', desc: 'Gold, Diamond & Weapon Royale' },
    { id: 114, label: '114 — Elite Pass', desc: 'Elite Pass controller & missions' },
    { id: 13, label: '13 — Character Profile', desc: 'Character selection & skills' },
    { id: 4, label: '4 — Vault / Inventory', desc: 'Costumes, skins & wardrobe' },
    { id: 26, label: '26 — Pet System', desc: 'Pet selection & abilities' },
    { id: 2, label: '2 — Squad Lobby', desc: 'Duo or Squad group matchmaking' },
    { id: 5, label: '5 — Clan / Guild', desc: 'Guild lobby & leaderboards' },
    { id: 6, label: '6 — Top-Up / Recharge', desc: 'Diamond purchase & rebates' },
    { id: 8, label: '8 — Friends List', desc: 'Friend requests & status' },
    { id: 9, label: '9 — Loadout', desc: 'Battle item loadout & airdrops' },
    { id: 99, label: '99 — External Web URL', desc: 'Opens URL in external browser' }
  ];

  // Internal module state
  const state = {
    announcements: [],
    marquees: [],
    banners: [],
    selectedNewsId: null,
    marqueeSpeed: 24, // seconds duration for full scroll
    marqueePlaying: true,
    isLoading: false
  };

  function getNavLabel(pos) {
    const dest = NAV_DESTINATIONS.find(d => d.id === parseInt(pos, 10));
    return dest ? dest.label : `Target #${pos}`;
  }

  function escapeHtml(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // --- API DATA FETCHERS ---
  async function loadData() {
    state.isLoading = true;
    try {
      const [cmsRes, bannerRes] = await Promise.all([
        window.apiClient.get('/api/dashboard/cms'),
        window.apiClient.get('/api/dashboard/cms/banners')
      ]);

      if (cmsRes.ok && cmsRes.data) {
        const cms = cmsRes.data.cms || {};
        state.announcements = cms.announcements || [];
        state.marquees = cms.marquees || [];
        if (!state.selectedNewsId && state.announcements.length > 0) {
          state.selectedNewsId = state.announcements[0].id;
        }
      }
      if (bannerRes.ok && bannerRes.data) {
        state.banners = bannerRes.data.banners || [];
      }
    } catch (e) {
      console.error('Error loading announcements/marquee data', e);
      window.UI.Toast('Failed to load announcements telemetry: ' + e.message, 'error');
    } finally {
      state.isLoading = false;
    }
  }

  // --- QUICK MARQUEE UPDATE ---
  async function quickUpdateMarquee(text) {
    if (!text || !text.trim()) {
      window.UI.Toast('Please enter marquee ticker text', 'warning');
      return;
    }

    // Try dedicated marquee endpoint
    let res = await window.apiClient.post('/api/dashboard/cms/marquee/update', { text: text.trim() });
    
    // If not handled, upsert into marquees category
    if (!res.ok) {
      res = await window.apiClient.post('/api/dashboard/cms/upsert', {
        category: 'marquees',
        item: {
          content: text.trim(),
          language: 'en',
          region: 'DEFAULT',
          enabled: true,
          order_in_this_language: 1
        }
      });
    }

    if (res.ok) {
      window.UI.Toast('Marquee ticker broadcast updated live!', 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Failed to update marquee: ' + (res.error || 'Server error'), 'error');
    }
  }

  // --- ANNOUNCEMENT ACTIONS ---
  async function toggleAnnouncement(id, currentStatus) {
    const res = await window.apiClient.post('/api/dashboard/cms/toggle', {
      category: 'announcements',
      id: id,
      enabled: !currentStatus
    });

    if (res.ok) {
      window.UI.Toast(`Announcement #${id} ${!currentStatus ? 'Activated' : 'Deactivated'}`, 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Failed to toggle announcement: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function deleteAnnouncement(id) {
    window.UI.Confirm(
      'Delete Announcement Notice',
      `Permanently delete announcement #${id}? It will be removed from player in-game bulletin boards.`,
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/delete', {
          category: 'announcements',
          id: id
        });
        if (res.ok) {
          window.UI.Toast(`Deleted announcement #${id}`, 'success');
          if (state.selectedNewsId === id) state.selectedNewsId = null;
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Delete failed: ' + (res.error || 'Server error'), 'error');
        }
      },
      true
    );
  }

  async function moveAnnouncement(index, direction) {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= state.announcements.length) return;

    const list = [...state.announcements];
    const item = list.splice(index, 1)[0];
    list.splice(targetIdx, 0, item);

    const orderedIds = list.map(a => a.id);
    const res = await window.apiClient.post('/api/dashboard/cms/reorder', {
      category: 'announcements',
      ordered_ids: orderedIds
    });

    if (res.ok) {
      window.UI.Toast('Announcement order updated', 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Reordering failed: ' + (res.error || 'Server error'), 'error');
    }
  }

  // --- MARQUEE ACTIONS ---
  async function toggleMarquee(id, currentStatus) {
    const res = await window.apiClient.post('/api/dashboard/cms/toggle', {
      category: 'marquees',
      id: id,
      enabled: !currentStatus
    });

    if (res.ok) {
      window.UI.Toast(`Marquee #${id} ${!currentStatus ? 'Activated' : 'Deactivated'}`, 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Failed to toggle marquee: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function deleteMarquee(id) {
    window.UI.Confirm(
      'Delete Marquee Message',
      `Delete scrolling marquee message #${id}?`,
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/delete', {
          category: 'marquees',
          id: id
        });
        if (res.ok) {
          window.UI.Toast(`Deleted marquee #${id}`, 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Delete failed: ' + (res.error || 'Server error'), 'error');
        }
      },
      true
    );
  }

  async function moveMarquee(index, direction) {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= state.marquees.length) return;

    const list = [...state.marquees];
    const item = list.splice(index, 1)[0];
    list.splice(targetIdx, 0, item);

    const orderedIds = list.map(m => m.id);
    const res = await window.apiClient.post('/api/dashboard/cms/reorder', {
      category: 'marquees',
      ordered_ids: orderedIds
    });

    if (res.ok) {
      window.UI.Toast('Marquee sequence updated', 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Reorder failed: ' + (res.error || 'Server error'), 'error');
    }
  }

  // --- RESET HANDLERS ---
  async function resetCategory(category) {
    window.UI.Confirm(
      `Reset ${category.toUpperCase()} to Factory Defaults`,
      `Reset all ${category} items back to initial server restore seed? Custom items will be lost.`,
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/reset', { category });
        if (res.ok) {
          window.UI.Toast(`Reset ${category} to defaults`, 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Reset failed: ' + (res.error || 'Server error'), 'error');
        }
      },
      true
    );
  }

  // --- MODALS ---
  function openAnnouncementModal(item = null) {
    const isEdit = !!item;
    const title = isEdit ? `Edit Announcement #${item.id}` : 'Create New In-Game Announcement';
    const currentTitle = item ? (item.title || '') : '';
    const currentDesc = item ? (item.desc || '') : '';
    const currentImg = item ? (item.image_url || '') : '';
    const currentGosPos = item ? (item.gos_pos || 0) : 0;
    const currentLink = item ? (item.link_url || '') : '';
    const currentEnabled = item ? (item.enabled !== false) : true;

    const bannerOptions = state.banners.map(b => `
      <option value="${b.url}" ${b.url === currentImg ? 'selected' : ''}>${b.name} (${Math.round(b.size / 1024)} KB)</option>
    `).join('');

    const navOptions = NAV_DESTINATIONS.map(d => `
      <option value="${d.id}" ${d.id === parseInt(currentGosPos, 10) ? 'selected' : ''}>${d.label} — ${d.desc}</option>
    `).join('');

    const bodyHtml = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Announcement Title</label>
          <input type="text" id="modal-news-title" class="form-input" placeholder="e.g. Bermuda 2019 Classic Server Restored!" value="${escapeHtml(currentTitle)}">
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Select Header Graphic Asset</label>
          <select id="modal-news-select" class="form-input" onchange="document.getElementById('modal-news-img').value = this.value; document.getElementById('modal-news-preview-img').src = this.value;">
            <option value="">-- Choose from Server Repository --</option>
            ${bannerOptions}
          </select>
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Header Image URL (image_url)</label>
          <input type="text" id="modal-news-img" class="form-input" placeholder="/banners/announce_welcome.png" value="${escapeHtml(currentImg)}" oninput="document.getElementById('modal-news-preview-img').src = this.value;">
        </div>

        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px; display: flex; align-items: center; gap: 12px;">
          <div style="width: 140px; height: 75px; background: #000; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-default);">
            <img id="modal-news-preview-img" src="${currentImg || '/banners/announce_welcome.png'}" style="max-width: 100%; max-height: 100%; object-fit: cover;" onerror="this.src='/banners/announce_welcome.png'">
          </div>
          <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
            Header image displayed at the top of the news detail article in the game bulletin board.
          </div>
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Detailed Notice Body Text</label>
          <textarea id="modal-news-desc" class="form-input" style="height: 110px; line-height: 1.5;" placeholder="Enter complete announcement text...">${escapeHtml(currentDesc)}</textarea>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Call-To-Action Jump (gos_pos)</label>
            <select id="modal-news-gos-pos" class="form-input">
              ${navOptions}
            </select>
          </div>
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Deep-Link / Sub Parameter</label>
            <input type="text" id="modal-news-link" class="form-input" placeholder="e.g. 7 or https://..." value="${escapeHtml(currentLink)}">
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
          <input type="checkbox" id="modal-news-enabled" style="accent-color: var(--accent-cyan); width: 16px; height: 16px;" ${currentEnabled ? 'checked' : ''}>
          <label for="modal-news-enabled" style="font-size: 12.5px; color: var(--text-primary); cursor: pointer;">Publish announcement immediately to in-game bulletin board</label>
        </div>
      </div>
    `;

    const footerButtonsHtml = `
      <button class="btn btn-primary" id="modal-news-save-btn">Save Announcement</button>
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Cancel</button>
    `;

    window.UI.Modal(title, bodyHtml, footerButtonsHtml);

    document.getElementById('modal-news-save-btn').onclick = async () => {
      const titleVal = document.getElementById('modal-news-title').value.trim() || 'Untitled Announcement';
      const imgUrl = document.getElementById('modal-news-img').value.trim() || '/banners/announce_welcome.png';
      const descVal = document.getElementById('modal-news-desc').value.trim();
      const gosPos = parseInt(document.getElementById('modal-news-gos-pos').value, 10) || 0;
      const linkUrl = document.getElementById('modal-news-link').value.trim();
      const enabled = document.getElementById('modal-news-enabled').checked;

      const payload = {
        category: 'announcements',
        item: {
          ...(item || {}),
          title: titleVal,
          desc: descVal,
          image_url: imgUrl,
          image_url_for_lobby: imgUrl,
          gos_pos: gosPos,
          link_url: linkUrl,
          enabled: enabled,
          language: 'en'
        }
      };

      const res = await window.apiClient.post('/api/dashboard/cms/upsert', payload);
      if (res.ok) {
        window.UI.Toast(`Announcement ${isEdit ? 'updated' : 'published'} successfully`, 'success');
        document.getElementById('global-modal-overlay').remove();
        await loadData();
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Error saving announcement: ' + (res.error || 'Server error'), 'error');
      }
    };
  }

  function openMarqueeModal(item = null) {
    const isEdit = !!item;
    const title = isEdit ? `Edit Marquee Message #${item.id}` : 'Create Marquee Ticker Message';
    const currentContent = item ? (item.content || '') : '';
    const currentRegion = item ? (item.region || 'DEFAULT') : 'DEFAULT';
    const currentEnabled = item ? (item.enabled !== false) : true;

    const bodyHtml = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Ticker Scrolling Text</label>
          <input type="text" id="modal-mq-text" class="form-input" placeholder="e.g. Server maintenance scheduled tonight at 02:00 UTC." value="${escapeHtml(currentContent)}">
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Server Region</label>
            <select id="modal-mq-region" class="form-input">
              <option value="DEFAULT" ${currentRegion === 'DEFAULT' ? 'selected' : ''}>DEFAULT (All Servers)</option>
              <option value="IND" ${currentRegion === 'IND' ? 'selected' : ''}>IND (India / Classic)</option>
              <option value="SEA" ${currentRegion === 'SEA' ? 'selected' : ''}>SEA (South East Asia)</option>
              <option value="BR" ${currentRegion === 'BR' ? 'selected' : ''}>BR (Brazil)</option>
            </select>
          </div>
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Language</label>
            <input type="text" id="modal-mq-lang" class="form-input" value="en">
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
          <input type="checkbox" id="modal-mq-enabled" style="accent-color: var(--accent-cyan); width: 16px; height: 16px;" ${currentEnabled ? 'checked' : ''}>
          <label for="modal-mq-enabled" style="font-size: 12.5px; color: var(--text-primary); cursor: pointer;">Active in live marquee broadcast rotation</label>
        </div>
      </div>
    `;

    const footerButtonsHtml = `
      <button class="btn btn-primary" id="modal-mq-save-btn">Save Marquee</button>
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Cancel</button>
    `;

    window.UI.Modal(title, bodyHtml, footerButtonsHtml);

    document.getElementById('modal-mq-save-btn').onclick = async () => {
      const content = document.getElementById('modal-mq-text').value.trim();
      const region = document.getElementById('modal-mq-region').value;
      const lang = document.getElementById('modal-mq-lang').value.trim() || 'en';
      const enabled = document.getElementById('modal-mq-enabled').checked;

      if (!content) {
        window.UI.Toast('Please enter ticker text', 'warning');
        return;
      }

      const payload = {
        category: 'marquees',
        item: {
          ...(item || {}),
          content: content,
          region: region,
          language: lang,
          enabled: enabled,
          order_in_this_language: item ? item.order_in_this_language : (state.marquees.length + 1)
        }
      };

      const res = await window.apiClient.post('/api/dashboard/cms/upsert', payload);
      if (res.ok) {
        window.UI.Toast(`Marquee ticker ${isEdit ? 'updated' : 'created'} successfully`, 'success');
        document.getElementById('global-modal-overlay').remove();
        await loadData();
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Error saving marquee: ' + (res.error || 'Server error'), 'error');
      }
    };
  }

  // --- MAIN RENDER ---
  async function render(canvas) {
    if (!canvas) return;

    const totalNews = state.announcements.length;
    const activeNews = state.announcements.filter(a => a.enabled !== false).length;
    const activeMqs = state.marquees.filter(m => m.enabled !== false);
    const marqueeString = activeMqs.length > 0 
      ? activeMqs.map(m => m.content).join('   ✦   ')
      : 'Welcome to Free Fire 2019 IND PROJECT Restoration Core — All Systems Operational';

    // Currently selected article for simulator preview
    const selectedArticle = state.announcements.find(a => a.id === state.selectedNewsId) || state.announcements[0];

    // Build News Table Rows
    const newsRows = state.announcements.map((a, idx) => {
      const isEnabled = a.enabled !== false;
      const navBadge = window.UI.Badge(getNavLabel(a.gos_pos), a.gos_pos > 0 ? 'cyan' : 'neutral');
      const statusBadge = isEnabled ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('DISABLED', 'neutral');

      return `
        <tr style="${state.selectedNewsId === a.id ? 'background: rgba(56, 189, 248, 0.08);' : ''}">
          <td style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary); width: 40px; text-align: center;">
            #${a.id}
          </td>
          <td style="width: 70px;">
            <div style="width: 60px; height: 34px; border-radius: 4px; overflow: hidden; background: #000; border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center; cursor: pointer;" onclick="window.CMSAnnouncements.selectArticle(${a.id})">
              <img src="${escapeHtml(a.image_url)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/banners/announce_welcome.png'">
            </div>
          </td>
          <td>
            <div style="font-weight: 600; color: #fff; font-size: 13px; cursor: pointer;" onclick="window.CMSAnnouncements.selectArticle(${a.id})">
              ${escapeHtml(a.title)}
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${escapeHtml(a.desc || 'No body text specified')}
            </div>
          </td>
          <td>${navBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Up" ${idx === 0 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSAnnouncements.moveNews(${idx}, -1)">▲</button>
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Down" ${idx === state.announcements.length - 1 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSAnnouncements.moveNews(${idx}, 1)">▼</button>
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSAnnouncements.toggleNews(${a.id}, ${isEnabled})">
                ${isEnabled ? 'Deactivate' : 'Activate'}
              </button>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSAnnouncements.openEditNews(${a.id})">
                Edit
              </button>
              <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSAnnouncements.deleteNews(${a.id})">
                Delete
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Build Marquee Table Rows
    const marqueeRows = state.marquees.map((m, idx) => {
      const isEnabled = m.enabled !== false;
      const statusBadge = isEnabled ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('DISABLED', 'neutral');
      const regionBadge = window.UI.Badge(m.region || 'DEFAULT', 'neutral');

      return `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary); width: 40px; text-align: center;">
            #${m.id}
          </td>
          <td>
            <div style="font-size: 12.5px; color: #fff; font-weight: 500;">
              ${escapeHtml(m.content)}
            </div>
          </td>
          <td>${regionBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Up" ${idx === 0 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSAnnouncements.moveMarquee(${idx}, -1)">▲</button>
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Down" ${idx === state.marquees.length - 1 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSAnnouncements.moveMarquee(${idx}, 1)">▼</button>
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSAnnouncements.toggleMarquee(${m.id}, ${isEnabled})">
                ${isEnabled ? 'Deactivate' : 'Activate'}
              </button>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSAnnouncements.openEditMarquee(${m.id})">
                Edit
              </button>
              <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSAnnouncements.deleteMarquee(${m.id})">
                Delete
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    canvas.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">

        <!-- Live Running Marquee Ticker Strip Simulator -->
        <div style="background: rgba(10, 16, 28, 0.7); border: 1px solid var(--border-default); border-radius: 10px; overflow: hidden;">
          <div style="display: flex; align-items: center; border-bottom: 1px solid var(--border-subtle); padding: 8px 16px; background: rgba(0,0,0,0.3);">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge badge-amber" style="font-size: 10px; font-weight: 700;">LIVE MARQUEE TICKER</span>
              <span style="font-size: 11px; color: var(--text-tertiary);">In-game top marquee broadcast strip</span>
            </div>
            <div style="margin-left: auto; display: flex; align-items: center; gap: 10px;">
              <label style="font-size: 11px; color: var(--text-tertiary);">Speed:</label>
              <select class="form-input" style="padding: 2px 6px; font-size: 11px; width: auto;" onchange="window.CMSAnnouncements.setSpeed(parseInt(this.value, 10))">
                <option value="36" ${state.marqueeSpeed === 36 ? 'selected' : ''}>Slow (36s)</option>
                <option value="24" ${state.marqueeSpeed === 24 ? 'selected' : ''}>Normal (24s)</option>
                <option value="14" ${state.marqueeSpeed === 14 ? 'selected' : ''}>Fast (14s)</option>
              </select>
              <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 11px;" onclick="window.CMSAnnouncements.toggleMarqueeAnimation()">
                ${state.marqueePlaying ? '⏸ Pause' : '▶ Play'}
              </button>
            </div>
          </div>

          <!-- Animated Marquee Track -->
          <div style="height: 42px; position: relative; overflow: hidden; display: flex; align-items: center; background: #000;">
            <div id="marquee-track" style="white-space: nowrap; font-size: 13.5px; font-weight: 600; color: var(--accent-amber); letter-spacing: 0.03em; animation: scrollMarquee ${state.marqueeSpeed}s linear infinite; ${!state.marqueePlaying ? 'animation-play-state: paused;' : ''}">
              ${escapeHtml(marqueeString)} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ✦ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${escapeHtml(marqueeString)}
            </div>
          </div>
          <style>
            @keyframes scrollMarquee {
              0% { transform: translateX(100%); }
              100% { transform: translateX(-100%); }
            }
          </style>
        </div>

        <!-- Quick Marquee Dispatch Strip -->
        <div class="glass-card" style="padding: 14px 18px;">
          <div style="display: flex; gap: 12px; align-items: center;">
            <div style="flex: 1;">
              <input type="text" id="quick-marquee-input" class="form-input" placeholder="Type a message to immediately broadcast across all game client marquees..." style="font-size: 13px;">
            </div>
            <button class="btn btn-primary" onclick="window.CMSAnnouncements.quickBroadcast()">
              ⚡ Broadcast Marquee
            </button>
            <button class="btn btn-secondary" onclick="window.CMSAnnouncements.openCreateMarqueeModal()">
              + Add to Queue
            </button>
          </div>
        </div>

        <!-- Summary Metric Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Published Notices</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-emerald); margin: 3px 0;">
              ${activeNews} <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ ${totalNews} total</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">In-game Bulletin Board news</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Marquee Sequence</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-amber); margin: 3px 0;">
              ${activeMqs.length} <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ ${state.marquees.length} messages</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">Cycling in active ticker strip</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default); display: flex; flex-direction: column; justify-content: center; gap: 8px;">
            <button class="btn btn-primary" onclick="window.CMSAnnouncements.openCreateNewsModal()" style="width: 100%;">+ New Announcement</button>
            <button class="btn btn-secondary" onclick="window.CMSAnnouncements.reload()" style="width: 100%;">🔄 Refresh Feeds</button>
          </div>
        </div>

        <!-- 1.39 In-Game Bulletin Board Simulator (Responsive 1366x768 to 4K) -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Free Fire 1.39 Bulletin Board Simulator</div>
              <div class="glass-card-subtitle">In-game news center interface rendered inside the client Notice dialog</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-primary" onclick="window.CMSAnnouncements.openCreateNewsModal()">+ New Notice</button>
            </div>
          </div>

          <div class="glass-card-body">
            <div style="display: flex; flex-wrap: wrap; gap: 16px; min-height: 320px; background: rgba(10, 16, 28, 0.5); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden;">
              
              <!-- Left Sidebar: News Tab List -->
              <div style="flex: 1 1 220px; max-width: 280px; min-width: 200px; border-right: 1px solid var(--border-subtle); background: rgba(0,0,0,0.25); display: flex; flex-direction: column;">
                <div style="padding: 10px 14px; font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; border-bottom: 1px solid var(--border-subtle);">
                  Game Announcements
                </div>
                <div style="flex: 1; overflow-y: auto; max-height: 400px;">
                  ${state.announcements.map(item => `
                    <div style="padding: 12px 14px; border-bottom: 1px solid rgba(255,255,255,0.04); cursor: pointer; transition: background 0.15s; ${item.id === (selectedArticle ? selectedArticle.id : 0) ? 'background: rgba(56, 189, 248, 0.12); border-left: 3px solid var(--accent-cyan);' : ''}" onclick="window.CMSAnnouncements.selectArticle(${item.id})">
                      <div style="font-size: 12px; font-weight: 600; color: #fff; margin-bottom: 3px; line-height: 1.3;">${escapeHtml(item.title)}</div>
                      <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: var(--text-tertiary);">
                        <span>${item.enabled !== false ? '● Published' : '○ Draft'}</span>
                        <span style="font-family: var(--font-mono);">${getNavLabel(item.gos_pos).split('—')[0].trim()}</span>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>

              <!-- Right Pane: Selected Article Content -->
              <div style="flex: 2 1 340px; min-width: min(100%, 280px); display: flex; flex-direction: column; overflow-y: auto; padding: 20px;">
                ${selectedArticle ? `
                  <div style="width: 100%; height: 160px; background: #000; border-radius: 8px; overflow: hidden; margin-bottom: 16px; border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center;">
                    <img src="${escapeHtml(selectedArticle.image_url)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/banners/announce_welcome.png'">
                  </div>

                  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                      <h2 style="font-size: 17px; font-weight: 700; color: #fff; margin-bottom: 4px;">${escapeHtml(selectedArticle.title)}</h2>
                      <div style="font-size: 11px; color: var(--text-tertiary);">Published in Bulletin Board • Category: Announcement</div>
                    </div>
                    <div>
                      ${window.UI.Badge(getNavLabel(selectedArticle.gos_pos), 'cyan')}
                    </div>
                  </div>

                  <div style="font-size: 12.5px; line-height: 1.7; color: var(--text-secondary); white-space: pre-wrap; flex: 1; margin-bottom: 16px;">
                    ${escapeHtml(selectedArticle.desc || 'No detailed content written for this notice.')}
                  </div>

                  <div style="display: flex; gap: 10px; justify-content: flex-end; border-top: 1px solid var(--border-subtle); padding-top: 14px;">
                    <button class="btn btn-secondary" onclick="window.CMSAnnouncements.openEditNews(${selectedArticle.id})">Edit Notice</button>
                    <button class="btn btn-primary" onclick="window.UI.Toast('Testing client navigation -> ' + '${escapeHtml(getNavLabel(selectedArticle.gos_pos))}', 'info')">
                      Action: ${getNavLabel(selectedArticle.gos_pos)}
                    </button>
                  </div>
                ` : `
                  <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary);">
                    No announcement selected
                  </div>
                `}
              </div>

            </div>
          </div>
        </div>

        <!-- Announcements Management Table with Responsive Container -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">In-Game Announcements Manager</div>
              <div class="glass-card-subtitle">Published bulletin board articles pushed to game clients</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="window.CMSAnnouncements.resetAnnouncements()">Reset Defaults</button>
              <button class="btn btn-primary" onclick="window.CMSAnnouncements.openCreateNewsModal()">+ Add Announcement</button>
            </div>
          </div>

          <div class="glass-card-body">
            <div class="glass-table-container">
              ${window.UI.Table(['ID', 'Preview', 'Notice Title & Snippet', 'Jump Target', 'Status', 'Order', 'Actions'], newsRows, 'No announcements registered.')}
            </div>
          </div>
        </div>

        <!-- Marquee Ticker Messages Table with Responsive Container -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Marquee Ticker Broadcast Queue</div>
              <div class="glass-card-subtitle">Active rotating banner text strings served to <code>/api/dashboard/cms</code> under <code>marquees</code></div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="window.CMSAnnouncements.resetMarquees()">Reset Defaults</button>
              <button class="btn btn-primary" onclick="window.CMSAnnouncements.openCreateMarqueeModal()">+ Add Marquee Text</button>
            </div>
          </div>

          <div class="glass-card-body">
            <div class="glass-table-container">
              ${window.UI.Table(['ID', 'Ticker Text Content', 'Region', 'Status', 'Order', 'Actions'], marqueeRows, 'No marquee messages in broadcast queue.')}
            </div>
          </div>
        </div>

      </div>
    `;
  }

  // --- PUBLIC API EXPORT ---
  window.CMSAnnouncements = {
    async init(canvas) {
      await loadData();
      await render(canvas);
    },
    async reload() {
      await loadData();
      render(document.getElementById('workspace-canvas'));
      window.UI.Toast('Announcements synchronized', 'info');
    },
    selectArticle(id) {
      state.selectedNewsId = id;
      render(document.getElementById('workspace-canvas'));
    },
    quickBroadcast() {
      const input = document.getElementById('quick-marquee-input');
      if (input) {
        quickUpdateMarquee(input.value);
        input.value = '';
      }
    },
    toggleMarqueeAnimation() {
      state.marqueePlaying = !state.marqueePlaying;
      const el = document.getElementById('marquee-track');
      if (el) {
        el.style.animationPlayState = state.marqueePlaying ? 'running' : 'paused';
      }
      render(document.getElementById('workspace-canvas'));
    },
    setSpeed(seconds) {
      state.marqueeSpeed = seconds;
      render(document.getElementById('workspace-canvas'));
    },
    toggleNews: toggleAnnouncement,
    deleteNews: deleteAnnouncement,
    moveNews: moveAnnouncement,
    openCreateNewsModal() {
      openAnnouncementModal(null);
    },
    openEditNews(id) {
      const a = state.announcements.find(item => item.id === id);
      if (a) openAnnouncementModal(a);
    },
    toggleMarquee,
    deleteMarquee,
    moveMarquee,
    openCreateMarqueeModal() {
      openMarqueeModal(null);
    },
    openEditMarquee(id) {
      const m = state.marquees.find(item => item.id === id);
      if (m) openMarqueeModal(m);
    },
    resetAnnouncements() {
      resetCategory('announcements');
    },
    resetMarquees() {
      resetCategory('marquees');
    }
  };

  // Register in SPA Router
  if (window.appRouter) {
    window.appRouter.register('#/cms/announcements', async (canvas) => {
      await window.CMSAnnouncements.init(canvas);
    });
  }

  // Expose on Modules namespace
  window.Modules = window.Modules || {};
  window.Modules.CMSAnnouncements = window.CMSAnnouncements.init;

})();
