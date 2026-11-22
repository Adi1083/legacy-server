"""
IND PROJECT Control Center — QA & Regression Suite
Suite 10: Inventory & Vault Module Verification
Tests: Syntax, Component Contracts, Zero Emojis, Lifecycle & Node VM Runtime Execution
Covering: manager.js, characters.js, pets.js, wardrobe.js
"""

import os
import re
import subprocess
import unittest

DASHBOARD_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(os.path.dirname(DASHBOARD_TESTS_DIR))
INVENTORY_DIR = os.path.join(SERVER_DIR, "static", "dashboard", "src", "modules", "inventory")

INVENTORY_MODULE_FILES = [
    "manager.js",
    "characters.js",
    "pets.js",
    "wardrobe.js",
]


class TestInventoryModule(unittest.TestCase):
    """Automated QA & Regression test cases for the Inventory & Vault Modules."""

    def test_all_inventory_modules_exist_and_syntax_valid(self):
        """Verify all 4 inventory module files exist and pass Node.js syntax parsing."""
        for filename in INVENTORY_MODULE_FILES:
            filepath = os.path.join(INVENTORY_DIR, filename)
            self.assertTrue(os.path.isfile(filepath), f"File missing: {filepath}")

            res = subprocess.run(["node", "--check", filepath], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Node syntax check failed for {filename}:\n{res.stderr}")

    def test_zero_emojis_in_inventory_modules(self):
        """Verify that zero consumer emoji icons exist in any inventory module source."""
        emoji_pattern = re.compile(
            r"[\U0001F300-\U0001F6FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FAFF]|[\u2600-\u26FF]|[\u2700-\u27BF]"
        )
        for filename in INVENTORY_MODULE_FILES:
            filepath = os.path.join(INVENTORY_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            matches = emoji_pattern.findall(content)
            self.assertEqual(len(matches), 0, f"Found consumer emojis in {filename}: {matches}")

    def test_shared_design_classes_present(self):
        """Verify that all inventory modules utilize standard tokens.css design system classes."""
        for filename in INVENTORY_MODULE_FILES:
            filepath = os.path.join(INVENTORY_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("page-container", content, f"{filename} must utilize .page-container")
            self.assertIn("grid-4", content, f"{filename} must utilize .grid-4 metric strip")

    def test_shared_ui_components_invoked(self):
        """Verify that inventory modules invoke standardized UI library factory methods."""
        for filename in INVENTORY_MODULE_FILES:
            filepath = os.path.join(INVENTORY_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("UI.PageHeader", content, f"{filename} must invoke UI.PageHeader")
            self.assertIn("UI.StatCard", content, f"{filename} must invoke UI.StatCard")
            self.assertIn("UI.Badge", content, f"{filename} must invoke UI.Badge")
            self.assertIn("UI.Icon", content, f"{filename} must invoke UI.Icon")

    def test_node_vm_runtime_lifecycle(self):
        """Execute all inventory modules in Node VM to verify registration and error-free execution."""
        runner_script = f"""
        const fs = require('fs');
        const vm = require('vm');
        const path = require('path');

        const inventoryDir = {repr(INVENTORY_DIR)};
        const files = {repr(INVENTORY_MODULE_FILES)};

        const registeredRoutes = {{}};

        const context = {{
            window: {{}},
            document: {{
                activeElement: null,
                getElementById: (id) => null,
                addEventListener: () => {{}}
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
                    inventory: [
                        {{ item_id: 907100098, name: 'AK47 Flaming Dragon', count: 1 }},
                        {{ item_id: 700000001, name: 'Sakura Demon Blossom Bundle', count: 1 }}
                    ],
                    profile: {{
                        account_id: 10001,
                        nickname: 'PushpaGG',
                        level: 60,
                        avatar_id: 102000004,
                        selected_pet_id: 1300000001,
                        selected_pet_skin_id: 1310000001
                    }},
                    wallet: {{ coins: 10000, gems: 500 }}
                }}
            }}),
            post: async (url, payload) => ({{ ok: true, data: {{}} }})
        }};

        // Mock window.playerContext
        context.window.playerContext = {{
            getSelectedAccountId: () => 10001,
            getCurrentPlayer: () => ({{
                account_id: 10001,
                nickname: 'PushpaGG',
                level: 60,
                avatar_id: 102000004,
                inventory: [
                    {{ item_id: 907100098, name: 'AK47 Flaming Dragon', count: 1 }}
                ],
                clothes: [211000000, 208000000, 203000573],
                profile: {{
                    avatar_id: 102000004,
                    selected_pet_id: 1300000001,
                    selected_pet_skin_id: 1310000001
                }}
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
                trash: '', info: '', eye: '', sparkles: '', crosshair: '', ticket: '',
                package: '', check: ''
            }},
            Icon: (name, size, cls, color) => `<svg data-icon="${{name}}"></svg>`,
            Badge: (text, tone) => `<span class="badge badge-${{tone}}">${{text}}</span>`,
            StatCard: (title, val, sub, icon, tone) => `<div class="stat-card">${{title}}:${{val}}</div>`,
            PageHeader: (title, sub, acts, icon) => `<header class="page-header">${{title}}</header>`,
            Card: (title, sub, body) => `<div class="card">${{title}}</div>`,
            Table: (cols, rows, empty) => `<table>${{rows}}</table>`,
            Loading: (msg) => `<div>${{msg}}</div>`,
            Confirm: (t, m, cb, dest) => {{ if (typeof cb === 'function') cb(); }},
            Modal: (t, b, f) => {{}},
            CloseModal: () => {{}},
            Toast: (m, t) => {{}}
        }};

        vm.createContext(context);

        // Execute each inventory module file
        files.forEach(file => {{
            const code = fs.readFileSync(path.join(inventoryDir, file), 'utf-8');
            vm.runInContext(code, context, {{ filename: file }});
        }});

        // Verify route registrations
        const expectedRoutes = [
            '#/inventory/manager',
            '#/inventory/characters',
            '#/inventory/pets',
            '#/inventory/wardrobe'
        ];

        expectedRoutes.forEach(r => {{
            if (!registeredRoutes[r]) {{
                throw new Error('Route not registered: ' + r);
            }}
        }});

        // Execute route callbacks into mock canvas
        (async () => {{
            for (const r of expectedRoutes) {{
                const canvas = {{ innerHTML: '' }};
                await registeredRoutes[r](canvas);
                if (!canvas.innerHTML || !canvas.innerHTML.includes('page-container')) {{
                    throw new Error('Render output missing page-container for route: ' + r);
                }}
            }}
            console.log('ALL_INVENTORY_MODULES_EXECUTED_SUCCESSFULLY');
        }})().catch(err => {{
            console.error('LIFECYCLE_EXECUTION_ERROR:', err);
            process.exit(1);
        }});
        """
        res = subprocess.run(["node", "-e", runner_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node VM lifecycle execution failed:\n{res.stderr}\n{res.stdout}")
        self.assertIn("ALL_INVENTORY_MODULES_EXECUTED_SUCCESSFULLY", res.stdout)


if __name__ == "__main__":
    unittest.main()
