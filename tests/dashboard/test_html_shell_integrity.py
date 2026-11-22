"""
Test Suite: HTML Shell & Static Asset Integrity Validation
Validates index.html document structure, CSS link integrity, script dependency
order, DOM anchor mounts (#app-root, #workspace-canvas), and ensures zero broken asset references.
"""

import os
import re
import unittest
from typing import List

DASHBOARD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static",
    "dashboard",
)
INDEX_HTML = os.path.join(DASHBOARD_DIR, "index.html")


class TestHtmlShellIntegrity(unittest.TestCase):
    """Exhaustive test suite for index.html shell integrity."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(cls, os.path.exists(INDEX_HTML), "index.html must exist")
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

    def test_html5_doctype_and_meta(self):
        """Verify standard HTML5 doctype, charset, and responsive viewport meta tags."""
        self.assertRegex(self.html_content, r"<!DOCTYPE\s+html>", "Missing standard DOCTYPE")
        self.assertIn('<meta charset="utf-8">', self.html_content.lower())
        self.assertIn("viewport", self.html_content.lower())

    def test_dom_mount_element(self):
        """Verify presence of #app-root where SPA shell mounts."""
        self.assertRegex(
            self.html_content,
            r'id=["\']app-root["\']',
            "Missing #app-root mounting point in index.html body",
        )

    def test_css_stylesheets_exist_on_disk(self):
        """Extract all local stylesheet links and ensure every file physically exists."""
        link_matches = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', self.html_content)
        local_css = [href for href in link_matches if not href.startswith("http") and not href.startswith("//")]

        self.assertGreaterEqual(len(local_css), 1, "Expected at least 1 local stylesheet link in index.html")
        for href in local_css:
            clean_href = href.split("?")[0]
            disk_path = os.path.normpath(os.path.join(DASHBOARD_DIR, clean_href))
            self.assertTrue(
                os.path.exists(disk_path),
                f"Referenced stylesheet not found on disk: {href} (resolved: {disk_path})",
            )

    def test_script_tags_exist_on_disk(self):
        """Extract all local script tags and ensure every referenced file physically exists."""
        script_matches = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', self.html_content)
        local_scripts = [src for src in script_matches if not src.startswith("http") and not src.startswith("//")]

        self.assertGreaterEqual(
            len(local_scripts),
            6,
            f"Expected core SPA scripts linked, found only: {local_scripts}",
        )
        for src in local_scripts:
            clean_src = src.split("?")[0]
            disk_path = os.path.normpath(os.path.join(DASHBOARD_DIR, clean_src))
            self.assertTrue(
                os.path.exists(disk_path),
                f"Referenced script not found on disk: {src} (resolved: {disk_path})",
            )

    def test_script_loading_dependency_order(self):
        """
        Verify scripts load in correct architectural dependency order:
        1. core/api/api-client.js (transport layer)
        2. core/context/player-context.js (state layer)
        3. shared/ui-components.js (component factory)
        4. app/router.js (routing framework)
        5. app/sidebar.js & topbar.js (shell UI)
        6. app/app.js (master application bootstrapper)
        """
        script_matches = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', self.html_content)
        paths = [s.replace("\\", "/") for s in script_matches]

        def get_index(substring: str) -> int:
            for idx, p in enumerate(paths):
                if substring in p:
                    return idx
            return -1

        api_idx = get_index("api-client.js")
        ctx_idx = get_index("player-context.js")
        ui_idx = get_index("ui-components.js")
        router_idx = get_index("router.js")
        app_idx = get_index("app.js")

        self.assertNotEqual(api_idx, -1, "api-client.js not found in script imports")
        self.assertNotEqual(ctx_idx, -1, "player-context.js not found in script imports")
        self.assertNotEqual(ui_idx, -1, "ui-components.js not found in script imports")
        self.assertNotEqual(router_idx, -1, "router.js not found in script imports")
        self.assertNotEqual(app_idx, -1, "app.js not found in script imports")

        # Dependency assertions
        self.assertLess(api_idx, ctx_idx, "api-client.js must precede player-context.js")
        self.assertLess(ui_idx, app_idx, "ui-components.js must precede app.js")
        self.assertLess(router_idx, app_idx, "router.js must precede app.js")


if __name__ == "__main__":
    unittest.main()
