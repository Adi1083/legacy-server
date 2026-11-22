/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Shared Constants & UI Primitives (common.js)
 * Clean macOS dark glass design system, zero emojis, authentic asset mappings.
 */

window.LuckRoyale = window.LuckRoyale || {};

(function () {
  'use strict';

  // 1. Known Free Fire 1.39 OB17 Vouchers & Special Tokens
  const VOUCHERS = {
    GOLD_ROYALE: 110100010,
    GOLD_ROYALE_LEGACY: 802000000,
    DIAMOND_ROYALE: 110100008,
    DIAMOND_ROYALE_LEGACY: 802000001,
    WEAPON_ROYALE: 110100009,
    WEAPON_ROYALE_LEGACY: 802000008,
    INCUBATOR: 110100018,
    INCUBATOR_LEGACY: 802000009,
  };

  const SPECIAL_ITEMS = {
    FF_TOKEN: 110200001,
    FF_TOKEN_LEGACY: 800000301,
    MAGIC_CUBE: 800000304,
    EVOLUTION_STONE: 808000003,
    EVOLUTION_STONE_ALT: 808000001,
    BLUEPRINT_YINYANG: 808000011,
    BLUEPRINT_JOKER: 808000012,
  };

  // 2. Explicit 19-Character Avatar Debris Map (Matches proto/character_models.py exactly)
  // Protected mechanic: Zero arithmetic modulo calculations allowed.
  const AVATAR_DEBRIS_MAP = {
    102000005: 800000001, // Andrew -> Cop
    101000005: 800000002, // Olivia -> Nurse
    101000006: 800000003, // Kelly -> Runner
    102000006: 800000004, // Ford -> Seaman
    101000007: 800000005, // Nikita -> Bodyguard
    101000008: 800000006, // Misha -> Racergirl
    102000007: 800000007, // Maxim -> Foodieboy
    102000008: 800000008, // Kla -> Thaiboxer
    101000009: 800000009, // Paloma -> Armsdealer
    102000009: 800000010, // Miguel -> BrazilSoldier
    101000010: 800000011, // Caroline -> Richgirl
    102000010: 800000012, // Antonio -> Gangleader
    102000011: 800000013, // Wukong -> Monkeygod
    101000011: 800000014, // Moco -> HackerGirl
    102000012: 800000015, // Hayato -> Samurai
    101000012: 800000016, // Laura -> Agent
    102000013: 800000017, // Rafael -> Hitman
    101000013: 800000018, // A124 -> MadeManA
    102000014: 800000019, // Joseph -> Playboy
  };

  const DEBRIS_TO_AVATAR_MAP = {};
  Object.keys(AVATAR_DEBRIS_MAP).forEach(aid => {
    DEBRIS_TO_AVATAR_MAP[AVATAR_DEBRIS_MAP[aid]] = parseInt(aid, 10);
  });

  const AVATAR_NAMES = {
    101000001: 'Eva',
    101000005: 'Olivia',
    101000006: 'Kelly',
    101000007: 'Nikita',
    101000008: 'Misha',
    101000009: 'Paloma',
    101000010: 'Caroline',
    101000011: 'Moco',
    101000012: 'Laura',
    101000013: 'A124',
    102000004: 'Adam',
    102000005: 'Andrew',
    102000006: 'Ford',
    102000007: 'Maxim',
    102000008: 'Kla',
    102000009: 'Miguel',
    102000010: 'Antonio',
    102000011: 'Wukong',
    102000012: 'Hayato',
    102000013: 'Rafael',
    102000014: 'Joseph'
  };

  const ITEM_CATALOG = {
    110100010: { name: 'Gold Royale Voucher', category: 'Voucher', rarity: 1 },
    802000000: { name: 'Gold Royale Voucher (Legacy)', category: 'Voucher', rarity: 1 },
    110100008: { name: 'Diamond Royale Voucher', category: 'Voucher', rarity: 2 },
    802000001: { name: 'Diamond Royale Voucher (Legacy)', category: 'Voucher', rarity: 2 },
    110100009: { name: 'Weapon Royale Voucher', category: 'Voucher', rarity: 2 },
    802000008: { name: 'Weapon Royale Voucher (Legacy)', category: 'Voucher', rarity: 2 },
    110100018: { name: 'Incubator Voucher', category: 'Voucher', rarity: 2 },
    802000009: { name: 'Incubator Voucher (Legacy)', category: 'Voucher', rarity: 2 },
    110200001: { name: 'FF Token', category: 'Token', rarity: 1 },
    800000301: { name: 'FF Token (Legacy)', category: 'Token', rarity: 1 },
    800000304: { name: 'Magic Cube', category: 'Material', rarity: 2 },
    808000003: { name: 'Evolution Stone', category: 'Material', rarity: 2 },
    808000001: { name: 'Evolution Stone / Blueprint', category: 'Material', rarity: 2 },
    808000002: { name: 'Blueprint Joker (Legacy)', category: 'Material', rarity: 2 },
    808000011: { name: 'Blueprint: YinYang', category: 'Material', rarity: 2 },
    808000012: { name: 'Blueprint: Joker', category: 'Material', rarity: 2 },
    710000410: { name: 'Bundle: Golden YinYang (Male)', category: 'Bundle', rarity: 2 },
    710000411: { name: 'Bundle: Golden YinYang (Female)', category: 'Bundle', rarity: 2 },
    710000412: { name: 'Bundle: Cloud YinYang (Male)', category: 'Bundle', rarity: 1 },
    710000413: { name: 'Bundle: Cloud YinYang (Female)', category: 'Bundle', rarity: 1 },
    710000401: { name: 'Bundle: Dino Green Jumpsuit', category: 'Bundle', rarity: 2 },
    710000400: { name: 'Bundle: Dino Yellow Jumpsuit', category: 'Bundle', rarity: 2 },
    710000403: { name: 'Bundle: Bioforge Cybernetic', category: 'Bundle', rarity: 1 },
    710000422: { name: 'Bundle: Street Hip Hop (Male)', category: 'Bundle', rarity: 2 },
    710000423: { name: 'Bundle: Street Hip Hop (Female)', category: 'Bundle', rarity: 2 },
    907001611: { name: 'M4A1 Carnival Carnage', category: 'WeaponSkin', rarity: 2 },
    907001612: { name: 'AK47 Flaming Dragon', category: 'WeaponSkin', rarity: 2 },
    907001613: { name: 'SCAR Cupid Love', category: 'WeaponSkin', rarity: 1 },
    907001614: { name: 'MP40 Mechanical Lightning', category: 'WeaponSkin', rarity: 1 },
    907001620: { name: 'AWM Duke Butterfly', category: 'WeaponSkin', rarity: 1 },
    907001621: { name: 'FAMAS Metallic Vampire', category: 'WeaponSkin', rarity: 1 },
    907001622: { name: 'M1014 Demolitionist', category: 'WeaponSkin', rarity: 0 },
    907001623: { name: 'UMP Cheetah Prowl', category: 'WeaponSkin', rarity: 0 },
  };

  function lookupItem(id) {
    const numId = parseInt(id, 10);
    if (ITEM_CATALOG[numId]) return { id: numId, ...ITEM_CATALOG[numId] };
    if (DEBRIS_TO_AVATAR_MAP[numId]) {
      const aid = DEBRIS_TO_AVATAR_MAP[numId];
      const charName = AVATAR_NAMES[aid] || `Character #${aid}`;
      return { id: numId, name: `${charName} Debris (Fragment)`, category: 'Character Fragment', rarity: 0 };
    }
    if (AVATAR_NAMES[numId]) {
      return { id: numId, name: `Character: ${AVATAR_NAMES[numId]}`, category: 'Avatar', rarity: 2 };
    }
    const prefix = Math.floor(numId / 1000000);
    let cat = 'General';
    if (prefix === 101 || prefix === 102) cat = 'Avatar';
    else if ([203, 204, 205, 208, 211].includes(prefix)) cat = 'Clothes';
    else if (prefix === 700 || prefix === 710) cat = 'Bundle';
    else if (prefix === 907) cat = 'WeaponSkin';
    else if ([800, 802, 808].includes(prefix)) cat = 'Consumable';
    return { id: numId, name: `Item #${numId}`, category: cat, rarity: 0 };
  }

  // 3. Navigation Sub-bar — Pure Lucide Outline SVGs, Zero Emojis
  const SUB_NAV_TABS = [
    { id: 'overview', hash: '#/luck-royale/overview', label: 'Overview', icon: 'sparkles' },
    { id: 'machines', hash: '#/luck-royale/machines', label: 'Royale Studio', icon: 'sliders' },
    { id: 'pools', hash: '#/luck-royale/pools', label: 'Reward Pools', icon: 'gift' },
    { id: 'banners', hash: '#/luck-royale/banners', label: 'Artwork & Assets', icon: 'image' },
    { id: 'events', hash: '#/luck-royale/events', label: 'Event Rewards', icon: 'calendar' },
    { id: 'pity', hash: '#/luck-royale/pity', label: 'Pity & Meters', icon: 'activity' },
    { id: 'currencies', hash: '#/luck-royale/currencies', label: 'Vouchers & Costs', icon: 'ticket' },
    { id: 'forge', hash: '#/luck-royale/forge', label: 'Incubator Forge', icon: 'hammer' },
    { id: 'player', hash: '#/luck-royale/player', label: 'Player State', icon: 'user' },
    { id: 'transactions', hash: '#/luck-royale/transactions', label: 'Audit Ledger', icon: 'scroll' },
    { id: 'simulator', hash: '#/luck-royale/simulator', label: 'Simulator', icon: 'cpu' },
    { id: 'config', hash: '#/luck-royale/config', label: 'Config Backup', icon: 'fileText' },
  ];

  function renderSubNav(activeId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const tabButtons = SUB_NAV_TABS.map(tab => {
      const isActive = tab.id === activeId;
      const iconSvg = window.UI && window.UI.Icon ? window.UI.Icon(tab.icon, 13) : '';
      return `
        <a href="${tab.hash}" class="lr-nav-pill ${isActive ? 'active' : ''}">
          <span style="display: inline-flex; align-items: center;">${iconSvg}</span>
          <span>${tab.label}</span>
        </a>
      `;
    }).join('');

    return `
      <style>
        .lr-sub-nav {
          display: flex;
          align-items: center;
          gap: 6px;
          overflow-x: auto;
          padding: 6px 4px;
          margin-bottom: 20px;
          border-bottom: 1px solid var(--border-subtle);
          scrollbar-width: none;
        }
        .lr-sub-nav::-webkit-scrollbar { display: none; }
        .lr-nav-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: var(--radius-full);
          background: rgba(255, 255, 255, 0.04);
          color: var(--text-secondary);
          text-decoration: none;
          font-size: 11.5px;
          font-weight: 500;
          white-space: nowrap;
          border: 1px solid var(--border-default);
          transition: all var(--transition-fast);
        }
        .lr-nav-pill:hover {
          color: var(--text-primary);
          background: rgba(255, 255, 255, 0.08);
          border-color: var(--border-hover);
        }
        .lr-nav-pill.active {
          color: #fff;
          background: rgba(56, 189, 248, 0.15);
          border-color: rgba(56, 189, 248, 0.4);
          box-shadow: var(--glow-cyan);
        }
        .lr-context-badge {
          margin-left: auto;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: rgba(16, 185, 129, 0.12);
          border: 1px solid rgba(16, 185, 129, 0.3);
          padding: 4px 10px;
          border-radius: var(--radius-full);
          font-size: 11px;
          color: var(--accent-emerald);
          font-family: var(--font-mono);
          cursor: pointer;
        }
      </style>
      <div class="lr-sub-nav">
        ${tabButtons}
        <div class="lr-context-badge" onclick="window.Topbar ? window.Topbar.promptSwitchPlayer() : null" title="Click to change active player context">
          <span>Active Context: UID ${aid}</span>
        </div>
      </div>
    `;
  }

  // 4. Formatting Utilities
  function formatNumber(num) {
    if (num === undefined || num === null || isNaN(num)) return '0';
    return Number(num).toLocaleString();
  }

  function formatTimestamp(ts) {
    if (!ts) return '—';
    const date = new Date(ts > 10000000000 ? ts : ts * 1000);
    return date.toLocaleString();
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function rarityBadge(level) {
    const l = parseInt(level, 10);
    if (l >= 2) return window.UI.Badge('SUPER RARE', 'amber');
    if (l === 1) return window.UI.Badge('RARE', 'cyan');
    return window.UI.Badge('NORMAL', 'neutral');
  }

  function coinBadge(type) {
    const t = parseInt(type, 10);
    if (t === 2) {
      return `<span style="color: var(--accent-cyan); font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('diamond', 12)} Diamonds</span>`;
    }
    return `<span style="color: var(--accent-amber); font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('coins', 12)} Gold</span>`;
  }

  function renderItemImage(url, name, size, itemId) {
    size = size || 36;
    let cleanUrl = url;
    if (!cleanUrl && itemId) {
      cleanUrl = `/assets/freefire/1.39/items/${itemId}.png`;
    } else if (cleanUrl && !cleanUrl.startsWith('/')) {
      cleanUrl = '/banners/' + cleanUrl;
    }
    if (!cleanUrl) {
      return `
        <div style="width: ${size}px; height: ${size}px; border-radius: 6px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center; color: var(--text-tertiary);" title="${escapeHtml(name || 'No image')}">
          ${window.UI.Icon('gift', Math.floor(size * 0.5))}
        </div>
      `;
    }
    const fallbackAttr = itemId
      ? `onerror="this.onerror=null; this.src='/assets/freefire/1.39/items/${itemId}.png'; this.onerror=function(){ this.style.opacity='0.2'; };"`
      : `onerror="this.onerror=null; this.style.opacity='0.2';"`;
    return `
      <div style="width: ${size}px; height: ${size}px; border-radius: 6px; overflow: hidden; background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border-default); display: flex; align-items: center; justify-content: center; flex-shrink: 0;" title="${escapeHtml(name || '')}">
        <img src="${cleanUrl}" alt="${escapeHtml(name || '')}" style="width: 100%; height: 100%; object-fit: contain;" ${fallbackAttr}>
      </div>
    `;
  }

  window.LuckRoyale.Common = {
    VOUCHERS,
    SPECIAL_ITEMS,
    ITEM_CATALOG,
    AVATAR_DEBRIS_MAP,
    AVATAR_NAMES,
    lookupItem,
    renderSubNav,
    formatNumber,
    formatTimestamp,
    escapeHtml,
    rarityBadge,
    coinBadge,
    renderItemImage,
  };
})();
