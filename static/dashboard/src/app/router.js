/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * SPA Hash Router & View Dispatcher
 * Manages hash navigation, error boundaries, dynamic module delegation, zero full-page reloads
 */

class AppRouter {
  constructor() {
    this.routes = new Map();
    this.currentPath = '';
    this.defaultRoute = '#/overview/main';
    this.isNavigating = false;

    // React to hashchange events without full-page reloads
    window.addEventListener('hashchange', () => this.handleRoute());

    // Intercept in-app link clicks to guarantee zero page reloads
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href^="#/"]');
      if (link) {
        const href = link.getAttribute('href');
        if (href && href.startsWith('#/')) {
          e.preventDefault();
          this.navigate(href);
        }
      }
    });
  }

  has(path) {
    return this.routes.has(path);
  }

  register(path, handler, isFallback = false) {
    if (isFallback && this.routes.has(path)) {
      return;
    }
    this.routes.set(path, handler);
  }

  navigate(path) {
    if (window.location.hash === path) {
      this.handleRoute();
    } else {
      window.location.hash = path;
    }
  }

  parseRoute(hash) {
    let clean = hash || this.defaultRoute;
    if (!clean.startsWith('#/')) {
      clean = this.defaultRoute;
    }

    const [pathPart, queryPart] = clean.split('?');
    const params = {};
    if (queryPart) {
      const sp = new URLSearchParams(queryPart);
      for (const [k, v] of sp.entries()) {
        params[k] = v;
      }
    }

    return {
      fullHash: clean,
      cleanPath: pathPart,
      params
    };
  }

  async handleRoute() {
    if (this.isNavigating) return;
    this.isNavigating = true;

    try {
      const { fullHash, cleanPath, params } = this.parseRoute(window.location.hash);
      this.currentPath = cleanPath;

      // 1. Update Navigation UI (Sidebar active item & Topbar breadcrumbs)
      if (window.Sidebar && window.Sidebar.setActive) {
        window.Sidebar.setActive(cleanPath);
      }
      if (window.Topbar && window.Topbar.updateBreadcrumbs) {
        window.Topbar.updateBreadcrumbs(cleanPath);
      }

      const canvas = document.getElementById('workspace-canvas');
      if (!canvas) {
        this.isNavigating = false;
        return;
      }

      // 2. Resolve View Handler
      let handler = this.routes.get(cleanPath);

      // Check dynamic module registry if not directly bound
      if (!handler && window.Modules) {
        const parts = cleanPath.replace('#/', '').split('/');
        const domain = parts[0];
        const view = parts[1];

        // Format name variations: OverviewMain, overview_main, etc.
        const camelName = domain.replace(/-([a-z])/g, g => g[1].toUpperCase()) +
                          view.charAt(0).toUpperCase() + view.slice(1).replace(/-([a-z])/g, g => g[1].toUpperCase());

        if (typeof window.Modules[cleanPath] === 'function') {
          handler = window.Modules[cleanPath];
        } else if (typeof window.Modules[camelName] === 'function') {
          handler = window.Modules[camelName];
        } else if (window.Modules[domain] && typeof window.Modules[domain][view] === 'function') {
          handler = window.Modules[domain][view];
        }
      }

      // 3. Execute View with Error Boundary
      if (handler) {
        try {
          if (window.UI && window.UI.Loading) {
            canvas.innerHTML = window.UI.Loading('Loading workspace...');
          }
          await handler(canvas, params);
        } catch (err) {
          console.error('Workspace view execution error:', err);
          canvas.innerHTML = `
            <div class="glass-card" style="border-color: rgba(244, 63, 94, 0.4); max-width: 600px; margin: 32px auto;">
              <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 20px;">⚠️</span>
                <span style="color: var(--accent-rose); font-weight: 600; font-size: 15px;">Workspace Render Error</span>
              </div>
              <div style="color: var(--text-secondary); font-size: 12px; margin-bottom: 16px; line-height: 1.6;">
                An unexpected error occurred while executing view <code>${cleanPath}</code>:
                <br>
                <code style="display: block; background: rgba(0,0,0,0.4); padding: 8px 12px; border-radius: 4px; color: var(--accent-rose); font-family: var(--font-mono); font-size: 11.5px; margin-top: 8px;">
                  ${err.message || 'Unknown render exception'}
                </code>
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="btn btn-primary" onclick="window.appRouter.handleRoute()">Retry View</button>
                <button class="btn btn-secondary" onclick="window.location.hash='#/overview/main'">Return to Overview</button>
              </div>
            </div>
          `;
        }
      } else {
        // 404 Route Not Found
        canvas.innerHTML = `
          <div class="unavailable-box">
            <div class="unavailable-icon">🧭</div>
            <div class="unavailable-title">Workspace Not Found</div>
            <div class="unavailable-desc">
              The requested route <code>${cleanPath}</code> has not been registered in the Control Center SPA router.
              <br><br>
              <button class="btn btn-primary" onclick="window.location.hash='#/overview/main'">Return to Main Dashboard</button>
            </div>
          </div>
        `;
      }
    } finally {
      this.isNavigating = false;
    }
  }

  start() {
    if (!window.location.hash) {
      window.location.hash = this.defaultRoute;
    } else {
      this.handleRoute();
    }
  }
}

window.appRouter = new AppRouter();
