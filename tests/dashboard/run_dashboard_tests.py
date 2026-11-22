"""
Master Test Runner: IND PROJECT Control Center QA & Regression Matrix
Executes all dashboard verification suites, collecting comprehensive metrics,
performance benchmarks, and error diagnostics for REGRESSION_REPORT.md.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from typing import Dict, List, Tuple

DASHBOARD_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(os.path.dirname(DASHBOARD_TESTS_DIR))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

# Import test cases
from tests.dashboard.test_routes_coverage import TestRoutesCoverage
from tests.dashboard.test_player_context import TestPlayerContext
from tests.dashboard.test_ui_components import TestUIComponents
from tests.dashboard.test_html_shell_integrity import TestHtmlShellIntegrity
from tests.dashboard.test_backend_api_integration import TestBackendApiIntegration
from tests.dashboard.test_responsive_viewports import TestResponsiveViewports
from tests.dashboard.test_overview_module import TestOverviewModule
from tests.dashboard.test_monitoring_module import TestMonitoringModule
from tests.dashboard.test_players_module import TestPlayersModule
from tests.dashboard.test_inventory_module import TestInventoryModule
from tests.dashboard.test_economy_module import TestEconomyModule
from tests.dashboard.test_luck_royale_module import TestLuckRoyaleModule


def run_all_dashboard_suites() -> Tuple[unittest.TestResult, float, Dict[str, Dict[str, Any]]]:
    """Execute all registered QA & regression suites."""
    suite_classes = [
        ("01_SPA_Route_Coverage", TestRoutesCoverage),
        ("02_Player_Context_Reactivity", TestPlayerContext),
        ("03_UI_Design_System_Factory", TestUIComponents),
        ("04_HTML_Shell_Asset_Integrity", TestHtmlShellIntegrity),
        ("05_Backend_API_Integration", TestBackendApiIntegration),
        ("06_Responsive_Viewport_Validation", TestResponsiveViewports),
        ("07_Overview_Module_Validation", TestOverviewModule),
        ("08_Monitoring_Module_Validation", TestMonitoringModule),
        ("09_Players_Module_Validation", TestPlayersModule),
        ("10_Inventory_Module_Validation", TestInventoryModule),
        ("11_Economy_Module_Validation", TestEconomyModule),
        ("12_Luck_Royale_Module_Validation", TestLuckRoyaleModule),
    ]

    master_suite = unittest.TestSuite()
    suite_breakdown: Dict[str, Dict[str, Any]] = {}

    for name, s_cls in suite_classes:
        tests = unittest.defaultTestLoader.loadTestsFromTestCase(s_cls)
        suite_breakdown[name] = {"count": tests.countTestCases(), "class": s_cls.__name__}
        master_suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.perf_counter()
    result = runner.run(master_suite)
    duration = time.perf_counter() - start_time

    return result, duration, suite_breakdown


if __name__ == "__main__":
    result, duration, breakdown = run_all_dashboard_suites()

    total = result.testsRun
    failed = len(result.failures)
    errored = len(result.errors)
    passed = total - failed - errored
    pass_rate = (passed / total * 100) if total > 0 else 0.0

    print("\n" + "=" * 70)
    print(f"IND PROJECT CONTROL CENTER — QA & REGRESSION SUMMARY")
    print("=" * 70)
    print(f"Total Test Cases   : {total}")
    print(f"Passed             : {passed}")
    print(f"Failed             : {failed}")
    print(f"Errors             : {errored}")
    print(f"Pass Rate          : {pass_rate:.1f}%")
    print(f"Total Duration     : {duration:.3f}s")
    print("=" * 70)

    for suite_name, info in breakdown.items():
        print(f"  • {suite_name:<30} ({info['count']} tests)")
    print("=" * 70)

    if not result.wasSuccessful():
        sys.exit(1)
    sys.exit(0)
