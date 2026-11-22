"""
IND PROJECT Control Center — QA & Regression Suite
Suite 09: Player Fleet Module Verification
Tests: Syntax, Component Contracts, Zero Emojis, Lifecycle & Node VM Runtime Execution
Covering: directory.js, inspector.js, account.js, sessions.js, bans.js
"""

import os
import re
import subprocess
import unittest

DASHBOARD_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(os.path.dirname(DASHBOARD_TESTS_DIR))
PLAYERS_DIR = os.path.join(SERVER_DIR, "static", "dashboard", "src", "modules", "players")

PLAYER_MODULE_FILES = [
    "directory.js",
    "inspector.js",
    "account.js",
    "sessions.js",
    "bans.js",
]


class TestPlayersModule(unittest.TestCase):
    """Automated QA & Regression test cases for the Player Fleet Modules."""

    def test_all_player_modules_exist_and_syntax_valid(self):
        """Verify all 5 player module files exist and pass Node.js syntax parsing."""
        for filename in PLAYER_MODULE_FILES:
            filepath = os.path.join(PLAYERS_DIR, filename)
            self.assertTrue(os.path.isfile(filepath), f"File missing: {filepath}")

            res = subprocess.run(["node", "--check", filepath], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node syntax check failed for {filename}:\n{res.stderr}")

    def test_zero_emojis_in_player_modules(self):
        """Verify that zero consumer emoji icons exist in any player module source."""
        emoji_pattern = re.compile(
            r"[\U0001F300-\U0001F6FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FAFF]|[\u2600-\u26FF]|[\u2700-\u27BF]"
        )
        for filename in PLAYER_MODULE_FILES:
            filepath = os.path.join(PLAYERS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            matches = emoji_pattern.findall(content)
            self.assertEqual(len(matches), 0, f"Found consumer emojis in {filename}: {matches}")

    def test_shared_design_classes_present(self):
        """Verify that all player modules utilize standard tokens.css design system classes."""
        for filename in PLAYER_MODULE_FILES:
            filepath = os.path.join(PLAYERS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("page-container", content, f"{filename} must utilize .page-container")
            self.assertIn("grid-4", content, f"{filename} must utilize .grid-4 metric strip")

    def test_shared_ui_components_invoked(self):
        """Verify that player modules invoke standardized UI library factory methods."""
        for filename in PLAYER_MODULE_FILES:
            filepath = os.path.join(PLAYERS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("UI.PageHeader", content, f"{filename} must invoke UI.PageHeader")
            self.assertIn("UI.StatCard", content, f"{filename} must invoke UI.StatCard")
            self.assertIn("UI.Badge", content, f"{filename} must invoke UI.Badge")
            self.assertIn("UI.Icon", content, f"{filename} must invoke UI.Icon")

    def test_node_vm_runtime_lifecycle(self):
        """Execute all player modules in Node VM to verify registration and error-free execution."""
        runner_script = f"""
        const fs = require('fs');
        const vm = require('vm');
        const path = require('path');

        const playersDir = {repr(PLAYERS_DIR)};
        const files = {repr(PLAYER_MODULE_FILES)};

        const registeredRoutes = {{}};

        const context = {{
            window: {{}},
            document: {{
                activeElement: null,
                getElementById: (id) => null
            }},
            performance: {{ now: () => 100 }},
            Date: Date,
            Math: Math,
            Number: Number,
            String: String,
            parseInt: parseInt,
            setTimeout: setTimeout,
            clearTimeout: clearTimeout,
            setInterval: setInterval,
            clearInterval: clearInterval,
            console: console,
            localStorage: {{
                getItem: () => '[]',
                setItem: () => {{}},
                removeItem: () => {{}}
            }}
        }};
        context.window = context;

        // Mock window.appRouter
        context.window.appRouter = {{
            register: (route, fn) => {{
                registeredRoutes[route] = fn;
            }}
        }};

        // Mock window.apiClient
        context.window.apiClient = {{
            get: async (url, params) => ({{
                ok: true,
                data: {{
                    players: [{{ account_id: 10001, nickname: 'Pushpa', level: 60, region: 'IND', is_banned: false, is_online: true, diamonds: 500, gold: 10000 }}],
                    total: 1,
                    profile: {{ account_id: 10001, nickname: 'Pushpa', level: 60, region: 'IND', is_banned: false, is_online: true, diamonds: 500, gold: 10000 }},
                    wallet: {{ coins: 10000, gems: 500 }},
                    requests: [{{ time: '22:00:00', method: 'GET', path: '/api/test', ip: '127.0.0.1', body_len: 120 }}]
                }}
            }}),
            post: async (url, payload) => ({{ ok: true, data: {{ account_id: 10002 }} }})
        }};

        // Mock window.playerContext
        context.window.playerContext = {{
            getSelectedAccountId: () => 10001,
            getCurrentPlayer: () => ({{
                profile: {{ account_id: 10001, nickname: 'Pushpa', level: 60, region: 'IND', is_banned: false, is_online: true, diamonds: 500, gold: 10000 }},
                wallet: {{ coins: 10000, gems: 500 }}
            }}),
            setAccountId: async (aid) => {{}},
            refresh: async () => {{}},
            onPlayerChange: (fn) => {{}}
        }};

        // Mock window.UI
        context.window.UI = {{
            Icons: {{
                users: '', user: '', settings: '', activity: '', shield: '',
                refresh: '', copy: '', search: '', x: '', plus: '', moreHorizontal: '',
                diamond: '', coins: '', award: '', trophy: '', heart: '', pawPrint: '',
                shirt: '', ban: '', unlock: '', checkCircle: '', alertTriangle: '',
                database: '', server: '', terminal: '', crosshair: '', fileText: '',
                creditCard: '', package: '', inbox: ''
            }},
            Icon: (name) => `<svg data-icon="${{name}}"></svg>`,
            PageHeader: (title, sub, actions, icon) => `<div class="page-header">${{title}}</div>`,
            StatCard: (label, val, sub, icon, variant) => `<div class="stat-card">${{label}}: ${{val}}</div>`,
            Badge: (txt, v) => `<span class="badge">${{txt}}</span>`,
            StatusDot: (s) => `<span class="status-dot"></span>`,
            Button: (label) => `<button>${{label}}</button>`,
            Table: (h, r) => `<table><tbody>${{r}}</tbody></table>`,
            CurrencyChip: (t, a) => `<div class="currency-chip">${{t}}: ${{a}}</div>`,
            EmptyState: (t, m) => `<div class="empty-state">${{t}}</div>`,
            UnavailableState: (f, e) => `<div class="unavailable">${{f}}</div>`,
            Loading: (m) => `<div class="loading">${{m}}</div>`,
            Card: (t, s, body) => `<div class="glass-card">${{body}}</div>`,
            Modal: () => {{}},
            CloseModal: () => {{}},
            Confirm: () => {{}},
            Toast: () => {{}}
        }};

        vm.createContext(context);

        // Load each player module
        for (const file of files) {{
            const code = fs.readFileSync(path.join(playersDir, file), 'utf8');
            vm.runInContext(code, context);
        }}

        // Verify registration of all 5 routes
        const expectedRoutes = [
            '#/players/directory',
            '#/players/inspector',
            '#/players/account',
            '#/players/sessions',
            '#/players/bans'
        ];

        for (const r of expectedRoutes) {{
            if (typeof registeredRoutes[r] !== 'function') {{
                console.error('Route not registered: ' + r);
                process.exit(1);
            }}
        }}

        // Test running each module function
        async function runModules() {{
            for (const r of expectedRoutes) {{
                const canvas = {{ innerHTML: '' }};
                await registeredRoutes[r](canvas);
                if (!canvas.innerHTML.includes('page-container')) {{
                    console.error('Module ' + r + ' failed to produce .page-container');
                    process.exit(1);
                }}
            }}
            console.log('ALL_MODULES_EXECUTED_CLEANLY');
            process.exit(0);
        }}

        runModules().catch(err => {{
            console.error('Runtime error in module execution:', err);
            process.exit(1);
        }});
        """

        res = subprocess.run(["node", "-e", runner_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node VM lifecycle test failed:\n{res.stderr}\nOutput: {res.stdout}")
        self.assertIn("ALL_MODULES_EXECUTED_CLEANLY", res.stdout)


if __name__ == "__main__":
    unittest.main()
