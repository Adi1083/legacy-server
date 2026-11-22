/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Domain 07: Social & Communication — Friends Manager (#/social/friends)
 */

(function (root) {
  'use strict';

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

  const state = {
    friends: [],
    requests: [],
    recommended: [],
    allPlayers: [],
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

  function getStatusBadge(statusNum) {
    const s = Number(statusNum);
    if (s === 1) return '<span class="badge badge-emerald">IN LOBBY</span>';
    if (s === 2) return '<span class="badge badge-cyan">IN SQUAD</span>';
    if (s === 3) return '<span class="badge badge-amber">IN MATCH</span>';
    return '<span class="badge badge-neutral">OFFLINE</span>';
  }

  function getStatusName(statusNum) {
    const s = Number(statusNum);
    if (s === 1) return 'In Lobby';
    if (s === 2) return 'In Squad';
    if (s === 3) return 'In Match';
    return 'Offline';
  }

  async function fetchFriends() {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    state.isLoading = true;
    try {
      const res = await window.apiClient.get('/api/dashboard/friends', { account_id: aid });
      if (res && res.ok && res.data) {
        state.friends = res.data.friends || [];
        state.requests = res.data.friend_requests || [];
        state.recommended = res.data.recommended_friends || [];
        state.allPlayers = res.data.all_players || [];
      } else {
        window.UI.Toast('Failed to load friends roster: ' + ((res && res.error) || 'Server error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error loading friends roster', 'error');
    } finally {
      state.isLoading = false;
    }
  }

  function getFilteredFriends() {
    let items = state.friends || [];
    if (state.filterQuery) {
      const q = state.filterQuery.toLowerCase();
      items = items.filter(f =>
        (f.nickname && f.nickname.toLowerCase().includes(q)) ||
        String(f.account_id).includes(q) ||
        (f.clan_name && f.clan_name.toLowerCase().includes(q))
      );
    }
    if (state.filterStatus !== 'all') {
      const targetStatus = Number(state.filterStatus);
      items = items.filter(f => Number(f.online_status || (f.is_online ? 1 : 0)) === targetStatus);
    }
    return items;
  }

  function render(canvas) {
    if (!canvas) canvas = document.getElementById('workspace-canvas');
    if (!canvas) return;

    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    canvas.innerHTML = window.UI.Loading('Loading social connections & friends roster...');

    fetchFriends().then(() => {
      buildUI(canvas, aid);
    });
  }

  function buildUI(canvas, aid) {
    const filteredFriends = getFilteredFriends();
    const totalFriends = state.friends.length;
    const onlineCount = state.friends.filter(f => Number(f.online_status || (f.is_online ? 1 : 0)) > 0).length;
    const inLobbyCount = state.friends.filter(f => Number(f.online_status || (f.is_online ? 1 : 0)) === 1).length;
    const inSquadMatchCount = state.friends.filter(f => Number(f.online_status || (f.is_online ? 1 : 0)) >= 2).length;
    const pendingReqsCount = state.requests.length;

    // Filter available bots not currently in friend list
    const currentFriendIds = new Set(state.friends.map(f => f.account_id));
    const availableBots = BOT_ROSTER.filter(b => !currentFriendIds.has(b.uid));

    const html = `
      <div class="social-friends-module">
        <!-- KPI Strip -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
          <div style="background: var(--bg-card); backdrop-filter: var(--blur-sm); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 14px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Friends Total</div>
            <div style="font-size: 22px; font-weight: 700; color: #fff; margin: 4px 0;">${totalFriends} <span style="font-size: 12px; color: var(--text-tertiary); font-weight: 400;">Connections</span></div>
            <div style="font-size: 11px; color: var(--text-secondary);">Target UID: <code style="color: var(--accent-cyan); font-family: var(--font-mono);">${aid}</code></div>
          </div>
          <div style="background: var(--bg-card); backdrop-filter: var(--blur-sm); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 14px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Online Telemetry</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-emerald); margin: 4px 0;">${onlineCount} <span style="font-size: 12px; color: var(--text-tertiary); font-weight: 400;">Active Now</span></div>
            <div style="font-size: 11px; color: var(--text-secondary);">${inLobbyCount} Lobby &bull; ${inSquadMatchCount} Squad/Match</div>
          </div>
          <div style="background: var(--bg-card); backdrop-filter: var(--blur-sm); border: 1px solid var(--border-default); border-radius: var(--radius-md); padding: 14px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; letter-spacing: 0.05em;">Pending Requests</div>
            <div style="font-size: 22px; font-weight: 700; color: ${pendingReqsCount > 0 ? 'var(--accent-amber)' : '#fff'}; margin: 4px 0;">${pendingReqsCount} <span style="font-size: 12px; color: var(--text-tertiary); font-weight: 400;">Awaiting Action</span></div>
            <div style="font-size: 11px; color: var(--text-secondary);">Incoming invitations</div>
          </div>
        </div>

        <!-- Filter & Search Bar -->
        <div class="glass-card" style="padding: 14px 18px; margin-bottom: 20px;">
          <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 10px; align-items: center; flex: 1; min-width: 280px;">
              <input type="text" id="friends-search-input" class="form-input" style="max-width: 260px;" placeholder="Search nickname or UID..." value="${escapeHtml(state.filterQuery)}" oninput="window.SocialFriends.onFilterChange(this.value)">
              <select id="friends-status-filter" class="form-input" style="max-width: 160px; cursor: pointer;" onchange="window.SocialFriends.onStatusChange(this.value)">
                <option value="all" ${state.filterStatus === 'all' ? 'selected' : ''}>All Statuses (${totalFriends})</option>
                <option value="1" ${state.filterStatus === '1' ? 'selected' : ''}>In Lobby (${inLobbyCount})</option>
                <option value="2" ${state.filterStatus === '2' ? 'selected' : ''}>In Squad (${state.friends.filter(f => Number(f.online_status) === 2).length})</option>
                <option value="3" ${state.filterStatus === '3' ? 'selected' : ''}>In Match (${state.friends.filter(f => Number(f.online_status) === 3).length})</option>
                <option value="0" ${state.filterStatus === '0' ? 'selected' : ''}>Offline (${totalFriends - onlineCount})</option>
              </select>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <button class="btn btn-secondary" onclick="window.SocialFriends.refresh()" title="Refresh Friends Roster">
                <span>🔄 Refresh</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Main 2-Column Grid -->
        <div style="display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; align-items: start;">
          <!-- Left Column: Friends Roster Table / Cards -->
          <div class="glass-card" style="padding: 20px;">
            <div class="glass-card-header" style="margin-bottom: 16px;">
              <div>
                <div class="glass-card-title" style="font-size: 15px;">Active Friends Roster (${filteredFriends.length})</div>
                <div class="glass-card-subtitle">Real-time presence, GM status simulation, squad invitations</div>
              </div>
              <span class="badge badge-cyan">${onlineCount} ONLINE</span>
            </div>

            <div id="friends-list-container" style="display: flex; flex-direction: column; gap: 10px;">
              ${renderFriendsListHtml(filteredFriends, aid)}
            </div>
          </div>

          <!-- Right Column: Requests & Bot Roster & Add Friend -->
          <div style="display: flex; flex-direction: column; gap: 20px;">
            <!-- Incoming Friend Requests Box -->
            <div class="glass-card" style="padding: 18px;">
              <div class="glass-card-header" style="margin-bottom: 12px;">
                <div>
                  <div class="glass-card-title" style="font-size: 13.5px;">Incoming Requests</div>
                  <div class="glass-card-subtitle">${pendingReqsCount} pending approval</div>
                </div>
                <span class="badge ${pendingReqsCount > 0 ? 'badge-amber' : 'badge-neutral'}">${pendingReqsCount}</span>
              </div>
              <div id="requests-list-container" style="display: flex; flex-direction: column; gap: 8px;">
                ${renderRequestsListHtml(state.requests, aid)}
              </div>
            </div>

            <!-- Manual Link / Add Friend Box -->
            <div class="glass-card" style="padding: 18px;">
              <div class="glass-card-title" style="font-size: 13.5px; margin-bottom: 4px;">Link New Friend</div>
              <div class="glass-card-subtitle" style="margin-bottom: 14px;">Establish two-way social friendship by Account UID</div>

              <div style="display: flex; flex-direction: column; gap: 10px;">
                <div>
                  <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Target Player UID <span style="color: var(--accent-rose);">*</span></label>
                  <input type="number" id="add-friend-uid" class="form-input monospace" placeholder="e.g. 20005">
                </div>
                <div>
                  <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Nickname (Optional)</label>
                  <input type="text" id="add-friend-nick" class="form-input" placeholder="e.g. Kelly">
                </div>
                <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
                  <input type="checkbox" id="add-friend-autoaccept" checked style="accent-color: var(--accent-cyan); cursor: pointer;">
                  <label for="add-friend-autoaccept" style="font-size: 11.5px; color: var(--text-secondary); cursor: pointer;">Auto-accept & bypass confirmation</label>
                </div>
                <button class="btn btn-primary" style="margin-top: 4px;" onclick="window.SocialFriends.submitAddFriend()">
                  <span>+ Add Friend to Account ${aid}</span>
                </button>
              </div>
            </div>

            <!-- Pre-Seeded Server Bot Quick Link -->
            <div class="glass-card" style="padding: 18px;">
              <div class="glass-card-header" style="margin-bottom: 12px;">
                <div>
                  <div class="glass-card-title" style="font-size: 13.5px;">Pre-Seeded Server Bots</div>
                  <div class="glass-card-subtitle">One-click connect test partners</div>
                </div>
              </div>
              <div style="display: flex; flex-direction: column; gap: 8px;">
                ${renderBotRosterHtml(availableBots, aid)}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    canvas.innerHTML = html;
  }

  function renderFriendsListHtml(friends, aid) {
    if (!friends || friends.length === 0) {
      return `
        <div style="padding: 40px 16px; text-align: center; color: var(--text-tertiary); font-size: 12px;">
          No friends found matching current criteria. Use the Quick-Link panel on the right to add friends or connect server bots.
        </div>
      `;
    }

    return friends.map(f => {
      const statusNum = Number(f.online_status || (f.is_online ? 1 : 0));
      return `
        <div style="
          background: rgba(10, 16, 28, 0.45);
          border: 1px solid var(--border-subtle);
          border-radius: var(--radius-sm);
          padding: 12px 14px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          transition: border-color var(--transition-fast);
        ">
          <!-- Profile Cluster -->
          <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
            <div style="
              width: 38px;
              height: 38px;
              border-radius: 50%;
              background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(99, 102, 241, 0.3));
              border: 1px solid rgba(56, 189, 248, 0.4);
              display: flex;
              align-items: center;
              justify-content: center;
              font-weight: 700;
              color: #fff;
              font-size: 13px;
              flex-shrink: 0;
            ">
              ${(f.nickname || 'FL').substring(0, 2).toUpperCase()}
            </div>
            <div style="min-width: 0;">
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span style="font-weight: 600; color: #fff; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(f.nickname || `Player_${f.account_id}`)}</span>
                ${getStatusBadge(statusNum)}
              </div>
              <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">
                <span>UID: <code style="font-family: var(--font-mono); color: var(--accent-cyan);">${f.account_id}</code></span>
                <span>&bull;</span>
                <span>Lv.${f.level || 50}</span>
                ${f.clan_name ? `<span>&bull;</span><span>[${escapeHtml(f.clan_name)}]</span>` : ''}
              </div>
            </div>
          </div>

          <!-- Actions & Presence Switcher -->
          <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
            <!-- GM Live Status Simulator Dropdown -->
            <select class="form-input monospace" style="font-size: 11px; padding: 4px 6px; width: 105px; cursor: pointer;" title="Simulate Online Status" onchange="window.SocialFriends.setStatus(${f.account_id}, this.value)">
              <option value="1" ${statusNum === 1 ? 'selected' : ''}>Lobby</option>
              <option value="2" ${statusNum === 2 ? 'selected' : ''}>Squad</option>
              <option value="3" ${statusNum === 3 ? 'selected' : ''}>Match</option>
              <option value="0" ${statusNum === 0 ? 'selected' : ''}>Offline</option>
            </select>

            <button class="btn btn-primary" style="font-size: 11px; padding: 4px 8px;" onclick="window.SocialFriends.inviteToSquad(${f.account_id})" title="Send Squad Invite">
              <span>+ Invite</span>
            </button>

            <button class="btn btn-danger" style="font-size: 11px; padding: 4px 8px;" onclick="window.SocialFriends.confirmRemove(${f.account_id}, '${escapeHtml(f.nickname || f.account_id).replace(/'/g, "\\'")}')" title="Remove Friend">
              <span>✕</span>
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderRequestsListHtml(requests, aid) {
    if (!requests || requests.length === 0) {
      return `<div style="color: var(--text-tertiary); font-size: 11.5px; padding: 12px 4px; text-align: center;">No incoming friend requests.</div>`;
    }

    return requests.map(r => `
      <div style="background: rgba(10, 16, 28, 0.5); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
        <div>
          <div style="font-weight: 600; color: #fff; font-size: 12.5px;">${escapeHtml(r.nickname || `UID ${r.from_id}`)}</div>
          <div style="font-size: 11px; color: var(--text-tertiary);">${escapeHtml(r.message || "Let's play squad!")}</div>
        </div>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-success" style="font-size: 11px; padding: 3px 8px;" onclick="window.SocialFriends.acceptRequest(${r.from_id})">Accept</button>
          <button class="btn btn-danger" style="font-size: 11px; padding: 3px 8px;" onclick="window.SocialFriends.confirmReject(${r.from_id})">Decline</button>
        </div>
      </div>
    `).join('');
  }

  function renderBotRosterHtml(bots, aid) {
    if (!bots || bots.length === 0) {
      return `<div style="color: var(--text-tertiary); font-size: 11.5px; padding: 8px 4px;">All pre-seeded server bots are already added.</div>`;
    }

    return bots.slice(0, 5).map(b => `
      <div style="background: rgba(10, 16, 28, 0.4); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 8px 10px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
        <div>
          <div style="font-weight: 600; color: #fff; font-size: 12px;">${escapeHtml(b.nick)}</div>
          <div style="font-size: 10.5px; color: var(--text-tertiary);">UID ${b.uid} &bull; ${b.role}</div>
        </div>
        <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 8px;" onclick="window.SocialFriends.quickAddBot(${b.uid}, '${escapeHtml(b.nick).replace(/'/g, "\\'")}')">
          + Link
        </button>
      </div>
    `).join('');
  }

  async function setStatus(playerId, newStatus) {
    try {
      const res = await window.apiClient.post('/api/dashboard/friends/online', {
        player_id: playerId,
        online_status: Number(newStatus)
      });
      if (res && res.ok) {
        window.UI.Toast(`Updated status for UID ${playerId} to ${getStatusName(newStatus)}`, 'success');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to update status', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error updating presence', 'error');
    }
  }

  function inviteToSquad(friendId) {
    if (typeof window !== 'undefined' && window.location) {
      window.location.hash = '#/social/squads';
    }
    setTimeout(() => {
      if (window.SocialSquads && window.SocialSquads.prepareInvite) {
        window.SocialSquads.prepareInvite(friendId);
      }
    }, 150);
  }

  function confirmRemove(friendId, friendNick) {
    window.UI.Confirm(
      'Remove Friend',
      `Are you sure you want to remove "${friendNick}" (UID: ${friendId}) from friends?`,
      () => {
        removeFriend(friendId);
      },
      true
    );
  }

  async function removeFriend(friendId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    try {
      const res = await window.apiClient.post('/api/dashboard/friends/remove', {
        account_id: aid,
        friend_id: friendId
      });
      if (res && res.ok) {
        window.UI.Toast(`Removed friend #${friendId}`, 'info');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to remove friend: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error removing friend', 'error');
    }
  }

  async function acceptRequest(fromId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    try {
      const res = await window.apiClient.post('/api/dashboard/friends/accept', {
        account_id: aid,
        friend_id: fromId
      });
      if (res && res.ok) {
        window.UI.Toast(`Accepted friend request from UID ${fromId}`, 'success');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to accept request', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error accepting request', 'error');
    }
  }

  function confirmReject(fromId) {
    window.UI.Confirm(
      'Decline Friend Request',
      `Decline pending friend request from UID ${fromId}?`,
      () => {
        rejectRequest(fromId);
      },
      true
    );
  }

  async function rejectRequest(fromId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    try {
      const res = await window.apiClient.post('/api/dashboard/friends/reject', {
        account_id: aid,
        friend_id: fromId
      });
      if (res && res.ok) {
        window.UI.Toast(`Declined request from UID ${fromId}`, 'info');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to decline request', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error declining request', 'error');
    }
  }

  async function submitAddFriend() {
    const uidEl = document.getElementById('add-friend-uid');
    const nickEl = document.getElementById('add-friend-nick');
    const autoAcceptEl = document.getElementById('add-friend-autoaccept');
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;

    const friendId = Number(uidEl ? uidEl.value : 0);
    const nickname = nickEl ? nickEl.value.trim() : '';
    const autoAccept = autoAcceptEl ? autoAcceptEl.checked : true;

    if (!friendId) {
      window.UI.Toast('Valid Player UID is required', 'error');
      return;
    }

    try {
      const res = await window.apiClient.post('/api/dashboard/friends/add', {
        account_id: aid,
        friend_id: friendId,
        nickname: nickname || `Player_${friendId}`,
        auto_accept: autoAccept
      });
      if (res && res.ok) {
        window.UI.Toast(`Linked friend ${nickname || friendId}!`, 'success');
        if (uidEl) uidEl.value = '';
        if (nickEl) nickEl.value = '';
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Add friend failed: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error adding friend', 'error');
    }
  }

  async function quickAddBot(uid, nick) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    try {
      const res = await window.apiClient.post('/api/dashboard/friends/add', {
        account_id: aid,
        friend_id: uid,
        nickname: nick,
        auto_accept: true
      });
      if (res && res.ok) {
        window.UI.Toast(`Linked bot ${nick} (#${uid})!`, 'success');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to link bot', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error linking bot', 'error');
    }
  }

  function onFilterChange(val) {
    state.filterQuery = val || '';
    const listContainer = document.getElementById('friends-list-container');
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    if (listContainer) {
      listContainer.innerHTML = renderFriendsListHtml(getFilteredFriends(), aid);
    }
  }

  function onStatusChange(val) {
    state.filterStatus = val || 'all';
    const listContainer = document.getElementById('friends-list-container');
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    if (listContainer) {
      listContainer.innerHTML = renderFriendsListHtml(getFilteredFriends(), aid);
    }
  }

  function refresh() {
    render(document.getElementById('workspace-canvas'));
    window.UI.Toast('Friends list refreshed', 'info');
  }

  // Public Interface
  const SocialFriends = {
    render,
    setStatus,
    inviteToSquad,
    confirmRemove,
    removeFriend,
    acceptRequest,
    confirmReject,
    rejectRequest,
    submitAddFriend,
    quickAddBot,
    onFilterChange,
    onStatusChange,
    refresh
  };

  root.SocialFriends = SocialFriends;

  if (root.playerContext) {
    root.playerContext.subscribe((aid) => {
      if (window.location.hash === '#/social/friends') {
        SocialFriends.render(document.getElementById('workspace-canvas'));
      }
    });
  }

})(typeof window !== 'undefined' ? window : this);
