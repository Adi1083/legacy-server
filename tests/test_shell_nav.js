const fs = require('fs');
const path = require('path');

// Mock browser environment with DOM simulation
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
    closest: (selector) => null
  };
  domElements.set(id, el);
  return el;
}

createMockElement('app-sidebar');
createMockElement('sidebar-collapse-btn');
createMockElement('sidebar-toggle-btn');
createMockElement('topbar-breadcrumbs');
createMockElement('player-pill');
createMockElement('player-pill-label');
createMockElement('workspace-canvas');

global.window = global;
global.window.location = { hash: '#/overview/main' };
global.window.addEventListener = () => {};
global.document = {
  addEventListener: () => {},
  getElementById: (id) => domElements.get(id) || null,
  querySelectorAll: (selector) => []
};

// UI Mock
global.window.UI = {
  Toast: (msg, type) => console.log(`[Toast] ${type}: ${msg}`),
  Loading: (txt) => `<div>${txt}</div>`,
  Card: (t, s, b) => `<div><h3>${t}</h3><p>${s}</p><div>${b}</div></div>`
};

// Load scripts
require('../static/dashboard/src/app/sidebar.js');
require('../static/dashboard/src/app/topbar.js');
require('../static/dashboard/src/app/router.js');

console.log('=== CHECKING SIDEBAR ===');
console.log('Domains count:', Sidebar.domains.length);
if (Sidebar.domains.length !== 10) throw new Error('Expected 10 domains');

const sidebarHtml = Sidebar.render();
if (!sidebarHtml.includes('id="sidebar-collapse-btn"') && !sidebarHtml.includes('id="sidebar-toggle-btn"')) throw new Error('Missing sidebar toggle/collapse button');
if (!sidebarHtml.includes('Overview')) throw new Error('Missing Overview domain');
if (!sidebarHtml.includes('System Administration')) throw new Error('Missing System Administration domain');

// Test toggle collapse
const sidebarEl = domElements.get('app-sidebar');
Sidebar.toggleCollapse();
if (!sidebarEl.classList.contains('collapsed')) throw new Error('Sidebar failed to add collapsed class');
if (localStorage.getItem('ind_sidebar_collapsed') !== 'true') throw new Error('Sidebar failed to save collapsed state');
Sidebar.toggleCollapse();
if (sidebarEl.classList.contains('collapsed')) throw new Error('Sidebar failed to remove collapsed class');
if (localStorage.getItem('ind_sidebar_collapsed') !== 'false') throw new Error('Sidebar failed to save expanded state');
console.log('Sidebar collapse toggle and persistence verified.');

console.log('=== CHECKING TOPBAR ===');
const topbarHtml = Topbar.render();
if (!topbarHtml.includes('player-pill')) throw new Error('Missing player-pill');
if (!topbarHtml.includes('topbar-breadcrumbs')) throw new Error('Missing topbar-breadcrumbs');
if (!topbarHtml.includes('openAuthModal')) throw new Error('Missing openAuthModal');

// Test breadcrumb update
Topbar.updateBreadcrumbs('#/luck-royale/pools');
const bcEl = domElements.get('topbar-breadcrumbs');
if (!bcEl.innerHTML.includes('LUCK ROYALE') || !bcEl.innerHTML.includes('REWARD POOL EDITOR')) {
  throw new Error('Breadcrumbs formatting incorrect: ' + bcEl.innerHTML);
}
console.log('Topbar dynamic breadcrumbs verified:', bcEl.innerHTML.trim());

console.log('=== CHECKING ROUTER ===');
if (typeof appRouter.register !== 'function') throw new Error('Router missing register');
if (typeof appRouter.navigate !== 'function') throw new Error('Router missing navigate');
if (typeof appRouter.parseRoute !== 'function') throw new Error('Router missing parseRoute');

const parsed = appRouter.parseRoute('#/luck-royale/pools?tab=weights');
if (parsed.cleanPath !== '#/luck-royale/pools') throw new Error('Route parsing mismatch');
if (parsed.params.tab !== 'weights') throw new Error('Query param parsing mismatch');

// Test router fallback protection
let primaryCalled = false;
let fallbackCalled = false;
appRouter.register('#/test/route', () => { primaryCalled = true; });
appRouter.register('#/test/route', () => { fallbackCalled = true; }, true); // fallback register should NOT overwrite
appRouter.routes.get('#/test/route')();
if (!primaryCalled || fallbackCalled) throw new Error('Fallback protection failed in router');
console.log('Router fallback registration protection verified.');

console.log('=== CHECKING INDEX.HTML REFERENCES ===');
const indexHtml = fs.readFileSync(path.join(__dirname, '../static/dashboard/index.html'), 'utf8');
const srcRegex = /src=["']([^"']+)["']/g;
let match;
let missing = 0;
while ((match = srcRegex.exec(indexHtml)) !== null) {
  const rel = match[1];
  const full = path.join(__dirname, '../static/dashboard', rel);
  if (!fs.existsSync(full)) {
    console.error('Missing script reference in index.html:', rel);
    missing++;
  }
}

const hrefRegex = /href=["']([^"']+\.css)["']/g;
while ((match = hrefRegex.exec(indexHtml)) !== null) {
  const rel = match[1];
  const full = path.join(__dirname, '../static/dashboard', rel);
  if (!fs.existsSync(full)) {
    console.error('Missing stylesheet reference in index.html:', rel);
    missing++;
  }
}

if (missing > 0) {
  throw new Error(`Found ${missing} missing file references in index.html`);
}

console.log('All referenced scripts and stylesheets in index.html exist on disk! 0 missing.');
console.log('=== ALL SHELL VERIFICATION TESTS PASSED SUCCESSFULLY! ===');
