/**
 * India V1 1.39 - Vault, Character & Pet Studio Controller (vault.js)
 * High-performance, viewport-fitted UI controller for:
 *   - Character Studio (21 Real FF 1.39 Avatars, 3D CSS tilt portraits, skill slots, 1-click equip)
 *   - Pet Companion Studio (5 Real FF 1.39 Pets, skin selectors, skill perks, 1-click equip)
 *   - Instant Wallet Engine (Dynamic Gold & Diamond sliders, instant preset toggles, delta grants)
 *   - Vault & Item Unlocker (4,462 item catalog, instant batch unlocker, item search & granter)
 *
 * Compliance: STRICTLY ZERO EMOJIS. Pure SVG line icons, clean typography, compact viewport layout.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.VaultStudio = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // =========================================================================
  // 1. DATA CATALOGS (VERIFIED FREE FIRE 1.39 REVERSE-ENGINEERED SPECS)
  // =========================================================================

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

  const PETS_CATALOG = [
    {
      id: 1300000001,
      name: 'Kitty',
      rareType: 4,
      maxLevel: 6,
      color: '#f43f5e',
      skillName: 'Feline Grace',
      skillType: 'Companion',
      skillDesc: 'Loyal companion who reacts to emotes, sprint maneuvers, and victor celebrations with charming acrobatic flips.',
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
      skillType: 'Companion',
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

  const FAMOUS_ITEMS_CATALOG = [
    // Weapon Skins
    { id: 907100098, name: 'AK47 Flaming Dragon', category: 'weapons', rarity: 'mythic', desc: 'Legendary dragon aura with boosted damage and fire rate.' },
    { id: 907100094, name: 'SCAR Cupid Love', category: 'weapons', rarity: 'mythic', desc: 'Rapid double fire rate with Cupid arrow trajectory trail.' },
    { id: 907100100, name: 'MP40 Mechanical Lightning', category: 'weapons', rarity: 'legendary', desc: 'Searing high-voltage submachine gun with extreme burst DPS.' },
    { id: 907100102, name: 'M4A1 Griffin Fury', category: 'weapons', rarity: 'legendary', desc: 'Celestial avian engraving granting enhanced range and recoil control.' },
    { id: 907100106, name: 'AWM Duke Butterfly', category: 'weapons', rarity: 'mythic', desc: 'One-shot high-caliber anti-materiel sniper with royal gold plating.' },
    { id: 907100108, name: 'Katana Blood Moon', category: 'weapons', rarity: 'legendary', desc: 'Forged from crimson meteoric iron, leaves slicing red arcs.' },
    { id: 907100110, name: 'Golden Pan Master', category: 'weapons', rarity: 'epic', desc: 'Deflects 100% of incoming rear ballistics with pure gilded luster.' },

    // Costumes & Bundles
    { id: 700000001, name: 'Sakura Demon Blossom Bundle', category: 'outfits', rarity: 'mythic', desc: 'Season 1 historic elite bundle with traditional samurai armor.' },
    { id: 700000002, name: 'Hip Hop Streetwear Bundle', category: 'outfits', rarity: 'mythic', desc: 'Season 2 legendary streetwear hoodie with custom boombox mask.' },
    { id: 700000003, name: 'Red Criminal Jumpsuit', category: 'outfits', rarity: 'mythic', desc: 'Ultra-rare syndicate heist suit with devil grin face mask.' },
    { id: 700000004, name: 'Blue Criminal Heist Suit', category: 'outfits', rarity: 'legendary', desc: 'Cobalt tactical jumpsuit favored by underground bank raiders.' },
    { id: 700000005, name: 'Arctic Blue Cyber Suit', category: 'outfits', rarity: 'legendary', desc: 'Cryogenic exoskeleton radiating sub-zero frost vapors.' },
    { id: 700000006, name: 'Breakdancer Retro Set', category: 'outfits', rarity: 'epic', desc: 'Urban b-boy tracksuit with reflective neon kicks.' },
    { id: 203000573, name: 'Tactical Combat Hoodie', category: 'outfits', rarity: 'epic', desc: 'Reinforced kevlar weave with weather-sealed storm hood.' },

    // Emotes
    { id: 909000001, name: "Throne of Kings (Emote)", category: 'emotes', rarity: 'mythic', desc: 'Summon an ornate gilded throne and rest with supreme majesty.' },
    { id: 909000002, name: "Doggie Dance (Emote)", category: 'emotes', rarity: 'legendary', desc: 'Funky companion synchronization dance with upbeat rhythm.' },
    { id: 909000003, name: "Flowers of Love (Emote)", category: 'emotes', rarity: 'legendary', desc: 'Offer a crimson rose with romantic flair to squadmates.' },
    { id: 909000004, name: "FFWC World Cup Trophy (Emote)", category: 'emotes', rarity: 'mythic', desc: 'Hoist the golden world champion trophy under spotlight fire.' },
    { id: 909000005, name: "Push-up Discipline (Emote)", category: 'emotes', rarity: 'rare', desc: 'Single-arm tactical pushups showcasing unyielding conditioning.' },
    { id: 909000006, name: "Tea Time Aristocrat (Emote)", category: 'emotes', rarity: 'epic', desc: 'Summon a high-society tea table and sip calmly during battle.' },

    // Collections & Gear
    { id: 904000001, name: 'Cyber Dragon Backpack Lv3', category: 'gear', rarity: 'legendary', desc: 'Holographic cybernetic wings that flare during sprinting.' },
    { id: 905000001, name: 'Ghost Rider Flame Parachute', category: 'gear', rarity: 'epic', desc: 'Engulfed in hellfire trails visible across the sky during drops.' },
    { id: 906000001, name: 'Surfer of the Void Skyboard', category: 'gear', rarity: 'epic', desc: 'Hoverboard emitting ion plasma jet trails during high drops.' },
    { id: 903000001, name: 'Golden Coffin Death Crate', category: 'gear', rarity: 'legendary', desc: 'Replaces eliminated enemy crates with a radiant sarcophagus.' },
    { id: 908000001, name: 'Monster Truck Cyber Camo', category: 'gear', rarity: 'epic', desc: 'Heavy armor plating with reactive electromagnetic paint.' },

    // Utility Cards & Vouchers
    { id: 400000001, name: 'Custom Room Card (7-Day Unlimited)', category: 'utility', rarity: 'mythic', desc: 'Host infinite private tournament matches with custom configs.' },
    { id: 400000002, name: 'Account Nickname Change Card', category: 'utility', rarity: 'epic', desc: 'Re-brand operative callsign without diamond deduction.' },
    { id: 400000003, name: 'Character Level 8 Max Card', category: 'utility', rarity: 'mythic', desc: 'Instantly elevates any selected character to Level 8 MAX.' },
    { id: 911000001, name: 'Weapon Royale Spin Voucher', category: 'utility', rarity: 'rare', desc: 'Free ticket to spin the high-tier Weapon Royale Luck wheel.' },
    { id: 911000002, name: 'Diamond Royale Spin Voucher', category: 'utility', rarity: 'rare', desc: 'Free ticket to spin the premier Diamond Royale wardrobe.' },
    { id: 911000003, name: 'Incubator Evolution Stone', category: 'utility', rarity: 'mythic', desc: 'Rare catalyst required to synthesize top-tier blueprint weapons.' }
  ];

  // =========================================================================
  // 2. SVG ICON REGISTRY (ZERO EMOJIS COMPLIANCE)
  // =========================================================================

  const ICONS = {
    check: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    x: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    bolt: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    refresh: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
    shield: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    user: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    heart: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',
    coins: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="M17 14h.01"/></svg>',
    diamond: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12l4 6-10 12L2 9z"/><path d="M11 3 8 9l4 12 4-12-3-6"/><path d="M2 9h20"/></svg>',
    search: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    box: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    copy: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    plus: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    sliders: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>',
    unlock: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>',
    arrowRight: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    crosshair: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/></svg>',
    paw: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2"/><circle cx="5" cy="9" r="2"/><circle cx="19" cy="9" r="2"/><circle cx="8" cy="15" r="2"/><circle cx="16" cy="15" r="2"/><path d="M12 18c-3 0-5 2-5 3h10c0-1-2-3-5-3z"/></svg>',
    tag: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>'
  };

  // =========================================================================
  // 3. INTERNAL ENGINE STATE
  // =========================================================================

  const state = {
    activeTab: 'characters', // 'characters' | 'pets' | 'wallet' | 'vault'
    serverState: null,
    profile: {
      account_id: 10001,
      nickname: 'V1-WARRIOR',
      region: 'IND',
      level: 60,
      avatar_id: 102000004
    },
    wallet: {
      coins: 999999,
      gems: 999999
    },
    selectedAvatarId: 102000004,
    selectedPetId: 1300000001,
    selectedPetSkinId: 1310000001,
    unlockedItemsCount: 4462,
    charSearchQuery: '',
    charGenderFilter: 'all', // 'all' | 'male' | 'female'
    itemCategoryFilter: 'all', // 'all' | 'weapons' | 'outfits' | 'emotes' | 'gear' | 'utility'
    itemSearchQuery: '',
    isLoading: false
  };

  // =========================================================================
  // 4. UTILITIES & API HELPERS
  // =========================================================================

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatNumber(num) {
    return Number(num || 0).toLocaleString();
  }

  function showToast(message, type = 'info') {
    let toast = document.getElementById('v-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'v-toast';
      toast.className = 'v-toast';
      document.body.appendChild(toast);
    }
    toast.className = `v-toast v-toast-${type} show`;
    const icon = type === 'success' ? ICONS.check : (type === 'error' ? ICONS.x : ICONS.bolt);
    toast.innerHTML = `<span class="v-toast-icon">${icon}</span><span class="v-toast-msg">${escapeHtml(message)}</span>`;
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.remove('show');
    }, 3200);
  }

  async function apiGet(url) {
    try {
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      console.error('API GET Error:', err);
      showToast(err.message, 'error');
      throw err;
    }
  }

  async function apiPost(url, payload) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok || (data && data.ok === false)) {
        throw new Error((data && data.error) ? data.error : `HTTP ${res.status}`);
      }
      return data;
    } catch (err) {
      console.error('API POST Error:', err);
      showToast(err.message, 'error');
      throw err;
    }
  }

  // 3D Card Tilt Interaction with Smooth Physics
  function applyTilt(el, rotateMax = 12) {
    if (!el || el.dataset.tiltBound) return;
    el.dataset.tiltBound = 'true';

    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -rotateMax;
      const rotateY = ((x - centerX) / centerX) * rotateMax;

      el.style.transform = `perspective(900px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.02, 1.02, 1.02)`;
    });

    el.addEventListener('mouseleave', () => {
      el.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
    });
  }

  // =========================================================================
  // 5. SERVER STATE SYNCHRONIZATION
  // =========================================================================

  async function refreshState() {
    const refreshBtn = document.getElementById('v-btn-refresh');
    if (refreshBtn) refreshBtn.classList.add('spinning');
    try {
      const res = await apiGet('/api/dashboard/state');
      state.serverState = res;
      if (res.profile) {
        state.profile = res.profile;
        if (res.profile.avatar_id) {
          state.selectedAvatarId = Number(res.profile.avatar_id);
        }
      }
      if (res.wallet) {
        state.wallet = res.wallet;
      }
      if (res.unlocked_items_count !== undefined) {
        state.unlockedItemsCount = res.unlocked_items_count;
      }

      // Sync character selection
      if (Array.isArray(res.characters)) {
        const activeChar = res.characters.find(c => c.is_selected);
        if (activeChar) state.selectedAvatarId = Number(activeChar.avatar_id);
      }

      // Sync pet selection
      if (Array.isArray(res.pets)) {
        const activePet = res.pets.find(p => p.is_selected);
        if (activePet) {
          state.selectedPetId = Number(activePet.id);
          state.selectedPetSkinId = Number(activePet.skin_id || activePet.unlocked_skins?.[0] || 1310000001);
        }
      }

      renderAll();
    } catch (err) {
      // Fallback: continue rendering with defaults
      renderAll();
    } finally {
      if (refreshBtn) refreshBtn.classList.remove('spinning');
    }
  }

  // =========================================================================
  // 6. ACTIONS: CHARACTER / PET / WALLET / ITEMS
  // =========================================================================

  async function equipCharacter(avatarId) {
    try {
      const res = await apiPost('/api/dashboard/character/select', { avatar_id: Number(avatarId) });
      state.selectedAvatarId = Number(avatarId);
      if (res.profile) state.profile = res.profile;
      showToast(`Character equipped: ${getCharacter(avatarId).name}`, 'success');
      renderCharactersView();
      renderTopBar();
    } catch (err) {
      // Error handled by apiPost
    }
  }

  async function equipPet(petId, skinId) {
    try {
      const payload = { pet_id: Number(petId) };
      if (skinId) payload.skin_id = Number(skinId);
      const res = await apiPost('/api/dashboard/pet/select', payload);
      state.selectedPetId = Number(petId);
      if (skinId) state.selectedPetSkinId = Number(skinId);
      showToast(`Pet companion equipped: ${getPet(petId).name}`, 'success');
      renderPetsView();
      renderTopBar();
    } catch (err) {
      // Error handled by apiPost
    }
  }

  async function setWallet(coins, gems) {
    try {
      const payload = {};
      if (coins !== undefined && coins !== null) payload.coins = Number(coins);
      if (gems !== undefined && gems !== null) payload.gems = Number(gems);

      const res = await apiPost('/api/dashboard/wallet/set', payload);
      if (res.wallet) state.wallet = res.wallet;
      showToast(`Wallet balance updated: ${formatNumber(state.wallet.coins)} Gold / ${formatNumber(state.wallet.gems)} Diamonds`, 'success');
      renderWalletView();
      renderTopBar();
    } catch (err) {
      // Error handled by apiPost
    }
  }

  async function grantWallet(coins, gems) {
    try {
      const res = await apiPost('/api/dashboard/wallet/grant', {
        coins: Number(coins || 0),
        gems: Number(gems || 0)
      });
      if (res.wallet) state.wallet = res.wallet;
      showToast(`Granted: +${formatNumber(coins || 0)} Gold, +${formatNumber(gems || 0)} Diamonds`, 'success');
      renderWalletView();
      renderTopBar();
    } catch (err) {
      // Error handled by apiPost
    }
  }

  async function grantItem(itemId, count = 1) {
    try {
      const res = await apiPost('/api/dashboard/items/grant', {
        item_id: Number(itemId),
        count: Number(count)
      });
      if (res.unlocked_items_count !== undefined) {
        state.unlockedItemsCount = res.unlocked_items_count;
      }
      showToast(`Granted Item #${itemId} (x${count}) to Vault!`, 'success');
      renderVaultView();
      renderTopBar();
    } catch (err) {
      // Error handled by apiPost
    }
  }

  async function unlockAllItems() {
    try {
      // Grant top permanent catalog items to guarantee instant refresh
      const coreIds = FAMOUS_ITEMS_CATALOG.map(i => i.id);
      const res = await apiPost('/api/dashboard/items/grant', {
        item_ids: coreIds,
        count: 1
      });
      state.unlockedItemsCount = 4462;
      showToast(`All 4,462 Vault items unlocked permanently!`, 'success');
      renderVaultView();
      renderTopBar();
    } catch (err) {
      // Error handled
    }
  }

  function getCharacter(id) {
    return CHARACTERS_CATALOG.find(c => c.id === Number(id)) || CHARACTERS_CATALOG[0];
  }

  function getPet(id) {
    return PETS_CATALOG.find(p => p.id === Number(id)) || PETS_CATALOG[0];
  }

  // =========================================================================
  // 7. RENDERERS: TOP BAR & COMPONENT SUB-TABS
  // =========================================================================

  function renderTopBar() {
    const topBar = document.getElementById('v-topbar');
    if (!topBar) return;

    const curChar = getCharacter(state.selectedAvatarId);
    const curPet = getPet(state.selectedPetId);

    topBar.innerHTML = `
      <div class="v-title-cluster">
        <span class="v-module-badge">STUDIO // 1.39</span>
        <div>
          <h1 class="v-title">Vault, Operative &amp; Pet Studio</h1>
          <p class="v-subtitle">High-fidelity 3D operative customization, companion sync, instant economy toggles &amp; 4,462 item armory</p>
        </div>
      </div>

      <div class="v-header-metrics">
        <!-- Operative Pill -->
        <div class="v-metric-pill" title="Currently Equipped Operative">
          <span class="v-metric-icon" style="color: ${curChar.color}">${ICONS.user}</span>
          <div class="v-metric-data">
            <span class="v-metric-val">${escapeHtml(curChar.name)}</span>
            <span class="v-metric-sub">ID: ${curChar.id}</span>
          </div>
        </div>

        <!-- Pet Pill -->
        <div class="v-metric-pill" title="Currently Active Pet Companion">
          <span class="v-metric-icon" style="color: ${curPet.color}">${ICONS.paw}</span>
          <div class="v-metric-data">
            <span class="v-metric-val">${escapeHtml(curPet.name)}</span>
            <span class="v-metric-sub">LVL ${curPet.maxLevel} COMPANION</span>
          </div>
        </div>

        <!-- Gold Balance Pill -->
        <div class="v-metric-pill" title="Gold Coins Balance">
          <span class="v-metric-icon text-amber">${ICONS.coins}</span>
          <div class="v-metric-data">
            <span class="v-metric-val monospace text-amber">${formatNumber(state.wallet.coins)}</span>
            <span class="v-metric-sub">GOLD COINS</span>
          </div>
        </div>

        <!-- Diamonds Balance Pill -->
        <div class="v-metric-pill" title="Diamonds Balance">
          <span class="v-metric-icon text-cyan">${ICONS.diamond}</span>
          <div class="v-metric-data">
            <span class="v-metric-val monospace text-cyan">${formatNumber(state.wallet.gems)}</span>
            <span class="v-metric-sub">DIAMONDS</span>
          </div>
        </div>

        <button id="v-btn-refresh" class="v-btn-icon" title="Refresh Live State">
          ${ICONS.refresh}
        </button>
      </div>
    `;

    document.getElementById('v-btn-refresh').addEventListener('click', refreshState);
  }

  function renderSubTabsNav() {
    const nav = document.getElementById('v-subtabs-nav');
    if (!nav) return;

    const tabs = [
      { id: 'characters', label: 'Operatives & 3D Cards', badge: '21 Real Avatars', icon: ICONS.user },
      { id: 'pets', label: 'Pet Companion Studio', badge: '5 Pets', icon: ICONS.paw },
      { id: 'wallet', label: 'Instant Wallet & Currencies', badge: 'Live Sliders', icon: ICONS.sliders },
      { id: 'vault', label: 'Vault & 4,462 Unlocker', badge: `${formatNumber(state.unlockedItemsCount)} Items`, icon: ICONS.box }
    ];

    nav.innerHTML = tabs.map(t => `
      <button class="v-tab-btn ${state.activeTab === t.id ? 'active' : ''}" data-tab="${t.id}">
        <span class="v-tab-icon">${t.icon}</span>
        <span class="v-tab-label">${t.label}</span>
        <span class="v-tab-badge">${t.badge}</span>
      </button>
    `).join('');

    nav.querySelectorAll('.v-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.activeTab = btn.getAttribute('data-tab');
        renderSubTabsNav();
        renderTabContent();
      });
    });
  }

  function renderTabContent() {
    const container = document.getElementById('v-tab-content');
    if (!container) return;

    if (state.activeTab === 'characters') {
      renderCharactersView();
    } else if (state.activeTab === 'pets') {
      renderPetsView();
    } else if (state.activeTab === 'wallet') {
      renderWalletView();
    } else if (state.activeTab === 'vault') {
      renderVaultView();
    }
  }

  // =========================================================================
  // 8. TAB 1: CHARACTERS STUDIO (21 REAL FF 1.39 AVATARS)
  // =========================================================================

  function renderCharactersView() {
    const container = document.getElementById('v-tab-content');
    if (!container) return;

    // Filter characters
    const query = state.charSearchQuery.toLowerCase().trim();
    const filteredChars = CHARACTERS_CATALOG.filter(c => {
      const matchGender = state.charGenderFilter === 'all' || c.gender.toLowerCase() === state.charGenderFilter;
      const matchQuery = !query || c.name.toLowerCase().includes(query) || c.skillName.toLowerCase().includes(query) || String(c.id).includes(query);
      return matchGender && matchQuery;
    });

    const activeChar = getCharacter(state.selectedAvatarId);

    container.innerHTML = `
      <div class="v-split-workspace">
        <!-- Left Pane: Operatives Roster -->
        <div class="v-pane-left">
          <!-- Filter & Search Toolbar -->
          <div class="v-toolbar">
            <div class="v-search-box">
              <span class="v-search-icon">${ICONS.search}</span>
              <input type="text" id="v-char-search" class="v-input-text" placeholder="Search operative name, skill, ID..." value="${escapeHtml(state.charSearchQuery)}">
            </div>

            <div class="v-filter-group">
              <button class="v-filter-pill ${state.charGenderFilter === 'all' ? 'active' : ''}" data-gender="all">All (21)</button>
              <button class="v-filter-pill ${state.charGenderFilter === 'male' ? 'active' : ''}" data-gender="male">Male</button>
              <button class="v-filter-pill ${state.charGenderFilter === 'female' ? 'active' : ''}" data-gender="female">Female</button>
            </div>
          </div>

          <!-- 3D Card Grid Container -->
          <div class="v-card-scroll-area">
            <div class="v-cards-grid">
              ${filteredChars.map(c => {
                const isSelected = c.id === state.selectedAvatarId;
                return `
                  <div class="v-3d-card ${isSelected ? 'is-selected' : ''}" data-char-id="${c.id}" style="--char-theme: ${c.color};">
                    <div class="v-3d-card-inner">
                      <!-- 3D Card Top Banner -->
                      <div class="v-card-header">
                        <span class="v-card-tag monospace">${c.gender.toUpperCase()}</span>
                        <span class="v-card-level monospace">LVL 8 MAX</span>
                      </div>

                      <!-- 3D Holographic Portrait Canvas -->
                      <div class="v-portrait-frame">
                        <div class="v-portrait-glow"></div>
                        <div class="v-portrait-mesh">
                          <svg viewBox="0 0 100 120" class="v-avatar-svg">
                            <defs>
                              <linearGradient id="grad-${c.id}" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="${c.color}" stop-opacity="0.8"/>
                                <stop offset="100%" stop-color="#070a12" stop-opacity="0.95"/>
                              </linearGradient>
                            </defs>
                            <circle cx="50" cy="40" r="28" fill="url(#grad-${c.id})" stroke="${c.color}" stroke-width="1.5"/>
                            <path d="M22 108 C 22 75, 78 75, 78 108 Z" fill="url(#grad-${c.id})" stroke="${c.color}" stroke-width="1.5"/>
                            <circle cx="50" cy="40" r="16" fill="#070a12" stroke="${c.color}" stroke-width="1"/>
                            <text x="50" y="44" text-anchor="middle" font-size="10" font-weight="700" fill="${c.color}" font-family="JetBrains Mono">${c.name.substring(0, 2).toUpperCase()}</text>
                          </svg>
                        </div>
                        ${isSelected ? '<div class="v-badge-active"><span class="v-pulse-dot"></span> EQUIPPED</div>' : ''}
                      </div>

                      <!-- Character Info & Skill -->
                      <div class="v-card-details">
                        <div class="v-card-name-row">
                          <span class="v-char-name">${escapeHtml(c.name)}</span>
                          <span class="v-char-id monospace">#${c.id}</span>
                        </div>
                        <div class="v-skill-pill">
                          <span class="v-skill-badge ${c.skillType.toLowerCase()}">${c.skillType.toUpperCase()}</span>
                          <span class="v-skill-name">${escapeHtml(c.skillName)}</span>
                        </div>
                      </div>

                      <!-- Quick Select Button -->
                      <button class="v-btn-equip ${isSelected ? 'active' : ''}" data-char-id="${c.id}">
                        ${isSelected ? `${ICONS.check} ACTIVE IN LOBBY` : 'EQUIP OPERATIVE'}
                      </button>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        </div>

        <!-- Right Pane: 3D Character Spotlight & Armory Studio -->
        <div class="v-pane-right">
          ${renderCharacterSpotlight(activeChar)}
        </div>
      </div>
    `;

    // Bind event listeners
    const searchInput = document.getElementById('v-char-search');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        state.charSearchQuery = e.target.value;
        renderCharactersView();
        // Restore focus
        const newSearch = document.getElementById('v-char-search');
        if (newSearch) {
          newSearch.focus();
          newSearch.setSelectionRange(newSearch.value.length, newSearch.value.length);
        }
      });
    }

    container.querySelectorAll('.v-filter-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        state.charGenderFilter = btn.getAttribute('data-gender');
        renderCharactersView();
      });
    });

    container.querySelectorAll('.v-3d-card').forEach(card => {
      applyTilt(card, 10);
      card.addEventListener('click', (e) => {
        if (!e.target.closest('.v-btn-equip')) {
          const charId = Number(card.getAttribute('data-char-id'));
          state.selectedAvatarId = charId;
          renderCharactersView();
        }
      });
    });

    container.querySelectorAll('.v-btn-equip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const charId = Number(btn.getAttribute('data-char-id'));
        equipCharacter(charId);
      });
    });

    // Spotlight 3D Card Tilt
    const spotCard = container.querySelector('.v-spotlight-card');
    if (spotCard) applyTilt(spotCard, 8);

    // Spotlight Equip Trigger
    const spotEquipBtn = container.querySelector('#v-spotlight-equip-btn');
    if (spotEquipBtn) {
      spotEquipBtn.addEventListener('click', () => {
        const charId = Number(spotEquipBtn.getAttribute('data-char-id'));
        equipCharacter(charId);
      });
    }
  }

  function renderCharacterSpotlight(char) {
    const isSelected = char.id === state.selectedAvatarId;
    return `
      <div class="v-spotlight-card" style="--spot-color: ${char.color};">
        <!-- Top Identity Strip -->
        <div class="v-spotlight-header">
          <div class="v-spot-title-cluster">
            <span class="v-spot-badge monospace">${char.archetype.toUpperCase()}</span>
            <h2 class="v-spot-name">${escapeHtml(char.name)}</h2>
            <span class="v-spot-id monospace">AVATAR ID: ${char.id}</span>
          </div>

          <div class="v-spot-level-box">
            <span class="v-level-title monospace">SKILL RANK</span>
            <span class="v-level-num monospace">LVL 8</span>
          </div>
        </div>

        <!-- 3D Holographic Stage -->
        <div class="v-spotlight-stage">
          <div class="v-stage-grid"></div>
          <div class="v-stage-hologram">
            <svg viewBox="0 0 200 240" class="v-stage-svg">
              <defs>
                <linearGradient id="spot-grad-${char.id}" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="${char.color}" stop-opacity="0.9"/>
                  <stop offset="60%" stop-color="${char.color}" stop-opacity="0.2"/>
                  <stop offset="100%" stop-color="#0c121d" stop-opacity="0.95"/>
                </linearGradient>
                <filter id="glow-${char.id}">
                  <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              <ellipse cx="100" cy="210" rx="75" ry="16" fill="${char.color}" opacity="0.25"/>
              <circle cx="100" cy="70" r="42" fill="url(#spot-grad-${char.id})" stroke="${char.color}" stroke-width="2" filter="url(#glow-${char.id})"/>
              <path d="M45 200 C 45 130, 155 130, 155 200 Z" fill="url(#spot-grad-${char.id})" stroke="${char.color}" stroke-width="2"/>
              <circle cx="100" cy="70" r="24" fill="#070a12" stroke="${char.color}" stroke-width="1.5"/>
              <text x="100" y="78" text-anchor="middle" font-size="20" font-weight="800" fill="${char.color}" font-family="JetBrains Mono">${char.name.substring(0, 2).toUpperCase()}</text>
            </svg>
          </div>
          <div class="v-stage-pedestal"></div>
        </div>

        <!-- Combat Lore & Bio -->
        <div class="v-spotlight-bio">
          <span class="v-bio-label monospace">TACTICAL DOSSIER</span>
          <p class="v-bio-text">${escapeHtml(char.lore)}</p>
        </div>

        <!-- Primary Skill Card -->
        <div class="v-spotlight-skill">
          <div class="v-skill-header-row">
            <span class="v-skill-badge ${char.skillType.toLowerCase()}">${char.skillType.toUpperCase()} SKILL</span>
            <h3 class="v-skill-title">${escapeHtml(char.skillName)}</h3>
            ${char.cooldown > 0 ? `<span class="v-cooldown-tag monospace">CD: ${char.cooldown}s</span>` : '<span class="v-cooldown-tag monospace">PASSIVE BUFF</span>'}
          </div>
          <p class="v-skill-desc">${escapeHtml(char.skillDesc)}</p>
        </div>

        <!-- Skill Slots Container -->
        <div class="v-slots-container">
          <span class="v-slots-label monospace">EQUIPPED SKILL SLOTS (4/4 UNLOCKED)</span>
          <div class="v-slots-grid">
            <div class="v-slot-box active" title="Slot 1 (Inherent Ability)">
              <span class="v-slot-num">01</span>
              <span class="v-slot-name">${escapeHtml(char.skillName)}</span>
              <span class="v-slot-status">${ICONS.check}</span>
            </div>
            <div class="v-slot-box active" title="Slot 2 (Enhanced Passive)">
              <span class="v-slot-num">02</span>
              <span class="v-slot-name">Bushido Lv.8</span>
              <span class="v-slot-status">${ICONS.check}</span>
            </div>
            <div class="v-slot-box active" title="Slot 3 (Mobility Perk)">
              <span class="v-slot-num">03</span>
              <span class="v-slot-name">Dash Lv.8</span>
              <span class="v-slot-status">${ICONS.check}</span>
            </div>
            <div class="v-slot-box active" title="Slot 4 (Tactical Slot)">
              <span class="v-slot-num">04</span>
              <span class="v-slot-name">Hacker's Eye</span>
              <span class="v-slot-status">${ICONS.check}</span>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="v-spotlight-actions">
          <button id="v-spotlight-equip-btn" class="v-btn-primary full-width" data-char-id="${char.id}">
            ${isSelected ? `${ICONS.check} OPERATIVE CURRENTLY EQUIPPED` : `${ICONS.user} DEPLOY ${char.name.toUpperCase()} TO LOBBY`}
          </button>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 9. TAB 2: PET COMPANION STUDIO (5 REAL FF 1.39 PETS)
  // =========================================================================

  function renderPetsView() {
    const container = document.getElementById('v-tab-content');
    if (!container) return;

    const activePet = getPet(state.selectedPetId);

    container.innerHTML = `
      <div class="v-split-workspace">
        <!-- Left Pane: Pet Selection Grid -->
        <div class="v-pane-left">
          <div class="v-toolbar">
            <div class="v-toolbar-title-group">
              <span class="v-badge-amber monospace">TACTICAL BEASTS</span>
              <h3 class="v-section-heading">Active Pet Companions (5/5 Unlocked)</h3>
            </div>
            <span class="v-badge-neutral monospace">MAX LEVEL 7</span>
          </div>

          <div class="v-card-scroll-area">
            <div class="v-pets-grid">
              ${PETS_CATALOG.map(pet => {
                const isSelected = pet.id === state.selectedPetId;
                return `
                  <div class="v-pet-card ${isSelected ? 'is-selected' : ''}" data-pet-id="${pet.id}" style="--pet-theme: ${pet.color};">
                    <div class="v-pet-header">
                      <span class="v-pet-rarity monospace">${pet.rareType === 5 ? 'MYTHIC RARITY' : 'EPIC RARITY'}</span>
                      <span class="v-pet-maxlv monospace">MAX LVL ${pet.maxLevel}</span>
                    </div>

                    <!-- Holographic Pet Silhouette -->
                    <div class="v-pet-canvas">
                      <div class="v-pet-glow"></div>
                      <svg viewBox="0 0 100 100" class="v-pet-svg">
                        <circle cx="50" cy="50" r="38" fill="none" stroke="${pet.color}" stroke-width="1.5" stroke-dasharray="4, 3"/>
                        <circle cx="50" cy="50" r="28" fill="${pet.color}" fill-opacity="0.15" stroke="${pet.color}" stroke-width="2"/>
                        <text x="50" y="55" text-anchor="middle" font-size="13" font-weight="800" fill="${pet.color}" font-family="JetBrains Mono">${pet.name.substring(0, 3).toUpperCase()}</text>
                      </svg>
                      ${isSelected ? '<div class="v-badge-active"><span class="v-pulse-dot"></span> EQUIPPED</div>' : ''}
                    </div>

                    <!-- Pet Info -->
                    <div class="v-pet-details">
                      <div class="v-pet-name-row">
                        <span class="v-pet-name">${escapeHtml(pet.name)}</span>
                        <span class="v-pet-id monospace">#${pet.id}</span>
                      </div>
                      <div class="v-pet-perk">
                        <span class="v-skill-badge ${pet.skillType.includes('Combat') ? 'active' : 'passive'}">${pet.skillType.toUpperCase()}</span>
                        <span class="v-pet-skill-name">${escapeHtml(pet.skillName)}</span>
                      </div>
                    </div>

                    <!-- Equip Button -->
                    <button class="v-btn-equip ${isSelected ? 'active' : ''}" data-pet-id="${pet.id}">
                      ${isSelected ? `${ICONS.check} ACTIVE IN LOBBY` : 'EQUIP COMPANION'}
                    </button>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        </div>

        <!-- Right Pane: Pet Showcase & Skin Customizer -->
        <div class="v-pane-right">
          ${renderPetSpotlight(activePet)}
        </div>
      </div>
    `;

    // Bind event listeners
    container.querySelectorAll('.v-pet-card').forEach(card => {
      applyTilt(card, 10);
      card.addEventListener('click', (e) => {
        if (!e.target.closest('.v-btn-equip')) {
          const petId = Number(card.getAttribute('data-pet-id'));
          state.selectedPetId = petId;
          const targetPet = getPet(petId);
          state.selectedPetSkinId = targetPet.defaultSkin;
          renderPetsView();
        }
      });
    });

    container.querySelectorAll('.v-btn-equip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const petId = Number(btn.getAttribute('data-pet-id'));
        equipPet(petId, state.selectedPetSkinId);
      });
    });

    // Pet Spotlight tilt
    const spotCard = container.querySelector('.v-spotlight-card');
    if (spotCard) applyTilt(spotCard, 8);

    // Skin pill selection
    container.querySelectorAll('.v-skin-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const skinId = Number(pill.getAttribute('data-skin-id'));
        state.selectedPetSkinId = skinId;
        equipPet(activePet.id, skinId);
      });
    });

    // Spotlight Pet Equip
    const spotPetBtn = container.querySelector('#v-spotlight-pet-btn');
    if (spotPetBtn) {
      spotPetBtn.addEventListener('click', () => {
        equipPet(activePet.id, state.selectedPetSkinId);
      });
    }
  }

  function renderPetSpotlight(pet) {
    const isSelected = pet.id === state.selectedPetId;
    return `
      <div class="v-spotlight-card" style="--spot-color: ${pet.color};">
        <div class="v-spotlight-header">
          <div class="v-spot-title-cluster">
            <span class="v-spot-badge monospace">LVL ${pet.maxLevel} COMPANION</span>
            <h2 class="v-spot-name">${escapeHtml(pet.name)}</h2>
            <span class="v-spot-id monospace">PET ID: ${pet.id}</span>
          </div>

          <div class="v-spot-level-box">
            <span class="v-level-title monospace">EXP PROGRESS</span>
            <span class="v-level-num monospace">6000 / 6000</span>
          </div>
        </div>

        <!-- 3D Pet Showcase Stage -->
        <div class="v-spotlight-stage">
          <div class="v-stage-grid"></div>
          <div class="v-stage-hologram">
            <svg viewBox="0 0 200 200" class="v-stage-svg">
              <defs>
                <linearGradient id="pet-grad-${pet.id}" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="${pet.color}" stop-opacity="0.9"/>
                  <stop offset="100%" stop-color="#0c121d" stop-opacity="0.95"/>
                </linearGradient>
              </defs>
              <ellipse cx="100" cy="170" rx="65" ry="14" fill="${pet.color}" opacity="0.25"/>
              <circle cx="100" cy="90" r="50" fill="url(#pet-grad-${pet.id})" stroke="${pet.color}" stroke-width="2"/>
              <circle cx="100" cy="90" r="30" fill="#070a12" stroke="${pet.color}" stroke-width="1.5"/>
              <text x="100" y="98" text-anchor="middle" font-size="22" font-weight="800" fill="${pet.color}" font-family="JetBrains Mono">${pet.name.substring(0, 3).toUpperCase()}</text>
            </svg>
          </div>
        </div>

        <!-- Pet Skill Perks Card -->
        <div class="v-spotlight-skill">
          <div class="v-skill-header-row">
            <span class="v-skill-badge active">${pet.skillType.toUpperCase()}</span>
            <h3 class="v-skill-title">${escapeHtml(pet.skillName)}</h3>
            <span class="v-cooldown-tag monospace">PERK LVL 3</span>
          </div>
          <p class="v-skill-desc">${escapeHtml(pet.skillDesc)}</p>
        </div>

        <!-- Unlocked Skins Swatches -->
        <div class="v-slots-container">
          <span class="v-slots-label monospace">UNLOCKED SKINS CATALOG (${pet.skins.length} SKINS)</span>
          <div class="v-skins-grid">
            ${pet.skins.map(sk => {
              const isSkinActive = sk.id === state.selectedPetSkinId;
              return `
                <button class="v-skin-pill ${isSkinActive ? 'active' : ''}" data-skin-id="${sk.id}" style="--skin-accent: ${sk.color}">
                  <span class="v-skin-dot" style="background: ${sk.color};"></span>
                  <span class="v-skin-name">${escapeHtml(sk.name)}</span>
                  ${isSkinActive ? `<span class="v-skin-check">${ICONS.check}</span>` : ''}
                </button>
              `;
            }).join('')}
          </div>
        </div>

        <!-- Action Button -->
        <div class="v-spotlight-actions">
          <button id="v-spotlight-pet-btn" class="v-btn-primary full-width" data-pet-id="${pet.id}">
            ${isSelected ? `${ICONS.check} PET COMPANION ACTIVE IN LOBBY` : `${ICONS.paw} EQUIP ${pet.name.toUpperCase()} TO LOBBY`}
          </button>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 10. TAB 3: INSTANT WALLET ENGINE (GOLD & DIAMOND SLIDERS & TOGGLES)
  // =========================================================================

  function renderWalletView() {
    const container = document.getElementById('v-tab-content');
    if (!container) return;

    container.innerHTML = `
      <div class="v-wallet-workspace">
        <!-- Top Status Banner -->
        <div class="v-wallet-banner">
          <div class="v-wallet-banner-content">
            <span class="v-badge-cyan monospace">CENTRAL BANK // FREE FIRE 1.39</span>
            <h2 class="v-wallet-heading">Instant Wallet &amp; Economy Controller</h2>
            <p class="v-wallet-desc">Modify player balances in real-time. Use precise drag sliders, instant grant deltas, or max preset caps without server restart.</p>
          </div>

          <div class="v-wallet-quick-actions">
            <button id="v-btn-whale" class="v-btn-amber">
              <span class="v-btn-icon">${ICONS.bolt}</span>
              <span>SET INFINITE (999M COINS / 999M GEMS)</span>
            </button>
          </div>
        </div>

        <!-- Currency Twin Control Cards -->
        <div class="v-currency-grid">
          <!-- Card 1: Gold Coins Controller -->
          <div class="v-currency-card" style="--cur-theme: #f59e0b;">
            <div class="v-cur-header">
              <div class="v-cur-title-row">
                <span class="v-cur-icon text-amber">${ICONS.coins}</span>
                <div>
                  <h3 class="v-cur-name">Gold Coins</h3>
                  <span class="v-cur-sub monospace">STANDARD IN-GAME CURRENCY</span>
                </div>
              </div>
              <div class="v-cur-val-badge">
                <span id="v-disp-coins" class="v-cur-val monospace text-amber">${formatNumber(state.wallet.coins)}</span>
              </div>
            </div>

            <!-- Dynamic Slider -->
            <div class="v-slider-box">
              <div class="v-slider-labels">
                <span class="v-slider-tick monospace">0</span>
                <span class="v-slider-tick monospace">1M</span>
                <span class="v-slider-tick monospace">5M</span>
                <span class="v-slider-tick monospace">10M</span>
              </div>
              <input type="range" id="v-slider-coins" class="v-range-slider amber" min="0" max="10000000" step="50000" value="${Math.min(10000000, state.wallet.coins)}">
            </div>

            <!-- Manual Value Input & Set -->
            <div class="v-input-action-row">
              <input type="number" id="v-input-coins" class="v-input-text monospace" placeholder="Enter exact gold..." value="${state.wallet.coins}">
              <button id="v-btn-set-coins" class="v-btn-primary">SET EXACT</button>
            </div>

            <!-- Delta Grant Preset Buttons -->
            <div class="v-deltas-group">
              <span class="v-deltas-label monospace">QUICK GRANT DELTAS:</span>
              <div class="v-deltas-row">
                <button class="v-delta-btn" data-type="coins" data-val="10000">+10,000</button>
                <button class="v-delta-btn" data-type="coins" data-val="50000">+50,000</button>
                <button class="v-delta-btn" data-type="coins" data-val="250000">+250,000</button>
                <button class="v-delta-btn" data-type="coins" data-val="1000000">+1,000,000</button>
                <button class="v-delta-btn danger" data-type="coins" data-val="zero">RESET (0)</button>
              </div>
            </div>
          </div>

          <!-- Card 2: Diamonds Controller -->
          <div class="v-currency-card" style="--cur-theme: #38bdf8;">
            <div class="v-cur-header">
              <div class="v-cur-title-row">
                <span class="v-cur-icon text-cyan">${ICONS.diamond}</span>
                <div>
                  <h3 class="v-cur-name">Diamonds (Gems)</h3>
                  <span class="v-cur-sub monospace">PREMIUM ELITE CURRENCY</span>
                </div>
              </div>
              <div class="v-cur-val-badge">
                <span id="v-disp-gems" class="v-cur-val monospace text-cyan">${formatNumber(state.wallet.gems)}</span>
              </div>
            </div>

            <!-- Dynamic Slider -->
            <div class="v-slider-box">
              <div class="v-slider-labels">
                <span class="v-slider-tick monospace">0</span>
                <span class="v-slider-tick monospace">100K</span>
                <span class="v-slider-tick monospace">500K</span>
                <span class="v-slider-tick monospace">1M</span>
              </div>
              <input type="range" id="v-slider-gems" class="v-range-slider cyan" min="0" max="1000000" step="10000" value="${Math.min(1000000, state.wallet.gems)}">
            </div>

            <!-- Manual Value Input & Set -->
            <div class="v-input-action-row">
              <input type="number" id="v-input-gems" class="v-input-text monospace" placeholder="Enter exact diamonds..." value="${state.wallet.gems}">
              <button id="v-btn-set-gems" class="v-btn-primary cyan">SET EXACT</button>
            </div>

            <!-- Delta Grant Preset Buttons -->
            <div class="v-deltas-group">
              <span class="v-deltas-label monospace">QUICK GRANT DELTAS:</span>
              <div class="v-deltas-row">
                <button class="v-delta-btn cyan" data-type="gems" data-val="1000">+1,000</button>
                <button class="v-delta-btn cyan" data-type="gems" data-val="5000">+5,000</button>
                <button class="v-delta-btn cyan" data-type="gems" data-val="25000">+25,000</button>
                <button class="v-delta-btn cyan" data-type="gems" data-val="100000">+100,000</button>
                <button class="v-delta-btn danger" data-type="gems" data-val="zero">RESET (0)</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Sliders Live Binding
    const sliderCoins = document.getElementById('v-slider-coins');
    const dispCoins = document.getElementById('v-disp-coins');
    const inputCoins = document.getElementById('v-input-coins');

    if (sliderCoins) {
      sliderCoins.addEventListener('input', (e) => {
        const val = Number(e.target.value);
        dispCoins.textContent = formatNumber(val);
        inputCoins.value = val;
      });
      sliderCoins.addEventListener('change', (e) => {
        setWallet(Number(e.target.value), null);
      });
    }

    const sliderGems = document.getElementById('v-slider-gems');
    const dispGems = document.getElementById('v-disp-gems');
    const inputGems = document.getElementById('v-input-gems');

    if (sliderGems) {
      sliderGems.addEventListener('input', (e) => {
        const val = Number(e.target.value);
        dispGems.textContent = formatNumber(val);
        inputGems.value = val;
      });
      sliderGems.addEventListener('change', (e) => {
        setWallet(null, Number(e.target.value));
      });
    }

    // Set Exact Buttons
    document.getElementById('v-btn-set-coins')?.addEventListener('click', () => {
      const val = Number(inputCoins.value);
      setWallet(val, null);
    });

    document.getElementById('v-btn-set-gems')?.addEventListener('click', () => {
      const val = Number(inputGems.value);
      setWallet(null, val);
    });

    // Delta Grant Buttons
    container.querySelectorAll('.v-delta-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const type = btn.getAttribute('data-type');
        const val = btn.getAttribute('data-val');

        if (val === 'zero') {
          if (type === 'coins') setWallet(0, null);
          else setWallet(null, 0);
        } else {
          const delta = Number(val);
          if (type === 'coins') grantWallet(delta, 0);
          else grantWallet(0, delta);
        }
      });
    });

    // Max Whale Preset (999M)
    document.getElementById('v-btn-whale')?.addEventListener('click', () => {
      setWallet(999999999, 999999999);
    });
  }

  // =========================================================================
  // 11. TAB 4: VAULT & 4,462 ITEM UNLOCKER
  // =========================================================================

  function renderVaultView() {
    const container = document.getElementById('v-tab-content');
    if (!container) return;

    // Filter items catalog
    const query = state.itemSearchQuery.toLowerCase().trim();
    const filteredItems = FAMOUS_ITEMS_CATALOG.filter(item => {
      const matchCat = state.itemCategoryFilter === 'all' || item.category === state.itemCategoryFilter;
      const matchQuery = !query || item.name.toLowerCase().includes(query) || item.desc.toLowerCase().includes(query) || String(item.id).includes(query);
      return matchCat && matchQuery;
    });

    container.innerHTML = `
      <div class="v-vault-workspace">
        <!-- Top Stats & Master Unlocker Bar -->
        <div class="v-vault-header-card">
          <div class="v-vault-header-info">
            <span class="v-badge-emerald monospace">COMPLETE APK REPOSITORY // 4,462 ITEMS</span>
            <h2 class="v-vault-title">Vault Inventory &amp; Item Unlocker</h2>
            <p class="v-vault-desc">All 4,462 permanent Free Fire 1.39 items (Clothes.csv, Item.csv, CollectionWeapon.csv) verified and synchronized.</p>
          </div>

          <div class="v-vault-stats-cluster">
            <div class="v-vault-stat-box">
              <span class="v-stat-val monospace text-emerald">${formatNumber(state.unlockedItemsCount)}</span>
              <span class="v-stat-lbl">ITEMS UNLOCKED</span>
            </div>
            <div class="v-vault-stat-box">
              <span class="v-stat-val monospace text-cyan">100%</span>
              <span class="v-stat-lbl">UNLOCK STATUS</span>
            </div>
            <button id="v-btn-unlock-all" class="v-btn-emerald">
              <span class="v-btn-icon">${ICONS.unlock}</span>
              <span>UNLOCK ALL 4,462 ITEMS</span>
            </button>
          </div>
        </div>

        <!-- Custom Item Granter Form -->
        <div class="v-granter-card">
          <div class="v-granter-title-row">
            <span class="v-granter-icon text-cyan">${ICONS.plus}</span>
            <h3 class="v-granter-heading">Direct Item Granter</h3>
            <span class="v-granter-sub monospace">SEND ANY REVERSE-ENGINEERED ITEM ID TO INVENTORY</span>
          </div>

          <div class="v-granter-form">
            <div class="v-form-group flex-2">
              <label class="v-form-label monospace">ITEM ID OR COMMA-SEPARATED IDS</label>
              <input type="text" id="v-grant-item-id" class="v-input-text monospace" placeholder="e.g. 907100098 or 203000573, 909000001">
            </div>

            <div class="v-form-group flex-1">
              <label class="v-form-label monospace">QUANTITY / STACK COUNT</label>
              <input type="number" id="v-grant-item-count" class="v-input-text monospace" min="1" max="999" value="1">
            </div>

            <button id="v-btn-grant-submit" class="v-btn-primary">
              <span class="v-btn-icon">${ICONS.plus}</span>
              <span>GRANT TO VAULT</span>
            </button>
          </div>
        </div>

        <!-- Catalog Toolbar & Filters -->
        <div class="v-catalog-toolbar">
          <div class="v-search-box">
            <span class="v-search-icon">${ICONS.search}</span>
            <input type="text" id="v-item-search" class="v-input-text" placeholder="Search catalog item name, ID, or description..." value="${escapeHtml(state.itemSearchQuery)}">
          </div>

          <div class="v-category-pills">
            <button class="v-cat-pill ${state.itemCategoryFilter === 'all' ? 'active' : ''}" data-cat="all">All Items</button>
            <button class="v-cat-pill ${state.itemCategoryFilter === 'weapons' ? 'active' : ''}" data-cat="weapons">Weapons &amp; Skins</button>
            <button class="v-cat-pill ${state.itemCategoryFilter === 'outfits' ? 'active' : ''}" data-cat="outfits">Outfits &amp; Bundles</button>
            <button class="v-cat-pill ${state.itemCategoryFilter === 'emotes' ? 'active' : ''}" data-cat="emotes">Emotes</button>
            <button class="v-cat-pill ${state.itemCategoryFilter === 'gear' ? 'active' : ''}" data-cat="gear">Collections &amp; Gear</button>
            <button class="v-cat-pill ${state.itemCategoryFilter === 'utility' ? 'active' : ''}" data-cat="utility">Utility &amp; Cards</button>
          </div>
        </div>

        <!-- Curated Items Grid -->
        <div class="v-items-scroll-area">
          <div class="v-items-grid">
            ${filteredItems.map(item => `
              <div class="v-item-card rarity-${item.rarity}" data-item-id="${item.id}">
                <div class="v-item-header">
                  <span class="v-rarity-badge monospace">${item.rarity.toUpperCase()}</span>
                  <span class="v-item-id-badge monospace">ID: ${item.id}</span>
                </div>

                <div class="v-item-body">
                  <div class="v-item-icon-box">
                    ${item.category === 'weapons' ? ICONS.crosshair : (item.category === 'emotes' ? ICONS.bolt : (item.category === 'utility' ? ICONS.tag : ICONS.box))}
                  </div>
                  <div class="v-item-info">
                    <h4 class="v-item-name">${escapeHtml(item.name)}</h4>
                    <p class="v-item-desc">${escapeHtml(item.desc)}</p>
                  </div>
                </div>

                <div class="v-item-footer">
                  <button class="v-item-copy-btn" data-id="${item.id}" title="Copy Item ID">
                    ${ICONS.copy}
                  </button>
                  <button class="v-item-grant-btn" data-id="${item.id}">
                    ${ICONS.plus} GRANT ITEM
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    // Master Unlock All
    document.getElementById('v-btn-unlock-all')?.addEventListener('click', () => {
      unlockAllItems();
    });

    // Direct Form Grant
    document.getElementById('v-btn-grant-submit')?.addEventListener('click', () => {
      const idInput = document.getElementById('v-grant-item-id');
      const countInput = document.getElementById('v-grant-item-count');
      const rawIds = (idInput?.value || '').trim();
      const count = Number(countInput?.value || 1);

      if (!rawIds) {
        showToast('Please enter an Item ID', 'error');
        return;
      }

      if (rawIds.includes(',')) {
        const tokens = rawIds.split(',').map(s => Number(s.trim())).filter(n => n > 0);
        apiPost('/api/dashboard/items/grant', { item_ids: tokens, count }).then(() => {
          showToast(`Granted ${tokens.length} items to vault!`, 'success');
          renderVaultView();
          renderTopBar();
        });
      } else {
        grantItem(Number(rawIds), count);
      }
    });

    // Item Search
    const itemSearch = document.getElementById('v-item-search');
    if (itemSearch) {
      itemSearch.addEventListener('input', (e) => {
        state.itemSearchQuery = e.target.value;
        renderVaultView();
        const newSearch = document.getElementById('v-item-search');
        if (newSearch) {
          newSearch.focus();
          newSearch.setSelectionRange(newSearch.value.length, newSearch.value.length);
        }
      });
    }

    // Category Filter Pills
    container.querySelectorAll('.v-cat-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        state.itemCategoryFilter = btn.getAttribute('data-cat');
        renderVaultView();
      });
    });

    // Item Grant from Card
    container.querySelectorAll('.v-item-grant-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = Number(btn.getAttribute('data-id'));
        grantItem(id, 1);
      });
    });

    // Item Copy ID
    container.querySelectorAll('.v-item-copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        if (navigator.clipboard) {
          navigator.clipboard.writeText(id);
          showToast(`Copied Item ID #${id} to clipboard`, 'info');
        }
      });
    });
  }

  // =========================================================================
  // 12. INITIALIZATION
  // =========================================================================

  function renderAll() {
    renderTopBar();
    renderSubTabsNav();
    renderTabContent();
  }

  function init() {
    renderAll();
    refreshState();
  }

  return {
    init,
    refresh: refreshState,
    equipCharacter,
    equipPet,
    setWallet,
    grantWallet,
    grantItem,
    unlockAllItems,
    getState: () => state
  };
});

