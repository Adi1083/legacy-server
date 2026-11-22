/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Domain 07: Social & Communication — Mailbox Manager (#/social/mail)
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
    mails: [],
    wallet: {},
    selectedMailId: null,
    filterQuery: '',
    filterStatus: 'all',
    isLoading: false
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

  function formatTimestamp(ts) {
    if (!ts) return 'Unknown';
    const date = new Date(ts > 1e11 ? ts : ts * 1000);
    return date.toLocaleTimeString() + ' (' + date.toLocaleDateString() + ')';
  }

  async function fetchMails() {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    state.isLoading = true;
    try {
      const res = await window.apiClient.get('/api/dashboard/mail', { account_id: aid });
      if (res && res.ok && res.data) {
        state.mails = res.data.mails || [];
        state.wallet = res.data.wallet || {};
        if (state.selectedMailId === null && state.mails.length > 0) {
          state.selectedMailId = state.mails[0].mail_id || state.mails[0].id;
        }
      } else {
        window.UI.Toast('Failed to load mailbox: ' + ((res && res.error) || 'Server error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error loading mailbox', 'error');
    } finally {
      state.isLoading = false;
    }
  }

  function getFilteredMails() {
    let items = state.mails || [];
    if (state.filterQuery) {
      const q = state.filterQuery.toLowerCase();
      items = items.filter(m =>
        (m.title && m.title.toLowerCase().includes(q)) ||
        (m.sender_nick && m.sender_nick.toLowerCase().includes(q)) ||
        (m.content && m.content.toLowerCase().includes(q))
      );
    }
    if (state.filterStatus === 'unclaimed') {
      items = items.filter(m => !m.is_claimed);
    } else if (state.filterStatus === 'claimed') {
      items = items.filter(m => m.is_claimed);
    }
    return items;
  }

  function render(canvas) {
    if (!canvas) canvas = document.getElementById('workspace-canvas');
    if (!canvas) return;

    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    canvas.innerHTML = window.UI.Loading('Loading in-game mailbox...');

    fetchMails().then(() => {
      buildUI(canvas, aid);
    });
  }

  function buildUI(canvas, aid) {
    const filteredMails = getFilteredMails();
    const totalMails = state.mails.length;
    const unclaimedMails = state.mails.filter(m => !m.is_claimed).length;
    const totalClaimableGold = state.mails.reduce((acc, m) => acc + (!m.is_claimed ? Number(m.coins || 0) : 0), 0);
    const totalClaimableGems = state.mails.reduce((acc, m) => acc + (!m.is_claimed ? Number(m.gems || 0) : 0), 0);
    const walletGold = Number((state.wallet && state.wallet.coins) || 0);
    const walletGems = Number((state.wallet && state.wallet.gems) || 0);

    const selectedMail = state.mails.find(m => (m.mail_id || m.id) === state.selectedMailId) || (filteredMails.length > 0 ? filteredMails[0] : null);
    if (selectedMail) {
      state.selectedMailId = selectedMail.mail_id || selectedMail.id;
    }

    const html = `
      <div class="social-mailbox-module">
        <!-- KPI Metrics Header Strip -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
          <div style="background: var(--bg-card); backdrop-filter: var(--blur-sm); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 14px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Inbox Capacity</div>
            <div style="font-size: 22px; font-weight: 700; color: #fff; margin: 4px 0;">${totalMails} <span style="font-size: 12px; color: var(--text-tertiary); font-weight: 400;">Messages</span></div>
            <div style="font-size: 11px; color: var(--text-secondary);">${unclaimedMails} Unclaimed &bull; Target UID: <code style="color: var(--accent-cyan); font-family: var(--font-mono);">${aid}</code></div>
          </div>
          <div style="background: var(--bg-card); backdrop-filter: var(--blur-sm); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 14px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Pending Rewards</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-amber); margin: 4px 0;">+${formatNumber(totalClaimableGems)} <span style="font-size: 12px; color: var(--text-tertiary); font-weight: 400;">Diamonds</span></div>
            <div style="font-size: 11px; color: var(--text-secondary);">+${formatNumber(totalClaimableGold)} Gold awaiting claim</div>
          </div>
          <div style="background: var(--bg-card); backdrop-filter: var(--blur-sm); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 14px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Current Player Wallet</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-emerald); margin: 4px 0;">${formatNumber(walletGold)} <span style="font-size: 12px; color: var(--text-tertiary); font-weight: 400;">Gold</span></div>
            <div style="font-size: 11px; color: var(--text-secondary);">${formatNumber(walletGems)} Diamonds in wallet</div>
          </div>
        </div>

        <!-- Filter & Action Bar -->
        <div class="glass-card" style="padding: 14px 18px; margin-bottom: 20px;">
          <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 10px; align-items: center; flex: 1; min-width: 280px;">
              <input type="text" id="mail-search-input" class="form-input" style="max-width: 260px;" placeholder="Search title, sender, content..." value="${escapeHtml(state.filterQuery)}" oninput="window.SocialMail.onFilterChange(this.value)">
              <select id="mail-status-filter" class="form-input" style="max-width: 150px; cursor: pointer;" onchange="window.SocialMail.onStatusChange(this.value)">
                <option value="all" ${state.filterStatus === 'all' ? 'selected' : ''}>All Mails (${totalMails})</option>
                <option value="unclaimed" ${state.filterStatus === 'unclaimed' ? 'selected' : ''}>Unclaimed (${unclaimedMails})</option>
                <option value="claimed" ${state.filterStatus === 'claimed' ? 'selected' : ''}>Claimed (${totalMails - unclaimedMails})</option>
              </select>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <button class="btn btn-primary" onclick="window.SocialMail.confirmClaimAll()" ${unclaimedMails === 0 ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : ''}>
                <span>Claim All (${unclaimedMails})</span>
              </button>
              <button class="btn btn-secondary" onclick="window.location.hash='#/social/mail-compose'">
                <span>+ Compose Mail</span>
              </button>
              <button class="btn btn-secondary" onclick="window.SocialMail.refresh()" title="Refresh Mailbox">
                <span>🔄</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Master-Detail 2-Column Grid -->
        <div style="display: grid; grid-template-columns: minmax(320px, 420px) 1fr; gap: 20px; align-items: start;">
          <!-- Left: Mail Item List -->
          <div class="glass-card" style="padding: 16px;">
            <div class="glass-card-header" style="margin-bottom: 12px;">
              <div>
                <div class="glass-card-title" style="font-size: 13.5px;">Inbox Messages (${filteredMails.length})</div>
                <div class="glass-card-subtitle">Showing mails for Account ${aid}</div>
              </div>
            </div>
            <div id="mail-list-container" style="display: flex; flex-direction: column; gap: 8px; max-height: 600px; overflow-y: auto; padding-right: 4px;">
              ${renderMailItemsHtml(filteredMails)}
            </div>
          </div>

          <!-- Right: Mail Inspector Pane -->
          <div class="glass-card" id="mail-detail-pane" style="padding: 20px;">
            ${renderMailDetailHtml(selectedMail, aid)}
          </div>
        </div>
      </div>
    `;

    canvas.innerHTML = html;
  }

  function renderMailItemsHtml(items) {
    if (!items || items.length === 0) {
      return `
        <div style="padding: 36px 16px; text-align: center; color: var(--text-tertiary); font-size: 12px;">
          No mail items match the filter criteria.
        </div>
      `;
    }

    return items.map(m => {
      const mid = m.mail_id || m.id;
      const isSelected = mid === state.selectedMailId;
      const isClaimed = Boolean(m.is_claimed);
      const coins = Number(m.coins || 0);
      const gems = Number(m.gems || 0);
      const attachments = m.attachments || [];

      return `
        <div class="mail-item-card" onclick="window.SocialMail.selectMail(${mid})" style="
          padding: 12px;
          border-radius: var(--radius-sm);
          border: 1px solid ${isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)'};
          background: ${isSelected ? 'rgba(56, 189, 248, 0.10)' : 'rgba(10, 16, 28, 0.4)'};
          cursor: pointer;
          transition: all var(--transition-fast);
        ">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 4px;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span class="badge ${isClaimed ? 'badge-neutral' : 'badge-emerald'}" style="font-size: 9.5px;">
                ${isClaimed ? 'CLAIMED' : 'UNCLAIMED'}
              </span>
              <span style="font-size: 11px; font-family: var(--font-mono); color: var(--accent-cyan);">#${mid}</span>
            </div>
            <span style="font-size: 10.5px; color: var(--text-tertiary);">${formatTimestamp(m.receive_time)}</span>
          </div>

          <div style="font-weight: 600; color: #fff; font-size: 13px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${escapeHtml(m.title || 'Untitled Mail')}
          </div>

          <div style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 8px; display: flex; justify-content: space-between;">
            <span>From: <strong style="color: var(--text-primary);">${escapeHtml(m.sender_nick || 'Admin')}</strong></span>
          </div>

          <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              ${coins > 0 ? `<span class="badge badge-amber" style="font-size: 9.5px;">+${formatNumber(coins)} Gold</span>` : ''}
              ${gems > 0 ? `<span class="badge badge-cyan" style="font-size: 9.5px;">+${formatNumber(gems)} Dia</span>` : ''}
              ${attachments.length > 0 ? `<span class="badge badge-neutral" style="font-size: 9.5px;">${attachments.length} Items</span>` : ''}
            </div>
            <div style="display: flex; gap: 4px;" onclick="event.stopPropagation();">
              ${!isClaimed ? `
                <button class="btn btn-primary" style="padding: 2px 8px; font-size: 10.5px;" onclick="window.SocialMail.confirmClaim(${mid})">Claim</button>
              ` : ''}
              <button class="btn btn-danger" style="padding: 2px 8px; font-size: 10.5px;" onclick="window.SocialMail.confirmDelete(${mid}, '${escapeHtml(m.title || 'Untitled Mail').replace(/'/g, "\\'")}')">✕</button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderMailDetailHtml(mail, aid) {
    if (!mail) {
      return `
        <div style="padding: 60px 20px; text-align: center; color: var(--text-tertiary);">
          <div style="font-size: 32px; margin-bottom: 8px; opacity: 0.5;">✉️</div>
          <div style="font-size: 14px; font-weight: 500; color: var(--text-secondary);">No Mail Selected</div>
          <div style="font-size: 11.5px; margin-top: 4px;">Choose a message from the inbox to inspect contents and claim attachments.</div>
        </div>
      `;
    }

    const mid = mail.mail_id || mail.id;
    const isClaimed = Boolean(mail.is_claimed);
    const coins = Number(mail.coins || 0);
    const gems = Number(mail.gems || 0);
    const attachments = mail.attachments || [];

    return `
      <div>
        <div class="glass-card-header" style="margin-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span class="badge badge-cyan">MAIL #${mid}</span>
              <span class="badge ${isClaimed ? 'badge-neutral' : 'badge-emerald'}">${isClaimed ? 'STATUS: CLAIMED' : 'STATUS: UNCLAIMED'}</span>
            </div>
            <div class="glass-card-title" style="font-size: 18px;">${escapeHtml(mail.title || 'Untitled Mail')}</div>
            <div class="glass-card-subtitle" style="font-size: 11.5px;">
              Dispatched by: <strong style="color: var(--accent-cyan);">${escapeHtml(mail.sender_nick || 'Admin')}</strong> (Sender ID: ${mail.sender_id || 0}) &bull; ${formatTimestamp(mail.receive_time)}
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            ${!isClaimed ? `
              <button class="btn btn-primary" onclick="window.SocialMail.confirmClaim(${mid})">Claim Rewards</button>
            ` : `
              <button class="btn btn-secondary" disabled style="opacity: 0.6; cursor: not-allowed;">Claimed</button>
            `}
            <button class="btn btn-danger" onclick="window.SocialMail.confirmDelete(${mid}, '${escapeHtml(mail.title || 'Untitled Mail').replace(/'/g, "\\'")}')">Delete Mail</button>
          </div>
        </div>

        <!-- Body Message Content Box -->
        <div style="margin-bottom: 20px;">
          <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; margin-bottom: 6px;">Message Content</div>
          <div style="background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border-default); border-radius: var(--radius-sm); padding: 14px; font-size: 13px; line-height: 1.6; color: var(--text-primary); white-space: pre-wrap;">
            ${escapeHtml(mail.content || '(Empty message body)')}
          </div>
        </div>

        <!-- Attached Rewards -->
        <div style="margin-bottom: 24px;">
          <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; margin-bottom: 8px;">Attached Claimable Assets</div>
          <div style="display: flex; flex-wrap: wrap; gap: 10px;">
            ${coins > 0 ? `
              <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: var(--radius-sm); padding: 8px 14px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">🪙</span>
                <div>
                  <div style="font-size: 10px; color: var(--accent-amber); font-weight: 600; text-transform: uppercase;">Gold Balance</div>
                  <div style="font-size: 14px; font-weight: 700; color: #fff;">+${formatNumber(coins)}</div>
                </div>
              </div>
            ` : ''}

            ${gems > 0 ? `
              <div style="background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: var(--radius-sm); padding: 8px 14px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">💎</span>
                <div>
                  <div style="font-size: 10px; color: var(--accent-cyan); font-weight: 600; text-transform: uppercase;">Diamonds</div>
                  <div style="font-size: 14px; font-weight: 700; color: #fff;">+${formatNumber(gems)}</div>
                </div>
              </div>
            ` : ''}

            ${attachments.map(att => {
              const meta = ITEM_CATALOG[att.item_id] || { name: 'Item #' + att.item_id, cat: 'Inventory Item' };
              return `
                <div style="background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: var(--radius-sm); padding: 8px 14px; display: flex; align-items: center; gap: 8px;">
                  <span style="font-size: 16px;">📦</span>
                  <div>
                    <div style="font-size: 10px; color: var(--accent-violet); font-weight: 600; text-transform: uppercase;">${escapeHtml(meta.cat)}</div>
                    <div style="font-size: 13px; font-weight: 600; color: #fff;">${escapeHtml(meta.name)} &times;${att.count || 1}</div>
                    <div style="font-size: 10px; color: var(--text-tertiary); font-family: var(--font-mono);">ID: ${att.item_id}</div>
                  </div>
                </div>
              `;
            }).join('')}

            ${coins === 0 && gems === 0 && attachments.length === 0 ? `
              <div style="color: var(--text-tertiary); font-size: 12px; padding: 10px 0;">No claimable attachments enclosed with this correspondence.</div>
            ` : ''}
          </div>
        </div>

        <!-- Wire JSON Inspector -->
        <details style="background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 10px 14px;">
          <summary style="font-size: 11px; font-weight: 600; color: var(--text-secondary); cursor: pointer; user-select: none;">
            Inspect Protobuf Wire State (JSON)
          </summary>
          <pre style="margin-top: 10px; font-family: var(--font-mono); font-size: 11px; color: #a5f3fc; overflow-x: auto; white-space: pre-wrap; line-height: 1.5;">${escapeHtml(JSON.stringify(mail, null, 2))}</pre>
        </details>
      </div>
    `;
  }

  function confirmClaim(mailId) {
    const mail = state.mails.find(m => (m.mail_id || m.id) === mailId);
    const title = mail ? mail.title : `Mail #${mailId}`;
    window.UI.Confirm(
      'Claim Mail Rewards',
      `Claim enclosed currencies and item rewards from "${escapeHtml(title)}" (Mail #${mailId})? Assets will be deposited directly to your wallet and inventory.`,
      () => {
        claimMail(mailId);
      },
      false
    );
  }

  async function claimMail(mailId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const res = await window.apiClient.post('/api/dashboard/mail/claim', {
      account_id: aid,
      mail_id: mailId
    });

    if (res && res.ok) {
      window.UI.Toast('Rewards claimed for Mail #' + mailId, 'success');
      if (window.playerContext) window.playerContext.refresh();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Claim failed: ' + ((res && res.error) || 'Unknown error'), 'error');
    }
  }

  function confirmClaimAll() {
    const unclaimedCount = state.mails.filter(m => !m.is_claimed).length;
    if (unclaimedCount === 0) return;
    window.UI.Confirm(
      'Claim All Mail Rewards',
      `Are you sure you want to claim all attachments across ${unclaimedCount} unclaimed inbox messages?`,
      () => {
        claimAllMails();
      },
      false
    );
  }

  async function claimAllMails() {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const res = await window.apiClient.post('/api/dashboard/mail/claim', {
      account_id: aid,
      mail_id: 'all'
    });

    if (res && res.ok) {
      const gold = res.data && res.data.claimed_coins ? formatNumber(res.data.claimed_coins) : '0';
      const gems = res.data && res.data.claimed_gems ? formatNumber(res.data.claimed_gems) : '0';
      window.UI.Toast(`Claimed all inbox rewards! (+${gold} Gold, +${gems} Diamonds)`, 'success');
      if (window.playerContext) window.playerContext.refresh();
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Claim all failed: ' + ((res && res.error) || 'Unknown error'), 'error');
    }
  }

  function confirmDelete(mailId, mailTitle) {
    window.UI.Confirm(
      'Delete Mail Message',
      `Are you sure you want to permanently delete Mail #${mailId} ("${mailTitle}")? This action cannot be reversed.`,
      () => {
        deleteMail(mailId);
      },
      true
    );
  }

  async function deleteMail(mailId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const res = await window.apiClient.post('/api/dashboard/mail/delete', {
      account_id: aid,
      mail_id: mailId
    });

    if (res && res.ok) {
      window.UI.Toast('Deleted Mail #' + mailId, 'info');
      if (state.selectedMailId === mailId) {
        state.selectedMailId = null;
      }
      render(document.getElementById('workspace-canvas'));
    } else {
      window.UI.Toast('Delete failed: ' + ((res && res.error) || 'Unknown error'), 'error');
    }
  }

  function selectMail(mailId) {
    state.selectedMailId = mailId;
    const canvas = document.getElementById('workspace-canvas');
    const detailPane = document.getElementById('mail-detail-pane');
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const selectedMail = state.mails.find(m => (m.mail_id || m.id) === mailId);

    if (detailPane) {
      detailPane.innerHTML = renderMailDetailHtml(selectedMail, aid);
    }
    const listContainer = document.getElementById('mail-list-container');
    if (listContainer) {
      listContainer.innerHTML = renderMailItemsHtml(getFilteredMails());
    }
  }

  function onFilterChange(val) {
    state.filterQuery = val || '';
    const listContainer = document.getElementById('mail-list-container');
    if (listContainer) {
      listContainer.innerHTML = renderMailItemsHtml(getFilteredMails());
    }
  }

  function onStatusChange(val) {
    state.filterStatus = val || 'all';
    const listContainer = document.getElementById('mail-list-container');
    if (listContainer) {
      listContainer.innerHTML = renderMailItemsHtml(getFilteredMails());
    }
  }

  function refresh() {
    render(document.getElementById('workspace-canvas'));
    window.UI.Toast('Mailbox refreshed', 'info');
  }

  // Public Interface
  const SocialMail = {
    render,
    selectMail,
    confirmClaim,
    confirmClaimAll,
    claimMail,
    claimAllMails,
    confirmDelete,
    deleteMail,
    onFilterChange,
    onStatusChange,
    refresh
  };

  root.SocialMail = SocialMail;

  // React to player switching
  if (root.playerContext) {
    root.playerContext.subscribe((aid) => {
      if (window.location.hash === '#/social/mail') {
        state.selectedMailId = null;
        SocialMail.render(document.getElementById('workspace-canvas'));
      }
    });
  }

})(typeof window !== 'undefined' ? window : this);
