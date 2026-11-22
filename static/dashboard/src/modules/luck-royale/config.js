/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.12: Configuration Backup & JSON State (config.js)
 * Clean macOS dark glass design system, zero emojis, JSON inspection.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Config = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Fetching raw machine configurations...');

  const [machRes, overviewRes] = await Promise.all([
    window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 }),
    window.apiClient.get('/api/admin/luck-royale/overview')
  ]);

  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];
  const overview = (overviewRes.ok && overviewRes.data) ? overviewRes.data : {};

  const dumpObj = {
    export_timestamp: Date.now(),
    overview: overview,
    machines: machines,
  };
  const jsonStr = JSON.stringify(dumpObj, null, 2);

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Configuration Backup & Raw State',
        'Inspect live backend JSON serialized structures and export machine state backups',
        `
          <button class="btn btn-primary" onclick="window.LuckRoyale.DownloadConfigBackup()">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('download', 12)} Download State JSON</span>
          </button>
        `,
        'fileText'
      )}

      ${C.renderSubNav('config')}

      <div class="glass-card" style="padding: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div style="font-size: 13px; font-weight: 600; color: #fff;">
            Live Serialized State Dump (${machines.length} Machines Registered)
          </div>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="navigator.clipboard.writeText(document.getElementById('raw-json-pre').innerText); window.UI.Toast('Copied JSON to clipboard', 'info');">
            ${window.UI.Icon('copy', 11)} Copy
          </button>
        </div>
        <pre id="raw-json-pre" style="background: rgba(0,0,0,0.6); padding: 16px; border-radius: 6px; border: 1px solid var(--border-default); font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); max-height: 520px; overflow-y: auto; white-space: pre-wrap; line-height: 1.5;">${C.escapeHtml(jsonStr)}</pre>
      </div>
    </div>
  `;
};

window.LuckRoyale.DownloadConfigBackup = function () {
  const pre = document.getElementById('raw-json-pre');
  if (!pre) return;
  const blob = new Blob([pre.innerText], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `luck_royale_backup_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  window.UI.Toast('Backup file downloaded.', 'success');
};
