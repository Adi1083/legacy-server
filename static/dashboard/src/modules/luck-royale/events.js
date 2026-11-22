/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Luck Royale Studio — Workspace 05.7: Event Rewards & Schedules (events.js)
 * Clean macOS dark glass design system, zero emojis, strict machine isolation.
 */

window.LuckRoyale = window.LuckRoyale || {};

window.LuckRoyale.Events = async function (canvas) {
  'use strict';
  const C = window.LuckRoyale.Common;
  canvas.innerHTML = window.UI.Loading('Loading Event Rewards & Schedules...');

  // Fetch events and machines
  const [eventsRes, machRes] = await Promise.all([
    window.apiClient.get('/api/admin/luck-royale/events-banners'),
    window.apiClient.get('/api/admin/luck-royale/machines', { include_disabled: 1 })
  ]);

  const assignments = (eventsRes.ok && eventsRes.data && eventsRes.data.assignments) ? eventsRes.data.assignments : [];
  const machines = (machRes.ok && machRes.data && machRes.data.machines) ? machRes.data.machines : [];

  let activeCid = window.LuckRoyale._selectedEventCid || 'all';

  // Machine Switcher Pills
  const machinePills = [
    { id: 'all', label: 'All Machines (Grouped)' },
    ...machines.map(m => ({ id: String(m.chest_id), label: `${m.display_name || m.chest_name} (#${m.chest_id})` }))
  ].map(p => {
    const isCur = String(p.id) === String(activeCid);
    return `
      <button class="btn ${isCur ? 'btn-primary' : 'btn-secondary'}" style="padding: 6px 14px; font-size: 12px; border-radius: var(--radius-full);" onclick="window.LuckRoyale._selectedEventCid='${p.id}'; window.appRouter.handleRoute();">
        ${C.escapeHtml(p.label)}
      </button>
    `;
  }).join('');

  // Filter assignments
  let displayedAssignments = assignments;
  if (activeCid !== 'all') {
    displayedAssignments = assignments.filter(a => String(a.chest_id) === String(activeCid));
  }

  const eventCards = displayedAssignments.map(a => {
    const ev = a.event || {};
    const hasEvent = Boolean(ev.event_id || ev.title);
    const isAct = Boolean(ev.active);
    const bannerUrl = (a.artwork && a.artwork.banner_url) || a.banner_url || '/banners/' + (a.banner_file || 'luck_royale_banner.png');

    return `
      <div class="glass-card" style="padding: 0; overflow: hidden; margin-bottom: 20px; border-color: ${isAct ? 'rgba(56, 189, 248, 0.3)' : 'var(--border-default)'};">
        <div style="display: grid; grid-template-columns: 280px 1fr; background: rgba(0,0,0,0.3);">
          <!-- Machine Poster & Info -->
          <div style="position: relative; height: 200px; background: #000; overflow: hidden; border-right: 1px solid var(--border-subtle);">
            <img src="${bannerUrl}" alt="${C.escapeHtml(a.display_name)}" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.9;">
            <div style="position: absolute; top: 10px; left: 10px;">
              ${window.UI.Badge('ID: ' + a.chest_id, 'neutral')}
            </div>
            <div style="position: absolute; bottom: 10px; left: 10px; right: 10px; background: rgba(0,0,0,0.7); padding: 8px 10px; border-radius: 4px; backdrop-filter: blur(4px);">
              <div style="font-weight: 600; color: #fff; font-size: 13px;">${C.escapeHtml(a.display_name || a.chest_name)}</div>
            </div>
          </div>

          <!-- Event Parameters & Rewards -->
          <div style="padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <div>
                  <div style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 2px;">
                    ${C.escapeHtml(ev.title || 'No Scheduled Campaign')}
                  </div>
                  <div style="font-size: 11.5px; color: var(--text-tertiary); font-family: var(--font-mono);">
                    ${hasEvent ? `Event ID: ${ev.event_id} • Target Royale: #${a.chest_id}` : 'Standard draw rates in effect'}
                  </div>
                </div>
                <div>
                  ${hasEvent && isAct ? window.UI.Badge('CAMPAIGN ACTIVE', 'emerald') : (hasEvent ? window.UI.Badge('PAUSED', 'neutral') : window.UI.Badge('NO EVENT', 'neutral'))}
                </div>
              </div>

              <!-- Metrics -->
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 16px;">
                <div style="background: rgba(255,255,255,0.02); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                  <div style="font-size: 10.5px; color: var(--text-tertiary);">Spin Discount</div>
                  <div style="font-size: 16px; font-weight: 700; color: var(--accent-amber); font-family: var(--font-mono);">
                    ${ev.discount_percent ? '-' + ev.discount_percent + '%' : '0%'}
                  </div>
                </div>
                <div style="background: rgba(255,255,255,0.02); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                  <div style="font-size: 10.5px; color: var(--text-tertiary);">Jackpot Multiplier</div>
                  <div style="font-size: 16px; font-weight: 700; color: var(--accent-cyan); font-family: var(--font-mono);">
                    ${ev.rate_up_multiplier ? ev.rate_up_multiplier + 'x Rate' : '1.0x (Standard)'}
                  </div>
                </div>
                <div style="background: rgba(255,255,255,0.02); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                  <div style="font-size: 10.5px; color: var(--text-tertiary);">Start Window</div>
                  <div style="font-size: 11.5px; color: #fff; font-family: var(--font-mono); margin-top: 2px;">
                    ${ev.start_time ? C.formatTimestamp(ev.start_time) : 'Immediate'}
                  </div>
                </div>
                <div style="background: rgba(255,255,255,0.02); padding: 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                  <div style="font-size: 10.5px; color: var(--text-tertiary);">End Window</div>
                  <div style="font-size: 11.5px; color: #fff; font-family: var(--font-mono); margin-top: 2px;">
                    ${ev.end_time ? C.formatTimestamp(ev.end_time) : 'Permanent'}
                  </div>
                </div>
              </div>
            </div>

            <!-- Actions Bar -->
            <div style="display: flex; justify-content: flex-end; gap: 8px;">
              <button class="btn btn-secondary" onclick="window.LuckRoyale.OpenScheduleEventModal(${a.chest_id})">
                <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('edit', 11)} Configure Campaign</span>
              </button>
              ${hasEvent ? `
                <button class="btn btn-secondary" onclick="window.LuckRoyale.ToggleEventActive(${a.chest_id}, ${!isAct})">
                  ${isAct ? 'Pause Campaign' : 'Activate Campaign'}
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');

  canvas.innerHTML = `
    <div class="page-container">
      ${window.UI.PageHeader(
        'Event Rewards & Schedules',
        'Configure limited-time rate-up campaigns, spin discounts, and machine promotional events',
        `
          <button class="btn btn-primary" onclick="window.LuckRoyale.OpenScheduleEventModal()">
            <span style="display: inline-flex; align-items: center; gap: 4px;">${window.UI.Icon('plus', 12)} Schedule Campaign</span>
          </button>
        `,
        'calendar'
      )}

      ${C.renderSubNav('events')}

      <!-- Machine Selector Bar -->
      <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 20px; scrollbar-width: none;">
        ${machinePills}
      </div>

      <!-- Event Cards -->
      ${displayedAssignments.length > 0 ? eventCards : '<div class="glass-card" style="text-align: center; color: var(--text-tertiary);">No machine campaigns found.</div>'}
    </div>
  `;
};

window.LuckRoyale.OpenScheduleEventModal = function (defaultCid) {
  defaultCid = defaultCid || 3;
  const modalHtml = `
    <div id="schedule-event-modal" class="modal-backdrop active" style="z-index: 9999;">
      <div class="modal-content" style="max-width: 480px;">
        <div class="modal-header">
          <div class="modal-title">Schedule Royale Campaign</div>
          <button class="modal-close" onclick="document.getElementById('schedule-event-modal').remove()">&times;</button>
        </div>
        <form id="schedule-event-form" onsubmit="window.LuckRoyale.SubmitScheduleEvent(event); return false;" style="padding: 16px;">
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Target Machine</label>
            <select name="chest_id" class="form-select">
              <option value="3" ${defaultCid === 3 ? 'selected' : ''}>Diamond Royale (#3)</option>
              <option value="4" ${defaultCid === 4 ? 'selected' : ''}>Weapon Royale (#4)</option>
              <option value="5" ${defaultCid === 5 ? 'selected' : ''}>Gold Royale (#5)</option>
              <option value="6" ${defaultCid === 6 ? 'selected' : ''}>Incubator (#6)</option>
            </select>
          </div>
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Campaign Title</label>
            <input type="text" name="title" class="form-input" placeholder="e.g. 2x Magic Cube Weekend" required>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Discount %</label>
              <input type="number" name="discount_percent" class="form-input" value="30" min="0" max="90">
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Rate-Up Multiplier</label>
              <input type="number" step="0.5" name="rate_up_multiplier" class="form-input" value="2.0" min="1.0" max="10.0">
            </div>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('schedule-event-modal').remove()">Cancel</button>
            <button type="submit" class="btn btn-primary">Schedule Campaign</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
};

window.LuckRoyale.SubmitScheduleEvent = async function (e) {
  const form = e.target;
  const chestId = parseInt(form.chest_id.value, 10);
  const payload = {
    chest_id: chestId,
    title: form.title.value.trim(),
    discount_percent: parseInt(form.discount_percent.value, 10) || 0,
    rate_up_multiplier: parseFloat(form.rate_up_multiplier.value) || 1.0,
    active: true,
  };

  const res = await window.apiClient.post(`/api/admin/luck-royale/machines/${chestId}/events`, payload);
  if (res.ok) {
    window.UI.Toast('Campaign scheduled successfully.', 'success');
    const modal = document.getElementById('schedule-event-modal');
    if (modal) modal.remove();
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to schedule campaign.', 'danger');
  }
};

window.LuckRoyale.ToggleEventActive = async function (chestId, newState) {
  const res = await window.apiClient.post(`/api/admin/luck-royale/machines/${chestId}/events`, {
    chest_id: chestId,
    active: newState
  });
  if (res.ok) {
    window.UI.Toast(`Campaign state updated.`, 'success');
    window.appRouter.handleRoute();
  } else {
    window.UI.Toast(res.error || 'Failed to toggle campaign.', 'danger');
  }
};
