/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Inventory & Vault Item Manager
 * Route: #/inventory/manager
 *
 * Capabilities:
 * - Dynamic PlayerContext binding & reactive re-render on player change
 * - Reverse-engineered FF 1.39 item catalog (Weapons, Outfits, Emotes, Gear, Utility)
 * - Category filtering, text search, ownership status filter
 * - Standardized .page-container layout with UI.PageHeader & .grid-4 metric strip
 * - High-polish dark glass styling with SVG artwork fallbacks (no broken image icons)
 * - Item Grant Modal (single & batch) with UI.Confirm safety guard -> POST /api/dashboard/items/grant
 * - Item Deletion with destructive UI.Confirm -> POST /api/dashboard/items/delete
 * - Batch catalog unlocker with UI.Confirm
 * - Zero consumer emojis
 */

(function () {
  'use strict';

  // 1. Comprehensive FF 1.39 Reverse-Engineered Item Catalog (44 Items)
  const ITEM_CATALOG = [
    // --- Weapons & Armory ---
    { id: 907100098, name: 'AK47 Flaming Dragon', category: 'weapons', rarity: 'mythic', desc: 'Legendary dragon aura granting boosted damage and extreme fire rate.' },
    { id: 907100094, name: 'SCAR Cupid Love', category: 'weapons', rarity: 'mythic', desc: 'Rapid double fire rate with pink arrow trajectory trail.' },
    { id: 907100100, name: 'MP40 Mechanical Lightning', category: 'weapons', rarity: 'legendary', desc: 'High-voltage submachine gun with extreme burst DPS.' },
    { id: 907100102, name: 'M4A1 Griffin Fury', category: 'weapons', rarity: 'legendary', desc: 'Celestial avian engraving granting enhanced range and recoil stability.' },
    { id: 907100106, name: 'AWM Duke Butterfly', category: 'weapons', rarity: 'mythic', desc: 'One-shot high-caliber anti-materiel sniper with royal gold plating.' },
    { id: 907100108, name: 'Katana Blood Moon', category: 'weapons', rarity: 'legendary', desc: 'Forged from crimson meteoric iron, leaves slicing red arcs.' },
    { id: 907100110, name: 'Golden Pan Master', category: 'weapons', rarity: 'epic', desc: 'Deflects 100% of incoming rear ballistics with pure gilded luster.' },
    { id: 907100112, name: 'M1014 Green Flame Draco', category: 'weapons', rarity: 'mythic', desc: 'Draconic pump shotgun emitting jade flames on each discharge.' },
    { id: 907100114, name: 'Groza Winterlands', category: 'weapons', rarity: 'epic', desc: 'Cryo-coated bullpup assault rifle with increased armor penetration.' },
    { id: 907100116, name: 'FAMAS Metallic Vampire', category: 'weapons', rarity: 'rare', desc: 'Three-round burst rifle siphon with gothic crimson plating.' },

    // --- Outfits & Legendary Bundles ---
    { id: 700000001, name: 'Sakura Demon Blossom Bundle', category: 'outfits', rarity: 'mythic', desc: 'Season 1 historic elite bundle with traditional samurai battle armor.' },
    { id: 700000002, name: 'Hip Hop Streetwear Bundle', category: 'outfits', rarity: 'mythic', desc: 'Season 2 legendary streetwear hoodie with custom boombox mask.' },
    { id: 700000003, name: 'Red Criminal Jumpsuit', category: 'outfits', rarity: 'mythic', desc: 'Ultra-rare syndicate heist suit with devil grin face mask.' },
    { id: 700000004, name: 'Blue Criminal Heist Suit', category: 'outfits', rarity: 'legendary', desc: 'Cobalt tactical jumpsuit favored by underground bank raiders.' },
    { id: 700000005, name: 'Arctic Blue Cyber Suit', category: 'outfits', rarity: 'legendary', desc: 'Cryogenic exoskeleton radiating sub-zero frost vapors.' },
    { id: 700000006, name: 'Breakdancer Retro Set', category: 'outfits', rarity: 'epic', desc: 'Urban b-boy tracksuit with reflective neon kicks.' },
    { id: 203000573, name: 'Tactical Combat Hoodie', category: 'outfits', rarity: 'epic', desc: 'Reinforced kevlar weave with weather-sealed storm hood.' },
    { id: 203000418, name: 'Hayato Bushido Kimono', category: 'outfits', rarity: 'rare', desc: 'Traditional samurai warrior vest with family crest embroidery.' },
    { id: 203000376, name: 'Moco Cybernetic Vest', category: 'outfits', rarity: 'rare', desc: 'Hacker tunic embedded with holographic data conduits.' },
    { id: 203000353, name: 'Wukong Simian Guard', category: 'outfits', rarity: 'rare', desc: 'Mystical battle vest woven with golden camouflage threads.' },

    // --- Emotes ---
    { id: 909000001, name: 'Throne of Kings (Emote)', category: 'emotes', rarity: 'mythic', desc: 'Summon an ornate gilded throne and rest with supreme authority.' },
    { id: 909000002, name: 'Doggie Dance (Emote)', category: 'emotes', rarity: 'legendary', desc: 'Funky companion synchronization dance with upbeat rhythm.' },
    { id: 909000003, name: 'Flowers of Love (Emote)', category: 'emotes', rarity: 'legendary', desc: 'Offer a crimson rose with romantic flair to squadmates.' },
    { id: 909000004, name: 'FFWC World Cup Trophy (Emote)', category: 'emotes', rarity: 'mythic', desc: 'Hoist the golden world champion trophy under spotlight fire.' },
    { id: 909000005, name: 'Push-up Discipline (Emote)', category: 'emotes', rarity: 'rare', desc: 'Single-arm tactical pushups showcasing unyielding conditioning.' },
    { id: 909000006, name: 'Tea Time Aristocrat (Emote)', category: 'emotes', rarity: 'epic', desc: 'Summon a high-society tea table and sip calmly during battle.' },
    { id: 909000007, name: 'LOL Provocation (Emote)', category: 'emotes', rarity: 'rare', desc: 'Point and laugh uncontrollably at defeated opponents.' },
    { id: 909000008, name: 'Provoke / Bring It On (Emote)', category: 'emotes', rarity: 'rare', desc: 'Beckon enemies forward with fearless combat confidence.' },

    // --- Collections & Gear ---
    { id: 904000001, name: 'Cyber Dragon Backpack Lv3', category: 'gear', rarity: 'legendary', desc: 'Holographic cybernetic wings that flare during sprinting.' },
    { id: 905000001, name: 'Ghost Rider Flame Parachute', category: 'gear', rarity: 'epic', desc: 'Engulfed in hellfire trails visible across the sky during drops.' },
    { id: 906000001, name: 'Surfer of the Void Skyboard', category: 'gear', rarity: 'epic', desc: 'Hoverboard emitting ion plasma jet trails during high drops.' },
    { id: 903000001, name: 'Golden Coffin Death Crate', category: 'gear', rarity: 'legendary', desc: 'Replaces eliminated enemy crates with a radiant sarcophagus.' },
    { id: 908000001, name: 'Monster Truck Cyber Camo', category: 'gear', rarity: 'epic', desc: 'Heavy armor plating with reactive electromagnetic paint.' },
    { id: 904000005, name: 'Panda Plush Backpack', category: 'gear', rarity: 'rare', desc: 'Soft tactical rucksack modeled after Detective Panda.' },

    // --- Utility, Cards & Vouchers ---
    { id: 400000001, name: 'Custom Room Card (7-Day Unlimited)', category: 'utility', rarity: 'mythic', desc: 'Host infinite private tournament matches with custom configs.' },
    { id: 400000002, name: 'Account Nickname Change Card', category: 'utility', rarity: 'epic', desc: 'Re-brand operative callsign without diamond deduction.' },
    { id: 400000003, name: 'Character Level 8 Max Card', category: 'utility', rarity: 'mythic', desc: 'Instantly elevates any selected character to Level 8 MAX.' },
    { id: 911000001, name: 'Weapon Royale Spin Voucher', category: 'utility', rarity: 'rare', desc: 'Free ticket to spin the high-tier Weapon Royale Luck wheel.' },
    { id: 911000002, name: 'Diamond Royale Spin Voucher', category: 'utility', rarity: 'rare', desc: 'Free ticket to spin the premier Diamond Royale wardrobe.' },
    { id: 911000003, name: 'Incubator Evolution Stone', category: 'utility', rarity: 'mythic', desc: 'Rare catalyst required to synthesize top-tier blueprint weapons.' },
    { id: 110100010, name: 'Gold Royale Voucher', category: 'utility', rarity: 'rare', desc: 'Standard ticket for Gold Royale spins.' },
    { id: 110200001, name: 'FF Token Currency', category: 'utility', rarity: 'rare', desc: 'Universal exchange currency awarded from duplicate gacha items.' }
  ];

  // Component view state
  let currentFilter = 'all';
  let currentSearch = '';
  let activeTab = 'catalog'; // 'catalog' | 'owned'
  let searchTimeout = null;

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function getRarityStyle(rarity) {
    switch (rarity) {
      case 'mythic':
        return {
          border: '1px solid rgba(244, 63, 94, 0.45)',
          glow: '0 0 16px rgba(244, 63, 94, 0.15)',
          badge: window.UI.Badge('MYTHIC', 'rose'),
          color: '#f43f5e',
          bgGradient: 'radial-gradient(circle at 50% 30%, rgba(244, 63, 94, 0.15) 0%, rgba(10, 16, 28, 0.6) 80%)'
        };
      case 'legendary':
        return {
          border: '1px solid rgba(245, 158, 11, 0.45)',
          glow: '0 0 16px rgba(245, 158, 11, 0.15)',
          badge: window.UI.Badge('LEGENDARY', 'amber'),
          color: '#f59e0b',
          bgGradient: 'radial-gradient(circle at 50% 30%, rgba(245, 158, 11, 0.15) 0%, rgba(10, 16, 28, 0.6) 80%)'
        };
      case 'epic':
        return {
          border: '1px solid rgba(56, 189, 248, 0.45)',
          glow: '0 0 16px rgba(56, 189, 248, 0.15)',
          badge: window.UI.Badge('EPIC', 'cyan'),
          color: '#38bdf8',
          bgGradient: 'radial-gradient(circle at 50% 30%, rgba(56, 189, 248, 0.15) 0%, rgba(10, 16, 28, 0.6) 80%)'
        };
      case 'rare':
      default:
        return {
          border: '1px solid rgba(16, 185, 129, 0.45)',
          glow: '0 0 16px rgba(16, 185, 129, 0.15)',
          badge: window.UI.Badge('RARE', 'emerald'),
          color: '#10b981',
          bgGradient: 'radial-gradient(circle at 50% 30%, rgba(16, 185, 129, 0.15) 0%, rgba(10, 16, 28, 0.6) 80%)'
        };
    }
  }

  function getCategoryIcon(cat) {
    switch (cat) {
      case 'weapons':
        return 'crosshair';
      case 'outfits':
        return 'shirt';
      case 'emotes':
        return 'sparkles';
      case 'gear':
        return 'package';
      case 'utility':
      default:
        return 'ticket';
    }
  }

  function getCategoryLabel(cat) {
    const map = {
      all: 'All Categories',
      weapons: 'Weapons',
      outfits: 'Outfits',
      emotes: 'Emotes',
      gear: 'Gear',
      utility: 'Utility & Cards'
    };
    return map[cat] || cat;
  }

  async function renderInventoryManager(canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Loading('Loading vault items & inventory state...');

    // Fetch live state for active player
    let playerData = window.playerContext.getCurrentPlayer();
    if (!playerData || playerData.account_id !== aid) {
      try {
        const res = await window.apiClient.get('/api/dashboard/state', { account_id: aid });
        if (res.ok && res.data) {
          playerData = res.data;
        }
      } catch (err) {
        console.error('Failed to fetch player state:', err);
      }
    }

    const inventoryList = (playerData && playerData.inventory) || [];
    let totalQuantity = 0;
    inventoryList.forEach(it => {
      totalQuantity += (it.count || it.amount || 1);
    });

    const nick = (playerData && (playerData.nickname || (playerData.profile && playerData.profile.nickname))) || 'PushpaGG';
    const level = (playerData && (playerData.level || (playerData.profile && playerData.profile.level))) || 60;

    // Filter items according to category and search
    const filteredCatalog = ITEM_CATALOG.filter(item => {
      if (currentFilter !== 'all' && item.category !== currentFilter) return false;
      if (currentSearch) {
        const q = currentSearch.toLowerCase();
        const matchesName = item.name.toLowerCase().includes(q);
        const matchesId = String(item.id).includes(q);
        const matchesDesc = (item.desc || '').toLowerCase().includes(q);
        if (!matchesName && !matchesId && !matchesDesc) return false;
      }
      return true;
    });

    const categories = ['all', 'weapons', 'outfits', 'emotes', 'gear', 'utility'];
    const categoryButtonsHtml = categories.map(cat => `
      <button class="btn ${currentFilter === cat ? 'btn-primary' : 'btn-secondary'}"
        style="padding: 4px 10px; font-size: 11px;"
        onclick="window.InventoryManager.setFilter('${cat}')">
        ${getCategoryLabel(cat)}
      </button>
    `).join('');

    // Catalog items cards grid
    const cardsHtml = filteredCatalog.map(item => {
      const rarityInfo = getRarityStyle(item.rarity);
      const iconName = getCategoryIcon(item.category);
      const isOwned = inventoryList.some(inv => (inv.item_id || inv.id || inv) === item.id);

      return `
        <div class="glass-card vault-card" style="
          background: ${rarityInfo.bgGradient};
          border: ${rarityInfo.border};
          box-shadow: ${rarityInfo.glow};
          border-radius: var(--radius-md);
          padding: 14px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          transition: all var(--transition-fast);
        ">
          <div>
            <!-- Header: Category Icon slot & Rarity Badge -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <div style="
                width: 34px;
                height: 34px;
                border-radius: var(--radius-sm);
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                justify-content: center;
              ">
                ${window.UI.Icon(iconName, 18, '', rarityInfo.color)}
              </div>
              <div style="display: flex; gap: 4px; align-items: center;">
                ${isOwned ? window.UI.Badge('OWNED', 'emerald') : ''}
                ${rarityInfo.badge}
              </div>
            </div>

            <div style="font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 3px; line-height: 1.35;">
              ${escapeHtml(item.name)}
            </div>

            <div style="margin-bottom: 8px;">
              <code style="font-family: var(--font-mono); font-size: 10.5px; color: var(--accent-cyan); font-weight: 600;">ID: ${item.id}</code>
            </div>

            <div style="font-size: 11px; color: var(--text-tertiary); line-height: 1.4; margin-bottom: 12px; min-height: 32px;">
              ${escapeHtml(item.desc)}
            </div>
          </div>

          <div style="display: flex; gap: 6px; padding-top: 10px; border-top: 1px solid var(--border-subtle);">
            <button class="btn btn-primary" style="flex: 1; padding: 5px 8px; font-size: 11px;"
              onclick="window.InventoryManager.promptGrantSingle(${item.id}, '${escapeHtml(item.name).replace(/'/g, "\\'")}')">
              ${window.UI.Icon('plus', 12)} Grant +1
            </button>
            <button class="btn btn-secondary" style="padding: 5px 8px; font-size: 11px;" title="Custom Quantity"
              onclick="window.InventoryManager.openGrantModal(${item.id})">
              Qty
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Owned Items table rows with Delete action
    const ownedRowsHtml = inventoryList.map(it => {
      const iid = it.item_id || it.id || it;
      const count = it.count || it.amount || 1;
      const catMatch = ITEM_CATALOG.find(c => c.id === iid);
      const name = it.name || (catMatch ? catMatch.name : `Item #${iid}`);
      const category = catMatch ? getCategoryLabel(catMatch.category) : 'General Item';
      const rarity = catMatch ? catMatch.rarity : 'rare';
      return `
        <tr>
          <td><code style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); font-weight: 600;">${iid}</code></td>
          <td style="font-weight: 600; color: #fff;">${escapeHtml(name)}</td>
          <td><span style="font-size: 11px; color: var(--text-secondary);">${category}</span></td>
          <td>${getRarityStyle(rarity).badge}</td>
          <td><span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-amber);">${count}</span></td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-primary" style="padding: 3px 8px; font-size: 11px;"
                onclick="window.InventoryManager.promptGrantSingle(${iid}, '${escapeHtml(name).replace(/'/g, "\\'")}')">
                ${window.UI.Icon('plus', 12)} +1 Add
              </button>
              <button class="btn btn-danger" style="padding: 3px 8px; font-size: 11px;"
                onclick="window.InventoryManager.promptDeleteItem(${iid}, '${escapeHtml(name).replace(/'/g, "\\'")}', ${count})">
                ${window.UI.Icon('trash', 12)} Remove
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    const pageActionsHtml = `
      <button class="btn btn-primary" onclick="window.InventoryManager.openGrantModal()">
        ${window.UI.Icon('plus', 14)} <span>Grant Item ID</span>
      </button>
      <button class="btn btn-secondary" onclick="window.InventoryManager.promptUnlockCoreCatalog()">
        ${window.UI.Icon('sparkles', 14, '', 'var(--accent-amber)')} <span>Unlock Core Catalog</span>
      </button>
      <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.InventoryManager.render(c);">
        ${window.UI.Icon('refresh', 14)} <span>Sync</span>
      </button>
    `;

    canvas.innerHTML = `
      <div class="page-container">
        <!-- 1. Page Header -->
        ${window.UI.PageHeader(
          'Inventory Vault & Item Catalogue',
          'Catalog management, item granting, and player inventory inspection',
          pageActionsHtml,
          'package'
        )}

        <!-- 2. Exactly 4 Compact Metrics (.grid-4) -->
        <div class="grid-4" style="margin-bottom: var(--space-md);">
          ${window.UI.StatCard(
            'Unique Items',
            inventoryList.length.toLocaleString(),
            'Distinct vault records',
            window.UI.Icon('package', 16, '', 'var(--accent-cyan)'),
            'cyan'
          )}
          ${window.UI.StatCard(
            'Total Vault Items',
            totalQuantity.toLocaleString(),
            'Cumulative item stacks',
            window.UI.Icon('sparkles', 16, '', 'var(--accent-amber)'),
            'amber'
          )}
          ${window.UI.StatCard(
            'Core Catalog Items',
            `${ITEM_CATALOG.length} Items`,
            'Verified FF 1.39 assets',
            window.UI.Icon('shield', 16, '', 'var(--accent-emerald)'),
            'emerald'
          )}
          ${window.UI.StatCard(
            'Active Context Account',
            `Account ${aid}`,
            `${escapeHtml(nick)} • Lv.${level}`,
            window.UI.Icon('user', 16, '', 'var(--accent-blue)'),
            'blue'
          )}
        </div>

        <!-- 3. View Switcher Tabs -->
        <div style="display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 10px;">
          <button class="btn ${activeTab === 'catalog' ? 'btn-primary' : 'btn-secondary'}" onclick="window.InventoryManager.switchTab('catalog')">
            ${window.UI.Icon('package', 14)} Browse Core Catalog (${ITEM_CATALOG.length})
          </button>
          <button class="btn ${activeTab === 'owned' ? 'btn-primary' : 'btn-secondary'}" onclick="window.InventoryManager.switchTab('owned')">
            ${window.UI.Icon('userCheck', 14)} Player Vault Inventory (${inventoryList.length})
          </button>
        </div>

        ${activeTab === 'catalog' ? `
          <!-- Controls & Filter Toolbar -->
          <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
              ${categoryButtonsHtml}
            </div>
            <div style="display: flex; gap: 8px; align-items: center; min-width: 260px; max-width: 340px;">
              <input type="text" id="vault-search-input" class="form-input" placeholder="Search name, ID, or description..." value="${escapeHtml(currentSearch)}" oninput="window.InventoryManager.handleSearch(this.value)">
            </div>
          </div>

          <!-- Catalog Cards Grid (auto-fill minmax(210px, 1fr)) -->
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 14px;">
            ${cardsHtml || '<div style="grid-column: 1 / -1; padding: 48px; text-align: center; color: var(--text-tertiary);">No catalog items match current filter criteria.</div>'}
          </div>
        ` : `
          <!-- Player Owned Inventory Table with Deletion -->
          <div class="glass-table-container" style="max-height: 520px; overflow-y: auto;">
            ${window.UI.Table(
              ['Item ID', 'Item Name', 'Category', 'Rarity', 'Owned Quantity', 'Admin Actions'],
              ownedRowsHtml,
              'Player vault currently has no recorded inventory items.'
            )}
          </div>
        `}
      </div>
    `;
  }

  // --- Actions & Modal Dialogs ---

  function switchTab(tab) {
    activeTab = tab;
    const canvas = document.getElementById('workspace-canvas');
    if (canvas) renderInventoryManager(canvas);
  }

  function setFilter(cat) {
    currentFilter = cat;
    const canvas = document.getElementById('workspace-canvas');
    if (canvas) renderInventoryManager(canvas);
  }

  function handleSearch(val) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentSearch = val.trim();
      const canvas = document.getElementById('workspace-canvas');
      if (canvas) renderInventoryManager(canvas);
    }, 200);
  }

  function promptGrantSingle(itemId, itemName) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Grant Vault Item',
      `Grant 1x <b>${itemName}</b> (ID: <code>${itemId}</code>) to Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/items/grant', {
            account_id: aid,
            item_ids: [itemId],
            count: 1
          });
          if (res.ok) {
            window.UI.Toast(`Granted 1x ${itemName} to Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderInventoryManager(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to grant item', 'error');
          }
        } catch (err) {
          window.UI.Toast(err.message, 'error');
        }
      }
    );
  }

  function promptDeleteItem(itemId, itemName, currentCount) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Delete Item from Vault',
      `<b>CAUTION:</b> Remove <b>${itemName}</b> (ID: <code>${itemId}</code>, Qty: ${currentCount}) from Account <b>${aid}</b>'s inventory? This deletes the database record.`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/items/delete', {
            account_id: aid,
            item_id: itemId,
            count: currentCount
          });
          if (res.ok) {
            window.UI.Toast(`Removed ${itemName} from Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderInventoryManager(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to remove item', 'error');
          }
        } catch (err) {
          window.UI.Toast(err.message, 'error');
        }
      },
      true // destructive confirm
    );
  }

  function openGrantModal(defaultItemId) {
    const aid = window.playerContext.getSelectedAccountId();
    const modalBodyHtml = `
      <div style="max-width: 440px;">
        <div style="margin-bottom: 12px;">
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; text-transform: uppercase;">Target Account</label>
          <input type="text" class="form-input" value="Account ${aid}" disabled style="opacity: 0.85;">
        </div>
        <div style="margin-bottom: 12px;">
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; text-transform: uppercase;">Item ID (Numeric)</label>
          <input type="number" id="grant-modal-item-id" class="form-input" placeholder="e.g. 907100098" value="${defaultItemId || ''}">
        </div>
        <div style="margin-bottom: 16px;">
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; text-transform: uppercase;">Quantity / Stacks</label>
          <input type="number" id="grant-modal-qty" class="form-input" value="1" min="1" max="9999">
        </div>
      </div>
    `;

    const footerButtonsHtml = `
      <button class="btn btn-secondary" onclick="window.UI.CloseModal()">Cancel</button>
      <button class="btn btn-primary" onclick="window.InventoryManager.executeGrantFromModal()">Grant to Vault</button>
    `;

    window.UI.Modal('Grant Item to Player Vault', modalBodyHtml, footerButtonsHtml);
  }

  async function executeGrantFromModal() {
    const aid = window.playerContext.getSelectedAccountId();
    const idInput = document.getElementById('grant-modal-item-id');
    const qtyInput = document.getElementById('grant-modal-qty');

    if (!idInput || !idInput.value.trim()) {
      window.UI.Toast('Numeric Item ID is required', 'warning');
      return;
    }

    const itemId = parseInt(idInput.value.trim(), 10);
    const qty = parseInt(qtyInput ? qtyInput.value : 1, 10) || 1;

    if (isNaN(itemId) || itemId <= 0) {
      window.UI.Toast('Please enter a valid positive Item ID', 'warning');
      return;
    }

    try {
      const res = await window.apiClient.post('/api/dashboard/items/grant', {
        account_id: aid,
        item_ids: [itemId],
        count: qty
      });

      if (res.ok) {
        window.UI.CloseModal();
        window.UI.Toast(`Granted ${qty}x (ID: ${itemId}) to Account ${aid}`, 'success');
        await window.playerContext.refresh();
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) renderInventoryManager(canvas);
      } else {
        window.UI.Toast(res.error || 'Failed to grant item', 'error');
      }
    } catch (e) {
      window.UI.Toast(e.message, 'error');
    }
  }

  function promptUnlockCoreCatalog() {
    const aid = window.playerContext.getSelectedAccountId();
    const allIds = ITEM_CATALOG.map(i => i.id);

    window.UI.Confirm(
      'Batch Catalog Unlock',
      `Grant all <b>${allIds.length} core items</b> in the catalog directly to Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/items/grant', {
            account_id: aid,
            item_ids: allIds,
            count: 1
          });
          if (res.ok) {
            window.UI.Toast(`All ${allIds.length} core items unlocked for Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderInventoryManager(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to unlock core catalog', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      }
    );
  }

  // Reactive listener to playerContext account switches
  if (window.playerContext && typeof window.playerContext.onPlayerChange === 'function') {
    window.playerContext.onPlayerChange(() => {
      if (window.location.hash.startsWith('#/inventory/manager')) {
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) renderInventoryManager(canvas);
      }
    });
  }

  // Export module interface
  window.Modules = window.Modules || {};
  window.Modules.InventoryManager = renderInventoryManager;

  window.InventoryManager = {
    render: renderInventoryManager,
    switchTab,
    setFilter,
    handleSearch,
    promptGrantSingle,
    promptDeleteItem,
    openGrantModal,
    executeGrantFromModal,
    promptUnlockCoreCatalog
  };

  // Register SPA route
  function bindRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/inventory/manager', renderInventoryManager);
    }
  }

  bindRoute();
  document.addEventListener('DOMContentLoaded', () => setTimeout(bindRoute, 0));
})();
