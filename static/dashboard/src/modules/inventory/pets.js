/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Pet Companion Studio & Manager
 * Route: #/inventory/pets
 *
 * Capabilities:
 * - Reactive binding to PlayerContext (active account, selected pet, selected skin)
 * - 5 Reverse-engineered Free Fire 1.39 Companions & 21 Skins
 * - Tactical skill breakdown & companion stats
 * - Standardized .page-container layout with UI.PageHeader & .grid-4 metric strip
 * - High-polish dark glass styling with active companion spotlight
 * - Skin picker per companion
 * - Pet & skin equip with UI.Confirm -> POST /api/dashboard/pet/select
 * - Zero consumer emojis
 */

(function () {
  'use strict';

  const PETS_CATALOG = [
    {
      id: 1300000001,
      name: 'Kitty',
      rareType: 4,
      maxLevel: 6,
      color: '#f43f5e',
      skillName: 'Feline Grace',
      skillType: 'Companion Emotes',
      skillDesc: 'Loyal companion that reacts to emotes, sprint maneuvers, and victory celebrations with acrobatic flips.',
      defaultSkin: 1310000001,
      skins: [
        { id: 1310000001, name: 'Default Tabby', color: '#f59e0b' },
        { id: 1310000002, name: 'Pink Velvet', color: '#f43f5e' },
        { id: 1310000003, name: 'Tuxedo Black', color: '#334155' },
        { id: 1310000004, name: 'Cyber Neon', color: '#06b6d4' },
        { id: 1310000005, name: 'Imperial Gold', color: '#eab308' }
      ]
    },
    {
      id: 1300000011,
      name: 'Mechanical Pup',
      rareType: 4,
      maxLevel: 7,
      color: '#06b6d4',
      skillName: 'Robotic Scout',
      skillType: 'Radar Companion',
      skillDesc: 'Engineered sentinel dog equipped with radar beacons and cybernetic sensors that emit audio cues near airdrops.',
      defaultSkin: 1310000011,
      skins: [
        { id: 1310000011, name: 'Titanium Base', color: '#64748b' },
        { id: 1310000012, name: 'Neon Plasma', color: '#06b6d4' },
        { id: 1310000013, name: 'Desert Camo', color: '#b45309' },
        { id: 1310000014, name: 'Obsidian Stealth', color: '#1e293b' }
      ]
    },
    {
      id: 1300000021,
      name: 'Night Panther',
      rareType: 5,
      maxLevel: 7,
      color: '#8b5cf6',
      skillName: 'Weight Training',
      skillType: 'Tactical Buff',
      skillDesc: 'Increases operative backpack item inventory capacity by 45 slots. Carry massive ordnance without encumbrance.',
      defaultSkin: 1310000021,
      skins: [
        { id: 1310000021, name: 'Midnight Shadow', color: '#8b5cf6' },
        { id: 1310000022, name: 'Magma Beast', color: '#ef4444' },
        { id: 1310000023, name: 'Cybernetic Hunter', color: '#38bdf8' },
        { id: 1310000024, name: 'Golden Apex', color: '#eab308' }
      ]
    },
    {
      id: 1300000031,
      name: 'Detective Panda',
      rareType: 5,
      maxLevel: 7,
      color: '#10b981',
      skillName: "Panda's Blessings",
      skillType: 'Combat Healing',
      skillDesc: 'Restores 10 HP immediately upon every enemy confirmed kill. Chain eliminations to sustain uninterrupted aggressive rushes.',
      defaultSkin: 1310000031,
      skins: [
        { id: 1310000031, name: 'Classic Detective', color: '#10b981' },
        { id: 1310000032, name: 'Bamboo Warrior', color: '#84cc16' },
        { id: 1310000033, name: 'Royal Scholar', color: '#6366f1' },
        { id: 1310000034, name: 'Shadow Operative', color: '#0f172a' }
      ]
    },
    {
      id: 1300000041,
      name: 'Shiba',
      rareType: 5,
      maxLevel: 7,
      color: '#f59e0b',
      skillName: 'Mushroom Sense',
      skillType: 'Radar Sense',
      skillDesc: 'Marks the exact location of 1 surrounding mushroom on the minimap every 120 seconds. The mark lasts for 30 seconds.',
      defaultSkin: 1310000041,
      skins: [
        { id: 1310000041, name: 'Original Akita', color: '#f59e0b' },
        { id: 1310000042, name: 'Crimson Kimono', color: '#ef4444' },
        { id: 1310000043, name: 'Gilded Sun', color: '#eab308' },
        { id: 1310000044, name: 'Cyber Samurai', color: '#38bdf8' }
      ]
    }
  ];

  // Selected skin per pet in current UI session
  const selectedSkins = {};
  PETS_CATALOG.forEach(p => {
    selectedSkins[p.id] = p.defaultSkin;
  });

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function renderPets(canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Loading('Loading companion state...');

    let p = window.playerContext.getCurrentPlayer();
    if (!p || p.account_id !== aid) {
      try {
        const res = await window.apiClient.get('/api/dashboard/state', { account_id: aid });
        if (res.ok && res.data) p = res.data;
      } catch (e) {
        console.error('Failed to load player state:', e);
      }
    }

    const currentPetId = (p && p.profile && p.profile.selected_pet_id) || (p && p.selected_pet_id) || 1300000001;
    const currentSkinId = (p && p.profile && p.profile.selected_pet_skin_id) || (p && p.selected_pet_skin_id) || 1310000001;

    // Sync current selection for active pet
    if (selectedSkins[currentPetId] === undefined) {
      selectedSkins[currentPetId] = currentSkinId;
    }

    const activePet = PETS_CATALOG.find(pet => pet.id === currentPetId) || PETS_CATALOG[0];

    // Compute total available companion skins
    let totalSkins = 0;
    PETS_CATALOG.forEach(pet => {
      totalSkins += (pet.skins ? pet.skins.length : 0);
    });

    const cardsHtml = PETS_CATALOG.map(pet => {
      const isEquipped = pet.id === currentPetId;
      const currentChosenSkinId = selectedSkins[pet.id] || pet.defaultSkin;
      const currentSkinObj = pet.skins.find(s => s.id === currentChosenSkinId) || pet.skins[0];

      const skinPillsHtml = pet.skins.map(skin => {
        const isSkinActive = skin.id === currentChosenSkinId;
        return `
          <button class="btn ${isSkinActive ? 'btn-primary' : 'btn-secondary'}"
            style="padding: 3px 8px; font-size: 11px;"
            onclick="window.PetManager.chooseSkin(${pet.id}, ${skin.id})">
            ${escapeHtml(skin.name)}
          </button>
        `;
      }).join('');

      return `
        <div class="glass-card pet-card" style="
          background: ${isEquipped ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(10, 16, 28, 0.6) 100%)' : 'rgba(10, 16, 28, 0.45)'};
          border: 1px solid ${isEquipped ? 'var(--accent-cyan)' : 'var(--border-default)'};
          box-shadow: ${isEquipped ? '0 0 16px rgba(56, 189, 248, 0.18)' : 'none'};
          border-radius: var(--radius-md);
          padding: 16px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          transition: all var(--transition-fast);
        ">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <code style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); font-weight: 600;">ID: ${pet.id}</code>
              ${isEquipped ? window.UI.Badge('ACTIVE COMPANION', 'cyan') : window.UI.Badge(`MAX LV.${pet.maxLevel}`, 'neutral')}
            </div>

            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
              <div style="
                width: 34px;
                height: 34px;
                border-radius: var(--radius-sm);
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                justify-content: center;
              ">
                ${window.UI.Icon('pawPrint', 18, '', pet.color || 'var(--accent-emerald)')}
              </div>
              <div style="font-size: 16px; font-weight: 700; color: #fff;">
                ${escapeHtml(pet.name)}
              </div>
            </div>

            <!-- Companion Tactical Skill -->
            <div style="background: rgba(0, 0, 0, 0.28); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px; margin: 10px 0;">
              <div style="display: flex; justify-content: space-between; font-size: 11.5px; font-weight: 600; color: var(--accent-emerald); margin-bottom: 4px;">
                <span>Skill: ${escapeHtml(pet.skillName)}</span>
                <span style="font-size: 10.5px; color: var(--text-tertiary);">${escapeHtml(pet.skillType)}</span>
              </div>
              <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.45;">
                ${escapeHtml(pet.skillDesc)}
              </div>
            </div>

            <!-- Skin Selector Pills -->
            <div style="margin: 12px 0 6px;">
              <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600; margin-bottom: 6px;">
                Selected Attire / Skin: <span style="color: #fff;">${escapeHtml(currentSkinObj.name)}</span>
              </div>
              <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                ${skinPillsHtml}
              </div>
            </div>
          </div>

          <div style="border-top: 1px solid var(--border-subtle); padding-top: 12px; margin-top: 12px;">
            <button class="btn ${isEquipped && currentSkinId === currentChosenSkinId ? 'btn-secondary' : 'btn-primary'}"
              style="width: 100%; font-size: 11.5px;"
              ${isEquipped && currentSkinId === currentChosenSkinId ? 'disabled' : ''}
              onclick="window.PetManager.promptEquipPet(${pet.id}, '${escapeHtml(pet.name).replace(/'/g, "\\'")}', ${currentChosenSkinId}, '${escapeHtml(currentSkinObj.name).replace(/'/g, "\\'")}')">
              ${isEquipped && currentSkinId === currentChosenSkinId ? window.UI.Icon('check', 12) + ' Currently Equipped' : `${window.UI.Icon('pawPrint', 12)} Equip ${escapeHtml(pet.name)} (${escapeHtml(currentSkinObj.name)})`}
            </button>
          </div>
        </div>
      `;
    }).join('');

    const pageActionsHtml = `
      <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.PetManager.render(c);">
        ${window.UI.Icon('refresh', 14)} <span>Sync Companion State</span>
      </button>
    `;

    canvas.innerHTML = `
      <div class="page-container">
        <!-- 1. Page Header -->
        ${window.UI.PageHeader(
          'Companion Pets & Tactical Studio',
          'Deploy and customize active companion pets and tactical skill synergies',
          pageActionsHtml,
          'pawPrint'
        )}

        <!-- 2. Exactly 4 Compact Metrics (.grid-4) -->
        <div class="grid-4" style="margin-bottom: var(--space-md);">
          ${window.UI.StatCard(
            'Available Companions',
            `${PETS_CATALOG.length} Tactical Pets`,
            'FF 1.39 companion engine',
            window.UI.Icon('pawPrint', 16, '', 'var(--accent-cyan)'),
            'cyan'
          )}
          ${window.UI.StatCard(
            'Equipped Companion',
            escapeHtml(activePet.name),
            `Pet ID: ${activePet.id}`,
            window.UI.Icon('checkCircle', 16, '', 'var(--accent-amber)'),
            'amber'
          )}
          ${window.UI.StatCard(
            'Total Skins Available',
            `${totalSkins} Skins`,
            'Custom attire & textures',
            window.UI.Icon('sparkles', 16, '', 'var(--accent-emerald)'),
            'emerald'
          )}
          ${window.UI.StatCard(
            'Tactical Synergy',
            escapeHtml(activePet.skillName),
            escapeHtml(activePet.skillType),
            window.UI.Icon('activity', 16, '', 'var(--accent-blue)'),
            'blue'
          )}
        </div>

        <!-- 3. Active Pet Overview Bar (Zero Emojis!) -->
        <div style="background: linear-gradient(135deg, rgba(14, 28, 54, 0.7), rgba(8, 14, 26, 0.85)); border: 1px solid var(--border-accent); border-radius: var(--radius-md); padding: 18px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, var(--accent-emerald), var(--accent-cyan)); display: flex; align-items: center; justify-content: center;">
              ${window.UI.Icon('pawPrint', 22, '', '#ffffff')}
            </div>
            <div>
              <div style="font-size: 11px; color: var(--accent-cyan); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Equipped Companion</div>
              <div style="font-size: 17px; font-weight: 700; color: #fff;">
                ${escapeHtml(activePet.name)} <span style="font-size: 12px; font-weight: 400; color: var(--text-tertiary);">(ID: ${activePet.id})</span>
              </div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">
                Perk: <b>${escapeHtml(activePet.skillName)}</b> — ${escapeHtml(activePet.skillDesc)}
              </div>
            </div>
          </div>

          <div>
            <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.PetManager.render(c);">
              ${window.UI.Icon('refresh', 14)} Sync Companion State
            </button>
          </div>
        </div>

        <!-- 4. Companions Grid (auto-fill minmax(280px, 1fr)) -->
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;">
          ${cardsHtml}
        </div>
      </div>
    `;
  }

  function chooseSkin(petId, skinId) {
    selectedSkins[petId] = skinId;
    const canvas = document.getElementById('workspace-canvas');
    if (canvas) renderPets(canvas);
  }

  function promptEquipPet(petId, petName, skinId, skinName) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Equip Companion',
      `Equip <b>${petName}</b> with <b>${skinName}</b> skin (Pet ID: <code>${petId}</code>, Skin ID: <code>${skinId}</code>) for Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/pet/select', {
            account_id: aid,
            pet_id: petId,
            skin_id: skinId
          });
          if (res.ok) {
            window.UI.Toast(`Equipped ${petName} (${skinName}) for Account ${aid}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderPets(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to select pet', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      }
    );
  }

  // Reactive listener to playerContext account switches
  if (window.playerContext && typeof window.playerContext.onPlayerChange === 'function') {
    window.playerContext.onPlayerChange(() => {
      if (window.location.hash.startsWith('#/inventory/pets')) {
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) renderPets(canvas);
      }
    });
  }

  // Export module interface
  window.Modules = window.Modules || {};
  window.Modules.PetManager = renderPets;

  window.PetManager = {
    render: renderPets,
    chooseSkin,
    promptEquipPet
  };

  // Register SPA route
  function bindRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/inventory/pets', renderPets);
    }
  }

  bindRoute();
  document.addEventListener('DOMContentLoaded', () => setTimeout(bindRoute, 0));
})();
