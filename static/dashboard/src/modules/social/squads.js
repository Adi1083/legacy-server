/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Domain 07: Social & Communication — Squad Manager (#/social/squads)
 */

(function (root) {
  'use strict';

  const BOT_ROSTER = [
    { uid: 20001, nick: 'IndiaV1_Bot', role: 'Server Bot' },
    { uid: 20002, nick: 'Kelly_Dash', role: 'Speed Runner' },
    { uid: 20003, nick: 'Hayato_Blade', role: 'Samurai Leader' },
    { uid: 20004, nick: 'Kla_OnePunch', role: 'Muay Thai Boxer' },
    { uid: 20005, nick: 'Paloma_Arms', role: 'Arms Dealer' },
    { uid: 20006, nick: 'Moco_Eye', role: 'Hacker Specialist' },
    { uid: 20007, nick: 'Laura_Sniper', role: 'Sharpshooter' },
    { uid: 20008, nick: 'Rafael_Silent', role: 'Dead Silent' },
    { uid: 20009, nick: 'A124_Android', role: 'Thrill of Battle' },
    { uid: 20010, nick: 'Alok_DJ', role: 'Drop the Beat' },
  ];

  const state = {
    team: null,
    invitations: [],
    invitableFriends: [],
    rooms: [],
    tcpLogs: [
      {
        time: new Date().toLocaleTimeString(),
        badge: 'READY',
        text: 'TCP Socket (Port 8081) ready for GroupInviteNtf dispatch.'
      }
    ],
    isLoading: false
  };

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/&/g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getMapName(mapId) {
    const m = Number(mapId);
    if (m === 1) return 'Bermuda';
    if (m === 2) return 'Purgatory';
    if (m === 3) return 'Kalahari';
    return 'Classic';
  }

  async function fetchSquadData() {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    state.isLoading = true;
    try {
      const res = await window.apiClient.get('/api/dashboard/squad', { account_id: aid });
      if (res && res.ok && res.data) {
        state.team = res.data.team || null;
        state.invitations = res.data.team_invitations || [];
        state.invitableFriends = res.data.invitable_friends || [];
        state.rooms = res.data.rooms || [];
      } else {
        window.UI.Toast('Failed to load squad state: ' + ((res && res.error) || 'Server error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error loading squad state', 'error');
    } finally {
      state.isLoading = false;
    }
  }

  function render(canvas) {
    if (!canvas) canvas = document.getElementById('workspace-canvas');
    if (!canvas) return;

    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    canvas.innerHTML = window.UI.Loading('Loading squad lobby telemetry...');

    fetchSquadData().then(() => {
      buildUI(canvas, aid);
    });
  }

  function buildUI(canvas, aid) {
    const team = state.team;
    const isLeader = team && (team.leader_id === aid || (team.members && team.members.some(m => m.account_id === aid && m.role === 1)));
    const myMember = team && (team.members || []).find(m => m.account_id === aid);
    const myReady = myMember ? Boolean(myMember.ready) : false;

    const html = `
      <div class="social-squads-module">
        <!-- Squad Status Banner -->
        <div class="glass-card" style="margin-bottom: 20px; padding: 16px 20px;">
          <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 14px;">
            <div>
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span class="badge ${team ? 'badge-cyan' : 'badge-neutral'}">
                  ${team ? `SQUAD #${team.team_id}` : 'SOLO LOBBY'}
                </span>
                <span style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono);">Active Account: ${aid}</span>
              </div>
              <div class="glass-card-title" style="font-size: 18px;">
                ${team ? escapeHtml(team.team_name || 'India V1 Squad') : 'Solo Pre-Match Lobby'}
              </div>
              <div class="glass-card-subtitle">
                ${team ? `Mode: ${(team.mode || 'squad').toUpperCase()} &bull; Map: ${getMapName(team.map_id)} &bull; ${team.members ? team.members.length : 1}/4 Slots Occupied` : 'Not in an active squad session. Form a squad or send TCP invites below.'}
              </div>
            </div>

            <!-- Action Controls -->
            <div style="display: flex; gap: 8px; align-items: center;">
              ${team ? `
                <button class="btn ${myReady ? 'btn-secondary' : 'btn-success'}" onclick="window.SocialSquads.toggleReady()">
                  <span>${myReady ? '⏳ Set to Preparing' : '✅ Ready Up!'}</span>
                </button>
                <button class="btn btn-danger" onclick="window.SocialSquads.confirmLeaveSquad()">
                  <span>Leave Squad</span>
                </button>
              ` : `
                <button class="btn btn-primary" onclick="window.SocialSquads.scrollToCreate()">
                  <span>+ Create Squad</span>
                </button>
              `}
              <button class="btn btn-secondary" onclick="window.SocialSquads.refresh()" title="Refresh Squad State">
                <span>🔄</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 4-Slot Tactical Roster Grid -->
        <div class="glass-card" style="padding: 20px; margin-bottom: 20px;">
          <div class="glass-card-header" style="margin-bottom: 16px;">
            <div>
              <div class="glass-card-title" style="font-size: 14px;">Tactical Squad Formation (4-Slot Roster)</div>
              <div class="glass-card-subtitle">Real-time player role badges, ready states, and member controls</div>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;">
            ${renderSquadSlotsHtml(team, aid)}
          </div>
        </div>

        <!-- 2-Column Split: TCP Trigger on Left, Incoming Invites & Create on Right -->
        <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; align-items: start;">
          <!-- Left: Instant TCP Squad Invite Dispatcher -->
          <div class="glass-card" style="padding: 20px;">
            <div class="glass-card-header" style="margin-bottom: 16px;">
              <div>
                <div class="glass-card-title" style="font-size: 14px;">Instant TCP Squad Invite Controller</div>
                <div class="glass-card-subtitle">Pushes binary GroupInviteNtf over TCP Port 8081 directly to live game client</div>
              </div>
              <span class="badge badge-emerald">PORT 8081</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px;">
              <!-- Invite Direction -->
              <div>
                <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Transmission Vector</label>
                <select id="tcp-invite-dir" class="form-input" onchange="window.SocialSquads.onDirChange(this.value)">
                  <option value="to_player">To Player: Simulate Bot/Friend Inviting UID ${aid}</option>
                  <option value="from_player">From Player: UID ${aid} Invites Target Friend/Bot</option>
                </select>
              </div>

              <!-- Target Bot / Friend Picker -->
              <div id="tcp-target-bot-container">
                <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Select Inviting Server Bot</label>
                <select id="tcp-invite-bot" class="form-input">
                  ${BOT_ROSTER.map(b => `
                    <option value="${b.uid}">${b.nick} (UID ${b.uid}) &mdash; ${b.role}</option>
                  `).join('')}
                </select>
              </div>

              <div id="tcp-target-uid-container" style="display: none;">
                <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Target Recipient UID</label>
                <input type="number" id="tcp-invite-target-uid" class="form-input monospace" placeholder="Enter Player UID" value="20001">
              </div>

              <!-- Game Mode & Map -->
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div>
                  <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Game Mode</label>
                  <select id="tcp-invite-gamemode" class="form-input">
                    <option value="1">Classic (Mode 1)</option>
                    <option value="2">Ranked (Mode 2)</option>
                    <option value="3">Rush Hour (Mode 3)</option>
                  </select>
                </div>
                <div>
                  <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Combat Map</label>
                  <select id="tcp-invite-map" class="form-input">
                    <option value="1">Bermuda (Map 1)</option>
                    <option value="2">Purgatory (Map 2)</option>
                    <option value="3">Kalahari (Map 3)</option>
                  </select>
                </div>
              </div>

              <button class="btn btn-primary" style="padding: 10px 16px; font-size: 12.5px; margin-top: 4px;" onclick="window.SocialSquads.triggerTcpInvite()">
                <span>⚡ Transmit TCP Squad Invite</span>
              </button>
            </div>

            <!-- Live TCP Telemetry Stream Console -->
            <div>
              <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; margin-bottom: 6px;">Live Dispatch Telemetry Stream</div>
              <div id="tcp-console-stream" style="
                background: #02040a;
                border: 1px solid var(--border-subtle);
                border-radius: var(--radius-sm);
                padding: 10px 12px;
                font-family: var(--font-mono);
                font-size: 11px;
                line-height: 1.5;
                color: #a5f3fc;
                max-height: 140px;
                overflow-y: auto;
              ">
                ${renderTcpLogsHtml()}
              </div>
            </div>
          </div>

          <!-- Right Column: Pending Invites & Create Squad -->
          <div style="display: flex; flex-direction: column; gap: 20px;">
            <!-- Pending Incoming Squad Invitations -->
            <div class="glass-card" style="padding: 18px;">
              <div class="glass-card-header" style="margin-bottom: 12px;">
                <div>
                  <div class="glass-card-title" style="font-size: 13.5px;">Incoming Squad Invites</div>
                  <div class="glass-card-subtitle">${state.invitations.length} pending squad invitations for UID ${aid}</div>
                </div>
                <span class="badge ${state.invitations.length > 0 ? 'badge-amber' : 'badge-neutral'}">${state.invitations.length}</span>
              </div>

              <div id="squad-invites-container" style="display: flex; flex-direction: column; gap: 8px;">
                ${renderInvitationsHtml(state.invitations, aid)}
              </div>
            </div>

            <!-- Create New Squad Lobby Card -->
            <div class="glass-card" id="create-squad-panel" style="padding: 18px;">
              <div class="glass-card-title" style="font-size: 13.5px; margin-bottom: 4px;">Create Squad Session</div>
              <div class="glass-card-subtitle" style="margin-bottom: 14px;">Establish a new squad room lobby with Account ${aid} as leader</div>

              <div style="display: flex; flex-direction: column; gap: 10px;">
                <div>
                  <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Squad Name</label>
                  <input type="text" id="create-squad-name" class="form-input" value="India V1 Elite Squad">
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                  <div>
                    <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Mode</label>
                    <select id="create-squad-mode" class="form-input">
                      <option value="squad">Squad (4-player)</option>
                      <option value="duo">Duo (2-player)</option>
                    </select>
                  </div>
                  <div>
                    <label style="font-size: 10.5px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; display: block; margin-bottom: 4px;">Map</label>
                    <select id="create-squad-map" class="form-input">
                      <option value="1">Bermuda</option>
                      <option value="2">Purgatory</option>
                      <option value="3">Kalahari</option>
                    </select>
                  </div>
                </div>

                <button class="btn btn-primary" style="margin-top: 4px;" onclick="window.SocialSquads.createSquad()">
                  <span>+ Create Squad Lobby</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    canvas.innerHTML = html;
  }

  function renderSquadSlotsHtml(team, aid) {
    const slots = [];
    const members = team && team.members ? team.members : [];

    for (let i = 0; i < 4; i++) {
      const mem = members[i];
      if (mem) {
        const isLeader = mem.role === 1 || (team && mem.account_id === team.leader_id);
        const isReady = Boolean(mem.ready);
        const isSelf = mem.account_id === aid;

        slots.push(`
          <div class="glass-card squad-slot-card" style="
            background: var(--bg-card);
            backdrop-filter: var(--blur-sm);
            border: 1px solid ${isLeader ? 'rgba(245, 158, 11, 0.45)' : 'rgba(56, 189, 248, 0.35)'};
            border-radius: var(--radius-md);
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            box-shadow: var(--shadow-glass);
            margin-bottom: 0;
            transition: transform var(--transition-fast), border-color var(--transition-fast);
          ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="badge ${isLeader ? 'badge-amber' : 'badge-cyan'}">${isLeader ? 'LEADER' : 'MEMBER'}</span>
              <span class="badge ${isReady ? 'badge-emerald' : 'badge-amber'}">${isReady ? 'READY' : 'PREPARING'}</span>
            </div>

            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="
                width: 42px;
                height: 42px;
                border-radius: 50%;
                background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #fff;
                font-weight: 700;
                font-size: 14px;
                flex-shrink: 0;
              ">
                ${(mem.nickname || `U${mem.account_id}`).substring(0, 2).toUpperCase()}
              </div>
              <div style="min-width: 0;">
                <div style="font-weight: 700; color: #fff; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  ${escapeHtml(mem.nickname || `Player_${mem.account_id}`)}
                </div>
                <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">
                  UID: <code style="font-family: var(--font-mono); color: var(--accent-cyan);">${mem.account_id}</code> ${isSelf ? '<strong style="color:var(--accent-cyan);">(You)</strong>' : ''}
                </div>
              </div>
            </div>

            ${!isLeader ? `
              <div style="margin-top: auto; padding-top: 8px; border-top: 1px solid var(--border-subtle); display: flex; justify-content: flex-end;">
                <button class="btn btn-danger" style="font-size: 11px; padding: 3px 10px;" onclick="window.SocialSquads.confirmKick(${mem.account_id}, '${escapeHtml(mem.nickname || mem.account_id).replace(/'/g, "\\'")}')">
                  Kick Member
                </button>
              </div>
            ` : '<div style="height: 24px;"></div>'}
          </div>
        `);
      } else {
        slots.push(`
          <div class="glass-card squad-slot-card-empty" style="
            background: rgba(10, 16, 28, 0.35);
            backdrop-filter: var(--blur-sm);
            border: 1px dashed var(--border-default);
            border-radius: var(--radius-md);
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            min-height: 145px;
            margin-bottom: 0;
            box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.2);
            transition: all var(--transition-fast);
          ">
            <span class="badge badge-neutral" style="margin-bottom: 8px;">SLOT ${i + 1} OPEN</span>
            <div style="font-size: 11.5px; color: var(--text-tertiary); margin-bottom: 10px;">Available Squad Seat</div>
            <button class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px;" onclick="window.SocialSquads.focusTcpTrigger()">
              + Invite Friend
            </button>
          </div>
        `);
      }
    }

    return slots.join('');
  }

  function renderInvitationsHtml(invites, aid) {
    if (!invites || invites.length === 0) {
      return `<div style="color: var(--text-tertiary); font-size: 11.5px; padding: 12px 4px; text-align: center;">No pending squad invitations.</div>`;
    }

    return invites.map(inv => `
      <div style="background: rgba(10, 16, 28, 0.5); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
        <div>
          <div style="font-weight: 600; color: #fff; font-size: 12.5px;">Invite from ${escapeHtml(inv.inviter_nick || `UID ${inv.inviter_id}`)}</div>
          <div style="font-size: 11px; color: var(--text-tertiary);">Squad #${inv.team_id} &bull; Mode: ${(inv.mode || 'squad').toUpperCase()}</div>
        </div>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-success" style="font-size: 11px; padding: 3px 8px;" onclick="window.SocialSquads.acceptInvite(${inv.team_id})">Join</button>
          <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 8px;" onclick="window.SocialSquads.declineInvite(${inv.invite_id})">✕</button>
        </div>
      </div>
    `).join('');
  }

  function renderTcpLogsHtml() {
    return state.tcpLogs.map(l => `
      <div style="margin-bottom: 3px; display: flex; gap: 8px;">
        <span style="color: var(--text-tertiary); flex-shrink: 0;">[${escapeHtml(l.time)}]</span>
        <span class="badge ${l.badge === 'DELIVERED' ? 'badge-emerald' : (l.badge === 'DISPATCHED' ? 'badge-cyan' : 'badge-neutral')}" style="padding: 1px 5px; font-size: 9px; flex-shrink: 0;">${escapeHtml(l.badge)}</span>
        <span style="overflow-wrap: anywhere;">${escapeHtml(l.text)}</span>
      </div>
    `).join('');
  }

  function appendTcpLog(log) {
    state.tcpLogs.push(log);
    const container = document.getElementById('tcp-console-stream');
    if (container) {
      container.innerHTML = renderTcpLogsHtml();
      container.scrollTop = container.scrollHeight;
    }
  }

  function onDirChange(val) {
    const botContainer = document.getElementById('tcp-target-bot-container');
    const uidContainer = document.getElementById('tcp-target-uid-container');
    if (val === 'to_player') {
      if (botContainer) botContainer.style.display = 'block';
      if (uidContainer) uidContainer.style.display = 'none';
    } else {
      if (botContainer) botContainer.style.display = 'none';
      if (uidContainer) uidContainer.style.display = 'block';
    }
  }

  function focusTcpTrigger() {
    const el = document.getElementById('tcp-invite-dir');
    if (el) el.focus();
    window.UI.Toast('Select a target below to dispatch instant TCP squad invite', 'info');
  }

  function scrollToCreate() {
    const el = document.getElementById('create-squad-panel');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }

  function prepareInvite(friendId) {
    const dirEl = document.getElementById('tcp-invite-dir');
    if (dirEl) {
      dirEl.value = 'from_player';
      onDirChange('from_player');
    }
    const targetEl = document.getElementById('tcp-invite-target-uid');
    if (targetEl) targetEl.value = friendId;
    window.UI.Toast(`Prepared squad invite for UID ${friendId}. Click Transmit!`, 'info');
  }

  async function triggerTcpInvite() {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const dirEl = document.getElementById('tcp-invite-dir');
    const modeEl = document.getElementById('tcp-invite-gamemode');
    const mapEl = document.getElementById('tcp-invite-map');

    const direction = dirEl ? dirEl.value : 'to_player';
    const gameMode = Number(modeEl ? modeEl.value : 1);
    const mapId = Number(mapEl ? mapEl.value : 1);

    let payload = {};
    if (direction === 'to_player') {
      const botId = Number(document.getElementById('tcp-invite-bot').value);
      payload = {
        direction: 'to_player',
        inviter_id: botId,
        account_id: aid,
        mode: 'squad',
        game_mode: gameMode,
        map_id: mapId
      };
    } else {
      const targetId = Number(document.getElementById('tcp-invite-target-uid').value);
      payload = {
        direction: 'from_player',
        account_id: aid,
        target_id: targetId,
        mode: 'squad',
        game_mode: gameMode,
        map_id: mapId,
        auto_join_bot: true
      };
    }

    try {
      const res = await window.apiClient.post('/api/dashboard/squad/invite', payload);
      if (res && res.ok) {
        const tcpPushed = res.data && res.data.tcp_pushed;
        const logLine = {
          time: new Date().toLocaleTimeString(),
          badge: tcpPushed ? 'DELIVERED' : 'DISPATCHED',
          text: `GroupInviteNtf sent: ${direction === 'to_player' ? `Bot #${payload.inviter_id} -> Player #${aid}` : `Player #${aid} -> Target #${payload.target_id}`} (${tcpPushed ? 'TCP Socket 8081 Pushed' : 'Lobby Sync'})`
        };
        appendTcpLog(logLine);
        window.UI.Toast('Squad invite dispatched successfully!', 'success');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Invite trigger failed: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error triggering squad invite', 'error');
    }
  }

  async function createSquad() {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const nameEl = document.getElementById('create-squad-name');
    const modeEl = document.getElementById('create-squad-mode');
    const mapEl = document.getElementById('create-squad-map');

    const teamName = nameEl ? nameEl.value.trim() : 'India V1 Elite Squad';
    const mode = modeEl ? modeEl.value : 'squad';
    const mapId = Number(mapEl ? mapEl.value : 1);

    try {
      const res = await window.apiClient.post('/api/dashboard/squad/create', {
        leader_id: aid,
        mode: mode,
        map_id: mapId,
        team_name: teamName
      });
      if (res && res.ok) {
        window.UI.Toast(`Squad lobby #${res.data && res.data.team ? res.data.team.team_id : ''} created!`, 'success');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to create squad: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error creating squad', 'error');
    }
  }

  async function toggleReady() {
    if (!state.team) return;
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    const myMember = (state.team.members || []).find(m => m.account_id === aid);
    const newReady = myMember ? !myMember.ready : true;

    try {
      const res = await window.apiClient.post('/api/dashboard/squad/ready', {
        team_id: state.team.team_id,
        player_id: aid,
        ready: newReady
      });
      if (res && res.ok) {
        window.UI.Toast(newReady ? 'Status set to READY!' : 'Status set to PREPARING', 'info');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to toggle ready state', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error toggling ready state', 'error');
    }
  }

  function confirmLeaveSquad() {
    window.UI.Confirm(
      'Leave Squad Lobby',
      'Are you sure you want to abandon the current squad session and return to solo queue?',
      () => {
        leaveSquad();
      },
      true
    );
  }

  async function leaveSquad() {
    if (!state.team) return;
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;

    try {
      const res = await window.apiClient.post('/api/dashboard/squad/leave', {
        team_id: state.team.team_id,
        player_id: aid
      });
      if (res && res.ok) {
        window.UI.Toast('Left squad lobby', 'info');
        state.team = null;
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to leave squad: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error leaving squad', 'error');
    }
  }

  function confirmKick(targetId, targetNick) {
    window.UI.Confirm(
      'Kick Squad Member',
      `Are you sure you want to kick player "${targetNick}" (UID: ${targetId}) from the squad?`,
      () => {
        kickMember(targetId);
      },
      true
    );
  }

  async function kickMember(targetId) {
    if (!state.team) return;
    try {
      const res = await window.apiClient.post('/api/dashboard/squad/kick', {
        team_id: state.team.team_id,
        target_id: targetId
      });
      if (res && res.ok) {
        window.UI.Toast(`Removed player #${targetId} from squad`, 'info');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Kick failed: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error kicking squad member', 'error');
    }
  }

  async function acceptInvite(teamId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    try {
      const res = await window.apiClient.post('/api/dashboard/squad/join', {
        team_id: teamId,
        player_id: aid
      });
      if (res && res.ok) {
        window.UI.Toast(`Joined Squad #${teamId}!`, 'success');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to join squad: ' + ((res && res.error) || 'Unknown error'), 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error joining squad', 'error');
    }
  }

  async function declineInvite(inviteId) {
    const aid = window.playerContext ? window.playerContext.getSelectedAccountId() : 10001;
    try {
      const res = await window.apiClient.post('/api/dashboard/squad/decline', {
        account_id: aid,
        invite_id: inviteId
      });
      if (res && res.ok) {
        window.UI.Toast('Declined squad invitation', 'info');
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Failed to decline invite', 'error');
      }
    } catch (err) {
      window.UI.Toast('Network error declining squad invite', 'error');
    }
  }

  function refresh() {
    render(document.getElementById('workspace-canvas'));
    window.UI.Toast('Squad status refreshed', 'info');
  }

  // Public Interface
  const SocialSquads = {
    render,
    onDirChange,
    focusTcpTrigger,
    scrollToCreate,
    prepareInvite,
    triggerTcpInvite,
    createSquad,
    toggleReady,
    confirmLeaveSquad,
    leaveSquad,
    confirmKick,
    kickMember,
    acceptInvite,
    declineInvite,
    refresh
  };

  root.SocialSquads = SocialSquads;

  if (root.playerContext) {
    root.playerContext.subscribe((aid) => {
      if (window.location.hash === '#/social/squads') {
        SocialSquads.render(document.getElementById('workspace-canvas'));
      }
    });
  }

})(typeof window !== 'undefined' ? window : this);
