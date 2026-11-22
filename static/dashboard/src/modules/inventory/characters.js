/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Character Studio & Loadout Selector
 * Route: #/inventory/characters
 *
 * Capabilities:
 * - Reactive binding to PlayerContext (active account ID & selected avatar)
 * - 21 Reverse-engineered Free Fire 1.39 Operatives
 * - Gender filtering & text search
 * - Standardized .page-container layout with UI.PageHeader & .grid-4 metric strip
 * - High-polish dark glass styling with active hero spotlight
 * - Character selection with UI.Confirm safety check -> POST /api/dashboard/character/select
 * - Wardrobe preset equip with UI.Confirm -> POST /api/dashboard/character/equip
 * - Active operative badge & card highlight
 * - Zero consumer emojis
 */

(function () {
  'use strict';

  const CHARACTERS_CATALOG = [
    {
      id: 102000004,
      name: 'Adam',
      gender: 'Male',
      archetype: 'Base Operative',
      color: '#38bdf8',
      skillName: 'Combat Instincts',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Original combat trainee with adaptable physical conditioning and balanced firearms agility.',
      level: 8,
      clothes: [211000000, 208000000, 203000573, 204000345, 205000299],
      lore: 'The foundational male operative of Bermuda. Unpretentious and lethal in close-quarters urban skirmishes.'
    },
    {
      id: 101000001,
      name: 'Eva',
      gender: 'Female',
      archetype: 'Base Operative',
      color: '#38bdf8',
      skillName: 'Tactical Presence',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Master strategist versed in recon maneuvers and tactical deployment in unknown battlezones.',
      level: 8,
      clothes: [211000000, 208000000, 203000573, 204000345, 205000299],
      lore: 'The first female operative on Bermuda. Exceptional spatial awareness and survivalist resilience.'
    },
    {
      id: 102000012,
      name: 'Hayato',
      gender: 'Male',
      archetype: 'Honor Samurai',
      color: '#ef4444',
      skillName: 'Bushido',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'When max HP decreases by 10%, front armor penetration increases by 10.0%. Lethal at low health.',
      level: 8,
      clothes: [211000000, 203000418, 204000237, 205000198],
      lore: 'Descendant of a legendary samurai family. Carries the curse of the ancestral blade with unyielding pride.'
    },
    {
      id: 101000011,
      name: 'Moco',
      gender: 'Female',
      archetype: 'Cyber Hacker',
      color: '#10b981',
      skillName: "Hacker's Eye",
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Tag enemies that Moco shoots for 5.0 seconds. Tag info is shared with teammates instantly on radar.',
      level: 8,
      clothes: [211000000, 203000376, 204000213, 205000178],
      lore: 'The chat-world legend known as "Chat Noir". Capable of breaking into any secured database in seconds.'
    },
    {
      id: 102000011,
      name: 'Wukong',
      gender: 'Male',
      archetype: 'Mystic Beast',
      color: '#f59e0b',
      skillName: 'Camouflage',
      skillType: 'Active',
      cooldown: 200,
      skillDesc: 'Transform into a bush for 15 seconds. Firing any weapon immediately ends the camouflage state.',
      level: 8,
      clothes: [211000000, 203000353, 204000200, 205000167],
      lore: 'An artificial monkey engineered with quantum cloaking fibers. Playful, unpredictable, and stealthy.'
    },
    {
      id: 101000006,
      name: 'Kelly',
      gender: 'Female',
      archetype: 'Track Athlete',
      color: '#eab308',
      skillName: 'Dash',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Sprint speed is permanently increased by 6.0%. The highest natural mobility in open-field sprints.',
      level: 8,
      clothes: [211000000, 203000059, 204000046, 205000029],
      lore: 'High school sprint champion Shimada Kiriko. Her instinct to run forward outpaces incoming gunfire.'
    },
    {
      id: 101000012,
      name: 'Laura',
      gender: 'Female',
      archetype: 'Elite Sharpshooter',
      color: '#06b6d4',
      skillName: 'Sharp Shooter',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Accuracy is increased by 30.0% while aiming through any scope or optical sight.',
      level: 8,
      clothes: [211000000, 203000455, 204000263, 205000221],
      lore: 'Top agent trained since childhood in target interdiction. She never misses a bullseye under pressure.'
    },
    {
      id: 101000013,
      name: 'A124',
      gender: 'Female',
      archetype: 'Bionic Android',
      color: '#6366f1',
      skillName: 'Thrill of Battle',
      skillType: 'Active',
      cooldown: 60,
      skillDesc: 'Quickly convert 50 EP into HP within 4.0 seconds. Turn energy into sustained combat survival.',
      level: 8,
      clothes: [211000000, 203000566, 204000340, 205000294],
      lore: 'A modern humanoid robot created in top-secret labs. Possesses dual personality modes: girl and soldier.'
    },
    {
      id: 102000013,
      name: 'Rafael',
      gender: 'Male',
      archetype: 'Silent Assassin',
      color: '#475569',
      skillName: 'Dead Silent',
      skillType: 'Active',
      cooldown: 40,
      skillDesc: 'Gunshots are completely silenced on the minimap for 8.0 seconds. Strike without revealing position.',
      level: 8,
      clothes: [211000000, 203000528, 204000310, 205000266],
      lore: 'A lethal operative dedicated to purging darkness from the underworld through cold, calculated assassinations.'
    },
    {
      id: 102000014,
      name: 'Joseph',
      gender: 'Male',
      archetype: 'Tech Physicist',
      color: '#ec4899',
      skillName: 'Nutty Movement',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Movement and sprint speed are increased by 20.0% for 1.0 second upon taking enemy damage.',
      level: 8,
      clothes: [211000000, 203000572, 204000344, 205000298],
      lore: 'A renowned scientist, billionaire playboy, and founder of a global military tech enterprise.'
    },
    {
      id: 102000008,
      name: 'Kla',
      gender: 'Male',
      archetype: 'Muay Thai Master',
      color: '#f97316',
      skillName: 'Muay Thai',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Fist damage is boosted by 400.0%. Capable of downing enemies with a single barehanded punch.',
      level: 8,
      clothes: [211000000, 203000177, 204000107, 205000092],
      lore: 'Renowned champion who vanished mysteriously from the ring, reappearing as a ruthless underground brawler.'
    },
    {
      id: 102000007,
      name: 'Maxim',
      gender: 'Male',
      archetype: 'Speed Eater',
      color: '#84cc16',
      skillName: 'Gluttony',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Reduce time for eating mushrooms and using medkits by 12.0%. Quick recovery mid-firefight.',
      level: 8,
      clothes: [211000000, 203000160, 204000096, 205000072],
      lore: 'Competitive eating streamer with an insane metabolism. Optimistic and quick-witted in tight corners.'
    },
    {
      id: 101000009,
      name: 'Paloma',
      gender: 'Female',
      archetype: 'Arms Boss',
      color: '#a855f7',
      skillName: 'Arms-Dealing',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: '180 AR ammo will not take up any inventory space. Frees vital backpack slots for grenades and medkits.',
      level: 8,
      clothes: [211000000, 203000243, 204000140, 205000116],
      lore: 'The reigning arms queen of South America. Feared for her beauty, elegance, and iron grip on black markets.'
    },
    {
      id: 102000009,
      name: 'Miguel',
      gender: 'Male',
      archetype: 'Special Forces',
      color: '#0284c7',
      skillName: 'Crazy Slayer',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Gain 45 EP for each enemy confirmed kill. Keeps energy full through aggressive eliminations.',
      level: 8,
      clothes: [211000000, 203000268, 204000151, 205000121],
      lore: 'Elite commander of a special forces detachment. Dedicated to justice even after deep squad betrayals.'
    },
    {
      id: 102000010,
      name: 'Antonio',
      gender: 'Male',
      archetype: 'Gangland Leader',
      color: '#b45309',
      skillName: "Gangster's Spirit",
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Receive an extra 35 Max HP at the start of each match (total 235 HP baseline). Tough frontline sponge.',
      level: 8,
      clothes: [211000000, 203000333, 204000188, 205000155],
      lore: 'Orphan who climbed to supreme syndicate boss of his home city. Extremely protective of his crew.'
    },
    {
      id: 101000010,
      name: 'Caroline',
      gender: 'Female',
      archetype: 'Highschool Idol',
      color: '#fb7185',
      skillName: 'Agility',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Movement speed is increased by 8.0% when holding any shotgun. Deadly in fast room clearing.',
      level: 8,
      clothes: [211000000, 203000295],
      lore: 'Cosplay superstar and heiress of an influential corporate family. Master of shotgun trick-shots.'
    },
    {
      id: 101000008,
      name: 'Misha',
      gender: 'Female',
      archetype: 'Racer Prodigy',
      color: '#14b8a6',
      skillName: 'Afterburner',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Driving speed increased by 12.0%. While in a vehicle, damage taken from enemy fire is reduced by 30.0%.',
      level: 8,
      clothes: [211000000, 203000127, 204000075, 205000055],
      lore: 'Talented speedway driver with fearless driving skills. No obstacle stops her from leading the track.'
    },
    {
      id: 101000007,
      name: 'Nikita',
      gender: 'Female',
      archetype: 'Bodyguard Elite',
      color: '#3b82f6',
      skillName: 'Firearms Expert',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Submachine gun reload speed is increased by 24.0%. Rapid continuous fire in close combat.',
      level: 8,
      clothes: [211000000, 203000090, 204000062, 205000046],
      lore: 'Professional private security operative tasked with protecting organization executives.'
    },
    {
      id: 101000005,
      name: 'Olivia',
      gender: 'Female',
      archetype: 'Combat Medic',
      color: '#10b981',
      skillName: 'Healing Touch',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Players revived by Olivia will get an extra 40 HP instantly upon standing up.',
      level: 8,
      clothes: [211000000, 203000058, 204000045, 205000028],
      lore: 'Dedicated head nurse whose calm compassion stabilizes critical squadmates amidst heavy shellings.'
    },
    {
      id: 102000005,
      name: 'Andrew',
      gender: 'Male',
      archetype: 'Veteran Police',
      color: '#64748b',
      skillName: 'Armor Specialist',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Vest durability loss is reduced by 12.0%. Prolongs life of level 2 and level 3 body armor.',
      level: 8,
      clothes: [211000000, 203000056, 204000043, 205000026],
      lore: 'Former police officer whose indomitable sense of duty survived deep corruption in law enforcement.'
    },
    {
      id: 102000006,
      name: 'Ford',
      gender: 'Male',
      archetype: 'Naval Sailor',
      color: '#0284c7',
      skillName: 'Iron Will',
      skillType: 'Passive',
      cooldown: 0,
      skillDesc: 'Reduce damage taken outside the safe zone by 24.0%. Outlive enemies during intense storm rotations.',
      level: 8,
      clothes: [211000000, 203000057, 204000044, 205000027],
      lore: 'Resilient navy officer with unyielding endurance honed against ocean gales and stormy seas.'
    }
  ];

  let genderFilter = 'all'; // 'all' | 'Male' | 'Female'
  let charSearch = '';
  let searchTimeout = null;

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function renderCharacters(canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    canvas.innerHTML = window.UI.Loading('Loading operative rosters & state...');

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

    const filtered = CHARACTERS_CATALOG.filter(c => {
      if (genderFilter !== 'all' && c.gender !== genderFilter) return false;
      if (charSearch) {
        const q = charSearch.toLowerCase();
        const matchesName = c.name.toLowerCase().includes(q);
        const matchesSkill = c.skillName.toLowerCase().includes(q);
        const matchesArch = c.archetype.toLowerCase().includes(q);
        if (!matchesName && !matchesSkill && !matchesArch) return false;
      }
      return true;
    });

    const activeChar = CHARACTERS_CATALOG.find(c => c.id === currentAvatarId) || CHARACTERS_CATALOG[0];
    const equippedClothes = (p && p.clothes) || (activeChar.clothes || []);
    const equippedClothesCount = Array.isArray(equippedClothes) ? equippedClothes.length : 0;

    const cardsHtml = filtered.map(c => {
      const isSelected = c.id === currentAvatarId;
      return `
        <div class="glass-card operative-card" style="
          background: ${isSelected ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(10, 16, 28, 0.6) 100%)' : 'rgba(10, 16, 28, 0.45)'};
          border: 1px solid ${isSelected ? 'var(--accent-cyan)' : 'var(--border-default)'};
          box-shadow: ${isSelected ? '0 0 16px rgba(56, 189, 248, 0.18)' : 'none'};
          border-radius: var(--radius-md);
          padding: 16px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          transition: all var(--transition-fast);
        ">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <code style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); font-weight: 600;">ID: ${c.id}</code>
              ${isSelected ? window.UI.Badge('ACTIVE OPERATIVE', 'cyan') : window.UI.Badge(c.gender.toUpperCase(), 'neutral')}
            </div>

            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
              <div style="
                width: 32px;
                height: 32px;
                border-radius: 50%;
                background: linear-gradient(135deg, ${c.color}, rgba(255, 255, 255, 0.1));
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                font-weight: 700;
                color: #fff;
              ">
                ${c.name.charAt(0)}
              </div>
              <div>
                <div style="font-size: 15px; font-weight: 700; color: #fff;">${escapeHtml(c.name)}</div>
                <div style="font-size: 11px; color: var(--text-tertiary);">${escapeHtml(c.archetype)}</div>
              </div>
            </div>

            <div style="background: rgba(0, 0, 0, 0.28); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px; margin: 10px 0;">
              <div style="display: flex; justify-content: space-between; font-size: 11.5px; font-weight: 600; color: var(--accent-amber); margin-bottom: 4px;">
                <span>Skill: ${escapeHtml(c.skillName)}</span>
                <span style="font-size: 10.5px; color: var(--text-tertiary);">${c.skillType}${c.cooldown ? ` (${c.cooldown}s CD)` : ''}</span>
              </div>
              <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.45;">
                ${escapeHtml(c.skillDesc)}
              </div>
            </div>

            <div style="font-size: 11px; color: var(--text-tertiary); font-style: italic; line-height: 1.4; margin-bottom: 12px; min-height: 32px;">
              "${escapeHtml(c.lore)}"
            </div>
          </div>

          <div style="display: flex; gap: 8px; border-top: 1px solid var(--border-subtle); padding-top: 12px;">
            <button class="btn ${isSelected ? 'btn-secondary' : 'btn-primary'}"
              style="flex: 1; font-size: 11px;"
              ${isSelected ? 'disabled' : ''}
              onclick="window.CharacterManager.promptSelectCharacter(${c.id}, '${escapeHtml(c.name).replace(/'/g, "\\'")}')">
              ${isSelected ? window.UI.Icon('check', 12) + ' Active Loadout' : 'Select Operative'}
            </button>
            <button class="btn btn-secondary" style="font-size: 11px;" title="Equip default battle attire"
              onclick="window.CharacterManager.promptEquipClothes(${c.id}, '${escapeHtml(c.name).replace(/'/g, "\\'")}', [${c.clothes.join(',')}])">
              ${window.UI.Icon('shirt', 12)} Attire
            </button>
          </div>
        </div>
      `;
    }).join('');

    const pageActionsHtml = `
      <button class="btn btn-primary" onclick="window.location.hash='#/inventory/wardrobe'">
        ${window.UI.Icon('shirt', 14)} <span>Open Cosmetics & Wardrobe</span>
      </button>
      <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.CharacterManager.render(c);">
        ${window.UI.Icon('refresh', 14)} <span>Sync Profile</span>
      </button>
    `;

    canvas.innerHTML = `
      <div class="page-container">
        <!-- 1. Page Header -->
        ${window.UI.PageHeader(
          'Operatives & Character Studio',
          'Equip active character avatars and manage operative skill loadouts',
          pageActionsHtml,
          'user'
        )}

        <!-- 2. Exactly 4 Compact Metrics (.grid-4) -->
        <div class="grid-4" style="margin-bottom: var(--space-md);">
          ${window.UI.StatCard(
            'Total Operatives',
            `${CHARACTERS_CATALOG.length} Heroes`,
            'Verified FF 1.39 roster',
            window.UI.Icon('users', 16, '', 'var(--accent-cyan)'),
            'cyan'
          )}
          ${window.UI.StatCard(
            'Active Hero',
            escapeHtml(activeChar.name),
            `ID: ${activeChar.id} • Lv.8 MAX`,
            window.UI.Icon('userCheck', 16, '', 'var(--accent-amber)'),
            'amber'
          )}
          ${window.UI.StatCard(
            'Collection Ratio',
            '100% Unlocked',
            'Full combat roster available',
            window.UI.Icon('award', 16, '', 'var(--accent-emerald)'),
            'emerald'
          )}
          ${window.UI.StatCard(
            'Equipped Attire Items',
            `${equippedClothesCount} Items`,
            'Cosmetic loadout slots',
            window.UI.Icon('shirt', 16, '', 'var(--accent-blue)'),
            'blue'
          )}
        </div>

        <!-- 3. Active Operative Spotlight Card -->
        <div style="background: linear-gradient(135deg, rgba(14, 28, 54, 0.7), rgba(8, 14, 26, 0.85)); border: 1px solid var(--border-accent); border-radius: var(--radius-md); padding: 18px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 16px;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue)); display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; color: #fff;">
              ${activeChar.name.charAt(0)}
            </div>
            <div>
              <div style="font-size: 11px; color: var(--accent-cyan); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em;">Current Active Operative</div>
              <div style="font-size: 18px; font-weight: 700; color: #fff;">
                ${escapeHtml(activeChar.name)} <span style="font-size: 12px; font-weight: 400; color: var(--text-tertiary);">(ID: ${activeChar.id})</span>
              </div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                Archetype: <b>${escapeHtml(activeChar.archetype)}</b> • Skill: <b>${escapeHtml(activeChar.skillName)}</b> (${activeChar.skillType})
              </div>
            </div>
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary" onclick="window.location.hash='#/inventory/wardrobe'">
              ${window.UI.Icon('shirt', 14)} Wardrobe & Equipment
            </button>
            <button class="btn btn-secondary" onclick="window.playerContext.refresh(); const c = document.getElementById('workspace-canvas'); if (c) window.CharacterManager.render(c);">
              ${window.UI.Icon('refresh', 14)} Sync
            </button>
          </div>
        </div>

        <!-- 4. Filter and Search Toolbar -->
        <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div style="display: flex; gap: 6px;">
            <button class="btn ${genderFilter === 'all' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 11px;" onclick="window.CharacterManager.setGender('all')">
              All (${CHARACTERS_CATALOG.length})
            </button>
            <button class="btn ${genderFilter === 'Male' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 11px;" onclick="window.CharacterManager.setGender('Male')">
              Male Operatives (11)
            </button>
            <button class="btn ${genderFilter === 'Female' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 11px;" onclick="window.CharacterManager.setGender('Female')">
              Female Operatives (10)
            </button>
          </div>

          <div style="min-width: 260px; max-width: 320px;">
            <input type="text" class="form-input" placeholder="Search operative or skill..." value="${escapeHtml(charSearch)}" oninput="window.CharacterManager.handleSearch(this.value)">
          </div>
        </div>

        <!-- 5. Operatives Cards Grid (auto-fill minmax(260px, 1fr)) -->
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px;">
          ${cardsHtml}
        </div>
      </div>
    `;
  }

  function setGender(g) {
    genderFilter = g;
    const canvas = document.getElementById('workspace-canvas');
    if (canvas) renderCharacters(canvas);
  }

  function handleSearch(val) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      charSearch = val.trim();
      const canvas = document.getElementById('workspace-canvas');
      if (canvas) renderCharacters(canvas);
    }, 200);
  }

  function promptSelectCharacter(charId, charName) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Deploy Active Operative',
      `Deploy <b>${charName}</b> (Avatar ID: <code>${charId}</code>) as the active hero for Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/character/select', {
            account_id: aid,
            avatar_id: charId
          });
          if (res.ok) {
            window.UI.Toast(`Operative ${charName} deployed successfully`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderCharacters(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to select character', 'error');
          }
        } catch (e) {
          window.UI.Toast(e.message, 'error');
        }
      }
    );
  }

  function promptEquipClothes(charId, charName, clothesArr) {
    const aid = window.playerContext.getSelectedAccountId();
    window.UI.Confirm(
      'Equip Signature Wardrobe',
      `Equip default battle attire (${clothesArr.length} items) on <b>${charName}</b> for Account <b>${aid}</b>?`,
      async () => {
        try {
          const res = await window.apiClient.post('/api/dashboard/character/equip', {
            account_id: aid,
            avatar_id: charId,
            character_id: charId,
            clothes: clothesArr,
            item_ids: clothesArr
          });
          if (res.ok) {
            window.UI.Toast(`Equipped signature attire on ${charName}`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) renderCharacters(canvas);
          } else {
            window.UI.Toast(res.error || 'Equip attire failed', 'error');
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
      if (window.location.hash.startsWith('#/inventory/characters')) {
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) renderCharacters(canvas);
      }
    });
  }

  // Export module interface
  window.Modules = window.Modules || {};
  window.Modules.CharacterManager = renderCharacters;

  window.CharacterManager = {
    render: renderCharacters,
    setGender,
    handleSearch,
    promptSelectCharacter,
    promptEquipClothes
  };

  // Register SPA route
  function bindRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/inventory/characters', renderCharacters);
    }
  }

  bindRoute();
  document.addEventListener('DOMContentLoaded', () => setTimeout(bindRoute, 0));
})();
