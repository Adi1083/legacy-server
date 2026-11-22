"""
Test Suite: Workspace Routes Coverage & Dispatcher Validation
Validates all 38 workspace routes across all 10 functional domains,
verifying router registration, sidebar linkage, and error boundaries.
"""

import os
import re
import sys
import unittest
from typing import Dict, List, Set

DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "dashboard")
APP_JS = os.path.join(DASHBOARD_DIR, "src", "app", "app.js")
SIDEBAR_JS = os.path.join(DASHBOARD_DIR, "src", "app", "sidebar.js")
ROUTER_JS = os.path.join(DASHBOARD_DIR, "src", "app", "router.js")
MODULES_DIR = os.path.join(DASHBOARD_DIR, "src", "modules")

# The 38 mandatory workspace routes specified by Lead Architect (Agent 0)
SPEC_MANDATORY_ROUTES: Dict[str, List[str]] = {
    "01_overview": [
        "#/overview/main",
        "#/overview/monitoring",
    ],
    "02_players": [
        "#/players/directory",
        "#/players/inspector",
        "#/players/account",
        "#/players/bans",
        "#/players/sessions",
    ],
    "03_inventory": [
        "#/inventory/manager",
        "#/inventory/characters",
        "#/inventory/pets",
        "#/inventory/wardrobe",
    ],
    "04_economy": [
        "#/economy/currencies",
        "#/economy/wallet",
    ],
    "05_luck_royale": [
        "#/luck-royale/overview",
        "#/luck-royale/machines",
        "#/luck-royale/pools",
        "#/luck-royale/pity",
        "#/luck-royale/currencies",
        "#/luck-royale/forge",
        "#/luck-royale/events",
        "#/luck-royale/banners",
        "#/luck-royale/player",
        "#/luck-royale/transactions",
        "#/luck-royale/simulator",
    ],
    "06_game": [
        "#/game/modes",
        "#/game/maps",
        "#/game/matchmaking",
        "#/game/rooms",
    ],
    "07_social": [
        "#/social/mail",
        "#/social/mail-compose",
        "#/social/friends",
        "#/social/squads",
    ],
    "08_cms": [
        "#/cms/banners",
        "#/cms/lobby",
        "#/cms/announcements",
    ],
    "09_logs": [
        "#/logs/api",
        "#/logs/audit",
    ],
    "10_system": [
        "#/system/settings",
        "#/system/database",
        "#/system/security",
    ],
}


def extract_registered_routes() -> Set[str]:
    """Extract all routes registered with router.register() across app.js and any module files."""
    routes: Set[str] = set()

    # Scan app.js
    if os.path.exists(APP_JS):
        with open(APP_JS, "r", encoding="utf-8") as f:
            content = f.read()
            matches = re.findall(r"router\.register\(\s*['\"]([^'\"]+)['\"]", content)
            routes.update(matches)

    # Scan all module js files
    if os.path.exists(MODULES_DIR):
        for root, _, files in os.walk(MODULES_DIR):
            for file in files:
                if file.endswith(".js"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        matches = re.findall(r"(?:router|window\.appRouter)\.register\(\s*['\"]([^'\"]+)['\"]", content)
                        routes.update(matches)

    return routes


def extract_sidebar_routes() -> Set[str]:
    """Extract all href routes linked in sidebar.js."""
    routes: Set[str] = set()
    if os.path.exists(SIDEBAR_JS):
        with open(SIDEBAR_JS, "r", encoding="utf-8") as f:
            content = f.read()
            matches = re.findall(r"href=['\"](#[^'\"]+)['\"]", content)
            routes.update(matches)
    return routes


class TestRoutesCoverage(unittest.TestCase):
    """Exhaustive test suite for SPA workspace routes."""

    @classmethod
    def setUpClass(cls):
        cls.registered_routes = extract_registered_routes()
        cls.sidebar_routes = extract_sidebar_routes()

    def test_registered_route_count(self):
        """Verify that at least 38 routes are registered in the SPA router."""
        self.assertGreaterEqual(
            len(self.registered_routes),
            38,
            f"Expected at least 38 registered routes, found {len(self.registered_routes)}: {sorted(self.registered_routes)}",
        )

    def test_all_spec_domains_represented(self):
        """Verify that all 10 functional domains have 100% of their mandatory routes registered."""
        missing_by_domain: Dict[str, List[str]] = {}

        for domain, expected_routes in SPEC_MANDATORY_ROUTES.items():
            missing = [r for r in expected_routes if r not in self.registered_routes]
            if missing:
                missing_by_domain[domain] = missing

        self.assertEqual(
            missing_by_domain,
            {},
            f"Mandatory routes missing from router registration: {missing_by_domain}",
        )

    def test_sidebar_routes_have_handlers(self):
        """Verify that every route linked in the sidebar navigation has a corresponding registered handler."""
        unhandled_sidebar_routes = self.sidebar_routes - self.registered_routes
        self.assertEqual(
            unhandled_sidebar_routes,
            set(),
            f"Sidebar links without route handlers: {unhandled_sidebar_routes}",
        )

    def test_route_syntax_standards(self):
        """Verify that all registered routes strictly follow '#/<domain>/<action>' syntax."""
        pattern = re.compile(r"^#/[a-z0-9\-]+/[a-z0-9\-]+$")
        invalid_routes = [r for r in self.registered_routes if not pattern.match(r)]
        self.assertEqual(
            invalid_routes,
            [],
            f"Routes violating standard '#/<domain>/<action>' pattern: {invalid_routes}",
        )

    def test_router_implementation_features(self):
        """Verify AppRouter implements essential SPA dispatch features: hashchange, register, navigate, defaultRoute."""
        self.assertTrue(os.path.exists(ROUTER_JS), "router.js must exist")
        with open(ROUTER_JS, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("class AppRouter", code)
        self.assertIn("hashchange", code)
        self.assertIn("register(", code)
        self.assertIn("navigate(", code)
        self.assertIn("handleRoute(", code)
        self.assertIn("defaultRoute", code)
        self.assertIn("workspace-canvas", code)
        self.assertIn("Workspace Not Found", code, "Router must have an explicit 404 fallback")


if __name__ == "__main__":
    unittest.main()
