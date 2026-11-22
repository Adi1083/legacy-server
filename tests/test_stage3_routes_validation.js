/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Stage 3 Final Integration Verification Test
 * Validates all 38 routes, default redirection, 404 fallback, and topbar title updates.
 */

const fs = require('fs');
const path = require('path');

// Mock DOM & Browser Environment
const localStorageData = {};
global.localStorage = {
  getItem: (k) => localStorageData[k] || null,
  setItem: (k, v) => { localStorageData[k] = String(v); },
  removeItem: (k) => { delete localStorageData[k]; }
};

const domElements = new Map();
function createMockElement(id, classes = []) {
  const el = {
    id,
    classList: {
      _classes: new Set(classes),
      add: (c) => el.classList._classes.add(c),
      remove: (c) => el.classList._classes.delete(c),
      toggle: (c) => {
        if (el.classList._classes.has(c)) {
          el.classList._classes.delete(c);
          return false;
        } else {
          el.classList._classes.add(c);
          return true;
        }
      },
      contains: (c) => el.classList._classes.has(c)
    },
    innerHTML: '',
    textContent: '',
    attributes: {},
    getAttribute: (name) => el.attributes[name] || null,
    setAttribute: (name, val) => { el.attributes[name] = val; },
    querySelector: (selector) => createMockElement('mock-inner'),
    querySelectorAll: (selector) => [],
    closest: (selector) => null,
    remove: () => {}
  };
  domElements.set(id, el);
  return el;
}

const mockCanvas = createMockElement('workspace-canvas');
const mockBreadcrumbs = createMockElement('topbar-breadcrumbs');
createMockElement('app-sidebar');
createMockElement('sidebar-collapse-btn');
createMockElement('player-pill');
createMockElement('player-pill-label');
createMockElement('app-root');
createMockElement('toast-container');

const domListeners = [];
global.window = global;
global.window.location = { hash: '' };
global.window.addEventListener = () => {};
global.document = {
  addEventListener: (event, cb) => {
    if (event === 'DOMContentLoaded') domListeners.push(cb);
  },
  getElementById: (id) => domElements.get(id) || null,
  querySelectorAll: (selector) => {
    if (selector === '.nav-item') {
      return (Sidebar.domains || []).flatMap(d => d.items.map(it => ({
        getAttribute: (attr) => attr === 'href' ? it.hash : null,
        classList: { add: () => {}, remove: () => {} },
        closest: () => ({ classList: { contains: () => false, remove: () => {} } })
      })));
    }
    return [];
  }
};

// Mock UI Factory
global.window.UI = {
  Card: (t, s, b) => `<div class="glass-card"><h3>${t}</h3><p>${s}</p><div>${b}</div></div>`,
  StatCard: (l, v, s, i) => `<div class="stat-card"><div>${l}</div><div>${v}</div><div>${s}</div></div>`,
  Button: (l, v, c) => `<button class="btn btn-${v}" onclick="${c}">${l}</button>`,
  Badge: (t, v) => `<span class="badge badge-${v}">${t}</span>`,
  Table: (cols, rows, empty) => `<table class="glass-table"><thead><tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${rows || empty}</tbody></table>`,
  Loading: (txt) => `<div class="loading-box">${txt}</div>`,
  EmptyState: (t, d) => `<div class="empty-state"><h4>${t}</h4><p>${d}</p></div>`,
  UnavailableState: (f, e, n) => `<div class="unavailable-box"><h4>${f}</h4><code>${e}</code><p>${n}</p></div>`,
  Modal: (t, b, f) => {},
  Confirm: (t, m, cb, d) => {},
  Toast: (m, t) => {}
};

// Mock ApiClient & PlayerContext
global.window.apiClient = {
  get: async (url) => {
    if (url.includes('requests')) return { ok: true, data: [] };
    if (url.includes('players')) return { ok: true, data: { players: [], total: 0 } };
    if (url.includes('machines')) return { ok: true, data: { machines: [] } };
    if (url.includes('audit')) return { ok: true, data: { transactions: [] } };
    if (url.includes('modes')) return { ok: true, data: { modes: {} } };
    if (url.includes('mail')) return { ok: true, data: { mails: [] } };
    if (url.includes('banners')) return { ok: true, data: { banners: [] } };
    if (url.includes('branding')) return { ok: true, data: { slots: {} } };
    return { ok: true, data: [] };
  },
  post: async (url) => ({ ok: true, data: {} }),
  getToken: () => 'mock_token',
  setToken: () => {}
};

global.window.playerContext = {
  getSelectedAccountId: () => 10001,
  getCurrentPlayer: () => ({ account_id: 10001, nickname: 'PushpaGG', wallet: { diamonds: 500, gold: 10000 } }),
  subscribe: () => () => {},
  refresh: async () => {}
};

// Load Shell & Router Scripts
require('../static/dashboard/src/app/sidebar.js');
require('../static/dashboard/src/app/topbar.js');
require('../static/dashboard/src/app/router.js');

// List of all 38 mandatory routes across all 10 domains
const MANDATORY_ROUTES = [
  // 01 Overview
  '#/overview/main',
  '#/overview/monitoring',
  // 02 Player Management
  '#/players/directory',
  '#/players/inspector',
  '#/players/account',
  '#/players/bans',
  '#/players/sessions',
  // 03 Inventory & Collection
  '#/inventory/manager',
  '#/inventory/characters',
  '#/inventory/pets',
  '#/inventory/wardrobe',
  // 04 Economy
  '#/economy/currencies',
  '#/economy/wallet',
  // 05 Luck Royale Studio
  '#/luck-royale/overview',
  '#/luck-royale/machines',
  '#/luck-royale/pools',
  '#/luck-royale/pity',
  '#/luck-royale/currencies',
  '#/luck-royale/forge',
  '#/luck-royale/events',
  '#/luck-royale/banners',
  '#/luck-royale/player',
  '#/luck-royale/transactions',
  '#/luck-royale/simulator',
  // 06 Game Management
  '#/game/modes',
  '#/game/maps',
  '#/game/matchmaking',
  '#/game/rooms',
  // 07 Social & Communication
  '#/social/mail',
  '#/social/mail-compose',
  '#/social/friends',
  '#/social/squads',
  // 08 Content Management
  '#/cms/banners',
  '#/cms/lobby',
  '#/cms/announcements',
  // 09 Logs & Monitoring
  '#/logs/api',
  '#/logs/audit',
  // 10 System Administration
  '#/system/settings',
  '#/system/database',
  '#/system/security'
];

async function runStage3Verification() {
  console.log('====================================================');
  console.log('STAGE 3 FINAL ROUTE & NAVIGATION INTEGRATION AUDIT');
  console.log('====================================================\n');

  // Load app.js fallback registration
  console.log('1. Loading app.js workspace registrations...');
  const appJsCode = fs.readFileSync(path.join(__dirname, '../static/dashboard/src/app/app.js'), 'utf8');

  // Execute app.js in sandboxed scope to register routes
  const evalApp = new Function('require', 'fs', 'path', appJsCode);
  evalApp(require, fs, path);
  for (const cb of domListeners) {
    await cb();
  }
  console.log(`   Registered routes in router: ${appRouter.routes.size}\n`);

  // 1. Verify Default Route Redirection
  console.log('2. Verifying default route redirection...');
  window.location.hash = '';
  appRouter.start();
  if (window.location.hash !== '#/overview/main') {
    throw new Error(`Default route redirection failed: expected #/overview/main, got ${window.location.hash}`);
  }
  console.log('   [PASS] Empty hash automatically redirected to #/overview/main\n');

  // 2. Verify All 38 Routes Dispatch Cleanly
  console.log(`3. Validating all ${MANDATORY_ROUTES.length} mandatory workspace routes...`);
  let dispatched = 0;

  for (const route of MANDATORY_ROUTES) {
    window.location.hash = route;
    await appRouter.handleRoute();

    // Verify workspace canvas received content
    if (!mockCanvas.innerHTML || mockCanvas.innerHTML.trim() === '') {
      throw new Error(`Route ${route} rendered empty canvas!`);
    }

    // Verify canvas did NOT render 404 or unhandled error
    if (mockCanvas.innerHTML.includes('Workspace Not Found')) {
      throw new Error(`Route ${route} unexpectedly triggered 404 Workspace Not Found!`);
    }
    if (mockCanvas.innerHTML.includes('Workspace Render Error')) {
      throw new Error(`Route ${route} unexpectedly triggered Workspace Render Error!`);
    }

    // Verify Topbar Breadcrumbs updated
    if (!mockBreadcrumbs.innerHTML || mockBreadcrumbs.innerHTML.trim() === '') {
      throw new Error(`Route ${route} failed to update topbar breadcrumbs!`);
    }

    dispatched++;
  }
  console.log(`   [PASS] Successfully dispatched all ${dispatched}/${MANDATORY_ROUTES.length} routes with non-empty content.\n`);

  // 3. Verify Topbar Route Title Formatting
  console.log('4. Verifying topbar dynamic breadcrumb titles...');
  const testCases = [
    { route: '#/overview/main', expectedSec: 'OVERVIEW', expectedView: 'MAIN DASHBOARD' },
    { route: '#/players/directory', expectedSec: 'PLAYER MANAGEMENT', expectedView: 'PLAYER DIRECTORY' },
    { route: '#/inventory/manager', expectedSec: 'INVENTORY & COLLECTION', expectedView: 'INVENTORY MANAGER' },
    { route: '#/economy/currencies', expectedSec: 'ECONOMY', expectedView: 'CURRENCY MANAGER' },
    { route: '#/luck-royale/pools', expectedSec: 'LUCK ROYALE STUDIO', expectedView: 'REWARD POOL EDITOR' },
    { route: '#/game/modes', expectedSec: 'GAME MANAGEMENT', expectedView: 'GAME MODES' },
    { route: '#/social/mail', expectedSec: 'SOCIAL & COMMUNICATION', expectedView: 'MAILBOX MANAGER' },
    { route: '#/cms/banners', expectedSec: 'CONTENT MANAGEMENT', expectedView: 'BILLBOARD' },
    { route: '#/logs/api', expectedSec: 'LOGS & MONITORING', expectedView: 'API LIVE MONITOR' },
    { route: '#/system/settings', expectedSec: 'SYSTEM ADMINISTRATION', expectedView: 'SERVER SETTINGS' }
  ];

  for (const tc of testCases) {
    window.location.hash = tc.route;
    await appRouter.handleRoute();
    const bcHtml = mockBreadcrumbs.innerHTML.toUpperCase();
    if (!bcHtml.includes(tc.expectedSec) || !bcHtml.includes(tc.expectedView)) {
      throw new Error(`Breadcrumbs for ${tc.route} mismatch: expected ${tc.expectedSec} and ${tc.expectedView}, got: ${bcHtml}`);
    }
  }
  console.log(`   [PASS] Verified topbar breadcrumb formatting across sample routes.\n`);

  // 4. Verify 404 Error Boundary Fallback
  console.log('5. Verifying 404 error boundary fallback...');
  window.location.hash = '#/nonexistent/subsystem';
  await appRouter.handleRoute();

  if (!mockCanvas.innerHTML.includes('Workspace Not Found')) {
    throw new Error('404 route failed to display Workspace Not Found card!');
  }
  if (!mockCanvas.innerHTML.includes('#/nonexistent/subsystem')) {
    throw new Error('404 card failed to echo unmapped route path!');
  }
  if (!mockCanvas.innerHTML.includes('#/overview/main')) {
    throw new Error('404 card missing return to overview navigation button!');
  }
  console.log('   [PASS] 404 error boundary triggered with clean recovery button.\n');

  // 5. Verify Exception Error Boundary
  console.log('6. Verifying runtime exception error boundary...');
  appRouter.register('#/test/error-route', async () => {
    throw new Error('Simulated runtime exception in view');
  });

  window.location.hash = '#/test/error-route';
  await appRouter.handleRoute();

  if (!mockCanvas.innerHTML.includes('Workspace Render Error')) {
    throw new Error('Runtime error boundary failed to catch view exception!');
  }
  if (!mockCanvas.innerHTML.includes('Simulated runtime exception in view')) {
    throw new Error('Error boundary failed to display error message!');
  }
  console.log('   [PASS] Runtime exception error boundary caught error and displayed recovery card.\n');

  console.log('====================================================');
  console.log('ALL STAGE 3 INTEGRATION ASSERTIONS PASSED (100%)');
  console.log('====================================================');
}

runStage3Verification().catch(err => {
  console.error('\n[STAGE 3 VERIFICATION FAILED]:', err);
  process.exit(1);
});
