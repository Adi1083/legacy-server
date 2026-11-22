/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Master Application Bootstrapper & Workspace Registry
 */

document.addEventListener('DOMContentLoaded', async () => {
  const root = document.getElementById('app-root');
  if (!root) return;

  // 1. Render App Shell Layout
  root.innerHTML = `
    ${window.Sidebar.render()}
    <div class="app-main">
      ${window.Topbar.render()}
      <div class="workspace-canvas" id="workspace-canvas"></div>
    </div>
  `;

  // 2. Initialize Shell Components
  window.Sidebar.init();
  window.Topbar.init();

  // 3. Register All 38 Workspaces in SPA Router
  const router = window.appRouter;
  const originalRegister = router.register.bind(router);

  function registerFallback(path, handler) {
    if (router.has(path)) return; // Don't override specialized module if already registered
    originalRegister(path, async (canvas, params) => {
      const parts = path.replace('#/', '').split('/');
      const domain = parts[0];
      const view = parts[1];
      const camel = domain.replace(/-([a-z])/g, g => g[1].toUpperCase()) +
                    view.charAt(0).toUpperCase() + view.slice(1).replace(/-([a-z])/g, g => g[1].toUpperCase());

      if (window.Modules && typeof window.Modules[camel] === 'function') {
        return window.Modules[camel](canvas, params);
      }
      if (window.Modules && typeof window.Modules[path] === 'function') {
        return window.Modules[path](canvas, params);
      }
      if (window.Modules && window.Modules[domain] && typeof window.Modules[domain][view] === 'function') {
        return window.Modules[domain][view](canvas, params);
      }

      return handler(canvas, params);
    }, true);
  }

  // Use registerFallback for workspace bootstrapping
  router.register = registerFallback;

  // --- 01 OVERVIEW ---
  router.register('#/overview/main', async (canvas) => {
    if (window.Modules && window.Modules.OverviewMain) {
      return window.Modules.OverviewMain(canvas);
    }
    const state = window.playerContext.getCurrentPlayer();
    canvas.innerHTML = window.UI.Card(
      'IND PROJECT Command Overview',
      'FF 2019 Restoration Status',
      `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase;">HTTP Server</div>
            <div style="font-size: 20px; font-weight: 700; color: var(--accent-emerald); margin: 4px 0;">PORT 8080</div>
            <div style="font-size: 11px; color: var(--text-secondary);">REST API & Dashboard UI</div>
          </div>
          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase;">TCP Lobby</div>
            <div style="font-size: 20px; font-weight: 700; color: var(--accent-cyan); margin: 4px 0;">PORT 8081</div>
            <div style="font-size: 11px; color: var(--text-secondary);">Proto Handshake & Sync</div>
          </div>
          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase;">UDP Combat</div>
            <div style="font-size: 20px; font-weight: 700; color: var(--accent-indigo); margin: 4px 0;">PORT 39800</div>
            <div style="font-size: 11px; color: var(--text-secondary);">Dedicated Match Server</div>
          </div>
          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase;">Active Context</div>
            <div style="font-size: 20px; font-weight: 700; color: var(--accent-amber); margin: 4px 0;" id="ov-account-label">
              ${window.playerContext.getSelectedAccountId()}
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">Selected Test Account</div>
          </div>
        </div>

        <div style="display: flex; gap: 12px;">
          <button class="btn btn-primary" onclick="window.location.hash='#/players/directory'">Open Player Directory</button>
          <button class="btn btn-secondary" onclick="window.location.hash='#/luck-royale/overview'">Luck Royale Studio</button>
          <button class="btn btn-secondary" onclick="window.location.hash='#/game/modes'">Game Modes</button>
        </div>
      `
    );
  });

  router.register('#/overview/monitoring', async (canvas) => {
    if (window.Modules && window.Modules.OverviewMonitoring) {
      return window.Modules.OverviewMonitoring(canvas);
    }
    canvas.innerHTML = window.UI.Loading('Fetching telemetry logs...');
    const res = await window.apiClient.get('/api/dashboard/requests', { limit: 50 });
    const rows = (res.data || []).map(r => `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">${r.time || '—'}</code></td>
        <td>${window.UI.Badge(r.method, r.method === 'GET' ? 'cyan' : 'emerald')}</td>
        <td style="font-family: var(--font-mono); font-size: 11.5px;">${r.path}</td>
        <td><code style="font-family: var(--font-mono); color: var(--text-tertiary);">${r.ip || '127.0.0.1'}</code></td>
      </tr>
    `).join('');

    canvas.innerHTML = window.UI.Card(
      'Server Request Telemetry',
      'Real-time traffic processed by HTTP handler',
      window.UI.Table(['Timestamp', 'Method', 'Request Path', 'Client IP'], rows, 'No request traffic recorded yet.'),
      `<button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/requests/clear').then(() => window.appRouter.handleRoute())">Clear Log</button>`
    );
  });

  // --- 02 PLAYER MANAGEMENT ---
  router.register('#/players/directory', async (canvas) => {
    if (window.Modules && window.Modules.PlayersDirectory) {
      return window.Modules.PlayersDirectory(canvas);
    }
    canvas.innerHTML = window.UI.Loading('Loading accounts...');
    // Check if backend admin endpoint is available, else fallback to current state accounts
    const res = await window.apiClient.get('/api/admin/players');
    if (res.ok && res.data && res.data.players) {
      const rows = res.data.players.map(p => `
        <tr>
          <td><code style="font-family: var(--font-mono); font-weight: 600; color: var(--accent-cyan);">${p.account_id}</code></td>
          <td style="font-weight: 500; color: #fff;">${p.nickname || 'Unknown'}</td>
          <td>${window.UI.Badge('Lv.' + (p.level || 1), 'neutral')}</td>
          <td><span style="color: var(--accent-amber);">💎 ${p.diamonds || 0}</span></td>
          <td><span style="color: #fbbf24;">🪙 ${p.gold || 0}</span></td>
          <td>${p.is_banned ? window.UI.Badge('BANNED', 'rose') : window.UI.Badge('ACTIVE', 'emerald')}</td>
          <td>
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.playerContext.setAccountId(${p.account_id}); window.location.hash='#/players/inspector';">Inspect</button>
          </td>
        </tr>
      `).join('');

      canvas.innerHTML = window.UI.Card(
        'Player Directory',
        `Registered accounts: ${res.data.total || res.data.players.length}`,
        window.UI.Table(['Account ID', 'Nickname', 'Level', 'Diamonds', 'Gold', 'Status', 'Action'], rows),
        `<button class="btn btn-primary" onclick="window.location.hash='#/players/account'">+ Create Account</button>`
      );
    } else {
      // Direct inspection fallback while backend API agent finishes /api/admin/players
      const curId = window.playerContext.getSelectedAccountId();
      const p = window.playerContext.getCurrentPlayer() || {};
      const rows = `
        <tr>
          <td><code style="font-family: var(--font-mono); font-weight: 600; color: var(--accent-cyan);">${curId}</code></td>
          <td style="font-weight: 500; color: #fff;">${p.nickname || 'PushpaGG'}</td>
          <td>${window.UI.Badge('Lv.' + (p.level || 1), 'neutral')}</td>
          <td><span style="color: var(--accent-amber);">💎 ${p.wallet ? p.wallet.diamonds : 0}</span></td>
          <td><span style="color: #fbbf24;">🪙 ${p.wallet ? p.wallet.gold : 0}</span></td>
          <td>${window.UI.Badge('ACTIVE', 'emerald')}</td>
          <td>
            <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.location.hash='#/players/inspector'">Inspect</button>
          </td>
        </tr>
      `;

      canvas.innerHTML = window.UI.Card(
        'Player Directory',
        'Database has 201 accounts. Enter any Account ID below to load:',
        `
          <div style="display: flex; gap: 8px; max-width: 400px; margin-bottom: 16px;">
            <input type="number" id="quick-aid-input" class="form-input" placeholder="Enter Account ID (e.g. 10001, 10002)" value="${curId}">
            <button class="btn btn-primary" onclick="window.playerContext.setAccountId(document.getElementById('quick-aid-input').value).then(() => window.appRouter.handleRoute())">Load</button>
          </div>
          ${window.UI.Table(['Account ID', 'Nickname', 'Level', 'Diamonds', 'Gold', 'Status', 'Action'], rows)}
        `
      );
    }
  });

  router.register('#/players/inspector', async (canvas) => {
    if (window.Modules && window.Modules.PlayersInspector) {
      return window.Modules.PlayersInspector(canvas);
    }
    const aid = window.playerContext.getSelectedAccountId();
    const p = window.playerContext.getCurrentPlayer() || {};
    canvas.innerHTML = window.UI.Card(
      `Player Dossier: ${p.nickname || 'Player'} (${aid})`,
      'Live synchronized state from core/player.py',
      `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="font-weight: 600; color: #fff; margin-bottom: 12px;">Profile Info</div>
            <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12px;">
              <div>Nickname: <b style="color: #fff;">${p.nickname || 'PushpaGG'}</b></div>
              <div>Level: <b style="color: #fff;">${p.level || 1}</b> (EXP: ${p.exp || 0})</div>
              <div>Rank Points: <b style="color: #fff;">${p.rank || 0}</b></div>
              <div>Signature: <i style="color: var(--text-tertiary);">${p.signature || 'None'}</i></div>
            </div>
          </div>
          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="font-weight: 600; color: #fff; margin-bottom: 12px;">Wallet Balances</div>
            <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12px;">
              <div>Diamonds: <b style="color: var(--accent-cyan);">${p.wallet ? p.wallet.diamonds : 0}</b></div>
              <div>Gold: <b style="color: #fbbf24;">${p.wallet ? p.wallet.gold : 0}</b></div>
            </div>
            <div style="margin-top: 16px;">
              <button class="btn btn-secondary" onclick="window.location.hash='#/economy/currencies'">Adjust Currencies</button>
            </div>
          </div>
        </div>
      `,
      `<button class="btn btn-secondary" onclick="window.location.hash='#/players/directory'">Back to Directory</button>`
    );
  });

  router.register('#/players/account', async (canvas) => {
    if (window.Modules && window.Modules.PlayersAccount) {
      return window.Modules.PlayersAccount(canvas);
    }
    canvas.innerHTML = window.UI.Card(
      'Account Manager',
      'Create or remove player accounts in india_v1.db',
      `
        <div style="max-width: 440px;">
          <div style="margin-bottom: 12px;">
            <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Player Nickname</label>
            <input type="text" id="new-acc-nick" class="form-input" placeholder="e.g. Commander_01">
          </div>
          <div style="display: flex; gap: 12px; margin-bottom: 16px;">
            <div style="flex: 1;">
              <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Initial Gold</label>
              <input type="number" id="new-acc-gold" class="form-input" value="10000">
            </div>
            <div style="flex: 1;">
              <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Initial Diamonds</label>
              <input type="number" id="new-acc-dia" class="form-input" value="500">
            </div>
          </div>
          <button class="btn btn-primary" onclick="
            const nick = document.getElementById('new-acc-nick').value.trim();
            if(!nick) return window.UI.Toast('Nickname required', 'warning');
            window.apiClient.post('/api/admin/players/create', {
              nickname: nick,
              gold: parseInt(document.getElementById('new-acc-gold').value, 10),
              diamonds: parseInt(document.getElementById('new-acc-dia').value, 10)
            }).then(r => {
              if(r.ok) {
                window.UI.Toast('Account created successfully', 'success');
                window.location.hash='#/players/directory';
              } else {
                window.UI.Toast(r.error || 'Requires backend route', 'error');
              }
            });
          ">Create Account</button>
        </div>
      `
    );
  });

  router.register('#/players/bans', async (canvas) => {
    if (window.Modules && window.Modules.PlayersBans) {
      return window.Modules.PlayersBans(canvas);
    }
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Card(
      'Sanction & Ban Manager',
      `Manage account suspension for Account ${aid}`,
      `
        <div style="max-width: 500px;">
          <p style="color: var(--text-secondary); margin-bottom: 16px;">
            Suspending an account terminates active lobby sockets and blocks authentication in <code>server/handlers/login_handler.py</code>.
          </p>
          <div style="display: flex; gap: 12px;">
            <button class="btn btn-danger" onclick="
              window.UI.Confirm('Confirm Ban', 'Are you sure you want to suspend Account ${aid}?', () => {
                window.apiClient.post('/api/admin/players/' + ${aid} + '/ban').then(r => {
                  window.UI.Toast(r.ok ? 'Account suspended' : (r.error || 'Requires backend route'), r.ok ? 'success' : 'error');
                });
              }, true);
            ">Suspend Account</button>
            <button class="btn btn-success" onclick="
              window.apiClient.post('/api/admin/players/' + ${aid} + '/unban').then(r => {
                window.UI.Toast(r.ok ? 'Account restored' : (r.error || 'Requires backend route'), r.ok ? 'success' : 'error');
              });
            ">Restore / Unban</button>
          </div>
        </div>
      `
    );
  });

  router.register('#/players/sessions', async (canvas) => {
    if (window.Modules && window.Modules.PlayersSessions) {
      return window.Modules.PlayersSessions(canvas);
    }
    canvas.innerHTML = window.UI.Card(
      'Live TCP/UDP Sessions',
      'Active player socket connections to TCP Lobby (8081)',
      window.UI.UnavailableState('Live Session Inspector', 'GET /api/admin/sessions', 'Pending bridge into tcp_server.py active client dictionary.')
    );
  });

  // --- 03 INVENTORY & COLLECTION ---
  router.register('#/inventory/manager', async (canvas) => {
    if (window.Modules && window.Modules.InventoryManager) {
      return window.Modules.InventoryManager(canvas);
    }
    const aid = window.playerContext.getSelectedAccountId();
    const p = window.playerContext.getCurrentPlayer() || {};
    const items = p.inventory || [];
    const rows = items.map(it => `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--accent-cyan); font-weight: 600;">${it.item_id || it}</code></td>
        <td>${it.name || 'Game Item'}</td>
        <td>${it.amount || 1}</td>
        <td>${it.equipped ? window.UI.Badge('EQUIPPED', 'emerald') : window.UI.Badge('IN VAULT', 'neutral')}</td>
      </tr>
    `).join('');

    canvas.innerHTML = window.UI.Card(
      `Inventory Vault (Account: ${aid})`,
      `Total items owned: ${items.length}`,
      `
        <div style="display: flex; gap: 8px; margin-bottom: 16px; max-width: 480px;">
          <input type="number" id="grant-item-id" class="form-input" placeholder="Item ID (e.g. 20000001)">
          <input type="number" id="grant-item-amt" class="form-input" placeholder="Qty" value="1" style="max-width: 80px;">
          <button class="btn btn-primary" onclick="
            const iid = parseInt(document.getElementById('grant-item-id').value, 10);
            const amt = parseInt(document.getElementById('grant-item-amt').value, 10) || 1;
            if(!iid) return window.UI.Toast('Item ID required', 'warning');
            window.apiClient.post('/api/dashboard/items/grant', { account_id: ${aid}, item_ids: [iid], amount: amt }).then(r => {
              if(r.ok) {
                window.UI.Toast('Item granted', 'success');
                window.playerContext.refresh().then(() => window.appRouter.handleRoute());
              } else {
                window.UI.Toast(r.error || 'Grant failed', 'error');
              }
            });
          ">Grant Item</button>
        </div>
        ${window.UI.Table(['Item ID', 'Item Name', 'Quantity', 'Status'], rows, 'Vault is empty for this account.')}
      `
    );
  });

  router.register('#/inventory/characters', async (canvas) => {
    if (window.Modules && window.Modules.CharacterManager) {
      return window.Modules.CharacterManager(canvas);
    }
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Card(
      `Character Manager (Account: ${aid})`,
      'Select active character and skill loadout',
      `
        <div style="display: flex; gap: 12px; margin-bottom: 16px;">
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/character/select', { account_id: ${aid}, character_id: 1 }).then(r => window.UI.Toast('Selected Adam', 'success'))">Adam (ID: 1)</button>
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/character/select', { account_id: ${aid}, character_id: 2 }).then(r => window.UI.Toast('Selected Eve', 'success'))">Eve (ID: 2)</button>
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/character/select', { account_id: ${aid}, character_id: 10 }).then(r => window.UI.Toast('Selected Alok', 'success'))">Alok (ID: 10)</button>
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/character/select', { account_id: ${aid}, character_id: 8 }).then(r => window.UI.Toast('Selected Hayato', 'success'))">Hayato (ID: 8)</button>
        </div>
      `
    );
  });

  router.register('#/inventory/pets', async (canvas) => {
    if (window.Modules && window.Modules.PetManager) {
      return window.Modules.PetManager(canvas);
    }
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Card(
      `Pet Manager (Account: ${aid})`,
      'Active companion companion selection',
      `
        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/pet/select', { account_id: ${aid}, pet_id: 1 }).then(r => window.UI.Toast('Selected Mechanical Puppy', 'success'))">Mechanical Puppy (1)</button>
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/pet/select', { account_id: ${aid}, pet_id: 2 }).then(r => window.UI.Toast('Selected Kitty', 'success'))">Kitty (2)</button>
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/pet/select', { account_id: ${aid}, pet_id: 3 }).then(r => window.UI.Toast('Selected Shiba', 'success'))">Shiba (3)</button>
        </div>
      `
    );
  });

  router.register('#/inventory/wardrobe', async (canvas) => {
    if (window.Modules && window.Modules.WardrobeManager) {
      return window.Modules.WardrobeManager(canvas);
    }
    canvas.innerHTML = window.UI.Card(
      'Cosmetics & Wardrobe',
      'Equip cosmetic clothing slots onto active character',
      '<p style="color: var(--text-secondary);">Manage head, mask, top, pants, and shoe equipment in the Vault workspace.</p>'
    );
  });

  // --- 04 ECONOMY ---
  router.register('#/economy/currencies', async (canvas) => {
    if (window.Modules && window.Modules.CurrencyManager) {
      return window.Modules.CurrencyManager(canvas);
    }
    const aid = window.playerContext.getSelectedAccountId();
    const p = window.playerContext.getCurrentPlayer() || {};
    canvas.innerHTML = window.UI.Card(
      `Currency Manager (Account: ${aid})`,
      'Grant or set Gold & Diamonds in india_v1.db',
      `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="font-weight: 600; color: #fff; margin-bottom: 12px;">Grant Currency (Increment)</div>
            <div style="margin-bottom: 8px;">
              <label style="font-size: 11px; color: var(--text-tertiary);">Add Gold</label>
              <input type="number" id="grant-gold" class="form-input" value="10000">
            </div>
            <div style="margin-bottom: 12px;">
              <label style="font-size: 11px; color: var(--text-tertiary);">Add Diamonds</label>
              <input type="number" id="grant-dia" class="form-input" value="1000">
            </div>
            <button class="btn btn-primary" onclick="
              const g = parseInt(document.getElementById('grant-gold').value, 10) || 0;
              const d = parseInt(document.getElementById('grant-dia').value, 10) || 0;
              window.apiClient.post('/api/dashboard/wallet/grant', { account_id: ${aid}, gold: g, diamonds: d }).then(r => {
                if(r.ok) {
                  window.UI.Toast('Currency granted', 'success');
                  window.playerContext.refresh().then(() => window.appRouter.handleRoute());
                }
              });
            ">Grant Funds</button>
          </div>

          <div style="background: rgba(10, 16, 28, 0.4); padding: 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="font-weight: 600; color: #fff; margin-bottom: 12px;">Set Absolute Balance</div>
            <div style="margin-bottom: 8px;">
              <label style="font-size: 11px; color: var(--text-tertiary);">Exact Gold Balance</label>
              <input type="number" id="set-gold" class="form-input" value="${p.wallet ? p.wallet.gold : 50000}">
            </div>
            <div style="margin-bottom: 12px;">
              <label style="font-size: 11px; color: var(--text-tertiary);">Exact Diamond Balance</label>
              <input type="number" id="set-dia" class="form-input" value="${p.wallet ? p.wallet.diamonds : 5000}">
            </div>
            <button class="btn btn-secondary" onclick="
              const g = parseInt(document.getElementById('set-gold').value, 10) || 0;
              const d = parseInt(document.getElementById('set-dia').value, 10) || 0;
              window.apiClient.post('/api/dashboard/wallet/set', { account_id: ${aid}, gold: g, diamonds: d }).then(r => {
                if(r.ok) {
                  window.UI.Toast('Balance updated', 'success');
                  window.playerContext.refresh().then(() => window.appRouter.handleRoute());
                }
              });
            ">Update Balance</button>
          </div>
        </div>
      `
    );
  });

  router.register('#/economy/wallet', async (canvas) => {
    if (window.Modules && window.Modules.WalletInspector) {
      return window.Modules.WalletInspector(canvas);
    }
    window.location.hash = '#/economy/currencies';
  });

  // --- 05 LUCK ROYALE STUDIO ---
  router.register('#/luck-royale/overview', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Overview) return window.LuckRoyale.Overview(canvas);
  });

  router.register('#/luck-royale/machines', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Machines) return window.LuckRoyale.Machines(canvas);
  });

  router.register('#/luck-royale/pools', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Pools) return window.LuckRoyale.Pools(canvas);
  });

  router.register('#/luck-royale/pity', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Pity) return window.LuckRoyale.Pity(canvas);
  });

  router.register('#/luck-royale/currencies', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Currencies) return window.LuckRoyale.Currencies(canvas);
  });

  router.register('#/luck-royale/forge', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Forge) return window.LuckRoyale.Forge(canvas);
  });

  router.register('#/luck-royale/events', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Events) return window.LuckRoyale.Events(canvas);
  });

  router.register('#/luck-royale/banners', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Banners) return window.LuckRoyale.Banners(canvas);
  });

  router.register('#/luck-royale/player', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Player) return window.LuckRoyale.Player(canvas);
  });

  router.register('#/luck-royale/transactions', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Transactions) return window.LuckRoyale.Transactions(canvas);
  });

  router.register('#/luck-royale/simulator', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Simulator) return window.LuckRoyale.Simulator(canvas);
  });

  router.register('#/luck-royale/config', async (canvas) => {
    if (window.LuckRoyale && window.LuckRoyale.Config) return window.LuckRoyale.Config(canvas);
  });

  // --- 06 GAME MANAGEMENT ---
  router.register('#/game/modes', async (canvas) => {
    canvas.innerHTML = window.UI.Loading('Loading game modes...');
    const res = await window.apiClient.get('/api/dashboard/modes');
    const modes = (res.data && res.data.modes) || {};
    const rows = Object.entries(modes).map(([k, v]) => `
      <tr>
        <td style="font-weight: 600; color: #fff;">${k.toUpperCase()}</td>
        <td>${v.enabled ? window.UI.Badge('ENABLED', 'emerald') : window.UI.Badge('LOCKED', 'rose')}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="
            window.apiClient.post('/api/dashboard/modes/update', { mode_id: '${k}', enabled: ${!v.enabled} }).then(() => window.appRouter.handleRoute());
          ">${v.enabled ? 'Disable' : 'Enable'}</button>
        </td>
      </tr>
    `).join('');

    canvas.innerHTML = window.UI.Card(
      'Game Mode Availability',
      'Real-time toggle in server/data/game_modes.json',
      window.UI.Table(['Mode', 'Status', 'Action'], rows),
      `
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-primary" onclick="window.apiClient.post('/api/dashboard/modes/unlock-all').then(() => window.appRouter.handleRoute())">Unlock All Modes</button>
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/modes/lock-optional').then(() => window.appRouter.handleRoute())">Lock Optional</button>
        </div>
      `
    );
  });

  router.register('#/game/maps', async (canvas) => {
    canvas.innerHTML = window.UI.Card(
      'Map Rotation',
      'Toggle Bermuda, Purgatory, and Kalahari availability',
      '<p style="color: var(--text-secondary);">Currently serving Bermuda classic map on UDP port 39800.</p>'
    );
  });

  router.register('#/game/matchmaking', async (canvas) => {
    canvas.innerHTML = window.UI.Card(
      'Matchmaking Queue',
      'Real-time ticket pool and matchmaking worker stats',
      window.UI.UnavailableState('Matchmaking Queue Monitor', 'GET /api/admin/matchmaking', 'Requires backend telemetry bridge into tcp_server.py matchmaking queue.')
    );
  });

  router.register('#/game/rooms', async (canvas) => {
    canvas.innerHTML = window.UI.Card(
      'Custom Rooms',
      'Active custom game instances and room password controls',
      window.UI.UnavailableState('Custom Room Manager', 'GET /api/admin/rooms', 'Requires custom room backend management service.')
    );
  });

  // --- 07 SOCIAL & COMMUNICATION ---
  router.register('#/social/mail', async (canvas) => {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Loading('Loading mail...');
    const res = await window.apiClient.get('/api/dashboard/mail', { account_id: aid });
    const mails = (res.data && res.data.mails) || [];
    const rows = mails.map(m => `
      <tr>
        <td style="font-weight: 600; color: #fff;">${m.title}</td>
        <td>${m.content}</td>
        <td>
          <button class="btn btn-primary" style="padding: 3px 8px; font-size: 11px;" onclick="window.apiClient.post('/api/dashboard/mail/claim', { account_id: ${aid}, mail_id: ${m.id} }).then(() => window.appRouter.handleRoute())">Claim</button>
          <button class="btn btn-danger" style="padding: 3px 8px; font-size: 11px;" onclick="window.apiClient.post('/api/dashboard/mail/delete', { account_id: ${aid}, mail_id: ${m.id} }).then(() => window.appRouter.handleRoute())">Delete</button>
        </td>
      </tr>
    `).join('');

    canvas.innerHTML = window.UI.Card(
      `Mailbox (Account: ${aid})`,
      `Total inbox messages: ${mails.length}`,
      window.UI.Table(['Title', 'Content', 'Actions'], rows, 'No mail messages in inbox.'),
      `<button class="btn btn-primary" onclick="window.location.hash='#/social/mail-compose'">+ Send New Mail</button>`
    );
  });

  router.register('#/social/mail-compose', async (canvas) => {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Card(
      'Compose System Mail',
      `Deliver mail with gold/diamond attachments to Account ${aid}`,
      `
        <div style="max-width: 500px;">
          <div style="margin-bottom: 8px;">
            <label style="font-size: 11px; color: var(--text-tertiary);">Mail Title</label>
            <input type="text" id="mail-title" class="form-input" placeholder="e.g. Compensation Reward">
          </div>
          <div style="margin-bottom: 8px;">
            <label style="font-size: 11px; color: var(--text-tertiary);">Message Content</label>
            <textarea id="mail-content" class="form-input" style="height: 80px;" placeholder="Message to player..."></textarea>
          </div>
          <div style="display: flex; gap: 12px; margin-bottom: 16px;">
            <div style="flex: 1;">
              <label style="font-size: 11px; color: var(--text-tertiary);">Attached Diamonds</label>
              <input type="number" id="mail-dia" class="form-input" value="100">
            </div>
            <div style="flex: 1;">
              <label style="font-size: 11px; color: var(--text-tertiary);">Attached Gold</label>
              <input type="number" id="mail-gold" class="form-input" value="5000">
            </div>
          </div>
          <button class="btn btn-primary" onclick="
            window.apiClient.post('/api/dashboard/mail/send', {
              account_id: ${aid},
              title: document.getElementById('mail-title').value,
              content: document.getElementById('mail-content').value,
              diamonds: parseInt(document.getElementById('mail-dia').value, 10),
              gold: parseInt(document.getElementById('mail-gold').value, 10)
            }).then(r => {
              if(r.ok) {
                window.UI.Toast('Mail sent successfully', 'success');
                window.location.hash='#/social/mail';
              }
            });
          ">Dispatch Mail</button>
        </div>
      `,
      `<button class="btn btn-secondary" onclick="window.location.hash='#/social/mail'">Cancel</button>`
    );
  });

  router.register('#/social/friends', async (canvas) => {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Card(
      `Friends & Social (Account: ${aid})`,
      'Friend relationships persisted in friends table',
      '<p style="color: var(--text-secondary);">Manage friend connections and accept/reject pending friend requests.</p>'
    );
  });

  router.register('#/social/squads', async (canvas) => {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Card(
      `Squad Lobby (Account: ${aid})`,
      'Active team pre-match lobby status',
      '<p style="color: var(--text-secondary);">Controls squad lobby creation, invites, ready states, and kicks.</p>'
    );
  });

  // --- 08 CONTENT MANAGEMENT ---
  router.register('#/cms/banners', async (canvas) => {
    canvas.innerHTML = window.UI.Loading('Loading banners...');
    const res = await window.apiClient.get('/api/dashboard/cms/banners');
    const banners = (res.data && res.data.banners) || [];
    const rows = banners.map(b => `
      <tr>
        <td><code style="font-family: var(--font-mono); color: var(--accent-cyan);">${b.id}</code></td>
        <td style="font-weight: 500; color: #fff;">${b.filename}</td>
        <td>${b.active ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('INACTIVE', 'neutral')}</td>
        <td>
          <button class="btn btn-danger" style="padding: 3px 8px; font-size: 11px;" onclick="window.apiClient.post('/api/dashboard/cms/banner/delete', { banner_id: '${b.id}' }).then(() => window.appRouter.handleRoute())">Delete</button>
        </td>
      </tr>
    `).join('');

    canvas.innerHTML = window.UI.Card(
      'Billboard Banners',
      'In-game billboard textures in server/static/banners/',
      window.UI.Table(['ID', 'Filename', 'Status', 'Action'], rows, 'No billboard banners registered.'),
      `
        <div style="display: flex; gap: 8px;">
          <input type="file" id="banner-file" style="display: none;" onchange="
            const file = this.files[0];
            if(file) {
              const fd = new FormData();
              fd.append('file', file);
              window.apiClient.upload('/api/dashboard/cms/banner/upload', fd).then(() => window.appRouter.handleRoute());
            }
          ">
          <button class="btn btn-primary" onclick="document.getElementById('banner-file').click()">+ Upload Banner Image</button>
        </div>
      `
    );
  });

  router.register('#/cms/lobby', async (canvas) => {
    canvas.innerHTML = window.UI.Card(
      'Lobby CMS & Splash Screens',
      'Manage promotional modal popups and startup splash screen',
      `
        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/cms/splash/toggle', { active: true }).then(() => window.UI.Toast('Splash screen enabled', 'success'))">Enable Startup Splash</button>
          <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/cms/splash/toggle', { active: false }).then(() => window.UI.Toast('Splash screen disabled', 'info'))">Disable Startup Splash</button>
        </div>
      `
    );
  });

  router.register('#/cms/announcements', async (canvas) => {
    canvas.innerHTML = window.UI.Card(
      'In-Game Announcements & Marquee Ticker',
      'Live server announcements pushed to client Announcement.csv',
      `
        <div style="max-width: 480px;">
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Scrolling Marquee Text</label>
          <input type="text" id="marquee-text" class="form-input" placeholder="e.g. Welcome to FF 2019 Restoration!" style="margin-bottom: 12px;">
          <button class="btn btn-primary" onclick="
            window.apiClient.post('/api/dashboard/cms/marquee/update', { text: document.getElementById('marquee-text').value }).then(r => {
              if(r.ok) window.UI.Toast('Marquee updated', 'success');
            });
          ">Update Marquee</button>
        </div>
      `
    );
  });

  // --- 09 LOGS & MONITORING ---
  router.register('#/logs/api', async (canvas) => {
    window.location.hash = '#/overview/monitoring';
  });

  router.register('#/logs/audit', async (canvas) => {
    canvas.innerHTML = window.UI.Card(
      'Administrative Audit Log',
      'Audit log of server mutations persisted in audit_log table',
      '<p style="color: var(--text-secondary);">Logs all administrative mutations, currency adjustments, and gacha configuration changes.</p>'
    );
  });

  // --- 10 SYSTEM ADMINISTRATION ---
  router.register('#/system/settings', async (canvas) => {
    canvas.innerHTML = window.UI.Loading('Loading settings...');
    const res = await window.apiClient.get('/api/dashboard/branding');
    const slots = (res.data && res.data.slots) || {};
    canvas.innerHTML = window.UI.Card(
      'Server Brand & Maintenance Settings',
      'Display names and client connection banners',
      `
        <div style="max-width: 440px;">
          <div style="margin-bottom: 8px;">
            <label style="font-size: 11px; color: var(--text-tertiary);">Brand Name</label>
            <input type="text" id="brand-name" class="form-input" value="${slots.brand_name || 'India V1'}">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="font-size: 11px; color: var(--text-tertiary);">Server Subtitle / MOTD</label>
            <input type="text" id="brand-sub" class="form-input" value="${slots.brand_subtitle || 'FF 2019 Restoration'}">
          </div>
          <button class="btn btn-primary" onclick="
            window.apiClient.post('/api/dashboard/branding/update', {
              key: 'brand_name',
              value: document.getElementById('brand-name').value
            }).then(() => window.UI.Toast('Brand settings updated', 'success'));
          ">Save Settings</button>
        </div>
      `
    );
  });

  router.register('#/system/database', async (canvas) => {
    canvas.innerHTML = window.UI.Card(
      'Database Status',
      'Active database file: server/data/india_v1.db (SQLite3)',
      `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
          <div style="background: rgba(10, 16, 28, 0.4); padding: 12px; border-radius: 6px; border: 1px solid var(--border-default);">
            <div style="font-size: 11px; color: var(--text-tertiary);">Accounts Table</div>
            <div style="font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px;">201 Rows</div>
          </div>
          <div style="background: rgba(10, 16, 28, 0.4); padding: 12px; border-radius: 6px; border: 1px solid var(--border-default);">
            <div style="font-size: 11px; color: var(--text-tertiary);">Inventory Table</div>
            <div style="font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px;">11,971 Rows</div>
          </div>
          <div style="background: rgba(10, 16, 28, 0.4); padding: 12px; border-radius: 6px; border: 1px solid var(--border-default);">
            <div style="font-size: 11px; color: var(--text-tertiary);">Gacha Tables</div>
            <div style="font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px;">3 Tables Active</div>
          </div>
        </div>
      `
    );
  });

  router.register('#/system/security', async (canvas) => {
    const curToken = window.apiClient.getToken();
    canvas.innerHTML = window.UI.Card(
      'Security & Authentication Status',
      'Control Center API protection',
      `
        <div style="max-width: 480px;">
          <p style="color: var(--text-secondary); margin-bottom: 12px;">
            Current Admin Token: <code>${curToken ? '••••••••' : 'None (Permissive Mode)'}</code>
          </p>
          <button class="btn btn-primary" onclick="window.Topbar.openAuthModal()">Configure Token</button>
        </div>
      `
    );
  });

  // Restore original register method so subsequent dynamic registers work normally
  router.register = originalRegister;

  // 4. Fetch initial player state & kick off router
  await window.playerContext.refresh();
  router.start();
});
