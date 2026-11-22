/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Server Settings & System Configuration
 * Route: #/system/settings
 */

(function () {
  'use strict';

  let currentBranding = {};

  /**
   * Main render function for #/system/settings
   */
  async function renderSystemSettings(canvas) {
    canvas.innerHTML = window.UI.Loading('Loading server settings and brand configurations...');

    try {
      const res = await window.apiClient.get('/api/dashboard/branding');
      if (res.ok && res.data) {
        currentBranding = res.data.slots || {};
      }
    } catch (e) {
      console.warn('Failed to load branding:', e);
    }

    canvas.innerHTML = `
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 4px;">Server Settings & Architecture</h2>
          <p style="color: var(--text-secondary); font-size: 12px;">Global IND PROJECT runtime parameters, client branding slots, gateway ports & operational switches</p>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <button class="btn btn-secondary" onclick="window.SystemSettingsModule.refresh()">
            🔄 Refresh Settings
          </button>
          <button class="btn btn-danger" onclick="window.SystemSettingsModule.resetBrandingDefaults()">
            ⚠️ Reset Defaults
          </button>
        </div>
      </div>

      <!-- Network Architecture & Gateway Status -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 24px;">
        <div class="stat-card">
          <div class="stat-label">
            <span>REST API & UI Gateway</span>
            <span class="badge badge-emerald">ACTIVE</span>
          </div>
          <div class="stat-value" style="font-size: 18px; color: var(--accent-emerald);">PORT 8080</div>
          <div class="stat-subtext">HTTP/1.1 IND PROJECT Server Host</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">
            <span>TCP Lobby Sync</span>
            <span class="badge badge-cyan">LISTENING</span>
          </div>
          <div class="stat-value" style="font-size: 18px; color: var(--accent-cyan);">PORT 8081</div>
          <div class="stat-subtext">Protobuf Framed Wire Stream</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">
            <span>UDP Dedicated Combat</span>
            <span class="badge badge-emerald">STANDBY</span>
          </div>
          <div class="stat-value" style="font-size: 18px; color: var(--accent-indigo);">PORT 39800</div>
          <div class="stat-subtext">Low-latency Match Host</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">
            <span>Client Target Protocol</span>
            <span class="badge badge-amber">OB17 LOCKED</span>
          </div>
          <div class="stat-value" style="font-size: 18px; color: var(--accent-amber);">v1.39.4</div>
          <div class="stat-subtext">Free Fire Summer 2019 Classic</div>
        </div>
      </div>

      <!-- Main Settings Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px;">
        <!-- Left: Brand Identity & Client MOTD -->
        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Server Brand & Client MOTD</div>
              <div class="glass-card-subtitle">Values served via /api/dashboard/branding to mobile clients & web portals</div>
            </div>
            <div class="glass-card-actions">
              <button class="btn btn-primary" onclick="window.SystemSettingsModule.saveBranding()">Save Brand Slots</button>
            </div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 14px;">
            <div>
              <label style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; display: block; margin-bottom: 4px;">Brand Name (Server Title)</label>
              <input type="text" id="setting-brand-name" class="form-input" value="${currentBranding.brand_name || 'India V1'}">
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; display: block; margin-bottom: 4px;">Server Subtitle / Restoration Tag</label>
              <input type="text" id="setting-brand-sub" class="form-input" value="${currentBranding.brand_subtitle || 'FF 2019 Restoration'}">
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; display: block; margin-bottom: 4px;">Message of the Day (MOTD)</label>
              <textarea id="setting-brand-motd" class="form-input" style="height: 60px; resize: vertical;">${currentBranding.motd || 'Welcome to IND PROJECT FF 2019 Classic Server! Enjoy OB17 Luck Royale & Bermuda battles.'}</textarea>
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; display: block; margin-bottom: 4px;">In-Lobby Marquee Announcement</label>
              <input type="text" id="setting-brand-announcement" class="form-input" value="${currentBranding.welcome_announcement || 'IND PROJECT IND PROJECT Server Online — All Modes & Vouchers Enabled!'}">
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div>
                <label style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; display: block; margin-bottom: 4px;">Region Tag</label>
                <input type="text" id="setting-brand-region" class="form-input" value="${currentBranding.region_tag || 'IND'}">
              </div>
              <div>
                <label style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; display: block; margin-bottom: 4px;">Community Link</label>
                <input type="text" id="setting-brand-discord" class="form-input" value="${currentBranding.discord_url || 'https://discord.gg/ff2019'}">
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Client Preview & Runtime Parameters -->
        <div style="display: flex; flex-direction: column; gap: 20px;">
          <!-- Live Client Preview Card -->
          <div class="glass-card">
            <div class="glass-card-header">
              <div class="glass-card-title">Live Client Presentation Preview</div>
              <div class="glass-card-subtitle">Real-time simulation of client banner banner presentation</div>
            </div>
            <div style="background: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.15) 0%, rgba(10, 16, 28, 0.7) 100%); border: 1px solid var(--border-default); border-radius: 8px; padding: 18px; text-align: center;">
              <div class="badge badge-cyan" style="margin-bottom: 8px;" id="prev-region-badge">${currentBranding.region_tag || 'IND'} • REGION</div>
              <h3 style="font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 4px;" id="prev-brand-name">${currentBranding.brand_name || 'India V1'}</h3>
              <div style="font-size: 12px; color: var(--accent-cyan); margin-bottom: 12px;" id="prev-brand-sub">${currentBranding.brand_subtitle || 'FF 2019 Restoration'}</div>
              <div style="background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px; font-size: 11.5px; color: var(--text-secondary); text-align: left; margin-bottom: 8px;">
                <div style="font-size: 10px; color: var(--text-tertiary); text-transform: uppercase; font-weight: 600; margin-bottom: 2px;">Lobby MOTD Broadcast:</div>
                <div id="prev-motd">${currentBranding.motd || 'Welcome to IND PROJECT FF 2019 Classic Server! Enjoy OB17 Luck Royale & Bermuda battles.'}</div>
              </div>
              <div style="font-size: 11px; color: var(--text-tertiary);">
                Protocol: <span style="color: var(--accent-emerald);">OB17 v1.39</span> • Handshake: <span style="color: var(--accent-cyan);">TLS/XOR</span>
              </div>
            </div>
          </div>

          <!-- Quick System Administration Actions -->
          <div class="glass-card">
            <div class="glass-card-header">
              <div class="glass-card-title">Operational Utilities</div>
              <div class="glass-card-subtitle">Maintenance, cache purges & state reset tools</div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(0,0,0,0.25); border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div>
                  <div style="font-weight: 600; color: #fff; font-size: 12px;">Flush Telemetry Request Buffer</div>
                  <div style="font-size: 11px; color: var(--text-tertiary);">Empties the in-memory 1,000-request ring buffer</div>
                </div>
                <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/requests/clear').then(() => window.UI.Toast('Telemetry buffer cleared', 'success'))">Clear Buffer</button>
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(0,0,0,0.25); border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div>
                  <div style="font-weight: 600; color: #fff; font-size: 12px;">Reset Game Modes Registry</div>
                  <div style="font-size: 11px; color: var(--text-tertiary);">Reloads game_modes.json default configuration</div>
                </div>
                <button class="btn btn-secondary" onclick="window.apiClient.post('/api/dashboard/modes/reset').then(() => window.UI.Toast('Game modes reset to default', 'success'))">Reset Modes</button>
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(0,0,0,0.25); border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div>
                  <div style="font-weight: 600; color: #fff; font-size: 12px;">Unlock All Game Modes</div>
                  <div style="font-size: 11px; color: var(--text-tertiary);">Forces all battle royale & clash squad modes active</div>
                </div>
                <button class="btn btn-primary" onclick="window.apiClient.post('/api/dashboard/modes/unlock_all').then(() => window.UI.Toast('All game modes unlocked', 'success'))">Unlock All</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Wire live input preview updates
    const bName = document.getElementById('setting-brand-name');
    const bSub = document.getElementById('setting-brand-sub');
    const bMotd = document.getElementById('setting-brand-motd');
    const bReg = document.getElementById('setting-brand-region');

    if (bName) bName.oninput = () => { document.getElementById('prev-brand-name').textContent = bName.value; };
    if (bSub) bSub.oninput = () => { document.getElementById('prev-brand-sub').textContent = bSub.value; };
    if (bMotd) bMotd.oninput = () => { document.getElementById('prev-motd').textContent = bMotd.value; };
    if (bReg) bReg.oninput = () => { document.getElementById('prev-region-badge').textContent = `${bReg.value} • REGION`; };
  }

  // --- Exposed Global Handlers ---
  window.SystemSettingsModule = {
    render: renderSystemSettings,

    async refresh() {
      const canvas = document.getElementById('workspace-canvas');
      if (canvas) await renderSystemSettings(canvas);
      window.UI.Toast('Settings refreshed', 'success');
    },

    async saveBranding() {
      const brandName = document.getElementById('setting-brand-name').value.trim();
      const brandSub = document.getElementById('setting-brand-sub').value.trim();
      const motd = document.getElementById('setting-brand-motd').value.trim();
      const announcement = document.getElementById('setting-brand-announcement').value.trim();
      const region = document.getElementById('setting-brand-region').value.trim();
      const discord = document.getElementById('setting-brand-discord').value.trim();

      const updates = [
        { key: 'brand_name', value: brandName },
        { key: 'brand_subtitle', value: brandSub },
        { key: 'motd', value: motd },
        { key: 'welcome_announcement', value: announcement },
        { key: 'region_tag', value: region },
        { key: 'discord_url', value: discord }
      ];

      try {
        for (const item of updates) {
          await window.apiClient.post('/api/dashboard/branding/update', item);
        }
        currentBranding = {
          brand_name: brandName,
          brand_subtitle: brandSub,
          motd,
          welcome_announcement: announcement,
          region_tag: region,
          discord_url: discord
        };
        window.UI.Toast('All server brand settings updated & saved successfully', 'success');
      } catch (err) {
        window.UI.Toast(`Error saving settings: ${err.message}`, 'error');
      }
    },

    resetBrandingDefaults() {
      window.UI.Confirm(
        'Reset Server Brand Settings',
        'Are you sure you want to revert server branding, subtitle, and MOTD back to factory IND PROJECT 2019 defaults?',
        async () => {
          const defaults = [
            { key: 'brand_name', value: 'India V1' },
            { key: 'brand_subtitle', value: 'FF 2019 Restoration' },
            { key: 'motd', value: 'Welcome to IND PROJECT FF 2019 Classic Server! Enjoy OB17 Luck Royale & Bermuda battles.' },
            { key: 'welcome_announcement', value: 'IND PROJECT IND PROJECT Server Online — All Modes & Vouchers Enabled!' },
            { key: 'region_tag', value: 'IND' },
            { key: 'discord_url', value: 'https://discord.gg/ff2019' }
          ];

          for (const item of defaults) {
            await window.apiClient.post('/api/dashboard/branding/update', item);
          }

          const canvas = document.getElementById('workspace-canvas');
          if (canvas) await renderSystemSettings(canvas);
          window.UI.Toast('Branding reset to IND PROJECT defaults', 'success');
        },
        true
      );
    }
  };

  // Register on window.Modules
  window.Modules = window.Modules || {};
  window.Modules.SystemSettings = renderSystemSettings;

  // Register in Router with resilient hook
  function hookRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/system/settings', renderSystemSettings);
    }
  }
  hookRoute();
  document.addEventListener('DOMContentLoaded', () => { setTimeout(hookRoute, 0); });
  window.addEventListener('load', hookRoute);
})();
