/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Player Inspector & Deep Dossier
 * Route: #/players/inspector
 * Domain: 02 Player Management
 *
 * Production Implementation: Apple macOS / iPadOS Dark Glassmorphism
 * Zero Emojis • Symmetrical 50/50 Split View • Live Deep Telemetry • Dynamic Context Sync
 */

window.Modules = window.Modules || {};

(function () {
  'use strict';

  // Character mapping helper
  const CHARACTER_NAMES = {
    102000001: 'Andrew',
    102000002: 'Olivia',
    102000003: 'Ford',
    102000004: 'Kelly',
    102000005: 'Nikita',
    102000006: 'Misha',
    102000007: 'Kla',
    102000008: 'Paloma',
    102000009: 'Maxim',
    102000010: 'Caroline',
    102000011: 'Wukong',
    102000012: 'Moco',
    102000013: 'Antonio',
    102000014: 'Hayato',
    102000015: 'Laura',
    102000016: 'Rafael',
    102000017: 'A124',
    102000018: 'Shani',
    102000019: 'Alok',
    102000020: 'Notora',
    102000021: 'Alvaro',
    102000022: 'Steffie',
    102000023: 'Jota',
    102000024: 'Kapella',
    102000025: 'Wolfrahh',
    102000026: 'Luqueta'
  };

  const PET_NAMES = {
    0: 'None Equipped',
    2000001: 'Kitty',
    2000002: 'Mechanical Puppy',
    2000003: 'Night Panther',
    2000004: 'Poring',
    2000005: 'Shiba',
    2000006: 'Robo',
    2000007: 'Spirit Fox',
    2000008: 'Ottero',
    2000009: 'Falco'
  };

  let inspectorCanvas = null;

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Main Module Handler
   */
  window.Modules.PlayersInspector = async function (canvas) {
    inspectorCanvas = canvas;
    const aid = window.playerContext.getSelectedAccountId();

    canvas.innerHTML = window.UI.Loading(`Synchronizing dossier for Account ${aid}...`);

    let player = window.playerContext.getCurrentPlayer();

    // Fetch deep dossier from admin API if available
    try {
      const deepRes = await window.apiClient.get(`/api/admin/players/${aid}`);
      if (deepRes.ok && deepRes.data && deepRes.data.profile) {
        player = {
          ...window.playerContext.getCurrentPlayer(),
          ...deepRes.data,
          profile: deepRes.data.profile,
          wallet: deepRes.data.wallet || (window.playerContext.getCurrentPlayer() || {}).wallet,
          is_banned: deepRes.data.is_banned,
          audit_logs: deepRes.data.audit_logs || []
        };
      }
    } catch (e) {
      // Fallback to existing playerContext state
    }

    if (!player || !player.profile || player.profile.account_id !== aid) {
      await window.playerContext.refresh();
      player = window.playerContext.getCurrentPlayer();
    }

    renderInspectorView(canvas, player);

    // Register reactive listener to player changes
    if (window.playerContext && typeof window.playerContext.onPlayerChange === 'function') {
      window.playerContext.onPlayerChange(async () => {
        if (inspectorCanvas && window.location.hash.includes('inspector')) {
          await window.Modules.PlayersInspector(inspectorCanvas);
        }
      });
    }
  };

  /**
   * Render Inspector Symmetrical 50/50 View
   */
  function renderInspectorView(canvas, customPlayer = null) {
    const aid = window.playerContext.getSelectedAccountId();
    const state = customPlayer || window.playerContext.getCurrentPlayer() || {};
    const prof = state.profile || {};
    const wallet = state.wallet || {};

    if (!prof.account_id && !aid) {
      canvas.innerHTML = `
        <div class="page-container">
          ${window.UI.PageHeader('Player Dossier & Deep Inspector', 'No account selected', '', 'user')}
          ${window.UI.EmptyState(
            'No Player Selected',
            'Please select an account from the directory to inspect its dossier.',
            window.UI.Icon('user', 36, '', 'var(--text-tertiary)'),
            window.UI.Button('Open Player Directory', 'primary', "window.location.hash='#/players/directory'")
          )}
        </div>
      `;
      return;
    }

    const nickname = prof.nickname || 'Unknown Player';
    const level = prof.level || 1;
    const exp = prof.exp || 0;
    const expProgress = Math.min(100, Math.floor((exp % 10000) / 100));
    const diamonds = prof.diamonds !== undefined ? prof.diamonds : (prof.gems || wallet.gems || 0);
    const gold = prof.gold !== undefined ? prof.gold : (prof.coins || wallet.coins || 0);
    const rank = prof.rank || 0;
    const rankingPoints = prof.ranking_points || rank;
    const isBanned = Boolean(prof.is_banned || state.is_banned);
    const isOnline = Boolean(prof.is_online || prof.online_status === 1);
    const badgeCount = prof.badge_cnt || 0;
    const likes = prof.liked || 0;
    const avatarId = prof.avatar_id || prof.selected_avatar_id || 102000001;
    const charName = CHARACTER_NAMES[avatarId] || `Hero #${avatarId}`;
    const petId = prof.selected_pet_id || 0;
    const petName = PET_NAMES[petId] || (petId ? `Companion #${petId}` : 'None Equipped');
    const signature = prof.signature || 'No bio or signature recorded.';
    const region = prof.region || 'IND';
    const createdAt = prof.create_at ? new Date(prof.create_at * 1000).toLocaleString() : 'Legacy Database Record';
    const lastLogin = prof.last_login_at ? new Date(prof.last_login_at * 1000).toLocaleString() : 'Recent Activity';

    // 1. Header Actions Toolbar
    const headerActionsHtml = `
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.04); padding: 3px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border-default);">
          <span style="font-size: 11px; color: var(--text-tertiary);">Account ID:</span>
          <input type="number" id="inspector-aid-input" class="form-input" style="padding: 2px 6px; font-size: 11px; width: 85px; height: 24px; background: transparent; border: 1px solid var(--border-subtle);" value="${aid}">
          <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 11px; height: 24px;" onclick="window.selectAndSetContextPlayer(document.getElementById('inspector-aid-input').value)">Load</button>
        </div>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px; height: 30px;" onclick="window.Modules.PlayersInspector(document.getElementById('workspace-canvas'))" title="Refresh dossier">
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('refresh', 13)} Refresh
          </span>
        </button>
        ${isBanned ? `
          <button class="btn btn-success" style="padding: 4px 12px; font-size: 11px; height: 30px;" onclick="window.executeQuickUnban(${aid})">
            <span style="display: inline-flex; align-items: center; gap: 4px;">
              ${window.UI.Icon('unlock', 13)} Lift Ban
            </span>
          </button>
        ` : `
          <button class="btn btn-danger" style="padding: 4px 12px; font-size: 11px; height: 30px;" onclick="window.executeQuickBan(${aid})">
            <span style="display: inline-flex; align-items: center; gap: 4px;">
              ${window.UI.Icon('ban', 13)} Suspend Account
            </span>
          </button>
        `}
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px; height: 30px;" onclick="window.location.hash='#/players/directory'">
          Directory
        </button>
      </div>
    `;

    // 2. Exactly 4 Compact Metrics (.grid-4)
    const metricCardsHtml = `
      <div class="grid-4" style="margin-bottom: var(--space-md);">
        ${window.UI.StatCard(
          'Target Account',
          `ID ${aid}`,
          escapeHtml(nickname),
          window.UI.Icon('user', 16, '', 'var(--accent-cyan)'),
          'cyan'
        )}
        ${window.UI.StatCard(
          'Combat Level',
          `Lv. ${level}`,
          `${exp.toLocaleString()} Total EXP`,
          window.UI.Icon('award', 16, '', 'var(--accent-emerald)'),
          'emerald'
        )}
        ${window.UI.StatCard(
          'Rank Progression',
          `${rankingPoints} RP`,
          `Rank Tier ${rank}`,
          window.UI.Icon('trophy', 16, '', 'var(--accent-amber)'),
          'amber'
        )}
        ${window.UI.StatCard(
          'Account Sanction',
          isBanned ? 'SUSPENDED' : 'GOOD STANDING',
          isOnline ? 'Online in Session' : 'Offline',
          window.UI.Icon(isBanned ? 'ban' : 'shield', 16, '', isBanned ? 'var(--accent-rose)' : 'var(--accent-emerald)'),
          isBanned ? 'rose' : 'emerald'
        )}
      </div>
    `;

    // 3. Symmetrical 50/50 Split View Layout
    // --- LEFT COLUMN: Identity & Combat Progression ---
    const leftColumnHtml = `
      <div style="display: flex; flex-direction: column; gap: var(--space-md);">
        <!-- Card 1: Identity Dossier -->
        ${window.UI.Card(
          'Account Identity & Telemetry',
          'Database record parameters and session identification',
          `
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--border-subtle);">
              <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 44px; height: 44px; border-radius: var(--radius-md); background: rgba(56, 189, 248, 0.12); border: 1px solid var(--border-default); display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: var(--accent-cyan);">
                  ${nickname.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div style="font-size: 16px; font-weight: 700; color: #fff;">${escapeHtml(nickname)}</div>
                  <div style="font-size: 11.5px; color: var(--accent-cyan); font-family: var(--font-mono);">Account ID: ${aid}</div>
                </div>
              </div>
              <div style="display: flex; gap: 6px;">
                ${isBanned ? window.UI.Badge('BANNED', 'rose') : window.UI.Badge('ACTIVE', 'emerald')}
                ${isOnline ? window.UI.Badge('ONLINE', 'cyan') : window.UI.Badge('OFFLINE', 'neutral')}
              </div>
            </div>

            <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12.5px;">
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-tertiary);">Server Region:</span>
                <span style="color: #fff; font-family: var(--font-mono);">${escapeHtml(region)}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-tertiary);">Registration Date:</span>
                <span style="color: var(--text-secondary);">${createdAt}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-tertiary);">Last Seen Telemetry:</span>
                <span style="color: var(--text-secondary);">${lastLogin}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: var(--text-tertiary);">Session Auth Token:</span>
                <code style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">
                  ${prof.token ? prof.token.substring(0, 16) + '...' : 'System Session Token'}
                </code>
              </div>
            </div>

            <div style="margin-top: 14px;">
              <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Player Bio / Signature:</div>
              <div style="background: rgba(0, 0, 0, 0.25); padding: 10px 12px; border-radius: var(--radius-sm); border-left: 3px solid var(--accent-cyan); font-style: italic; color: var(--text-secondary); font-size: 12px;">
                "${escapeHtml(signature)}"
              </div>
            </div>
          `,
          `<button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="window.openProfileEditModal(${aid})">
            ${window.UI.Icon('settings', 12)} Edit Profile
          </button>`
        )}

        <!-- Card 2: Combat Progression & Rank -->
        ${window.UI.Card(
          'Combat Progression',
          'Experience milestones, competitive rank, and social engagement',
          `
            <div style="margin-bottom: 14px;">
              <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: var(--text-tertiary); margin-bottom: 4px;">
                <span>EXP Progression (Level ${level})</span>
                <span style="color: var(--text-primary); font-family: var(--font-mono);">${exp.toLocaleString()} EXP</span>
              </div>
              <div style="background: rgba(255, 255, 255, 0.06); height: 7px; border-radius: 4px; overflow: hidden;">
                <div style="background: var(--accent-cyan); height: 100%; width: ${expProgress}%; transition: width 0.3s;"></div>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px;">
              <div style="background: rgba(255, 255, 255, 0.02); padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                <div style="color: var(--text-tertiary); font-size: 10.5px;">Rank Points</div>
                <div style="font-size: 14px; font-weight: 700; color: #fff; font-family: var(--font-mono); margin-top: 2px;">${rankingPoints} RP</div>
              </div>
              <div style="background: rgba(255, 255, 255, 0.02); padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                <div style="color: var(--text-tertiary); font-size: 10.5px;">Elite Pass Badges</div>
                <div style="font-size: 14px; font-weight: 700; color: var(--accent-amber); margin-top: 2px; display: flex; align-items: center; gap: 4px;">
                  ${window.UI.Icon('award', 13, '', 'var(--accent-amber)')} ${badgeCount.toLocaleString()}
                </div>
              </div>
              <div style="background: rgba(255, 255, 255, 0.02); padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                <div style="color: var(--text-tertiary); font-size: 10.5px;">Player Likes</div>
                <div style="font-size: 14px; font-weight: 700; color: var(--accent-rose); margin-top: 2px; display: flex; align-items: center; gap: 4px;">
                  ${window.UI.Icon('heart', 13, '', 'var(--accent-rose)')} ${likes.toLocaleString()}
                </div>
              </div>
              <div style="background: rgba(255, 255, 255, 0.02); padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                <div style="color: var(--text-tertiary); font-size: 10.5px;">Guild / Clan</div>
                <div style="font-size: 13px; font-weight: 600; color: #fff; margin-top: 2px;">${escapeHtml(prof.clan_name || 'No Clan')}</div>
              </div>
            </div>
          `
        )}
      </div>
    `;

    // --- RIGHT COLUMN: Active Loadout, Financial Vault & Security Administration ---
    const rightColumnHtml = `
      <div style="display: flex; flex-direction: column; gap: var(--space-md);">
        <!-- Card 3: Hero Loadout & Cosmetics -->
        ${window.UI.Card(
          'Active Hero Loadout',
          'Equipped avatar hero, companion pet, and wardrobe selection',
          `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
              <div style="background: rgba(255, 255, 255, 0.02); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; display: flex; align-items: center; gap: 4px;">
                  ${window.UI.Icon('user', 12, '', 'var(--accent-cyan)')} Equipped Hero
                </div>
                <div style="font-size: 14px; font-weight: 700; color: #fff;">${escapeHtml(charName)}</div>
                <div style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); margin-top: 2px;">ID: ${avatarId}</div>
              </div>

              <div style="background: rgba(255, 255, 255, 0.02); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; display: flex; align-items: center; gap: 4px;">
                  ${window.UI.Icon('pawPrint', 12, '', 'var(--accent-amber)')} Equipped Companion
                </div>
                <div style="font-size: 14px; font-weight: 700; color: #fff;">${escapeHtml(petName)}</div>
                <div style="font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); margin-top: 2px;">ID: ${petId || '0 (None)'}</div>
              </div>
            </div>

            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 4px 8px;" onclick="window.location.hash='#/inventory/manager'">
                ${window.UI.Icon('package', 12)} Inventory Vault
              </button>
              <button class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 4px 8px;" onclick="window.location.hash='#/inventory/wardrobe'">
                ${window.UI.Icon('shirt', 12)} Wardrobe Loadout
              </button>
            </div>
          `
        )}

        <!-- Card 4: Financial Vault & Balances -->
        ${window.UI.Card(
          'Financial Vault & Balances',
          'In-game premium diamonds and persistent gold reserves',
          `
            <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 14px; flex-wrap: wrap;">
              <div style="flex: 1; min-width: 140px; background: rgba(56, 189, 248, 0.06); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(56, 189, 248, 0.2);">
                <div style="font-size: 11px; color: var(--accent-cyan); margin-bottom: 4px; display: flex; align-items: center; gap: 4px;">
                  ${window.UI.Icon('diamond', 13, '', 'var(--accent-cyan)')} Diamonds
                </div>
                <div style="font-size: 20px; font-weight: 700; color: #fff; font-family: var(--font-mono);">${diamonds.toLocaleString()}</div>
              </div>

              <div style="flex: 1; min-width: 140px; background: rgba(245, 158, 11, 0.06); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(245, 158, 11, 0.2);">
                <div style="font-size: 11px; color: var(--accent-amber); margin-bottom: 4px; display: flex; align-items: center; gap: 4px;">
                  ${window.UI.Icon('coins', 13, '', 'var(--accent-amber)')} Gold
                </div>
                <div style="font-size: 20px; font-weight: 700; color: #fff; font-family: var(--font-mono);">${gold.toLocaleString()}</div>
              </div>
            </div>

            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 4px 8px;" onclick="window.location.hash='#/economy/currencies'">
                ${window.UI.Icon('coins', 12)} Currency Manager
              </button>
              <button class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 4px 8px;" onclick="window.location.hash='#/economy/wallet'">
                ${window.UI.Icon('creditCard', 12)} Wallet Ledger
              </button>
            </div>
          `
        )}

        <!-- Card 5: Sanctions & Access Revocation -->
        ${window.UI.Card(
          'Security & Sanctions Status',
          'Enforce access revocation or lift existing disciplinary holds',
          `
            <div style="background: ${isBanned ? 'rgba(244, 63, 94, 0.08)' : 'rgba(16, 185, 129, 0.08)'}; border-left: 3px solid ${isBanned ? 'var(--accent-rose)' : 'var(--accent-emerald)'}; padding: 12px; border-radius: var(--radius-sm); margin-bottom: 14px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; color: #fff; font-size: 13px;">
                  Status: ${isBanned ? 'Suspended / Revoked' : 'Active / Clean Record'}
                </span>
                ${isBanned ? window.UI.Badge('BANNED', 'rose') : window.UI.Badge('AUTHORIZED', 'emerald')}
              </div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 4px; line-height: 1.4;">
                ${isBanned
                  ? 'Account is blocked from lobby authentication handshakes and combat matchmaking.'
                  : 'Account holds valid credentials and unrestricted lobby/combat access.'}
              </div>
            </div>

            <div style="display: flex; gap: 8px;">
              ${isBanned ? `
                <button class="btn btn-success" style="flex: 1; font-size: 11px; padding: 6px 12px;" onclick="window.executeQuickUnban(${aid})">
                  ${window.UI.Icon('unlock', 13)} Lift Disciplinary Sanction
                </button>
              ` : `
                <button class="btn btn-danger" style="flex: 1; font-size: 11px; padding: 6px 12px;" onclick="window.executeQuickBan(${aid})">
                  ${window.UI.Icon('ban', 13)} Suspend Account Access
                </button>
              `}
              <button class="btn btn-secondary" style="flex: 1; font-size: 11px; padding: 6px 12px;" onclick="window.location.hash='#/players/bans'">
                ${window.UI.Icon('shield', 13)} Full Sanctions Panel
              </button>
            </div>
          `
        )}
      </div>
    `;

    // --- BOTTOM SECTION: Audit Log Stream ---
    const auditLogs = state.audit_logs || [];
    const auditRowsHtml = auditLogs.slice(0, 8).map(log => {
      let timeStr = log.timestamp || '—';
      if (typeof log.timestamp === 'number' || (!isNaN(log.timestamp) && String(log.timestamp).length >= 10)) {
        timeStr = new Date(Number(log.timestamp) * 1000).toLocaleString();
      }
      return `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); width: 160px;">${timeStr}</td>
          <td style="width: 120px;">${window.UI.Badge(log.action || 'MUTATION', 'neutral')}</td>
          <td style="font-size: 11.5px; color: var(--text-secondary);">${escapeHtml(log.details || log.reason || 'Record updated')}</td>
        </tr>
      `;
    }).join('');

    const auditLogCardHtml = window.UI.Card(
      'Security Mutation Audit Log',
      'Historical record of administrative interventions, wallet mutations, and profile state changes for this account',
      auditRowsHtml ? `
        ${window.UI.Table(['Timestamp', 'Action', 'Summary Details'], auditRowsHtml)}
      ` : `
        <div style="text-align: center; padding: 18px; color: var(--text-tertiary); font-size: 12px;">
          No disciplinary audit events logged for Account ${aid}.
        </div>
      `
    );

    // 4. Mount into page container
    canvas.innerHTML = `
      <div class="page-container">
        ${window.UI.PageHeader(
          'Player Dossier & Deep Inspector',
          `Comprehensive telemetry, combat progression, loadout, and sanctions for Account ${aid}`,
          headerActionsHtml,
          'user'
        )}
        ${metricCardsHtml}
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: var(--space-md); align-items: start; margin-bottom: var(--space-md);">
          ${leftColumnHtml}
          ${rightColumnHtml}
        </div>
        ${auditLogCardHtml}
      </div>
    `;
  }

  // --- Modal Helpers & Actions ---

  window.openProfileEditModal = function (accountId) {
    const cur = window.playerContext.getCurrentPlayer() || {};
    const prof = cur.profile || {};

    const contentHtml = `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div>
            <label class="form-label">Nickname</label>
            <input type="text" id="modal-edit-nick" class="form-input" value="${escapeHtml(prof.nickname || '')}">
          </div>
          <div>
            <label class="form-label">Region</label>
            <input type="text" id="modal-edit-region" class="form-input" value="${escapeHtml(prof.region || 'IND')}">
          </div>
        </div>

        <div>
          <label class="form-label">Signature / Bio</label>
          <input type="text" id="modal-edit-sig" class="form-input" value="${escapeHtml(prof.signature || '')}">
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
          <div>
            <label class="form-label">Level</label>
            <input type="number" id="modal-edit-level" class="form-input" value="${prof.level || 1}">
          </div>
          <div>
            <label class="form-label">EXP</label>
            <input type="number" id="modal-edit-exp" class="form-input" value="${prof.exp || 0}">
          </div>
          <div>
            <label class="form-label">Rank Points</label>
            <input type="number" id="modal-edit-rp" class="form-input" value="${prof.ranking_points || prof.rank || 0}">
          </div>
        </div>
      </div>
    `;

    const actionsHtml = `
      <button class="btn btn-primary" onclick="window.saveProfileEditChanges(${accountId})">Save Changes</button>
      <button class="btn btn-secondary" onclick="window.UI.CloseModal()">Cancel</button>
    `;

    window.UI.Modal(`Edit Profile: Account ${accountId}`, contentHtml, actionsHtml);
  };

  window.saveProfileEditChanges = async function (accountId) {
    const payload = {
      account_id: accountId,
      nickname: (document.getElementById('modal-edit-nick').value || '').trim(),
      region: (document.getElementById('modal-edit-region').value || '').trim(),
      signature: (document.getElementById('modal-edit-sig').value || '').trim(),
      level: parseInt(document.getElementById('modal-edit-level').value, 10) || 1,
      exp: parseInt(document.getElementById('modal-edit-exp').value, 10) || 0,
      ranking_points: parseInt(document.getElementById('modal-edit-rp').value, 10) || 0
    };

    try {
      const res = await window.apiClient.post('/api/dashboard/profile/update', payload);
      if (res.ok) {
        window.UI.Toast('Profile updated successfully', 'success');
        window.UI.CloseModal();
        await window.playerContext.refresh();
        const canvas = document.getElementById('workspace-canvas');
        if (canvas) window.Modules.PlayersInspector(canvas);
      } else {
        window.UI.Toast(res.error || 'Failed to update profile', 'error');
      }
    } catch (e) {
      window.UI.Toast(`Update error: ${e.message}`, 'error');
    }
  };

  window.executeQuickBan = function (accountId) {
    window.UI.Confirm(
      `Suspend Account ${accountId}?`,
      `Are you sure you want to suspend Account ${accountId}? This will set is_banned = 1 and disconnect active lobby sessions.`,
      async () => {
        try {
          const res = await window.apiClient.post(`/api/admin/players/${accountId}/ban`, {
            reason: 'Disciplinary suspension enforced via Inspector'
          });
          if (res.ok) {
            window.UI.Toast(`Account ${accountId} suspended`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) window.Modules.PlayersInspector(canvas);
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

  window.executeQuickUnban = function (accountId) {
    window.UI.Confirm(
      `Restore Account ${accountId}?`,
      `Lift ban for Account ${accountId} and authorize login access?`,
      async () => {
        try {
          const res = await window.apiClient.post(`/api/admin/players/${accountId}/unban`);
          if (res.ok) {
            window.UI.Toast(`Account ${accountId} restored`, 'success');
            await window.playerContext.refresh();
            const canvas = document.getElementById('workspace-canvas');
            if (canvas) window.Modules.PlayersInspector(canvas);
          } else {
            window.UI.Toast(res.error || 'Failed to unban account', 'error');
          }
        } catch (e) {
          window.UI.Toast(`Unban error: ${e.message}`, 'error');
        }
      }
    );
  };

  // Self-register with AppRouter if initialized
  if (window.appRouter) {
    window.appRouter.register('#/players/inspector', window.Modules.PlayersInspector);
  }
})();
