/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: 08.1 Billboard Banner Manager (#/cms/banners)
 * 
 * Features:
 * - Live Free Fire 1.39 Lobby Billboard Carousel Simulator (Responsive 1366x768 to 4K)
 * - Interactive Drag & Drop / File Image Uploader (Multipart & Base64 with UI.Modal)
 * - Banner Asset Gallery with Instant URL Clipboard Copy & Deletion
 * - Real-time Priority Reordering (Move Up / Down) with /api/dashboard/cms/reorder
 * - Instant Active Status Toggling with /api/dashboard/cms/toggle
 * - Billboard Ad Slot CRUD with FF 1.39 Navigation Jump Target Presets
 * - Responsive .glass-table-container Horizontal Containment
 * - Apple macOS/iPadOS Dark Glassmorphism Design
 */

(function () {
  'use strict';

  // Navigation targets reverse-engineered from Free Fire 1.39 IL2CPP
  const NAV_DESTINATIONS = [
    { id: 0, label: '0 — Dismiss / None', desc: 'No action or closes dialog' },
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
    adverts: [],
    banners: [],
    activeAdIndex: 0,
    carouselTimer: null,
    carouselPlaying: true,
    editingAdId: null,
    isLoading: false,
    searchQuery: '',
    galleryFilter: ''
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
        window.apiClient.get('/api/dashboard/cms', { category: 'adverts' }),
        window.apiClient.get('/api/dashboard/cms/banners')
      ]);

      if (cmsRes.ok && cmsRes.data) {
        state.adverts = cmsRes.data.items || (cmsRes.data.cms && cmsRes.data.cms.adverts) || [];
      }
      if (bannerRes.ok && bannerRes.data) {
        state.banners = bannerRes.data.banners || [];
      }
    } catch (e) {
      console.error('Error loading billboard banner data', e);
      window.UI.Toast('Failed to load banner telemetry: ' + e.message, 'error');
    } finally {
      state.isLoading = false;
    }
  }

  // --- UPLOAD HANDLER (Supports Multipart & Base64) ---
  async function uploadImageFile(file) {
    if (!file) return;
    window.UI.Toast(`Uploading ${file.name}...`, 'info');

    // 1. Read Base64 payload
    const base64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    // 2. Attempt JSON base64 upload to /api/dashboard/cms/upload_banner
    let res = await window.apiClient.post('/api/dashboard/cms/upload_banner', {
      filename: file.name,
      data_base64: base64
    });

    // 3. Fallback to multipart FormData if needed
    if (!res.ok) {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('name', file.name);
      res = await window.apiClient.upload('/api/dashboard/cms/banner/upload', fd);
    }

    if (res.ok) {
      window.UI.Toast(`Uploaded ${file.name} successfully`, 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast(`Upload failed: ${res.error || 'Server rejected file'}`, 'error');
    }
  }

  // --- ACTIONS ---
  async function toggleAd(adId, currentStatus) {
    const res = await window.apiClient.post('/api/dashboard/cms/toggle', {
      category: 'adverts',
      id: adId,
      enabled: !currentStatus
    });

    if (res.ok) {
      window.UI.Toast(`Billboard Ad #${adId} ${!currentStatus ? 'Activated' : 'Deactivated'}`, 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Failed to toggle ad: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function deleteAd(adId) {
    window.UI.Confirm(
      'Delete Billboard Ad Spot',
      `Are you sure you want to remove Billboard Ad #${adId} from the rotation? This will remove the banner from client lobbies.`,
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/delete', {
          category: 'adverts',
          id: adId
        });
        if (res.ok) {
          window.UI.Toast(`Deleted Billboard Ad #${adId}`, 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Failed to delete ad: ' + (res.error || 'Server error'), 'error');
        }
      },
      true
    );
  }

  async function deleteBannerAsset(filename) {
    window.UI.Confirm(
      'Delete Image Asset',
      `Permanently delete the image file <code>${escapeHtml(filename)}</code> from the server? Any ad or splash referencing this file will show a missing asset.`,
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/delete_banner', {
          filename: filename
        });
        if (res.ok) {
          window.UI.Toast(`Removed ${filename}`, 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Failed to delete asset: ' + (res.error || 'Server error'), 'error');
        }
      },
      true
    );
  }

  async function moveAd(index, direction) {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= state.adverts.length) return;

    const list = [...state.adverts];
    const item = list.splice(index, 1)[0];
    list.splice(targetIdx, 0, item);

    const orderedIds = list.map(a => a.id);
    const res = await window.apiClient.post('/api/dashboard/cms/reorder', {
      category: 'adverts',
      ordered_ids: orderedIds
    });

    if (res.ok) {
      window.UI.Toast('Billboard priority order updated', 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Reordering failed: ' + (res.error || 'Server error'), 'error');
    }
  }

  function openUploadModal() {
    const bodyHtml = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div id="modal-banner-drop" style="border: 2px dashed var(--border-default); border-radius: 10px; padding: 28px; text-align: center; background: rgba(10, 16, 28, 0.4); cursor: pointer; transition: border-color 0.2s;" onclick="document.getElementById('modal-upload-input').click()" ondragover="event.preventDefault(); this.style.borderColor='var(--accent-cyan)';" ondragleave="this.style.borderColor='var(--border-default)';" ondrop="event.preventDefault(); this.style.borderColor='var(--border-default)'; if(event.dataTransfer.files[0]) { window.CMSBanners.handleFileUpload(event.dataTransfer.files[0]); document.getElementById('global-modal-overlay')?.remove(); }">
          <div style="font-size: 32px; opacity: 0.6; margin-bottom: 8px;">📁</div>
          <div style="font-size: 13.5px; font-weight: 500; color: #fff;">Click or Drag & Drop Banner Here</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 6px;">PNG, JPG, or JPEG up to 10 MB. High-res 16:9 billboard textures recommended.</div>
          <input type="file" id="modal-upload-input" accept="image/png,image/jpeg,image/jpg" style="display: none;" onchange="if(this.files[0]) { window.CMSBanners.handleFileUpload(this.files[0]); document.getElementById('global-modal-overlay')?.remove(); }">
        </div>
      </div>
    `;
    window.UI.Modal('Upload Banner Texture', bodyHtml, '<button class="btn btn-secondary" onclick="document.getElementById(\'global-modal-overlay\').remove()">Cancel</button>');
  }

  function openUpsertModal(ad = null) {
    const isEdit = !!ad;
    const title = isEdit ? `Edit Billboard Ad #${ad.id}` : 'Create New Billboard Ad';
    const currentName = ad ? (ad.name || `Ad #${ad.id}`) : '';
    const currentUrl = ad ? (ad.advertisment_url || '') : '';
    const currentGoPos = ad ? (ad.go_pos || 0) : 0;
    const currentLink = ad ? (ad.link_url || '') : '';
    const currentEnabled = ad ? (ad.enabled !== false) : true;
    const currentSort = ad ? (ad.sort_id || 1) : (state.adverts.length + 1);

    const bannerOptions = state.banners.map(b => `
      <option value="${b.url}" ${b.url === currentUrl ? 'selected' : ''}>${b.name} (${Math.round(b.size / 1024)} KB)</option>
    `).join('');

    const navOptions = NAV_DESTINATIONS.map(d => `
      <option value="${d.id}" ${d.id === parseInt(currentGoPos, 10) ? 'selected' : ''}>${d.label} — ${d.desc}</option>
    `).join('');

    const bodyHtml = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Ad Title / Campaign Label</label>
          <input type="text" id="modal-ad-name" class="form-input" placeholder="e.g. Winterlands Royale Banner" value="${escapeHtml(currentName)}">
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Select Banner Texture Asset</label>
          <select id="modal-ad-banner-select" class="form-input" onchange="document.getElementById('modal-ad-url').value = this.value; document.getElementById('modal-ad-preview-img').src = this.value;">
            <option value="">-- Select from Uploaded Gallery --</option>
            ${bannerOptions}
          </select>
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Image Resource Path / URL</label>
          <input type="text" id="modal-ad-url" class="form-input" placeholder="e.g. /banners/lobby_ad_1.png" value="${escapeHtml(currentUrl)}" oninput="document.getElementById('modal-ad-preview-img').src = this.value;">
        </div>

        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px; display: flex; align-items: center; gap: 12px;">
          <div style="width: 140px; height: 78px; background: #000; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-default);">
            <img id="modal-ad-preview-img" src="${currentUrl || '/banners/lobby_ad_1.png'}" style="max-width: 100%; max-height: 100%; object-fit: cover;" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%2260%22><rect width=%22100%22 height=%2260%22 fill=%22%23111%22/><text x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23555%22 font-size=%2210%22>No Image</text></svg>'">
          </div>
          <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
            <strong>Texture Spec:</strong> 16:9 aspect ratio (approx 1024x576 or 800x450).<br>
            Texture auto-resizes to fit client billboard frame in Waiting Island & Lobby.
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">In-Game Jump Destination (go_pos)</label>
            <select id="modal-ad-go-pos" class="form-input">
              ${navOptions}
            </select>
          </div>
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Sort Priority</label>
            <input type="number" id="modal-ad-sort" class="form-input" value="${currentSort}">
          </div>
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Deep Link / External Target (link_url / sub_go_pos)</label>
          <input type="text" id="modal-ad-link" class="form-input" placeholder="e.g. 1,6 or https://event.ff.garena.com" value="${escapeHtml(currentLink)}">
        </div>

        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
          <input type="checkbox" id="modal-ad-enabled" style="accent-color: var(--accent-cyan); width: 16px; height: 16px;" ${currentEnabled ? 'checked' : ''}>
          <label for="modal-ad-enabled" style="font-size: 12.5px; color: var(--text-primary); cursor: pointer;">Enable this ad immediately in lobby carousel</label>
        </div>
      </div>
    `;

    const footerButtonsHtml = `
      <button class="btn btn-primary" id="modal-save-btn">Save Billboard Ad</button>
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Cancel</button>
    `;

    window.UI.Modal(title, bodyHtml, footerButtonsHtml);

    document.getElementById('modal-save-btn').onclick = async () => {
      const name = document.getElementById('modal-ad-name').value.trim() || 'Untitled Banner';
      const url = document.getElementById('modal-ad-url').value.trim();
      const goPos = parseInt(document.getElementById('modal-ad-go-pos').value, 10) || 0;
      const sortId = parseInt(document.getElementById('modal-ad-sort').value, 10) || 1;
      const linkUrl = document.getElementById('modal-ad-link').value.trim();
      const enabled = document.getElementById('modal-ad-enabled').checked;

      if (!url) {
        window.UI.Toast('Please select or specify a banner image URL', 'warning');
        return;
      }

      const payload = {
        category: 'adverts',
        item: {
          ...(ad || {}),
          name: name,
          advertisment_url: url,
          go_pos: goPos,
          sort_id: sortId,
          link_url: linkUrl,
          enabled: enabled,
          go_to_switch: true
        }
      };

      const res = await window.apiClient.post('/api/dashboard/cms/upsert', payload);
      if (res.ok) {
        window.UI.Toast(`Billboard Ad ${isEdit ? 'updated' : 'created'} successfully`, 'success');
        document.getElementById('global-modal-overlay').remove();
        await loadData();
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Error saving ad: ' + (res.error || 'Server error'), 'error');
      }
    };
  }

  // --- SIMULATOR CONTROLS ---
  function nextAd() {
    const activeAds = state.adverts.filter(a => a.enabled !== false);
    if (!activeAds.length) return;
    state.activeAdIndex = (state.activeAdIndex + 1) % activeAds.length;
    updateSimulatorDOM();
  }

  function prevAd() {
    const activeAds = state.adverts.filter(a => a.enabled !== false);
    if (!activeAds.length) return;
    state.activeAdIndex = (state.activeAdIndex - 1 + activeAds.length) % activeAds.length;
    updateSimulatorDOM();
  }

  function toggleCarouselPlay() {
    state.carouselPlaying = !state.carouselPlaying;
    if (state.carouselPlaying) {
      startCarouselTimer();
      window.UI.Toast('Carousel auto-play resumed', 'info');
    } else {
      clearInterval(state.carouselTimer);
      window.UI.Toast('Carousel paused', 'info');
    }
    const btn = document.getElementById('sim-play-btn');
    if (btn) btn.textContent = state.carouselPlaying ? '⏸ Pause' : '▶ Play';
  }

  function startCarouselTimer() {
    clearInterval(state.carouselTimer);
    if (state.carouselPlaying) {
      state.carouselTimer = setInterval(() => {
        nextAd();
      }, 4200);
    }
  }

  function updateSimulatorDOM() {
    const activeAds = state.adverts.filter(a => a.enabled !== false);
    const container = document.getElementById('sim-ad-frame');
    const badge = document.getElementById('sim-nav-badge');
    const indicator = document.getElementById('sim-indicator');
    const titleEl = document.getElementById('sim-title');

    if (!container) return;

    if (!activeAds.length) {
      container.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary);">
          <div style="font-size: 24px; opacity: 0.5; margin-bottom: 8px;">🎨</div>
          <div style="font-size: 13px; font-weight: 500;">No Active Billboard Ads</div>
          <div style="font-size: 11px;">Activate or create an ad below to preview</div>
        </div>
      `;
      if (badge) badge.style.display = 'none';
      if (indicator) indicator.textContent = '0 / 0';
      if (titleEl) titleEl.textContent = 'No Ad Active';
      return;
    }

    if (state.activeAdIndex >= activeAds.length) {
      state.activeAdIndex = 0;
    }

    const cur = activeAds[state.activeAdIndex];
    container.innerHTML = `
      <img src="${escapeHtml(cur.advertisment_url)}" style="width: 100%; height: 100%; object-fit: cover; transition: opacity 0.3s ease-in-out;" onerror="this.src='/banners/lobby_ad_1.png'">
    `;

    if (badge) {
      badge.style.display = 'inline-flex';
      badge.textContent = getNavLabel(cur.go_pos);
    }
    if (indicator) {
      indicator.textContent = `${state.activeAdIndex + 1} / ${activeAds.length}`;
    }
    if (titleEl) {
      titleEl.textContent = cur.name || `Ad #${cur.id}`;
    }
  }

  // --- MAIN RENDER ---
  async function render(canvas) {
    if (!canvas) return;

    // Build Quick Stats
    const totalSlots = state.adverts.length;
    const activeSlots = state.adverts.filter(a => a.enabled !== false).length;
    const totalAssets = state.banners.length;

    // Build Table Rows
    const rowsHtml = state.adverts.map((ad, idx) => {
      const isEnabled = ad.enabled !== false;
      const navBadge = window.UI.Badge(getNavLabel(ad.go_pos), ad.go_pos > 0 ? 'cyan' : 'neutral');
      const statusBadge = isEnabled ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('DISABLED', 'neutral');

      return `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary); width: 40px; text-align: center;">
            #${ad.id}
          </td>
          <td style="width: 80px;">
            <div style="width: 72px; height: 40px; border-radius: 4px; overflow: hidden; background: #000; border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center;">
              <img src="${escapeHtml(ad.advertisment_url)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/banners/lobby_ad_1.png'">
            </div>
          </td>
          <td>
            <div style="font-weight: 600; color: #fff; font-size: 13px;">${escapeHtml(ad.name || `Ad #${ad.id}`)}</div>
            <div style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);">${escapeHtml(ad.advertisment_url)}</div>
          </td>
          <td>${navBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Up" ${idx === 0 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSBanners.moveAd(${idx}, -1)">▲</button>
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Down" ${idx === state.adverts.length - 1 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSBanners.moveAd(${idx}, 1)">▼</button>
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSBanners.toggleAd(${ad.id}, ${isEnabled})">
                ${isEnabled ? 'Deactivate' : 'Activate'}
              </button>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSBanners.openEditModal(${ad.id})">
                Edit
              </button>
              <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSBanners.deleteAd(${ad.id})">
                Delete
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Build Gallery Cards
    const galleryHtml = state.banners.map(b => {
      const sizeKb = Math.round(b.size / 1024);
      return `
        <div style="background: rgba(10, 16, 28, 0.5); border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column;">
          <div style="height: 110px; background: #000; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center;">
            <img src="${escapeHtml(b.url)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/banners/lobby_ad_1.png'">
            <div style="position: absolute; bottom: 4px; right: 4px; background: rgba(0,0,0,0.7); font-size: 9.5px; font-family: var(--font-mono); padding: 1px 5px; border-radius: 3px; color: var(--text-secondary);">
              ${sizeKb} KB
            </div>
          </div>
          <div style="padding: 8px 10px; flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
            <div style="font-weight: 500; font-size: 11.5px; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(b.name)}">
              ${escapeHtml(b.name)}
            </div>
            <div style="display: flex; gap: 6px; margin-top: 8px;">
              <button class="btn btn-secondary" style="flex: 1; padding: 2px 4px; font-size: 10.5px;" onclick="navigator.clipboard.writeText('${escapeHtml(b.url)}'); window.UI.Toast('Copied texture URL to clipboard', 'info');">
                Copy URL
              </button>
              <button class="btn btn-secondary" style="flex: 1; padding: 2px 4px; font-size: 10.5px;" onclick="window.CMSBanners.createAdWithUrl('${escapeHtml(b.url)}', '${escapeHtml(b.name)}')">
                + Use in Ad
              </button>
              <button class="btn btn-danger" style="padding: 2px 6px; font-size: 10.5px;" onclick="window.CMSBanners.deleteBannerAsset('${escapeHtml(b.name)}')">
                ✕
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    canvas.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        
        <!-- Summary Stats Strip -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Active Rotation</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-emerald); margin: 3px 0;">
              ${activeSlots} <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ ${totalSlots} total</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">Currently displayed in lobby</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Texture Assets</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-cyan); margin: 3px 0;">
              ${totalAssets}
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">Images in server/static/banners/</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Carousel Auto-Play</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-amber); margin: 3px 0;">
              ${state.carouselPlaying ? 'Active' : 'Paused'}
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">4.2s cycle interval</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default); display: flex; flex-direction: column; justify-content: center; gap: 8px;">
            <button class="btn btn-primary" onclick="window.CMSBanners.openCreateModal()" style="width: 100%;">+ Add Billboard Ad</button>
            <button class="btn btn-secondary" onclick="window.CMSBanners.openUploadDialog()" style="width: 100%;">📁 Upload Banner Image</button>
            <input type="file" id="banner-file-input" accept="image/png,image/jpeg,image/jpg" style="display: none;" onchange="window.CMSBanners.handleFileUpload(this.files[0])">
          </div>
        </div>

        <!-- 1.39 Lobby Billboard Live Simulator (Responsive Scaling for 1366x768 to 4K) -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Free Fire 1.39 Lobby Billboard Simulator</div>
              <div class="glass-card-subtitle">Real-time simulation of client billboard renderer (Waiting Island & Lobby)</div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span id="sim-nav-badge" class="badge badge-cyan" style="font-size: 11px;">Store / Mall</span>
              <span id="sim-indicator" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">1 / ${Math.max(1, activeSlots)}</span>
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.CMSBanners.prevAd()">◀ Prev</button>
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" id="sim-play-btn" onclick="window.CMSBanners.togglePlay()">${state.carouselPlaying ? '⏸ Pause' : '▶ Play'}</button>
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.CMSBanners.nextAd()">Next ▶</button>
            </div>
          </div>

          <div class="glass-card-body">
            <div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: stretch;">
              <!-- 16:9 Display Stage -->
              <div style="flex: 1 1 480px; min-width: min(100%, 320px); height: 260px; background: radial-gradient(circle at center, #111a2e 0%, #060a14 100%); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; position: relative; box-shadow: 0 8px 24px rgba(0,0,0,0.5);">
                <div id="sim-ad-frame" style="width: 100%; height: 100%; cursor: pointer;" onclick="window.CMSBanners.simulateClick()" title="Click to test navigation jump">
                  <!-- Injected by updateSimulatorDOM -->
                </div>
                
                <div style="position: absolute; bottom: 12px; left: 16px; background: rgba(0,0,0,0.65); backdrop-filter: blur(8px); padding: 4px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);">
                  <div style="font-size: 12px; font-weight: 600; color: #fff;" id="sim-title">Featured Ad</div>
                </div>

                <div style="position: absolute; top: 12px; right: 14px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); color: var(--accent-cyan); font-size: 10px; font-family: var(--font-mono); padding: 2px 7px; border-radius: 4px;">
                  1.39 RENDERER
                </div>
              </div>

              <!-- Simulator Telemetry Info -->
              <div style="flex: 1 1 260px; min-width: min(100%, 240px); background: rgba(10, 16, 28, 0.4); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 10px;">
                <div>
                  <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Simulation Telemetry</div>
                  <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.6;">
                    • <strong>Cycle Period:</strong> 4.2 seconds auto-scroll<br>
                    • <strong>Interaction:</strong> Click billboard image to trigger <code>S2C_Navigate</code> event<br>
                    • <strong>Resolution:</strong> Rendered in native 16:9 lobby proportions<br>
                    • <strong>Asset Base:</strong> <code>http://127.0.0.1:8080/banners/...</code>
                  </div>
                </div>
                <div>
                  <button class="btn btn-secondary" style="width: 100%; font-size: 11.5px;" onclick="window.CMSBanners.simulateClick()">
                    ⚡ Test Navigation Jump
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Billboard Ad Management Table with Responsive Container -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Billboard Ad Rotation Queue</div>
              <div class="glass-card-subtitle">Active and queued campaign spots served to <code>/api/dashboard/cms/banners</code></div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="window.CMSBanners.reload()">🔄 Refresh</button>
              <button class="btn btn-primary" onclick="window.CMSBanners.openCreateModal()">+ Add Ad Slot</button>
            </div>
          </div>

          <div class="glass-card-body">
            <div class="glass-table-container">
              ${window.UI.Table(['ID', 'Preview', 'Campaign / Texture', 'Jump Destination', 'Status', 'Priority', 'Actions'], rowsHtml, 'No Billboard Ads configured yet. Click "+ Add Ad Slot" to start.')}
            </div>
          </div>
        </div>

        <!-- Image Asset Gallery & Uploader -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Banner Image Texture Repository</div>
              <div class="glass-card-subtitle">Uploaded graphic assets saved on disk in <code>server/static/banners/</code></div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-primary" onclick="window.CMSBanners.openUploadDialog()">+ Upload Image Asset</button>
            </div>
          </div>

          <div class="glass-card-body">
            <!-- Drag and Drop Zone -->
            <div id="banner-drop-zone" style="border: 2px dashed var(--border-default); border-radius: 10px; padding: 24px; text-align: center; margin-bottom: 20px; background: rgba(10, 16, 28, 0.3); transition: all 0.2s;" ondragover="event.preventDefault(); this.style.borderColor='var(--accent-cyan)';" ondragleave="this.style.borderColor='var(--border-default)';" ondrop="event.preventDefault(); this.style.borderColor='var(--border-default)'; window.CMSBanners.handleFileUpload(event.dataTransfer.files[0]);">
              <div style="font-size: 26px; opacity: 0.6; margin-bottom: 6px;">📥</div>
              <div style="font-size: 13px; font-weight: 500; color: #fff;">Drag & Drop Banner Files Here</div>
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">PNG, JPG, or JPEG up to 10 MB. High-res 16:9 billboard textures recommended.</div>
            </div>

            <!-- Assets Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px;">
              ${galleryHtml}
            </div>
          </div>
        </div>

      </div>
    `;

    // Start or update simulator frame
    updateSimulatorDOM();
    startCarouselTimer();
  }

  // --- PUBLIC API EXPORT ---
  window.CMSBanners = {
    async init(canvas) {
      await loadData();
      await render(canvas);
    },
    async reload() {
      await loadData();
      render(document.getElementById('workspace-canvas'));
      window.UI.Toast('Banner state synchronized', 'info');
    },
    toggleAd,
    deleteAd,
    deleteBannerAsset,
    moveAd,
    nextAd,
    prevAd,
    togglePlay: toggleCarouselPlay,
    openCreateModal() {
      openUpsertModal(null);
    },
    openEditModal(adId) {
      const ad = state.adverts.find(a => a.id === adId);
      if (ad) openUpsertModal(ad);
    },
    openUploadDialog: openUploadModal,
    createAdWithUrl(url, name) {
      openUpsertModal({
        name: name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '),
        advertisment_url: url,
        go_pos: 3,
        enabled: true
      });
    },
    handleFileUpload(file) {
      uploadImageFile(file);
    },
    simulateClick() {
      const activeAds = state.adverts.filter(a => a.enabled !== false);
      if (!activeAds.length) return;
      const cur = activeAds[state.activeAdIndex];
      window.UI.Toast(`[Simulator] Fired S2C_Navigate -> ${getNavLabel(cur.go_pos)} (${cur.link_url || 'default'})`, 'success');
    }
  };

  // Register in SPA Router
  if (window.appRouter) {
    window.appRouter.register('#/cms/banners', async (canvas) => {
      await window.CMSBanners.init(canvas);
    });
  }

  // Expose on Modules namespace
  window.Modules = window.Modules || {};
  window.Modules.CMSBanners = window.CMSBanners.init;

})();
