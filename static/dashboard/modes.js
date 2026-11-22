// Game Modes & Maps Studio Client Script (Free Fire 1.39 India V1)

let allModes = [];
let activeFilter = 'all';

function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.style.borderColor = isError ? '#f43f5e' : '#38bdf8';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2600);
}

async function loadModes() {
  try {
    const res = await fetch('/api/dashboard/modes');
    const data = await res.json();
    if (!data.ok && !Array.isArray(data.modes)) {
      showToast(data.error || 'Failed to load modes', true);
      return;
    }
    allModes = data.modes || [];
    renderModes();
    updateStats();
  } catch (err) {
    console.error('loadModes error:', err);
    showToast('Network error loading modes', true);
  }
}

function updateStats() {
  const total = allModes.length;
  const active = allModes.filter(m => m.enable).length;
  const locked = total - active;

  document.getElementById('stat-total').textContent = total;
  document.getElementById('stat-active').textContent = active;
  document.getElementById('stat-locked').textContent = locked;
}

function filterMap(mapId, btn) {
  activeFilter = mapId;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderModes();
}

function renderModes() {
  const grid = document.getElementById('modes-grid');
  if (!grid) return;
  grid.innerHTML = '';

  const filtered = allModes.filter(m => {
    if (activeFilter === 'all') return true;
    return String(m.map_id) === String(activeFilter);
  });

  filtered.forEach(mode => {
    const card = document.createElement('div');
    const isEnabled = Boolean(mode.enable);
    card.className = `mode-card ${isEnabled ? 'is-active' : 'is-locked'}`;

    const matchModeName = mode.match_mode === 2 ? 'Ranked' : 'Casual';
    const mapName = mode.name || (mode.map_id === 1 ? 'Bermuda' : (mode.map_id === 2 ? 'Purgatory' : 'Death Uprising'));

    card.innerHTML = `
      <div class="card-head">
        <div class="card-title-group">
          <div class="card-title">${escapeHtml(mode.mode_title || mode.name)}</div>
          <div class="card-meta-tags">
            <span class="badge badge-map">MAP ${mode.map_id}: ${escapeHtml(mapName)}</span>
            <span class="badge badge-mode">MODE ID: ${mode.game_mode}</span>
            <span class="badge ${mode.match_mode === 2 ? 'badge-ranked' : ''}">${matchModeName}</span>
            ${mode.is_new ? '<span class="badge badge-new">NEW</span>' : ''}
            <span class="badge ${isEnabled ? 'badge-status-on' : 'badge-status-off'}">
              ${isEnabled ? 'ACTIVE' : 'LOCKED'}
            </span>
          </div>
        </div>
      </div>

      <div class="card-body">
        ${escapeHtml(mode.tips || 'Authentic Free Fire 1.39 game mode with native client descriptors.')}
      </div>

      <div class="card-params">
        <div class="param-row">
          <span>Squad Size:</span>
          <span class="param-val">${escapeHtml(mode.player_count_limit || '1;2;4')}</span>
        </div>
        <div class="param-row">
          <span>Sort Order:</span>
          <span class="param-val">#${mode.sort_id || 0}</span>
        </div>
        <div class="param-row">
          <span>Visual Style:</span>
          <span class="param-val">${mode.level_visual_style === 1 ? 'Ranked (Gold)' : 'Normal'}</span>
        </div>
        <div class="param-row">
          <span>Rank Req:</span>
          <span class="param-val">${mode.limited_rank > 0 ? 'Lv.' + mode.limited_rank : 'None'}</span>
        </div>
      </div>

      <div class="card-foot">
        <label class="toggle-wrap">
          <span class="switch">
            <input type="checkbox" ${isEnabled ? 'checked' : ''} onchange="toggleMode(${mode.map_id}, ${mode.game_mode}, ${mode.match_mode}, this.checked)">
            <span class="slider"></span>
          </span>
          <span class="toggle-label ${isEnabled ? 'on' : 'off'}">${isEnabled ? 'Unlocked' : 'Closed'}</span>
        </label>
        <div>
          <button class="btn-icon" onclick="toggleNewBadge(${mode.map_id}, ${mode.game_mode}, ${mode.match_mode}, ${!mode.is_new})">
            ${mode.is_new ? 'Remove NEW' : 'Set NEW'}
          </button>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

async function toggleMode(mapId, gameMode, matchMode, enable) {
  try {
    const res = await fetch('/api/dashboard/modes/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ map_id: mapId, game_mode: gameMode, match_mode: matchMode, enable: enable })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`Mode ${enable ? 'unlocked' : 'locked'} successfully`);
      const item = allModes.find(m => m.map_id === mapId && m.game_mode === gameMode && m.match_mode === matchMode);
      if (item) item.enable = enable;
      renderModes();
      updateStats();
    } else {
      showToast(data.error || 'Failed to toggle mode', true);
      loadModes();
    }
  } catch (err) {
    showToast('Failed to update mode state', true);
    loadModes();
  }
}

async function toggleNewBadge(mapId, gameMode, matchMode, isNew) {
  try {
    const res = await fetch('/api/dashboard/modes/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ map_id: mapId, game_mode: gameMode, match_mode: matchMode, is_new: isNew })
    });
    const data = await res.json();
    if (data.ok) {
      showToast(`Badge updated: ${isNew ? 'NEW' : 'Default'}`);
      const item = allModes.find(m => m.map_id === mapId && m.game_mode === gameMode && m.match_mode === matchMode);
      if (item) item.is_new = isNew;
      renderModes();
    } else {
      showToast(data.error || 'Failed to update badge', true);
    }
  } catch (err) {
    showToast('Network error updating badge', true);
  }
}

async function unlockAllModes() {
  try {
    const res = await fetch('/api/dashboard/modes/unlock_all', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    const data = await res.json();
    if (data.ok) {
      showToast(data.msg || 'All 16 authentic modes unlocked!');
      loadModes();
    } else {
      showToast(data.error || 'Unlock all failed', true);
    }
  } catch (err) {
    showToast('Network error unlocking modes', true);
  }
}

async function lockOptionalModes() {
  try {
    const res = await fetch('/api/dashboard/modes/lock_optional', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    const data = await res.json();
    if (data.ok) {
      showToast(data.msg || 'Optional modes locked. Core modes active.');
      loadModes();
    } else {
      showToast(data.error || 'Action failed', true);
    }
  } catch (err) {
    showToast('Network error locking modes', true);
  }
}

async function resetModes() {
  if (!confirm('Reset all game modes to authentic default configuration?')) return;
  try {
    const res = await fetch('/api/dashboard/modes/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    const data = await res.json();
    if (data.ok) {
      showToast('Game modes reset to default');
      loadModes();
    } else {
      showToast(data.error || 'Reset failed', true);
    }
  } catch (err) {
    showToast('Network error resetting modes', true);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', loadModes);
