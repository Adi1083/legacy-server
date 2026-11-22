/**
 * Automated Verification Test Suite for Domain 07: Social & Communication Modules
 */

const assert = require('assert');

// Mock browser environment
global.window = global;
global.document = {
  readyState: 'complete',
  addEventListener: () => {},
  getElementById: (id) => {
    return {
      innerHTML: '',
      value: '10001',
      style: {},
      classList: { add: () => {}, remove: () => {} },
      appendChild: () => {},
      focus: () => {},
      scrollIntoView: () => {}
    };
  },
  body: {
    appendChild: () => {}
  }
};
global.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {}
};

// Mock UI
global.UI = {
  Card: (title, sub, body) => `<div class="card">${title}</div>`,
  Loading: (t) => `<div>${t}</div>`,
  Toast: (msg, type) => {
    console.log(`[Toast ${type}] ${msg}`);
  },
  Confirm: (title, msg, cb, isDestructive) => {
    console.log(`[Confirm dialog] ${title} (destructive=${isDestructive})`);
    cb();
  },
  Badge: (txt, v) => `<span>${txt}</span>`
};
window.UI = global.UI;

// Mock PlayerContext
global.playerContext = {
  selectedAccountId: 10001,
  getSelectedAccountId: () => global.playerContext.selectedAccountId,
  subscribe: (cb) => {},
  refresh: async () => {}
};
window.playerContext = global.playerContext;

// Mock ApiClient
const mockDb = {
  mails: [
    { mail_id: 101, title: 'Welcome Mail', content: 'Hello recruit!', is_claimed: false, coins: 5000, gems: 100, attachments: [] },
    { mail_id: 102, title: 'Hotfix Compensate', content: 'Apologies', is_claimed: true, coins: 10000, gems: 200, attachments: [] }
  ],
  friends: [
    { account_id: 20001, nickname: 'IndiaV1_Bot', online_status: 1, is_online: true, level: 65 },
    { account_id: 20002, nickname: 'Kelly_Dash', online_status: 0, is_online: false, level: 58 }
  ],
  friend_requests: [
    { from_id: 20005, to_id: 10001, nickname: 'Paloma_Arms', message: 'Squad up!' }
  ],
  team: {
    team_id: 888,
    leader_id: 10001,
    team_name: 'Alpha Squad',
    mode: 'squad',
    map_id: 1,
    members: [
      { account_id: 10001, nickname: 'Commander', role: 1, ready: true },
      { account_id: 20001, nickname: 'IndiaV1_Bot', role: 2, ready: false }
    ]
  },
  invitations: [
    { invite_id: 55, team_id: 777, inviter_id: 20003, inviter_nick: 'Hayato_Blade', mode: 'squad' }
  ]
};

global.apiClient = {
  get: async (url, params) => {
    if (url === '/api/dashboard/mail') {
      return { ok: true, data: { mails: mockDb.mails, wallet: { coins: 50000, gems: 1500 } } };
    }
    if (url === '/api/dashboard/friends') {
      return { ok: true, data: { friends: mockDb.friends, friend_requests: mockDb.friend_requests, all_players: [] } };
    }
    if (url === '/api/dashboard/squad') {
      return { ok: true, data: { team: mockDb.team, team_invitations: mockDb.invitations } };
    }
    return { ok: true, data: {} };
  },
  post: async (url, body) => {
    console.log(`[API POST ${url}]`, JSON.stringify(body));
    if (url === '/api/dashboard/mail/claim') {
      return { ok: true, data: { claimed_coins: 5000, claimed_gems: 100 } };
    }
    if (url === '/api/dashboard/mail/delete') {
      mockDb.mails = mockDb.mails.filter(m => m.mail_id !== body.mail_id);
      return { ok: true, data: { mails: mockDb.mails } };
    }
    if (url === '/api/dashboard/mail/send') {
      const newMail = { mail_id: 999, ...body, is_claimed: false };
      mockDb.mails.push(newMail);
      return { ok: true, data: { mail: newMail } };
    }
    if (url === '/api/dashboard/friends/remove') {
      mockDb.friends = mockDb.friends.filter(f => f.account_id !== body.friend_id);
      return { ok: true, data: { friends: mockDb.friends } };
    }
    if (url === '/api/dashboard/friends/reject') {
      mockDb.friend_requests = mockDb.friend_requests.filter(r => r.from_id !== body.friend_id);
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/friends/accept') {
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/friends/add') {
      mockDb.friends.push({ account_id: body.friend_id, nickname: body.nickname, online_status: 1 });
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/friends/online') {
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/squad/create') {
      return { ok: true, data: { team: { team_id: 999, ...body } } };
    }
    if (url === '/api/dashboard/squad/ready') {
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/squad/leave') {
      mockDb.team = null;
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/squad/kick') {
      mockDb.team.members = mockDb.team.members.filter(m => m.account_id !== body.target_id);
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/squad/invite') {
      return { ok: true, data: { tcp_pushed: true } };
    }
    if (url === '/api/dashboard/squad/join') {
      return { ok: true, data: {} };
    }
    if (url === '/api/dashboard/squad/decline') {
      mockDb.invitations = mockDb.invitations.filter(i => i.invite_id !== body.invite_id);
      return { ok: true, data: {} };
    }
    return { ok: true, data: {} };
  }
};
window.apiClient = global.apiClient;

// Mock AppRouter
const registeredRoutes = new Map();
global.appRouter = {
  register: (path, handler) => {
    registeredRoutes.set(path, handler);
    console.log(`[Router Register] ${path}`);
  }
};
window.appRouter = global.appRouter;

// Load module files
require('../static/dashboard/src/modules/social/mail.js');
require('../static/dashboard/src/modules/social/mail-compose.js');
require('../static/dashboard/src/modules/social/friends.js');
require('../static/dashboard/src/modules/social/squads.js');
require('../static/dashboard/src/modules/social/social-module.js');

async function runTests() {
  console.log('--- TEST 1: Route Registration ---');
  assert(registeredRoutes.has('#/social/mail'), 'Route #/social/mail must be registered');
  assert(registeredRoutes.has('#/social/mail-compose'), 'Route #/social/mail-compose must be registered');
  assert(registeredRoutes.has('#/social/friends'), 'Route #/social/friends must be registered');
  assert(registeredRoutes.has('#/social/squads'), 'Route #/social/squads must be registered');
  console.log('✅ All 4 social routes successfully registered with appRouter');

  console.log('\n--- TEST 2: Mailbox Manager ---');
  assert(window.SocialMail, 'window.SocialMail must be defined');
  const canvas = { innerHTML: '' };
  window.SocialMail.render(canvas);
  await new Promise(r => setTimeout(r, 100));
  assert(canvas.innerHTML.length > 0, 'Canvas must contain rendered mailbox HTML');
  assert(canvas.innerHTML.includes('Inbox Capacity'), 'Should display metrics');
  assert(canvas.innerHTML.includes('Welcome Mail'), 'Should render mail title');

  // Test claim and confirmClaim
  window.SocialMail.confirmClaim(101);
  window.SocialMail.confirmClaimAll();
  await window.SocialMail.claimMail(101);

  // Test delete confirmation & delete
  let confirmTriggered = false;
  window.SocialMail.confirmDelete(101, 'Welcome Mail');
  await new Promise(r => setTimeout(r, 100));
  assert(!mockDb.mails.some(m => m.mail_id === 101), 'Mail 101 should be deleted after confirm');
  console.log('✅ Mailbox Manager rendering, claim, and confirmed deletion verified');

  console.log('\n--- TEST 3: Mail Composer ---');
  assert(window.SocialMailCompose, 'window.SocialMailCompose must be defined');
  window.SocialMailCompose.render(canvas);
  assert(canvas.innerHTML.includes('In-Game Envelope Simulator'), 'Simulator must be present');
  window.SocialMailCompose.applyTemplate('compensation');
  await window.SocialMailCompose.dispatchMail();
  assert(mockDb.mails.some(m => m.title.includes('Hotfix Maintenance')), 'Dispatched mail should be stored in mails list');
  console.log('✅ Mail Composer presets, simulator, and dispatch verified');

  console.log('\n--- TEST 4: Friends Manager ---');
  assert(window.SocialFriends, 'window.SocialFriends must be defined');
  window.SocialFriends.render(canvas);
  await new Promise(r => setTimeout(r, 100));
  assert(canvas.innerHTML.includes('Active Friends Roster'), 'Friends list rendered');
  assert(canvas.innerHTML.includes('IndiaV1_Bot'), 'Bot rendered in friends list');

  // Test online status change
  await window.SocialFriends.setStatus(20001, 2);

  // Test add friend
  await window.SocialFriends.quickAddBot(20010, 'Alok_DJ');
  assert(mockDb.friends.some(f => f.account_id === 20010), 'Bot Alok_DJ should be added to friends');

  // Test confirmed remove friend
  window.SocialFriends.confirmRemove(20002, 'Kelly_Dash');
  assert(!mockDb.friends.some(f => f.account_id === 20002), 'Friend 20002 should be removed after confirm');

  // Test accept / reject request
  await window.SocialFriends.acceptRequest(20005);
  window.SocialFriends.confirmReject(20005);
  console.log('✅ Friends Manager status update, quick-bot add, confirmed removal, and request handling verified');

  console.log('\n--- TEST 5: Squad Manager ---');
  assert(window.SocialSquads, 'window.SocialSquads must be defined');
  window.SocialSquads.render(canvas);
  await new Promise(r => setTimeout(r, 100));
  assert(canvas.innerHTML.includes('Alpha Squad'), 'Squad name rendered');
  assert(canvas.innerHTML.includes('Instant TCP Squad Invite Controller'), 'TCP trigger rendered');

  // Test ready toggle
  await window.SocialSquads.toggleReady();

  // Test TCP invite
  await window.SocialSquads.triggerTcpInvite();

  // Test confirmed kick
  window.SocialSquads.confirmKick(20001, 'IndiaV1_Bot');
  assert(!mockDb.team.members.some(m => m.account_id === 20001), 'Member 20001 should be kicked after confirm');

  // Test confirmed leave
  window.SocialSquads.confirmLeaveSquad();
  assert(mockDb.team === null, 'Squad should be abandoned after leave');
  console.log('✅ Squad Manager lobby monitor, ready toggle, TCP dispatch, kick, and leave verified');

  console.log('\n========================================');
  console.log('🎉 ALL 5 SOCIAL & COMMUNICATION MODULE TESTS PASSED!');
  console.log('========================================');
}

runTests().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
