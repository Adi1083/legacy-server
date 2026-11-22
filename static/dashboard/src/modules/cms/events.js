/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: 08.4 Events & Quests Studio (#/cms/events)
 * 
 * Features:
 * - Live Event & Quest Manager for IND PROJECT FF 1.39 Core
 * - Activity CRUD (activity_id, act_title, act_text, award_context, awards)
 * - Priority Reordering & In-Game Tagging
 * - Active Status Toggling via /api/dashboard/cms/toggle
 * - Responsive .glass-table-container Horizontal Containment
 * - Apple macOS/iPadOS Dark Glassmorphism Design
 */

(function () {
  'use strict';

  const state = {
    events: [],
    isLoading: false
  };

  function escapeHtml(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async function loadData() {
    state.isLoading = true;
    try {
      const res = await window.apiClient.get('/api/dashboard/cms', { category: 'events' });
      if (res.ok && res.data) {
        state.events = res.data.items || (res.data.cms && res.data.cms.events) || [];
      }
    } catch (e) {
      console.error('Error loading events data', e);
    } finally {
      state.isLoading = false;
    }
  }

  async function toggleEvent(id, currentStatus) {
    const res = await window.apiClient.post('/api/dashboard/cms/toggle', {
      category: 'events',
      id: id,
      enabled: !currentStatus
    });
    if (res.ok) {
      window.UI.Toast(`Event #${id} status updated`, 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    }
  }

  async function deleteEvent(id) {
    window.UI.Confirm(
      'Delete Event / Quest',
      `Delete event activity #${id}? Players will no longer be able to claim rewards from this event.`,
      async () => {
        const res = await window.apiClient.post('/api/dashboard/cms/delete', {
          category: 'events',
          id: id
        });
        if (res.ok) {
          window.UI.Toast(`Deleted event #${id}`, 'success');
          await loadData();
          render(document.getElementById('workspace-canvas'));
        }
      },
      true
    );
  }

  async function moveEvent(index, direction) {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= state.events.length) return;

    const list = [...state.events];
    const item = list.splice(index, 1)[0];
    list.splice(targetIdx, 0, item);

    const orderedIds = list.map(e => e.activity_id || e.id);
    const res = await window.apiClient.post('/api/dashboard/cms/reorder', {
      category: 'events',
      ordered_ids: orderedIds
    });

    if (res.ok) {
      window.UI.Toast('Event display priority updated', 'success');
      await loadData();
      render(document.getElementById('workspace-canvas'));
    }
  }

  function openEventModal(event = null) {
    const isEdit = !!event;
    const title = isEdit ? `Edit Event #${event.activity_id || event.id}` : 'Create New Event Campaign';
    const curTitle = event ? (event.act_title || '') : '';
    const curText = event ? (event.act_text || '') : '';
    const curAward = event ? (event.award_context || 'Special Reward') : 'Special Reward';
    const curImg = event ? (event.image_url || '/banners/activity_banner.png') : '/banners/activity_banner.png';
    const curEnabled = event ? (event.enabled !== false) : true;

    const bodyHtml = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Event Title (act_title)</label>
          <input type="text" id="modal-ev-title" class="form-input" placeholder="e.g. Bermuda 2019 Revival Festival" value="${escapeHtml(curTitle)}">
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Description / Mission Rules (act_text)</label>
          <textarea id="modal-ev-text" class="form-input" style="height: 80px;" placeholder="Complete 3 matches to claim event rewards...">${escapeHtml(curText)}</textarea>
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Award Label / Context (award_context)</label>
          <input type="text" id="modal-ev-award" class="form-input" placeholder="e.g. Diamond Royale Voucher x5" value="${escapeHtml(curAward)}">
        </div>

        <div>
          <label style="display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px;">Banner Graphic Path (image_url)</label>
          <input type="text" id="modal-ev-img" class="form-input" placeholder="/banners/activity_banner.png" value="${escapeHtml(curImg)}">
        </div>

        <div style="display: flex; align-items: center; gap: 8px;">
          <input type="checkbox" id="modal-ev-enabled" style="accent-color: var(--accent-cyan); width: 16px; height: 16px;" ${curEnabled ? 'checked' : ''}>
          <label for="modal-ev-enabled" style="font-size: 12.5px; color: var(--text-primary); cursor: pointer;">Enable event immediately in Events & Quests tab</label>
        </div>
      </div>
    `;

    const footerButtonsHtml = `
      <button class="btn btn-primary" id="modal-ev-save-btn">Save Event</button>
      <button class="btn btn-secondary" onclick="document.getElementById('global-modal-overlay').remove()">Cancel</button>
    `;

    window.UI.Modal(title, bodyHtml, footerButtonsHtml);

    document.getElementById('modal-ev-save-btn').onclick = async () => {
      const actTitle = document.getElementById('modal-ev-title').value.trim() || 'Untitled Event';
      const actText = document.getElementById('modal-ev-text').value.trim();
      const awardCtx = document.getElementById('modal-ev-award').value.trim() || 'Event Reward';
      const imgUrl = document.getElementById('modal-ev-img').value.trim() || '/banners/activity_banner.png';
      const enabled = document.getElementById('modal-ev-enabled').checked;

      const payload = {
        category: 'events',
        item: {
          ...(event || {}),
          act_title: actTitle,
          act_text: actText,
          award_context: awardCtx,
          image_url: imgUrl,
          image_url_for_lobby: imgUrl,
          enabled: enabled
        }
      };

      const res = await window.apiClient.post('/api/dashboard/cms/upsert', payload);
      if (res.ok) {
        window.UI.Toast('Event saved successfully', 'success');
        document.getElementById('global-modal-overlay').remove();
        await loadData();
        render(document.getElementById('workspace-canvas'));
      } else {
        window.UI.Toast('Error saving event: ' + (res.error || 'Server error'), 'error');
      }
    };
  }

  async function render(canvas) {
    if (!canvas) return;

    const totalEvents = state.events.length;
    const activeEvents = state.events.filter(e => e.enabled !== false).length;

    const rows = state.events.map((e, idx) => {
      const isEnabled = e.enabled !== false;
      const statusBadge = isEnabled ? window.UI.Badge('ACTIVE', 'emerald') : window.UI.Badge('DISABLED', 'neutral');
      const eid = e.activity_id || e.id;

      return `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary); width: 40px; text-align: center;">
            #${eid}
          </td>
          <td style="width: 70px;">
            <div style="width: 60px; height: 34px; border-radius: 4px; overflow: hidden; background: #000; border: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: center;">
              <img src="${escapeHtml(e.image_url)}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/banners/activity_banner.png'">
            </div>
          </td>
          <td>
            <div style="font-weight: 600; color: #fff; font-size: 13px;">${escapeHtml(e.act_title)}</div>
            <div style="font-size: 11px; color: var(--text-tertiary);">${escapeHtml(e.award_context || 'Reward')}</div>
          </td>
          <td>${statusBadge}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Up" ${idx === 0 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSEvents.moveEvent(${idx}, -1)">▲</button>
              <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 11px;" title="Move Down" ${idx === state.events.length - 1 ? 'disabled style="opacity:0.3;"' : ''} onclick="window.CMSEvents.moveEvent(${idx}, 1)">▼</button>
            </div>
          </td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSEvents.toggleEvent(${eid}, ${isEnabled})">
                ${isEnabled ? 'Deactivate' : 'Activate'}
              </button>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSEvents.openEditEvent(${eid})">
                Edit
              </button>
              <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="window.CMSEvents.deleteEvent(${eid})">
                Delete
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    canvas.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default);">
            <div style="color: var(--text-tertiary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">Active Quests</div>
            <div style="font-size: 22px; font-weight: 700; color: var(--accent-emerald); margin: 3px 0;">
              ${activeEvents} <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ ${totalEvents} total</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary);">Claimable in client Events hub</div>
          </div>
          <div style="background: rgba(10, 16, 28, 0.45); padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border-default); display: flex; flex-direction: column; justify-content: center; gap: 8px;">
            <button class="btn btn-primary" onclick="window.CMSEvents.openCreateModal()" style="width: 100%;">+ Add Event Campaign</button>
            <button class="btn btn-secondary" onclick="window.CMSEvents.reload()" style="width: 100%;">🔄 Refresh Events</button>
          </div>
        </div>

        <div class="glass-card">
          <div class="glass-card-header">
            <div>
              <div class="glass-card-title">Events & Quests Studio</div>
              <div class="glass-card-subtitle">Server-driven activities served to client <code>/GetActivityList</code></div>
            </div>
            <button class="btn btn-primary" onclick="window.CMSEvents.openCreateModal()">+ Add Event</button>
          </div>
          <div class="glass-card-body">
            <div class="glass-table-container">
              ${window.UI.Table(['ID', 'Art', 'Campaign & Reward', 'Status', 'Order', 'Actions'], rows, 'No event campaigns configured.')}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  window.CMSEvents = {
    async init(canvas) {
      await loadData();
      await render(canvas);
    },
    async reload() {
      await loadData();
      render(document.getElementById('workspace-canvas'));
      window.UI.Toast('Events refreshed', 'info');
    },
    toggleEvent,
    deleteEvent,
    moveEvent,
    openCreateModal() {
      openEventModal(null);
    },
    openEditEvent(id) {
      const e = state.events.find(x => (x.activity_id || x.id) === id);
      if (e) openEventModal(e);
    }
  };

  if (window.appRouter) {
    window.appRouter.register('#/cms/events', async (canvas) => {
      await window.CMSEvents.init(canvas);
    });
  }

  window.Modules = window.Modules || {};
  window.Modules.CMSEvents = window.CMSEvents.init;

})();
