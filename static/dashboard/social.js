/**
 * India V1 1.39 - Mail Dispatch & Social Operations Engine (social.js)
 * Viewport-fitted, high-performance dashboard component for:
 *   - Rich Mail Composer with claimable Gold, Diamonds, and Item attachments
 *   - Live In-Game Letterhead & Envelope Preview Simulator
 *   - In-Game Mailbox Inspector & Instant Reward Claiming Terminal
 *   - Online Friends Directory with live status badges and server status simulator
 *   - Squad Lobby Controller (4-slot roster, ready states, create/disband)
 *   - Instant TCP Squad Invite Trigger (pushes GroupInviteNtf over port 8081)
 *
 * Compliance: Strictly ZERO emojis. Clean typography, subtle badges, and SVG line icons.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.SocialSection = factory();
    // Backward compatibility bindings for external dashboard caller
    root.loadMailList = function() { root.SocialSection.loadMailbox(); };
    root.sendCustomMail = function() { root.SocialSection.dispatchMail(); };
    root.loadFriends = function() { root.SocialSection.loadFriends(); };
    root.sendSquadInvite = function() { root.SocialSection.triggerTcpSquadInvite(); };
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Item Presets Metadata Catalog
  const ITEM_CATALOG = {
    907100001: { name: 'Weapon Royale Crate', cat: 'Loot Crate' },
    700000001: { name: 'Elite Pass Badge Token', cat: 'Pass Token' },
    901000001: { name: 'Season Founder Banner', cat: 'Banner' },
    902000001: { name: 'Cyber Soldier Avatar', cat: 'Avatar' },
    203000001: { name: 'Tactical Combat Jacket', cat: 'Costume Top' },
    204000001: { name: 'Spec-Ops Tactical Pants', cat: 'Costume Bottom' },
    205000001: { name: 'High-Top Combat Sneakers', cat: 'Shoes' },
    908000001: { name: 'Level 3 Tactical Backpack', cat: 'Backpack' },
    910000001: { name: 'Neon Surfboard', cat: 'Surfboard' },
    909000001: { name: 'Blackout Parachute', cat: 'Parachute' },
    911000001: { name: 'Cyber Death Box', cat: 'Loot Box' },
  };

  // Pre-Seeded Recommended Bots Metadata
  const BOT_ROSTER = [
    { uid: 20001, nick: 'IndiaV1_Bot', role: 'Server Bot', level: 65, status: 1 },
    { uid: 20002, nick: 'Kelly_Dash', role: 'Speed Runner', level: 58, status: 1 },
    { uid: 20003, nick: 'Hayato_Blade', role: 'Samurai Leader', level: 62, status: 1 },
    { uid: 20004, nick: 'Kla_OnePunch', role: 'Muay Thai Boxer', level: 54, status: 2 },
    { uid: 20005, nick: 'Paloma_Arms', role: 'Arms Dealer', level: 51, status: 3 },
    { uid: 20006, nick: 'Moco_Eye', role: 'Hacker Specialist', level: 49, status: 0 },
    { uid: 20007, nick: 'Laura_Sniper', role: 'Sharpshooter', level: 61, status: 1 },
    { uid: 20008, nick: 'Rafael_Silent', role: 'Dead Silent', level: 56, status: 1 },
    { uid: 20009, nick: 'A124_Android', role: 'Thrill of Battle', level: 47, status: 0 },
    { uid: 20010, nick: 'Alok_DJ', role: 'Drop the Beat', level: 60, status: 1 },
  ];

  // Component Internal Reactive State
  const state = {
    activeTab: 'mail-composer',
    targetAccountId: 10001,
    composer: {
      recipient_uid: 10001,
      sender_nick: 'India V1 Operations',
      mail_type: 3,
      title: 'Welcome Care Package & Elite Pass Drop',
      content: 'Welcome to India V1 1.39 Server! Claim your exclusive gold, diamonds, and rare cosmetic loadout below. Ready up and join the squad!',
      coins: 50000,
      gems: 2500,
      attachments: [
        { item_id: 907100001, count: 1, type: 1 },
        { item_id: 700000001, count: 1, type: 1 }
      ]
    },
    mailbox: {
      items: [],
      selectedMailId: null,
      filterQuery: '',
      filterStatus: 'unclaimed'
    },
    friends: {
      items: [],
      requests: [],
      recommended: [],
      allPlayers: [],
      filterQuery: '',
      filterStatus: '1'
    },
    squad: {
      team: null,
      invitations: [],
      invitableFriends: [],
      rooms: []
    },
    tcpLogs: [
      {
        time: new Date().toLocaleTimeString(),
        badge: 'READY',
        text: 'TCP Server port 8081 ready for GroupInviteNtf instant dispatch.'
      }
    ]
  };

  /* ==========================================================================
     API CLIENT UTILITIES
     ========================================================================== */
  async function apiGet(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      console.error(`[SocialAPI] GET ${path} failed:`, err);
      return { ok: false, error: err.message };
    }
  }

  async function apiPost(path, body) {
    try {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      console.error(`[SocialAPI] POST ${path} failed:`, err);
      return { ok: false, error: err.message };
    }
  }

  function showToast(message, type = 'info') {
    const box = document.getElementById('s-toast-box');
    if (!box) return;

    const toast = document.createElement('div');
    toast.className = 's-toast-msg';

    let strokeColor = 'var(--s-cyan)';
    if (type === 'success') strokeColor = 'var(--s-green)';
    if (type === 'error') strokeColor = 'var(--s-rose)';
    if (type === 'gold') strokeColor = 'var(--s-gold)';

    toast.innerHTML = `
      <svg width="14" height="14" fill="none" stroke="${strokeColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
      <span>${escapeHtml(message)}</span>
    `;

    box.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s, transform 0.3s';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(8px)';
      setTimeout(() => toast.remove(), 320);
    }, 2800);
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

  function formatNumber(num) {
    return Number(num || 0).toLocaleString();
  }

  function formatTimestamp(ts) {
    if (!ts) return 'Unknown';
    const date = new Date(ts > 1e11 ? ts : ts * 1000);
    return date.toLocaleTimeString() + ' (' + date.toLocaleDateString() + ')';
  }

  /* ==========================================================================
     SUB-TAB SWITCHING
     ========================================================================== */
  function switchSubTab(tabKey) {
    state.activeTab = tabKey;

    document.querySelectorAll('.s-subtab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.s-subtab-pane').forEach(pane => pane.classList.remove('active'));

    const btn = document.getElementById(`tabbtn-${tabKey}`);
    const pane = document.getElementById(`pane-${tabKey}`);

    if (btn) btn.classList.add('active');
    if (pane) pane.classList.add('active');

    // Trigger tab-specific refresh
    if (tabKey === 'mail-composer') {
      renderAttachmentChips();
      renderEnvelopePreview();
    } else if (tabKey === 'mailbox-inspector') {
      loadMailbox();
    } else if (tabKey === 'friends-roster') {
      loadFriends();
    } else if (tabKey === 'squad-lobby') {
      loadSquad();
    }
  }

  function refreshCurrentTab() {
    if (state.activeTab === 'mail-composer') {
      renderAttachmentChips();
      renderEnvelopePreview();
      showToast('Composer preview updated', 'info');
    } else if (state.activeTab === 'mailbox-inspector') {
      loadMailbox();
    } else if (state.activeTab === 'friends-roster') {
      loadFriends();
    } else if (state.activeTab === 'squad-lobby') {
      loadSquad();
    }
  }

  /* ==========================================================================
     SUB-TAB 1: MAIL COMPOSER LOGIC
     ========================================================================== */
  function onComposerFieldChange() {
    const uidEl = document.getElementById('comp-recipient-uid');
    const nickEl = document.getElementById('comp-sender-nick');
    const typeEl = document.getElementById('comp-mail-type');
    const titleEl = document.getElementById('comp-mail-title');
    const bodyEl = document.getElementById('comp-mail-body');
    const coinsEl = document.getElementById('comp-coins');
    const gemsEl = document.getElementById('comp-gems');

    state.composer.recipient_uid = Number(uidEl ? uidEl.value : 10001);
    state.composer.sender_nick = nickEl ? nickEl.value : 'India V1 Operations';
    state.composer.mail_type = Number(typeEl ? typeEl.value : 3);
    state.composer.title = titleEl ? titleEl.value : '';
    state.composer.content = bodyEl ? bodyEl.value : '';
    state.composer.coins = Math.max(0, Number(coinsEl ? coinsEl.value : 0));
    state.composer.gems = Math.max(0, Number(gemsEl ? gemsEl.value : 0));

    // Update mini formatted labels
    const goldFmt = document.getElementById('gold-preview-formatted');
    if (goldFmt) goldFmt.textContent = '+' + formatNumber(state.composer.coins);

    const gemsFmt = document.getElementById('gems-preview-formatted');
    if (gemsFmt) gemsFmt.textContent = '+' + formatNumber(state.composer.gems);

    const targetBadge = document.getElementById('composer-account-badge');
    if (targetBadge) targetBadge.textContent = `Target: ${state.composer.recipient_uid}`;

    renderEnvelopePreview();
  }

  function addCurrency(type, delta) {
    const input = document.getElementById(`comp-${type}`);
    if (!input) return;
    const current = Math.max(0, Number(input.value || 0));
    input.value = current + delta;
    onComposerFieldChange();
  }

  function setCurrency(type, val) {
    const input = document.getElementById(`comp-${type}`);
    if (!input) return;
    input.value = Math.max(0, val);
    onComposerFieldChange();
  }

  function onItemPresetSelected() {
    const presetEl = document.getElementById('comp-item-preset');
    if (!presetEl || !presetEl.value) return;
    const countEl = document.getElementById('comp-item-count');
    if (countEl && Number(countEl.value) <= 0) {
      countEl.value = 1;
    }
  }

  function addAttachmentItem() {
    const presetEl = document.getElementById('comp-item-preset');
    const countEl = document.getElementById('comp-item-count');
    if (!presetEl || !presetEl.value) {
      showToast('Select an item from the preset list', 'error');
      return;
    }

    const itemId = Number(presetEl.value);
    const count = Math.max(1, Number(countEl ? countEl.value : 1));

    // Check if already in list
    const existing = state.composer.attachments.find(a => a.item_id === itemId);
    if (existing) {
      existing.count += count;
    } else {
      state.composer.attachments.push({ item_id: itemId, count, type: 1 });
    }

    renderAttachmentChips();
    renderEnvelopePreview();
    showToast(`Attached ${count}x item #${itemId}`, 'success');
  }

  function removeAttachmentItem(index) {
    if (index >= 0 && index < state.composer.attachments.length) {
      state.composer.attachments.splice(index, 1);
      renderAttachmentChips();
      renderEnvelopePreview();
    }
  }

  function renderAttachmentChips() {
    const container = document.getElementById('comp-attachment-chips');
    const countLabel = document.getElementById('attachments-count-label');
    if (!container) return;

    if (countLabel) {
      countLabel.textContent = `${state.composer.attachments.length} Items Attached`;
    }

    if (!state.composer.attachments.length) {
      container.innerHTML = `<span style="font-size:11px; color:var(--s-text-dim); padding:4px;">No items attached. Choose from preset dropdown above.</span>`;
      return;
    }

    container.innerHTML = state.composer.attachments.map((att, idx) => {
      const meta = ITEM_CATALOG[att.item_id] || { name: `Item #${att.item_id}`, cat: 'Custom' };
      return `
        <div class="s-attachment-pill">
          <span>${escapeHtml(meta.name)} (${att.item_id}) &times;${att.count}</span>
          <button type="button" onclick="SocialSection.removeAttachmentItem(${idx})" title="Remove item">
            <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      `;
    }).join('');
  }

  function renderEnvelopePreview() {
    const c = state.composer;

    const prevType = document.getElementById('preview-type-tag');
    if (prevType) prevType.textContent = `TYPE ${c.mail_type}`;

    const prevAvatar = document.getElementById('prev-sender-avatar');
    if (prevAvatar) {
      prevAvatar.textContent = (c.sender_nick || 'OP').substring(0, 2).toUpperCase();
    }

    const prevNick = document.getElementById('prev-sender-nick');
    if (prevNick) prevNick.textContent = c.sender_nick || 'India V1 Operations';

    const prevTitle = document.getElementById('prev-mail-title');
    if (prevTitle) prevTitle.textContent = c.title || '(No Subject)';

    const prevBody = document.getElementById('prev-mail-body');
    if (prevBody) prevBody.textContent = c.content || '(No message content)';

    const rewardsContainer = document.getElementById('prev-rewards-container');
    if (!rewardsContainer) return;

    const rewards = [];
    if (c.coins > 0) {
      rewards.push(`
        <div class="s-reward-badge s-reward-gold">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/></svg>
          <span>${formatNumber(c.coins)} Gold</span>
        </div>
      `);
    }
    if (c.gems > 0) {
      rewards.push(`
        <div class="s-reward-badge s-reward-gems">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M6 3h12l4 6-10 12L2 9z"/><path d="M11 3 8 9l4 12 4-12-3-6"/></svg>
          <span>${formatNumber(c.gems)} Diamonds</span>
        </div>
      `);
    }
    c.attachments.forEach(att => {
      const meta = ITEM_CATALOG[att.item_id] || { name: `Item #${att.item_id}` };
      rewards.push(`
        <div class="s-reward-badge s-reward-item">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/></svg>
          <span>${escapeHtml(meta.name)} &times;${att.count}</span>
        </div>
      `);
    });

    if (!rewards.length) {
      rewardsContainer.innerHTML = `<span style="font-size:11px; color:var(--s-text-dim);">No rewards attached (Letter only).</span>`;
    } else {
      rewardsContainer.innerHTML = rewards.join('');
    }
  }

  function applyTemplate(key) {
    if (key === 'welcome') {
      state.composer.title = 'Welcome Recruit Care Package';
      state.composer.content = 'Welcome to the India V1 server! Here is a welcome pack of 50,000 Gold, 2,500 Diamonds, plus your exclusive Founder Banner and Soldier Avatar!';
      state.composer.coins = 50000;
      state.composer.gems = 2500;
      state.composer.mail_type = 2;
      state.composer.attachments = [
        { item_id: 901000001, count: 1, type: 1 },
        { item_id: 902000001, count: 1, type: 1 }
      ];
    } else if (key === 'compensation') {
      state.composer.title = 'Hotfix Maintenance Compensation Drop';
      state.composer.content = 'Thank you for your patience during server maintenance. Enjoy 100,000 Gold, 5,000 Diamonds, and 2x Weapon Royale Crates!';
      state.composer.coins = 100000;
      state.composer.gems = 5000;
      state.composer.mail_type = 3;
      state.composer.attachments = [
        { item_id: 907100001, count: 2, type: 1 }
      ];
    } else if (key === 'ranked') {
      state.composer.title = 'Ranked Grandmaster Season Rewards';
      state.composer.content = 'Congratulations on finishing the ranked season in Grandmaster! Here is your full Tactical Combat Suit, 250,000 Gold, and 15,000 Diamonds.';
      state.composer.coins = 250000;
      state.composer.gems = 15000;
      state.composer.mail_type = 3;
      state.composer.attachments = [
        { item_id: 203000001, count: 1, type: 1 },
        { item_id: 204000001, count: 1, type: 1 },
        { item_id: 205000001, count: 1, type: 1 }
      ];
    } else if (key === 'whale') {
      state.composer.title = 'Infinite Ops Founder Grants';
      state.composer.content = 'Direct developer ops package: 1,000,000 Gold, 100,000 Diamonds, 10x Elite Pass Tokens, and 5x Weapon Crates.';
      state.composer.coins = 1000000;
      state.composer.gems = 100000;
      state.composer.mail_type = 1;
      state.composer.attachments = [
        { item_id: 700000001, count: 10, type: 1 },
        { item_id: 907100001, count: 5, type: 1 }
      ];
    }

    // Sync input fields
    const titleEl = document.getElementById('comp-mail-title');
    const bodyEl = document.getElementById('comp-mail-body');
    const coinsEl = document.getElementById('comp-coins');
    const gemsEl = document.getElementById('comp-gems');
    const typeEl = document.getElementById('comp-mail-type');

    if (titleEl) titleEl.value = state.composer.title;
    if (bodyEl) bodyEl.value = state.composer.content;
    if (coinsEl) coinsEl.value = state.composer.coins;
    if (gemsEl) gemsEl.value = state.composer.gems;
    if (typeEl) typeEl.value = state.composer.mail_type;

    onComposerFieldChange();
    renderAttachmentChips();
    showToast(`Applied preset: ${key.toUpperCase()}`, 'success');
  }

  async function dispatchMail() {
    const c = state.composer;
    if (!c.title.trim()) {
      showToast('Mail title cannot be empty', 'error');
      return;
    }

    const payload = {
      account_id: c.recipient_uid,
      title: c.title.trim(),
      content: c.content.trim(),
      sender_nick: c.sender_nick.trim() || 'India V1 Admin',
      mail_type: c.mail_type,
      coins: c.coins,
      gems: c.gems,
      attachments: c.attachments
    };

    const res = await apiPost('/api/dashboard/mail/send', payload);
    if (res && res.ok) {
      showToast(`Mail #${res.mail ? res.mail.mail_id : 'NEW'} dispatched to player ${c.recipient_uid}!`, 'success');
      loadMailbox(); // refresh inbox in background
    } else {
      showToast('Dispatch failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  function resetComposer() {
    state.composer.title = 'Welcome Care Package & Elite Pass Drop';
    state.composer.content = 'Welcome to India V1 1.39 Server! Claim your exclusive gold, diamonds, and rare cosmetic loadout below. Ready up and join the squad!';
    state.composer.coins = 50000;
    state.composer.gems = 2500;
    state.composer.mail_type = 3;
    state.composer.attachments = [
      { item_id: 907100001, count: 1, type: 1 },
      { item_id: 700000001, count: 1, type: 1 }
    ];

    const titleEl = document.getElementById('comp-mail-title');
    const bodyEl = document.getElementById('comp-mail-body');
    const coinsEl = document.getElementById('comp-coins');
    const gemsEl = document.getElementById('comp-gems');
    const typeEl = document.getElementById('comp-mail-type');

    if (titleEl) titleEl.value = state.composer.title;
    if (bodyEl) bodyEl.value = state.composer.content;
    if (coinsEl) coinsEl.value = state.composer.coins;
    if (gemsEl) gemsEl.value = state.composer.gems;
    if (typeEl) typeEl.value = state.composer.mail_type;

    onComposerFieldChange();
    renderAttachmentChips();
    showToast('Composer reset to defaults', 'info');
  }

  /* ==========================================================================
     SUB-TAB 2: IN-GAME MAILBOX INSPECTOR LOGIC
     ========================================================================== */
  async function loadMailbox() {
    const res = await apiGet(`/api/dashboard/mail?account_id=${state.targetAccountId}`);
    if (res && res.ok) {
      state.mailbox.items = res.mails || [];
      renderMailboxList();

      // If a mail is currently selected, refresh its details
      if (state.mailbox.selectedMailId) {
        inspectMail(state.mailbox.selectedMailId);
      } else if (state.mailbox.items.length > 0) {
        inspectMail(state.mailbox.items[0].mail_id);
      }
    }
  }

  function filterMailList() {
    const queryEl = document.getElementById('mailbox-search-input');
    const statusEl = document.getElementById('mailbox-status-filter');

    state.mailbox.filterQuery = queryEl ? queryEl.value.trim().toLowerCase() : '';
    state.mailbox.filterStatus = statusEl ? statusEl.value : 'all';

    renderMailboxList();
  }

  function renderMailboxList() {
    const container = document.getElementById('mailbox-items-container');
    if (!container) return;

    let items = state.mailbox.items || [];

    // Filter by query
    if (state.mailbox.filterQuery) {
      const q = state.mailbox.filterQuery;
      items = items.filter(m =>
        (m.title && m.title.toLowerCase().includes(q)) ||
        (m.sender_nick && m.sender_nick.toLowerCase().includes(q)) ||
        (m.content && m.content.toLowerCase().includes(q))
      );
    }

    // Filter by status
    if (state.mailbox.filterStatus === 'unclaimed') {
      items = items.filter(m => !m.is_claimed);
    } else if (state.mailbox.filterStatus === 'claimed') {
      items = items.filter(m => m.is_claimed);
    }

    if (!items.length) {
      container.innerHTML = `
        <div style="color:var(--s-text-dim); text-align:center; padding:32px 16px;">
          No mails found matching the filter criteria.
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(m => {
      const isSelected = m.mail_id === state.mailbox.selectedMailId;
      const isClaimed = Boolean(m.is_claimed);
      const coins = Number(m.coins || 0);
      const gems = Number(m.gems || 0);
      const attachments = m.attachments || [];

      return `
        <div class="s-mail-item-card ${isSelected ? 'active' : ''}" onclick="SocialSection.inspectMail(${m.mail_id})">
          <div class="s-mail-item-left">
            <div class="s-mail-item-title">
              <span class="s-tag s-tag-cyan" style="font-size:10px;">#${m.mail_id}</span>
              <span>${escapeHtml(m.title || 'Untitled Mail')}</span>
            </div>
            <div class="s-mail-item-meta">
              <span>From: <strong style="color:var(--s-text-main);">${escapeHtml(m.sender_nick || 'Admin')}</strong></span>
              <span>&bull;</span>
              <span>${formatTimestamp(m.receive_time)}</span>
            </div>
            <div class="s-mail-item-rewards-row">
              ${coins > 0 ? `<span class="s-reward-badge s-reward-gold" style="font-size:10px; padding:2px 6px;">+${formatNumber(coins)} Gold</span>` : ''}
              ${gems > 0 ? `<span class="s-reward-badge s-reward-gems" style="font-size:10px; padding:2px 6px;">+${formatNumber(gems)} Gems</span>` : ''}
              ${attachments.length > 0 ? `<span class="s-reward-badge s-reward-item" style="font-size:10px; padding:2px 6px;">${attachments.length} Items</span>` : ''}
            </div>
          </div>

          <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">
            <span class="s-tag ${isClaimed ? 's-tag-muted' : 's-tag-green'}">
              ${isClaimed ? 'CLAIMED' : 'UNCLAIMED'}
            </span>
            <div class="s-btn-cluster">
              ${!isClaimed ? `
                <button class="s-btn s-btn-gold s-btn-sm" onclick="event.stopPropagation(); SocialSection.claimMail(${m.mail_id})" title="Claim Reward">
                  Claim
                </button>
              ` : ''}
              <button class="s-btn s-btn-danger s-btn-sm" onclick="event.stopPropagation(); SocialSection.deleteMail(${m.mail_id})" title="Delete Mail">
                <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function inspectMail(mailId) {
    state.mailbox.selectedMailId = mailId;
    renderMailboxList(); // update active card highlight

    const detailContainer = document.getElementById('mail-detail-container');
    const idTag = document.getElementById('inspect-mail-id-tag');
    if (!detailContainer) return;

    const mail = (state.mailbox.items || []).find(m => m.mail_id === mailId);
    if (!mail) {
      if (idTag) idTag.textContent = 'Not Found';
      detailContainer.innerHTML = `<div style="color:var(--s-rose); padding:16px;">Mail #${mailId} not found.</div>`;
      return;
    }

    if (idTag) idTag.textContent = `MAIL #${mail.mail_id}`;

    const isClaimed = Boolean(mail.is_claimed);
    const coins = Number(mail.coins || 0);
    const gems = Number(mail.gems || 0);
    const attachments = mail.attachments || [];

    detailContainer.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:12px;">
        <!-- Header Info -->
        <div style="background:rgba(10,15,29,0.7); border:1px solid var(--s-border); border-radius:var(--s-radius-sm); padding:12px; display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <div style="font-size:15px; font-weight:800; color:#fff;">${escapeHtml(mail.title || 'Untitled Mail')}</div>
            <div style="font-size:11.5px; color:var(--s-text-dim); margin-top:3px;">
              From: <strong style="color:var(--s-cyan);">${escapeHtml(mail.sender_nick || 'Admin')}</strong> (ID: ${mail.sender_id || 0}) &bull; ${formatTimestamp(mail.receive_time)}
            </div>
          </div>
          <span class="s-tag ${isClaimed ? 's-tag-muted' : 's-tag-green'}">
            ${isClaimed ? 'STATUS: CLAIMED' : 'STATUS: UNCLAIMED'}
          </span>
        </div>

        <!-- Body Message Content -->
        <div class="s-form-group">
          <label class="s-form-label">Mail Content</label>
          <div style="background:rgba(0,0,0,0.3); border:1px solid var(--s-border); border-radius:var(--s-radius-sm); padding:12px; font-size:12.5px; line-height:1.6; color:var(--s-text-main); white-space:pre-wrap;">${escapeHtml(mail.content || '')}</div>
        </div>

        <!-- Attached Rewards -->
        <div class="s-form-group">
          <label class="s-form-label">Attached Claimable Rewards</label>
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            ${coins > 0 ? `
              <div class="s-reward-badge s-reward-gold">
                <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/></svg>
                <span>${formatNumber(coins)} Gold</span>
              </div>
            ` : ''}
            ${gems > 0 ? `
              <div class="s-reward-badge s-reward-gems">
                <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M6 3h12l4 6-10 12L2 9z"/><path d="M11 3 8 9l4 12 4-12-3-6"/></svg>
                <span>${formatNumber(gems)} Diamonds</span>
              </div>
            ` : ''}
            ${attachments.map(att => {
              const meta = ITEM_CATALOG[att.item_id] || { name: `Item #${att.item_id}` };
              return `
                <div class="s-reward-badge s-reward-item">
                  <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/></svg>
                  <span>${escapeHtml(meta.name)} (#${att.item_id}) &times;${att.count}</span>
                </div>
              `;
            }).join('')}
            ${(coins === 0 && gems === 0 && attachments.length === 0) ? `
              <span style="font-size:11px; color:var(--s-text-dim);">No rewards attached to this mail.</span>
            ` : ''}
          </div>
        </div>

        <!-- Action Bar -->
        <div class="s-btn-cluster" style="border-top:1px solid var(--s-border); padding-top:12px;">
          ${!isClaimed ? `
            <button class="s-btn s-btn-gold" onclick="SocialSection.claimMail(${mail.mail_id})">
              <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
              Claim Rewards Now
            </button>
          ` : `
            <button class="s-btn s-btn-secondary" disabled style="opacity:0.6; cursor:not-allowed;">
              Rewards Already Claimed
            </button>
          `}
          <button class="s-btn s-btn-danger" onclick="SocialSection.deleteMail(${mail.mail_id})">
            <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            Delete Mail
          </button>
        </div>

        <!-- Raw Wire JSON Inspector -->
        <details style="margin-top:6px; background:rgba(0,0,0,0.3); border:1px solid var(--s-border); border-radius:var(--s-radius-sm); padding:8px 12px;">
          <summary style="font-size:11px; font-weight:700; color:var(--s-text-muted); cursor:pointer;">
            Inspect Protobuf Wire State (JSON)
          </summary>
          <pre class="monospace" style="font-size:10.5px; color:#a5f3fc; margin-top:8px; overflow-x:auto; white-space:pre-wrap;">${escapeHtml(JSON.stringify(mail, null, 2))}</pre>
        </details>
      </div>
    `;
  }

  async function claimMail(mailId) {
    const res = await apiPost('/api/dashboard/mail/claim', {
      account_id: state.targetAccountId,
      mail_id: mailId
    });

    if (res && res.ok) {
      showToast(`Claimed rewards for Mail #${mailId}!`, 'gold');
      loadMailbox();
    } else {
      showToast('Claim failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function claimAllMails() {
    const res = await apiPost('/api/dashboard/mail/claim', {
      account_id: state.targetAccountId,
      mail_id: 'all'
    });

    if (res && res.ok) {
      showToast(`Successfully claimed all mails! (+${formatNumber(res.claimed_coins || 0)} Gold, +${formatNumber(res.claimed_gems || 0)} Gems)`, 'gold');
      loadMailbox();
    } else {
      showToast('Claim all failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function deleteMail(mailId) {
    const res = await apiPost('/api/dashboard/mail/delete', {
      account_id: state.targetAccountId,
      mail_id: mailId
    });

    if (res && res.ok) {
      showToast(`Deleted Mail #${mailId}`, 'info');
      state.mailbox.selectedMailId = null;
      loadMailbox();
    } else {
      showToast('Delete failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  /* ==========================================================================
     SUB-TAB 3: ONLINE FRIENDS & SOCIAL ROSTER LOGIC
     ========================================================================== */
  async function loadFriends() {
    const res = await apiGet(`/api/dashboard/friends?account_id=${state.targetAccountId}`);
    if (res && res.ok) {
      state.friends.items = res.friends || [];
      state.friends.requests = res.friend_requests || [];
      state.friends.recommended = res.recommended_friends || [];
      state.friends.allPlayers = res.all_players || [];

      // Update online count badge
      const onlineCount = state.friends.items.filter(f => f.is_online).length;
      const onlineBadge = document.getElementById('friends-online-badge');
      if (onlineBadge) onlineBadge.textContent = `${onlineCount} Online`;

      renderFriendsList();
      renderFriendRequests();
      renderRecommendedBots();
    }
  }

  function filterFriendsList() {
    const searchEl = document.getElementById('friends-search-input');
    const statusEl = document.getElementById('friends-status-filter');

    state.friends.filterQuery = searchEl ? searchEl.value.trim().toLowerCase() : '';
    state.friends.filterStatus = statusEl ? statusEl.value : 'all';

    renderFriendsList();
  }

  function renderFriendsList() {
    const container = document.getElementById('friends-list-container');
    if (!container) return;

    let items = state.friends.items || [];

    // Filter by query
    if (state.friends.filterQuery) {
      const q = state.friends.filterQuery;
      items = items.filter(f =>
        (f.nickname && f.nickname.toLowerCase().includes(q)) ||
        String(f.account_id).includes(q)
      );
    }

    // Filter by status: 1=online/lobby, 2=squad, 3=match, 0=offline
    if (state.friends.filterStatus !== 'all') {
      const targetStatus = Number(state.friends.filterStatus);
      items = items.filter(f => Number(f.online_status) === targetStatus);
    }

    if (!items.length) {
      container.innerHTML = `
        <div style="color:var(--s-text-dim); text-align:center; padding:32px 16px;">
          No friends matching the active status filter.
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(f => {
      const statusNum = Number(f.online_status || (f.is_online ? 1 : 0));
      let dotClass = 'offline';
      let tagText = 'OFFLINE';
      let tagClass = 's-tag-muted';

      if (statusNum === 1) {
        dotClass = 'online';
        tagText = 'IN LOBBY';
        tagClass = 's-tag-green';
      } else if (statusNum === 2) {
        dotClass = 'squad';
        tagText = 'IN SQUAD';
        tagClass = 's-tag-cyan';
      } else if (statusNum === 3) {
        dotClass = 'match';
        tagText = 'IN MATCH';
        tagClass = 's-tag-amber';
      }

      return `
        <div class="s-friend-card">
          <div class="s-friend-profile-cluster">
            <div class="s-avatar-frame">${f.nickname.substring(0, 2).toUpperCase()}</div>
            <div class="s-friend-info">
              <div class="s-friend-name-row">
                <span class="s-friend-name">${escapeHtml(f.nickname)}</span>
                <span class="s-status-dot ${dotClass}"></span>
                <span class="s-tag ${tagClass}">${tagText}</span>
              </div>
              <div class="s-friend-subline">
                <span>UID: ${f.account_id}</span>
                <span>&bull;</span>
                <span>LVL ${f.level || 50}</span>
                ${f.clan_name ? `<span>&bull;</span><span>[${escapeHtml(f.clan_name)}]</span>` : ''}
              </div>
            </div>
          </div>

          <div class="s-friend-actions">
            <!-- Dynamic Server Status Switcher -->
            <select class="s-form-select s-btn-sm monospace" style="width:115px; padding:3px 6px;" onchange="SocialSection.setPlayerOnlineStatus(${f.account_id}, this.value)" title="Simulate Status">
              <option value="1" ${statusNum === 1 ? 'selected' : ''}>Lobby</option>
              <option value="2" ${statusNum === 2 ? 'selected' : ''}>Squad</option>
              <option value="3" ${statusNum === 3 ? 'selected' : ''}>Match</option>
              <option value="0" ${statusNum === 0 ? 'selected' : ''}>Offline</option>
            </select>

            <button class="s-btn s-btn-primary s-btn-sm" onclick="SocialSection.sendSquadInviteToFriend(${f.account_id})" title="Instant Squad Invite">
              <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49"/></svg>
              Invite
            </button>

            <button class="s-btn s-btn-danger s-btn-sm" onclick="SocialSection.removeFriend(${f.account_id})" title="Remove Friend">
              <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderFriendRequests() {
    const container = document.getElementById('friend-requests-container');
    const badge = document.getElementById('friend-requests-count');
    if (!container) return;

    const reqs = state.friends.requests || [];
    if (badge) badge.textContent = `${reqs.length} Requests`;

    if (!reqs.length) {
      container.innerHTML = `<div style="color:var(--s-text-dim); text-align:center; padding:18px;">No pending incoming requests.</div>`;
      return;
    }

    container.innerHTML = reqs.map(r => `
      <div style="background:rgba(10,15,29,0.7); border:1px solid var(--s-border); border-radius:var(--s-radius-sm); padding:8px 10px; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-weight:700; color:#fff; font-size:12px;">${escapeHtml(r.nickname || `UID ${r.from_id}`)}</div>
          <div style="font-size:10.5px; color:var(--s-text-dim);">${escapeHtml(r.message || "Let's play squad!")}</div>
        </div>
        <div class="s-btn-cluster">
          <button class="s-btn s-btn-green s-btn-sm" onclick="SocialSection.acceptFriendRequest(${r.from_id})">Accept</button>
          <button class="s-btn s-btn-secondary s-btn-sm" onclick="SocialSection.rejectFriendRequest(${r.from_id})">Decline</button>
        </div>
      </div>
    `).join('');
  }

  function renderRecommendedBots() {
    const container = document.getElementById('recommended-bots-list');
    if (!container) return;

    // Filter bots not currently in friend list
    const currentFriendIds = new Set((state.friends.items || []).map(f => f.account_id));
    const availableBots = BOT_ROSTER.filter(b => !currentFriendIds.has(b.uid));

    if (!availableBots.length) {
      container.innerHTML = `<span style="font-size:11px; color:var(--s-text-dim);">All pre-seeded server bots are already added.</span>`;
      return;
    }

    container.innerHTML = availableBots.slice(0, 4).map(b => `
      <div style="background:rgba(10,15,29,0.5); border:1px solid var(--s-border); border-radius:var(--s-radius-sm); padding:6px 10px; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <span style="font-weight:700; color:#fff; font-size:12px;">${escapeHtml(b.nick)}</span>
          <span style="font-size:10.5px; color:var(--s-text-dim); margin-left:6px;">UID: ${b.uid} &bull; ${b.role}</span>
        </div>
        <button class="s-btn s-btn-secondary s-btn-sm" onclick="SocialSection.quickAddBot(${b.uid}, '${escapeHtml(b.nick)}')">
          + Add
        </button>
      </div>
    `).join('');
  }

  async function setPlayerOnlineStatus(playerId, newStatus) {
    const res = await apiPost('/api/dashboard/friends/online', {
      player_id: playerId,
      online_status: Number(newStatus)
    });

    if (res && res.ok) {
      showToast(`Updated status for UID ${playerId} to ${getStatusName(newStatus)}`, 'success');
      loadFriends();
    } else {
      showToast('Failed to update player status', 'error');
    }
  }

  function getStatusName(status) {
    const s = Number(status);
    if (s === 1) return 'In Lobby';
    if (s === 2) return 'In Squad';
    if (s === 3) return 'In Match';
    return 'Offline';
  }

  async function submitAddFriend() {
    const uidEl = document.getElementById('add-friend-uid');
    const nickEl = document.getElementById('add-friend-nick');
    const autoAcceptEl = document.getElementById('add-friend-autoaccept');

    const friendId = Number(uidEl ? uidEl.value : 0);
    const nickname = nickEl ? nickEl.value.trim() : '';
    const autoAccept = autoAcceptEl ? autoAcceptEl.checked : true;

    if (!friendId) {
      showToast('Valid Player UID is required', 'error');
      return;
    }

    const res = await apiPost('/api/dashboard/friends/add', {
      account_id: state.targetAccountId,
      friend_id: friendId,
      nickname: nickname || `Player_${friendId}`,
      auto_accept: autoAccept
    });

    if (res && res.ok) {
      showToast(`Added ${nickname || friendId} to friends list!`, 'success');
      if (uidEl) uidEl.value = '';
      if (nickEl) nickEl.value = '';
      loadFriends();
    } else {
      showToast('Add friend failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function quickAddBot(uid, nick) {
    const res = await apiPost('/api/dashboard/friends/add', {
      account_id: state.targetAccountId,
      friend_id: uid,
      nickname: nick,
      auto_accept: true
    });

    if (res && res.ok) {
      showToast(`Linked bot ${nick} (#${uid})!`, 'success');
      loadFriends();
    } else {
      showToast('Bot link failed', 'error');
    }
  }

  async function acceptFriendRequest(fromId) {
    const res = await apiPost('/api/dashboard/friends/accept', {
      account_id: state.targetAccountId,
      friend_id: fromId
    });

    if (res && res.ok) {
      showToast(`Accepted friend request from UID ${fromId}`, 'success');
      loadFriends();
    } else {
      showToast('Accept failed', 'error');
    }
  }

  async function rejectFriendRequest(fromId) {
    const res = await apiPost('/api/dashboard/friends/reject', {
      account_id: state.targetAccountId,
      friend_id: fromId
    });

    if (res && res.ok) {
      showToast(`Declined friend request from UID ${fromId}`, 'info');
      loadFriends();
    } else {
      showToast('Decline failed', 'error');
    }
  }

  async function removeFriend(friendId) {
    const res = await apiPost('/api/dashboard/friends/remove', {
      account_id: state.targetAccountId,
      friend_id: friendId
    });

    if (res && res.ok) {
      showToast(`Removed friend #${friendId}`, 'info');
      loadFriends();
    } else {
      showToast('Remove failed', 'error');
    }
  }

  /* ==========================================================================
     SUB-TAB 4: SQUAD LOBBY & INSTANT TCP INVITE TRIGGER
     ========================================================================== */
  async function loadSquad() {
    const res = await apiGet(`/api/dashboard/squad?account_id=${state.targetAccountId}`);
    if (res && res.ok) {
      state.squad.team = res.team || null;
      state.squad.invitations = res.team_invitations || [];
      state.squad.invitableFriends = res.invitable_friends || [];
      state.squad.rooms = res.rooms || [];

      renderSquadLobby();
      renderIncomingSquadInvites();
    }
  }

  function renderSquadLobby() {
    const team = state.squad.team;
    const slotsGrid = document.getElementById('squad-slots-grid');
    const nameDisplay = document.getElementById('squad-name-display');
    const metaDisplay = document.getElementById('squad-meta-display');
    const statusBadge = document.getElementById('squad-status-badge');
    const readyBtn = document.getElementById('squad-ready-btn');
    const leaveBtn = document.getElementById('squad-leave-btn');

    if (!slotsGrid) return;

    if (!team) {
      if (nameDisplay) nameDisplay.textContent = 'No Active Squad Session';
      if (metaDisplay) metaDisplay.textContent = 'Currently in Solo Lobby queue. Form or join a squad below.';
      if (statusBadge) {
        statusBadge.textContent = 'SOLO LOBBY';
        statusBadge.className = 's-tag s-tag-muted';
      }
      if (readyBtn) readyBtn.style.display = 'none';
      if (leaveBtn) leaveBtn.style.display = 'none';

      // 4 Empty Slots
      slotsGrid.innerHTML = [1, 2, 3, 4].map(idx => `
        <div class="s-squad-slot-card">
          <div class="s-slot-header">
            <span class="s-slot-role-badge s-slot-role-member">SLOT ${idx}</span>
            <span class="s-tag s-tag-muted">EMPTY</span>
          </div>
          <div class="s-slot-empty-prompt">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            <span>Empty Slot</span>
          </div>
        </div>
      `).join('');
      return;
    }

    // Active Team Session
    if (nameDisplay) nameDisplay.textContent = team.team_name || 'India V1 Squad';
    if (metaDisplay) {
      metaDisplay.textContent = `Squad ID: ${team.team_id} &bull; Mode: ${(team.mode || 'squad').toUpperCase()} &bull; Map: ${getMapName(team.map_id)}`;
    }
    if (statusBadge) {
      statusBadge.textContent = `SQUAD #${team.team_id}`;
      statusBadge.className = 's-tag s-tag-cyan';
    }
    if (readyBtn) readyBtn.style.display = 'inline-flex';
    if (leaveBtn) leaveBtn.style.display = 'inline-flex';

    const members = team.members || [];
    const maxSlots = 4;
    const renderedSlots = [];

    for (let i = 0; i < maxSlots; i++) {
      const mem = members[i];
      if (mem) {
        const isLeader = mem.role === 1 || mem.account_id === team.leader_id;
        const isReady = Boolean(mem.ready);
        renderedSlots.push(`
          <div class="s-squad-slot-card filled">
            <div class="s-slot-header">
              <span class="s-slot-role-badge ${isLeader ? 's-slot-role-leader' : 's-slot-role-member'}">
                ${isLeader ? 'LEADER' : 'MEMBER'}
              </span>
              <span class="s-tag ${isReady ? 's-tag-green' : 's-tag-amber'}">
                ${isReady ? 'READY' : 'PREPARING'}
              </span>
            </div>
            <div style="display:flex; align-items:center; gap:8px; margin-top:4px;">
              <div class="s-avatar-frame">${(mem.nickname || `UID ${mem.account_id}`).substring(0, 2).toUpperCase()}</div>
              <div>
                <div style="font-weight:700; color:#fff; font-size:12.5px;">${escapeHtml(mem.nickname || `Player_${mem.account_id}`)}</div>
                <div style="font-size:10.5px; color:var(--s-text-dim);">UID: ${mem.account_id}</div>
              </div>
            </div>
            ${!isLeader ? `
              <div style="margin-top:auto; display:flex; justify-content:flex-end;">
                <button class="s-btn s-btn-danger s-btn-sm" onclick="SocialSection.kickSquadMember(${mem.account_id})">Kick</button>
              </div>
            ` : ''}
          </div>
        `);
      } else {
        renderedSlots.push(`
          <div class="s-squad-slot-card" onclick="SocialSection.promptInviteToSlot()">
            <div class="s-slot-header">
              <span class="s-slot-role-badge s-slot-role-member">SLOT ${i + 1}</span>
              <span class="s-tag s-tag-muted">OPEN</span>
            </div>
            <div class="s-slot-empty-prompt">
              <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              <span>+ Invite Friend</span>
            </div>
          </div>
        `);
      }
    }

    slotsGrid.innerHTML = renderedSlots.join('');
  }

  function renderIncomingSquadInvites() {
    const container = document.getElementById('incoming-invitations-container');
    if (!container) return;

    const invites = state.squad.invitations || [];
    if (!invites.length) {
      container.innerHTML = `<div style="color:var(--s-text-dim); font-size:11.5px; padding:8px 0;">No pending squad invites for UID 10001.</div>`;
      return;
    }

    container.innerHTML = invites.map(inv => `
      <div style="background:rgba(10,15,29,0.7); border:1px solid var(--s-border); border-radius:var(--s-radius-sm); padding:8px 12px; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-weight:700; color:#fff; font-size:12px;">Invite from ${escapeHtml(inv.inviter_nick || `UID ${inv.inviter_id}`)}</div>
          <div style="font-size:10.5px; color:var(--s-text-dim);">Squad #${inv.team_id} &bull; Mode: ${(inv.mode || 'Squad').toUpperCase()}</div>
        </div>
        <div class="s-btn-cluster">
          <button class="s-btn s-btn-green s-btn-sm" onclick="SocialSection.acceptSquadInvitation(${inv.team_id})">Join</button>
          <button class="s-btn s-btn-secondary s-btn-sm" onclick="SocialSection.declineSquadInvitation(${inv.invite_id})">Decline</button>
        </div>
      </div>
    `).join('');
  }

  function getMapName(mapId) {
    const m = Number(mapId);
    if (m === 1) return 'Bermuda';
    if (m === 2) return 'Purgatory';
    if (m === 3) return 'Kalahari';
    return 'Classic';
  }

  async function createNewSquad() {
    const modeEl = document.getElementById('create-squad-mode');
    const mapEl = document.getElementById('create-squad-map');

    const mode = modeEl ? modeEl.value : 'squad';
    const mapId = mapEl ? Number(mapEl.value) : 1;

    const res = await apiPost('/api/dashboard/squad/create', {
      leader_id: state.targetAccountId,
      mode: mode,
      map_id: mapId,
      team_name: 'India V1 Elite Squad'
    });

    if (res && res.ok) {
      showToast(`Created squad lobby #${res.team ? res.team.team_id : ''}!`, 'success');
      loadSquad();
    } else {
      showToast('Squad creation failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function toggleSquadReady() {
    if (!state.squad.team) return;

    const myMember = (state.squad.team.members || []).find(m => m.account_id === state.targetAccountId);
    const newReady = myMember ? !myMember.ready : true;

    const res = await apiPost('/api/dashboard/squad/ready', {
      team_id: state.squad.team.team_id,
      player_id: state.targetAccountId,
      ready: newReady
    });

    if (res && res.ok) {
      showToast(newReady ? 'Set status to READY!' : 'Set status to PREPARING', 'info');
      loadSquad();
    } else {
      showToast('Toggle ready failed', 'error');
    }
  }

  async function leaveSquad() {
    if (!state.squad.team) return;

    const res = await apiPost('/api/dashboard/squad/leave', {
      player_id: state.targetAccountId,
      team_id: state.squad.team.team_id
    });

    if (res && res.ok) {
      showToast('Left squad session', 'info');
      loadSquad();
    } else {
      showToast('Leave squad failed', 'error');
    }
  }

  async function kickSquadMember(targetId) {
    if (!state.squad.team) return;

    const res = await apiPost('/api/dashboard/squad/kick', {
      team_id: state.squad.team.team_id,
      target_id: targetId
    });

    if (res && res.ok) {
      showToast(`Removed player #${targetId} from squad`, 'info');
      loadSquad();
    } else {
      showToast('Kick failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  function promptInviteToSlot() {
    switchSubTab('squad-lobby');
    const select = document.getElementById('invite-bot-select');
    if (select) select.focus();
    showToast('Choose a friend or bot below to transmit an instant invite', 'info');
  }

  function sendSquadInviteToFriend(friendId) {
    switchSubTab('squad-lobby');
    const dirSelect = document.getElementById('invite-direction-select');
    const targetGroup = document.getElementById('invite-target-group');
    const botGroup = document.getElementById('invite-bot-group');
    const targetUid = document.getElementById('invite-target-uid');

    if (dirSelect) dirSelect.value = 'from_player';
    if (targetGroup) targetGroup.style.display = 'flex';
    if (botGroup) botGroup.style.display = 'none';
    if (targetUid) targetUid.value = friendId;

    showToast(`Prepared squad invite for UID ${friendId}. Click Transmit!`, 'info');
  }

  function onInviteDirectionChange() {
    const dir = document.getElementById('invite-direction-select').value;
    const botGroup = document.getElementById('invite-bot-group');
    const targetGroup = document.getElementById('invite-target-group');

    if (dir === 'to_player') {
      if (botGroup) botGroup.style.display = 'flex';
      if (targetGroup) targetGroup.style.display = 'none';
    } else {
      if (botGroup) botGroup.style.display = 'none';
      if (targetGroup) targetGroup.style.display = 'flex';
    }
  }

  async function triggerTcpSquadInvite() {
    const dir = document.getElementById('invite-direction-select').value;
    const gameModeEl = document.getElementById('invite-gamemode-select');
    const gameMode = Number(gameModeEl ? gameModeEl.value : 1);

    let payload = {};

    if (dir === 'to_player') {
      const botId = Number(document.getElementById('invite-bot-select').value);
      payload = {
        direction: 'to_player',
        inviter_id: botId,
        account_id: state.targetAccountId,
        mode: 'squad',
        game_mode: gameMode,
        map_id: 1
      };
    } else {
      const targetId = Number(document.getElementById('invite-target-uid').value);
      payload = {
        direction: 'from_player',
        account_id: state.targetAccountId,
        target_id: targetId,
        mode: 'squad',
        game_mode: gameMode,
        map_id: 1,
        auto_join_bot: true
      };
    }

    const res = await apiPost('/api/dashboard/squad/invite', payload);

    if (res && res.ok) {
      const tcpPushed = res.tcp_pushed ? 'TCP SOCKET PUSHED' : 'STATE RECORDED';
      const logLine = {
        time: new Date().toLocaleTimeString(),
        badge: res.tcp_pushed ? 'DELIVERED' : 'DISPATCHED',
        text: `GroupInviteNtf sent: ${dir === 'to_player' ? `Bot #${payload.inviter_id} -> Player #${payload.account_id}` : `Player #${payload.account_id} -> #${payload.target_id}`} (${tcpPushed})`
      };
      appendTcpLog(logLine);
      showToast(`Squad invite dispatched! (${tcpPushed})`, 'success');
      loadSquad();
    } else {
      showToast('TCP Invite trigger error: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  function appendTcpLog(log) {
    state.tcpLogs.push(log);
    const container = document.getElementById('tcp-log-container');
    if (!container) return;

    const row = document.createElement('div');
    row.className = 's-tcp-log-line';
    row.innerHTML = `
      <span class="s-tcp-time">[${escapeHtml(log.time)}]</span>
      <span class="s-tcp-badge">${escapeHtml(log.badge)}</span>
      <span>${escapeHtml(log.text)}</span>
    `;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
  }

  async function acceptSquadInvitation(teamId) {
    const res = await apiPost('/api/dashboard/squad/join', {
      team_id: teamId,
      player_id: state.targetAccountId
    });

    if (res && res.ok) {
      showToast(`Joined Squad #${teamId}!`, 'success');
      loadSquad();
    } else {
      showToast('Join squad failed: ' + (res.error || 'Unknown error'), 'error');
    }
  }

  async function declineSquadInvitation(inviteId) {
    const res = await apiPost('/api/dashboard/squad/decline', {
      account_id: state.targetAccountId,
      invite_id: inviteId
    });

    if (res && res.ok) {
      showToast('Declined squad invitation', 'info');
      loadSquad();
    } else {
      showToast('Decline failed', 'error');
    }
  }

  /* ==========================================================================
     INITIALIZATION & LIFECYCLE
     ========================================================================== */
  function init() {
    renderAttachmentChips();
    renderEnvelopePreview();
    loadMailbox();
    loadFriends();
    loadSquad();
  }

  // Auto-boot on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Public Interface
  return {
    init,
    switchSubTab,
    refreshCurrentTab,
    onComposerFieldChange,
    addCurrency,
    setCurrency,
    onItemPresetSelected,
    addAttachmentItem,
    removeAttachmentItem,
    applyTemplate,
    dispatchMail,
    resetComposer,
    loadMailbox,
    filterMailList,
    inspectMail,
    claimMail,
    claimAllMails,
    deleteMail,
    loadFriends,
    filterFriendsList,
    setPlayerOnlineStatus,
    submitAddFriend,
    quickAddBot,
    acceptFriendRequest,
    rejectFriendRequest,
    removeFriend,
    loadSquad,
    createNewSquad,
    toggleSquadReady,
    leaveSquad,
    kickSquadMember,
    promptInviteToSlot,
    sendSquadInviteToFriend,
    onInviteDirectionChange,
    triggerTcpSquadInvite,
    acceptSquadInvitation,
    declineSquadInvitation
  };
});
