"""
IND PROJECT Control Center — Automated Test Suite
Suite 12: Luck Royale Studio Module Contract & UI Standards (test_luck_royale_module.py)
Tests: Syntax, Component Contracts, Zero Emojis, Lifecycle & Node VM Runtime Execution
"""

import os
import re
import subprocess
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULE_DIR = os.path.join(BASE_DIR, "static", "dashboard", "src", "modules", "luck-royale")

MODULE_FILES = [
    "common.js",
    "overview.js",
    "machines.js",
    "pools.js",
    "banners.js",
    "events.js",
    "pity.js",
    "currencies.js",
    "forge.js",
    "player.js",
    "transactions.js",
    "simulator.js",
    "config.js",
]


class TestLuckRoyaleModule(unittest.TestCase):
    """Automated verification suite for Luck Royale Studio modules."""

    def test_all_luck_royale_modules_exist_and_syntax_valid(self):
        """Verify all luck-royale module files exist and pass Node.js syntax parsing."""
        for filename in MODULE_FILES:
            filepath = os.path.join(MODULE_DIR, filename)
            self.assertTrue(os.path.isfile(filepath), f"Missing luck-royale file: {filepath}")

            result = subprocess.run(
                ["node", "--check", filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"Node syntax error in {filename}:\n{result.stderr}",
            )

    def test_zero_emojis_in_luck_royale_modules(self):
        """Verify that zero consumer emoji icons exist in any luck-royale module source."""
        emoji_pattern = re.compile(
            r"[\U0001F300-\U0001F6FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FAFF]|[\u2600-\u26FF]|[\u2700-\u27BF]"
        )

        for filename in MODULE_FILES:
            filepath = os.path.join(MODULE_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            matches = emoji_pattern.findall(content)
            self.assertEqual(
                len(matches),
                0,
                f"Found consumer emojis in {filename}: {matches}",
            )

    def test_shared_design_classes_present(self):
        """Verify that luck-royale modules utilize standard tokens.css design system classes."""
        primary_modules = ["overview.js", "machines.js", "pools.js", "banners.js", "pity.js", "currencies.js"]
        for filename in primary_modules:
            filepath = os.path.join(MODULE_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("page-container", content, f"{filename} must use .page-container class")
            self.assertIn("glass-card", content, f"{filename} must use .glass-card class")

    def test_shared_ui_components_invoked(self):
        """Verify that luck-royale modules invoke standardized UI library factory methods."""
        for filename in ["overview.js", "machines.js", "pools.js", "banners.js", "events.js", "pity.js", "currencies.js"]:
            filepath = os.path.join(MODULE_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertTrue(
                "window.UI.PageHeader" in content or "UI.PageHeader" in content,
                f"{filename} must invoke UI.PageHeader",
            )
            self.assertTrue(
                "window.UI.Badge" in content or "UI.Badge" in content or "rarityBadge" in content,
                f"{filename} must invoke UI.Badge or badge helper",
            )

    def test_node_vm_runtime_lifecycle(self):
        """Execute all luck-royale modules in Node VM to verify registration and error-free execution."""
        mod_dir_escaped = MODULE_DIR.replace('\\', '/')
        node_script = f"""
        const fs = require('fs');
        const path = require('path');
        const vm = require('vm');

        const context = {{
            window: {{
                location: {{ hash: '#/luck-royale/overview' }},
                UI: {{
                    PageHeader: (t, s, a, i) => `<header><h1>${{t}}</h1><p>${{s}}</p></header>`,
                    Card: (t, s, b, f) => `<div class="glass-card"><h3>${{t}}</h3><div>${{b}}</div></div>`,
                    Badge: (l, v) => `<span class="badge ${{v}}">${{l}}</span>`,
                    Table: (h, r, e) => `<table><thead><tr>${{h.map(x=>'<th>'+x+'</th>').join('')}}</tr></thead><tbody>${{r}}</tbody></table>`,
                    Loading: (m) => `<div>${{m}}</div>`,
                    Icon: (n, s) => `<svg class="lucide-${{n}}" width="${{s}}" height="${{s}}"></svg>`,
                    Toast: () => {{}},
                    Confirm: () => {{}}
                }},
                apiClient: {{
                    get: async (url, params) => {{
                        if (url.includes('overview')) return {{ ok: true, data: {{ total_spins: 100, diamonds_burn: 5000, gold_burn: 10000 }} }};
                        if (url.includes('assets')) return {{ ok: true, data: {{ assets: [{{ filename: 'test.png', url: '/banners/test.png', size_bytes: 1024, category: 'General' }}] }} }};
                        if (url.includes('reward-images')) return {{ ok: true, data: {{ reward_images: {{}} }} }};
                        if (url.includes('reward-pools')) return {{ ok: true, data: {{ items: [{{ item_id: 110100008, name: 'Voucher', weight: 100, reward_level: 1, item_num: 1 }}] }} }};
                        if (url.includes('meters')) return {{ ok: true, data: {{ meters: {{ 3: 50, 4: 20, 5: 10, 6: 5 }} }} }};
                        if (url.includes('events-banners')) return {{ ok: true, data: {{ assignments: [{{ chest_id: 3, display_name: 'Diamond Royale', banner_url: '/banners/test.png' }}] }} }};
                        if (url.includes('exchange')) return {{ ok: true, data: {{ exchanges: [{{ item_id: 710000410, name: 'Bundle', forge_tab_id: 1, evolution_stones: 3, blueprints: 1 }}] }} }};
                        if (url.includes('players/')) return {{ ok: true, data: {{ player: {{ account_id: 10001, nickname: 'Commander', level: 100, inventory: [] }} }} }};
                        if (url.includes('transactions')) return {{ ok: true, data: {{ transactions: [{{ timestamp: 12345678, machine_id: 3, gacha_type: 1, cost_amount: 60, cost_type: 2 }}] }} }};
                        return {{ ok: true, data: {{ machines: [{{ chest_id: 3, display_name: 'Diamond Royale', chest_name: 'CHEST_DIAMOND', enabled: true, coin_type: 2, once_price: 60, ten_price: 600, rare_item_max: 150 }}] }} }};
                    }},
                    post: async () => ({{ ok: true, data: {{}} }}),
                    put: async () => ({{ ok: true, data: {{}} }}),
                    delete: async () => ({{ ok: true, data: {{}} }})
                }},
                playerContext: {{
                    getSelectedAccountId: () => 10001,
                    setAccountId: async () => {{}}
                }},
                appRouter: {{
                    handleRoute: () => {{}}
                }},
                LuckRoyale: {{}},
                Modules: {{}}
            }},
            console: console,
            setTimeout: setTimeout,
            clearTimeout: clearTimeout,
            document: {{
                getElementById: () => null,
                body: {{ insertAdjacentHTML: () => {{}} }}
            }}
        }};
        context.window.window = context.window;
        vm.createContext(context);

        const modDir = '{mod_dir_escaped}';
        const files = ['common.js', 'overview.js', 'machines.js', 'pools.js', 'banners.js', 'events.js', 'pity.js', 'currencies.js', 'forge.js', 'player.js', 'transactions.js', 'simulator.js', 'config.js'];

        for (const file of files) {{
            const code = fs.readFileSync(path.join(modDir, file), 'utf-8');
            vm.runInContext(code, context);
        }}

        async function testLifecycles() {{
            const canvas = {{ innerHTML: '' }};
            await context.window.LuckRoyale.Overview(canvas);
            if (!canvas.innerHTML.includes('Luck Royale Studio')) throw new Error('Overview render failed');

            await context.window.LuckRoyale.Machines(canvas);
            if (!canvas.innerHTML.includes('Royale Studio')) throw new Error('Machines render failed');

            await context.window.LuckRoyale.Pools(canvas);
            if (!canvas.innerHTML.includes('Reward Pool Editor')) throw new Error('Pools render failed');

            await context.window.LuckRoyale.Banners(canvas);
            if (!canvas.innerHTML.includes('Artwork & Image Studio')) throw new Error('Banners render failed');

            await context.window.LuckRoyale.Events(canvas);
            if (!canvas.innerHTML.includes('Event Rewards & Schedules')) throw new Error('Events render failed');

            await context.window.LuckRoyale.Pity(canvas);
            if (!canvas.innerHTML.includes('Lucky Meter & Guaranteed Pity')) throw new Error('Pity render failed');

            await context.window.LuckRoyale.Currencies(canvas);
            if (!canvas.innerHTML.includes('Vouchers & Spin Costs')) throw new Error('Currencies render failed');

            await context.window.LuckRoyale.Forge(canvas);
            if (!canvas.innerHTML.includes('Incubator Special Exchange Forge')) throw new Error('Forge render failed');

            await context.window.LuckRoyale.Player(canvas);
            if (!canvas.innerHTML.includes('Player Gacha State')) throw new Error('Player render failed');

            await context.window.LuckRoyale.Transactions(canvas);
            if (!canvas.innerHTML.includes('Spin Audit Ledger')) throw new Error('Transactions render failed');

            await context.window.LuckRoyale.Simulator(canvas);
            if (!canvas.innerHTML.includes('Probability Simulator')) throw new Error('Simulator render failed');

            await context.window.LuckRoyale.Config(canvas);
            if (!canvas.innerHTML.includes('Configuration Backup')) throw new Error('Config render failed');

            console.log('ALL_LIFECYCLES_PASSED');
        }}

        testLifecycles().catch(e => {{
            console.error('LIFECYCLE_ERROR:', e);
            process.exit(1);
        }});
        """;

        result = subprocess.run(
            ["node", "-e", node_script],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Node VM lifecycle test failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}",
        )
        self.assertIn("ALL_LIFECYCLES_PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
