"""
Test Suite: Player Context & Global Reactive State Validation
Validates PlayerContext singleton API, dynamic account switching,
subscriber notifications, localStorage persistence, and audits frontend
source code for zero hardcoded account IDs (anti-regression).
"""

import json
import os
import re
import subprocess
import unittest
from typing import List, Tuple

DASHBOARD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static",
    "dashboard",
)
PLAYER_CONTEXT_JS = os.path.join(DASHBOARD_DIR, "src", "core", "context", "player-context.js")
SRC_DIR = os.path.join(DASHBOARD_DIR, "src")


class TestPlayerContext(unittest.TestCase):
    """Exhaustive test suite for PlayerContext and zero-hardcoded ID policy."""

    def test_player_context_source_contract(self):
        """Verify PlayerContext implements required contract methods and properties."""
        self.assertTrue(os.path.exists(PLAYER_CONTEXT_JS), "player-context.js must exist")
        with open(PLAYER_CONTEXT_JS, "r", encoding="utf-8") as f:
            code = f.read()

        required_symbols = [
            "class PlayerContext",
            "constructor(",
            "getSelectedAccountId(",
            "getCurrentPlayer(",
            "subscribe(",
            "_notify(",
            "setAccountId(",
            "refresh(",
            "ind_selected_account_id",
            "window.playerContext = new PlayerContext()",
        ]
        for sym in required_symbols:
            self.assertIn(
                sym,
                code,
                f"Missing required method or symbol '{sym}' in player-context.js",
            )

    def test_zero_hardcoded_account_ids_in_modules(self):
        """
        Audit all JavaScript files in src/ for hardcoded account ID 10001 in API requests or mutation payloads.
        Only default fallback initialization in player-context.js is allowed.
        """
        violations: List[Tuple[str, int, str]] = []

        # Patterns that indicate hardcoding account IDs rather than using playerContext
        hardcoded_patterns = [
            re.compile(r"account_id\s*:\s*10001\b"),
            re.compile(r"accountId\s*:\s*10001\b"),
            re.compile(r"account_id=10001\b"),
            re.compile(r"['\"]/api/[^'\"]*10001[^'\"]*['\"]"),
        ]

        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                if not file.endswith(".js"):
                    continue
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, DASHBOARD_DIR)

                # Skip player-context.js itself where 10001 is the initial default fallback
                if relpath.replace("\\", "/") == "src/core/context/player-context.js":
                    continue

                with open(filepath, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, start=1):
                        stripped = line.strip()
                        # Ignore comments
                        if stripped.startswith("//") or stripped.startswith("*"):
                            continue
                        for pat in hardcoded_patterns:
                            if pat.search(line):
                                violations.append((relpath, line_no, stripped))

        self.assertEqual(
            violations,
            [],
            f"Found hardcoded account IDs in frontend source! Must use window.playerContext.getSelectedAccountId():\n"
            + "\n".join(f"  {v[0]}:{v[1]} -> {v[2]}" for v in violations),
        )

    def test_player_context_node_runtime(self):
        """
        Execute PlayerContext in a Node.js VM sandbox to verify runtime instantiation,
        state updates, localStorage persistence, and subscriber notification dispatch.
        """
        node_script = f"""
        const fs = require('fs');
        const path = require('path');

        // Mock window & browser globals
        const storage = {{}};
        global.localStorage = {{
            getItem: (k) => storage[k] || null,
            setItem: (k, v) => {{ storage[k] = String(v); }},
            removeItem: (k) => {{ delete storage[k]; }}
        }};

        let fetchCalls = [];
        global.window = {{
            apiClient: {{
                get: async (url, params) => {{
                    fetchCalls.push({{ url, params }});
                    return {{ ok: true, data: {{ account_id: params ? params.account_id : 10001, nickname: 'TestUser' }} }};
                }}
            }}
        }};

        const code = fs.readFileSync({repr(PLAYER_CONTEXT_JS)}, 'utf8');
        eval(code);

        const ctx = global.window.playerContext;
        if (!ctx) throw new Error('window.playerContext not initialized');

        // Test initial default
        if (ctx.getSelectedAccountId() !== 10001) {{
            throw new Error('Initial account ID should be 10001, got ' + ctx.getSelectedAccountId());
        }}

        // Test subscription
        let subscriberNotified = false;
        let lastNotifiedId = null;
        const unsubscribe = ctx.subscribe((aid, player) => {{
            subscriberNotified = true;
            lastNotifiedId = aid;
        }});

        // Test switching account ID
        (async () => {{
            await ctx.setAccountId(10055);
            if (ctx.getSelectedAccountId() !== 10055) {{
                throw new Error('Account ID failed to update to 10055');
            }}
            if (global.localStorage.getItem('ind_selected_account_id') !== '10055') {{
                throw new Error('localStorage ind_selected_account_id not updated');
            }}
            if (!subscriberNotified || lastNotifiedId !== 10055) {{
                throw new Error('Subscriber was not notified with new account ID');
            }}

            // Test unsubscribe
            subscriberNotified = false;
            unsubscribe();
            await ctx.setAccountId(10099);
            if (subscriberNotified) {{
                throw new Error('Unsubscribed listener was still notified');
            }}

            console.log(JSON.stringify({{ ok: true, calls: fetchCalls.length }}));
        }})().catch(err => {{
            console.error(err);
            process.exit(1);
        }});
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
                f"Node runtime verification failed:\nstdout: {res.stdout}\nstderr: {res.stderr}",
            )
            output = json.loads(res.stdout.strip())
            self.assertTrue(output.get("ok"))
        except FileNotFoundError:
            self.skipTest("node binary not available in PATH")


if __name__ == "__main__":
    unittest.main()
