/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Map Rotation & Territory Management (#/game/maps)
 * Domain: 06 Game Management
 * Phase 2 Refinement: Standardized Dark Glass Surface Tokens & Design System Components
 */

(function () {
  'use strict';

  const state = {
    modes: [],
    loading: false,
    error: null,
    selectedMap: null
  };

  const MAP_METADATA = {
    1: {
      name: 'Bermuda',
      sub: 'Island of Origin — Flagship 8x8 km Territory',
      status: 'ONLINE / CORE',
      statusVariant: 'emerald',
      environment: 'Tropical Island, Coastal Shoals, Industrial Complexes, Open Meadows',
      pointsOfInterest: [
        'Clock Tower', 'Peak', 'Factory', 'Pochinok', 'Bimasakti Strip',
        'Katulistiwa', 'Shipyard', 'Mars Electric', 'Cape Town', 'Kota Tua',
        'Mill', 'Riverside', 'Plantation', 'Rim Nam Village', 'Graveyard'
      ],
      defaultGateway: 'IND-Local-01 (127.0.0.1:39800)',
      supportedTypes: ['Battle Royale Casual', 'Ranked Bermuda', 'Rush Hour', 'Clash Squad', 'Big Head'],
      description: 'The definitive battleground of Free Fire 2019. Bermuda serves as the primary combat grid with high tactical density, multi-level building compounds, and balanced hot-drop zones.'
    },
    2: {
      name: 'Purgatory',
      sub: 'Isla del Purgatorio — Mountain Archipelago & Valleys',
      status: 'ONLINE / ROTATION',
      statusVariant: 'cyan',
      environment: 'River Gorges, High-Altitude Zipline Networks, Elevated Mountain Plateaus',
      pointsOfInterest: [
        'Brasilia', 'Central', 'Moathouse', 'Forge', 'Campsite',
        'Ski Lodge', 'Quarry', 'Golf Course', 'Mt. Villa', 'Crossroads',
        'Fields', 'Fire Brigade', 'Marbleworks', 'Lumber Mill'
      ],
      defaultGateway: 'IND-Local-01 (127.0.0.1:39800)',
      supportedTypes: ['Battle Royale Casual', 'Ranked Purgatory', 'Rush Hour'],
      description: 'Rugged topography split by a central water channel. Features intense long-range rifle skirmishes across mountainous ridges and dynamic bridge choke points.'
    },
    3: {
      name: 'Death Uprising',
      sub: 'PVE Quarantine Outpost & Arid Badlands',
      status: 'ONLINE / SPECIAL EVENT',
      statusVariant: 'amber',
      environment: 'Contaminated Laboratory Complex, Barren Wasteland, Subterranean Bunkers',
      pointsOfInterest: [
        'Research Facility', 'Outpost Delta', 'Reactor Core', 'Helipad Evacuation Area'
      ],
      defaultGateway: 'IND-Local-01 (127.0.0.1:39800)',
      supportedTypes: ['Death Uprising (PVE Hyakki)', 'Zombie Survival'],
      description: 'Cooperative survival arena where squads confront progressive zombie horde waves and elite boss encounters with custom weapon upgrade drop mechanics.'
    }
  };

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function fetchModes() {
    state.loading = true;
    state.error = null;
    try {
      const res = await window.apiClient.get('/api/dashboard/modes');
      if (res.ok && res.data) {
        const rawModes = res.data.modes;
        if (Array.isArray(rawModes)) {
          state.modes = rawModes;
        } else if (rawModes && typeof rawModes === 'object') {
          state.modes = Object.values(rawModes);
        } else {
          state.modes = [];
        }
      } else {
        state.error = res.error || 'Failed to retrieve mode registry.';
      }
    } catch (err) {
      state.error = err.message || 'Network unreachable';
    } finally {
      state.loading = false;
    }
  }

  async function setMapModesStatus(mapId, enable) {
    const targetMapModes = state.modes.filter(m => m.map_id === parseInt(mapId, 10));
    if (targetMapModes.length === 0) return;

    window.UI.Confirm(
      `${enable ? 'Enable' : 'Disable'} All ${MAP_METADATA[mapId]?.name || `Map ${mapId}`} Modes`,
      `This will batch ${enable ? 'unlock' : 'lock'} all ${targetMapModes.length} modes assigned to this territory. Continue?`,
      async () => {
        let successCount = 0;
        for (const mode of targetMapModes) {
          try {
            const res = await window.apiClient.post('/api/dashboard/modes/toggle', {
              map_id: mode.map_id,
              game_mode: mode.game_mode,
              match_mode: mode.match_mode,
              enable: enable
            });
            if (res.ok) successCount++;
          } catch (e) {}
        }
        window.UI.Toast(`Updated ${successCount}/${targetMapModes.length} modes for ${MAP_METADATA[mapId]?.name}`, 'success');
        await fetchModes();
        renderContent(activeCanvas);
      }
    );
  }

  let activeCanvas = null;

  function renderContent(canvas) {
    canvas = canvas || activeCanvas || document.getElementById('workspace-canvas');
    if (!canvas) return;
    activeCanvas = canvas;

    if (state.loading && state.modes.length === 0) {
      canvas.innerHTML = window.UI.Loading('Loading territory & map telemetry...');
      return;
    }

    // Top Summary Banner with UI.StatCard
    const totalMaps = Object.keys(MAP_METADATA).length;
    const totalModes = state.modes.length;
    const activeModes = state.modes.filter(m => m.enable).length;

    const summaryHtml = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px;">
        ${window.UI.StatCard('Active Territories', `${totalMaps} Maps`, 'Bermuda • Purgatory • Uprising', '🗺️', 'cyan')}
        ${window.UI.StatCard('Mode Allocation', `${activeModes} / ${totalModes}`, 'Active / Total Registered', '●', 'emerald')}
        ${window.UI.StatCard('Combat Gateway', 'IND-Local-01', 'UDP Port :39800 Gateway', '📡', 'indigo')}
      </div>
    `;

    // Territory Cards Grid
    const territoryCardsHtml = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px; margin-bottom: 28px;">
        ${[1, 2, 3].map(mapId => renderTerritoryCard(mapId)).join('')}
      </div>
    `;

    // Gateway Nodes Card
    const gatewayNodesHtml = renderGatewayNodesCard();

    // Map Rotation Schedule Matrix
    const rotationScheduleHtml = renderScheduleMatrix();

    canvas.innerHTML = `
      <div style="max-width: 1400px; margin: 0 auto;">
        ${window.UI.Card(
          'Map Rotation & Territory Control',
          'Free Fire 2019 Combat Territories, Server Node Routing & Rotation Matrix',
          summaryHtml + territoryCardsHtml + rotationScheduleHtml + gatewayNodesHtml,
          `<button class="btn btn-secondary" onclick="window.GameMaps.refresh()">🔄 Refresh Telemetry</button>`
        )}
      </div>
    `;
  }

  function renderTerritoryCard(mapId) {
    const meta = MAP_METADATA[mapId];
    if (!meta) return '';

    const mapModes = state.modes.filter(m => m.map_id === mapId);
    const activeCount = mapModes.filter(m => m.enable).length;

    return `
      <div class="glass-card" style="margin-bottom: 0; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden;">
        <!-- Card Top -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
              <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">
                ${escapeHtml(meta.name)}
              </div>
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">
                ${escapeHtml(meta.sub)}
              </div>
            </div>
            ${window.UI.Badge(meta.status, meta.statusVariant)}
          </div>

          <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 14px;">
            ${escapeHtml(meta.description)}
          </p>

          <!-- Modes Count & Status -->
          <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 10px 12px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600;">Active Modes</span>
              <span style="font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: ${activeCount > 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">
                ${activeCount} / ${mapModes.length} Unlocked
              </span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
              ${mapModes.map(m => `
                <span class="badge ${m.enable ? 'badge-emerald' : 'badge-neutral'}" style="font-size: 9.5px;" title="${m.enable ? 'Active in rotation' : 'Locked'}">
                  ${m.enable ? '●' : '○'} ${escapeHtml(m.mode_title || m.name)}
                </span>
              `).join('')}
            </div>
          </div>

          <!-- Points of Interest -->
          <div style="margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary); margin-bottom: 6px;">
              Key Drop Zones &amp; Sectors
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
              ${meta.pointsOfInterest.map(poi => `
                <span style="font-size: 10.5px; background: rgba(255,255,255,0.05); color: var(--text-secondary); padding: 2px 7px; border-radius: 4px; border: 1px solid var(--border-subtle);">
                  ${escapeHtml(poi)}
                </span>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- Card Actions -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 12px; margin-top: 12px;">
          <div style="display: flex; gap: 6px;">
            <button
              class="btn btn-secondary"
              style="padding: 4px 10px; font-size: 11px;"
              onclick="window.GameMaps.setMapStatus(${mapId}, true)"
              title="Enable all modes on this map"
            >
              Unlock All
            </button>
            <button
              class="btn btn-secondary"
              style="padding: 4px 10px; font-size: 11px;"
              onclick="window.GameMaps.setMapStatus(${mapId}, false)"
              title="Lock all modes on this map"
            >
              Lock All
            </button>
          </div>
          <button
            class="btn btn-secondary"
            style="padding: 4px 10px; font-size: 11px;"
            onclick="window.GameMaps.jumpToFilter('${mapId}')"
            title="Inspect in Game Modes workspace"
          >
            Modes Workspace ↗
          </button>
        </div>
      </div>
    `;
  }

  function renderGatewayNodesCard() {
    const columns = ['Cluster Region', 'Node Name', 'Server Gateway Address', 'Protocol', 'Role', 'Capacity Alert', 'Status'];
    const rowsHtml = `
      <tr>
        <td>${window.UI.Badge('IND', 'cyan')} India Central</td>
        <td style="font-weight: 600; color: var(--text-primary);">IND-Local-01</td>
        <td style="font-family: var(--font-mono); font-size: 11.5px;">127.0.0.1:39800</td>
        <td><span style="font-family: var(--font-mono); font-size: 11px;">UDP / ENet</span></td>
        <td>${window.UI.Badge('PRIMARY DEFAULT', 'emerald')}</td>
        <td style="font-family: var(--font-mono);">1,000 CCU</td>
        <td>${window.UI.Badge('ONLINE', 'emerald')}</td>
      </tr>
      <tr>
        <td>${window.UI.Badge('SG', 'neutral')} Singapore Relay</td>
        <td style="font-weight: 600; color: var(--text-primary);">SG-Node-01</td>
        <td style="font-family: var(--font-mono); font-size: 11.5px;">127.0.0.1:39800</td>
        <td><span style="font-family: var(--font-mono); font-size: 11px;">UDP / ENet</span></td>
        <td>${window.UI.Badge('STANDBY RECOVERY', 'neutral')}</td>
        <td style="font-family: var(--font-mono);">1,000 CCU</td>
        <td>${window.UI.Badge('STANDBY', 'amber')}</td>
      </tr>
    `;

    return `
      <div style="margin-top: 24px;">
        <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">Combat Cluster Gateway Nodes</div>
        <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 12px;">Allocated server sockets registered for real-time match routing.</div>
        ${window.UI.Table(columns, rowsHtml)}
      </div>
    `;
  }

  function renderScheduleMatrix() {
    const columns = ['Map Territory', 'Game Mode Title', 'Daily Window', 'Weekday Mask', 'Squad Size', 'Level Gate', 'Status'];
    const rowsHtml = state.modes.map(mode => {
      const mapName = MAP_METADATA[mode.map_id]?.name || `Map ${mode.map_id}`;
      const isEnabled = Boolean(mode.enable);

      return `
        <tr>
          <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(mapName)}</td>
          <td>
            <div style="font-weight: 500; color: var(--text-primary);">${escapeHtml(mode.mode_title || mode.name)}</div>
            <div style="font-size: 10px; color: var(--text-tertiary); font-family: var(--font-mono);">Key: ${mode.key || `${mode.map_id}_${mode.game_mode}_${mode.match_mode}`}</div>
          </td>
          <td style="font-family: var(--font-mono); font-size: 11px;">
            ${escapeHtml(mode.start_time || '00:00:00')} - ${escapeHtml(mode.end_time || '23:59:59')}
          </td>
          <td style="font-family: var(--font-mono); font-size: 11px;">
            ${mode.weekday === '0' || !mode.weekday ? 'All Days (Daily)' : `Mask: ${escapeHtml(mode.weekday)}`}
          </td>
          <td style="font-family: var(--font-mono); font-size: 11px;">
            ${escapeHtml(mode.player_count_limit || '1;2;4')}
          </td>
          <td style="font-family: var(--font-mono); font-size: 11px;">
            ${mode.limited_rank > 0 ? 'Lv. ' + mode.limited_rank : 'None'}
          </td>
          <td>
            ${isEnabled ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('CLOSED', 'rose')}
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div style="margin-top: 24px;">
        <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">Authentic Match Rotation Matrix</div>
        <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 12px;">Active operating schedule and access rules synchronised with native client descriptors.</div>
        ${window.UI.Table(columns, rowsHtml, 'No modes registered')}
      </div>
    `;
  }

  // Public Interface
  const GameMaps = {
    async render(container) {
      if (container) activeCanvas = container;
      if (state.modes.length === 0) {
        await fetchModes();
      }
      renderContent(activeCanvas);
    },

    async refresh() {
      await fetchModes();
      window.UI.Toast('Map telemetry refreshed', 'info');
      renderContent(activeCanvas);
    },

    setMapStatus: setMapModesStatus,

    jumpToFilter(mapId) {
      if (window.GameModes) {
        window.GameModes.setMapFilter(String(mapId));
      }
      window.location.hash = '#/game/modes';
    }
  };

  window.GameMaps = GameMaps;

  // Export to window.Modules for coordinator / app.js integration
  window.Modules = window.Modules || {};
  window.Modules.GameMaps = (canvas) => GameMaps.render(canvas);

  // Register with router
  function registerRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/game/maps', (canvas) => GameMaps.render(canvas));
    }
  }

  registerRoute();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(registerRoute, 0));
  } else {
    setTimeout(registerRoute, 0);
  }
})();
