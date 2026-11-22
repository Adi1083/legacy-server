/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Cosmetics & Wardrobe Manager
 * Route: #/inventory/wardrobe
 *
 * Capabilities:
 * - Dynamic PlayerContext binding (active account & operative)
 * - Standardized .page-container layout with UI.PageHeader & .grid-4 metric strip
 * - High-polish dark glass styling with equipment slot preview
 * - Loadout equipment slots (Headwear, Face/Mask, Torso, Legs, Shoes)
 * - 1-Click Signature Wardrobe Presets (Samurai, Cyber, Track, Bionic, Syndicate)
 * - Custom cosmetic clothing array editor with UI.Confirm safety check
 * - Dispatches POST /api/dashboard/character/equip
 * - Zero consumer emojis
 */

(function () {
  'use strict';

  const WARDROBE_PRESETS = [
    {
      id: 'trainee',
      name: 'Base Operative Combat Trainee',
      character: 'Adam / Eva',
      clothes: [211000000, 208000000, 203000573, 204000345, 205000299],
      desc: 'Standard-issue Bermuda combat fatigues with reinforced tactical boots and storm hood.'
    },
    {
      id: 'samurai',
      name: 'Honor Samurai Kimono',
      character: 'Hayato',
      clothes: [211000000, 203000418, 204000237, 205000198],
      desc: 'Ancestral crimson kimono bearing the Shimada house crest with lightweight battle hakama.'
    },
    {
      id: 'hacker',
      name: 'Cyberpunk Neon Infiltrator',
      character: 'Moco',
      clothes: [211000000, 203000376, 204000213, 205000178],
      desc: 'Fiber-optic laced tunic with data cables woven into armor plates.'
    },
    {
      id: 'track',
      name: 'Shimada Highspeed Tracksuit',
      character: 'Kelly',
      clothes: [211000000, 203000059, 204000046, 205000029],
      desc: 'Aerodynamic yellow sprint jacket matched with high-flexibility running tights.'
    },
    {
      id: 'bionic',
      name: 'A124 Synthetic Exoskeleton',
      character: 'A124',
      clothes: [211000000, 203000566, 204000340, 205000294],
      desc: 'High-density alloy frame radiating bioluminescent energy pulses.'
    },
    {
      id: 'gangster',
      name: 'Syndicate Boss Formal Attire',
      character: 'Antonio',
      clothes: [211000000, 203000333, 204000188, 205000155],
      desc: 'Silk button-down with gold embroidery and tailored gangland slacks.'
    },
    {
      id: 'red_crim',
      name: 'Red Criminal Syndicate Suit',
      character: 'Universal',
      clothes: [700000003],
      desc: 'Full-body crimson bank raider jumpsuit with signature devil grin mask.'
    },
    {
      id: 'sakura',
      name: 'Sakura Demon Dynasty Set',
      character: 'Universal',
      clothes: [700000001],
      desc: 'Historical feudal armor adorned with fallen cherry blossoms and lacquered plates.'
    }
  ];

  const HERO_MAP = {
    102000004: 'Adam',
    101000001: 'Eva',
    102000012: 'Hayato',
    101000011: 'Moco',
    102000011: 'Wukong',
    101000006: 'Kelly',
    101000012: 'Laura',
    101000013: 'A124',
    102000013: 'Rafael',
    102000014: 'Joseph',
    102000008: 'Kla',
    102000007: 'Maxim',
    101000009: 'Paloma',
    102000009: 'Miguel',
    102000010: 'Antonio',
    101000010: 'Caroline',
    101000008: 'Misha',
    101000007: 'Nikita',
    101000005: 'Olivia',
    102000005: 'Andrew',
    102000006: 'Ford'
  };

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function renderWardrobe(canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Loading('Loading wardrobe configuration...');

    let p = window.playerContext.getCurrentPlayer();
    if (!p || p.account_id !== aid) {
      try {
        const res = await window.apiClient.get('/api/dashboard/state', { account_id: aid });
        if (res.ok && res.data) p = res.data;
      } catch (e) {
        console.error('State load error', e);
      }
    }

    const currentAvatarId = (p && p.profile && (p.profile.avatar_id || p.profile.selected_avatar_id)) || (p && p.avatar_id) || 102000004;
    const heroName = HERO_MAP[currentAvatarId] || `Operative #${currentAvatarId}`;

    const equippedClothes = (p && p.clothes) || [211000000, 208000000, 203000573, 204000345, 205000299];
    const equippedSlotsCount = Array.isArray(equippedClothes) ? equippedClothes.length : 0;

    // Slot labels
    const slotNames = ['Headwear / Hat', 'Face / Mask', 'Torso / Top', 'Pants / Legs', 'Footwear / Shoes'];
    const slotIcons = ['shield', 'eye', 'shirt', 'package', 'sparkles'];

    const slotsPreviewHtml = slotNames.map((name, idx) => {
      const itemId = equippedClothes[idx] || null;
      const icon = slotIcons[idx] || 'package';
      return `
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: 12px; display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 32px; height: 32px; border-radius: var(--radius-sm); background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); display: flex; align-items: center; justify-content: center;">
              ${window.UI.Icon(icon, 16, '', 'var(--accent-cyan)')}
            </div>
            <div>
              <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600;">Slot ${idx + 1}</div>
              <div style="font-size: 13px; font-weight: 600; color: #fff;">${name}</div>
            </div>
          </div>
          <div>
            ${itemId ? `<code style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-amber); font-weight: 600;">${itemId}</code>` : window.UI.Badge('EMPTY', 'neutral')}
          </div>
        </div>
      `;
    }).join('');

    const presetsHtml = WARDROBE_PRESETS.map(preset => `
      <div class="glass-card wardrobe-preset-card" style="
        background: rgba(10, 16, 28, 0.45);
        border: 1px solid var(--border-default);
        border-radius: var(--radius-md);
        padding: 16px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all var(--transition-fast);
      ">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 13.5px; font-weight: 700; color: #fff;">${escapeHtml(preset.name)}</span>
            ${window.UI.Badge(preset.character, 'cyan')}
          </div>
          <div style="font-size: 11px; color: var(--text-tertiary); line-height: 1.4; margin-bottom: 12px; min-height: 32px;">
            ${escapeHtml(preset.desc)}
          </div>
          <div style="background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border-subtle); padding: 8px 10px; border-radius: 6px; margin-bottom: 12px; font-family: var(--font-mono); font-size: 10.5px; color: var(--accent-amber);">
            Items: ${preset.clothes.join(', ')}
          </div>
        </div>

        <div style="border-top: 1px solid var(--border-subtle); padding-top: 12px;">
          <button class="btn btn-primary" style="width: 100%; font-size: 11px;"
            onclick="window.WardrobeManager.promptEquipPreset('${escapeHtml(preset.name).replace(/'/g, "\\'")}', [${preset.clothes.join(',')}])">
            ${window.UI.Icon('shirt', 12)} Equip This Preset
          </button>
        </div>
      </div>
    `).join('');

    const pageActionsHtml = `
      <button class="btn btn-primary" onclick="window.location.hash='#/inventory/characters'">
        ${window.UI.Icon('user', 14)} <span>Operatives Studio</span>
      </button>
      <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.WardrobeManager.render(c);">
        ${window.UI.Icon('refresh', 14)} <span>Sync</span>
      </button>
    `;

    canvas.innerHTML = `
      <div class="page-container">
        <!-- 1. Page Header -->
        ${window.UI.PageHeader(
          'Wardrobe & Cosmetic Equipment',
          'Configure cosmetic attire slots, battle suits, and signature wardrobe sets',
          pageActionsHtml,
          'shirt'
        )}

        <!-- 2. Exactly 4 Compact Metrics (.grid-4) -->
        <div class="grid-4" style="margin-bottom: var(--space-md);">
          ${window.UI.StatCard(
            'Active Operative',
            escapeHtml(heroName),
            `Avatar ID: ${currentAvatarId}`,
            window.UI.Icon('user', 16, '', 'var(--accent-cyan)'),
            'cyan'
          )}
          ${window.UI.StatCard(
            'Equipped Clothing Slots',
            `${equippedSlotsCount} Slots`,
            'Active battle attire',
            window.UI.Icon('shirt', 16, '', 'var(--accent-amber)'),
            'amber'
          )}
          ${window.UI.StatCard(
            'Signature Presets',
            `${WARDROBE_PRESETS.length} Sets`,
            'Curated loadout presets',
            window.UI.Icon('sparkles', 16, '', 'var(--accent-emerald)'),
            'emerald'
          )}
          ${window.UI.StatCard(
            'Vault Sync Status',
            'Synchronized',
            `Account ${aid} active`,
            window.UI.Icon('checkCircle', 16, '', 'var(--accent-blue)'),
            'blue'
          )}
        </div>

        <!-- 3. Active Operative & Loadout Slots Preview -->
        <div style="background: linear-gradient(135deg, rgba(14, 28, 54, 0.7), rgba(8, 14, 26, 0.85)); border: 1px solid var(--border-accent); border-radius: var(--radius-md); padding: 18px; margin-bottom: 20px;">
          <div style="display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 14px;">
            <div>
              <div style="font-size: 11px; color: var(--accent-cyan); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Active Subject Operative</div>
              <div style="font-size: 18px; font-weight: 700; color: #fff;">
                ${escapeHtml(heroName)} <span style="font-size: 12px; font-weight: 400; color: var(--text-tertiary);">(Avatar ID: ${currentAvatarId} • Account: ${aid})</span>
              </div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">
                Cosmetics and wardrobe loadouts apply directly to the equipped character slot.
              </div>
            </div>

            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="window.location.hash='#/inventory/characters'">
                ${window.UI.Icon('user', 14)} Switch Operative
              </button>
              <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.WardrobeManager.render(c);">
                ${window.UI.Icon('refresh', 14)} Refresh
              </button>
            </div>
          </div>

          <!-- Slots Strip -->
          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;">
            ${slotsPreviewHtml}
          </div>
        </div>

        <!-- 4. Custom Equipment Bar -->
        <div style="background: rgba(10, 16, 28, 0.45); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 16px; margin-bottom: 24px;">
          <div style="font-weight: 600; color: #fff; margin-bottom: 6px; font-size: 13.5px;">Equip Custom Attire Array</div>
          <p style="color: var(--text-secondary); font-size: 11.5px; margin-bottom: 12px;">
            Enter custom clothing Item IDs (comma-separated numeric IDs) to apply directly to the active operative:
          </p>
          <div style="display: flex; gap: 8px; max-width: 580px;">
            <input type="text" id="custom-clothes-input" class="form-input" placeholder="e.g. 211000000, 208000000, 203000573, 204000345, 205000299">
            <button class="btn btn-primary" style="white-space: nowrap;" onclick="window.WardrobeManager.applyCustomClothes()">
              ${window.UI.Icon('shirt', 14)} Apply Attire
            </button>
          </div>
        </div>

        <!-- 5. Signature Presets Grid -->
        <div style="font-weight: 600; color: #fff; margin-bottom: 12px; font-size: 14px;">Signature Wardrobe Presets</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px;">
          ${presetsHtml}
        </div>
      </div>
    `;
  }

  function promptEquipPreset(presetName, clothesArr) {
    const aid = window.playerContext.getSelectedAccountId();
    const p = window.playerContext.getCurrentPlayer() || {};
    const avatarId = (p.profile && p.profile.avatar_id) || p.avatar_id || 102000004;

    window.UI.Confirm(
      'Equip Preset Wardrobe',
      `Equip <b>${presetName}</b> (${clothesArr.length} items) on Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/character/equip', {
            account_id: aid,
            avatar_id: avatarId,
            clothes: clothesArr,
            item_ids: clothesArr
          });
          if (res.ok) {
            window.UI.Toast(`Equipped ${presetName} successfully`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderWardrobe(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to equip wardrobe', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      }
    );
  }

  function applyCustomClothes() {
    const input = document.getElementById('custom-clothes-input');
    if (!input || !input.value.trim()) {
      window.UI.Toast('Please enter at least one clothing Item ID', 'warning');
      return;
    }

    const tokens = input.value.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n) && n > 0);
    if (tokens.length === 0) {
      window.UI.Toast('No valid numeric Item IDs found', 'warning');
      return;
    }

    promptEquipPreset('Custom Outfit Selection', tokens);
  }

  // Reactive listener to playerContext account switches
  if (window.playerContext && typeof window.playerContext.onPlayerChange === 'function') {
    window.playerContext.onPlayerChange(() => {
      if (window.location.hash.startsWith('#/inventory/wardrobe')) {
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) renderWardrobe(canvas);
      }
    });
  }

  // Export module interface
  window.Modules = window.Modules || {};
  window.Modules.WardrobeManager = renderWardrobe;

  window.WardrobeManager = {
    render: renderWardrobe,
    promptEquipPreset,
    applyCustomClothes
  };

  // Register SPA route
  function bindRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/inventory/wardrobe', renderWardrobe);
    }
  }

  bindRoute();
  document.addEventListener('DOMContentLoaded', () => setTimeout(bindRoute, 0));
})();
