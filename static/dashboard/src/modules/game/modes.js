/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Game Modes Management (#/game/modes)
 * Domain: 06 Game Management
 * Phase 2 Refinement: Standardized Dark Glass Surface Tokens & Design System Components
 */

(function () {
  'use strict';

  // Module state
  const state = {
    modes: [],
    loading: false,
    error: null,
    searchQuery: '',
    mapFilter: 'all',        // 'all', '1', '2', '3'
    matchModeFilter: 'all',  // 'all', '1' (casual), '2' (ranked)
    statusFilter: 'all',     // 'all', 'active', 'locked'
    viewMode: 'grid',        // 'grid' | 'table'
    lastSync: null
  };

  const MAP_NAMES = {
    1: 'Bermuda',
    2: 'Purgatory',
    3: 'Death Uprising'
  };

  const GAME_MODE_NAMES = {
    1: 'Battle Royale',
    2: 'Rush Hour',
    15: 'Clash Squad',
    16: 'Big Head',
    17: 'Death Uprising (PVE)',
    18: 'Zombie Survival'
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

  function getModeKey(m) {
    return m.key || `${m.map_id}_${m.game_mode}_${m.match_mode}`;
  }

  // --- API Actions ---

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
        state.lastSync = new Date();
      } else {
        state.error = res.error || 'Failed to retrieve game modes registry.';
      }
    } catch (err) {
      state.error = err.message || 'Network unreachable';
    } finally {
      state.loading = false;
    }
  }

  async function toggleMode(mapId, gameMode, matchMode, enable) {
    try {
      const res = await window.apiClient.post('/api/dashboard/modes/toggle', {
        map_id: parseInt(mapId, 10),
        game_mode: parseInt(gameMode, 10),
        match_mode: parseInt(matchMode, 10),
        enable: Boolean(enable)
      });

      if (res.ok) {
        if (Array.isArray(res.data?.modes)) {
          state.modes = res.data.modes;
        } else {
          const item = state.modes.find(m =>
            m.map_id === parseInt(mapId, 10) &&
            m.game_mode === parseInt(gameMode, 10) &&
            m.match_mode === parseInt(matchMode, 10)
          );
          if (item) item.enable = enable;
        }
        window.UI.Toast(`Mode ${enable ? 'unlocked' : 'locked'} successfully`, 'success');
        renderContent(activeCanvas);
      } else {
        window.UI.Toast(res.error || 'Failed to update mode state', 'error');
        await fetchModes();
        renderContent(activeCanvas);
      }
    } catch (err) {
      window.UI.Toast('Network error while toggling mode', 'error');
    }
  }

  async function toggleNewBadge(mapId, gameMode, matchMode, isNew) {
    try {
      const res = await window.apiClient.post('/api/dashboard/modes/update', {
        map_id: parseInt(mapId, 10),
        game_mode: parseInt(gameMode, 10),
        match_mode: parseInt(matchMode, 10),
        is_new: Boolean(isNew)
      });

      if (res.ok) {
        if (Array.isArray(res.data?.modes)) {
          state.modes = res.data.modes;
        } else {
          const item = state.modes.find(m =>
            m.map_id === parseInt(mapId, 10) &&
            m.game_mode === parseInt(gameMode, 10) &&
            m.match_mode === parseInt(matchMode, 10)
          );
          if (item) item.is_new = isNew;
        }
        window.UI.Toast(`NEW badge ${isNew ? 'enabled' : 'removed'}`, 'info');
        renderContent(activeCanvas);
      } else {
        window.UI.Toast(res.error || 'Failed to update badge', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error updating badge', 'error');
    }
  }

  async function unlockAllModes() {
    window.UI.Confirm(
      'Unlock All Game Modes',
      'This will enable all 16 authentic Free Fire 1.39 game modes across Bermuda, Purgatory, and Death Uprising for all players in real time. Proceed?',
      async () => {
        try {
          let res = await window.apiClient.post('/api/dashboard/modes/unlock_all', {});
          if (!res.ok) {
            res = await window.apiClient.post('/api/dashboard/modes/unlock-all', {});
          }
          if (res.ok) {
            if (Array.isArray(res.data?.modes)) {
              state.modes = res.data.modes;
            } else {
              await fetchModes();
            }
            window.UI.Toast(
              res.data?.unlocked_count
                ? `All ${res.data.unlocked_count} authentic modes unlocked!`
                : 'All game modes unlocked successfully!',
              'success'
            );
            renderContent(activeCanvas);
          } else {
            window.UI.Toast(res.error || 'Unlock All failed', 'error');
          }
        } catch (err) {
          window.UI.Toast('Network error executing Unlock All', 'error');
        }
      }
    );
  }

  async function lockOptionalModes() {
    window.UI.Confirm(
      'Lock Optional Game Modes',
      'This will lock all experimental and rotating modes, leaving only core authentic modes (Classic Bermuda, Ranked Bermuda, Purgatory, Clash Squad) active. Proceed?',
      async () => {
        try {
          let res = await window.apiClient.post('/api/dashboard/modes/lock_optional', {});
          if (!res.ok) {
            res = await window.apiClient.post('/api/dashboard/modes/lock-optional', {});
          }
          if (res.ok) {
            if (Array.isArray(res.data?.modes)) {
              state.modes = res.data.modes;
            } else {
              await fetchModes();
            }
            window.UI.Toast(
              res.data?.locked_count
                ? `Locked ${res.data.locked_count} optional modes. Core modes active.`
                : 'Optional modes locked successfully',
              'info'
            );
            renderContent(activeCanvas);
          } else {
            window.UI.Toast(res.error || 'Lock optional failed', 'error');
          }
        } catch (err) {
          window.UI.Toast('Network error locking modes', 'error');
        }
      }
    );
  }

  async function resetModes() {
    window.UI.Confirm(
      'Reset Game Modes to Authentic Defaults',
      'This will reset the entire game modes registry back to original Free Fire 1.39 factory settings, restoring default unlock statuses, sort IDs, and rank thresholds. This action cannot be undone.',
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/modes/reset', {});
          if (res.ok) {
            if (Array.isArray(res.data?.modes)) {
              state.modes = res.data.modes;
            } else {
              await fetchModes();
            }
            window.UI.Toast('All game modes reset to authentic defaults', 'success');
            renderContent(activeCanvas);
          } else {
            window.UI.Toast(res.error || 'Reset failed', 'error');
          }
        } catch (err) {
          window.UI.Toast('Network error resetting game modes', 'error');
        }
      },
      true
    );
  }

  function openEditModal(modeKey) {
    const mode = state.modes.find(m => getModeKey(m) === modeKey);
    if (!mode) return;

    const modalBody = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div>
          <label class="form-label">Mode Title</label>
          <input type="text" id="edit-mode-title" class="form-input" value="${escapeHtml(mode.mode_title || mode.name || '')}">
        </div>

        <div>
          <label class="form-label">Description / Tips</label>
          <textarea id="edit-mode-tips" class="form-input" rows="3" style="resize: vertical;">${escapeHtml(mode.tips || '')}</textarea>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label class="form-label">Squad Limit (e.g. 1;2;4)</label>
            <input type="text" id="edit-mode-squads" class="form-input" value="${escapeHtml(mode.player_count_limit || '1;2;4')}">
          </div>
          <div>
            <label class="form-label">Sort Order</label>
            <input type="number" id="edit-mode-sort" class="form-input" value="${mode.sort_id || 0}">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label class="form-label">Min Rank Requirement</label>
            <input type="number" id="edit-mode-rank" class="form-input" value="${mode.limited_rank || 0}" min="0">
          </div>
          <div>
            <label class="form-label">Visual Style</label>
            <select id="edit-mode-style" class="form-select">
              <option value="0" ${mode.level_visual_style === 0 ? 'selected' : ''}>0 — Normal Visuals</option>
              <option value="1" ${mode.level_visual_style === 1 ? 'selected' : ''}>1 — Ranked (Gold Frame)</option>
            </select>
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 10px; margin-top: 6px;">
          <label class="mac-toggle">
            <input type="checkbox" id="edit-mode-is-new" ${mode.is_new ? 'checked' : ''}>
            <span class="mac-toggle-track">
              <span class="mac-toggle-thumb"></span>
            </span>
          </label>
          <label for="edit-mode-is-new" class="mac-toggle-label" style="cursor: pointer;">
            Display "NEW" badge on client mode selector
          </label>
        </div>
      </div>
    `;

    const modalFooter = `
      <button class="btn btn-primary" onclick="window.GameModes.saveEditModal('${escapeHtml(modeKey)}')">Save Configuration</button>
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay')?.remove()">Cancel</button>
    `;

    window.UI.Modal(`Edit Mode: ${escapeHtml(mode.mode_title || mode.name)}`, modalBody, modalFooter);
  }

  async function saveEditModal(modeKey) {
    const mode = state.modes.find(m => getModeKey(m) === modeKey);
    if (!mode) return;

    const titleInput = document.getElementById('edit-mode-title');
    const tipsInput = document.getElementById('edit-mode-tips');
    const squadsInput = document.getElementById('edit-mode-squads');
    const sortInput = document.getElementById('edit-mode-sort');
    const rankInput = document.getElementById('edit-mode-rank');
    const styleInput = document.getElementById('edit-mode-style');
    const isNewInput = document.getElementById('edit-mode-is-new');

    const payload = {
      map_id: mode.map_id,
      game_mode: mode.game_mode,
      match_mode: mode.match_mode,
      mode_title: titleInput ? titleInput.value.trim() : mode.mode_title,
      tips: tipsInput ? tipsInput.value.trim() : mode.tips,
      player_count_limit: squadsInput ? squadsInput.value.trim() : mode.player_count_limit,
      sort_id: sortInput ? parseInt(sortInput.value, 10) || 0 : mode.sort_id,
      limited_rank: rankInput ? parseInt(rankInput.value, 10) || 0 : mode.limited_rank,
      level_visual_style: styleInput ? parseInt(styleInput.value, 10) || 0 : mode.level_visual_style,
      is_new: isNewInput ? isNewInput.checked : mode.is_new
    };

    try {
      const res = await window.apiClient.post('/api/dashboard/modes/update', payload);
      if (res.ok) {
        document.getElementById('global-modal-overlay')?.remove();
        window.UI.Toast('Mode configuration saved successfully', 'success');
        if (Array.isArray(res.data?.modes)) {
          state.modes = res.data.modes;
        } else {
          await fetchModes();
        }
        renderContent(activeCanvas);
      } else {
        window.UI.Toast(res.error || 'Failed to update mode configuration', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error saving configuration', 'error');
    }
  }

  // --- Filtering Logic ---

  function getFilteredModes() {
    return state.modes.filter(mode => {
      // Map filter
      if (state.mapFilter !== 'all' && String(mode.map_id) !== state.mapFilter) {
        return false;
      }
      // Match mode filter
      if (state.matchModeFilter !== 'all' && String(mode.match_mode) !== state.matchModeFilter) {
        return false;
      }
      // Status filter
      if (state.statusFilter === 'active' && !mode.enable) {
        return false;
      }
      if (state.statusFilter === 'locked' && mode.enable) {
        return false;
      }
      // Search query
      if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        const title = (mode.mode_title || '').toLowerCase();
        const name = (mode.name || '').toLowerCase();
        const tips = (mode.tips || '').toLowerCase();
        const key = getModeKey(mode).toLowerCase();
        if (!title.includes(q) && !name.includes(q) && !tips.includes(q) && !key.includes(q)) {
          return false;
        }
      }
      return true;
    });
  }

  // --- Rendering UI ---

  let activeCanvas = null;

  function renderContent(canvas) {
    canvas = canvas || activeCanvas || document.getElementById('workspace-canvas');
    if (!canvas) return;
    activeCanvas = canvas;

    if (state.loading && state.modes.length === 0) {
      canvas.innerHTML = window.UI.Loading('Loading game modes registry...');
      return;
    }

    if (state.error && state.modes.length === 0) {
      canvas.innerHTML = `
        <div class="glass-card" style="border-color: rgba(244, 63, 94, 0.4); max-width: 600px; margin: 40px auto; text-align: center;">
          <div style="font-size: 28px; margin-bottom: 8px;">⚠️</div>
          <div style="color: var(--accent-rose); font-weight: 600; font-size: 16px; margin-bottom: 8px;">Modes Telemetry Unreachable</div>
          <div style="color: var(--text-secondary); font-size: 12px; margin-bottom: 20px;">${escapeHtml(state.error)}</div>
          <button class="btn btn-primary" onclick="window.GameModes.refresh()">Retry Connection</button>
        </div>
      `;
      return;
    }

    const filtered = getFilteredModes();
    const totalCount = state.modes.length;
    const activeCount = state.modes.filter(m => m.enable).length;
    const lockedCount = totalCount - activeCount;
    const rankedCount = state.modes.filter(m => m.match_mode === 2).length;
    const casualCount = state.modes.filter(m => m.match_mode === 1).length;

    // Header & Actions
    const actionsHtml = `
      <button class="btn btn-success" onclick="window.GameModes.unlockAll()" title="Unlock all 16 authentic modes">
        <span>🔓</span><span>Unlock All</span>
      </button>
      <button class="btn btn-secondary" onclick="window.GameModes.lockOptional()" title="Lock optional, keep core only">
        <span>🔒</span><span>Lock Optional</span>
      </button>
      <button class="btn btn-secondary" onclick="window.GameModes.refresh()" title="Refresh registry">
        <span>🔄</span><span>Sync</span>
      </button>
      <button class="btn btn-danger" onclick="window.GameModes.reset()" title="Reset to authentic 1.39 defaults">
        <span>⚠️</span><span>Reset</span>
      </button>
    `;

    // Standardized Stat Cards Row using UI.StatCard
    const metricsHtml = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px;">
        ${window.UI.StatCard('Total Modes', String(totalCount), 'Registered Descriptors', '🎮', 'cyan')}
        ${window.UI.StatCard('Active / Unlocked', String(activeCount), 'Available in Lobby', '●', 'emerald')}
        ${window.UI.StatCard('Locked / Disabled', String(lockedCount), 'Closed in Client', '○', 'rose')}
        ${window.UI.StatCard('Ranked Modes', String(rankedCount), 'Competitive Queues', '🏆', 'amber')}
        ${window.UI.StatCard('Casual Modes', String(casualCount), 'Standard Playlists', '🎯', 'blue')}
      </div>
    `;

    // Filter Controls Bar
    const filterBarHtml = `
      <div style="background: var(--bg-card); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 20px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;">
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px; flex: 1; min-width: 280px;">
          <!-- Search Input -->
          <div style="position: relative; flex: 1; min-width: 180px; max-width: 320px;">
            <input
              type="text"
              id="modes-search-input"
              class="form-input"
              placeholder="Search mode, title, tips..."
              value="${escapeHtml(state.searchQuery)}"
              oninput="window.GameModes.setSearch(this.value)"
              style="padding-left: 28px;"
            >
            <span style="position: absolute; left: 9px; top: 8px; opacity: 0.5; font-size: 12px;">🔍</span>
          </div>

          <!-- Map Filter Buttons -->
          <div style="display: inline-flex; background: var(--bg-input); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: 2px;">
            <button class="filter-pill ${state.mapFilter === 'all' ? 'active' : ''}" onclick="window.GameModes.setMapFilter('all')">All Maps</button>
            <button class="filter-pill ${state.mapFilter === '1' ? 'active' : ''}" onclick="window.GameModes.setMapFilter('1')">Bermuda (1)</button>
            <button class="filter-pill ${state.mapFilter === '2' ? 'active' : ''}" onclick="window.GameModes.setMapFilter('2')">Purgatory (2)</button>
            <button class="filter-pill ${state.mapFilter === '3' ? 'active' : ''}" onclick="window.GameModes.setMapFilter('3')">Death Uprising (3)</button>
          </div>

          <!-- Status Filter -->
          <div style="display: inline-flex; background: var(--bg-input); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: 2px;">
            <button class="filter-pill ${state.statusFilter === 'all' ? 'active' : ''}" onclick="window.GameModes.setStatusFilter('all')">All Status</button>
            <button class="filter-pill ${state.statusFilter === 'active' ? 'active' : ''}" onclick="window.GameModes.setStatusFilter('active')">Active</button>
            <button class="filter-pill ${state.statusFilter === 'locked' ? 'active' : ''}" onclick="window.GameModes.setStatusFilter('locked')">Locked</button>
          </div>

          <!-- Match Mode Filter -->
          <div style="display: inline-flex; background: var(--bg-input); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: 2px;">
            <button class="filter-pill ${state.matchModeFilter === 'all' ? 'active' : ''}" onclick="window.GameModes.setMatchModeFilter('all')">All Types</button>
            <button class="filter-pill ${state.matchModeFilter === '1' ? 'active' : ''}" onclick="window.GameModes.setMatchModeFilter('1')">Casual</button>
            <button class="filter-pill ${state.matchModeFilter === '2' ? 'active' : ''}" onclick="window.GameModes.setMatchModeFilter('2')">Ranked</button>
          </div>
        </div>

        <!-- View Switcher -->
        <div style="display: inline-flex; background: var(--bg-input); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: 2px;">
          <button class="filter-pill ${state.viewMode === 'grid' ? 'active' : ''}" onclick="window.GameModes.setViewMode('grid')" title="Card Grid View">
            ⊞ Grid
          </button>
          <button class="filter-pill ${state.viewMode === 'table' ? 'active' : ''}" onclick="window.GameModes.setViewMode('table')" title="Dense Table View">
            ☰ Table
          </button>
        </div>
      </div>
    `;

    // Mode Content (Grid or Table)
    let bodyHtml = '';
    if (filtered.length === 0) {
      bodyHtml = window.UI.EmptyState(
        'No Matching Modes Found',
        'Adjust your search keyword or map/status filters to display registered game modes.',
        '🎮'
      );
    } else if (state.viewMode === 'grid') {
      bodyHtml = `
        <div class="modes-grid-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
          ${filtered.map(mode => renderModeCard(mode)).join('')}
        </div>
      `;
    } else {
      bodyHtml = renderModesTable(filtered);
    }

    // Embed Component Custom Filter Pill Styles
    const styleBlock = `
      <style>
        .filter-pill {
          background: transparent;
          border: none;
          color: var(--text-secondary);
          font-family: var(--font-sans);
          font-size: 11px;
          font-weight: 500;
          padding: 4px 10px;
          border-radius: var(--radius-xs);
          cursor: pointer;
          transition: all var(--transition-fast);
        }
        .filter-pill:hover {
          color: var(--text-primary);
        }
        .filter-pill.active {
          background: var(--bg-surface-elevated);
          color: var(--accent-cyan);
          box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }
        .mode-glass-card {
          background: var(--bg-card);
          backdrop-filter: var(--blur-sm);
          -webkit-backdrop-filter: var(--blur-sm);
          border: 1px solid var(--border-default);
          border-radius: var(--radius-md);
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          transition: all var(--transition-fast);
          position: relative;
        }
        .mode-glass-card:hover {
          background: var(--bg-card-hover);
          border-color: rgba(255, 255, 255, 0.2);
          box-shadow: var(--shadow-glass);
        }
        .mode-glass-card.is-active {
          border-left: 3px solid var(--accent-emerald);
        }
        .mode-glass-card.is-locked {
          border-left: 3px solid var(--accent-rose);
          opacity: 0.85;
        }
      </style>
    `;

    canvas.innerHTML = `
      ${styleBlock}
      <div style="max-width: 1400px; margin: 0 auto;">
        ${window.UI.Card(
          'Game Modes Management',
          'Authentic Free Fire 1.39 Game Mode Configuration & Live Server Availability',
          metricsHtml + filterBarHtml + bodyHtml,
          actionsHtml
        )}
      </div>
    `;
  }

  function renderModeCard(mode) {
    const isEnabled = Boolean(mode.enable);
    const modeKey = getModeKey(mode);
    const mapName = MAP_NAMES[mode.map_id] || `Map ${mode.map_id}`;
    const gmName = GAME_MODE_NAMES[mode.game_mode] || `Mode ${mode.game_mode}`;

    const rankedBadge = mode.match_mode === 2
      ? window.UI.Badge('Ranked', 'amber')
      : window.UI.Badge('Casual', 'neutral');

    const newBadge = mode.is_new ? window.UI.Badge('NEW', 'rose') : '';
    const statusBadge = isEnabled
      ? window.UI.Badge('ACTIVE', 'emerald')
      : window.UI.Badge('LOCKED', 'rose');

    return `
      <div class="mode-glass-card ${isEnabled ? 'is-active' : 'is-locked'}" id="mode-card-${escapeHtml(modeKey)}">
        <!-- Card Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
          <div>
            <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">${escapeHtml(mode.mode_title || mode.name)}</div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">
              ${window.UI.Badge(`${mapName} (${mode.map_id})`, 'cyan')}
              ${window.UI.Badge(gmName, 'neutral')}
              ${rankedBadge}
              ${newBadge}
              ${statusBadge}
            </div>
          </div>
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary); padding: 2px 6px; background: rgba(0,0,0,0.3); border-radius: 4px;">
            ${escapeHtml(modeKey)}
          </div>
        </div>

        <!-- Description / Tips -->
        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.45; min-height: 32px; background: rgba(0,0,0,0.2); padding: 8px 10px; border-radius: var(--radius-xs);">
          ${escapeHtml(mode.tips || 'Authentic Free Fire 1.39 game mode with native client descriptors.')}
        </div>

        <!-- Key Parameters Grid -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; font-family: var(--font-mono); font-size: 10.5px; background: rgba(0,0,0,0.15); padding: 8px 10px; border-radius: var(--radius-xs);">
          <div style="display: flex; justify-content: space-between;">
            <span style="color: var(--text-tertiary);">Squad Size:</span>
            <span style="color: var(--text-primary); font-weight: 500;">${escapeHtml(mode.player_count_limit || '1;2;4')}</span>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="color: var(--text-tertiary);">Sort Order:</span>
            <span style="color: var(--text-primary); font-weight: 500;">#${mode.sort_id || 0}</span>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="color: var(--text-tertiary);">Visual Style:</span>
            <span style="color: var(--text-primary); font-weight: 500;">${mode.level_visual_style === 1 ? 'Ranked (Gold)' : 'Normal'}</span>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="color: var(--text-tertiary);">Min Rank:</span>
            <span style="color: var(--text-primary); font-weight: 500;">${mode.limited_rank > 0 ? 'Lv. ' + mode.limited_rank : 'None'}</span>
          </div>
        </div>

        <!-- Card Footer & Controls using design system mac-toggle -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 10px; margin-top: auto;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <label class="mac-toggle" title="Toggle active status">
              <input
                type="checkbox"
                ${isEnabled ? 'checked' : ''}
                onchange="window.GameModes.toggle('${mode.map_id}', '${mode.game_mode}', '${mode.match_mode}', this.checked)"
              >
              <span class="mac-toggle-track">
                <span class="mac-toggle-thumb"></span>
              </span>
            </label>
            <span style="font-size: 11px; font-weight: 500; color: ${isEnabled ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">
              ${isEnabled ? 'Active' : 'Locked'}
            </span>
          </div>

          <div style="display: flex; gap: 6px;">
            <button
              class="btn btn-secondary"
              style="padding: 3px 8px; font-size: 10.5px;"
              onclick="window.GameModes.toggleNew('${mode.map_id}', '${mode.game_mode}', '${mode.match_mode}', ${!mode.is_new})"
              title="Toggle NEW banner tag"
            >
              ${mode.is_new ? 'Remove NEW' : 'Set NEW'}
            </button>
            <button
              class="btn btn-secondary"
              style="padding: 3px 8px; font-size: 10.5px;"
              onclick="window.GameModes.edit('${escapeHtml(modeKey)}')"
              title="Edit parameters"
            >
              ⚙️ Edit
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function renderModesTable(modesList) {
    const columns = [
      'Map',
      'Mode Title',
      'Mode ID',
      'Match Type',
      'Squads',
      'Sort',
      'Min Rank',
      'NEW Tag',
      'Status',
      'Actions'
    ];

    const rowsHtml = modesList.map(m => {
      const modeKey = getModeKey(m);
      const mapName = MAP_NAMES[m.map_id] || `Map ${m.map_id}`;
      const gmName = GAME_MODE_NAMES[m.game_mode] || `Mode ${m.game_mode}`;
      const isEnabled = Boolean(m.enable);

      return `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--text-primary);">${escapeHtml(mapName)}</div>
            <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary);">ID: ${m.map_id}</div>
          </td>
          <td>
            <div style="font-weight: 600; color: var(--text-primary);">${escapeHtml(m.mode_title || m.name)}</div>
            <div style="font-size: 11px; color: var(--text-secondary); max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              ${escapeHtml(m.tips || '-')}
            </div>
          </td>
          <td>
            <span style="font-family: var(--font-mono);">${m.game_mode}</span>
            <div style="font-size: 10px; color: var(--text-tertiary);">${escapeHtml(gmName)}</div>
          </td>
          <td>
            ${m.match_mode === 2 ? window.UI.Badge('Ranked', 'amber') : window.UI.Badge('Casual', 'neutral')}
          </td>
          <td style="font-family: var(--font-mono); font-size: 11px;">
            ${escapeHtml(m.player_count_limit || '1;2;4')}
          </td>
          <td style="font-family: var(--font-mono);">
            #${m.sort_id || 0}
          </td>
          <td style="font-family: var(--font-mono);">
            ${m.limited_rank > 0 ? 'Lv. ' + m.limited_rank : 'None'}
          </td>
          <td>
            ${m.is_new ? window.UI.Badge('NEW', 'rose') : '<span style="color: var(--text-tertiary);">-</span>'}
          </td>
          <td>
            <label class="mac-toggle" title="Toggle active status">
              <input
                type="checkbox"
                ${isEnabled ? 'checked' : ''}
                onchange="window.GameModes.toggle('${m.map_id}', '${m.game_mode}', '${m.match_mode}', this.checked)"
              >
              <span class="mac-toggle-track">
                <span class="mac-toggle-thumb"></span>
              </span>
            </label>
          </td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button
                class="btn btn-secondary"
                style="padding: 2px 6px; font-size: 10px;"
                onclick="window.GameModes.edit('${escapeHtml(modeKey)}')"
              >
                Edit
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    return window.UI.Table(columns, rowsHtml, 'No matching game modes');
  }

  // --- Public Interface ---

  const GameModes = {
    async render(container) {
      if (container) activeCanvas = container;
      if (state.modes.length === 0) {
        await fetchModes();
      }
      renderContent(activeCanvas);
    },

    async refresh() {
      await fetchModes();
      window.UI.Toast('Game modes synchronized', 'info');
      renderContent(activeCanvas);
    },

    toggle: toggleMode,
    toggleNew: toggleNewBadge,
    unlockAll: unlockAllModes,
    lockOptional: lockOptionalModes,
    reset: resetModes,
    edit: openEditModal,
    saveEditModal: saveEditModal,

    setSearch(val) {
      state.searchQuery = val || '';
      renderContent(activeCanvas);
    },

    setMapFilter(mapId) {
      state.mapFilter = mapId;
      renderContent(activeCanvas);
    },

    setStatusFilter(status) {
      state.statusFilter = status;
      renderContent(activeCanvas);
    },

    setMatchModeFilter(mm) {
      state.matchModeFilter = mm;
      renderContent(activeCanvas);
    },

    setViewMode(mode) {
      state.viewMode = mode;
      renderContent(activeCanvas);
    }
  };

  window.GameModes = GameModes;

  // Export to window.Modules for coordinator / app.js integration
  window.Modules = window.Modules || {};
  window.Modules.GameModes = (canvas) => GameModes.render(canvas);

  // Register with SPA Hash Router
  function registerRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/game/modes', (canvas) => GameModes.render(canvas));
    }
  }

  registerRoute();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(registerRoute, 0));
  } else {
    setTimeout(registerRoute, 0);
  }
})();
