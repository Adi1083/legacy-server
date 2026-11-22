"""
IND PROJECT Control Center — QA & Regression Suite
Suite 07: Overview / Main Dashboard Module Verification
Tests: Syntax, Component Contracts, Zero Emojis, Lifecycle & Error Handling
"""

import os
import re
import subprocess
import unittest

DASHBOARD_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(os.path.dirname(DASHBOARD_TESTS_DIR))
OVERVIEW_JS_PATH = os.path.join(SERVER_DIR, "static", "dashboard", "src", "modules", "overview", "main.js")


class TestOverviewModule(unittest.TestCase):
    """Automated QA & Regression test cases for the Overview Module."""

    def test_overview_file_exists_and_syntax_valid(self):
        """Verify overview/main.js exists and passes Node.js syntax parsing."""
        self.assertTrue(os.path.isfile(OVERVIEW_JS_PATH), f"File missing: {OVERVIEW_JS_PATH}")

        # Run node --check
        res = subprocess.run(["node", "--check", OVERVIEW_JS_PATH], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node syntax check failed:\n{res.stderr}")

    def test_zero_emojis_in_source(self):
        """Verify that zero consumer emoji icons exist in overview/main.js."""
        with open(OVERVIEW_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for common emoji ranges
        emoji_pattern = re.compile(
            r"[\U0001F300-\U0001F6FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FAFF]|[\u2600-\u26FF]|[\u2700-\u27BF]"
        )
        matches = emoji_pattern.findall(content)
        self.assertEqual(len(matches), 0, f"Found consumer emojis in overview/main.js: {matches}")

    def test_shared_design_classes_present(self):
        """Verify that overview/main.js utilizes the standard tokens.css design system classes."""
        with open(OVERVIEW_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        required_classes = [
            "page-container",
            "grid-4",
            "split-view",
            "split-pane-left",
            "split-pane-right",
            "glass-card",
        ]
        for cls in required_classes:
            self.assertIn(cls, content, f"Overview module must utilize CSS class .{cls}")

    def test_shared_ui_components_invoked(self):
        """Verify that overview/main.js reuses the shared UI library components."""
        with open(OVERVIEW_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        required_components = [
            "UI.PageHeader",
            "UI.StatCard",
            "UI.Badge",
            "UI.CurrencyChip",
            "UI.StatusDot",
            "UI.Table",
            "UI.EmptyState",
            "UI.Icon",
        ]
        for comp in required_components:
            self.assertIn(comp, content, f"Overview module must invoke {comp}")

    def test_node_vm_runtime_lifecycle(self):
        """Execute Overview module in a Node.js VM to verify registration, rendering, and lifecycle."""
        escaped_path = OVERVIEW_JS_PATH.replace("\\", "\\\\")
        runner_script = f"""
        const fs = require('fs');
        const vm = require('vm');

        // Setup mock browser environment
        const context = {{
            window: {{}},
            document: {{}},
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
            console: console
        }};
        context.window = context;

        // Mock UI Component library
        context.UI = {{
            PageHeader: (t, s, a, i) => `<header>${{t}}</header>`,
            StatCard: (l, v, d, i, vr) => `<div class="stat-card">${{l}}:${{v}}</div>`,
            Card: (opts) => `<div class="glass-card">${{typeof opts === 'object' ? (opts.title || '') + (opts.content || '') : opts}}</div>`,
            Badge: (txt, vr) => `<span class="badge">${{txt}}</span>`,
            CurrencyChip: (t, a) => `<span class="chip">${{t}}:${{a}}</span>`,
            StatusDot: (s) => `<span class="dot ${{s}}"></span>`,
            Table: (cols, rows) => `<table>${{rows}}</table>`,
            EmptyState: (t, m) => `<div class="empty">${{t}}</div>`,
            Icon: (name) => `<svg data-icon="${{name}}"></svg>`,
            Loading: (m) => `<div>${{m}}</div>`,
            Toast: () => {{}}
        }};

        // Mock router, playerContext and apiClient
        let registeredRoute = null;
        context.appRouter = {{
            register: (route, handler) => {{ registeredRoute = route; }}
        }};
        context.playerContext = {{
            getSelectedAccountId: () => 10001,
            subscribe: () => () => {{}}
        }};
        context.apiClient = {{
            get: async (url) => {{
                if (url.includes('/state')) {{
                    return {{
                        ok: true,
                        data: {{
                            server: {{ uptime_sec: 1234, request_count: 50 }},
                            all_players: [{{ account_id: 10001, is_online: true }}],
                            profile: {{ nickname: 'Tester', level: 50, ranking_points: 1000 }},
                            wallet: {{ gems: 500, coins: 10000 }},
                            rooms: []
                        }}
                    }};
                }}
                if (url.includes('/requests')) {{
                    return {{ ok: true, data: {{ requests: [{{ time: '12:00:00', method: 'GET', path: '/test', client: '127.0.0.1', body_len: 128 }}] }} }};
                }}
                return {{ ok: true, data: {{}} }};
            }},
            post: async () => ({{ ok: true }})
        }};
        context.location = {{ hash: '#/overview/main', startsWith: (s) => true }};

        vm.createContext(context);
        const code = fs.readFileSync('{escaped_path}', 'utf8');
        vm.runInContext(code, context);

        // Verification assertions
        if (registeredRoute !== '#/overview/main') {{
            throw new Error('Expected route #/overview/main to be registered, got: ' + registeredRoute);
        }}
        if (!context.OverviewMainModule || typeof context.OverviewMainModule.render !== 'function') {{
            throw new Error('OverviewMainModule.render missing');
        }}
        if (typeof context.OverviewMainModule.manualRefresh !== 'function') {{
            throw new Error('OverviewMainModule.manualRefresh missing');
        }}
        if (typeof context.OverviewMainModule.setPollRate !== 'function') {{
            throw new Error('OverviewMainModule.setPollRate missing');
        }}

        // Test execution of render
        const canvas = {{ innerHTML: '' }};
        context.OverviewMainModule.render(canvas).then(() => {{
            if (!canvas.innerHTML.includes('page-container')) {{
                throw new Error('Render output did not contain page-container');
            }}
            if (!canvas.innerHTML.includes('stat-card')) {{
                throw new Error('Render output did not contain stat-card');
            }}
            console.log('SUCCESS');
            process.exit(0);
        }}).catch(err => {{
            console.error('Async render failed:', err);
            process.exit(1);
        }});
        """

        res = subprocess.run(["node", "-e", runner_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node VM runtime validation failed:\n{res.stderr}\n{res.stdout}")
        self.assertIn("SUCCESS", res.stdout)


if __name__ == "__main__":
    unittest.main()
