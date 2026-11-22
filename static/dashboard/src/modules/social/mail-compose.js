/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Domain 07: Social & Communication — Mail Composer (#/social/mail-compose)
 */

(function (root) {
  'use strict';

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

  const state = {
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
  };

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
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

  function render(canvas) {
    if (!canvas) canvas = document.getElementById('workspace-canvas');
    if (!canvas) return;

    if (window.playerContext) {
      state.recipient_uid = window.playerContext.getSelectedAccountId() || 10001;
    }

    const html = `
      <div class="social-mail-composer-module">
        <!-- Header Strip with Quick Presets -->
        <div class="glass-card" style="margin-bottom: 20px; padding: 16px 20px;">
          <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
            <div>
              <div class="glass-card-title" style="font-size: 16px;">Mail Composer & Attachment Dispatcher</div>
              <div class="glass-card-subtitle">Deliver system mail with gold, diamonds, and item attachments directly to player inboxes.</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="window.location.hash='#/social/mail'">
                <span>← Back to Mailbox</span>
              </button>
              <button class="btn btn-secondary" onclick="window.SocialMailCompose.reset()">
                <span>Reset Form</span>
              </button>
            </div>
          </div>

          <!-- Quick Templates Bar -->
          <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); display: flex; flex-wrap: wrap; align-items: center; gap: 8px;">
            <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Quick Presets:</span>
            <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 10px;" onclick="window.SocialMailCompose.applyTemplate('welcome')">
              🎁 Welcome Recruit
            </button>
            <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 10px;" onclick="window.SocialMailCompose.applyTemplate('compensation')">
              🛠️ Hotfix Compensation
            </button>
            <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 10px;" onclick="window.SocialMailCompose.applyTemplate('ranked')">
              🏆 Grandmaster Rewards
            </button>
            <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 10px;" onclick="window.SocialMailCompose.applyTemplate('founder')">
              👑 Infinite Ops Grant
            </button>
          </div>
        </div>

        <!-- 2-Column Split: Form on Left, Live Simulator Preview on Right -->
        <div style="display: grid; grid-template-columns: minmax(360px, 1.2fr) minmax(320px, 1fr); gap: 20px; align-items: start;">
          <!-- Left: Input Form -->
          <div class="glass-card" style="padding: 20px;">
            <div class="glass-card-title" style="font-size: 14px; margin-bottom: 16px;">Dispatch Parameters</div>

            <!-- Recipient & Sender -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
              <div>
                <label style="display: block; font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">
                  Recipient UID
                </label>
                <div style="display: flex; gap: 6px;">
                  <input type="number" id="comp-recipient-uid" class="form-input monospace" value="${state.recipient_uid}" oninput="window.SocialMailCompose.onFieldChange()">
                  <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.SocialMailCompose.useActivePlayer()" title="Set to Active Player Context">Active</button>
                </div>
              </div>
              <div>
                <label style="display: block; font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">
                  Sender Nickname
                </label>
                <input type="text" id="comp-sender-nick" class="form-input" value="${escapeHtml(state.sender_nick)}" oninput="window.SocialMailCompose.onFieldChange()">
              </div>
            </div>

            <!-- Mail Type & Title -->
            <div style="display: grid; grid-template-columns: 140px 1fr; gap: 12px; margin-bottom: 14px;">
              <div>
                <label style="display: block; font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">
                  Mail Type
                </label>
                <select id="comp-mail-type" class="form-input" onchange="window.SocialMailCompose.onFieldChange()">
                  <option value="1" ${state.mail_type === 1 ? 'selected' : ''}>Type 1: System</option>
                  <option value="2" ${state.mail_type === 2 ? 'selected' : ''}>Type 2: Event</option>
                  <option value="3" ${state.mail_type === 3 ? 'selected' : ''}>Type 3: Hotfix</option>
                  <option value="4" ${state.mail_type === 4 ? 'selected' : ''}>Type 4: Personal</option>
                </select>
              </div>
              <div>
                <label style="display: block; font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">
                  Mail Title / Subject <span style="color: var(--accent-rose);">*</span>
                </label>
                <input type="text" id="comp-mail-title" class="form-input" placeholder="e.g. Compensation Drop" value="${escapeHtml(state.title)}" oninput="window.SocialMailCompose.onFieldChange()">
              </div>
            </div>

            <!-- Mail Body -->
            <div style="margin-bottom: 16px;">
              <label style="display: block; font-size: 11px; color: var(--text-tertiary); font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">
                Message Content
              </label>
              <textarea id="comp-mail-content" class="form-input" style="height: 90px; resize: vertical;" placeholder="Type body message shown to player..." oninput="window.SocialMailCompose.onFieldChange()">${escapeHtml(state.content)}</textarea>
            </div>

            <!-- Currency Attachments -->
            <div style="background: rgba(10, 16, 28, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 16px;">
              <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary); margin-bottom: 10px;">
                Currency Attachments
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <!-- Gold -->
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <label style="font-size: 11px; color: var(--accent-amber); font-weight: 600;">🪙 Attached Gold</label>
                  </div>
                  <input type="number" id="comp-coins" class="form-input monospace" value="${state.coins}" oninput="window.SocialMailCompose.onFieldChange()">
                  <div style="display: flex; gap: 4px; margin-top: 6px;">
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.addCurrency('coins', 10000)">+10k</button>
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.addCurrency('coins', 50000)">+50k</button>
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.addCurrency('coins', 100000)">+100k</button>
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.setCurrency('coins', 0)">Clr</button>
                  </div>
                </div>

                <!-- Diamonds -->
                <div>
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <label style="font-size: 11px; color: var(--accent-cyan); font-weight: 600;">💎 Attached Diamonds</label>
                  </div>
                  <input type="number" id="comp-gems" class="form-input monospace" value="${state.gems}" oninput="window.SocialMailCompose.onFieldChange()">
                  <div style="display: flex; gap: 4px; margin-top: 6px;">
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.addCurrency('gems', 500)">+500</button>
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.addCurrency('gems', 2500)">+2.5k</button>
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.addCurrency('gems', 10000)">+10k</button>
                    <button type="button" class="btn btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.SocialMailCompose.setCurrency('gems', 0)">Clr</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Item Attachments -->
            <div style="background: rgba(10, 16, 28, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 20px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Item Attachments</span>
                <span id="comp-attached-count" class="badge badge-cyan">${state.attachments.length} Items</span>
              </div>

              <!-- Attach Item Form Row -->
              <div style="display: grid; grid-template-columns: 1fr 100px 90px auto; gap: 8px; align-items: end; margin-bottom: 12px;">
                <div>
                  <label style="font-size: 10px; color: var(--text-tertiary); display: block; margin-bottom: 2px;">Item Preset</label>
                  <select id="comp-preset-select" class="form-input" style="font-size: 11.5px;" onchange="window.SocialMailCompose.onPresetSelected(this.value)">
                    <option value="">-- Choose Preset Item --</option>
                    ${Object.entries(ITEM_CATALOG).map(([id, meta]) => `
                      <option value="${id}">${meta.name} (#${id})</option>
                    `).join('')}
                  </select>
                </div>
                <div>
                  <label style="font-size: 10px; color: var(--text-tertiary); display: block; margin-bottom: 2px;">Custom ID</label>
                  <input type="number" id="comp-item-id-input" class="form-input monospace" placeholder="Item ID" value="907100001">
                </div>
                <div>
                  <label style="font-size: 10px; color: var(--text-tertiary); display: block; margin-bottom: 2px;">Quantity</label>
                  <input type="number" id="comp-item-count-input" class="form-input monospace" value="1" min="1">
                </div>
                <div>
                  <button type="button" class="btn btn-secondary" style="height: 34px;" onclick="window.SocialMailCompose.addAttachment()">
                    + Add
                  </button>
                </div>
              </div>

              <!-- Attached Items Pill List -->
              <div id="comp-attachment-list" style="display: flex; flex-wrap: wrap; gap: 6px;">
                ${renderAttachmentPillsHtml()}
              </div>
            </div>

            <!-- Submit Button Cluster -->
            <div style="display: flex; gap: 10px; align-items: center;">
              <button class="btn btn-primary" style="padding: 10px 20px; font-size: 13px;" onclick="window.SocialMailCompose.dispatchMail()">
                <span>🚀 Dispatch Mail to Player</span>
              </button>
              <button class="btn btn-secondary" onclick="window.location.hash='#/social/mail'">
                Cancel
              </button>
            </div>
          </div>

          <!-- Right: Live Envelope & Letterhead Preview Simulator -->
          <div class="glass-card" style="padding: 20px;">
            <div class="glass-card-header" style="margin-bottom: 14px;">
              <div>
                <div class="glass-card-title" style="font-size: 14px;">In-Game Envelope Simulator</div>
                <div class="glass-card-subtitle">Live preview of letter appearance in Free Fire 1.39 client</div>
              </div>
              <span id="preview-type-pill" class="badge badge-cyan">TYPE ${state.mail_type}</span>
            </div>

            <!-- Client Envelope Letterhead Simulation -->
            <div style="
              background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(8, 13, 24, 0.95));
              border: 1px solid rgba(56, 189, 248, 0.25);
              box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
              border-radius: var(--radius-md);
              padding: 20px;
            ">
              <!-- Sender Header in Simulator -->
              <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px; margin-bottom: 14px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                  <div id="prev-avatar" style="
                    width: 38px;
                    height: 38px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
                    color: #fff;
                    font-weight: 700;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                  ">
                    ${(state.sender_nick || 'OP').substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <div id="prev-sender" style="font-weight: 700; color: #fff; font-size: 13.5px;">${escapeHtml(state.sender_nick)}</div>
                    <div id="prev-target" style="font-size: 11px; color: var(--text-tertiary);">To: Account #${state.recipient_uid}</div>
                  </div>
                </div>
                <span class="badge badge-emerald">PREVIEW</span>
              </div>

              <!-- Subject & Body in Simulator -->
              <div style="margin-bottom: 16px;">
                <div id="prev-title" style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 8px;">
                  ${escapeHtml(state.title || '(No Subject)')}
                </div>
                <div id="prev-body" style="
                  background: rgba(0, 0, 0, 0.3);
                  border: 1px solid var(--border-subtle);
                  border-radius: var(--radius-sm);
                  padding: 12px;
                  font-size: 12.5px;
                  line-height: 1.6;
                  color: var(--text-primary);
                  min-height: 80px;
                  white-space: pre-wrap;
                ">
                  ${escapeHtml(state.content || '(No message content)')}
                </div>
              </div>

              <!-- Attached Rewards Section in Simulator -->
              <div>
                <div style="font-size: 10.5px; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary); margin-bottom: 8px;">
                  Enclosed Rewards
                </div>
                <div id="prev-rewards-box" style="display: flex; flex-wrap: wrap; gap: 8px;">
                  ${renderPreviewRewardsHtml()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    canvas.innerHTML = html;
  }

  function renderAttachmentPillsHtml() {
    if (!state.attachments || state.attachments.length === 0) {
      return `<span style="font-size: 11px; color: var(--text-tertiary);">No items attached. Choose from preset dropdown above.</span>`;
    }

    return state.attachments.map((att, idx) => {
      const meta = ITEM_CATALOG[att.item_id] || { name: 'Item #' + att.item_id, cat: 'Custom' };
      return `
        <div class="attachment-glass-chip" style="
          background: rgba(15, 23, 42, 0.75);
          backdrop-filter: var(--blur-sm);
          border: 1px solid rgba(56, 189, 248, 0.35);
          border-radius: var(--radius-sm);
          padding: 6px 10px;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 11.5px;
          color: var(--text-primary);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
        ">
          <span style="font-size: 13px;">📦</span>
          <span style="font-weight: 600; color: #fff;">${escapeHtml(meta.name)}</span>
          <span class="badge badge-cyan" style="font-size: 9.5px; font-family: var(--font-mono);">#${att.item_id}</span>
          <span class="badge badge-neutral" style="font-size: 9.5px;">&times;${att.count}</span>
          <button type="button" class="btn btn-danger" style="padding: 1px 6px; font-size: 10px; border-radius: var(--radius-xs); line-height: 1;" onclick="window.SocialMailCompose.removeAttachment(${idx})" title="Remove item">✕</button>
        </div>
      `;
    }).join('');
  }

  function renderPreviewRewardsHtml() {
    const rewards = [];
    if (state.coins > 0) {
      rewards.push(`
        <span class="badge badge-amber" style="padding: 4px 10px; font-size: 11px;">
          🪙 +${formatNumber(state.coins)} Gold
        </span>
      `);
    }
    if (state.gems > 0) {
      rewards.push(`
        <span class="badge badge-cyan" style="padding: 4px 10px; font-size: 11px;">
          💎 +${formatNumber(state.gems)} Diamonds
        </span>
      `);
    }
    state.attachments.forEach(att => {
      const meta = ITEM_CATALOG[att.item_id] || { name: 'Item #' + att.item_id };
      rewards.push(`
        <span class="badge badge-neutral" style="padding: 4px 10px; font-size: 11px; color: #fff;">
          📦 ${escapeHtml(meta.name)} &times;${att.count}
        </span>
      `);
    });

    if (rewards.length === 0) {
      return `<span style="font-size: 11px; color: var(--text-tertiary);">No currency or items attached (Letter only).</span>`;
    }
    return rewards.join('');
  }

  function onFieldChange() {
    const uidEl = document.getElementById('comp-recipient-uid');
    const nickEl = document.getElementById('comp-sender-nick');
    const typeEl = document.getElementById('comp-mail-type');
    const titleEl = document.getElementById('comp-mail-title');
    const contentEl = document.getElementById('comp-mail-content');
    const coinsEl = document.getElementById('comp-coins');
    const gemsEl = document.getElementById('comp-gems');

    if (uidEl) state.recipient_uid = Number(uidEl.value) || 10001;
    if (nickEl) state.sender_nick = nickEl.value || 'India V1 Operations';
    if (typeEl) state.mail_type = Number(typeEl.value) || 1;
    if (titleEl) state.title = titleEl.value || '';
    if (contentEl) state.content = contentEl.value || '';
    if (coinsEl) state.coins = Math.max(0, Number(coinsEl.value) || 0);
    if (gemsEl) state.gems = Math.max(0, Number(gemsEl.value) || 0);

    // Update live simulator preview DOM elements
    const prevSender = document.getElementById('prev-sender');
    if (prevSender) prevSender.textContent = state.sender_nick;

    const prevAvatar = document.getElementById('prev-avatar');
    if (prevAvatar) prevAvatar.textContent = (state.sender_nick || 'OP').substring(0, 2).toUpperCase();

    const prevTarget = document.getElementById('prev-target');
    if (prevTarget) prevTarget.textContent = `To: Account #${state.recipient_uid}`;

    const prevTitle = document.getElementById('prev-title');
    if (prevTitle) prevTitle.textContent = state.title || '(No Subject)';

    const prevBody = document.getElementById('prev-body');
    if (prevBody) prevBody.textContent = state.content || '(No message content)';

    const prevType = document.getElementById('preview-type-pill');
    if (prevType) prevType.textContent = `TYPE ${state.mail_type}`;

    const rewardsBox = document.getElementById('prev-rewards-box');
    if (rewardsBox) rewardsBox.innerHTML = renderPreviewRewardsHtml();
  }

  function useActivePlayer() {
    if (window.playerContext) {
      state.recipient_uid = window.playerContext.getSelectedAccountId() || 10001;
      const el = document.getElementById('comp-recipient-uid');
      if (el) el.value = state.recipient_uid;
      onFieldChange();
      window.UI.Toast(`Set recipient to active account ${state.recipient_uid}`, 'info');
    }
  }

  function addCurrency(type, delta) {
    if (type === 'coins') {
      state.coins = Math.max(0, state.coins + delta);
      const el = document.getElementById('comp-coins');
      if (el) el.value = state.coins;
    } else if (type === 'gems') {
      state.gems = Math.max(0, state.gems + delta);
      const el = document.getElementById('comp-gems');
      if (el) el.value = state.gems;
    }
    onFieldChange();
  }

  function setCurrency(type, val) {
    if (type === 'coins') {
      state.coins = Math.max(0, val);
      const el = document.getElementById('comp-coins');
      if (el) el.value = state.coins;
    } else if (type === 'gems') {
      state.gems = Math.max(0, val);
      const el = document.getElementById('comp-gems');
      if (el) el.value = state.gems;
    }
    onFieldChange();
  }

  function onPresetSelected(val) {
    if (!val) return;
    const input = document.getElementById('comp-item-id-input');
    if (input) input.value = val;
  }

  function addAttachment() {
    const idInput = document.getElementById('comp-item-id-input');
    const countInput = document.getElementById('comp-item-count-input');
    const itemId = Number(idInput ? idInput.value : 0);
    const count = Math.max(1, Number(countInput ? countInput.value : 1));

    if (!itemId) {
      window.UI.Toast('Enter a valid Item ID to attach', 'error');
      return;
    }

    const existing = state.attachments.find(a => a.item_id === itemId);
    if (existing) {
      existing.count += count;
    } else {
      state.attachments.push({ item_id: itemId, count, type: 1 });
    }

    const listEl = document.getElementById('comp-attachment-list');
    if (listEl) listEl.innerHTML = renderAttachmentPillsHtml();

    const badgeEl = document.getElementById('comp-attached-count');
    if (badgeEl) badgeEl.textContent = `${state.attachments.length} Items`;

    const rewardsBox = document.getElementById('prev-rewards-box');
    if (rewardsBox) rewardsBox.innerHTML = renderPreviewRewardsHtml();

    window.UI.Toast(`Attached ${count}x item #${itemId}`, 'success');
  }

  function removeAttachment(idx) {
    if (idx >= 0 && idx < state.attachments.length) {
      state.attachments.splice(idx, 1);
      const listEl = document.getElementById('comp-attachment-list');
      if (listEl) listEl.innerHTML = renderAttachmentPillsHtml();
      const badgeEl = document.getElementById('comp-attached-count');
      if (badgeEl) badgeEl.textContent = `${state.attachments.length} Items`;
      const rewardsBox = document.getElementById('prev-rewards-box');
      if (rewardsBox) rewardsBox.innerHTML = renderPreviewRewardsHtml();
    }
  }

  function applyTemplate(key) {
    if (key === 'welcome') {
      state.title = 'Welcome Recruit Care Package';
      state.content = 'Welcome to the India V1 server! Here is a welcome pack of 50,000 Gold, 2,500 Diamonds, plus your exclusive Founder Banner and Soldier Avatar!';
      state.coins = 50000;
      state.gems = 2500;
      state.mail_type = 2;
      state.attachments = [
        { item_id: 901000001, count: 1, type: 1 },
        { item_id: 902000001, count: 1, type: 1 }
      ];
    } else if (key === 'compensation') {
      state.title = 'Hotfix Maintenance Compensation Drop';
      state.content = 'Thank you for your patience during server maintenance. Enjoy 100,000 Gold, 5,000 Diamonds, and 2x Weapon Royale Crates!';
      state.coins = 100000;
      state.gems = 5000;
      state.mail_type = 3;
      state.attachments = [
        { item_id: 907100001, count: 2, type: 1 }
      ];
    } else if (key === 'ranked') {
      state.title = 'Ranked Grandmaster Season Rewards';
      state.content = 'Congratulations on finishing the ranked season in Grandmaster! Here is your full Tactical Combat Suit, 250,000 Gold, and 15,000 Diamonds.';
      state.coins = 250000;
      state.gems = 15000;
      state.mail_type = 3;
      state.attachments = [
        { item_id: 203000001, count: 1, type: 1 },
        { item_id: 204000001, count: 1, type: 1 },
        { item_id: 205000001, count: 1, type: 1 }
      ];
    } else if (key === 'founder') {
      state.title = 'Infinite Ops Founder Grants';
      state.content = 'Direct developer ops package: 1,000,000 Gold, 100,000 Diamonds, 10x Elite Pass Tokens, and 5x Weapon Crates.';
      state.coins = 1000000;
      state.gems = 100000;
      state.mail_type = 1;
      state.attachments = [
        { item_id: 700000001, count: 10, type: 1 },
        { item_id: 907100001, count: 5, type: 1 }
      ];
    }

    render(document.getElementById('workspace-canvas'));
    window.UI.Toast(`Applied preset: ${key.toUpperCase()}`, 'info');
  }

  function reset() {
    state.title = 'Welcome Care Package & Elite Pass Drop';
    state.content = 'Welcome to India V1 1.39 Server! Claim your exclusive gold, diamonds, and rare cosmetic loadout below. Ready up and join the squad!';
    state.coins = 50000;
    state.gems = 2500;
    state.mail_type = 3;
    state.attachments = [
      { item_id: 907100001, count: 1, type: 1 },
      { item_id: 700000001, count: 1, type: 1 }
    ];
    render(document.getElementById('workspace-canvas'));
    window.UI.Toast('Composer reset to defaults', 'info');
  }

  async function dispatchMail() {
    if (!state.title || !state.title.trim()) {
      window.UI.Toast('Mail title / subject is required', 'error');
      return;
    }
    if (!state.recipient_uid) {
      window.UI.Toast('Valid Recipient UID is required', 'error');
      return;
    }

    const payload = {
      account_id: state.recipient_uid,
      title: state.title.trim(),
      content: state.content.trim(),
      sender_nick: state.sender_nick.trim() || 'India V1 Admin',
      mail_type: state.mail_type,
      coins: state.coins,
      gems: state.gems,
      attachments: state.attachments
    };

    try {
      const res = await window.apiClient.post('/api/dashboard/mail/send', payload);
      if (res && res.ok) {
        const mailId = res.data && res.data.mail ? res.data.mail.mail_id : 'NEW';
        window.UI.Toast(`Mail #${mailId} dispatched to Account #${state.recipient_uid}!`, 'success');
        if (window.playerContext) window.playerContext.refresh();
        if (typeof window !== 'undefined' && window.location) {
          window.location.hash = '#/social/mail';
        }
      } else {
        window.UI.Toast('Dispatch failed: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error dispatching mail', 'error');
    }
  }

  // Public Interface
  const SocialMailCompose = {
    render,
    onFieldChange,
    useActivePlayer,
    addCurrency,
    setCurrency,
    onPresetSelected,
    addAttachment,
    removeAttachment,
    applyTemplate,
    reset,
    dispatchMail
  };

  root.SocialMailCompose = SocialMailCompose;

})(typeof window !== 'undefined' ? window : this);
