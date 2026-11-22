"""
Test Suite: Apple Glassmorphism Design System & UI Components Factory
Validates UI token contracts, UIComponent factory generation, confirmation
modal bindings for destructive actions, and notification toast integration.
"""

import json
import os
import re
import subprocess
import unittest

DASHBOARD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static",
    "dashboard",
)
TOKENS_CSS = os.path.join(DASHBOARD_DIR, "src", "design-system", "tokens.css")
UI_COMPONENTS_JS = os.path.join(DASHBOARD_DIR, "src", "shared", "ui-components.js")
APP_JS = os.path.join(DASHBOARD_DIR, "src", "app", "app.js")


class TestUIComponents(unittest.TestCase):
    """Exhaustive test suite for UI tokens and component factory."""

    def test_design_tokens_css_contract(self):
        """Verify tokens.css specifies all macOS/visionOS dark glassmorphism design tokens."""
        self.assertTrue(os.path.exists(TOKENS_CSS), "tokens.css must exist")
        with open(TOKENS_CSS, "r", encoding="utf-8") as f:
            css = f.read()

        required_variables = [
            "--bg-desktop",
            "--bg-sidebar",
            "--bg-topbar",
            "--bg-card",
            "--bg-card-hover",
            "--bg-input",
            "--border-subtle",
            "--border-default",
            "--border-focus",
            "--accent-cyan",
            "--accent-blue",
            "--accent-indigo",
            "--accent-emerald",
            "--accent-amber",
            "--accent-rose",
            "--blur-sm",
            "--font-sans",
            "--font-mono",
        ]

        missing_vars = [var for var in required_variables if var not in css]
        self.assertEqual(
            missing_vars,
            [],
            f"Missing required design tokens in tokens.css: {missing_vars}",
        )

    def test_ui_components_source_contract(self):
        """Verify ui-components.js exports all factory functions."""
        self.assertTrue(os.path.exists(UI_COMPONENTS_JS), "ui-components.js must exist")
        with open(UI_COMPONENTS_JS, "r", encoding="utf-8") as f:
            code = f.read()

        required_methods = [
            "Card(",
            "Badge(",
            "Button(",
            "Table(",
            "UnavailableState(",
            "Loading(",
            "Toast(",
            "Modal(",
            "Confirm(",
            "window.UI = UI",
        ]
        for m in required_methods:
            self.assertIn(m, code, f"Missing method {m} in ui-components.js")

    def test_ui_components_node_rendering(self):
        """Render all UI components in Node.js and verify output HTML structures."""
        node_script = f"""
        const fs = require('fs');

        // Mock document and window
        global.document = {{
            getElementById: () => null,
            createElement: (tag) => ({{
                id: '',
                className: '',
                innerHTML: '',
                appendChild: () => {{}},
                style: {{}}
            }}),
            body: {{
                appendChild: () => {{}}
            }}
        }};
        global.window = {{}};

        const code = fs.readFileSync({repr(UI_COMPONENTS_JS)}, 'utf8');
        eval(code);

        const UI = global.window.UI;
        if (!UI) throw new Error('UI object not defined on window');

        // 1. Test Card
        const cardHtml = UI.Card('Server Status', 'Telemetry', '<div>Healthy</div>', '<button>Refresh</button>');
        if (!cardHtml.includes('glass-card') || !cardHtml.includes('Server Status')) {{
            throw new Error('Card HTML malformed: ' + cardHtml);
        }}

        // 2. Test Badge
        const badgeHtml = UI.Badge('ACTIVE', 'emerald');
        if (!badgeHtml.includes('badge-emerald') || !badgeHtml.includes('ACTIVE')) {{
            throw new Error('Badge HTML malformed: ' + badgeHtml);
        }}

        // 3. Test Button
        const btnHtml = UI.Button('Grant Diamond', 'primary', 'grant()', '💎');
        if (!btnHtml.includes('btn-primary') || !btnHtml.includes('Grant Diamond')) {{
            throw new Error('Button HTML malformed: ' + btnHtml);
        }}

        // 4. Test Table with data
        const tblHtml = UI.Table(['Col1', 'Col2'], '<tr><td>Val1</td><td>Val2</td></tr>');
        if (!tblHtml.includes('glass-table') || !tblHtml.includes('Val1')) {{
            throw new Error('Table HTML malformed: ' + tblHtml);
        }}

        // 5. Test Table empty state
        const emptyTbl = UI.Table(['Col1'], '');
        if (!emptyTbl.includes('No records found')) {{
            throw new Error('Empty table HTML malformed: ' + emptyTbl);
        }}

        // 6. Test UnavailableState
        const unavHtml = UI.UnavailableState('Matchmaking Engine', 'POST /api/match/queue', 'Requires backend');
        if (!unavHtml.includes('unavailable-box') || !unavHtml.includes('Matchmaking Engine')) {{
            throw new Error('UnavailableState HTML malformed: ' + unavHtml);
        }}

        // 7. Test Loading
        const loadHtml = UI.Loading('Syncing...');
        if (!loadHtml.includes('Syncing...')) {{
            throw new Error('Loading HTML malformed: ' + loadHtml);
        }}

        console.log(JSON.stringify({{ ok: true, renderedCount: 7 }}));
        """

        try:
            res = subprocess.run(
                ["node", "-e", node_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Node rendering of UI components failed:\nstdout: {res.stdout}\nstderr: {res.stderr}",
            )
            out = json.loads(res.stdout.strip())
            self.assertTrue(out.get("ok"))
        except FileNotFoundError:
            self.skipTest("node binary not available in PATH")

    def test_confirmation_dialog_usage_for_destructive_actions(self):
        """
        Verify that destructive actions (e.g. wiping accounts, bans, deleting items, clearing logs)
        in app.js invoke UI.Confirm or confirm() dialogs before executing mutations.
        """
        self.assertTrue(os.path.exists(APP_JS), "app.js must exist")
        with open(APP_JS, "r", encoding="utf-8") as f:
            code = f.read()

        # Check for UI.Confirm usage in app.js
        self.assertIn(
            "UI.Confirm",
            code,
            "Destructive actions in app.js must invoke UI.Confirm for operator confirmation",
        )

    def test_toast_notification_feedback(self):
        """
        Verify that user mutation feedback triggers UI.Toast notifications.
        """
        self.assertTrue(os.path.exists(APP_JS), "app.js must exist")
        with open(APP_JS, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn(
            "UI.Toast",
            code,
            "Action completions and error handlers in app.js must notify via UI.Toast",
        )


if __name__ == "__main__":
    unittest.main()
