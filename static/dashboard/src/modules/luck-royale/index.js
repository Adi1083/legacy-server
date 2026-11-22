/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Master Module Entry Point & SPA Workspace Router Registration
 * (index.js)
 */

window.LuckRoyale = window.LuckRoyale || {};
window.Modules = window.Modules || {};

(function () {
  'use strict';

  // Sub-script manifest for modular loading
  const MODULE_SCRIPTS = [
    'src/modules/luck-royale/common.js',
    'src/modules/luck-royale/overview.js',
    'src/modules/luck-royale/machines.js',
    'src/modules/luck-royale/pools.js',
    'src/modules/luck-royale/pity.js',
    'src/modules/luck-royale/currencies.js',
    'src/modules/luck-royale/forge.js',
    'src/modules/luck-royale/events.js',
    'src/modules/luck-royale/banners.js',
    'src/modules/luck-royale/player.js',
    'src/modules/luck-royale/transactions.js',
    'src/modules/luck-royale/simulator.js',
    'src/modules/luck-royale/config.js',
  ];

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      // Check if script already loaded
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        return resolve();
      }
      const s = document.createElement('script');
      s.src = src;
      s.onload = () => resolve();
      s.onerror = (e) => {
        console.warn(`[LuckRoyale] Script load error: ${src}`, e);
        resolve(); // Continue anyway
      };
      document.head.appendChild(s);
    });
  }

  async function ensureModuleScriptsLoaded() {
    for (const src of MODULE_SCRIPTS) {
      await loadScript(src);
    }
  }

  function registerWorkspaces() {
    const router = window.appRouter;
    if (!router) {
      console.warn('[LuckRoyale] appRouter not yet ready, deferring route registration.');
      return;
    }

    // 1. Studio Overview (#05.1)
    router.register('#/luck-royale/overview', async (canvas) => {
      if (window.LuckRoyale.Overview) return window.LuckRoyale.Overview(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Overview) return window.LuckRoyale.Overview(canvas);
    });

    // 2. Machine Manager (#05.2)
    router.register('#/luck-royale/machines', async (canvas) => {
      if (window.LuckRoyale.Machines) return window.LuckRoyale.Machines(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Machines) return window.LuckRoyale.Machines(canvas);
    });

    // 3. Reward Pool Editor (#05.3)
    router.register('#/luck-royale/pools', async (canvas) => {
      if (window.LuckRoyale.Pools) return window.LuckRoyale.Pools(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Pools) return window.LuckRoyale.Pools(canvas);
    });

    // 4. Lucky Meter & Pity Thresholds (#05.4)
    router.register('#/luck-royale/pity', async (canvas) => {
      if (window.LuckRoyale.Pity) return window.LuckRoyale.Pity(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Pity) return window.LuckRoyale.Pity(canvas);
    });

    // 5. Currency & Voucher Manager (#05.5)
    router.register('#/luck-royale/currencies', async (canvas) => {
      if (window.LuckRoyale.Currencies) return window.LuckRoyale.Currencies(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Currencies) return window.LuckRoyale.Currencies(canvas);
    });

    // 6. Incubator Special Exchange Forge (#05.6)
    router.register('#/luck-royale/forge', async (canvas) => {
      if (window.LuckRoyale.Forge) return window.LuckRoyale.Forge(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Forge) return window.LuckRoyale.Forge(canvas);
    });

    // 7. Gacha Events & Discounts (#05.7)
    router.register('#/luck-royale/events', async (canvas) => {
      if (window.LuckRoyale.Events) return window.LuckRoyale.Events(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Events) return window.LuckRoyale.Events(canvas);
    });

    // 8. Banner Overrides (#05.8)
    router.register('#/luck-royale/banners', async (canvas) => {
      if (window.LuckRoyale.Banners) return window.LuckRoyale.Banners(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Banners) return window.LuckRoyale.Banners(canvas);
    });

    // 9. Player Gacha State (#05.9)
    router.register('#/luck-royale/player', async (canvas) => {
      if (window.LuckRoyale.Player) return window.LuckRoyale.Player(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Player) return window.LuckRoyale.Player(canvas);
    });

    // 10. Spin Audit Ledger (#05.10)
    router.register('#/luck-royale/transactions', async (canvas) => {
      if (window.LuckRoyale.Transactions) return window.LuckRoyale.Transactions(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Transactions) return window.LuckRoyale.Transactions(canvas);
    });

    // 11. Probability Simulator (#05.11)
    router.register('#/luck-royale/simulator', async (canvas) => {
      if (window.LuckRoyale.Simulator) return window.LuckRoyale.Simulator(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Simulator) return window.LuckRoyale.Simulator(canvas);
    });

    // 12. Gacha Config & Client Preview (#05.12)
    router.register('#/luck-royale/config', async (canvas) => {
      if (window.LuckRoyale.Config) return window.LuckRoyale.Config(canvas);
      await ensureModuleScriptsLoaded();
      if (window.LuckRoyale.Config) return window.LuckRoyale.Config(canvas);
    });

    // Export module container
    window.Modules.LuckRoyale = {
      Overview: window.LuckRoyale.Overview,
      Machines: window.LuckRoyale.Machines,
      Pools: window.LuckRoyale.Pools,
      Pity: window.LuckRoyale.Pity,
      Currencies: window.LuckRoyale.Currencies,
      Forge: window.LuckRoyale.Forge,
      Events: window.LuckRoyale.Events,
      Banners: window.LuckRoyale.Banners,
      Player: window.LuckRoyale.Player,
      Transactions: window.LuckRoyale.Transactions,
      Simulator: window.LuckRoyale.Simulator,
      Config: window.LuckRoyale.Config
    };

    // If current hash is within luck-royale, re-trigger route
    if (window.location.hash && window.location.hash.startsWith('#/luck-royale/')) {
      router.handleRoute();
    }
  }

  // Preload scripts and register
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async () => {
      await ensureModuleScriptsLoaded();
      registerWorkspaces();
    });
  } else {
    ensureModuleScriptsLoaded().then(() => {
      registerWorkspaces();
    });
  }

  // Also immediately expose on window
  window.LuckRoyale.registerWorkspaces = registerWorkspaces;
  window.LuckRoyale.ensureModuleScriptsLoaded = ensureModuleScriptsLoaded;
})();
