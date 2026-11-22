/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: 08.2 Lobby CMS & Splash Manager (#/cms/lobby)
 * 
 * Features:
 * - Free Fire 1.39 Startup Splash Popup Simulator (Responsive Mobile Frame for 1366x768+)
 * - Cache-Busting Force-Show Controller (/api/dashboard/cms/bump_splashes)
 * - Splash Sequence Queue Reordering (Move Up / Down) with /api/dashboard/cms/reorder
 * - Instant Active Status Toggling with /api/dashboard/cms/toggle
 * - Full Splash CRUD with FF 1.39 In-Game Action Destinations (gos_pos)
 * - Integrated Image Asset Selector & Multipart/Base64 Uploader with UI.Modal
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
    splashes: [],
    banners: [],
    activeSplashIndex: 0,
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
        window.apiClient.get('/api/dashboard/cms', { category: 'splashes' }),
        window.apiClient.get('/api/dashboard/cms/banners')
      ]);

      if (cmsRes.ok && cmsRes.data) {
        state.splashes = cmsRes.data.items || (cmsRes.data.cms && cmsRes.data.cms.splashes) || [];
      }
      if (bannerRes.ok && bannerRes.data) {
        state.banners = bannerRes.data.banners || [];
      }
    } catch (e) {
      console.error('Error loading splash CMS data', e);
      window.UI.Toast('Failed to load splash telemetry: ' + e.message, 'error');
    } finally {
      state.isLoading = false;
    }
  }

  // --- UPLOAD HANDLER ---
  async function uploadImageFile(file, autoCreate = false) {
    if (!file) return;
    window.UI.Toast(`Uploading ${file.name}...`, 'info');

    const base64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    let res = await window.apiClient.post('/api/dashboard/cms/upload_banner', {
      filename: file.name,
      data_base64: base64
    });

    if (!res.ok) {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('name', file.name);
      res = await window.apiClient.upload('/api/dashboard/cms/banner/upload', fd);
    }

    if (res.ok) {
      window.UI.Toast(`Uploaded ${file.name} successfully`, 'success');
      await loadData();

      if (autoCreate) {
        openUpsertModal({
          name: file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '),
          image_url: `/banners/${file.name}`,
          bg_img_url: `/banners/${file.name}`,
          gos_pos: 7,
          enabled: true
        });
      } else {
        render(document.getElementById('workspace-canvas'));
      }
    } else {
      window.UI.Toast(`Upload failed: ${res.error || 'Server error'}`, 'error');
    }
  }

  // --- ACTIONS ---
  async function bumpVersions() {
    window.UI.Confirm(
      'Force-Show Splash Screens',
      'This action will increment the cache version of all active splash popups. Returning players whose game client previously dismissed these splashes will see them again on their next login or reconnect. Proceed?',
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/bump_splashes', {});
        if (res.ok) {
          window.UI.Toast('Client cache invalidated! All splash versions bumped.', 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Failed to bump splashes: ' + (res.error || 'Server error'), 'error');
        }
      }
    );
  }

  async function toggleSplash(splashId, currentStatus) {
    const res = await window.apiClient.post('/api/dashboard/cms/toggle', {
      category: 'splashes',
      id: splashId,
      enabled: !currentStatus
    });

    if (res.ok) {
      window.UI.Toast(`Splash #${splashId} ${!currentStatus ? 'Activated' : 'Deactivated'}`, 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Failed to toggle splash: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function deleteSplash(splashId) {
    window.UI.Confirm(
      'Delete Splash Screen',
      `Permanently delete Splash Popup #${splashId}? It will be removed from client startup sequences.`,
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/delete', {
          category: 'splashes',
          id: splashId
        });
        if (res.ok) {
          window.UI.Toast(`Deleted Splash #${splashId}`, 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Failed to delete splash: ' + (res.error || 'Server error'), 'error');
        }
      },
      true
    );
  }

  async function moveSplash(index, direction) {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= state.splashes.length) return;

    const list = [...state.splashes];
    const item = list.splice(index, 1)[0];
    list.splice(targetIdx, 0, item);

    const orderedIds = list.map(s => s.id);
    const res = await window.apiClient.post('/api/dashboard/cms/reorder', {
      category: 'splashes',
      ordered_ids: orderedIds
    });

    if (res.ok) {
      window.UI.Toast('Splash sequence order updated', 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Reordering failed: ' + (res.error || 'Server error'), 'error');
    }
  }

  async function resetSplashesToDefaults() {
    window.UI.Confirm(
      'Reset Splashes to Factory Seed',
      'Reset all startup splash screens to IND PROJECT default configuration? Custom splashes will be overwritten.',
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/reset', { category: 'splashes' });
        if (res.ok) {
          window.UI.Toast('Splashes restored to factory seed', 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        } else {
          window.UI.Toast('Reset failed: ' + (res.error || 'Server error'), 'error');
        }
      },
      true
    );
  }

  function openUploadModal() {
    const bodyHtml = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div id="modal-splash-drop" style="border: 2px dashed var(--border-default); border-radius: 10px; padding: 28px; text-align: center; background: rgba(10, 16, 28, 0.4); cursor: pointer; transition: border-color 0.2s;" onclick="document.getElementById('modal-splash-file-input').click()" ondragover="event.preventDefault(); this.style.borderColor='var(--accent-cyan)';" ondragleave="this.style.borderColor='var(--border-default)';" ondrop="event.preventDefault(); this.style.borderColor='var(--border-default)'; if(event.dataTransfer.files[0]) { window.CMSLobby.handleUpload(event.dataTransfer.files[0], true); document.getElementById('global-modal-overlay')?.remove(); }">
          <div style="font-size: 32px; opacity: 0.6; margin-bottom: 8px;">🖼️</div>
          <div style="font-size: 13.5px; font-weight: 500; color: #fff;">Click or Drag & Drop Splash Art Here</div>
          <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 6px;">PNG, JPG, or JPEG up to 10 MB. Image will automatically register as a new splash screen.</div>
          <input type="file" id="modal-splash-file-input" accept="image/png,image/jpeg,image/jpg" style="display: none;" onchange="if(this.files[0]) { window.CMSLobby.handleUpload(this.files[0], true); document.getElementById('global-modal-overlay')?.remove(); }">
        </div>
      </div>
    `;
    window.UI.Modal('Upload Splash Art', bodyHtml, '<button class="btn btn-secondary" onclick="document.getElementById(\'global-modal-overlay\').remove()">Cancel</button>');
  }

  function openUpsertModal(splash = null) {
    const isEdit = !!splash;
    const title = isEdit ? `Edit Splash Screen #${splash.id}` : 'Create New Startup Splash';
    const currentName = splash ? (splash.name || `Splash #${splash.id}`) : '';
    const currentImg = splash ? (splash.image_url || '') : '';
    const currentBg = splash ? (splash.bg_img_url || '') : '';
    const currentGosPos = splash ? (splash.gos_pos || 0) : 0;
    const currentLink = splash ? (splash.link_url || '') : '';
    const currentEnabled = splash ? (splash.enabled !== false) : true;
    const currentSort = splash ? (splash.sort_id || 1) : (state.splashes.length + 1);

    const bannerOptions = state.banners.map(b => `
      <option value="${b.url}" ${b.url === currentImg ? 'selected' : ''}>${b.name} (${Math.round(b.size / 1024)} KB)</option>
    `).join('');

    const navOptions = NAV_DESTINATIONS.map(d => `
      <option value="${d.id}" ${d.id === parseInt(currentGosPos, 10) ? 'selected' : ''}>${d.label} — ${d.desc}</option>
    `).join('');

    const bodyHtml = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Splash Screen Title / Campaign Name</label>
          <input type="text" id="modal-splash-name" class="form-input" placeholder="e.g. Bermuda 2019 Revival Launch" value="${escapeHtml(currentName)}">
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Select Graphic Asset from Gallery</label>
          <select id="modal-splash-select" class="form-input" onchange="document.getElementById('modal-splash-img').value = this.value; document.getElementById('modal-splash-bg').value = this.value; document.getElementById('modal-splash-preview-img').src = this.value;">
            <option value="">-- Choose from Server Repository --</option>
            ${bannerOptions}
          </select>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Foreground Art (image_url)</label>
            <input type="text" id="modal-splash-img" class="form-input" placeholder="/banners/splash_welcome.png" value="${escapeHtml(currentImg)}" oninput="document.getElementById('modal-splash-preview-img').src = this.value;">
          </div>
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Background Wallpaper (bg_img_url)</label>
            <input type="text" id="modal-splash-bg" class="form-input" placeholder="/banners/splash_welcome.png" value="${escapeHtml(currentBg)}">
          </div>
        </div>

        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px; display: flex; align-items: center; gap: 12px;">
          <div style="width: 140px; height: 80px; background: #000; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-default);">
            <img id="modal-splash-preview-img" src="${currentImg || '/banners/splash_welcome.png'}" style="max-width: 100%; max-height: 100%; object-fit: cover;" onerror="this.src='/banners/splash_welcome.png'">
          </div>
          <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
            <strong>Startup Screen Spec:</strong> Rendered as modal overlay upon major login.<br>
            Supports both portrait and landscape viewports with dark frosted blur backdrop.
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">On-Click Action (gos_pos)</label>
            <select id="modal-splash-gos-pos" class="form-input">
              ${navOptions}
            </select>
          </div>
          <div>
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Display Priority</label>
            <input type="number" id="modal-splash-sort" class="form-input" value="${currentSort}">
          </div>
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Target Link URL / Deep-Link</label>
          <input type="text" id="modal-splash-link" class="form-input" placeholder="e.g. https://event.ff.garena.com or 7,1" value="${escapeHtml(currentLink)}">
        </div>

        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
          <input type="checkbox" id="modal-splash-enabled" style="accent-color: var(--accent-cyan); width: 16px; height: 16px;" ${currentEnabled ? 'checked' : ''}>
          <label for="modal-splash-enabled" style="font-size: 12.5px; color: var(--text-primary); cursor: pointer;">Enable this splash popup in client login rotation</label>
        </div>
      </div>
    `;

    const footerButtonsHtml = `
      <button class="btn btn-primary" id="modal-splash-save-btn">Save Splash Screen</button>
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Cancel</button>
    `;

    window.UI.Modal(title, bodyHtml, footerButtonsHtml);

    document.getElementById('modal-splash-save-btn').onclick = async () => {
      const name = document.getElementById('modal-splash-name').value.trim() || 'Untitled Splash';
      const imgUrl = document.getElementById('modal-splash-img').value.trim();
      const bgUrl = document.getElementById('modal-splash-bg').value.trim() || imgUrl;
      const gosPos = parseInt(document.getElementById('modal-splash-gos-pos').value, 10) || 0;
      const sortId = parseInt(document.getElementById('modal-splash-sort').value, 10) || 1;
      const linkUrl = document.getElementById('modal-splash-link').value.trim();
      const enabled = document.getElementById('modal-splash-enabled').checked;

      if (!imgUrl) {
        window.UI.Toast('Please select or specify an image URL', 'warning');
        return;
      }

      const payload = {
        category: 'splashes',
        item: {
          ...(splash || {}),
          name: name,
          image_url: imgUrl,
          bg_img_url: bgUrl,
          gos_pos: gosPos,
          sort_id: sortId,
          link_url: linkUrl,
          enabled: enabled,
          version: splash ? (splash.version || 1) : 1
        }
      };

      const res = await window.apiClient.post('/api/dashboard/cms/upsert', payload);
      if (res.ok) {
        window.UI.Toast(`Splash Screen ${isEdit ? 'updated' : 'created'} successfully`, 'success');
        document.getElementById('global-modal-overlay').remove();
        await loadData();
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Error saving splash: ' + (res.error || 'Server error'), 'error');
      }
    };
  }

  // --- SIMULATOR DOM ---
  function updateSimulatorDOM() {
    const activeSplashes = state.splashes.filter(s => s.enabled !== false);
    const container = document.getElementById('splash-sim-body');
    const titleEl = document.getElementById('splash-sim-title');
    const badgeEl = document.getElementById('splash-sim-badge');
    const actionBtn = document.getElementById('splash-sim-action-btn');
    const counterEl = document.getElementById('splash-sim-counter');

    if (!container) return;

    if (!activeSplashes.length) {
      container.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary); padding: 40px;">
          <div style="font-size: 28px; opacity: 0.5; margin-bottom: 8px;">📺</div>
          <div style="font-size: 14px; font-weight: 500;">No Startup Splashes Active</div>
          <div style="font-size: 11px;">Activate a splash screen to preview client login sequence</div>
        </div>
      `;
      if (titleEl) titleEl.textContent = 'Free Fire 1.39';
      if (counterEl) counterEl.textContent = '0 / 0';
      return;
    }

    if (state.activeSplashIndex >= activeSplashes.length) {
      state.activeSplashIndex = 0;
    }

    const cur = activeSplashes[state.activeSplashIndex];

    container.innerHTML = `
      <div style="width: 100%; height: 100%; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #000;">
        <img src="${escapeHtml(cur.bg_img_url || cur.image_url)}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.4; filter: blur(6px);">
        <img src="${escapeHtml(cur.image_url)}" style="position: relative; max-width: 90%; max-height: 85%; object-fit: contain; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.8);" onerror="this.src='/banners/splash_welcome.png'">
      </div>
    `;

    if (titleEl) titleEl.textContent = cur.name || `Splash #${cur.id}`;
    if (badgeEl) badgeEl.textContent = getNavLabel(cur.gos_pos);
    if (counterEl) counterEl.textContent = `${state.activeSplashIndex + 1} / ${activeSplashes.length}`;
    if (actionBtn) {
      actionBtn.textContent = cur.gos_pos > 0 ? `Open: ${getNavLabel(cur.gos_pos)}` : 'Claim / Continue';
    }
  }

  function nextSplash() {
    const activeSplashes = state.splashes.filter(s => s.enabled !== false);
    if (!activeSplashes.length) return;
    state.activeSplashIndex = (state.activeSplashIndex + 1) % activeSplashes.length;
    updateSimulatorDOM();
  }

  function prevSplash() {
    const activeSplashes = state.splashes.filter(s => s.enabled !== false);
    if (!activeSplashes.length) return;
    state.activeSplashIndex = (state.activeSplashIndex - 1 + activeSplashes.length) % activeSplashes.length;
    updateSimulatorDOM();
  }

  // --- MAIN RENDER ---
  async function render(canvas) {
    if (!canvas) return;

    const totalSplashes = state.splashes.length;
    const activeSplashes = state.splashes.filter(s => s.enabled !== false).length;
    const maxVersion = Math.max(...state.splashes.map(s => s.version || 1), 1);

    const rowsHtml = state.splashes.map((s, idx) => {
      const isEnabled = s.enabled !== false;
      const navBadge = window.UI.Badge(getNavLabel(s.gos_pos), s.gos_pos > 0 ? 'cyan' : 'neutral');
      const statusBadge = isEnabled ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('DISABLED', 'neutral');
      const versionBadge = window.UI.Badge(`v${s.version || 1}`, 'amber');

      return `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary); width: 40px; text-align: center;">
            #${s.id}
          </td>
          <td style="width: 80px;">
            <div style="width: 72px; height: 42px; border-radius: 4px; overflow: hidden; background: #000; border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center;">
              <img src="${escapeHtml(s.image_url)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/banners/splash_welcome.png'">
            </div>
          </td>
          <td>
            <div style="font-weight: 600; color: #fff; font-size: 13px;">${escapeHtml(s.name || `Splash #${s.id}`)}</div>
            <div style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);">${escapeHtml(s.image_url)}</div>
          </td>
          <td>${versionBadge}</td>
          <td>${navBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Up" ${idx === 0 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSLobby.moveSplash(${idx}, -1)">▲</button>
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Down" ${idx === state.splashes.length - 1 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSLobby.moveSplash(${idx}, 1)">▼</button>
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSLobby.toggleSplash(${s.id}, ${isEnabled})">
                ${isEnabled ? 'Deactivate' : 'Activate'}
              </button>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSLobby.openEditModal(${s.id})">
                Edit
              </button>
              <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSLobby.deleteSplash(${s.id})">
                Delete
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    canvas.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">

        <!-- Summary Metric Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Active Splashes</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-emerald); margin: 3px 0;">
              ${activeSplashes} <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ ${totalSplashes} total</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">Served on MajorLogin handshake</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Cache Version Level</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-cyan); margin: 3px 0;">
              v${maxVersion}
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">Current client invalidation tag</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default); display: flex; flex-direction: column; justify-content: center; gap: 6px;">
            <button class="btn btn-primary" onclick="window.CMSLobby.bumpVersions()" title="Increments all splash versions to bypass client dismissal caches" style="width: 100%;">
              ⚡ Force-Show Splashes
            </button>
            <div style="font-size: 10.5px; color: var(--text-tertiary); text-align: center;">Busts dismissed device state</div>
          </div>

          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default); display: flex; flex-direction: column; justify-content: center; gap: 8px;">
            <button class="btn btn-secondary" onclick="window.CMSLobby.openCreateModal()" style="width: 100%;">+ Add Splash Screen</button>
            <button class="btn btn-secondary" onclick="window.CMSLobby.openUploadDialog()" style="width: 100%;">📁 Upload Splash Art</button>
            <input type="file" id="splash-quick-file" accept="image/png,image/jpeg,image/jpg" style="display: none;" onchange="window.CMSLobby.handleUpload(this.files[0], true)">
          </div>
        </div>

        <!-- 1.39 Login Splash Screen Simulator (Responsive Frame with max-width: 580px for 1366x768+) -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Free Fire 1.39 Startup Splash Popup Simulator</div>
              <div class="glass-card-subtitle">Authentic reproduction of the in-game modal popup rendered during initial lobby entry</div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span id="splash-sim-badge" class="badge badge-cyan" style="font-size: 11px;">Events</span>
              <span id="splash-sim-counter" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">1 / ${Math.max(1, activeSplashes)}</span>
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.CMSLobby.prevSplash()">◀ Prev</button>
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.CMSLobby.nextSplash()">Next ▶</button>
            </div>
          </div>

          <div class="glass-card-body" style="display: flex; justify-content: center; align-items: center; padding: 24px 0;">
            <!-- Mobile Device Mockup Frame: width: 100%; max-width: 580px -->
            <div style="width: 100%; max-width: 580px; height: 340px; background: #000; border: 3px solid rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden; position: relative; box-shadow: 0 16px 40px rgba(0,0,0,0.7); display: flex; flex-direction: column;">
              
              <!-- Device Top Bar Simulator -->
              <div style="height: 28px; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid rgba(255,255,255,0.06); user-select: none;">
                <span id="splash-sim-title" style="font-size: 11px; font-weight: 600; color: var(--text-secondary); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">Free Fire 1.39</span>
                <span style="font-size: 10px; font-family: var(--font-mono); color: var(--text-tertiary);">BATTERY 100% • 5G</span>
              </div>

              <!-- Popup Canvas Body -->
              <div id="splash-sim-body" style="flex: 1; position: relative; overflow: hidden;">
                <!-- Injected by updateSimulatorDOM -->
              </div>

              <!-- Popup Footer with Action Button and Checkbox -->
              <div style="height: 48px; background: rgba(10, 16, 28, 0.95); backdrop-filter: blur(12px); border-top: 1px solid var(--border-default); display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
                <div style="display: flex; align-items: center; gap: 8px; color: var(--text-tertiary); font-size: 11px;">
                  <input type="checkbox" checked style="accent-color: var(--accent-cyan);">
                  <span>Do not show again today</span>
                </div>
                <div style="display: flex; gap: 8px;">
                  <button id="splash-sim-action-btn" class="btn btn-primary" style="padding: 4px 14px; font-size: 11.5px;" onclick="window.UI.Toast('Triggered client action jump', 'info')">
                    Go To Event
                  </button>
                  <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11.5px;" onclick="window.UI.Toast('Dismissed splash popup', 'info')">
                    ✕ Close
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>

        <!-- Splash Sequence Queue Table with Responsive Container -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Login Splash Sequence Queue</div>
              <div class="glass-card-subtitle">Configured splash popups stored in <code>data/lobby_cms.json</code> under <code>splashes</code></div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="window.CMSLobby.reload()">🔄 Refresh</button>
              <button class="btn btn-secondary" onclick="window.CMSLobby.resetDefaults()">Reset Seed</button>
              <button class="btn btn-primary" onclick="window.CMSLobby.openCreateModal()">+ Add Splash Screen</button>
            </div>
          </div>

          <div class="glass-card-body">
            <div class="glass-table-container">
              ${window.UI.Table(['ID', 'Preview', 'Splash Campaign', 'Cache Version', 'Jump Target', 'Status', 'Order', 'Actions'], rowsHtml, 'No startup splash screens configured yet.')}
            </div>
          </div>
        </div>

      </div>
    `;

    updateSimulatorDOM();
  }

  // --- PUBLIC API EXPORT ---
  window.CMSLobby = {
    async init(canvas) {
      await loadData();
      await render(canvas);
    },
    async reload() {
      await loadData();
      render(document.getElementById('workspace-canvas'));
      window.UI.Toast('Lobby splash state refreshed', 'info');
    },
    toggleSplash,
    deleteSplash,
    moveSplash,
    nextSplash,
    prevSplash,
    bumpVersions,
    resetDefaults: resetSplashesToDefaults,
    openCreateModal() {
      openUpsertModal(null);
    },
    openEditModal(splashId) {
      const s = state.splashes.find(item => item.id === splashId);
      if (s) openUpsertModal(s);
    },
    openUploadDialog: openUploadModal,
    handleUpload(file, autoCreate = false) {
      uploadImageFile(file, autoCreate);
    }
  };

  // Register in SPA Router
  if (window.appRouter) {
    window.appRouter.register('#/cms/lobby', async (canvas) => {
      await window.CMSLobby.init(canvas);
    });
  }

  // Expose on Modules namespace
  window.Modules = window.Modules || {};
  window.Modules.CMSLobby = window.CMSLobby.init;

})();
