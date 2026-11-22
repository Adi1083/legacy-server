/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Domain 07: Social & Communication — Master Module Aggregator & Route Registry
 *
 * Workspaces Registered:
 * - #/social/mail         -> SocialMail.render
 * - #/social/mail-compose -> SocialMailCompose.render
 * - #/social/friends      -> SocialFriends.render
 * - #/social/squads       -> SocialSquads.render
 */

(function (root) {
  'use strict';

  // Ensure Modules namespace exists
  root.Modules = root.Modules || {};
  root.Modules.social = root.Modules.social || {};

  function registerRoutes() {
    // 1. Hook into window.Modules with all naming conventions
    if (root.SocialMail && root.SocialMail.render) {
      root.Modules.SocialMail = root.SocialMail.render;
      root.Modules.socialMail = root.SocialMail.render;
      root.Modules['#/social/mail'] = root.SocialMail.render;
      root.Modules.social.mail = root.SocialMail.render;
      if (root.appRouter && root.appRouter.register) {
        root.appRouter.register('#/social/mail', root.SocialMail.render);
      }
    }

    if (root.SocialMailCompose && root.SocialMailCompose.render) {
      root.Modules.SocialMailCompose = root.SocialMailCompose.render;
      root.Modules.socialMailCompose = root.SocialMailCompose.render;
      root.Modules['#/social/mail-compose'] = root.SocialMailCompose.render;
      root.Modules.social['mail-compose'] = root.SocialMailCompose.render;
      if (root.appRouter && root.appRouter.register) {
        root.appRouter.register('#/social/mail-compose', root.SocialMailCompose.render);
      }
    }

    if (root.SocialFriends && root.SocialFriends.render) {
      root.Modules.SocialFriends = root.SocialFriends.render;
      root.Modules.socialFriends = root.SocialFriends.render;
      root.Modules['#/social/friends'] = root.SocialFriends.render;
      root.Modules.social.friends = root.SocialFriends.render;
      if (root.appRouter && root.appRouter.register) {
        root.appRouter.register('#/social/friends', root.SocialFriends.render);
      }
    }

    if (root.SocialSquads && root.SocialSquads.render) {
      root.Modules.SocialSquads = root.SocialSquads.render;
      root.Modules.socialSquads = root.SocialSquads.render;
      root.Modules['#/social/squads'] = root.SocialSquads.render;
      root.Modules.social.squads = root.SocialSquads.render;
      if (root.appRouter && root.appRouter.register) {
        root.appRouter.register('#/social/squads', root.SocialSquads.render);
      }
    }
  }

  // Attempt immediate registration
  registerRoutes();

  // Also bind to DOMContentLoaded and window load to guarantee registration
  if (typeof document !== 'undefined' && document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerRoutes);
  }
  if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('load', registerRoutes);
  }

  // Unified SocialModule Export
  root.SocialModule = {
    get Mail() { return root.SocialMail; },
    get MailCompose() { return root.SocialMailCompose; },
    get Friends() { return root.SocialFriends; },
    get Squads() { return root.SocialSquads; },
    registerRoutes
  };

})(typeof window !== 'undefined' ? window : this);
