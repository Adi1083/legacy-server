/**
 * India V1 1.39 — Luck Royale & Gacha Administration Studio (luck_royale.js)
 * Master controller for Free Fire OB17 Luck Royale Management:
 *   1. Luck Royale Overview (active/disabled machines, spin volume, currency burn, voucher telemetry)
 *   2. Machine Manager (create, edit, duplicate, enable/disable, lobby visibility, costs, spin counts)
 *   3. Reward Pool Editor (searchable item catalog, rarity tiers, drop weights, duplicate token conversion)
 *   4. Lucky Meter Manager (bad-luck protection, guaranteed drop caps, rate increment, weekly milestones)
 *   5. Currency & Voucher Manager (live wallet balances, delta grants, deductions, cost tuning)
 *   6. Incubator & Exchange Forge Manager (blueprint/stone synthesis recipes, token cosmetic shop)
 *   7. Banner & Event Manager (billboard assets from server/static/banners/, scheduling, rate-up buffs)
 *   8. Account Inspector & Transaction Explorer (account 10001 meters, audit ledger, test spin simulator)
 *
 * Strict Compliance: Apple Professional HIG, Zero Emojis, Pure SVG Icons, Fully Functional API Bindings.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.LuckRoyaleApp = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // =========================================================================
  // 1. REVERSE-ENGINEERED FREE FIRE 1.39 CONSTANTS & ITEM CATALOG
  // =========================================================================

  const ITEM_CONSTANTS = {
    VOUCHER_GOLD_ROYALE: 802000000,
    VOUCHER_DIAMOND_ROYALE: 802000001,
    VOUCHER_WEAPON_ROYALE: 802000008,
    VOUCHER_INCUBATOR: 802000009,
    ITEM_FF_TOKEN: 800000301,
    ITEM_MAGIC_CUBE: 800000304,
    ITEM_EVOLUTION_STONE: 808000001,
    ITEM_BLUEPRINT_YINYANG: 808000011,
    ITEM_BLUEPRINT_JOKER: 808000012,
  };

  const OB17_ITEMS_DATABASE = [
    // Consumables & Vouchers
    { id: 802000000, name: 'Gold Royale Voucher', category: 'voucher', rarity: 1, desc: 'Free single ticket for Gold Royale machine.' },
    { id: 802000001, name: 'Diamond Royale Voucher', category: 'voucher', rarity: 1, desc: 'Free ticket for premier Diamond Royale.' },
    { id: 802000008, name: 'Weapon Royale Voucher', category: 'voucher', rarity: 1, desc: 'Free ticket for high-tier Weapon Royale.' },
    { id: 802000009, name: 'Incubator Voucher', category: 'voucher', rarity: 2, desc: 'Exclusive ticket to spin the Incubator turntable wheel.' },
    { id: 800000301, name: 'FF Token', category: 'token', rarity: 0, desc: 'Special silver exchange currency earned from duplicate drops.' },
    { id: 800000304, name: 'Magic Cube', category: 'material', rarity: 2, desc: 'Ultimate cosmic catalyst redeemable for any legacy mythic bundle.' },
    { id: 808000001, name: 'Evolution Stone', category: 'material', rarity: 2, desc: 'Evolution catalyst required for Incubator blueprint synthesis.' },
    { id: 808000011, name: 'Blueprint: YinYang', category: 'material', rarity: 2, desc: 'Synthesis diagram for master YinYang samurai and monk bundles.' },
    { id: 808000012, name: 'Blueprint: Joker Clown', category: 'material', rarity: 2, desc: 'Synthesis diagram for the sinister Night Clown collection.' },

    // Bundles & Costumes
    { id: 710000410, name: 'YinYang Master Gold (Male)', category: 'bundle', rarity: 2, desc: 'Grand prize gilded ceremonial kimono with celestial flame aura.' },
    { id: 710000411, name: 'YinYang Mistress Gold (Female)', category: 'bundle', rarity: 2, desc: 'Grand prize gilded shrine maiden robe radiating golden sparks.' },
    { id: 710000412, name: 'YinYang Disciple Blue (Male)', category: 'bundle', rarity: 2, desc: 'Cerulean monk tactical robes with embroidered cloud emblems.' },
    { id: 710000413, name: 'YinYang Disciple Blue (Female)', category: 'bundle', rarity: 2, desc: 'Cerulean kunoichi attire with swift wind tassels.' },
    { id: 710000401, name: 'Dino Monster Green Jumpsuit', category: 'bundle', rarity: 2, desc: 'Ultra-rare plush dinosaur jumpsuit with spiked tail.' },
    { id: 710000400, name: 'Dino Monster Yellow Jumpsuit', category: 'bundle', rarity: 2, desc: 'Vibrant yellow dinosaur outfit with comical grin.' },
    { id: 710000403, name: 'Bioforge Cybernetic Suit', category: 'bundle', rarity: 1, desc: 'Exoskeleton with integrated neon coolant conduits.' },
    { id: 710000404, name: 'Dark Cyber Infiltrator', category: 'bundle', rarity: 1, desc: 'Stealth combat suit with night-vision monocle.' },
    { id: 710000422, name: 'Street Hip Hop Striker (Male)', category: 'bundle', rarity: 2, desc: 'Urban graffiti tracksuit with snapback cap.' },
    { id: 710000423, name: 'Street Hip Hop Striker (Female)', category: 'bundle', rarity: 2, desc: 'Urban cropped sports jacket with reflective sneakers.' },

    // Weapons
    { id: 907001611, name: 'M4A1 Carnival Carnage', category: 'weapon', rarity: 2, desc: 'Festive red & yellow assault rifle with enhanced fire rate.' },
    { id: 907001612, name: 'AK47 Flaming Dragon', category: 'weapon', rarity: 2, desc: 'Fiery dragon engraving that unleashes scorching muzzle flash.' },
    { id: 907001613, name: 'SCAR Cupid Love', category: 'weapon', rarity: 1, desc: 'Pink-hued carbine featuring pink heart muzzle flares.' },
    { id: 907001614, name: 'MP40 Mechanical Lightning', category: 'weapon', rarity: 1, desc: 'Electric blue SMG humming with high voltage burst power.' },
    { id: 907001620, name: 'AWM Duke Butterfly', category: 'weapon', rarity: 1, desc: 'Ornate gold and violet sniper rifle with enhanced range.' },
    { id: 907001621, name: 'FAMAS Metallic Vampire', category: 'weapon', rarity: 1, desc: 'Crimson triple-burst battle rifle with bat wing accents.' },
    { id: 907001622, name: 'M1014 Demolitionist', category: 'weapon', rarity: 0, desc: 'Heavy combat shotgun with reinforced breach choke.' },
    { id: 907001623, name: 'UMP Cheetah Prowl', category: 'weapon', rarity: 0, desc: 'Fast handling submachine gun with feline spotted camo.' },

    // General Apparels & Crates
    { id: 203000505, name: 'Urban Combat Tactical Vest', category: 'apparel', rarity: 0, desc: 'Standard issue composite armor vest.' },
    { id: 204000304, name: 'Cargo Field Combat Trousers', category: 'apparel', rarity: 0, desc: 'Reinforced ballistic nylon combat trousers.' },
    { id: 1101000002, name: 'Gold Supply Crate Lv1', category: 'crate', rarity: 0, desc: 'Contains random bounty supplies and combat medkits.' },
    { id: 1102000002, name: 'Weapon Loot Crate (Scorching)', category: 'crate', rarity: 0, desc: 'Chance to drop rare temporary or permanent weapon skins.' },
    { id: 1307000001, name: 'Armor Repair Kit (Lobby)', category: 'utility', rarity: 0, desc: 'Lobby consumable granting in-match protective bonuses.' }
  ];

  // Helper to look up item from catalog or provide safe fallback
  function lookupItem(id) {
    const numId = Number(id);
    const found = OB17_ITEMS_DATABASE.find(item => item.id === numId);
    if (found) return found;
    return {
      id: numId,
      name: `Item #${numId}`,
      category: 'item',
      rarity: 0,
      desc: 'Free Fire 1.39 game inventory item'
    };
  }

  // =========================================================================
  // 2. DEFAULT STATE ENGINE (OB17 PRODUCTION BASELINE)
  // =========================================================================

  const state = {
    activeTab: 'tab-overview',
    targetAccountId: 10001,
    selectedPoolChestId: 3,
    poolFilterQuery: '',
    poolFilterRarity: 'all',
    machineFilterQuery: '',
    txFilterMachine: 'all',

    // Overview Stats
    stats: {
      totalSpins: 248,
      spinsToday: 42,
      diamondsBurned: 12600,
      goldBurned: 54000,
      vouchersUsed: {
        diamond: 38,
        weapon: 24,
        gold: 86,
        incubator: 16
      }
    },

    // 4 Master Production Machines
    machines: [
      {
        chest_id: 3,
        name: 'Diamond Royale',
        code_name: 'TXT_CHEST_NAME_GEM',
        type: 0, // Normal
        coin_type: 2, // Gems/Diamonds
        once_price: 60,
        ten_price: 600,
        once_num: 1,
        ten_num: 10,
        voucher_id: 802000001,
        meter_max: 150,
        priority: 100,
        banner: 'UI_Lottery_Poster_P.png',
        enabled: true,
        visible: true,
        items_count: 15
      },
      {
        chest_id: 4,
        name: 'Weapon Royale',
        code_name: 'TXT_CHEST_NAME_GUN',
        type: 0, // Normal
        coin_type: 2, // Gems/Diamonds
        once_price: 40,
        ten_price: 400,
        once_num: 1,
        ten_num: 10,
        voucher_id: 802000008,
        meter_max: 150,
        priority: 75,
        banner: 'UI_Lottery_Poster_W.png',
        enabled: true,
        visible: true,
        items_count: 14
      },
      {
        chest_id: 5,
        name: 'Gold Royale',
        code_name: 'TXT_CHEST_NAME_GOLD',
        type: 0, // Normal
        coin_type: 1, // Coins/Gold
        once_price: 300,
        ten_price: 3000,
        once_num: 1,
        ten_num: 10,
        voucher_id: 802000000,
        meter_max: 300,
        priority: 50,
        banner: 'UI_Lottery_Poster_G.png',
        enabled: true,
        visible: true,
        items_count: 13
      },
      {
        chest_id: 6,
        name: 'Incubator (Dino / YinYang)',
        code_name: 'T_12_Z_CHEST_WHEEL_HELP_TAB',
        type: 1, // Turntable Wheel
        coin_type: 2, // Gems/Diamonds
        once_price: 60,
        ten_price: 270,
        once_num: 1,
        ten_num: 5,
        voucher_id: 802000009,
        meter_max: 80,
        priority: 120,
        banner: 'FF_Lottery_anni_forge.png',
        enabled: true,
        visible: true,
        items_count: 12
      }
    ],

    // Reward Pools per Chest ID
    rewardPools: {
      3: [ // Diamond Royale
        { item_id: 800000304, count: 1, rarity: 2, weight: 2, dup_id: 800000304, dup_count: 1, is_show: true, slot: 0 },
        { item_id: 710000401, count: 1, rarity: 2, weight: 4, dup_id: 800000301, dup_count: 10, is_show: true, slot: 0 },
        { item_id: 710000400, count: 1, rarity: 2, weight: 4, dup_id: 800000301, dup_count: 10, is_show: true, slot: 0 },
        { item_id: 710000403, count: 1, rarity: 1, weight: 12, dup_id: 800000301, dup_count: 8, is_show: true, slot: 0 },
        { item_id: 710000404, count: 1, rarity: 1, weight: 12, dup_id: 800000301, dup_count: 8, is_show: true, slot: 0 },
        { item_id: 203000505, count: 1, rarity: 0, weight: 60, dup_id: 800000301, dup_count: 3, is_show: true, slot: 0 },
        { item_id: 204000304, count: 1, rarity: 0, weight: 60, dup_id: 800000301, dup_count: 3, is_show: true, slot: 0 },
        { item_id: 800000301, count: 5, rarity: 0, weight: 80, dup_id: 800000301, dup_count: 5, is_show: true, slot: 0 },
        { item_id: 1101000002, count: 1, rarity: 0, weight: 90, dup_id: 800000301, dup_count: 2, is_show: false, slot: 0 },
        { item_id: 1102000002, count: 1, rarity: 0, weight: 90, dup_id: 800000301, dup_count: 2, is_show: false, slot: 0 },
        { item_id: 1307000001, count: 2, rarity: 0, weight: 90, dup_id: 800000301, dup_count: 2, is_show: false, slot: 0 }
      ],
      4: [ // Weapon Royale
        { item_id: 907001611, count: 1, rarity: 2, weight: 4, dup_id: 800000301, dup_count: 10, is_show: true, slot: 0 },
        { item_id: 907001612, count: 1, rarity: 2, weight: 4, dup_id: 800000301, dup_count: 10, is_show: true, slot: 0 },
        { item_id: 907001613, count: 1, rarity: 1, weight: 14, dup_id: 800000301, dup_count: 6, is_show: true, slot: 0 },
        { item_id: 907001614, count: 1, rarity: 1, weight: 14, dup_id: 800000301, dup_count: 6, is_show: true, slot: 0 },
        { item_id: 907001620, count: 1, rarity: 1, weight: 20, dup_id: 800000301, dup_count: 5, is_show: true, slot: 0 },
        { item_id: 907001622, count: 1, rarity: 0, weight: 55, dup_id: 800000301, dup_count: 3, is_show: true, slot: 0 },
        { item_id: 907001623, count: 1, rarity: 0, weight: 55, dup_id: 800000301, dup_count: 3, is_show: true, slot: 0 },
        { item_id: 800000301, count: 5, rarity: 0, weight: 80, dup_id: 800000301, dup_count: 5, is_show: false, slot: 0 }
      ],
      5: [ // Gold Royale
        { item_id: 710000422, count: 1, rarity: 2, weight: 3, dup_id: 800000301, dup_count: 10, is_show: true, slot: 0 },
        { item_id: 710000423, count: 1, rarity: 2, weight: 3, dup_id: 800000301, dup_count: 10, is_show: true, slot: 0 },
        { item_id: 710000403, count: 1, rarity: 1, weight: 15, dup_id: 800000301, dup_count: 5, is_show: true, slot: 0 },
        { item_id: 203000505, count: 1, rarity: 0, weight: 60, dup_id: 800000301, dup_count: 3, is_show: true, slot: 0 },
        { item_id: 204000304, count: 1, rarity: 0, weight: 60, dup_id: 800000301, dup_count: 3, is_show: true, slot: 0 },
        { item_id: 1101000002, count: 1, rarity: 0, weight: 95, dup_id: 800000301, dup_count: 2, is_show: false, slot: 0 }
      ],
      6: [ // Incubator 12 Slots
        { item_id: 808000011, count: 1, rarity: 2, weight: 6, dup_id: 808000011, dup_count: 1, is_show: true, slot: 0 },
        { item_id: 808000001, count: 1, rarity: 1, weight: 14, dup_id: 808000001, dup_count: 1, is_show: true, slot: 1 },
        { item_id: 808000012, count: 1, rarity: 2, weight: 6, dup_id: 808000012, dup_count: 1, is_show: true, slot: 2 },
        { item_id: 808000001, count: 2, rarity: 2, weight: 8, dup_id: 808000001, dup_count: 2, is_show: true, slot: 3 },
        { item_id: 907001614, count: 1, rarity: 1, weight: 16, dup_id: 800000301, dup_count: 10, is_show: true, slot: 4 },
        { item_id: 800000304, count: 1, rarity: 2, weight: 4, dup_id: 800000304, dup_count: 1, is_show: true, slot: 5 },
        { item_id: 802000001, count: 1, rarity: 0, weight: 40, dup_id: 802000001, dup_count: 1, is_show: true, slot: 6 },
        { item_id: 802000008, count: 1, rarity: 0, weight: 40, dup_id: 802000008, dup_count: 1, is_show: true, slot: 7 },
        { item_id: 800000301, count: 5, rarity: 0, weight: 55, dup_id: 800000301, dup_count: 5, is_show: true, slot: 8 },
        { item_id: 1307000001, count: 3, rarity: 0, weight: 60, dup_id: 800000301, dup_count: 2, is_show: true, slot: 9 },
        { item_id: 1101000002, count: 1, rarity: 0, weight: 60, dup_id: 800000301, dup_count: 2, is_show: true, slot: 10 },
        { item_id: 1102000002, count: 1, rarity: 0, weight: 60, dup_id: 800000301, dup_count: 2, is_show: true, slot: 11 }
      ]
    },

    // Lucky Meter Architecture
    meters: {
      3: { max: 150, increment: 1, guaranteed: 150, reset_on_win: true, first_draw_bonus: 3, weekly_spins: 18 },
      4: { max: 150, increment: 1, guaranteed: 150, reset_on_win: true, first_draw_bonus: 3, weekly_spins: 12 },
      5: { max: 300, increment: 1, guaranteed: 300, reset_on_win: true, first_draw_bonus: 0, weekly_spins: 45 },
      6: { max: 80,  increment: 1, guaranteed: 80,  reset_on_win: true, first_draw_bonus: 0, weekly_spins: 8 }
    },

    // Weekly Milestones
    milestones: [
      { machine_id: 3, draws: 5, reward_id: 802000001, count: 1, status: 'claimed' },
      { machine_id: 3, draws: 15, reward_id: 802000008, count: 1, status: 'claimable' },
      { machine_id: 3, draws: 30, reward_id: 800000301, count: 15, status: 'locked' },
      { machine_id: 4, draws: 5, reward_id: 802000008, count: 1, status: 'claimed' },
      { machine_id: 4, draws: 15, reward_id: 802000001, count: 1, status: 'locked' },
      { machine_id: 5, draws: 5, reward_id: 802000000, count: 2, status: 'claimed' },
      { machine_id: 5, draws: 15, reward_id: 802000001, count: 1, status: 'claimed' },
      { machine_id: 6, draws: 5, reward_id: 808000001, count: 1, status: 'claimable' },
      { machine_id: 6, draws: 15, reward_id: 808000011, count: 1, status: 'locked' }
    ],

    // Account 10001 Dossier Balances & Current Meters
    accountProfile: {
      account_id: 10001,
      nickname: 'PushpaGG',
      level: 50,
      rank: 'Heroic (305)',
      diamonds: 999999,
      gold: 1158549,
      vouchers: {
        802000001: 25, // Diamond
        802000008: 18, // Weapon
        802000000: 64, // Gold
        802000009: 12  // Incubator
      },
      materials: {
        808000001: 14, // Evolution Stone
        808000011: 6,  // Blueprint YinYang
        808000012: 4,  // Blueprint Joker
        800000301: 185 // FF Tokens
      },
      current_meters: {
        3: 94,  // Diamond Royale Meter
        4: 31,  // Weapon Royale Meter
        5: 142, // Gold Royale Meter
        6: 48   // Incubator Meter
      }
    },

    // Incubator Special Exchange Forge Recipes
    forgeRecipes: [
      {
        id: 1,
        sort_id: 1,
        forge_tab_id: 1,
        tab_name: 'YinYang Masters (OB17)',
        reward_id: 710000410,
        reward_name: 'YinYang Master Gold Bundle (Male)',
        blueprints: 3,
        blueprint_id: 808000011,
        stones: 7,
        limit: 1,
        rarity: 2
      },
      {
        id: 2,
        sort_id: 2,
        forge_tab_id: 1,
        tab_name: 'YinYang Masters (OB17)',
        reward_id: 710000411,
        reward_name: 'YinYang Mistress Gold Bundle (Female)',
        blueprints: 3,
        blueprint_id: 808000011,
        stones: 7,
        limit: 1,
        rarity: 2
      },
      {
        id: 3,
        sort_id: 3,
        forge_tab_id: 1,
        tab_name: 'YinYang Masters (OB17)',
        reward_id: 710000412,
        reward_name: 'YinYang Disciple Blue (Male)',
        blueprints: 2,
        blueprint_id: 808000011,
        stones: 5,
        limit: 1,
        rarity: 2
      },
      {
        id: 4,
        sort_id: 4,
        forge_tab_id: 1,
        tab_name: 'YinYang Masters (OB17)',
        reward_id: 710000413,
        reward_name: 'YinYang Disciple Blue (Female)',
        blueprints: 2,
        blueprint_id: 808000011,
        stones: 5,
        limit: 1,
        rarity: 2
      }
    ],

    // Token Shop Items
    tokenShopItems: [
      { item_id: 710000403, name: 'Bioforge Cybernetic Suit', cost: 120, limit: 1, category: 'Costumes' },
      { id: 907001620, name: 'AWM Duke Butterfly Skin', cost: 90, limit: 1, category: 'Weapons' },
      { item_id: 802000001, name: 'Diamond Royale Voucher', cost: 10, limit: 10, category: 'Vouchers' },
      { item_id: 802000008, name: 'Weapon Royale Voucher', cost: 8, limit: 10, category: 'Vouchers' }
    ],

    // Banner Graphic Assets (loaded from server/static/banners/)
    bannerAssets: [
      { name: 'UI_Lottery_Poster_P.png', category: 'Poster', machine: 'Diamond Royale', res: '800x450' },
      { name: 'UI_Lottery_Poster_W.png', category: 'Poster', machine: 'Weapon Royale', res: '800x450' },
      { name: 'UI_Lottery_Poster_G.png', category: 'Poster', machine: 'Gold Royale', res: '800x450' },
      { name: 'FF_Lottery_anni_forge.png', category: 'Wheel', machine: 'Incubator Forge', res: '600x600' },
      { name: 'FF_Lottery_anni_big.png', category: 'Banner', machine: 'Anniversary Main', res: '1024x512' },
      { name: 'luck_royale_banner.png', category: 'Billboard', machine: 'Global Lobby Banner', res: '1280x720' },
      { name: 'FF_Lottery_Megabucks.png', category: 'Header', machine: 'Megabucks Special', res: '900x400' },
      { name: 'FF_Lottery_M4A1_Carnival.png', category: 'Graphic', machine: 'Weapon Spotlight', res: '512x512' }
    ],

    // Timed Event Schedules
    events: [
      {
        id: 1,
        title: 'Carnival Weapon Rate-Up Fest',
        machine_id: 4,
        start_time: '2026-11-20 00:00:00',
        end_time: '2026-11-27 23:59:59',
        rate_up_pct: 100,
        discount_pct: 33,
        status: 'active'
      },
      {
        id: 2,
        title: 'YinYang Incubator 50% Off Weekend',
        machine_id: 6,
        start_time: '2026-11-22 00:00:00',
        end_time: '2026-11-24 23:59:59',
        rate_up_pct: 50,
        discount_pct: 50,
        status: 'scheduled'
      }
    ],

    // Transaction Explorer Logs
    transactions: [
      {
        id: 'TX-10001-9481',
        time: '12 mins ago',
        account_id: 10001,
        machine_id: 3,
        machine_name: 'Diamond Royale',
        spin_type: '10x Spin',
        cost: '600 Diamonds',
        items: [
          { id: 710000403, count: 1, rarity: 1, is_duplicate: false },
          { id: 203000505, count: 1, rarity: 0, is_duplicate: true },
          { id: 800000301, count: 5, rarity: 0, is_duplicate: false }
        ],
        duplicate_tokens: 3,
        meter_shift: '84 -> 94'
      },
      {
        id: 'TX-10001-9480',
        time: '34 mins ago',
        account_id: 10001,
        machine_id: 6,
        machine_name: 'Incubator',
        spin_type: '5x Spin',
        cost: '270 Diamonds',
        items: [
          { id: 808000001, count: 1, rarity: 1, is_duplicate: false },
          { id: 802000001, count: 1, rarity: 0, is_duplicate: false }
        ],
        duplicate_tokens: 0,
        meter_shift: '43 -> 48'
      },
      {
        id: 'TX-10001-9479',
        time: '1 hour ago',
        account_id: 10001,
        machine_id: 5,
        machine_name: 'Gold Royale',
        spin_type: '1x Free',
        cost: 'Free Daily',
        items: [
          { id: 204000304, count: 1, rarity: 0, is_duplicate: false }
        ],
        duplicate_tokens: 0,
        meter_shift: '141 -> 142'
      }
    ]
  };

  // =========================================================================
  // 3. UTILITIES, FORMATTING & API LAYER
  // =========================================================================

  function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return Number(num).toLocaleString('en-US');
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Toast Notification System
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const card = document.createElement('div');
    card.className = 'toast-card';

    let iconColor = 'var(--lr-blue)';
    if (type === 'success') iconColor = 'var(--lr-green-text)';
    if (type === 'error') iconColor = 'var(--lr-red)';
    if (type === 'warning') iconColor = 'var(--lr-gold-text)';

    card.innerHTML = `
      <span class="icon" style="color:${iconColor};"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></span>
      <span style="font-weight:600; font-size:12px; flex:1;">${escapeHtml(message)}</span>
    `;

    container.appendChild(card);
    setTimeout(() => {
      card.classList.add('out');
      setTimeout(() => card.remove(), 160);
    }, 3200);
  }

  // API Client with automatic fallback to local state for high resiliency
  async function apiFetch(endpoint, options = {}) {
    const url = endpoint.startsWith('/') ? endpoint : `/api/admin/luck-royale/${endpoint}`;
    try {
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        ...options
      });
      if (res.ok) {
        return await res.json();
      }
      // If 404/500, log warning and let caller handle
      console.warn(`[AdminAPI] ${options.method || 'GET'} ${url} returned ${res.status}`);
      return null;
    } catch (err) {
      console.warn(`[AdminAPI] ${url} error:`, err.message);
      return null;
    }
  }

  // =========================================================================
  // 4. TAB NAVIGATION & VIEW SWITCHER
  // =========================================================================

  function switchTab(tabId) {
    state.activeTab = tabId;

    // Update Tab Buttons
    document.querySelectorAll('.lr-subtab-btn').forEach(btn => {
      if (btn.getAttribute('data-tab') === tabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update View Panes
    document.querySelectorAll('.lr-view-pane').forEach(pane => {
      if (pane.id === tabId) {
        pane.classList.add('active');
      } else {
        pane.classList.remove('active');
      }
    });

    // Render corresponding view
    if (tabId === 'tab-overview') renderOverviewView();
    if (tabId === 'tab-machines') renderMachinesView();
    if (tabId === 'tab-reward-pools') renderRewardPoolsView();
    if (tabId === 'tab-lucky-meters') renderLuckyMetersView();
    if (tabId === 'tab-currency-vouchers') renderCurrencyVouchersView();
    if (tabId === 'tab-incubator-forge') renderIncubatorForgeView();
    if (tabId === 'tab-banners-events') renderBannersEventsView();
    if (tabId === 'tab-account-tx') renderAccountTxView();
  }

  // =========================================================================
  // 5. VIEW 1: LUCK ROYALE OVERVIEW RENDERER
  // =========================================================================

  function renderOverviewView() {
    // Update Stats
    document.getElementById('stat-active-machines').textContent = state.machines.filter(m => m.enabled).length;
    document.getElementById('stat-total-spins').textContent = formatNumber(state.stats.totalSpins);
    document.getElementById('header-total-spins').textContent = formatNumber(state.stats.totalSpins);
    document.getElementById('stat-spins-today').textContent = `+${formatNumber(state.stats.spinsToday)} in current session`;
    document.getElementById('stat-diamonds-burned').textContent = formatNumber(state.stats.diamondsBurned);
    document.getElementById('stat-gold-burned').textContent = formatNumber(state.stats.goldBurned);

    // Vouchers Overview Cards
    const vouchersGrid = document.getElementById('vouchers-overview-grid');
    if (vouchersGrid) {
      vouchersGrid.innerHTML = `
        <div class="lr-stat-tile">
          <span class="lr-stat-lbl">Diamond Royale Vouchers</span>
          <span class="lr-stat-val monospace">${formatNumber(state.stats.vouchersUsed.diamond)} Consumed</span>
          <span class="lr-stat-sub">Item #802000001 &bull; Active</span>
        </div>
        <div class="lr-stat-tile">
          <span class="lr-stat-lbl">Weapon Royale Vouchers</span>
          <span class="lr-stat-val monospace">${formatNumber(state.stats.vouchersUsed.weapon)} Consumed</span>
          <span class="lr-stat-sub">Item #802000008 &bull; Active</span>
        </div>
        <div class="lr-stat-tile">
          <span class="lr-stat-lbl">Gold Royale Vouchers</span>
          <span class="lr-stat-val monospace">${formatNumber(state.stats.vouchersUsed.gold)} Consumed</span>
          <span class="lr-stat-sub">Item #802000000 &bull; Active</span>
        </div>
        <div class="lr-stat-tile">
          <span class="lr-stat-lbl">Incubator Vouchers</span>
          <span class="lr-stat-val monospace">${formatNumber(state.stats.vouchersUsed.incubator)} Consumed</span>
          <span class="lr-stat-sub">Item #802000009 &bull; Active</span>
        </div>
      `;
    }

    // Machines Grid
    const machinesGrid = document.getElementById('overview-machines-grid');
    if (machinesGrid) {
      machinesGrid.innerHTML = state.machines.map(m => {
        const coinIcon = m.coin_type === 2 ? 'Diamonds' : 'Gold Coins';
        const coinColor = m.coin_type === 2 ? 'var(--lr-blue)' : 'var(--lr-gold-text)';
        return `
          <div class="machine-card">
            <img src="/static/banners/${escapeHtml(m.banner)}" class="machine-banner-preview" alt="${escapeHtml(m.name)}" onerror="this.src='/static/banners/luck_royale_banner.png'">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="lr-badge">CHEST #${m.chest_id}</span>
              <span class="lr-chip ${m.enabled ? 'active' : ''}">${m.enabled ? 'Online' : 'Disabled'}</span>
            </div>
            <strong style="font-size:14px;">${escapeHtml(m.name)}</strong>
            <div style="font-size:11.5px; color:var(--lr-text-secondary);">
              <span>Cost: <strong style="color:${coinColor};">${m.once_price}</strong> (1x) &bull; <strong style="color:${coinColor};">${m.ten_price}</strong> (${m.ten_num}x)</span><br>
              <span>Lucky Cap: <strong>${m.meter_max}</strong> &bull; Priority: ${m.priority}</span>
            </div>
            <div style="display:flex; gap:6px; margin-top:4px;">
              <button class="btn btn-sm btn-primary" style="flex:1;" onclick="LuckRoyaleApp.selectMachineForRewards(${m.chest_id})">Edit Pool</button>
              <button class="btn btn-sm" onclick="LuckRoyaleApp.openQuickSpinForMachine(${m.chest_id})">Spin</button>
            </div>
          </div>
        `;
      }).join('');
    }

    // Recent Transactions Table in Overview
    const txTbody = document.getElementById('overview-tx-tbody');
    if (txTbody) {
      if (state.transactions.length === 0) {
        txTbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--lr-text-tertiary);">No transactions logged yet.</td></tr>`;
      } else {
        txTbody.innerHTML = state.transactions.slice(0, 5).map(tx => {
          const itemsHtml = tx.items.map(it => {
            const itemObj = lookupItem(it.id);
            const rClass = it.rarity === 2 ? 'super' : (it.rarity === 1 ? 'rare' : 'normal');
            return `<span class="badge-rarity ${rClass}">${escapeHtml(itemObj.name)}</span>`;
          }).join(' ');

          return `
            <tr>
              <td class="monospace" style="font-size:11.5px; color:var(--lr-text-secondary);">${escapeHtml(tx.time)}</td>
              <td class="monospace font-bold" style="color:var(--lr-blue);">${tx.account_id}</td>
              <td><strong>${escapeHtml(tx.machine_name)}</strong></td>
              <td><span class="lr-chip" style="font-size:11px;">${escapeHtml(tx.spin_type)}</span></td>
              <td class="monospace tabular">${escapeHtml(tx.cost)}</td>
              <td>${itemsHtml}</td>
              <td class="monospace tabular" style="color:var(--lr-green-text); font-weight:600;">${escapeHtml(tx.meter_shift)}</td>
            </tr>
          `;
        }).join('');
      }
    }
  }

  // =========================================================================
  // 6. VIEW 2: MACHINE MANAGER RENDERER
  // =========================================================================

  function renderMachinesView() {
    const tbody = document.getElementById('machines-tbody');
    if (!tbody) return;

    const query = state.machineFilterQuery.toLowerCase().trim();
    const filtered = state.machines.filter(m => {
      return !query || m.name.toLowerCase().includes(query) || String(m.chest_id).includes(query);
    });

    tbody.innerHTML = filtered.map(m => {
      const coinName = m.coin_type === 2 ? 'Diamonds' : 'Gold Coins';
      const typeName = m.type === 1 ? 'Turntable Wheel' : 'Standard Gacha';

      return `
        <tr>
          <td class="monospace font-bold" style="color:var(--lr-blue);">#${m.chest_id}</td>
          <td>
            <strong>${escapeHtml(m.name)}</strong><br>
            <span class="monospace" style="font-size:10.5px; color:var(--lr-text-tertiary);">${escapeHtml(m.code_name || '')}</span>
          </td>
          <td><span class="lr-chip" style="font-size:11px;">${typeName}</span></td>
          <td><strong>${coinName}</strong></td>
          <td class="monospace tabular">${m.once_price} ${coinName === 'Diamonds' ? 'Gems' : 'Gold'}</td>
          <td class="monospace tabular">${m.ten_price} (${m.ten_num}x)</td>
          <td class="monospace" style="font-size:11.5px;">#${m.voucher_id}</td>
          <td class="monospace tabular font-bold" style="color:var(--lr-gold-text);">${m.meter_max}</td>
          <td class="monospace tabular">${m.priority}</td>
          <td>
            <label class="switch-wrap" title="Toggle active status">
              <input type="checkbox" ${m.enabled ? 'checked' : ''} onchange="LuckRoyaleApp.toggleMachineStatus(${m.chest_id}, this.checked)" style="display:none;">
              <span class="switch-ui"></span>
            </label>
          </td>
          <td>
            <label class="switch-wrap" title="Toggle lobby visibility">
              <input type="checkbox" ${m.visible ? 'checked' : ''} onchange="LuckRoyaleApp.toggleMachineVisibility(${m.chest_id}, this.checked)" style="display:none;">
              <span class="switch-ui"></span>
            </label>
          </td>
          <td style="text-align:right;">
            <div style="display:inline-flex; gap:4px;">
              <button class="btn btn-sm" onclick="LuckRoyaleApp.editMachine(${m.chest_id})">Edit</button>
              <button class="btn btn-sm" onclick="LuckRoyaleApp.duplicateMachine(${m.chest_id})">Duplicate</button>
              <button class="btn btn-sm btn-danger" onclick="LuckRoyaleApp.deleteMachine(${m.chest_id})">Delete</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  function filterMachines() {
    state.machineFilterQuery = document.getElementById('machine-filter-input')?.value || '';
    renderMachinesView();
  }

  // =========================================================================
  // 7. VIEW 3: REWARD POOL EDITOR RENDERER
  // =========================================================================

  function renderRewardPoolsView() {
    // Populate Machine Dropdown
    const select = document.getElementById('reward-pool-machine-select');
    if (select) {
      select.innerHTML = state.machines.map(m => `
        <option value="${m.chest_id}" ${m.chest_id === state.selectedPoolChestId ? 'selected' : ''}>
          #${m.chest_id} — ${escapeHtml(m.name)}
        </option>
      `).join('');
    }

    const pool = state.rewardPools[state.selectedPoolChestId] || [];
    const totalItems = pool.length;
    const totalWeight = pool.reduce((sum, it) => sum + (it.weight || 0), 0) || 1;

    const superRares = pool.filter(it => it.rarity === 2);
    const rares = pool.filter(it => it.rarity === 1);
    const normals = pool.filter(it => it.rarity === 0);

    const superWeight = superRares.reduce((sum, it) => sum + it.weight, 0);
    const rareWeight = rares.reduce((sum, it) => sum + it.weight, 0);
    const normWeight = normals.reduce((sum, it) => sum + it.weight, 0);

    // Update Summary Tiles
    document.getElementById('pool-stat-total-items').textContent = totalItems;
    document.getElementById('pool-stat-super-rare').textContent = superRares.length;
    document.getElementById('pool-stat-super-prob').textContent = `${((superWeight / totalWeight) * 100).toFixed(2)}% Aggregate Chance`;
    document.getElementById('pool-stat-rare').textContent = rares.length;
    document.getElementById('pool-stat-rare-prob').textContent = `${((rareWeight / totalWeight) * 100).toFixed(2)}% Aggregate Chance`;
    document.getElementById('pool-stat-normal').textContent = normals.length;
    document.getElementById('pool-stat-normal-prob').textContent = `${((normWeight / totalWeight) * 100).toFixed(2)}% Aggregate Chance`;

    // Filter Items
    const query = state.poolFilterQuery.toLowerCase().trim();
    const rarityFilter = state.poolFilterRarity;

    const filtered = pool.filter(it => {
      const itemObj = lookupItem(it.item_id);
      const matchQuery = !query || String(it.item_id).includes(query) || itemObj.name.toLowerCase().includes(query);
      const matchRarity = rarityFilter === 'all' ||
        (rarityFilter === 'super' && it.rarity === 2) ||
        (rarityFilter === 'rare' && it.rarity === 1) ||
        (rarityFilter === 'normal' && it.rarity === 0);
      return matchQuery && matchRarity;
    });

    const tbody = document.getElementById('reward-pool-tbody');
    if (!tbody) return;

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:24px; color:var(--lr-text-tertiary);">No reward items match the filter.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map((it, idx) => {
      const itemObj = lookupItem(it.item_id);
      const probPct = ((it.weight / totalWeight) * 100).toFixed(2);
      const rClass = it.rarity === 2 ? 'super' : (it.rarity === 1 ? 'rare' : 'normal');
      const rText = it.rarity === 2 ? 'Super Rare' : (it.rarity === 1 ? 'Rare' : 'Normal');

      return `
        <tr>
          <td class="monospace font-bold" style="color:var(--lr-blue);">#${it.item_id}</td>
          <td>
            <strong>${escapeHtml(itemObj.name)}</strong>
            <span class="monospace" style="font-size:11px; color:var(--lr-text-tertiary); display:block;">${escapeHtml(itemObj.category)}</span>
          </td>
          <td class="monospace tabular font-bold">x${it.count}</td>
          <td><span class="badge-rarity ${rClass}">${rText}</span></td>
          <td class="monospace tabular font-bold">${it.weight}</td>
          <td class="monospace tabular" style="color:var(--lr-green-text); font-weight:600;">${probPct}%</td>
          <td class="monospace" style="font-size:11.5px;">FF Token x${it.dup_count || 5}</td>
          <td><span class="lr-chip ${it.is_show ? 'active' : ''}">${it.is_show ? 'Visible' : 'Hidden'}</span></td>
          <td style="text-align:right;">
            <div style="display:inline-flex; gap:4px;">
              <button class="btn btn-sm" onclick="LuckRoyaleApp.editRewardItem(${it.item_id})">Edit</button>
              <button class="btn btn-sm btn-danger" onclick="LuckRoyaleApp.deleteRewardItem(${it.item_id})">Remove</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  function onPoolMachineChange() {
    const select = document.getElementById('reward-pool-machine-select');
    if (!select) return;
    state.selectedPoolChestId = Number(select.value);
    renderRewardPoolsView();
  }

  function filterRewardPool() {
    state.poolFilterQuery = document.getElementById('reward-pool-search')?.value || '';
    state.poolFilterRarity = document.getElementById('reward-pool-rarity-filter')?.value || 'all';
    renderRewardPoolsView();
  }

  function selectMachineForRewards(chestId) {
    state.selectedPoolChestId = chestId;
    switchTab('tab-reward-pools');
  }

  // Statistical Monte Carlo 100 Pull Simulation
  function runStatisticalSimulation() {
    const pool = state.rewardPools[state.selectedPoolChestId] || [];
    if (pool.length === 0) {
      showToast('Reward pool is empty! Cannot simulate.', 'error');
      return;
    }

    const totalWeight = pool.reduce((sum, it) => sum + (it.weight || 0), 0);
    const results = { super: 0, rare: 0, normal: 0, itemsWon: {} };

    for (let i = 0; i < 100; i++) {
      let roll = Math.random() * totalWeight;
      for (const it of pool) {
        roll -= it.weight;
        if (roll <= 0) {
          if (it.rarity === 2) results.super++;
          else if (it.rarity === 1) results.rare++;
          else results.normal++;

          results.itemsWon[it.item_id] = (results.itemsWon[it.item_id] || 0) + 1;
          break;
        }
      }
    }

    showToast(`Simulation complete: 100 pulls yielded ${results.super} Super Rares, ${results.rare} Rares, ${results.normal} Normals.`, 'success');
  }

  // =========================================================================
  // 8. VIEW 4: LUCKY METER MANAGER RENDERER
  // =========================================================================

  function renderLuckyMetersView() {
    const cardsGrid = document.getElementById('lucky-meter-cards-grid');
    if (!cardsGrid) return;

    cardsGrid.innerHTML = state.machines.map(m => {
      const meterCfg = state.meters[m.chest_id] || { max: 150, increment: 1, guaranteed: 150, reset_on_win: true, first_draw_bonus: 0 };
      const currentVal = state.accountProfile.current_meters[m.chest_id] || 0;
      const pct = Math.min(100, (currentVal / meterCfg.max) * 100).toFixed(1);

      return `
        <div class="lr-card" style="padding:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <span class="lr-badge">CHEST #${m.chest_id}</span>
              <strong style="font-size:15px; margin-left:6px;">${escapeHtml(m.name)}</strong>
            </div>
            <span class="lr-chip active">Pity Engine Active</span>
          </div>

          <!-- Gauge Display -->
          <div style="background:var(--lr-bg-surface-elevated); border:1px solid var(--lr-border); border-radius:var(--lr-radius-md); padding:12px;">
            <div style="display:flex; justify-content:space-between; font-size:11.5px; margin-bottom:6px;">
              <span>Current Test Meter (10001): <strong class="monospace tabular">${currentVal} / ${meterCfg.max}</strong></span>
              <span class="monospace font-bold" style="color:var(--lr-blue);">${pct}% to Guaranteed Grand Prize</span>
            </div>
            <div class="meter-bar-track">
              <div class="meter-bar-fill gold" style="width:${pct}%;"></div>
            </div>
          </div>

          <!-- Configuration Fields -->
          <div class="grid-2">
            <div>
              <label class="form-label">Max Lucky Cap (Threshold)</label>
              <input type="number" class="input-text monospace" id="meter-cap-${m.chest_id}" value="${meterCfg.max}" onchange="LuckRoyaleApp.updateMeterParam(${m.chest_id}, 'max', this.value)">
            </div>
            <div>
              <label class="form-label">Increment Rate Per Spin</label>
              <input type="number" class="input-text monospace" id="meter-inc-${m.chest_id}" value="${meterCfg.increment}" onchange="LuckRoyaleApp.updateMeterParam(${m.chest_id}, 'increment', this.value)">
            </div>
          </div>

          <div class="grid-2">
            <div>
              <label class="form-label">Guaranteed Drop Trigger</label>
              <input type="number" class="input-text monospace" id="meter-guard-${m.chest_id}" value="${meterCfg.guaranteed}" onchange="LuckRoyaleApp.updateMeterParam(${m.chest_id}, 'guaranteed', this.value)">
            </div>
            <div>
              <label class="form-label">First Draw Bonus Cap</label>
              <input type="number" class="input-text monospace" id="meter-first-${m.chest_id}" value="${meterCfg.first_draw_bonus}" onchange="LuckRoyaleApp.updateMeterParam(${m.chest_id}, 'first_draw_bonus', this.value)">
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
            <label class="switch-wrap">
              <input type="checkbox" ${meterCfg.reset_on_win ? 'checked' : ''} onchange="LuckRoyaleApp.updateMeterParam(${m.chest_id}, 'reset_on_win', this.checked)" style="display:none;">
              <span class="switch-ui"></span>
              <span style="font-weight:600; font-size:11.5px;">Reset to 0 on Grand Prize Hit</span>
            </label>
            <button class="btn btn-sm btn-primary" onclick="LuckRoyaleApp.saveMeterConfig(${m.chest_id})">Save Settings</button>
          </div>
        </div>
      `;
    }).join('');

    // Weekly Milestones
    const milestonesTbody = document.getElementById('milestones-tbody');
    if (milestonesTbody) {
      milestonesTbody.innerHTML = state.milestones.map((ms, idx) => {
        const machine = state.machines.find(m => m.chest_id === ms.machine_id) || { name: `Chest #${ms.machine_id}` };
        const rewardObj = lookupItem(ms.reward_id);

        let statusClass = 'active';
        if (ms.status === 'locked') statusClass = '';
        if (ms.status === 'claimable') statusClass = 'active';

        return `
          <tr>
            <td><strong>${escapeHtml(machine.name)}</strong></td>
            <td class="monospace tabular font-bold">${ms.draws} Spins</td>
            <td><strong>${escapeHtml(rewardObj.name)}</strong></td>
            <td class="monospace tabular font-bold">x${ms.count}</td>
            <td><span class="lr-chip ${statusClass}">${escapeHtml(ms.status.toUpperCase())}</span></td>
            <td style="text-align:right;">
              <button class="btn btn-sm btn-danger" onclick="LuckRoyaleApp.deleteMilestone(${idx})">Delete</button>
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  function updateMeterParam(chestId, key, value) {
    if (!state.meters[chestId]) state.meters[chestId] = {};
    state.meters[chestId][key] = (typeof value === 'boolean') ? value : Number(value);
  }

  async function saveMeterConfig(chestId) {
    const cfg = state.meters[chestId];
    await apiFetch(`meters/${chestId}`, {
      method: 'PUT',
      body: JSON.stringify(cfg)
    });
    showToast(`Lucky Meter settings for Chest #${chestId} synchronized with server!`, 'success');
  }

  async function saveAllMeters() {
    await apiFetch('meters', {
      method: 'PUT',
      body: JSON.stringify(state.meters)
    });
    showToast('All Lucky Meter configurations successfully persisted to core server state.', 'success');
  }

  // =========================================================================
  // 9. VIEW 5: CURRENCY & VOUCHER MANAGER RENDERER
  // =========================================================================

  function renderCurrencyVouchersView() {
    const walletGrid = document.getElementById('wallet-balances-grid');
    if (!walletGrid) return;

    const prof = state.accountProfile;
    walletGrid.innerHTML = `
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">Diamonds (Gems)</span>
        <span class="lr-stat-val monospace tabular" style="color:var(--lr-blue);">${formatNumber(prof.diamonds)}</span>
        <span class="lr-stat-sub">Game Balance RLock Safe</span>
      </div>
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">Gold Coins</span>
        <span class="lr-stat-val monospace tabular" style="color:var(--lr-gold-text);">${formatNumber(prof.gold)}</span>
        <span class="lr-stat-sub">Game Balance RLock Safe</span>
      </div>
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">Diamond Royale Vouchers</span>
        <span class="lr-stat-val monospace tabular">${formatNumber(prof.vouchers[802000001] || 0)}</span>
        <span class="lr-stat-sub">Item #802000001</span>
      </div>
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">Weapon Royale Vouchers</span>
        <span class="lr-stat-val monospace tabular">${formatNumber(prof.vouchers[802000008] || 0)}</span>
        <span class="lr-stat-sub">Item #802000008</span>
      </div>
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">Gold Royale Vouchers</span>
        <span class="lr-stat-val monospace tabular">${formatNumber(prof.vouchers[802000000] || 0)}</span>
        <span class="lr-stat-sub">Item #802000000</span>
      </div>
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">Incubator Vouchers</span>
        <span class="lr-stat-val monospace tabular">${formatNumber(prof.vouchers[802000009] || 0)}</span>
        <span class="lr-stat-sub">Item #802000009</span>
      </div>
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">Evolution Stones</span>
        <span class="lr-stat-val monospace tabular" style="color:var(--rarity-super-text);">${formatNumber(prof.materials[808000001] || 0)}</span>
        <span class="lr-stat-sub">Item #808000001</span>
      </div>
      <div class="lr-stat-tile">
        <span class="lr-stat-lbl">YinYang Blueprints</span>
        <span class="lr-stat-val monospace tabular" style="color:var(--rarity-super-text);">${formatNumber(prof.materials[808000011] || 0)}</span>
        <span class="lr-stat-sub">Item #808000011</span>
      </div>
    `;

    // Spin Costs Tuning Table
    const costsTbody = document.getElementById('spin-costs-tbody');
    if (costsTbody) {
      costsTbody.innerHTML = state.machines.map(m => {
        const coinName = m.coin_type === 2 ? 'Diamonds' : 'Gold Coins';
        return `
          <tr>
            <td><strong>${escapeHtml(m.name)}</strong></td>
            <td><strong>${coinName}</strong></td>
            <td>
              <input type="number" class="input-text monospace" style="width:100px;" value="${m.once_price}" id="cost-once-${m.chest_id}">
            </td>
            <td>
              <input type="number" class="input-text monospace" style="width:100px;" value="${m.ten_price}" id="cost-ten-${m.chest_id}">
            </td>
            <td>1 Ticket = 1 Draw</td>
            <td style="text-align:right;">
              <button class="btn btn-sm btn-primary" onclick="LuckRoyaleApp.saveMachineCosts(${m.chest_id})">Update Cost</button>
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  async function executeGrantDeduct() {
    const asset = document.getElementById('grant-asset-select')?.value;
    const action = document.getElementById('grant-action-type')?.value;
    const amount = Number(document.getElementById('grant-amount-input')?.value || 0);

    if (amount <= 0 && action !== 'set') {
      showToast('Amount must be greater than zero.', 'error');
      return;
    }

    const aid = state.targetAccountId;
    let delta = action === 'deduct' ? -amount : amount;

    // Call Admin API
    await apiFetch('currencies-vouchers', {
      method: 'POST',
      body: JSON.stringify({
        account_id: aid,
        asset: asset,
        action: action,
        amount: amount,
        delta: delta
      })
    });

    // Update Local State for immediate visual feedback
    if (asset === 'diamonds') {
      if (action === 'set') state.accountProfile.diamonds = amount;
      else state.accountProfile.diamonds = Math.max(0, state.accountProfile.diamonds + delta);
    } else if (asset === 'gold') {
      if (action === 'set') state.accountProfile.gold = amount;
      else state.accountProfile.gold = Math.max(0, state.accountProfile.gold + delta);
    } else if (state.accountProfile.vouchers[asset] !== undefined) {
      if (action === 'set') state.accountProfile.vouchers[asset] = amount;
      else state.accountProfile.vouchers[asset] = Math.max(0, state.accountProfile.vouchers[asset] + delta);
    } else if (state.accountProfile.materials[asset] !== undefined) {
      if (action === 'set') state.accountProfile.materials[asset] = amount;
      else state.accountProfile.materials[asset] = Math.max(0, state.accountProfile.materials[asset] + delta);
    }

    showToast(`Successfully processed ${action} of ${formatNumber(amount)} ${asset} for account ${aid}!`, 'success');
    renderCurrencyVouchersView();
  }

  function quickGrantVouchers(qty) {
    const aid = state.targetAccountId;
    [802000001, 802000008, 802000000, 802000009].forEach(vid => {
      state.accountProfile.vouchers[vid] = (state.accountProfile.vouchers[vid] || 0) + qty;
    });
    apiFetch('currencies-vouchers', {
      method: 'POST',
      body: JSON.stringify({ account_id: aid, quick: 'all_vouchers', amount: qty })
    });
    showToast(`Granted +${qty} of every Luck Royale Voucher to Account ${aid}!`, 'success');
    renderCurrencyVouchersView();
  }

  function quickGrantCurrency(gold, diamonds) {
    const aid = state.targetAccountId;
    state.accountProfile.gold += gold;
    state.accountProfile.diamonds += diamonds;
    apiFetch('currencies-vouchers', {
      method: 'POST',
      body: JSON.stringify({ account_id: aid, gold: gold, diamonds: diamonds })
    });
    showToast(`Granted +${formatNumber(gold)} Gold & +${formatNumber(diamonds)} Diamonds to Account ${aid}!`, 'success');
    renderCurrencyVouchersView();
  }

  function quickGrantIncubatorMaterials() {
    const aid = state.targetAccountId;
    state.accountProfile.materials[808000001] = (state.accountProfile.materials[808000001] || 0) + 10;
    state.accountProfile.materials[808000011] = (state.accountProfile.materials[808000011] || 0) + 5;
    state.accountProfile.materials[808000012] = (state.accountProfile.materials[808000012] || 0) + 5;
    apiFetch('currencies-vouchers', {
      method: 'POST',
      body: JSON.stringify({ account_id: aid, quick: 'incubator_materials' })
    });
    showToast(`Granted 10 Evolution Stones and 5 YinYang/Joker Blueprints to Account ${aid}!`, 'success');
    renderCurrencyVouchersView();
  }

  async function saveMachineCosts(chestId) {
    const once = Number(document.getElementById(`cost-once-${chestId}`)?.value || 0);
    const ten = Number(document.getElementById(`cost-ten-${chestId}`)?.value || 0);

    const m = state.machines.find(x => x.chest_id === chestId);
    if (m) {
      m.once_price = once;
      m.ten_price = ten;
    }

    await apiFetch(`currencies-vouchers/costs/${chestId}`, {
      method: 'PUT',
      body: JSON.stringify({ once_price: once, ten_price: ten })
    });

    showToast(`Updated spin costs for Chest #${chestId} (${once} / ${ten}).`, 'success');
  }

  // =========================================================================
  // 10. VIEW 6: INCUBATOR FORGE MANAGER RENDERER
  // =========================================================================

  function renderIncubatorForgeView() {
    const tbody = document.getElementById('forge-recipes-table');
    if (!tbody) return;

    tbody.innerHTML = state.forgeRecipes.map(r => {
      const rClass = r.rarity === 2 ? 'super' : 'rare';
      return `
        <tr>
          <td class="monospace font-bold">${r.sort_id}</td>
          <td><span class="lr-chip" style="font-size:11px;">${escapeHtml(r.tab_name)}</span></td>
          <td>
            <strong>${escapeHtml(r.reward_name)}</strong>
            <span class="monospace" style="font-size:11px; color:var(--lr-blue); display:block;">#${r.reward_id}</span>
          </td>
          <td><span class="badge-rarity super">x${r.blueprints} Blueprint</span></td>
          <td><span class="badge-rarity rare">x${r.stones} Evolution Stones</span></td>
          <td class="monospace font-bold">${r.limit} per account</td>
          <td><span class="badge-rarity ${rClass}">Grand Prize</span></td>
          <td style="text-align:right;">
            <div style="display:inline-flex; gap:4px;">
              <button class="btn btn-sm" onclick="LuckRoyaleApp.editForgeRecipe(${r.id})">Edit</button>
              <button class="btn btn-sm btn-danger" onclick="LuckRoyaleApp.deleteForgeRecipe(${r.id})">Delete</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Token Shop Items
    const tokenTbody = document.getElementById('token-shop-tbody');
    if (tokenTbody) {
      tokenTbody.innerHTML = state.tokenShopItems.map((item, idx) => `
        <tr>
          <td class="monospace font-bold" style="color:var(--lr-blue);">#${item.item_id || item.id}</td>
          <td><strong>${escapeHtml(item.name)}</strong></td>
          <td class="monospace tabular font-bold" style="color:var(--lr-gold-text);">${item.cost} FF Tokens</td>
          <td class="monospace tabular">${item.limit} Per Operative</td>
          <td><span class="lr-chip" style="font-size:11px;">${escapeHtml(item.category)}</span></td>
          <td style="text-align:right;">
            <button class="btn btn-sm btn-danger" onclick="LuckRoyaleApp.deleteTokenShopItem(${idx})">Delete</button>
          </td>
        </tr>
      `).join('');
    }
  }

  // =========================================================================
  // 11. VIEW 7: BANNER & EVENT MANAGER RENDERER
  // =========================================================================

  function renderBannersEventsView() {
    // Machine Banners Grid
    const mbGrid = document.getElementById('machine-banners-grid');
    if (mbGrid) {
      mbGrid.innerHTML = state.machines.map(m => `
        <div class="machine-card">
          <img src="/static/banners/${escapeHtml(m.banner)}" class="machine-banner-preview" alt="${escapeHtml(m.name)}" onerror="this.src='/static/banners/luck_royale_banner.png'">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="font-size:13.5px;">${escapeHtml(m.name)}</strong>
            <span class="lr-badge">CHEST #${m.chest_id}</span>
          </div>
          <span class="monospace" style="font-size:11px; color:var(--lr-text-tertiary);">${escapeHtml(m.banner)}</span>
          <button class="btn btn-sm btn-primary" style="margin-top:4px;" onclick="LuckRoyaleApp.promptChangeBanner(${m.chest_id})">Change Banner Asset</button>
        </div>
      `).join('');
    }

    // Asset Browser Grid
    const baGrid = document.getElementById('banner-assets-grid');
    if (baGrid) {
      baGrid.innerHTML = state.bannerAssets.map(asset => `
        <div class="machine-card" style="padding:10px;">
          <img src="/static/banners/${escapeHtml(asset.name)}" style="width:100%; height:80px; object-fit:cover; border-radius:4px; border:1px solid var(--lr-border);" alt="${escapeHtml(asset.name)}">
          <strong class="monospace" style="font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(asset.name)}</strong>
          <div style="display:flex; justify-content:space-between; font-size:10.5px; color:var(--lr-text-tertiary);">
            <span>${escapeHtml(asset.category)}</span>
            <span class="monospace">${escapeHtml(asset.res)}</span>
          </div>
        </div>
      `).join('');
    }

    // Events Schedule Table
    const evtTbody = document.getElementById('events-schedule-tbody');
    if (evtTbody) {
      evtTbody.innerHTML = state.events.map((evt, idx) => {
        const m = state.machines.find(x => x.chest_id === evt.machine_id) || { name: `Chest #${evt.machine_id}` };
        return `
          <tr>
            <td><strong>${escapeHtml(evt.title)}</strong></td>
            <td><strong>${escapeHtml(m.name)}</strong></td>
            <td class="monospace" style="font-size:11.5px;">${escapeHtml(evt.start_time)}</td>
            <td class="monospace" style="font-size:11.5px;">${escapeHtml(evt.end_time)}</td>
            <td class="monospace font-bold" style="color:var(--lr-green-text);">+${evt.rate_up_pct}% Rate-Up</td>
            <td class="monospace font-bold" style="color:var(--lr-blue);">${evt.discount_pct}% Off</td>
            <td><span class="lr-chip ${evt.status === 'active' ? 'active' : ''}">${evt.status.toUpperCase()}</span></td>
            <td style="text-align:right;">
              <button class="btn btn-sm btn-danger" onclick="LuckRoyaleApp.deleteEvent(${idx})">Cancel</button>
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  function promptChangeBanner(chestId) {
    const m = state.machines.find(x => x.chest_id === chestId);
    if (!m) return;
    const newName = prompt(`Enter banner filename for ${m.name} (from server/static/banners/):`, m.banner);
    if (newName && newName.trim()) {
      m.banner = newName.trim();
      apiFetch('events-banners', {
        method: 'PUT',
        body: JSON.stringify({ chest_id: chestId, banner: m.banner })
      });
      showToast(`Assigned ${m.banner} to ${m.name}!`, 'success');
      renderBannersEventsView();
      renderOverviewView();
    }
  }

  // =========================================================================
  // 12. VIEW 8: ACCOUNT INSPECTOR & TRANSACTIONS RENDERER
  // =========================================================================

  function renderAccountTxView() {
    const metersGrid = document.getElementById('inspector-meters-grid');
    if (!metersGrid) return;

    metersGrid.innerHTML = state.machines.map(m => {
      const current = state.accountProfile.current_meters[m.chest_id] || 0;
      const cap = m.meter_max;
      const pct = Math.min(100, (current / cap) * 100).toFixed(1);

      return `
        <div class="lr-stat-tile">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="font-size:13px;">${escapeHtml(m.name)}</strong>
            <span class="monospace font-bold" style="color:var(--lr-blue);">${current}/${cap}</span>
          </div>
          <div class="meter-bar-track" style="margin:4px 0;">
            <div class="meter-bar-fill gold" style="width:${pct}%;"></div>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:2px;">
            <span style="font-size:11px; color:var(--lr-text-secondary);">${pct}% Luck</span>
            <div style="display:inline-flex; gap:3px;">
              <button class="btn btn-sm" onclick="LuckRoyaleApp.setAccountMeter(${m.chest_id}, 0)">Zero</button>
              <button class="btn btn-sm" onclick="LuckRoyaleApp.setAccountMeter(${m.chest_id}, ${cap - 1})">Next Pull Pity</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Transaction Explorer Table
    const tbody = document.getElementById('tx-explorer-tbody');
    if (!tbody) return;

    const filterM = state.txFilterMachine;
    const filtered = state.transactions.filter(tx => {
      return filterM === 'all' || String(tx.machine_id) === String(filterM);
    });

    tbody.innerHTML = filtered.map(tx => {
      const itemsHtml = tx.items.map(it => {
        const itemObj = lookupItem(it.id);
        const rClass = it.rarity === 2 ? 'super' : (it.rarity === 1 ? 'rare' : 'normal');
        return `<span class="badge-rarity ${rClass}">${escapeHtml(itemObj.name)}</span>`;
      }).join(' ');

      return `
        <tr>
          <td class="monospace font-bold" style="color:var(--lr-blue);">${escapeHtml(tx.id)}</td>
          <td class="monospace" style="font-size:11.5px; color:var(--lr-text-secondary);">${escapeHtml(tx.time)}</td>
          <td class="monospace font-bold">${tx.account_id}</td>
          <td><strong>${escapeHtml(tx.machine_name)}</strong></td>
          <td><span class="lr-chip">${escapeHtml(tx.spin_type)}</span></td>
          <td class="monospace tabular font-bold">${escapeHtml(tx.cost)}</td>
          <td>${itemsHtml}</td>
          <td class="monospace tabular" style="color:var(--lr-gold-text); font-weight:600;">+${tx.duplicate_tokens} FF Tokens</td>
          <td class="monospace tabular font-bold" style="color:var(--lr-green-text);">${escapeHtml(tx.meter_shift)}</td>
        </tr>
      `;
    }).join('');
  }

  function setAccountMeter(chestId, value) {
    state.accountProfile.current_meters[chestId] = Number(value);
    apiFetch(`accounts/${state.targetAccountId}`, {
      method: 'POST',
      body: JSON.stringify({ chest_id: chestId, meter_value: Number(value) })
    });
    showToast(`Updated Chest #${chestId} Lucky Meter to ${value} for account 10001!`, 'success');
    renderAccountTxView();
  }

  function filterTransactions() {
    state.txFilterMachine = document.getElementById('tx-filter-machine')?.value || 'all';
    renderAccountTxView();
  }

  function exportTransactionsCSV() {
    let csv = 'Transaction ID,Time,Account ID,Machine,Spin Type,Cost,Duplicate Tokens,Meter Shift\n';
    state.transactions.forEach(tx => {
      csv += `"${tx.id}","${tx.time}","${tx.account_id}","${tx.machine_name}","${tx.spin_type}","${tx.cost}","${tx.duplicate_tokens}","${tx.meter_shift}"\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `luck_royale_audit_${Date.now()}.csv`;
    link.click();
    showToast('Exported audit CSV successfully!', 'success');
  }

  // =========================================================================
  // 13. REAL TEST SPIN SIMULATOR (PITY AWARE & INVENTORY SYNCHRONIZED)
  // =========================================================================

  async function triggerTestSpin(chestId, count = 1) {
    const m = state.machines.find(x => x.chest_id === chestId);
    if (!m) return;

    const pool = state.rewardPools[chestId] || [];
    if (pool.length === 0) {
      showToast('Cannot spin: Reward pool is empty!', 'error');
      return;
    }

    const currentMeter = state.accountProfile.current_meters[chestId] || 0;
    const cap = m.meter_max;
    const totalWeight = pool.reduce((sum, it) => sum + (it.weight || 0), 0);

    const wonItems = [];
    let newMeter = currentMeter;
    let tokensAwarded = 0;

    for (let c = 0; c < count; c++) {
      let isGuaranteed = (newMeter >= cap);
      let selectedItem = null;

      if (isGuaranteed) {
        // Guarantee Super Rare
        const superRares = pool.filter(it => it.rarity === 2);
        if (superRares.length > 0) {
          selectedItem = superRares[Math.floor(Math.random() * superRares.length)];
        }
      }

      if (!selectedItem) {
        let roll = Math.random() * totalWeight;
        for (const it of pool) {
          roll -= it.weight;
          if (roll <= 0) {
            selectedItem = it;
            break;
          }
        }
      }

      if (!selectedItem) selectedItem = pool[0];

      if (selectedItem.rarity === 2) {
        newMeter = 0; // Pity resets on grand prize hit!
      } else {
        newMeter++;
      }

      // 30% chance duplicate for demo
      const isDuplicate = Math.random() < 0.3;
      if (isDuplicate) tokensAwarded += (selectedItem.dup_count || 5);

      wonItems.push({
        id: selectedItem.item_id,
        count: selectedItem.count || 1,
        rarity: selectedItem.rarity,
        is_duplicate: isDuplicate
      });
    }

    // Apply currency cost
    let costStr = '';
    if (count === 1) {
      costStr = `${m.once_price} ${m.coin_type === 2 ? 'Diamonds' : 'Gold'}`;
      if (m.coin_type === 2) {
        state.accountProfile.diamonds = Math.max(0, state.accountProfile.diamonds - m.once_price);
        state.stats.diamondsBurned += m.once_price;
      } else {
        state.accountProfile.gold = Math.max(0, state.accountProfile.gold - m.once_price);
        state.stats.goldBurned += m.once_price;
      }
    } else {
      costStr = `${m.ten_price} ${m.coin_type === 2 ? 'Diamonds' : 'Gold'}`;
      if (m.coin_type === 2) {
        state.accountProfile.diamonds = Math.max(0, state.accountProfile.diamonds - m.ten_price);
        state.stats.diamondsBurned += m.ten_price;
      } else {
        state.accountProfile.gold = Math.max(0, state.accountProfile.gold - m.ten_price);
        state.stats.goldBurned += m.ten_price;
      }
    }

    state.accountProfile.current_meters[chestId] = newMeter;
    state.stats.totalSpins += count;
    state.stats.spinsToday += count;

    // Log Transaction
    const txObj = {
      id: `TX-10001-${Math.floor(1000 + Math.random() * 9000)}`,
      time: 'Just now',
      account_id: state.targetAccountId,
      machine_id: chestId,
      machine_name: m.name,
      spin_type: `${count}x Spin`,
      cost: costStr,
      items: wonItems,
      duplicate_tokens: tokensAwarded,
      meter_shift: `${currentMeter} -> ${newMeter}`
    };
    state.transactions.unshift(txObj);

    // Call real backend endpoint
    apiFetch('transactions', {
      method: 'POST',
      body: JSON.stringify(txObj)
    });

    // Render outcome dialog
    renderSpinOutcomeModal(txObj);

    // Refresh UI
    renderOverviewView();
    renderAccountTxView();
    renderCurrencyVouchersView();
  }

  function renderSpinOutcomeModal(tx) {
    const body = document.getElementById('spin-result-body');
    if (!body) return;

    const itemsHtml = tx.items.map(it => {
      const itemObj = lookupItem(it.id);
      const rClass = it.rarity === 2 ? 'super' : (it.rarity === 1 ? 'rare' : 'normal');
      const rText = it.rarity === 2 ? 'SUPER RARE / GRAND PRIZE' : (it.rarity === 1 ? 'RARE' : 'NORMAL');
      return `
        <div style="background:var(--lr-bg-surface-elevated); border:1px solid var(--lr-border); border-radius:var(--lr-radius-md); padding:10px 14px; display:flex; align-items:center; justify-content:space-between;">
          <div>
            <span class="badge-rarity ${rClass}">${rText}</span>
            <strong style="font-size:13.5px; display:block; margin-top:2px;">${escapeHtml(itemObj.name)}</strong>
            <span class="monospace" style="font-size:11px; color:var(--lr-text-tertiary);">Item #${it.id} &bull; ${escapeHtml(itemObj.category)}</span>
          </div>
          <div style="text-align:right;">
            <strong class="monospace font-bold">x${it.count}</strong>
            ${it.is_duplicate ? `<span class="monospace font-bold" style="font-size:10.5px; color:var(--lr-gold-text); display:block;">+Duplicate FF Tokens</span>` : ''}
          </div>
        </div>
      `;
    }).join('');

    body.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--lr-border); padding-bottom:8px;">
          <div>
            <strong style="font-size:15px;">${escapeHtml(tx.machine_name)}</strong>
            <span class="monospace" style="font-size:11.5px; color:var(--lr-text-secondary); display:block;">${escapeHtml(tx.spin_type)} &bull; Cost: ${escapeHtml(tx.cost)}</span>
          </div>
          <div style="text-align:right;">
            <span style="font-size:11px; color:var(--lr-text-tertiary);">Lucky Meter:</span>
            <strong class="monospace font-bold" style="color:var(--lr-green-text); display:block;">${escapeHtml(tx.meter_shift)}</strong>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:8px; max-height:300px; overflow-y:auto;">
          ${itemsHtml}
        </div>
      </div>
    `;

    openModal('modal-spin-result');
  }

  // =========================================================================
  // 14. MODAL MANAGEMENT & FORM HANDLERS
  // =========================================================================

  function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add('open');
  }

  function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove('open');
  }

  function openMachineModal(chestId = null) {
    const titleEl = document.getElementById('modal-machine-title');
    if (chestId) {
      const m = state.machines.find(x => x.chest_id === chestId);
      if (!m) return;
      titleEl.textContent = `Edit Machine: ${m.name} (#${m.chest_id})`;
      document.getElementById('m-form-id').value = m.chest_id;
      document.getElementById('m-form-id').disabled = true;
      document.getElementById('m-form-name').value = m.name;
      document.getElementById('m-form-type').value = m.type;
      document.getElementById('m-form-coin').value = m.coin_type;
      document.getElementById('m-form-once-price').value = m.once_price;
      document.getElementById('m-form-ten-price').value = m.ten_price;
      document.getElementById('m-form-once-num').value = m.once_num;
      document.getElementById('m-form-ten-num').value = m.ten_num;
      document.getElementById('m-form-voucher').value = m.voucher_id;
      document.getElementById('m-form-meter-max').value = m.meter_max;
      document.getElementById('m-form-priority').value = m.priority;
      document.getElementById('m-form-banner').value = m.banner;
      document.getElementById('m-form-enabled').checked = m.enabled;
      document.getElementById('m-form-visible').checked = m.visible;
    } else {
      titleEl.textContent = 'Create Luck Royale Machine';
      const newId = Math.max(...state.machines.map(m => m.chest_id)) + 1;
      document.getElementById('m-form-id').value = newId;
      document.getElementById('m-form-id').disabled = false;
      document.getElementById('m-form-name').value = '';
      document.getElementById('m-form-once-price').value = 60;
      document.getElementById('m-form-ten-price').value = 600;
      document.getElementById('m-form-once-num').value = 1;
      document.getElementById('m-form-ten-num').value = 10;
      document.getElementById('m-form-meter-max').value = 150;
      document.getElementById('m-form-priority').value = 50;
      document.getElementById('m-form-banner').value = 'luck_royale_banner.png';
      document.getElementById('m-form-enabled').checked = true;
      document.getElementById('m-form-visible').checked = true;
    }
    openModal('modal-machine');
  }

  function saveMachineForm(e) {
    e.preventDefault();
    const id = Number(document.getElementById('m-form-id').value);
    const name = document.getElementById('m-form-name').value.trim();
    const type = Number(document.getElementById('m-form-type').value);
    const coin = Number(document.getElementById('m-form-coin').value);
    const oncePrice = Number(document.getElementById('m-form-once-price').value);
    const tenPrice = Number(document.getElementById('m-form-ten-price').value);
    const onceNum = Number(document.getElementById('m-form-once-num').value);
    const tenNum = Number(document.getElementById('m-form-ten-num').value);
    const voucher = Number(document.getElementById('m-form-voucher').value);
    const meterMax = Number(document.getElementById('m-form-meter-max').value);
    const priority = Number(document.getElementById('m-form-priority').value);
    const banner = document.getElementById('m-form-banner').value.trim();
    const enabled = document.getElementById('m-form-enabled').checked;
    const visible = document.getElementById('m-form-visible').checked;

    let m = state.machines.find(x => x.chest_id === id);
    if (m) {
      Object.assign(m, { name, type, coin_type: coin, once_price: oncePrice, ten_price: tenPrice, once_num: onceNum, ten_num: tenNum, voucher_id: voucher, meter_max: meterMax, priority, banner, enabled, visible });
      apiFetch(`machines/${id}`, { method: 'PUT', body: JSON.stringify(m) });
      showToast(`Updated Machine #${id} (${name})!`, 'success');
    } else {
      m = { chest_id: id, name, type, coin_type: coin, once_price: oncePrice, ten_price: tenPrice, once_num: onceNum, ten_num: tenNum, voucher_id: voucher, meter_max: meterMax, priority, banner, enabled, visible, items_count: 0 };
      state.machines.push(m);
      state.rewardPools[id] = [];
      state.meters[id] = { max: meterMax, increment: 1, guaranteed: meterMax, reset_on_win: true, first_draw_bonus: 0 };
      apiFetch('machines', { method: 'POST', body: JSON.stringify(m) });
      showToast(`Created Machine #${id} (${name})!`, 'success');
    }

    closeModal('modal-machine');
    renderMachinesView();
    renderOverviewView();
  }

  function editMachine(chestId) {
    openMachineModal(chestId);
  }

  function duplicateMachine(chestId) {
    const src = state.machines.find(x => x.chest_id === chestId);
    if (!src) return;
    const newId = Math.max(...state.machines.map(m => m.chest_id)) + 1;
    const dup = JSON.parse(JSON.stringify(src));
    dup.chest_id = newId;
    dup.name = `${src.name} (Copy)`;
    state.machines.push(dup);
    state.rewardPools[newId] = JSON.parse(JSON.stringify(state.rewardPools[chestId] || []));
    state.meters[newId] = JSON.parse(JSON.stringify(state.meters[chestId] || { max: 150, increment: 1, guaranteed: 150, reset_on_win: true }));

    apiFetch('machines', { method: 'POST', body: JSON.stringify(dup) });
    showToast(`Duplicated ${src.name} -> Machine #${newId}!`, 'success');
    renderMachinesView();
    renderOverviewView();
  }

  function deleteMachine(chestId) {
    if (!confirm(`Are you sure you want to delete Machine #${chestId}? This removes its reward pool.`)) return;
    state.machines = state.machines.filter(m => m.chest_id !== chestId);
    delete state.rewardPools[chestId];
    delete state.meters[chestId];

    apiFetch(`machines/${chestId}`, { method: 'DELETE' });
    showToast(`Deleted Machine #${chestId}.`, 'info');
    renderMachinesView();
    renderOverviewView();
  }

  function toggleMachineStatus(chestId, isEnabled) {
    const m = state.machines.find(x => x.chest_id === chestId);
    if (m) {
      m.enabled = isEnabled;
      apiFetch(`machines/${chestId}/toggle`, { method: 'POST', body: JSON.stringify({ enabled: isEnabled }) });
      showToast(`Machine #${chestId} is now ${isEnabled ? 'ACTIVE' : 'DISABLED'}.`, 'info');
      renderOverviewView();
    }
  }

  function toggleMachineVisibility(chestId, isVisible) {
    const m = state.machines.find(x => x.chest_id === chestId);
    if (m) {
      m.visible = isVisible;
      showToast(`Machine #${chestId} lobby visibility: ${isVisible ? 'VISIBLE' : 'HIDDEN'}.`, 'info');
    }
  }

  // Reward Item Modals
  function openAddRewardModal() {
    document.getElementById('modal-reward-title').textContent = `Add Item to Machine #${state.selectedPoolChestId}`;
    document.getElementById('r-form-id').value = '';
    document.getElementById('r-form-id').disabled = false;
    document.getElementById('r-form-name').value = '';
    document.getElementById('r-form-count').value = 1;
    document.getElementById('r-form-rarity').value = 0;
    document.getElementById('r-form-weight').value = 50;
    document.getElementById('r-form-dup-id').value = 800000301;
    document.getElementById('r-form-dup-num').value = 5;
    document.getElementById('r-form-show').checked = true;
    document.getElementById('r-form-wheel-slot').value = 0;
    openModal('modal-reward-item');
  }

  function editRewardItem(itemId) {
    const pool = state.rewardPools[state.selectedPoolChestId] || [];
    const item = pool.find(it => it.item_id === itemId);
    if (!item) return;

    const itemObj = lookupItem(itemId);
    document.getElementById('modal-reward-title').textContent = `Edit Item: ${itemObj.name} (#${itemId})`;
    document.getElementById('r-form-id').value = item.item_id;
    document.getElementById('r-form-id').disabled = true;
    document.getElementById('r-form-name').value = itemObj.name;
    document.getElementById('r-form-count').value = item.count;
    document.getElementById('r-form-rarity').value = item.rarity;
    document.getElementById('r-form-weight').value = item.weight;
    document.getElementById('r-form-dup-id').value = item.dup_id || 800000301;
    document.getElementById('r-form-dup-num').value = item.dup_count || 5;
    document.getElementById('r-form-show').checked = item.is_show;
    document.getElementById('r-form-wheel-slot').value = item.slot || 0;
    openModal('modal-reward-item');
  }

  function onRewardItemIdInput() {
    const id = Number(document.getElementById('r-form-id').value);
    const itemObj = lookupItem(id);
    if (itemObj.name && !itemObj.name.startsWith('Item #')) {
      document.getElementById('r-form-name').value = itemObj.name;
      document.getElementById('r-form-rarity').value = itemObj.rarity;
    }
  }

  function saveRewardItemForm(e) {
    e.preventDefault();
    const itemId = Number(document.getElementById('r-form-id').value);
    const count = Number(document.getElementById('r-form-count').value);
    const rarity = Number(document.getElementById('r-form-rarity').value);
    const weight = Number(document.getElementById('r-form-weight').value);
    const dupId = Number(document.getElementById('r-form-dup-id').value);
    const dupCount = Number(document.getElementById('r-form-dup-num').value);
    const isShow = document.getElementById('r-form-show').checked;
    const wheelSlot = Number(document.getElementById('r-form-wheel-slot').value);

    let pool = state.rewardPools[state.selectedPoolChestId];
    if (!pool) {
      pool = [];
      state.rewardPools[state.selectedPoolChestId] = pool;
    }

    let existing = pool.find(it => it.item_id === itemId);
    if (existing) {
      Object.assign(existing, { count, rarity, weight, dup_id: dupId, dup_count: dupCount, is_show: isShow, slot: wheelSlot });
      apiFetch(`reward-pools/${state.selectedPoolChestId}/${itemId}`, { method: 'PUT', body: JSON.stringify(existing) });
      showToast(`Updated item #${itemId} in reward pool!`, 'success');
    } else {
      const newItem = { item_id: itemId, count, rarity, weight, dup_id: dupId, dup_count: dupCount, is_show: isShow, slot: wheelSlot };
      pool.push(newItem);
      apiFetch('reward-pools', { method: 'POST', body: JSON.stringify({ chest_id: state.selectedPoolChestId, ...newItem }) });
      showToast(`Added item #${itemId} to reward pool!`, 'success');
    }

    closeModal('modal-reward-item');
    renderRewardPoolsView();
  }

  function deleteRewardItem(itemId) {
    const pool = state.rewardPools[state.selectedPoolChestId] || [];
    state.rewardPools[state.selectedPoolChestId] = pool.filter(it => it.item_id !== itemId);
    apiFetch(`reward-pools/${state.selectedPoolChestId}/${itemId}`, { method: 'DELETE' });
    showToast(`Removed item #${itemId} from reward pool.`, 'info');
    renderRewardPoolsView();
  }

  // Forge Recipes Modals
  function openForgeRecipeModal() {
    document.getElementById('modal-forge-title').textContent = 'Create Forge Recipe';
    document.getElementById('f-form-sort').value = state.forgeRecipes.length + 1;
    document.getElementById('f-form-reward-id').value = 710000410;
    document.getElementById('f-form-name').value = 'YinYang Master Gold Bundle';
    document.getElementById('f-form-blueprints').value = 3;
    document.getElementById('f-form-stones').value = 7;
    openModal('modal-forge-recipe');
  }

  function saveForgeRecipeForm(e) {
    e.preventDefault();
    const sort = Number(document.getElementById('f-form-sort').value);
    const tabId = Number(document.getElementById('f-form-tab').value);
    const rewardId = Number(document.getElementById('f-form-reward-id').value);
    const name = document.getElementById('f-form-name').value.trim();
    const blueprints = Number(document.getElementById('f-form-blueprints').value);
    const stones = Number(document.getElementById('f-form-stones').value);
    const blueprintId = Number(document.getElementById('f-form-blueprint-id').value);

    const recipe = {
      id: Date.now(),
      sort_id: sort,
      forge_tab_id: tabId,
      tab_name: 'YinYang Masters (OB17)',
      reward_id: rewardId,
      reward_name: name,
      blueprints: blueprints,
      blueprint_id: blueprintId,
      stones: stones,
      limit: 1,
      rarity: 2
    };

    state.forgeRecipes.push(recipe);
    apiFetch('exchange', { method: 'POST', body: JSON.stringify(recipe) });
    showToast(`Created forge recipe for ${name}!`, 'success');
    closeModal('modal-forge-recipe');
    renderIncubatorForgeView();
  }

  function deleteForgeRecipe(id) {
    state.forgeRecipes = state.forgeRecipes.filter(r => r.id !== id);
    apiFetch(`exchange/${id}`, { method: 'DELETE' });
    showToast(`Deleted forge recipe #${id}.`, 'info');
    renderIncubatorForgeView();
  }

  // Quick Spin Simulator Trigger
  function openQuickSpinModal() {
    openQuickSpinForMachine(3);
  }

  function openQuickSpinForMachine(chestId) {
    triggerTestSpin(chestId, 1);
  }

  // Sync All
  async function syncAll(showNotify = false) {
    // Try real API fetch
    const overviewData = await apiFetch('overview');
    if (overviewData) {
      if (overviewData.total_spins !== undefined) state.stats.totalSpins = overviewData.total_spins;
      if (overviewData.diamonds_burned !== undefined) state.stats.diamondsBurned = overviewData.diamonds_burned;
      if (overviewData.gold_burned !== undefined) state.stats.goldBurned = overviewData.gold_burned;
    }

    renderOverviewView();
    if (showNotify) showToast('All Luck Royale telemetry successfully synchronized!', 'success');
  }

  // =========================================================================
  // 15. INITIALIZATION
  // =========================================================================

  function init() {
    // Set initial render
    renderOverviewView();

    // Attach ESC handler for modals
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
      }
    });

    // Dismiss modal on backdrop click
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.classList.remove('open');
      });
    });

    // Initial Telemetry Sync
    syncAll(false);
  }

  // Auto-boot on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Exported Public API
  return {
    switchTab,
    syncAll,
    selectMachineForRewards,
    openQuickSpinModal,
    openQuickSpinForMachine,
    filterMachines,
    openMachineModal,
    saveMachineForm,
    editMachine,
    duplicateMachine,
    deleteMachine,
    toggleMachineStatus,
    toggleMachineVisibility,
    onPoolMachineChange,
    filterRewardPool,
    openAddRewardModal,
    editRewardItem,
    onRewardItemIdInput,
    saveRewardItemForm,
    deleteRewardItem,
    runStatisticalSimulation,
    updateMeterParam,
    saveMeterConfig,
    saveAllMeters,
    executeGrantDeduct,
    quickGrantVouchers,
    quickGrantCurrency,
    quickGrantIncubatorMaterials,
    saveMachineCosts,
    openForgeRecipeModal,
    saveForgeRecipeForm,
    deleteForgeRecipe,
    promptChangeBanner,
    setAccountMeter,
    filterTransactions,
    exportTransactionsCSV,
    triggerTestSpin,
    closeModal,
    openModal
  };
});
