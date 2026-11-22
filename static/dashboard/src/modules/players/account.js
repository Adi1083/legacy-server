/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Account Manager & Provisioning Engine
 * Route: #/players/account
 * Domain: 02 Player Management
 *
 * Production Implementation: Apple macOS / iPadOS Dark Glassmorphism
 * Zero Emojis • Symmetrical Provisioning Grid • Field-Level Validation • Context Synchronization
 */

window.Modules = window.Modules || {};

(function () {
  'use strict';

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  window.Modules.PlayersAccount = async function (canvas) {
    const aid = window.playerContext.getSelectedAccountId();
    let curPlayer = window.playerContext.getCurrentPlayer();

    if (!curPlayer || !curPlayer.profile) {
      canvas.innerHTML = window.UI.Loading('Synchronizing player state...');
      await window.playerContext.refresh();
      curPlayer = window.playerContext.getCurrentPlayer() || {};
    }

    renderAccountView(canvas, curPlayer);
  };

  function renderAccountView(canvas, curPlayer) {
    const aid = window.playerContext.getSelectedAccountId();
    const prof = (curPlayer && curPlayer.profile) || {};
    const wallet = (curPlayer && curPlayer.wallet) || {};

    const diamonds = prof.diamonds !== undefined ? prof.diamonds : (prof.gems || wallet.gems || 0);
    const gold = prof.gold !== undefined ? prof.gold : (prof.coins || wallet.coins || 0);

    // 1. Header Actions
    const headerActionsHtml = `
      < div style = "display: flex; gap: 8px; align-items: center;" >
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px; height: 30px;" onclick="window.Modules.PlayersAccount(document.getElementById('workspace-canvas'))">
          <span style="display: inline-flex; align-items: center; gap: 4px;">
            ${window.UI.Icon('refresh', 13)} Refresh
          </span>
        </button>
        <button class="btn btn-secondary" style="padding: 4px 12px; font-size: 11px; height: 30px;" onclick="window.location.hash='#/players/directory'">
          Back to Directory
        </button>
      </div >
      `;

    // 2. Exactly 4 Compact Metrics (.grid-4)
    const metricCardsHtml = `
      < div class="grid-4" style = "margin-bottom: var(--space-md);" >
        ${
          window.UI.StatCard(
            'Target Database',
            'india_v1.db',
            'SQLite Persistent Store',
            window.UI.Icon('database', 16, '', 'var(--accent-violet)'),
            'violet'
          )
    }
        ${
      window.UI.StatCard(
        'Active Context',
        `Account ${aid}`,
        escapeHtml(prof.nickname || 'Unknown'),
        window.UI.Icon('userCheck', 16, '', 'var(--accent-amber)'),
        'amber'
      )
    }
        ${
      window.UI.StatCard(
        'Starter Default Level',
        'Level 60',
        '100,000 Starter EXP',
        window.UI.Icon('award', 16, '', 'var(--accent-emerald)'),
        'emerald'
      )
    }
        ${
      window.UI.StatCard(
        'Starter Vault Package',
        '10,000 Gold / 500 Dia',
        'Default Initial Currencies',
        window.UI.Icon('coins', 16, '', 'var(--accent-cyan)'),
        'cyan'
      )
    }
      </div >
      `;

    // 3. Symmetrical 2-Column Grid
    // Card A: Provision New Account
    const provisionCardHtml = window.UI.Card(
      'Provision New Account',
      'Create and insert an authorized player record into india_v1.db',
      `
      < div id = "account-create-feedback" style = "display: none; margin-bottom: 14px;" ></div >

        <div style="display: flex; flex-direction: column; gap: 12px;">
          <div>
            <label class="form-label">Player Nickname *</label>
            <input type="text" id="new-account-nick" class="form-input" placeholder="e.g. GhostRider_99" maxlength="24">
              <div style="font-size: 10.5px; color: var(--text-tertiary); margin-top: 2px;">Unique display name for lobby and battle sessions</div>
          </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div>
                  <label class="form-label">Server Region</label>
                  <select id="new-account-region" class="form-select">
                    <option value="IND" selected>India (IND)</option>
                    <option value="BRA">Brazil (BRA)</option>
                    <option value="ID">Indonesia (ID)</option>
                    <option value="NA">North America (NA)</option>
                    <option value="EU">Europe (EU)</option>
                    <option value="TH">Thailand (TH)</option>
                  </select>
              </div>
                <div>
                  <label class="form-label">Target Account ID (Optional)</label>
                  <input type="number" id="new-account-aid" class="form-input" placeholder="Auto-generated if empty">
                </div>
              </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                  <div>
                    <label class="form-label">Initial Gold (Coins)</label>
                    <input type="number" id="new-account-gold" class="form-input" value="10000" min="0">
                  </div>
                  <div>
                      <label class="form-label">Initial Diamonds (Gems)</label>
                      <input type="number" id="new-account-dia" class="form-input" value="500" min="0">
                      </div>
                  </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                      <div>
                        <label class="form-label">Initial Level</label>
                        <input type="number" id="new-account-level" class="form-input" value="60" min="1" max="100">
                      </div>
                      <div>
                        <label class="form-label">Account Status</label>
                        <select id="new-account-status" class="form-select">
                          <option value="active" selected>Active / Authorized</option>
                          <option value="banned">Suspended / Banned</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label class="form-label">Starter Signature / Bio</label>
                      <input type="text" id="new-account-sig" class="form-input" value="India V1 1.39 Restoration">
                    </div>

                    <div style="margin-top: 6px;">
                      <button id="btn-submit-create-account" class="btn btn-primary" style="width: 100%; height: 36px;" onclick="window.submitCreateAccount()">
                        <span style="display: inline-flex; align-items: center; gap: 6px;">
                          ${window.UI.Icon('plus', 14)} Provision & Initialize Account
                        </span>
                      </button>
                    </div>
                  </div>
                  `
                  );

    // Card B: Active Profile Administration
                      const profileEditCardHtml = window.UI.Card(
                      `Active Profile: Account ${aid}`,
                      'Directly update attributes for the currently active context player',
                      `
                      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
                        <span style="font-size: 12px; color: var(--text-tertiary);">Account Context Status:</span>
                        <div>
                          ${prof.is_banned ? window.UI.Badge('BANNED', 'rose') : window.UI.Badge('ACTIVE', 'emerald')}
                          ${window.UI.Badge('Lv.' + (prof.level || 1), 'neutral')}
                        </div>
                      </div>

                        <div style="display: flex; flex-direction: column; gap: 12px;">
                          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div>
                              <label class="form-label">Player Nickname</label>
                              <input type="text" id="edit-prof-nick" class="form-input" value="${escapeHtml(prof.nickname || '')}">
                            </div>
                            <div>
                              <label class="form-label">Region</label>
                              <select id="edit-prof-region" class="form-select">
                                <option value="IND" ${prof.region === 'IND' ? 'selected' : ''}>India (IND)</option>
                                <option value="BRA" ${prof.region === 'BRA' ? 'selected' : ''}>Brazil (BRA)</option>
                                <option value="ID" ${prof.region === 'ID' ? 'selected' : ''}>Indonesia (ID)</option>
                                <option value="NA" ${prof.region === 'NA' ? 'selected' : ''}>North America (NA)</option>
                                <option value="EU" ${prof.region === 'EU' ? 'selected' : ''}>Europe (EU)</option>
                                <option value="TH" ${prof.region === 'TH' ? 'selected' : ''}>Thailand (TH)</option>
                              </select>
                            </div>
                          </div>

                          <div>
                            <label class="form-label">Signature / Bio Text</label>
                            <input type="text" id="edit-prof-sig" class="form-input" value="${escapeHtml(prof.signature || '')}">
                          </div>

                          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div>
                              <label class="form-label">Combat Level</label>
                              <input type="number" id="edit-prof-level" class="form-input" value="${prof.level || 1}">
                            </div>
                            <div>
                              <label class="form-label">EXP Points</label>
                              <input type="number" id="edit-prof-exp" class="form-input" value="${prof.exp || 0}">
                            </div>
                          </div>

                              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                <div>
                                  <label class="form-label">Rank Tier</label>
                                  <input type="number" id="edit-prof-rank" class="form-input" value="${prof.rank || 0}">
                                </div>
                                <div>
                                  <label class="form-label">Ranking Points (RP)</label>
                                  <input type="number" id="edit-prof-rp" class="form-input" value="${prof.ranking_points || prof.rank || 0}">
                                </div>
                              </div>

                                <div style="margin-top: 6px;">
                                  <button id="btn-submit-edit-profile" class="btn btn-secondary" style="width: 100%; height: 36px;" onclick="window.submitUpdateProfile(${aid})">
                                    <span style="display: inline-flex; align-items: center; gap: 6px;">
                                      ${window.UI.Icon('checkCircle', 14, '', 'var(--accent-emerald)')} Save Profile Changes
                                    </span>
                                  </button>
                                </div>
                              </div>
                              `,
                              `<button class="btn btn-secondary" style="padding: 2px 8px; font-size: 11px;" onclick="window.location.hash='#/players/inspector'">
                                Inspect Dossier
                              </button>`
                              );

                              // Card C: Administrative Danger Zone
                              const dangerZoneCardHtml = `
                              <div style="background: rgba(244, 63, 94, 0.05); padding: 18px 20px; border-radius: var(--radius-md); border: 1px solid rgba(244, 63, 94, 0.25); margin-top: var(--space-md);">
                                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                                  <div>
                                    <div style="font-weight: 600; color: var(--accent-rose); font-size: 13.5px; display: flex; align-items: center; gap: 6px;">
                                      ${window.UI.Icon('alertTriangle', 15, '', 'var(--accent-rose)')} Administrative Danger Zone
                                    </div>
                                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">
                                      Destructive mutations against target Account ${aid} (${escapeHtml(prof.nickname || 'Unknown')}).
                                    </div>
                                  </div>
                                  <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                    <button class="btn btn-secondary" style="font-size: 11px; padding: 6px 12px;" onclick="window.confirmResetAccountData(${aid})">
                                      Reset Account Data
                                    </button>
                                    <button class="btn btn-danger" style="font-size: 11px; padding: 6px 12px;" onclick="window.confirmDeleteAccount(${aid})">
                                      Delete Account ${aid}
                                    </button>
                                  </div>
                                </div>
                              </div>
                              `;

                              // 4. Assemble Page Container
                              canvas.innerHTML = `
                              <div class="page-container">
                                ${window.UI.PageHeader(
                                  'Account Provisioning & Management',
                                  'Create new player records and administer account lifecycle in india_v1.db',
                                  headerActionsHtml,
                                  'settings'
                                )}
                                ${metricCardsHtml}
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: var(--space-md); align-items: start;">
                                  ${provisionCardHtml}
                                  ${profileEditCardHtml}
                                </div>
                                ${dangerZoneCardHtml}
                              </div>
                              `;
  }

                              // --- Handlers ---

                              window.submitCreateAccount = async function () {
    const nick = (document.getElementById('new-account-nick').value || '').trim();
                              if (!nick) {
                                window.UI.Toast('Nickname is required', 'warning');
                              return;
    }

                              const initialGold = parseInt(document.getElementById('new-account-gold').value, 10) || 10000;
                              const initialDiamonds = parseInt(document.getElementById('new-account-dia').value, 10) || 500;
                              const initialLevel = parseInt(document.getElementById('new-account-level').value, 10) || 60;
                              const isBanned = document.getElementById('new-account-status').value === 'banned';
                              const region = document.getElementById('new-account-region').value || 'IND';
                              const signature = (document.getElementById('new-account-sig').value || '').trim();

                              const payload = {
                                nickname: nick,
                              coins: initialGold,
                              gold: initialGold,
                              gems: initialDiamonds,
                              diamonds: initialDiamonds,
                              level: initialLevel,
                              exp: 100000,
                              region: region,
                              signature: signature,
                              is_banned: isBanned
    };

                              const targetAid = parseInt(document.getElementById('new-account-aid').value, 10);
                              if (targetAid && !isNaN(targetAid)) {
                                payload.account_id = targetAid;
    }

                              const submitBtn = document.getElementById('btn-submit-create-account');
                              if (submitBtn) {
                                submitBtn.disabled = true;
                              submitBtn.textContent = 'Provisioning...';
    }

                              try {
      const res = await window.apiClient.post('/api/admin/players/create', payload);
                              if (res.ok) {
                              window.UI.Toast(`Account "${nick}" provisioned successfully!`, 'success');
                              if (res.data && res.data.account_id) {
                                await window.playerContext.setAccountId(res.data.account_id);
                              window.location.hash = '#/players/inspector';
        } else {
                                window.location.hash = '#/players/directory';
        }
      } else {
                              window.UI.Toast(res.error || 'Failed to create account', 'error');
      }
    } catch (e) {
                              window.UI.Toast(`Creation error: ${e.message}`, 'error');
    } finally {
      if (submitBtn) {
                                submitBtn.disabled = false;
                              submitBtn.innerHTML = `${window.UI.Icon('plus', 14)} Provision & Initialize Account`;
      }
    }
  };

                              window.submitUpdateProfile = async function (accountId) {
    const payload = {
                                account_id: accountId,
                              nickname: (document.getElementById('edit-prof-nick').value || '').trim(),
                              region: document.getElementById('edit-prof-region').value || 'IND',
                              signature: (document.getElementById('edit-prof-sig').value || '').trim(),
                              level: parseInt(document.getElementById('edit-prof-level').value, 10) || 1,
                              exp: parseInt(document.getElementById('edit-prof-exp').value, 10) || 0,
                              rank: parseInt(document.getElementById('edit-prof-rank').value, 10) || 0,
                              ranking_points: parseInt(document.getElementById('edit-prof-rp').value, 10) || 0
    };

                              const submitBtn = document.getElementById('btn-submit-edit-profile');
                              if (submitBtn) {
                                submitBtn.disabled = true;
                              submitBtn.textContent = 'Saving...';
    }

                              try {
      const res = await window.apiClient.post('/api/dashboard/profile/update', payload);
                              if (res.ok) {
                                window.UI.Toast('Profile attributes updated successfully', 'success');
                              await window.playerContext.refresh();
                              const canvas = document.getElementById('workspace-canvas');
                              if (canvas) window.Modules.PlayersAccount(canvas);
      } else {
                                window.UI.Toast(res.error || 'Failed to update profile', 'error');
      }
    } catch (e) {
                                window.UI.Toast(`Update error: ${e.message}`, 'error');
    } finally {
      if (submitBtn) {
                                submitBtn.disabled = false;
                              submitBtn.innerHTML = `${window.UI.Icon('checkCircle', 14, '', 'var(--accent-emerald)')} Save Profile Changes`;
      }
    }
  };

                              window.confirmDeleteAccount = function (accountId) {
                                window.UI.Confirm(
                                  `Delete Account ${accountId}?`,
                                  `Are you sure you want to permanently delete Account ${accountId} from india_v1.db? This operation will remove all associated inventory, currencies, and progression.`,
                                  async () => {
                                      try {
                                        const res = await window.apiClient.delete(`/api/admin/players/${accountId}`);
                                        if (res.ok) {
                                          window.UI.Toast(`Account ${accountId} deleted`, 'success');
                                          window.location.hash = '#/players/directory';
                                        } else {
                                          window.UI.Toast(res.error || 'Account deletion restricted', 'warning');
                                        }
                                      } catch (e) {
                                        window.UI.Toast(`Deletion error: ${e.message}`, 'error');
                                      }
                                    },
                                  true
                                );
  };

                              window.confirmResetAccountData = function (accountId) {
                                window.UI.Confirm(
                                  `Reset Data for Account ${accountId}?`,
                                  `Reset level, rank, EXP, and progression data for Account ${accountId} back to factory defaults?`,
                                  async () => {
                                    try {
                                      const res = await window.apiClient.post('/api/dashboard/profile/update', {
                                        account_id: accountId,
                                        level: 1,
                                        exp: 0,
                                        rank: 0,
                                        ranking_points: 0
                                      });
                                      if (res.ok) {
                                        window.UI.Toast(`Account ${accountId} progression reset`, 'info');
                                        await window.playerContext.refresh();
                                        const canvas = document.getElementById('workspace-canvas');
                                        if (canvas) window.Modules.PlayersAccount(canvas);
                                      } else {
                                        window.UI.Toast(res.error || 'Reset failed', 'error');
                                      }
                                    } catch (e) {
                                      window.UI.Toast(`Reset error: ${e.message}`, 'error');
                                    }
                                  },
                                  true
                                );
  };

                              // Self-register with AppRouter if initialized
                              if (window.appRouter) {
                                window.appRouter.register('#/players/account', window.Modules.PlayersAccount);
  }
})();
