"""
IND PROJECT Control Center — QA & Regression Suite
Suite 08: Server Monitoring Module Verification
Tests: Syntax, Component Contracts, Zero Emojis, Lifecycle & Drawer Inspector
"""

import os
import re
import subprocess
import unittest

DASHBOARD_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(os.path.dirname(DASHBOARD_TESTS_DIR))
MONITORING_JS_PATH = os.path.join(SERVER_DIR, "static", "dashboard", "src", "modules", "overview", "monitoring.js")


class TestMonitoringModule(unittest.TestCase):
    """Automated QA & Regression test cases for the Server Monitoring Module."""

    def test_monitoring_file_exists_and_syntax_valid(self):
        """Verify overview/monitoring.js exists and passes Node.js syntax parsing."""
        self.assertTrue(os.path.isfile(MONITORING_JS_PATH), f"File missing: {MONITORING_JS_PATH}")

        # Run node --check
        res = subprocess.run(["node", "--check", MONITORING_JS_PATH], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node syntax check failed:\n{res.stderr}")

    def test_zero_emojis_in_source(self):
        """Verify that zero consumer emoji icons exist in overview/monitoring.js."""
        with open(MONITORING_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        emoji_pattern = re.compile(
            r"[\U0001F300-\U0001F6FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FAFF]|[\u2600-\u26FF]|[\u2700-\u27BF]"
        )
        matches = emoji_pattern.findall(content)
        self.assertEqual(len(matches), 0, f"Found consumer emojis in overview/monitoring.js: {matches}")

    def test_shared_design_classes_present(self):
        """Verify that overview/monitoring.js utilizes the standard tokens.css design system classes."""
        with open(MONITORING_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        required_classes = [
            "page-container",
            "grid-4",
            "glass-card",
            "glass-card-header",
            "glass-card-title",
            "glass-table",
        ]
        for cls in required_classes:
            self.assertIn(cls, content, f"Monitoring module must utilize CSS class .{cls}")

    def test_shared_ui_components_invoked(self):
        """Verify that overview/monitoring.js reuses the shared UI library components."""
        with open(MONITORING_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        required_components = [
            "UI.PageHeader",
            "UI.StatCard",
            "UI.Badge",
            "UI.StatusDot",
            "UI.Drawer",
            "UI.EmptyState",
            "UI.Icon",
            "UI.Confirm",
        ]
        for comp in required_components:
            self.assertIn(comp, content, f"Monitoring module must invoke {comp}")

    def test_node_vm_runtime_lifecycle(self):
        """Execute Monitoring module in a Node.js VM to verify registration, rendering, and lifecycle."""
        escaped_path = MONITORING_JS_PATH.replace("\\", "\\\\")
        runner_script = f"""
        const fs = require('fs');
        const vm = require('vm');

        // Setup mock browser environment
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
            console: console
        }};
        context.window = context;

        // Mock UI Component library
        context.UI = {{
            PageHeader: (t, s, a, i) => `<header>${{t}}</header>`,
            StatCard: (l, v, d, i, vr) => `<div class="stat-card">${{l}}:${{v}}</div>`,
            Badge: (txt, vr) => `<span class="badge">${{txt}}</span>`,
            StatusDot: (s) => `<span class="dot ${{s}}"></span>`,
            Drawer: (title, body, footer, opts) => `<div class="drawer">${{title}}</div>`,
            CloseDrawer: () => {{}},
            EmptyState: (t, m, i, a) => `<div class="empty">${{t}}</div>`,
            Icon: (name) => `<svg data-icon="${{name}}"></svg>`,
            Loading: (m) => `<div>${{m}}</div>`,
            Confirm: (t, m, cb) => cb(),
            Toast: () => {{}}
        }};

        // Mock router and apiClient
        let registeredRoute = null;
        context.appRouter = {{
            register: (route, handler) => {{ registeredRoute = route; }}
        }};

        context.apiClient = {{
            get: async (url, params) => {{
                if (url === '/api/dashboard/requests') {{
                    return {{
                        ok: true,
                        data: {{
                            requests: [
                                {{
                                    id: 1,
                                    time: '12:00:00',
                                    method: 'GET',
                                    path: '/api/dashboard/state',
                                    client: '127.0.0.1',
                                    body_len: 0
                                }},
                                {{
                                    id: 2,
                                    time: '12:00:01',
                                    method: 'POST',
                                    path: '/MajorLogin',
                                    client: '127.0.0.1',
                                    body_len: 64,
                                    body_hex: '089601',
                                    decoded: {{ summary: 'Login: 10001' }}
                                }}
                            ],
                            total: 2
                        }}
                    }};
                }}
                if (url === '/api/dashboard/state') {{
                    return {{
                        ok: true,
                        data: {{
                            server: {{ uptime_sec: 3600, request_count: 42 }},
                            all_players: [{{ is_online: true }}],
                            rooms: []
                        }}
                    }};
                }}
                return {{ ok: true, data: {{}} }};
            }},
            post: async (url, body) => ({{ ok: true, data: {{}} }}),
            onActivity: (cb) => (() => {{}})
        }};

        context.location = {{
            hash: '#/overview/monitoring'
        }};

        // Execute monitoring.js inside Node VM
        const code = fs.readFileSync('{escaped_path}', 'utf8');
        vm.runInNewContext(code, context);

        if (registeredRoute !== '#/overview/monitoring') {{
            console.error('Expected route #/overview/monitoring to be registered, got: ' + registeredRoute);
            process.exit(1);
        }}

        if (!context.Modules || typeof context.Modules.OverviewMonitoring !== 'function') {{
            console.error('Modules.OverviewMonitoring handler not exported');
            process.exit(1);
        }}

        // Mock canvas mounting
        const mockCanvas = {{ innerHTML: '' }};
        context.Modules.OverviewMonitoring(mockCanvas).then(() => {{
            const html = mockCanvas.innerHTML;
            if (!html.includes('page-container')) {{
                console.error('Expected page-container in rendered HTML');
                process.exit(1);
            }}
            if (!html.includes('Server Monitoring')) {{
                console.error('Expected Server Monitoring title in rendered HTML');
                process.exit(1);
            }}
            if (!html.includes('Wire Packet Stream')) {{
                console.error('Expected Wire Packet Stream in rendered HTML');
                process.exit(1);
            }}

            // Test drawer inspection call
            if (context.ServerMonitoringModule && typeof context.ServerMonitoringModule.inspectRequest === 'function') {{
                context.ServerMonitoringModule.inspectRequest(1);
                const sel = context.ServerMonitoringModule.getSelectedRequest();
                if (!sel || sel.id !== 2) {{
                    console.error('Drawer inspectRequest failed to set selected request');
                    process.exit(1);
                }}
            }}

            // Clean exit to prevent setInterval hanging
            process.exit(0);
        }}).catch(err => {{
            console.error('Render execution failed:', err);
            process.exit(1);
        }});
        """

        res = subprocess.run(["node", "-e", runner_script], capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Node VM runtime validation failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")


if __name__ == "__main__":
    unittest.main()
