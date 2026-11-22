/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: Custom Room Server Management (#/game/rooms)
 * Domain: 06 Game Management
 * Phase 2 Refinement: Standardized Dark Glass Surface Tokens & Design System Components
 */

(function () {
  'use strict';

  function renderCustomRooms(canvas) {
    if (!canvas) canvas = document.getElementById('workspace-canvas');
    if (!canvas) return;

    // Standard UnavailableState Requirement with Documented UDP Combat Server Memory Dependency
    const unavailableHtml = window.UI.UnavailableState(
      'Custom Room Server Manager',
      'GET /api/dashboard/rooms & POST /api/dashboard/rooms/allocate',
      'Requires live backend endpoint support. Dedicated custom room server allocation, observer / referee slots, password-protected lobby management, and UDP port 39800 combat instances reside in active server memory (Phase 4).'
    );

    // Custom Room Specifications Card with Standardized Dark Glass Tokens
    const specsHtml = `
      <div class="glass-card" style="margin-top: 24px;">
        <div class="glass-card-header">
          <div>
            <div class="glass-card-title">Custom Room Engine Specification &amp; Modifiers</div>
            <div class="glass-card-subtitle">Authentic Free Fire 1.39 Private Room Feature Matrix</div>
          </div>
          <div>${window.UI.Badge('PHASE 4 SPEC', 'cyan')}</div>
        </div>
        <div class="glass-card-body">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 20px;">
            <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px;">
              <div style="font-size: 11px; text-transform: uppercase; color: var(--accent-cyan); font-weight: 600; margin-bottom: 4px;">Room Access Item</div>
              <div style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">Diamond Room Card</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                Item ID: <code style="color: var(--accent-cyan);">720001</code>. Consumed upon successful room initialization.
              </div>
            </div>

            <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px;">
              <div style="font-size: 11px; text-transform: uppercase; color: var(--accent-emerald); font-weight: 600; margin-bottom: 4px;">Capacity Scale</div>
              <div style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">20 / 30 / 48 / 100 Players</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                Full support for Battle Royale, 4v4 Clash Squad, and 20-player Rush Hour scrimmages.
              </div>
            </div>

            <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px;">
              <div style="font-size: 11px; text-transform: uppercase; color: var(--accent-amber); font-weight: 600; margin-bottom: 4px;">Referee / Spectator</div>
              <div style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">Up to 10 Spectator Slots</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                Zero-latency referee camera view with full HUD telemetry for competitive esports broadcasts.
              </div>
            </div>

            <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px;">
              <div style="font-size: 11px; text-transform: uppercase; color: var(--accent-rose); font-weight: 600; margin-bottom: 4px;">Security &amp; Passwords</div>
              <div style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">Encrypted Room Access</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                4 to 6 digit numeric passwords preventing public matchmaker intrusion.
              </div>
            </div>
          </div>

          <!-- Modifiers Table -->
          <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px;">
            Match Modifier Configuration Registry
          </div>
          ${window.UI.Table(
            ['Modifier Name', 'Supported Values', 'Authentic Default', 'Description'],
            `
              <tr>
                <td style="font-weight: 600; color: var(--text-primary);">Fall Damage</td>
                <td><code>Enabled / Disabled</code></td>
                <td>${window.UI.Badge('Enabled', 'cyan')}</td>
                <td>Disables kinetic HP loss from high-altitude terrain descents</td>
              </tr>
              <tr>
                <td style="font-weight: 600; color: var(--text-primary);">Limited Ammo</td>
                <td><code>Yes / No (Unlimited)</code></td>
                <td>${window.UI.Badge('Yes', 'cyan')}</td>
                <td>Enables unlimited weapon ammo and grenade capacity when disabled</td>
              </tr>
              <tr>
                <td style="font-weight: 600; color: var(--text-primary);">Movement Speed</td>
                <td><code>100% / 150% / 200%</code></td>
                <td>${window.UI.Badge('100%', 'cyan')}</td>
                <td>Multiplies base avatar sprinting and traversal velocity</td>
              </tr>
              <tr>
                <td style="font-weight: 600; color: var(--text-primary);">Base Health (HP)</td>
                <td><code>100 / 200 / 500</code></td>
                <td>${window.UI.Badge('200', 'cyan')}</td>
                <td>Max avatar hitpoint pool at round inception</td>
              </tr>
              <tr>
                <td style="font-weight: 600; color: var(--text-primary);">Friendly Fire</td>
                <td><code>Yes / No</code></td>
                <td>${window.UI.Badge('No', 'cyan')}</td>
                <td>Allows teammates to damage each other in squad configurations</td>
              </tr>
              <tr>
                <td style="font-weight: 600; color: var(--text-primary);">Airdrop Drops</td>
                <td><code>Yes / No</code></td>
                <td>${window.UI.Badge('Yes', 'cyan')}</td>
                <td>Spawns mid-game military transport airdrops containing Groza / AWM</td>
              </tr>
            `
          )}
        </div>
      </div>
    `;

    canvas.innerHTML = `
      <div style="max-width: 1400px; margin: 0 auto;">
        ${unavailableHtml}
        ${specsHtml}
      </div>
    `;
  }

  const GameRooms = {
    render: renderCustomRooms
  };

  window.GameRooms = GameRooms;

  // Export to window.Modules for coordinator / app.js integration
  window.Modules = window.Modules || {};
  window.Modules.GameRooms = (canvas) => GameRooms.render(canvas);

  // Register with SPA Router
  function registerRoute() {
    if (window.appRouter) {
      window.appRouter.register('#/game/rooms', (canvas) => GameRooms.render(canvas));
    }
  }

  registerRoute();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(registerRoute, 0));
  } else {
    setTimeout(registerRoute, 0);
  }
})();
