/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Ban Manager & Sanctions Enforcement
 * Route: #/players/bans
 * Domain: 02 Player Management
 *
 * Production Implementation: Apple macOS / iPadOS Dark Glassmorphism
 * Zero Emojis • Live Sanctions Enforcement • Banned Accounts Fleet • Security Audit Ledger
 */

window.Modules = window.Modules || {};

(function () {
  'use strict';

  const AUDIT_STORAGE_KEY = 'ind_sanction_audit_log';

  function getLocalAuditLog() {
    try {
      return JSON.parse(localStorage.getItem(AUDIT_STORAGE_KEY) || '[]');
    } catch (e) {
      return [];
    }
  }

  function appendAuditLog(entry) {
    const list = getLocalAuditLog();
    list.unshift(entry);
    localStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(list.slice(0, 50)));
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  window.Modules.PlayersBans = async function (canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    let curPlayer = window.playerContext.getCurrentPlayer();

      if (!curPlayer || !curPlayer.profile || curPlayer.profile.account_id !== aid) {
        canvas.innerHTML = window.UI.Loading(`Synchronizing sanction state for Account ${aid}...`);
        await window.playerContext.refresh();
        curPlayer = window.playerContext.getCurrentPlayer();
      }

      // Query banned accounts directory from backend
      let bannedPlayers = [];
      try {
        const banRes = await window.apiClient.get('/api/admin/players', { is_banned: '1', limit: 50 });
        if (banRes.ok && banRes.data) {
          bannedPlayers = banRes.data.players || (Array.isArray(banRes.data) ? banRes.data : []);
        }
      } catch (e) {
        // Fallback: check dashboard state all_players
        try {
          const stateRes = await window.apiClient.get('/api/dashboard/state');
          if (stateRes.ok && stateRes.data && stateRes.data.all_players) {
            bannedPlayers = stateRes.data.all_players.filter(p => p.is_banned);
          }
        } catch (err) { }
      }

      renderBansView(canvas, curPlayer, bannedPlayers);
    };

      function renderBansView(canvas, curPlayer, bannedPlayers) {
        const aid = window.playerContext.getSelectedAccountId();
        const prof = (curPlayer && curPlayer.profile) || {};
        const isBanned = Boolean(prof.is_banned || (curPlayer && curPlayer.is_banned));
        const auditLogs = getLocalAuditLog();

        // 1. Header Actions
        const headerActionsHtml = `
      <div style="display: flex; gap: 8px; align-items: center;">
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px; height: 30px;" onclick="window.Modules.PlayersBans(document.getElementById('workspace-canvas'))">
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('refresh', 13)} Refresh Ledger
          </span>
        </button>
        <button class="btn btn-secondary" style="padding: 4px 12px; font-size: 11px; height: 30px;" onclick="window.location.hash='#/players/directory'">
          Directory
        </button>
      </div>
    `;

    // 2. Exactly 4 Compact Metrics (.grid-4)
    const metricCardsHtml = `
          < div class="grid-4" style = "margin-bottom: var(--space-md);" >
            ${
              window.UI.StatCard(
                'Total Sanctioned Accounts',
                bannedPlayers.length.toString(),
                'Banned in india_v1.db',
                window.UI.Icon('ban', 16, '', 'var(--accent-rose)'),
                'rose'
              )
        }
        ${
          window.UI.StatCard(
            'Target Context Account',
            `Account ${aid}`,
            escapeHtml(prof.nickname || 'Unknown'),
            window.UI.Icon('user', 16, '', 'var(--accent-amber)'),
            'amber'
          )
        }
        ${
          window.UI.StatCard(
            'Security Enforcement Policy',
            'Zero-Tolerance',
            'Anti-Cheat & Netcode Policy',
            window.UI.Icon('shield', 16, '', 'var(--accent-emerald)'),
            'emerald'
          )
        }
        ${
          window.UI.StatCard(
            'Sanction Audit Records',
            auditLogs.length.toString(),
            'Historical Disciplinary Log',
            window.UI.Icon('fileText', 16, '', 'var(--accent-cyan)'),
            'cyan'
          )
        }
      </div >
          `;

    // 3. Symmetrical 2-Column Grid
    // Left Card: Target Account Status & Sanction Controls
    const sanctionControlCardHtml = window.UI.Card(
      'Target Account Status & Sanctions Form',
      'Enforce security suspensions and access revocation against target account',
      `
          < !--Target Player Summary Banner-- >
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-bottom: 14px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div>
                  <span style="font-size: 15px; font-weight: 700; color: #fff;">${escapeHtml(prof.nickname || 'Unknown')}</span>
                  <span style="font-size: 12px; color: var(--accent-cyan); font-family: var(--font-mono); margin-left: 6px;">(ID: ${aid})</span>
                </div>
                  <div>
                    ${isBanned ? window.UI.Badge('SUSPENDED / BANNED', 'rose') : window.UI.Badge('ACTIVE / CLEAN', 'emerald')}
                  </div>
                </div>
                  <div style="display: flex; gap: 12px; font-size: 11px; color: var(--text-tertiary);">
                    <span>Level: <b style="color: #fff;">${prof.level || 1}</b></span>
                    <span>Region: <b style="color: #fff;">${escapeHtml(prof.region || 'IND')}</b></span>
                    <span>Last Active: <b style="color: var(--text-secondary);">${prof.last_login_at ? new Date(prof.last_login_at * 1000).toLocaleDateString() : 'N/A'}</b></span>
                  </div>
                </div>

                  <!-- Target Switcher -->
                  <div style="margin-bottom: 14px;">
                    <label class="form-label">Switch Target Account ID</label>
                    <div style="display: flex; gap: 6px;">
                      <input type="number" id="bans-switch-aid-input" class="form-input" style="height: 30px; font-size: 11.5px;" placeholder="Account ID..." value="${aid}">
                        <button class="btn btn-secondary" style="height: 30px; font-size: 11px; padding: 2px 10px;" onclick="window.playerContext.setAccountId(document.getElementById('bans-switch-aid-input').value).then(() => window.Modules.PlayersBans(document.getElementById('workspace-canvas')))">
                          Load
                        </button>
                    </div>
                  </div>

                      <!-- Enforcement Form -->
                      <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div>
                          <label class="form-label">Infraction Category</label>
                          <select id="ban-reason-select" class="form-select">
                            <option value="Speedhack / Movement Manipulation">Speedhack / Movement Manipulation</option>
                            <option value="Aim Assist / Memory Patching">Aim Assist / Memory Patching</option>
                            <option value="Packet Injection / Netcode Desync">Packet Injection / Netcode Desync</option>
                            <option value="Illegal Currency / Gem Duplication">Illegal Currency / Gem Duplication</option>
                            <option value="Toxic Communication / Harassment">Toxic Communication / Harassment</option>
                            <option value="Administrative Hold / Investigation">Administrative Hold / Investigation</option>
                          </select>
                        </div>

                        <div>
                          <label class="form-label">Sanction Duration</label>
                          <select id="ban-duration-select" class="form-select">
                            <option value="Permanent">Permanent (Indefinite)</option>
                            <option value="30 Days">30 Days</option>
                            <option value="7 Days">7 Days</option>
                            <option value="24 Hours">24 Hours</option>
                          </select>
                        </div>

                          <div>
                            <label class="form-label">Security Officer Notes</label>
                            <textarea id="ban-notes-input" class="form-input" style="height: 55px; resize: none; font-size: 11.5px;" placeholder="Optional telemetry evidence, memory signature, or ticket ID..."></textarea>
                          </div>

                          <div style="display: flex; gap: 8px; margin-top: 4px;">
                            <button class="btn btn-danger" style="flex: 1; height: 34px;" onclick="window.executeBanAction(${aid})">
                              <span style="display: inline-flex; align-items: center; gap: 4px;">
                                ${window.UI.Icon('ban', 13)} Suspend / Ban Account
                              </span>
                            </button>
                            <button class="btn btn-success" style="flex: 1; height: 34px;" onclick="window.executeUnbanAction(${aid})">
                              <span style="display: inline-flex; align-items: center; gap: 4px;">
                                ${window.UI.Icon('unlock', 13)} Lift Ban / Restore
                              </span>
                            </button>
                          </div>
                        </div>
                        `
                        );

                            // Right Card: Restricted / Banned Accounts Directory
                            let bannedTableHtml = '';
    if (bannedPlayers.length > 0) {
      const rows = bannedPlayers.map(p => `
                            <tr>
                              <td><code style="font-family: var(--font-mono); color: var(--accent-rose); font-weight: 700;">${p.account_id}</code></td>
                              <td style="font-weight: 600; color: #fff;">${escapeHtml(p.nickname || 'Unknown')}</td>
                              <td>${window.UI.Badge('Lv.' + (p.level || 1), 'neutral')}</td>
                              <td><span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">${escapeHtml(p.region || 'IND')}</span></td>
                              <td>
                                <div style="display: flex; gap: 4px;">
                                  <button class="btn btn-success" style="padding: 2px 8px; font-size: 10px;" onclick="window.executeUnbanAction(${p.account_id})">
                                    Lift Ban
                                  </button>
                                    <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="window.playerContext.setAccountId(${p.account_id}).then(() => window.location.hash='#/players/inspector')">
                                      Inspect
                                    </button>
                                </div>
                      </td>
                    </tr>
                    `).join('');

                        bannedTableHtml = window.UI.Table(['Account ID', 'Nickname', 'Level', 'Region', 'Actions'], rows);
    } else {
                          bannedTableHtml = window.UI.EmptyState(
                            'No Banned Accounts',
                            'All registered player accounts in india_v1.db are currently in good standing.',
                            window.UI.Icon('shield', 32, '', 'var(--accent-emerald)')
                          );
    }

                        const bannedDirectoryCardHtml = window.UI.Card(
                        `Restricted Fleet Directory (${bannedPlayers.length})`,
                        'Accounts currently restricted from lobby handshake and combat matchmaking',
                        bannedTableHtml
                        );

    // Bottom Card: Sanction Audit Ledger
    const auditRows = auditLogs.map(log => `
                        <tr>
                          <td><code style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan);">${log.timestamp}</code></td>
                          <td><code style="font-family: var(--font-mono); font-weight: 600;">${log.account_id}</code></td>
                          <td>${window.UI.Badge(log.action, log.action === 'BAN' ? 'rose' : 'emerald')}</td>
                          <td style="font-size: 12px;">${escapeHtml(log.reason)}</td>
                          <td style="font-size: 11px; color: var(--text-tertiary);">${escapeHtml(log.duration || 'Permanent')}</td>
                          <td style="font-size: 11px; color: var(--text-muted);">${escapeHtml(log.notes || '—')}</td>
                        </tr>
                        `).join('');

                        const auditLedgerCardHtml = window.UI.Card(
                        'Recent Sanction Audit Ledger',
                        'Historical disciplinary enforcement and ban revocation records',
                        window.UI.Table(['Timestamp', 'Account ID', 'Action', 'Infraction Reason', 'Duration', 'Notes'], auditRows, 'No sanctions recorded in local audit ledger yet.'),
                        `<button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="localStorage.removeItem('${AUDIT_STORAGE_KEY}'); window.Modules.PlayersBans(document.getElementById('workspace-canvas'));">Clear Ledger</button>`
                        );

                        // 4. Mount into page container
                        canvas.innerHTML = `
                        <div class="page-container">
                          ${window.UI.PageHeader(
                            'Sanctions & Ban Enforcement',
                            'Manage security suspensions, access revocation, and infraction history in india_v1.db',
                            headerActionsHtml,
                            'shield'
                          )}
                          ${metricCardsHtml}
                          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: var(--space-md); align-items: start; margin-bottom: var(--space-md);">
                            ${sanctionControlCardHtml}
                            ${bannedDirectoryCardHtml}
                          </div>
                          ${auditLedgerCardHtml}
                        </div>
                        `;
  }

                        // --- Actions ---

                        window.executeBanAction = function (accountId) {
    const reason = document.getElementById('ban-reason-select').value;
                        const duration = document.getElementById('ban-duration-select').value;
                        const notes = (document.getElementById('ban-notes-input').value || '').trim();

                        window.UI.Confirm(
                        `Confirm Suspension: Account ${accountId}`,
                        `Are you sure you want to enforce a ${duration.toLowerCase()} ban on Account ${accountId} for "${reason}"? This sets is_banned = 1 in india_v1.db and rejects subsequent lobby handshakes.`,
      async () => {
                        try {
          const res = await window.apiClient.post(`/api/admin/players/${accountId}/ban`, {
                          reason,
                          duration,
                          notes
                        });

                        if (res.ok) {
                          window.UI.Toast(`Account ${accountId} suspended successfully`, 'success');
                        appendAuditLog({
                          timestamp: new Date().toLocaleTimeString(),
                        account_id: accountId,
                        action: 'BAN',
                        reason,
                        duration,
                        notes
            });
                        await window.playerContext.refresh();
                        const canvas = document.getElementById('workspace-canvas');
                        if (canvas) window.Modules.PlayersBans(canvas);
          } else {
                        window.UI.Toast(res.error || 'Failed to ban account', 'error');
          }
        } catch (e) {
                        window.UI.Toast(`Ban error: ${e.message}`, 'error');
        }
      },
                        true
                        );
  };

                        window.executeUnbanAction = function (accountId) {
                          window.UI.Confirm(
                            `Lift Suspension: Account ${accountId}`,
                            `Are you sure you want to restore full login access for Account ${accountId}? This sets is_banned = 0 in india_v1.db.`,
                            async () => {
                              try {
                                const res = await window.apiClient.post(`/api/admin/players/${accountId}/unban`);

                                if (res.ok) {
                                  window.UI.Toast(`Account ${accountId} restored successfully`, 'success');
                                  appendAuditLog({
                                    timestamp: new Date().toLocaleTimeString(),
                                    account_id: accountId,
                                    action: 'UNBAN',
              reason: 'Administrative reinstatement',
                                    duration: 'N/A',
                                    notes: 'Restored to active status'
                                  });
                                  await window.playerContext.refresh();
                                  const canvas = document.getElementById('workspace-canvas');
                                  if (canvas) window.Modules.PlayersBans(canvas);
                                } else {
                                  window.UI.Toast(res.error || 'Failed to lift ban', 'error');
                                }
                              } catch (e) {
                                window.UI.Toast(`Unban error: ${e.message}`, 'error');
                              }
                            }
                          );
  };

                      // Self-register with AppRouter if initialized
                      if (window.appRouter) {
                        window.appRouter.register('#/players/bans', window.Modules.PlayersBans);
  }
})();
