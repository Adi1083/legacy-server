/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.8: Artwork & Image Management Studio (banners.js)
 * Comprehensive asset browser, image upload, machine artwork slots, and reward mappings.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Banners = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Artwork & Game Asset Catalog...');

  // Fetch all assets, machines, and reward image assignments
  const [assetRes, machRes, rewardImgRes] = await Promise.all([
    window.apiClient.get('/api/admin/luck-royale/assets'),
    window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 }),
    window.apiClient.get('/api/admin/luck-royale/reward-images')
  ]);

  const assets = (assetRes.ok && assetRes.data && assetRes.data.assets) ? assetRes.data.assets : [];
  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];
  const rewardImages = (rewardImgRes.ok && rewardImgRes.data && rewardImgRes.data.reward_images) ? rewardImgRes.data.reward_images : {};

  // Active view: 'assets' | 'machine_slots' | 'reward_images'
  const activeView = window.LuckRoyale._activeArtworkView || 'assets';
  const activeCat = window.LuckRoyale._selectedAssetCategory || 'All';
  const searchQuery = (window.LuckRoyale._assetSearchQuery || '').toLowerCase();

  // Filter assets
  let filteredAssets = assets;
  if (activeCat !== 'All') {
    filteredAssets = filteredAssets.filter(a => a.category.toLowerCase() === activeCat.toLowerCase());
  }
  if (searchQuery) {
    filteredAssets = filteredAssets.filter(a => a.filename.toLowerCase().includes(searchQuery));
  }

  // Sub-Navigation Pills
  const viewNav = [
    { id: 'assets', label: `Asset Catalog (${assets.length})`, icon: 'image' },
    { id: 'machine_slots', label: 'Machine Artwork Slots', icon: 'sliders' },
    { id: 'reward_images', label: 'Reward Icon Mappings', icon: 'gift' },
  ].map(v => {
    const isCur = v.id === activeView;
    return `
      <button class="btn ${isCur ? 'btn-primary' : 'btn-secondary'}" style="padding: 6px 14px; font-size: 11.5px; border-radius: var(--radius-sm);" onclick="window.LuckRoyale._activeArtworkView='${v.id}'; window.appRouter.handleRoute();">
        <span style="display: inline-flex; align-items: center; gap: 5px;">${window.UI.Icon(v.icon, 12)} ${v.label}</span>
      </button>
    `;
  }).join('');

  // --- VIEW 1: ASSET BROWSER & UPLOADER ---
  function renderAssetBrowserView() {
    const categories = ['All', 'Banners & Posters', 'Weapons', 'Tokens & UI', 'Incubator & Effects', 'Uploads'];
    const catPills = categories.map(cat => {
      const isCur = cat === activeCat;
      return `
        <button class="btn ${isCur ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 11px; border-radius: var(--radius-full);" onclick="window.LuckRoyale._selectedAssetCategory='${cat}'; window.appRouter.handleRoute();">
          ${cat}
        </button>
      `;
    }).join('');

    const assetCards = filteredAssets.map(a => {
      const isUp = Boolean(a.is_upload);
      return `
        <div class="glass-card" style="padding: 10px; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden;">
          <div>
            <div style="height: 110px; border-radius: 6px; overflow: hidden; background: #000; border: 1px solid var(--border-default); display: flex; align-items: center; justify-content: center; margin-bottom: 8px;">
              <img src="${a.url}" alt="${C.escapeHtml(a.filename)}" style="width: 100%; height: 100%; object-fit: contain;">
            </div>
            <div style="font-size: 11px; font-family: var(--font-mono); font-weight: 600; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 3px;" title="${C.escapeHtml(a.filename)}">
              ${C.escapeHtml(a.filename)}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: var(--text-tertiary); margin-bottom: 10px;">
              <span>${a.category}</span>
              <span>${Math.round(a.size_bytes / 1024)} KB</span>
            </div>
          </div>

          <div style="display: flex; gap: 4px;">
            <button class="btn btn-secondary" style="flex: 1; padding: 4px 6px; font-size: 10.5px;" onclick="window.LuckRoyale.OpenAssignAssetToMachineModal('${a.filename}')">
              Assign
            </button>
            <button class="btn btn-secondary" style="padding: 4px 6px; font-size: 10.5px;" onclick="navigator.clipboard.writeText('${a.url}'); window.UI.Toast('Copied URL to clipboard', 'info');" title="Copy URL">
              ${window.UI.Icon('copy', 11)}
            </button>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div>
        <!-- Search and Action Bar -->
        <div class="glass-card" style="padding: 14px 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
          <div style="display: flex; gap: 8px; flex: 1; min-width: 280px;">
            <input type="text" id="asset-search-input" class="form-input" placeholder="Search assets by filename..." value="${C.escapeHtml(window.LuckRoyale._assetSearchQuery || '')}" oninput="window.LuckRoyale._assetSearchQuery=this.value;" onkeydown="if(event.key==='Enter') window.appRouter.handleRoute();">
            <button class="btn btn-secondary" onclick="window.appRouter.handleRoute()">Search</button>
          </div>
          <div style="display: flex; gap: 6px; overflow-x: auto;">
            ${catPills}
          </div>
          <button class="btn btn-primary" onclick="window.LuckRoyale.OpenAssetUploadModal()">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('arrowUpRight', 12)} Upload Asset</span>
          </button>
        </div>

        <!-- Asset Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px;">
          ${filteredAssets.length > 0 ? assetCards : '<div class="glass-card" style="grid-column: 1 / -1; text-align: center; color: var(--text-tertiary);">No assets found matching filter.</div>'}
        </div>
      </div>
    `;
  }

  // --- VIEW 2: MACHINE ARTWORK SLOTS MATRIX ---
  function renderMachineSlotsView() {
    const activeCid = window.LuckRoyale._selectedBannerCid || (machines[0] ? machines[0].chest_id : 3);
    const activeMach = machines.find(m => m.chest_id === activeCid) || machines[0];
    const art = activeMach.artwork || {};

    const machinePills = machines.map(m => {
      const isCur = m.chest_id === activeCid;
      return `
        <button class="btn ${isCur ? 'btn-primary' : 'btn-secondary'}" style="padding: 6px 14px; font-size: 11.5px; border-radius: var(--radius-full);" onclick="window.LuckRoyale._selectedBannerCid=${m.chest_id}; window.appRouter.handleRoute();">
          ${C.escapeHtml(m.display_name || m.chest_name)}
        </button>
      `;
    }).join('');

    const slots = [
      { key: 'banner', label: 'Main Royale Poster Banner', file: art.banner || 'luck_royale_banner.png', url: art.banner_url || '/banners/' + (art.banner || 'luck_royale_banner.png') },
      { key: 'thumbnail', label: 'Machine Thumbnail', file: art.thumbnail || art.banner, url: art.thumbnail_url || art.banner_url },
      { key: 'background', label: 'Background Texture', file: art.background || 'FF_Lottery_onebg.png', url: art.background_url || '/banners/FF_Lottery_onebg.png' },
      { key: 'featured', label: 'Featured Reward Artwork', file: art.featured || 'FF_Lottery_gaindiamond_big.png', url: art.featured_url || '/banners/FF_Lottery_gaindiamond_big.png' },
      { key: 'promo', label: 'Promotional Ribbon', file: art.promo || 'announce_events.png', url: art.promo_url || '/banners/announce_events.png' },
    ];

    const slotCards = slots.map(s => `
      <div class="glass-card" style="padding: 16px; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="font-weight: 600; font-size: 12.5px; color: #fff;">${s.label}</div>
            ${window.UI.Badge(s.key.toUpperCase(), 'cyan')}
          </div>
          <div style="height: 120px; border-radius: 6px; overflow: hidden; background: #000; border: 1px solid var(--border-default); display: flex; align-items: center; justify-content: center; margin-bottom: 10px;">
            <img src="${s.url}" alt="${s.label}" style="width: 100%; height: 100%; object-fit: contain;">
          </div>
          <div style="font-size: 11px; font-family: var(--font-mono); color: var(--accent-cyan); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 12px;">
            ${s.file}
          </div>
        </div>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-primary" style="flex: 1; padding: 5px 8px; font-size: 11px;" onclick="window.LuckRoyale.OpenAssetPickerForSlot(${activeCid}, '${s.key}')">
            Change Asset
          </button>
          <button class="btn btn-secondary" style="padding: 5px 8px; font-size: 11px;" onclick="window.LuckRoyale.OpenUploadForSlot(${activeCid}, '${s.key}')">
            Upload
          </button>
        </div>
      </div>
    `).join('');

    return `
      <div>
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          ${machinePills}
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">
          ${slotCards}
        </div>
      </div>
    `;
  }

  // --- VIEW 3: REWARD ITEM IMAGE MAPPING TABLE ---
  function renderRewardImagesView() {
    const catalogKeys = Object.keys(C.ITEM_CATALOG);
    const rows = catalogKeys.map(k => {
      const it = C.ITEM_CATALOG[k];
      const iid = parseInt(k, 10);
      const customImg = rewardImages[iid];
      const defaultImg = customImg || '/banners/FF_Lottery_previewbg.png';

      return `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 10px;">
              ${C.renderItemImage(defaultImg, it.name, 36)}
              <div>
                <div style="font-weight: 600; color: #fff;">${C.escapeHtml(it.name)}</div>
                <div style="font-size: 10.5px; font-family: var(--font-mono); color: var(--accent-cyan);">ID: ${iid}</div>
              </div>
            </div>
          </td>
          <td>${C.escapeHtml(it.category)}</td>
          <td>${C.rarityBadge(it.rarity)}</td>
          <td>
            <code style="font-family: var(--font-mono); font-size: 11px; color: ${customImg ? 'var(--accent-amber)' : 'var(--text-tertiary)'};">
              ${customImg || 'default_catalog'}
            </code>
          </td>
          <td>
            ${customImg ? window.UI.Badge('CUSTOM', 'amber') : window.UI.Badge('DEFAULT', 'neutral')}
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.PromptChangeRewardImage(${iid})">Assign</button>
              ${customImg ? `<button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.LuckRoyale.ResetRewardImage(${iid})">Reset</button>` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="glass-card" style="padding: 0; overflow: hidden;">
        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div style="font-weight: 600; font-size: 13.5px; color: #fff;">
            Reward Item Artwork & Icon Mappings (${catalogKeys.length} Catalog Items)
          </div>
          <div style="font-size: 11.5px; color: var(--text-tertiary);">
            Custom assignments persist across server restarts
          </div>
        </div>
        <div style="max-height: 520px; overflow-y: auto;">
          ${window.UI.Table(['Reward Item', 'Category', 'Rarity', 'Image Source', 'Mapping Status', 'Actions'], rows)}
        </div>
      </div>
    `;
  }

  let bodyHtml = '';
  if (activeView === 'assets') bodyHtml = renderAssetBrowserView();
  else if (activeView === 'machine_slots') bodyHtml = renderMachineSlotsView();
  else if (activeView === 'reward_images') bodyHtml = renderRewardImagesView();

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Artwork & Image Studio',
        'Direct administrative control over Royale poster banners, machine visual slots, and reward icons',
        `
          <button class="btn btn-primary" onclick="window.LuckRoyale.OpenAssetUploadModal()">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('arrowUpRight', 12)} Upload Asset</span>
          </button>
        `,
        'image'
      )}

      ${C.renderSubNav('banners')}

      <!-- View Selector Tabs -->
      <div style="display: flex; gap: 8px; margin-bottom: 20px;">
        ${viewNav}
      </div>

      <!-- Main Body -->
      ${bodyHtml}
    </div>
  `;
};

// Handlers for Banners & Artwork
window.LuckRoyale.OpenAssetUploadModal = function () {
  const modalHtml = `
    <div id="general-upload-modal" class="modal-backdrop active" style="z-index: 9999;">
      <div class="modal-content" style="max-width: 440px;">
        <div class="modal-header">
          <div class="modal-title">Upload New Game Asset</div>
          <button class="modal-close" onclick="document.getElementById('general-upload-modal').remove()">&times;</button>
        </div>
        <div style="padding: 16px;">
          <input type="file" id="general-file-input" accept="image/*" class="form-input" style="margin-bottom: 12px;">
          <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 16px;">
            Supports PNG, JPG, WebP. Safe upload directly persists to static/banners/uploads directory.
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button class="btn btn-secondary" onclick="document.getElementById('general-upload-modal').remove()">Cancel</button>
            <button class="btn btn-primary" onclick="window.LuckRoyale.PerformGeneralUpload()">Upload Asset</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
};

window.LuckRoyale.PerformGeneralUpload = async function () {
  const fileInput = document.getElementById('general-file-input');
  if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
    window.UI.Toast('Please select a file to upload.', 'warning');
    return;
  }
  const file = fileInput.files[0];
  const reader = new FileReader();
  reader.onload = async () => {
    const base64 = reader.result;
    const res = await window.apiClient.post('/api/admin/luck-royale/assets/upload', {
      filename: file.name,
      base64: base64
    });
    if (res.ok) {
      window.UI.Toast(`Asset ${file.name} uploaded successfully.`, 'success');
      const modal = document.getElementById('general-upload-modal');
      if (modal) modal.remove();
      window.appRouter.handleRoute();
    } else {
      window.UI.Toast(res.error || 'Upload failed.', 'danger');
    }
  };
  reader.readAsDataURL(file);
};

window.LuckRoyale.OpenAssignAssetToMachineModal = function (filename) {
  const modalHtml = `
    <div id="assign-machine-modal" class="modal-backdrop active" style="z-index: 9999;">
      <div class="modal-content" style="max-width: 440px;">
        <div class="modal-header">
          <div class="modal-title">Assign ${C.escapeHtml(filename)}</div>
          <button class="modal-close" onclick="document.getElementById('assign-machine-modal').remove()">&times;</button>
        </div>
        <form id="assign-machine-form" onsubmit="window.LuckRoyale.SubmitAssignToMachine(event, '${filename}'); return false;" style="padding: 16px;">
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Target Machine</label>
            <select name="chest_id" class="form-select">
              <option value="3">Diamond Royale (#3)</option>
              <option value="4">Weapon Royale (#4)</option>
              <option value="5">Gold Royale (#5)</option>
              <option value="6">Incubator (#6)</option>
            </select>
          </div>
          <div style="margin-bottom: 16px;">
            <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Artwork Slot</label>
            <select name="slot" class="form-select">
              <option value="banner">Main Poster Banner</option>
              <option value="thumbnail">Thumbnail</option>
              <option value="background">Background Texture</option>
              <option value="featured">Featured Reward Artwork</option>
              <option value="promo">Promotional Ribbon</option>
            </select>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('assign-machine-modal').remove()">Cancel</button>
            <button type="submit" class="btn btn-primary">Assign Artwork</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
};

window.LuckRoyale.SubmitAssignToMachine = async function (e, filename) {
  const form = e.target;
  const chestId = parseInt(form.chest_id.value, 10);
  const slot = form.slot.value;

  const payload = { chest_id: chestId };
  payload[slot] = filename;

  const res = await window.apiClient.post(`/api/admin/luck-royale/machines/${chestId}/artwork`, payload);
  if (res.ok) {
    window.UI.Toast(`Assigned ${filename} to Machine #${chestId} (${slot}).`, 'success');
    const modal = document.getElementById('assign-machine-modal');
    if (modal) modal.remove();
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to assign artwork.', 'danger');
  }
};

window.LuckRoyale.PromptChangeRewardImage = function (itemId) {
  const url = prompt(`Enter image URL or filename for Item #${itemId} (e.g. /banners/FF_Lottery_gun_big.png):`);
  if (!url) return;
  window.apiClient.post('/api/admin/luck-royale/reward-images', { item_id: itemId, image_url: url }).then(res => {
    if (res.ok) {
      window.UI.Toast(`Image assigned to Item #${itemId}.`, 'success');
      window.appRouter.handleRoute();
    } else {
      window.UI.Toast(res.error || 'Failed to assign image.', 'danger');
    }
  });
};

window.LuckRoyale.ResetRewardImage = async function (itemId) {
  const res = await window.apiClient.delete('/api/admin/luck-royale/reward-images', { item_id: itemId });
  if (res.ok) {
    window.UI.Toast(`Reset image for Item #${itemId} to default.`, 'info');
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to reset image.', 'danger');
  }
};
