/**
 * Dedicated Unit & DOM Integration Test Suite for Player Management Modules
 * Tests: directory.js, inspector.js, account.js, bans.js, sessions.js
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

console.log('--- Initializing Player Modules Test Environment ---');

// Mock Browser Environment
const window = {
  location: { hash: '#/players/directory' },
  localStorage: {
    _store: {},
    getItem(k) { return this._store[k] || null; },
    setItem(k, v) { this._store[k] = String(v); },
    removeItem(k) { delete this._store[k]; }
  },
  navigator: {
    clipboard: {
      async writeText(t) { return true; }
    }
  },
  document: {
    getElementById(id) {
      if (!this._elements) this._elements = {};
      if (!this._elements[id]) {
        this._elements[id] = {
          id,
          innerHTML: '',
          value: '',
          style: {},
          classList: { add() {}, remove() {} },
          appendChild() {},
          remove() {}
        };
      }
      return this._elements[id];
    },
    createElement(tag) {
      return {
        tagName: tag,
        innerHTML: '',
        style: {},
        classList: { add() {}, remove() {} },
        appendChild() {},
        remove() {}
      };
    },
    body: {
      appendChild() {}
    },
    querySelectorAll() { return []; },
    addEventListener() {}
  },
  addEventListener() {},
  UI: {
    Card(t, s, b, a = '') { return `<div class="card"><h3>${t}</h3><p>${s}</p>${b}${a}</div>`; },
    StatCard(l, v, d = '', i = '', var_ = 'cyan') { return `<div class="stat-card"><span>${l}</span><div>${v}</div></div>`; },
    EmptyState(t, m, i = '') { return `<div class="empty-state">${t}</div>`; },
    Badge(t, v) { return `<span class="badge ${v}">${t}</span>`; },
    Button(l, v, c) { return `<button class="${v}" onclick="${c}">${l}</button>`; },
    Table(cols, rows, empty = '') { return `<table><thead><tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${rows || empty}</tbody></table>`; },
    UnavailableState(f, r, n) { return `<div class="unavailable">${f} ${r} ${n}</div>`; },
    Loading(t) { return `<div class="loading">${t}</div>`; },
    Toast(m, t) {},
    Modal(t, b, a) {},
    Confirm(t, m, cb) { cb(); }
  },
  apiClient: {
    _token: '',
    getToken() { return this._token; },
    setToken(t) { this._token = t; },
    async get(endpoint, params) {
      if (endpoint === '/api/admin/players') {
        return {
          ok: true,
          data: {
            players: [
              { account_id: 10001, nickname: 'Pushpa_1795265111', level: 60, diamonds: 50000, gold: 499700, is_banned: false, is_online: true },
              { account_id: 10002, nickname: 'SniperKing', level: 60, diamonds: 25000, gold: 300000, is_banned: false, is_online: false }
            ],
            total: 2,
            page: 1,
            limit: 15
          }
        };
      }
      if (endpoint.startsWith('/api/admin/players/')) {
        return {
          ok: true,
          data: {
            account_id: 10001,
            profile: { account_id: 10001, nickname: 'Pushpa_1795265111', level: 60, exp: 99999, rank: 315, diamonds: 50000, gold: 499700 },
            wallet: { coins: 499700, gems: 50000 },
            is_banned: false
          }
        };
      }
      if (endpoint === '/api/dashboard/state') {
        return {
          ok: true,
          data: {
            profile: { account_id: 10001, nickname: 'Pushpa_1795265111', level: 60, exp: 99999, rank: 315 },
            wallet: { coins: 499700, gems: 50000 },
            all_players: [
              { account_id: 10001, nickname: 'Pushpa_1795265111', level: 60, diamonds: 50000, gold: 499700, is_banned: false },
              { account_id: 10002, nickname: 'SniperKing', level: 60, diamonds: 25000, gold: 300000, is_banned: false }
            ]
          }
        };
      }
      if (endpoint === '/api/dashboard/requests') {
        return { ok: true, data: [{ time: '18:00:00', method: 'GET', path: '/api/dashboard/state', ip: '127.0.0.1' }] };
      }
      return { ok: true, data: {} };
    },
    async post(endpoint, body) {
      if (endpoint === '/api/admin/players/create') {
        return { ok: true, data: { account_id: 10003 } };
      }
      if (endpoint.endsWith('/ban')) {
        return { ok: true, is_banned: true };
      }
      if (endpoint.endsWith('/unban')) {
        return { ok: true, is_banned: false };
      }
      if (endpoint === '/api/dashboard/profile/update') {
        return { ok: true, profile: body };
      }
      if (endpoint === '/api/dashboard/wallet/grant') {
        return { ok: true, wallet: body };
      }
      return { ok: true, data: {} };
    },
    async delete(endpoint) {
      return { ok: true };
    }
  },
  playerContext: {
    selectedAccountId: 10001,
    playerData: {
      profile: { account_id: 10001, nickname: 'Pushpa_1795265111', level: 60, exp: 99999, rank: 315, diamonds: 50000, gold: 499700 },
      wallet: { coins: 499700, gems: 50000 }
    },
    getSelectedAccountId() { return this.selectedAccountId; },
    getCurrentPlayer() { return this.playerData; },
    async setAccountId(id) { this.selectedAccountId = parseInt(id, 10); },
    async refresh() {},
    subscribe(cb) {}
  },
  appRouter: {
    routes: new Map(),
    register(path, handler) { this.routes.set(path, handler); },
    navigate(path) { window.location.hash = path; }
  },
  Modules: {}
};

global.window = window;
global.document = window.document;
global.navigator = window.navigator;
global.localStorage = window.localStorage;

const sandbox = vm.createContext({
  ...window,
  window: window,
  global: window,
  console: console,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout
});

function loadScript(relPath) {
  const fullPath = path.resolve(__dirname, relPath);
  const code = fs.readFileSync(fullPath, 'utf8');
  vm.runInContext(code, sandbox, { filename: relPath });
}

// 1. Load Player Modules
loadScript('../static/dashboard/src/modules/players/directory.js');
loadScript('../static/dashboard/src/modules/players/inspector.js');
loadScript('../static/dashboard/src/modules/players/account.js');
loadScript('../static/dashboard/src/modules/players/bans.js');
loadScript('../static/dashboard/src/modules/players/sessions.js');

console.log('✓ All 5 player modules evaluated cleanly in sandbox.');

// 2. Assert Modules Exported
assert.strictEqual(typeof window.Modules.PlayersDirectory, 'function', 'PlayersDirectory must be a function');
assert.strictEqual(typeof window.Modules.PlayersInspector, 'function', 'PlayersInspector must be a function');
assert.strictEqual(typeof window.Modules.PlayersAccount, 'function', 'PlayersAccount must be a function');
assert.strictEqual(typeof window.Modules.PlayersBans, 'function', 'PlayersBans must be a function');
assert.strictEqual(typeof window.Modules.PlayersSessions, 'function', 'PlayersSessions must be a function');
console.log('✓ All 5 module views registered on window.Modules.');

// 3. Assert Router Registrations
assert(window.appRouter.routes.has('#/players/directory'), 'Route #/players/directory must be registered');
assert(window.appRouter.routes.has('#/players/inspector'), 'Route #/players/inspector must be registered');
assert(window.appRouter.routes.has('#/players/account'), 'Route #/players/account must be registered');
assert(window.appRouter.routes.has('#/players/bans'), 'Route #/players/bans must be registered');
assert(window.appRouter.routes.has('#/players/sessions'), 'Route #/players/sessions must be registered');
console.log('✓ All 5 routes registered in SPA AppRouter.');

// 4. Test Render Execution
async function testRender() {
  const canvas = { innerHTML: '' };
  
  // Test Directory Render
  await window.Modules.PlayersDirectory(canvas);
  assert(canvas.innerHTML.includes('Player Directory'), 'Directory must render header');
  assert(canvas.innerHTML.includes('10001'), 'Directory must render account 10001');
  console.log('✓ PlayersDirectory rendered successfully.');

  // Test Inspector Render
  await window.Modules.PlayersInspector(canvas);
  assert(canvas.innerHTML.includes('Player Inspector'), 'Inspector must render header');
  assert(canvas.innerHTML.includes('Pushpa_1795265111'), 'Inspector must render player nickname');
  console.log('✓ PlayersInspector rendered successfully.');

  // Test Account Render
  await window.Modules.PlayersAccount(canvas);
  assert(canvas.innerHTML.includes('Account Manager'), 'Account manager must render header');
  assert(canvas.innerHTML.includes('Create Account'), 'Account manager must render create button');
  console.log('✓ PlayersAccount rendered successfully.');

  // Test Bans Render
  await window.Modules.PlayersBans(canvas);
  assert(canvas.innerHTML.includes('Ban Manager'), 'Bans manager must render header');
  assert(canvas.innerHTML.includes('Suspend / Ban Account'), 'Bans manager must render ban button');
  console.log('✓ PlayersBans rendered successfully.');

  // Test Sessions Render
  await window.Modules.PlayersSessions(canvas);
  assert(canvas.innerHTML.includes('Live Sessions'), 'Sessions must render header');
  assert(canvas.innerHTML.includes('PORT 8081'), 'Sessions must render TCP Lobby Port');
  console.log('✓ PlayersSessions rendered successfully.');

  // 5. Test Player Switching Logic
  await window.selectAndSetContextPlayer(10002);
  assert.strictEqual(window.playerContext.getSelectedAccountId(), 10002, 'Context must switch to 10002');
  console.log('✓ PlayerContext switching verified.');

  console.log('======================================================================');
  console.log('ALL PLAYER MANAGEMENT UNIT & DOM INTEGRATION TESTS PASSED (100%)');
  console.log('======================================================================');
}

testRender().catch(err => {
  console.error('Test failure:', err);
  process.exit(1);
});
