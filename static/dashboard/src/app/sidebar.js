/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Sidebar Navigation Component: 10 Expandable Functional Domains
 * Professional SVG Icons (Lucide-style), Persistent Collapsible State & Section Accordion
 */

const Sidebar = {
  storageKeys: {
    collapsed: 'ind_sidebar_collapsed',
    collapsedSections: 'ind_collapsed_sections'
  },

  domains: [
    {
      id: 'overview',
      title: 'Overview',
      items: [
        { hash: '#/overview/main', icon: 'dashboard', label: 'Main Dashboard' },
        { hash: '#/overview/monitoring', icon: 'activity', label: 'Server Monitoring' }
      ]
    },
    {
      id: 'players',
      title: 'Player Management',
      items: [
        { hash: '#/players/directory', icon: 'users', label: 'Player Directory' },
        { hash: '#/players/inspector', icon: 'search', label: 'Player Inspector' },
        { hash: '#/players/account', icon: 'userCog', label: 'Account Manager' },
        { hash: '#/players/bans', icon: 'ban', label: 'Ban & Sanction Manager' },
        { hash: '#/players/sessions', icon: 'zap', label: 'Live Sessions' }
      ]
    },
    {
      id: 'inventory',
      title: 'Inventory & Collection',
      items: [
        { hash: '#/inventory/manager', icon: 'package', label: 'Inventory Manager' },
        { hash: '#/inventory/characters', icon: 'user', label: 'Character Manager' },
        { hash: '#/inventory/pets', icon: 'pawPrint', label: 'Pet Manager' },
        { hash: '#/inventory/wardrobe', icon: 'shirt', label: 'Cosmetics & Wardrobe' }
      ]
    },
    {
      id: 'economy',
      title: 'Economy',
      items: [
        { hash: '#/economy/currencies', icon: 'gem', label: 'Currency Manager' },
        { hash: '#/economy/wallet', icon: 'wallet', label: 'Player Wallet' }
      ]
    },
    {
      id: 'luck-royale',
      title: 'Luck Royale Studio',
      items: [
        { hash: '#/luck-royale/overview', icon: 'dices', label: 'Studio Overview' },
        { hash: '#/luck-royale/machines', icon: 'cog', label: 'Machine Manager' },
        { hash: '#/luck-royale/pools', icon: 'gift', label: 'Reward Pool Editor' },
        { hash: '#/luck-royale/pity', icon: 'trendingUp', label: 'Lucky Meter & Pity' },
        { hash: '#/luck-royale/currencies', icon: 'ticket', label: 'Currencies & Vouchers' },
        { hash: '#/luck-royale/forge', icon: 'hammer', label: 'Incubator Forge' },
        { hash: '#/luck-royale/events', icon: 'flame', label: 'Events & Discounts' },
        { hash: '#/luck-royale/banners', icon: 'image', label: 'Banner Overrides' },
        { hash: '#/luck-royale/player', icon: 'crosshair', label: 'Player Gacha State' },
        { hash: '#/luck-royale/transactions', icon: 'scrollText', label: 'Spin Audit Ledger' },
        { hash: '#/luck-royale/simulator', icon: 'barChart', label: 'Probability Simulator' },
        { hash: '#/luck-royale/config', icon: 'save', label: 'Config Backup' }
      ]
    },
    {
      id: 'game',
      title: 'Game Management',
      items: [
        { hash: '#/game/modes', icon: 'gamepad', label: 'Game Modes' },
        { hash: '#/game/maps', icon: 'map', label: 'Map Rotation' },
        { hash: '#/game/matchmaking', icon: 'timer', label: 'Matchmaking Queue' },
        { hash: '#/game/rooms', icon: 'doorOpen', label: 'Custom Rooms' }
      ]
    },
    {
      id: 'social',
      title: 'Social & Communication',
      items: [
        { hash: '#/social/mail', icon: 'mail', label: 'Mailbox Manager' },
        { hash: '#/social/mail-compose', icon: 'penLine', label: 'Compose Mail' },
        { hash: '#/social/friends', icon: 'handshake', label: 'Friends Manager' },
        { hash: '#/social/squads', icon: 'shield', label: 'Squad Manager' }
      ]
    },
    {
      id: 'cms',
      title: 'Content Management',
      items: [
        { hash: '#/cms/banners', icon: 'palette', label: 'Billboard Banners' },
        { hash: '#/cms/lobby', icon: 'monitor', label: 'Lobby CMS & Splash' },
        { hash: '#/cms/announcements', icon: 'megaphone', label: 'Announcements' }
      ]
    },
    {
      id: 'logs',
      title: 'Logs & Monitoring',
      items: [
        { hash: '#/logs/api', icon: 'zap', label: 'API Live Monitor' },
        { hash: '#/logs/audit', icon: 'clipboardList', label: 'Administrative Audit' }
      ]
    },
    {
      id: 'system',
      title: 'System Administration',
      items: [
        { hash: '#/system/settings', icon: 'settings', label: 'Server Settings' },
        { hash: '#/system/database', icon: 'database', label: 'Database Status' },
        { hash: '#/system/security', icon: 'lock', label: 'Security & Auth' }
      ]
    }
  ],

  _icon(name) {
    return (window.Icons && window.Icons[name]) || '';
  },

  render() {
    const isCollapsed = localStorage.getItem(this.storageKeys.collapsed) === 'true';
    let collapsedSections = [];
    try {
      collapsedSections = JSON.parse(localStorage.getItem(this.storageKeys.collapsedSections) || '[]');
    } catch (e) {
      collapsedSections = [];
    }

    const sectionsHtml = this.domains.map(domain => {
      const isSecCollapsed = collapsedSections.includes(domain.id);
      const itemsHtml = domain.items.map(it => `
        <a class="nav-item" href="${it.hash}" data-route="${it.hash}" title="${it.label}">
          <span class="nav-icon">${this._icon(it.icon)}</span>
          <span class="nav-label">${it.label}</span>
        </a>
      `).join('');

      return `
        <div class="nav-section ${isSecCollapsed ? 'collapsed' : ''}" id="nav-section-${domain.id}" data-section="${domain.id}">
          <div class="nav-section-header" onclick="Sidebar.toggleSection('${domain.id}')">
            <span class="nav-section-title">${domain.title}</span>
            <span class="nav-section-chevron">${this._icon('chevronDown')}</span>
          </div>
          <div class="nav-section-items">
            ${itemsHtml}
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="app-sidebar ${isCollapsed ? 'collapsed' : ''}" id="app-sidebar">
        <div class="sidebar-header" onclick="Sidebar.onHeaderClick(event)">
          <div class="sidebar-brand-group">
            <div class="brand-badge" title="${isCollapsed ? 'Expand sidebar (Ctrl+B)' : 'IND'}">
              <span class="badge-text">IND</span>
              <span class="badge-icon">${this._icon('panelLeft')}</span>
            </div>
            <div class="brand-info">
              <span class="brand-title">Control Center</span>
              <span class="brand-subtitle">FF 2019 Restoration</span>
            </div>
          </div>
          <button class="sidebar-collapse-btn" id="sidebar-collapse-btn" onclick="Sidebar.toggleCollapse(event)" title="Collapse sidebar (Ctrl+B)">
            ${this._icon('panelLeft')}
          </button>
        </div>

        <div class="sidebar-nav">
          ${sectionsHtml}
        </div>
      </div>
    `;
  },

  onHeaderClick(e) {
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar && sidebar.classList.contains('collapsed')) {
      this.toggleCollapse(e);
    }
  },

  onBrandClick(e) {
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar && sidebar.classList.contains('collapsed')) {
      this.toggleCollapse(e);
    }
  },

  init() {
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        this.toggleCollapse();
      }
    });

    window.addEventListener('hashchange', () => {
      this.closeMobile();
    });
  },

  toggleCollapse(e) {
    if (e && e.stopPropagation) e.stopPropagation();
    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;

    const isNowCollapsed = !sidebar.classList.contains('collapsed');
    sidebar.classList.toggle('collapsed', isNowCollapsed);
    localStorage.setItem(this.storageKeys.collapsed, isNowCollapsed ? 'true' : 'false');

    const badge = sidebar.querySelector('.brand-badge');
    if (badge) {
      badge.setAttribute('title', isNowCollapsed ? 'Expand sidebar (Ctrl+B)' : 'IND');
    }
    const btn = document.getElementById('sidebar-collapse-btn');
    if (btn) {
      btn.setAttribute('title', isNowCollapsed ? 'Expand sidebar (Ctrl+B)' : 'Collapse sidebar (Ctrl+B)');
    }
  },

  toggleSection(domainId) {
    const sec = document.getElementById(`nav-section-${domainId}`);
    if (!sec) return;

    // Don't toggle sections in collapsed sidebar mode
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar && sidebar.classList.contains('collapsed')) return;

    sec.classList.toggle('collapsed');

    let collapsed = [];
    document.querySelectorAll('.nav-section.collapsed').forEach(el => {
      const id = el.getAttribute('data-section');
      if (id) collapsed.push(id);
    });
    localStorage.setItem(this.storageKeys.collapsedSections, JSON.stringify(collapsed));
  },

  setActive(hash) {
    document.querySelectorAll('.nav-item').forEach(item => {
      const target = item.getAttribute('href');
      if (target === hash) {
        item.classList.add('active');
        const parentSec = item.closest('.nav-section');
        if (parentSec && parentSec.classList.contains('collapsed')) {
          parentSec.classList.remove('collapsed');
          let collapsed = [];
          document.querySelectorAll('.nav-section.collapsed').forEach(el => {
            const id = el.getAttribute('data-section');
            if (id) collapsed.push(id);
          });
          localStorage.setItem(this.storageKeys.collapsedSections, JSON.stringify(collapsed));
        }
      } else {
        item.classList.remove('active');
      }
    });
  },

  toggleMobile() {
    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;

    const isOpen = sidebar.classList.toggle('mobile-open');
    let backdrop = document.getElementById('sidebar-backdrop');
    if (isOpen) {
      if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.id = 'sidebar-backdrop';
        backdrop.className = 'sidebar-backdrop';
        backdrop.onclick = () => this.closeMobile();
        document.body.appendChild(backdrop);
      }
    } else {
      if (backdrop) backdrop.remove();
    }
  },

  closeMobile() {
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar) sidebar.classList.remove('mobile-open');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (backdrop) backdrop.remove();
  }
};

window.Sidebar = Sidebar;
