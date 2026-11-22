/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Module: 08 Content Management System (CMS) Main Entry Point
 * 
 * Aggregates:
 * - #/cms/banners       -> Billboard Banner Manager
 * - #/cms/lobby         -> Lobby CMS & Splash Screens
 * - #/cms/announcements -> Announcements & Marquee Ticker
 * - #/cms/events        -> Events & Quests Studio
 */

(function () {
  'use strict';

  window.CMS = {
    get Banners() { return window.CMSBanners; },
    get Lobby() { return window.CMSLobby; },
    get Announcements() { return window.CMSAnnouncements; },
    get Events() { return window.CMSEvents; }
  };

  // Safe router check to ensure all 4 routes are registered
  if (window.appRouter) {
    if (window.CMSBanners) {
      window.appRouter.register('#/cms/banners', async (canvas) => window.CMSBanners.init(canvas));
    }
    if (window.CMSLobby) {
      window.appRouter.register('#/cms/lobby', async (canvas) => window.CMSLobby.init(canvas));
    }
    if (window.CMSAnnouncements) {
      window.appRouter.register('#/cms/announcements', async (canvas) => window.CMSAnnouncements.init(canvas));
    }
    if (window.CMSEvents) {
      window.appRouter.register('#/cms/events', async (canvas) => window.CMSEvents.init(canvas));
    }
  }
})();
